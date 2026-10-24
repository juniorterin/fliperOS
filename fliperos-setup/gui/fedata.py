# Os dados do frontend do FliperOS (gui/fliperos-frontend): as pastas de
# jogos, os jogos de cada uma, os filtros, os favoritos, a midia e as
# informacoes salvas. Sao os mesmos do painel web: as funcoes vem dele
# (config/fliperos-web, importado como modulo), para os dois mostrarem a
# mesma coisa.
#
# - As pastas e o comando de cada uma: fliperos-setup --systems.
# Nada aqui depende do Attract-Mode Plus ou do ES-DE, que sao opcionais.
#
# - Os jogos: os arquivos de cada pasta e, nas de arcade, a lista do FliperOS
#   (~/.local/share/fliperos/lists, no formato das romlists do Attract-Mode)
#   com o nome, o ano, o fabricante, os clones e a categoria do XML do MAME
#   (fliperos-romclean romlist); um arquivo que a lista ainda nao tem aparece
#   pelo nome. Uma pasta que muda pede ao Setup que refaca as listas
#   (fliperos-setup --romlists) e o frontend as le de novo.
# - Os filtros: os do Setup (fliperos-setup --filters, no formato dos do
#   Attract-Mode), aplicados como ele aplica.
# - Os favoritos: ~/.config/fliperos/favourites. As vezes jogadas:
#   ~/.local/share/fliperos/stats (fliperos-web stats_folder).
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
VIDEO_EXTS = (".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv")
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
        folder = web.stats_folder(system)
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

    def rom_files(self, game):
        """Os arquivos do jogo na pasta: a ROM e, no MAME, a pasta dos CHDs
        de mesmo nome. A arte em ~/media fica."""
        system = game["_system"]
        folder = system["folder"]
        out = []
        if game.get("file"):
            out.append(os.path.join(folder, game["file"]))
        chd = os.path.join(folder, game["Name"])
        if system.get("arcade") and os.path.isdir(chd) and not os.path.islink(chd):
            out.append(chd)
        return [p for p in out if os.path.lexists(p)]

    def delete(self, game):
        """Apaga o jogo da pasta (rom_files). Devolve quantos itens sairam;
        a lista e lida de novo (a pasta mudou: o frontend pede ao Setup as
        romlists novas, como com um jogo copiado)."""
        import shutil
        n = 0
        for path in self.rom_files(game):
            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                n += 1
            except OSError:
                pass
        if n:
            self.forget()
        return n

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

    def video(self, game):
        """O video do jogo (~/media/preview), o do set ou o do pai."""
        system = game["_system"]
        base = os.path.join(web.player_home(), "media", "preview", system["key"])
        for name in (game["Name"], game.get("CloneOf")):
            if not name:
                continue
            for ext in VIDEO_EXTS:
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


# ── Os pacotes de arte do archive.org ──────────────────────────────
# Os mesmos do Setup > Games > Scraper > Art packs by torrent
# (config/fliperos-media-torrents): o logo e o video que o Arcade Database
# nao tem para o jogo saem dali, um arquivo so, pelo HTTP do archive.org,
# sem baixar o pacote. A lista de arquivos de cada pacote (e a de dentro
# de cada .zip de letra) fica guardada em ~/.cache/fliperos/archive.
PACKS_FILE = os.environ.get("FLIPEROS_MEDIA_TORRENTS", "/usr/local/share/fliperos/media-torrents")
ARCHIVE = os.environ.get("FLIPEROS_ARCHIVE_URL", "https://archive.org")
PACK_EXTS = {"logo": (".png", ".jpg"), "preview": VIDEO_EXTS}
LISTING_DAYS = 30


def art_packs(system, kind):
    """Os pacotes (id) do tipo de arte para a pasta do jogo."""
    out = []
    try:
        with open(PACKS_FILE, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return out
    key = system["key"]
    for line in lines:
        parts = line.split("\t")
        if len(parts) < 4 or line.startswith("#") or parts[1] != kind:
            continue
        folders = parts[2].split(",")
        if (key in folders or ("@arcade" in folders and system.get("arcade"))
                or ("@arcade-cores" in folders and system.get("arcade") and key.startswith("retroarch/"))):
            m = re.search(r"/download/([^/]+)/", parts[3])
            if m:
                out.append(m.group(1))
    return out


def fetch_text(url, cache_name):
    """O texto do endereco, guardado LISTING_DAYS dias."""
    import urllib.request
    path = os.path.join(web.player_home(), ".cache", "fliperos", "archive", cache_name)
    try:
        if time.time() - os.path.getmtime(path) < LISTING_DAYS * 86400:
            with open(path, encoding="utf-8") as f:
                return f.read()
    except OSError:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "FliperOS frontend"})
        with urllib.request.urlopen(req, timeout=30) as res:
            text = res.read(32 << 20).decode("utf-8", "replace")
    except (OSError, ValueError):
        return None
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(path + ".tmp", path)
    except OSError:
        pass
    return text


def pack_file(item, names, exts):
    """O endereco do arquivo do jogo (um dos nomes) no pacote: solto, ou
    dentro do .zip da letra dele (o archive.org serve um arquivo de dentro
    do zip). None: o pacote nao tem."""
    from urllib.parse import quote, unquote
    text = fetch_text("%s/metadata/%s/files" % (ARCHIVE, item), item + ".json")
    try:
        files = [f["name"] for f in json.loads(text or "{}").get("result", [])]
    except (ValueError, AttributeError, TypeError):
        return None
    loose = {}
    for name in files:
        stem, ext = os.path.splitext(os.path.basename(name))
        if ext.lower() in exts and not stem.endswith(".ia"):
            loose.setdefault(stem.lower(), name)
    zips = {os.path.splitext(n)[0].upper(): n for n in files if n.lower().endswith(".zip") and "/" not in n}
    for game in names:
        if game.lower() in loose:
            return "%s/download/%s/%s" % (ARCHIVE, item, quote(loose[game.lower()]))
    for game in names:
        letter = game[:1].upper()
        zname = zips.get(letter) or (zips.get("#") if not letter.isalpha() else None)
        if not zname:
            continue
        listing = fetch_text("%s/download/%s/%s/" % (ARCHIVE, item, quote(zname)),
                             "%s-%s.html" % (item, re.sub(r"[^A-Za-z0-9]", "_", zname)))
        for href in re.findall(r'href="([^"]+)"', listing or ""):
            inner = href.rsplit("/", 1)[-1]
            stem, ext = os.path.splitext(unquote(inner).rsplit("/", 1)[-1])
            if stem.lower() == game.lower() and ext.lower() in exts:
                return "%s/download/%s/%s/%s" % (ARCHIVE, item, quote(zname), inner)
    return None


def pack_art(library, game, kinds):
    """O logo e o video do jogo dos pacotes do archive.org. Devolve
    quantos arquivos vieram."""
    system = game["_system"]
    names = [n for n in (game["Name"], game.get("CloneOf")) if n]
    got = 0
    for kind in kinds:
        exts = PACK_EXTS.get(kind)
        if not exts:
            continue
        for item in art_packs(system, kind):
            url = pack_file(item, names, exts)
            if not url:
                continue
            ext = os.path.splitext(url)[1].lower()
            target = os.path.join(web.player_home(), "media", kind, system["key"], game["Name"] + ext)
            if download(url, target):
                got += 1
                break
    return got


def missing_art(library, game):
    """As midias que o jogo ainda nao tem (das que o scrape traz)."""
    out = [kind for kind in ("snap", "box", "marquee", "logo") if not library.media(game, kind)]
    if not library.video(game):
        out.append("preview")
    return out


def scrape(library, game, lang="en", only_missing=False):
    """As informacoes (salvas em ~/media/info), as imagens e o video do jogo
    em ~/media: do Arcade Database nos de arcade (a tela, o marquee, o flyer e
    o video curto), do libretro-thumbnails nos de console. Devolve quantos
    arquivos novos vieram. only_missing: so o que falta (o scrape sozinho do
    frontend nao baixa de novo o que ja esta la)."""
    system = game["_system"]
    home = web.player_home()
    got = 0
    want = set(missing_art(library, game)) if only_missing else None
    if system["arcade"]:
        path = library.info.path(system["key"], game["Name"], lang)
        if path and os.path.exists(path):
            os.remove(path)            # pedido de novo: busca de verdade
        library.info.cache.clear()
        info, _ = library.info.arcade(system["key"], game["Name"], lang)
        for field, kind in (("url_image_ingame", "snap"), ("url_image_marquee", "marquee"),
                            ("url_image_flyer", "box"), ("url_video_shortplay", "preview")):
            url = (info or {}).get(field)
            if url and (want is None or kind in want):
                ext = os.path.splitext(url.split("?")[0])[1].lower() or (".mp4" if kind == "preview" else ".png")
                target = os.path.join(home, "media", kind, system["key"], game["Name"] + ext)
                got += download(url, target)
        # O logo: o "decal" do Arcade Database (fora da API, o mesmo que o
        # Skyscraper busca), o do set ou o do pai.
        if info and (want is None or "logo" in want):
            target = os.path.join(home, "media", "logo", system["key"], game["Name"] + ".png")
            for name in (game["Name"], game.get("CloneOf")):
                if name and download("%s/media/mame.current/decals/%s.png" % (web.ADB_ORIGIN, name), target):
                    got += 1
                    break
        got += 1 if info else 0
    else:
        for item in web.thumbnails(system, game):
            kind = {"boxart": "box", "snap": "snap"}.get(item["kind"])
            if kind and (want is None or kind in want):
                target = os.path.join(home, "media", kind, system["key"], game["Name"] + ".png")
                got += download(item["url"], target)
    # O logo (e o video que o Arcade Database nao tinha) dos pacotes.
    missing = missing_art(library, game)
    got += pack_art(library, game, [k for k in ("logo", "preview") if k in missing])
    return got
