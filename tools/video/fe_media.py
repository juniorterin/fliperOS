"""Grava a midia fisica do frontend (os drives de CD/DVD e o OSCR) para o
site: o frontend de verdade, com drives, discos e um OSCR de mentira (as
funcoes de gui/femedia.py trocadas aqui), em tempo virtual a 30 quadros por
segundo. Em PASTA, um WebP animado por cena (media-*.webp), 320x240, para
website/public/screenshots/anim.

    python3 fe_media.py PASTA

Roda no rig.sh (a amostra do gabinete atras do frontend).
"""
import importlib.util
import os
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader

os.environ["SDL_VIDEODRIVER"] = "dummy"
FPS = 30
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
REAL = time.monotonic
T0 = REAL()
VT = [T0]
time.monotonic = lambda: VT[0]

sys.path.insert(0, "/g")   # o python -I do rig.sh nao poe a pasta no caminho
import femedia  # noqa: E402

# ── Os drives, os discos e o OSCR de mentira ──
DEVICES = [
    {"key": "sr0", "kind": "cd", "name": "DRIVE 1", "model": "HL-DT-ST DVDRAM", "dev": "/dev/sr0", "sg": "sg1",
     "state": "disc", "label": "DISC"},
    {"key": "sr1", "kind": "cd", "name": "DRIVE 2", "model": "ASUS BW-16D1HT", "dev": "/dev/sr1", "sg": "sg2",
     "state": "empty", "label": "EMPTY"},
    {"key": "oscr", "kind": "oscr", "name": "OSCR", "model": "CART READER", "dev": "/dev/ttyUSB0", "state": "ready",
     "label": "READY"},
]
DISCS = {
    "/dev/sr0": {"console": "psx", "name": "Sony PlayStation", "title": "CASTLEVANIA - SYMPHONY OF THE NIGHT",
                 "serial": "SLUS-00067"},
    "/dev/sr1": {"console": "segacd", "name": "Sega CD", "title": "SONIC CD", "serial": "MK-4407"},
}
CORE = {"icon": "retroarch", "missing": False}
OPTIONS = {
    "psx": [{"id": "duckstation", "label": "DUCKSTATION", "icon": "duckstation", "folder": "ps1", "core": None},
            dict(CORE, id="retroarch:mednafen_psx_hw", label="BEETLE PSX HW", folder="retroarch/mednafen_psx_hw",
                 core="mednafen_psx_hw"),
            dict(CORE, id="retroarch:mednafen_psx", label="BEETLE PSX", folder="retroarch/mednafen_psx",
                 core="mednafen_psx"),
            dict(CORE, id="retroarch:pcsx_rearmed", label="PCSX REARMED", folder="retroarch/pcsx_rearmed",
                 core="pcsx_rearmed")],
    "segacd": [dict(CORE, id="retroarch:genesis_plus_gx", label="GENESIS PLUS GX",
                    folder="retroarch/genesis_plus_gx", core="genesis_plus_gx")],
    "snes": [dict(CORE, id="retroarch:snes9x", label="SNES9X", folder="retroarch/snes9x", core="snes9x"),
             dict(CORE, id="retroarch:bsnes", label="BSNES", folder="retroarch/bsnes", core="bsnes")],
    "md": [dict(CORE, id="retroarch:genesis_plus_gx", label="GENESIS PLUS GX", folder="retroarch/genesis_plus_gx",
                core="genesis_plus_gx")],
}
CARTS = [{"system": "SNES", "console": "snes", "title": "SUPER MARIO WORLD", "rom": 524288, "save": 2048},
         {"system": "MD", "console": "md", "title": "SONIC THE HEDGEHOG 2", "rom": 1048576, "save": 0}]
OSCR_CARTS = [CARTS]


def later(seconds):
    """Espera seconds do relogio do video (o laco de baixo o anda)."""
    until = VT[0] + seconds
    while VT[0] < until:
        time.sleep(0.003)


def identify(dev):
    later(1.6)
    return dict(DISCS[dev])


def oscr_call(dev, what, system=None):
    later(1.8)
    return {"carts": [dict(c) for c in OSCR_CARTS[0]], "systems": ["SNES", "MD", "N64", "GB", "GBA"]}


femedia.scan = lambda: [dict(d) for d in DEVICES]
femedia.identify = identify
femedia.oscr_call = oscr_call
femedia.emulators = lambda c: [dict(o) for o in OPTIONS[c]]
femedia.pick = lambda c, saved=None: dict(next((o for o in OPTIONS[c] if o["id"] == saved), OPTIONS[c][0]))

sys.argv = ["fliperos-frontend"]
loader = SourceFileLoader("fe", "/g/fliperos-frontend")
spec = importlib.util.spec_from_loader("fe", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class Args:
    shot = None
    keys = ""


fe = m.Frontend(Args())
pg = fe.pg
import theme as T  # noqa: E402
import tiny  # noqa: E402
import widgets as W  # noqa: E402

GAME = {}                  # o jogo aberto (simulado): as linhas e ate quando
RIP = {}                   # o rip (simulado): o comeco, a duracao, o texto


def fake_launch(argv, media=False, game=None):
    """O jogo abre: a tela preta com o emulador e de onde ele le."""
    emu = os.path.basename(argv[3]).replace("_libretro.so", "").upper() if "-L" in argv else argv[1].upper()
    GAME.update(line1=emu, line2=argv[-1].upper(), until=VT[0] + 2.2)


def fake_rip(play=False):
    """O rip ou o dump: a barra anda sozinha, como o femedia.py a mandaria."""
    card = fe.ov
    oscr = card.get("oscr")
    name = card["title"]
    head = "READING THE CARTRIDGE" if play else ("DUMPING" if oscr else "RIPPING")
    dest = "TEMPORARY COPY - NOTHING IS KEPT" if play else "%s/%s" % (card["dest"], name)
    fe.overlay, fe.ov = "mediarip", {"card": card, "proc": None, "head": head, "title": name, "result": None,
                                     "error": "", "progress": (0, 100, "STARTING"), "dest": dest, "oscr": oscr,
                                     "play": play}
    size = 512 if oscr else 642
    RIP.update(start=VT[0], dur=2.4 if play else 4.5, oscr=oscr, size=size,
               path="/home/fliperos/.cache/fliperos/oscr/smw.sfc" if play else "/r/x")


fe.launch = fake_launch
fe.media_rip = fake_rip


def encoder(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", "320x240", "-r", str(FPS), "-i", "-", "-c:v", "libwebp_anim", "-lossless", "0",
                             "-quality", "85", "-loop", "0", path], stdin=subprocess.PIPE)


OUTS = []


def advance(data):
    for enc in OUTS:
        enc.stdin.write(data)
    VT[0] += 1 / FPS
    late = T0 + (VT[0] - T0) - REAL()
    if late > 0:
        time.sleep(late)


def game_frame():
    back = pg.Surface((320, 240))
    back.fill((0, 0, 0))
    tiny.centered(back, GAME["line1"], T.FG, 160, 106)
    tiny.centered(back, GAME["line2"], T.CYAN, 160, 116)
    tiny.centered(back, "THE GAME RUNS HERE", T.COMMENT, 160, 132)
    return back


def run(seconds):
    for _ in range(round(seconds * FPS)):
        now = VT[0]
        if RIP and fe.overlay == "mediarip":
            p = min(1.0, (now - RIP["start"]) / RIP["dur"])
            if RIP["oscr"]:
                text = "ROM %d OF %d KB" % (round(RIP["size"] * p), RIP["size"])
            else:
                text = "READING %d OF %d MB" % (round(RIP["size"] * min(1, p / 0.85)), RIP["size"])
                if p > 0.85:
                    text = "COMPRESSING (CHD)"
            fe.ov["progress"] = (round(p * 100), 100, text)
            if p >= 1:
                fe.ov["path"], fe.ov["result"] = RIP["path"], "ok"
                RIP.clear()
        fe.tick(now)
        fe.media_tick(now)
        if fe.lib.generation != fe.generation:
            fe.generation = fe.lib.generation
            fe.cats = fe.lib.categories()
            fe.rebuild()
        while fe.dirty:
            fe.dirty.pop()
        fe.prefetch()
        if GAME and now < GAME["until"]:
            advance(pg.image.tostring(game_frame(), "RGB"))
            continue
        GAME.clear()
        fe.draw(now)
        advance(pg.image.tostring(fe.back, "RGB"))


def key(a, wait=0.5):
    fe.act(a)
    run(wait)


def reset():
    fe.overlay, fe.ov = None, {}
    fe.picking, fe.pick, fe.strip, fe.boot = False, 0, None, None
    fe.ribbon_until = 0
    fe.devices = femedia.scan()
    fe.media_emus = {}
    fe.toast = None


def scene(name, fn):
    reset()
    enc = encoder(os.path.join(OUT, "media-%s.webp" % name))
    OUTS.append(enc)
    fn()
    OUTS.remove(enc)
    enc.stdin.close()
    enc.wait()
    print(name, flush=True)


def disc():
    # A tira, a seta, a fileira; o disco lido; RetroArch > o core; jogar.
    run(1.0)
    key("right", 0.35)
    key("down", 1.0)
    key("b1", 3.4)
    key("right", 0.7)
    key("b1", 1.0)
    key("down", 0.7)
    key("b1", 1.0)
    key("down", 0.6)
    key("b1", 1.6)
    key("left", 0.7)
    key("b1", 3.4)
    run(0.8)


def rip():
    run(0.4)
    key("right", 0.35)
    key("down", 0.6)
    key("b1", 2.6)
    key("right", 0.5)
    key("right", 1.0)
    key("b1", 5.0)
    run(2.4)


def onecore():
    DEVICES[1].update(state="disc", label="DISC")
    run(0.4)
    key("right", 0.35)
    key("down", 0.5)
    key("right", 0.8)
    key("b1", 2.8)
    key("right", 0.7)
    key("b1", 1.2)
    key("b1", 2.4)
    run(0.4)
    DEVICES[1].update(state="empty", label="EMPTY")


def oscr():
    run(0.4)
    key("right", 0.35)
    key("down", 0.4)
    key("right", 0.4)
    key("right", 0.8)
    key("b1", 3.0)
    key("right", 0.8)
    key("left", 0.8)
    key("b1", 1.6)
    key("b1", 3.0)
    run(2.6)


def boot_disc():
    DEVICES[0].update(state="empty", label="EMPTY")
    fe.devices = femedia.scan()
    fe.boot = "sr0"
    fe.overlay, fe.ov = "medianone", fe.none_ov()
    run(4.5)
    DEVICES[0].update(state="disc", label="DISC")
    fe.devices = femedia.scan()
    run(4.6)


def boot_cart():
    fe.boot = "oscr"
    fe.overlay, fe.ov = "medianone", fe.none_ov()
    OSCR_CARTS[0] = CARTS[:1]
    run(4.0)
    key("b1", 4.6)
    OSCR_CARTS[0] = CARTS


def setup():
    """Setup > Games > Frontend > Boot from media, no Setup grafico."""
    import background
    bg = background.pick("stars", seed=3)
    tile = {"physical": lambda s, x, y, sc: s.blit(T.icon("physical", sc), (x, y))}
    entries = [("fliperos", "FliperOS frontend", "FliperOS's own game list, in the menu's look."),
               ("attractplus", "Attract-Mode Plus", "The Attract-Mode Plus frontend."),
               ("emulationstation", "EmulationStation", "The EmulationStation Desktop Edition frontend."),
               ("physical", "Boot from media: Off", "Opens on the disc in a drive, or the cartridge in the OSCR."),
               ("return", "Return", "Back.")]
    text = "Choose what starts when the computer turns on. Now: FliperOS frontend."
    shown = [W.Menu("Frontend", entries, "fliperos", text, tiles=tile)]
    start = VT[0]

    def frames(seconds):
        for _ in range(round(seconds * FPS)):
            back = pg.Surface((320, 240))
            bg.draw(back, VT[0] - start)
            ui = pg.Surface((320, 240), pg.SRCALPHA)
            shown[0].draw(ui, {"now": VT[0] - start, "status": ""})
            back.blit(ui, (0, 0))
            advance(pg.image.tostring(back, "RGB"))
    frames(1.2)
    for _ in range(3):
        shown[0].key("right")
        frames(0.6)
    frames(1.0)
    radio = W.Menu("Boot from media", [("off", "Off"), ("sr0", "Drive 1 - HL-DT-ST DVDRAM (sr0)"),
                                       ("sr1", "Drive 2 - ASUS BW-16D1HT (sr1)"),
                                       ("oscr", "Cartridge reader (OSCR)")], "off",
                   "The FliperOS frontend opens on the disc in this drive, or the cartridge in the OSCR. With none, "
                   "the screen asks for one; Button 2 goes to the game list.", mode="radio", marked={"off"})
    shown[0] = radio
    frames(1.4)
    radio.key("down")
    frames(0.7)
    radio.marked = {"sr0"}
    frames(1.2)
    entries[3] = ("physical", "Boot from media: Drive 1", entries[3][2])
    shown[0] = W.Menu("Frontend", entries, "physical", text, tiles=tile)
    frames(2.0)


# A biblioteca carregando, sem gravar.
fe.overlay = None
run(4.0)
for name, fn in (("disc", disc), ("rip", rip), ("onecore", onecore), ("oscr", oscr), ("boot-disc", boot_disc),
                 ("boot-cart", boot_cart), ("setup", setup)):
    scene(name, fn)
fe.player.stop()
fe.grid.stop()
os._exit(0)
