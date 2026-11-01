#!/usr/bin/env python3
"""Prints do link play no frontend REAL (fliperos-setup/gui/fliperos-frontend):
a lista com as marcas e o grupo dos jogos que outros gabinetes jogam, o menu do
jogo com o link, a sala de espera e a copia dos arquivos. A biblioteca de jogos
e de mentira (os jogos de link e alguns outros, com a arte do gabinete) e a rede
tambem (uma tabela de presenca; a sala usa o loopback de verdade).

    docker run --rm -v "$PWD:/w:ro" -v OUT:/out -v ARTE:/art:ro -w /w fliperos-guitest \\
        python3 tools/link-tests/frontend-shots.py /out /art

ARTE: as capturas do gabinete, snap_<sistema>_<jogo>.png (o do ssf2tb e o do ssf2).
Sem ela, os jogos ficam sem imagem. Nao e codigo do frontend: so o ambiente dos prints.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
import time
from importlib.machinery import SourceFileLoader

os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUI = os.path.join(ROOT, "fliperos-setup", "gui")
OUT = sys.argv[1] if len(sys.argv) > 1 else "."
ART = sys.argv[2] if len(sys.argv) > 2 else ""
sys.path.insert(0, GUI)

HOME = tempfile.mkdtemp()
os.environ["HOME"] = HOME
os.environ["FLIPEROS_HOME"] = HOME
os.environ["FLIPEROS_LINK_NVRAM"] = os.path.join(ROOT, "config", "link-nvram")
# O FBNeo roda o X-Men: o jogo de 4 jogadores tem net play num gabinete de 2 controles.
import lzma
with lzma.open(os.path.join(HOME, "fbneo.tsv.xz"), "wt") as f:
    f.write("\txmen\t\t\n")
os.environ["FLIPEROS_FBNEO_INDEX"] = os.path.join(HOME, "fbneo.tsv.xz")

# (sistema, set, titulo, ano, fabricante, categoria, jogadores, controle, botoes, arte)
GAMES = [
    ("mame", "1944", "1944: The Loop Master", "2000", "Capcom", "Shooter / Flying Vertical", "2", "joystick (8-way)", "2", "snap_mame_1944.png"),
    ("mame", "3countb", "3 Count Bout", "1993", "SNK", "Fighter / Versus", "2", "joystick (8-way)", "4", "snap_mame_3countb.png"),
    ("mame", "aof", "Art of Fighting", "1992", "SNK", "Fighter / Versus", "2", "joystick (8-way)", "4", "snap_mame_aof.png"),
    ("model3", "dirtdvls", "Dirt Devils", "1998", "Sega", "Driving / Race", "1", "paddle,pedal", "4", "snap_model3_dirtdvls.png"),
    ("model2", "daytona", "Daytona USA", "1994", "Sega", "Driving / Race (chase view)", "1", "paddle,pedal", "6", "snap_model2_daytona.png"),
    ("mame", "ssf2tb", "Super Street Fighter II: The Tournament Battle", "1993", "Capcom", "Fighter / Versus", "2",
     "joystick (8-way)", "6", "snap_mame_ssf2.png"),
    ("mame", "xmen", "X-Men (4 Players)", "1992", "Konami", "Fighter / 2.5D", "4", "joystick (8-way)", "3", "snap_mame_xmen.png"),
]
SYSTEMS = [
    {"key": key, "folder": os.path.join(HOME, "roms", key), "platform": "arcade", "name": name, "exe": "/x/fliperos-x11-run",
     "args": "x [name]", "extensions": [".zip"], "arcade": True}
    for key, name in (("mame", "MAME"), ("model2", "Model 2"), ("model3", "Supermodel"))
]


def make_home():
    for sysd in SYSTEMS:
        os.makedirs(sysd["folder"], exist_ok=True)
    for system, name, *_rest, art in GAMES:
        with open(os.path.join(HOME, "roms", system, name + ".zip"), "wb") as f:
            f.write(b"x")
        src = os.path.join(ART, art)
        if ART and os.path.isfile(src):
            dst = os.path.join(HOME, "media", "snap", system)
            os.makedirs(dst, exist_ok=True)
            shutil.copyfile(src, os.path.join(dst, name + ".png"))


def main():
    make_home()
    import fedata
    import felink

    class FakeLibrary(fedata.Library):
        def __init__(self):
            self.lock = threading.Lock()
            self.systems = SYSTEMS
            self.filters = [fedata.FAVOURITES, {"name": "All Games", "rules": [], "sort_by": "", "reverse": False, "limit": 0}]
            self.info = fedata.web.GameInfo()
            self.cache, self.stamps = {}, {}
            self.refreshing, self.generation = False, 0

        def games(self, category):
            out = []
            for system, name, title, year, maker, cat, players, control, buttons, _art in GAMES:
                s = next(x for x in SYSTEMS if x["key"] == system)
                out.append({"Name": name, "Title": title, "Year": year, "Manufacturer": maker, "Category": cat,
                            "Players": players, "Control": control, "Buttons": buttons, "_system": s,
                            "file": name + ".zip"})
            out.sort(key=lambda g: g["Title"].lower())
            return out

        def command(self, game):
            return ["/x/fliperos-x11-run", {"model3": "supermodel", "model2": "fliperos-model2"}.get(game["_system"]["key"], "groovymame"),
                    game["Name"]]

        def changed(self):
            return False

        def refresh(self, done=None):
            pass

        def hidden(self):
            return set()

        def favourites(self):
            return set()

    fedata.Library = FakeLibrary
    sys.argv = ["fliperos-frontend"]
    loader = SourceFileLoader("fe", os.path.join(GUI, "fliperos-frontend"))
    import importlib.util
    spec = importlib.util.spec_from_loader("fe", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)

    # A rede de mentira: outro gabinete (CABINET-A) com um Daytona na sala de espera (2 de 8) e outro (CABINET-C)
    # com um Tournament Battle ja comecado (3 de 4).
    net = {"table": [
        {"v": 1, "id": "a1", "name": "CABINET-A", "ip": "10.9.9.2", "game": "daytona", "system": "model2", "link": "daytona",
         "party": "a1", "slot": 1, "max": 8, "state": "lobby"},
        {"v": 1, "id": "a2", "name": "CABINET-B", "ip": "10.9.9.3", "game": "daytona", "system": "model2", "link": "daytona",
         "party": "a1", "slot": 2, "max": 8, "state": "lobby"},
        {"v": 1, "id": "c1", "name": "CABINET-C", "ip": "10.9.9.4", "game": "ssf2tb", "system": "mame", "link": "ssf2tb",
         "party": "c1", "slot": 1, "max": 4, "state": "playing"},
        {"v": 1, "id": "c2", "name": "CABINET-D", "ip": "10.9.9.5", "game": "ssf2tb", "system": "mame", "link": "ssf2tb",
         "party": "c1", "slot": 2, "max": 4, "state": "playing"},
        {"v": 1, "id": "c3", "name": "CABINET-E", "ip": "10.9.9.6", "game": "ssf2tb", "system": "mame", "link": "ssf2tb",
         "party": "c1", "slot": 3, "max": 4, "state": "playing"},
    ]}
    path = os.path.join(HOME, "net.json")
    with open(path, "w") as f:
        json.dump(net, f)
    os.environ["FLIPEROS_LINK_FAKE"] = path
    os.makedirs(OUT, exist_ok=True)

    def shots(prefix, keys, mode="list", setup=None):
        class Args:
            shot = os.path.join(OUT, prefix)
        fe = m.Frontend(Args)
        fe.overlay = None
        fe.mode = mode
        fe.rebuild()
        if setup:
            setup(fe)
        frames = [None] + list(keys)
        for i, k in enumerate(frames):
            if k:
                if callable(k):
                    k(fe)
                else:
                    fe.act(k)
            fe.draw(time.monotonic())
            fe.pg.image.save(fe.back, "%s-%d.png" % (fe.shot, i))
        return fe

    def go(name):
        def f(fe):
            fe.cursor = next(i for i, r in enumerate(fe.rows) if r[0]["Name"] == name and r[2] != "elsewhere")
        return f

    def on_row(name, elsewhere=False):
        def f(fe):
            fe.cursor = next(i for i, r in enumerate(fe.rows) if r[0]["Name"] == name and (r[2] == "elsewhere") == elsewhere)
        return f

    # A lista: um jogo de link que ninguem joga (Dirt Devils); e um que alguem joga, no grupo do alto (Daytona).
    shots("list-dim", [], setup=on_row("dirtdvls"))
    shots("list-lit", [], setup=on_row("daytona", elsewhere=True))
    shots("grid", [], mode="flow", setup=on_row("ssf2tb"))
    shots("full", [], mode="full", setup=on_row("daytona"))
    # O menu do jogo: sem festa (LINK PLAY), com uma festa na sala de espera (JOIN LINK), com uma que ja comecou.
    shots("popup-new", ["b1", "right"], setup=on_row("dirtdvls"))
    shots("popup-join", ["b1", "right"], setup=on_row("daytona"))
    shots("popup-started", ["b1", "right"], setup=on_row("ssf2tb"))
    shots("popup-net", ["b1", "right"], setup=on_row("xmen"))
    shots("list-net", [], setup=on_row("xmen"))
    # A sala: este gabinete abre a festa de verdade, no loopback, e dois outros entram.
    link = felink.Link(HOME, wire=felink.Wire("lo", "127.0.0.1", "255.0.0.0", "127.255.255.255"), ident="me0", name="THIS",
                       ports={"presence": 55501, "party": 55502, "files": 55503})
    link.presence = felink.FakePresence(net["table"])
    guests = []

    def host(fe):
        fe.link = link
        fe.act("right")
        fe.act("b1")

    def join(n):
        def f(fe):
            for i in range(n):
                g = felink.PartyGuest(link.wire, "g%d" % i, "CAB-%d" % i, port=55502)
                g.join("127.0.0.1", "dirtdvls")
                guests.append(g)
            time.sleep(0.5)
        return f

    fe = shots("lobby", ["b1", host, join(1)], setup=on_row("dirtdvls"))
    fe.act("b1")
    fe.draw(time.monotonic())
    fe.pg.image.save(fe.back, os.path.join(OUT, "lobby-started.png"))
    for g in guests:
        g.leave()
    link.leave()
    print("ok")


if __name__ == "__main__":
    main()
