#!/usr/bin/env python3
"""Mock-ups of the link and net play screens of the FliperOS frontend.

Draws at the frontend's logical size (320x240) with its font (Press Start 2P,
8 px, no antialias) and palette, and scales 3x to 960x720 like the real
screenshots. The title band is cut from a real frontend screenshot. The game
art is the scraped snap from the cabinet, and the genre, controls and buttons
icons are the Arcadeflow ones the frontend already ships (gui/icons/metapics).

    python3 frontend-mockups.py OUT_DIR [REAL_LIST_SCREENSHOT] [ART_DIR]

ART_DIR holds the snaps as snap_<system>_<game>.png (see GAMES). Without it
the art is a plain box. These are design sketches for discussion, not
frontend code.
"""
import math
import os
import random
import sys

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT = os.environ.get("FE_FONT") or os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "fonts", "PressStart2P-Regular.ttf")
METAPICS = os.environ.get("FE_METAPICS") or os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "icons", "metapics")
ART = ""
W, H, SCALE = 320, 240, 3

SPACE = (0x0B, 0x0B, 0x12)
BG = (0x28, 0x2A, 0x36)
BG_DEEP = (0x19, 0x1A, 0x21)
CARD = (0x14, 0x14, 0x1E)
LINE = (0x44, 0x47, 0x5A)
COMMENT = (0x62, 0x72, 0xA4)
FG = (0xF8, 0xF8, 0xF2)
GREEN = (0x50, 0xFA, 0x7B)
GREEN_DIM = (0x2E, 0x5E, 0x40)
GREEN_MID = (0x3C, 0xB0, 0x5C)   # an unlit globe on the selected tile, over its pink tint
PINK = (0xFF, 0x79, 0xC6)
CYAN = (0x8B, 0xE9, 0xFD)
YELLOW = (0xF1, 0xFA, 0x8C)
ORANGE = (0xFF, 0xB8, 0x6C)
PURPLE = (0xBD, 0x93, 0xF9)
RED = (0xFF, 0x55, 0x55)
LIST_TEXT = (0x7A, 0x88, 0xC8)

# The games of the mock-ups. genre / control / buttons / players are what the
# frontend reads from the game's info (same keys as feview.py).
GAMES = {
    "daytona": dict(title="DAYTONA USA", year="1994", maker="SEGA", snap="snap_model2_daytona.png",
                    genre="Driving / Race (chase view)", control="paddle,pedal", buttons=6, players=1, link=8),
    "scud": dict(title="SCUD RACE", year="1996", maker="SEGA", snap="snap_model3_scud.png",
                 genre="Driving / Race (chase view)", control="paddle,pedal", buttons=4, players=1, link=8),
    "daytona2": dict(title="DAYTONA USA 2", year="1998", maker="SEGA", snap="snap_model3_daytona2.png",
                     genre="Driving / Race (chase view)", control="paddle,pedal", buttons=6, players=1, link=8),
    "dirtdvls": dict(title="DIRT DEVILS", year="1998", maker="SEGA", snap="snap_model3_dirtdvls.png",
                     genre="Driving / Race", control="paddle,pedal", buttons=4, players=1, link=2),
    "ssf2tb": dict(title="SF2 TOURNAMENT", year="1993", maker="CAPCOM", snap="snap_mame_ssf2.png",
                   genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2, link=4),
    "xmen": dict(title="X-MEN (6 PLAYERS)", year="1992", maker="KONAMI", snap="snap_mame_xmen.png",
                 genre="Fighter / 2.5D", control="joystick (8-way)", buttons=3, players=6, net=True),
    "3countb": dict(title="3 COUNT BOUT", year="1993", maker="SNK", snap="snap_mame_3countb.png"),
    "1944": dict(title="1944", year="2000", maker="CAPCOM", snap="snap_mame_1944.png"),
}


def font():
    return ImageFont.truetype(FONT, 8)


# ----------------------------------------------------------------- the art

def snap(key):
    g = GAMES.get(key) or {}
    path = os.path.join(ART, g.get("snap", "")) if ART else ""
    if path and os.path.isfile(path):
        return Image.open(path).convert("RGB")
    return None


def stretch(im, w, h):
    """The frontend stretches a snap to the box (4:3 tiles, wider games too)."""
    if im is None:
        return Image.new("RGB", (w, h), BG_DEEP)
    return im.resize((w, h), Image.LANCZOS)


def dim(im, k):
    return ImageEnhance.Brightness(im).enhance(k)


class Canvas:
    def __init__(self, band=None, seed=7, bg=None):
        self.im = Image.new("RGB", (W, H), SPACE)
        if bg is not None:
            self.im.paste(bg, (0, 0))
        else:
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
        self.im.paste(icon, (x, y), icon if icon.mode == "RGBA" else None)

    def paste_art(self, im, x, y):
        self.im.paste(im, (x, y))

    def dim_all(self, k):
        self.im = dim(self.im, k)
        self.d = ImageDraw.Draw(self.im)
        self.d.fontmode = "1"

    def save(self, path):
        self.im.resize((W * SCALE, H * SCALE), Image.NEAREST).save(path)


# ----------------------------------------------------- the frontend's icons

def tint(img, color):
    r, g, b, a = img.split()
    return Image.merge("RGBA", [r.point(lambda v: v * color[0] // 255), g.point(lambda v: v * color[1] // 255),
                                b.point(lambda v: v * color[2] // 255), a])


def solid_bbox(img, min_alpha):
    return img.getchannel("A").point(lambda v: 255 if v >= min_alpha else 0).getbbox()


def af_icon(kind, name, h, color):
    """feview.af_icon: the solid part of the Arcadeflow icon, h px high, in the colour."""
    path = os.path.join(METAPICS, kind, name + ".png")
    if not name or not os.path.isfile(path):
        return None
    src = Image.open(path).convert("RGBA")
    box = solid_bbox(src, 180)
    if not box:
        return None
    src = src.crop(box)
    w = min(max(1, round(src.width * h / src.height)), 4 * h)
    small = src.height <= 2 * h
    return tint(src.resize((w, h), Image.NEAREST if small else Image.LANCZOS), color)


def af_glyph(name, color):
    """feview.af_glyph: only the drawing of a genre icon, in the colour, at its own size."""
    path = os.path.join(METAPICS, "category", name + ".png")
    if not os.path.isfile(path):
        return None
    src = Image.open(path).convert("RGBA")
    out = Image.new("RGBA", src.size, (0, 0, 0, 0))
    px, po = src.load(), out.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            if a > 128 and r + g + b < 384:
                po[x, y] = color + (255,)
    box = out.getbbox()
    return out.crop(box) if box else None


def genre_icon(cat, h, color):
    import re
    if not cat:
        return None
    full = re.sub(r"[^a-z0-9]", "", cat.lower())
    main = re.sub(r"[^a-z0-9]", "", cat.split("/")[0].lower())
    for name in (full, main, main.rstrip("s")):
        img = af_glyph(name, color) if name else None
        if img and img.height > h:
            img = img.resize((max(1, round(img.width * h / img.height)), h), Image.LANCZOS)
        if img:
            return img
    return None


def control_icon(control, h, color):
    c = (control or "").lower()
    name = None
    if "trackball" in c:
        name = "control_trackball"
    elif "double joystick" in c:
        name = "control_double_joystick"
    elif "pedal" in c:
        name = "control_paddle_pedal"
    elif "paddle" in c or "dial" in c:
        name = "control_paddle"
    elif "analog" in c:
        name = "control_joystick_analog"
    elif "2-way" in c:
        name = "control_joystick_2way"
    elif "4-way" in c:
        name = "control_joystick_4way"
    elif "joystick" in c:
        name = "control_joystick_8way"
    return af_icon("overlaycontroller", name, h, color) if name else None


def buttons_icon(n, h, color):
    if n is None:
        return None
    name = str(n if n in (0, 1, 2, 3, 4, 6) else (6 if n >= 5 else 0))
    return af_icon("overlaybuttons", name, h, color)


PLAYER_ICON = (
    "......####......", ".....######.....", "....########....", "....########....",
    "....########....", "....########....", ".....######.....", "......####......",
    "................", "...##########...", "..############..", ".##############.",
    ".##############.", ".##############.", ".##############.", ".##############.",
)


def players_icon(color, h=16):
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    for y, row in enumerate(PLAYER_ICON):
        for x, c in enumerate(row):
            if c == "#":
                im.putpixel((x, y), color + (255,))
    if h != 16:
        im = im.resize((round(16 * h / 16), h), Image.LANCZOS)
    return im


def text_img(s, color):
    im = Image.new("RGBA", (8 * len(s), 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.text((0, 0), s, font=font(), fill=color)
    return im


def hcat(imgs, gap=3, height=None):
    imgs = [i for i in imgs if i is not None]
    height = height or max((i.height for i in imgs), default=1)
    out = Image.new("RGBA", (sum(i.width for i in imgs) + gap * max(0, len(imgs) - 1), height), (0, 0, 0, 0))
    x = 0
    for i in imgs:
        out.paste(i, (x, (height - i.height) // 2), i)
        x += i.width + gap
    return out


def draw_globe(lit, s, unlit=GREEN_DIM):
    """A globe made of green lines: outline, a meridian, the equator and two latitudes."""
    c = GREEN if lit else unlit
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = s - 1
    mx = round(s * 0.26)
    ly = round(s * 0.26)
    d.ellipse([0, 0, e, e], outline=c)
    d.ellipse([mx, 0, e - mx, e], outline=c)
    d.line([(0, e // 2), (e, e // 2)], fill=c)
    d.line([(e // 2, 0), (e // 2, e)], fill=c)
    inset = round(s * 0.12)
    d.line([(inset, ly), (e - inset, ly)], fill=c)
    d.line([(inset, e - ly), (e - inset, e - ly)], fill=c)
    if lit:  # the net: three bright nodes
        for p in ((inset, ly), (e - inset, e - ly), (e - inset - 1, ly)):
            d.point(p, fill=FG)
    return im


def globe(lit, size=16, unlit=GREEN_DIM):
    return draw_globe(lit, size, unlit)


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


def pads(lit=True, size=16):
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
    if size != 16:
        im = im.resize((size, size), Image.NEAREST)
    return im


def play_icon(color=GREEN, s=20):
    """The play triangle of the solo option, as in the frontend's own card."""
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    ImageDraw.Draw(im).polygon([(s * 0.2, 0), (s * 0.2, s - 1), (s - 1, (s - 1) / 2)], fill=color)
    return im


def star_icon(color=LIST_TEXT, s=22):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    cx = cy = (s - 1) / 2
    pts = []
    for i in range(10):
        r = (s - 1) / 2 * (1 if i % 2 == 0 else 0.42)
        a = -math.pi / 2 + i * math.pi / 5
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a) + 1))
    ImageDraw.Draw(im).polygon(pts, fill=color)
    return im


def plus_icon(color=LIST_TEXT, s=20, t=4):
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    m = (s - t) // 2
    d.rectangle([m, 0, m + t - 1, s - 1], fill=color)
    d.rectangle([0, m, s - 1, m + t - 1], fill=color)
    return im


def with_plus(icon, color=GREEN):
    """A small plus in the corner: the 'start a new one' version of an icon."""
    im = icon.copy()
    d = ImageDraw.Draw(im)
    x, y = im.width - 6, im.height - 6
    d.rectangle([x, y, x + 5, y + 5], fill=CARD)
    d.line([(x + 2, y), (x + 2, y + 5)], fill=color, width=2)
    d.line([(x, y + 2), (x + 5, y + 2)], fill=color, width=2)
    return im


def slots(cv, x, y, filled, total, w=6, h=9, gap=2, you=None):
    for i in range(total):
        cv.paste_icon(cabinet(i < filled, w, h), x + i * (w + gap), y)
    if you is not None:
        cv.d.rectangle([x + you * (w + gap) - 2, y - 2, x + you * (w + gap) + w + 1, y + h + 1], outline=PINK)


def title_band(path):
    if not path or not os.path.exists(path):
        return None
    real = Image.open(path).convert("RGB").resize((W, H), Image.NEAREST)
    return real.crop((0, 0, W, 30))


# ------------------------------------------------------- the info of a game

def info_items(g, h, link=None, label_color=None):
    """The icons of the frontend's info line for a game, as images (no text
    but the number of players). link: None, False (dim globe), True (lit)."""
    items = {}
    items["genre"] = genre_icon(g.get("genre"), h, CYAN)
    items["players"] = hcat([players_icon(GREEN, h), text_img(str(g["players"]), GREEN)], 2) if g.get("players") else None
    if link is not None:
        items["link"] = globe(link, h)
    if g.get("net"):
        items["net"] = pads(True, h)
    items["control"] = control_icon(g.get("control"), h, PINK)
    items["buttons"] = buttons_icon(g.get("buttons"), h, YELLOW)
    return items


def place(cv, imgs, x, y, gap=8, h=16):
    for img in imgs:
        if img is None:
            continue
        cv.paste_icon(img, x, y + (h - img.height) // 2)
        x += img.width + gap
    return x


def cab_row(cv, x, y, filled, total, you=None, w=5, h=8, gap=1, count=True, center_x1=None):
    """The cabinets of a link: lit ones are in, dim ones are free, the pink ring is this cabinet."""
    width = total * (w + gap) - gap
    slots(cv, x, y, filled, total, w, h, gap, you)
    if count:
        cv.text(x + width + 6, y, "%d/%d" % (filled, total), GREEN)
    return x + width


# ---------------------------------------------------------------- the lists

def list_screen(band, selected="dirtdvls"):
    g = GAMES[selected]
    elsewhere = {"daytona": 2, "ssf2tb": 3}   # the games other cabinets have open, and how many are in
    playing = selected in elsewhere
    cv = Canvas(band)
    cv.text(14, 36, "PLAYING NOW ELSEWHERE", COMMENT)
    y = 48
    for key, n in elsewhere.items():
        gg = GAMES[key]
        total = gg["link"]
        cv.paste_icon(globe(True, 12), 14, y - 2)
        sel = key == selected
        row_text(cv, 30, y, gg["title"], selected=sel, color=YELLOW, maxc=14)
        sw = total * 6 - 1
        slots(cv, 192 - sw, y, n, total, 5, 8, 1)
        y += 15
    cv.d.line([(14, y)] + [(190, y)], fill=LINE)
    y += 8
    rows = [("1944: THE LOOP MAST", None), ("3 COUNT BOUT", None), ("AEROFIGHTERS 2", None), ("DIRT DEVILS", "link"),
            ("SCUD RACE", "link"), ("X-MEN (6 PLAYERS)", "net"), ("ALIEN STORM", None)]
    for name, kind in rows:
        sel = selected == "dirtdvls" and name == "DIRT DEVILS"
        if kind == "link":
            cv.paste_icon(globe(False, 12), 14, y - 2)
        elif kind == "net":
            cv.paste_icon(pads(False, 12), 14, y - 2)
        row_text(cv, 30, y, name, selected=sel, maxc=19)
        y += 15
    cv.d.line([(194, 34), (194, 214)], fill=PINK)
    # the right panel: art, year and maker, icons, and who is in the link
    cv.box(206, 38, 306, 112, fill=PURPLE)
    cv.box(204, 36, 304, 110, fill=BG_DEEP, outline=PINK)
    cv.paste_art(stretch(snap(selected), 99, 73), 205, 37)
    cv.text(204, 120, "%s %s" % (g["year"], g["maker"]), YELLOW)
    it = info_items(g, 16, link=playing)
    place(cv, [it["genre"], it["players"], it["link"]], 204, 136, 10)
    place(cv, [it["control"], it["buttons"]], 204, 160, 12)
    if playing:
        cab_row(cv, 204, 186, elsewhere[selected], g["link"], you=None)
    cv.text(196, 226, "4/15", COMMENT)
    return cv


def row_text(cv, x, y, s, selected=False, color=LIST_TEXT, maxc=21):
    s = s[:maxc]
    if selected:
        cv.box(x - 3, y - 3, x + 8 * maxc + 2, y + 9, fill=(0x2c, 0x2c, 0x3c), outline=PINK)
        color = FG
    cv.text(x, y, s, color)


def grid_screen(band):
    cv = Canvas(band)
    tiles = [(26, 40), (116, 40), (206, 40), (26, 108), (116, 108), (206, 108)]
    items = [("3countb", None, 0), ("dirtdvls", "link", 0), ("ssf2tb", "linklive", 3), ("1944", None, 0),
             ("xmen", "net", 0), ("daytona", "linklive", 2)]
    sel_index = 2
    for i, ((x, y), (key, kind, n)) in enumerate(zip(tiles, items)):
        sel = i == sel_index
        cv.box(x, y, x + 80, y + 60, fill=BG_DEEP, outline=PINK if sel else LINE)
        cv.paste_art(stretch(snap(key), 79, 59), x + 1, y + 1)
        if kind in ("link", "linklive", "net"):
            ic = pads(True, 16) if kind == "net" else globe(kind == "linklive", 16)
            cv.box(x + 2, y + 2, x + 21, y + 21, fill=(0x10, 0x12, 0x18))
            cv.paste_icon(ic, x + 4, y + 4)
        if kind == "linklive":
            total = GAMES[key]["link"]
            cv.box(x + 1, y + 46, x + 79, y + 59, fill=(0x10, 0x12, 0x18))
            slots(cv, x + 4, y + 49, n, total, 5, 8, 1)
            cv.text(x + 76 - 24, y + 50, "%d/%d" % (n, total), GREEN)
    g = GAMES["ssf2tb"]
    cv.text(26, 177, g["title"], YELLOW)
    cv.text(26, 191, "%s %s" % (g["year"], g["maker"]), CYAN)
    it = info_items(g, 16, link=True)
    x = place(cv, [it["genre"], it["players"], it["link"]], 26, 205, 10)
    cab_row(cv, x + 2, 209, 3, 4, count=True, w=6, h=9, gap=2)
    place(cv, [it["control"], it["buttons"]], 190, 205, 12)
    return cv


def full_background(cv, key, link=None, filled=None, k=1.0, info=True):
    """The frontend's full screen mode: the art fills the screen, with the
    title, maker and the info icons at the bottom (info=False: only the art,
    for the screens that bring their own title and icons)."""
    g = GAMES[key]
    art = stretch(snap(key), W, H)
    # a dark gradient under the info line so it stays readable on any art
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for yy in range(150, H):
        sd.line([(0, yy), (W, yy)], fill=int(190 * (yy - 150) / (H - 150)))
    art = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), art, shade)
    cv.im.paste(art, (0, 0))
    cv.d = ImageDraw.Draw(cv.im)
    cv.d.fontmode = "1"
    if not info:
        if k != 1.0:
            cv.dim_all(k)
        return
    cv.text(16, 181, g["title"], YELLOW)
    cv.text(16, 196, "%s %s" % (g["year"], g["maker"]), CYAN)
    it = info_items(g, 14, link=link)
    x = place(cv, [it["genre"], it["players"], it.get("link"), it.get("net"), it["control"], it["buttons"]],
              16, 211, 9, 14)
    if filled is not None:
        cab_row(cv, x + 4, 214, filled, g["link"], count=True)
    if k != 1.0:
        cv.dim_all(k)


def full_screen_mark(playing=True):
    cv = Canvas()
    full_background(cv, "daytona", link=playing, filled=2 if playing else None)
    return cv


# -------------------------------------------------------------- the card

def tile(cv, x, y, s, icon, selected=False, art=None):
    """A tile of the frontend's card: the selected one is pink with a
    pixelated tint of the game art behind its icon."""
    if selected:
        cv.box(x + 2, y + 2, x + s + 1, y + s + 1, fill=PURPLE)
        mos = dim(stretch(art, 6, 6).resize((s - 1, s - 1), Image.NEAREST), 0.55)
        mos = Image.blend(mos, Image.new("RGB", mos.size, PINK), 0.35)
        cv.box(x, y, x + s, y + s, fill=CARD, outline=PINK)
        cv.paste_art(mos, x + 1, y + 1)
    else:
        cv.box(x, y, x + s, y + s, fill=CARD, outline=LINE)
    cv.paste_icon(icon, x + (s + 1 - icon.width) // 2, y + (s + 1 - icon.height) // 2)


def card(cv, key, tiles, selected, caption, caption_color=YELLOW, body=None, extra_h=0, size=40, gap=8):
    """The card over the dimmed full screen: title, a row of tiles (the
    selected one named under them) and whatever `body` draws below."""
    g = GAMES[key]
    n = len(tiles)
    w = n * size + (n - 1) * gap + 28
    x0 = (W - w) // 2
    y0, y1 = 34, 150 + extra_h
    cv.box(x0 + 3, y0 + 3, x0 + w + 3, y1 + 3, fill=PURPLE)
    cv.box(x0, y0, x0 + w, y1, fill=CARD, outline=PINK)
    cv.text(x0 + 12, y0 + 10, g["title"], YELLOW)
    ty = y0 + 28
    for i, icon in enumerate(tiles):
        tile(cv, x0 + 14 + i * (size + gap), ty, size, icon, i == selected, snap(key))
    cv.center(ty + size + 10, caption, caption_color, x0, x0 + w)
    if body:
        body(cv, x0, x0 + w, ty + size + 26)


def options_screen(joined):
    """Daytona USA: play solo, or a link (new, or joining the one that exists)."""
    cv = Canvas()
    full_background(cv, "daytona", link=joined, filled=2 if joined else None)
    cv.dim_all(0.45)
    if not joined:
        tiles = [play_icon(), globe(False, 24, GREEN_MID), star_icon(), plus_icon()]

        def body(c, x0, x1, y):
            total = GAMES["daytona"]["link"]
            width = total * 15 - 3
            slots(c, (x0 + x1 - width) // 2, y, 1, total, 12, 16, 3, you=0)
        card(cv, "daytona", tiles, 1, "LINK PLAY", body=body)
    else:
        tiles = [play_icon(), globe(True, 24), with_plus(globe(False, 24)), star_icon(), plus_icon()]

        def body(c, x0, x1, y):
            total = GAMES["daytona"]["link"]
            width = total * 15 - 3
            slots(c, (x0 + x1 - width) // 2, y, 2, total, 12, 16, 3, you=2)
        card(cv, "daytona", tiles, 1, "JOIN LINK", body=body)
    return cv


def person(lit, ring=False):
    im = players_icon(GREEN if lit else LINE, 16)
    return im


def netplay_slots(c, x0, x1, y, host=2, you=(2, 3), total=6):
    step = 28
    width = total * step - (step - 16)
    sx = (x0 + x1 - width) // 2
    for i in range(total):
        x = sx + i * step
        taken = i < host
        mine = i in you
        c.paste_icon(players_icon(GREEN if taken else (PINK if mine else LINE), 16), x, y)
        if mine:
            c.d.rectangle([x - 3, y - 3, x + 18, y + 18], outline=PINK)
        c.center(y + 22, str(i + 1), GREEN if taken else (PINK if mine else LINE), x - 4, x + 20)


def options_netplay_screen():
    """X-Men (6 players): this cabinet has two controls. Join a party and take the free pair."""
    cv = Canvas()
    full_background(cv, "xmen")
    cv.dim_all(0.45)
    tiles = [play_icon(), pads(True, 24), with_plus(pads(False, 24)), star_icon(), plus_icon()]

    def body(c, x0, x1, y):
        netplay_slots(c, x0, x1, y)
    card(cv, "xmen", tiles, 1, "NET PLAY", caption_color=CYAN, body=body, extra_h=14)
    return cv


# ----------------------------------------------------------- the lobby, etc

def lobby_screen(flags, starting=False):
    total = len(flags)
    ready = sum(flags)
    cv = Canvas()
    full_background(cv, "ssf2tb", info=False, k=0.2)
    g = GAMES["ssf2tb"]
    cv.center(16, g["title"], YELLOW)
    it = info_items(g, 14, link=True)
    imgs = [it["genre"], it["players"], it["link"], it["control"], it["buttons"]]
    wtot = sum(i.width for i in imgs if i) + 9 * (len([i for i in imgs if i]) - 1)
    place(cv, imgs, (W - wtot) // 2, 32, 9, 14)
    names = ["1", "2", "3", "4"]
    x0 = 28
    for i in range(total):
        x = x0 + i * 66
        lit = flags[i]
        cv.box(x, 72, x + 52, 140, fill=CARD, outline=GREEN if lit else LINE)
        cv.paste_icon(cabinet(lit, 22, 30), x + 15, 80)
        cv.center(118, "#" + names[i], GREEN if lit else LINE, x, x + 52)
        if i == 2:
            cv.d.rectangle([x - 3, 69, x + 55, 143], outline=PINK)
    cv.paste_icon(globe(True, 20), 118, 152)
    cv.text(146, 156, "%d/%d" % (ready, total), GREEN)
    if starting:
        cv.center(188, "STARTING 3", GREEN)
    else:
        cv.center(188, "WAITING", FG)
    cv.text(14, 226, "B:LEAVE", COMMENT)
    return cv


def netplay_screen():
    cv = Canvas()
    full_background(cv, "xmen", info=False, k=0.2)
    g = GAMES["xmen"]
    cv.center(14, g["title"], YELLOW)
    # what the game has and what this cabinet has: icons and numbers only
    row = [hcat([players_icon(GREEN, 14), text_img("6", GREEN)], 2), pads(True, 14), hcat([control_icon(g["control"], 14, PINK), text_img("2", PINK)], 3)]
    wtot = sum(i.width for i in row) + 14 * 2
    place(cv, row, (W - wtot) // 2, 30, 14, 14)
    rows = [("1", "CABINET-1", True), ("2", "CABINET-1", True), ("3", "", False), ("4", "", False), ("5", "", False), ("6", "", False)]
    y = 58
    for i, (p, who, taken) in enumerate(rows):
        sel = i in (2, 3)   # two controls here: the guest takes a pair of slots
        cv.box(36, y - 2, 284, y + 12, fill=(0x2c, 0x2c, 0x3c) if sel else CARD, outline=PINK if sel else LINE)
        cv.paste_icon(players_icon(GREEN if taken else (PINK if sel else LINE), 12), 44, y)
        cv.text(62, y + 2, p, GREEN if taken else (FG if sel else COMMENT))
        if taken:
            cv.paste_icon(cabinet(True, 8, 11), 90, y)
            cv.text(104, y + 2, who, FG)
        if sel:
            cv.paste_icon(cabinet(False, 8, 11), 90, y)
            cv.text(104, y + 2, "YOU", PINK)
        y += 20
    cv.text(14, 226, "A:JOIN  B:BACK", COMMENT)
    return cv


def transfer_screen(pct=62):
    cv = Canvas()
    full_background(cv, "daytona", info=False, k=0.2)
    g = GAMES["daytona"]
    cv.center(16, g["title"], YELLOW)
    it = info_items(g, 14, link=True)
    imgs = [it["genre"], it["players"], it["link"], it["control"], it["buttons"]]
    wtot = sum(i.width for i in imgs if i) + 9 * (len([i for i in imgs if i]) - 1)
    place(cv, imgs, (W - wtot) // 2, 190, 9, 14)
    # the host sends, this cabinet receives
    cv.paste_icon(cabinet(True, 26, 36), 62, 44)
    cv.paste_icon(cabinet(False, 26, 36), 232, 44)
    cv.d.rectangle([229, 41, 261, 83], outline=PINK)
    cv.center(86, "#1", GREEN, 52, 108)
    cv.center(86, "YOU", PINK, 222, 270)
    for i in range(6):
        cv.paste_icon(play_icon(GREEN if i <= 3 else GREEN_DIM, 12), 112 + i * 16, 56)
    cv.box(34, 112, 286, 130, fill=CARD, outline=LINE)
    cv.box(36, 114, 36 + int(248 * pct / 100), 128, fill=GREEN)
    cv.center(142, "%d%%   38/61 MB" % pct, FG)
    cv.center(160, "daytona.zip", COMMENT)
    cv.center(172, "model1io.zip", COMMENT)
    cv.text(22, 226, "B:CANCEL", COMMENT)
    return cv


def main():
    global ART
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    band = title_band(sys.argv[2] if len(sys.argv) > 2 else None)
    ART = sys.argv[3] if len(sys.argv) > 3 else os.environ.get("FE_ART", "")
    os.makedirs(out, exist_ok=True)
    shots = {
        "01-list-link-badges": list_screen(band, "dirtdvls"),
        "01b-list-link-playing": list_screen(band, "daytona"),
        "02-grid-link-badges": grid_screen(band),
        "02b-full-link-mark": full_screen_mark(True),
        "03-options-new-link": options_screen(joined=False),
        "04-options-join-link": options_screen(joined=True),
        "03b-options-netplay": options_netplay_screen(),
        "05-lobby-waiting": lobby_screen([True, True, True, False]),
        "06-lobby-all-here": lobby_screen([True, True, True, True], starting=True),
        "07-netplay-party": netplay_screen(),
        "08-rom-transfer": transfer_screen(),
    }
    for name, cv in shots.items():
        cv.save(os.path.join(out, name + ".png"))
        print(name)


if __name__ == "__main__":
    main()
