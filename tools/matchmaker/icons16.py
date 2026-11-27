#!/usr/bin/env python3
"""16-bit icons of the Matchmaker (the same style as fists.py): the online
mark and the replay, each in three options, shaded and outlined like a
SNES / Mega Drive sprite. Every function draws at the size asked, so the
small ones are drawn, not shrunk.

    python3 icons16.py OUT.png      # the sheet of the options, numbered
"""
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fists import MATERIALS, outline_all, part  # noqa: E402

OCEAN = ((0x0C, 0x1C, 0x40), (0x1C, 0x48, 0x9C), (0x30, 0x78, 0xD8), (0x6C, 0xB4, 0xFF), (0xE8, 0xF6, 0xFF))
LAND = ((0x0C, 0x30, 0x14), (0x1C, 0x7A, 0x34), (0x3C, 0xB8, 0x4C), (0x8C, 0xE8, 0x70), (0xE0, 0xFF, 0xC8))
YELLOW = (0xF1, 0xFA, 0x8C)
CYAN = (0x8B, 0xE9, 0xFD)
PINK = (0xFF, 0x79, 0xC6)
WHITE = (0xFF, 0xFF, 0xFF)
SPACE = (0x0B, 0x0B, 0x12)


def _tone(ramp, k):
    """k: 0 = in the light, 1 = in the shade."""
    o, s, b, l, h = ramp
    return h if k < 0.10 else l if k < 0.32 else b if k < 0.66 else s


def sphere(size, ramp=OCEAN, land=True, lit=True):
    """A shaded ball lit from the top left, with continents and a shine."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    px = im.load()
    r = size / 2 - 1
    cx = cy = size / 2
    lx, ly = cx - r * 0.45, cy - r * 0.45
    # the continents: blobs in sphere space
    blobs = [(-0.35, -0.15, 0.42, 0.30), (0.30, 0.25, 0.40, 0.34), (0.15, -0.55, 0.30, 0.18), (-0.25, 0.55, 0.28, 0.16)]
    for y in range(size):
        for x in range(size):
            dx, dy = x + 0.5 - cx, y + 0.5 - cy
            if dx * dx + dy * dy > r * r:
                continue
            k = math.hypot(x + 0.5 - lx, y + 0.5 - ly) / (2 * r)
            nx, ny = dx / r, dy / r
            on_land = land and any(((nx - bx) / bw) ** 2 + ((ny - by) / bh) ** 2 <= 1 for bx, by, bw, bh in blobs)
            ramp_here = LAND if on_land else ramp
            c = _tone(ramp_here, k if lit else min(1, k + 0.35))
            px[x, y] = c + (255,)
    outline_all(im, ramp[0])
    return im


def ring_over(im, color, front=True, tilt=0.33):
    """An orbit ring around the ball: the back half before, the front half after."""
    w, h = im.size
    d = ImageDraw.Draw(im)
    rx, ry = w / 2 - 1, max(2, h * tilt / 2)
    box = [w / 2 - rx, h / 2 - ry + 1, w / 2 + rx, h / 2 + ry + 1]
    if front:
        d.arc(box, 0, 180, fill=color + (255,), width=max(1, w // 16))
    else:
        d.arc(box, 180, 360, fill=color + (255,), width=max(1, w // 16))


def globe(size, lit=True):
    """Online, option 1: the Earth with a glowing orbit (people online around the world)."""
    pad = max(2, size // 8)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ball = sphere(size - 2 * pad, lit=lit)
    ring_back = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ring_over(ring_back, CYAN if lit else MATERIALS["cyan"][1], front=False)
    im.alpha_composite(ring_back)
    im.alpha_composite(ball, (pad, pad))
    ring_over(im, YELLOW if lit else MATERIALS["cyan"][1], front=True)
    if lit and size >= 12:
        d = ImageDraw.Draw(im)
        for x, y in ((size - 3, size // 2 + 1), (2, size // 2 - 1)):
            d.point((x, y), fill=WHITE + (255,))
    return im


def cabinet_sprite(w, h, mat):
    """A little arcade cabinet in profile, shaded."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    part(im, (0, 0, w - 1, h - 1), max(1, w // 6), mat, ramp=(0.25, 0.75))
    d = ImageDraw.Draw(im)
    sx0, sy0, sx1, sy1 = 2, 2, max(2, w - 3), max(2, h // 2 - 1)
    d.rectangle([sx0, sy0, sx1, sy1], fill=(0x10, 0x10, 0x20, 255))
    if sx1 - sx0 >= 2:
        d.rectangle([sx0 + 1, sy0 + 1, sx1 - 1, sy0 + 1 + max(0, (sy1 - sy0) // 3)], fill=CYAN + (255,))
    d.line([(2, h // 2 + 2), (w - 3, h // 2 + 2)], fill=MATERIALS[mat][0] + (255,))
    d.point((w // 2 - 1, h // 2 + 4), fill=YELLOW + (255,))
    d.point((w // 2 + 1, h // 2 + 4), fill=PINK + (255,))
    return im


def cabinets_link(size, lit=True):
    """Online, option 2: two cabinets, a spark between them."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cw, ch = max(5, size * 5 // 16), max(8, size * 11 // 16)
    a = cabinet_sprite(cw, ch, "pink" if lit else "purple")
    b = cabinet_sprite(cw, ch, "cyan" if lit else "purple")
    y = size - ch - 1
    im.alpha_composite(a, (0, y))
    im.alpha_composite(b, (size - cw, y))
    d = ImageDraw.Draw(im)
    color = YELLOW if lit else MATERIALS["purple"][1]
    mid_y = y + ch // 4
    pts = [(cw, mid_y), (size // 2 - 1, mid_y - size // 6), (size // 2 + 1, mid_y + size // 10), (size - cw - 1, mid_y - size // 8)]
    d.line(pts, fill=color + (255,), width=max(1, size // 12))
    return im


def globe_signal(size, lit=True):
    """Online, option 3: the Earth sending waves (the cabinet on the air)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    gs = size * 3 // 4
    ball = sphere(gs, lit=lit)
    im.alpha_composite(ball, ((size - gs) // 2, size - gs))
    d = ImageDraw.Draw(im)
    cx = size / 2
    color = YELLOW if lit else MATERIALS["purple"][1]
    for i, r in enumerate((size * 0.30, size * 0.46)):
        d.arc([cx - r, size * 0.55 - r, cx + r, size * 0.55 + r], 230, 310, fill=color + (255,), width=max(1, size // 16))
    return im


def vhs(size):
    """Replay, option 1: a video tape (the match is recorded) with a rewind arrow."""
    w, h = size, max(6, size * 11 // 16)
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    y0 = (size - h) // 2 + 1
    tape = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    dark = "purple"
    part(tape, (0, 0, w - 1, h - 1), max(1, w // 10), dark, ramp=(0.2, 0.8))
    d = ImageDraw.Draw(tape)
    body = (0x22, 0x22, 0x30, 255)
    d.rectangle([2, 2, w - 3, h - 3], fill=body)
    d.rectangle([2, 2, w - 3, 2 + max(1, h // 5)], fill=PINK + (255,))       # the label
    rr = max(1, h // 4)
    for cx in (w // 3, w - w // 3 - 1):
        cy = h // 2 + max(1, h // 8)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=(0xE8, 0xE8, 0xF0, 255))
        d.point((cx, cy), fill=body)
        if rr >= 3:
            for ang in (0, 120, 240):
                a = math.radians(ang)
                d.point((round(cx + (rr - 1) * math.cos(a)), round(cy + (rr - 1) * math.sin(a))), fill=body)
    wx0, wx1 = w // 3 + rr + 1, w - w // 3 - rr - 2
    if wx1 >= wx0:
        d.rectangle([wx0, h // 2, wx1, h // 2 + max(1, h // 6)], fill=(0x6A, 0x3A, 0x20, 255))
    im.alpha_composite(tape, (0, y0))
    if size >= 14:   # the rewind arrows in a badge
        bs = size // 2 - 1
        badge = Image.new("RGBA", (bs, bs), (0, 0, 0, 0))
        bd = ImageDraw.Draw(badge)
        bd.ellipse([0, 0, bs - 1, bs - 1], fill=CYAN + (255,), outline=MATERIALS["cyan"][0] + (255,))
        m = bs // 2
        t = max(2, bs // 4)
        bd.polygon([(m - 1, m - t), (m - 1, m + t), (m - 1 - t, m)], fill=(0x10, 0x30, 0x40, 255))
        bd.polygon([(m + t - 1, m - t), (m + t - 1, m + t), (m - 1, m)], fill=(0x10, 0x30, 0x40, 255))
        im.alpha_composite(badge, (size - bs, size - bs))
    return im


def rewind_arrow(size):
    """Replay, option 2: a thick round arrow around a play triangle."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    o, s, b, l, h = MATERIALS["cyan"]
    t = max(2, size // 6)
    box = [t // 2, t // 2, size - 1 - t // 2, size - 1 - t // 2]
    d.arc(box, 60, 360 - 10, fill=s + (255,), width=t)
    d.arc([box[0] - 1, box[1] - 1, box[2] - 1, box[3] - 1], 70, 340, fill=b + (255,), width=max(1, t - 1))
    # the arrow head at the top right end of the arc
    ax, ay = size * 0.80, size * 0.20
    hs = t + 2
    d.polygon([(ax - hs, ay - 1), (ax + 2, ay - hs), (ax + 1, ay + hs - 1)], fill=b + (255,))
    m = size / 2
    tri = size * 0.20
    d.polygon([(m - tri * 0.7, m - tri), (m - tri * 0.7, m + tri), (m + tri, m)], fill=YELLOW + (255,))
    outline_all(im, o)
    return im


def clapper(size):
    """Replay, option 3: a clapperboard (the take of the match)."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    hb = max(5, size * 9 // 16)
    part(im, (0, size - hb, size - 1, size - 1), 1, "purple", ramp=(0.2, 0.8), shine=False)
    d = ImageDraw.Draw(im)
    d.rectangle([2, size - hb + 2, size - 3, size - 3], fill=(0x22, 0x22, 0x30, 255))
    d.text((3, size - hb + 3), "", fill=WHITE)
    top = size - hb - max(3, size // 5)
    stripes = Image.new("RGBA", (size, size - hb - top + 1), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stripes)
    sd.rectangle([0, 0, size - 1, stripes.height - 1], fill=(0xF0, 0xF0, 0xF0, 255))
    step = max(3, size // 5)
    for x in range(-stripes.height, size, step * 2):
        sd.polygon([(x, stripes.height), (x + step, stripes.height), (x + step + stripes.height, 0), (x + stripes.height, 0)],
                   fill=(0x22, 0x22, 0x30, 255))
    stripes = stripes.rotate(-8, resample=Image.NEAREST, expand=False)
    im.alpha_composite(stripes, (0, top))
    m = size // 2
    tri = max(2, size // 6)
    d.polygon([(m - tri, size - hb // 2 - tri), (m - tri, size - hb // 2 + tri), (m + tri, size - hb // 2)], fill=YELLOW + (255,))
    outline_all(im, MATERIALS["purple"][0])
    return im


ONLINE = {1: ("EARTH + ORBIT", globe), 2: ("CABINETS LINKED", cabinets_link), 3: ("EARTH ON THE AIR", globe_signal)}
REPLAY = {1: ("VIDEO TAPE", vhs), 2: ("ROUND ARROW", rewind_arrow), 3: ("CLAPPERBOARD", clapper)}


def sheet(path):
    from PIL import ImageFont
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fliperos-setup", "gui",
                                           "fonts", "PressStart2P-Regular.ttf"), 8)
    out = Image.new("RGB", (640, 440), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    for row, (title, table) in enumerate((("ONLINE MARK", ONLINE), ("REPLAY", REPLAY))):
        y = 10 + row * 215
        d.text((10, y), title, font=font, fill=YELLOW)
        for i, n in enumerate(sorted(table)):
            name, fn = table[n]
            x = 10 + i * 210
            big = fn(32).resize((96, 96), Image.NEAREST)
            out.paste(big, (x + 14, y + 16), big)
            sx = x + 118
            for s in (32, 16, 12, 10):
                ic = fn(s)
                out.paste(ic, (sx, y + 24), ic)
                sx += s + 6
            if table is ONLINE:
                dim = fn(16, lit=False)
                out.paste(dim, (x + 118, y + 64), dim)
                d.text((x + 140, y + 68), "OFF", font=font, fill=(0x62, 0x72, 0xA4))
            d.text((x, y + 16), str(n), font=font, fill=PINK)
            d.text((x + 14, y + 120), name, font=font, fill=(0x62, 0x72, 0xA4))
    out.save(path)


if __name__ == "__main__":
    sheet(sys.argv[1] if len(sys.argv) > 1 else "icons16.png")
