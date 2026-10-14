# Tema da interface grafica: as cores, as fontes e os icones.
#
# As cores sao as do Dracula, as mesmas de fliperos-setup/lib/ui.sh
# (UI_PALETTE) e de config/vtrgb-dracula, com os mesmos papeis: roxo na barra
# e nas molduras, rosa no titulo e no item escolhido, ciano no status e nas
# dicas, "comment" no que e apagado, verde/laranja/vermelho em sim, aviso e
# erro.

import os

import pygame

BG = (0x28, 0x2A, 0x36)
RED = (0xFF, 0x55, 0x55)
GREEN = (0x50, 0xFA, 0x7B)
YELLOW = (0xF1, 0xFA, 0x8C)
PURPLE = (0xBD, 0x93, 0xF9)
PINK = (0xFF, 0x79, 0xC6)
CYAN = (0x8B, 0xE9, 0xFD)
FG = (0xF8, 0xF8, 0xF2)
COMMENT = (0x62, 0x72, 0xA4)
ORANGE = (0xFF, 0xB8, 0x6C)
# Os dois tons do site (website/src/app/globals.css) para fundo de painel e
# linha.
BG_DEEP = (0x19, 0x1A, 0x21)
LINE = (0x44, 0x47, 0x5A)

# A tela logica. O modo de video e 640x240, com o pixel duas vezes mais
# largo que alto: a interface e desenhada em 320x240 e cada pixel vira 2x1,
# o que da pixels quadrados no tubo 4:3.
WIDTH, HEIGHT = 320, 240
MODE = (640, 240)
# Margem de overscan: nada de texto fora dela.
SAFE_X, SAFE_Y = 16, 10
SAFE_W = WIDTH - 2 * SAFE_X

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIRS = [
    os.environ.get("FLIPEROS_GUI_FONTS", ""),
    os.path.join(HERE, "..", "..", "config", "fonts"),
    "/usr/share/fonts/truetype/fliperos",
]
# Fontes de pixel, sem antialias: a Press Start 2P (8x8) nos titulos e nos
# botoes, a Jersey 10 (maiusculas de 11 pixels) no texto.
FONT_FILES = {
    "title": ("press-start-2p/PressStart2P-Regular.ttf", 8),
    "text": ("jersey10/Jersey10-Regular.ttf", 20),
}

_fonts = {}


def font(name):
    if name not in _fonts:
        rel, size = FONT_FILES[name]
        for base in FONT_DIRS:
            for path in (os.path.join(base, rel), os.path.join(base, os.path.basename(rel))):
                if base and os.path.isfile(path):
                    _fonts[name] = pygame.font.Font(path, size)
                    return _fonts[name]
        raise SystemExit("fliperos-gui: font not found: " + rel)
    return _fonts[name]


# Icones de 16x16, uma letra por pixel ("." e transparente).
ICON_COLORS = {
    "P": PURPLE, "K": PINK, "C": CYAN, "F": FG, "M": COMMENT, "G": GREEN,
    "O": ORANGE, "R": RED, "Y": YELLOW, "D": BG_DEEP, "L": LINE,
}

ICONS = {
    "frontend": """
................
......RRRR......
.....RRFRRR.....
.....RRRRRR.....
.....RRRRRR.....
......RRRR......
.......FF.......
.......FF.......
.......FF.......
.......FF.......
...PPPPPPPPPP...
..PPPPPPPPPPPP..
..PPYYPPPPGGPP..
..PPPPPPPPPPPP..
.MMMMMMMMMMMMMM.
................
""",
    "setup": """
................
......CCCC......
..CC..CCCC..CC..
..CCCCCCCCCCCC..
...CCCCCCCCCC...
...CCC....CCC...
.CCCC......CCCC.
.CCCC......CCCC.
.CCCC......CCCC.
.CCCC......CCCC.
...CCC....CCC...
...CCCCCCCCCC...
..CCCCCCCCCCCC..
..CC..CCCC..CC..
......CCCC......
................
""",
    "desktop": """
................
.PPPPPPPPPPPPPP.
.PDDDDDDDDDDDDP.
.PDCCCCDDDDDDDP.
.PDDDDDDDDDDDDP.
.PDKKKKKKDDDDDP.
.PDDDDDDDDDDDDP.
.PDGGGGDDDDDDDP.
.PDDDDDDDDDDDDP.
.PDDDDDDDDDDDDP.
.PPPPPPPPPPPPPP.
......MMMM......
......MMMM......
....MMMMMMMM....
................
................
""",
    "shell": """
................
.MMMMMMMMMMMMMM.
.MRMYMGMMMMMMMM.
.MMMMMMMMMMMMMM.
.MDDDDDDDDDDDDM.
.MDGDDDDDDDDDDM.
.MDDGDDDDDDDDDM.
.MDDDGDDDDDDDDM.
.MDDGDDDDDDDDDM.
.MDGDDDFFFFDDDM.
.MDDDDDDDDDDDDM.
.MDDDDDDDDDDDDM.
.MMMMMMMMMMMMMM.
................
................
................
""",
    "power": """
................
.......OO.......
.......OO.......
...OO..OO..OO...
..OOO..OO..OOO..
..OO...OO...OO..
.OO....OO....OO.
.OO....OO....OO.
.OO..........OO.
.OO..........OO.
..OO........OO..
..OOO......OOO..
...OOOOOOOOOO...
.....OOOOOO.....
................
................
""",
    "install": """
................
.......GG.......
.......GG.......
.......GG.......
.......GG.......
....GGGGGGGG....
.....GGGGGG.....
......GGGG......
.......GG.......
................
.PPPPPPPPPPPPPP.
.PDDDDDDDDDDDDP.
.PDDDDDDDDGDYDP.
.PDDDDDDDDDDDDP.
.PPPPPPPPPPPPPP.
................
""",
    "recovery": """
................
................
..RRRRRRRRRRRR..
..RRRRRRRRRRRR..
..RRRRRFFRRRRR..
..RRRRRFFRRRRR..
..RRRRRFFRRRRR..
..RRFFFFFFFFRR..
..RRFFFFFFFFRR..
..RRRRRFFRRRRR..
..RRRRRFFRRRRR..
..RRRRRFFRRRRR..
..RRRRRRRRRRRR..
..RRRRRRRRRRRR..
................
................
""",
}
ICONS["terminal"] = ICONS["shell"]
ICONS["shutdown"] = ICONS["power"]

_icons = {}


def icon(name, scale):
    """A surface do icone ampliada, ou None quando nao ha icone com o nome."""
    if name not in ICONS:
        return None
    if (name, scale) not in _icons:
        rows = ICONS[name].split()
        surf = pygame.Surface((16, 16), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    surf.set_at((x, y), ICON_COLORS[ch])
        _icons[(name, scale)] = pygame.transform.scale(surf, (16 * scale, 16 * scale))
    return _icons[(name, scale)]
