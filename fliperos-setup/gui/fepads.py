# Os botoes da direita dos joypads dos videogames, para o guia dos controles
# do frontend (Frontend controls > Joypad layout): so o conjunto de botoes de
# acao de cada controle, como ele e, em perspectiva e do tamanho dos botoes do
# painel de arcade do guia (feview.button3d: raio 12, a elipse achatada, o
# lado de 4 pixels), sem o corpo do controle atras.
#
# As posicoes e os tamanhos foram medidos em imagens de cima de cada controle
# (Wikimedia Commons: o desenho tecnico do DualShock 4, os layouts em SVG do
# Xbox 360, do GameCube e do NES, e fotos do Evan-Amos e de closes dos botoes;
# nas fotos em angulo, a distancia vertical corrigida pela elipse dos
# botoes). Cada tabela da o centro e o diametro de cada botao em diametros do
# botao principal (o B no Saturn e no Mega Drive, o A no GameCube e no N64),
# com o y para baixo; o desenho centra o conjunto em (cx, cy).
#
# Cada desenho devolve onde fica cada botao ({papel: (x, y do topo, raio)}),
# para o guia escrever a funcao ao lado. Os papeis sao os do Button mapping de
# um joypad, pela posicao: south, east, west, north; e os de quem tem mais
# botoes: a b c x y z (Saturn, Mega Drive) e cup cdown cleft cright (os C do
# Nintendo 64). O Neo Geo CD tem A B C D nos papeis que o Batocera da a eles:
# A sul, B leste, C oeste, D norte.

import math

import pygame

import tiny

FLAT, LIFT = 0.62, 4        # os mesmos do guia (feview): a elipse e a altura
R = 12                      # o raio de um botao do painel de arcade do guia
OUTLINE = (0x10, 0x10, 0x16)
WHITE = (0xF4, 0xF4, 0xF6)
DARK = (0x3C, 0x3E, 0x48)


def shade(color, k):
    if k <= 1:
        return tuple(int(c * k) for c in color)
    return tuple(min(255, int(c + (255 - c) * (k - 1))) for c in color)


def ellipse(surf, color, cx, cy, rx, ry, width=0):
    pygame.draw.ellipse(surf, color, (cx - rx, cy - ry, 2 * rx, 2 * ry), width)


def button3d(surf, cx, cy, r, color):
    """O botao em perspectiva, como o do painel de arcade do guia: o aro
    escuro, o lado (um cilindro mais escuro) e o topo com o brilho. (cx, cy)
    e o centro do topo."""
    ry = round(r * FLAT)
    ellipse(surf, OUTLINE, cx, cy + LIFT + 1, r + 2, ry + 2)
    ellipse(surf, shade(color, 0.35), cx, cy + LIFT, r, ry)
    surf.fill(shade(color, 0.5), (cx - r, cy, 2 * r, LIFT))
    pygame.draw.line(surf, shade(color, 0.7), (cx - r + 2, cy + 1), (cx - r + 2, cy + LIFT))
    ellipse(surf, color, cx, cy, r, ry)
    ellipse(surf, shade(color, 1.35), cx - r // 3, cy - ry // 3, r // 2, max(1, ry // 3))
    ellipse(surf, shade(color, 0.6), cx, cy, r, ry, 1)


def letter(surf, cx, cy, s, color, scale=2):
    """A letra no topo de um botao (a fonte tiny), achatada como ele; a de
    tamanho 1 (os botoes pequenos) fica inteira, ou nao se le."""
    if scale == 1:
        tiny.centered(surf, s, color, cx + 1, cy - 2)
        return
    img = pygame.Surface((tiny.width(s), 5), pygame.SRCALPHA)
    tiny.text(img, s, color, 0, 0)
    w, h = img.get_width() * scale, max(3, round(5 * scale * FLAT) + 1)
    img = pygame.transform.scale(img, (w, h))
    surf.blit(img, (cx - w // 2 + 1, cy - h // 2))


def flat(points, cx, cy):
    """Os pontos de um simbolo (em volta de 0, 0) achatados no topo do botao."""
    return [(cx + x, cy + round(y * FLAT)) for x, y in points]


def symbol(surf, x, y, kind, color):
    """Os simbolos do PlayStation e as setas dos C do N64 no topo do botao."""
    if kind == "tri":
        pygame.draw.polygon(surf, color, flat([(0, -6), (-6, 5), (6, 5)], x, y), 2)
    elif kind == "cir":
        ellipse(surf, color, x, y, 6, 4, 2)
    elif kind == "cross":
        pygame.draw.line(surf, color, *flat([(-5, -5), (5, 5)], x, y), 2)
        pygame.draw.line(surf, color, *flat([(-5, 5), (5, -5)], x, y), 2)
    elif kind == "sq":
        pygame.draw.polygon(surf, color, flat([(-5, -5), (5, -5), (5, 5), (-5, 5)], x, y), 2)
    elif kind.startswith("arrow"):
        d = {"arrowup": (0, -1), "arrowdown": (0, 1), "arrowleft": (-1, 0), "arrowright": (1, 0)}[kind]
        tip, side = (d[0] * 4, d[1] * 4), (d[1] * 3, d[0] * 3)
        pygame.draw.polygon(surf, color, flat(
            [tip, (-d[0] * 2 + side[0], -d[1] * 2 + side[1]), (-d[0] * 2 - side[0], -d[1] * 2 - side[1])], x, y))


def bean(surf, cx, cy, radius, start, end, thick, color):
    """Um botao em feijao (o X e o Y do GameCube) em perspectiva: um arco de
    raio radius e largura thick (pixels de frente) em volta de (cx, cy), com
    o lado e o topo. Devolve o meio dele."""
    steps = 16
    pts = []
    for i in range(steps + 1):
        a = math.radians(start + (end - start) * i / steps)
        pts.append((cx + round(radius * math.cos(a)), cy + round(radius * math.sin(a) * FLAT)))
    half = max(3, round(thick / 2))
    ry = max(2, round(half * FLAT))
    for x, y in pts:
        ellipse(surf, OUTLINE, x, y + LIFT + 1, half + 2, ry + 2)
    for x, y in pts:
        ellipse(surf, shade(color, 0.35), x, y + LIFT, half, ry)
        surf.fill(shade(color, 0.5), (x - half, y, 2 * half, LIFT))
    for x, y in pts:
        ellipse(surf, color, x, y, half, ry)
    x, y = pts[len(pts) // 2]
    ellipse(surf, shade(color, 1.3), x - 2, y - 1, 2, 1)
    return x, y


# ── As medidas: (papel, x, y, diametro, cor, letra ou simbolo, tinta) ─
# Em diametros do botao principal, o y para baixo, vista de cima.

PLAYSTATION = [  # o desenho tecnico do DualShock 4: losango simetrico, 1,15
    ("north", 0, -1.15, 1, DARK, "tri", (0x3C, 0xC8, 0x9C)),
    ("west", -1.16, 0, 1, DARK, "sq", (0xF0, 0x96, 0xD0)),
    ("east", 1.16, 0, 1, DARK, "cir", (0xF2, 0x5C, 0x6C)),
    ("south", 0, 1.14, 1, DARK, "cross", (0x7C, 0xA4, 0xF4)),
]
XBOX = [  # o SVG do Xbox 360 e a foto do Xbox Series: losango de 1,06
    ("north", 0, -1.05, 1, (0xF2, 0xC2, 0x1E), "Y", WHITE),
    ("west", -1.08, 0, 1, (0x2E, 0x7E, 0xEC), "X", WHITE),
    ("east", 1.08, 0, 1, (0xE4, 0x34, 0x34), "B", WHITE),
    ("south", 0, 1.05, 1, (0x46, 0xB8, 0x46), "A", WHITE),
]
SNES = [  # o close de cima: mais largo (1,28) que alto (1,02); as cores do Super Famicom
    ("north", 0, -1.02, 1, (0x3A, 0x5A, 0xCC), "", None),
    ("west", -1.28, 0, 1, (0x2E, 0x9C, 0x4E), "", None),
    ("east", 1.27, 0, 1, (0xDC, 0x2C, 0x3C), "", None),
    ("south", 0, 1.03, 1, (0xF0, 0xC4, 0x2C), "", None),
]
NES = [  # o SVG: lado a lado, 1,39 diametro de centro a centro
    ("west", -0.69, 0, 1, (0xD4, 0x24, 0x2C), "", None),
    ("south", 0.69, 0, 1, (0xD4, 0x24, 0x2C), "", None),
]
DREAMCAST = [  # o close de cima, com o controle nivelado: o losango girado ~11 graus
    ("north", -0.21, -1.0, 1, (0x2E, 0xA8, 0x4E), "Y", WHITE),
    ("west", -1.18, 0.23, 1, (0xF0, 0xC0, 0x24), "X", WHITE),
    ("east", 1.18, -0.23, 1, (0x34, 0x6C, 0xDC), "B", WHITE),
    ("south", 0.21, 1.0, 1, (0xDC, 0x2C, 0x2C), "A", WHITE),
]
SATURN = [  # o close e a foto inteira: A B C num arco, X Y Z menores e mais juntos
    ("x", -1.40, -0.47, 0.75, (0xC8, 0xC8, 0xD2), "X", (0x34, 0x36, 0x40)),
    ("y", -0.54, -1.05, 0.75, (0xC8, 0xC8, 0xD2), "Y", (0x34, 0x36, 0x40)),
    ("z", 0.37, -1.40, 0.75, (0xC8, 0xC8, 0xD2), "Z", (0x34, 0x36, 0x40)),
    ("a", -0.96, 0.71, 1, (0x34, 0x36, 0x40), "A", (0xE8, 0xE8, 0xF0)),
    ("b", 0, 0, 1, (0x34, 0x36, 0x40), "B", (0xE8, 0xE8, 0xF0)),
    ("c", 1.12, -0.45, 1, (0x34, 0x36, 0x40), "C", (0xE8, 0xE8, 0xF0)),
]
MEGADRIVE = [  # a foto do de seis botoes, o vertical corrigido pela elipse (0,65)
    ("x", -1.10, -1.32, 0.72, (0x50, 0x50, 0x5C), "X", (0xF0, 0x50, 0x50)),
    ("y", -0.05, -1.56, 0.72, (0x50, 0x50, 0x5C), "Y", (0xF0, 0x50, 0x50)),
    ("z", 1.01, -1.51, 0.72, (0x50, 0x50, 0x5C), "Z", (0xF0, 0x50, 0x50)),
    ("a", -1.16, 0.36, 1, (0x50, 0x50, 0x5C), "A", (0xF0, 0x50, 0x50)),
    ("b", 0, 0, 1, (0x50, 0x50, 0x5C), "B", (0xF0, 0x50, 0x50)),
    ("c", 1.16, -0.04, 1, (0x50, 0x50, 0x5C), "C", (0xF0, 0x50, 0x50)),
]
NEOGEO = [  # a foto, sem o giro dela: C em cima do A, D em cima do B, a coluna direita mais alta
    ("c", -0.68, -0.58, 1, (0x2E, 0xAC, 0x4E), "C", WHITE),
    ("d", 0.68, -0.74, 1, (0x34, 0x6C, 0xDC), "D", WHITE),
    ("a", -0.68, 0.74, 1, (0xDC, 0x2C, 0x2C), "A", WHITE),
    ("b", 0.69, 0.58, 1, (0xF0, 0xC0, 0x24), "B", WHITE),
]
NEOGEO_ROLES = {"a": "south", "b": "east", "c": "west", "d": "north"}
N64 = [  # o close de cima: o B do tamanho do A, os C com 0,75
    ("cup", 0.94, -2.41, 0.75, (0xF2, 0xC6, 0x2A), "arrowup", (0x5C, 0x48, 0x10)),
    ("cleft", 0.19, -1.69, 0.75, (0xF2, 0xC6, 0x2A), "arrowleft", (0x5C, 0x48, 0x10)),
    ("cright", 1.73, -1.65, 0.75, (0xF2, 0xC6, 0x2A), "arrowright", (0x5C, 0x48, 0x10)),
    ("cdown", 0.98, -0.94, 0.75, (0xF2, 0xC6, 0x2A), "arrowdown", (0x5C, 0x48, 0x10)),
    ("west", -0.95, -0.98, 0.99, (0x2E, 0x9C, 0x4E), "B", WHITE),
    ("south", 0, 0, 1, (0x34, 0x58, 0xCC), "A", WHITE),
]
# O GameCube (a foto de cima): o A, o B com 0,64 embaixo a esquerda, e os
# feijoes num arco de 1 diametro do A em volta dele, 0,36 de largura: o Y de
# -130 a -82 graus (em cima), o X de -40 a +10 (a direita).
GAMECUBE = [
    ("south", 0, 0, 1, (0x2E, 0xBE, 0x8A), "A", WHITE),
    ("west", -0.96, 0.48, 0.64, (0xE2, 0x3A, 0x44), "B", WHITE),
]
GAMECUBE_BEANS = [("north", "Y", -130, -82), ("east", "X", -40, 10)]


def layout(surf, cx, cy, buttons, extent=None, size=1.0):
    """Desenha a tabela com o conjunto no meio de (cx, cy): cada botao do
    tamanho e no lugar medidos (o principal com o raio R vezes size).
    Devolve {papel: (x, y, raio)} e a escala (pixels por diametro do
    principal)."""
    k = 2 * R * size
    xs = [b[1] for b in buttons] + ([extent[0], extent[2]] if extent else [])
    ys = [b[2] for b in buttons] + ([extent[1], extent[3]] if extent else [])
    ox = cx - round((min(xs) + max(xs)) / 2 * k)
    oy = cy - round((min(ys) + max(ys)) / 2 * k * FLAT)
    pos = {}
    # De tras para a frente: o de cima (mais longe) primeiro.
    for role, x, y, d, color, glyph, ink in sorted(buttons, key=lambda b: b[2]):
        bx, by = ox + round(x * k), oy + round(y * k * FLAT)
        r = max(4, round(d * k / 2))
        button3d(surf, bx, by, r, color)
        if glyph in ("tri", "cir", "cross", "sq") or glyph.startswith("arrow"):
            symbol(surf, bx, by, glyph, ink)
        elif glyph:
            letter(surf, bx, by, glyph, ink, 2 if d >= 0.9 else 1)
        pos[role] = (bx, by, r)
    return pos, (ox, oy, k)


# ── Os controles ────────────────────────────────────────────────────

def playstation(surf, cx, cy):
    """O DualShock: quatro botoes pretos com os simbolos coloridos."""
    return layout(surf, cx, cy, PLAYSTATION)[0]


def xbox(surf, cx, cy):
    """O do Xbox: Y amarelo, B vermelho, A verde e X azul."""
    return layout(surf, cx, cy, XBOX)[0]


def gamecube(surf, cx, cy):
    """O do GameCube: o A verde grande (30% maior que um botao de arcade: ele
    e o botao grande do controle), o B vermelho, o X e o Y em feijao."""
    grey = (0xC4, 0xC4, 0xCE)
    # O arco dos feijoes entra no tamanho do conjunto (o A no meio dele).
    pos, (ox, oy, k) = layout(surf, cx, cy, [], (-1.15, -1.15, 1.15, 0.8), 1.3)
    for role, glyph, start, end in GAMECUBE_BEANS:
        x, y = bean(surf, ox, oy, k, start, end, 0.36 * k, grey)
        letter(surf, x, y, glyph, (0x50, 0x50, 0x5C), 1)
        pos[role] = (x, y, round(0.18 * k))
    for role, x, y, d, color, glyph, ink in GAMECUBE:
        bx, by = ox + round(x * k), oy + round(y * k * FLAT)
        r = round(d * k / 2)
        button3d(surf, bx, by, r, color)
        letter(surf, bx, by, glyph, ink)
        pos[role] = (bx, by, r)
    return pos


def snes(surf, cx, cy):
    """O do Super Nintendo, nas cores do Super Famicom: X azul, A vermelho, B
    amarelo, Y verde (a letra fica no corpo do controle, fora do guia)."""
    return layout(surf, cx, cy, SNES)[0]


def nes(surf, cx, cy):
    """O do NES: B e A vermelhos lado a lado (a letra fica no corpo)."""
    return layout(surf, cx, cy, NES)[0]


def dreamcast(surf, cx, cy):
    """O do Dreamcast: Y verde, B azul, A vermelho e X amarelo, girados."""
    return layout(surf, cx, cy, DREAMCAST)[0]


def saturn(surf, cx, cy):
    """O do Saturn: A B C escuros e grandes, X Y Z claros e menores."""
    return layout(surf, cx, cy, SATURN)[0]


def megadrive(surf, cx, cy):
    """O do Mega Drive de seis botoes: tudo preto, a letra vermelha em cada um."""
    return layout(surf, cx, cy, MEGADRIVE)[0]


def neogeo(surf, cx, cy):
    """O do Neo Geo CD: C e D em cima, A e B embaixo, em colunas."""
    return layout(surf, cx, cy, NEOGEO)[0]


def n64(surf, cx, cy):
    """O do Nintendo 64: A azul, B verde e os quatro C amarelos."""
    return layout(surf, cx, cy, N64)[0]


# O Joypad layout do Frontend controls: (valor, nome na tela, desenho).
PADS = (
    ("playstation", "PLAYSTATION", playstation), ("xbox", "XBOX", xbox), ("gamecube", "GAMECUBE", gamecube),
    ("snes", "SUPER NINTENDO", snes), ("nes", "NES", nes), ("dreamcast", "DREAMCAST", dreamcast),
    ("saturn", "SATURN", saturn), ("megadrive", "MEGA DRIVE", megadrive), ("neogeo", "NEO GEO CD", neogeo),
    ("n64", "NINTENDO 64", n64),
)


# O botao de cada videogame na posicao do controle que o Button mapping
# gravou (sul, leste, oeste, norte, os ombros), como num controle desses
# ligado por USB: o B do NES embaixo e o A a direita; no Mega Drive e no
# Saturn o B no meio embaixo, o A a esquerda, o C a direita, o Y em cima e o
# X e o Z nos ombros; no Nintendo 64 os C de cima e da direita. Os que nao
# estao aqui ja tem o nome da posicao.
SIX = {"a": "west", "b": "south", "c": "east", "x": "l1", "y": "north", "z": "r1"}
ROLES = {"nes": {"west": "south", "south": "east"}, "megadrive": SIX, "saturn": SIX,
         "neogeo": NEOGEO_ROLES, "n64": {"cup": "north", "cright": "east"}}


def draw(surf, kind, cx, cy):
    """Desenha os botoes do joypad KIND com o centro em (cx, cy); devolve
    {posicao no controle: (x, y do topo, raio)} (ROLES; um botao sem posicao,
    como o C de baixo do Nintendo 64, fica com o nome dele)."""
    fn = next((f for value, _, f in PADS if value == kind), playstation)
    roles = ROLES.get(kind if fn is not playstation else "playstation", {})
    return {roles.get(k, k): v for k, v in fn(surf, cx, cy).items()}
