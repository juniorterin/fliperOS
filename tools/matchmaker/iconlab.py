#!/usr/bin/env python3
"""Every icon of the Matchmaker as a 16-bit sprite, ten options each, for the
user to choose (the fist bump is fists.py, option 3 chosen).

Every shape is a layer with its own dark outline, a bevel (light on the top
left edge, shade on the bottom right), four tones and a shine, like a SNES /
Mega Drive sprite. Icons are drawn at 32x32.

    python3 iconlab.py OUT_DIR      # one sheet per icon, and all.png
"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import icons16  # noqa: E402
from fists import MATERIALS, outline_all  # noqa: E402

RAMPS = dict(MATERIALS)
RAMPS.update({
    # outline, shadow, base, light, highlight
    "green": ((0x0C, 0x34, 0x18), (0x20, 0x90, 0x40), (0x50, 0xFA, 0x7B), (0xA0, 0xFF, 0xB8), (0xF0, 0xFF, 0xF4)),
    "orange": ((0x4A, 0x24, 0x08), (0xC8, 0x70, 0x20), (0xFF, 0xB8, 0x6C), (0xFF, 0xD8, 0xA8), (0xFF, 0xF4, 0xE4)),
    "gold": ((0x4A, 0x30, 0x04), (0xC0, 0x8A, 0x10), (0xF8, 0xC8, 0x30), (0xFF, 0xE8, 0x80), (0xFF, 0xFC, 0xE0)),
    "gray": ((0x1E, 0x20, 0x2A), (0x50, 0x54, 0x68), (0x80, 0x86, 0x9C), (0xB0, 0xB6, 0xC8), (0xEC, 0xEE, 0xF4)),
    "dark": ((0x08, 0x08, 0x10), (0x16, 0x16, 0x22), (0x2A, 0x2A, 0x3A), (0x44, 0x46, 0x5A), (0x80, 0x84, 0xA0)),
    "brown": ((0x2A, 0x14, 0x08), (0x6A, 0x3A, 0x18), (0x9C, 0x60, 0x30), (0xC8, 0x90, 0x58), (0xEC, 0xC8, 0x98)),
    "board": ((0x06, 0x22, 0x10), (0x10, 0x50, 0x28), (0x1C, 0x7C, 0x40), (0x3C, 0xA8, 0x60), (0x9C, 0xE0, 0xB0)),
    "ocean": icons16.OCEAN,
})
YELLOW, WHITE, RED = (0xF1, 0xFA, 0x8C), (0xFF, 0xFF, 0xFF), (0xFF, 0x55, 0x55)
SPACE = (0x0B, 0x0B, 0x12)
S = 32


def shade(mask, ramp, radial=False, outline=True, shine=True):
    """A layer from a shape: four tones lit from the top left, a bevel, a shine, the outline."""
    o, sh, b, l, h = RAMPS[ramp]
    w, hh = mask.size
    m = mask.load()
    box = mask.getbbox()
    out = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    if not box:
        return out
    x0, y0, x1, y1 = box
    px = out.load()

    def inside(x, y):
        return 0 <= x < w and 0 <= y < hh and m[x, y]

    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rad = max(1, max(x1 - x0, y1 - y0) / 2)
    lx, ly = cx - rad * 0.45, cy - rad * 0.45
    for y in range(y0, y1):
        for x in range(x0, x1):
            if not m[x, y]:
                continue
            if radial:
                k = math.hypot(x + 0.5 - lx, y + 0.5 - ly) / (2 * rad)
                c = h if k < 0.10 else l if k < 0.32 else b if k < 0.66 else sh
            else:
                t = (y - y0) / max(1, y1 - y0 - 1)
                c = l if t < 0.28 else sh if t > 0.74 else b
                if not inside(x - 1, y - 1):
                    c = l if c != l else h
                elif not inside(x + 1, y + 1):
                    c = sh
            px[x, y] = c + (255,)
    if shine and not radial and x1 - x0 > 6:
        for x in range(x0 + 2, x0 + 2 + max(1, (x1 - x0) // 4)):
            if inside(x, y0 + 1):
                px[x, y0 + 1] = h + (255,)
    if outline:
        outline_all(out, o)
    return out


class Icon:
    def __init__(self, s=S):
        self.s = s
        self.im = Image.new("RGBA", (s, s), (0, 0, 0, 0))

    def layer(self, draw, ramp, **kw):
        m = Image.new("L", (self.s, self.s), 0)
        draw(ImageDraw.Draw(m))
        self.im.alpha_composite(shade(m, ramp, **kw))
        return self

    def ellipse(self, box, ramp, **kw):
        return self.layer(lambda d: d.ellipse(box, fill=255), ramp, **kw)

    def ball(self, box, ramp, **kw):
        return self.layer(lambda d: d.ellipse(box, fill=255), ramp, radial=True, **kw)

    def rrect(self, box, r, ramp, **kw):
        return self.layer(lambda d: d.rounded_rectangle(box, r, fill=255), ramp, **kw)

    def poly(self, pts, ramp, **kw):
        return self.layer(lambda d: d.polygon(pts, fill=255), ramp, **kw)

    def arc(self, box, a0, a1, width, ramp, **kw):
        return self.layer(lambda d: d.arc(box, a0, a1, fill=255, width=width), ramp, **kw)

    def line(self, pts, width, ramp, **kw):
        return self.layer(lambda d: d.line(pts, fill=255, width=width), ramp, **kw)

    def flat(self, fn):
        fn(ImageDraw.Draw(self.im))
        return self

    def paste(self, other, xy=(0, 0)):
        self.im.alpha_composite(other, xy)
        return self


def star_pts(cx, cy, r, k=0.45, n=5, rot=-90):
    pts = []
    for i in range(2 * n):
        a = math.radians(rot + i * 180 / n)
        rr = r if i % 2 == 0 else r * k
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def heart_layer(I, box, ramp):
    x0, y0, x1, y1 = box
    w = x1 - x0
    r = w // 4

    def draw(d):
        d.ellipse([x0, y0, x0 + 2 * r + 1, y0 + 2 * r + 1], fill=255)
        d.ellipse([x1 - 2 * r - 1, y0, x1, y0 + 2 * r + 1], fill=255)
        d.polygon([(x0, y0 + r + 1), (x1, y0 + r + 1), ((x0 + x1) / 2, y1)], fill=255)
    return I.layer(draw, ramp)


def person(I, x, y, ramp, k=1.0):
    """A person: a round head and rounded shoulders."""
    hr = round(5 * k)
    I.rrect((x - round(8 * k), y + round(9 * k), x + round(8 * k), y + round(20 * k)), round(6 * k), ramp)
    I.ball((x - hr, y, x + hr, y + 2 * hr), ramp)


def plus_badge(I, color="green"):
    I.rrect((20, 20, 31, 31), 3, color)
    I.flat(lambda d: (d.rectangle([24, 22, 26, 29], fill=WHITE + (255,)), d.rectangle([22, 24, 29, 26], fill=WHITE + (255,))))


def arrow_down(I, x, y, w, h, ramp):
    s = w // 3
    I.poly([(x + s, y), (x + w - s, y), (x + w - s, y + h // 2), (x + w, y + h // 2), (x + w // 2, y + h),
            (x, y + h // 2), (x + s, y + h // 2)], ramp)


def arcs(I, cx, cy, radii, a0, a1, width, ramp):
    for r in radii:
        I.arc((cx - r, cy - r, cx + r, cy + r), a0, a1, width, ramp)


# ------------------------------------------------------------------ ONLINE

def online_options():
    def o5():
        I = Icon()
        I.arc((2, 2, 29, 29), 0, 360, 3, "cyan")
        I.arc((9, 2, 22, 29), 0, 360, 2, "cyan")
        I.line([(3, 15), (28, 15)], 2, "cyan")
        I.line([(5, 8), (26, 8)], 2, "cyan")
        I.line([(5, 22), (26, 22)], 2, "cyan")
        return I.im

    def o6():
        I = Icon()
        I.arc((0, 11, 31, 23), 180, 360, 3, "gold", shine=False)
        I.ball((7, 4, 24, 27), "pink")
        I.arc((0, 11, 31, 23), 0, 180, 3, "gold", shine=False)
        return I.im

    def o7():
        I = Icon()
        I.rrect((5, 1, 26, 31), 3, "purple")
        I.rrect((8, 4, 23, 17), 2, "dark")
        I.paste(icons16.sphere(12), (10, 5))
        I.rrect((7, 20, 24, 24), 1, "pink")
        I.flat(lambda d: (d.point((11, 22), fill=YELLOW + (255,)), d.point((19, 22), fill=(0x8B, 0xE9, 0xFD, 255))))
        return I.im

    def o8():
        I = Icon()
        I.poly([(4, 6), (22, 24), (10, 26), (3, 18)], "gray")
        I.line([(12, 17), (19, 10)], 2, "gray")
        I.ball((18, 7, 22, 11), "red")
        I.rrect((8, 26, 20, 30), 1, "dark")
        arcs(I, 20, 9, (5, 9), 280, 360, 2, "gold")
        return I.im

    def o9():
        I = Icon()
        I.poly([(16, 6), (22, 30), (10, 30)], "gray")
        I.flat(lambda d: (d.line([(13, 18), (19, 18)], fill=RAMPS["gray"][0] + (255,)),
                          d.line([(12, 24), (20, 24)], fill=RAMPS["gray"][0] + (255,))))
        I.ball((13, 2, 19, 8), "red")
        arcs(I, 16, 5, (8, 13), 200, 250, 2, "cyan")
        arcs(I, 16, 5, (8, 13), 290, 340, 2, "cyan")
        return I.im

    def o10():
        I = Icon()
        I.rrect((4, 22, 27, 30), 3, "red")
        I.line([(16, 24), (16, 13)], 3, "gray")
        I.ball((11, 6, 21, 16), "red")
        arcs(I, 16, 11, (10, 14), 210, 330, 2, "gold")
        return I.im

    def plain():
        I = Icon()
        I.paste(icons16.sphere(28), (2, 2))
        return I.im

    return [("EARTH ORBIT", lambda: icons16.globe(S)), ("EARTH", plain), ("EARTH WAVES", lambda: icons16.globe_signal(S)),
            ("CABINETS", lambda: icons16.cabinets_link(S)), ("WIREFRAME", o5), ("RINGED PLANET", o6),
            ("CABINET GLOBE", o7), ("DISH", o8), ("TOWER", o9), ("STICK WAVES", o10)]


# ------------------------------------------------------------------ LOBBY

def lobby_options():
    def l1():
        I = Icon()
        person(I, 21, 5, "cyan", 0.85)
        person(I, 11, 7, "pink", 0.95)
        return I.im

    def l2():
        I = Icon()
        person(I, 7, 6, "purple", 0.7)
        person(I, 25, 6, "purple", 0.7)
        person(I, 16, 8, "pink", 0.9)
        return I.im

    def l3():
        I = Icon()
        person(I, 7, 9, "pink", 0.75)
        person(I, 25, 9, "cyan", 0.75)
        I.poly([(17, 2), (12, 15), (16, 15), (13, 26), (21, 11), (17, 11), (20, 2)], "gold")
        return I.im

    def l4():
        I = Icon()
        for x, y, r in ((6, 4, "purple"), (16, 2, "cyan"), (26, 4, "purple"), (11, 13, "pink"), (21, 13, "gold")):
            I.ball((x - 5, y, x + 5, y + 10), r)
        I.rrect((2, 24, 29, 31), 3, "purple")
        return I.im

    def l5():
        I = Icon()
        I.poly([(1, 18), (16, 11), (31, 18), (16, 26)], "blue")
        for x, y in ((1, 18), (16, 11), (31, 18), (16, 26)):
            I.rrect((x - 1, y - 9, x + 1, y), 0, "white", shine=False)
        I.line([(1, 12), (16, 5), (31, 12)], 1, "red", outline=False)
        I.line([(1, 12), (16, 19), (31, 12)], 1, "red", outline=False)
        return I.im

    def l6():
        I = Icon()
        I.rrect((6, 2, 25, 31), 2, "brown")
        I.rrect((9, 5, 22, 31), 1, "gold", shine=False)
        I.poly([(9, 5), (17, 8), (17, 31), (9, 31)], "brown")
        I.ball((14, 17, 16, 19), "gold")
        return I.im

    def l7():
        I = Icon()
        I.rrect((3, 2, 28, 30), 3, "white")
        for i, c in enumerate(("pink", "cyan", "gold")):
            y = 6 + i * 8
            I.ball((6, y, 11, y + 5), c)
            I.rrect((14, y + 1, 25, y + 4), 1, "gray", shine=False)
        return I.im

    def l8():
        I = Icon()
        I.poly([(1, 14), (16, 2), (31, 14)], "red")
        I.rrect((4, 13, 27, 31), 1, "white")
        I.rrect((8, 17, 23, 28), 1, "dark")
        I.ball((10, 19, 15, 24), "pink")
        I.ball((17, 19, 22, 24), "cyan")
        return I.im

    def l9():
        I = Icon()
        for x, c in ((1, "pink"), (17, "cyan")):
            I.rrect((x, 1, x + 13, 25), 2, "purple")
            I.rrect((x + 2, 3, x + 11, 11), 1, "dark")
            I.rrect((x + 3, 4, x + 10, 6), 0, c, outline=False, shine=False)
        person(I, 8, 18, "pink", 0.55)
        person(I, 24, 18, "cyan", 0.55)
        return I.im

    def l10():
        I = Icon()
        I.ellipse((2, 18, 29, 31), "purple")
        for x, y, c in ((16, 3, "gold"), (6, 10, "pink"), (26, 10, "cyan")):
            I.ball((x - 5, y, x + 5, y + 10), c)
        return I.im

    return [("TWO PEOPLE", l1), ("THREE PEOPLE", l2), ("VERSUS", l3), ("CROWD", l4), ("RING", l5),
            ("DOOR", l6), ("ROSTER", l7), ("HOUSE", l8), ("CABINETS", l9), ("ROUND TABLE", l10)]


# ------------------------------------------------------------------ REPLAY

def replay_options():
    def r4():
        I = Icon()
        I.ball((2, 2, 27, 27), "gray")
        for a in range(0, 360, 72):
            x, y = 14.5 + 7 * math.cos(math.radians(a)), 14.5 + 7 * math.sin(math.radians(a))
            I.ellipse((x - 3, y - 3, x + 3, y + 3), "dark", shine=False)
        I.ball((12, 12, 17, 17), "dark")
        I.rrect((18, 24, 31, 30), 1, "brown", shine=False)
        return I.im

    def r5():
        I = Icon()
        I.rrect((1, 6, 30, 27), 3, "orange")
        I.rrect((4, 9, 27, 14), 1, "white", shine=False)
        I.rrect((6, 16, 25, 24), 3, "dark")
        I.ball((8, 17, 14, 23), "white")
        I.ball((17, 17, 23, 23), "white")
        return I.im

    def r6():
        I = Icon()
        I.rrect((1, 4, 30, 27), 4, "purple")
        I.rrect((4, 7, 24, 24), 2, "dark")
        I.poly([(14, 10), (14, 21), (7, 15.5)], "cyan")
        I.poly([(22, 10), (22, 21), (15, 15.5)], "cyan")
        I.ball((26, 9, 29, 12), "gold")
        I.ball((26, 15, 29, 18), "gold")
        return I.im

    def r7():
        I = Icon()
        I.poly([(15, 5), (15, 27), (1, 16)], "cyan")
        I.poly([(30, 5), (30, 27), (16, 16)], "cyan")
        return I.im

    def r8():
        I = Icon()
        I.rrect((1, 9, 22, 27), 3, "dark")
        I.poly([(22, 13), (31, 8), (31, 28), (22, 23)], "dark")
        I.ball((5, 12, 15, 22), "cyan")
        I.ball((17, 3, 23, 9), "red")
        return I.im

    def r9():
        I = Icon()
        I.ball((4, 4, 28, 28), "white")
        I.flat(lambda d: (d.line([(16, 16), (16, 8)], fill=RAMPS["dark"][1] + (255,), width=2),
                          d.line([(16, 16), (22, 16)], fill=RAMPS["dark"][1] + (255,), width=2)))
        I.arc((0, 0, 31, 31), 200, 340, 3, "cyan")
        I.poly([(0, 12), (6, 12), (2, 6)], "cyan")
        return I.im

    def r10():
        I = Icon()
        I.ball((1, 1, 30, 30), "dark")
        I.ball((7, 7, 24, 24), "red")
        return I.im

    return [("VIDEO TAPE", lambda: icons16.vhs(S)), ("ROUND ARROW", lambda: icons16.rewind_arrow(S)),
            ("CLAPPERBOARD", lambda: icons16.clapper(S)), ("FILM REEL", r4), ("CASSETTE", r5), ("TV REWIND", r6),
            ("REWIND", r7), ("CAMCORDER", r8), ("CLOCK BACK", r9), ("REC BUTTON", r10)]


# ------------------------------------------------------------------ FRIEND (the star tile)

def friend_options():
    def f1():
        return Icon().poly(star_pts(16, 17, 15), "gold").im

    def f2():
        I = Icon().poly(star_pts(16, 17, 15), "gold")
        I.flat(lambda d: (d.rectangle([12, 14, 13, 17], fill=RAMPS["gold"][0] + (255,)),
                          d.rectangle([18, 14, 19, 17], fill=RAMPS["gold"][0] + (255,)),
                          d.line([(13, 21), (15, 22), (17, 22), (19, 21)], fill=RAMPS["gold"][0] + (255,))))
        return I.im

    def f3():
        return heart_layer(Icon(), (2, 4, 29, 28), "pink").im

    def f4():
        I = Icon()
        I.poly([(2, 10), (9, 18), (16, 6), (23, 18), (30, 10), (27, 27), (5, 27)], "gold")
        for x, c in ((9, "red"), (16, "cyan"), (23, "green")):
            I.ball((x - 2, 20, x + 2, 24), c)
        return I.im

    def f5():
        I = Icon()
        I.arc((1, 4, 11, 16), 90, 270, 3, "gold")
        I.arc((20, 4, 30, 16), 270, 90, 3, "gold")
        I.poly([(6, 2), (25, 2), (23, 14), (19, 19), (12, 19), (8, 14)], "gold")
        I.rrect((13, 19, 18, 24), 0, "gold")
        I.rrect((8, 24, 23, 30), 1, "brown")
        return I.im

    def f6():
        I = Icon()
        I.poly([(6, 1), (13, 1), (17, 14), (12, 16)], "red")
        I.poly([(25, 1), (18, 1), (14, 14), (19, 16)], "blue")
        I.ball((7, 12, 24, 29), "gold")
        I.poly(star_pts(15.5, 21, 5), "orange", shine=False)
        return I.im

    def f7():
        I = Icon()
        I.poly([(8, 4), (23, 4), (30, 12), (16, 29), (1, 12)], "cyan")
        I.poly([(8, 4), (12, 12), (1, 12)], "cyan")
        I.poly([(23, 4), (30, 12), (19, 12)], "cyan")
        return I.im

    def f8():
        I = Icon().poly(star_pts(16, 16, 15, k=0.25, n=4, rot=-90), "gold")
        I.poly(star_pts(26, 6, 5, k=0.3, n=4), "white")
        return I.im

    def f9():
        I = Icon()
        I.poly([(7, 1), (25, 1), (25, 31), (16, 24), (7, 31)], "pink")
        I.poly(star_pts(16, 12, 6), "gold", shine=False)
        return I.im

    def f10():
        I = Icon().ball((1, 1, 30, 30), "purple")
        I.poly(star_pts(16, 17, 10), "gold")
        return I.im

    return [("STAR", f1), ("STAR FACE", f2), ("HEART", f3), ("CROWN", f4), ("TROPHY", f5), ("MEDAL", f6),
            ("GEM", f7), ("SPARKLE", f8), ("BOOKMARK", f9), ("STAR BADGE", f10)]


# ------------------------------------------------------------------ WATCH

def watch_options():
    def eye(I, box, iris="cyan"):
        x0, y0, x1, y1 = box
        I.layer(lambda d: d.chord(box, 180, 360, fill=255) or d.chord(box, 0, 180, fill=255), "white")
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        r = (y1 - y0) // 2 - 1
        I.ball((cx - r, cy - r, cx + r, cy + r), iris)
        I.flat(lambda d: (d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(0x10, 0x10, 0x18, 255)),
                          d.point((cx - 3, cy - 3), fill=WHITE + (255,))))

    def w1():
        I = Icon()
        eye(I, (1, 8, 30, 24))
        return I.im

    def w2():
        I = Icon()
        for x in (2, 17):
            I.rrect((x, 6, x + 12, 28), 4, "dark")
            I.ball((x + 1, 17, x + 11, 27), "cyan")
        I.rrect((12, 9, 19, 16), 1, "dark")
        return I.im

    def w3():
        I = Icon()
        I.rrect((1, 4, 30, 26), 4, "purple")
        I.rrect((4, 7, 27, 23), 2, "dark")
        eye(I, (7, 10, 24, 20))
        I.rrect((10, 26, 21, 30), 1, "purple")
        return I.im

    def w4():
        I = Icon()
        I.poly([(3, 15), (29, 15), (25, 29), (7, 29)], "red")
        I.flat(lambda d: [d.polygon([(x, 16), (x + 3, 16), (x + 2 - (x - 16) // 8, 28), (x - (x - 16) // 8, 28)],
                                    fill=WHITE + (255,)) for x in (8, 15, 22)])
        kernels = [(5, 13), (9, 14), (13, 13), (17, 14), (21, 13), (25, 14), (28, 12),
                   (7, 10), (11, 10), (15, 9), (19, 10), (23, 10), (27, 9),
                   (11, 6), (15, 5), (19, 6), (23, 6)]
        for i, (x, y) in enumerate(kernels):
            I.ball((x - 3, y - 1, x + 2, y + 4), "gold" if i % 5 == 2 else "white")
        return I.im

    def w5():
        I = Icon()
        I.rrect((1, 10, 30, 22), 3, "dark")
        I.rrect((3, 12, 14, 20), 2, "red", shine=False)
        I.rrect((17, 12, 28, 20), 2, "cyan", shine=False)
        return I.im

    def w6():
        I = Icon()
        I.rrect((1, 3, 30, 24), 3, "gray")
        I.rrect((4, 6, 27, 21), 2, "dark")
        I.ball((20, 8, 25, 13), "red")
        I.poly([(10, 26), (22, 26), (25, 31), (7, 31)], "gray")
        return I.im

    def w7():
        I = Icon()
        eye(I, (1, 10, 30, 26), "pink")
        I.flat(lambda d: [d.line([(x, 9), (x + dx, 4)], fill=RAMPS["dark"][1] + (255,), width=2)
                          for x, dx in ((8, -2), (15, 0), (22, 2))])
        return I.im

    def w8():
        I = Icon()
        I.layer(lambda d: (d.rectangle([1, 7, 30, 25], fill=255), d.ellipse([-3, 13, 3, 19], fill=0),
                           d.ellipse([28, 13, 34, 19], fill=0)), "gold")
        I.flat(lambda d: d.line([(22, 9), (22, 23)], fill=RAMPS["gold"][1] + (255,)))
        I.poly(star_pts(12, 16, 5), "orange", shine=False)
        return I.im

    def w9():
        I = Icon()
        I.poly([(2, 18), (24, 4), (28, 10), (6, 24)], "purple")
        I.ball((22, 2, 30, 12), "cyan")
        I.line([(14, 16), (10, 30)], 2, "brown")
        I.line([(14, 16), (20, 30)], 2, "brown")
        return I.im

    def w10():
        I = Icon()
        I.rrect((1, 1, 30, 18), 2, "dark")
        I.rrect((3, 3, 28, 16), 1, "ocean", shine=False)
        for x, c in ((6, "pink"), (16, "gold"), (26, "cyan")):
            I.ball((x - 5, 20, x + 5, 30), c)
        return I.im

    return [("EYE", w1), ("BINOCULARS", w2), ("TV EYE", w3), ("POPCORN", w4), ("3D GLASSES", w5), ("LIVE SCREEN", w6),
            ("LASHES", w7), ("TICKET", w8), ("TELESCOPE", w9), ("AUDIENCE", w10)]


# ------------------------------------------------------------------ WI-FI

def wifi_options():
    def fan(ramp, dot=None, width=3, radii=(6, 12, 18), cy=26, a=(225, 315)):
        I = Icon()
        arcs(I, 16, cy, radii, a[0], a[1], width, ramp)
        I.ball((13, cy - 3, 19, cy + 3), dot or ramp)
        return I

    def w3():
        I = Icon()
        I.line([(9, 18), (6, 6)], 2, "gray")
        I.line([(22, 18), (25, 6)], 2, "gray")
        I.rrect((2, 17, 29, 28), 3, "dark")
        I.flat(lambda d: [d.point((x, 22), fill=(0x50, 0xFA, 0x7B, 255)) for x in (8, 12, 16)])
        arcs(I, 16, 10, (4, 8), 230, 310, 2, "gold")
        return I.im

    def w4():
        I = Icon()
        I.ball((12, 12, 19, 19), "gold")
        arcs(I, 16, 16, (8, 13), 135, 225, 2, "gold")
        arcs(I, 16, 16, (8, 13), 315, 45, 2, "gold")
        return I.im

    def w5():
        I = Icon().rrect((1, 1, 30, 30), 6, "purple")
        arcs(I, 16, 23, (5, 10, 15), 230, 310, 2, "gold")
        I.ball((14, 21, 18, 25), "gold")
        return I.im

    def w6():
        I = Icon()
        for i in range(4):
            I.rrect((2 + i * 7, 24 - i * 6, 7 + i * 7, 30), 1, "gold")
        arcs(I, 24, 14, (5,), 230, 310, 2, "cyan")
        return I.im

    def w7():
        I = Icon()
        I.line([(16, 12), (16, 30)], 3, "gray")
        I.ball((13, 8, 19, 14), "red")
        arcs(I, 16, 11, (7, 12), 150, 210, 2, "gold")
        arcs(I, 16, 11, (7, 12), 330, 30, 2, "gold")
        return I.im

    def w8():
        I = Icon()
        for r in (6, 12, 18):
            for a in range(228, 313, 14):
                x, y = 16 + r * math.cos(math.radians(a)), 26 + r * math.sin(math.radians(a))
                I.ball((x - 2, y - 2, x + 2, y + 2), "gold")
        I.ball((13, 23, 19, 29), "gold")
        return I.im

    def w9():
        I = Icon()
        for r, c in ((18, "red"), (12, "gold"), (6, "green")):
            I.arc((16 - r, 26 - r, 16 + r, 26 + r), 225, 315, 3, c)
        I.ball((13, 23, 19, 29), "green")
        return I.im

    def w10():
        I = Icon().ball((1, 1, 30, 30), "gold")
        arcs(I, 16, 22, (4, 9), 230, 310, 2, "dark")
        I.ball((14, 20, 18, 24), "dark")
        return I.im

    return [("FAN GOLD", lambda: fan("gold").im), ("FAN CYAN", lambda: fan("cyan").im), ("ROUTER", w3), ("BROADCAST", w4),
            ("IN A TILE", w5), ("BARS + ARC", w6), ("ANTENNA", w7), ("DOTS", w8), ("TRAFFIC", w9), ("SIGN", w10)]


# ------------------------------------------------------------------ CABLE

def cable_options():
    def plug(I, x, y, ramp, w=14, h=14, pins="gold"):
        I.rrect((x, y, x + w, y + h), 2, ramp)
        I.rrect((x + 2, y + 2, x + w - 2, y + 6), 1, "dark", shine=False)
        I.flat(lambda d: [d.point((xx, y + 4), fill=RAMPS[pins][2] + (255,)) for xx in range(x + 3, x + w - 2, 2)])
        I.rrect((x + w // 2 - 3, y + h, x + w // 2 + 3, y + h + 4), 1, ramp)

    def c1():
        I = Icon()
        plug(I, 9, 2, "green")
        I.line([(16, 20), (16, 31)], 4, "green")
        return I.im

    def c2():
        I = Icon()
        plug(I, 9, 2, "purple")
        I.line([(16, 20), (16, 31)], 4, "purple")
        return I.im

    def c3():
        I = Icon().rrect((1, 4, 30, 27), 3, "gray")
        I.rrect((7, 9, 24, 23), 1, "dark")
        I.flat(lambda d: [d.point((x, 11), fill=RAMPS["gold"][2] + (255,)) for x in range(9, 23, 2)])
        I.rrect((13, 21, 18, 25), 0, "dark", shine=False)
        return I.im

    def c4():
        I = Icon()
        plug(I, 2, 2, "green", 12, 12)
        for i in range(4):
            I.arc((5 + i * 5, 16, 13 + i * 5, 26), 0, 360, 2, "green")
        return I.im

    def c5():
        I = Icon()
        plug(I, 1, 9, "pink", 12, 12)
        I.rrect((17, 8, 30, 23), 2, "cyan")
        I.rrect((19, 11, 28, 16), 1, "dark", shine=False)
        I.line([(14, 15), (17, 15)], 2, "gold")
        return I.im

    def c6():
        I = Icon()
        plug(I, 9, 10, "green")
        I.poly([(14, 0), (21, 0), (18, 5), (22, 5), (13, 12), (15, 7), (11, 7)], "gold")
        return I.im

    def c7():
        I = Icon().rrect((1, 1, 30, 30), 4, "dark")
        I.layer(lambda d: d.polygon([(6, 8), (25, 8), (25, 20), (20, 20), (20, 24), (11, 24), (11, 20), (6, 20)], fill=255), "gray")
        I.flat(lambda d: [d.point((x, 10), fill=RAMPS["gold"][2] + (255,)) for x in range(8, 24, 2)])
        return I.im

    def c8():
        I = Icon()
        I.ellipse((1, 12, 22, 31), "green", shine=False)
        I.ellipse((6, 17, 17, 26), "dark", shine=False)
        plug(I, 18, 1, "green", 12, 12)
        return I.im

    def c9():
        I = Icon().ball((1, 1, 30, 30), "green")
        plug(I, 10, 6, "white", 12, 11)
        I.line([(16, 22), (16, 27)], 3, "white")
        return I.im

    def c10():
        I = Icon()
        I.rrect((1, 2, 21, 17), 2, "gray")
        I.rrect((3, 4, 19, 14), 1, "ocean", shine=False)
        I.rrect((7, 19, 15, 22), 0, "gray")
        I.rrect((22, 8, 31, 30), 2, "dark")
        I.line([(26, 30), (26, 31)], 2, "green")
        return I.im

    def c11():
        I = Icon().rrect((1, 2, 30, 29), 3, "gray")
        I.rrect((5, 11, 26, 26), 1, "dark")
        I.layer(lambda d: d.polygon([(7, 13), (24, 13), (24, 22), (19, 22), (19, 25), (12, 25), (12, 22), (7, 22)],
                                    fill=255), "dark", outline=False, shine=False)
        I.flat(lambda d: [d.rectangle([x, 14, x, 16], fill=RAMPS["gold"][2] + (255,)) for x in range(9, 23, 2)])
        I.ball((4, 3, 11, 9), "green")      # RX
        I.ball((20, 3, 27, 9), "orange")    # TX
        return I.im

    return [("RX/TX JACK", c11), ("PLUG GREEN", c1), ("PLUG PURPLE", c2), ("PORT", c3), ("CURLY CORD", c4), ("PLUGGING", c5), ("POWER", c6),
            ("JACK", c7), ("COIL", c8), ("BADGE", c9), ("PC WIRED", c10)]


# ------------------------------------------------------------------ PING

def ping_options():
    def bars(colors):
        I = Icon()
        for i, c in enumerate(colors):
            I.rrect((2 + i * 7, 24 - i * 6, 7 + i * 7, 30), 1, c)
        return I.im

    def p3():
        I = Icon()
        for i in range(4):
            r = 2 + i
            x = 4 + i * 7
            I.ball((x - r, 24 - r, x + r, 24 + r), "green")
        return I.im

    def p4():
        I = Icon()
        I.layer(lambda d: d.pieslice((1, 4, 30, 33), 180, 360, fill=255), "dark")
        I.arc((4, 7, 27, 30), 180, 240, 3, "red", outline=False)
        I.arc((4, 7, 27, 30), 240, 300, 3, "gold", outline=False)
        I.arc((4, 7, 27, 30), 300, 360, 3, "green", outline=False)
        I.line([(16, 18), (24, 9)], 2, "white")
        I.ball((13, 15, 19, 21), "gray")
        return I.im

    def p5():
        return Icon().poly([(18, 0), (6, 17), (14, 17), (10, 31), (26, 11), (17, 11), (22, 0)], "gold").im

    def p6():
        I = Icon().rrect((9, 1, 22, 30), 3, "dark")
        for y, c in ((3, "red"), (12, "gold"), (21, "green")):
            I.ball((11, y, 19, y + 8), c if c == "green" else "dark")
        return I.im

    def p7():
        I = Icon().rrect((1, 4, 30, 27), 3, "dark")
        I.line([(3, 16), (9, 16), (12, 9), (16, 23), (19, 13), (21, 16), (28, 16)], 2, "green", outline=False)
        return I.im

    def p8():
        I = Icon().ball((3, 5, 28, 30), "white")
        I.rrect((13, 1, 18, 5), 1, "gray")
        I.flat(lambda d: (d.line([(15, 17), (15, 9)], fill=RAMPS["dark"][1] + (255,), width=2),
                          d.line([(15, 17), (21, 20)], fill=RAMPS["red"][2] + (255,), width=2)))
        return I.im

    def p9():
        I = Icon()
        I.line([(6, 14), (6, 30)], 2, "gray")
        I.ball((3, 9, 9, 15), "red")
        for i in range(3):
            I.rrect((12 + i * 7, 24 - i * 7, 17 + i * 7, 30), 1, "green")
        return I.im

    def p10():
        I = Icon().rrect((1, 10, 30, 22), 4, "dark")
        for i in range(4):
            I.ball((3 + i * 7, 12, 10 + i * 7, 19), "green")
        return I.im

    return [("BARS GREEN", lambda: bars(["green"] * 4)), ("BARS RAINBOW", lambda: bars(["red", "orange", "gold", "green"])),
            ("DOTS", p3), ("DIAL", p4), ("LIGHTNING", p5), ("TRAFFIC LIGHT", p6), ("HEARTBEAT", p7), ("STOPWATCH", p8),
            ("TOWER BARS", p9), ("GEM LIGHTS", p10)]


# ------------------------------------------------------------------ FAIRPLAY

def fair_options():
    def shield(I, ramp, box=(3, 1, 28, 31)):
        x0, y0, x1, y1 = box
        cx = (x0 + x1) / 2
        I.poly([(x0, y0 + 2), (cx, y0), (x1, y0 + 2), (x1, y0 + 14), (cx, y1), (x0, y0 + 14)], ramp)

    def check(I, ramp="white", k=1.0, dx=0, dy=0):
        I.line([(9 + dx, 15 + dy), (14 + dx, 21 + dy), (23 + dx, 9 + dy)], max(2, round(3 * k)), ramp)

    def s1():
        I = Icon()
        shield(I, "green")
        check(I)
        return I.im

    def s2():
        I = Icon()
        shield(I, "blue")
        I.poly(star_pts(15.5, 14, 7), "gold")
        return I.im

    def s3():
        I = Icon()
        I.arc((8, 1, 23, 18), 180, 360, 3, "gray")
        I.line([(9, 9), (9, 14)], 3, "gray")
        I.line([(22, 9), (22, 14)], 3, "gray")
        I.rrect((4, 13, 27, 30), 3, "gold")
        I.ball((13, 18, 18, 23), "dark")
        return I.im

    def s4():
        I = Icon().ball((1, 1, 30, 30), "green")
        check(I)
        return I.im

    def s5():
        I = Icon()
        I.line([(16, 3), (16, 27)], 2, "gold")
        I.line([(4, 7), (28, 7)], 2, "gold")
        I.layer(lambda d: d.pieslice((0, 8, 11, 20), 0, 180, fill=255), "gold")
        I.layer(lambda d: d.pieslice((20, 8, 31, 20), 0, 180, fill=255), "gold")
        I.rrect((9, 26, 22, 30), 1, "brown")
        return I.im

    def s6():
        I = Icon()
        I.poly([(7, 1), (13, 1), (17, 12), (12, 14)], "red")
        I.poly([(24, 1), (18, 1), (14, 12), (19, 14)], "blue")
        I.ball((5, 10, 26, 31), "gold")
        check(I, "green", 0.8, 0, 6)
        return I.im

    def s7():
        I = Icon().poly(star_pts(16, 16, 15, k=0.62, n=6), "gold")
        I.ball((10, 10, 21, 21), "blue")
        return I.im

    def s8():
        I = Icon()
        I.line([(19, 19), (29, 29)], 4, "brown")
        I.ball((1, 1, 22, 22), "cyan")
        check(I, "green", 0.8, -4, -4)
        return I.im

    def s9():
        I = Icon()
        I.layer(lambda d: d.polygon([(3, 3), (16, 1), (16, 31), (3, 15)], fill=255), "red")
        I.layer(lambda d: d.polygon([(16, 1), (28, 3), (28, 15), (16, 31)], fill=255), "blue")
        check(I, "white", 0.9)
        return I.im

    def s10():
        I = Icon()
        I.poly([(10, 18), (5, 31), (11, 28), (14, 31), (16, 20)], "green")
        I.poly([(22, 18), (27, 31), (21, 28), (18, 31), (16, 20)], "green")
        I.poly(star_pts(16, 12, 11, k=0.8, n=10), "green")
        I.ball((10, 6, 22, 18), "gold")
        return I.im

    return [("SHIELD CHECK", s1), ("CREST STAR", s2), ("PADLOCK", s3), ("CHECK BADGE", s4), ("SCALES", s5),
            ("MEDAL CHECK", s6), ("SHERIFF", s7), ("MAGNIFIER", s8), ("RED/BLUE SHIELD", s9), ("ROSETTE", s10)]


# ------------------------------------------------------------------ PASS

def pass_options():
    def x_(I, ramp, w=6, box=(4, 4, 27, 27)):
        x0, y0, x1, y1 = box
        I.line([(x0, y0), (x1, y1)], w, ramp)
        I.line([(x1, y0), (x0, y1)], w, ramp)

    def p1():
        I = Icon()
        x_(I, "red")
        return I.im

    def p2():
        I = Icon().ball((1, 1, 30, 30), "red")
        I.line([(8, 23), (23, 8)], 4, "white")
        return I.im

    def p3():
        I = Icon()
        I.poly([(2, 5), (14, 16), (2, 27)], "orange")
        I.poly([(14, 5), (26, 16), (14, 27)], "orange")
        I.rrect((26, 5, 30, 27), 1, "orange")
        return I.im

    def p4():
        I = Icon()
        heart_layer(I, (2, 4, 29, 28), "red")
        I.flat(lambda d: d.line([(16, 6), (12, 13), (18, 18), (14, 26)], fill=SPACE + (255,), width=2))
        return I.im

    def p5():
        I = Icon()
        I.poly([(10, 1), (21, 1), (30, 10), (30, 21), (21, 30), (10, 30), (1, 21), (1, 10)], "red")
        I.rrect((7, 13, 24, 18), 1, "white")
        return I.im

    def p6():
        I = Icon()
        I.rrect((2, 2, 17, 30), 1, "brown")
        I.rrect((5, 5, 14, 30), 0, "dark", shine=False)
        I.poly([(16, 12), (24, 12), (24, 7), (31, 16), (24, 25), (24, 20), (16, 20)], "orange")
        return I.im

    def p7():
        I = Icon().rrect((1, 1, 30, 30), 6, "red")
        x_(I, "white", 4, (8, 8, 23, 23))
        return I.im

    def p8():
        I = Icon()
        I.arc((5, 6, 29, 30), 180, 90, 4, "orange")
        I.poly([(0, 18), (10, 18), (5, 11)], "orange")
        return I.im

    def p9():
        I = Icon()
        I.rrect((4, 6, 27, 10), 1, "gray")
        I.rrect((12, 2, 19, 7), 1, "gray")
        I.poly([(6, 11), (25, 11), (23, 31), (8, 31)], "gray")
        I.flat(lambda d: [d.line([(x, 14), (x, 28)], fill=RAMPS["gray"][0] + (255,)) for x in (12, 16, 20)])
        return I.im

    def p10():
        I = Icon()
        I.layer(lambda d: (d.ellipse((2, 2, 29, 29), fill=255), d.ellipse((10, -2, 35, 23), fill=0)), "gold")
        I.flat(lambda d: (d.text((20, 18), "z", fill=WHITE + (255,)), d.text((25, 10), "z", fill=WHITE + (255,))))
        return I.im

    return [("BIG X", p1), ("NO SIGN", p2), ("SKIP", p3), ("BROKEN HEART", p4), ("STOP", p5), ("EXIT DOOR", p6),
            ("X BUTTON", p7), ("TURN BACK", p8), ("BIN", p9), ("NOT NOW", p10)]


# ------------------------------------------------------------------ ROM DOWNLOAD

def rom_options():
    def a1():
        I = Icon()
        arrow_down(I, 4, 1, 24, 22, "orange")
        I.rrect((2, 25, 29, 30), 1, "orange")
        return I.im

    def a2():
        I = Icon()
        I.rrect((3, 1, 28, 26), 2, "gray")
        I.rrect((6, 4, 25, 14), 1, "white", shine=False)
        I.rrect((5, 26, 26, 31), 0, "board")
        arrow_down(I, 10, 13, 12, 12, "orange")
        return I.im

    def a3():
        I = Icon().rrect((1, 1, 30, 30), 2, "blue")
        I.rrect((7, 1, 24, 11), 0, "gray")
        I.rrect((6, 16, 25, 30), 1, "white", shine=False)
        arrow_down(I, 10, 15, 12, 13, "orange")
        return I.im

    def a4():
        I = Icon()
        I.poly([(2, 9), (16, 4), (30, 9), (30, 27), (16, 31), (2, 27)], "brown")
        I.flat(lambda d: d.line([(16, 10), (16, 31)], fill=RAMPS["brown"][0] + (255,)))
        arrow_down(I, 9, 0, 14, 14, "orange")
        return I.im

    def a5():
        I = Icon()
        I.poly([(4, 1), (21, 1), (28, 8), (28, 31), (4, 31)], "white")
        I.flat(lambda d: [d.rectangle([12, y, 15, y + 1], fill=RAMPS["gray"][1] + (255,)) for y in range(4, 20, 4)])
        I.rrect((10, 20, 17, 27), 1, "gold")
        return I.im

    def a6():
        I = Icon()
        I.rrect((5, 3, 26, 28), 2, "dark")
        I.flat(lambda d: [(d.rectangle([2, y, 4, y + 1], fill=RAMPS["gold"][2] + (255,)),
                           d.rectangle([27, y, 29, y + 1], fill=RAMPS["gold"][2] + (255,))) for y in range(6, 27, 4)])
        I.ball((8, 6, 11, 9), "gray")
        return I.im

    def a7():
        I = Icon()
        for box in ((1, 10, 15, 24), (8, 4, 24, 20), (16, 9, 30, 24)):
            I.ellipse(box, "white", shine=False)
        arrow_down(I, 10, 14, 12, 16, "orange")
        return I.im

    def a8():
        I = Icon().ball((1, 1, 30, 30), "metal")
        I.ball((12, 12, 19, 19), "dark")
        I.arc((5, 5, 26, 26), 200, 250, 2, "cyan", outline=False)
        return I.im

    def a9():
        I = Icon().rrect((1, 4, 30, 27), 2, "board")
        for x, y in ((5, 8), (17, 8), (5, 17)):
            I.rrect((x, y, x + 9, y + 6), 1, "dark")
        I.rrect((17, 17, 26, 23), 1, "gold")
        return I.im

    def a10():
        I = Icon()
        arrow_down(I, 8, 0, 16, 16, "orange")
        I.rrect((1, 20, 30, 29), 3, "dark")
        I.rrect((3, 22, 18, 27), 1, "green", shine=False)
        return I.im

    return [("ARROW", a1), ("CARTRIDGE", a2), ("FLOPPY", a3), ("BOX", a4), ("ZIP", a5), ("ROM CHIP", a6),
            ("CLOUD", a7), ("DISC", a8), ("PCB", a9), ("PROGRESS", a10)]


# ------------------------------------------------------------------ WINS / LOSSES

def skull(I, box):
    x0, y0, x1, y1 = box
    w = x1 - x0
    I.ball((x0, y0, x1, y0 + w - 2), "white")
    I.rrect((x0 + w // 4, y0 + w - 7, x1 - w // 4, y1), 2, "white")
    ex = w // 4
    I.flat(lambda d: (d.ellipse([x0 + ex - 2, y0 + w // 3, x0 + ex + 4, y0 + w // 3 + 6], fill=(0x10, 0x10, 0x18, 255)),
                      d.ellipse([x1 - ex - 4, y0 + w // 3, x1 - ex + 2, y0 + w // 3 + 6], fill=(0x10, 0x10, 0x18, 255)),
                      d.polygon([(x0 + w // 2, y0 + w // 2 + 2), (x0 + w // 2 - 2, y0 + w // 2 + 5),
                                 (x0 + w // 2 + 2, y0 + w // 2 + 5)], fill=(0x10, 0x10, 0x18, 255)),
                      [d.line([(x, y1 - 5), (x, y1 - 1)], fill=RAMPS["white"][1] + (255,)) for x in range(x0 + w // 4 + 3, x1 - w // 4 - 1, 3)]))


def trophy(I):
    I.arc((1, 4, 11, 16), 90, 270, 3, "gold")
    I.arc((20, 4, 30, 16), 270, 90, 3, "gold")
    I.poly([(6, 2), (25, 2), (23, 14), (19, 19), (12, 19), (8, 14)], "gold")
    I.rrect((13, 19, 18, 24), 0, "gold")
    I.rrect((8, 24, 23, 30), 1, "brown")


def wl_options():
    def w1():
        I = Icon()
        trophy(I)
        return I.im

    def l1():
        I = Icon()
        skull(I, (4, 2, 27, 30))
        return I.im

    def w2():
        I = Icon()
        I.poly([(2, 10), (9, 18), (16, 6), (23, 18), (30, 10), (27, 27), (5, 27)], "gold")
        for x, c in ((9, "red"), (16, "cyan"), (23, "green")):
            I.ball((x - 2, 20, x + 2, 24), c)
        return I.im

    def l2():
        I = Icon()
        I.layer(lambda d: (d.pieslice((6, 2, 25, 21), 180, 360, fill=255), d.rectangle((6, 11, 25, 27), fill=255)), "gray")
        I.flat(lambda d: (d.line([(15, 8), (15, 19)], fill=RAMPS["gray"][0] + (255,), width=2),
                          d.line([(11, 12), (19, 12)], fill=RAMPS["gray"][0] + (255,), width=2)))
        I.rrect((2, 26, 29, 31), 2, "green")
        return I.im

    def w3():
        I = Icon()
        I.poly([(16, 1), (30, 16), (21, 16), (21, 30), (11, 30), (11, 16), (2, 16)], "green")
        return I.im

    def l3():
        I = Icon()
        I.poly([(16, 30), (30, 15), (21, 15), (21, 1), (11, 1), (11, 15), (2, 15)], "red")
        return I.im

    def w4():
        from fists import glove_fist
        g = glove_fist("red").rotate(90, resample=Image.NEAREST, expand=True)
        I = Icon()
        I.paste(g, ((S - g.width) // 2, (S - g.height) // 2))
        return I.im

    def l4():
        from fists import glove_fist
        g = glove_fist("metal").rotate(-90, resample=Image.NEAREST, expand=True)
        I = Icon()
        I.paste(g, ((S - g.width) // 2, (S - g.height) // 2))
        return I.im

    def w5():
        I = Icon()
        I.poly([(7, 1), (13, 1), (17, 14), (12, 16)], "red")
        I.poly([(24, 1), (18, 1), (14, 14), (19, 16)], "blue")
        I.ball((5, 10, 26, 31), "gold")
        I.flat(lambda d: (d.line([(16, 15), (16, 26)], fill=RAMPS["gold"][0] + (255,), width=3),
                          d.line([(13, 17), (16, 15)], fill=RAMPS["gold"][0] + (255,), width=2)))
        return I.im

    def l5():
        I = Icon().rrect((1, 6, 30, 25), 4, "red")
        f = ImageFont.truetype(os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "fonts", "PressStart2P-Regular.ttf"), 8)
        I.flat(lambda d: (d.text((9, 12), "KO", font=f, fill=RAMPS["red"][0] + (255,)),
                          d.text((8, 11), "KO", font=f, fill=WHITE + (255,))))
        return I.im

    return [("TROPHY / SKULL", w1, l1), ("CROWN / GRAVE", w2, l2), ("UP / DOWN", w3, l3),
            ("GLOVE UP / DOWN", w4, l4), ("MEDAL 1 / KO", w5, l5)]


def wl_sheet():
    cw = 128
    out = Image.new("RGB", (5 * cw + 16, 170), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    d.text((8, 8), "WINS / LOSSES: 5 OPTIONS", font=font(), fill=YELLOW)
    for i, (name, w, l) in enumerate(wl_options()):
        x = 8 + i * cw
        a, b = w(), l()
        for k, ic in enumerate((a, b)):
            big = ic.resize((48, 48), Image.NEAREST)
            out.paste(big, (x + 8 + k * 56, 30), big)
        sw, sl = shrink(a, 10, 10), shrink(b, 10, 10)
        out.paste(sw, (x + 8, 92), sw)
        d.text((x + 20, 93), "34", font=font(), fill=WHITE)
        out.paste(sl, (x + 44, 92), sl)
        d.text((x + 56, 93), "12", font=font(), fill=WHITE)
        d.text((x, 30), str(i + 1), font=font(), fill=(0xFF, 0x79, 0xC6))
        d.text((x + 2, 116), name.split(" / ")[0], font=font(), fill=(0x62, 0x72, 0xA4))
        d.text((x + 2, 128), "/ " + name.split(" / ")[1], font=font(), fill=(0x62, 0x72, 0xA4))
    return out


# ------------------------------------------------------------------ LOSS (ten skulls and others)

EYE = (0x10, 0x10, 0x18, 255)


def skull2(I, ramp="white", eyes=None, dx=0, dy=0, cracks=False, xeyes=False, glow=None):
    """A skull with a shape: a wide crown, cheekbones, a narrow jaw with teeth."""
    o = RAMPS[ramp][0]
    I.ball((3 + dx, 1 + dy, 28 + dx, 24 + dy), ramp)                     # the crown
    I.rrect((8 + dx, 18 + dy, 23 + dx, 29 + dy), 3, ramp)                # the jaw
    I.layer(lambda d: d.rectangle((6 + dx, 14 + dy, 25 + dx, 20 + dy), fill=255), ramp, outline=False, shine=False)

    def face(d):
        if xeyes:
            for cx in (11, 20):
                d.line([(cx - 3 + dx, 10 + dy), (cx + 3 + dx, 16 + dy)], fill=EYE, width=2)
                d.line([(cx + 3 + dx, 10 + dy), (cx - 3 + dx, 16 + dy)], fill=EYE, width=2)
        else:
            d.polygon([(6 + dx, 11 + dy), (14 + dx, 10 + dy), (14 + dx, 17 + dy), (8 + dx, 17 + dy)], fill=EYE)
            d.polygon([(25 + dx, 11 + dy), (17 + dx, 10 + dy), (17 + dx, 17 + dy), (23 + dx, 17 + dy)], fill=EYE)
            if glow:
                d.rectangle([10 + dx, 13 + dy, 11 + dx, 14 + dy], fill=glow + (255,))
                d.rectangle([20 + dx, 13 + dy, 21 + dx, 14 + dy], fill=glow + (255,))
        d.polygon([(15 + dx, 18 + dy), (17 + dx, 18 + dy), (16 + dx, 21 + dy)], fill=EYE)   # the nose
        d.line([(10 + dx, 24 + dy), (21 + dx, 24 + dy)], fill=o + (255,))                    # the bite
        for x in range(11, 21, 3):
            d.line([(x + dx, 22 + dy), (x + dx, 28 + dy)], fill=o + (255,))
        if cracks:
            d.line([(17 + dx, 2 + dy), (19 + dx, 5 + dy), (17 + dx, 8 + dy)], fill=o + (255,))
    I.flat(face)
    return I


SMALL_SKULL = [
    "..oooooo..",
    ".owwwwwwo.",
    "owwwwwwwwo",
    "owddwwddwo",
    "owddwwddwo",
    "owwwwdwwwo",
    ".owwwwwwo.",
    "..owdwdo..",
    "..owwwwo..",
    "...oooo...",
]


def from_rows(rows, pal):
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in pal:
                im.putpixel((x, y), pal[c] + (255,))
    return im


def loss_options():
    white = RAMPS["white"]

    def l1():
        return skull2(Icon()).im

    def l2():
        I = Icon()
        I.line([(3, 22), (28, 30)], 4, "white")
        I.line([(28, 22), (3, 30)], 4, "white")
        for x, y in ((2, 20), (26, 28), (27, 20), (1, 28)):
            I.ball((x, y, x + 4, y + 4), "white")
        skull2(I, dy=-2)
        return I.im

    def l3():
        return skull2(Icon(), "red").im

    def l4():
        I = Icon().ball((0, 0, 31, 31), "red")
        I.paste(shrink(skull2(Icon()).im, 22, 22), (5, 4))
        return I.im

    def l5():
        return skull2(Icon(), cracks=True).im

    def l6():
        return skull2(Icon(), xeyes=True).im

    def l7():
        small = from_rows(SMALL_SKULL, {"o": white[0], "w": white[2], "d": (0x10, 0x10, 0x18)})
        return small.resize((30, 30), Image.NEAREST).crop((-1, -1, 31, 31))

    def l8():
        return skull2(Icon(), "purple", glow=(0xFF, 0x79, 0xC6)).im

    def l9():
        I = skull2(Icon())
        I.rrect((2, 6, 29, 10), 1, "blue")
        I.poly([(27, 7), (31, 4), (31, 13)], "blue")
        return I.im

    def l10():
        I = Icon()
        I.layer(lambda d: (d.pieslice((5, 1, 26, 22), 180, 360, fill=255), d.rectangle((5, 11, 26, 26), fill=255),
                           d.polygon([(5, 26), (8, 31), (11, 26), (15, 31), (19, 26), (23, 31), (26, 26)], fill=255)),
                "white")
        I.flat(lambda d: (d.ellipse([10, 9, 14, 15], fill=EYE), d.ellipse([17, 9, 21, 15], fill=EYE),
                          d.arc([12, 17, 19, 23], 200, 340, fill=EYE, width=2)))
        return I.im

    return [("SKULL", l1), ("CROSSBONES", l2), ("RED SKULL", l3), ("SKULL BADGE", l4), ("CRACKED", l5),
            ("KO EYES", l6), ("8-BIT SKULL", l7), ("PURPLE GLOW", l8), ("HEADBAND", l9), ("SAD GHOST", l10)]


def loss_sheet():
    opts = loss_options()
    cw, chh = 128, 132
    out = Image.new("RGB", (5 * cw + 16, 2 * chh + 30), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    d.text((8, 8), "LOSS: 10 OPTIONS", font=font(), fill=YELLOW)
    for i, (name, fn) in enumerate(opts):
        x, y = 8 + (i % 5) * cw, 26 + (i // 5) * chh
        ic = fn()
        big = ic.resize((96, 96), Image.NEAREST)
        out.paste(big, (x + 12, y + 4), big)
        sm = from_rows(SMALL_SKULL, {"o": RAMPS["white"][0], "w": RAMPS["white"][2], "d": (0x10, 0x10, 0x18)}) \
            if name == "8-BIT SKULL" else shrink(ic, 10, 10)
        out.paste(sm, (x + 12, y + 106), sm)
        d.text((x + 24, y + 107), "12", font=font(), fill=(0xFF, 0x55, 0x55))
        d.text((x, y + 4), str(i + 1), font=font(), fill=(0xFF, 0x79, 0xC6))
        d.text((x + 2, y + 120), name, font=font(), fill=(0x62, 0x72, 0xA4))
    return out


# ------------------------------------------------------------------ THE CHOSEN ONES

# What the user chose on 2026-11-27 (fists: fists.py option 3).
CHOSEN = {"online": 1, "lobby": 5, "replay": 7, "friend": 2, "watch": 4, "wifi": 1, "cable": 1, "ping": 1,
          "fairplay": 7, "pass": 7, "rom": 10, "wl": 3}
_OPTS = {"online": online_options, "lobby": lobby_options, "replay": replay_options, "friend": friend_options,
         "watch": watch_options, "wifi": wifi_options, "cable": cable_options, "ping": ping_options,
         "fairplay": fair_options, "pass": pass_options, "rom": rom_options}


def shrink(im, w, h):
    """A smaller copy of a sprite that keeps its own colours (no blur)."""
    pal = sorted({im.getpixel((x, y))[:3] for x in range(im.width) for y in range(im.height) if im.getpixel((x, y))[3]})
    sm = im.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            r, g, b, a = sm.getpixel((x, y))
            if a >= 110:
                out.putpixel((x, y), min(pal, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2) + (255,))
    return out


_cache = {}

# Hand-drawn small versions, for the icons that a shrink turns into a blur
# (the router loses its waves at 10 px).
SMALL = {
    ("wifi", 10, 1): [
        "..........",
        "..YYYYYY..",
        ".Y......Y.",
        "Y..YYYY..Y",
        "..Y....Y..",
        "....YY....",
        "...YYYY...",
        "....YY....",
        "..........",
        "..........",
    ],
    ("cable", 10, 1): [
        ".oooooooo.",
        "oGGGooOOOo",
        "oGGGooOOOo",
        "ommmmmmmmo",
        "omkkkkkkmo",
        "omkYkYkYmo",
        "omkkkkkkmo",
        "ommmkkmmmo",
        "ommmmmmmmo",
        ".oooooooo.",
    ],
    ("cable", 10, 2): [
        ".oooooooo.",
        "oPPPPPPPPo",
        "oPddddddPo",
        "oPdYdYdYPo",
        "oPPPPPPPPo",
        ".oPPPPPPo.",
        "..oPPPPo..",
        "...oPPo...",
        "...oPPo...",
        "...oooo...",
    ],
    ("wifi", 10, 3): [
        "..YYYYYY..",
        ".Y......Y.",
        "Y..YYYY..Y",
        "..Y....Y..",
        "....YY....",
        ".g......g.",
        "oooooooooo",
        "odGdGdGddo",
        "oddddddddo",
        "oooooooooo",
    ],
}
SMALL_PAL = {"Y": (0xF8, 0xC8, 0x30), "g": (0xB0, 0xB6, 0xC8), "o": (0x08, 0x08, 0x10), "d": (0x2A, 0x2A, 0x3A),
             "G": (0x50, 0xFA, 0x7B), "P": (0xBD, 0x93, 0xF9), "O": (0xFF, 0xB8, 0x6C), "k": (0x10, 0x10, 0x18), "m": (0x80, 0x86, 0x9C)}


def chosen(name, size=32, lit=True):
    """The chosen icon of a kind, at a size (32 is the drawing; smaller ones keep the colours)."""
    key = (name, size, lit)
    if key in _cache:
        return _cache[key]
    if (name, size, CHOSEN.get(name)) in SMALL:
        rows = SMALL[(name, size, CHOSEN.get(name))]
        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        for y, row in enumerate(rows):
            for x, c in enumerate(row):
                if c in SMALL_PAL:
                    im.putpixel((x, y), SMALL_PAL[c] + (255,))
        im = im.crop(im.getbbox())     # no empty rows: centred on a line, the drawing is on its middle
        _cache[key] = im
        return im
    if name == "online":
        im = icons16.globe(size, lit=lit) if size >= 12 else shrink(icons16.globe(24, lit=lit), size, size)
    elif name in ("win", "loss"):
        _, w, l = wl_options()[CHOSEN["wl"] - 1]
        im = (w if name == "win" else l)()
    else:
        im = _OPTS[name]()[CHOSEN[name] - 1][1]()
    if name != "online" and size != S:
        im = shrink(im, size, size)
    _cache[key] = im
    return im


def ping_bars(ms, w=12, h=10):
    """The ping as four bevelled bars, lit by how good it is."""
    if ms <= 40:
        ramp, n = "green", 4
    elif ms <= 80:
        ramp, n = "gold", 3
    elif ms <= 130:
        ramp, n = "orange", 2
    else:
        ramp, n = "red", 1
    I = Icon(max(w, h))
    bw = max(2, (w - 3) // 4)
    for i in range(4):
        bh = round(h * (i + 1) / 4)
        I.rrect((i * (bw + 1), h - bh, i * (bw + 1) + bw - 1, h - 1), 0, ramp if i < n else "dark", shine=False)
    return I.im.crop((0, 0, w, h))


def chosen_sheet():
    names = ["online", "lobby", "replay", "friend", "watch", "wifi", "cable", "ping", "fairplay", "pass", "rom", "win", "loss"]
    cw = 96
    out = Image.new("RGB", (7 * cw + 16, 2 * 120 + 30), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    d.text((8, 8), "THE CHOSEN ICONS", font=font(), fill=YELLOW)
    for i, n in enumerate(names):
        x, y = 8 + (i % 7) * cw, 26 + (i // 7) * 120
        ic = chosen(n)
        big = ic.resize((64, 64), Image.NEAREST)
        out.paste(big, (x + 8, y), big)
        for k, sz in enumerate((16, 12, 10)):
            sm = chosen(n, sz)
            out.paste(sm, (x + 8 + k * 22, y + 72), sm)
        d.text((x + 8, y + 96), n.upper(), font=font(), fill=(0x62, 0x72, 0xA4))
    return out


GROUPS = [("ONLINE MARK", online_options), ("LOBBY", lobby_options), ("REPLAY", replay_options),
          ("FRIEND / FAVOURITE", friend_options), ("WATCH", watch_options), ("WI-FI", wifi_options),
          ("CABLE", cable_options), ("PING", ping_options), ("FAIRPLAY", fair_options), ("PASS", pass_options),
          ("ROM DOWNLOAD", rom_options)]


def font():
    return ImageFont.truetype(os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "fonts", "PressStart2P-Regular.ttf"), 8)


def group_sheet(title, options):
    cw, chh = 128, 132
    out = Image.new("RGB", (5 * cw + 16, ((len(options) + 4) // 5) * chh + 30), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    d.text((8, 8), title, font=font(), fill=YELLOW)
    for i, (name, fn) in enumerate(options):
        x, y = 8 + (i % 5) * cw, 26 + (i // 5) * chh
        ic = fn()
        big = ic.resize((96, 96), Image.NEAREST)
        out.paste(big, (x + 12, y + 4), big)
        out.paste(ic, (x + 12, y + 104), ic)
        sm = ic.resize((16, 16), Image.NEAREST)
        out.paste(sm, (x + 50, y + 112), sm)
        d.text((x, y + 4), str(i + 1), font=font(), fill=(0xFF, 0x79, 0xC6))
        d.text((x + 70, y + 112), "", font=font(), fill=WHITE)
        d.text((x + 2, y + 124 - 0), name[:15], font=font(), fill=(0x62, 0x72, 0xA4)) if False else None
        d.text((x + 70, y + 108), "\n".join(name.split(" ")[:2])[:16], font=font(), fill=(0x62, 0x72, 0xA4))
    return out


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)
    sheets = []
    for i, (title, fn) in enumerate(GROUPS):
        opts = fn()
        sh = group_sheet("%s: %d OPTIONS" % (title, len(opts)), opts)
        name = "%02d-%s.png" % (i + 1, title.lower().replace(" / ", "-").replace(" ", "-"))
        sh.save(os.path.join(out, name))
        sheets.append(sh)
        print(name)
    wl_sheet().save(os.path.join(out, "12-wins-losses.png"))
    loss_sheet().save(os.path.join(out, "13-loss.png"))
    chosen_sheet().save(os.path.join(out, "00-chosen.png"))
    print("12-wins-losses.png 00-chosen.png")


if __name__ == "__main__":
    main()
