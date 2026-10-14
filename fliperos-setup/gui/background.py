# Os fundos animados, como os da interface do ZSNES: neve, agua, fogo e
# fumaca, mais o ceu de estrelas. Um e sorteado cada vez que a interface
# abre (FLIPEROS_GUI_BG=nome fixa um).
#
# Cada fundo tem draw(surf, t), com t em segundos, e e escuro o bastante
# para o texto claro ficar legivel por cima. Tirando o fogo, a imagem
# depende so de t: o mesmo t da sempre o mesmo quadro (os prints).

import math
import os
import random

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
    """A agua: faixas de luz que ondulam, linha por linha."""

    def __init__(self, rnd):
        self.tile = pygame.Surface((W + 32, H))
        for y in range(H):
            depth = y / (H - 1)
            for x in range(0, W + 32, 4):
                band = (x + y * 2) // 24 % 2
                shade = 14 + 10 * band
                self.tile.fill((4, round(shade + 12 * depth), round(40 + shade + 26 * depth)), (x, y, 4, 1))

    def draw(self, surf, t):
        for y in range(H):
            off = 16 + round(10 * math.sin(y / 14 + t * 1.6) + 5 * math.sin(y / 5 - t * 2.3))
            surf.blit(self.tile, (0, y), (off, y, W, 1))


class Fire:
    """O fogo subindo de baixo: o algoritmo classico, numa grade de 80x44
    ampliada quatro vezes."""

    GW, GH = 80, 44
    STEPS = 15   # passos por segundo

    def __init__(self, rnd):
        self.rnd = rnd
        self.heat = [[0] * self.GW for _ in range(self.GH + 1)]
        self.small = pygame.Surface((self.GW, self.GH))
        self.step = 0
        # Do preto ao laranja, sem chegar ao branco: o texto fica por cima.
        self.palette = []
        for i in range(64):
            f = i / 63
            self.palette.append((round(min(1, f * 1.6) * 200), round(max(0, f - 0.35) * 190), round(f * 18)))

    def advance(self):
        heat, rnd = self.heat, self.rnd
        heat[self.GH] = [rnd.randrange(30, 64) if rnd.random() < 0.6 else 0 for _ in range(self.GW)]
        for y in range(self.GH):
            below, row = heat[y + 1], heat[y]
            for x in range(self.GW):
                total = below[x - 1] + below[x] + below[x] + below[(x + 1) % self.GW]
                row[x] = max(0, total * 10 // 43 - 1)

    def draw(self, surf, t):
        while self.step < int(t * self.STEPS) and self.step < 100000:
            self.advance()
            self.step += 1
        pix = pygame.PixelArray(self.small)
        palette = self.palette
        for y in range(self.GH):
            row = self.heat[y]
            for x in range(self.GW):
                pix[x, y] = palette[min(63, row[x])]
        del pix
        surf.fill((0, 0, 0))
        pygame.transform.scale(self.small, (W, self.GH * 4), surf.subsurface((0, H - self.GH * 4, W, self.GH * 4)))


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
