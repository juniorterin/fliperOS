#!/usr/bin/env python3
"""Real screenshots of the Matchmaker (fliperos-setup/gui/fliperos-matchmaker):
the program itself, drawn with a fake library (a few arcade games, with the
snaps and logos of ART_DIR when given) and a fake online session (the counts
and a lobby as the server sends them). PNGs at 3x, nearest, like the mockups.

    docker run --rm -v "$PWD:/w" -v ART:/art -w /w fliperos-guitest \\
        python3 tools/matchmaker/shots.py OUT_DIR [/art]
    docker run --rm -v "$PWD:/w" -w /w fliperos-tests-pil \\
        python3 tools/matchmaker/shots.py --gif OUT_DIR     # the page switch frames -> GIF

ART_DIR holds snap_<system>_<name>.png and logo_<system>_<name>.png.
"""
import copy
import importlib.machinery
import importlib.util
import os
import sys
import tempfile
import threading
import types

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
GUI = os.path.join(ROOT, "fliperos-setup", "gui")
SCALE = 3
STEP = 1 / 30                 # the GIF's frame time

GAMES = {
    "mame": [
        ("sf2ce", "Street Fighter II': Champion Edition (World 920513)", "1992", "Capcom", "2"),
        ("ssf2t", "Super Street Fighter II Turbo (World 940223)", "1994", "Capcom", "2"),
        ("kof98", "The King of Fighters '98 - The Slugfest", "1998", "SNK", "2"),
        ("sfiii3nr1", "Street Fighter III 3rd Strike: Fight for the Future", "1999", "Capcom", "2"),
        ("garou", "Garou - Mark of the Wolves (NGM-2530)", "1999", "SNK", "2"),
        ("samsho2", "Samurai Shodown II / Shin Samurai Spirits", "1994", "SNK", "2"),
        ("xmvsf", "X-Men Vs. Street Fighter (Euro 961004)", "1996", "Capcom", "2"),
        ("3countb", "3 Count Bout / Fire Suplex (NGM-043)", "1993", "SNK", "2"),
        ("aof", "Art of Fighting / Ryuuko no Ken", "1992", "SNK", "2"),
        ("1944", "1944: The Loop Master (USA 000620)", "2000", "Capcom", "2"),
        ("xmen", "X-Men (4 Players ver EAA)", "1992", "Konami", "4"),
    ],
    "naomi": [("mvsc2", "Marvel Vs. Capcom 2 New Age of Heroes", "2000", "Capcom", "2")],
    "atomiswave": [("kofnw", "The King of Fighters Neowave", "2004", "SNK Playmore", "2")],
    "retroarch/fbneo": [
        ("sf2ce", "Street Fighter II': Champion Edition (World 920513)", "1992", "Capcom", "2"),
        ("kof98", "The King of Fighters '98 - The Slugfest", "1998", "SNK", "2"),
    ],
}
SYSTEMS = [
    {"key": "mame", "name": "Arcade (MAME)", "exe": "/usr/local/bin/fliperos-kms-run", "args": "groovymame [name]"},
    {"key": "naomi", "name": "Sega Naomi", "exe": "/usr/local/bin/fliperos-kms-run", "args": "flycast [romfilename]"},
    {"key": "atomiswave", "name": "Sammy Atomiswave", "exe": "/usr/local/bin/fliperos-kms-run",
     "args": "flycast [romfilename]"},
    {"key": "retroarch/fbneo", "name": "FinalBurn Neo", "exe": "/usr/local/bin/fliperos-kms-run",
     "args": "retroarch -L fbneo"},
    {"key": "model2", "name": "Sega Model 2", "exe": "/usr/local/bin/fliperos-x11-run", "args": "fliperos-model2"},
]
COUNTS = {
    "mame:sf2ce": {"players": 8, "looking": 3}, "mame:kof98": {"players": 3, "looking": 1},
    "mame:xmen": {"players": 3, "looking": 0}, "mame:rbff2": {"players": 2, "looking": 1},
    "flycast:mvsc2": {"players": 4, "looking": 2},
}
ME = {"id": 99, "nick": "BIGBLUE", "tag": "x1y2"}
ROOM = [
    {"id": 1, "nick": "MANGO", "tag": "a7k2", "state": "looking", "conn": "cable", "rtt": 28},
    {"id": 2, "nick": "TAPIR", "tag": "k8z1", "state": "looking", "conn": "wifi", "rtt": 75},
    {"id": 3, "nick": "ZEBRA", "tag": "5vw0", "state": "looking", "conn": "cable", "rtt": 96},
    {"id": 4, "nick": "KIWI", "tag": "0f3d", "state": "playing", "conn": "wifi", "rtt": 64, "group": "m1",
     "kind": "match", "score": "2-1"},
    {"id": 5, "nick": "LYNX", "tag": "9q2m", "state": "playing", "conn": "cable", "rtt": 70, "group": "m1",
     "kind": "match", "score": "2-1"},
    {"id": 6, "nick": "OTTER", "tag": "b52c", "state": "party", "conn": "cable", "rtt": 40, "group": "p1",
     "kind": "party", "score": "2/4"},
    {"id": 7, "nick": "GUAVA", "tag": "3mxp", "state": "download", "conn": "wifi", "rtt": 110, "group": "p1",
     "kind": "party", "pct": 45},
    dict(ME, state="idle", conn="cable", rtt=31),
]


class FakeLibrary:
    def __init__(self, art):
        self.art = art
        self.systems = SYSTEMS

    def games(self, system):
        out = []
        for name, title, year, maker, players in GAMES.get(system["key"], []):
            out.append({"Name": name, "Title": title, "Year": year, "Manufacturer": maker, "Players": players,
                        "Category": "Fighter / Versus", "Control": "8-way Joystick", "Buttons": "6",
                        "_system": system})
        return out

    def media(self, game, kind):
        if not self.art:
            return None
        kind = {"snap": "snap", "box": "snap", "logo": "logo"}.get(kind)
        system = game["_system"]["key"].split("/")[-1]
        for sys_key in (system, "mame"):
            path = os.path.join(self.art, "%s_%s_%s.png" % (kind, sys_key, game["Name"]))
            if kind and os.path.isfile(path):
                return path
        return None

    def hidden(self):
        return set()


class FakeOnline:
    """The session as feonline.Online shows it to the program."""

    def __init__(self, status="online"):
        self.state = {"status": status, "error": None, "me": dict(ME), "profile": None, "verified": None,
                      "counts": COUNTS, "rooms": {}, "rtt": 31}
        self.changed = threading.Event()
        self.sent = []

    def snapshot(self):
        return copy.deepcopy(self.state)

    def presence(self, **fields):
        self.sent.append(("presence", fields))

    def watch(self, game):
        self.sent.append(("watch", game))
        if game:
            self.state["rooms"][game] = ROOM

    def start(self):
        pass

    def stop(self):
        pass


def load_program():
    path = os.path.join(GUI, "fliperos-matchmaker")
    loader = importlib.machinery.SourceFileLoader("matchmaker_program", path)
    spec = importlib.util.spec_from_loader("matchmaker_program", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class Clock:
    """The program's clock, moved by hand (the GIF's frames)."""

    def __init__(self):
        self.t = 1000.0

    def monotonic(self):
        return self.t


def shots(out, art):
    os.environ["HOME"] = tempfile.mkdtemp()          # the program's matchmaker.json goes there
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    sys.path.insert(0, GUI)
    prog = load_program()
    import pygame
    os.makedirs(out, exist_ok=True)

    def make(check="ok", status="online", shot=True):
        online = FakeOnline(status)
        mm = prog.Matchmaker(types.SimpleNamespace(shot="x" if shot else None), library=FakeLibrary(art),
                             online=online, check=lambda: check, netplay_core=lambda k: k == "retroarch/fbneo",
                             nick="BIGBLUE")
        return mm, online

    def save(mm, name, now=None):
        mm.draw(now if now is not None else prog.time.monotonic())
        img = pygame.transform.scale(mm.back, (mm.back.get_width() * SCALE, mm.back.get_height() * SCALE))
        pygame.image.save(img, os.path.join(out, name + ".png"))
        print(name)

    def cursor_on(mm, test):
        mm.cursor = next(i for i, r in enumerate(mm.rows) if test(r))

    mm, online = make()
    mm.screen = "checking"
    save(mm, "01-checking")
    mm.screen = "home"
    mm.rebuild()
    cursor_on(mm, lambda r: r.get("id") == "mame:sf2ce" and r["kind"] == "online")
    save(mm, "02-home")
    cursor_on(mm, lambda r: r.get("id") == "mame:rbff2")
    save(mm, "03-home-not-on-this-cabinet")
    cursor_on(mm, lambda r: r.get("id") == "mame:samsho2")
    save(mm, "04-home-nobody")
    cursor_on(mm, lambda r: r.get("id") == "mame:sf2ce" and r["kind"] == "online")
    mm.accept()
    assert ("watch", "mame:sf2ce") in online.sent, online.sent
    cursor_on(mm, lambda r: r["kind"] == "player" and r["player"]["nick"] == "KIWI")
    save(mm, "05-lobby-playing")
    cursor_on(mm, lambda r: r["kind"] == "player" and r["player"]["nick"] == "GUAVA")
    save(mm, "06-lobby-downloading")
    cursor_on(mm, lambda r: r["kind"] == "player" and r["player"]["nick"] == "MANGO")
    save(mm, "07-lobby-looking")
    mm.act("b2")
    assert mm.screen == "home" and mm.rows[mm.cursor].get("id") == "mame:sf2ce"
    mm.switch_page(1)
    save(mm, "08-page-switch-ribbon")
    mm.pick_page(now=True)
    mm.ribbon_until = 0
    cursor_on(mm, lambda r: r.get("id") == "flycast:mvsc2" and r["kind"] == "online")
    save(mm, "09-home-flycast")
    for i, (check, status) in enumerate((("internet", "online"), ("server", "online"))):
        mm, _ = make(check)
        mm.offline_choice = i
        save(mm, "%02d-offline-%s" % (10 + i, check))
    mm, online = make()
    online.state["status"] = "refused"
    online.changed.set()
    mm.tick(prog.time.monotonic())
    save(mm, "12-offline-refused")
    mm, online = make()
    online.state["status"] = "offline"
    online.changed.set()
    mm.tick(prog.time.monotonic())
    save(mm, "13-home-reconnecting")
    switch_frames(prog, make, out)


def switch_frames(prog, make, out):
    """The page switch as on the cabinet: right on the GAME LIST strip, the
    stop (PICK_WAIT), the strip fading and the double door, at 30 fps."""
    import pygame
    clock = Clock()
    real_time = prog.time
    prog.time = clock
    try:
        prog.CONFIG = os.path.join(tempfile.mkdtemp(), "matchmaker.json")     # opens on GROOVYMAME
        mm, _ = make(shot=False)
        mm.worker.join()
        mm.tick(clock.t)                     # the check is over: the home
        mm.cursor = next(i for i, r in enumerate(mm.rows) if r.get("id") == "mame:sf2ce")
        frames = os.path.join(out, "switch-frames")
        os.makedirs(frames, exist_ok=True)
        n = 0

        def frame():
            nonlocal n
            mm.tick(clock.t)
            mm.draw(clock.t)
            img = pygame.transform.scale(mm.back, (mm.back.get_width() * SCALE, mm.back.get_height() * SCALE))
            pygame.image.save(img, os.path.join(frames, "%03d.png" % n))
            n += 1
            clock.t += STEP
        for _ in range(10):
            frame()
        mm.act("right")
        total = prog.PICK_WAIT + prog.RIBBON_HOLD + prog.RIBBON_FADE + 0.85 + 0.3
        for _ in range(round(total / STEP)):
            frame()
        print("switch-frames:", n)
    finally:
        prog.time = real_time


def make_gif(out):
    from PIL import Image
    frames = os.path.join(out, "switch-frames")
    names = sorted(f for f in os.listdir(frames) if f.endswith(".png"))
    images = [Image.open(os.path.join(frames, f)).convert("RGB") for f in names]
    gif = os.path.join(out, "14-page-switch.gif")
    images[0].save(gif, save_all=True, append_images=images[1:], duration=round(STEP * 1000), loop=0,
                   optimize=False)
    # A sheet of every third frame, 6 across, at 1x.
    pick = images[::3]
    w, h = images[0].width // SCALE, images[0].height // SCALE
    cols = 6
    sheet = Image.new("RGB", (cols * w, ((len(pick) + cols - 1) // cols) * h))
    for i, im in enumerate(pick):
        sheet.paste(im.resize((w, h), Image.NEAREST), ((i % cols) * w, (i // cols) * h))
    sheet.save(os.path.join(out, "14-page-switch-frames.png"))
    print(gif, len(images), "frames")


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--gif":
        make_gif(sys.argv[2])
        return 0
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    shots(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
