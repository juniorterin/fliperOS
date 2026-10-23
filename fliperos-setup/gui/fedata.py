# Os dados do frontend do FliperOS (gui/fliperos-frontend): as pastas de
# jogos, os jogos de cada uma, os filtros, os favoritos, a midia e as
# informacoes salvas. Sao os mesmos do painel web: as funcoes vem dele
# (config/fliperos-web, importado como modulo), para os dois mostrarem a
# mesma coisa.
#
# - As pastas e o comando de cada uma: fliperos-setup --systems.
# - Os jogos: a romlist do Attract-Mode Plus de cada pasta. As de arcade tem
#   o nome, o ano, o fabricante, os clones e a categoria do XML do MAME (a
#   AttractPlus ROM List, fliperos-romclean romlist); um arquivo que a lista
#   ainda nao tem aparece pelo nome. Uma pasta que muda pede ao Setup que
#   refaca as listas (fliperos-setup --romlists) e o frontend as le de novo.
# - Os filtros: os que o Setup poe em cada tela do Attract-Mode
#   (fliperos-setup --filters), aplicados como ele aplica.
# - Os favoritos: ~/.config/fliperos/favourites. As vezes jogadas: as do
#   Attract-Mode (~/.attract/stats), que o frontend tambem grava.
# - O que a pessoa muda num jogo (Classify, Rename):
#   ~/media/info/<pasta>/<set>.user.json, por cima da romlist.

import json
import os
import re
import subprocess
import threading
import time
from importlib.machinery import SourceFileLoader
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
SETUP = os.environ.get("FLIPEROS_SETUP", "/usr/local/bin/fliperos-setup")
WEB = os.environ.get("FLIPEROS_WEB_MODULE", "/opt/fliperos/bin/fliperos-web")
MEDIA_TYPES = ("snap", "box", "logo", "marquee")
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
# Os campos que o Classify muda (os da romlist do Attract-Mode).
EDIT_FIELDS = ("Title", "Category", "Players", "Buttons", "Control", "Year", "Manufacturer", "Rotation", "Series")
ARCADE_ALL = "Arcade"


def load_web():
    """O config/fliperos-web como modulo (instalado ou o do repositorio)."""
    path = WEB if os.path.exists(WEB) else os.path.join(HERE, "..", "..", "config", "fliperos-web")
    loader = SourceFileLoader("fliperos_web", path)
    spec = importlib.util.spec_from_loader("fliperos_web", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


web = load_web()


def setup(*args, timeout=120):
    """O fliperos-setup, como root (a regra do sudoers do usuario) ou direto."""
    cmd = [SETUP, *args]
    if os.geteuid() != 0 and os.path.exists("/usr/bin/sudo"):
        cmd = ["sudo", "-n", *cmd]
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def parse_systems(out):
    rows = []
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) >= 7:
            key, folder, platform, name, exe, args, exts = parts[:7]
            rows.append({"key": key, "folder": folder, "platform": platform, "name": name, "exe": exe,
                         "args": args, "extensions": [e.lower() for e in exts.split(";") if e],
                         "arcade": len(parts) > 7 and parts[7] == "1"})
    return rows


def cache_dir():
    path = os.path.join(web.player_home(), ".cache", "fliperos")
    os.makedirs(path, exist_ok=True)
    return path


def cached(name, fresh):
    """O que o Setup respondeu da ultima vez (abre na hora) ou, sem isso, a
    resposta de agora."""
    path = os.path.join(cache_dir(), name)
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        pass
    return save_cache(name, fresh())


def save_cache(name, text):
    if text.strip():
        path = os.path.join(cache_dir(), name)
        try:
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(path + ".tmp", path)
        except OSError:
            pass
    return text


# ── Filtros, como o Attract-Mode os aplica ─────────────────────────

NUMERIC = {"greater_than": lambda a, b: a > b, "less_than": lambda a, b: a < b,
           "greater_than_or_equal": lambda a, b: a >= b, "less_than_or_equal": lambda a, b: a <= b}
SPECIAL = re.compile(r"[.+*?^$()\[\]{}|\\]")


def number(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return 0.0


def rule_matches(rule, game):
    target = str(game.get(rule["field"], "") or "")
    what = rule.get("what", "")
    if rule["op"] in NUMERIC:
        return NUMERIC[rule["op"]](number(target), number(what))
    if "rex" not in rule:
        rule["rex"] = None
        if SPECIAL.search(what):
            try:
                rule["rex"] = re.compile(what, re.I)
            except re.error:
                pass
    rex, low, w = rule["rex"], target.lower(), what.lower()
    op = rule["op"]
    if op == "equals":
        return not what if not target else (bool(rex.fullmatch(target)) if rex else low == w)
    if op == "not_equals":
        return bool(what) if not target else (not rex.fullmatch(target) if rex else low != w)
    if op == "contains":
        return bool(target) and (bool(rex.search(target)) if rex else w in low)
    if op == "not_contains":
        return not target or (not rex.search(target) if rex else w not in low)
    return True


def sort_key(value):
    """Como o Attract-Mode (e o painel) ordena: o vazio antes de tudo, os
    numeros pelo valor e o resto pelo texto."""
    s = "" if value is None else str(value)
    if not s:
        return (0, 0.0, "")
    try:
        return (1, float(s), "")
    except ValueError:
        return (2, 0.0, s.lower())


def apply_filter(games, flt):
    if not flt:
        return games
    out = []
    for g in games:
        keep = True
        for rule in flt.get("rules", []):
            if rule_matches(rule, g) == rule.get("exception", False):
                keep = rule.get("exception", False)
                break
        if keep:
            out.append(g)
    if flt.get("sort_by"):
        out.sort(key=lambda g: sort_key(g.get(flt["sort_by"])))
    if flt.get("reverse"):
        out.reverse()
    limit = flt.get("limit", 0)
    if limit > 0:
        out = out[:limit]
    elif limit < 0:
        out = out[limit:]
    return out


FAVOURITES = {"name": "Favourites", "rules": [{"field": "Favourite", "op": "equals", "what": "1"}],
              "sort_by": "", "reverse": False, "limit": 0}


# ── A biblioteca ───────────────────────────────────────────────────

class Library:
    """As pastas, os jogos e os filtros. reload() le de novo; changed() diz
    se alguma pasta mudou desde a ultima leitura."""

    def __init__(self):
        self.lock = threading.Lock()
        self.systems = parse_systems(cached("frontend-systems", lambda: setup("--systems")))
        self.filters = [FAVOURITES] + web.parse_filters(cached("frontend-filters", lambda: setup("--filters")))
        self.info = web.GameInfo()
        self.cache = {}            # chave -> lista de jogos
        self.stamps = self.folder_stamps()
        self.refreshing = False
        self.generation = 0        # muda a cada releitura (a tela refaz a lista)

    # As categorias: cada pasta e, antes delas, todas as de arcade juntas
    # (a tela "Arcade" do Attract-Mode).
    def categories(self):
        rows = []
        arcade = [s for s in self.systems if s["arcade"]]
        if len(arcade) > 1:
            rows.append({"key": "@arcade", "name": ARCADE_ALL, "arcade": True, "parts": arcade})
        rows.extend(self.systems)
        return rows

    def favourites(self):
        try:
            return web.favourite_set(self.systems)
        except OSError:
            return set()

    def games(self, category):
        """Os jogos da categoria, com o que a pessoa mudou e a pasta de cada um."""
        key = category["key"]
        with self.lock:
            if key in self.cache:
                return self.cache[key]
        favs = self.favourites()
        out = []
        for system in category.get("parts", [category]):
            try:
                rows = web.games(system, favs)
            except OSError:
                rows = []
            for g in rows:
                g["_system"] = system
                edits = self.edits(system, g["Name"])
                if edits:
                    g.update(edits)
                    g["Edited"] = "1"
                out.append(g)
        if "parts" in category:
            out.sort(key=lambda e: (e.get("Title") or e["Name"]).lower())
        with self.lock:
            self.cache[key] = out
        return out

    def forget(self, key=None):
        with self.lock:
            if key is None:
                self.cache.clear()
            else:
                self.cache.pop(key, None)
                self.cache.pop("@arcade", None)

    # ── O que a pessoa muda num jogo ──
    def edits_path(self, system, name):
        path = self.info.path(system["key"], name, "x")
        return path[:-len(".x.json")] + ".user.json" if path else None

    def edits(self, system, name):
        path = self.edits_path(system, name)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            return {k: str(v) for k, v in data.items() if k in EDIT_FIELDS and v not in (None, "")}
        except (OSError, ValueError, TypeError):
            return {}

    def save_edits(self, game, changes):
        system = game["_system"]
        path = self.edits_path(system, game["Name"])
        if not path:
            return False
        data = self.edits(system, game["Name"])
        data.update({k: v for k, v in changes.items() if k in EDIT_FIELDS})
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path + ".tmp", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(path + ".tmp", path)
        except OSError:
            return False
        game.update(data)
        game["Edited"] = "1"
        return True

    def values(self, category, field):
        """Os valores que o campo ja tem nas listas (para o Classify)."""
        seen = {}
        for g in self.games(category):
            v = g.get(field)
            if v:
                seen[v] = seen.get(v, 0) + 1
        return sorted(seen, key=lambda v: (-seen[v], v.lower()))[:200]

    # ── Favoritos e vezes jogadas ──
    def set_favourite(self, game, on):
        try:
            on = web.set_favourite(self.systems, game["_system"], game["Name"], on)
        except OSError:
            return game.get("Favourite") == "1"
        if on:
            game["Favourite"] = "1"
        else:
            game.pop("Favourite", None)
        return on

    def played(self, game, seconds):
        """Uma partida a mais no stats do Attract-Mode (os filtros Most Played)."""
        system = game["_system"]
        folder = os.path.join(web.attract_dir(), "stats", system["name"])
        path = os.path.join(folder, game["Name"] + ".stat")
        count, total = web.play_stats(system).get(game["Name"], (0, 0))
        count, total = count + 1, total + int(seconds)
        try:
            os.makedirs(folder, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write("%d\n%d\n" % (count, total))
        except OSError:
            return
        game["PlayedCount"], game["PlayedTime"] = count, total

    def command(self, game):
        return web.game_command(game["_system"], game["Name"])

    # ── Midia ──
    def media(self, game, kind):
        """O arquivo de midia do jogo (o do set; o clone sem o dele usa o do pai)."""
        system = game["_system"]
        base = os.path.join(web.player_home(), "media", kind, system["key"])
        for name in (game["Name"], game.get("CloneOf")):
            if not name:
                continue
            for ext in IMAGE_EXTS:
                path = os.path.join(base, name + ext)
                if os.path.isfile(path):
                    return path
        return None

    # ── Pastas que mudaram ──
    def folder_stamps(self):
        out = {}
        for s in self.systems:
            try:
                out[s["key"]] = os.stat(s["folder"]).st_mtime
            except OSError:
                out[s["key"]] = None
        return out

    def changed(self):
        """As chaves das pastas que mudaram (jogos postos ou tirados)."""
        now = self.folder_stamps()
        keys = [k for k, v in now.items() if self.stamps.get(k) != v]
        self.stamps = now
        return keys

    def refresh(self, done=None):
        """Em segundo plano: o Setup refaz as listas (as de arcade pelo XML do
        MAME) e confere as pastas e os filtros; depois o frontend relê."""
        if self.refreshing:
            return
        self.refreshing = True

        def work():
            try:
                setup("--romlists", timeout=900)
                systems = parse_systems(save_cache("frontend-systems", setup("--systems")))
                filters = web.parse_filters(save_cache("frontend-filters", setup("--filters")))
                with self.lock:
                    if systems:
                        self.systems = systems
                    if filters:
                        self.filters = [FAVOURITES] + filters
                    self.cache.clear()
                self.stamps = self.folder_stamps()
                self.generation += 1
            finally:
                self.refreshing = False
                if done:
                    done()

        threading.Thread(target=work, daemon=True).start()


# ── Clones ─────────────────────────────────────────────────────────

def tree(games):
    """A lista com os clones debaixo do pai: [(jogo, clones)]. Um clone cujo
    pai nao esta na lista fica sozinho."""
    by_name = {g["Name"]: g for g in games}
    children = {}
    for g in games:
        parent = g.get("CloneOf")
        if parent and parent in by_name and parent != g["Name"]:
            children.setdefault(parent, []).append(g)
    out = []
    for g in games:
        parent = g.get("CloneOf")
        if parent and parent in by_name and parent != g["Name"]:
            continue
        out.append((g, children.get(g["Name"], [])))
    return out


def variant(clone, parent):
    """O que muda no nome do clone em relacao ao pai: o que esta entre
    parenteses e o pai nao tem (a regiao, o set, bootleg)."""
    title = clone.get("Title") or clone["Name"]
    own = re.findall(r"\(([^()]*)\)", title)
    theirs = set(re.findall(r"\(([^()]*)\)", parent.get("Title") or ""))
    parts = [p for p in own if p not in theirs]
    if parts:
        return ", ".join(parts)
    short = title.split(" (")[0]
    return short if short != (parent.get("Title") or "").split(" (")[0] else clone["Name"]


def short_title(game):
    """O titulo sem os parenteses e sem o segundo nome ("A / B")."""
    title = game.get("Title") or game["Name"]
    return title.split(" (")[0].split(" / ")[0].strip() or title


def first_letter(game):
    c = short_title(game)[:1].upper()
    return c if "A" <= c <= "Z" else "#"


# ── Scrape de um jogo ──────────────────────────────────────────────

def download(url, path):
    import urllib.request
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FliperOS frontend"})
        with urllib.request.urlopen(req, timeout=20) as res:
            data = res.read(16 << 20)
        if len(data) < 64:
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "wb") as f:
            f.write(data)
        os.replace(path + ".tmp", path)
        return True
    except (OSError, ValueError):
        return False


def scrape(library, game, lang="en"):
    """As informacoes (salvas em ~/media/info) e as imagens do jogo em
    ~/media: do Arcade Database nos de arcade, do libretro-thumbnails nos de
    console. Devolve quantos arquivos novos vieram."""
    system = game["_system"]
    home = web.player_home()
    got = 0
    if system["arcade"]:
        path = library.info.path(system["key"], game["Name"], lang)
        if path and os.path.exists(path):
            os.remove(path)            # pedido de novo: busca de verdade
        library.info.cache.clear()
        info, _ = library.info.arcade(system["key"], game["Name"], lang)
        if not info:
            return 0
        for field, kind in (("url_image_ingame", "snap"), ("url_image_marquee", "marquee"),
                            ("url_image_flyer", "box")):
            url = info.get(field)
            if url:
                ext = os.path.splitext(url.split("?")[0])[1].lower() or ".png"
                target = os.path.join(home, "media", kind, system["key"], game["Name"] + ext)
                got += download(url, target)
        return got + 1
    for item in web.thumbnails(system, game):
        kind = {"boxart": "box", "snap": "snap"}.get(item["kind"])
        if kind:
            target = os.path.join(home, "media", kind, system["key"], game["Name"] + ".png")
            got += download(item["url"], target)
    return got
