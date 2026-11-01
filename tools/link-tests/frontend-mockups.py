#!/usr/bin/env python3
"""Mock-ups of the link and net play screens of the FliperOS frontend.

Draws at the frontend's logical size (320x240) with its font (Press Start 2P,
8 px, no antialias) and palette, and scales 3x to 960x720 like the real
screenshots. The title band is cut from a real frontend screenshot.

    python3 frontend-mockups.py OUT_DIR [REAL_LIST_SCREENSHOT]

These are design sketches for discussion, not frontend code.
"""
import os
import random
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ.get("FE_FONT") or os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "fonts", "PressStart2P-Regular.ttf")
W, H, SCALE = 320, 240, 3

SPACE = (0x0B, 0x0B, 0x12)
BG = (0x28, 0x2A, 0x36)
BG_DEEP = (0x19, 0x1A, 0x21)
LINE = (0x44, 0x47, 0x5A)
COMMENT = (0x62, 0x72, 0xA4)
FG = (0xF8, 0xF8, 0xF2)
GREEN = (0x50, 0xFA, 0x7B)
GREEN_DIM = (0x2E, 0x5E, 0x40)
PINK = (0xFF, 0x79, 0xC6)
CYAN = (0x8B, 0xE9, 0xFD)
YELLOW = (0xF1, 0xFA, 0x8C)
ORANGE = (0xFF, 0xB8, 0x6C)
PURPLE = (0xBD, 0x93, 0xF9)
RED = (0xFF, 0x55, 0x55)
LIST_TEXT = (0x7A, 0x88, 0xC8)


def font():
    return ImageFont.truetype(FONT, 8)


class Canvas:
    def __init__(self, band=None, seed=7):
        self.im = Image.new("RGB", (W, H), SPACE)
        rnd = random.Random(seed)
        d = ImageDraw.Draw(self.im)
        for _ in range(60):
            x, y = rnd.randrange(W), rnd.randrange(H)
            d.point((x, y), fill=rnd.choice([LINE, COMMENT, (0x30, 0x34, 0x4a)]))
        if band is not None:
            self.im.paste(band, (0, 0))
        self.d = ImageDraw.Draw(self.im)
        self.d.fontmode = "1"
        self.f = font()

    def text(self, x, y, s, color=FG):
        self.d.text((x, y), s, font=self.f, fill=color)

    def width(self, s):
        return 8 * len(s)

    def center(self, y, s, color=FG, x0=0, x1=W):
        self.text(x0 + (x1 - x0 - self.width(s)) // 2, y, s, color)

    def box(self, x0, y0, x1, y1, fill=None, outline=None):
        self.d.rectangle([x0, y0, x1, y1], fill=fill, outline=outline)

    def paste_icon(self, icon, x, y):
        self.im.paste(icon, (x, y), icon)

    def save(self, path):
        self.im.resize((W * SCALE, H * SCALE), Image.NEAREST).save(path)


def globe(lit, size=16):
    """A globe made of green lines: outline, a meridian, the equator and two latitudes."""
    c = GREEN if lit else GREEN_DIM
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 15, 15], outline=c)
    d.ellipse([4, 0, 11, 15], outline=c)
    d.line([(0, 8), (15, 8)], fill=c)
    d.line([(2, 4), (13, 4)], fill=c)
    d.line([(2, 12), (13, 12)], fill=c)
    d.line([(7, 0), (7, 15)], fill=c)
    if lit:  # the net: three bright nodes
        for p in ((2, 4), (13, 12), (12, 4)):
            d.point(p, fill=FG)
    if size != 16:
        im = im.resize((size, size), Image.NEAREST)
    return im


def cabinet(lit, w=8, h=12):
    """A small arcade cabinet: lit when a machine is in that slot."""
    c = GREEN if lit else LINE
    screen = CYAN if lit else BG_DEEP
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, w - 1, h - 1], outline=c)
    d.rectangle([1, 1, w - 2, h // 2 - 1], fill=screen)
    d.line([(1, h // 2 + 1), (w - 2, h // 2 + 1)], fill=c)
    d.point((w // 2, h // 2 + 3), fill=c)
    return im


def pads(lit=True):
    """Net play: two controllers joined by a line."""
    c = CYAN if lit else LINE
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 9, 7, 14], outline=c)
    d.point((2, 11), fill=c)
    d.point((5, 12), fill=c)
    d.rectangle([8, 1, 15, 6], outline=c)
    d.point((10, 3), fill=c)
    d.point((13, 4), fill=c)
    d.line([(4, 8), (4, 7), (11, 7)], fill=GREEN if lit else GREEN_DIM)
    return im


def play_icon(color=FG):
    """The play triangle of the solo option."""
    im = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon([(2, 0), (2, 11), (10, 5)], fill=color)
    return im


def slots(cv, x, y, filled, total, w=6, h=9, gap=2):
    for i in range(total):
        cv.paste_icon(cabinet(i < filled, w, h), x + i * (w + gap), y)


def title_band(path):
    if not path or not os.path.exists(path):
        return None
    real = Image.open(path).convert("RGB").resize((W, H), Image.NEAREST)
    return real.crop((0, 0, W, 30))


def row_text(cv, x, y, s, selected=False, color=LIST_TEXT, maxc=21):
    s = s[:maxc]
    if selected:
        cv.box(x - 3, y - 3, x + 8 * maxc + 2, y + 9, fill=(0x2c, 0x2c, 0x3c), outline=PINK)
        color = FG
    cv.text(x, y, s, color)


def list_screen(band):
    cv = Canvas(band)
    cv.text(14, 36, "PLAYING NOW ELSEWHERE", COMMENT)
    y = 48
    for name, n in (("DAYTONA USA", 2), ("SF2 TOURNAMEN", 3)):
        cv.paste_icon(globe(True, 12), 14, y - 2)
        row_text(cv, 30, y, name, color=YELLOW, maxc=13)
        slots(cv, 136, y, n, 4, 5, 8, 1)
        cv.text(162, y, "%d/4" % n, GREEN)
        y += 15
    cv.d.line([(14, y)] + [(190, y)], fill=LINE)
    y += 8
    rows = [("1944: THE LOOP MAST", None), ("3 COUNT BOUT", None), ("AEROFIGHTERS 2", None), ("SCUD RACE", "link"),
            ("SEGA RALLY", "link"), ("X-MEN (6 PLAYERS)", "net"), ("ALIEN STORM", None)]
    for name, kind in rows:
        sel = name == "SCUD RACE"
        if kind == "link":
            cv.paste_icon(globe(False, 12), 14, y - 2)
        elif kind == "net":
            cv.paste_icon(pads(False).resize((12, 12), Image.NEAREST), 14, y - 2)
        row_text(cv, 30, y, name, selected=sel, maxc=19)
        y += 15
    cv.d.line([(194, 34), (194, 214)], fill=PINK)
    cv.box(204, 36, 306, 100, fill=BG_DEEP, outline=PINK)
    cv.center(64, "SCUD RACE", FG, 204, 306)
    cv.center(78, "(ART)", COMMENT, 204, 306)
    cv.text(204, 108, "1996 SEGA", YELLOW)
    cv.paste_icon(globe(False, 12), 204, 122)
    cv.text(220, 124, "LINK 2-8", GREEN)
    cv.text(204, 142, "NOBODY IS", COMMENT)
    cv.text(204, 152, "PLAYING IT", COMMENT)
    cv.text(196, 226, "4/15", COMMENT)
    return cv


def grid_screen(band):
    cv = Canvas(band)
    tiles = [(26, 38), (116, 38), (206, 38), (26, 120), (116, 120), (206, 120)]
    names = ["PUZZLE BOBBLE", "SCUD RACE", "SF2 TOURNAMENT", "ALIEN STORM", "X-MEN 6P", "SEGA RALLY"]
    kinds = [None, "link", "linklive", None, "net", "link"]
    for (x, y), name, kind in zip(tiles, names, kinds):
        cv.box(x, y, x + 80, y + 70, fill=BG_DEEP, outline=LINE)
        cv.center(y + 28, name[:9], COMMENT, x, x + 80)
        if kind in ("link", "linklive"):
            cv.box(x + 2, y + 2, x + 21, y + 21, fill=(0x10, 0x12, 0x18))
            cv.paste_icon(globe(kind == "linklive"), x + 3, y + 3)
        if kind == "net":
            cv.box(x + 2, y + 2, x + 21, y + 21, fill=(0x10, 0x12, 0x18))
            cv.paste_icon(pads(False), x + 3, y + 3)
        if kind == "linklive":
            cv.box(x, y + 56, x + 80, y + 70, fill=(0x10, 0x12, 0x18))
            slots(cv, x + 4, y + 59, 3, 4, 6, 9, 2)
            cv.text(x + 50, y + 60, "3/4", GREEN)
    cv.box(204, 118, 286, 190, outline=PINK)
    cv.text(26, 200, "SF2 TOURNAMENT", YELLOW)
    cv.text(26, 214, "1993 CAPCOM", CYAN)
    cv.paste_icon(globe(True), 150, 210)
    cv.text(170, 214, "3 OF 4 WAITING", GREEN)
    return cv


def options_screen(band, joined):
    cv = Canvas(band)
    cv.center(36, "DAYTONA USA", YELLOW)
    cv.center(48, "1994 SEGA", CYAN)
    cv.box(14, 62, 134, 142, fill=BG_DEEP, outline=PINK)
    cv.center(98, "(ART)", COMMENT, 14, 134)
    cv.text(14, 152, "1 PLAYER", COMMENT)
    cv.text(14, 162, "PER CABINET", COMMENT)
    cv.paste_icon(globe(True, 12), 14, 176)
    cv.text(30, 178, "LINK 2-8", GREEN)
    cv.text(14, 226, "A:SELECT B:BACK", COMMENT)
    cv.box(146, 62, 308, 86, fill=(0x2c, 0x2c, 0x3c), outline=PINK if not joined else LINE)
    cv.paste_icon(play_icon(FG if not joined else LIST_TEXT), 154, 68)
    cv.text(174, 70, "PLAY", FG if not joined else LIST_TEXT)
    cv.text(230, 70, "SOLO", COMMENT)
    y = 94
    if not joined:
        cv.box(146, y, 308, y + 24, fill=BG_DEEP, outline=LINE)
        cv.paste_icon(globe(False), 152, y + 4)
        cv.text(176, y + 8, "LINK PLAY", LIST_TEXT)
        cv.text(150, y + 32, "NOBODY IS PLAYING", COMMENT)
        cv.text(150, y + 44, "YOU BECOME #1", YELLOW)
        cv.text(150, y + 56, "(THE MASTER)", COMMENT)
        for i in range(4):
            cv.paste_icon(cabinet(i == 0, 10, 14), 150 + i * 16, y + 74)
    else:
        cv.box(146, y, 308, y + 24, fill=(0x2c, 0x2c, 0x3c), outline=PINK)
        cv.paste_icon(globe(True), 152, y + 4)
        cv.text(176, y + 8, "JOIN LINK", FG)
        cv.text(150, y + 32, "#1 IS WAITING", GREEN)
        cv.text(150, y + 44, "YOU BECOME #3", YELLOW)
        for i in range(4):
            cv.paste_icon(cabinet(i < 2, 10, 14), 150 + i * 16, y + 62)
        cv.d.rectangle([150 + 2 * 16 - 2, y + 60, 150 + 2 * 16 + 11, y + 78], outline=PINK)
        cv.text(222, y + 66, "2/4", GREEN)
        cv.box(146, y + 86, 308, y + 106, fill=BG_DEEP, outline=LINE)
        cv.text(154, y + 92, "+ NEW LINK", LIST_TEXT)
    return cv


def options_netplay_screen(band):
    """A game with more players than this cabinet has controls: play here, or join a party."""
    cv = Canvas(band)
    cv.center(36, "X-MEN (6 PLAYERS)", YELLOW)
    cv.center(48, "1992 KONAMI", CYAN)
    cv.box(14, 62, 134, 142, fill=BG_DEEP, outline=PINK)
    cv.center(98, "(ART)", COMMENT, 14, 134)
    cv.text(14, 152, "6 PLAYERS", COMMENT)
    cv.text(14, 162, "2 CONTROLS HERE", COMMENT)
    cv.paste_icon(pads(True).resize((12, 12), Image.NEAREST), 14, 176)
    cv.text(30, 178, "NET PLAY", CYAN)
    cv.text(14, 226, "A:SELECT B:BACK", COMMENT)
    cv.box(146, 62, 308, 86, fill=BG_DEEP, outline=LINE)
    cv.paste_icon(play_icon(LIST_TEXT), 154, 68)
    cv.text(174, 70, "PLAY", LIST_TEXT)
    cv.text(230, 70, "SOLO", COMMENT)
    cv.box(146, 94, 308, 118, fill=(0x2c, 0x2c, 0x3c), outline=PINK)
    cv.paste_icon(pads(True), 152, 98)
    cv.text(176, 102, "NET PLAY", FG)
    cv.text(150, 126, "PARTY OF CABINET-1", GREEN)
    cv.text(150, 138, "P1-P2 TAKEN", YELLOW)
    cv.text(150, 148, "P3-P6 FREE", YELLOW)
    cv.box(146, 162, 308, 182, fill=BG_DEEP, outline=LINE)
    cv.text(154, 168, "+ NEW PARTY", LIST_TEXT)
    return cv


def lobby_screen(band, flags, starting=False):
    total = len(flags)
    ready = sum(flags)
    cv = Canvas(band)
    cv.center(36, "SF2 TOURNAMENT BATTLE", YELLOW)
    cv.paste_icon(globe(True, 24), 148, 50)
    cv.center(82, "STARTING..." if starting else "WAITING FOR CABINETS", GREEN if starting else FG)
    names = ["#1", "#2", "YOU #3", "#4"]
    x0 = 28
    for i in range(total):
        x = x0 + i * 66
        lit = flags[i]
        cv.box(x, 100, x + 52, 168, fill=BG_DEEP, outline=GREEN if lit else LINE)
        cv.paste_icon(cabinet(lit, 22, 30), x + 15, 108)
        cv.center(146, names[i], GREEN if lit else LINE, x, x + 52)
        cv.center(158, "READY" if lit else "...", GREEN if lit else LINE, x, x + 52)
    cv.center(180, "%d / %d" % (ready, total), GREEN)
    if starting:
        cv.center(194, "ALL CABINETS ARE HERE", COMMENT)
        cv.center(208, "THE GAME OPENS IN 3", FG)
    else:
        cv.center(194, "STARTS WHEN ALL %d ARE HERE" % total, COMMENT)
        cv.center(208, "NO ONE CAN JOIN AFTER IT STARTS", COMMENT)
    cv.text(14, 226, "B:LEAVE", COMMENT)
    return cv


def netplay_screen(band):
    cv = Canvas(band)
    cv.center(36, "X-MEN (6 PLAYERS)", YELLOW)
    cv.paste_icon(pads(True), 148, 46)
    cv.center(66, "NET PLAY", FG)
    cv.center(80, "THIS GAME HAS 6 PLAYERS.", COMMENT)
    cv.center(90, "THIS CABINET HAS 2 CONTROLS", COMMENT)
    cv.text(26, 104, "PARTY OF CABINET-1", CYAN)
    rows = [("P1", "CABINET-1 (HOST)", True), ("P2", "CABINET-1 (HOST)", True), ("P3", "FREE", False),
            ("P4", "FREE", False), ("P5", "FREE", False), ("P6", "FREE", False)]
    y = 118
    for i, (p, who, taken) in enumerate(rows):
        sel = i in (2, 3)   # two controls here: the guest takes a pair of slots
        cv.box(26, y - 2, 294, y + 10, fill=(0x2c, 0x2c, 0x3c) if sel else BG_DEEP, outline=PINK if sel else LINE)
        cv.text(34, y, p, GREEN if taken else FG)
        cv.text(70, y, who, FG if taken else (YELLOW if sel else COMMENT))
        if sel:
            cv.text(238, y, "< YOU", PINK)
        y += 15
    cv.text(26, 210, "THIS CABINET TAKES 2 SLOTS", COMMENT)
    cv.text(26, 226, "A: JOIN   B: BACK", COMMENT)
    return cv


def transfer_screen(band, pct=62):
    cv = Canvas(band)
    cv.center(36, "DAYTONA USA", YELLOW)
    cv.paste_icon(globe(True, 24), 148, 52)
    cv.center(86, "THIS CABINET DOES NOT HAVE", FG)
    cv.center(98, "THE GAME FILES", FG)
    cv.center(114, "CABINET-1 IS SENDING THEM", GREEN)
    cv.box(34, 138, 286, 154, fill=BG_DEEP, outline=LINE)
    cv.box(36, 140, 36 + int(248 * pct / 100), 152, fill=GREEN)
    cv.center(164, "%d%%   38 OF 61 MB" % pct, FG)
    cv.center(178, "daytona.zip", COMMENT)
    cv.center(190, "model1io.zip", COMMENT)
    cv.center(210, "THE LINK STARTS WHEN IT IS DONE", COMMENT)
    cv.text(22, 226, "B: CANCEL", COMMENT)
    return cv


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    band = title_band(sys.argv[2] if len(sys.argv) > 2 else None)
    os.makedirs(out, exist_ok=True)
    shots = {
        "01-list-link-badges": list_screen(band),
        "02-grid-link-badges": grid_screen(band),
        "03-options-new-link": options_screen(band, joined=False),
        "04-options-join-link": options_screen(band, joined=True),
        "03b-options-netplay": options_netplay_screen(band),
        "05-lobby-waiting": lobby_screen(band, [True, True, True, False]),
        "06-lobby-all-here": lobby_screen(band, [True, True, True, True], starting=True),
        "07-netplay-party": netplay_screen(band),
        "08-rom-transfer": transfer_screen(band),
    }
    for name, cv in shots.items():
        cv.save(os.path.join(out, name + ".png"))
        print(name)


if __name__ == "__main__":
    main()
