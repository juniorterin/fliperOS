#!/usr/bin/env python3
"""Mock-ups of the FliperOS Matchmaker (online play): a program of its own,
apart from the FliperOS frontend, with its lobby in the look of the
frontend's list mode.

Draws at the frontend's logical size (320x240) with its font (Press Start 2P,
8 px, no antialias) and palette, and scales 3x to 960x720 like the real
screenshots. Reuses the drawing pieces of the link mock-ups
(tools/link-tests/frontend-mockups.py). Animations are written as a GIF and a
sheet of frames, in whole-pixel steps (crisp on a CRT).

    python3 mockups.py OUT_DIR ART_DIR

ART_DIR holds the scraped art as snap_<system>_<game>.png and
logo_<system>_<game>.png. These are design sketches for discussion, not
Matchmaker code.
"""
import importlib.util
import os
import random
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
_spec = importlib.util.spec_from_file_location("fm", os.path.join(ROOT, "tools", "link-tests", "frontend-mockups.py"))
fm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fm)

W, H, SCALE = fm.W, fm.H, fm.SCALE
SPACE, BG, BG_DEEP, CARD, LINE = fm.SPACE, fm.BG, fm.BG_DEEP, fm.CARD, fm.LINE
COMMENT, FG, GREEN, PINK, CYAN = fm.COMMENT, fm.FG, fm.GREEN, fm.PINK, fm.CYAN
YELLOW, ORANGE, PURPLE, RED, LIST_TEXT = fm.YELLOW, fm.ORANGE, fm.PURPLE, fm.RED, fm.LIST_TEXT
SHADOW = (0x6A, 0x4C, 0x9C)
SEL_FILL = (0x2C, 0x2C, 0x3C)
SKIN_D = (0xC0, 0x7A, 0x40)
REAL_LIST = os.path.join(ROOT, "website", "public", "screenshots", "frontend", "list.webp")
THEME = os.path.join(ROOT, "fliperos-setup", "gui", "theme.py")
ART = ""

GAMES = {
    "sf2ce": dict(title="STREET FIGHTER II'", year="1992", maker="CAPCOM", snap="snap_mame_sf2ce.png",
                  logo="logo_mame_sf2ce.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2),
    "kof98": dict(title="THE KING OF FIGHTERS '98", year="1998", maker="SNK", snap="snap_mame_kof98.png",
                  logo="logo_mame_kof98.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=4, players=2),
    "mvsc2": dict(title="MARVEL VS. CAPCOM 2", year="2000", maker="CAPCOM", snap="snap_naomi_mvsc2.png",
                  logo="logo_naomi_mvsc2.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2),
    "sfiii3nr1": dict(title="STREET FIGHTER III 3RD STRIKE", year="1999", maker="CAPCOM", snap="snap_mame_sfiii3nr1.png",
                      logo="logo_mame_sfiii3nr1.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2),
    "garou": dict(title="GAROU: MARK OF THE WOLVES", year="1999", maker="SNK", snap="snap_mame_garou.png",
                  logo="logo_mame_garou.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=4, players=2),
    "samsho2": dict(title="SAMURAI SHODOWN II", year="1994", maker="SNK", snap="snap_mame_samsho2.png",
                    logo="logo_mame_samsho2.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=4, players=2),
    "ssf2t": dict(title="SUPER STREET FIGHTER II TURBO", year="1994", maker="CAPCOM", snap="snap_mame_ssf2t.png",
                  logo="logo_mame_ssf2t.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2),
    "xmvsf": dict(title="X-MEN VS. STREET FIGHTER", year="1996", maker="CAPCOM", snap="snap_mame_xmvsf.png",
                  logo="logo_mame_xmvsf.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2),
    "3countb": dict(title="3 COUNT BOUT", year="1993", maker="SNK", snap="snap_mame_3countb.png",
                    logo="logo_mame_3countb.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=4, players=2),
    "aof": dict(title="ART OF FIGHTING", year="1992", maker="SNK", snap="snap_mame_aof.png",
                logo="logo_mame_aof.png", genre="Fighter / Versus", control="joystick (8-way)", buttons=4, players=2),
    "xmen": dict(title="X-MEN (4 PLAYERS)", year="1992", maker="KONAMI", snap="", logo="logo_mame_xmen.png",
                 genre="Fighter / 2.5D", control="joystick (8-way)", buttons=3, players=4),
}
fm.GAMES.update(GAMES)

# The players of the mock-ups: NICK#tag (the tag is 4 lowercase base36
# characters), connection, ping, state, record and favourite characters.
PLAYERS = {
    "mango": dict(nick="MANGO", tag="a7k2", conn="cable", ping=28, state="looking", w=34, l=12, aw=210, al=98, chars="RYU KEN"),
    "tapir": dict(nick="TAPIR", tag="k8z1", conn="wifi", ping=112, state="looking", w=8, l=9, aw=40, al=51, chars="GUILE"),
    "zebra": dict(nick="ZEBRA", tag="5vw0", conn="cable", ping=46, state="looking", w=19, l=3, aw=77, al=20, chars="CHUN-LI"),
    "kiwi": dict(nick="KIWI", tag="0f3d", conn="wifi", ping=64, state="playing", vs="LYNX#9q2m", w=12, l=20, aw=66, al=70, chars="BLANKA"),
    "lynx": dict(nick="LYNX", tag="9q2m", conn="cable", ping=41, state="playing", vs="KIWI#0f3d", w=51, l=30, aw=300, al=188, chars="KEN SAGAT"),
    "guava": dict(nick="GUAVA", tag="3mxp", conn="cable", ping=19, state="download", pct=45, w=2, l=1, aw=2, al=1, chars="RYU"),
    "otter": dict(nick="OTTER", tag="b52c", conn="cable", ping=35, state="idle", w=5, l=5, aw=30, al=22, chars="DHALSIM"),
    "acai": dict(nick="ACAI", tag="77rt", conn="wifi", ping=150, state="idle", w=0, l=2, aw=0, al=2, chars="ZANGIEF"),
}


def tag_of(p):
    return "%s#%s" % (p["nick"], p["tag"])


def font(size=8):
    return ImageFont.truetype(fm.FONT, size)


# ------------------------------------------------------------ pixel icons
# Same format as fliperos-setup/gui/theme.py ICONS: one letter per pixel.

PAL = {"P": PURPLE, "K": PINK, "C": CYAN, "F": FG, "M": COMMENT, "G": GREEN, "O": ORANGE, "R": RED, "Y": YELLOW,
       "D": BG_DEEP, "L": LINE, "W": SKIN_D, "S": SHADOW}

ART16 = {
    "pass": """
................
.RR..........RR.
.RRR........RRR.
..RRR......RRR..
...RRR....RRR...
....RRR..RRR....
.....RRRRRR.....
......RRRR......
......RRRR......
.....RRRRRR.....
....RRR..RRR....
...RRR....RRR...
..RRR......RRR..
.RRR........RRR.
.RR..........RR.
................
""",
}

ART8 = {
    "wifi": """
.YYYYYY.
Y......Y
..YYYY..
.Y....Y.
...YY...
........
...YY...
........
""",
    "cable": """
.GGGGGG.
.GFGFGG.
.GGGGGG.
.GGGGGG.
..GGGG..
...GG...
...GG...
...GG...
""",
    "shield": """
GGGGGGGG
GGGGGGDG
GGGGGDGG
GDGGDGGG
GGDDGGGG
.GGGGGG.
..GGGG..
...GG...
""",
    "check": """
........
.......G
......GG
.....GG.
G...GG..
GG.GG...
.GGG....
..G.....
""",
    "cross": """
RR....RR
RRR..RRR
.RRRRRR.
..RRRR..
..RRRR..
.RRRRRR.
RRR..RRR
RR....RR
""",
    "down": """
...OO...
...OO...
...OO...
.OOOOOO.
..OOOO..
...OO...
........
.OOOOOO.
""",
    "eye": """
........
..CCCC..
.C....C.
C..CC..C
C..CC..C
.C....C.
..CCCC..
........
""",
    "replay": """
..CCCC..
.C....C.
C..C...C
C..CC..C
C..CCC.C
C..CC..C
.C.C..C.
..CCCC..
""",
    "clock": """
..MMMM..
.M..F.M.
M...F..M
M...FF.M
M......M
M......M
.M....M.
..MMMM..
""",
    "person": """
...GG...
..GGGG..
..GGGG..
...GG...
........
.GGGGGG.
GGGGGGGG
GGGGGGGG
""",
}


def from_art(art, pal=None):
    rows = art.strip("\n").split("\n")
    pal = pal or PAL
    im = Image.new("RGBA", (len(rows[0]), len(rows)), (0, 0, 0, 0))
    for y, row in enumerate(rows):
        for x, c in enumerate(row):
            if c in pal:
                im.putpixel((x, y), pal[c] + (255,))
    return im


def recolor(im, color):
    out = im.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            if px[x, y][3]:
                px[x, y] = color + (255,)
    return out


def icon16(name, k=1):
    im = from_art(ART16[name])
    return im.resize((16 * k, 16 * k), Image.NEAREST) if k != 1 else im


def icon8(name, color=None, k=1):
    im = from_art(ART8[name])
    if color:
        im = recolor(im, color)
    return im.resize((im.width * k, im.height * k), Image.NEAREST) if k != 1 else im


# The fist bump: the 16-bit sprites of tools/matchmaker/fists.py (ten
# options; FIST is the one the screens use).
sys.path.insert(0, HERE)
import fists  # noqa: E402
import iconlab  # noqa: E402

FIST = int(os.environ.get("MM_FIST", "3"))   # the user chose 3: boxing gloves, red and blue
FIST_VARIANTS = fists.OPTIONS


def fist_pair(variant=None):
    """The gloves with the spark over them, and as much room under them as the
    spark takes above: centred on anything, the gloves are in the middle."""
    p = fists.pair(variant or FIST)
    top = 12          # fists.pair puts the fists 12 px down, under the effect
    out = Image.new("RGBA", (p.width, p.height + top), (0, 0, 0, 0))
    out.paste(p, (0, 0), p)
    return out


def pixel_shrink(im, w, h):
    """Smaller copy of a sprite that keeps its own colours (no blur)."""
    pal = sorted({im.getpixel((x, y))[:3] for x in range(im.width) for y in range(im.height) if im.getpixel((x, y))[3]})
    sm = im.resize((w, h), Image.LANCZOS)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    for y in range(h):
        for x in range(w):
            r, g, b, a = sm.getpixel((x, y))
            if a >= 110:
                out.putpixel((x, y), min(pal, key=lambda c: (c[0] - r) ** 2 + (c[1] - g) ** 2 + (c[2] - b) ** 2) + (255,))
    return out


_fist_cache = {}


def fist_icon(w, variant=None):
    key = (w, variant or FIST)
    if key not in _fist_cache:
        p = fist_pair(variant)
        _fist_cache[key] = p if w >= p.width else pixel_shrink(p, w, max(1, round(w * p.height / p.width)))
    return _fist_cache[key]


def fist(k=1, name=None):
    """The fist bump at the size of an icon: k=1 about 17 px high, 2 for a tile, 4 the full sprite."""
    return fist_icon({1: 30, 2: 38, 4: 70}.get(k, 30))


# Icons that sit side by side share one height: 10 px in a line of text (the
# list rows, the card's counters), 14 px in the rows of the right panel.
ROW_ICON, PANEL_ICON = 10, 14


# The tiles of a card: every icon as high as the others (TILE_ICON), the
# gloves as wide as the tile lets them (they are wider than high).
TILE, TILE_ICON = 44, 32


def fist_tile():
    return fist_icon(TILE - 6)


def fist_h(h):
    """The gloves alone (no spark), h px high, for a row next to other icons."""
    key = ("h", h, FIST)
    if key not in _fist_cache:
        p = fists.pair(FIST, fx=False)
        _fist_cache[key] = pixel_shrink(p, round(p.width * h / p.height), h)
    return _fist_cache[key]


# Two solid gloves side by side weigh more than one icon of the same height:
# next to other icons they are this much of their height.
GLOVE_K = 0.72


def fist_beside(h):
    """The gloves to sit next to h-px icons, looking as big as they do."""
    return fist_h(round(h * GLOVE_K))


def fist_small(color=PINK):
    """The fist bump for a line of text, next to the 10 px row icons."""
    return fist_beside(ROW_ICON)


def fist_half(side, k):
    """One fist of the bump, for the DUEL! screen."""
    opt = fists.OPTIONS[FIST]
    im = opt["left"]() if side == "left" else opt["right"]().transpose(Image.FLIP_LEFT_RIGHT)
    return im.resize((im.width * k, im.height * k), Image.NEAREST)


def planet(lit=True, s=12, color=CYAN):
    """The online mark: a planet with a ring (the LAN link is the green globe)."""
    c = color if lit else (0x3A, 0x6A, 0x78)
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    e = s - 1
    ry0, ry1 = round(s * 0.40), round(s * 0.66)
    d.ellipse([0, ry0, e, ry1], outline=c)                      # the ring, behind
    px0, px1 = round(s * 0.2), e - round(s * 0.2)
    d.ellipse([px0, round(s * 0.08), px1, e - round(s * 0.08)], fill=CYAN if lit else BG_DEEP, outline=c)
    d.arc([0, ry0, e, ry1], 0, 180, fill=c if not lit else FG)  # the ring, in front
    if lit:
        d.point((px0 + 2, round(s * 0.3)), fill=FG)
        d.point((px1 - 2, round(s * 0.25)), fill=BG_DEEP)
    return im


def live_person(s=12):
    """Online mark variant: a person with a red 'live' dot."""
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    im.paste(fm.players_icon(CYAN, s - 2), (0, 2), fm.players_icon(CYAN, s - 2))
    d = ImageDraw.Draw(im)
    d.ellipse([s - 5, 0, s - 1, 4], fill=RED)
    return im


def ping_bars(ms, lit=True):
    if ms <= 40:
        color, n = GREEN, 4
    elif ms <= 80:
        color, n = YELLOW, 3
    elif ms <= 130:
        color, n = ORANGE, 2
    else:
        color, n = RED, 1
    im = Image.new("RGBA", (11, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i in range(4):
        h = 2 * (i + 1)
        d.rectangle([i * 3, 8 - h, i * 3 + 1, 7], fill=color if (lit and i < n) else LINE)
    return im


def ping_color(ms):
    return GREEN if ms <= 40 else YELLOW if ms <= 80 else ORANGE if ms <= 130 else RED


def conn_icon(p):
    return iconlab.chosen("cable", 10) if p["conn"] == "cable" else iconlab.chosen("wifi", 10)


def direct_icon(color=GREEN):
    im = Image.new("RGBA", (12, 7), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(1, 3), (10, 3)], fill=color)
    d.polygon([(0, 3), (3, 0), (3, 6)], fill=color)
    d.polygon([(11, 3), (8, 0), (8, 6)], fill=color)
    return im


def relay_icon(color=ORANGE):
    im = Image.new("RGBA", (15, 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.line([(0, 5), (4, 5)], fill=color)
    d.line([(10, 5), (14, 5)], fill=color)
    d.rectangle([5, 1, 9, 7], outline=color)
    d.line([(6, 3), (8, 3)], fill=color)
    return im


def people_icon(color=CYAN, h=16):
    a = fm.players_icon(color, h)
    b = fm.players_icon(tuple(max(0, v - 70) for v in color), h)
    im = Image.new("RGBA", (h + h // 2, h), (0, 0, 0, 0))
    im.paste(b, (h // 2, 0), b)
    im.paste(a, (0, 0), a)
    return im


# ------------------------------------------------------------ text helpers

def big_text(cv, x, y, s, color, size=16, shadow=SHADOW, off=1):
    f = font(size)
    cv.d.text((x + off, y + off), s, font=f, fill=shadow)
    cv.d.text((x, y), s, font=f, fill=color)


def big_center(cv, y, s, color, size=16, x0=0, x1=W, **kw):
    big_text(cv, x0 + (x1 - x0 - size * len(s)) // 2, y, s, color, size, **kw)


def gradient_title(img, s, y, size=16):
    """The frontend's title: pink on top, light in the middle, cyan below, a purple shadow."""
    f = font(size)
    w = size * len(s)
    x = (W - w) // 2
    mask = Image.new("L", (w, size + 2), 0)
    md = ImageDraw.Draw(mask)
    md.fontmode = "1"
    md.text((0, 0), s, font=f, fill=255)
    rows = [PINK] * (size // 3) + [(0xF0, 0xD8, 0xF8)] * (size // 3) + [CYAN] * (size + 2 - 2 * (size // 3))
    colour = Image.new("RGB", mask.size)
    cd = ImageDraw.Draw(colour)
    for yy, c in enumerate(rows):
        cd.line([(0, yy), (w, yy)], fill=c)
    shadow = Image.new("RGB", mask.size, SHADOW)
    img.paste(shadow, (x + 1, y + 2), mask)
    img.paste(colour, (x, y), mask)


_band_cache = {}


def band(title="MATCHMAKER"):
    """The title band of the list screens: the rainbow bars of the real
    frontend (cut from its screenshot) and the title in its style."""
    if title in _band_cache:
        return _band_cache[title]
    real = Image.open(REAL_LIST).convert("RGB").resize((W, H), Image.NEAREST).crop((0, 0, W, 30))
    out = Image.new("RGB", (W, 30), SPACE)
    rnd = random.Random(3)
    d = ImageDraw.Draw(out)
    for _ in range(14):
        d.point((rnd.randrange(W), rnd.randrange(30)), fill=rnd.choice([LINE, COMMENT]))
    strip = real.crop((40, 0, 41, 30))
    tw = 16 * len(title)
    left_end = (W - tw) // 2 - 8
    right_start = (W + tw) // 2 + 8
    for x in list(range(16, left_end)) + list(range(right_start, 304)):
        out.paste(strip, (x, 0))
    gradient_title(out, title, 9)
    _band_cache[title] = out
    return out


def canvas(title="MATCHMAKER", seed=7):
    return fm.Canvas(band(title), seed=seed)


def art_box(cv, key, x0=204, y0=36, x1=304, y1=110):
    """The art of the list's right panel: pink frame and purple shadow."""
    cv.box(x0 + 2, y0 + 2, x1 + 2, y1 + 2, fill=PURPLE)
    cv.box(x0, y0, x1, y1, fill=BG_DEEP, outline=PINK)
    cv.paste_art(game_art(key, x1 - x0 - 1, y1 - y0 - 1), x0 + 1, y0 + 1)


def game_art(key, w, h):
    g = GAMES[key]
    try:
        im = fm.snap(key)
    except OSError:          # a scrape that saved a web page instead of a picture
        im = None
    if im is not None:
        return fm.stretch(im, w, h)
    out = Image.new("RGB", (w, h), BG_DEEP)
    lg = logo(key, w - 8, h - 8)
    if lg is not None:
        out.paste(lg, ((w - lg.width) // 2, (h - lg.height) // 2), lg)
    return out


def logo(key, w, h):
    g = GAMES.get(key) or {}
    path = os.path.join(ART, g.get("logo", "")) if ART else ""
    if not path or not os.path.isfile(path):
        return None
    im = Image.open(path).convert("RGBA")
    k = min(w / im.width, h / im.height)
    return im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)


# ------------------------------------------------------------ the list mode

LX, LY, PITCH = 16, 38, 14


def list_chrome(cv, counter, thumb=(36, 150)):
    """The list's scroll bar (pink thumb on the dark track) and the counter."""
    cv.box(194, 36, 197, 214, fill=LINE)
    cv.box(194, thumb[0], 197, thumb[1], fill=PINK)
    cv.text(190 - 8 * len(counter), 220, counter, COMMENT)


def sel_box(cv, y):
    cv.box(14, y - 1, 192, y + 11, fill=PURPLE)
    cv.box(12, y - 3, 190, y + 9, fill=SEL_FILL, outline=PINK)


def header_row(cv, y, text, color=COMMENT, icon=None):
    x = LX - 2
    if icon is not None:
        cv.paste_icon(icon, x, y + (8 - icon.height) // 2)
        x += icon.width + 4
    cv.text(x, y, text, color)


def player_row(cv, y, p, selected=False, slot=None, you=False):
    """A player in the list: connection, NICK#tag, ping at the end."""
    if selected:
        sel_box(cv, y)
    x = LX - 2
    if slot is not None:
        cv.text(x, y, str(slot), GREEN if not you else PINK)
        x += 12
    ic = conn_icon(p)
    cv.paste_icon(ic, x, y)
    x += 12
    name = "YOU" if you else tag_of(p)
    downloading = p.get("state") == "download"
    color = PINK if you else (FG if selected else (ORANGE if downloading else LIST_TEXT))
    cv.text(x, y, name, color)
    if downloading:
        cv.text(190 - 8 * 3 - 2, y, "%d%%" % p["pct"], ORANGE)
    else:
        cv.paste_icon(ping_bars(p["ping"]), 178, y)


def game_row(cv, y, key, selected=False, live=None, looking=0, have=True, size=None, maxc=17):
    g = GAMES[key]
    if selected:
        sel_box(cv, y)
    cv.paste_icon(planet(live is not None and live > 0, 10), LX - 2, y - 1)
    title = g["title"][:maxc]
    if not have:
        color = FG if selected else COMMENT
    elif live:
        color = FG if selected else YELLOW
    else:
        color = FG if selected else LIST_TEXT
    cv.text(LX + 12, y, title, color)
    right = 190
    if not have and size:
        s = size
        cv.text(right - 8 * len(s), y, s, ORANGE)
        right -= 8 * len(s) + 2
        dn = iconlab.chosen("rom", 10)
        cv.paste_icon(dn, right - 8, y)
        return
    if live:
        s = str(live)
        cv.text(right - 8 * len(s), y, s, CYAN)
        right -= 8 * len(s) + 1
        pi = fm.players_icon(CYAN, 8)
        cv.paste_icon(pi, right - 8, y)
        right -= 10
        if looking:
            fs = fist_small()
            cv.paste_icon(fs, right - fs.width - 1, y)


def panel_game(cv, key, live=0, looking=0, have=True, size=None):
    g = dict(dict(year="", maker="", genre="Fighter / Versus", control="joystick (8-way)", buttons=6, players=2), **GAMES[key])
    art_box(cv, key)
    cv.text(204, 120, "%s %s" % (g["year"], g["maker"]), YELLOW)
    it = fm.info_items(g, 14)
    fm.place(cv, [it["genre"], it["players"]], 204, 134, 10, 14)
    fm.place(cv, [it["control"], it["buttons"]], 204, 154, 10, 14)
    y = 178
    if live:
        g = planet(True, PANEL_ICON)
        cv.paste_icon(g, 204, y)
        cv.text(204 + g.width + 4, y + 3, str(live), CYAN)
        if looking:
            f = fist_beside(PANEL_ICON)
            fx = 204 + g.width + 4 + 8 * len(str(live)) + 10
            cv.paste_icon(f, fx, y + (g.height - f.height) // 2)
            cv.text(fx + f.width + 4, y + 3, str(looking), PINK)
    if not have:
        cv.paste_icon(iconlab.chosen("rom", 10), 204, 198)
        cv.text(216, 198, size or "", ORANGE)
        cv.text(216 + 8 * (len(size or "") + 1), 198, "DIRECT", COMMENT)


def panel_player(cv, p, key, state_line=None):
    art_box(cv, key)
    cv.text(204, 120, tag_of(p), YELLOW)
    mid(cv, conn_icon(p), 204, 136)
    mid(cv, ping_bars(p["ping"]), 216, 136)
    cv.text(232, 136, "%dMS" % p["ping"], ping_color(p["ping"]))
    wl(cv, 204, 150, p["w"], p["l"])
    st = p.get("state")
    if state_line:
        text, color = state_line
    elif st == "looking":
        text, color = "LOOKING", PINK
    elif st == "playing":
        text, color = "VS " + p["vs"], YELLOW
    elif st == "download":
        text, color = "GETTING ROM", ORANGE
    else:
        text, color = "IDLE", COMMENT
    cv.text(204, 168, text, color)



# The groups of the lists work like the frontend's clone groups
# (fliperos-setup/gui/feview.py list_row / expand_mark / group_header): the
# parent row has the [+] (open: [-], pink) box, the name and the count at the
# right end; the rows inside it are 26 px in, hung on an L-shaped rail.
LXX, LEND = 16, 190
# The rows inside a group are IND px in (the frontend's clones use 26: narrower here, more room for the names).
IND = 14


def rt(i):
    """The top of list row i (the text sits 2 px lower)."""
    return 36 + 14 * i


def expand_mark(cv, x, y, opened):
    c = PINK if opened else COMMENT
    mark = Image.new("RGBA", (10, 10), BG_DEEP + (255,))
    d = ImageDraw.Draw(mark)
    d.rectangle([0, 0, 9, 9], outline=c)
    d.rectangle([2, 4, 7, 5], fill=c)
    if not opened:
        d.rectangle([4, 2, 5, 7], fill=c)
    mark.putalpha(190 if opened else 120)
    cv.im.paste(mark, (x, y), mark)


def frame_on(cv, x, ry):
    """The chosen row: from its text to the end of the list, pink, with the purple shadow."""
    cv.box(x - 2, ry + 2, LEND + 2, ry + 14, fill=PURPLE)
    cv.box(x - 4, ry, LEND, ry + 12, fill=SEL_FILL, outline=PINK)


def group_row(cv, ry, name, count, opened, selected=False):
    x = LXX + 14
    if selected:
        frame_on(cv, x, ry)
    expand_mark(cv, LXX, ry + 1, opened)
    color = FG if opened or selected else COMMENT
    cv.text(x, ry + 2, name, color)
    txt = str(count)
    cv.text(LEND - 6 - 8 * len(txt), ry + 2, txt, color)


def mid(cv, icon, x, text_y):
    """An icon on the middle of an 8 px line of text that starts at text_y."""
    cv.paste_icon(icon, x, text_y + (8 - icon.height) // 2)


def fade(color, bg, k):
    """The colour as if drawn at k opacity over bg."""
    return tuple(round(c * k + b * (1 - k)) for c, b in zip(color, bg))


def rail(cv, ry, last):
    cv.d.line([(LXX + 5, ry - 3), (LXX + 5, ry + (5 if last else 14))], fill=LINE)
    cv.d.line([(LXX + 5, ry + 5), (LXX + 11, ry + 5)], fill=LINE)


def rail2(cv, ry, last, outer):
    """The rail of the second level (the players inside a match or a party);
    outer: the first level's rail goes on past them (more matches below)."""
    if outer:
        cv.d.line([(LXX + 5, ry - 3), (LXX + 5, ry + 14)], fill=LINE)
    cv.d.line([(LXX + IND + 5, ry - 3), (LXX + IND + 5, ry + (5 if last else 14))], fill=LINE)
    cv.d.line([(LXX + IND + 5, ry + 5), (LXX + IND + 11, ry + 5)], fill=LINE)


def sub_row(cv, ry, text, right, opened, last, selected=False, right_color=YELLOW):
    """A match or a party inside PLAYING / IN PARTY: its [+] box, the names and
    the score (or the places taken), the players under it when open."""
    rail(cv, ry, last)
    x = LXX + IND
    if selected:
        frame_on(cv, x + 14, ry)
    expand_mark(cv, x, ry + 1, opened)
    cv.text(x + 14, ry + 2, text, FG if opened or selected else COMMENT)
    cv.text(LEND - 6 - 8 * len(right), ry + 2, right, right_color)


def child_player(cv, ry, p, last, selected=False, slot=None, you=False, free=False, level=1, outer=False):
    if level == 2:
        rail2(cv, ry, last, outer)
        x = LXX + 2 * IND
    else:
        rail(cv, ry, last)
        x = LXX + IND
    if selected:
        frame_on(cv, x, ry)
    if slot is not None:
        cv.text(x, ry + 2, str(slot), PINK if you else (LINE if free else GREEN))
        x += 12
    if free:
        cv.paste_icon(fm.players_icon(LINE, 8), x, ry + 2)
        cv.text(x + 12, ry + 2, "FREE", LINE)
        return
    mid(cv, conn_icon(p), x, ry + 2)
    downloading = p.get("state") == "download"
    if you:
        color = PINK
    elif selected:
        color = FG
    elif downloading:
        color = ORANGE
    else:
        color = CYAN
    if you:
        cv.text(x + 12, ry + 2, "YOU", color)
    else:
        # the #tag a little transparent: the nickname stands out, the code is there
        cv.text(x + 12, ry + 2, p["nick"], color)
        bg = SEL_FILL if selected else SPACE
        cv.text(x + 12 + 8 * len(p["nick"]), ry + 2, "#" + p["tag"], fade(color, bg, 0.5))
    if downloading:
        cv.text(LEND - 6 - 24, ry + 2, str(p["pct"]) + "%", ORANGE)
    else:
        mid(cv, ping_bars(p["ping"]), LEND - 6 - 11, ry + 2)


def child_game(cv, ry, key, last, selected=False, live=0, looking=0, have=True, size=None):
    rail(cv, ry, last)
    x = LXX + IND
    if selected:
        frame_on(cv, x, ry)
    cv.paste_icon(planet(bool(live), 10), x, ry + 1)
    x += 12
    right = LEND - 6
    tail = []
    if not have and size:
        tail = [iconlab.chosen("rom", 10), fm.text_img(size, ORANGE)]
    elif live:
        tail = ([fist_small()] if looking else []) + [fm.players_icon(CYAN, 8), fm.text_img(str(live), CYAN)]
    row = fm.hcat(tail, 1) if tail else None
    room = right - x - (row.width + 4 if row else 0)
    g = GAMES[key]
    color = FG if selected else (COMMENT if not have else YELLOW if live else CYAN)
    cv.text(x, ry + 2, g["title"][:max(1, room // 8)], color)
    if row:
        cv.paste_icon(row, right - row.width, ry + 2 + (8 - row.height) // 2)


def title_row(cv, ry, text, right=None, right_color=CYAN, icon=None):
    x = LXX - 2
    if icon is not None:
        cv.paste_icon(icon, x, ry + 1)
        x += icon.width + 4
    room = (LEND - 6 - x) // 8 - (len(right) + 1 if right else 0)
    cv.text(x, ry + 2, text[:room], YELLOW)
    if right:
        cv.text(LEND - 6 - 8 * len(right), ry + 2, right, right_color)


# ------------------------------------------------------------ 1: home

# One page per emulator or core, as the frontend has one per system: the band
# says which one, left and right go to the next. On each page the games with
# people online come first (ONLINE NOW, open like the frontend's RECENT), then
# all the others. A game with no scoreboard (no win detector, as on Fightcade)
# is party only: no gloves, no duel, no wins and losses (X-Men here).
GAMES.update({
    "cvs2": dict(title="CAPCOM VS. SNK 2"), "ggxx": dict(title="GUILTY GEAR XX"), "doa2": dict(title="DEAD OR ALIVE 2"),
    "meltyb": dict(title="MELTY BLOOD"), "kofxi": dict(title="THE KING OF FIGHTERS XI"), "vf4": dict(title="VIRTUA FIGHTER 4"),
    "sfz3": dict(title="STREET FIGHTER ZERO 3"), "tekken": dict(title="TEKKEN"),
})
PAGES = {
    "GROOVYMAME": dict(online=[("sf2ce", 5, 2, True, None), ("kof98", 3, 1, True, None), ("xmen", 3, 0, True, None)],
                       games=["3countb", "aof", "garou", "samsho2", "sfiii3nr1", "ssf2t", "xmvsf"], total=38),
    "FLYCAST DOJO": dict(online=[("mvsc2", 2, 1, False, "88M")],
                         games=["cvs2", "doa2", "ggxx", "kofxi", "meltyb", "sfz3", "vf4", "tekken"], total=12),
}
HOME_ONLINE = PAGES["GROOVYMAME"]["online"]


def game_row(cv, ry, key, selected=False):
    """A game of the page, outside any group: the online mark (dim: nobody on it now) and its title."""
    x = LXX
    if selected:
        frame_on(cv, x + 14, ry)
    cv.paste_icon(planet(False, ROW_ICON), x, ry + 1)
    g = GAMES[key]
    cv.text(x + 14, ry + 2, g["title"][:(LEND - 6 - x - 14) // 8], FG if selected else LIST_TEXT)


def home_page(emu, selected):
    page = PAGES[emu]
    cv = canvas(emu)
    i = 0
    online = page["online"]
    group_row(cv, rt(i), "ONLINE NOW", len(online), True)
    i += 1
    for n, (key, live, looking, have, size) in enumerate(online):
        child_game(cv, rt(i), key, n == len(online) - 1, key == selected, live, looking, have, size)
        i += 1
    for key in page["games"]:
        if rt(i) > 204:
            break
        game_row(cv, rt(i), key, key == selected)
        i += 1
    keys = [k for k, *_ in online] + page["games"]
    list_chrome(cv, "%d/%d" % (keys.index(selected) + 1, page["total"]), thumb=(36, 120))
    sel = next((r for r in online if r[0] == selected), None)
    if sel:
        panel_game(cv, selected, sel[1], sel[2], sel[3], sel[4])
    else:
        panel_game(cv, selected)
    return cv


def home_screen(selected="sf2ce"):
    emu = next(e for e, pg in PAGES.items() if selected in [k for k, *_ in pg["online"]] + pg["games"])
    return home_page(emu, selected)


# The page switch is the frontend's own (fliperos-frontend switch_category /
# pick_category, feview.draw_ribbon / leave / enter, the LIST mode's "doors"),
# with its numbers: the GAME LIST strip slides on a spring (omega 16), the
# page is picked after PICK_WAIT, the strip holds RIBBON_HOLD with the count
# and fades in RIBBON_FADE over the old page; then the doors: the old page
# opens (the list to the left, the panel to the right) and the new one closes
# piece by piece (the title from the top, the rows and the bar from the left,
# the panel from the right).
PICK_WAIT, RIBBON_HOLD, RIBBON_FADE = 0.6, 0.8, 0.25
INTRO, INTRO_EXIT, INTRO_PART = 0.85, 0.25, 0.35
INTRO_DELAY = {"title": 0.0, "chrome": 0.05, "row": 0.06, "picture": 0.1, "icons": 0.26, "text": 0.3}
INTRO_STEP = {"row": 0.022}
RIBBON_STEP, RIBBON_WIDE, DOOR_CUT = 112, 2.2, 197
STRIP_PAGES = [("FBNEO", 210), ("GROOVYMAME", 38), ("FLYCAST DOJO", 12), ("GENESIS PLUS GX", 64), ("SNES9X", 120)]

import math  # noqa: E402

_TINY = None


def tiny_text(img, cx, y, text, color):
    """The frontend's 3x5 font (fliperos-setup/gui/tiny.py), centred on cx."""
    global _TINY
    if _TINY is None:
        src = open(os.path.join(ROOT, "fliperos-setup", "gui", "tiny.py"), encoding="utf-8").read()
        _TINY = dict(re.findall(r'"(.)": "([01]{15})"', src))
    w = len(text) * 4 - 1
    x = round(cx - w / 2)
    for ch in text:
        g = _TINY.get(ch)
        if g:
            for i, bit in enumerate(g):
                if bit == "1":
                    img.putpixel((x + i % 3, y + i // 3), color)
        x += 4


def spring_pos(t, omega=16.0):
    """feview.spring from 0 to 1 started at t=0: the exact critically damped motion."""
    if t <= 0:
        return 0.0
    return 1 - (1 + omega * t) * math.exp(-omega * t)


def wordmark(name, w, h):
    """An emulator's name as a logo for its tile (the frontend's tiles show the system logo)."""
    words = name.split(" ")
    lines = [" ".join(words[:2]), " ".join(words[2:])] if len(words) > 2 else ([name] if len(name) <= 10 else words)
    lines = [ln for ln in lines if ln]
    tw = max(8 * len(ln) for ln in lines)
    th = 10 * len(lines)
    im = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    for i, ln in enumerate(lines):
        x = (tw - 8 * len(ln)) // 2
        d.text((x + 1, i * 10 + 1), ln, font=font(8), fill=SHADOW)
        d.text((x, i * 10), ln, font=font(8), fill=YELLOW if i == 0 else CYAN)
    k = min(w / tw, h / th)
    if k >= 1:
        k = int(k)
        return im.resize((tw * k, th * k), Image.NEAREST)
    return im.resize((max(1, round(tw * k)), max(1, round(th * k))), Image.LANCZOS)


def draw_strip(base, pos, alpha=1.0):
    """feview.draw_ribbon: the GAME LIST band with the tiles, the one in the middle grown."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    band_y, band_h = 70, 104
    d.rectangle([0, band_y, W - 1, band_y + band_h - 1], fill=BG_DEEP + (255,))
    d.line([(0, band_y), (W, band_y)], fill=PINK + (255,))
    d.line([(0, band_y + band_h - 1), (W, band_y + band_h - 1)], fill=PINK + (255,))
    tiny_text(layer, W // 2, band_y + 5, "GAME LIST", COMMENT + (255,))
    cur = 1                      # the page the list shows (GROOVYMAME); pos goes from it to the next
    tiles = []
    for k in range(-3, 4):
        dpos = (cur + k) - (cur + pos)
        if abs(dpos) > 2.6:
            continue
        tiles.append((abs(dpos), dpos, (cur + k) % len(STRIP_PAGES)))
    for dist, dd, idx in sorted(tiles, reverse=True):
        name, _ = STRIP_PAGES[idx]
        sf = 32 + 24 / (1 + 2 * dist * dist)
        on = dist < 0.5
        wf = max(sf, min(RIBBON_WIDE * sf, sf * 1.9))
        cx, cy = W / 2 + dd * RIBBON_STEP, band_y + 48
        x, y = round(cx - wf / 2), round(cy - sf / 2)
        w, size = round(cx + wf / 2) - x, round(cy + sf / 2) - y
        if on:
            d.rectangle([x + 2, y + 2, x + w + 1, y + size + 1], fill=PURPLE + (255,))
            mos = mosaic(max(w, size), seed=9).resize((w, size), Image.NEAREST).convert("RGBA")
            layer.paste(mos, (x, y))
        else:
            d.rectangle([x, y, x + w - 1, y + size - 1], fill=BG_DEEP + (255,))
        lit = max(0.0, 1.0 - dist)
        edge = tuple(round(a2 + (b2 - a2) * lit) for a2, b2 in zip(LINE, PINK))
        d.rectangle([x, y, x + w - 1, y + size - 1], outline=edge + (255,), width=2 if on else 1)
        logo_im = wordmark(name, round(wf * 0.8), round(sf * 0.8))
        if dist > 0.05:
            a = logo_im.getchannel("A").point(lambda v, k=(255 - 145 * min(1.0, dist)) / 255: int(v * k))
            logo_im.putalpha(a)
        layer.alpha_composite(logo_im, (round(cx - logo_im.width / 2), round(cy - logo_im.height / 2)))
    name, count = STRIP_PAGES[(cur + round(pos)) % len(STRIP_PAGES)]
    tiny_text(layer, W // 2, band_y + 84, "%d GAMES" % count, CYAN + (255,))
    if alpha < 1:
        layer.putalpha(layer.getchannel("A").point(lambda v: int(v * max(0.0, alpha))))
    out = base.convert("RGBA")
    out.alpha_composite(layer)
    return out.convert("RGB")


def new_parts(page):
    """The pieces of the new page, as the frontend draws them in their own layers."""
    parts = [("title", 0, (0, 0, W, 31))]
    for i in range(13):
        parts.append(("row", i, (0, rt(i) - 2, 194, rt(i) + 12)))
    parts += [("chrome", 0, (193, 33, 200, 217)), ("chrome", 0, (100, 217, 194, 230)),
              ("picture", 0, (200, 32, 310, 116)), ("text", 0, (200, 116, 320, 132)),
              ("icons", 0, (200, 132, 320, 216))]
    return [(name, order, box, page.crop(box)) for name, order, box in parts]


def doors_frame(old, new, bg, t):
    """t seconds into the doors: the old page opening, the new one closing in."""
    out = bg.copy()
    if t < INTRO_EXIT:
        k = (t / INTRO_EXIT) ** 2
        out.paste(old.crop((0, 0, DOOR_CUT, H)), (round(-k * DOOR_CUT), 0))
        out.paste(old.crop((DOOR_CUT, 0, W, H)), (DOOR_CUT + round(k * (W - DOOR_CUT)), 0))
    for name, order, box, piece in new_parts(new):
        tt = t - INTRO_EXIT * 0.6 - INTRO_DELAY[name] - INTRO_STEP.get(name, 0) * order
        p = tt / INTRO_PART
        if p <= 0:
            continue
        if p >= 1:
            out.paste(piece, box[:2])
            continue
        e = 1 - (1 - p) ** 3
        if name == "title":
            dx, dy, alpha = 0, -(1 - e) * 24, e
        else:
            dx, dy, alpha = (-1 if name in ("row", "chrome") else 1) * (1 - e) * W * 0.6, 0, 1.0
        under = out.crop((round(box[0] + dx), round(box[1] + dy), round(box[2] + dx), round(box[3] + dy)))
        blended = Image.blend(under, piece, alpha) if alpha < 1 else piece
        out.paste(blended, (round(box[0] + dx), round(box[1] + dy)))
    return out


def page_switch(fps=25):
    """Right on GROOVYMAME: the strip slides to FLYCAST DOJO, then the doors."""
    old = home_page("GROOVYMAME", "sf2ce").im
    new = home_page("FLYCAST DOJO", "mvsc2").im
    bg = fm.Canvas(seed=7).im
    start = PICK_WAIT + RIBBON_HOLD + RIBBON_FADE          # the doors begin when the strip is gone
    end = start + INTRO
    frames, durations = [fm.Canvas(bg=old)], [500]
    n = int(end * fps) + 1
    for i in range(n + 1):
        t = i / fps
        if t < start:
            alpha = 1.0 if t < start - RIBBON_FADE else (start - t) / RIBBON_FADE
            img = draw_strip(old, spring_pos(t), alpha)
        else:
            img = doors_frame(old, new, bg, t - start)
        frames.append(fm.Canvas(bg=img))
        durations.append(round(1000 / fps))
    frames.append(fm.Canvas(bg=new))
    durations.append(1200)
    return frames, durations


# ------------------------------------------------------------ 2: game menu (card)

def game_menu(party=False):
    cv = home_screen("sf2ce")
    cv.dim_all(0.45)
    if not party:
        tiles = [fist_tile(), fm.with_plus(planet(False, TILE_ICON)), iconlab.chosen("lobby", TILE_ICON), iconlab.chosen("replay", TILE_ICON), iconlab.chosen("friend", TILE_ICON)]

        def body(c, x0, x1, y):
            items = [fist_small(), fm.text_img("2 LOOKING", PINK), planet(True, ROW_ICON), fm.text_img("5 ONLINE", CYAN)]
            row = fm.hcat(items, 4)
            c.paste_icon(row, (x0 + x1 - row.width) // 2, y)
        fm.card(cv, "sf2ce", tiles, 0, "DUEL", caption_color=YELLOW, body=body, extra_h=-2, size=TILE)
    else:
        tiles = [fist_tile(), planet(True, TILE_ICON), fm.with_plus(planet(False, TILE_ICON)), iconlab.chosen("lobby", TILE_ICON), iconlab.chosen("friend", TILE_ICON)]

        def body(c, x0, x1, y):
            total, filled = 4, 2
            sx = (x0 + x1 - (total * 20 - 4)) // 2
            for i in range(total):
                c.paste_icon(fm.players_icon(GREEN if i < filled else (PINK if i == filled else LINE), 16), sx + i * 20, y)
            c.d.rectangle([sx + filled * 20 - 3, y - 3, sx + filled * 20 + 18, y + 18], outline=PINK)
        fm.card(cv, "sf2ce", tiles, 1, "JOIN KIWI#0f3d", caption_color=YELLOW, body=body, extra_h=14, size=TILE)
    return cv


def game_menu_party_only():
    """A game with no scoreboard (no win detector): party only, no DUEL tile."""
    cv = home_screen("xmen")
    cv.dim_all(0.45)
    tiles = [planet(True, TILE_ICON), fm.with_plus(planet(False, TILE_ICON)), iconlab.chosen("lobby", TILE_ICON),
             iconlab.chosen("replay", TILE_ICON), iconlab.chosen("friend", TILE_ICON)]

    def body(c, x0, x1, y):
        total, filled = 4, 3
        sx = (x0 + x1 - (total * 20 - 4)) // 2
        for i in range(total):
            c.paste_icon(fm.players_icon(GREEN if i < filled else PINK, 16), sx + i * 20, y)
        c.d.rectangle([sx + filled * 20 - 3, y - 3, sx + filled * 20 + 18, y + 18], outline=PINK)
        c.center(y + 26, "NO SCOREBOARD: PARTY ONLY", COMMENT, x0, x1)
    fm.card(cv, "xmen", tiles, 0, "JOIN KIWI#0f3d", caption_color=YELLOW, body=body, extra_h=26, size=TILE)
    return cv


# ------------------------------------------------------------ 3: the lobby of a game

PLAYERS["otter"] = dict(PLAYERS["otter"], state="party")
# The lobby of a game. Who plays together is one row (a match: the score of the
# FT; a party: the places taken) with its players inside, like the clones.
LOBBY = [
    ("LOOKING", "players", ["mango", "tapir", "zebra"]),
    ("PLAYING", "groups", [("KIWI VS LYNX", "2-1", ["kiwi", "lynx"])]),
    ("IN PARTY", "groups", [("PARTY OTTER", "2/2", ["otter", "guava"])]),
    ("IDLE", "players", ["acai"]),
]


def lobby_screen(selected="mango", notice=None):
    cv = canvas()
    i = 0
    title_row(cv, rt(i), GAMES["sf2ce"]["title"], "8", CYAN, planet(True, 10))
    i += 1
    # open: the group of the chosen player, and the ones that fit (13 rows)
    in_party = selected in ("otter", "guava")
    open_groups = {"LOOKING": True, "PLAYING": True, "IN PARTY": True, "IDLE": False}
    open_subs = {"KIWI VS LYNX": not in_party, "PARTY OTTER": in_party}
    order = []
    for group, kind, items in LOBBY:
        count = len(items) if kind == "players" else sum(len(m[2]) for m in items)
        group_row(cv, rt(i), group, count, open_groups[group])
        i += 1
        if not open_groups[group]:
            continue
        if kind == "players":
            for n, k in enumerate(items):
                child_player(cv, rt(i), PLAYERS[k], n == len(items) - 1, k == selected)
                order.append(k)
                i += 1
            continue
        for m, (text, right, members) in enumerate(items):
            last_sub = m == len(items) - 1
            opened = open_subs[text]
            sub_row(cv, rt(i), text, right, opened, last_sub, right_color=YELLOW if group == "PLAYING" else GREEN)
            i += 1
            if not opened:
                continue
            for n, k in enumerate(members):
                child_player(cv, rt(i), PLAYERS[k], n == len(members) - 1, k == selected, level=2, outer=not last_sub)
                order.append(k)
                i += 1
    list_chrome(cv, "%d/%d" % (order.index(selected) + 2, 12), thumb=(36, 214))
    p = PLAYERS[selected]
    if p["state"] == "download":
        panel_player(cv, p, "sf2ce", ("WILL JOIN", GREEN))
        cv.box(204, 150, 304, 162, fill=SPACE)
        mid(cv, iconlab.chosen("rom", 10), 204, 152)
        cv.box(216, 152, 304, 156, fill=BG_DEEP, outline=LINE)
        cv.box(217, 153, 217 + int(86 * p["pct"] / 100), 155, fill=ORANGE)
    elif p["state"] == "party":
        panel_player(cv, p, "sf2ce", ("HOST: PARTY", GREEN))
    else:
        panel_player(cv, p, "sf2ce")
    if notice:
        notice_bar(cv, notice[0], notice[1], iconlab.chosen("rom", 16))
    return cv


def lobby_card(selected="mango"):
    cv = lobby_screen(selected)
    cv.dim_all(0.45)
    tiles = [fist_tile(), iconlab.chosen("watch", TILE_ICON), planet(True, TILE_ICON), iconlab.chosen("friend", TILE_ICON)]
    fm.GAMES["_p"] = dict(title=tag_of(PLAYERS[selected]))
    fm.card(cv, "_p", tiles, 0, "DUEL", caption_color=YELLOW, extra_h=-10, size=TILE)
    return cv


def dimmed(icon, k=0.35):
    """An icon of something that cannot be done here: faded, with the X in its corner."""
    out = icon.copy()
    a = out.getchannel("A").point(lambda v: int(v * k))
    out.putalpha(a)
    x = iconlab.chosen("pass", 14)
    out.alpha_composite(x, (out.width - x.width, out.height - x.height))
    return out


def lobby_card_no_rom():
    """Someone in a duel in a game this cabinet does not have: watching needs
    the ROM already here (the ROM is only sent to who plays, never to who watches)."""
    cv = lobby_screen("kiwi")
    cv.dim_all(0.45)
    tiles = [dimmed(iconlab.chosen("watch", TILE_ICON)), iconlab.chosen("friend", TILE_ICON)]
    fm.GAMES["_p"] = dict(title=tag_of(PLAYERS["kiwi"]))

    def body(c, x0, x1, y):
        c.center(y, "MARVEL VS. CAPCOM 2", YELLOW, x0, x1)
        c.center(y + 14, "NO ROM HERE:", ORANGE, x0, x1)
        c.center(y + 26, "WATCHING NEEDS IT", ORANGE, x0, x1)
    card_wide(cv, tag_of(PLAYERS["kiwi"]), tiles, 0, "WATCH", COMMENT, body, width=232, extra_h=30)
    return cv


def card_wide(cv, title, tiles, selected, caption, caption_color, body, width, extra_h=0, size=None, gap=8):
    """The frontend's card (as fm.card) with a minimum width and the tiles centred in it."""
    size = size or TILE
    n = len(tiles)
    w = max(width, n * size + (n - 1) * gap + 28)
    x0 = (W - w) // 2
    y0, y1 = 34, 150 + extra_h
    cv.box(x0 + 3, y0 + 3, x0 + w + 3, y1 + 3, fill=PURPLE)
    cv.box(x0, y0, x0 + w, y1, fill=CARD, outline=PINK)
    cv.text(x0 + 12, y0 + 10, title, YELLOW)
    ty = y0 + 28
    tx = x0 + (w - (n * size + (n - 1) * gap)) // 2
    for i, icon in enumerate(tiles):
        fm.tile(cv, tx + i * (size + gap), ty, size, icon, i == selected, fm.snap("sf2ce"))
    cv.center(ty + size + 10, caption, caption_color, x0, x0 + w)
    if body:
        body(cv, x0, x0 + w, ty + size + 26)


# ------------------------------------------------------------ 4: the cards

CW, CH = 160, 164


def card_image(p, key, stamp=None, frame=PINK, badge=False):
    """A player's card, Tinder style: the art of the game they want, the
    NICK#tag over its foot, then connection, record, characters, FairPlay."""
    im = Image.new("RGBA", (CW + 3, CH + 3), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    f8, f16 = font(8), font(16)
    d.rectangle([3, 3, CW + 2, CH + 2], fill=PURPLE)
    d.rectangle([0, 0, CW - 1, CH - 1], fill=CARD, outline=frame)
    if frame != PINK:
        d.rectangle([1, 1, CW - 2, CH - 2], outline=frame)
    art = game_art(key, CW - 4, 108)
    shade = Image.new("L", art.size, 0)
    sd = ImageDraw.Draw(shade)
    for yy in range(70, 108):
        sd.line([(0, yy), (art.width, yy)], fill=int(210 * (yy - 70) / 38))
    art = Image.composite(Image.new("RGB", art.size, (0, 0, 0)), art, shade)
    im.paste(art, (2, 2))
    lg = logo(key, 76, 30)
    if lg is not None:
        im.paste(lg, (6, 6), lg)
    d.text((7, 87), p["nick"], font=f16, fill=SHADOW)
    d.text((6, 86), p["nick"], font=f16, fill=FG)
    d.text((8 + 16 * len(p["nick"]), 94), "#" + p["tag"], font=f8, fill=CYAN)
    y = 116
    ci = conn_icon(p)
    im.paste(ci, (6, y + (8 - ci.height) // 2), ci)
    d.text((18, y), "CABLE" if p["conn"] == "cable" else "WI-FI", font=f8, fill=GREEN if p["conn"] == "cable" else YELLOW)
    pb = ping_bars(p["ping"])
    im.paste(pb, (104, y + (8 - pb.height) // 2), pb)
    d.text((118, y), "%dMS" % p["ping"], font=f8, fill=ping_color(p["ping"]))
    y += 15
    d.text((6, y), "GAME", font=f8, fill=COMMENT)
    wl_img(im, d, 48, y - 1, p["w"], p["l"], f8)
    y += 13
    d.text((6, y), "ALL", font=f8, fill=COMMENT)
    wl_img(im, d, 48, y - 1, p["aw"], p["al"], f8)
    if badge:
        d.rectangle([2, 2, CW - 3, 16], fill=PINK)
        fs = fist_icon(26)
        im.paste(fs, (4, 3), fs)
        d.text((34, 6), "WANTS A DUEL", font=f8, fill=BG_DEEP)
    if stamp == "pass":
        sx, sy = CW - 84, 26
        d.rectangle([sx, sy, sx + 76, sy + 26], outline=RED)
        d.rectangle([sx + 2, sy + 2, sx + 74, sy + 24], outline=RED)
        d.text((sx + 7, sy + 6), "PASS", font=f16, fill=RED)
    elif stamp == "duel":
        sx, sy = 8, 40
        d.rectangle([sx, sy, sx + 108, sy + 26], fill=CARD, outline=GREEN)
        d.rectangle([sx + 2, sy + 2, sx + 106, sy + 24], outline=GREEN)
        fs = fist_icon(30)
        im.paste(fs, (sx + 5, sy + 5), fs)
        d.text((sx + 39, sy + 6), "DUEL", font=f16, fill=GREEN)
    return im


def stack_back(cv, x0, y0, n=2):
    for i in range(n, 0, -1):
        inset = 4 * i
        cv.box(x0 + inset, y0 + 4 * i, x0 + CW - 1 - inset, y0 + CH - 1 + 4 * i, fill=BG_DEEP, outline=LINE)


def round_button(cv, cx, cy, icon, color, label, label_color):
    r = 17
    cv.d.ellipse([cx - r + 2, cy - r + 2, cx + r + 2, cy + r + 2], fill=PURPLE)
    cv.d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=CARD, outline=color)
    cv.d.ellipse([cx - r + 1, cy - r + 1, cx + r - 1, cy + r - 1], outline=color)
    cv.paste_icon(icon, cx - icon.width // 2, cy - icon.height // 2)
    # the label with a drop shadow, so it reads over the dimmed game art
    cv.center(cy + r + 9, label, (0x08, 0x08, 0x10), cx - 39, cx + 41)
    cv.center(cy + r + 8, label, label_color, cx - 40, cx + 40)


def cards_background(key="sf2ce"):
    cv = fm.Canvas()
    fm.full_background(cv, key, info=False, k=0.22)
    return cv


# The title, the card and the cards behind it, centred in the height above
# the line of hints (y 228); the buttons on the card's middle.
HEAD_GAP, STACK = 14, 8
X0 = (W - CW) // 2
Y0 = (228 - (HEAD_GAP + CH + STACK)) // 2 + HEAD_GAP
BTN_Y = Y0 + CH // 2


def tilt(card, angle):
    """The card tilted as it is dragged, like Tinder: turned around its middle
    in whole pixels (nearest, no blur), with its centre lower as it turns."""
    if not angle:
        return card, 0, 0
    r = card.rotate(angle, resample=Image.NEAREST, expand=True)
    return r, (card.width - r.width) // 2, (card.height - r.height) // 2


def cards_frame(top_card, under=None, top_dx=0, under_rise=0, header=None, buttons=True, extra=None,
                angle=0, top_dy=0):
    cv = cards_background()
    if header is None:
        header = ("STREET FIGHTER II'", "5")
    cv.center(Y0 - HEAD_GAP, header[0], YELLOW)
    if under is None:
        stack_back(cv, X0, Y0)
    else:
        stack_back(cv, X0, Y0, 1) if under_rise < 4 else None
        cv.im.paste(under, (X0, Y0 + 4 - under_rise), under)
        cv.d = ImageDraw.Draw(cv.im)
        cv.d.fontmode = "1"
    if top_card is not None:
        card, ox, oy = tilt(top_card, angle)
        cv.im.paste(card, (X0 + top_dx + ox, Y0 + top_dy + oy), card)
        cv.d = ImageDraw.Draw(cv.im)
        cv.d.fontmode = "1"
    if buttons:
        hot = -1 if angle > 0 else 1 if angle < 0 else 0
        round_button(cv, 38, BTN_Y, iconlab.chosen("pass", 16), RED, "<PASS", RED)
        round_button(cv, 282, BTN_Y, fist(), GREEN, "DUEL>", GREEN)
        if hot:   # the button of the side the card goes to lights up
            cx = 38 if hot < 0 else 282
            color = RED if hot < 0 else GREEN
            cv.d.ellipse([cx - 20, BTN_Y - 20, cx + 20, BTN_Y + 20], outline=color)
            cv.d.ellipse([cx - 21, BTN_Y - 21, cx + 21, BTN_Y + 21], outline=color)
    cv.center(230, "UP:INFO  B:BACK", COMMENT)
    if extra:
        extra(cv)
    return cv


def cards_screen():
    return cards_frame(card_image(PLAYERS["mango"], "sf2ce"))


# Holding the stick to one side drags the card: it slides, tilts and drops a
# little at each step (Tinder's arc), the stamp shows, and past the edge it is
# thrown out; the card under it comes up.
SWIPE_DX = [0, 6, 16, 32, 56, 92, 140, 200]
SWIPE_ANGLE = [0, 2, 4, 7, 10, 14, 18, 22]
SWIPE_DY = [0, 0, 1, 2, 4, 7, 11, 16]


def swipe_frames(direction):
    top = PLAYERS["mango"]
    nxt = card_image(PLAYERS["tapir"], "sf2ce")
    frames = []
    for i, dx in enumerate(SWIPE_DX):
        stamp = None if i < 2 else ("pass" if direction < 0 else "duel")
        card = card_image(top, "sf2ce", stamp=stamp)
        rise = min(4, max(0, i - 3))
        frames.append(cards_frame(card, nxt, top_dx=direction * dx, under_rise=rise,
                                  angle=SWIPE_ANGLE[i] * (1 if direction < 0 else -1), top_dy=SWIPE_DY[i]))
    if direction > 0:
        def sent(cv):
            row = fm.hcat([fist(), fm.text_img("FIST SENT: MANGO#a7k2", GREEN)], 4)
            cv.box(0, Y0 - HEAD_GAP - 5, W, Y0 - 2, fill=SPACE)
            cv.paste_icon(row, (W - row.width) // 2, Y0 - HEAD_GAP - 4)
            cv.paste_icon(icon8("clock"), 262, BTN_Y + 34)
            cv.text(272, BTN_Y + 34, "1", PINK)
        frames.append(cards_frame(None, nxt, under_rise=4, extra=sent))
    else:
        frames.append(cards_frame(None, nxt, under_rise=4))
    return frames


def incoming_frames():
    lynx = PLAYERS["lynx"]
    out = []
    for frame in (PINK, FG, PINK, FG):
        card = card_image(lynx, "sf2ce", frame=frame, badge=True)
        out.append(cards_frame(card, header=("STREET FIGHTER II'", "5")))
    return out


def cards_in_list():
    """Variant B: the cards inside the list mode. The open group is the
    players looking for a duel, the panel on the right is the card."""
    cv = canvas()
    i = 0
    title_row(cv, rt(i), GAMES["sf2ce"]["title"], "8", CYAN, planet(True, 10))
    i += 1
    group_row(cv, rt(i), "LOOKING", 3, True)
    i += 1
    for n, k in enumerate(["mango", "tapir", "zebra"]):
        child_player(cv, rt(i), PLAYERS[k], n == 2, k == "mango")
        i += 1
    for g, c in (("PLAYING", 2), ("IN PARTY", 1), ("IDLE", 2)):
        group_row(cv, rt(i), g, c, False)
        i += 1
    list_chrome(cv, "3/8", thumb=(36, 214))
    p = PLAYERS["mango"]
    cv.box(204, 36, 311, 216, fill=PURPLE)
    cv.box(202, 34, 309, 214, fill=CARD, outline=PINK)
    cv.paste_art(game_art("sf2ce", 102, 70), 205, 37)
    lg = logo("sf2ce", 60, 22)
    if lg is not None:
        cv.paste_icon(lg, 207, 39)
    cv.text(206, 112, p["nick"], FG)
    cv.text(206 + 8 * len(p["nick"]), 112, "#" + p["tag"], CYAN)
    mid(cv, conn_icon(p), 206, 126)
    mid(cv, ping_bars(p["ping"]), 218, 126)
    cv.text(234, 126, str(p["ping"]) + "MS", GREEN)
    wl(cv, 206, 139, p["w"], p["l"])
    cv.paste_icon(iconlab.chosen("pass", 16), 206, 188)
    cv.text(224, 192, "<", RED)
    cv.paste_icon(fist(), 270, 188)
    cv.text(260, 192, ">", GREEN)
    return cv


def details_screen():
    cv = cards_background()
    p = PLAYERS["mango"]
    x0, y0, x1, y1 = 16, 12, 303, 226
    cv.box(x0 + 3, y0 + 3, x1 + 3, y1 + 3, fill=PURPLE)
    cv.box(x0, y0, x1, y1, fill=CARD, outline=PINK)
    big_text(cv, x0 + 10, y0 + 8, p["nick"], FG)
    cv.text(x0 + 12 + 16 * len(p["nick"]), y0 + 16, "#" + p["tag"], CYAN)
    mid(cv, conn_icon(p), x1 - 64, y0 + 12)
    cv.paste_icon(ping_bars(p["ping"]), x1 - 52, y0 + 12)
    cv.text(x1 - 38, y0 + 12, "%dMS" % p["ping"], GREEN)
    y = y0 + 32
    cv.text(x0 + 10, y, "PLAYS ONLINE", COMMENT)
    y += 12
    for i, key in enumerate(["sf2ce", "kof98", "garou", "sfiii3nr1"]):
        bx = x0 + 10 + i * 68
        cv.box(bx, y, bx + 62, y + 26, fill=BG_DEEP, outline=LINE)
        lg = logo(key, 58, 22)
        if lg is not None:
            cv.paste_icon(lg, bx + 2 + (58 - lg.width) // 2, y + 2 + (22 - lg.height) // 2)
    y += 36
    cv.text(x0 + 10, y, "AGAINST YOU", COMMENT)
    y += 12
    cv.text(x0 + 10, y, "YOU", PINK)
    cv.text(x0 + 46, y, "3 - 5", FG)
    cv.text(x0 + 94, y, "MANGO", YELLOW)
    y += 18
    cv.text(x0 + 10, y, "MATCHES ONLINE", COMMENT)
    y += 12
    cv.text(x0 + 10, y, "142", FG)
    cv.center(y1 - 12, "DOWN:CARD  <PASS  DUEL>", COMMENT, x0, x1)
    return cv


# ------------------------------------------------------------ 9: DUEL!

def duel_frames():
    frames, durations = [], []
    lf, rf = fist_half("left", 3), fist_half("right", 3)
    cy = 46
    final_l, final_r = 160 - lf.width - 3, 163
    path_l = [-lf.width, -50, 0, 34, 50, final_l]
    path_r = [W, 300, 250, 216, 170, final_r]

    def base(flash=False):
        cv = fm.Canvas(seed=11)
        if flash:
            cv.im.paste((0x3A, 0x1A, 0x40), (0, 0, W, H))
            cv.d = ImageDraw.Draw(cv.im)
            cv.d.fontmode = "1"
        return cv

    for xl, xr in zip(path_l, path_r):
        cv = base()
        cv.paste_icon(lf, xl, cy)
        cv.paste_icon(rf, xr, cy)
        frames.append(cv)
        durations.append(60)

    def burst(cv, r0, r1, color):
        cx, cyy = 160, cy + lf.height // 2
        for dx, dy in ((0, -1), (1, -1), (1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1)):
            cv.d.line([(cx + dx * r0, cyy + dy * r0), (cx + dx * r1, cyy + dy * r1)], fill=color, width=3)

    cv = base(flash=True)
    cv.paste_icon(lf, final_l, cy)
    cv.paste_icon(rf, final_r, cy)
    burst(cv, 28, 44, FG)
    frames.append(cv)
    durations.append(70)
    for step in range(3):
        cv = base()
        cv.paste_icon(lf, final_l, cy)
        cv.paste_icon(rf, final_r, cy)
        if step < 2:
            burst(cv, 34 + 6 * step, 52 + 6 * step, YELLOW)
        if step >= 1:
            big_center(cv, 12, "DUEL!", PINK, size=32, off=2)
        if step >= 2:
            names(cv)
        frames.append(cv)
        durations.append(80 if step < 2 else 1800)
    return frames, durations


def names(cv):
    me, other = "YOU", tag_of(PLAYERS["mango"])
    cv.center(138, me, PINK, 0, 160)
    cv.paste_icon(iconlab.chosen("cable", 10), 76, 150)
    cv.center(138, other, YELLOW, 160, W)
    cv.paste_icon(iconlab.chosen("cable", 10), 236, 150)
    lg = logo("sf2ce", 150, 44)
    if lg is not None:
        cv.paste_icon(lg, (W - lg.width) // 2, 164)
    cv.center(220, "FT5", CYAN)


# ------------------------------------------------------------ 10, 11: waiting rooms

def check_row(cv, y, ok, text, color=None):
    cv.paste_icon(icon8("check" if ok is True else "cross" if ok is False else "down"), 204, y)
    cv.text(216, y, text, color or (GREEN if ok is True else RED if ok is False else ORANGE))


def duel_wait(state="ready"):
    cv = canvas()
    i = 0
    title_row(cv, rt(i), GAMES["sf2ce"]["title"], "FT5", CYAN)
    i += 1
    group_row(cv, rt(i), "PLAYERS", 2, True)
    i += 1
    me = dict(PLAYERS["otter"], conn="cable", ping=28)
    child_player(cv, rt(i), me, False, True, slot=1, you=True)
    i += 1
    other = dict(PLAYERS["mango"])
    if state == "download":
        other.update(state="download", pct=45)
    if state == "relay":
        other.update(ping=61)
    child_player(cv, rt(i), other, True, slot=2)
    i += 1
    group_row(cv, rt(i), "WATCHING", 2, True)
    i += 1
    for n, k in enumerate(["kiwi", "otter"]):
        child_player(cv, rt(i), dict(PLAYERS[k], state="idle"), n == 1)
        i += 1
    list_chrome(cv, "3/7", thumb=(36, 214))
    art_box(cv, "sf2ce")
    if state == "relay":
        cv.paste_icon(relay_icon(), 204, 120)
        cv.text(222, 120, "RELAY", ORANGE)
        cv.paste_icon(ping_bars(61), 266, 120)
        cv.text(204, 132, "61MS", YELLOW)
    else:
        cv.paste_icon(direct_icon(), 204, 120)
        cv.text(220, 120, "DIRECT", GREEN)
        cv.paste_icon(ping_bars(28), 272, 120)
        cv.text(204, 132, "28MS", GREEN)
    if state == "ready":
        check_row(cv, 148, True, "ROM")
        check_row(cv, 160, True, "EMULATOR")
        check_row(cv, 172, True, "FAIRPLAY")
        cv.text(204, 196, "STARTING 3", GREEN)
    elif state == "download":
        check_row(cv, 148, None, "ROM 45%")
        cv.box(216, 158, 304, 162, fill=BG_DEEP, outline=LINE)
        cv.box(217, 159, 217 + 39, 161, fill=ORANGE)
        check_row(cv, 168, True, "EMULATOR")
        check_row(cv, 180, True, "FAIRPLAY")
        cv.text(204, 200, "WAITING", FG)
    else:
        check_row(cv, 148, False, "ROM")
        check_row(cv, 160, True, "EMULATOR")
        check_row(cv, 172, True, "FAIRPLAY")
        cv.text(204, 188, "ROM NOT SENT", RED)
        cv.text(204, 200, "OVER RELAY", RED)
    return cv


def party_lobby():
    cv = canvas()
    g = GAMES["xmen"]
    i = 0
    title_row(cv, rt(i), g["title"], "3/4", GREEN)
    i += 1
    group_row(cv, rt(i), "PLAYERS", "3/4", True)
    i += 1
    slots = [(1, "kiwi", False, False), (2, "lynx", False, False), (3, None, True, False), (4, None, False, True)]
    for n, key, mine, free in slots:
        last = n == 4
        if mine:
            child_player(cv, rt(i), dict(PLAYERS["otter"], ping=33), last, True, slot=n, you=True)
        elif free:
            child_player(cv, rt(i), None, last, slot=n, free=True)
        else:
            child_player(cv, rt(i), PLAYERS[key], last, slot=n)
        i += 1
    group_row(cv, rt(i), "WATCHING", 1, False)
    list_chrome(cv, "4/7", thumb=(36, 214))
    art_box(cv, "xmen")
    cv.text(204, 120, "%s %s" % (g["year"], g["maker"]), YELLOW)
    cv.paste_icon(fm.players_icon(GREEN, 14), 204, 134)
    cv.text(222, 138, "3/4", GREEN)
    cv.paste_icon(direct_icon(), 256, 138)
    cv.text(204, 160, "HOST", COMMENT)
    cv.text(204, 172, "KIWI#0f3d", FG)
    cv.text(204, 196, "WAITING HOST", COMMENT)
    return cv


# ------------------------------------------------------------ 12: transfer

def transfer_screen(pct=45):
    cv = fm.Canvas()
    fm.full_background(cv, "kof98", info=False, k=0.2)
    g = GAMES["kof98"]
    cv.center(14, g["title"], YELLOW)
    cv.paste_icon(fm.cabinet(True, 26, 36), 62, 40)
    cv.paste_icon(fm.cabinet(False, 26, 36), 232, 40)
    cv.d.rectangle([229, 37, 261, 79], outline=PINK)
    cv.center(84, "MANGO#a7k2", FG, 20, 130)
    cv.paste_icon(iconlab.chosen("cable", 10), 71, 96)
    cv.center(84, "YOU", PINK, 200, 290)
    cv.paste_icon(iconlab.chosen("wifi", 10), 241, 96)
    for i in range(6):
        cv.paste_icon(fm.play_icon(GREEN if i <= 2 else fm.GREEN_DIM, 12), 112 + i * 16, 52)
    cv.box(34, 112, 286, 128, fill=CARD, outline=LINE)
    cv.box(36, 114, 36 + int(248 * pct / 100), 126, fill=GREEN)
    cv.center(136, "%d%%  5.4/12 MB" % pct, FG)
    cv.paste_icon(direct_icon(), 96, 150)
    cv.text(112, 150, "DIRECT 1.2 MB/S", GREEN)
    cv.center(170, "kof98.zip", COMMENT)
    cv.center(182, "neogeo.zip", COMMENT)
    cv.text(14, 226, "B:CANCEL", COMMENT)
    return cv


def notice_bar(cv, line1, line2, icon, y0=194):
    cv.box(10, y0 + 2, 312, y0 + 36, fill=PURPLE)
    cv.box(8, y0, 310, y0 + 34, fill=CARD, outline=PINK)
    cv.paste_icon(icon, 16, y0 + (34 - icon.height) // 2)
    x = 16 + icon.width + 8
    cv.text(x, y0 + 7, line1, FG)
    cv.text(x, y0 + 20, line2, CYAN)


# ------------------------------------------------------------ 13: result

def result_screen(kind="win"):
    cv = fm.Canvas()
    fm.full_background(cv, "sf2ce", info=False, k=0.25)
    x0, y0, x1, y1 = 36, 14, 284, 226
    cv.box(x0 + 3, y0 + 3, x1 + 3, y1 + 3, fill=PURPLE)
    cv.box(x0, y0, x1, y1, fill=CARD, outline=PINK)
    title, color = {"win": ("YOU WIN", GREEN), "disputed": ("DISPUTED", ORANGE), "desync": ("DESYNC", RED)}[kind]
    big_center(cv, y0 + 10, title, color, x0=x0, x1=x1)
    score = "5 - 3" if kind != "desync" else "2 - 1"
    big_center(cv, y0 + 34, score, FG, x0=x0, x1=x1)
    cv.center(y0 + 54, "FT5", CYAN, x0, x1)
    cv.center(y0 + 70, "YOU", PINK, x0, 160)
    cv.center(y0 + 70, "MANGO#a7k2", YELLOW, 160, x1)
    cv.center(y0 + 82, "RYU", FG, x0, 160)
    cv.center(y0 + 82, "KEN", FG, 160, x1)
    if kind == "win":
        row = fm.hcat([iconlab.chosen("replay", 10), fm.text_img("REPLAY SAVED", CYAN)], 4)
        cv.paste_icon(row, (x0 + x1 - row.width) // 2, y0 + 100)
    elif kind == "disputed":
        cv.center(y0 + 98, "THE REPORTS DIFFER", ORANGE, x0, x1)
        cv.center(y0 + 110, "UNDER REVIEW", ORANGE, x0, x1)
    else:
        cv.center(y0 + 98, "AT 01:42", RED, x0, x1)
        cv.center(y0 + 110, "MATCH VOID", RED, x0, x1)
    tiles = [fist_tile(), iconlab.chosen("replay", TILE_ICON), iconlab.Icon(32).poly([(3, 16), (22, 3), (22, 11), (29, 11), (29, 21), (22, 21), (22, 29)], "purple").im]
    names_ = ["REMATCH", "REPLAY", "BACK"]
    size, gap = TILE, 10
    tx = (x0 + x1 - (3 * size + 2 * gap)) // 2
    for i, ic in enumerate(tiles):
        fm.tile(cv, tx + i * (size + gap), y0 + 126, size, ic, i == 0, fm.snap("sf2ce"))
    cv.center(y0 + 176, names_[0], YELLOW, x0, x1)
    # no dispute and no review: a match the two cabinets don't agree on just doesn't count
    return cv


# ------------------------------------------------------------ 14: OSD notice

def osd_over_frontend():
    bg = Image.open(REAL_LIST).convert("RGB").resize((W, H), Image.NEAREST)
    cv = fm.Canvas(bg=bg)
    notice_bar(cv, "MANGO#a7k2 WANTS A DUEL", "HOLD COIN+START: GO", fist())
    return cv


def osd_over_game():
    cv = fm.Canvas()
    cv.im.paste(fm.stretch(fm.snap("kof98"), W, H), (0, 0))
    cv.d = ImageDraw.Draw(cv.im)
    cv.d.fontmode = "1"
    notice_bar(cv, "MANGO#a7k2 WANTS A DUEL", "SF2  AFTER THIS GAME", fist(), y0=4)
    return cv


# ------------------------------------------------------------ 15, 16: Setup and options

def theme_icons():
    """The 16x16 icons of the real Setup (theme.py), read without pygame."""
    src = open(THEME, encoding="utf-8").read()
    colours = {}
    for name, r, g, b in re.findall(r"^([A-Z_]+) = \((0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+), (0x[0-9A-Fa-f]+)\)", src, re.M):
        colours[name] = (int(r, 16), int(g, 16), int(b, 16))
    m = re.search(r"ICON_COLORS = \{(.*?)\}", src, re.S)
    pal = {}
    for letter, cname in re.findall(r'"(\w)": (\w+)', m.group(1)):
        if cname in colours:
            pal[letter] = colours[cname]
    icons = {}
    for name, art in re.findall(r'"([\w-]+)": """\n(.*?)"""', src, re.S):
        rows = [r for r in art.split("\n") if r]
        if len(rows) == 16:
            icons[name] = from_art("\n".join(rows), pal)
    return icons


def mosaic(size, seed=5):
    rnd = random.Random(seed)
    small = Image.new("RGB", (6, 6))
    for y in range(6):
        for x in range(6):
            small.putpixel((x, y), rnd.choice([(0x5a, 0x2a, 0x4a), (0x3a, 0x2a, 0x40), (0x6a, 0x30, 0x55), (0x2e, 0x3a, 0x48)]))
    return small.resize((size, size), Image.NEAREST)


def setup_carousel(title_band, icons, center_icon, name, desc, tag=None, tag_color=COMMENT, dots=(7, 11)):
    cv = canvas(title_band)
    xs = [16, 72, 208, 264]
    for x, ic in zip(xs, icons):
        cv.box(x, 64, x + 40, 104, fill=CARD, outline=LINE)
        big = ic.resize((32, 32), Image.NEAREST)
        cv.paste_icon(big, x + 4, 68)
    cv.box(127, 51, 199, 123, fill=PURPLE)
    cv.box(124, 48, 196, 120, fill=CARD, outline=PINK)
    cv.paste_art(mosaic(71), 125, 49)
    cv.paste_icon(center_icon, 160 - center_icon.width // 2, 84 - center_icon.height // 2)
    if tag:
        tw = 8 * len(tag) + 8
        cv.box(196 - tw, 113, 200, 125, fill=CARD, outline=tag_color)
        cv.text(200 - tw + 4 - 2, 116, tag, tag_color)
    big_center(cv, 132, name, YELLOW)
    for i, line in enumerate(desc):
        cv.center(156 + 11 * i, line, CYAN)
    n, sel = dots[1], dots[0]
    dx = (W - (n * 10 - 4)) // 2
    for i in range(n):
        cv.box(dx + i * 10, 200, dx + i * 10 + 5, 205, fill=PINK if i == sel else LINE)
    cv.center(221, "< > SELECT  A OK  B BACK", COMMENT)
    return cv


# The Matchmaker's icon for the Setup menu, in the Setup's own 8-bit style
# (theme.py ICONS: 16x16, one letter per pixel, flat colours of the theme):
# the red and the blue glove touching, white laced cuffs, a yellow spark.
SETUP_GLOVES = """
................
................
.......YY.......
....Y..YY..Y....
.....Y....Y.....
...RRRR..BBBB...
..RFFRRRBFFBBB..
FFRFRRRRBFBBBBFF
FMRRRRRRBBBBBBMF
FFRRRRRRBBBBBBFF
FMRRRRRRBBBBBBMF
FFRRRRRRBBBBBBFF
..RRRRRRBBBBBB..
...RRRR..BBBB...
................
................
"""
THEME_PAL = {"R": RED, "B": (0x00, 0x5E, 0xB8), "F": FG, "M": COMMENT, "Y": YELLOW, "C": CYAN, "G": GREEN}

# ONLINE in Setup > Network (on/off, like DEBUG MODE): the Earth, in the
# Setup's 8-bit style (cyan sea, green land, a white shine, the blue shade).
SETUP_ONLINE = """
................
.....CCCCCC.....
...CCFFCGGCCC...
..CCFCGGGGCCCC..
..CCCGGGGGCCGC..
.CCCCGGGCCCGGGB.
.CCCCCGCCCCGGGB.
.CCCCCCCCCCCGCB.
.CCCCCCCCCCCCCB.
.CCGGCCCCCCCCCB.
..CGGGGCCCCCCB..
..CCGGGCCCGCBB..
...CCCCCCGGBB...
.....BBBBBB.....
................
................
"""


def setup_online_icon(k=1):
    im = from_art(SETUP_ONLINE, THEME_PAL)
    return im.resize((16 * k, 16 * k), Image.NEAREST) if k != 1 else im


def setup_gloves(k=1):
    im = from_art(SETUP_GLOVES, THEME_PAL)
    return im.resize((16 * k, 16 * k), Image.NEAREST) if k != 1 else im


def setup_gloves_sheet(ti):
    """The gloves next to the real Setup icons, at 1x and 4x."""
    names = ["frontend", "joysticks", "network", "cloud", "desktop", "games"]
    icons = [ti[n] for n in names if n in ti] + [setup_gloves()]
    out = Image.new("RGB", (len(icons) * 76 + 12, 120), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    for i, ic in enumerate(icons):
        x = 8 + i * 76
        big = ic.resize((64, 64), Image.NEAREST)
        out.paste(big, (x, 8), big)
        out.paste(ic, (x + 24, 80), ic)
        if i == len(icons) - 1:
            d.rectangle([x - 4, 4, x + 68, 100], outline=PINK)
    d.text((8, 106), "THE SETUP ICONS AND THE MATCHMAKER (PINK)", font=font(8), fill=COMMENT)
    return out


def setup_frontend(ti):
    icons = [ti.get("frontend"), ti.get("games"), ti.get("desktop"), ti.get("emulators")]
    icons = [i if i is not None else from_art(ART16["pass"]) for i in icons]
    return setup_carousel("FRONTEND", icons, setup_gloves(4), "MATCHMAKER",
                          ["Online duels and parties", "with other FliperOS cabinets."], dots=(3, 9))


def setup_online(ti):
    """Setup > Network: ONLINE switches the online service on and off (A, like
    DEBUG MODE); the online settings are the next items of the same row, and
    the Matchmaker's own options have them too (the same keys)."""
    icons = [ti.get("network"), ti.get("status") or ti.get("lab"), ti.get("cabinetname"), setup_gloves()]
    icons = [i if i is not None else setup_gloves() for i in icons]
    return setup_carousel("NETWORK", icons, setup_online_icon(4), "ONLINE",
                          ["Play online as MANGO#a7k2.", "Cable. Server answers in 32 ms."], tag="ON", tag_color=GREEN,
                          dots=(3, 9))


def options_screen():
    cv = home_screen("sf2ce")
    cv.dim_all(0.45)
    x0, y0, x1, y1 = 42, 8, 278, 232
    cv.box(x0 + 3, y0 + 3, x1 + 3, y1 + 3, fill=PURPLE)
    cv.box(x0, y0, x1, y1, fill=CARD, outline=PINK)
    cv.text(x0 + 10, y0 + 8, "MATCHMAKER OPTIONS", YELLOW)
    rows = [
        ("NICKNAME", "MANGO#a7k2", None, True),
        ("SHOW MY GAME", None, ("ON", "OFF"), False),
        ("FISTS IN GAMES", None, ("ON", "OFF"), False),
        ("RELAY ONLY", None, ("OFF", "ON"), False),
        ("SERVER", "OK  32MS", None, False),
        ("CONNECTION", "CABLE", None, False),
    ]
    y = y0 + 22
    for label, value, chips, sel in rows:
        h = 30
        if sel:
            cv.box(x0 + 9, y + 2, x1 - 7, y + h + 1, fill=PURPLE)
            cv.box(x0 + 7, y, x1 - 9, y + h - 1, fill=SEL_FILL, outline=PINK)
        else:
            cv.box(x0 + 7, y, x1 - 9, y + h - 1, fill=CARD, outline=LINE)
        cv.text(x0 + 14, y + 5, label, FG if sel else LIST_TEXT)
        if value:
            color = CYAN if label != "SERVER" else GREEN
            cv.text(x0 + 14, y + 17, value, color if sel or label != "NICKNAME" else CYAN)
        if chips:
            cx = x0 + 14
            for i, c in enumerate(chips):
                w = 8 * len(c) + 8
                if i == 0:
                    cv.box(cx, y + 15, cx + w, y + 26, fill=PURPLE)
                    cv.text(cx + 4, y + 17, c, BG_DEEP)
                else:
                    cv.box(cx, y + 15, cx + w, y + 26, outline=LINE)
                    cv.text(cx + 4, y + 17, c, COMMENT)
                cx += w + 6
        y += h + 3
    return cv


# ------------------------------------------------------------ 17: icon sheet

def icon_sheet():
    sw, sh = 480, 300
    im = Image.new("RGB", (sw, sh), SPACE)
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    f = font(8)
    d.text((8, 6), "FIST BUMP: OPTION %d IN THE SCREENS" % FIST, font=f, fill=YELLOW)
    pr = fist_pair()
    big = pr.resize((pr.width * 2, pr.height * 2), Image.NEAREST)
    im.paste(big, (8, 20), big)
    sx = 160
    for w in (70, 38, 30, 18):
        sm = fist_icon(w)
        im.paste(sm, (sx, 60 - sm.height // 2), sm)
        sx += w + 10
    d.text((8, 104), "ONLINE MARK", font=f, fill=YELLOW)
    marks = [(planet(True, 12), planet(False, 12)), (live_person(12), None), (fist_small(), None)]
    for i, (a, b) in enumerate(marks):
        x = 8 + i * 94
        im.paste(a.resize((a.width * 4, a.height * 4), Image.NEAREST), (x, 118), a.resize((a.width * 4, a.height * 4), Image.NEAREST))
        im.paste(a, (x + 56, 118), a)
        if b is not None:
            im.paste(b.resize((48, 48), Image.NEAREST), (x + 56, 134), b.resize((48, 48), Image.NEAREST))
        d.text((x, 170), "%d" % (i + 1), font=f, fill=FG)
    d.text((8, 188), "PLAYER AND MATCH", font=f, fill=YELLOW)
    items = [("WI-FI", iconlab.chosen("wifi", 10)), ("CABLE", iconlab.chosen("cable", 10)), ("PING", None), ("FAIR", icon8("shield")),
             ("NEW", recolor(icon8("shield"), YELLOW)), ("WARN", recolor(icon8("shield"), ORANGE)),
             ("DIRECT", direct_icon()), ("RELAY", relay_icon()), ("ROM", iconlab.chosen("rom", 10)), ("WATCH", iconlab.chosen("watch", 10)),
             ("REPLAY", iconlab.chosen("replay", 10)), ("PASS", iconlab.chosen("pass", 16))]
    for i, (name, ic) in enumerate(items):
        x = 8 + (i % 6) * 78
        y = 202 + (i // 6) * 48
        if ic is None:
            for j, ms in enumerate((20, 60, 100, 200)):
                b = ping_bars(ms)
                im.paste(b.resize((22, 16), Image.NEAREST), (x + j * 0, y), b.resize((22, 16), Image.NEAREST)) if j == 0 else None
                im.paste(b, (x + 26 + (j % 2) * 14, y + (j // 2) * 10), b)
        else:
            k = 3 if ic.width <= 16 else 2
            if ic.width == 16:
                k = 2
            big = ic.resize((ic.width * k, ic.height * k), Image.NEAREST)
            im.paste(big, (x, y), big)
            im.paste(ic, (x + big.width + 4, y), ic)
        d.text((x, y + 30), name, font=f, fill=COMMENT)
    return im


# ------------------------------------------------------------ the chosen icons
# (iconlab.CHOSEN; these replace the first sketches above)

def planet(lit=True, s=12, color=CYAN):
    return iconlab.chosen("online", s, lit)


def ping_bars(ms, lit=True):
    return iconlab.ping_bars(ms, 12, 9)


def conn_icon(p):
    return iconlab.chosen("cable" if p["conn"] == "cable" else "wifi", 10)


def wl(cv, x, y, w, l):
    """Wins and losses: the trophy and the number, the skull and the number."""
    cv.paste_icon(iconlab.chosen("win", 10), x, y)
    cv.text(x + 12, y + 1, str(w), GREEN)
    x2 = x + 12 + 8 * len(str(w)) + 8
    cv.paste_icon(iconlab.chosen("loss", 10), x2, y)
    cv.text(x2 + 12, y + 1, str(l), RED)


def wl_img(im, d, x, y, w, l, f8):
    a, b = iconlab.chosen("win", 10), iconlab.chosen("loss", 10)
    im.paste(a, (x, y), a)
    d.text((x + 12, y + 1), str(w), font=f8, fill=GREEN)
    x2 = x + 12 + 8 * len(str(w)) + 8
    im.paste(b, (x2, y), b)
    d.text((x2 + 12, y + 1), str(l), font=f8, fill=RED)



# ------------------------------------------------------------ output

def save_anim(frames, durations, out, name):
    big = [f.im.resize((W * SCALE, H * SCALE), Image.NEAREST) for f in frames]
    big[0].save(os.path.join(out, name + ".gif"), save_all=True, append_images=big[1:], duration=durations,
                loop=0, disposal=1)
    cols = 4
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (W + 4) + 4, rows * (H + 4) + 4), (0x30, 0x30, 0x40))
    for i, f in enumerate(frames):
        sheet.paste(f.im, (4 + (i % cols) * (W + 4), 4 + (i // cols) * (H + 4)))
    sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).save(os.path.join(out, name + "-frames.png"))


def main():
    global ART
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    ART = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("FE_ART", "")
    fm.ART = ART
    os.makedirs(out, exist_ok=True)
    ti = theme_icons()
    shots = {
        "01-home": home_screen("sf2ce"),
        "01b-home-flycast-dojo": home_screen("mvsc2"),
        "02-game-menu": game_menu(False),
        "02b-game-menu-party": game_menu(True),
        "02c-game-menu-party-only": game_menu_party_only(),
        "03-lobby-looking": lobby_screen("mango"),
        "03b-lobby-playing": lobby_screen("kiwi"),
        "03c-lobby-card": lobby_card("mango"),
        "03d-lobby-watch-needs-rom": lobby_card_no_rom(),
        "04a-cards": cards_screen(),
        "04b-cards-in-list": cards_in_list(),
        "08-card-details": details_screen(),
        "10-duel-wait": duel_wait("ready"),
        "10b-duel-wait-download": duel_wait("download"),
        "10c-duel-wait-relay": duel_wait("relay"),
        "11-party-lobby": party_lobby(),
        "12-transfer": transfer_screen(),
        "12b-lobby-someone-downloading": lobby_screen("guava", ("GUAVA#3mxp IS DOWNLOADING", "SF2: WILL JOIN AT 100%")),
        "13-result": result_screen("win"),
        "13c-result-desync": result_screen("desync"),
        "14a-osd-over-frontend": osd_over_frontend(),
        "14b-osd-over-game": osd_over_game(),
        "15a-setup-frontend": setup_frontend(ti),
        "15b-setup-online": setup_online(ti),
        "16-options": options_screen(),
    }
    for name, cv in shots.items():
        cv.save(os.path.join(out, name + ".png"))
        print(name)
    left = swipe_frames(-1)
    save_anim(left, [70] * (len(left) - 1) + [900], out, "05-swipe-pass")
    left[4].save(os.path.join(out, "05-swipe-pass.png"))
    right = swipe_frames(1)
    save_anim(right, [70] * (len(right) - 1) + [1200], out, "06-swipe-duel")
    right[4].save(os.path.join(out, "06-swipe-duel.png"))
    right[-1].save(os.path.join(out, "06b-fist-sent.png"))
    sw, swd = page_switch()
    save_anim(sw, swd, out, "01c-page-switch")
    sw[12].save(os.path.join(out, "01c-page-switch.png"))
    inc = incoming_frames()
    save_anim(inc, [300] * len(inc), out, "07-incoming-fist")
    inc[0].save(os.path.join(out, "07-incoming-fist.png"))
    duel, durs = duel_frames()
    save_anim(duel, durs, out, "09-duel")
    duel[-1].save(os.path.join(out, "09-duel.png"))
    names = sorted(n for n in os.listdir(out) if n.endswith(".png") and n[:2].isdigit() and "frames" not in n
                   and not n.startswith(("00", "18")))
    cols = 4
    rows = (len(names) + cols - 1) // cols
    over = Image.new("RGB", (cols * (W + 8) + 8, rows * (H + 20) + 8), (0x30, 0x30, 0x40))
    od = ImageDraw.Draw(over)
    od.fontmode = "1"
    for i, n in enumerate(names):
        im = Image.open(os.path.join(out, n)).convert("RGB").resize((W, H), Image.NEAREST)
        x, y = 8 + (i % cols) * (W + 8), 8 + (i // cols) * (H + 20)
        over.paste(im, (x, y + 12))
        od.text((x, y), n[:-4].upper(), font=font(8), fill=YELLOW)
    over.save(os.path.join(out, "00-overview.png"))
    setup_gloves_sheet(ti).resize((setup_gloves_sheet(ti).width * 2, 240), Image.NEAREST).save(
        os.path.join(out, "icons", "14-setup-gloves.png"))
    print("animations and icons")


if __name__ == "__main__":
    main()
