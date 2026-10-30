#!/usr/bin/env python3
# Abertura do FliperOS para o ZeDMD (128x32), feita pixel a pixel como uma animacao de
# DMD de pinball: sem suavizacao, poucas cores chapadas, sprites desenhados a mao.
#
#   1. Plunger: a mola solta, a bola sobe pela rampa da direita e faz a curva do topo
#   2. Pop bumpers: a bola ricocheteia (cada batida acende o bumper e solta a pontuacao)
#   3. Flipper: a bola pousa, os dois flippers batem e ela some pelo topo
#   4. Jackpot: flash, o logo estoura em zoom com tremida, raios girando, onda de saltos,
#      reflexo de luz e faiscas, com as luzes da moldura correndo
#   5. Saida: as letras caem como alvos que abaixam; o ciclo recomeca
#
# A bola quica de bumper em bumper em arcos de gravidade, sempre pelo topo dos bumpers: e o
# que cabe em 32 linhas e se le de longe. So numpy + Pillow; o resultado e um GIF com
# paleta exata (sao poucas cores chapadas, nada de suavizacao: cada pixel e um LED).
#
#   python3 tools/zedmd-pinball-anim.py [saida.gif]      (padrao config/zedmd-fliperos.gif)
#   PREVIEW=pasta python3 tools/zedmd-pinball-anim.py    tambem grava uma folha de quadros e
#                                                        uma ampliacao com pontos de LED
import math
import os
import random
import sys

import numpy as np
from PIL import Image

W, H = 128, 32
FPS = 25


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


BLACK, WHITE = (0, 0, 0), (255, 255, 255)
PURPLE, PINK, CYAN = rgb('#bd93f9'), rgb('#ff79c6'), rgb('#8be9fd')
YELLOW, ORANGE, RED = rgb('#f1fa8c'), rgb('#ffb86c'), rgb('#ff5555')


def mix(a, b, k):
    return tuple(int(round(a[i] + (b[i] - a[i]) * k)) for i in range(3))


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


# -- Desenho -------------------------------------------------------------

class Canvas:
    def __init__(self):
        self.a = np.zeros((H, W, 3), np.uint8)

    def px(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < W and 0 <= y < H:
            self.a[y, x] = c

    def rect(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W - 1, x1), min(H - 1, y1)
        if x0 <= x1 and y0 <= y1:
            self.a[y0:y1 + 1, x0:x1 + 1] = c

    def line(self, x0, y0, x1, y1, c):
        x0, y0, x1, y1 = (int(round(v)) for v in (x0, y0, x1, y1))
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        while True:
            self.px(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x0 += sx
            if e2 <= dx:
                err += dx
                y0 += sy

    def sprite(self, rows, pal, x, y):
        for j, row in enumerate(rows):
            for i, ch in enumerate(row):
                if ch in pal:
                    self.px(x + i, y + j, pal[ch])

    def text(self, s, x, y, c):
        for ch in s:
            for j, row in enumerate(DIGITS[ch]):
                for i, v in enumerate(row):
                    if v == '1':
                        self.px(x + i, y + j, c)
            x += 4


DIGITS = {
    '0': ('111', '101', '101', '101', '111'), '1': ('010', '110', '010', '010', '111'),
    '2': ('111', '001', '111', '100', '111'), '3': ('111', '001', '111', '001', '111'),
    '4': ('101', '101', '111', '001', '001'), '5': ('111', '100', '111', '001', '111'),
    '6': ('111', '100', '111', '101', '111'), '7': ('111', '001', '001', '001', '001'),
    '8': ('111', '101', '111', '101', '111'), '9': ('111', '101', '111', '001', '111'),
}

BALL = ('.wll.',
        'wwlmm',
        'llmmd',
        'lmmdd',
        '.mdd.')
BALL_PAL = {'w': WHITE, 'l': (214, 218, 238), 'm': (150, 156, 188), 'd': (84, 90, 126)}
TRAIL = [(255, 250, 200), (255, 214, 120), (255, 150, 90), (190, 70, 120), (100, 40, 90)]


# -- O logo, letra por letra (12x17, barras de 4) ---------------------------

GLYPHS = {
    'F': ('###########.', '############', '############', '############',
          '####........', '####........', '####........',
          '##########..', '##########..', '##########..',
          '####........', '####........', '####........', '####........',
          '####........', '####........', '####........'),
    'L': ('####........', '####........', '####........', '####........', '####........',
          '####........', '####........', '####........', '####........', '####........',
          '####........', '####........', '####........',
          '############', '############', '############', '###########.'),
    'I': ('##########', '##########', '##########', '##########',
          '...####...', '...####...', '...####...', '...####...', '...####...', '...####...',
          '...####...', '...####...', '...####...',
          '##########', '##########', '##########', '##########'),
    'P': ('###########.', '############', '############', '############',
          '####....####', '####....####', '####....####',
          '############', '############', '############', '#########...',
          '####........', '####........', '####........', '####........',
          '####........', '####........'),
    'E': ('############', '############', '############', '############',
          '####........', '####........', '####........',
          '##########..', '##########..', '##########..',
          '####........', '####........', '####........',
          '############', '############', '############', '############'),
    'R': ('###########.', '############', '############', '############',
          '####....####', '####....####', '####....####',
          '############', '############', '############', '#########...',
          '####.####...', '####..####..', '####...####.', '####....####',
          '####....####', '####....####'),
    'O': ('..########..', '.##########.', '############', '############',
          '#####..#####', '####....####', '####....####', '####....####', '####....####',
          '####....####', '####....####', '####....####', '#####..#####',
          '############', '############', '.##########.', '..########..'),
    'S': ('.##########.', '############', '############', '############',
          '####........', '####........', '####........',
          '############', '############', '############',
          '........####', '........####', '........####',
          '############', '############', '############', '.##########.'),
}
COLORS = {  # realce, corpo, sombra: Fliper roxo, OS rosa (as cores do logo)
    'purple': ((236, 220, 255), PURPLE, (112, 80, 190)),
    'pink': ((255, 205, 232), PINK, (186, 58, 138)),
}
GAP = 3
GH = 17


def letter_sprite(ch, tone):
    bits = np.array([[c == '#' for c in row] for row in GLYPHS[ch]])
    assert bits.shape[0] == GH and len({len(r) for r in GLYPHS[ch]}) == 1, ch
    h, w = bits.shape
    pad = np.pad(bits, 1)
    hl, body, sh = COLORS[tone]
    out = np.zeros((h + 2, w + 2, 3), np.uint8)
    alpha = np.zeros((h + 2, w + 2), bool)
    fill = np.zeros((h + 2, w + 2), bool)
    for y in range(1, h + 1):
        for x in range(1, w + 1):
            if pad[y, x]:
                if not pad[y - 1, x] or not pad[y, x - 1]:
                    c = hl
                elif not pad[y + 1, x] or not pad[y, x + 1]:
                    c = sh
                else:
                    c = body
                out[y, x], alpha[y, x], fill[y, x] = c, True, True
    for y in range(h + 2):
        for x in range(w + 2):
            if not pad[y, x] and pad[max(0, y - 1):y + 2, max(0, x - 1):x + 2].any():
                alpha[y, x] = True       # contorno preto de 1 pixel (preto = zeros)
    return out, alpha, fill, w


class Logo:
    def __init__(self):
        self.letters, x = [], 0
        for i, ch in enumerate('FLIPEROS'):
            spr = letter_sprite(ch, 'pink' if ch in 'OS' else 'purple')
            self.letters.append((spr, x))
            x += spr[3] + GAP
        self.total = x - GAP
        self.x0, self.y0 = (W - self.total) // 2, (H - GH) // 2

    def layer(self, dy=None, tint=0.0, shine=None):
        """O logo (com os saltos/quedas de cada letra) em camadas: cor, opaco e miolo."""
        img = np.zeros((H, W, 3), np.uint8)
        alpha = np.zeros((H, W), bool)
        fill = np.zeros((H, W), bool)
        for i, ((spr, a, f, w), x) in enumerate(self.letters):
            ox, oy = self.x0 + x - 1, self.y0 - 1 + (dy[i] if dy else 0)
            h = spr.shape[0]
            sx0, sy0 = max(0, -ox), max(0, -oy)
            ex, ey = min(w + 2, W - ox), min(h, H - oy)
            if ex <= sx0 or ey <= sy0:
                continue
            ys, xs = slice(oy + sy0, oy + ey), slice(ox + sx0, ox + ex)
            sa = a[sy0:ey, sx0:ex]
            img[ys, xs][sa] = spr[sy0:ey, sx0:ex][sa]
            alpha[ys, xs] |= sa
            fill[ys, xs] = np.where(sa, f[sy0:ey, sx0:ex], fill[ys, xs])
        yy, xx = np.mgrid[0:H, 0:W]
        def toward_white(m, k):
            if m.any():
                img[m] = np.round(img[m] + (255 - img[m].astype(np.float32)) * k).astype(np.uint8)
        if tint:
            toward_white(fill, tint)
        if shine is not None:                # faixa diagonal de luz, em dois degraus
            d = np.abs(xx + yy * 0.5 - shine)
            for width, k in ((4.5, 0.3), (2.0, 0.65)):
                toward_white(fill & (d <= width), k)
        return img, alpha, fill

    @staticmethod
    def zoom(img, alpha, s, shake=(0, 0)):
        ys, xs = np.mgrid[0:H, 0:W]
        sx = np.floor((xs + 0.5 - W / 2) / s + W / 2).astype(int)
        sy = np.floor((ys + 0.5 - H / 2) / s + H / 2).astype(int)
        ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
        sx, sy = np.clip(sx, 0, W - 1), np.clip(sy, 0, H - 1)
        out, oa = img[sy, sx], alpha[sy, sx] & ok
        out = np.where(oa[..., None], out, 0).astype(np.uint8)
        dx, dy = shake
        out, oa = np.roll(out, (dy, dx), (0, 1)), np.roll(oa, (dy, dx), (0, 1))
        return out, oa


# -- Mesa: rampa, bumpers, flippers --------------------------------------------

LANE_X = 122
ARC_C, ARC_R = (110, 14), 12
BALL_R = 2.5
BUMP_R = 5
SPEED = 118.0                       # px/s da bola solta na mesa
FL_REST, FL_UP = math.radians(28), math.radians(-26)
FLIPPERS = (((30, 22), 1), ((97, 22), -1))      # pivo e sentido (1: para a direita)
FL_LEN = 20


def flipper_geometry(pivot, side, ang):
    tip = (pivot[0] + side * FL_LEN * math.cos(ang), pivot[1] + FL_LEN * math.sin(ang))
    return tip


def flipper_radius(t):
    return lerp(3.1, 1.6, t)


def flipper_point(pivot, side, ang, d):
    """O ponto da bola pousada sobre o flipper, a d pixels do pivo."""
    px, py = pivot
    fx, fy = px + side * d * math.cos(ang), py + d * math.sin(ang)
    n = (side * math.sin(ang), -math.cos(ang))
    r = flipper_radius(d / FL_LEN) + BALL_R
    return fx + n[0] * r, fy + n[1] * r


Q0 = (110, 2)
# Quatro pop bumpers em fila; a bola cai no primeiro e quica de bumper em bumper, em
# arcos de gravidade (cada batida a joga para cima), ate pousar no flipper esquerdo.
BUMPERS = [(92, 18), (66, 17), (40, 18), (15, 17)]
LEAN = [-2.0, 2.0, -2.0, 2.0]           # em que ponto da curva a bola encosta (pixels de lado)
HITS = [(cx + lean, cy - math.sqrt((BUMP_R + BALL_R) ** 2 - lean ** 2))
        for (cx, cy), lean in zip(BUMPERS, LEAN)]
LAND = flipper_point(FLIPPERS[0][0], 1, FL_REST, 13)
PATH = [Q0] + HITS + [LAND]
ARC_H = [0, 7, 7, 7, 6]                 # altura do arco de cada trecho (0: queda vinda da rampa)
SCORES = ['100', '250', '500', '1000']

# Tempos: a rampa, o rally (a velocidade horizontal fixa), a batida do flipper e a saida.
T_RELEASE, T_LANE_END, T_ARC_END = 0.50, 0.66, 0.90
T_ARRIVE = [T_ARC_END]
for a, b in zip(PATH, PATH[1:]):
    T_ARRIVE.append(T_ARRIVE[-1] + max(0.18, abs(b[0] - a[0]) / SPEED))
T_HIT = T_ARRIVE[1:5]                   # as 4 batidas nos bumpers
T_CLEAR = T_HIT[3] + 0.12               # os bumpers somem e os flippers entram
T_LAND = T_ARRIVE[5]
T_FLIP = T_LAND + 0.10                  # os flippers comecam a subir
EXIT = (LAND[0] + 12, -5)
T_LAUNCH = T_FLIP + 0.04
T_EXIT = T_LAUNCH + math.hypot(EXIT[0] - LAND[0], EXIT[1] - LAND[1]) / 190.0
T_FLASH = round(T_EXIT * FPS) / FPS     # o primeiro quadro branco do jackpot
T_OUT = T_FLASH + 3.7                   # as letras comecam a cair
N = int(math.ceil((T_OUT + 1.0) * FPS / 8)) * 8     # multiplo de 8: a moldura emenda na cor e no passo
DUR = N / FPS


def ball_at(t):
    """Centro da bola em t (None: fora da mesa)."""
    t = max(t, 0.0)
    if t < T_RELEASE:
        u = t / T_RELEASE
        return (LANE_X, 23.5 + 3.0 * (u * u * (3 - 2 * u)))
    if t < T_LANE_END:
        u = (t - T_RELEASE) / (T_LANE_END - T_RELEASE)
        return (LANE_X, lerp(26.5, ARC_C[1], u ** 1.4))
    if t < T_ARC_END:
        u = (t - T_LANE_END) / (T_ARC_END - T_LANE_END)
        ang = -u * math.pi / 2
        return (ARC_C[0] + ARC_R * math.cos(ang), ARC_C[1] + ARC_R * math.sin(ang))
    for i in range(5):
        if t < T_ARRIVE[i + 1]:
            u = (t - T_ARRIVE[i]) / (T_ARRIVE[i + 1] - T_ARRIVE[i])
            a, b = PATH[i], PATH[i + 1]
            if i == 0:                  # sai horizontal da rampa e cai
                return (lerp(a[0], b[0], u), lerp(a[1], b[1], u * u))
            return (lerp(a[0], b[0], u), lerp(a[1], b[1], u) - ARC_H[i] * 4 * u * (1 - u))
    if t < T_LAUNCH:
        return LAND
    if t < T_EXIT:
        u = (t - T_LAUNCH) / (T_EXIT - T_LAUNCH)
        return (lerp(LAND[0], EXIT[0], u), lerp(LAND[1], EXIT[1], u))
    return None


def flipper_angle(t):
    if t < T_FLIP:
        return FL_REST
    u = (t - T_FLIP) / 0.10
    if u < 1:
        return lerp(FL_REST, FL_UP, u)
    if t < T_FLIP + 0.10 + 0.20:
        return FL_UP
    u = (t - T_FLIP - 0.30) / 0.10
    return lerp(FL_UP, FL_REST, clamp(u))


def draw_flipper(cv, pivot, side, ang, lit):
    tip = flipper_geometry(pivot, side, ang)
    ax, ay = pivot
    vx, vy = tip[0] - ax, tip[1] - ay
    ll = vx * vx + vy * vy
    mask = np.zeros((H, W), bool)
    for y in range(max(0, int(min(ay, tip[1])) - 4), min(H, int(max(ay, tip[1])) + 5)):
        for x in range(max(0, int(min(ax, tip[0])) - 4), min(W, int(max(ax, tip[0])) + 5)):
            t = clamp(((x - ax) * vx + (y - ay) * vy) / ll)
            if math.hypot(x - (ax + vx * t), y - (ay + vy * t)) <= flipper_radius(t):
                mask[y, x] = True
    body = (255, 110, 110) if lit else RED
    for y, x in zip(*np.nonzero(mask)):
        edge = y == 0 or not mask[y - 1, x]
        cv.px(x, y, (255, 190, 190) if edge else (body if y == 0 or mask[y - 1, x] and (y + 1 >= H or mask[y + 1, x]) else (190, 50, 70)))
    cv.rect(int(ax) - 1, int(ay) - 1, int(ax), int(ay), YELLOW)


def draw_bumper(cv, cx, cy, hit):
    """hit: 0 normal, 1 branco com anel (quadros logo apos a batida), 2 anel claro."""
    for y in range(int(cy) - 7, int(cy) + 8):
        for x in range(int(cx) - 7, int(cx) + 8):
            d = math.hypot(x - cx, y - cy)
            if d <= BUMP_R + 0.4:
                if hit == 1:
                    c = (255, 232, 246) if d > 1.9 else YELLOW
                elif d > BUMP_R - 1.6:
                    c = PINK if hit == 0 else (255, 190, 225)
                elif d > 1.9:
                    c = PURPLE if hit == 0 else (225, 205, 255)
                else:
                    c = YELLOW
                cv.px(x, y, c)
            elif hit and BUMP_R + 0.4 < d <= BUMP_R + 1.7:
                cv.px(x, y, CYAN if hit == 1 else (60, 110, 125))


def draw_rails(cv):
    dim = (44, 76, 88)
    for y in range(15, 31):
        cv.px(LANE_X - 4, y, dim)
        cv.px(LANE_X + 4, y, dim)
    for r, edge in ((ARC_R - 4, 0), (ARC_R + 4, 1)):
        for k in range(0, 91, 3 if r < 10 else 2):
            a = -math.radians(k)
            cv.px(ARC_C[0] + r * math.cos(a), ARC_C[1] + r * math.sin(a), dim)


def draw_plunger(cv, t):
    if t < T_RELEASE:
        u = t / T_RELEASE
        top = 26 + round(3 * (u * u * (3 - 2 * u)))
    else:
        u = (t - T_RELEASE) * FPS
        top = 26 + (1 if u < 1 else 0)
    cv.rect(LANE_X - 2, top, LANE_X + 2, top + 1, (176, 180, 196))
    for y in range(top + 2, 32):
        cv.px(LANE_X + (-1 if (y + top) % 2 else 1), y, (118, 122, 140))
    cv.px(LANE_X, top + 2, (118, 122, 140))


def border(cv, i, bright=1.0):
    """Moldura de lampadas: a cada 4 pixels uma acesa, correndo 1 pixel por quadro."""
    ring = [(x, 0) for x in range(W)] + [(W - 1, y) for y in range(1, H)] + \
        [(x, H - 1) for x in range(W - 2, -1, -1)] + [(0, y) for y in range(H - 2, 0, -1)]
    for k, (x, y) in enumerate(ring):
        slot = (k - i) % 4
        if slot == 0:
            cv.px(x, y, mix(BLACK, YELLOW if ((k - i) // 4) % 2 else PINK, bright))
        elif slot == 2:
            cv.px(x, y, mix(BLACK, (92, 56, 132), bright))


def rays(cv, t, k):
    if k <= 0:
        return
    ys, xs = np.mgrid[0:H, 0:W]
    ang = np.arctan2(ys - (H - 1) / 2, xs - (W - 1) / 2) / (2 * math.pi) * 16 + t * 1.1
    odd = np.floor(ang).astype(int) % 2
    a, b = [tuple(int(v * k) for v in c) for c in ((88, 34, 128), (30, 12, 54))]
    cv.a[:] = np.where(odd[..., None] == 1, a, b)


def star(cv, x, y, stage):
    """Faisca de LED: ponto, cruz pequena, cruz grande."""
    cv.px(x, y, WHITE)
    if stage >= 1:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.px(x + dx, y + dy, mix(CYAN, WHITE, 0.6))
    if stage >= 2:
        for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
            cv.px(x + dx, y + dy, CYAN)
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            cv.px(x + dx, y + dy, (120, 190, 235))


# -- A cena, quadro a quadro ---------------------------------------------------

class Scene:
    def __init__(self):
        self.logo = Logo()
        rnd = random.Random(11)
        self.sparkles = []
        for k in range(18):
            i = rnd.randrange(len(self.logo.letters))
            (spr, a, f, w), x = self.logo.letters[i]
            sx = self.logo.x0 + x + rnd.randrange(0, w)
            sy = self.logo.y0 + rnd.choice((-2, -1, GH, GH + 1))
            self.sparkles.append((T_FLASH + 0.9 + k * 0.15 + rnd.uniform(0, 0.1), sx, sy))

    # Antes do jackpot: a mesa.
    def table(self, cv, t, i):
        draw_rails(cv)
        draw_plunger(cv, t)
        # os bumpers surgem logo depois da rampa, acendem na batida e somem na hora dos flippers
        for k, (cx, cy) in enumerate(BUMPERS):
            born = 0.45 + 0.07 * k
            if t < born:
                continue
            since = t - T_HIT[k]
            hit = 1 if 0 <= since < 0.08 else 2 if 0.08 <= since < 0.16 else 0
            if t < born + 0.04:
                hit = 1
            if t >= T_CLEAR:
                if t >= T_CLEAR + 0.08:
                    continue
                hit = 1
            draw_bumper(cv, cx, cy, hit)
        if t >= T_CLEAR + 0.04:
            ang = flipper_angle(t)
            lit = t < T_CLEAR + 0.12 or T_FLIP <= t < T_FLIP + 0.3
            for pivot, side in FLIPPERS:
                draw_flipper(cv, pivot, side, ang, lit)
        for k, (cx, cy) in enumerate(BUMPERS):
            since = t - T_HIT[k]
            if 0 <= since < 0.5 and t < T_CLEAR:        # a pontuacao, embaixo do bumper
                s = SCORES[k]
                wd = 4 * len(s) - 1
                cv.text(s, int(clamp(round(cx - wd / 2), 2, W - wd - 2)), cy + BUMP_R + 3,
                        YELLOW if since < 0.3 else ORANGE)
            if 0 <= since < 0.14:                       # centelhas da batida
                px, py = HITS[k]
                r = 2 + int(since * FPS) * 2
                for dx, dy in ((1, -1), (-1, -1), (2, 0), (-2, 0)):
                    cv.px(px + dx * r * 0.7, py + dy * r * 0.7, WHITE if since < 0.08 else YELLOW)
        # rastro e bola
        pos = ball_at(t)
        if pos is not None:
            prev = pos
            for k, col in enumerate(TRAIL, 1):
                p = ball_at(t - k / FPS) or prev
                if p is prev:
                    break
                cv.line(prev[0], prev[1], p[0], p[1], col)
                if k <= 2:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        cv.line(prev[0] + dx, prev[1] + dy, p[0] + dx, p[1] + dy, col)
                prev = p
            cv.sprite(BALL, BALL_PAL, int(round(pos[0])) - 2, int(round(pos[1])) - 2)

    # Depois: o jackpot do logo.
    ZOOM = [4.4, 3.4, 2.7, 2.1, 1.7, 1.4, 1.2, 1.05, 0.94, 1.0]
    TINT = [1.0, 0.65, 0.35, 0.2, 0, 0, 0, 0, 0, 0]
    SHAKE = [(3, -2), (-3, 2), (3, 1), (-2, -1), (2, 1), (-1, 0), (1, 0), (-1, 0), (0, 0), (0, 0)]
    HOP = [-2, -4, -5, -4, -2, 0]

    def jackpot(self, cv, t, i):
        f = int(round((t - T_FLASH) * FPS))
        if f == 0:
            cv.a[:] = WHITE
            return
        since = t - T_FLASH
        falling = t >= T_OUT
        rays(cv, t, (1.7 if f <= 2 else lerp(1.7, 1.0, clamp((f - 2) / 8))) * (1 - clamp((t - T_OUT) / 0.6)))
        dy = [0] * 8
        # onda de saltos, depois a queda dos alvos
        for k in range(8):
            u = int(round((since - 0.55 - 0.05 * k) * FPS))
            if 0 <= u < len(self.HOP):
                dy[k] = self.HOP[u]
            if falling:
                s = t - T_OUT - 0.06 * k
                if s > 0:
                    dy[k] = int(round(0.5 * 520 * s * s))
        shine = None
        for a, b in ((1.3, 1.95), (2.55, 3.2)):
            if a <= since < b:
                shine = lerp(-10, 140, (since - a) / (b - a))
        k = f - 1
        if k < len(self.ZOOM):
            img, alpha, fill = self.logo.layer(dy, self.TINT[k])
            img, alpha = self.logo.zoom(img, alpha, self.ZOOM[k], self.SHAKE[k])
        else:
            img, alpha, fill = self.logo.layer(dy, 0.0, shine)
        cv.a[alpha] = img[alpha]
        if not falling:
            for t0, x, y in self.sparkles:
                s = int(round((t - t0) * FPS / 2))
                if 0 <= s < 5:
                    star(cv, x, y, (0, 1, 2, 1, 0)[s])

    def frame(self, i):
        t = i / FPS
        cv = Canvas()
        if t < T_FLASH:
            self.table(cv, t, i)
        else:
            self.jackpot(cv, t, i)
        if not (t >= T_FLASH and int(round((t - T_FLASH) * FPS)) == 0):
            border(cv, i)
        return cv.a


def palettize(frames):
    """Paleta exata (sao poucas cores chapadas); indice 0 = preto."""
    colors = {(0, 0, 0): 0}
    for f in frames:
        for c in np.unique(f.reshape(-1, 3), axis=0):
            colors.setdefault(tuple(int(v) for v in c), len(colors))
    if len(colors) > 256:
        raise SystemExit('%d cores: mais que um GIF comporta' % len(colors))
    lut = {c: k for c, k in colors.items()}
    pal = [0] * 768
    for c, k in lut.items():
        pal[k * 3:k * 3 + 3] = c
    out = []
    for f in frames:
        key = f[..., 0].astype(np.uint32) << 16 | f[..., 1].astype(np.uint32) << 8 | f[..., 2]
        table = {(c[0] << 16 | c[1] << 8 | c[2]): k for c, k in lut.items()}
        idx = np.vectorize(table.__getitem__, otypes=[np.uint8])(key)
        im = Image.fromarray(idx, 'P')
        im.putpalette(pal)
        out.append(im)
    return out, len(colors)


def led_sim(a, scale=6):
    """Os pontos de um painel de LED (so para olhar)."""
    img = np.kron(a, np.ones((scale, scale, 1), np.uint8)).astype(np.float32)
    yy, xx = np.mgrid[0:H * scale, 0:W * scale]
    cx, cy = (xx % scale) - (scale - 1) / 2, (yy % scale) - (scale - 1) / 2
    dot = np.clip(1.5 - np.hypot(cx, cy) / (scale * 0.42), 0, 1)
    return Image.fromarray(np.clip(img * dot[..., None], 0, 255).astype(np.uint8), 'RGB')


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      '..', 'config', 'zedmd-fliperos.gif')
    scene = Scene()
    arrays = [scene.frame(i) for i in range(N)]
    frames, ncolors = palettize(arrays)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                   loop=0, disposal=1, optimize=False)
    print('%s: %d quadros (%.1f s), %d cores, %d bytes' % (out, N, DUR, ncolors, os.path.getsize(out)))
    prev = os.environ.get('PREVIEW')
    if prev:
        os.makedirs(prev, exist_ok=True)
        step = max(1, N // 36)
        keys = list(range(0, N, step))[:36]
        sheet = Image.new('RGB', (W * 3 * 3, H * 3 * 12))
        for n, k in enumerate(keys):
            sheet.paste(Image.fromarray(np.kron(arrays[k], np.ones((3, 3, 1), np.uint8)), 'RGB'),
                        ((n % 3) * W * 3, (n // 3) * H * 3))
        sheet.save(os.path.join(prev, 'pinball-sheet.png'))
        print('hits', [round(x, 2) for x in T_HIT], 'land', round(T_LAND, 2), 'flash', round(T_FLASH, 2),
              'out', round(T_OUT, 2), 'bumpers', [(round(b[0]), round(b[1])) for b in BUMPERS])
        big = [led_sim(a) for a in arrays]
        big[0].save(os.path.join(prev, 'pinball-led.gif'), save_all=True, append_images=big[1:],
                    duration=round(1000 / FPS), loop=0)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
