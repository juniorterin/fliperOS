"""O desenho das animacoes de link do site (netplay-anim.py, ssf2tb-anim.py):
gabinetes em pixel art (contorno escuro, sombreado em degraus, lambri roxo e
piso xadrez, como a arte isometrica do site) ligados por cabos de rede, com as
capturas reais por cima das telas. Tudo em pixels da arte (W/PX x H/PX),
ampliado sem suavizar no fim; as telas, os logos e a legenda vao na resolucao
cheia."""
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
    "body": "#353849", "bodyhi": "#4a4e66", "bodylo": "#2c2e3d", "side": "#3d3256", "sidehi": "#54467a",
    "panel": "#4b4f66", "panelhi": "#60657f", "strip": "#3f4257", "bezel": "#101116", "glass": "#0a0a0e",
    "mq1": "#7b4fb0", "mq2": "#9466c9", "mq3": "#ad80dd", "mqp1": "#2a1d48", "mqp2": "#3a2862",
    "metal": "#c8c8d2", "cable": "#6272a4", "cablehi": "#8a9ad0", "door": "#22232d"}.items()}
BALLS = (C["red"], C["cyan"], C["yellow"], C["green"])


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


class Cab:
    """Um gabinete, em pixels da arte: o centro, a meia largura, o topo, o chao,
    a tela (largura, altura) e para que lado aparece a lateral (0: nenhum)."""

    def __init__(self, cx, half, top, floor, scr, side=0, socket="side"):
        self.cx, self.half, self.top, self.floor, self.scr, self.side = cx, half, top, floor, scr, side
        self.x0, self.x1 = cx - half, cx + half - 1
        self.scr_y = top + 22
        self.panel = self.scr_y + scr[1] + 5
        self.label_y = self.panel + 15
        self.socket = socket

    @property
    def edge(self):
        return self.x1 if self.side > 0 else self.x0

    def screen_box(self, px):
        x = (self.cx - self.scr[0] // 2) * px
        return x, self.scr_y * px

    def plug(self, toward):
        """Onde o cabo entra: na lateral (embaixo) ou na frente, no canto do lado do vizinho."""
        if self.socket == "side":
            return self.edge + 4 * self.side, self.floor - 8
        return (self.x1 - 7 if toward > 0 else self.x0 + 7), self.floor - 7


def background(lw, lh, cabs, lit=None, globes=()):
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
        cabinet(d, cab)
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
    """O corpo: a lateral, a frente, o letreiro (vazio), a moldura da tela, o
    painel e a porta das fichas."""
    cx, x0, x1, top, floor, s = cab.cx, cab.x0, cab.x1, cab.top, cab.floor, cab.side
    sw, sh = cab.scr
    panel = cab.panel
    rect(d, (x0 - 3, floor, x1 + 3, floor + 1), C["ink"])     # a sombra no chao
    if s:
        edge = cab.edge
        outer = edge + 7 * s
        rect(d, (min(edge, outer) - 3, floor, max(edge, outer) + 3, floor + 1), C["ink"])
        d.polygon([(edge, top), (outer, top + 3), (outer, floor - 1), (edge, floor - 1)], fill=C["side"], outline=C["ink"])
        d.line([(outer - s, top + 4), (outer - s, floor - 2)], fill=C["pink"])
        d.line([(edge + 2 * s, top + 60), (outer - 2 * s, top + 56)], fill=C["sidehi"])
        d.line([(edge + 2 * s, top + 61), (outer - 2 * s, top + 57)], fill=C["sidehi"])
        d.polygon([(edge, panel), (outer, panel + 1), (outer + 2 * s, panel + 9), (edge + 3 * s, panel + 8)],
                  fill=C["panel"], outline=C["ink"])
        rect(d, (min(edge, outer + 2 * s), panel + 9, max(edge, outer + 2 * s), panel + 13), C["strip"])
    # A frente
    rect(d, (x0, top, x1, floor - 1), C["body"], C["ink"])
    d.line([(x0 + 1, top + 1), (x0 + 1, floor - 2)], fill=C["bodyhi"])
    d.line([(x1 - 1, top + 1), (x1 - 1, floor - 2)], fill=C["bodylo"])
    d.line([(x0 + 1, top + 1), (x1 - 1, top + 1)], fill=C["bodyhi"])
    # O letreiro e a moldura da tela
    rect(d, (x0 + 2, top + 3, x1 - 2, top + 17), C["mq1"], C["ink"])
    rect(d, (x0 + 2, top + 19, x1 - 2, panel - 2), C["bezel"], C["ink"])
    sx0, sx1 = cx - sw // 2, cx + sw // 2 - 1
    rect(d, (sx0 - 2, cab.scr_y - 2, sx1 + 2, cab.scr_y + sh + 1), C["glass"])
    d.line([(sx0 - 2, cab.scr_y + sh + 2), (sx1 + 2, cab.scr_y + sh + 2)], fill=C["line"])
    # O painel de controle: inclinado, sai para a frente
    d.polygon([(x0, panel), (x1, panel), (x1 + 3, panel + 8), (x0 - 3, panel + 8)], fill=C["panel"], outline=C["ink"])
    d.line([(x0 + 1, panel + 1), (x1 - 1, panel + 1)], fill=C["panelhi"])
    rect(d, (x0 - 3, panel + 9, x1 + 3, panel + 13), C["strip"], C["ink"])
    d.line([(x0 - 2, panel + 10), (x1 + 2, panel + 10)], fill=C["pink"])
    # A porta das fichas, perto do chao, e o rodape
    door = floor - 20
    rect(d, (cx - 14, door, cx + 14, floor - 4), C["door"], C["line"])
    for x in (cx - 7, cx + 5):
        rect(d, (x - 1, door + 3, x + 2, door + 10), C["ink"])
        rect(d, (x, door + 4, x + 1, door + 9), C["red"])
    d.line([(cx - 10, door + 13), (cx + 10, door + 13)], fill=C["ink"])
    rect(d, (x0 + 1, floor - 3, x1 - 1, floor - 2), C["bodylo"])
    if s == 0 and door - cab.label_y > 20:        # um gabinete alto: uma faixa na frente
        y = (cab.label_y + 10 + door) // 2
        d.line([(x0 + 2, y), (x1 - 2, y)], fill=C["pink"])
        d.line([(x0 + 2, y + 2), (x1 - 2, y + 2)], fill=C["purple"])


def marquee(d, cab, text, playing, f8):
    """O fundo do letreiro (roxo; escuro quando o jogo roda) e o texto, em
    pixels; devolve a caixa, para o logo do jogo ir por cima em resolucao cheia."""
    box = (cab.x0 + 3, cab.top + 4, cab.x1 - 3, cab.top + 16)
    h = box[3] - box[1] + 1
    bands = (C["mqp1"], C["mqp2"]) if playing else (C["mq1"], C["mq2"], C["mq3"])
    for i, y in enumerate(range(box[1], box[3] + 1)):
        d.line([(box[0], y), (box[2], y)], fill=bands[min(len(bands) - 1, i * len(bands) // h)])
    if not playing and text:
        w = box[2] - box[0] + 1
        tw = int(d.textlength(text, font=f8))
        tx, ty = box[0] + (w - tw) // 2, box[1] + (h - 8) // 2
        d.text((tx + 1, ty + 1), text, font=f8, fill=C["ink"])
        d.text((tx, ty), text, font=f8, fill=C["yellow"])
    return box


def label(d, cab, text, f8):
    d.text((cab.cx - int(d.textlength(text, font=f8)) // 2, cab.label_y), text, font=f8, fill=C["green"])


def controls(d, cab, press, balls):
    """As duas alavancas (balls: a cor de cada uma, ou uma so para as duas) e os
    botoes; a do jogador 1 mexe e o botao acende num aperto."""
    cx, panel = cab.cx, cab.panel
    off = int(cab.half * 0.58)
    if not isinstance(balls[0], tuple):
        balls = (balls, balls)
    for p, jx in enumerate((cx - off, cx + int(cab.half * 0.13))):
        ball = balls[p]
        dx, dy = {"down": (0, 1), "up": (0, -1), "right": (2, 0), "left": (-2, 0)}.get(press, (0, 0)) if p == 0 else (0, 0)
        rect(d, (jx - 3, panel + 4, jx + 3, panel + 5), C["ink"])
        d.line([(jx, panel + 4), (jx + dx // 2, panel + 1 + dy)], fill=C["metal"])
        bx, by = jx + dx, panel - 2 + dy
        rect(d, (bx - 2, by - 1, bx + 2, by + 1), ball)
        rect(d, (bx - 1, by - 2, bx + 1, by + 2), ball)
        d.point((bx - 1, by - 1), fill=C["fg"])
        for i, col in enumerate((C["yellow"], C["green"], C["pink"])):
            x, y = jx + 6 + i * 4, panel + 2 + (i % 2)
            on = p == 0 and i == 0 and press == "a"
            rect(d, (x, y + 1, x + 2, y + 2), C["ink"])
            rect(d, (x, y + (1 if on else 0), x + 2, y + (1 if on else 0) + 1), C["fg"] if on else col)


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


def chain(cabs, sag):
    """Os cabos de um gabinete ao seguinte."""
    return [bezier(cabs[i].plug(1), cabs[i + 1].plug(-1), sag) for i in range(len(cabs) - 1)]


def draw_cables(d, cables, dots):
    """Os cabos e os pulsos: dots = [(cabo, posicao 0..1, cor), ...]."""
    for pts in cables:
        for x, y in pts:
            rect(d, (x - 1, y - 2, x + 1, y + 2), C["ink"])
    for pts in cables:
        for x, y in pts:
            rect(d, (x, y - 1, x, y + 1), C["cable"])
            d.point((x, y - 1), fill=C["cablehi"])
        for x, y in (pts[0], pts[-1]):            # os conectores
            rect(d, (x - 2, y - 3, x + 2, y + 1), C["cyan"], C["ink"])
    for i, p, col in dots:
        pts = cables[i]
        x, y = pts[max(0, min(len(pts) - 1, int(round(p * (len(pts) - 1)))))]
        dim = tuple(int(c * 0.45 + b * 0.55) for c, b in zip(col, C["bg"]))
        rect(d, (x - 2, y - 2, x + 2, y + 2), dim)
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
