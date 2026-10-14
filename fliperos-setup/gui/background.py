# Os fundos animados, como os da interface do ZSNES: neve, agua, fogo e
# fumaca, mais o ceu de estrelas. Um e sorteado cada vez que o menu abre,
# nunca o da vez anterior (serve.py); FLIPEROS_GUI_BG=nome fixa um.
#
# Cada fundo tem draw(surf, t), com t em segundos, e e escuro o bastante
# para o texto claro ficar legivel por cima. Tirando o fogo, a imagem
# depende so de t: o mesmo t da sempre o mesmo quadro (os prints).

import math
import os
import random

import numpy
import pygame

import theme as T

W, H = T.WIDTH, T.HEIGHT


def gradient(top, bottom):
    surf = pygame.Surface((W, H))
    for y in range(H):
        t = y / (H - 1)
        surf.fill([round(a + (b - a) * t) for a, b in zip(top, bottom)], (0, y, W, 1))
    return surf


class Stars:
    """As estrelas passando devagar, em tres camadas."""

    def __init__(self, rnd):
        self.stars = [(rnd.randrange(W), rnd.randrange(H), rnd.choice([3, 3, 6, 12]),
                       rnd.choice([T.COMMENT, T.COMMENT, T.PURPLE, T.FG])) for _ in range(80)]

    def draw(self, surf, t):
        surf.fill(T.SPACE)
        for x, y, speed, color in self.stars:
            surf.set_at((int(x - speed * t) % W, y), color)


class Snow:
    """A neve caindo: flocos de um ou dois pixels, balancando de lado."""

    def __init__(self, rnd):
        self.sky = gradient((0x08, 0x0A, 0x1C), (0x16, 0x1C, 0x3A))
        self.flakes = [(rnd.randrange(W), rnd.randrange(H), rnd.uniform(10, 34), rnd.uniform(0, 6.28),
                        rnd.choice([1, 1, 2])) for _ in range(90)]

    def draw(self, surf, t):
        surf.blit(self.sky, (0, 0))
        for x, y, speed, phase, size in self.flakes:
            px = int(x + 6 * math.sin(t * 1.3 + phase)) % W
            py = int(y + speed * t) % H
            color = T.FG if size == 2 else (0x9A, 0xA4, 0xC8)
            surf.fill(color, (px, py, size, size))


class Water:
    """O fundo de uma piscina: a rede de luz que a superficie projeta (as
    causticas, o metodo iterativo classico dos shaders de agua), sobre o
    azul em degrade, uns raios de sol inclinados e bolhas subindo. A agua e
    calculada em 160x120 com numpy e ampliada suave."""

    GW, GH = 160, 120
    TAU = 6.28318

    def __init__(self, rnd):
        x = numpy.arange(self.GW, dtype=numpy.float32)[:, None] / self.GW
        y = numpy.arange(self.GH, dtype=numpy.float32)[None, :] / self.GW
        self.px = numpy.broadcast_to((x * self.TAU * 1.6) % self.TAU - 250, (self.GW, self.GH)).copy()
        self.py = numpy.broadcast_to((y * self.TAU * 1.6) % self.TAU - 250, (self.GW, self.GH)).copy()
        self.x = numpy.arange(self.GW, dtype=numpy.float32)[:, None]
        self.y = numpy.arange(self.GH, dtype=numpy.float32)[None, :]
        depth = self.y / (self.GH - 1)
        # Do azul da superficie ao fundo escuro.
        self.base = numpy.stack([(5 + 0 * self.x + 3 * depth), (30 + 0 * self.x - 16 * depth),
                                 (64 + 0 * self.x - 26 * depth)], -1)
        self.light = (1 - 0.6 * depth)[..., None] * numpy.array([60, 150, 170], numpy.float32)
        self.small = pygame.Surface((self.GW, self.GH))
        self.offset = rnd.uniform(0, 50)
        self.cached = None
        self.big = pygame.Surface((W, H))
        self.bubbles = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.uniform(14, 34), rnd.uniform(0, 6.28),
                         rnd.choice([1, 1, 2, 2, 3])) for _ in range(20)]

    def draw(self, surf, t):
        # A agua anda devagar: recalculada a 30 Hz, as bolhas a cada quadro.
        if self.cached is None or abs(t - self.cached[0]) >= 1 / 30:
            self.cached = (t, self.render(t))
        surf.blit(self.cached[1], (0, 0))
        for bx, by, speed, phase, size in self.bubbles:
            yy = (by - speed * t) % (H + 20) - 10
            xx = bx + 4 * math.sin(t * 1.7 + phase + yy * 0.05)
            pygame.draw.circle(surf, (110, 190, 220), (int(xx), int(yy)), size, 1)
            if size > 1:
                surf.set_at((int(xx) - 1, int(yy) - 1), (200, 240, 255))

    def render(self, t):
        time_ = t * 0.45 + 23 + self.offset
        px, py = self.px, self.py
        ix, iy = px, py
        c = numpy.ones_like(px)
        inten = 0.005
        for n in range(4):
            t2 = time_ * (1 - 3.5 / (n + 1))
            ix, iy = (px + numpy.cos(t2 - ix) + numpy.sin(t2 + iy), py + numpy.sin(t2 - iy) + numpy.cos(t2 + ix))
            c += 1 / numpy.hypot(px / (numpy.sin(ix + t2) / inten), py / (numpy.cos(iy + t2) / inten))
        c /= 4
        c = 1.17 - c ** 1.4
        caustic = numpy.clip(numpy.abs(c) ** 8, 0, 1)
        x, y = self.x, self.y
        rays = numpy.zeros_like(caustic)
        for k, x0 in enumerate((20, 75, 120, 155)):
            center = x0 - 40 + y * 0.45 + 9 * math.sin(t * 0.35 + k * 1.7)
            rays += numpy.exp(-((x - center) / 8.0) ** 2) * (0.30 + 0.12 * math.sin(t * 0.8 + k))
        rays *= (1 - y / self.GH) ** 1.6
        rgb = self.base + self.light * (caustic * 0.8 + rays * 0.35)[..., None]
        pygame.surfarray.blit_array(self.small, numpy.clip(rgb, 0, 255).astype(numpy.uint8))
        pygame.transform.smoothscale(self.small, (W, H), self.big)
        return self.big


class Fire:
    """O fogo subindo de baixo: o algoritmo classico, numa grade de 80x44
    calculada com numpy a 30 passos por segundo e ampliada suave."""

    GW, GH = 80, 44
    STEPS = 30   # passos por segundo

    def __init__(self, rnd):
        self.rng = numpy.random.default_rng(rnd.randrange(1 << 30))
        self.heat = numpy.zeros((self.GH + 1, self.GW), numpy.int32)
        self.small = pygame.Surface((self.GW, self.GH))
        self.step = 0
        # Do preto ao laranja, sem chegar ao branco: o texto fica por cima.
        f = numpy.arange(64, dtype=numpy.float32) / 63
        self.palette = numpy.stack([numpy.minimum(1, f * 1.6) * 205, numpy.maximum(0, f - 0.35) * 195, f * 20],
                                   -1).astype(numpy.uint8)

    def advance(self):
        heat = self.heat
        fuel = self.rng.integers(30, 64, self.GW)
        heat[self.GH] = numpy.where(self.rng.random(self.GW) < 0.6, fuel, 0)
        below = heat[1:]
        total = numpy.roll(below, 1, 1) + below * 2 + numpy.roll(below, -1, 1)
        heat[:self.GH] = numpy.maximum(0, total * 10 // 43 - 1)

    def draw(self, surf, t):
        target = min(int(t * self.STEPS), self.step + 400)
        while self.step < target:
            self.advance()
            self.step += 1
        rgb = self.palette[numpy.minimum(63, self.heat[:self.GH])]
        pygame.surfarray.blit_array(self.small, rgb.transpose(1, 0, 2))
        surf.fill((0, 0, 0))
        pygame.transform.smoothscale(self.small, (W, self.GH * 4), surf.subsurface((0, H - self.GH * 4, W, self.GH * 4)))


class Smoke:
    """A fumaca: nuvens que sobem devagar, crescendo e sumindo."""

    def __init__(self, rnd):
        self.sky = gradient((0x0C, 0x0A, 0x14), (0x1E, 0x18, 0x2A))
        self.layer = pygame.Surface((W, H), pygame.SRCALPHA)
        self.puffs = [(rnd.randrange(W), rnd.randrange(H + 80), rnd.uniform(8, 20), rnd.uniform(0, 6.28))
                      for _ in range(26)]

    def draw(self, surf, t):
        surf.blit(self.sky, (0, 0))
        self.layer.fill((0, 0, 0, 0))
        for x, y, speed, phase in self.puffs:
            rise = (y + speed * t) % (H + 80)
            px = int(x + 18 * math.sin(t * 0.4 + phase))
            radius = 10 + int(rise / 9)
            alpha = max(0, 46 - int(rise / 7))
            pygame.draw.circle(self.layer, (0x8A, 0x80, 0xA8, alpha), (px, H + 30 - int(rise)), radius)
        surf.blit(self.layer, (0, 0))


BACKGROUNDS = {"stars": Stars, "snow": Snow, "water": Water, "fire": Fire, "smoke": Smoke}


def pick(name=None, seed=None, exclude=None):
    """O fundo pedido ou, sem nome (nem FLIPEROS_GUI_BG), um sorteado, que
    nao e o exclude (o que estava na tela). O sorteado tambem tem estrelas,
    flocos e nuvens em lugares novos; o pedido (os prints) e sempre igual."""
    fixed = name or os.environ.get("FLIPEROS_GUI_BG")
    if fixed:
        name = fixed if fixed in BACKGROUNDS else "stars"
    else:
        name = random.choice([n for n in BACKGROUNDS if n != exclude] or list(BACKGROUNDS))
    if seed is None:
        seed = 7 if fixed else random.randrange(1 << 30)
    bg = BACKGROUNDS[name](random.Random(seed))
    bg.name = name
    return bg
