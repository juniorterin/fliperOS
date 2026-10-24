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
# tem continua sem ter): ~/.local/share/fliperos/scrape-state.json. Com um
# jogo aberto, para (a rede e o disco sao do jogo). O menu do Tab mostra o
# andamento (total, left, torrent).

import json
import os
import threading
import time

RETRY_DAYS = 30
PAUSE = 0.6                # entre um jogo e outro (o Arcade Database agradece)
TORRENT_EVERY = 6 * 3600   # de quanto em quanto tempo os pacotes sao conferidos
STATUS_EVERY = 20          # o andamento dos torrents, enquanto baixam


class Harvester:
    def __init__(self, fe):
        self.fe, self.fd, self.lib = fe, fe.fd, fe.lib
        self.total = 0             # jogos nas pastas
        self.left = 0              # jogos que ainda faltam
        self.scanned = False
        self.current = None
        self.paused = False        # um jogo aberto
        self.torrent = None        # (porcentagem, estado) dos pacotes
        self.wake = threading.Event()
        self.path = os.path.join(self.fd.web.player_home(), ".local", "share", "fliperos", "scrape-state.json")
        self.state = self.load()

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
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            with open(self.path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(self.state, f)
            os.replace(self.path + ".tmp", self.path)
        except OSError:
            pass

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

    # ── O laco ──
    def run(self):
        time.sleep(5)              # a tela abre primeiro
        while True:
            # Os torrents primeiro: baixam sozinhos (o Transmission) enquanto
            # o laco busca o resto, um jogo de cada vez.
            self.torrents()
            generation = self.lib.generation
            for g in self.scan():
                while self.paused:
                    time.sleep(1)
                if self.lib.generation != generation:
                    break          # as listas mudaram: conta de novo
                k = self.key(g)
                if self.fe.scraping is not g:
                    self.current = g
                    try:
                        self.fd.scrape(self.lib, g, only_missing=True, bulk=True)
                    except Exception:  # sem rede, um site fora: na proxima volta
                        pass
                    self.current = None
                    self.fe.dirty.add((g["_system"]["key"], g["Name"]))
                self.state.setdefault("tried", {})[k] = int(time.time())
                self.left = max(0, self.left - 1)
                if self.left % 20 == 0:
                    self.save()
                time.sleep(PAUSE)
            self.save()
            self.wake.wait(600)
            self.wake.clear()

    def torrents(self):
        """Os pacotes em torrent, de TORRENT_EVERY em TORRENT_EVERY."""
        if self.paused or time.time() - self.state.get("torrents", 0) < TORRENT_EVERY:
            return
        self.state["torrents"] = int(time.time())
        self.save()
        self.fd.setup("--mediapacks", "auto", timeout=1800)
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

    def watch(self):
        """O andamento dos torrents enquanto houver um baixando."""
        time.sleep(15)
        while True:
            if self.state.get("torrents"):
                self.status()
            time.sleep(STATUS_EVERY if self.torrent and self.torrent[1] == "downloading" else 300)
