#!/usr/bin/env python3
# O logotipo padrao do marquee (128x32): o que a previa do painel web mostra
# quando nao ha jogo, sistema nem animacao para desenhar (antes era o nome
# "FliperOS" em texto). Um coqueiro balancando a esquerda, na frente de um sol
# synthwave listrado, e a palavra FliperOS em traco futurista com cromado neon
# (ciano, branco, magenta), com glitches de tempos em tempos (fatias deslocadas,
# separacao de cor, ruido) e uma linha de varredura. 3 s em laco, sem emenda.
# Pixel a pixel, sem suavizacao: cada pixel e um LED. So numpy + Pillow.
#
#   python3 tools/marquee-logo-anim.py [saida.gif]     (padrao config/web/marquee-fliperos.gif)
#   PREVIEW=pasta python3 tools/marquee-logo-anim.py   tambem grava uma folha de quadros e
#                                                      uma ampliacao com pontos de LED
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
}
WIDTH = {'F': 8, 'L': 8, 'I': 6, 'P': 9, 'E': 8, 'R': 9, 'O': 9, 'S': 9}
SCALE, GAP, TEXT_X, TEXT_Y = 0.8, 4, 40, 9


def word_mask():
    mask = np.zeros((H, W), bool)
    x = TEXT_X
    for ch in 'FLIPEROS':
        for path in GLYPHS[ch]:
            for (ax, ay), (bx, by) in zip(path, path[1:]):
                line(mask, x + ax * SCALE, TEXT_Y + ay * SCALE, x + bx * SCALE, TEXT_Y + by * SCALE, brush=2)
        x += WIDTH[ch] * SCALE + GAP
    return mask


def chrome(y):
    """O cromado: ciano em cima, branco no meio, magenta embaixo."""
    k = (y - TEXT_Y) / (14 * SCALE + 1)
    return mix(CYAN, WHITE, k * 2) if k < 0.5 else mix(WHITE, MAGENTA, (k - 0.5) * 2)


# -- O coqueiro e o sol ------------------------------------------------------------
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


# -- Os glitches ---------------------------------------------------------------------
GLITCHES = [(17, 4), (43, 3), (61, 5)]    # (quadro inicial, quantos quadros)


def glitch(frame, mask, i, rnd):
    on = [g for g in GLITCHES if g[0] <= i < g[0] + g[1]]
    if not on:
        return frame
    out = frame.copy()
    region = slice(TEXT_X - 4, W)
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
        x, y = rnd.randrange(TEXT_X - 4, W - 3), rnd.randrange(2, H - 2)
        out[y:y + 1, x:x + rnd.randint(2, 6)] = rnd.choice((CYAN, MAGENTA, WHITE))
    return out


def frame_at(i, mask):
    t = i / FPS
    frame = np.zeros((H, W, 3), np.uint8)
    sun(frame)
    palm(frame, t)
    ys, xs = np.nonzero(mask)
    for y, x in zip(ys, xs):
        frame[y, x] = chrome(y)
    # a linha de varredura descendo pelo texto (2 voltas no laco)
    sy = TEXT_Y - 2 + int((t * 2 / 3.0 % 1.0) * 18)
    if 0 <= sy < H:
        row = frame[sy, TEXT_X - 2:]
        lit = row.sum(1) > 0
        row[lit] = WHITE
        row[~lit] = (40, 25, 70)
    # o horizonte neon embaixo do texto
    frame[H - 2, TEXT_X - 2:W - 2] = PURPLE
    if (i // 3) % 2:
        frame[H - 2, TEXT_X - 2 + (i * 3) % 84] = CYAN
    return glitch(frame, mask, i, random.Random(i * 7919))


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


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      '..', 'config', 'web', 'marquee-fliperos.gif')
    mask = word_mask()
    arrays = [frame_at(i, mask) for i in range(N)]
    frames, ncolors = palettize(arrays)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                   loop=0, disposal=1, optimize=False)
    print('%s: %d quadros, %d cores, %d bytes' % (out, N, ncolors, os.path.getsize(out)))
    prev = os.environ.get('PREVIEW')
    if prev:
        os.makedirs(prev, exist_ok=True)
        keys = [0, 10, 17, 18, 19, 30, 43, 44, 61, 62, 63, 70]
        sheet = Image.new('RGB', (W * 4 * 2, H * 4 * 6), (30, 30, 30))
        for n, k in enumerate(keys):
            sheet.paste(Image.fromarray(np.kron(arrays[k], np.ones((4, 4, 1), np.uint8)), 'RGB'),
                        ((n % 2) * W * 4, (n // 2) * H * 4))
        sheet.save(os.path.join(prev, 'marquee-logo-sheet.png'))
        big = [led_sim(a) for a in arrays]
        big[0].save(os.path.join(prev, 'marquee-logo-led.gif'), save_all=True, append_images=big[1:],
                    duration=round(1000 / FPS), loop=0)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
