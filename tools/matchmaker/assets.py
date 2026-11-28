#!/usr/bin/env python3
"""The Matchmaker's icons as PNG files for the program: the ones the user
chose (iconlab.CHOSEN, the gloves of fists.py option 3), at the sizes the
screens use. The program loads them from fliperos-setup/gui/icons/matchmaker.

    python3 assets.py [OUT_DIR]     # default: fliperos-setup/gui/icons/matchmaker
"""
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fists  # noqa: E402
import iconlab  # noqa: E402

FIST = 3
GLOVE_K = 0.72          # two solid gloves next to an icon: this much of its height


def gloves(variant=FIST, spark=True):
    """The pair; with the spark, as much room under the gloves as the spark takes above."""
    p = fists.pair(variant, fx=spark)
    if not spark:
        return p
    out = Image.new("RGBA", (p.width, p.height + 12), (0, 0, 0, 0))
    out.paste(p, (0, 0), p)
    return out


def at_height(im, h):
    return iconlab.shrink(im, max(1, round(im.width * h / im.height)), h)


def at_width(im, w):
    return iconlab.shrink(im, w, max(1, round(im.height * w / im.width)))


def ping(level):
    return iconlab.ping_bars({4: 20, 3: 60, 2: 100, 1: 200}[level], 12, 9)


def build():
    out = {}
    for size in (10, 14, 32):
        out["online_%d" % size] = iconlab.chosen("online", size, True)
        out["online_dim_%d" % size] = iconlab.chosen("online", size, False)
    out["gloves_tile"] = at_width(gloves(), 38)
    out["gloves_big"] = gloves()
    for h in (10, 14):
        out["gloves_%d" % h] = at_height(gloves(spark=False), round(h * GLOVE_K))
    for name in ("lobby", "replay", "friend", "watch"):
        out[name + "_32"] = iconlab.chosen(name, 32)
    for name in ("replay", "watch", "wifi", "cable", "win", "loss", "rom"):
        out[name + "_10"] = iconlab.chosen(name, 10)
    out["rom_16"] = iconlab.chosen("rom", 16)
    out["pass_16"] = iconlab.chosen("pass", 16)
    out["pass_14"] = iconlab.chosen("pass", 14)
    for level in (1, 2, 3, 4):
        out["ping_%d" % level] = ping(level)
    out["retry_32"] = iconlab.retry_icon()
    out["back_32"] = iconlab.Icon(32).poly([(3, 16), (22, 3), (22, 11), (29, 11), (29, 21), (22, 21), (22, 29)],
                                           "purple").im
    return out


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "fliperos-setup", "gui", "icons",
                                                               "matchmaker")
    os.makedirs(dest, exist_ok=True)
    icons = build()
    for name, im in sorted(icons.items()):
        im.save(os.path.join(dest, name + ".png"), optimize=True)
    print(len(icons), "icons in", os.path.normpath(dest))


if __name__ == "__main__":
    main()
