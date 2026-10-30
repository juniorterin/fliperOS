#!/usr/bin/env python3
# Abertura do FliperOS para o ZeDMD (128x32): vetor 3D minimalista, so duas cores
# chapadas (ciano e magenta) sobre preto, linhas de 1 pixel, como os graficos de
# ciberespaco dos filmes dos anos 90. Cada pixel e um LED: nada de suavizacao.
#
#   1. A tela abre como um CRT (um ponto vira linha e a linha abre)
#   2. Tunel de arame: a camera mergulha por retangulos que correm para o ponto de fuga,
#      com cubos de arame girando ao passar; o fim do tunel estoura numa linha de luz
#   3. FliperOS: letras de traco extrudadas em 3D (frente numa cor, fundo e arestas na
#      outra, trocadas em OS); cada letra gira como uma moeda e e desenhada linha a linha
#      sobre um piso de grade
#   4. Uma varredura inverte as cores, a palavra da uma volta inteira mostrando a
#      profundidade e recua para o fundo; a tela fecha como um CRT
#
# Um rasterizador proprio de linhas (Bresenham) com projecao em perspectiva; so numpy +
# Pillow, e o GIF sai com uma paleta de 3 cores.
#
#   python3 tools/zedmd-vector-anim.py [saida.gif]      (padrao config/zedmd-fliperos.gif)
#   PREVIEW=pasta python3 tools/zedmd-vector-anim.py    tambem grava uma folha de quadros e
#                                                       uma ampliacao com pontos de LED
import math
import os
import sys

import numpy as np
from PIL import Image

W, H = 128, 32
FPS = 25
DUR = 8.2
N = int(round(DUR * FPS))
CX, CY = (W - 1) / 2, (H - 1) / 2
BLACK, CYAN, MAGENTA = (0, 0, 0), (25, 227, 255), (255, 62, 181)


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x, p=3):
    return 1 - (1 - clamp(x)) ** p


def ease_in(x, p=3):
    return clamp(x) ** p


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


# -- Linhas -------------------------------------------------------------------

class Canvas:
    def __init__(self):
        self.a = np.zeros((H, W, 3), np.uint8)

    def line(self, x0, y0, x1, y1, c, dotted=False, shift=0):
        """Linha de 1 pixel (Bresenham) cortada na tela; tracejada: um sim, um nao."""
        # corte (Liang-Barsky) para nao andar por centenas de pixels fora da tela
        dx, dy = x1 - x0, y1 - y0
        t0, t1 = 0.0, 1.0
        for p, q in ((-dx, x0 + 0.49), (dx, W - 0.51 - x0), (-dy, y0 + 0.49), (dy, H - 0.51 - y0)):
            if p == 0:
                if q < 0:
                    return
            else:
                r = q / p
                if p < 0:
                    if r > t1:
                        return
                    t0 = max(t0, r)
                else:
                    if r < t0:
                        return
                    t1 = min(t1, r)
        ax, ay = int(round(x0 + dx * t0)), int(round(y0 + dy * t0))
        bx, by = int(round(x0 + dx * t1)), int(round(y0 + dy * t1))
        ddx, ddy = abs(bx - ax), -abs(by - ay)
        sx, sy = (1 if ax < bx else -1), (1 if ay < by else -1)
        err, i = ddx + ddy, 0
        while True:
            if 0 <= ax < W and 0 <= ay < H and not (dotted and (i + shift) % 2):
                self.a[ay, ax] = c
            if ax == bx and ay == by:
                return
            e2 = 2 * err
            if e2 >= ddy:
                err += ddy
                ax += sx
            if e2 <= ddx:
                err += ddx
                ay += sy
            i += 1

    def rect(self, x0, y0, x1, y1, c, dotted=False):
        self.line(x0, y0, x1, y0, c, dotted)
        self.line(x1, y0, x1, y1, c, dotted)
        self.line(x1, y1, x0, y1, c, dotted)
        self.line(x0, y1, x0, y0, c, dotted)


# -- Tunel -----------------------------------------------------------------------

F_T = 40.0                       # distancia focal do tunel
TW, TH = 78.0, 15.0              # meia largura e meia altura do tunel
SPACING = 26.0
T_GATE = 2.35                    # a camera atravessa o portal do fim do tunel


def cam_z(t):
    return 70.0 * t + 38.0 * t * t           # acelera: de 70 a 260 unidades por segundo


Z_GATE = cam_z(T_GATE) + 16.0
CUBES = [(-40, -5, 150), (31, 6, 255), (-12, 7, 345), (47, -7, 440), (-46, 6, 520)]
RAILS = [(-1, -1, CYAN, False), (1, -1, CYAN, False), (-1, 1, CYAN, False), (1, 1, CYAN, False),
         (-0.33, -1, MAGENTA, True), (0.33, 1, MAGENTA, True), (0.33, -1, MAGENTA, True),
         (-0.33, 1, MAGENTA, True)]


def cube_edges(size, rx, ry):
    v = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], float) * size
    cy_, sy_, cx_, sx_ = math.cos(ry), math.sin(ry), math.cos(rx), math.sin(rx)
    v = np.stack([v[:, 0] * cy_ + v[:, 2] * sy_, v[:, 1], -v[:, 0] * sy_ + v[:, 2] * cy_], 1)
    v = np.stack([v[:, 0], v[:, 1] * cx_ - v[:, 2] * sx_, v[:, 1] * sx_ + v[:, 2] * cx_], 1)
    edges = [(a, b) for a in range(8) for b in range(a + 1, 8) if bin(a ^ b).count('1') == 1]
    return v, edges


def tunnel(cv, t):
    zc = cam_z(t)
    zlim = Z_GATE - zc
    for sx, sy, color, dotted in RAILS:                   # as arestas longas
        z0, z1 = 12.0, min(190.0, zlim)
        if z1 <= z0:
            continue
        cv.line(CX + sx * TW * F_T / z0, CY + sy * TH * F_T / z0,
                CX + sx * TW * F_T / z1, CY + sy * TH * F_T / z1, color, dotted)
    k = int(math.ceil((zc + 12.0) / SPACING))
    frames = []
    while True:
        z = k * SPACING - zc
        if z > min(190.0, zlim):
            break
        frames.append((z, k))
        k += 1
    for z, k in reversed(frames):                         # de longe para perto
        r = F_T / z
        hw, hh = TW * r, TH * r
        if hw >= 3:
            cv.rect(CX - hw, CY - hh, CX + hw, CY + hh, MAGENTA if k % 4 == 0 else CYAN)
    if zlim > 6.0:                                        # o portal do fim: o ultimo retangulo
        r = F_T / max(zlim, 4.0)
        cv.rect(CX - TW * r, CY - TH * r, CX + TW * r, CY + TH * r, MAGENTA)
        cv.rect(CX - TW * r * 0.8, CY - TH * r * 0.8, CX + TW * r * 0.8, CY + TH * r * 0.8, CYAN)
    for i, (x, y, zw) in enumerate(CUBES):                # cubos de arame girando
        z = zw - zc
        if not 16.0 < z < min(200.0, zlim):
            continue
        v, edges = cube_edges(7.0, t * (1.3 + 0.4 * i) + i, t * (1.9 - 0.3 * i) + 2 * i)
        r = F_T / (z + v[:, 2])
        px, py = CX + (x + v[:, 0]) * r, CY + (y + v[:, 1]) * r
        for a, b in edges:
            cv.line(px[a], py[a], px[b], py[b], MAGENTA if i % 2 else CYAN)


# -- O logo: letras de traco, extrudadas ------------------------------------------

WORD = 'FLIPEROS'
GLYPHS = {   # caixa de 14 de altura (y para baixo); a largura de cada letra em WIDTH
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
GAP = 6
DEPTH = 3.5                       # meia espessura da extrusao
CAM = 320.0
LOGO_Y = 10.5                     # linha do centro do logo; a grade fica abaixo dele
HORIZON = 22

T_LOGO = 2.55
T_SPIN = 4.55                     # a ultima letra assentou
T_SCAN = 4.7
T_ORBIT = 5.5
T_AWAY = 7.1
T_OFF = 7.72


class Word:
    def __init__(self):
        total = sum(WIDTH[c] for c in WORD) + GAP * (len(WORD) - 1)
        x = -total / 2.0
        segs = []        # p0, p1, papel (0 frente, 1 fundo, 2 aresta), s0, s1, letra
        self.length, self.cx = [], []
        for i, ch in enumerate(WORD):
            w = WIDTH[ch]
            self.cx.append(x + w / 2.0)
            off = 0.0
            for path in GLYPHS[ch]:
                pts = [(px - w / 2.0, py - 7.0) for px, py in path]
                cum = [off]
                for a, b in zip(pts, pts[1:]):
                    cum.append(cum[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
                for j in range(len(pts) - 1):
                    for role, z in ((0, DEPTH), (1, -DEPTH)):
                        segs.append(((pts[j][0], pts[j][1], z), (pts[j + 1][0], pts[j + 1][1], z), role,
                                     cum[j], cum[j + 1], i))
                for j, (px, py) in enumerate(pts):
                    if path[0] == path[-1] and j == len(pts) - 1:
                        continue
                    segs.append(((px, py, DEPTH), (px, py, -DEPTH), 2, cum[j], cum[j], i))
                off = cum[-1]
            self.length.append(off)
            x += w + GAP
        self.p0 = np.array([s[0] for s in segs], float)
        self.p1 = np.array([s[1] for s in segs], float)
        self.role = np.array([s[2] for s in segs])
        self.s0 = np.array([s[3] for s in segs])
        self.s1 = np.array([s[4] for s in segs])
        self.let = np.array([s[5] for s in segs])
        self.length = np.array(self.length)
        self.cx = np.array(self.cx)

    def draw(self, cv, t, p):
        """p: o estado da cena (giro e posicao de cada letra, da palavra e da varredura)."""
        L = self.length[self.let]
        g = p['draw'][self.let]
        gb = np.clip((g - 0.3) / 0.7, 0, 1)
        drawn = np.where(self.role == 0, g * L, gb * L)
        span = np.where(self.role == 2, 8.0, np.maximum(self.s1 - self.s0, 1e-9))
        f = np.clip((drawn - self.s0) / span, 0, 1)
        ok = f > 0
        a, b = self.p0, self.p0 + (self.p1 - self.p0) * f[:, None]
        # a letra gira como uma moeda e vai para a sua posicao
        ang = p['alpha'][self.let]
        ca, sa = np.cos(ang)[:, None], np.sin(ang)[:, None]
        out = []
        for q in (a, b):
            x, y, z = q[:, 0:1], q[:, 1:2], q[:, 2:3]
            x, z = x * ca + z * sa, -x * sa + z * ca
            x = x + self.cx[self.let][:, None]
            z = z + p['dz'][self.let][:, None]
            # a palavra toda: giro, inclinacao e escala
            ct, st = math.cos(p['theta']), math.sin(p['theta'])
            x, z = x * ct + z * st, -x * st + z * ct
            cp, sp = math.cos(p['phi']), math.sin(p['phi'])
            y, z = y * cp - z * sp, y * sp + z * cp
            x, y, z = x * p['scale'], y * p['scale'], z * p['scale']
            out.append(np.concatenate([x, y, z], 1))
        a3, b3 = out
        ok &= (CAM - a3[:, 2] > 50) & (CAM - b3[:, 2] > 50)
        ka, kb = CAM / (CAM - a3[:, 2]), CAM / (CAM - b3[:, 2])
        ax, ay = CX + a3[:, 0] * ka, LOGO_Y + a3[:, 1] * ka
        bx, by = CX + b3[:, 0] * kb, LOGO_Y + b3[:, 1] * kb
        # cores: Fliper = frente ciano e fundo magenta; OS ao contrario; a varredura troca
        swap = (self.let >= 6) ^ (np.abs((ax + bx) / 2 - p['scan']) < 8.5 if p['scan'] is not None else False)
        front = np.where(swap, 1, 0)
        color = np.where(self.role == 0, front, 1 - front)
        order = np.argsort((a3[:, 2] + b3[:, 2]) / 2)
        for i in order:
            if ok[i]:
                cv.line(ax[i], ay[i], bx[i], by[i], MAGENTA if color[i] else CYAN)


def grid(cv, t, progress):
    """O piso: linhas que vem em direcao a camera e as que saem do ponto de fuga."""
    if progress <= 0:
        return
    depth = H - 1 - HORIZON
    last = HORIZON + progress * depth
    cv.line(0, HORIZON, W - 1, HORIZON, CYAN, dotted=True)
    phase = (t * 0.6) % 1.0               # as barras descem para a camera, cada vez mais espacadas
    for j in range(7):
        y = HORIZON + depth * 0.6 ** (j - phase)
        if HORIZON + 1.4 < y <= last:
            cv.line(0, y, W - 1, y, MAGENTA)


# -- A cena, quadro a quadro ------------------------------------------------------

def scene_state(t, word):
    n = len(WORD)
    p = dict(alpha=np.zeros(n), dz=np.zeros(n), draw=np.ones(n), theta=0.0, phi=0.0, scale=1.0, scan=None)
    for i in range(n):
        t0 = T_LOGO + 0.1 + 0.11 * i
        p['draw'][i] = ease_out((t - t0) / 0.9, 2)
        p['alpha'][i] = math.radians(270) * (1 - ease_out((t - t0) / 1.1, 3))
    # a camera recua (a escala sobe) e a palavra assenta
    k = (t - T_LOGO) / 1.9
    p['scale'] = 0.55 + 0.45 * ease_out(k, 3)
    p['theta'] = math.radians(-38) * (1 - ease_out(k, 3))
    p['phi'] = math.radians(14) * (1 - ease_out(k, 2))
    if T_SPIN <= t < T_ORBIT:                             # balanca de lado a lado, mostrando a espessura
        u = (t - T_SPIN) / (T_ORBIT - T_SPIN)
        p['theta'] = math.radians(16) * math.sin(2 * math.pi * u)
        p['phi'] = math.radians(5) * math.sin(math.pi * u)
    if t >= T_ORBIT:                                      # uma volta inteira
        u = (t - T_ORBIT) / 1.6
        p['theta'] = math.radians(360) * ease_io(u)
        p['phi'] = math.radians(10) * math.sin(math.pi * clamp(u))
    if T_SCAN <= t < T_SCAN + 0.7:
        p['scan'] = -10 + 150 * (t - T_SCAN) / 0.7
    if t >= T_ORBIT + 0.55 and t < T_ORBIT + 1.15:
        p['scan'] = -10 + 150 * (t - T_ORBIT - 0.55) / 0.6
    if t >= T_AWAY:                                       # cada letra recua para o fundo
        for i in range(n):
            u = (t - T_AWAY - 0.05 * i) / 0.55
            p['dz'][i] = -520.0 * ease_in(u, 2.2)
            p['alpha'][i] = math.radians(-200) * ease_in(u, 2)
    return p


def crt(cv, t):
    """O CRT: um ponto vira linha e a linha abre (e o contrario no fim)."""
    def box(ww, hh, line):
        x0, x1 = max(0, int(round(CX - ww))), min(W - 1, int(round(CX + ww)))
        y0, y1 = max(0, int(round(CY - hh))), min(H - 1, int(round(CY + hh)))
        keep = cv.a[y0:y1 + 1, x0:x1 + 1].copy()
        cv.a[:] = 0
        cv.a[y0:y1 + 1, x0:x1 + 1] = CYAN if line else keep
    if t < 0.12:                                          # abre: o ponto vira linha
        box(1 + 62.5 * ease_out(t / 0.12, 2), 0.5, True)
    elif t < 0.36:                                        # e a linha abre a tela
        u = ease_out((t - 0.12) / 0.24, 2)
        box(W / 2, 0.5 + 15.5 * u, u < 0.18)
    elif t >= T_OFF + 0.36:
        cv.a[:] = 0
    elif t >= T_OFF + 0.24:                               # fecha: a linha encolhe ate sumir
        box(1 + 62.5 * (1 - ease_out((t - T_OFF - 0.24) / 0.12, 2)), 0.5, True)
    elif t >= T_OFF:                                      # a tela fecha numa linha
        u = ease_in((t - T_OFF) / 0.24, 2)
        box(W / 2, 0.5 + 15.5 * (1 - u), u > 0.82)


def frame(i, word):
    t = i / FPS
    cv = Canvas()
    if t < T_GATE:
        tunnel(cv, t)
    elif t < T_GATE + 0.12:                               # a linha de luz do corte
        cv.rect(0, 14, W - 1, 17, MAGENTA)
        cv.line(0, 15, W - 1, 15, CYAN)
        cv.line(0, 16, W - 1, 16, CYAN)
    else:
        grid(cv, t, ease_out((t - T_LOGO - 0.2) / 0.9, 2))
        word.draw(cv, t, scene_state(t, word))
    crt(cv, t)
    return cv.a


def palettize(frames):
    pal = [0] * 768
    pal[3:6], pal[6:9] = CYAN, MAGENTA
    lut = {BLACK: 0, CYAN: 1, MAGENTA: 2}
    out = []
    for f in frames:
        idx = np.zeros((H, W), np.uint8)
        for c, k in lut.items():
            idx[(f == np.array(c, np.uint8)).all(2)] = k
        im = Image.fromarray(idx, 'P')
        im.putpalette(pal)
        out.append(im)
    return out


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
    word = Word()
    arrays = [frame(i, word) for i in range(N)]
    frames = palettize(arrays)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                   loop=0, disposal=1, optimize=False)
    print('%s: %d quadros (%.1f s), 3 cores, %d bytes' % (out, N, DUR, os.path.getsize(out)))
    prev = os.environ.get('PREVIEW')
    if prev:
        os.makedirs(prev, exist_ok=True)
        keys = list(range(0, N, max(1, N // 36)))[:36]
        sheet = Image.new('RGB', (W * 3 * 3, H * 3 * 12), (30, 30, 30))
        for n, k in enumerate(keys):
            sheet.paste(Image.fromarray(np.kron(arrays[k], np.ones((3, 3, 1), np.uint8)), 'RGB'),
                        ((n % 3) * W * 3, (n // 3) * H * 3))
        sheet.save(os.path.join(prev, 'vector-sheet.png'))
        big = [led_sim(a) for a in arrays]
        big[0].save(os.path.join(prev, 'vector-led.gif'), save_all=True, append_images=big[1:],
                    duration=round(1000 / FPS), loop=0)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
