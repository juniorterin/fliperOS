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
    ("status-pc", "#system", 1440, 900, 1, False, True, ""),
    ("status-celular", "#system/status", 390, 844, 2, True, True, ""),
    ("logs-pc", "#system/logs", 1440, 900, 1, False, False, ""),
    ("aovivo-pc", "#live/obs", 1440, 900, 1, False, False, ""),
    # O Setup inteiro como lista (setup.js) e os jogos custom (customgames.js).
    ("setup-video-pc", "#system/setup/video", 1440, 900, 1, False, True, ""),
    ("setup-video-celular", "#system/setup/video", 390, 844, 2, True, True, "filter"),
    ("setup-lista-celular", "#system/setup", 390, 844, 2, True, False, ""),
    ("setup-audio-pc", "#system/setup/audio", 1440, 900, 1, False, True, ""),
    ("setup-rede-pc", "#system/setup/network", 1440, 900, 1, False, True, ""),
    ("setup-jogos-pc", "#system/setup/games", 1440, 900, 1, False, True, ""),
    ("setup-controles-celular", "#system/setup/joysticks", 390, 844, 2, True, True, ""),
    ("setup-sistema-pc", "#system/setup/system", 1440, 900, 1, False, True, ""),
    ("setup-versao-pc", "#system/setup/system/version", 1440, 900, 1, False, False, ""),
    ("setup-busca-pc", "#system/setup/video", 1440, 900, 1, False, True, "search"),
    ("setup-gabinete-pc", "#system/setup/video", 1440, 900, 1, False, False, "cabinet"),
    ("conquistas-pc", "#system/achievements", 1440, 900, 1, False, False, ""),
    ("nuvem-celular", "#system/cloud", 390, 844, 2, True, False, ""),
    ("terminal-pc", "#system/terminal", 1440, 900, 1, False, False, ""),
    ("lab-celular", "#system/lab", 390, 844, 2, True, False, ""),
    # As do site e da wiki (website/public/screenshots/web, 1280x800).
    ("site-status", "#system/status", 1280, 800, 1, False, False, ""),
    ("site-setup", "#system/setup/video", 1280, 800, 1, False, False, ""),
    # As do post do Telegram de um update (docs/telegram/img).
    ("tg-entrelacado", "#system/setup/video", 1280, 800, 1, False, False, "scroll:#si-video-mode480"),
    ("tg-osd", "#system/setup/video", 1280, 800, 1, False, False, "scroll:#si-video-osd"),
    ("tg-sons", "#system/setup/audio", 1280, 800, 1, False, False, ""),
    ("tg-gabinete", "#system/setup/video", 1280, 800, 1, False, False, "cabinet"),
    ("tg-custom", "#system/setup/games/custom", 1280, 800, 1, False, False, ""),
    ("tg-celular-lista", "#system/setup", 390, 844, 2, True, False, ""),
    ("tg-celular-video", "#system/setup/video", 390, 844, 2, True, False, ""),
    ("custom-pc", "#system/setup/games/custom", 1440, 900, 1, False, True, "cg-table"),
    ("custom-celular", "#system/setup/games/custom", 390, 844, 2, True, True, "cg-table"),
    ("custom-adicionar-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-add"),
    ("custom-adicionar-celular", "#system/setup/games/custom", 390, 844, 2, True, False, "cg-add"),
    ("custom-tabela-celular", "#system/setup/games/custom", 390, 844, 2, True, False, "cg-table-view"),
    ("custom-instalar-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-tab-install"),
    ("custom-instalar-celular", "#system/setup/games/custom", 390, 844, 2, True, True, "cg-tab-install"),
    ("custom-criar-pc", "#system/setup/games/custom", 1440, 900, 1, False, True, "cg-tab-create"),
    ("custom-criar-celular", "#system/setup/games/custom", 390, 844, 2, True, False, "cg-tab-create"),
    ("custom-previa-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-create-preview"),
    ("custom-arte-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-table-art"),
    ("custom-estrutura-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-structure"),
    ("custom-teste-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-test-panel"),
    ("custom-teste-celular", "#system/setup/games/custom", 390, 844, 2, True, False, "cg-test-panel"),
    ("custom-estrutura-celular", "#system/setup/games/custom", 390, 844, 2, True, False, "cg-structure"),
    ("custom-apagar-grupo-pc", "#system/setup/games/custom", 1440, 900, 1, False, False, "cg-group-delete"),
]

# Os jogos custom de exemplo: grupo, nome, plataforma, modo, cena.
CUSTOM_GAMES = [("PC games", "Metal Slug X", "windows", "640x240@60", "shooter"),
                ("PC games", "Cave Story", "native", "640x240@60", "platform"),
                ("PC games", "Pang Deluxe", "command", "640x480@60", "racing"),
                ("Homebrew", "Pong 2026", "command", "320x240@60", "")]
# A tabela de exemplo (o que "Importar de uma pasta" e "Colar" deixariam),
# com uma linha de erro como o Setup a devolve.
CUSTOM_TABLE = """[
 {group: "PC games", name: "Street Racer 98", platform: "windows", folder: "/media/fliperos/USB/Street Racer 98",
  exes: ["Racer.exe", "Setup/config.exe"], exe: "Racer.exe", mode: "240p", category: "Driving / Race", players: "2",
  buttons: "4", controls: ["joy8", "pedal"],
  video: {path: "/media/fliperos/USB/Street Racer 98.mp4", name: "Street Racer 98.mp4"},
  key: {path: "/media/fliperos/USB/Street Racer 98.key", name: "Street Racer 98.key"},
  ppdb: {path: "/media/fliperos/USB/Street Racer 98.ppdb", name: "Street Racer 98.ppdb"}},
 {group: "PC games", name: "Tyrian 2000", platform: "windows", folder: "/media/fliperos/USB/Tyrian2000",
  exes: ["tyrian.exe"], exe: "tyrian.exe", mode: "other", modeOther: "320x200@70", category: "Shooter / Flying Vertical",
  players: "1", buttons: "3", controls: ["joy8"]},
 {group: "Homebrew", name: "Celeste Classic", platform: "native", folder: "/home/fliperos/games/celeste",
  programs: ["celeste.x86_64"], command: "./celeste.x86_64", mode: "240p", category: "Platform / Run Jump",
  players: "1", buttons: "2", controls: ["joy8"]},
 {group: "PC games", name: "Metal Slug X", platform: "windows", folder: "", exe: "", mode: "240p",
  errors: {name: "Metal Slug X is already in PC games.", folder: "Not a folder: (empty)"}}
]"""


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
    # Os jogos custom: os grupos como sistemas (custom/GRUPO), um .sh por jogo e
    # a imagem de cada um; o fliperos-setup --customgames descreve os mesmos.
    describe = []
    for group in sorted({g[0] for g in CUSTOM_GAMES}):
        folder = os.path.join(home, "roms", "custom", group)
        lines.append("custom/%s|%s|custom|%s|/bin/sh|\"[romfilename]\"|.sh|0" % (group, folder, group))
        describe.append("group\t%s\t%d" % (group, sum(1 for g in CUSTOM_GAMES if g[0] == group)))
    for n, (group, name, platform, mode, kind) in enumerate(CUSTOM_GAMES):
        write(os.path.join(home, "roms", "custom", group, name + ".sh"), "#!/bin/sh\n", mode=0o755)
        if kind:
            write(os.path.join(home, "media", "snap", "custom", group, name + ".png"), scene(kind, 40 + n), "wb")
            if n % 2 == 0:
                # O logotipo (a wheel) de uns jogos, por cima da imagem.
                write(os.path.join(home, "media", "logo", "custom", group, name + ".png"), marquee_art(n + 5, 320, 80), "wb")
        describe.append("\t".join(("game", group, name, platform, mode, "", "joy8", "2", "2",
                                   "wine pang.exe" if platform == "command" else "./CaveStory.x86_64" if platform == "native" else "",
                                   "MetalSlugX.exe" if platform == "windows" else "", "/home/fliperos/games/%s/%s" % (group, name), "")))
    # Os cartoes do Instalar pacotes: zips de verdade em ~/roms/custom-packages
    # (o fliperos-customgame packages os le): novos com imagem e texto, um
    # instalado, um com o nome errado e um sem a pasta do jogo.
    import zipfile
    pkgdir = os.path.join(home, "roms", "custom-packages")
    os.makedirs(pkgdir, exist_ok=True)
    blurb = ("Street fighters from around the world meet again. Pick a fighter, learn the special moves and the "
             "Ultra combos, and beat the tournament. Six buttons, two players side by side on the cabinet.")
    for base, cfg, kind, extra in (
            ("Street Fighter 4", "platform=windows\nexe=StreetFighterIV.exe\nmode=480i\ncategory=Fighter / Versus\n"
             "controls=joy8\nbuttons=6\nplayers=2\n", "racing", {"txt": blurb, "key": "p1_b1=Z\n"}),
            ("Tetris DX", "platform=windows\nexe=tetris.exe\nmode=240p\ncategory=Puzzle / Drop\ncontrols=joy4\n"
             "buttons=2\nplayers=1\n", "platform", {"txt": "Blocks fall; make lines."}),
            ("Cave Story", "platform=native\ncommand=./CaveStory.x86_64\nmode=240p\ncategory=Platform / Run Jump\n"
             "controls=joy8\nbuttons=2\nplayers=1\n", "platform", {})):
        path = os.path.join(pkgdir, base + ".fliperos-customgame.zip")
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr(base + ".cfg", "name=%s\n%s" % (base, cfg))
            zf.writestr(base + ".png", scene(kind, len(base)))
            zf.writestr(base + "/" + (cfg.split("exe=")[1].split("\n")[0] if "exe=" in cfg else "CaveStory.x86_64"), "MZ")
            for ext, data in extra.items():
                zf.writestr(base + "." + ext, data)
    # O Cave Story ja instalado dele (o cfg aponta o zip, com o tamanho e a data).
    cave = os.path.join(pkgdir, "Cave Story.fliperos-customgame.zip")
    st = os.stat(cave)
    write(os.path.join(home, "roms", "custom", "PC games", "Cave Story.cfg"),
          "name=Cave Story\nplatform=native\npackage=%s\npackage_stamp=%d:%d\n" % (cave, st.st_size, int(st.st_mtime)))
    with zipfile.ZipFile(os.path.join(pkgdir, "Pang.zip"), "w") as zf:
        zf.writestr("Pang.cfg", "name=Pang\nplatform=native\n")
        zf.writestr("Pang/pang", "#!/bin/sh\n")
    with zipfile.ZipFile(os.path.join(pkgdir, "Metal Slug X.fliperos-customgame.zip"), "w") as zf:
        zf.writestr("Metal Slug X.cfg", "platform=windows\n")
        zf.writestr("readme.txt", "x")
    # Os pacotes de ~/roms/custom-packages (a aba Instalar pacotes): novos, um
    # que mudou, um instalado e um que nao serve.
    pkgs = "/home/fliperos/roms/custom-packages/"
    describe += ["pending\t%sStreet Fighter 4.fliperos-customgame.zip\t\tStreet Fighter 4\twindows\tnew\t" % pkgs,
                 "pending\t%sTetris DX.fliperos-customgame.zip\t\tTetris DX\twindows\tnew\t" % pkgs,
                 "pending\t%sCave Story.fliperos-customgame.zip\tPC games\tCave Story\tnative\tupdate\t" % pkgs,
                 "pending\t%sMetal Slug X.fliperos-customgame.zip\tPC games\tMetal Slug X\twindows\tinstalled\t" % pkgs,
                 "pending\t%sPang.zip\t\tPang\twindows\tbad\trename it to Pang.fliperos-customgame.zip "
                 "(packages always end in .fliperos-customgame.zip)" % pkgs,
                 "packages\t/home/fliperos/roms/custom-packages", "lastgroup\tPC games",
                 "mode\t240p\t640x240@60", "mode\t480i\t640x480@60"]
    for genre, subs in (("Driving", ("Race", "Motorcycle")), ("Fighter", ("Versus", "2.5D")), ("Platform", ("Run Jump",)),
                        ("Puzzle", ("Drop", "Match")), ("Shooter", ("Flying Vertical", "Gallery", "Scrolling"))):
        describe.append("genre\t" + genre)
        describe += ["sub\t%s / %s" % (genre, s) for s in subs]
    for value, label in (("joy8", "8-way joystick"), ("joy4", "4-way joystick"), ("joy2", "2-way joystick"),
                         ("twin", "Twin sticks"), ("trackball", "Trackball"), ("spinner", "Spinner"), ("paddle", "Paddle"),
                         ("positional", "Rotary joystick"), ("analog", "Analog stick"), ("pedal", "Pedals"),
                         ("lightgun", "Light gun"), ("keyboard", "Keyboard"), ("mahjong", "Mahjong")):
        describe.append("control\t%s\t%s" % (value, label))
    describe += ["squash\t/home/fliperos/games/PC games/Metal Slug X\t1\t412M", "portproton\t0",
                 "games\t/home/fliperos/games", "free\t%d" % (183 << 30)]
    write(os.path.join(tmp, "customgames"), "\n".join(describe) + "\n")
    setup = os.path.join(tmp, "fliperos-setup")
    write(setup, "#!/bin/sh\ncase \"$1\" in\n  --systems) cat %s/systems ;;\n"
          "  --volume) [ \"$2\" = state ] && echo 72 on ;;\n"
          "  --filters) printf 'filter \"All Games\"\\n\\tsort_by Title\\nfilter \"Fighting\"\\n\\trule Category contains Fight\\n"
          "filter \"Shooters\"\\n\\trule Category contains Shooter\\nfilter \"80s\"\\n\\trule Year less_than 1990\\n' ;;\n"
          "  --downloader) echo pct=45; echo state=downloading; echo 'line=5.2 GB of 11.6 GB, 3.1 MB/s'; echo filter=Cabinet ;;\n"
          "  --bios) [ \"$2\" = status ] && printf 'auto=1\\ndownloaded=3\\npresent=128\\nmissing=3\\nfailed=1\\n' ;;\n"
          "  --settings) echo 'monitor|Video|Monitor type|choice|d9200|generic_15=Generic 15.7 kHz;"
          "arcade_31=Arcade 31.5 kHz - high resolution;d9200=Wells Gardner D9200|The monitor model or its frequencies.'\n"
          "    echo 'resolution|Video|Boot resolution|choice|640x480S|640x480S=640x480 60 Hz progressive|"
          "The video mode of the boot, the menus, the frontend and the desktop.'\n"
          "    echo 'video.previous|Video|Back to the previous monitor|action|||Back to Generic 15.7 kHz, 640x480i:"
          " the monitor and resolution before the last change.'\n"
          "    echo 'orientation|Video|Monitor orientation|choice|horizontal|horizontal=Horizontal;"
          "vertical-cw=Vertical clockwise|How the monitor is mounted in the cabinet.'\n"
          "    echo 'osd|Video|On-screen menu|choice|on|on=On;off=Off|Volume, filter, geometry and colour over any game.'\n"
          "    echo 'color.brightness|Colour|Brightness|number|0|-50..50:1|Moves the whole picture up or down.'\n"
          "    echo 'color.contrast|Colour|Contrast|number|100|50..150:1|Spreads or squeezes the picture.'\n"
          "    echo 'color.gamma|Colour|Gamma|number|100|50..200:5|The midtones.'\n"
          "    echo 'color.reset|Colour|Back to the defaults|action|||Every colour setting back to the default.'\n"
          "    for p in RetroArch:240p Flycast:filter Dolphin:filter PCSX2:pure GroovyMAME:240p SM2-Emu:240p Supermodel:240p"
          " DuckStation:240p PPSSPP:240p; do k=${p%%%%:*}; v=${p#*:};"
          " echo \"mode480.$k|Interlaced hacks|$k|choice|$v|240p=640x240;filter=Interlaced filter;pure=Interlaced pure|How $k draws.\";"
          " echo \"deflicker.$k|Interlaced hacks|$k: filter level|choice|medium|light=Light;medium=Medium;strong=Strong|The level.\"; done\n"
          "    echo 'menu_sounds|Audio|Menu sounds|choice|on|on=On;off=Off|The WAV files in sounds/menu.'\n"
          "    echo 'gun_flash|GunCon 2|Screen flash|choice|pulse|pulse=Pulse (two light frames on each shot);hold=Hold;off=Off|The flash.'\n"
          "    echo 'gun.flash_level|GunCon 2|Flash brightness (%%)|number|100|10..100:10|Lower is calmer.'\n"
          "    echo 'gun_offscreen_reload|GunCon 2|Off-screen reload button|choice|on|on=On;off=Off|Off the screen the trigger reloads.'\n"
          "    echo 'padcolor|Joysticks|Controller light|choice|fliperos|fliperos=FliperOS (roulette, game colours);7a00ff=Purple;"
          "ff0080=Pink;off=Off|The light colour of DualSense.'\n"
          "    echo 'stream_audio|Live screen|Live screen sound|choice|on|off=Off;on=On|A copy of the sound for the live screen.'\n"
          "    echo 'stream_quality|Live screen|Live screen quality|choice|normal|light=Light (weak Wi-Fi);normal=Normal;high=High;"
          "max=Maximum (network cable)|The picture of the live screen.'\n"
          "    echo 'launcher|System|What starts when the cabinet turns on|choice|fliperos|fliperos=FliperOS frontend;"
          "attractplus=Attract-Mode Plus;esde=ES-DE;menu=FliperOS menu|The default launcher.'\n"
          "    echo 'debug|System|Debug mode|choice|off|off=Off;on=On (show all text)|Frontends and emulators follow it now.'\n"
          "    echo 'splash|System|Boot splash|choice|fliperos|fliperos=FliperOS;arcade=Arcade;neon=Neon|The picture while the cabinet boots.'\n"
          "    echo 'audio_card|Audio|Sound card|choice|1_0|0_3=HDMI 0;1_0=HD-Audio Generic - ALC887 Analog|The card used by the system.'\n"
          "    echo 'mame_latency|Audio|MAME audio latency|number|0.0|0..50:0.5|Lower responds faster.'\n"
          "    echo 'audio.test|Audio|Test sound|action|||A voice on the cabinet speakers.'\n"
          "    echo 'marquee_overlay|Live screen|Marquee overlay for OBS|choice|off|off=Off;on=On|The marquee for OBS.'\n"
          "    echo 'cabinet_name|System|Cabinet name|text|SALA 2|12|The name the other cabinets see.'\n"
          "    echo 'latency|System|Latency mode|choice|low|standard=Standard;low=Low|Shorter input lag.'\n"
          "    echo 'service.ssh|Services|SSH|choice|boot|boot=Boot;after=After boot;off=Off|Remote shell.'\n"
          "    echo 'power.reboot|Power|Restart the cabinet|action|||The cabinet restarts.'\n"
          "    echo 'power.poweroff|Power|Turn off the cabinet|action|||The cabinet turns off.' ;;\n"
          "  --geometry) printf 'monitor=generic_15\\nlabel=Generic 15 kHz\\nrange=\\npreset=15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576\\n' ;;\n"
          "  --wifi) case \"$2\" in status) echo 'eth0|ethernet|unavailable||'; echo 'wlan0|wifi|connected|Casa|192.168.1.241' ;;\n"
          "    scan) echo 'wlan0|Casa|82|WPA2'; echo 'wlan0|Vizinho 5G|41|WPA2'; echo 'wlan0|Cafe|20|' ;; esac ;;\n"
          "  --whatsnew) printf 'This is FliperOS 0.25, update 77.\\n\\nUpdates installed:\\n- 34. Web panel redesign\\n' ;;\n"
          "  --customgames) case \"$2\" in describe) cat %s/customgames ;; check) echo bytes=1288490188; echo free=196494753792 ;;\n"
          "    group-info) printf 'games=3\\nfolders=2\\npackages=1\\nothers=1\\nother=manual.pdf\\n' ;; esac ;;\n"
          "  --setup-items) printf 'item|driver|1\\ninfo|driver|radeon (tested on the CRT) or amdgpu (with Vulkan).\\n"
          "item|bluetooth|1\\nitem|romlist|1\\ninfo|buttons|Player 1: arcade panel (V-USB Mame Panel). Player 2: 8BitDo Pro 2.\\n"
          "info|lpt|\\n' ;;\n"
          "  --frontends) [ \"$2\" = list ] && echo 'custom-1|Pegasus|pegasus-fe --silent|1' ;;\n"
          "  --folders) [ \"$2\" = list ] && printf 'roms|custom|/media/fliperos/USB/ROMs|1|The games: one folder per emulator.\\n"
          "bios|default||1|The BIOS files of RetroArch and of the other emulators.\\nmedia|default||1|The art the frontends show.\\n"
          "start|/media/fliperos\\n' ;;\n"
          "  --quirks) case \"$2\" in list) echo '0x16c0:0x05e1:0x40|Xin-Mo dual encoder' ;;\n"
          "    devices) echo '0x16c0:0x05e1|Van Ooijen Technische Informatica Free shared VID'; echo '0x2dc8:0x6101|8BitDo Pro 2' ;; esac ;;\n"
          "  --bluetooth) case \"$2\" in status) printf 'installed=yes\\nadapter=hci0\\npowered=yes\\n' ;;\n"
          "    devices) echo 'E4:17:D8:00:11:22|8BitDo Pro 2|input-gaming|yes|yes' ;; esac ;;\n"
          "esac\nexit 0\n" % (tmp, tmp), mode=0o755)
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
    # O fliperos-update: os updates da versao (Setup > System > FliperOS version).
    update = os.path.join(tmp, "fliperos-update")
    write(update, "#!/bin/sh\n[ \"$1\" = versions ] && printf 'level=74\\nbase=60\\nlatest=74\\nhold=\\nreboot=no\\n"
          "74\\tcurrent\\tno\\tCustom games in the web panel\\n73\\tolder\\tno\\tCustom game packages\\n'\nexit 0\n", mode=0o755)
    check = os.path.join(tmp, "video-check.py")
    write(check, "def read_active():\n    return [{'card': '/dev/dri/card0', 'connector': 'VGA-1', 'active': True, 'width': 640, 'height': 240,"
          " 'horizontal_khz': 15.6875, 'vertical_hz': 59.6, 'interlaced': False, 'clock_khz': 13013, 'htotal': 830, 'vtotal': 263,"
          " 'flags': 10}], []\n")
    write(os.path.join(tmp, "fliperos.conf"), "monitor=generic_15\nfrequency=15k\nboot_resolution=640x240S\nconnector=VGA-1\n")
    # Os perfis do menu na tela e um dos dois sons do menu ja enviado.
    write(os.path.join(tmp, "osd-profiles.conf"), "default\tcolor.brightness\t0\ndefault\tcolor.gamma\t100\n"
          "game:fbneo/sf2\tcolor.brightness\t6\ngame:fbneo/sf2\tcolor.gamma\t110\ngame:fbneo/sf2\tlevel.fbneo\tstrong\n"
          "core:fbneo\tcolor.contrast\t110\nemu:groovymame\tlevel.groovymame\tmedium\nres:640x480i\tcolor.contrast\t105\n")
    write(os.path.join(tmp, "sounds", "move.wav"), b"RIFF\x24\x23\x00\x00WAVEfmt " + bytes(9000), "wb")
    # A placa de video no /sys (o driver e o nome do lspci de mentira).
    dev = os.path.join(tmp, "pci", "0000:01:00.0")
    for name, value in (("gpu_busy_percent", "12"), ("mem_info_vram_used", str(310 << 20)), ("mem_info_vram_total", str(2 << 30)),
                        ("pp_dpm_sclk", "0: 300Mhz\n1: 1050Mhz *\n")):
        write(os.path.join(dev, name), value + "\n")
    os.makedirs(os.path.join(tmp, "drivers", "amdgpu"), exist_ok=True)
    os.symlink(os.path.join(tmp, "drivers", "amdgpu"), os.path.join(dev, "driver"))
    os.makedirs(os.path.join(tmp, "sys/class/drm/card0"), exist_ok=True)
    os.symlink(dev, os.path.join(tmp, "sys/class/drm/card0/device"))
    write(os.path.join(tmp, "bin", "lspci"), "#!/bin/sh\necho '01:00.0 \"VGA compatible controller\" "
          "\"Advanced Micro Devices, Inc. [AMD/ATI]\" \"Oland PRO [Radeon R7 240/340]\"'\n", mode=0o755)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    env = dict(os.environ, FLIPEROS_SHADOW=os.path.join(tmp, "shadow"), FLIPEROS_WEB_STATIC=os.path.join(ROOT, "config/web"),
               FLIPEROS_WEB_GUI=os.path.join(ROOT, "fliperos-setup/gui"), FLIPEROS_HOME=home, FLIPEROS_USER="root",
               FLIPEROS_CUSTOMGAME=os.path.join(ROOT, "config/fliperos-customgame"),
               FLIPEROS_SETUP=setup, FLIPEROS_RUN_USER=os.path.join(tmp, "run"), FLIPEROS_CONF=os.path.join(tmp, "fliperos.conf"),
               FLIPEROS_VIDEO_CHECK=check, FLIPEROS_BUTTONS_TOOL=buttons, FLIPEROS_STREAM=stream,
               FLIPEROS_UPDATE_TOOL=update, FLIPEROS_WEB_STAGE=os.path.join(tmp, "stage"),
               FLIPEROS_LOGS=os.path.join(tmp, "logs"), FLIPEROS_ADB_URL="http://127.0.0.1:9/none",
               FLIPEROS_OVERLAY_KEY=os.path.join(tmp, "overlay.key"), FLIPEROS_SYS=os.path.join(tmp, "sys"),
               FLIPEROS_OSD_PROFILES=os.path.join(tmp, "osd-profiles.conf"), FLIPEROS_MENU_SOUNDS=os.path.join(tmp, "sounds"),
               PATH=os.path.join(tmp, "bin") + os.pathsep + os.environ.get("PATH", ""))
    # Os sensores de temperatura (o hwmon do /sys): CPU, GPU, disco e Wi-Fi.
    for n, (name, label, temp, crit) in enumerate((("coretemp", "Core 0", 52, 100), ("coretemp", "Core 1", 58, 100),
                                                   ("amdgpu", "edge", 71, 0), ("nvme", "Composite", 38, 84),
                                                   ("acpitz", "", 44, 0), ("rtw88", "", 83, 0))):
        mon = os.path.join(tmp, "sys/class/hwmon/hwmon%d" % n)
        write(os.path.join(mon, "name"), name + "\n")
        write(os.path.join(mon, "temp1_input"), "%d\n" % (temp * 1000))
        if label:
            write(os.path.join(mon, "temp1_label"), label + "\n")
        if crit:
            write(os.path.join(mon, "temp1_crit"), "%d\n" % (crit * 1000))
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
                  "system/terminal", "system/lab", "system/achievements", "system/cloud"]
        SHOTS[:] = [("00-login-pc", "", 1440, 900, 1, False, False, "logout"),
                    ("00-login-celular", "", 390, 844, 2, True, False, "logout")]
        for i, route in enumerate(routes, 1):
            name = "%02d-%s" % (i, route.replace("/", "-"))
            SHOTS.append((name + "-pc", "#" + route, 1440, 900, 1, False, True, ""))
            SHOTS.append((name + "-celular", "#" + route, 390, 844, 2, True, True, ""))
        SHOTS.append(("15-jogo-pc", "#frontend", 1440, 900, 1, False, False, "sheet"))
        SHOTS.append(("15-jogo-celular", "#frontend", 390, 844, 2, True, True, "sheet"))
        SHOTS.append(("16-tarefas-pc", "#library", 1440, 900, 1, False, False, "tasks"))
        for pick in ("marquee", "pad"):
            SHOTS.append(("03-live-obs-%s-pc" % pick, "#live/obs", 1440, 900, 1, False, True, "obs-" + pick))
            SHOTS.append(("03-live-obs-%s-celular" % pick, "#live/obs", 390, 844, 2, True, True, "obs-" + pick))
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
        elif action == "open-all":
            browser.js("document.querySelectorAll('#settings details').forEach((d) => { d.open = true; })")
            browser.wait(3)
        elif action == "filter":
            # Um programa com o filtro: o nivel aparece na mesma linha.
            browser.js("const b = document.querySelector('.m480 .choice button[data-value=\"filter\"]');"
                       " if (b) b.closest('.srow').scrollIntoView()")
            browser.wait(1)
        elif action == "search":
            browser.js("const q = document.getElementById('setup-q'); q.value = 'gama'; q.dispatchEvent(new Event('input'))")
            browser.wait(1.5)
        elif action.startswith("scroll:"):
            # Uma secao no alto da tela (o seletor depois de "scroll:").
            browser.js("const s = document.querySelector(%s); if (s) { s.scrollIntoView(); window.scrollBy(0, -16); }"
                       % json.dumps(action[7:]))
            browser.wait(1)
        elif action == "cabinet":
            browser.js("document.querySelector('#settings .srow.cab-row').click()")
            browser.wait(1)
        elif action in ("cg-table", "cg-table-view"):
            # A tabela com linhas de exemplo (as de "Importar de uma pasta" e
            # uma com os erros que o Setup devolve).
            browser.js("cgShowTab('games'); cg.rows = %s.map((r) => cgNewRow(r)); cgTableDraw();"
                       " document.getElementById('cg-status').textContent = t('cg_errors');%s"
                       % (CUSTOM_TABLE, " document.getElementById('cg-table').scrollIntoView();" if action == "cg-table-view" else ""))
            browser.wait(1.5)
        elif action == "cg-add":
            browser.js("cgShowTab('games'); cgAddOne()")
            browser.wait(1.5)
        elif action in ("cg-tab-install", "cg-tab-create"):
            # As abas Instalar pacotes e Criar pacote (a de criar com a
            # estrutura do pacote aberta).
            browser.js("cgShowTab(%s);%s" % (json.dumps(action[7:]),
                       " cg.el.structure.open = true;" if action == "cg-tab-create" else ""))
            browser.wait(1)
        elif action == "cg-create-preview":
            # O Criar pacote preenchido, com a previa aberta ao lado.
            browser.js("cgShowTab('create'); Object.assign(cg.createRow, {name: 'Street Fighter 4', platform: 'windows',"
                       " folder: '/media/fliperos/USB/Street Fighter 4', exe: 'StreetFighterIV.exe', exes: ['StreetFighterIV.exe'],"
                       " mode: '480i', category: 'Fighter / Versus', players: '2', buttons: '6', controls: ['joy8'],"
                       " snap: {path: '/x/sf4.png', name: 'Street Fighter 4.png', url: 'icon-512.png'},"
                       " text: {path: '/x/sf4.txt', name: 'Street Fighter 4.txt', url: '', value: 'Street fighters from around"
                       " the world meet again. Pick a fighter, learn the special moves and the Ultra combos, and beat the"
                       " tournament. Six buttons, two players side by side on the cabinet.'},"
                       " key: {path: '/x/sf4.key', name: 'Street Fighter 4.key'}});"
                       " cg.el.createPreview.hidden = false; cgCreateDraw();"
                       " document.querySelector('.cg-create-foot').scrollIntoView({block: 'end'});")
            browser.wait(1.5)
        elif action == "cg-table-art":
            # A tabela rolada ate a coluna da arte (a que veio com a pasta).
            browser.js("cgShowTab('games'); cg.rows = %s.map((r) => cgNewRow(r)); cgTableDraw();"
                       " const w = document.querySelector('.cg-table-wrap'); w.scrollIntoView(); w.scrollLeft = 99999;"
                       % CUSTOM_TABLE)
            browser.wait(1.5)
        elif action == "cg-structure":
            # A estrutura do pacote aberta (na aba Criar pacote).
            browser.js("cgShowTab('create'); cg.el.structure.open = true; cg.el.structure.scrollIntoView({block: 'start'})")
            browser.wait(1)
        elif action == "cg-test-panel":
            # O jogo aberto no teste: o aviso das teclas e a captura (com uma foto ja tirada).
            browser.js("cgShowTab('create'); Object.assign(cg.createRow, {name: 'Street Fighter 4'});"
                       " cg.el.createStatus.replaceChildren(cgTestPanel(cg.createRow));"
                       " (() => { const f = document.createElement('figure'); f.className = 'cg-capshot snap';"
                       " const i = document.createElement('img'); i.src = 'icon-512.png'; f.append(i);"
                       " document.querySelector('.cg-capshots').append(f); })();"
                       " cg.el.createStatus.scrollIntoView({block: 'center'})")
            browser.wait(1)
        elif action == "cg-group-delete":
            # A pergunta de apagar o grupo PC games (o que vai junto). void: a
            # pergunta espera um clique, e o js() esperaria a promessa.
            browser.js("cgShowTab('games'); void cgDeleteGroup('PC games')")
            browser.wait(1.5)
        elif action.startswith("obs-"):
            browser.js("obsPick(%s); document.getElementById('ovl-on').click()" % json.dumps(action[4:]) if action == "obs-marquee"
                       else "obsPick(%s)" % json.dumps(action[4:]))
            browser.wait(2)
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
