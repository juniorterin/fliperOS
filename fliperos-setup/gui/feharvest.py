# O scrape automatico do frontend do FliperOS: em segundo plano, um jogo de
# cada vez, o que falta de cada jogo das pastas.
#
# - Arcade: as informacoes, a tela, o flyer, o marquee e o logo do Arcade
#   Database; console: a capa e a tela do libretro-thumbnails (fedata.scrape
#   com bulk: sem os videos, que sao grandes um a um).
# - Os videos e os logos que faltarem: os pacotes em torrent do Setup > Games >
#   Scraper > Art packs by torrent, so os arquivos dos jogos que estao nas
#   pastas (fliperos-setup --mediapacks auto), de tempos em tempos.
#
# Um jogo tentado nao e tentado de novo por RETRY_DAYS dias (o que a fonte nao
# tem continua sem ter): ~/.local/share/fliperos/scrape-state.json. O menu do
# Tab mostra o andamento (total, left, torrent).
#
# Quem roda o laco e o servico fliperos-scrape (gui/fliperos-scrape --daemon,
# Setup > System > Services > Auto scrape): continua com um jogo aberto e com
# o frontend fechado, com a CPU e o disco na prioridade mais baixa. Ele grava
# o andamento em scrape-status.json, que o frontend le (follow). Sem o
# servico, o frontend roda o laco ele mesmo e para durante o jogo.

import fcntl
import json
import os
import threading
import time

RETRY_DAYS = 30
PAUSE = 0.6                # entre um jogo e outro (o Arcade Database agradece)
TORRENT_EVERY = 6 * 3600   # de quanto em quanto tempo os pacotes sao conferidos
STATUS_EVERY = 20          # o andamento dos torrents, enquanto baixam


# Os pacotes de arte da imagem e os da pessoa (lib/mediapacks.sh): o tipo
# de cada um, para o quadro do Tab dizer LOGOS e VIDEOS.
MEDIA_TORRENTS = ("/usr/local/share/fliperos/media-torrents", "/etc/fliperos/media-torrents")
KIND_LABELS = {"logo": "LOGOS", "preview": "VIDEOS", "snap": "SCREENS", "box": "BOXES", "marquee": "MARQUEES"}


def pack_kinds():
    kinds = {}
    for path in MEDIA_TORRENTS:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 2 and not line.startswith("#"):
                        kinds[parts[0]] = KIND_LABELS.get(parts[1], parts[1].upper())
        except OSError:
            pass
    return kinds


class Harvester:
    RETRY_DAYS = RETRY_DAYS
    def __init__(self, fe):
        self.fe, self.fd, self.lib = fe, fe.fd, fe.lib
        self.total = 0             # jogos nas pastas
        self.left = 0              # jogos que ainda faltam
        self.scanned = False
        self.current = None
        self.paused = False        # um jogo aberto
        self.torrent = None        # (porcentagem, estado) dos pacotes
        self.packs = {}            # pacote -> (estado, porcentagem)
        self.wake = threading.Event()
        self.path = os.path.join(self.fd.web.player_home(), ".local", "share", "fliperos", "scrape-state.json")
        self.status_path = self.path.replace("scrape-state", "scrape-status")
        self.state = self.load()
        self.followed = (0, time.time())   # (mtime do status, ultima leitura)
        self.publishing = False    # o servico: grava o andamento (publish)
        self.external = False      # no frontend: o servico esta rodando o laco (follow)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        threading.Thread(target=self.watch, daemon=True).start()

    # ── O estado ──
    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self):
        """Grava o estado somado ao que esta no disco: o servico e o frontend
        (o scrape do jogo sob o cursor) gravam o mesmo arquivo."""
        disk = self.load()
        for name, value in disk.items():
            if isinstance(value, dict) and isinstance(self.state.get(name), dict):
                for k, t in value.items():
                    self.state[name][k] = max(t, self.state[name].get(k, 0))
            elif name not in self.state:
                self.state[name] = value
        self.write(self.path, self.state)

    @staticmethod
    def write(path, data):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".%d.tmp" % os.getpid(), "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(path + ".%d.tmp" % os.getpid(), path)
        except OSError:
            pass

    def publish(self):
        """O andamento para o frontend (o servico)."""
        if not self.publishing:
            return
        self.write(self.status_path, {
            "total": self.total, "left": self.left, "scanned": self.scanned,
            "current": self.fd.short_title(self.current) if self.current else "",
            "torrent": self.torrent, "packs": self.packs, "pid": os.getpid()})

    def follow(self):
        """No frontend com o servico no ar: o andamento dele, e os jogos que
        ele buscou desde a ultima leitura tem a midia lida de novo. False: o
        servico nao esta rodando (o frontend roda o laco)."""
        try:
            mtime = os.stat(self.status_path).st_mtime
            with open(self.status_path, encoding="utf-8") as f:
                data = json.load(f)
            os.kill(int(data["pid"]), 0)
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if mtime != self.followed[0]:
            since = self.followed[1]
            self.followed = (mtime, time.time())
            self.total, self.left = data.get("total", 0), data.get("left", 0)
            self.scanned, self.torrent = data.get("scanned", False), data.get("torrent")
            self.packs = {k: tuple(v) for k, v in (data.get("packs") or {}).items()}
            self.current = {"Title": data["current"], "Name": data["current"]} if data.get("current") else None
            self.state = self.load()
            for key, t in self.state.get("tried", {}).items():
                if t >= since - 5 and "/" in key:
                    self.fe.dirty.add(tuple(key.split("/", 1)))
        return True

    @staticmethod
    def key(game):
        return "%s/%s" % (game["_system"]["key"], game["Name"])

    # ── O que falta ──
    def kinds(self, game):
        """A arte que o scrape de um jogo traz (os videos vem do torrent)."""
        if game["_system"].get("arcade"):
            return ("snap", "box", "marquee", "logo")
        return ("snap", "box")

    def needs(self, game):
        tried = self.state.get("tried", {}).get(self.key(game), 0)
        if time.time() - tried < RETRY_DAYS * 86400:
            return False
        return self.missing(game)

    def missing(self, game):
        """O jogo ainda sem as informacoes (arcade) ou sem alguma arte."""
        if game["_system"].get("arcade"):
            path = self.lib.info.path(game["_system"]["key"], game["Name"], "en")
            if path and not os.path.exists(path):
                return True
        return any(not self.lib.media(game, kind) for kind in self.kinds(game))

    def scan(self):
        """Os jogos de todas as pastas (sem repetir) e os que faltam."""
        games, seen = [], set()
        for system in self.lib.systems:
            try:
                rows = self.lib.games(system)
            except Exception:  # uma pasta fora (o disco saiu): fica para depois
                rows = []
            for g in rows:
                k = self.key(g)
                if k not in seen:
                    seen.add(k)
                    games.append(g)
        todo = [g for g in games if self.needs(g)]
        self.total, self.left, self.scanned = len(games), len(todo), True
        return todo

    def mark(self, game):
        self.state.setdefault("tried", {})[self.key(game)] = int(time.time())

    # ── Um scraper de cada vez ──
    # O do Setup (gui/fliperos-scrape) segura a trava enquanto roda; o laco do
    # frontend a pega a cada jogo e espera quando ela esta com o outro.
    def lock(self, wait):
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            f = open(self.path[:-len(".json")] + ".lock", "w")
        except OSError:
            return None
        try:
            fcntl.flock(f, fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))
        except OSError:
            f.close()
            return False
        return f

    @staticmethod
    def unlock(f):
        if f:
            fcntl.flock(f, fcntl.LOCK_UN)
            f.close()

    # ── O laco ──
    def run(self, reload=None):
        """O laco, para sempre. reload: o servico, que nao tem o frontend para
        refazer as listas, le a biblioteca de novo antes de cada volta."""
        time.sleep(5)              # a tela abre primeiro
        while True:
            if reload:
                self.lib = self.fe.lib = reload()
            # No frontend, com o servico no ar, o laco e dele.
            while self.external:
                time.sleep(2)
            self.run_pass()
            self.wake.wait(600)
            self.wake.clear()

    def run_pass(self):
        # Os torrents primeiro: baixam sozinhos (o Transmission) enquanto
        # o laco busca o resto, um jogo de cada vez.
        self.torrents()
        generation = self.lib.generation
        todo = self.scan()
        self.publish()
        for g in todo:
            while self.paused or self.external:
                time.sleep(1)
            if self.lib.generation != generation:
                break          # as listas mudaram: conta de novo
            lock, waited = self.lock(wait=False), False
            while lock is False:   # o scraper do Setup esta rodando
                if not waited:
                    self.save()
                waited = True
                time.sleep(5)
                lock = self.lock(wait=False)
            fetched = False
            try:
                # O do Setup pode ter feito este enquanto o laco esperava.
                if waited:
                    self.state = self.load()
                if self.fe.scraping is not g and self.needs(g):
                    self.current = g
                    self.publish()
                    try:
                        self.fd.scrape(self.lib, g, only_missing=True, bulk=True)
                    except Exception:  # sem rede, um site fora: na proxima volta
                        pass
                    self.current = None
                    self.fe.dirty.add((g["_system"]["key"], g["Name"]))
                    fetched = True
                self.mark(g)
            finally:
                self.unlock(lock)
            self.left = max(0, self.left - 1)
            # Cada jogo buscado vai logo ao disco: o frontend (follow) le a
            # midia dele de novo.
            if fetched or self.left % 20 == 0:
                self.save()
                self.publish()
            time.sleep(PAUSE)
        self.save()
        self.publish()

    def torrents(self):
        """Os pacotes em torrent, de TORRENT_EVERY em TORRENT_EVERY. A saida
        diz os pacotes de .zip de letra ("ID<TAB>jogos<TAB>zip"): esses vem
        arquivo por arquivo, pelo scrape de cada jogo (fedata.pack_art)."""
        if self.paused or (time.time() - self.state.get("torrents", 0) < TORRENT_EVERY
                           and "zip" in self.state):
            return
        self.state["torrents"] = int(time.time())
        self.save()
        out = self.fd.setup("--mediapacks", "auto", timeout=1800)
        self.state["zip"] = sorted(line.split("\t")[0] for line in out.splitlines()
                                   if line.count("\t") == 2 and line.endswith("\tzip"))
        self.save()
        self.status()

    def status(self):
        out = self.fd.setup("--mediapacks", "status", timeout=60)
        values = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
        state = values.get("state", "none")
        try:
            pct = int(float(values.get("pct", "0")))
        except ValueError:
            pct = 0
        self.torrent = (pct, state) if state not in ("none", "") else None
        # Cada pacote: "pack.ID=estado|pct|texto".
        self.packs = {}
        for key, value in values.items():
            if key.startswith("pack."):
                parts = value.split("|")
                try:
                    self.packs[key[5:]] = (parts[0], int(float(parts[1])) if len(parts) > 1 else 0)
                except ValueError:
                    self.packs[key[5:]] = (parts[0], 0)

    def pack_line(self):
        """Os pacotes de arte por tipo, para o quadro do Tab: "LOGOS 34%",
        "LOGOS DONE", "VIDEOS ONE BY ONE" (o .zip de letra). Vazio sem
        nenhum pacote."""
        kinds = pack_kinds()
        rows = {}
        for pack, (state, pct) in self.packs.items():
            label = kinds.get(pack, "ART")
            text = {"downloading": "%d%%" % pct, "ready": "SAVING", "done": "DONE",
                    "stopped": "STOPPED"}.get(state, state.upper())
            # O tipo com mais de um pacote: o que ainda baixa vale.
            if label not in rows or state == "downloading":
                rows[label] = text
        for pack in self.state.get("zip", []):
            rows.setdefault(kinds.get(pack, "ART"), "ONE BY ONE")
        return "  ".join("%s %s" % (label, rows[label]) for label in sorted(rows))

    def watch(self):
        """O andamento dos torrents enquanto houver um baixando."""
        time.sleep(15)
        while True:
            if self.state.get("torrents") and not self.external:
                self.status()
                self.publish()
            time.sleep(STATUS_EVERY if self.torrent and self.torrent[1] == "downloading" else 300)
