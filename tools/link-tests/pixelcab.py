"""O desenho das animacoes de link do site (netplay-anim.py, ssf2tb-anim.py):
gabinetes candy japoneses em pixel art (corpo claro de topo arredondado,
letreiro verde aceso, vidro preto em volta do monitor, painel saliente com
manches vermelhos, porta das fichas e rodape escuro, como a arte isometrica da
home) ligados por cabos de rede, com as capturas reais por cima das telas. Tudo
em pixels da arte (W/PX x H/PX), ampliado sem suavizar no fim; as telas, os
logos e a legenda vao na resolucao cheia."""
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 900
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONT = os.path.join(ROOT, "fliperos-setup", "gui", "fonts", "PressStart2P-Regular.ttf")
CAPTION_H = 110

hexc = lambda h: tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))
C = {k: hexc(v) for k, v in {
    "ink": "#191a21", "deeper": "#14151b", "bg": "#282a36", "line": "#44475a", "comment": "#6272a4",
    "purple": "#bd93f9", "pink": "#ff79c6", "green": "#50fa7b", "cyan": "#8be9fd", "yellow": "#f1fa8c",
    "orange": "#ffb86c", "red": "#ff5555", "fg": "#f8f8f2",
    "wall": "#2b2d3a", "wallline": "#262834", "wain": "#4a3d6b", "wainhi": "#6a5a96", "wainlo": "#3b3157",
    "floora": "#23242f", "floorb": "#1c1d26", "pinkfloor": "#5c2f50",
    # o gabinete candy
    "body": "#d7dae4", "bodyhi": "#f3f4f8", "bodymid": "#bfc3cf", "bodylo": "#9da2b3", "teal": "#2fb3a1",
    "mqg": "#5ae88b", "mqghi": "#aaf7c5", "mqglo": "#3cbf73", "mqtext": "#1d4a2c", "mqp1": "#2a1d48", "mqp2": "#3a2862",
    "panel": "#2b2e3f", "panelhi": "#3d4157", "glass": "#121319", "glasshi": "#2a2c3a", "tube": "#07070a",
    "kick": "#2b2e3f", "kickhi": "#3d4157", "steel": "#9aa0b8", "steello": "#6e7489",
    "metal": "#c8c8d2", "ballhi": "#ffc4c4", "balllo": "#c03a42", "cable": "#7b8fd4"}.items()}

# Uma fonte de 3x5 pixels, a da arte isometrica da home, para as plaquinhas.
FONT3 = {
    "P": ["###", "#.#", "###", "#..", "#.."], "-": ["...", "...", "###", "...", "..."],
    "#": ["#.#", "###", "#.#", "###", "#.#"],
    "0": ["###", "#.#", "#.#", "#.#", "###"], "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"], "3": ["###", "..#", "###", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"], "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"], "7": ["###", "..#", "..#", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"], "9": ["###", "#.#", "###", "..#", "###"],
}


def font(size):
    return ImageFont.truetype(FONT, size)


def at(table, t):
    """O valor da tabela [(inicio, valor), ...] no instante t."""
    cur = table[0][1]
    for start, v in table:
        if t >= start:
            cur = v
    return cur


def rect(d, box, fill, outline=None):
    d.rectangle(box, fill=fill, outline=outline)


def tiny(d, x, y, text, fill):
    """Texto na fonte de 3x5 pixels, a partir do canto (x, y)."""
    for i, ch in enumerate(text):
        for r, row in enumerate(FONT3.get(ch, ())):
            for c, v in enumerate(row):
                if v == "#":
                    d.point((x + i * 4 + c, y + r), fill=fill)


class Cab:
    """Um gabinete de frente, em pixels da arte: o centro, a meia largura, o
    topo, o chao e a tela (largura, altura). cp_out: quanto o painel de controle
    passa do corpo de cada lado (0 para gabinetes encostados um no outro)."""

    def __init__(self, cx, half, top, floor, scr, cp_out=None):
        self.cx, self.half, self.top, self.floor, self.scr = cx, half, top, floor, scr
        self.x0, self.x1 = cx - half, cx + half - 1
        big = half >= 40
        self.rim = 4                               # a borda clara de cada lado do vidro
        self.radius = 9 if big else 7              # o topo arredondado
        self.cp_out = (3 if big else 1) if cp_out is None else cp_out
        self.head = top + 19                       # onde acaba a cabeca (o letreiro) e comeca o vidro
        self.scr_y = top + 22
        self.panel = self.scr_y + scr[1] + 5       # o painel de controle
        self.lower = self.panel + 14               # a parte de baixo
        self.label_y = self.lower + 5

    def screen_box(self, px):
        x = (self.cx - self.scr[0] // 2) * px
        return x, self.scr_y * px

    def plug(self, toward):
        """De onde o cabo sai: de baixo do gabinete, no chao, perto do canto do
        lado do vizinho."""
        return (self.x1 - 8 if toward > 0 else self.x0 + 8), self.floor + 1


def background(lw, lh, cabs, lit=None, globes=(), draw=None):
    """A sala: a parede, o lambri, o piso e os gabinetes (draw = a funcao que
    desenha um; cabinet, o candy, se nada for dito)."""
    floor = cabs[0].floor
    im = Image.new("RGB", (lw, lh), C["wall"])
    d = ImageDraw.Draw(im)
    for x in range(6, lw, 24):                    # as juntas da parede
        d.line([(x, 22), (x, floor - 41)], fill=C["wallline"])
    rect(d, (0, floor - 40, lw, floor - 1), C["wain"])   # o lambri roxo, como na arte do site
    d.line([(0, floor - 40), (lw, floor - 40)], fill=C["wainhi"])
    d.line([(0, floor - 39), (lw, floor - 39)], fill=C["wainhi"])
    for x in range(0, lw, 12):
        d.line([(x, floor - 36), (x, floor - 3)], fill=C["wainlo"])
    rect(d, (0, floor - 2, lw, floor - 1), C["ink"])
    for y in range(floor, lh):                    # o piso em xadrez
        row = (y - floor) // 5
        for x in range(lw):
            im.putpixel((x, y), C["floora"] if ((x + row * 4) // 8 + row) % 2 == 0 else C["floorb"])
    for cab in [] if lit is None else [cabs[lit]]:      # o chao rosa embaixo de quem esta agindo
        for y in range(floor, min(lh, floor + 12)):
            half = cab.half + 7 - (y - floor) * 2
            for x in range(max(0, cab.cx - half), min(lw, cab.cx + half)):
                if (x + y) % 2 == 0 or y < floor + 6:
                    im.putpixel((x, y), C["pinkfloor"])
    for gx, gy in globes:
        globe(d, gx, gy)
    for cab in cabs:
        (draw or cabinet)(d, cab)
    return im


def globe(d, cx, cy, r=9):
    """O globo do link do frontend, em neon, na parede."""
    d.ellipse((cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1), outline=C["wainlo"])
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=C["pink"])
    d.ellipse((cx - r // 2, cy - r, cx + r // 2, cy + r), outline=C["pink"])
    d.line([(cx, cy - r), (cx, cy + r)], fill=C["pink"])
    d.line([(cx - r, cy), (cx + r, cy)], fill=C["pink"])
    d.line([(cx - r + 2, cy - r // 2), (cx + r - 2, cy - r // 2)], fill=C["pink"])
    d.line([(cx - r + 2, cy + r // 2), (cx + r - 2, cy + r // 2)], fill=C["pink"])


def cabinet(d, cab):
    """Um gabinete candy japones, de frente: o corpo claro de topo arredondado,
    o letreiro (aceso a cada quadro por marquee), o vidro preto do monitor, o
    painel de controle saliente, a porta das fichas e o rodape escuro."""
    cx, x0, x1, top, floor = cab.cx, cab.x0, cab.x1, cab.top, cab.floor
    sw, sh = cab.scr
    rim, r, panel, out, lower = cab.rim, cab.radius, cab.panel, cab.cp_out, cab.lower
    ink = C["ink"]
    rect(d, (x0 - 1 - out, floor, x1 + 1 + out, floor + 1), ink)     # a sombra no chao
    # o corpo, com o topo arredondado, o brilho em cima e a esquerda e a sombra a direita
    d.rounded_rectangle((x0, top, x1, floor - 1), radius=r, fill=C["body"], outline=ink,
                        corners=(True, True, False, False))
    d.arc((x0 + 1, top + 1, x0 + 2 * r - 1, top + 2 * r - 1), 180, 270, fill=C["bodyhi"])
    d.line([(x0 + r, top + 1), (x1 - r, top + 1)], fill=C["bodyhi"])
    d.arc((x1 - 2 * r + 1, top + 1, x1 - 1, top + 2 * r - 1), 270, 360, fill=C["bodymid"])
    d.line([(x0 + 1, top + r), (x0 + 1, floor - 7)], fill=C["bodyhi"])
    d.line([(x1 - 1, top + r), (x1 - 1, floor - 7)], fill=C["bodylo"])
    # a moldura do letreiro e a sombra embaixo dele
    d.rounded_rectangle((x0 + rim - 1, top + 3, x1 - rim + 1, top + 17), radius=3, fill=ink)
    d.line([(x0 + rim, top + 18), (x1 - rim, top + 18)], fill=C["bodylo"])
    # o vidro preto do monitor, entre as bordas claras, com um brilho no canto
    rect(d, (x0 + rim, cab.head, x1 - rim, panel - 1), C["glass"])
    d.line([(x0 + rim, cab.head), (x1 - rim, cab.head)], fill=ink)
    d.line([(x0 + rim - 1, cab.head), (x0 + rim - 1, panel - 1)], fill=C["bodylo"])
    d.line([(x1 - rim + 1, cab.head), (x1 - rim + 1, panel - 1)], fill=C["bodymid"])
    sx0, sx1 = cx - sw // 2, cx + sw // 2 - 1
    if sx0 - (x0 + rim) >= 5:                    # o reflexo do vidro, na margem da esquerda
        gx = x0 + rim + 1
        for i, (a, b) in enumerate(((6, 2), (11, 4))):
            d.line([(gx, cab.head + a + 4), (gx + b, cab.head + a + 4 - b)], fill=C["glasshi"])
    rect(d, (sx0 - 1, cab.scr_y - 1, sx1 + 1, cab.scr_y + sh), C["tube"])
    # o painel de controle: o tampo escuro inclinado e a frente clara com o friso verde-agua
    d.polygon([(x0, panel), (x1, panel), (x1 + out, panel + 8), (x0 - out, panel + 8)], fill=C["panel"], outline=ink)
    d.line([(x0 + 1, panel + 1), (x1 - 1, panel + 1)], fill=C["panelhi"])
    rect(d, (x0 - out, panel + 9, x1 + out, panel + 13), C["body"], ink)
    d.line([(x0 - out + 1, panel + 10), (x1 + out - 1, panel + 10)], fill=C["bodyhi"])
    d.line([(x0 - out + 1, panel + 11), (x1 + out - 1, panel + 11)], fill=C["teal"])
    # a parte de baixo: a sombra do painel e a porta
    rect(d, (x0 + 1, lower, x1 - 1, lower + 1), C["bodylo"])
    for x in range(x0 + 1, x1, 2):
        d.point((x, lower + 2), fill=C["bodylo"])
    d.rectangle((x0 + rim, lower + 4, x1 - rim, floor - 8), outline=C["bodymid"])
    # a porta das fichas: as luzes laranja das entradas, as fendas e a devolucao
    dw = 11 if cab.half >= 40 else 10
    dy1 = floor - 9
    dy0 = max(cab.label_y + 12, dy1 - 18)
    rect(d, (cx - dw, dy0, cx + dw, dy1), C["steel"], ink)
    d.rectangle((cx - dw + 2, dy0 + 2, cx + dw - 2, dy1 - 2), outline=C["steello"])
    for x in (cx - 5, cx + 4):
        rect(d, (x - 1, dy0 + 4, x + 1, dy0 + 5), C["orange"])
        rect(d, (x, dy0 + 7, x, dy0 + 10), ink)
    rect(d, (cx - 2, dy1 - 4, cx + 1, dy1 - 3), ink)
    # num gabinete alto, a grade do alto-falante entre a plaquinha e a porta
    gap = dy0 - (cab.label_y + 10)
    if gap > 14:
        gy = cab.label_y + 10 + gap // 2 - 3
        for k in range(4):
            d.line([(cx - 12, gy + k * 2), (cx + 12, gy + k * 2)], fill=C["bodylo"])
    # o rodape
    rect(d, (x0 + 1, floor - 6, x1 - 1, floor - 2), C["kick"])
    d.line([(x0 + 1, floor - 6), (x1 - 1, floor - 6)], fill=C["kickhi"])


def marquee(d, cab, text, playing, f8):
    """O letreiro: verde aceso com o texto (o numero do gabinete), ou escuro
    quando o jogo roda; devolve a caixa, para o logo do jogo ir por cima em
    resolucao cheia."""
    box = (cab.x0 + cab.rim, cab.top + 4, cab.x1 - cab.rim, cab.top + 16)
    x0, y0, x1, y1 = box
    if playing:
        d.rounded_rectangle(box, radius=2, fill=C["mqp1"])
        d.line([(x0 + 2, y0 + 1), (x1 - 2, y0 + 1)], fill=C["mqp2"])
        return box
    d.rounded_rectangle(box, radius=2, fill=C["mqg"])
    d.line([(x0 + 2, y0 + 1), (x1 - 2, y0 + 1)], fill=C["mqghi"])
    d.line([(x0 + 1, y0 + 2), (x1 - 1, y0 + 2)], fill=C["mqghi"])
    d.line([(x0 + 2, y1 - 1), (x1 - 2, y1 - 1)], fill=C["mqglo"])
    if text:
        tw = int(d.textlength(text, font=f8))
        d.text((x0 + (x1 - x0 + 1 - tw) // 2, y0 + 3), text, font=f8, fill=C["mqtext"])
    return box


def label(d, cab, text, f8=None):
    """A plaquinha embaixo do painel com os jogadores do gabinete (P1-2...)."""
    tw = len(text) * 4 - 1
    x = cab.cx - tw // 2
    rect(d, (x - 3, cab.label_y, x + tw + 2, cab.label_y + 8), C["ink"])
    tiny(d, x, cab.label_y + 2, text, C["green"])


def controls(d, cab, press, balls=None):
    """Os dois jogadores do gabinete: cada um com um manche vermelho classico a
    esquerda e tres botoes em fila a direita dele. O manche do jogador 1 mexe e
    o primeiro botao dele acende num aperto."""
    panel = cab.panel
    for p, (a, b) in enumerate(((cab.x0, cab.cx - 1), (cab.cx, cab.x1))):
        bx = a + (b - a + 1 - 22) // 2
        jx = bx + 2
        dx, dy = {"down": (0, 1), "up": (0, -1), "right": (2, 0), "left": (-2, 0)}.get(press, (0, 0)) if p == 0 else (0, 0)
        rect(d, (jx - 2, panel + 4, jx + 2, panel + 6), C["ink"])                  # a base
        d.line([(jx, panel + 4), (jx + dx // 2, panel - 1 + dy)], fill=C["metal"])  # a haste
        ox, oy = jx + dx, panel - 3 + dy
        d.ellipse((ox - 2, oy - 2, ox + 2, oy + 2), fill=C["red"])                 # a bola
        d.point((ox - 1, oy - 1), fill=C["ballhi"])
        d.point((ox + 1, oy + 1), fill=C["balllo"])
        for i, col in enumerate((C["yellow"], C["green"], C["pink"])):
            x, y = bx + 8 + i * 5, panel + 3
            on = p == 0 and i == 0 and press == "a"
            rect(d, (x, y + 1, x + 3, y + 3), C["ink"])
            cy = y + (1 if on else 0)
            rect(d, (x, cy, x + 3, cy + 1), C["fg"] if on else col)
            d.point((x, cy), fill=C["panel"])        # os cantos de cima, para o botao ficar redondo
            d.point((x + 3, cy), fill=C["panel"])


RACE = {k: hexc(v) for k, v in {
    "red": "#e03a44", "redhi": "#ff6670", "redlo": "#a8222c", "dome": "#b22a35", "domehi": "#cf3b46",
    "domelo": "#7e1a24", "blk": "#23242f", "blkhi": "#3a3c4c", "tire": "#1d1e27", "tirehi": "#34364a",
    "lit": "#ffb347", "lithi": "#ffd28a", "litlo": "#d98a2b"}.items()}


class RaceCab:
    """Um gabinete de corrida em forma de Formula 1, como os da sala RACE LINK
    da home: a cupula vermelha do monitor com o letreiro aceso em cima (a
    bandeira quadriculada e o numero do carro) e o carro na frente dela, visto
    de tras e um pouco de cima, como a camera de um jogo de corrida: a asa de
    tras e os pneus grandes embaixo, o cockpit com o volante e o bico subindo
    ate a tela. Em pixels da arte: o centro, a meia largura, o topo, o chao, a
    tela (largura, altura) e o numero do carro."""

    def __init__(self, cx, half, top, floor, scr, n):
        self.cx, self.half, self.top, self.floor, self.scr, self.n = cx, half, top, floor, scr, n
        self.x0, self.x1 = cx - half, cx + half - 1
        self.dome = top + 14                       # a cupula comeca embaixo do letreiro
        self.scr_y = self.dome + 6
        self.dash = self.scr_y + scr[1] + 2        # o painel embaixo da tela
        self.car = self.dash + 11                  # a asa da frente
        self.label_y = floor - 16

    def screen_box(self, px):
        return (self.cx - self.scr[0] // 2) * px, self.scr_y * px

    def plug(self, toward):
        return (self.x1 - 6 if toward > 0 else self.x0 + 6), self.floor + 1


def racer(d, cab):
    """O gabinete de corrida parado (o fundo de cada quadro): a cupula, a tela
    apagada, o painel e o carro. O letreiro, os botoes, o volante, os pneus
    rodando e a luz de tras sao de race_live, a cada quadro."""
    cx, x0, x1, floor = cab.cx, cab.x0, cab.x1, cab.floor
    sw, sh = cab.scr
    ink, blk = C["ink"], RACE["blk"]
    red, redhi, redlo = RACE["red"], RACE["redhi"], RACE["redlo"]
    rect(d, (x0 - 1, floor, x1 + 1, floor + 1), ink)                     # a sombra no chao
    # a cupula do monitor, de cantos redondos, com a pala por cima; embaixo do
    # painel ela fica na sombra do carro
    d.rounded_rectangle((x0, cab.dome, x1, floor - 6), radius=6, fill=RACE["dome"], outline=ink,
                        corners=(True, True, False, False))
    d.line([(x0 + 4, cab.dome + 1), (x1 - 4, cab.dome + 1)], fill=RACE["domehi"])
    d.line([(x0 + 1, cab.dome + 5), (x0 + 1, cab.dash)], fill=RACE["domehi"])
    d.line([(x1 - 1, cab.dome + 5), (x1 - 1, cab.dash)], fill=RACE["domelo"])
    d.line([(x0 + 1, cab.dome + 3), (x1 - 1, cab.dome + 3)], fill=RACE["domelo"])
    rect(d, (x0 + 1, cab.dash + 5, x1 - 1, floor - 7), RACE["domelo"])
    for x in (x0 + 5, x1 - 5):                                           # as juntas da frente
        d.line([(x, cab.dash + 7), (x, floor - 8)], fill=RACE["dome"])
    # o vidro preto em volta da tela
    sx0, sx1 = cx - sw // 2, cx + sw // 2 - 1
    rect(d, (sx0 - 2, cab.scr_y - 2, sx1 + 2, cab.scr_y + sh + 1), blk, ink)
    rect(d, (sx0 - 1, cab.scr_y - 1, sx1 + 1, cab.scr_y + sh), C["tube"])
    # o painel embaixo da tela: as faixas branca e amarela (os botoes VR sao de race_live)
    dash = cab.dash
    for k, col in enumerate((C["fg"], C["fg"], C["yellow"], ink)):
        d.line([(x0 + 1, dash + 1 + k), (x1 - 1, dash + 1 + k)], fill=col)
    # o carro, de longe para perto: a asa da frente, os pneus da frente e o bico
    y = cab.car
    rect(d, (cx - 21, y, cx + 20, y + 2), red, ink)
    d.line([(cx - 20, y), (cx + 19, y)], fill=C["fg"])
    for a in (cx - 23, cx + 21):
        rect(d, (a, y - 1, a + 2, y + 3), blk, ink)
    for a in (cx - 19, cx + 12):
        d.rounded_rectangle((a, y + 2, a + 7, y + 11), radius=1, fill=RACE["tire"], outline=ink)
        d.line([(a + 2, y + 3), (a + 5, y + 3)], fill=RACE["tirehi"])
    d.polygon([(cx - 2, y - 1), (cx + 1, y - 1), (cx + 3, y + 8), (cx - 4, y + 8)], fill=red, outline=ink)
    # os sidepods, dos lados do cockpit
    for a, b in ((cx - 18, cx - 7), (cx + 6, cx + 17)):
        d.rounded_rectangle((a, y + 12, b, y + 30), radius=2, fill=red, outline=ink)
        d.line([(a + 1, y + 13), (b - 1, y + 13)], fill=C["fg"])
        d.line([(a + 1, y + 14), (b - 1, y + 14)], fill=redhi)
        rect(d, (a + 2, y + 16, b - 2, y + 17), ink)                      # a boca do sidepod
    # o monocoque com o cockpit aberto: o volante (race_live) e o banco azul
    d.polygon([(cx - 4, y + 8), (cx + 3, y + 8), (cx + 6, y + 26), (cx - 7, y + 26)], fill=red, outline=ink)
    d.line([(cx - 3, y + 9), (cx - 5, y + 25)], fill=redhi)
    rect(d, (cx - 4, y + 9, cx + 3, y + 17), blk)
    rect(d, (cx - 3, y + 15, cx + 2, y + 17), C["comment"])
    d.line([(cx - 3, y + 15), (cx + 2, y + 15)], fill=C["purple"])
    # a tomada de ar atras da cabeca
    rect(d, (cx - 3, y + 17, cx + 2, y + 25), red, ink)
    rect(d, (cx - 2, y + 18, cx + 1, y + 19), blk)
    d.line([(cx - 2, y + 20), (cx - 2, y + 24)], fill=redhi)
    # a asa de tras, larga, com as placas nas pontas e o pilar
    yw = y + 24
    rect(d, (cx - 1, yw + 7, cx, yw + 10), blk)
    rect(d, (cx - 21, yw, cx + 20, yw + 2), red, ink)                    # a aba de cima
    d.line([(cx - 20, yw), (cx + 19, yw)], fill=C["fg"])
    rect(d, (cx - 21, yw + 4, cx + 20, yw + 7), red, ink)                # o plano principal
    d.line([(cx - 20, yw + 5), (cx + 19, yw + 5)], fill=redhi)
    for a in (cx - 24, cx + 21):
        rect(d, (a, yw - 3, a + 3, yw + 11), redlo, ink)
        d.line([(a + 1, yw - 2), (a + 1, yw + 10)], fill=red)
    # o difusor entre os pneus de tras (a luz de chuva e de race_live)
    rect(d, (cx - 20, yw + 11, cx + 19, floor - 7), blk, ink)
    for x in range(cx - 16, cx + 17, 4):
        if abs(x - cx) > 8:
            d.line([(x, yw + 13), (x, floor - 8)], fill=RACE["blkhi"])
    # a base preta do gabinete, no chao
    rect(d, (x0 + 1, floor - 6, x1 - 1, floor - 1), blk, ink)
    d.line([(x0 + 2, floor - 5), (x1 - 2, floor - 5)], fill=RACE["blkhi"])
    race_live(d, cab)


def race_live(d, cab, playing=False, text=None, f8=None, press=None, roll=0, light=False):
    """O que muda no gabinete de corrida: o letreiro aceso (a bandeira
    quadriculada dos dois lados, o numero no meio, ou o meio escuro para o logo
    do jogo: devolve a caixa dele), um botao VR aceso a cada aperto, o volante
    (vira num aperto para o lado), os pneus de tras rodando (roll) e a luz de
    chuva acesa (light)."""
    cx, x0, x1, top = cab.cx, cab.x0, cab.x1, cab.top
    ink = C["ink"]
    box = (x0 + 3, top, x1 - 3, top + 13)
    d.rounded_rectangle(box, radius=2, fill=RACE["lit"], outline=ink)
    d.line([(box[0] + 2, top + 1), (box[2] - 2, top + 1)], fill=RACE["lithi"])
    d.line([(box[0] + 2, top + 12), (box[2] - 2, top + 12)], fill=RACE["litlo"])
    for fx in (box[0] + 2, box[2] - 11):                                 # as bandeiras quadriculadas
        for i in range(5):
            for j in range(5):
                rect(d, (fx + i * 2, top + 2 + j * 2, fx + i * 2 + 1, top + 3 + j * 2),
                     C["fg"] if (i + j) % 2 else ink)
    mid = (box[0] + 13, top + 2, box[2] - 13, top + 11)
    if playing:
        rect(d, mid, C["mqp1"])
        d.line([(mid[0], mid[1]), (mid[2], mid[1])], fill=C["mqp2"])
    elif text and f8:
        tw = int(d.textlength(text, font=f8))
        d.text((cx - tw // 2 + 1, top + 4), text, font=f8, fill=RACE["litlo"])
        d.text((cx - tw // 2, top + 3), text, font=f8, fill=RACE["redlo"])
    # os botoes VR no painel: vermelho, azul, amarelo, verde
    vr = {"a": 0, "down": 1, "up": 2, "right": 3, "left": 3}.get(press)
    for i, col in enumerate((C["red"], C["cyan"], C["yellow"], C["green"])):
        x = cx - 13 + i * 7
        on = i == vr
        rect(d, (x, cab.dash + 6, x + 4, cab.dash + 8), ink)
        rect(d, (x + 1, cab.dash + 6 + (1 if on else 0), x + 3, cab.dash + 7), C["fg"] if on else col)
    # o volante no cockpit, de tras: o aro e o braco, girando num aperto
    y = cab.car + 9
    turn = {"left": -1, "right": 1}.get(press, 0)
    rect(d, (cx - 4, y, cx + 3, y + 5), RACE["blk"])
    d.ellipse((cx - 3, y, cx + 2, y + 5), outline=C["steel"])
    d.line([(cx - 2, y + 3 + turn), (cx + 1, y + 3 - turn)], fill=C["steel"])
    # os pneus de tras: pretos, com os sulcos descendo quando o carro anda
    yt, yb = cab.car + 27, cab.floor - 3
    for a in (cx - 35, cx + 22):
        d.rounded_rectangle((a, yt, a + 12, yb), radius=3, fill=RACE["tire"], outline=ink)
        d.line([(a + 3, yt + 1), (a + 9, yt + 1)], fill=C["bodylo"])
        d.line([(a + 1, yt + 3), (a + 1, yb - 3)], fill=RACE["tirehi"])
        for k in range(yt + 3 + roll % 4, yb - 2, 4):
            d.line([(a + 3, k), (a + 9, k)], fill=RACE["tirehi"])
    yl = cab.car + 37
    rect(d, (cx - 2, yl, cx + 1, yl + 2), C["red"] if light else RACE["redlo"])
    if light:
        d.point((cx - 1, yl), fill=C["ballhi"])
    return mid


def bezier(a, b, sag):
    """Um cabo pendurado entre dois pontos, em pixels inteiros, sem repetir."""
    c1, c2 = (a[0] + (b[0] - a[0]) * 0.1, sag), (b[0] - (b[0] - a[0]) * 0.1, sag)
    out = []
    for i in range(301):
        u = i / 300
        x = (1 - u) ** 3 * a[0] + 3 * (1 - u) ** 2 * u * c1[0] + 3 * (1 - u) * u ** 2 * c2[0] + u ** 3 * b[0]
        y = (1 - u) ** 3 * a[1] + 3 * (1 - u) ** 2 * u * c1[1] + 3 * (1 - u) * u ** 2 * c2[1] + u ** 3 * b[1]
        p = (round(x), round(y))
        if not out or out[-1] != p:
            out.append(p)
    return out


def chain(cabs):
    """Os cabos de um gabinete ao seguinte, deitados no chao: saem de baixo de
    um e chegam embaixo do outro numa curva rasa, um pouco para a frente."""
    return [bezier(cabs[i].plug(1), cabs[i + 1].plug(-1), cabs[i].floor + 6) for i in range(len(cabs) - 1)]


def draw_cables(d, cables, dots):
    """Os cabos (um pixel azul com o contorno escuro) e os pulsos que andam
    neles: dots = [(cabo, posicao 0..1, cor), ...]."""
    for pts in cables:
        for x, y in pts:
            rect(d, (x - 1, y - 1, x + 1, y + 1), C["ink"])
    for pts in cables:
        for x, y in pts:
            d.point((x, y), fill=C["cable"])
    for i, p, col in dots:
        pts = cables[i]
        x, y = pts[max(0, min(len(pts) - 1, int(round(p * (len(pts) - 1)))))]
        rect(d, (x - 1, y - 1, x + 1, y + 1), col)
        d.point((x, y), fill=C["fg"])


def trip(t, start, src, dst, color, per=0.45):
    """Um pulso que sai do gabinete src em start e anda pelos cabos ate dst
    (per segundos por cabo): a lista com o ponto onde ele esta agora."""
    if t < start or src == dst:
        return []
    step = 1 if dst > src else -1
    hops = list(range(src, dst, step))            # cabo i liga o gabinete i ao i+1
    k = int((t - start) // per)
    if k >= len(hops):
        return []
    p = ((t - start) - k * per) / per
    cable = hops[k] if step > 0 else hops[k] - 1
    return [(cable, p if step > 0 else 1 - p, color)]


def crt(im, size):
    """A imagem no tubo: o tamanho da tela e as linhas."""
    im = im.resize(size, Image.LANCZOS)
    lines = Image.new("L", size, 0)
    d = ImageDraw.Draw(lines)
    for y in range(0, size[1], 3):
        d.line([(0, y), (size[0], y)], fill=60)
    return Image.composite(Image.new("RGB", size, (0, 0, 0)), im, lines)


def screen_mask(scr, px):
    """Os cantos da tela em degraus de pixel, como o resto da arte."""
    m = Image.new("L", scr, 255)
    for x, y in ((0, 0), (1, 0), (0, 1)):
        for cx, cy in ((x, y), (scr[0] - 1 - x, y), (x, scr[1] - 1 - y), (scr[0] - 1 - x, scr[1] - 1 - y)):
            m.putpixel((cx, cy), 0)
    return m.resize((scr[0] * px, scr[1] * px), Image.NEAREST)


def paste_logo(im, logo, box, px):
    """O logo do jogo no letreiro, em resolucao cheia (e arte do jogo, como as telas)."""
    x0, y0, x1, y1 = (v * px for v in box)
    x1 += px
    y1 += px
    lg = logo.copy()
    lg.thumbnail((x1 - x0 - 2 * px, y1 - y0 - px), Image.LANCZOS)
    im.paste(lg, (x0 + (x1 - x0 - lg.width) // 2, y0 + (y1 - y0 - lg.height) // 2), lg)


def caption(im, text, k, total, f_cap, f_num):
    d = ImageDraw.Draw(im)
    d.fontmode = "1"
    d.rectangle((0, 0, W, CAPTION_H - 1), fill=C["ink"])
    d.rectangle((0, CAPTION_H - 5, W, CAPTION_H - 1), fill=C["purple"])
    # O numero do passo (um quadrado de pixels) e os pontinhos
    d.rectangle((45, 30, 90, 75), fill=C["pink"])
    d.rectangle((40, 35, 95, 70), fill=C["pink"])
    n = str(k + 1)
    nw = d.textlength(n, font=f_num)
    d.text((68 - nw // 2, 41), n, font=f_num, fill=C["ink"])
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        test = (cur + " " + w_).strip()
        if d.textlength(test, font=f_cap) > W - 160:
            lines.append(cur)
            cur = w_
        else:
            cur = test
    lines.append(cur)
    y = 41 if len(lines) == 1 else 23
    for line in lines:
        d.text((120, y), line, font=f_cap, fill=C["fg"])
        y += 36
    for i in range(total):
        x = W - 35 - (total - 1 - i) * 20
        d.rectangle((x, 85, x + 9, 94), fill=C["pink"] if i == k else C["line"])


def encode(src, webp, gif, fps):
    """Os quadros (src = padrao %04d.png) em WebP animado e GIF. WEBP_QUALITY
    (80) baixa o peso de uma animacao longa."""
    quality = os.environ.get("WEBP_QUALITY", "80")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", src, "-c:v", "libwebp_anim",
                    "-lossless", "0", "-quality", quality, "-compression_level", "6", "-loop", "0", webp], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(fps), "-i", src, "-vf",
                    "split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
                    "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
                    "-loop", "0", gif], check=True)
