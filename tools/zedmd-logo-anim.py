#!/usr/bin/env python3
# Abertura do FliperOS para o ZeDMD (128x32): o nome em letras 3D extrudadas,
# nas cores do logo (Fliper roxo, OS rosa), com estrias de warp, giro, onda de
# flips (uma letra de cada vez, como um flipper), orbita, reflexos e faiscas.
# Um renderizador proprio (nuvem de pontos com z-buffer, 4x de supersampling e
# media em luz linear), so Pillow + numpy; o resultado e um GIF que o
# fliperos-dmd (startup) repete ate o proximo evento. O ciclo fecha sem emenda:
# o flash do fim e o flash do comeco sao o mesmo.
#
#   python3 tools/zedmd-logo-anim.py [saida.gif]      (padrao config/zedmd-fliperos.gif)
#   PREVIEW=pasta python3 tools/zedmd-logo-anim.py    tambem grava quadros-chave e uma
#                                                     simulacao dos LEDs, para olhar
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 128, 32
SS = 4                      # supersampling
CW, CH = W * SS, H * SS
FPS = 25
DUR = 8.4
N = round(FPS * DUR)
FONT = os.environ.get('DMD_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf')
WORD = 'FliperOS'
EM = 20.5 * SS              # tamanho da fonte
DEPTH = 4 * SS              # espessura das letras
CAM = 700.0                 # distancia da camera (pixels do supersampling)
PURPLE = np.array([189, 147, 249], np.float32) / 255
PINK = np.array([255, 121, 198], np.float32) / 255
CYAN = np.array([139, 233, 253], np.float32) / 255
WHITE = np.array([1, 1, 1], np.float32)
T_LAND = 1.9                # a palavra pousa de frente
T_FLIP = 3.55               # comeca a onda de flips
T_ORBIT = 5.2               # volta completa
T_END = 7.9                 # sai para o flash


def clamp(x, a=0.0, b=1.0):
    return np.clip(x, a, b)


def smooth(a, b, x):
    x = clamp((x - a) / (b - a))
    return x * x * (3 - 2 * x)


def ease_out(x, p=3):
    return 1 - (1 - clamp(x)) ** p


def ease_in(x, p=3):
    return clamp(x) ** p


def ease_io(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def bump(x):
    return math.exp(-x * x)


# -- A palavra em 3D ----------------------------------------------------

def blur(a, sigma):
    r = int(math.ceil(sigma * 3))
    k = np.exp(-0.5 * (np.arange(-r, r + 1) / sigma) ** 2)
    k /= k.sum()

    def axis(x, ax):
        pad = [(0, 0)] * x.ndim
        pad[ax] = (r, r)
        xp = np.pad(x, pad, mode='edge')
        n = x.shape[ax]
        out = np.zeros(x.shape, np.float32)
        for i, w in enumerate(k):
            sl = [slice(None)] * x.ndim
            sl[ax] = slice(i, i + n)
            out += w * xp[tuple(sl)]
        return out
    return axis(axis(a.astype(np.float32), 0), 1)


def erode(mask, size):
    img = Image.fromarray(mask.astype(np.uint8) * 255).filter(ImageFilter.MinFilter(size))
    return np.array(img) > 127


class Word:
    def __init__(self):
        f = ImageFont.truetype(FONT, int(round(EM)))
        track = 1.2 * SS
        advance = [f.getlength(c) for c in WORD]
        boxes = [f.getbbox(c, anchor='ls') for c in WORD]
        top = -min(b[1] for b in boxes)
        bottom = max(b[3] for b in boxes)
        pad = 12
        total = sum(advance) + track * (len(WORD) - 1)
        tw, th = int(math.ceil(total)) + 2 * pad, int(math.ceil(top + bottom)) + 2 * pad
        baseline = pad + top
        mask = np.zeros((th, tw), bool)
        lid = np.zeros((th, tw), np.int32)
        x = pad
        for i, c in enumerate(WORD):
            img = Image.new('L', (tw, th))
            ImageDraw.Draw(img).text((x, baseline), c, font=f, fill=255, anchor='ls')
            m = np.array(img) >= 128
            mask |= m
            lid[m] = i
            x += advance[i] + track
        self.n = len(WORD)
        cx, cy = tw / 2, baseline - (top - bottom) / 2
        mf = mask.astype(np.float32)
        g = blur(mf, 2.0)
        gy, gx = np.gradient(g)
        mag = np.hypot(gx, gy)
        nx = np.where(mag > 1e-4, -gx / np.maximum(mag, 1e-6), 0.0)
        ny = np.where(mag > 1e-4, -gy / np.maximum(mag, 1e-6), 0.0)
        h = blur(mf, 3.0)
        band = mask & ~erode(mask, 5)
        ys, xs = np.nonzero(mask)
        b = np.clip((0.93 - h[ys, xs]) / 0.43, 0, 1)
        fx, fy = nx[ys, xs] * 0.9 * b, ny[ys, xs] * 0.9 * b
        norm = np.sqrt(fx * fx + fy * fy + 1)
        px, py = xs - cx, ys - cy
        lids = lid[ys, xs]
        # frente e fundo: a borda inclinada (bisel) pega o brilho
        P = [np.stack([px, py, np.full(px.shape, DEPTH / 2.0)], 1),
             np.stack([px, py, np.full(px.shape, -DEPTH / 2.0)], 1)]
        Nrm = [np.stack([fx, fy, np.ones_like(fx)], 1) / norm[:, None],
               np.stack([fx, fy, -np.ones_like(fx)], 1) / norm[:, None]]
        L = [lids, lids]
        K = [np.zeros(px.shape, np.int8), np.ones(px.shape, np.int8)]   # 0 frente, 1 fundo
        # lateral: so a faixa da borda, uma camada por pixel de espessura
        bys, bxs = np.nonzero(band)
        zs = np.arange(-DEPTH / 2.0 + 1, DEPTH / 2.0 - 0.5, 1.0)
        bpx, bpy = np.repeat(bxs - cx, len(zs)), np.repeat(bys - cy, len(zs))
        bz = np.tile(zs, len(bxs))
        bn = np.stack([np.repeat(nx[bys, bxs], len(zs)), np.repeat(ny[bys, bxs], len(zs)),
                       np.zeros(len(bz))], 1)
        P.append(np.stack([bpx, bpy, bz], 1))
        Nrm.append(bn)
        L.append(np.repeat(lid[bys, bxs], len(zs)))
        K.append(np.full(len(bz), 2, np.int8))
        self.p = np.concatenate(P).astype(np.float32)
        self.n3 = np.concatenate(Nrm).astype(np.float32)
        self.lid = np.concatenate(L)
        self.kind = np.concatenate(K)
        # cor de cada ponto: Fliper roxo, OS rosa, mais claro em cima
        base = np.where((self.lid >= 6)[:, None], PINK, PURPLE)
        yn = (self.p[:, 1] - self.p[:, 1].min()) / (self.p[:, 1].max() - self.p[:, 1].min())
        base = base * (1.12 - 0.34 * yn)[:, None]
        base = np.where((self.kind == 2)[:, None], base * 0.7, base)
        base = np.where((self.kind == 1)[:, None], base * 0.8, base)
        self.base = base.astype(np.float32)
        # pontos onde nascem as faiscas: bordas viradas para a luz, na frente
        lit = band & ((ny < -0.35) | (nx < -0.45))
        ay, ax = np.nonzero(lit)
        self.anchor = np.stack([ax - cx, ay - cy], 1).astype(np.float32)
        self.anchor_lid = lid[ay, ax]


def rotate(st, p, n, lid, pops=True):
    """Aplica o flip da letra, o giro e a inclinacao da palavra."""
    ca, sa = np.cos(st['flip'])[lid], np.sin(st['flip'])[lid]
    zp = st['pop'][lid] if pops else 0
    y1 = p[..., 1] * ca - p[..., 2] * sa
    z1 = p[..., 1] * sa + p[..., 2] * ca + zp
    x1 = p[..., 0]
    ny1 = n[..., 1] * ca - n[..., 2] * sa
    nz1 = n[..., 1] * sa + n[..., 2] * ca
    nx1 = n[..., 0]
    ct, stt = math.cos(st['theta']), math.sin(st['theta'])
    x2 = x1 * ct + z1 * stt
    z2 = -x1 * stt + z1 * ct
    nx2 = nx1 * ct + nz1 * stt
    nz2 = -nx1 * stt + nz1 * ct
    cp, sp = math.cos(st['phi']), math.sin(st['phi'])
    y3 = y1 * cp - z2 * sp
    z3 = y1 * sp + z2 * cp
    ny3 = ny1 * cp - nz2 * sp
    nz3 = ny1 * sp + nz2 * cp
    S = st['scale']
    x3, y3, z3 = x2 * S, y3 * S, z3 * S
    k = CAM / np.maximum(CAM - z3, 80.0)
    sx = CW / 2 + st['tx'] * SS + x3 * k
    sy = CH / 2 + st['ty'] * SS + y3 * k
    return sx, sy, z3, np.stack([nx2, ny3, nz3], -1)


LIGHT = np.array([-0.38, -0.58, 0.72], np.float32)
LIGHT /= np.linalg.norm(LIGHT)
HALF = LIGHT + np.array([0, 0, 1], np.float32)
HALF /= np.linalg.norm(HALF)


def shade(word, st, sx, sy, n):
    """Cor de cada ponto: difusa, brilho, reflexo de ambiente, contraluz ciano."""
    nz = n[:, 2]
    diff = np.clip(n @ LIGHT, 0, 1)
    spec = np.clip(n @ HALF, 0, 1) ** 22
    # reflexo de ambiente: faixas claras que deslizam quando a superficie gira
    # (a face plana de frente fica fora das faixas: o brilho so aparece inclinada)
    rx, ry = 2 * nz * n[:, 0], 2 * nz * n[:, 1]
    env = smooth(0.80, 0.98, 0.5 + 0.5 * np.sin(rx * 7.0 + ry * 4.5 + math.pi))
    env = env * (0.3 + 0.7 * np.abs(nz) ** 0.5) * 0.7
    rim = (1 - np.clip(np.abs(nz), 0, 1)) ** 2.5
    back = np.clip(n @ np.array([0.7, 0.1, -0.4], np.float32), 0, 1)
    col = word.base * (0.26 + 0.92 * diff)[:, None]
    col += (spec * 0.55 + env * 0.6)[:, None] * WHITE
    col += (rim * 0.4 + back * 0.3)[:, None] * CYAN
    # varredura de luz: uma faixa diagonal que cruza a palavra
    if st['sweep'] is not None:
        d = (sx * 0.92 + sy * 0.38) / SS
        band = np.exp(-(((d - st['sweep']) / 7.0) ** 2))
        col += (band * 0.9)[:, None] * np.array([1.0, 0.96, 1.0], np.float32)
    return np.clip(col * st['alpha'], 0, 1)


OFFS = ((0, 0), (1, 0), (0, 1), (1, 1))


def render_word(word, st):
    sx, sy, z, n = rotate(st, word.p, word.n3, word.lid)
    col = shade(word, st, sx, sy, n)
    ix, iy = np.floor(sx).astype(np.int32), np.floor(sy).astype(np.int32)
    idx, cs, zs = [], [], []
    for dx, dy in OFFS:
        x, y = ix + dx, iy + dy
        ok = (x >= 0) & (x < CW) & (y >= 0) & (y < CH)
        idx.append((y * CW + x)[ok])
        cs.append(col[ok])
        zs.append(z[ok])
    idx, cs, zs = np.concatenate(idx), np.concatenate(cs), np.concatenate(zs)
    order = np.argsort(zs, kind='stable')           # de tras para frente
    buf = np.zeros((CH * CW, 3), np.float32)
    cov = np.zeros(CH * CW, np.float32)
    buf[idx[order]] = cs[order]
    cov[idx[order]] = 1.0
    buf = buf.reshape(CH, CW, 3)
    cov = cov.reshape(CH, CW)
    # media em luz linear
    lin = (buf ** 2.2).reshape(H, SS, W, SS, 3).mean((1, 3))
    return lin ** (1 / 2.2), cov.reshape(H, SS, W, SS).mean((1, 3)) * float(st['alpha'])


# -- Cena: tempo -> camera ------------------------------------------------

def state(t):
    n = len(WORD)
    st = dict(theta=0.0, phi=0.0, scale=1.0, alpha=1.0, tx=0.0, ty=0.0, sweep=None,
              flip=np.zeros(n, np.float32), pop=np.zeros(n, np.float32))
    if t < T_LAND:                                     # chega do fundo, girando
        k = (t - 0.35) / (T_LAND - 0.35)
        st['scale'] = 0.05 + 0.95 * ease_out(k, 3)
        st['theta'] = math.radians(-720) * (1 - ease_out(k, 4))
        st['phi'] = math.radians(12) * (1 - ease_out(k, 2))
        st['alpha'] = smooth(0.35, 0.95, t)
    elif t < T_ORBIT:                                  # de frente, balancando
        st['theta'] = math.radians(16) * math.sin(2 * math.pi * (t - T_LAND) / (T_ORBIT - T_LAND))
        st['phi'] = math.radians(4) * math.sin(4 * math.pi * (t - T_LAND) / (T_ORBIT - T_LAND))
    elif t < T_END:                                    # uma volta inteira
        k = (t - T_ORBIT) / (T_END - 1.0 - T_ORBIT)
        e = ease_io(k)
        st['theta'] = math.radians(360) * e
        st['phi'] = math.radians(9) * math.sin(math.pi * clamp(k))
        st['scale'] = 1 + 0.04 * math.sin(math.pi * clamp(k))
    else:                                              # some dentro do flash
        k = (t - T_END) / (DUR - 0.05 - T_END)
        st['scale'] = 1 - 0.95 * ease_in(k, 3)
        st['theta'] = math.radians(-360) * ease_in(k, 2)
        st['alpha'] = 1 - smooth(0.55, 1.0, k)
    for i in range(n):                                 # a onda de flips
        k = (t - T_FLIP - 0.09 * i) / 0.85
        if 0 < k < 1:
            st['flip'][i] = 2 * math.pi * ease_io(k)
            st['pop'][i] = 55 * math.sin(math.pi * k)
    for a, b in ((2.1, 2.95), (7.0, 7.7)):
        if a <= t <= b:
            st['sweep'] = -20 + (W + 40) * ease_io((t - a) / (b - a))
    return st


def over_loop(t):
    """O tempo sem emenda: o fim do ciclo vem antes do comeco (u < 0)."""
    return t if t <= DUR / 2 else t - DUR


# -- Fundo e efeitos (na resolucao do painel) --------------------------------

def line(frame, x0, y0, x1, y1, color, gain):
    steps = max(2, int(math.hypot(x1 - x0, y1 - y0) * 2) + 1)
    for s in range(steps):
        f = s / (steps - 1)
        x, y = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        ix, iy = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - ix, y - iy
        for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                          (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
            if 0 <= ix + dx < W and 0 <= iy + dy < H:
                frame[iy + dy, ix + dx] += color * (gain * w * 0.5)


def star(frame, cx, cy, size, color, gain):
    """Faisca de 4 pontas (mais curta na vertical, o painel e largo)."""
    r = int(size) + 3
    xs = np.arange(int(cx) - r, int(cx) + r + 1)
    ys = np.arange(int(cy) - r, int(cy) + r + 1)
    dx, dy = xs[None, :] - cx, ys[:, None] - cy
    ray_h = np.exp(-dy ** 2 / (2 * 0.42 ** 2)) * np.clip(1 - np.abs(dx) / size, 0, 1) ** 1.6
    ray_v = np.exp(-dx ** 2 / (2 * 0.42 ** 2)) * np.clip(1 - np.abs(dy) / (size * 0.7), 0, 1) ** 1.6
    core = np.exp(-(dx ** 2 + dy ** 2) / (2 * 0.6 ** 2))
    halo = 0.22 * np.exp(-(dx ** 2 + dy ** 2) / (2 * 1.7 ** 2))
    v = (ray_h + ray_v) * 0.8 + core * 1.2 + halo
    ok_y = (ys >= 0) & (ys < H)
    ok_x = (xs >= 0) & (xs < W)
    sub = v[np.ix_(ok_y, ok_x)] * gain
    if sub.size:
        y0, x0 = ys[ok_y][0], xs[ok_x][0]
        c = (color * 0.8 + WHITE * 0.2)
        frame[y0:y0 + sub.shape[0], x0:x0 + sub.shape[1]] += sub[..., None] * c


class Scene:
    def __init__(self):
        self.word = Word()
        rnd = random.Random(7)
        # tudo que se repete (deriva, estrias, brilho) da um numero inteiro de voltas em
        # DUR, para o fim do ciclo emendar no comeco sem pulo
        turn = 2 * math.pi / DUR
        self.stars = [(rnd.uniform(0, W), rnd.uniform(1, H - 1), rnd.uniform(0.10, 0.30),
                       rnd.choice((1, 1, 2)) * W / DUR, rnd.randint(1, 3) * turn, rnd.uniform(0, 6.3),
                       rnd.choice((CYAN, PURPLE, WHITE)))
                      for _ in range(38)]
        self.warp = [(rnd.uniform(0, 6.283), rnd.random(), rnd.randint(4, 8) / DUR,
                      rnd.choice((CYAN, PINK, PURPLE, WHITE, WHITE))) for _ in range(70)]
        # glitter: pontinhos que piscam sobre as letras (so onde ha letra)
        self.glitter = [(rnd.randrange(10, W - 10), rnd.randrange(5, H - 5), rnd.uniform(0, 6.3),
                         rnd.randint(2, 5) * 2 * turn, rnd.choice((WHITE, WHITE, CYAN, PINK)))
                        for _ in range(90)]
        self.sparks = []        # (t0, duracao, letra, ancora, tamanho, cor)
        pool = self.word.anchor
        lids = self.word.anchor_lid

        def spark(t0, dur, size, letter=None):
            ok = np.nonzero(lids == letter)[0] if letter is not None else np.arange(len(lids))
            if not len(ok):
                ok = np.arange(len(lids))
            j = int(rnd.choice(ok.tolist()))
            self.sparks.append((t0, dur, int(lids[j]), pool[j], size,
                                rnd.choice((WHITE, WHITE, CYAN, PINK, PURPLE))))
        for i in range(10):
            spark(T_LAND + rnd.uniform(0, 0.25), 0.6, rnd.uniform(3.5, 6.5))
        for i in range(8):
            spark(2.1 + rnd.uniform(0, 1.2), 0.5, rnd.uniform(2.5, 4.5))
        for i in range(len(WORD)):
            spark(T_FLIP + 0.09 * i + 0.85, 0.5, rnd.uniform(3.5, 5.5), letter=i)
        for i in range(10):
            spark(T_ORBIT + 0.25 + rnd.uniform(0, 1.3), 0.5, rnd.uniform(2.5, 4.5))
        for i in range(10):
            spark(7.0 + rnd.uniform(0, 0.75), 0.5, rnd.uniform(3.0, 5.5))

    def background(self, t, u):
        frame = np.zeros((H, W, 3), np.float32)
        warp = max(bump((u - 0.85) / 0.75), bump((u + 0.3) / 0.3))
        for x, y, b, drift, tw_rate, ph, color in self.stars:      # poeira de estrelas
            xx = (x - t * drift) % W
            tw = 0.6 + 0.4 * math.sin(t * tw_rate + ph)
            ix, iy = int(xx), int(y)
            fx, fy = xx - ix, y - iy
            for dx, dy, w in ((0, 0, (1 - fx) * (1 - fy)), (1, 0, fx * (1 - fy)),
                              (0, 1, (1 - fx) * fy), (1, 1, fx * fy)):
                if 0 <= ix + dx < W and 0 <= iy + dy < H:
                    frame[iy + dy, ix + dx] += color * (b * tw * w * (1 - 0.8 * warp))
        if warp > 0.02:                                  # estrias saindo do centro
            for a, ph, sp, color in self.warp:
                p = (ph + t * sp) % 1.0
                r1, r0 = p ** 2.2, max(0.0, p - 0.05 - 0.09 * warp) ** 2.2
                rx, ry = 76.0, 19.0
                ca, sa = math.cos(a), math.sin(a)
                gain = warp * min(1.0, p * 4) * (1 - p ** 6) * 1.3
                line(frame, W / 2 + ca * r0 * rx, H / 2 + sa * r0 * ry,
                     W / 2 + ca * r1 * rx, H / 2 + sa * r1 * ry, color, gain)
        return frame

    def effects(self, frame, st, t, u, cov):
        # flash no centro (a palavra nasce e some dentro dele) + pouso
        flash = bump((u - 0.25) / 0.28) + bump((t - T_LAND) / 0.1) * 0.35
        if flash > 0.01:
            dx = (np.arange(W)[None, :] - W / 2) / 15.0
            dy = (np.arange(H)[:, None] - H / 2) / 5.5
            frame += (flash * np.exp(-(dx ** 2 + dy ** 2) / 2))[..., None] * (CYAN * 0.5 + WHITE * 0.7)
        # reflexo anamorfico: um risco horizontal que atravessa a tela
        streak = 0.7 * bump((u - 0.3) / 0.3) + 0.8 * bump((t - T_LAND - 0.05) / 0.25)
        if streak > 0.01:
            x = np.abs(np.arange(W)[None, :] - W / 2 + 0.0)
            y = np.arange(H)[:, None] - H / 2 + 0.5
            ln = np.exp(-y ** 2 / (2 * 0.55 ** 2)) * np.exp(-x / (14 + 36 * streak))
            glow = np.exp(-y ** 2 / (2 * 1.8 ** 2)) * np.exp(-x / (10 + 24 * streak)) * 0.18
            frame += ((ln + glow) * streak)[..., None] * (CYAN * 0.6 + WHITE * 0.5)
        for x, y, ph, rate, color in self.glitter:
            if cov[y, x] > 0.7:
                g = max(0.0, math.sin(ph + t * rate)) ** 10
                frame[y, x] += color * (0.75 * g)
        # faiscas, coladas nas bordas das letras (somem quando a letra vira)
        for t0, dur, letter, anchor, size, color in self.sparks:
            k = (t - t0) / dur
            if not 0 < k < 1:
                continue
            p = np.array([[anchor[0], anchor[1], DEPTH / 2.0]], np.float32)
            nrm = np.array([[0, 0, 1.0]], np.float32)
            sx, sy, _, n = rotate(st, p, nrm, np.array([letter]))
            vis = smooth(0.15, 0.55, float(n[0, 2])) * st['alpha']
            if vis < 0.02:
                continue
            star(frame, float(sx[0]) / SS, float(sy[0]) / SS, size * (0.55 + 0.45 * math.sin(math.pi * k)),
                 color, 1.25 * vis * math.sin(math.pi * k) ** 1.4)

    def frame(self, i):
        t = i / FPS
        u = over_loop(t)
        st = state(t)
        word, cov = render_word(self.word, st)
        bg = self.background(t, u)
        frame = word + bg * (1 - cov)[..., None]
        self.effects(frame, st, t, u, cov)
        # brilho (bloom) suave nas partes claras
        glow = blur(np.clip(frame, 0, 1.2) ** 2, 1.5)
        frame = frame + glow * 0.3
        return np.clip(frame, 0, 1)


def to_image(a):
    return Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGB')


def palettize(images):
    """Uma paleta so para o GIF todo: sem cintilar entre quadros, preto puro no 0."""
    px = np.concatenate([np.array(im).reshape(-1, 3) for im in images[::3]])
    px = px[px.sum(1) > 24]
    sample = Image.fromarray(px[np.random.RandomState(1).permutation(len(px))[:60000]]
                             .reshape(-1, 1, 3).astype(np.uint8))
    pal = sample.quantize(colors=255, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    table = list(pal.getpalette()[:255 * 3])
    base = Image.new('P', (1, 1))
    base.putpalette([0, 0, 0] + table)
    return [im.quantize(palette=base, dither=Image.Dither.NONE) for im in images]


def led_sim(a, scale=8):
    """Os pontos de um painel de LED (so para olhar), com uma pontinha de luz entre eles."""
    img = to_image(a).resize((W * scale, H * scale), Image.NEAREST)
    arr = np.array(img).astype(np.float32)
    yy, xx = np.mgrid[0:H * scale, 0:W * scale]
    cx, cy = (xx % scale) - (scale - 1) / 2, (yy % scale) - (scale - 1) / 2
    dot = np.clip(1.35 - np.hypot(cx, cy) / (scale * 0.46), 0, 1)
    out = arr * dot[..., None]
    out += blur(out, scale * 0.5) * 0.5
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB')


def main(argv):
    out = argv[1] if len(argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                      '..', 'config', 'zedmd-fliperos.gif')
    scene = Scene()
    arrays = []
    for i in range(N):
        arrays.append(scene.frame(i))
        if i % 25 == 0:
            sys.stderr.write('frame %d/%d\n' % (i, N))
    images = [to_image(a) for a in arrays]
    frames = palettize(images)
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=round(1000 / FPS),
                   loop=0, disposal=1, optimize=False)
    print('%s: %d quadros, %d bytes' % (out, len(frames), os.path.getsize(out)))
    prev = os.environ.get('PREVIEW')
    if prev:
        os.makedirs(prev, exist_ok=True)
        keys = [int(s * FPS) for s in (0.0, 0.5, 1.0, 1.5, 1.9, 2.5, 3.0, 3.8, 4.2, 4.6, 5.0, 5.7, 6.1, 6.5,
                                     6.9, 7.4, 8.0, 8.3)]
        sheet = Image.new('RGB', (W * 4 * 3, H * 4 * 6))
        for n, k in enumerate(keys):
            sheet.paste(to_image(arrays[min(k, N - 1)]).resize((W * 4, H * 4), Image.NEAREST),
                        ((n % 3) * W * 4, (n // 3) * H * 4))
        sheet.save(os.path.join(prev, 'sheet.png'))
        for k in (1.9, 4.2, 5.9):
            led_sim(arrays[int(k * FPS)]).save(os.path.join(prev, 'led-%.1f.png' % k))


if __name__ == '__main__':
    sys.exit(main(sys.argv))
