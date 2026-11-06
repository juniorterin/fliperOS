#!/usr/bin/env python3
"""As telas do link para as animacoes do site, do frontend REAL, em cada
gabinete: o 1 escolhe o jogo e abre a festa, espera; cada um dos outros ve o
jogo no alto da lista, entra (JOIN), copia o jogo, e a sala enche ate comecar.
A biblioteca e de mentira (com a arte do gabinete); a festa corre de verdade,
no loopback.

    docker run --rm -v "$PWD:/w:ro" -v OUT:/out -v ARTE:/art:ro -w /w fliperos-guitest \\
        python3 tools/link-tests/link-story.py CENA /out /art

CENA: netplay (Escape Kids, 2 gabinetes de 2 controles), ssf2tb (Super Street
Fighter II: The Tournament Battle, 4 gabinetes) ou daytona (Daytona USA, 4
gabinetes de um jogador). ARTE: a ~/media do gabinete (snap/mame/<set>.png,
logo, box, marquee; snap/model2/... no daytona) dos jogos da cena. Saida, na
resolucao do frontend, um prefixo por gabinete (a, b, c, d):
  a-list-N, a-popup-0/1, a-wait-0     o 1 escolhe e abre a festa
  X-list-0/1/2, X-popup-0/1, X-copy-N  cada um dos outros ve o jogo e entra
  X-join-K                             a sala de cada um depois da entrada K
  X-start-N                            a contagem, a cada 0,5 s
Nao e codigo do frontend: so o ambiente dos prints.
"""
import lzma
import os
import shutil
import sys
import tempfile
import threading
import time
from importlib.machinery import SourceFileLoader
import importlib.util

os.environ["SDL_VIDEODRIVER"] = "dummy"
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUI = os.path.join(ROOT, "fliperos-setup", "gui")
SCENE = sys.argv[1] if len(sys.argv) > 1 else "netplay"
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
ART = sys.argv[3] if len(sys.argv) > 3 else ""
sys.path.insert(0, GUI)

# (set, titulo, ano, fabricante, categoria, jogadores, botoes)
SCENES = {
    "netplay": {
        "game": "esckids", "cabinets": 2, "players": 2, "key": "retroarch/fbneo", "system_name": "FBNeo", "countdown": 16, "path": ["captcomm", "crimfght", "ddsom"], "guest_row": "tmnt",
        "games": [
            ("asterix", "Asterix", "1992", "Konami", "Platform / Fighter Scrolling", "2", "2"),
            ("bucky", "Bucky O'Hare", "1992", "Konami", "Platform / Shooter Scrolling", "4", "2"),
            ("captcomm", "Captain Commando", "1991", "Capcom", "Fighter / Scrolling", "4", "2"),
            ("crimfght", "Crime Fighters", "1989", "Konami", "Fighter / Scrolling", "4", "2"),
            ("ddsom", "Dungeons & Dragons: Shadow over Mystara", "1996", "Capcom", "Fighter / Scrolling", "4", "4"),
            ("esckids", "Escape Kids", "1991", "Konami", "Fighter / Scrolling", "4", "2"),
            ("gijoe", "G.I. Joe", "1992", "Konami", "Shooter / Gallery", "4", "2"),
            ("simpsons", "The Simpsons", "1991", "Konami", "Fighter / Scrolling", "4", "2"),
            ("ssriders", "Sunset Riders", "1991", "Konami", "Shooter / Walking", "4", "2"),
            ("tmnt", "Teenage Mutant Ninja Turtles", "1989", "Konami", "Fighter / Scrolling", "4", "2"),
            ("vendetta", "Vendetta", "1991", "Konami", "Fighter / Scrolling", "4", "3"),
            ("xmen", "X-Men (4 Players)", "1992", "Konami", "Fighter / 2.5D", "4", "3"),
        ]},
    "ssf2tb": {
        "game": "ssf2tb", "cabinets": 4, "players": 2, "key": "mame", "system_name": "MAME", "countdown": 52, "path": ["sfa3", "sf2ce", "ssf2"],
        "guest_row": ["xmvsf", "kof98", "vsav"],
        "games": [
            ("cybots", "Cyberbots: Fullmetal Madness", "1995", "Capcom", "Fighter / Versus", "2", "4"),
            ("dstlk", "Darkstalkers: The Night Warriors", "1994", "Capcom", "Fighter / Versus", "2", "6"),
            ("garou", "Garou: Mark of the Wolves", "1999", "SNK", "Fighter / Versus", "2", "4"),
            ("kof98", "The King of Fighters '98", "1998", "SNK", "Fighter / Versus", "2", "4"),
            ("msh", "Marvel Super Heroes", "1995", "Capcom", "Fighter / Versus", "2", "6"),
            ("mshvsf", "Marvel Super Heroes vs. Street Fighter", "1997", "Capcom", "Fighter / Versus", "2", "6"),
            ("mvsc", "Marvel vs. Capcom", "1998", "Capcom", "Fighter / Versus", "2", "6"),
            ("samsho2", "Samurai Shodown II", "1994", "SNK", "Fighter / Versus", "2", "4"),
            ("sf2ce", "Street Fighter II': Champion Edition", "1992", "Capcom", "Fighter / Versus", "2", "6"),
            ("sfa", "Street Fighter Alpha", "1995", "Capcom", "Fighter / Versus", "2", "6"),
            ("sfa2", "Street Fighter Alpha 2", "1996", "Capcom", "Fighter / Versus", "2", "6"),
            ("sfa3", "Street Fighter Alpha 3", "1998", "Capcom", "Fighter / Versus", "2", "6"),
            ("ssf2", "Super Street Fighter II: The New Challengers", "1993", "Capcom", "Fighter / Versus", "2", "6"),
            ("ssf2tb", "Super Street Fighter II: The Tournament Battle", "1993", "Capcom", "Fighter / Versus", "2", "6"),
            ("ssf2t", "Super Street Fighter II Turbo", "1994", "Capcom", "Fighter / Versus", "2", "6"),
            ("vsav", "Vampire Savior: The Lord of Vampire", "1997", "Capcom", "Fighter / Versus", "2", "6"),
            ("xmcota", "X-Men: Children of the Atom", "1994", "Capcom", "Fighter / Versus", "2", "6"),
            ("xmvsf", "X-Men vs. Street Fighter", "1996", "Capcom", "Fighter / Versus", "2", "6"),
        ]},
    "daytona": {
        "game": "daytona", "cabinets": 4, "players": 1, "key": "model2", "system_name": "Model 2", "art": "model2",
        "countdown": 48, "path": ["manxtt", "indy500", "desert"], "guest_row": ["srallyc", "stcc", "sgt24h"],
        "games": [
            ("daytona", "Daytona USA", "1994", "Sega", "Driving / Race", "1", "4"),
            ("desert", "Desert Tank", "1995", "Sega", "Shooter / Driving", "1", "2"),
            ("indy500", "INDY 500 Twin", "1995", "Sega", "Driving / Race", "1", "4"),
            ("manxtt", "Manx TT Superbike", "1995", "Sega", "Driving / Motorbike", "1", "4"),
            ("motoraid", "Motor Raid", "1997", "Sega", "Driving / Motorbike", "1", "3"),
            ("overrev", "Over Rev", "1997", "Jaleco", "Driving / Race", "1", "4"),
            ("rchase2", "Rail Chase 2", "1994", "Sega", "Shooter / Gallery", "2", "1"),
            ("segawski", "Sega Water Ski", "1997", "Sega", "Sports / Water", "1", "1"),
            ("sgt24h", "Super GT 24h", "1996", "Jaleco", "Driving / Race", "1", "4"),
            ("skisuprg", "Sega Ski Super G", "1996", "Sega", "Sports / Skiing", "1", "1"),
            ("srallyc", "Sega Rally Championship", "1995", "Sega", "Driving / Race", "1", "4"),
            ("stcc", "Sega Touring Car Championship", "1996", "Sega", "Driving / Race", "1", "4"),
            ("topskatr", "Top Skater", "1997", "Sega", "Sports / Skateboarding", "1", "2"),
            ("von", "Cyber Troopers Virtual-On", "1995", "Sega", "Fighter / Versus", "2", "4"),
            ("waverunr", "Wave Runner", "1996", "Sega", "Driving / Boat", "1", "2"),
        ]},
}
S = SCENES[SCENE]
GAME, N, KEY = S["game"], S["cabinets"], S["key"]
SIDES = "abcd"[:N]


def make_home(home):
    folder = os.path.join(home, "roms", *KEY.split("/"))
    os.makedirs(folder, exist_ok=True)
    for name, *_ in S["games"]:
        with open(os.path.join(folder, name + ".zip"), "wb") as f:
            f.write(b"x" * 4096)
        for kind in ("snap", "logo", "box", "marquee"):
            src = os.path.join(ART, kind, S.get("art", "mame"), name + ".png")
            if ART and os.path.isfile(src):
                dst = os.path.join(home, "media", kind, *KEY.split("/"))
                os.makedirs(dst, exist_ok=True)
                shutil.copyfile(src, os.path.join(dst, name + ".png"))
    with lzma.open(os.path.join(home, "fbneo.tsv.xz"), "wt") as f:
        f.writelines("\t%s\t\t\n" % name for name, *_ in S["games"] if SCENE == "netplay")
    return folder


def main():
    homes = {k: tempfile.mkdtemp() for k in SIDES}
    folders = {k: make_home(h) for k, h in homes.items()}
    # Todos os frontends no mesmo processo: o HOME e o do gabinete 1; cada Link
    # tem a sua pasta (a copia dos outros cai na deles).
    os.environ["HOME"] = os.environ["FLIPEROS_HOME"] = homes["a"]
    os.environ["FLIPEROS_FBNEO_INDEX"] = os.path.join(homes["a"], "fbneo.tsv.xz")
    os.environ["FLIPEROS_LINK_NVRAM"] = os.path.join(ROOT, "config", "link-nvram")
    # O core do FBNeo "instalado", com o savestate que o net play pede.
    for sub in ("cores", "info"):
        os.makedirs(os.path.join(homes["a"], "ra", sub), exist_ok=True)
    open(os.path.join(homes["a"], "ra", "cores", "fbneo_libretro.so"), "w").close()
    with open(os.path.join(homes["a"], "ra", "info", "fbneo_libretro.info"), "w") as f:
        f.write('savestate_features = "deterministic"\n')
    os.environ["FLIPEROS_RA_CORES"] = os.path.join(homes["a"], "ra", "cores")
    os.environ["FLIPEROS_RA_INFO"] = os.path.join(homes["a"], "ra", "info")
    import fedata
    import felink

    def library(folder):
        system = {"key": KEY, "folder": folder, "platform": "arcade", "name": S["system_name"], "exe": "/x/fliperos-x11-run",
                  "args": "x [name]", "extensions": [".zip"], "arcade": True}

        class FakeLibrary(fedata.Library):
            def __init__(self):
                self.lock = threading.Lock()
                self.systems = [system]
                self.filters = [fedata.FAVOURITES, {"name": "All Games", "rules": [], "sort_by": "", "reverse": False, "limit": 0}]
                self.info = fedata.web.GameInfo()
                self.cache, self.stamps = {}, {}
                self.refreshing, self.generation = False, 0

            def games(self, category):
                out = [{"Name": n, "Title": t, "Year": y, "Manufacturer": mk, "Category": c, "Players": p,
                        "Control": "joystick (8-way)", "Buttons": b, "_system": system, "file": n + ".zip"}
                       for n, t, y, mk, c, p, b in S["games"]]
                out.sort(key=lambda g: g["Title"].lower())
                return out

            def rom_files(self, game):
                return [os.path.join(folder, game["Name"] + ".zip")]

            def command(self, game):
                return ["/x/fliperos-x11-run", "groovymame", game["Name"]]

            def changed(self):
                return False

            def refresh(self, done=None):
                pass

            def hidden(self):
                return set()

            def favourites(self):
                return set()
        return FakeLibrary

    sys.argv = ["fliperos-frontend"]
    loader = SourceFileLoader("fe", os.path.join(GUI, "fliperos-frontend"))
    spec = importlib.util.spec_from_loader("fe", loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    os.makedirs(OUT, exist_ok=True)
    lo = felink.Wire("lo", "127.0.0.1", "255.0.0.0", "127.255.255.255")
    ports = {"presence": 55521, "party": 55522, "files": 55523}
    links, seen, fes = {}, {}, {}
    for i, side in enumerate(SIDES):
        links[side] = felink.Link(homes[side], wire=lo, ident="cab%d" % (i + 1), name="CABINET-%d" % (i + 1),
                                  ports=dict(ports, presence=55531 + i) if i else dict(ports), local_players=S["players"])
        seen[side] = []                         # a presenca de mentira: o que cada um ve dos outros
        links[side].presence = felink.FakePresence(seen[side])

    def frontend(side):
        fedata.Library = library(folders[side])

        class Args:
            shot = os.path.join(OUT, side)
        fe = m.Frontend(Args)
        fe.overlay = None
        fe.mode = "list"
        fe.link = links[side]
        fe.rebuild()
        return fe

    def save(fe, name, now=None):
        fe.draw(now if now is not None else time.monotonic())
        fe.pg.image.save(fe.back, os.path.join(OUT, name + ".png"))

    def row(fe, name, elsewhere=False):
        fe.cursor = next(i for i, r in enumerate(fe.rows) if r[0]["Name"] == name and (r[2] == "elsewhere") == elsewhere)

    def tick_all():
        for _ in range(10):
            for side in SIDES:
                links[side].tick()
            time.sleep(0.05)

    # O gabinete 1: a lista andando ate o jogo, o menu do jogo, o link.
    fa = fes["a"] = frontend("a")
    for i, name in enumerate(S["path"] + [GAME]):
        row(fa, name)
        save(fa, "a-list-%d" % i)
    fa.act("b1")
    save(fa, "a-popup-0")
    fa.act("right")
    save(fa, "a-popup-1")
    fa.act("b1")                                # abre a festa: a sala, so ele
    save(fa, "a-wait-0")
    lob = links["a"].lobby()
    take = lob["take"] if lob else 1
    # Os outros, um de cada vez: a lista dele, o jogo aparecendo no alto, o JOIN, a copia, a sala.
    joined = [{"v": 1, "id": "cab1", "name": "CABINET-1", "ip": "127.0.0.1", "game": GAME, "system": KEY,
               "link": links["a"].lobby()["profile"]["id"], "party": "cab1", "slot": 1, "take": take,
               "max": lob["max"], "state": "lobby"}]
    rows = S["guest_row"] if isinstance(S["guest_row"], list) else [S["guest_row"]]
    for k, side in enumerate(SIDES[1:]):
        fe = fes[side] = frontend(side)
        row(fe, rows[k % len(rows)])
        save(fe, "%s-list-0" % side)
        seen[side][:] = [dict(r) for r in joined]
        fe.rebuild(keep=rows[k % len(rows)])
        save(fe, "%s-list-1" % side)
        fe.cursor = 0                           # o jogo de quem esta na rede, no alto
        save(fe, "%s-list-2" % side)
        fe.act("b1")
        save(fe, "%s-popup-0" % side)
        fe.act("right")
        save(fe, "%s-popup-1" % side)
        party = fe.link_party(fe.game())
        fe.link_game = fe.game()
        fe.overlay, fe.ov = "transfer", {"party": party, "result": None}
        for i, pct in enumerate((0.15, 0.45, 0.8, 1.0)):
            fe.ov["progress"] = (int(pct * 4096), 4096, os.path.join(folders["a"], GAME + ".zip"))
            save(fe, "%s-copy-%d" % (side, i), time.monotonic() + i * 0.25)
        fe.overlay = None
        ok = links[side].join_party(party, fe.link_profile(fe.game()), KEY, GAME, fe.link_rom(fe.game()))
        print(side, "join", ok, links[side].number, links[side].message)
        fe.overlay, fe.ov = "lobby", {}
        time.sleep(0.6)
        tick_all()
        joined.append(dict(joined[0], id="cab%d" % (k + 2), name="CABINET-%d" % (k + 2), slot=links[side].number,
                           take=links[side].take or 1))
        for s2 in SIDES[:k + 2]:
            save(fes[s2], "%s-join-%d" % (s2, k + 1))
    # A contagem: um comeca sozinho quando a sala enche (o jogo de tamanho fixo); o outro, o anfitriao aperta.
    if not links["a"].lobby()["plan"]:
        fa.act("b1")
    for i in range(S["countdown"]):
        for side in SIDES:
            links[side].tick()
            save(fes[side], "%s-start-%d" % (side, i))
        time.sleep(0.5)
    for side in reversed(SIDES):
        links[side].leave()
    print("ok")


if __name__ == "__main__":
    main()
