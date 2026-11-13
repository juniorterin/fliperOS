"""O selo de conquistas do frontend: um trofeu e quantas conquistas do
RetroAchievements o jogador ja tem e quantas o jogo tem (3/24), so nos jogos
que tem conquistas e so onde o emulador daquele jogo as da.

O site reconhece o jogo pelo hash da ROM, como os emuladores (o rcheevos,
src/rhash): no arcade (FBNeo, MAME 2003-Plus), o MD5 do nome do arquivo sem a
extensao (com a pasta de console do FBNeo na frente, "nes_smb"); nos cartuchos,
o MD5 do arquivo (dentro do .zip, o primeiro arquivo), sem o cabecalho do NES,
do SNES, do PC Engine, do Lynx e do 7800, e o N64 em big-endian. Os discos
(PlayStation, PS2, GameCube, Dreamcast...) tem um hash proprio para cada
console: so com o RAHasher instalado (RAHASHER).

Os dados vem da Web API do site (retroachievements.org/API), com a chave da
conta (Web API Key, em retroachievements.org/settings), que o menu
RetroAchievements do Setup e o painel web guardam em /etc/fliperos/cheevos
(apikey=):

  API_GetGameList.php?i=CONSOLE&f=1&h=1     os jogos com conquistas e os hashes
                                            de cada um (uma vez por semana)
  API_GetUserCompletionProgress.php?u=...   quantas o jogador tem em cada jogo
                                            (ao abrir o frontend)
  API_GetGameInfoAndUserProgress.php?g=...  um jogo so, depois de jogar

Tudo fica em ~/.cache/fliperos/cheevos e e buscado numa thread: o frontend
nunca espera, o selo aparece quando a resposta chega."""
import hashlib
import json
import os
import queue
import re
import subprocess
import threading
import time
import urllib.parse
import urllib.request
import zipfile

CONF = os.environ.get("FLIPEROS_CHEEVOS", "/etc/fliperos/cheevos")
API = os.environ.get("FLIPEROS_RA_API", "https://retroachievements.org/API/")
RAHASHER = os.environ.get("FLIPEROS_RAHASHER", "/usr/local/bin/RAHasher")
USER_AGENT = "FliperOS/1.0 (frontend achievements badge)"
LIST_DAYS = 7               # a lista de jogos de um console vale uma semana
PROGRESS_MINUTES = 10       # o progresso do jogador, dez minutos
MAX_BUFFER = 64 * 1024 * 1024   # o rcheevos so le ate aqui (MAX_BUFFER_SIZE)

# As plataformas das pastas (as do Skyscraper, lib/scraper.sh) -> o console no
# RetroAchievements (rc_consoles.h). As de disco so com o RAHasher.
CONSOLES = {
    "arcade": 27, "fba": 27, "neogeo": 27,
    "nes": 7, "fds": 81, "snes": 3, "n64": 2, "gb": 4, "gbc": 6, "gba": 5, "virtualboy": 28, "pokemini": 24,
    "megadrive": 1, "genesis": 1, "mastersystem": 11, "gamegear": 15, "sg-1000": 33, "sega32x": 10,
    "pcengine": 8, "atari2600": 25, "atari7800": 51, "atarilynx": 13, "atarijaguar": 17,
    "ngp": 14, "ngpc": 14, "wonderswan": 53, "wonderswancolor": 53, "coleco": 44, "intellivision": 45,
    "vectrex": 46, "videopac": 23, "channelf": 57, "msx": 29,
}
DISC_CONSOLES = {"psx": 12, "ps2": 21, "gc": 16, "dreamcast": 40, "segacd": 9, "saturn": 39, "pcenginecd": 76,
                 "neogeocd": 56, "psp": 41, "3do": 43, "atarijaguarcd": 77, "nds": 18}
# A extensao muda o console nos cores de varios (Genesis Plus GX, Gambatte...).
BY_EXTENSION = {".gbc": 6, ".cgb": 6, ".sms": 11, ".gg": 15, ".sg": 33, ".32x": 10, ".fds": 81}
# Os cores de arcade que tem conquistas (o FBNeo e o MAME 2003-Plus); os
# outros MAME do RetroArch e o GroovyMAME nao.
ARCADE_CORES = ("fbneo", "fbalpha2012", "mame2003_plus")
# Os emuladores de fora do RetroArch que tem conquistas (pelos discos).
STANDALONE = {"duckstation": 12, "pcsx2": 21, "dolphin-emu": 16, "flycast": 40}
# As pastas de console do FBNeo que entram no hash (rc_hash_arcade).
FBNEO_FOLDERS = ("nes", "fds", "sms", "msx", "ngp", "pce", "chf", "sgx", "tg16", "msx1", "neocd", "coleco",
                 "sg1000", "genesis", "gamegear", "megadriv", "pcengine", "channelf", "spectrum", "megadrive",
                 "supergrafx", "zxspectrum", "mastersystem", "colecovision")


def read_conf(path=None):
    out = {}
    try:
        with open(path or CONF, encoding="utf-8") as f:
            for line in f:
                key, sep, value = line.rstrip("\n").partition("=")
                if sep:
                    out[key] = value
    except OSError:
        pass
    return out


def core_of(system):
    """O core do RetroArch da pasta (o -L dos argumentos), sem _libretro.so."""
    m = re.search(r"(?:^|\s)(?:-L|--libretro)\s+(\S+)", system.get("args", ""))
    if not m:
        return ""
    return os.path.basename(m.group(1)).replace("_libretro.so", "").replace(".so", "")


def console_of(system, filename, rahasher=None):
    """O console do RetroAchievements de um jogo, ou None se ali nao ha
    conquista (o emulador nao da, ou o hash dele precisa do RAHasher)."""
    platform = system.get("platform", "")
    exe = os.path.basename(system.get("exe", ""))
    ext = os.path.splitext(filename)[1].lower()
    rahasher = os.path.exists(RAHASHER) if rahasher is None else rahasher
    if exe == "retroarch":
        core = core_of(system)
        if platform in ("arcade", "fba", "neogeo"):
            return 27 if core in ARCADE_CORES else None
        if platform in CONSOLES:
            return BY_EXTENSION.get(ext, CONSOLES[platform])
        if platform in DISC_CONSOLES and rahasher:
            return DISC_CONSOLES[platform]
        return None
    if exe in STANDALONE and rahasher and system.get("key") not in ("naomi", "naomi2", "atomiswave", "namco2x6"):
        return STANDALONE[exe]
    return None


def _strip(console, data):
    """O que o rcheevos tira do comeco da ROM antes do MD5."""
    if console in (7, 81) and data[:4] in (b"NES\x1a", b"FDS\x1a"):
        return data[16:]
    if console == 3 and len(data) % 0x2000 == 512:
        return data[512:]
    if console == 8 and len(data) & 512:
        return data[512:]
    if console == 13 and data[:5] == b"LYNX\0":
        return data[64:]
    if console == 51 and data[1:10] == b"ATARI7800":
        return data[128:]
    if console == 2:
        if data[:1] == b"\x37":           # v64: os bytes trocados de 2 em 2
            swapped = bytearray(data)
            swapped[0::2], swapped[1::2] = data[1::2], data[0::2]
            return bytes(swapped)
        if data[:1] == b"\x40":           # n64: little-endian de 4 em 4
            swapped = bytearray(len(data))
            for i in range(4):
                swapped[i::4] = data[3 - i::4][:len(swapped[i::4])]
            return bytes(swapped)
    return data


def rom_hash(console, path):
    """O hash do RetroAchievements do arquivo (None se nao da)."""
    if console == 27:
        folder = os.path.basename(os.path.dirname(path)).lower()
        name = os.path.splitext(os.path.basename(path))[0]
        if folder in FBNEO_FOLDERS:
            name = folder + "_" + name
        return hashlib.md5(name.encode("utf-8")).hexdigest()
    if console in DISC_CONSOLES.values():
        try:
            out = subprocess.run([RAHASHER, str(console), path], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return None
        m = re.search(r"\b([0-9a-f]{32})\b", out.stdout)
        return m.group(1) if out.returncode == 0 and m else None
    try:
        if path.lower().endswith(".zip"):
            with zipfile.ZipFile(path) as z:
                names = [i for i in z.infolist() if not i.is_dir()]
                if not names:
                    return None
                with z.open(names[0]) as f:
                    data = f.read(MAX_BUFFER + 1024)
        else:
            with open(path, "rb") as f:
                data = f.read(MAX_BUFFER + 1024)
    except (OSError, zipfile.BadZipFile, RuntimeError):
        return None
    return hashlib.md5(_strip(console, data)[:MAX_BUFFER]).hexdigest()


class Cheevos:
    """Os dados do selo. lookup() responde na hora com o que ja se sabe e pede
    o resto a thread; refresh_game() depois de uma partida."""

    def __init__(self, cache_dir, conf=None, fetch=None, rahasher=None):
        self.cache_dir = cache_dir
        self.conf_path = conf or CONF
        self.fetch = fetch or self.http_json
        self.rahasher = rahasher
        self.lock = threading.Lock()
        self.tasks = queue.Queue()
        self.pending = set()
        self.hashes = self.load("hashes.json")          # caminho -> [tamanho, mtime, hash]
        self.lists = {}                                  # console -> {hash: [id, total]}
        self.progress = self.load("progress.json")      # {"time", "games": {id: [n, hardcore, total]}}
        self.thread = None
        self.reload_conf()

    # ── A conta ──
    def reload_conf(self):
        conf = read_conf(self.conf_path)
        self.user, self.key = conf.get("user", ""), conf.get("apikey", "")
        self.hardcore = conf.get("hardcore") == "1"
        self.on = bool(self.user and self.key and conf.get("enabled") == "1")

    # ── O cache ──
    def path(self, name):
        return os.path.join(self.cache_dir, name)

    def load(self, name):
        try:
            with open(self.path(name), encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, name, data):
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            tmp = self.path(name) + ".%d.tmp" % os.getpid()
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, self.path(name))
        except OSError:
            pass

    # ── O que o frontend pergunta ──
    def lookup(self, game):
        """(tem, total) do jogo, ou None: sem conquistas, sem conta, ou ainda
        buscando (a thread busca e a proxima chamada ja sabe)."""
        if not self.on:
            return None
        system = game.get("_system") or {}
        filename = game.get("file") or ""
        console = console_of(system, filename, self.rahasher)
        if console is None or not filename:
            return None
        path = os.path.join(system.get("folder", ""), filename)
        with self.lock:
            games = self.lists.get(console)
            known = self.hashes.get(path)
        if games is None:
            games = self.console_list(console)
            if games is None:
                return None
        try:
            st = os.stat(path)
        except OSError:
            return None
        if not known or known[:2] != [st.st_size, int(st.st_mtime)]:
            self.ask(("hash", console, path))
            return None
        found = games.get(known[2])
        if not found:
            return None
        game_id, total = found
        done = self.progress.get("games", {}).get(str(game_id))
        if self.progress_stale():
            self.ask(("progress",))
        have = (done[1] if self.hardcore else done[0]) if done else 0
        return have, total

    def refresh_game(self, game):
        """Depois de uma partida: o progresso daquele jogo de novo."""
        system = game.get("_system") or {}
        console = console_of(system, game.get("file") or "", self.rahasher)
        path = os.path.join(system.get("folder", ""), game.get("file") or "")
        with self.lock:
            known = self.hashes.get(path)
            games = self.lists.get(console) or {}
        found = games.get(known[2]) if known else None
        if self.on and found:
            self.ask(("game", found[0]))

    # ── A fila ──
    def ask(self, task):
        with self.lock:
            if task in self.pending:
                return
            self.pending.add(task)
        self.tasks.put(task)
        if self.thread is None:
            self.thread = threading.Thread(target=self.worker, daemon=True)
            self.thread.start()

    def worker(self):
        while True:
            task = self.tasks.get()
            try:
                self.run(task)
            except Exception:      # um erro de rede ou de arquivo nao derruba o frontend
                pass
            with self.lock:
                self.pending.discard(task)

    def run(self, task):
        kind = task[0]
        if kind == "hash":
            _, console, path = task
            digest = rom_hash(console, path)
            try:
                st = os.stat(path)
            except OSError:
                return
            with self.lock:
                self.hashes[path] = [st.st_size, int(st.st_mtime), digest or ""]
                data = dict(self.hashes)
            self.save("hashes.json", data)
        elif kind == "list":
            self.fetch_list(task[1])
        elif kind == "progress":
            self.fetch_progress()
        elif kind == "game":
            self.fetch_game(task[1])

    # ── O site ──
    def http_json(self, endpoint, **params):
        params["y"] = self.key
        url = API + endpoint + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))

    def console_list(self, console):
        """A lista do console do cache (pedindo a do site se e velha); None
        enquanto nao ha nenhuma."""
        name = "console-%d.json" % console
        data = self.load(name)
        if not data or time.time() - data.get("time", 0) > LIST_DAYS * 86400:
            self.ask(("list", console))
        if not data:
            return None
        games = {h: v for h, v in data.get("games", {}).items()}
        with self.lock:
            self.lists[console] = games
        return games

    def fetch_list(self, console):
        rows = self.fetch("API_GetGameList.php", i=console, f=1, h=1)
        games = {}
        for row in rows if isinstance(rows, list) else []:
            if row.get("NumAchievements"):
                for h in row.get("Hashes") or []:
                    games[str(h).lower()] = [int(row["ID"]), int(row["NumAchievements"])]
        with self.lock:
            self.lists[console] = games
        self.save("console-%d.json" % console, {"time": time.time(), "games": games})

    def progress_stale(self):
        return time.time() - self.progress.get("time", 0) > PROGRESS_MINUTES * 60

    def fetch_progress(self):
        games, offset = {}, 0
        while True:
            page = self.fetch("API_GetUserCompletionProgress.php", u=self.user, c=500, o=offset)
            rows = (page.get("Results") or []) if isinstance(page, dict) else []
            for row in rows:
                games[str(row.get("GameID"))] = [int(row.get("NumAwarded") or 0),
                                                int(row.get("NumAwardedHardcore") or 0),
                                                int(row.get("MaxPossible") or 0)]
            offset += len(rows)
            if not rows or offset >= int(page.get("Total") or 0):
                break
        with self.lock:
            self.progress = {"time": time.time(), "games": games}
            data = dict(self.progress)
        self.save("progress.json", data)

    def fetch_game(self, game_id):
        row = self.fetch("API_GetGameInfoAndUserProgress.php", u=self.user, g=game_id)
        if not isinstance(row, dict):
            return
        with self.lock:
            games = dict(self.progress.get("games", {}))
            games[str(game_id)] = [int(row.get("NumAwardedToUser") or 0), int(row.get("NumAwardedToUserHardcore") or 0),
                                   int(row.get("NumAchievements") or 0)]
            self.progress = {"time": self.progress.get("time", 0), "games": games}
            data = dict(self.progress)
        self.save("progress.json", data)
