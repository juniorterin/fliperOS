#!/usr/bin/env python3
"""The Matchmaker's "heart": two fists bumping, drawn as 16-bit sprites.

Each fist is built from rounded parts (back of the hand, four fingers, the
thumb with its nail, the wrist and the sleeve), each with a dark outline and
four tones (shadow, base, light, highlight), lit from the top left, like a
SNES / Mega Drive sprite. The pair is one fist pointing right and its mirror,
with an effect behind the contact.

    python3 fists.py OUT.png      # the sheet of the options, numbered
"""
import sys

from PIL import Image, ImageDraw

# outline, shadow, base, light, highlight
MATERIALS = {
    "skin": ((0x4A, 0x22, 0x18), (0xC0, 0x6A, 0x40), (0xF0, 0xA8, 0x70), (0xFF, 0xCC, 0x98), (0xFF, 0xF0, 0xDC)),
    "skin_dark": ((0x2A, 0x14, 0x0C), (0x6A, 0x38, 0x20), (0x9A, 0x5A, 0x36), (0xC0, 0x80, 0x52), (0xE8, 0xB8, 0x88)),
    "yellow": ((0x6A, 0x40, 0x10), (0xD8, 0x90, 0x20), (0xFF, 0xC8, 0x38), (0xFF, 0xE0, 0x70), (0xFF, 0xF8, 0xC8)),
    "red": ((0x40, 0x08, 0x10), (0xA0, 0x10, 0x20), (0xE0, 0x28, 0x30), (0xFF, 0x60, 0x60), (0xFF, 0xD0, 0xD0)),
    "blue": ((0x08, 0x10, 0x40), (0x18, 0x30, 0xA0), (0x30, 0x60, 0xE0), (0x70, 0xA0, 0xFF), (0xD8, 0xE8, 0xFF)),
    "pink": ((0x50, 0x10, 0x40), (0xB0, 0x30, 0x80), (0xFF, 0x79, 0xC6), (0xFF, 0xA8, 0xDC), (0xFF, 0xE8, 0xF6)),
    "cyan": ((0x10, 0x40, 0x50), (0x30, 0x90, 0xB0), (0x8B, 0xE9, 0xFD), (0xC0, 0xF6, 0xFF), (0xFF, 0xFF, 0xFF)),
    "metal": ((0x20, 0x24, 0x30), (0x60, 0x68, 0x80), (0xA0, 0xA8, 0xC0), (0xD0, 0xD8, 0xE8), (0xFF, 0xFF, 0xFF)),
    "white": ((0x40, 0x40, 0x50), (0xA8, 0xA8, 0xBC), (0xE8, 0xE8, 0xF0), (0xFF, 0xFF, 0xFF), (0xFF, 0xFF, 0xFF)),
    "purple": ((0x2A, 0x18, 0x48), (0x6A, 0x4C, 0x9C), (0xBD, 0x93, 0xF9), (0xD8, 0xC0, 0xFF), (0xF4, 0xEC, 0xFF)),
}
YELLOW = (0xF1, 0xFA, 0x8C)
ORANGE = (0xFF, 0xB8, 0x6C)
WHITE = (0xFF, 0xFF, 0xFF)
PINK = (0xFF, 0x79, 0xC6)
CYAN = (0x8B, 0xE9, 0xFD)
SPACE = (0x0B, 0x0B, 0x12)
FW, FH = 34, 28   # one fist


def part(img, box, r, mat, outline=True, ramp=(0.28, 0.74), shine=True):
    """A rounded part with its outline and four tones, lit from the top left."""
    o, s, b, l, h = MATERIALS[mat]
    x0, y0, x1, y1 = box
    d = ImageDraw.Draw(img)
    if outline:
        d.rounded_rectangle(box, r, fill=o + (255,))
        x0, y0, x1, y1 = x0 + 1, y0 + 1, x1 - 1, y1 - 1
        r = max(0, r - 1)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((x0, y0, x1, y1), r, fill=255)
    px, mk = img.load(), mask.load()
    hgt = max(1, y1 - y0)
    for y in range(max(0, y0), min(img.height, y1 + 1)):
        t = (y - y0) / hgt
        c = l if t < ramp[0] else s if t > ramp[1] else b
        for x in range(max(0, x0), min(img.width, x1 + 1)):
            if mk[x, y]:
                # the left edge a little darker, the right edge (the front) keeps the tone
                px[x, y] = (s if (x - x0) < 1 and t > 0.2 else c) + (255,)
    if shine and x1 - x0 > 4:
        for x in range(x0 + 2, x0 + 2 + max(1, (x1 - x0) // 3)):
            if mk[x, y0 + 1]:
                px[x, y0 + 1] = h + (255,)


def outline_all(img, color):
    """The sprite's outer line: every empty pixel next to a filled one."""
    a = img.getchannel("A").load()
    px = img.load()
    w, hh = img.size
    edge = []
    for y in range(hh):
        for x in range(w):
            if a[x, y]:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                xx, yy = x + dx, y + dy
                if 0 <= xx < w and 0 <= yy < hh and a[xx, yy]:
                    edge.append((x, y))
                    break
    for x, y in edge:
        px[x, y] = color + (255,)


def side_fist(skin="skin", sleeve="pink", tape=False, glove=None):
    """A fist pointing right, seen from the side: the thumb over the index
    finger, the four fingers stacked on the front, the wrist and the sleeve."""
    im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    back = glove or skin
    if sleeve:
        part(im, (-4, 9, 9, 24), 2, sleeve, shine=False)
        part(im, (6, 8, 10, 25), 1, sleeve, ramp=(0.5, 0.9), shine=False)
    if tape:
        part(im, (6, 8, 12, 25), 1, "white", ramp=(0.3, 0.8), shine=False)
        d = ImageDraw.Draw(im)
        for y in (12, 16, 20):
            d.line([(7, y), (11, y + 1)], fill=MATERIALS["white"][1] + (255,))
    part(im, (9, 4, 24, 26), 5, back)                      # back of the hand
    for box in ((15, 21, 29, 26), (15, 16, 31, 22), (15, 11, 32, 17), (15, 6, 31, 12)):
        part(im, box, 3, skin, ramp=(0.3, 0.7))          # pinky, ring, middle, index
    part(im, (10, 1, 27, 8), 3, skin, ramp=(0.35, 0.8))    # the thumb
    o, s, b, l, h = MATERIALS[skin]
    nail = MATERIALS["white"][3] if skin != "metal" else MATERIALS["cyan"][2]
    d = ImageDraw.Draw(im)
    d.rectangle([23, 3, 25, 5], fill=l + (255,))
    d.point((24, 3), fill=nail + (255,))
    d.point((25, 3), fill=nail + (255,))
    for y in (8, 13, 18, 23):                              # a knuckle shine on each finger
        d.point((28 if y != 23 else 25, y), fill=h + (255,))
    return im


def glove_fist(mat="red", cuff="white"):
    """A boxing glove pointing right: the round body, the thumb seam, the laced cuff."""
    im = Image.new("RGBA", (FW, FH), (0, 0, 0, 0))
    part(im, (0, 7, 11, 25), 2, cuff, ramp=(0.3, 0.75), shine=False)
    d = ImageDraw.Draw(im)
    for y in (11, 15, 19):
        d.line([(2, y), (8, y + 2)], fill=MATERIALS[cuff][1] + (255,))
    part(im, (8, 1, 33, 27), 11, mat, ramp=(0.3, 0.72))
    o, s, b, l, h = MATERIALS[mat]
    d.arc([12, 6, 30, 20], 200, 330, fill=s + (255,))     # the thumb seam
    d.ellipse([13, 4, 19, 8], fill=h + (255,))            # the shine
    d.point((26, 6), fill=h + (255,))
    return im


def mitt_fist(skin="skin", glove="red"):
    """A fighter's fingerless glove: the glove on the back, bare fingers, tape on the wrist."""
    return side_fist(skin, sleeve=None, tape=True, glove=glove)


def heart(w, h, mat="pink"):
    o, s, b, l, hh = MATERIALS[mat]
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = w // 4
    d.ellipse([0, 0, 2 * r, 2 * r], fill=b + (255,))
    d.ellipse([w - 2 * r - 1, 0, w - 1, 2 * r], fill=b + (255,))
    d.polygon([(0, r), (w - 1, r), (w // 2, h - 1)], fill=b + (255,))
    d.ellipse([3, 3, r, r], fill=l + (255,))
    outline_all(im, o)
    return im


def hit_spark(r):
    """A fighting-game hit spark: white core, yellow, orange tips."""
    import math
    im = Image.new("RGBA", (2 * r + 1, 2 * r + 1), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for rr, color, k in ((r, ORANGE, 0.42), (int(r * 0.78), YELLOW, 0.45), (int(r * 0.45), WHITE, 0.5)):
        pts = []
        for i in range(16):
            a = -math.pi / 2 + i * math.pi / 8
            rad = rr if i % 2 == 0 else rr * k
            pts.append((r + rad * math.cos(a), r + rad * math.sin(a)))
        d.polygon(pts, fill=color + (255,))
    return im


def spark_lines(img, cx, top):
    d = ImageDraw.Draw(img)
    for x0, y0, x1, y1 in ((cx, top, cx, top + 5), (cx - 8, top + 3, cx - 5, top + 6), (cx + 8, top + 3, cx + 5, top + 6)):
        d.line([(x0, y0), (x1, y1)], fill=YELLOW + (255,), width=2)


def ring(img, cx, cy, r, color):
    d = ImageDraw.Draw(img)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color + (255,), width=2)
    d.ellipse([cx - r + 4, cy - r + 4, cx + r - 4, cy + r - 4], outline=color + (160,), width=1)


def metal_glow(im):
    d = ImageDraw.Draw(im)
    for y in (9, 14, 19):
        d.line([(19, y), (27, y)], fill=CYAN + (255,))
    return im


OPTIONS = {
    1: dict(name="SKIN, SLEEVES", left=lambda: side_fist("skin", "pink"), right=lambda: side_fist("skin", "cyan"), fx="spark"),
    2: dict(name="FIGHTER TAPE", left=lambda: side_fist("skin", None, tape=True), right=lambda: side_fist("skin_dark", None, tape=True), fx="hit"),
    3: dict(name="BOXING RED/BLUE", left=lambda: glove_fist("red"), right=lambda: glove_fist("blue"), fx="spark"),
    4: dict(name="BOXING PINK/CYAN", left=lambda: glove_fist("pink"), right=lambda: glove_fist("cyan"), fx="heart"),
    5: dict(name="EMOJI YELLOW", left=lambda: side_fist("yellow", "pink"), right=lambda: side_fist("yellow", "cyan"), fx="spark"),
    6: dict(name="PINK VS CYAN", left=lambda: side_fist("pink", "purple"), right=lambda: side_fist("cyan", "purple"), fx="spark"),
    7: dict(name="FINGERLESS GLOVES", left=lambda: mitt_fist("skin", "red"), right=lambda: mitt_fist("skin_dark", "blue"), fx="hit"),
    8: dict(name="ROBOT", left=lambda: metal_glow(side_fist("metal", "purple")), right=lambda: metal_glow(side_fist("metal", "purple")), fx="ring"),
    9: dict(name="ON A HEART", left=lambda: side_fist("skin", "pink"), right=lambda: side_fist("skin_dark", "cyan"), fx="bigheart"),
    10: dict(name="P1 RED / P2 BLUE", left=lambda: side_fist("skin", "red"), right=lambda: side_fist("skin_dark", "blue"), fx="hit"),
}


def pair(n, fx=True):
    """Option n: the two fists, knuckles touching, and the effect behind: 70x40.
    fx=False: the fists alone, cut to their own height (for a line of text)."""
    opt = OPTIONS[n]
    a = opt["left"]()
    b = opt["right"]().transpose(Image.FLIP_LEFT_RIGHT)
    w, h = 2 * FW + 2, FH + 12
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cx, cy = w // 2, 12 + FH // 2
    fx = opt["fx"] if fx else None
    if fx == "hit":
        sp = hit_spark(13)
        im.paste(sp, (cx - 13, cy - 13 - 4), sp)
    elif fx == "heart":
        ht = heart(22, 19)
        im.paste(ht, (cx - 11, 0), ht)
    elif fx == "bigheart":
        ht = heart(48, 40)
        im.paste(ht, (cx - 24, 0), ht)
    elif fx == "ring":
        ring(im, cx, cy - 2, 17, CYAN)
    im.paste(a, (0, 12), a)
    im.paste(b, (FW + 2, 12), b)
    if fx == "spark":
        spark_lines(im, cx, 1)
    return im if fx is not None or opt["fx"] is None else im.crop(im.getbbox())


def sheet(path):
    from PIL import ImageFont
    import os
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "fliperos-setup", "gui",
                                           "fonts", "PressStart2P-Regular.ttf"), 8)
    cols, cw, ch = 2, 300, 150
    out = Image.new("RGB", (cols * cw + 20, 5 * ch + 20), SPACE)
    d = ImageDraw.Draw(out)
    d.fontmode = "1"
    for i, n in enumerate(sorted(OPTIONS)):
        x, y = 10 + (i % cols) * cw, 10 + (i // cols) * ch
        p = pair(n)
        big = p.resize((p.width * 3, p.height * 3), Image.NEAREST)
        out.paste(big, (x + 30, y + 8), big)
        out.paste(p, (x + 30 + big.width + 12, y + 30), p)
        d.text((x, y + 4), str(n), font=font, fill=PINK)
        d.text((x + 30, y + 134), OPTIONS[n]["name"], font=font, fill=(0x62, 0x72, 0xA4))
    out.save(path)


if __name__ == "__main__":
    sheet(sys.argv[1] if len(sys.argv) > 1 else "fists.png")
