#!/usr/bin/env python3
"""Capturas do painel web num Chromium sem tela, no tamanho de um celular e
de um PC: para conferir o desenho sem o gabinete, ou com ele.

    python3 tools/web-shots.py --demo OUT        o painel deste repositorio com
                                                 dados de exemplo (pastas, jogos,
                                                 arte gerada, um jogo aberto)
    python3 tools/web-shots.py http://IP:8081 OUT --password SENHA

Roda na imagem do tools/video/Dockerfile.web (Chromium e python3-websocket):

    docker run --rm -v "$PWD:/w" -w /w fliperos-video-web python3 tools/web-shots.py --demo /w/.shots/web

Cada captura vira OUT/<nome>.png; um erro no console da pagina faz o script
sair com 1 (e e listado)."""
import argparse
import base64
import ctypes
import ctypes.util
import json
import os
import random
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# As telas: (nome, endereco, largura, altura, escala, celular?, pagina inteira?, acao)
SHOTS = [
    ("login-celular", "", 390, 844, 2, True, False, "logout"),
    ("frontend-pc", "#frontend", 1440, 900, 1, False, False, ""),
    ("frontend-pc-inteiro", "#frontend", 1440, 900, 1, False, True, ""),
    ("frontend-celular", "#frontend", 390, 844, 2, True, False, ""),
    ("frontend-celular-inteiro", "#frontend", 390, 844, 2, True, True, ""),
    ("jogo-pc", "#frontend", 1440, 900, 1, False, False, "sheet"),
    ("jogo-celular", "#frontend", 390, 844, 2, True, False, "sheet"),
    ("lista-celular", "#frontend", 390, 844, 2, True, False, "list"),
    ("tarefas-pc", "#library", 1440, 900, 1, False, False, "tasks"),
    ("biblioteca-celular", "#library", 390, 844, 2, True, False, ""),
    ("downloads-pc", "#library/downloads", 1440, 900, 1, False, False, ""),
    ("status-pc", "#system", 1440, 900, 1, False, False, ""),
    ("ajustes-celular", "#system/settings", 390, 844, 2, True, False, ""),
    ("aovivo-pc", "#live/obs", 1440, 900, 1, False, False, ""),
]


# ── A arte de exemplo: cenas de pixel geradas (nada de jogo de verdade) ──
def png(width, height, pixels):
    rows = b"".join(b"\0" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(rows, 9)) + chunk(b"IEND", b""))


def hexrgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def scene(kind, seed, width=160, height=120):
    rnd = random.Random(seed)
    buf = bytearray(width * height * 3)

    def rect(x, y, w, h, color):
        c = hexrgb(color) if isinstance(color, str) else color
        for yy in range(max(0, int(y)), min(height, int(y + h))):
            for xx in range(max(0, int(x)), min(width, int(x + w))):
                i = (yy * width + xx) * 3
                buf[i:i + 3] = bytes(c)

    pal = rnd.choice([("#1b1440", "#3a2a7a", "#ff7a59", "#ffd166"), ("#08263a", "#11557a", "#7bdff2", "#f7d6e0"),
                      ("#2d0b1e", "#7a1f3d", "#ffb347", "#fff275"), ("#0b2a12", "#1f6b35", "#9cff57", "#e6ff99"),
                      ("#0f1b3d", "#2f4b9a", "#ff6ad5", "#c774e8")])
    if kind == "fighter":
        sky = ["#ff9a5a", "#ff7a4a", "#e85a4a", "#b8405a", "#7a3060", "#4a2a5a", "#2a2050", "#1a1440", "#140f35", "#100c2a",
               "#0c0a22", "#0c0a22"]
        for i, c in enumerate(sky):
            rect(0, i * 6, width, 6, c)
        for i in range(12):
            bh = 14 + rnd.random() * 30
            rect(i * 14, 70 - bh, 8 + rnd.random() * 14, bh, "#1a1230")
            rect(i * 14 + 3, 74 - bh, 2, 2, "#ffd166")
        for y in range(70, height, 5):
            rect(0, y, width, 5, "#6b4a3a" if y % 10 else "#5a3a2e")
        for x, c1, c2 in ((44, "#f4f4f4", "#e83030"), (100, rnd.choice(["#2f6bff", "#2fbf6b", "#bf2fbf"]), "#ffd400")):
            rect(x + 4, 58, 8, 8, "#f2c49b"); rect(x + 3, 56, 10, 3, c2); rect(x + 2, 66, 12, 16, c1)
            rect(x + 2, 82, 5, 18, c1); rect(x + 9, 82, 5, 18, c1); rect(x + 2, 78, 12, 3, c2)
        rect(6, 6, 64, 6, "#2a0a0a"); rect(7, 7, 50, 4, "#ffd400"); rect(90, 6, 64, 6, "#2a0a0a"); rect(91, 7, 38, 4, "#ffd400")
    elif kind == "shooter":
        rect(0, 0, width, height // 2, pal[0]); rect(0, height // 2, width, height // 2, pal[1])
        for _ in range(40):
            rect(rnd.random() * width, rnd.random() * height, 1, 1, pal[3] if rnd.random() > .7 else "#cccccc")
        for i in range(6):
            x, y = 10 + i * 24, 20 + (i % 2) * 10
            rect(x, y, 12, 6, pal[2]); rect(x + 3, y + 6, 6, 3, pal[3])
        rect(74, 96, 12, 10, "#d8d8d8"); rect(78, 90, 4, 6, "#ffffff"); rect(70, 102, 20, 4, "#7a7aff")
        for i in range(5):
            rect(79, 80 - i * 12, 2, 6, "#fff275")
    elif kind == "platform":
        rect(0, 0, width, height, "#5c94fc")
        for _ in range(3):
            x, y = rnd.random() * width, 10 + rnd.random() * 30
            rect(x, y, 22, 6, "#ffffff"); rect(x + 4, y - 4, 12, 4, "#ffffff")
        for i in range(4):
            h = 20 + rnd.random() * 20
            rect(i * 46, 96 - h, 40, h, "#3aa83a")
        for x in range(0, width, 10):
            rect(x, 96, 10, 24, "#c84c0c"); rect(x, 96, 10, 3, "#fcbcb0")
        rect(60, 60, 30, 8, "#c84c0c"); rect(70, 48, 10, 10, "#fc9838"); rect(40, 78, 10, 18, "#e40058")
    elif kind == "racing":
        rect(0, 0, width, 60, "#ff9a5a"); rect(0, 30, width, 30, "#ffcf7a")
        for i in range(8):
            rect(i * 22, 40 - rnd.random() * 14, 26, 40, "#6a4a8a")
        rect(0, 60, width, 60, "#3aa83a")
        for y in range(60, height, 2):
            t = (y - 60) / 60
            w = 20 + t * 140
            rect(80 - w / 2, y, w, 2, "#5a5a6a" if (y // 2) % 4 < 2 else "#64647a")
            rect(80 - w / 2, y, 3 + t * 6, 2, "#ffffff" if (y // 4) % 2 else "#ee0000")
            rect(80 + w / 2 - 3 - t * 6, y, 3 + t * 6, 2, "#ffffff" if (y // 4) % 2 else "#ee0000")
        rect(64, 96, 32, 14, "#e00000"); rect(68, 90, 24, 8, "#ff4040"); rect(72, 92, 16, 4, "#2a2a4a")
    else:
        rect(0, 0, width, height, pal[0])
        rect(40, 6, 80, 108, "#000000")
        colors = [pal[2], pal[3], "#50fa7b", "#8be9fd", "#ff79c6"]
        for y in range(13):
            for x in range(9):
                if y > 4 + (x % 3) or rnd.random() > .8:
                    rect(42 + x * 8.6, 8 + y * 8, 8, 7, rnd.choice(colors))
    return png(width, height, buf)


def marquee_art(title_seed, width=320, height=80):
    rnd = random.Random(title_seed)
    buf = bytearray(width * height * 3)
    base = hexrgb(rnd.choice(["#a8152a", "#152aa8", "#0f6b3a", "#6a1fa8"]))
    for y in range(height):
        k = 0.45 + 0.55 * (1 - abs(y - height / 2) / (height / 2))
        for x in range(width):
            i = (y * width + x) * 3
            buf[i:i + 3] = bytes(min(255, int(c * k + (40 if (x // 8 + y // 8) % 2 else 0))) for c in base)
    for i in range(10):
        x0 = 24 + i * 28
        for y in range(24, 56):
            for x in range(x0, x0 + 20):
                if (x - x0) in (0, 1, 18, 19) or y in (24, 25, 54, 55) or (i % 3 == 0 and y in (39, 40)):
                    j = (y * width + x) * 3
                    buf[j:j + 3] = bytes((255, 214, 80))
    return png(width, height, buf)


GAMES = [("sf2", "Street Fighter II: The World Warrior", "1991", "Capcom", "Fighter / Versus", "2", "6", "joystick (8-way)", "fighter"),
         ("mslug", "Metal Slug - Super Vehicle-001", "1996", "Nazca", "Shooter / Run and Gun", "2", "3", "joystick (8-way)", "shooter"),
         ("kof98", "The King of Fighters '98", "1998", "SNK", "Fighter / Versus", "2", "4", "joystick (8-way)", "fighter"),
         ("daytona", "Daytona USA", "1994", "Sega", "Driving / Race", "1", "4", "paddle", "racing"),
         ("pbobble", "Puzzle Bobble", "1994", "Taito", "Puzzle / Match", "2", "1", "joystick (2-way)", "puzzle"),
         ("ffight", "Final Fight", "1989", "Capcom", "Fighter / Scrolling", "2", "2", "joystick (8-way)", "fighter"),
         ("aerofgt", "Aero Fighters", "1992", "Video System", "Shooter / Flying Vertical", "2", "2", "joystick (8-way)", "shooter"),
         ("outrun", "Out Run", "1986", "Sega", "Driving / Race", "1", "2", "paddle", "racing"),
         ("bublbobl", "Bubble Bobble", "1986", "Taito", "Platform / Run Jump", "2", "2", "joystick (2-way)", "platform"),
         ("captcomm", "Captain Commando", "1991", "Capcom", "Fighter / Scrolling", "4", "2", "joystick (8-way)", "fighter"),
         ("1942", "1942", "1984", "Capcom", "Shooter / Flying Vertical", "2", "2", "joystick (8-way)", "shooter"),
         ("samsho2", "Samurai Shodown II", "1994", "SNK", "Fighter / Versus", "2", "4", "joystick (8-way)", "fighter"),
         ("columns", "Columns", "1990", "Sega", "Puzzle / Drop", "2", "1", "joystick (4-way)", "puzzle"),
         ("raiden2", "Raiden II", "1993", "Seibu Kaihatsu", "Shooter / Flying Vertical", "2", "2", "joystick (8-way)", "shooter"),
         ("dino", "Cadillacs and Dinosaurs", "1993", "Capcom", "Fighter / Scrolling", "3", "2", "joystick (8-way)", ""),
         ("nbbatman", "Ninja Baseball Bat Man", "1993", "Irem", "Fighter / Scrolling", "4", "2", "joystick (8-way)", ""),
         ("mvsc2", "Marvel vs. Capcom 2", "2000", "Capcom", "Fighter / Versus", "2", "6", "joystick (8-way)", "fighter"),
         ("pang", "Pang!", "1989", "Mitchell", "Platform / Shooter", "2", "1", "joystick (8-way)", "platform")]
SYSTEMS = [("mame", "MAME", "groovymame", 1), ("naomi", "Naomi", "flycast", 1), ("snes", "Super Nintendo", "retroarch", 0),
           ("megadrive", "Mega Drive", "retroarch", 0)]


def demo(tmp):
    """O HOME, as ferramentas e o servidor de exemplo; devolve o endereco."""
    home = os.path.join(tmp, "home")
    lib = ctypes.CDLL(ctypes.util.find_library("crypt") or "libcrypt.so.1")
    lib.crypt.restype = ctypes.c_char_p
    lib.crypt.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    write(os.path.join(tmp, "shadow"), "fliperos:%s:19000:0:99999:7:::\n" % lib.crypt(b"fliperos", b"$6$demo$").decode())
    lines = []
    for key, name, exe, arcade in SYSTEMS:
        folder = os.path.join(home, "roms", key)
        os.makedirs(folder, exist_ok=True)
        lines.append("%s|%s|%s|%s|/opt/fliperos/bin/fliperos-kms-run|%s [name]|.zip|%d" % (key, folder, key, name, exe, arcade))
        games = GAMES if key == "mame" else GAMES[:6] if key == "naomi" else [(g[0] + key, g[1].split(":")[0] + " (" + name + ")") + g[2:]
                                                                             for g in GAMES[2:9]]
        rows = ["#Name;Title;Emulator;CloneOf;Year;Manufacturer;Category;Players;Rotation;Control;Status;DisplayCount;"
                "DisplayType;AltRomname;AltTitle;Extra;Buttons;Series;Language;Region;Rating"]
        for n, (rom, title, year, maker, cat, players, buttons, control, kind) in enumerate(games):
            write(os.path.join(folder, rom + ".zip"), "")
            rows.append("%s;%s;%s;;%s;%s;%s;%s;0;%s;good;1;raster;;;;%s;;;;" % (rom, title, name, year, maker, cat, players,
                                                                                control, buttons))
            if kind:
                write(os.path.join(home, "media", "snap", key, rom + ".png"), scene(kind, n * 7 + len(key)), "wb")
        write(os.path.join(home, ".local/share/fliperos/lists", name + ".txt"), "\n".join(rows) + "\n")
    write(os.path.join(home, "media", "marquee", "mame", "sf2.png"), marquee_art(3), "wb")
    write(os.path.join(home, ".config/fliperos/favourites"), "mame\tsf2\nmame\tmslug\nmame\tkof98\nmame\tmvsc2\nmame\toutrun\n")
    for rom, count, secs in (("sf2", 23, 15120), ("mslug", 9, 5400), ("kof98", 14, 9000), ("ffight", 4, 2400)):
        write(os.path.join(home, ".local/share/fliperos/stats/MAME", rom + ".stat"), "%d\n%d\n" % (count, secs))
    setup = os.path.join(tmp, "fliperos-setup")
    write(setup, "#!/bin/sh\ncase \"$1\" in\n  --systems) cat %s/systems ;;\n"
          "  --volume) [ \"$2\" = state ] && echo 72 on ;;\n"
          "  --filters) printf 'filter \"All Games\"\\n\\tsort_by Title\\nfilter \"Fighting\"\\n\\trule Category contains Fight\\n"
          "filter \"Shooters\"\\n\\trule Category contains Shooter\\nfilter \"80s\"\\n\\trule Year less_than 1990\\n' ;;\n"
          "  --downloader) echo pct=45; echo state=downloading; echo 'line=5.2 GB of 11.6 GB, 3.1 MB/s'; echo filter=Cabinet ;;\n"
          "  --bios) [ \"$2\" = status ] && printf 'auto=1\\ndownloaded=3\\npresent=128\\nmissing=3\\nfailed=1\\n' ;;\n"
          "  --settings) echo 'latency|System|Latency mode|choice|low|standard=Standard;low=Low|Shorter input lag.' ;;\n"
          "esac\nexit 0\n" % tmp, mode=0o755)
    write(os.path.join(tmp, "systems"), "\n".join(lines) + "\n")
    # O jogo aberto: um processo "groovymame" com o set na linha de comando.
    sleeper = os.path.join(tmp, "game")
    write(sleeper, "import time\nwhile True:\n    time.sleep(1)\n")
    game = subprocess.Popen(["groovymame", sleeper, "-rompath", os.path.join(home, "roms", "mame"), "sf2"], executable=sys.executable)
    run = os.path.join(tmp, "run", "0")
    os.makedirs(run, exist_ok=True)

    def fps_loop():
        n = 0
        while game.poll() is None:
            write(os.path.join(run, "fliperos-fps"), "%d %.1f groovymame - 0\n" % (game.pid, 59.6 + (n % 5) * .1))
            n += 1
            time.sleep(1)
    threading.Thread(target=fps_loop, daemon=True).start()
    # O controle: alguem jogando (o golpe da demonstracao do OBS, sem parar).
    buttons = os.path.join(tmp, "fliperos-buttons")
    write(buttons, "#!/bin/sh\nwhile true; do for s in '[\"down\"]' '[\"down\",\"right\"]' '[\"right\",\"b3\"]' '[\"right\"]' '[]' "
          "'[\"b4\"]' '[\"b2\",\"b5\"]' '[]'; do echo \"{\\\"1\\\": $s, \\\"2\\\": [\\\"b1\\\"]}\"; sleep .3; done; done\n", mode=0o755)
    stream = os.path.join(tmp, "fliperos-stream")
    write(stream, "#!/bin/sh\n[ \"$1\" = status ] && printf 'installed=1\\nactive=1\\nencoder=x264\\naudio=1\\nlink=wired\\n'\nexit 0\n", mode=0o755)
    check = os.path.join(tmp, "video-check.py")
    write(check, "def read_active():\n    return [{'card': '/dev/dri/card0', 'connector': 'VGA-1', 'active': True, 'width': 640, 'height': 240,"
          " 'horizontal_khz': 15.6875, 'vertical_hz': 59.6, 'interlaced': False, 'clock_khz': 13013, 'htotal': 830, 'vtotal': 263,"
          " 'flags': 10}], []\n")
    write(os.path.join(tmp, "fliperos.conf"), "monitor=generic_15\nfrequency=15k\nboot_resolution=640x240S\nconnector=VGA-1\n")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, FLIPEROS_SHADOW=os.path.join(tmp, "shadow"), FLIPEROS_WEB_STATIC=os.path.join(ROOT, "config/web"),
               FLIPEROS_WEB_GUI=os.path.join(ROOT, "fliperos-setup/gui"), FLIPEROS_HOME=home, FLIPEROS_USER="root",
               FLIPEROS_SETUP=setup, FLIPEROS_RUN_USER=os.path.join(tmp, "run"), FLIPEROS_CONF=os.path.join(tmp, "fliperos.conf"),
               FLIPEROS_VIDEO_CHECK=check, FLIPEROS_BUTTONS_TOOL=buttons, FLIPEROS_STREAM=stream,
               FLIPEROS_LOGS=os.path.join(tmp, "logs"), FLIPEROS_ADB_URL="http://127.0.0.1:9/none",
               FLIPEROS_OVERLAY_KEY=os.path.join(tmp, "overlay.key"))
    os.makedirs(os.path.join(tmp, "logs"), exist_ok=True)
    write(os.path.join(tmp, "logs", "retroarch.log"), "[INFO] Loading content\n")
    subprocess.Popen([sys.executable, os.path.join(ROOT, "config/fliperos-web"), "--bind", "127.0.0.1", "--port", str(port),
                      "--redirect-port", "0"], env=env)
    for _ in range(100):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.1)
    return "http://127.0.0.1:%d" % port


def write(path, data, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode if mode in ("w", "wb") else "w") as f:
        f.write(data)
    if not isinstance(mode, str):
        os.chmod(path, mode)


# ── O Chromium, pelo protocolo de depuracao ──
class Browser:
    def __init__(self):
        import websocket
        self.proc = subprocess.Popen(["chromium", "--headless=new", "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
                                      "--remote-debugging-port=9223", "--remote-allow-origins=*", "--hide-scrollbars",
                                      "--autoplay-policy=no-user-gesture-required", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            try:
                page = next(t for t in json.load(urllib.request.urlopen("http://127.0.0.1:9223/json/list")) if t["type"] == "page")
                break
            except Exception:
                time.sleep(0.5)
        self.ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60)
        self.seq = 0
        self.errors = []
        for domain in ("Page", "Runtime", "Log", "Network"):
            self.call(domain + ".enable")

    def call(self, method, **params):
        self.seq += 1
        n = self.seq
        self.ws.send(json.dumps({"id": n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("method") == "Runtime.exceptionThrown":
                self.errors.append(msg["params"]["exceptionDetails"].get("exception", {}).get("description", "exception"))
            elif msg.get("method") == "Log.entryAdded" and msg["params"]["entry"]["level"] == "error":
                entry = msg["params"]["entry"]
                # O 401 do login e o 503 da captura (sem tela na demonstracao) sao esperados.
                if not any(x in entry.get("url", "") for x in ("favicon", "/api/gameinfo", "/api/me", "/api/screenshot")):
                    self.errors.append("%s %s" % (entry.get("text"), entry.get("url", "")))
            elif msg.get("id") == n:
                if "error" in msg:
                    raise RuntimeError("%s: %s" % (method, msg["error"]))
                return msg.get("result", {})

    def js(self, code):
        out = self.call("Runtime.evaluate", expression=code, awaitPromise=True, returnByValue=True)
        return out.get("result", {}).get("value")

    def wait(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            self.js("1")
            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="the panel of this repository with example data")
    parser.add_argument("paths", nargs="+", help="[the panel address (http://IP:8081)] OUT")
    parser.add_argument("--password", default="fliperos")
    parser.add_argument("--lang", default="pt")
    parser.add_argument("--only", default="", help="names, comma-separated")
    parser.add_argument("--all", action="store_true", help="every area and tab, whole page, PC and phone")
    args = parser.parse_args()
    if args.all:
        routes = ["frontend", "live/watch", "live/obs", "library/overview", "library/install", "library/downloads",
                  "library/romfilter", "library/art", "library/files", "system/status", "system/logs", "system/settings",
                  "system/terminal", "system/lab"]
        SHOTS[:] = [("00-login-pc", "", 1440, 900, 1, False, False, "logout"),
                    ("00-login-celular", "", 390, 844, 2, True, False, "logout")]
        for i, route in enumerate(routes, 1):
            name = "%02d-%s" % (i, route.replace("/", "-"))
            SHOTS.append((name + "-pc", "#" + route, 1440, 900, 1, False, True, ""))
            SHOTS.append((name + "-celular", "#" + route, 390, 844, 2, True, True, ""))
        SHOTS.append(("15-jogo-pc", "#frontend", 1440, 900, 1, False, False, "sheet"))
        SHOTS.append(("15-jogo-celular", "#frontend", 390, 844, 2, True, True, "sheet"))
        SHOTS.append(("16-tarefas-pc", "#library", 1440, 900, 1, False, False, "tasks"))
    if len(args.paths) != (1 if args.demo else 2):
        parser.error("give OUT with --demo, or the address and OUT")
    args.out = args.paths[-1]
    tmp = tempfile.mkdtemp()
    base = demo(tmp) if args.demo else args.paths[0].rstrip("/")
    os.makedirs(args.out, exist_ok=True)
    req = urllib.request.Request(base + "/api/login", json.dumps({"user": "fliperos", "password": args.password}).encode(),
                                 {"Content-Type": "application/json", "X-FliperOS": "1"})
    cookie = urllib.request.urlopen(req).headers["Set-Cookie"].split(";")[0].split("=", 1)
    browser = Browser()
    host = base.split("//")[1].split(":")[0]
    failed = False
    for name, route, width, height, scale, mobile, full, action in SHOTS:
        if args.only and name not in args.only.split(","):
            continue
        browser.call("Emulation.setDeviceMetricsOverride", width=width, height=height, deviceScaleFactor=scale, mobile=mobile)
        browser.call("Emulation.setTouchEmulationEnabled", enabled=mobile)
        browser.call("Network.clearBrowserCookies")
        if action != "logout":
            browser.call("Network.setCookie", name=cookie[0], value=cookie[1], domain=host, path="/")
        browser.call("Page.navigate", url=base + "/")
        browser.wait(1)
        browser.js("localStorage.setItem('fliperos-lang', %s); localStorage.removeItem('fliperos-view'); location.hash = %s;"
                   " location.reload()" % (json.dumps(args.lang), json.dumps(route)))
        browser.wait(4)
        if action == "sheet":
            browser.js("document.querySelector('#games .game').click()")
            browser.wait(2)
        elif action == "list":
            browser.js("document.getElementById('view-list').click(); document.getElementById('games-head').scrollIntoView()")
            browser.wait(1.5)
        elif action == "tasks":
            browser.js("document.getElementById('tasks-btn').click()")
            browser.wait(1.5)
        shot = {"format": "png"}
        if full:
            size = browser.js("[document.documentElement.scrollWidth, document.documentElement.scrollHeight]")
            browser.call("Emulation.setDeviceMetricsOverride", width=width, height=size[1], deviceScaleFactor=scale, mobile=mobile)
            browser.wait(1.5)
        data = browser.call("Page.captureScreenshot", **shot)["data"]
        with open(os.path.join(args.out, name + ".png"), "wb") as f:
            f.write(base64.b64decode(data))
        wide = browser.js("document.documentElement.scrollWidth > window.innerWidth + 1")
        if wide:
            print("%s: the page scrolls sideways" % name)
            failed = True
        print(name, "ok")
    for error in browser.errors:
        print("console:", error)
    browser.proc.terminate()
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if failed or browser.errors else 0


if __name__ == "__main__":
    sys.exit(main())
