#!/usr/bin/env python3
# As animacoes do marquee (128x32) em estilo synthwave: um desenho animado a
# esquerda, na frente de um sol listrado, e uma palavra em traco futurista com
# cromado neon (ciano, branco, magenta), com glitches de tempos em tempos (fatias
# deslocadas, separacao de cor, ruido) e uma linha de varredura. 3 s em laco, sem
# emenda. Pixel a pixel, sem suavizacao: cada pixel e um LED. So numpy + Pillow.
#
#   marquee-fliperos.gif       o logotipo padrao: um coqueiro balancando e FLIPEROS
#                              (a previa do painel web sem jogo nem sistema)
#   marquee-menu-ITEM.gif      os 5 itens do menu do FliperOS (fliperos-pixelcade
#                              menu ITEM): frontend (joystick), setup (engrenagens),
#                              desktop (monitor), shell (terminal), power (energia)
#
#   python3 tools/marquee-logo-anim.py [PASTA]      (padrao config/web)
#   PREVIEW=pasta python3 tools/marquee-logo-anim.py   tambem grava uma folha de cada
#                                                      e ampliacoes com pontos de LED
import math
import os
import random
import sys

import numpy as np
from PIL import Image

W, H = 128, 32
FPS = 25
N = 75                                    # 3 s
CYAN, WHITE, MAGENTA = (25, 227, 255), (255, 255, 255), (255, 62, 181)
PURPLE, ORANGE, YELLOW = (150, 70, 230), (255, 140, 60), (255, 220, 90)
DEEP, BLACK = (40, 18, 72), (0, 0, 0)


def mix(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def line(mask, x0, y0, x1, y1, brush=1):
    """Bresenham num mapa booleano; brush 2 = traco de 2x2."""
    x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        for bx in range(brush):
            for by in range(brush):
                if 0 <= x0 + bx < W and 0 <= y0 + by < H:
                    mask[y0 + by, x0 + bx] = True
        if x0 == x1 and y0 == y1:
            return
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def disc(cx, cy, r):
    yy, xx = np.mgrid[0:H, 0:W]
    return (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r


def stamp(frame, mask, color):
    """Pinta mask (uma cor ou uma funcao (y, x) -> cor) com um contorno preto de
    1 pixel em volta: o desenho se le na frente do sol."""
    grown = mask.copy()
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            grown |= np.roll(np.roll(mask, dy, 0), dx, 1)
    frame[grown & ~mask] = BLACK
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        frame[y, x] = color(y, x) if callable(color) else color


# -- A palavra: o mesmo traco do tools/zedmd-vector-anim.py ---------------------
GLYPHS = {
    'F': [[(0, 14), (0, 0), (8, 0)], [(0, 7), (6, 7)]],
    'L': [[(0, 0), (0, 14), (8, 14)]],
    'I': [[(0, 0), (6, 0)], [(3, 0), (3, 14)], [(0, 14), (6, 14)]],
    'P': [[(0, 14), (0, 0), (7, 0), (9, 2), (9, 5), (7, 7), (0, 7)]],
    'E': [[(8, 0), (0, 0), (0, 14), (8, 14)], [(0, 7), (6, 7)]],
    'R': [[(0, 14), (0, 0), (7, 0), (9, 2), (9, 5), (7, 7), (0, 7)], [(4, 7), (9, 14)]],
    'O': [[(2, 0), (7, 0), (9, 2), (9, 12), (7, 14), (2, 14), (0, 12), (0, 2), (2, 0)]],
    'S': [[(9, 2), (7, 0), (2, 0), (0, 2), (0, 5), (2, 7), (7, 7), (9, 9), (9, 12), (7, 14), (2, 14), (0, 12)]],
    'N': [[(0, 14), (0, 0), (9, 14), (9, 0)]],
    'T': [[(0, 0), (9, 0)], [(4.5, 0), (4.5, 14)]],
    'D': [[(0, 0), (6, 0), (9, 3), (9, 11), (6, 14), (0, 14), (0, 0)]],
    'U': [[(0, 0), (0, 12), (2, 14), (7, 14), (9, 12), (9, 0)]],
    'K': [[(0, 0), (0, 14)], [(9, 0), (1, 8)], [(3, 6), (9, 14)]],
    'H': [[(0, 0), (0, 14)], [(9, 0), (9, 14)], [(0, 7), (9, 7)]],
    'W': [[(0, 0), (2.5, 14), (5.5, 5), (8.5, 14), (11, 0)]],
}
WIDTH = {'F': 8, 'L': 8, 'I': 6, 'P': 9, 'E': 8, 'R': 9, 'O': 9, 'S': 9,
         'N': 9, 'T': 9, 'D': 9, 'U': 9, 'K': 9, 'H': 9, 'W': 11}
SCALE, GAP, TEXT_Y = 0.8, 4, 9
AREA = (38, 126)                          # onde a palavra cabe (a esquerda e do desenho)


def word_width(word):
    return sum(WIDTH[ch] for ch in word) * SCALE + GAP * (len(word) - 1) + 1


def word_mask(word, x0):
    mask = np.zeros((H, W), bool)
    x = x0
    for ch in word:
        for path in GLYPHS[ch]:
            for (ax, ay), (bx, by) in zip(path, path[1:]):
                line(mask, x + ax * SCALE, TEXT_Y + ay * SCALE, x + bx * SCALE, TEXT_Y + by * SCALE, brush=2)
        x += WIDTH[ch] * SCALE + GAP
    return mask


def chrome(y):
    """O cromado: ciano em cima, branco no meio, magenta embaixo."""
    k = (y - TEXT_Y) / (14 * SCALE + 1)
    return mix(CYAN, WHITE, k * 2) if k < 0.5 else mix(WHITE, MAGENTA, (k - 0.5) * 2)


# -- O sol e os desenhos da esquerda ---------------------------------------------
SUN_C, SUN_R, HORIZON = (17, 24), 10, 30


def sun(frame):
    for y in range(H):
        for x in range(0, 36):
            d = math.hypot(x - SUN_C[0], (y - SUN_C[1]) * 1.1)
            if d <= SUN_R and y <= HORIZON:
                # As listas do sol synthwave: frestas que engrossam para baixo.
                band = y - (SUN_C[1] - 2)
                if band > 0 and band % 3 == 0:
                    continue
                k = (y - (SUN_C[1] - SUN_R)) / (2 * SUN_R)
                frame[y, x] = mix(YELLOW, MAGENTA, max(0.0, min(1.0, k * 1.4)))
    frame[HORIZON + 1, 0:36] = PURPLE


def palm(frame, t):
    """O coqueiro do logotipo padrao, balancando."""
    sway = math.sin(2 * math.pi * t / 3.0)
    base, top = (11.0, 31.0), (19.0 + 1.2 * sway, 9.0)
    trunk = np.zeros((H, W), bool)
    pts = []
    for i in range(13):                      # o tronco curvo, com aneis
        u = i / 12
        x = base[0] + (top[0] - base[0]) * u + 3.5 * math.sin(math.pi * u)
        y = base[1] + (top[1] - base[1]) * u
        pts.append((x, y))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(trunk, ax, ay, bx, by, brush=2)
    ys, xs = np.nonzero(trunk)
    for y, x in zip(ys, xs):
        frame[y, x] = (95, 45, 150) if (y // 2) % 2 else (140, 70, 200)
    cx, cy = top
    fronds = np.zeros((H, W), bool)
    for i, (ang, length) in enumerate(((-2.9, 13), (-2.3, 12), (-1.7, 9), (-1.2, 11), (-0.5, 13), (0.1, 12))):
        a = ang + 0.14 * math.sin(2 * math.pi * t / 3.0 + i * 0.7)
        prev = (cx, cy)
        for s in range(1, length + 1):
            u = s / length
            x = cx + math.cos(a) * s
            y = cy + math.sin(a) * s + 5.0 * u * u          # a folha cai na ponta
            line(fronds, prev[0], prev[1], x, y)
            if 2 <= s < length - 1 and s % 2 == 0:       # os foliolos
                line(fronds, x, y, x + 0.9 * math.cos(a + 1.9), y + 1.8)
            prev = (x, y)
    ys, xs = np.nonzero(fronds)
    for y, x in zip(ys, xs):
        frame[y, x] = MAGENTA if (x + y) % 3 else (255, 140, 220)
    for dx, dy in ((-1, 1), (1, 1), (0, 2)):                 # os cocos
        x, y = int(round(cx + dx)), int(round(cy + dy))
        if 0 <= x < W and 0 <= y < H:
            frame[y, x] = ORANGE


def joystick(frame, t):
    """Start frontend: o joystick de fliperama balancando e os botoes piscando."""
    base = np.zeros((H, W), bool)
    base[25:30, 5:31] = True
    stamp(frame, base, lambda y, x: (255, 120, 210) if y == 25 else DEEP)
    tilt = 4.0 * math.sin(2 * math.pi * t / 1.5)
    top = (13 + tilt, 11.0)
    stick = np.zeros((H, W), bool)
    line(stick, 13, 24, top[0], top[1], brush=2)
    stamp(frame, stick, (170, 190, 225))
    ball = disc(top[0] + 0.5, top[1], 4.2)
    stamp(frame, ball, lambda y, x: (255, 170, 230) if (x - top[0]) + (y - top[1]) < -2.5 else MAGENTA)
    lit = int(t / 0.25) % 2
    for n, (bx, color) in enumerate(((22, CYAN), (28, YELLOW))):
        stamp(frame, disc(bx, 22.5, 2.3), color if lit == n else mix(color, BLACK, 0.55))


def gear_mask(cx, cy, outer, inner, hole, teeth, angle):
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - cx, yy - cy)
    a = (np.arctan2(yy - cy, xx - cx) - angle) % (2 * math.pi / teeth)
    tooth = a < (2 * math.pi / teeth) * 0.5
    return ((r <= inner) | ((r <= outer) & tooth)) & (r > hole)


def gears(frame, t):
    """Setup: duas engrenagens engrenadas girando (2 dentes por volta do laco)."""
    a = 2 * (2 * math.pi / 8) * t / 3.0
    big = gear_mask(15.5, 13.5, 10.5, 7.5, 3.0, 8, a)
    stamp(frame, big, lambda y, x: (255, 150, 220) if math.hypot(x - 15.5, y - 13.5) > 8.2 else MAGENTA)
    small = gear_mask(28.0, 24.5, 6.0, 4.2, 1.6, 6, -a * 8 / 6 + 0.25)
    stamp(frame, small, lambda y, x: (150, 245, 255) if math.hypot(x - 28, y - 24.5) > 4.6 else CYAN)


def desktop(frame, t):
    """Start desktop: o monitor com duas janelas e o cursor do mouse que clica."""
    mon = np.zeros((H, W), bool)
    mon[4:23, 4:31] = True
    stamp(frame, mon, lambda y, x: CYAN if y in (4, 22) or x in (4, 30) else (22, 12, 44))
    stand = np.zeros((H, W), bool)
    stand[23:26, 15:20] = True
    stand[26:28, 11:24] = True
    stamp(frame, stand, PURPLE)
    u = (t % 3.0) / 3.0
    click = 0.42 < u < 0.52
    frame[7, 7:19] = (255, 150, 220) if click else MAGENTA         # a janela de tras
    frame[8:15, 7:19] = (70, 40, 120)
    for y in (10, 12):
        frame[y, 9:17] = (120, 90, 180)
    frame[11, 14:28] = CYAN                                           # a da frente
    frame[12:20, 14:28] = (55, 30, 100)
    for y in (14, 16, 18):
        frame[y, 16:26 - (y % 3)] = (110, 80, 170)
    # o cursor vai ao titulo da janela de tras, clica e volta
    k = math.sin(math.pi * min(1.0, u / 0.45)) if u < 0.45 else 1.0 if u < 0.55 else math.sin(math.pi * 0.5 * (1 - (u - 0.55) / 0.45))
    cx, cy = 25 - 14 * k, 19 - 11 * k
    arrow = ("W....", "WW...", "WWW..", "WWWW.", "WW...", "W....")
    cur = np.zeros((H, W), bool)
    for j, row in enumerate(arrow):
        for i, ch in enumerate(row):
            if ch == "W" and 0 <= int(cy) + j < H and 0 <= int(cx) + i < W:
                cur[int(cy) + j, int(cx) + i] = True
    stamp(frame, cur, WHITE)


TINY = {  # letras 3x5 do terminal
    '>': ("#..", ".#.", "..#", ".#.", "#.."),
    'O': ("###", "#.#", "#.#", "#.#", "###"), 'K': ("#.#", "#.#", "##.", "#.#", "#.#"),
    'M': ("#.#", "###", "#.#", "#.#", "#.#"), 'E': ("###", "#..", "##.", "#..", "###"),
    'N': ("##.", "#.#", "#.#", "#.#", "#.#"), 'U': ("#.#", "#.#", "#.#", "#.#", "###"),
}


def tiny(frame, text, x, y, color):
    for ch in text:
        if ch in TINY:
            for j, row in enumerate(TINY[ch]):
                for i, c in enumerate(row):
                    if c == "#":
                        frame[y + j, x + i] = color
        x += 4


def shell(frame, t):
    """Exit to shell: o terminal digitando, com o cursor piscando."""
    win = np.zeros((H, W), bool)
    win[6:28, 3:32] = True
    stamp(frame, win, lambda y, x: MAGENTA if y < 9 else CYAN if x in (3, 31) or y == 27 else (14, 8, 30))
    for x, color in ((5, YELLOW), (7, CYAN), (9, WHITE)):
        frame[7, x] = color
    tiny(frame, "OK", 5, 11, (90, 200, 160))
    typed = "MENU"[:min(4, int(t / 0.35))]
    tiny(frame, ">", 5, 19, YELLOW)
    tiny(frame, typed, 10, 19, WHITE)
    if int(t / 0.25) % 2 == 0:
        x = 10 + 4 * len(typed)
        frame[19:24, x:x + 3] = CYAN


def power(frame, t):
    """Shutdown / Reboot: o simbolo de energia pulsando, com ondas saindo."""
    k = 0.5 + 0.5 * math.sin(2 * math.pi * t / 1.5)
    ring_r = 9.0 + ((t / 1.5) % 1.0) * 6.5
    fade = 1.0 - ((t / 1.5) % 1.0)
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.hypot(xx - 17, yy - 15)
    ring = (np.abs(r - ring_r) < 0.55) & (xx < 36) & ((xx + yy) % 2 == 0)
    frame[ring] = mix(BLACK, MAGENTA, fade)
    sym = np.zeros((H, W), bool)
    prev = None
    for deg in range(-55, 236, 6):                           # o arco aberto em cima (-90 e para cima)
        a = math.radians(deg)
        p = (17 + 8.5 * math.cos(a), 15 + 8.5 * math.sin(a))
        if prev:
            line(sym, prev[0], prev[1], p[0], p[1], brush=2)
        prev = p
    line(sym, 16.5, 4, 16.5, 14, brush=2)                     # o traco do meio
    stamp(frame, sym, mix(CYAN, WHITE, k))


# A palavra e o desenho de cada animacao.
ANIMS = {
    "marquee-fliperos": ("FLIPEROS", palm, 40),
    "marquee-menu-frontend": ("FRONTEND", joystick, None),
    "marquee-menu-setup": ("SETUP", gears, None),
    "marquee-menu-desktop": ("DESKTOP", desktop, None),
    "marquee-menu-shell": ("SHELL", shell, None),
    "marquee-menu-power": ("POWER", power, None),
}


# -- Os glitches ---------------------------------------------------------------------
GLITCHES = [(17, 4), (43, 3), (61, 5)]    # (quadro inicial, quantos quadros)


def glitch(frame, mask, x0, i, rnd):
    on = [g for g in GLITCHES if g[0] <= i < g[0] + g[1]]
    if not on:
        return frame
    out = frame.copy()
    region = slice(x0 - 4, W)
    # separacao de cor: uma copia ciano a esquerda e uma magenta a direita
    k = rnd.choice((1, 2))
    shifted_l = np.roll(mask, -k, axis=1)
    shifted_r = np.roll(mask, k, axis=1)
    out[shifted_l & ~mask] = CYAN
    out[shifted_r & ~mask] = MAGENTA
    # fatias deslocadas (poucas e curtas: a palavra continua legivel)
    for _ in range(rnd.randint(1, 2)):
        y0 = rnd.randrange(TEXT_Y - 1, TEXT_Y + 12)
        h = rnd.randint(1, 2)
        dx = rnd.choice((-1, 1)) * rnd.randint(2, 4)
        out[y0:y0 + h, region] = np.roll(out[y0:y0 + h, region], dx, axis=1)
    # ruido: blocos e pixels soltos
    for _ in range(rnd.randint(2, 4)):
        x, y = rnd.randrange(x0 - 4, W - 3), rnd.randrange(2, H - 2)
        out[y:y + 1, x:x + rnd.randint(2, 6)] = rnd.choice((CYAN, MAGENTA, WHITE))
    return out


def frame_at(i, mask, x0, painter):
    t = i / FPS
    frame = np.zeros((H, W, 3), np.uint8)
    sun(frame)
    painter(frame, t)
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        frame[y, x] = chrome(y)
    # a linha de varredura descendo pelo texto (2 voltas no laco)
    sy = TEXT_Y - 2 + int((t * 2 / 3.0 % 1.0) * 18)
    if 0 <= sy < H:
        row = frame[sy, x0 - 2:]
        lit = row.sum(1) > 0
        row[lit] = WHITE
        row[~lit] = (40, 25, 70)
    # o horizonte neon embaixo do texto
    frame[H - 2, x0 - 2:W - 2] = PURPLE
    if (i // 3) % 2:
        frame[H - 2, x0 - 2 + (i * 3) % (W - x0)] = CYAN
    return glitch(frame, mask, x0, i, random.Random(i * 7919))


def palettize(frames):
    colors = {(0, 0, 0): 0}
    for f in frames:
        for c in np.unique(f.reshape(-1, 3), axis=0):
            colors.setdefault(tuple(int(v) for v in c), len(colors))
    if len(colors) > 256:
        raise SystemExit('%d cores: mais que um GIF comporta' % len(colors))
    pal = [0] * 768
    for c, k in colors.items():
        pal[k * 3:k * 3 + 3] = c
    table = {(c[0] << 16 | c[1] << 8 | c[2]): k for c, k in colors.items()}
    out = []
    for f in frames:
        key = f[..., 0].astype(np.uint32) << 16 | f[..., 1].astype(np.uint32) << 8 | f[..., 2]
        im = Image.fromarray(np.vectorize(table.__getitem__, otypes=[np.uint8])(key), 'P')
        im.putpalette(pal)
        out.append(im)
    return out, len(colors)


def led_sim(a, scale=6):
    img = np.kron(a, np.ones((scale, scale, 1), np.uint8)).astype(np.float32)
    yy, xx = np.mgrid[0:H * scale, 0:W * scale]
    cx, cy = (xx % scale) - (scale - 1) / 2, (yy % scale) - (scale - 1) / 2
    dot = np.clip(1.5 - np.hypot(cx, cy) / (scale * 0.42), 0, 1)
    return Image.fromarray(np.clip(img * dot[..., None], 0, 255).astype(np.uint8), 'RGB')


def render(name):
    word, painter, x0 = ANIMS[name]
    if x0 is None:                        # a palavra no meio da area dela
        x0 = int(AREA[0] + (AREA[1] - AREA[0] - word_width(word)) // 2)
    mask = word_mask(word, x0)
    return [frame_at(i, mask, x0, painter) for i in range(N)]


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'web')
    prev = os.environ.get('PREVIEW')
    sheets = []
    for name in ANIMS:
        arrays = render(name)
        frames, ncolors = palettize(arrays)
        path = os.path.join(out, name + '.gif')
        frames[0].save(path, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                       loop=0, disposal=1, optimize=False)
        print('%s: %d quadros, %d cores, %d bytes' % (path, N, ncolors, os.path.getsize(path)))
        if prev:
            sheets.append([arrays[k] for k in (0, 18, 37, 56)])
            big = [led_sim(a) for a in arrays]
            os.makedirs(prev, exist_ok=True)
            big[0].save(os.path.join(prev, name + '-led.gif'), save_all=True, append_images=big[1:],
                        duration=round(1000 / FPS), loop=0)
    if prev:
        sheet = Image.new('RGB', (W * 3 * 4, H * 3 * len(sheets)), (30, 30, 30))
        for r, row in enumerate(sheets):
            for c, a in enumerate(row):
                sheet.paste(Image.fromarray(np.kron(a, np.ones((3, 3, 1), np.uint8)), 'RGB'),
                            (c * W * 3, r * H * 3))
        sheet.save(os.path.join(prev, 'marquee-anims-sheet.png'))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
