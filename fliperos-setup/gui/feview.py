# O desenho do frontend do FliperOS (gui/fliperos-frontend): os tres modos
# (lista, tela cheia, grade) e o que fica por cima deles (o guia dos
# controles, o menu do jogo, a pagina "+", os filtros, as categorias, o menu
# do Tab, o Classify, o Rename e a pergunta de sair). draw(fe, agora) desenha
# em fe.back, a tela logica de 320x240.

import contextlib
import math
import os
import re
import time

import pygame

import theme as T
import tiny
import widgets as W

SX, SW = T.SAFE_X, T.SAFE_W
WW, HH = T.WIDTH, T.HEIGHT


# ── Imagens ────────────────────────────────────────────────────────

LIST_W, LIST_SH = 174, 74  # a lista do modo lista e a altura da imagem dela
THUMB = (56, 42)           # as miniaturas da tela cheia
GRID_COLS = 3              # a grade (o COLS do fliperos-frontend)
PRELOAD_ROWS = 3           # fileiras da grade com o video pronto, antes e depois


def grid_geom(fe):
    """(miniatura, a escolhida, fileiras, espaco): 4:3, ou 3:4 com o
    monitor em pe (orientation=vertical-* no fliperos.conf)."""
    if getattr(fe, "vertical", False):
        return (54, 72), (72, 96), (3 if T.VERTICAL else 2), 14
    return (80, 60), (112, 84), 2, 10
SLIDE = 0.3                # segundos da troca de romlist
CACHE = 400              # imagens e caminhos guardados (os mais antigos saem)


def remember(fe, key, value):
    fe.media[key] = value
    while len(fe.media) > CACHE:
        del fe.media[next(iter(fe.media))]
    return value


def media(fe, game, kind):
    """O arquivo de midia do jogo (fedata), guardado: procurar no disco a
    cada quadro deixava a troca de jogo lenta."""
    key = ("path", kind, game["_system"]["key"], game["Name"])
    if key in fe.media:
        return fe.media[key]
    return remember(fe, key, fe.lib.media(game, kind))


def load(path, w, h, how):
    """O arquivo lido e ajustado a w x h (fit: inteira; cover: cortada
    para encher); serve tambem a thread que adianta os proximos jogos."""
    try:
        img = pygame.image.load(path)
    except (pygame.error, OSError):
        return None
    iw, ih = img.get_size()
    k = (max if how == "cover" else min)(w / iw, h / ih)
    size = (max(1, round(iw * k)), max(1, round(ih * k)))
    try:                       # (a PNG de paleta nao suaviza: fica o simples)
        img = pygame.transform.smoothscale(img, size)
    except ValueError:
        img = pygame.transform.scale(img, size)
    if how == "cover":
        x, y = (size[0] - w) // 2, (size[1] - h) // 2
        img = img.subsurface((max(0, x), max(0, y), min(w, size[0]), min(h, size[1]))).copy()
    return img


def image(fe, path, w, h, how="fit"):
    """A imagem do arquivo ajustada a w x h, guardada para os proximos
    quadros. A que a thread de adiantar ja leu (fe.ready) so e convertida."""
    if not path:
        return None
    key = (path, w, h, how)
    if key in fe.media:
        img = fe.media.pop(key)
        fe.media[key] = img
        return img
    img = fe.ready.pop(key, None) if key in fe.ready else load(path, w, h, how)
    if img is not None and pygame.display.get_surface():
        img = img.convert_alpha()
    return remember(fe, key, img)


def wanted(fe, game):
    """As imagens que o modo de agora desenha para o jogo (caminho, w, h,
    modo): o que a thread de adiantar le antes do cursor chegar nele."""
    out = []
    shot = media(fe, game, "snap") or media(fe, game, "box")
    cover = media(fe, game, "box") or media(fe, game, "snap")
    logo = media(fe, game, "logo")
    if fe.mode == "list":
        _, (_, _, pw, ph) = list_geom()
        out += [(shot, pw - 4, ph - 4, "cover"), (logo, min(pw - 8, 200), 28, "fit")]
    elif fe.mode == "full":
        right = SX + SW - THUMB[0] - 8
        out += [(shot, WW, HH, "cover"), (shot, THUMB[0] - 2, THUMB[1] - 2, "cover"),
                (logo, min(200, right - SX), 44, "fit")]
    else:
        snap = media(fe, game, "snap")
        tile, big, _, _ = grid_geom(fe)
        for (w, h), pad in ((tile, 2),):
            out.append((snap, w - pad, h - pad, "cover") if snap else (cover, w - pad, h - pad, "fit"))
        out.append((logo, 110, 30, "fit"))
    return [k for k in out if k[0]]


def ease(fe, name, target, now, speed=16.0, reach=6):
    """O valor que corre ate target (a rolagem animada); de longe (um salto
    de pagina, de letra) ele comeca a reach do destino."""
    v, last = fe.anim.get(name, (target, now))
    if fe.shot:                # os prints do --shot: ja no lugar
        v = target
    if abs(target - v) > reach:
        v = target - reach if target > v else target + reach
    v += (target - v) * min(1.0, max(0.0, now - last) * speed)
    if abs(target - v) < 0.01:
        v = target
    fe.anim[name] = (v, now)
    return v


def spring(fe, name, target, now, omega=16.0):
    """Como ease, mas com velocidade: uma mola sem balanco (a solucao exata,
    igual em qualquer taxa de quadros). Sai devagar, acelera e para devagar
    no destino, sem passar dele, tambem quando o destino muda no meio."""
    x, v, last = fe.anim.get(name, (target, 0.0, now))
    if fe.shot:
        x, v = target, 0.0
    t = min(0.1, max(0.0, now - last))
    e = x - target
    k = math.exp(-omega * t)
    e, v = (e + (v + omega * e) * t) * k, (v - omega * (v + omega * e) * t) * k
    if abs(e) < 0.002 and abs(v) < 0.02:
        e, v = 0.0, 0.0
    fe.anim[name] = (target + e, v, now)
    return target + e


def video_frame(fe, game, w, h):
    """O quadro de agora do video do jogo em w x h (fevideo.py), ou None:
    sem video, sem o ffmpeg, ou enquanto o primeiro quadro nao chega (a
    imagem fica no lugar)."""
    if not getattr(fe, "video_ok", False):
        return None
    key = ("video", game["_system"]["key"], game["Name"])
    if key not in fe.media:
        fe.media[key] = fe.lib.video(game)
    fe.video_used = True
    frame = fe.player.request(fe.media[key], w, h, fe.abs_now)
    if not frame:
        return None
    return pygame.image.frombuffer(frame, (w, h), "RGB")


def picture(fe, game, w, h):
    """O video do jogo e, sem ele, a imagem (a tela, ou a capa)."""
    return video_frame(fe, game, w, h) or image(
        fe, media(fe, game, "snap") or media(fe, game, "box"), w, h, "cover")


def blit_center(surf, img, x, y, w, h):
    if img:
        surf.blit(img, (x + (w - img.get_width()) // 2, y + (h - img.get_height()) // 2))


def tile_frame(surf, rect, on, now):
    x, y, w, h = rect
    W.block(surf, rect, T.BG_DEEP, T.PURPLE if on else None)
    if on:
        W.glow(surf, (x + 2, y + 2, w - 4, h - 4), {"now": now})


def fit(s, w):
    s = s.upper()
    while s and W.width(s) > w:
        s = s[:-1]
    return s


# ── Icones ─────────────────────────────────────────────────────────

def arrow(surf, cx, cy, d, color, size=6):
    dx, dy = d
    pts = [(cx + dx * size, cy + dy * size), (cx - dy * size - dx * 2, cy + dx * size - dy * 2),
           (cx + dy * size - dx * 2, cy - dx * size - dy * 2)]
    pygame.draw.polygon(surf, color, pts)


def star(surf, cx, cy, color, r=7, outline=False):
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    pygame.draw.polygon(surf, color, pts, 1 if outline else 0)


def play_icon(surf, cx, cy, c):
    pygame.draw.polygon(surf, c, [(cx - 7, cy - 10), (cx - 7, cy + 10), (cx + 10, cy)])


def plus_icon(surf, cx, cy, c):
    surf.fill(c, (cx - 2, cy - 10, 5, 21))
    surf.fill(c, (cx - 10, cy - 2, 21, 5))


# O link: um globo de linhas verdes (apagado quando ninguem joga o jogo em
# outro gabinete, aceso, com tres nos brancos, quando alguem joga) e os
# gabinetes do link, acesos os que estao nele.
GREEN_DIM, GREEN_MID = (0x2E, 0x5E, 0x40), (0x3C, 0xB0, 0x5C)


_globes = {}
# O globo pequeno (a lista, r ate 6), pixel a pixel: o contorno, o equador e
# um meridiano em lente. Reduzido, o desenho grande vira um borrao.
GLOBE_SMALL = ("...#####...",
               ".##..#..##.",
               ".#..#.#..#.",
               "#..#...#..#",
               "#..#...#..#",
               "###########",
               "#..#...#..#",
               "#..#...#..#",
               ".#..#.#..#.",
               ".##..#..##.",
               "...#####...")


def globe_small(c, lit):
    img = pygame.Surface((11, 11), pygame.SRCALPHA)
    if lit:
        pygame.draw.circle(img, (*c[:3], 70), (5, 5), 5)
    for y, line in enumerate(GLOBE_SMALL):
        for x, ch in enumerate(line):
            if ch == "#":
                img.set_at((x, y), c)
    return img


def globe_icon(surf, cx, cy, r, lit, unlit=None):
    """O globo do link: pequeno, o desenho a mao (GLOBE_SMALL); grande,
    desenhado 4 vezes maior e reduzido com suavizacao (linhas finas, sem
    degraus), com duas latitudes. Aceso, o fundo um pouco cheio."""
    c = T.GREEN if lit else (unlit or GREEN_DIM)
    key = (r, tuple(c), bool(lit))
    img = _globes.get(key)
    if img is None and r <= 6:
        img = _globes[key] = globe_small(c, lit)
    if img is None:
        k, size = 4, 2 * r + 1
        big = pygame.Surface((size * k, size * k), pygame.SRCALPHA)
        o, R, w = size * k / 2, r * k + k / 2 - 1, k
        if lit:
            pygame.draw.circle(big, (*c[:3], 60), (o, o), R)
        pygame.draw.circle(big, c, (o, o), R, w)
        mw = R * (0.55 if r < 8 else 0.5)
        pygame.draw.ellipse(big, c, (o - mw, o - R, 2 * mw, 2 * R), w)
        pygame.draw.line(big, c, (o - R, o), (o + R, o), w)
        if r >= 8:
            pygame.draw.line(big, c, (o, o - R), (o, o + R), w)
            for dy in (-0.5, 0.5):
                half = R * 0.84
                pygame.draw.line(big, c, (o - half, o + dy * R), (o + half, o + dy * R), w)
        img = _globes[key] = pygame.transform.smoothscale(big, (size, size))
    surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))


def link_mark(fe, g):
    """None: o jogo nao tem link. False: tem, e ninguem joga. True: alguem joga."""
    f = getattr(fe, "link_mark", None)
    return f(g) if f and g else None


def link_kind(fe, g):
    """"link" (o jogo liga gabinetes), "net" (net play: mais jogadores do que controles) ou None."""
    f = getattr(fe, "link_kind", None)
    return f(g) if f and g else None


def link_party(fe, g):
    f = getattr(fe, "link_party", None)
    return f(g) if f and g else None


def link_badge(fe, ui, g, x, y, w, h):
    """A marca do link no canto da miniatura (a grade e a tela cheia): o globo
    e, se alguem joga o jogo, os gabinetes da festa na beirada de baixo."""
    lit = link_mark(fe, g)
    if lit is None:
        return
    ui.fill((0x10, 0x12, 0x18), (x, y, 13, 13))
    if link_kind(fe, g) == "net":
        pads_icon(ui, x + 6, y + 6, lit, small=True)
    else:
        globe_icon(ui, x + 6, y + 6, 5, lit)
    party = link_party(fe, g) if lit else None
    if party and h >= 30:
        ui.fill((0x10, 0x12, 0x18), (x, y + h - 11, w, 11))
        cabinet_row(ui, x + 3, y + h - 9, party["used"], party["max"] or 1, w=5, h=7, gap=1)


def cabinet_icon(surf, x, y, w, h, lit):
    """Um gabinetezinho: a tela e o painel (aceso: verde e ciano)."""
    c = T.GREEN if lit else T.LINE
    pygame.draw.rect(surf, c, (x, y, w, h), 1)
    surf.fill(T.CYAN if lit else T.BG_DEEP, (x + 1, y + 1, w - 2, h // 2 - 1))
    pygame.draw.line(surf, c, (x + 1, y + h // 2 + 1), (x + w - 2, y + h // 2 + 1))
    surf.fill(c, (x + w // 2, y + h // 2 + 3, 1, 1))


def cabinet_row(surf, x, y, filled, total, you=None, w=5, h=8, gap=1):
    """Os gabinetes de um link, da esquerda: `filled` acesos, o resto apagado;
    `you` (de 0) leva o aro rosa: o lugar deste gabinete. Devolve onde acaba."""
    for i in range(total):
        cabinet_icon(surf, x + i * (w + gap), y, w, h, i < filled)
    if you is not None:
        pygame.draw.rect(surf, T.PINK, (x + you * (w + gap) - 2, y - 2, w + 4, h + 4), 1)
    return x + total * (w + gap) - gap


def person_icon(surf, x, y, lit, color=None):
    """Um jogador (10x12): a cabeca e os ombros; aceso, verde."""
    c = color or (T.GREEN if lit else T.LINE)
    pygame.draw.circle(surf, c, (x + 5, y + 3), 3)
    surf.fill(c, (x + 1, y + 7, 9, 5))


def slots_row(surf, x, y, used, total, ring=None, step=14):
    """Os jogadores de um jogo de net play: `used` acesos (os ja ocupados) e o
    resto apagado; ring = (primeiro, quantos), de 1, leva o aro rosa: os
    lugares deste gabinete (um por controle). Devolve onde acaba."""
    for i in range(total):
        person_icon(surf, x + i * step, y, i < used)
    if ring:
        first, take = ring
        # 2 pixels livres dos quatro lados (o boneco ocupa x+1..x+9, y..y+11).
        pygame.draw.rect(surf, T.PINK, (x + (first - 1) * step - 2, y - 3, (take - 1) * step + 15, 18), 1)
    return x + total * step - (step - 10)


def pads_icon(surf, cx, cy, lit=True, small=False):
    """O net play: dois controles ligados por uma linha (small: o da lista)."""
    c = T.CYAN if lit else T.LINE
    link = T.GREEN if lit else GREEN_DIM
    if small:
        pygame.draw.rect(surf, c, (cx - 5, cy + 1, 5, 4), 1)
        pygame.draw.rect(surf, c, (cx, cy - 4, 5, 4), 1)
        pygame.draw.lines(surf, link, False, [(cx - 3, cy), (cx - 3, cy - 1), (cx + 1, cy - 1)])
        return
    pygame.draw.rect(surf, c, (cx - 9, cy + 1, 8, 6), 1)
    pygame.draw.rect(surf, c, (cx + 1, cy - 8, 8, 6), 1)
    pygame.draw.lines(surf, link, False, [(cx - 5, cy), (cx - 5, cy - 1), (cx + 2, cy - 1)])


def menu_icon(surf, cx, cy, c):
    for dy in (-4, 0, 4):
        surf.fill(c, (cx - 5, cy + dy - 1, 11, 2))


def back_icon(surf, cx, cy, c):
    pygame.draw.polygon(surf, c, [(cx - 6, cy), (cx - 1, cy - 5), (cx - 1, cy + 5)])
    surf.fill(c, (cx - 1, cy - 2, 7, 4))


def chevrons(surf, cx, cy, c, up):
    """As duas setas da pagina, centradas em (cx, cy): cada uma um V de 2
    pixels de grossura, 5 pixels uma da outra (de cy - 6 a cy + 6)."""
    s = -1 if up else 1
    for k in (0, 1):
        tip = cy + s * (3 - 5 * k)
        pygame.draw.polygon(surf, c, [(cx - 5, tip - 4 * s), (cx, tip + s), (cx + 5, tip - 4 * s),
                                      (cx + 5, tip - 2 * s), (cx, tip + 3 * s), (cx - 5, tip - 2 * s)])


def funnel(surf, cx, cy, c):
    pygame.draw.polygon(surf, c, [(cx - 6, cy - 5), (cx + 6, cy - 5), (cx + 1, cy + 1), (cx + 1, cy + 6),
                                  (cx - 1, cy + 6), (cx - 1, cy + 1)])


# ── O modo comercial ──────────────────────────────────────────────
# O indicador (Tab > Frontend options > Commercial mode): na lista debaixo
# dos icones dos comandos, na tela cheia no canto de cima a esquerda, na
# grade no canto de baixo a direita.

COIN_W, COIN_H = 80, 30
COIN_CREAM, COIN_GLASS = (236, 232, 218), (178, 176, 170)
COIN_CYCLE = 1.6                              # segundos de uma ficha entrando
# A placa (17x18; com a chapa cinza, 19x20) tem a mesma folga de 3 pixels
# ate a linha da moldura (2 pixels) em cima, embaixo e a esquerda.
COIN_PLATE = (6, 6)                           # onde a placa comeca na moldura
COIN_TEXT = 27                                # onde o texto comeca


def coin_slot(x, y):
    """(x, y) do meio da fenda, no meio da faixa clara da placa que comeca
    em x, y (a faixa vai de y + 1 a y + 16; a fenda, de y + 4 a y + 13)."""
    return x + 3, y + 8


def coin_icon(ui, x, y, t):
    """A entrada de ficha da porta do gabinete: numa moldura preta sobre a
    chapa cinza, a faixa clara com a fenda fina e, ao lado, a janelinha
    iluminada."""
    px, py = x, y
    pygame.draw.rect(ui, (112, 114, 120), (px - 1, py - 1, 19, 20), 1)   # a chapa da porta
    ui.fill(T.SPACE, (px, py, 17, 18))
    ui.fill(COIN_CREAM, (px + 1, py + 1, 5, 16))
    sx, sy = coin_slot(px, py)
    # A fenda, centrada na faixa: a largura e a espessura da ficha de lado.
    ui.fill(T.SPACE, (sx - 1, sy - 4, 3, 10))
    ui.fill(COIN_CREAM, (px + 7, py + 1, 9, 16))
    ui.fill(COIN_GLASS, (px + 7, py + 12, 9, 5))


# A ficha prateada: a face cinza clara, o contorno e o relevo mais escuros,
# e a borda (a espessura) no cinza do meio.
COIN_FACE, COIN_LINE, COIN_EDGE = (214, 216, 222), (150, 153, 162), (128, 131, 140)


def coin_moving(ui, x, y, t):
    """A ficha, um pouco de lado (a face e a espessura dela), vem da
    esquerda (passa por cima da moldura), chega na fenda, termina de virar
    (so a espessura) e some nela."""
    sx, sy = coin_slot(x, y)
    p = (t % COIN_CYCLE) / COIN_CYCLE
    # A altura e a da fenda (10, de sy - 4 a sy + 5): a ficha entra justa.
    h, thick = 10, 3
    if p < 0.3:                               # vem deslizando
        k = p / 0.3
        cx, face = round(x - 14 + (sx - x + 14) * (1 - (1 - k) ** 2)), 7
    elif p < 0.45:                            # termina de virar e entra
        cx, face = sx, round(7 - (p - 0.3) / 0.15 * 7)
    else:
        return
    w = face + thick
    coin = pygame.Surface((w, h), pygame.SRCALPHA)
    # A espessura: a mesma elipse, atras, deslocada para a direita.
    pygame.draw.ellipse(coin, COIN_EDGE, (thick, 0, max(2, face), h))
    coin.fill(COIN_EDGE, (max(1, face // 2), 1, thick, h - 2))
    if face >= 2:
        pygame.draw.ellipse(coin, COIN_FACE, (0, 0, face, h))
        if face >= 5:
            pygame.draw.ellipse(coin, COIN_LINE, (0, 0, face, h), 1)
            coin.fill(COIN_LINE, (face // 2, 4, 1, 3))   # o relevo
    # Espelhada: a espessura a esquerda, a face a direita (o giro e para la).
    ui.blit(pygame.transform.flip(coin, True, False), (cx - w // 2, sy - 4))


def clock_icon(ui, cx, cy, color, t):
    """O relogio: o ponteiro dos segundos da a volta em 4 s."""
    pygame.draw.circle(ui, color, (cx, cy), 7, 2)
    ui.fill(color, (cx - 1, cy - 10, 3, 2))
    pygame.draw.line(ui, color, (cx, cy), (cx, cy - 4))
    a = t * math.pi / 2
    pygame.draw.line(ui, color, (cx, cy), (cx + round(5 * math.sin(a)), cy - round(5 * math.cos(a))))


def time_left(seconds):
    """O tempo que resta no indicador: MIN, SEC no ultimo minuto, e horas
    com muitas fichas."""
    if seconds < 60:
        return "%d SEC" % math.ceil(seconds)
    minutes = math.ceil(seconds / 60)
    return "%d MIN" % minutes if minutes < 100 else "%dH%02d" % divmod(minutes, 60)


def coin_box(fe, ui, x, y, t):
    """Sem tempo: a ficha entrando na fenda e o INSERT COIN piscando (mais
    rapido logo depois de um jogo pedido sem ficha). Com tempo: o relogio e
    o que resta, piscando logo depois da ficha e no ultimo minuto (vermelho).
    Tudo numa moldura."""
    left = fe.left()
    W.block(ui, (x, y, COIN_W, COIN_H), T.BG_DEEP, None)
    if left <= 0:
        nag = time.monotonic() - getattr(fe, "nag_at", 0.0) < 1.5
        on = int(t * (6 if nag else 2)) % 2 == 0
        coin_icon(ui, x + COIN_PLATE[0], y + COIN_PLATE[1], t)
        if on:
            W.text(ui, "INSERT", T.YELLOW, x + COIN_TEXT, y + 6)
            W.text(ui, "COIN", T.YELLOW, x + COIN_TEXT, y + 17)
        border = T.YELLOW if nag and on else T.PINK
    else:
        last = left < 60
        color = T.RED if last else T.GREEN
        fresh = time.monotonic() - getattr(fe, "coin_at", 0.0) < 2
        clock_icon(ui, x + 14, y + 16, color, t)
        if not (last and int(t * 2) % 2) and not (fresh and int(t * 6) % 2):
            W.text(ui, time_left(left), color, x + COIN_TEXT, y + 6)
        tiny.text(ui, "LEFT", T.COMMENT, x + COIN_TEXT, y + 19)
        border = color
    pygame.draw.rect(ui, border, (x, y, COIN_W, COIN_H), 2)
    if left <= 0:
        # A ficha por ultimo: ela vem de fora da moldura, por cima dela.
        coin_moving(ui, x + COIN_PLATE[0], y + COIN_PLATE[1], t)


# ── Os icones do Arcadeflow ────────────────────────────────────────
# O genero, o controle e os botoes de cada jogo com os icones do Arcadeflow,
# copiados em gui/icons/metapics. Sem o icone, a linha fica so com o texto.
# O icone do genero tem o nome da categoria do MAME sem pontuacao
# ("Fighter / Versus" e fighterversus.png); sem ele, o do genero principal
# (fighter.png).

METAPICS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "metapics")


def af_path(fe, kind, name):
    base = os.path.join(METAPICS, kind, name + ".png")
    return base if os.path.isfile(base) else None


def af_icon(fe, kind, name, h, color):
    """O icone, recortado do quadro transparente e na cor pedida, com h
    pixels de altura (os pequenos ficam nitidos, sem suavizar)."""
    key = ("af", kind, name, h, color)
    if key in fe.media:
        return fe.media[key]
    path = af_path(fe, kind, name)
    img = None
    if path:
        try:
            src = pygame.image.load(path)
            src = src.convert_alpha() if pygame.display.get_surface() else src
            # So a parte solida: a sombra suave dos icones grandes do
            # Arcadeflow ocupa o quadro inteiro.
            rect = src.get_bounding_rect(min_alpha=180)
            if rect.w and rect.h:
                src = src.subsurface(rect).copy()
                w = max(1, round(src.get_width() * h / src.get_height()))
                small = src.get_height() <= 2 * h
                img = (pygame.transform.scale if small else pygame.transform.smoothscale)(src, (min(w, 4 * h), h))
                img.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        except (pygame.error, OSError, ValueError):
            img = None
    fe.media[key] = img
    return img


def af_glyph(fe, name, color):
    """O icone de genero do Arcadeflow (16x16, um quadrado branco com o
    desenho em preto) so com o desenho, na cor pedida e no tamanho
    original: pintar o quadrado inteiro virava um borrao."""
    key = ("glyph", name, color)
    if key in fe.media:
        return fe.media[key]
    path = af_path(fe, "category", name)
    img = None
    if path:
        try:
            src = pygame.image.load(path)
            out = pygame.Surface(src.get_size(), pygame.SRCALPHA)
            for y in range(src.get_height()):
                for x in range(src.get_width()):
                    r, g, b, a = src.get_at((x, y))
                    if a > 128 and r + g + b < 384:
                        out.set_at((x, y), color + (255,))
            rect = out.get_bounding_rect()
            img = out.subsurface(rect).copy() if rect.w and rect.h else None
        except (pygame.error, OSError, ValueError):
            img = None
    fe.media[key] = img
    return img


def genre_icon(fe, game, h, color):
    cat = game.get("Category") or ""
    if not cat:
        return None
    full = re.sub(r"[^a-z0-9]", "", cat.lower())
    main = re.sub(r"[^a-z0-9]", "", cat.split("/")[0].lower())
    for name in (full, main, main.rstrip("s")):
        img = af_glyph(fe, name, color) if name else None
        if img and img.get_height() > h:
            # A linha pequena da tela cheia e da grade.
            w = max(1, round(img.get_width() * h / img.get_height()))
            img = pygame.transform.smoothscale(img, (w, h))
        if img:
            return img
    return None


# O icone de jogadores, no mesmo jeito dos de genero (16 pixels, cheio).
PLAYER_ICON = (
    "......####......",
    ".....######.....",
    "....########....",
    "....########....",
    "....########....",
    "....########....",
    ".....######.....",
    "......####......",
    "................",
    "...##########...",
    "..############..",
    ".##############.",
    ".##############.",
    ".##############.",
    ".##############.",
    ".##############.",
)


def players_icon(fe, color, h=None):
    """h: a altura pedida (o bitmap tem 16); sem h, o tamanho do bitmap."""
    key = ("players", color, h)
    if key not in fe.media:
        img = pygame.Surface((len(PLAYER_ICON[0]), len(PLAYER_ICON)), pygame.SRCALPHA)
        for y, row in enumerate(PLAYER_ICON):
            for x, c in enumerate(row):
                if c == "#":
                    img.set_at((x, y), color + (255,))
        if h and h != img.get_height():
            img = pygame.transform.smoothscale(img, (round(img.get_width() * h / img.get_height()), h))
        fe.media[key] = img
    return fe.media[key]


def lightgun_art(k):
    """A pistola (o Arcadeflow nao tem icone de lightgun) virada para a
    direita, numa grade de 64x40 com k pixels cada, em branco: o cano com a
    mira, o cabo inclinado e o guarda-mato vazado com o gatilho. Mais escura
    embaixo, como os icones do Arcadeflow (a luz vem de cima)."""
    img = pygame.Surface((64 * k, 40 * k), pygame.SRCALPHA)
    white, clear = (255, 255, 255, 255), (0, 0, 0, 0)

    def rect(x, y, w, h, r=0, c=white):
        pygame.draw.rect(img, c, (x * k, y * k, w * k, h * k), 0, round(r * k))

    def poly(points):
        pygame.draw.polygon(img, white, [(x * k, y * k) for x, y in points])

    rect(22, 8, 20, 22, 8)
    rect(27, 13, 10, 12, 4, clear)
    poly([(8, 12), (27, 12), (20, 36), (3, 36)])
    rect(2.5, 32, 17.5, 7, 3)
    rect(5, 3, 56, 13, 4)
    rect(52, 0.5, 4, 4, 1)
    poly([(30, 15), (33, 15), (32, 22), (30, 22)])
    shade = pygame.Surface(img.get_size(), pygame.SRCALPHA)
    for y in range(shade.get_height()):
        v = round(255 - 85 * y / shade.get_height())
        shade.fill((v, v, v, 255), (0, y, shade.get_width(), 1))
    img.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return img


def lightgun_icon(fe, h, color):
    """A pistola com h pixels de altura: desenhada grande e reduzida com
    suavizacao, como os icones de controle do Arcadeflow ao lado dela."""
    key = ("lightgun", h, color)
    if key not in fe.media:
        img = lightgun_art(8)
        img = img.subsurface(img.get_bounding_rect()).copy()
        w = max(1, round(img.get_width() * h / img.get_height()))
        img = pygame.transform.smoothscale(img, (w, h))
        img.fill(color + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        fe.media[key] = img
    return fe.media[key]


def control_icon(fe, game, h, color):
    c = (game.get("Control") or "").lower()
    name = None
    if "lightgun" in c or "gun" in c.split(","):
        return lightgun_icon(fe, h, color)
    if "trackball" in c:
        name = "control_trackball"
    elif "double joystick" in c:
        name = "control_double_joystick"
    elif "pedal" in c:
        name = "control_paddle_pedal"
    elif "paddle" in c or "dial" in c:
        name = "control_paddle"
    elif "analog" in c:
        name = "control_joystick_analog"
    elif "2-way" in c:
        name = "control_joystick_2way"
    elif "4-way" in c:
        name = "control_joystick_4way"
    elif "joystick" in c:
        name = "control_joystick_8way"
    return af_icon(fe, "overlaycontroller", name, h, color) if name else None


def buttons_icon(fe, game, h, color):
    n = (game.get("Buttons") or "").strip()
    if not n.isdigit():
        return None
    n = int(n)
    # O Arcadeflow tem 0 a 4 e 6: 5 fica no de 6.
    name = str(n if n in (0, 1, 2, 3, 4, 6) else (6 if n >= 5 else 0))
    return af_icon(fe, "overlaybuttons", name, h, color)


def control_short(control):
    """O controle em poucas letras, o que o icone nao diz: "joystick
    (8-way)" e 8-WAY, "double joystick (8-way)" e 2X 8-WAY."""
    c = control.split(",")[0].strip().lower()
    inside = re.search(r"\(([^()]*)\)", c)
    if "joystick" in c and inside:
        return ("2x " if c.startswith("double") else "") + inside.group(1)
    return c


def icon_rows(fe, game, h=10, icons_only=False):
    """[(icone ou None, texto, cor)] do genero, do controle e dos botoes e
    jogadores."""
    rows = []
    if game.get("Category"):
        rows.append((genre_icon(fe, game, h, T.CYAN), game["Category"].split(" / ")[0], T.CYAN))
    # Os jogadores: o boneco e o numero, depois do genero (o modo lista os
    # desenha a parte, por isso o icons_only os deixa de fora).
    players = (game.get("Players") or "").strip()
    if players.isdigit() and not icons_only:
        rows.append((players_icon(fe, T.GREEN, h), players, T.GREEN))
    if game.get("Control"):
        rows.append((control_icon(fe, game, h, T.PINK), control_short(game["Control"]), T.PINK))
    parts = []
    if game.get("Buttons"):
        parts.append("%s BTN" % game["Buttons"])
    if players and not players.isdigit() and not icons_only:
        parts.append("%sP" % players)
    if parts:
        rows.append((buttons_icon(fe, game, h, T.YELLOW), ", ".join(parts), T.YELLOW))
    return rows


def icon_line(fe, ui, game, x, y, right, h=10, rows=None):
    """Os icones lado a lado numa linha (a tela cheia e a grade); rows: so
    esses (a grade do modo comercial os divide em duas linhas)."""
    for img, text, color in icon_rows(fe, game, h) if rows is None else rows:
        if img:
            if x + img.get_width() > right:
                break
            ui.blit(img, (x, y))
            x += img.get_width() + 3
        label = text.upper()
        if x + tiny.width(label) > right:
            break
        x += tiny.text(ui, label, T.FG, x, y + (h - 5) // 2) + 10
    return x


# ── As informacoes do jogo ─────────────────────────────────────────

def category(game):
    return (game.get("Category") or "").split(" / ")[0]


def facts_line(game):
    parts = [p for p in (game.get("Year"), (game.get("Manufacturer") or "").split(" (")[0]) if p]
    return " ".join(parts)


def stars(surf, x, y, rate, r=5):
    n = max(0.0, min(5.0, rate / 20.0))
    for i in range(5):
        cx = x + r + i * (2 * r + 4)
        star(surf, cx, y + r, T.LINE, r)
        if n >= i + 1:
            star(surf, cx, y + r, T.YELLOW, r)
        elif n > i:
            half = pygame.Surface((2 * r + 2, 2 * r + 2), pygame.SRCALPHA)
            star(half, r + 1, r + 1, T.YELLOW, r)
            surf.blit(half, (cx - r - 1, y - 1), (0, 0, r + 1, 2 * r + 2))


def info_rows(game):
    """(rotulo, valor) do que a romlist sabe do jogo."""
    rows = []
    for label, field in (("GENRE", "Category"), ("PLAYERS", "Players"), ("BUTTONS", "Buttons"),
                         ("CONTROL", "Control"), ("SERIES", "Series")):
        if game.get(field):
            rows.append((label, game[field]))
    return rows


# ── A entrada da lista nova (a troca de romlist) ───────────────────
#
# Escolhido o sistema na tira, a tela de antes sai (leave) e a nova entra
# pedaco por pedaco (part): o titulo da romlist, a lista (linha por linha) ou
# as miniaturas, a imagem ou o video, o logo do jogo, os icones e o texto.
# Cada pedaco e desenhado numa camada so dele enquanto entra.

TRANSITIONS = {"list": "doors", "full": "mosaic", "flow": "pop"}
# As cinco de cada modo (a primeira, a tela inteira deslizando, e a de antes).
TRANSITION_CHOICES = {"list": ("slide", "cascade", "drum", "blinds", "doors"),
                      "full": ("slide", "tv", "zoom", "mosaic", "curtain"),
                      "flow": ("slide", "flip", "fall", "explode", "pop")}
TRANSITION_NAMES = {"slide": "SLIDE", "cascade": "CASCADE", "drum": "SLOT DRUM", "blinds": "BLINDS",
                    "doors": "DOUBLE DOOR", "tv": "TV", "zoom": "ZOOM", "mosaic": "MOSAIC",
                    "curtain": "CURTAIN", "flip": "CARD FLIP", "fall": "FALLING CARDS",
                    "explode": "EXPLOSION", "pop": "POP"}
INTRO = 0.85               # segundos de toda a troca
INTRO_EXIT = 0.25          # a tela de antes saindo
INTRO_PART = 0.35          # cada pedaco entrando
RIBBON_FADE = 0.25         # a tira some nos ultimos segundos dela
# Quando cada pedaco comeca a entrar (as linhas e as miniaturas, uma depois
# da outra), contado do fim da saida da tela de antes.
INTRO_DELAY = {"title": 0.0, "chrome": 0.05, "row": 0.06, "thumb": 0.06, "picture": 0.1,
               "logo": 0.2, "icons": 0.26, "text": 0.3}
INTRO_STEP = {"row": 0.022, "thumb": 0.045}


def transition(fe):
    """A animacao da troca de romlist no modo de agora: a escolhida no Tab >
    Transition (fe.transitions) ou a de TRANSITIONS ("slide": a tela inteira
    desliza, a de antes)."""
    picked = (getattr(fe, "transitions", None) or {}).get(fe.mode)
    return picked if picked in TRANSITION_CHOICES.get(fe.mode, ()) else TRANSITIONS.get(fe.mode, "slide")


def intro_now(fe):
    """A troca em andamento: (o estilo, o lado, os segundos desde o comeco),
    ou None."""
    intro = getattr(fe, "intro", None)
    if not intro or fe.shot or intro.get("style") == "slide":
        return None
    t = fe.abs_now - intro["start"]
    return (intro["style"], intro["side"], t) if t < INTRO else None


def intro_progress(fe, name, order):
    """Quanto o pedaco ja entrou: None (no lugar; desenhado direto no ui), ou
    de 0 (ainda escondido) a 1."""
    state = intro_now(fe)
    if state is None:
        return None
    if state[0] == "curtain":
        # A cortina: tudo aparece de uma vez, atras dela (curtain_open).
        return 0.0 if state[2] < INTRO_EXIT else None
    t = state[2] - INTRO_EXIT * 0.6 - INTRO_DELAY[name] - INTRO_STEP.get(name, 0) * order
    p = t / INTRO_PART
    return None if p >= 1 else max(0.0, p)


@contextlib.contextmanager
def part(fe, ui, name, order=0):
    """Desenha um pedaco da tela: fora da troca, direto no ui; durante ela,
    numa camada que entra no ui com a animacao do pedaco."""
    p = intro_progress(fe, name, order)
    if p is None:
        yield ui
        return
    layer = pygame.Surface(ui.get_size(), pygame.SRCALPHA)
    layer.set_clip(ui.get_clip())
    yield layer
    if p > 0:
        place(ui, layer, lambda rect: enter(fe.intro["style"], fe.intro["side"], name, p, rect))


def ribbon_center():
    """O meio do azulejo do sistema escolhido na tira (o do zoom)."""
    return WW / 2, 118


def bounce(p):
    """De 0 a 1 quicando no fim, como uma carta que cai na mesa."""
    if p < 1 / 2.75:
        return 7.5625 * p * p
    if p < 2 / 2.75:
        p -= 1.5 / 2.75
        return 7.5625 * p * p + 0.75
    if p < 2.5 / 2.75:
        p -= 2.25 / 2.75
        return 7.5625 * p * p + 0.9375
    p -= 2.625 / 2.75
    return 7.5625 * p * p + 0.984375


def enter(style, side, name, p, rect):
    """Como o pedaco (em rect) esta, com p de 0 a 1: deslocado (dx, dy),
    esticado (sx, sy, em volta do centro dele), transparente (alpha), aceso
    (glow), em blocos (pixel) ou so a faixa do meio a vista (reveal)."""
    e = 1 - (1 - p) ** 3
    # O titulo, os icones e o texto, nos estilos das miniaturas e da TV:
    # aparecem subindo (o titulo descendo) um pouco.
    plain = {"dy": (1 - e) * (-10 if name == "title" else 10), "alpha": e}
    if style == "cascade":
        # LIST: cada pedaco chega do lado da romlist nova, um depois do outro;
        # o titulo desce de cima.
        if name == "title":
            return {"dy": -(1 - e) * 24, "alpha": e}
        return {"dx": side * (1 - e) * WW * 0.55, "alpha": min(1.0, e * 1.6)}
    if style == "drum":
        # LIST: o tambor do caca-niquel: as linhas sobem de baixo, girando, e
        # param no lugar; o resto vem junto, mais devagar.
        if name == "title":
            return {"dy": -(1 - e) * 24, "alpha": e}
        if name == "row":
            return {"dy": (1 - e) * HH * 0.7, "sy": 0.55 + 0.45 * e, "alpha": min(1.0, e * 2)}
        return {"dy": (1 - e) * 70, "alpha": e}
    if style == "blinds":
        # LIST: a persiana abrindo: cada pedaco cresce da linha do meio dele.
        return {"sy": max(0.02, e), "alpha": min(1.0, e * 2)}
    if style == "doors":
        # LIST: a porta dupla fechando: a lista vem da esquerda, a imagem e as
        # informacoes da direita, o titulo de cima.
        if name == "title":
            return {"dy": -(1 - e) * 24, "alpha": e}
        left = name in ("row", "chrome")
        return {"dx": (-1 if left else 1) * (1 - e) * WW * 0.6}
    if style == "tv":
        # FULL SCREEN: a imagem acende como a TV de tubo: uma linha clara que
        # se abre na largura e depois na altura; o resto aparece por cima.
        if name == "picture":
            if p < 0.35:
                return {"sx": max(0.02, p / 0.35), "sy": 0.012, "glow": True}
            q = (p - 0.35) / 0.65
            return {"sy": max(0.012, 1 - (1 - q) ** 3), "glow": q < 0.3}
        return plain
    if style == "zoom":
        # FULL SCREEN: cada pedaco sai do azulejo escolhido na tira e cresce
        # ate o lugar dele.
        cx, cy = ribbon_center()
        return {"dx": (cx - rect.centerx) * (1 - e), "dy": (cy - rect.centery) * (1 - e),
                "sx": max(0.02, e), "sy": max(0.02, e), "alpha": min(1.0, e * 2)}
    if style == "mosaic":
        # FULL SCREEN: comeca em blocos grandes, que se desfazem.
        return {"pixel": 1 + round((1 - e) * 14), "alpha": min(1.0, e * 1.8)}
    if style == "flip":
        # GRID: cada miniatura vira como uma carta, na diagonal.
        if name == "thumb":
            return {"sx": max(0.02, e), "alpha": min(1.0, e * 3)}
        return plain
    if style == "fall":
        # GRID: as cartas caem de cima, na diagonal, e quicam no lugar.
        if name == "thumb":
            return {"dy": -(1 - bounce(p)) * (rect.bottom + 8)}
        return plain
    if style == "explode":
        # GRID: as miniaturas voam do meio da tela para o lugar.
        if name == "thumb":
            return {"dx": (WW / 2 - rect.centerx) * (1 - e), "dy": (HH / 2 - rect.centery) * (1 - e),
                    "sx": 0.3 + 0.7 * e, "sy": 0.3 + 0.7 * e, "alpha": min(1.0, e * 2)}
        return plain
    if style == "pop":
        # GRID: cada miniatura nasce do meio dela, passa um pouco do tamanho e
        # volta (um pulinho).
        if name == "thumb":
            s = 1 + 2.7 * (p - 1) ** 3 + 1.7 * (p - 1) ** 2
            return {"sx": max(0.02, s), "sy": max(0.02, s), "alpha": min(1.0, p * 3)}
        return plain
    return {}


def place(ui, layer, move):
    """Poe no ui o que foi desenhado na camada, com o movimento que
    move(rect do desenho) devolve."""
    rect = layer.get_bounding_rect()
    if not rect.w or not rect.h:
        return
    m = move(rect)
    piece = layer.subsurface(rect)
    reveal = m.get("reveal")
    if reveal is not None:
        # So a faixa do meio, reveal da largura, a vista.
        w = max(1, round(rect.w * reveal))
        cut = pygame.Rect(rect.x + (rect.w - w) // 2, rect.y, w, rect.h)
        ui.blit(layer.subsurface(cut), cut.topleft)
        return
    w = max(1, round(rect.w * m.get("sx", 1)))
    h = max(1, round(rect.h * m.get("sy", 1)))
    piece = pygame.transform.smoothscale(piece, (w, h)) if (w, h) != rect.size else piece.copy()
    block = m.get("pixel", 1)
    if block > 1:
        small = pygame.transform.scale(piece, (max(1, w // block), max(1, h // block)))
        piece = pygame.transform.scale(small, (w, h))
    if m.get("glow"):
        piece.fill((90, 90, 90, 0), special_flags=pygame.BLEND_RGBA_ADD)
    alpha = m.get("alpha", 1.0)
    if alpha < 1:
        piece.set_alpha(round(255 * max(0.0, alpha)))
    ui.blit(piece, (round(rect.centerx - w / 2 + m.get("dx", 0)), round(rect.centery - h / 2 + m.get("dy", 0))))


def scaled(img, k, center):
    """img em k do tamanho, com o meio em center."""
    w, h = max(1, round(WW * k)), max(1, round(HH * k))
    return pygame.transform.smoothscale(img, (w, h)), (round(center[0] - w / 2), round(center[1] - h / 2))


def curtain_panels(back, k):
    """As duas metades da cortina, fechadas k (0: abertas, 1: encostadas no meio)."""
    w = round(WW / 2 * k)
    if w <= 2:
        return                # aberta (sem sobrar a borda rosa no canto)
    for x in (0, WW - w):
        back.fill(T.BG_DEEP, (x, 0, w, HH))
        for i in range(x + 6, x + w, 12):
            back.fill(T.SPACE, (i, 0, 2, HH))
    pygame.draw.line(back, T.PINK, (w - 1, 0), (w - 1, HH - 1), 2)
    pygame.draw.line(back, T.PINK, (WW - w, 0), (WW - w, HH - 1), 2)


def curtain_open(back, fe):
    """A cortina abrindo por cima da tela nova (depois da saida)."""
    state = intro_now(fe)
    if state is None or state[0] != "curtain" or state[2] < INTRO_EXIT:
        return
    q = (state[2] - INTRO_EXIT) / (INTRO - INTRO_EXIT)
    curtain_panels(back, (1 - q) ** 2)


def leave(back, fe):
    """A tela de antes saindo, por baixo do que entra."""
    state = intro_now(fe)
    old = fe.intro.get("old") if state else None
    if old is None or state[2] >= INTRO_EXIT:
        return
    style, side, t = state
    e = t / INTRO_EXIT
    k = e * e
    if style == "drum":
        img = old.copy()
        img.set_alpha(round(255 * (1 - e)))
        back.blit(img, (0, round(-k * HH * 0.7)))
        return
    if style == "blinds":
        # A persiana fechando: tiras da altura de uma linha da lista.
        for y in range(0, HH, 14):
            h = round(14 * (1 - k))
            if h > 0:
                back.blit(old, (0, y + (14 - h) // 2), (0, y + (14 - h) // 2, WW, h))
        return
    if style == "doors":
        # A porta abrindo: a lista vai para a esquerda, a imagem para a direita.
        cut = list_geom()[1][0] - 7 if fe.mode == "list" and not T.VERTICAL else WW // 2
        back.blit(old, (round(-k * cut), 0), (0, 0, cut, HH))
        back.blit(old, (cut + round(k * (WW - cut)), 0), (cut, 0, WW - cut, HH))
        return
    if style == "zoom":
        cx, cy = ribbon_center()
        img, at = scaled(old, max(0.02, 1 - k), (WW / 2 + (cx - WW / 2) * k, HH / 2 + (cy - HH / 2) * k))
        back.blit(img, at)
        return
    if style == "mosaic":
        block = 1 + round(e * 14)
        img = pygame.transform.scale(pygame.transform.scale(old, (WW // block, HH // block)), (WW, HH))
        img.set_alpha(round(255 * min(1.0, 2 * (1 - e))))
        back.blit(img, (0, 0))
        return
    if style == "curtain":
        back.blit(old, (0, 0))
        curtain_panels(back, 1 - (1 - e) ** 2)
        return
    if style == "fall":
        back.blit(old, (0, round(k * HH)))
        return
    if style == "explode":
        img, at = scaled(old, 1 + 0.6 * e, (WW / 2, HH / 2))
        img.set_alpha(round(255 * (1 - e)))
        back.blit(img, at)
        return
    if style == "pop":
        img, at = scaled(old, max(0.02, 1 - k), (WW / 2, HH / 2))
        back.blit(img, at)
        return
    if style == "tv":
        # A TV desligando: a tela achata numa linha clara, e a linha num ponto.
        if e < 0.6:
            h = max(2, round(HH * (1 - e / 0.6)))
            img = pygame.transform.smoothscale(old, (WW, h))
            img.fill((round(140 * e), round(140 * e), round(140 * e)), special_flags=pygame.BLEND_RGB_ADD)
            back.blit(img, (0, (HH - h) // 2))
        else:
            w = max(2, round(WW * (1 - (e - 0.6) / 0.4)))
            back.fill((230, 230, 240), ((WW - w) // 2, HH // 2 - 1, w, 2))
        return
    if style == "flip":
        # A carta da tela inteira virando: estreita ate a linha do meio.
        w = max(1, round(WW * (1 - k)))
        back.blit(pygame.transform.smoothscale(old, (w, HH)), ((WW - w) // 2, 0))
        return
    # cascade: sai para o lado contrario e some.
    img = old.copy()
    img.set_alpha(round(255 * (1 - e)))
    back.blit(img, (round(-side * k * WW * 0.6), 0))


# ── Os modos ───────────────────────────────────────────────────────

def frame(fe, ui):
    cat = fe.category()
    W.frame(ui, {}, (cat or {}).get("name", "FliperOS") or "FliperOS", [])
    if cat and cat.get("name"):
        title_logo(ui, cat["name"])
    # O filtro e o controle em uso, pequenos, debaixo do titulo (o "All
    # Games" e todos os controles nao).
    name = fe.lib.filters[fe.flt % len(fe.lib.filters)]["name"]
    parts = ["FILTER: " + name.replace("©", "(C)")] if name.lower() != "all games" else []
    if getattr(fe, "ctrl", None):
        parts.append("CONTROL: " + fe.ctrl)
    if parts:
        tiny.text(ui, "  ".join(parts), T.CYAN, SX, 29)


def title_logo(ui, name):
    """O logotipo escrito do sistema no topo, no lugar do nome da romlist (que
    o W.frame escreveu): no meio, com as faixas do mesmo tamanho dos dois lados.
    Sem logotipo, fica o do W.frame, o nome."""
    logo = system_logo(name, min(180, T.SAFE_W - 2 * 24), 18)
    if logo is None:
        return
    gx = (WW - logo.get_width()) // 2
    ui.fill((0, 0, 0, 0), (0, 8, WW, 22))
    ui.blit(logo, (gx, 9 + (18 - logo.get_height()) // 2))
    bar = gx - T.SAFE_X - 8
    if bar >= 8:
        for i, color in enumerate(W.RAINBOW):
            pygame.draw.rect(ui, color, (T.SAFE_X, 12 + i * 2, bar, 2))
            pygame.draw.rect(ui, color, (T.WIDTH - T.SAFE_X - bar, 12 + i * 2, bar, 2))


def empty(fe, ui):
    frame(fe, ui)
    flt = fe.lib.filters[fe.flt % len(fe.lib.filters)]["name"]
    if getattr(fe, "ctrl", None):
        flt += ", control: " + fe.ctrl
    W.paragraph(ui, ["No games here.", "", "Filter: " + flt,
                     "Copy games to the folders in ~/roms (the network share \\\\fliperos\\roms)."], 80)


def list_geom():
    """((x, largura, y, linhas) da lista, (x, y, largura, altura) da imagem).
    Deitado, a lista a esquerda e a imagem a direita; em pe, a imagem em
    cima, larga, e a lista embaixo."""
    if T.VERTICAL:
        return (SX, SW - 8, 164, 10), (SX + SW - 87, 34, 87, 116)
    px = SX + LIST_W + 14
    return (SX, LIST_W, 36, 13), (px, 36, SX + SW - px, LIST_SH)


def draw_list(fe, ui, now):
    with part(fe, ui, "title") as s:
        frame(fe, s)
    (lx, lw, y0, rows), (px, py, pw, sh) = list_geom()
    # Os jogos que outros gabinetes jogam (no alto) e o resto: um vao de sep
    # pixels com a linha no meio; uma linha a menos na lista para caber.
    sep = 8 if fe.rows and fe.rows[0][2] == "elsewhere" else 0
    rows -= 1 if sep else 0
    if fe.cursor < fe.top:
        fe.top = fe.cursor
    if fe.cursor >= fe.top + rows:
        fe.top = fe.cursor - rows + 1
    fe.top = max(0, min(fe.top, max(0, len(fe.rows) - rows)))
    shown = sep and fe.rows[fe.top][2] == "elsewhere"
    for i in range(fe.top, min(len(fe.rows), fe.top + rows)):
        y = y0 + (i - fe.top) * 14 + (sep if shown and fe.rows[i][2] != "elsewhere" else 0)
        with part(fe, ui, "row", i - fe.top) as s:
            list_row(fe, s, i, lx, lw, y, sep, now)
    with part(fe, ui, "chrome") as s:
        if len(fe.rows) > rows:
            W.scrollbar(s, lx + lw + 4, y0, rows * 14 - 2 + sep, fe.top, rows, len(fe.rows))
        # O contador debaixo da ultima linha, tambem com o vao dos jogos de
        # outro gabinete (que empurra a lista para baixo).
        count = "%d/%d" % (fe.cursor + 1, len(fe.rows))
        if T.VERTICAL:
            # Em pe a lista vai quase ate o fim da tela: o contador na letra pequena.
            tiny.text(s, count, T.LINE, lx + lw - tiny.width(count), y0 + rows * 14 + 2 + sep)
        else:
            W.text(s, count, T.LINE, lx + lw, y0 + rows * 14 + 1 + sep, right=True)
    # A imagem, o logo e as informacoes (a direita, ou em cima em pe).
    game = fe.game()
    y0 = py
    with part(fe, ui, "picture") as s:
        W.block(s, (px, y0, pw, sh), T.BG_DEEP, T.PURPLE)
        if game is None:
            # Num cabecalho de grupo: so a moldura e o que abrir faz.
            pygame.draw.rect(s, T.PINK, (px, y0, pw, sh), 2)
            head = fe.rows[fe.cursor][2] if fe.rows else None
            if fe.fd.group_head(head):
                opened = head[1] in fe.groups_open
                tiny.centered(s, "%d GAMES" % head[2], T.FG, px + pw // 2, y0 + sh // 2 - 8)
                tiny.centered(s, "1: CLOSE" if opened else "1: OPEN", T.COMMENT, px + pw // 2, y0 + sh // 2 + 4)
        else:
            shot = picture(fe, game, pw - 4, sh - 4)
            if shot:
                blit_center(s, shot, px + 2, y0 + 2, pw - 4, sh - 4)
                if fe.scraping is game:
                    looking(s, px + 4, y0 + sh - 14, pw - 8)
            elif fe.scraping is game:
                # Sem nada ainda: o scrape sozinho esta buscando.
                W.glow(s, (px + 2, y0 + 2, pw - 4, sh - 4), {"now": now})
                tiny.centered(s, "LOOKING FOR ART...", T.CYAN, px + pw // 2, y0 + sh // 2 - 2)
            pygame.draw.rect(s, T.PINK, (px, y0, pw, sh), 2)
    if game is None:
        return
    logo = image(fe, media(fe, game, "logo"), min(pw - 8, 200), 28)
    if logo:
        with part(fe, ui, "logo") as s:
            blit_center(s, logo, px, y0 + sh - 14, pw, 28)
    if T.VERTICAL:
        with part(fe, ui, "text") as s:
            list_info_vertical(fe, s, game, (SX, y0, px - SX - 6, sh), now)
        return
    y = y0 + sh + 6
    with part(fe, ui, "text") as s:
        if logo:
            y = y0 + sh + 18
        else:
            # Sem logo, o titulo numa linha: o que nao cabe corre em circulo.
            ticker(s, text_img(fe.fd.short_title(game).upper(), T.YELLOW), px, y, pw, now)
            y += 12
        W.text(s, fit(facts_line(game), pw), T.YELLOW, px, y)
        y += 12
    with part(fe, ui, "icons") as s:
        # Os icones numa fileira so: o genero, os jogadores, o controle e os botoes.
        strip = icon_strip(fe, s, game, px, y, SX + SW)
        y += strip + 4 if strip else 0
        if link_mark(fe, game) is not None:
            # Um jogo de link: o globo (aceso se alguem joga) e os gabinetes dessa festa.
            party = link_party(fe, game)
            if link_kind(fe, game) == "net":
                pads_icon(s, px + 7, y + 7, party is not None)
            else:
                globe_icon(s, px + 7, y + 7, 7, party is not None)
            if party:
                cabinet_row(s, px + 22, y + 3, party["used"], party["max"] or 1, w=5, h=8, gap=1)
            y += 18
        y += play_chips(s, game, px, y)
    # O modo comercial: o indicador debaixo dos icones dos comandos; fora
    # dele, a sinopse do jogo rolando.
    with part(fe, ui, "text", 1) as s:
        if fe.commercial:
            coin_box(fe, s, px, min(y + 2, HH - COIN_H - 6), now)
        else:
            draw_synopsis(fe, s, game, (px, y, pw, HH - 6 - y), now)


def list_row(fe, ui, i, lx, lw, y, sep, now):
    """A linha i da lista: o jogo (o pai com o [+], o clone com o trilho, o
    de outro gabinete com o globo) ou o cabecalho de um grupo."""
    game, level, extra = fe.rows[i]
    on = i == fe.cursor
    if game is None:
        group_header(fe, ui, (lx, y, lw, 12), extra, on, now)
        return
    # Os clones do jogo pai; "elsewhere" (um jogo que outro gabinete joga
    # agora, no alto da lista) nao e uma lista deles.
    clones = extra if isinstance(extra, list) else None
    party = link_party(fe, game) if extra == "elsewhere" else None
    if party:
        globe_icon(ui, lx + 5, y + 6, 5, True)
        x = lx + 14
        label, color = fe.fd.short_title(game), T.YELLOW
        total = party["max"] or 1
        sw = total * 6 - 1
        cabinet_row(ui, lx + lw - 14 - sw, y + 2, party["used"], total, w=5, h=8, gap=1)
        room = lx + lw - x - 12 - sw - 6
        if i + 1 < len(fe.rows) and fe.rows[i + 1][2] != "elsewhere":
            pygame.draw.line(ui, T.LINE, (lx, y + 13 + sep // 2), (lx + lw - 2, y + 13 + sep // 2))
    elif level == 0:
        room = None
        lmark = link_mark(fe, game)
        x = lx + 14 if clones else lx
        if fe.fd.group_item(extra):
            # Um jogo dentro de RECENT ou FAVOURITES: recuado, com um trilho
            # na cor do grupo.
            x = lx + 12
            pygame.draw.line(ui, T.LINE, (lx + 4, y - 1), (lx + 4, y + 13))
        if clones:
            # O [+] do jogo pai, um pouco transparente (aberto, menos).
            expand_mark(ui, lx, y + 1, game["Name"] in fe.opened)
        if lmark is not None:
            # O link: o globo (ou, no net play, os dois controles) ao lado
            # do titulo, apagado ou aceso.
            if link_kind(fe, game) == "net":
                pads_icon(ui, x + 5, y + 6, lmark, small=True)
            else:
                globe_icon(ui, x + 5, y + 6, 5, lmark)
            x += 14
        label = fe.fd.short_title(game)
        color = T.FG if game["Name"] in fe.opened or fe.fd.group_item(extra) else T.COMMENT
    else:
        room = None
        x = lx + 26
        last = i + 1 >= len(fe.rows) or fe.rows[i + 1][1] == 0
        pygame.draw.line(ui, T.LINE, (lx + 5, y - 3), (lx + 5, y + (5 if last else 14)))
        pygame.draw.line(ui, T.LINE, (lx + 5, y + 5), (lx + 20, y + 5))
        label = "MAIN SET" if extra == "main" else fe.fd.variant(game, extra)
        color = T.CYAN
    if on:
        tile_frame(ui, (x - 4, y, lx + lw - x + 4, 12), True, now)
        pygame.draw.rect(ui, T.PINK, (x - 4, y, lx + lw - x + 4, 12), 1)
        color = T.FG
    if game.get("Favourite") == "1" and level == 0:
        star(ui, lx + lw - 6, y + 6, T.YELLOW, 4)
    room = lx + lw - x - 12 if room is None else room
    if on:
        # O escolhido inteiro: o que nao cabe corre em circulo.
        ticker(ui, text_img(label.upper(), color), x, y + 2, room, now)
    else:
        W.text(ui, fit(label, room), color, x, y + 2)


def expand_mark(ui, x, y, opened):
    """O [+] (aberto, o [-]) do jogo pai com clones e do grupo RECENT: um
    pouco transparente (aberto, menos)."""
    mark = pygame.Surface((10, 10), pygame.SRCALPHA)
    mark.fill(T.BG_DEEP)
    pygame.draw.rect(mark, T.PINK if opened else T.COMMENT, (0, 0, 10, 10), 1)
    mark.fill(T.PINK if opened else T.COMMENT, (2, 4, 6, 2))
    if not opened:
        mark.fill(T.COMMENT, (4, 2, 2, 6))
    mark.set_alpha(190 if opened else 120)
    ui.blit(mark, (x, y))


def group_header(fe, ui, rect, head, on, now):
    """O cabecalho de RECENT (com o [+] de sempre) ou FAVOURITES (com a
    estrela) no alto da lista, como a linha de um jogo pai: o nome, e quantos
    jogos tem na ponta direita."""
    lx, y, lw, _ = rect
    key, count = head[1], head[2]
    opened = key in fe.groups_open
    x = lx + 14
    color = T.FG if opened else T.COMMENT
    if on:
        tile_frame(ui, (x - 4, y, lx + lw - x + 4, 12), True, now)
        pygame.draw.rect(ui, T.PINK, (x - 4, y, lx + lw - x + 4, 12), 1)
        color = T.FG
    if key == "fav":
        star(ui, lx + 5, y + 6, T.PINK if opened else T.COMMENT, 4)
    else:
        expand_mark(ui, lx, y + 1, opened)
    W.text(ui, dict(fe.fd.GROUPS)[key], color, x, y + 2)
    W.text(ui, str(count), color, lx + lw - 6, y + 2, right=True)


def play_chips(ui, game, x, y):
    """Os selinhos do jogo: * FAV e o contador de partidas (PLAYED nX, do
    NOME.stat). Devolve a altura que usou (0 sem nenhum)."""
    played = game.get("PlayedCount")
    chips = []
    if game.get("Favourite") == "1":
        chips.append(("* FAV", T.YELLOW))
    if played:
        chips.append(("PLAYED %sX" % played, T.COMMENT))
    for text, color in chips:
        w = tiny.width(text) + 8
        W.block(ui, (x, y, w, 10), T.BG_DEEP, None)
        pygame.draw.rect(ui, T.LINE, (x, y, w, 10), 1)
        tiny.text(ui, text, color, x + 4, y + 3)
        x += w + 4
    return 14 if chips else 0


def list_info_vertical(fe, ui, game, box, now):
    """O modo lista em pe: a coluna a esquerda da imagem (que e em pe, 3:4,
    no canto de cima a direita). De cima para baixo: o ano e o fabricante (o
    que nao cabe corre em circulo), os icones dois por linha e, no resto, a
    sinopse rolando; no modo comercial, no lugar da sinopse, o indicador de
    ficha. O nome do jogo ja esta na lista."""
    x, y, w, h = box
    bottom = y + h
    ticker(ui, text_img(facts_line(game).upper(), T.YELLOW), x, y + 1, w, now)
    y += 14
    # Os icones, dois por linha.
    cell = (w - 6) // 2
    rows = icon_rows(fe, game, 12)
    for i, (img, text, color) in enumerate(rows):
        cx = x + (i % 2) * (cell + 6)
        if img:
            ui.blit(img, (cx, y + 14 * (i // 2)))
        off = img.get_width() + 3 if img else 0
        tiny.text(ui, tiny.fit(text.upper(), cell - off), T.FG, cx + off, y + 14 * (i // 2) + 3)
    y += 14 * ((len(rows) + 1) // 2)
    if link_mark(fe, game) is not None:
        # Um jogo de link: o globo (aceso se alguem joga) e os gabinetes dessa festa.
        party = link_party(fe, game)
        if link_kind(fe, game) == "net":
            pads_icon(ui, x + 7, y + 6, party is not None)
        else:
            globe_icon(ui, x + 7, y + 6, 7, party is not None)
        if party:
            cabinet_row(ui, x + 22, y + 2, party["used"], party["max"] or 1, w=5, h=8, gap=1)
        y += 14
    y += play_chips(ui, game, x, y + 2)
    if fe.commercial:
        # No meio do espaco que sobra embaixo dos icones.
        coin_box(fe, ui, x + (w - COIN_W) // 2, y + max(0, (bottom - y - COIN_H) // 2), now)
    else:
        # A sinopse comeca com uma folga debaixo dos icones.
        y += 6
        draw_synopsis(fe, ui, game, (x, y, w, bottom - y), now)


def icon_strip(fe, ui, game, x, y, right):
    """Os icones do jogo numa fileira so (o modo lista): o genero, os
    jogadores (o boneco e o numero), o controle e os botoes; sem o icone, o
    texto pequeno no lugar dele. Na maior altura em que todos cabem ate right
    (16, 13 ou 10; na menor, o que nao cabe fica de fora). Devolve a altura
    (0 sem nenhum)."""
    players = (game.get("Players") or "").strip()

    def width(item):
        img, text, color = item
        if color == T.GREEN:
            return img.get_width() + 2 + W.width(text)
        return img.get_width() if img else tiny.width(text)
    for h in (16, 13, 10):
        items = []
        for img, text, color in icon_rows(fe, game, h, icons_only=True):
            if color == T.YELLOW:
                # O dos botoes e largo: um pouco mais baixo que os outros.
                img = buttons_icon(fe, game, round(h * 0.75), T.YELLOW)
            items.append((img, text.upper(), color))
            if color == T.CYAN and players.isdigit():
                items.append((players_icon(fe, T.GREEN, h - 2), players, T.GREEN))
        if players.isdigit() and not any(c == T.GREEN for _, _, c in items):
            items.insert(0, (players_icon(fe, T.GREEN, h - 2), players, T.GREEN))
        if not items:
            return 0
        if sum(width(i) for i in items) + 6 * (len(items) - 1) <= right - x or h == 10:
            break
    for img, text, color in items:
        if x + width((img, text, color)) > right:
            break
        if color == T.GREEN:
            ui.blit(img, (x, y + (h - img.get_height()) // 2))
            W.text(ui, text, T.GREEN, x + img.get_width() + 2, y + (h - 8) // 2)
        elif img:
            ui.blit(img, (x, y + (h - img.get_height()) // 2))
        else:
            tiny.text(ui, text, color, x, y + (h - 5) // 2)
        x += width((img, text, color)) + 6
    return h


SYNOPSIS_FADE, SYNOPSIS_SPEED, SYNOPSIS_WAIT = 10, 6.0, 2.0  # pixels, pixels por segundo, segundos


def game_description(fe, game):
    """A sinopse do jogo: o comeco da historia do arcade-history, do que o
    scrape ja salvou em ~/media/info (sem rede); o clone sem a sua usa a do
    pai. Os jogos de console nao tem: vazia."""
    system = game["_system"]
    key = ("desc", system["key"], game["Name"])
    if key not in fe.media:
        text = ""
        for name in (game["Name"], game.get("CloneOf")) if system.get("arcade") else ():
            path = fe.lib.info.path(system["key"], name, "en") if name else None
            info = ((fe.lib.info.load(path) if path else None) or {}).get("info")
            if info:
                text = fe.fd.web.history_parts(info.get("history"))[0]
                if text:
                    break
        return remember(fe, key, text)
    return fe.media[key]


TINY_SWAP = str.maketrans({'"': "'", "`": "'", ";": ",", "[": "(", "]": ")", "{": "(", "}": ")"})


def wrap_tiny(text, w):
    """O texto em linhas da fonte pequena de ate w pixels. Sem os acentos e
    com os sinais que ela nao tem trocados por parecidos (senao saem "?")."""
    import unicodedata
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().translate(TINY_SWAP)
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            while tiny.width(word) > w:
                cut = max(1, w // 4)
                if line:
                    lines.append(line)
                    line = ""
                lines.append(word[:cut])
                word = word[cut:]
            joined = (line + " " + word).strip()
            if tiny.width(joined) <= w:
                line = joined
            else:
                lines.append(line)
                line = word
        lines.append(line)
    while lines and not lines[-1]:
        lines.pop()
    return lines


def draw_synopsis(fe, ui, game, box, now):
    """A sinopse debaixo das informacoes do modo lista, subindo devagar (do
    fim volta ao comeco, sem emenda), com um degrade transparente em cima e
    embaixo. Comeca SYNOPSIS_WAIT segundos depois de o cursor parar no jogo;
    a que cabe inteira fica parada."""
    x, y, w, h = box
    text = game_description(fe, game) if h >= 24 else ""
    if not text:
        return
    key = ("desc-img", text, w)
    img = fe.media.get(key)
    if img is None:
        lines = wrap_tiny(text, w - 2)
        img = pygame.Surface((w, max(1, len(lines) * 7)), pygame.SRCALPHA)
        for i, line in enumerate(lines):
            tiny.text(img, line, T.FG, 0, i * 7)
        remember(fe, key, img)
    if getattr(fe, "synopsis_game", None) is not game:
        fe.synopsis_game, fe.synopsis_at = game, now
    view = pygame.Surface((w, h), pygame.SRCALPHA)
    if img.get_height() <= h:
        view.blit(img, (0, 0))
    else:
        period = img.get_height() + h // 2
        moved = int(max(0.0, now - fe.synopsis_at - SYNOPSIS_WAIT) * SYNOPSIS_SPEED)
        off = moved % period
        view.blit(img, (0, -off))
        view.blit(img, (0, period - off))
        # O degrade de cima aparece aos poucos, com o texto ja subindo: parada,
        # a primeira linha fica inteira.
        top = min(SYNOPSIS_FADE, moved)
        view.blit(fade_mask(w, h, top), (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    ui.blit(view, (x, y))


FADE_MASKS = {}


def fade_mask(w, h, top=SYNOPSIS_FADE):
    """A mascara do degrade: transparente nas bordas de cima (top pixels) e
    de baixo (SYNOPSIS_FADE pixels), opaca no meio."""
    if (w, h, top) not in FADE_MASKS:
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        mask.fill((255, 255, 255, 255))
        for i in range(SYNOPSIS_FADE):
            mask.fill((255, 255, 255, round(255 * i / SYNOPSIS_FADE)), (0, h - 1 - i, w, 1))
        for i in range(top):
            mask.fill((255, 255, 255, round(255 * i / top)), (0, i, w, 1))
        FADE_MASKS[(w, h, top)] = mask
    return FADE_MASKS[(w, h, top)]


def looking(ui, x, y, w=None):
    """O aviso de que o scrape sozinho esta buscando a arte do jogo."""
    label = "LOOKING FOR ART..." if w is None or w >= tiny.width("LOOKING FOR ART...") + 6 else "SCRAPING..."
    w = w or tiny.width(label) + 8
    W.block(ui, (x, y, w, 10), T.BG_DEEP, None)
    pygame.draw.rect(ui, T.CYAN, (x, y, w, 10), 1)
    tiny.centered(ui, label, T.CYAN, x + w // 2, y + 3)


def full_shade(fe):
    """O escuro em cima e embaixo da imagem da tela cheia (feito uma vez)."""
    key = ("full_shade",)
    if key not in fe.media:
        shade = pygame.Surface((WW, HH), pygame.SRCALPHA)
        for y in range(HH):
            a = int(120 * (1 - y / 40)) if y < 40 else (int(165 * min(1, (y - (HH - 115)) / 60)) if y > HH - 115 else 0)
            pygame.draw.line(shade, T.SPACE + (max(0, a),), (0, y), (WW, y))
        remember(fe, key, shade)
    return fe.media[key]


def thumb_dim(fe):
    key = ("thumb_dim",)
    if key not in fe.media:
        dim_ = pygame.Surface((THUMB[0] - 2, THUMB[1] - 2), pygame.SRCALPHA)
        dim_.fill(T.SPACE + (115,))
        remember(fe, key, dim_)
    return fe.media[key]


def full_picture(fe, i):
    """O fundo da tela cheia para o jogo da linha i: o do escolhido e o
    video com o som (o Player); o dos outros, o video mudo ja aberto
    (fevideo.Grid) ou a imagem."""
    g = fe.rows[i][0]
    frame_ = None
    if getattr(fe, "video_ok", False):
        path = video_path(fe, g)
        if i == fe.cursor:
            fe.video_used = True
            start = fe.grid.offset(path, WW, HH) if getattr(fe, "grid", None) is not None else 0.0
            frame_ = fe.player.request(path, WW, HH, fe.abs_now, start)
        if frame_ is None and getattr(fe, "grid", None) is not None:
            frame_ = fe.grid.frame(path, WW, HH)
    if frame_:
        return pygame.image.frombuffer(frame_, (WW, HH), "RGB")
    return image(fe, media(fe, g, "snap") or media(fe, g, "box"), WW, HH, "cover")


def full_background(fe, back):
    """O fundo desliza com o cursor, como a coluna de miniaturas: o jogo de
    antes sai e o novo entra (de baixo, andando para baixo). Os videos de
    PRELOAD_ROWS jogos antes e depois ficam abertos, parados no primeiro
    quadro, para o novo ja entrar tocando."""
    pos = ease(fe, "full_bg", fe.cursor, fe.abs_now)
    base = int(math.floor(pos))
    frac = pos - base
    shown = [base] if frac < 0.002 else [base, base + 1]
    for i in shown:
        if 0 <= i < len(fe.rows):
            pic = full_picture(fe, i)
            if pic:
                back.blit(pic, (0, round((i - pos) * HH)))
    if getattr(fe, "grid", None) is not None:
        if getattr(fe, "video_ok", False):
            def paths(idx):
                return [p for p in (video_path(fe, fe.rows[k][0]) for k in idx if 0 <= k < len(fe.rows)) if p]
            near = range(fe.cursor - PRELOAD_ROWS, fe.cursor + PRELOAD_ROWS + 1)
            # O do jogo escolhido fica parado no primeiro quadro, o mesmo
            # com que o video com som (o Player) comeca: a troca entre os
            # dois nao pisca.
            fe.grid.update(paths([i for i in shown if i != fe.cursor]), paths(near), WW, HH)
        else:
            fe.grid.stop()
    back.blit(full_shade(fe), (0, 0))


def clone_badge(ui, right, y):
    """O selo do clone, no canto de cima a direita da miniatura da tela
    cheia e da grade (a seta para cima: o jogo pai vem antes); devolve onde comeca."""
    label = "CLONE"
    w = tiny.width(label) + 6
    x = right - w
    # Fino e discreto: um fundo preto leve e transparente, 1 pixel de
    # folga em volta da seta e do texto.
    shade = pygame.Surface((w, 7), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 110))
    ui.blit(shade, (x, y))
    ui.fill(T.ORANGE, (x + 2, y + 1, 1, 1))
    ui.fill(T.ORANGE, (x + 1, y + 2, 3, 1))
    ui.fill(T.ORANGE, (x + 2, y + 3, 1, 3))
    tiny.text(ui, label, T.ORANGE, x + 5, y + 1)
    return x


def draw_full(fe, ui, back, now):
    game = fe.game()
    with part(fe, back, "picture") as s:
        full_background(fe, s)
    cat = fe.category()
    with part(fe, ui, "title") as s:
        W.text(s, (cat or {}).get("name", "").upper()[:24], T.RED, SX, 12)
        for i, c in enumerate(W.RAINBOW):
            pygame.draw.rect(s, c, (SX, 24 + i, 40, 1))
    with part(fe, ui, "chrome") as s:
        W.text(s, "%d/%d" % (fe.cursor + 1, len(fe.rows)), T.FG, SX + SW, 12, right=True)
        # O modo comercial: o indicador no canto de cima, a esquerda.
        if fe.commercial:
            coin_box(fe, s, SX, 34, now)
        if fe.scraping is game:
            looking(s, SX, 38 + COIN_H if fe.commercial else 36)
    # A lista na direita: quatro miniaturas empilhadas, a do jogo escolhido
    # acesa, com uma seta em cima e embaixo enquanto ha mais jogos para
    # aquele lado. A coluna e a moldura rosa deslizam ate o lugar novo.
    (tw, th), gap, n = THUMB, 4, (5 if T.VERTICAL else 4)
    step = th + gap
    tx = SX + SW - tw
    ty = 38
    top = max(0, min(fe.cursor - 1, len(fe.rows) - n))
    now = fe.abs_now
    ftop = ease(fe, "full_top", top, now)
    fsel = ease(fe, "full_sel", fe.cursor, now)
    with part(fe, ui, "chrome") as s:
        arrow(s, tx + tw // 2, ty - 7, (0, -1), T.PINK if top > 0 else T.LINE, 5)
    ui.set_clip((tx - 2, ty - 1, tw + 6, n * step - gap + 4))
    first = int(math.floor(ftop))
    for i in range(max(0, first), min(len(fe.rows), first + n + 1)):
        y = round(ty + (i - ftop) * step)
        with part(fe, ui, "thumb", i - first) as s:
            full_thumb(fe, s, i, tx, y, tw, th)
    with part(fe, ui, "chrome") as s:
        y = round(ty + (fsel - ftop) * step)
        pygame.draw.rect(s, T.PINK, (tx, y, tw, th), 2)
    ui.set_clip(None)
    more = top + n < len(fe.rows)
    with part(fe, ui, "chrome") as s:
        arrow(s, tx + tw // 2, ty + n * step + 3, (0, 1), T.PINK if more else T.LINE, 5)
    # O jogo escolhido, embaixo a esquerda (fora da coluna).
    right = tx - 8
    clone = is_clone(fe, game)
    logo = None if clone else image(fe, media(fe, game, "logo"), min(200, right - SX), 44)
    if logo:
        with part(fe, ui, "logo") as s:
            s.blit(logo, (SX, HH - 62 - logo.get_height()))
    y = HH - 56
    with part(fe, ui, "text") as s:
        if clone:
            # O clone: o logo seria o do pai; o nome completo dele, correndo.
            ticker(s, text_img((game.get("Title") or game["Name"]).upper(), T.YELLOW, big=True),
                   SX, y, right - SX, now)
        else:
            s.blit(W.big(fit(fe.fd.short_title(game), right - SX), 1, W.LABEL), (SX, y))
        W.text(s, fit(facts_line(game), right - SX), T.CYAN, SX, y + 12)
    with part(fe, ui, "icons") as s:
        icon_line(fe, s, game, SX, y + 24, right, 12)
        lit = link_mark(fe, game)
        if lit is not None:
            # O link, no fim da linha dos icones (os gabinetes da festa ficam nas
            # miniaturas): o globo, aceso se alguem joga.
            globe_icon(s, right - 8, y + 30, 6, lit)


def full_thumb(fe, ui, i, tx, y, tw, th):
    """A miniatura do jogo da linha i na coluna da tela cheia."""
    g = fe.rows[i][0]
    on = i == fe.cursor
    W.block(ui, (tx, y, tw, th), T.BG_DEEP, T.LINE)
    thumb = image(fe, media(fe, g, "snap") or media(fe, g, "box"), tw - 2, th - 2, "cover")
    if thumb:
        ui.blit(thumb, (tx + 1, y + 1))
        if not on:
            ui.blit(thumb_dim(fe), (tx + 1, y + 1))
    else:
        # No clone, o texto comeca embaixo do selo.
        top = 11 if fe.rows[i][1] else 5
        for j, line in enumerate(W.wrap(fe.fd.short_title(g).upper(), tw - 6)[:4 if top == 5 else 3]):
            tiny.text(ui, tiny.fit(line, tw - 6), T.FG if on else T.COMMENT, tx + 3, y + top + j * 8)
    pygame.draw.rect(ui, T.LINE, (tx, y, tw, th), 1)
    clone = fe.rows[i][1]
    if clone:
        clone_badge(ui, tx + tw - 1, y + 1)
    if g.get("Favourite") == "1":
        # No clone a estrela vai para a esquerda: a direita e do selo.
        star(ui, tx + 6 if clone else tx + tw - 6, y + 6, T.YELLOW, 4)
    link_badge(fe, ui, g, tx + 1, y + 1, tw - 2, th - 2)


def grid_image(fe, g, w, h):
    """A miniatura 4:3 da grade: a tela do jogo cortada para encher; sem
    ela, a capa inteira."""
    shot = media(fe, g, "snap")
    if shot:
        return image(fe, shot, w, h, "cover")
    return image(fe, media(fe, g, "box"), w, h)


def video_path(fe, game):
    key = ("video", game["_system"]["key"], game["Name"])
    if key not in fe.media:
        remember(fe, key, fe.lib.video(game))
    return fe.media[key]


def grid_picture(fe, g, w, h, index):
    """A miniatura da grade: o video do jogo (o do escolhido com o som, pelo
    Player; os outros mudos, pelo fevideo.Grid) ou a imagem."""
    frame_ = None
    if getattr(fe, "video_ok", False):
        path = video_path(fe, g)
        if index == fe.cursor:
            fe.video_used = True
            start = fe.grid.offset(path, w, h) if getattr(fe, "grid", None) is not None else 0.0
            frame_ = fe.player.request(path, w, h, fe.abs_now, start)
        if frame_ is None and getattr(fe, "grid", None) is not None:
            frame_ = fe.grid.frame(path, w, h)
    if frame_:
        return pygame.image.frombuffer(frame_, (w, h), "RGB")
    return grid_image(fe, g, w, h)


def grid_videos(fe, top_row, rows_shown, w, h):
    """Os videos da grade: tocando os das fileiras a vista, prontos (parados no
    primeiro quadro) os de PRELOAD_ROWS fileiras antes e depois."""
    if getattr(fe, "grid", None) is None:
        return
    if not getattr(fe, "video_ok", False):
        fe.grid.stop()
        return
    cols = GRID_COLS

    def paths(r0, r1):
        out = []
        for i in range(max(0, r0) * cols, min(len(fe.rows), r1 * cols)):
            p = video_path(fe, fe.rows[i][0])
            if p:
                out.append(p)
        return out
    visible = paths(top_row, top_row + rows_shown + 1)
    preload = paths(top_row - PRELOAD_ROWS, top_row) + paths(top_row + rows_shown + 1,
                                                              top_row + rows_shown + 1 + PRELOAD_ROWS)
    # O escolhido parado no primeiro quadro, ate o video com som (o Player)
    # chegar nele: sem a piscada da troca.
    chosen = video_path(fe, fe.rows[fe.cursor][0]) if fe.rows else None
    if chosen in visible:
        visible.remove(chosen)
        preload.append(chosen)
    fe.grid.update(visible, preload, w, h)


def draw_flow(fe, ui, now):
    with part(fe, ui, "title") as s:
        frame(fe, s)
    # A grade: tres por fileira, miniaturas 4:3 (3:4 no monitor em pe) com a
    # tela do jogo (sem ela, a capa inteira); a esquerda as setas de quando
    # ha mais fileiras, no canto direito a barra de rolagem.
    (tw, th), (bw, bh), rows_shown, gap = grid_geom(fe)
    cols = GRID_COLS
    x0 = SX + (SW - 8 - (cols * tw + (cols - 1) * gap)) // 2
    y0 = 40 if th <= 60 else 38
    step_y = th + (8 if th <= 60 else 4)
    row, top_row = fe.cursor // cols, fe.top // cols
    if row < top_row:
        top_row = row
    elif row > top_row + rows_shown - 1:
        top_row = row - rows_shown + 1
    fe.top = top_row * cols
    total_rows = (len(fe.rows) + cols - 1) // cols
    # As fileiras deslizam ate o lugar novo, e a moldura rosa ate o jogo
    # escolhido; todo jogo do mesmo tamanho, nenhum escurecido.
    now_abs = fe.abs_now
    ftop = ease(fe, "flow_top", top_row, now_abs)
    frow = ease(fe, "flow_row", row, now_abs)
    fcol = ease(fe, "flow_col", fe.cursor % cols, now_abs)
    gw = cols * tw + (cols - 1) * gap
    ui.set_clip((x0 - 3, y0 - 3, gw + 6, rows_shown * step_y + 2))
    sel = None
    first_row = int(math.floor(ftop))
    for i in range(first_row * cols, min(len(fe.rows), (first_row + rows_shown + 1) * cols)):
        r, c = divmod(i, cols)
        x, y = x0 + c * (tw + gap), round(y0 + (r - ftop) * step_y)
        if i == fe.cursor:
            sel = fe.rows[i][0]
        # As cartas viram na diagonal, do canto de cima a esquerda.
        with part(fe, ui, "thumb", r - first_row + c) as s:
            flow_thumb(fe, s, i, x, y, tw, th)
    grid_videos(fe, top_row, rows_shown, tw - 2, th - 2)
    with part(fe, ui, "chrome") as s:
        fx = round(x0 + fcol * (tw + gap))
        fy = round(y0 + (frow - ftop) * step_y)
        pygame.draw.rect(s, T.PINK, (fx - 2, fy - 2, tw + 4, th + 4), 2)
    ui.set_clip(None)
    with part(fe, ui, "chrome") as s:
        # No canto, a barra de rolagem com uma seta pequena em cima e embaixo.
        bx_, by_, bh_ = SX + SW - 2, y0 + 7, rows_shown * step_y - 22
        W.scrollbar(s, bx_, by_, bh_, top_row, rows_shown, max(rows_shown, total_rows))
        arrow(s, bx_ + 2, by_ - 4, (0, -1), T.PINK if top_row > 0 else T.LINE, 3)
        arrow(s, bx_ + 2, by_ + bh_ + 4, (0, 1), T.PINK if top_row + rows_shown < total_rows else T.LINE, 3)
        if sel:
            # A aba debaixo das miniaturas, do lado do jogo escolhido: mais um
            # toque para aquele lado troca a romlist.
            col = fe.cursor % cols
            if len(fe.cats) > 1 and (col == cols - 1 or fe.cursor == len(fe.rows) - 1 or col == 0):
                side = 1 if (col == cols - 1 or fe.cursor == len(fe.rows) - 1) else -1
                nxt = fe.cats[(fe.cat + side) % len(fe.cats)]["name"].upper()
                bottom_tab(s, nxt, side, x0, gw, y0 + rows_shown * step_y - 4)
    g = fe.game()
    # No modo comercial o logo, os textos e os icones sobem um pouco, os
    # icones vao em duas linhas, e o indicador fica no canto de baixo a
    # direita.
    commercial = fe.commercial
    y = HH - 52 if commercial else HH - 46
    clone = is_clone(fe, g)
    # Em pe nao ha largura para o logo, os icones e o indicador: o nome.
    vertical = getattr(fe, "vertical", False)
    narrow = commercial and vertical
    logo = None if clone or narrow else image(fe, media(fe, g, "logo"), 110, 30)
    # Em pe, uma margem a direita (o texto nao encosta na borda da tela) e o
    # que nao cabe corre em circulo.
    right = SX + SW - (8 if vertical else 0)
    tx = SX
    if logo:
        with part(fe, ui, "logo") as s:
            blit_center(s, logo, SX, y, 110, 30)
        tx = SX + 118
    with part(fe, ui, "text") as s:
        if logo:
            facts_x, facts_w = tx, right - tx
        else:
            if vertical:
                title = (g.get("Title") or g["Name"]) if clone else fe.fd.short_title(g)
                ticker(s, text_img(title.upper(), T.YELLOW), SX, y + 2, 92, now)
            elif clone:
                # O clone: o nome completo, correndo (o logo seria o do pai).
                ticker(s, text_img((g.get("Title") or g["Name"]).upper(), T.YELLOW), SX, y + 2, 150, now)
            else:
                W.text(s, fit(fe.fd.short_title(g), 150), T.YELLOW, SX, y + 2)
            facts_x, facts_w = (SX + 100, right - SX - 100) if vertical else (SX + 154, 150)
            tx = SX
        if vertical:
            ticker(s, text_img(facts_line(g).upper(), T.CYAN), facts_x, y + 2, facts_w, now)
        else:
            W.text(s, fit(facts_line(g), facts_w), T.CYAN, facts_x, y + 2)
    with part(fe, ui, "icons") as s:
        if commercial:
            bx, by = SX + SW - COIN_W, HH - COIN_H - 8
            rows = icon_rows(fe, g, 12)
            icon_line(fe, s, g, tx, y + 13, bx - 4, 12, rows[:2])
            icon_line(fe, s, g, tx, y + 26, bx - 4, 12, rows[2:])
            coin_box(fe, s, bx, by, now)
        else:
            icon_line(fe, s, g, tx, y + 14, right, 12)


def flow_thumb(fe, ui, i, x, y, tw, th):
    """A miniatura do jogo da linha i na grade."""
    g = fe.rows[i][0]
    pygame.draw.rect(ui, T.BG_DEEP, (x, y, tw, th))
    img = grid_picture(fe, g, tw - 2, th - 2, i)
    if img:
        blit_center(ui, img, x, y, tw, th)
    else:
        # No clone, o texto comeca embaixo do selo.
        top = 10 if fe.rows[i][1] else 4
        for k, line in enumerate(W.wrap(fe.fd.short_title(g).upper(), tw - 6)[:4]):
            tiny.text(ui, tiny.fit(line, tw - 6), T.FG if i == fe.cursor else T.COMMENT,
                      x + 3, y + top + k * 8)
    pygame.draw.rect(ui, T.LINE, (x, y, tw, th), 1)
    clone = fe.rows[i][1]
    if clone:
        clone_badge(ui, x + tw - 1, y + 1)
    if g.get("Favourite") == "1":
        # No clone a estrela vai para a esquerda: a direita e do selo.
        star(ui, x + 6 if clone else x + tw - 6, y + 6, T.YELLOW, 4)
    link_badge(fe, ui, g, x + 1, y + 1, tw - 2, th - 2)
    if fe.scraping is g:
        looking(ui, x + 2, y + th - 12, tw - 4)


def bottom_tab(ui, label, side, x0, width, y):
    """A aba deitada da proxima romlist, encostada no lado (side 1: a
    direita, -1: a esquerda) da faixa de x0 a x0 + width."""
    label = tiny.fit(label, width - 30)
    w = tiny.width(label) + 22
    x = x0 + width - w if side > 0 else x0
    W.block(ui, (x, y, w, 11), T.PINK, T.PURPLE)
    if side > 0:
        tiny.text(ui, label, T.SPACE, x + 5, y + 3)
        arrow(ui, x + w - 7, y + 5, (1, 0), T.SPACE, 4)
    else:
        arrow(ui, x + 6, y + 5, (-1, 0), T.SPACE, 4)
        tiny.text(ui, label, T.SPACE, x + 15, y + 3)


def edge_tab(ui, label, side):
    tab = pygame.Surface((tiny.width(label) + 8, 7), pygame.SRCALPHA)
    tiny.text(tab, label, T.SPACE, 4, 1)
    tab = pygame.transform.rotate(tab, -90 if side > 0 else 90)
    h = tab.get_height() + 16
    x = WW - 12 if side > 0 else 0
    y = 60
    W.block(ui, (x, y, 12, h), T.PINK, T.PURPLE)
    ui.blit(tab, (x + 3, y + 3 if side > 0 else y + 13))
    arrow(ui, x + 6, y + h - 7 if side > 0 else y + 6, (side, 0), T.SPACE, 4)


# ── Por cima ───────────────────────────────────────────────────────

def dim(back, alpha=170):
    d = pygame.Surface((WW, HH), pygame.SRCALPHA)
    d.fill(T.SPACE + (alpha,))
    back.blit(d, (0, 0))


def card(ui, rect):
    W.block(ui, rect, T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.PINK, rect, 1)


def view_icon(surf, cx, cy, c):
    """O modo de ver: quatro quadradinhos."""
    for dx in (-4, 1):
        for dy in (-4, 1):
            surf.fill(c, (cx + dx, cy + dy, 4, 4))


def exit_icon(surf, cx, cy, c):
    """Fechar o jogo: um X."""
    pygame.draw.line(surf, c, (cx - 4, cy - 4), (cx + 4, cy + 4), 3)
    pygame.draw.line(surf, c, (cx - 4, cy + 4), (cx + 4, cy - 4), 3)


def reset_icon(surf, cx, cy, c):
    """Voltar ao padrao: uma volta com a ponta da seta."""
    pygame.draw.circle(surf, c, (cx, cy), 5, 2)
    pygame.draw.polygon(surf, c, [(cx + 2, cy - 7), (cx + 6, cy - 4), (cx + 2, cy - 2)])


def save_icon(surf, cx, cy, c):
    """Salvar: um visto."""
    pygame.draw.lines(surf, c, False, [(cx - 5, cy), (cx - 1, cy + 4), (cx + 5, cy - 4)], 3)


def options_icon(surf, cx, cy, c):
    """As opcoes do Tab: tres linhas."""
    for dy in (-4, 0, 4):
        surf.fill(c, (cx - 5, cy + dy - 1, 11, 2))


# As funcoes do frontend (feinput.FUNCTIONS): o nome, a cor e o desenho no
# topo do botao, no guia dos controles e no Frontend controls.
FUNCTION_NAMES = {"up": "GAMES UP", "down": "GAMES DOWN", "left": "LIST LEFT", "right": "LIST RIGHT",
                  "b1": "SELECT", "b2": "BACK", "b3": "PAGE UP", "b6": "PAGE DOWN", "b4": "FAVOURITE",
                  "b5": "FILTER", "start": "VIEW MODE", "tab": "GAME OPTIONS"}
FUNCTION_STYLE = {
    "up": (T.CYAN, lambda s, x, y, c: arrow(s, x, y, (0, -1), c, 6)),
    "down": (T.CYAN, lambda s, x, y, c: arrow(s, x, y, (0, 1), c, 6)),
    "left": (T.PINK, lambda s, x, y, c: arrow(s, x, y, (-1, 0), c, 6)),
    "right": (T.PINK, lambda s, x, y, c: arrow(s, x, y, (1, 0), c, 6)),
    "b1": (T.GREEN, menu_icon), "b2": (T.RED, back_icon),
    "b3": (T.CYAN, lambda s, x, y, c: chevrons(s, x, y, c, True)),
    "b6": (T.CYAN, lambda s, x, y, c: chevrons(s, x, y, c, False)),
    "b4": (T.YELLOW, lambda s, x, y, c: star(s, x, y + 1, c)), "b5": (T.PURPLE, funnel),
    "start": (T.ORANGE, view_icon), "tab": (T.PINK, options_icon)}
# No direcional, a funcao da propria direcao leva o nome curto (a seta ja diz
# para onde).
STICK_NAMES = {"up": "GAMES", "down": "GAMES", "left": "GAME LIST", "right": "GAME LIST"}


def shade(color, k):
    """A cor mais escura (k < 1) ou mais clara (k > 1)."""
    if k < 1:
        return tuple(int(c * k) for c in color)
    return tuple(min(255, int(c + (255 - c) * (k - 1))) for c in color)


FLAT, LIFT = 0.62, 4       # o botao visto de cima e de lado: a elipse e a altura


def ellipse(ui, color, cx, cy, rx, ry, width=0):
    pygame.draw.ellipse(ui, color, (cx - rx, cy - ry, 2 * rx, 2 * ry), width)


def button3d(ui, cx, cy, r, color):
    """O botao do painel em perspectiva, visto um pouco de cima: o aro preto
    no painel, o lado do botao (um cilindro mais escuro) e o topo, com o
    brilho. (cx, cy) e o centro do topo."""
    ry = round(r * FLAT)
    # O aro, no painel, um pouco maior e abaixo do topo.
    ellipse(ui, (0x10, 0x10, 0x16), cx, cy + LIFT + 1, r + 4, ry + 3)
    ellipse(ui, T.LINE, cx, cy + LIFT + 1, r + 4, ry + 3, 1)
    # O lado: a elipse de baixo e o retangulo ate o topo.
    side = shade(color, 0.5)
    ellipse(ui, shade(color, 0.35), cx, cy + LIFT, r, ry)
    ui.fill(side, (cx - r, cy, 2 * r, LIFT))
    pygame.draw.line(ui, shade(color, 0.7), (cx - r + 2, cy + 1), (cx - r + 2, cy + LIFT))
    # O topo e o brilho do lado da luz (em cima, a esquerda).
    ellipse(ui, color, cx, cy, r, ry)
    ellipse(ui, shade(color, 1.35), cx - r // 3, cy - ry // 3, r // 2, max(1, ry // 3))
    ellipse(ui, shade(color, 0.6), cx, cy, r, ry, 1)


# O formato do painel (Frontend controls > Panel layout): seis botoes em duas
# fileiras, quatro em linha como o do Neo Geo MVS, tres ou dois em linha, ou
# dois um em cima do outro. O guia so desenha os botoes que ele tem.
PANEL_LAYOUTS = (("6", "6 BUTTONS"), ("4", "4 IN LINE (MVS)"), ("3", "3 IN LINE"), ("2", "2 IN LINE"),
                 ("2v", "2 STACKED"))
PANEL_COUNT = {"6": 6, "4": 4, "3": 3, "2": 2, "2v": 2}


def panel_layout(fe):
    layout = getattr(fe, "panel_layout", "6")
    return layout if layout in PANEL_COUNT else "6"


def panel_slots(layout, where, buttons, step):
    """Onde cada botao fica no guia: {botao: (dx, dy, subido, lado do nome,
    alinhamento)}. dx a partir do meio; dy a fileira (0 e 32, ou 16 numa
    fileira so); os do meio de uma fileira sobem 3 pixels, como num painel.
    O nome vai em cima ("up") ou embaixo; no de 6 botoes os das pontas
    encostam do lado de fora (-1, 1), nas fileiras so alternam em cima e
    embaixo (centrados, 0). No de 6, a posicao e a do Buttons layout (where)."""
    slots = {}
    for b in buttons:
        n = int(b[1:])
        if layout == "6":
            i = where[n - 1] - 1
            col, row = i % 3, i // 3
            slots[b] = ((col - 1) * step, row * 32, 3 if col == 1 else 0, "down" if row else "up", col - 1)
        elif layout == "2v":
            slots[b] = (0, (n - 1) * 32, 0, "down" if n > 1 else "up", 0)
        else:
            count, i = PANEL_COUNT[layout], n - 1
            raised = 3 if 0 < i < count - 1 else 0
            slots[b] = (round((i - (count - 1) / 2) * step), 16, raised, "down" if i % 2 else "up", 0)
    return slots


def guide_map(fe):
    """O que o guia desenha, do Frontend controls: {comando do painel: funcao}.
    Um botao que o formato do painel nao tem (o 5 num MVS) e como nenhum."""
    count = PANEL_COUNT[panel_layout(fe)]
    return {b["pad"]: f for f, b in fe.input.binds.items()
            if b["pad"] and not (b["pad"][0] == "b" and int(b["pad"][1:]) > count)}


def stick_parts(pad):
    """O direcional do guia, em volta do centro (0, 0): [(direcao, funcao,
    nome, cor)] e os limites (esquerda, cima, direita, baixo) com os nomes."""
    parts = []
    for direction in ("up", "down", "left", "right"):
        f = pad.get(direction)
        if f:
            parts.append((direction, f, STICK_NAMES[f] if f == direction else FUNCTION_NAMES[f],
                          FUNCTION_STYLE[f][0]))
    widths = {d: tiny.width(label) for d, _, label, _ in parts}
    hold = pad.get("down") in ("up", "down") or pad.get("up") in ("up", "down")
    side = max([35, widths.get("up", 0) // 2, widths.get("down", 0) // 2]
               + ([tiny.width("3 S: LETTER BY LETTER") // 2] if hold else []))
    left = -max(side, 19 + widths.get("left", 0))
    right = max(side, 19 + widths.get("right", 0))
    top = -44 if "up" in widths else -35
    bottom = 61 if hold else (45 if "down" in widths else 35)
    return parts, hold, (left, top, right, bottom)


def button_parts(layout, where, pad, buttons, step=30, r=12):
    """Os botoes do guia em volta do centro (0, 0) do painel: [(botao,
    funcao, x, y do topo, nome, x do nome, y do nome, lado)] e os limites
    (esquerda, cima, direita, baixo) com os nomes."""
    ry = round(r * FLAT)
    slots = panel_slots(layout, where, buttons, step)
    # A largura do nome do botao do meio de cada fileira (o de 6 botoes).
    middle = {dy: tiny.width(b[1:] + " " + FUNCTION_NAMES[pad[b]])
              for b, (_, dy, _, _, align) in slots.items() if layout == "6" and align == 0}
    parts, xs, ys = [], [], []
    for b in buttons:
        dx, dy, raised, side, align = slots[b]
        cy = dy - raised
        text = b[1:] + " " + FUNCTION_NAMES[pad[b]]
        w = tiny.width(text)
        # Um nome longo no meio (GAME OPTIONS) empurra os dos lados para fora.
        mid = middle.get(dy, 0) // 2 + 4
        tx = {-1: min(dx + 3, dx + step - mid) - w, 0: dx - w // 2, 1: max(dx - 3, dx - step + mid)}[align]
        ty = dy - 30 if side == "up" else cy + LIFT + ry + 18
        parts.append((b, pad[b], dx, cy, text, tx, ty, side))
        xs += [dx - r - 4, dx + r + 4, tx, tx + w]
        ys += [cy - ry - 4, cy + LIFT + ry + 4, ty, ty + 5]
    return parts, ((min(xs), min(ys), max(xs), max(ys)) if parts else (0, 0, 0, 0))


def draw_guide(fe, ui):
    """O guia dos controles, do jeito que o Frontend controls os deixou: o
    direcional com a funcao de cada direcao e os botoes no formato do painel,
    cada um na cor da funcao dele. Um comando sem funcao nao aparece (o
    direcional sem nenhuma, nem ele). Os dois ficam no meio da janela."""
    # Deitado, o direcional a esquerda e os botoes a direita; em pe, o
    # direcional em cima e os botoes embaixo.
    vertical = T.VERTICAL is not None
    pw, ph = SW, (276 if vertical else 162)
    px, py = SX, (HH - ph) // 2 + 6
    card(ui, (px, py, pw, ph))
    title = "CONTROLS"
    ui.blit(W.big(title, 1, W.LABEL), (px + 10, py + 9))
    for i, c in enumerate(W.RAINBOW):
        pygame.draw.rect(ui, c, (px + 18 + W.width(title), py + 10 + i, pw - 28 - W.width(title), 1))
    pad = guide_map(fe)
    # Os botoes que o painel tem (o formato dele) e que fazem alguma coisa.
    layout = panel_layout(fe)
    buttons = ["b%d" % n for n in range(1, PANEL_COUNT[layout] + 1) if pad.get("b%d" % n)]
    try:
        where = fe.fd.web.button_layout(6)
    except Exception:  # sem o painel web (os testes): a ordem do painel
        where = list(range(1, 7))
    sparts, hold, (sl, st, sr, sb) = stick_parts(pad)
    bparts, (bl, bt, br, bb) = button_parts(layout, where, pad, buttons)
    split = bool(sparts and bparts)
    # A area entre o titulo e o "PRESS ANY BUTTON", e o espaco entre os dois.
    top, bottom, gap = py + 28, py + ph - 22, 24
    if vertical:
        # Um em cima do outro, os dois no meio da largura e o par no meio da altura.
        hs, hb = (sb - st if sparts else 0), (bb - bt if bparts else 0)
        y = (top + bottom - hs - hb - (gap if split else 0)) // 2
        jx, jy = WW // 2 - (sl + sr) // 2, y - st
        mx, by0 = WW // 2 - (bl + br) // 2, y + hs + (gap if split else 0) - bt
        if split:
            pygame.draw.line(ui, T.LINE, (px + 10, y + hs + gap // 2), (px + pw - 11, y + hs + gap // 2))
    else:
        # Lado a lado, o par no meio da largura; cada um no meio da altura.
        ws, wb = (sr - sl if sparts else 0), (br - bl if bparts else 0)
        x = WW // 2 - (ws + wb + (gap if split else 0)) // 2
        jx, mx = x - sl, x + ws + (gap if split else 0) - bl
        jy, by0 = (top + bottom) // 2 - (st + sb) // 2, (top + bottom) // 2 - (bt + bb) // 2
        if split:
            pygame.draw.line(ui, T.LINE, (x + ws + gap // 2, top), (x + ws + gap // 2, bottom - 4))
    if sparts:
        pygame.draw.circle(ui, T.SPACE, (jx, jy), 21)
        pygame.draw.circle(ui, T.LINE, (jx, jy), 21, 2)
        pygame.draw.circle(ui, T.RED, (jx, jy), 9)
        pygame.draw.circle(ui, (0xff, 0xa0, 0xa0), (jx - 3, jy - 3), 3)
        for direction, f, label, color in sparts:
            d = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}[direction]
            arrow(ui, jx + d[0] * 30, jy + d[1] * 30, d, color, 5)
            if direction == "up":
                tiny.centered(ui, label, color, jx, jy - 44)
            elif direction == "down":
                tiny.centered(ui, label, color, jx, jy + 40)
            elif direction == "left":
                tiny.text(ui, label, color, jx - 19 - tiny.width(label), jy + 9)
            else:
                tiny.text(ui, label, color, jx + 19, jy + 9)
        # Segurar acelera o que anda pelos jogos (onde quer que esteja).
        if hold:
            tiny.centered(ui, "HOLD: FASTER", T.COMMENT, jx, jy + 49)
            tiny.centered(ui, "3 S: LETTER BY LETTER", T.COMMENT, jx, jy + 56)
    # Os botoes, o nome de cada um fora, em cima ou embaixo, com uma linha e a
    # seta ate ele.
    r = 12
    ry = round(r * FLAT)
    for b, f, dx, dy, text, tx, ty, side in bparts:
        color, draw_icon = FUNCTION_STYLE[f]
        cx, cy = mx + dx, by0 + dy
        button3d(ui, cx, cy, r, color)
        # O desenho no topo, achatado como ele.
        icon = pygame.Surface((24, 24), pygame.SRCALPHA)
        draw_icon(icon, 12, 12, shade(color, 0.3))
        icon = pygame.transform.smoothscale(icon, (24, round(24 * FLAT)))
        ui.blit(icon, (cx - 12, cy - icon.get_height() // 2))
        tiny.text(ui, text, T.FG, mx + tx, by0 + ty)
        if side == "up":
            y0, y1, d = by0 + ty + 7, cy - ry - 4, (0, 1)
        else:
            y0, y1, d = by0 + ty - 2, cy + LIFT + ry + 5, (0, -1)
        pygame.draw.line(ui, T.COMMENT, (cx, y0), (cx, y1 - d[1] * 2))
        arrow(ui, cx, y1, d, T.COMMENT, 3)
    msg = "PRESS ANY BUTTON TO START"
    ui.blit(W.big(msg, 1, W.LABEL), (px + (pw - W.width(msg)) // 2, py + ph - 16))


HINT_H = 22                 # a altura do botao de uma dica (button_hint)


def button_hint(ui, x, y, items):
    """As dicas de uma janela com os botoes do guia: para cada (funcao, nome),
    um botao com a borda na cor da funcao e, dentro dele, o botao pequeno do
    painel (com o desenho da funcao no topo) e o nome. (x, y) e o canto de
    cima a esquerda da linha; cada botao tem HINT_H de altura."""
    r = 7
    for f, label in items:
        color, draw_icon = FUNCTION_STYLE[f]
        w = 2 * r + 16 + W.width(label) + 8
        W.block(ui, (x, y, w, HINT_H), T.BG_DEEP, None)
        ui.fill(shade(color, 0.25), (x + 1, y + 1, w - 2, HINT_H - 2))
        pygame.draw.rect(ui, color, (x, y, w, HINT_H), 1)
        cx, cy = x + r + 7, y + 8
        button3d(ui, cx, cy, r, color)
        icon = pygame.Surface((24, 24), pygame.SRCALPHA)
        draw_icon(icon, 12, 12, shade(color, 0.3))
        icon = pygame.transform.smoothscale(icon, (14, round(14 * FLAT)))
        ui.blit(icon, (cx - 7, cy - icon.get_height() // 2))
        W.text(ui, label, T.FG, cx + r + 7, y + 7)
        x += w + 6


LINK_KINDS = ("link", "join", "new", "closed")


def popup_icon(ui, kind, cx, cy, on, lit=False, net=False):
    """O icone de um azulejo do menu do jogo (net: os controles, no lugar do globo)."""
    if kind == "play":
        play_icon(ui, cx, cy, T.GREEN if on else T.COMMENT)
    elif kind in ("link", "join", "new", "closed"):
        if net:
            pads_icon(ui, cx, cy, lit or on)
        else:
            globe_icon(ui, cx, cy, 10, lit, GREEN_MID if on else GREEN_DIM)
        if kind == "new":
            ui.fill(T.GREEN, (cx + 4, cy + 6, 7, 2))
            ui.fill(T.GREEN, (cx + 6, cy + 4, 2, 7))
    elif kind == "net":
        pads_icon(ui, cx, cy, on)
    elif kind == "fav":
        star(ui, cx, cy, T.YELLOW if on else T.COMMENT, 11, outline=False)
    else:
        plus_icon(ui, cx, cy, T.CYAN if on else T.COMMENT)


def draw_popup(fe, ui, now):
    """O menu do jogo: os azulejos (jogar, o link se o jogo tem, os favoritos e
    o "+") com o nome do escolhido embaixo. Um jogo de link ainda mostra, sob o
    nome, os gabinetes da festa: acesos os que estao nela e o aro rosa no lugar
    deste."""
    g = fe.game()
    tiles = fe.popup_tiles() if hasattr(fe, "popup_tiles") else [
        {"kind": "play", "label": "PLAY"},
        {"kind": "fav", "label": "UNFAVOURITE" if g.get("Favourite") == "1" else "FAVOURITE"},
        {"kind": "more", "label": "MORE"}]
    n = len(tiles)
    gap = 12 if n <= 3 else 6
    size = 52 if n <= 3 else min(40, (WW - 4 - 28 - gap * (n - 1)) // n)
    pw = max(216, n * size + (n - 1) * gap + 28) if n <= 3 else min(WW - 4, n * size + (n - 1) * gap + 28)
    sel = fe.ov["sel"] % n
    kind = tiles[sel]["kind"]
    # Net play com mais de um controle aqui: a seta embaixo do azulejo chama
    # para baixo, onde as setas dos lados escolhem quantos jogadores este
    # gabinete fornece (fe.ov["row"] 1); o resto desce para dar lugar a ela.
    pick = tiles[sel].get("net") and (tiles[sel].get("most") or 1) > 1 and kind != "closed"
    row = pick and fe.ov.get("row")
    drop = 8 if pick else 0
    host = (tiles[sel].get("party") or {}).get("host")
    ph = 28 + size + 28 + drop + (22 if kind in LINK_KINDS else 0) + (4 if host else 0)
    px, py = (WW - pw) // 2, (HH - ph) // 2 - 4
    card(ui, (px, py, pw, ph))
    W.text(ui, fit(fe.fd.short_title(g), pw - 16), T.YELLOW, px + 8, py + 8)
    tx0 = px + (pw - (n * size + (n - 1) * gap)) // 2
    ty = py + 24
    for i, tile in enumerate(tiles):
        x = tx0 + i * (size + gap)
        on = i == sel
        tile_frame(ui, (x, ty, size, size), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (x, ty, size, size), 2 if on else 1)
        popup_icon(ui, tile["kind"], x + size // 2, ty + size // 2, on, tile.get("lit", False), tile.get("net", False))
    label = tiles[sel]["label"]
    ui.blit(W.big(label, 1, W.LABEL), (px + (pw - W.width(label)) // 2, ty + size + 10 + drop))
    blink = int(now * 2.5) % 2 == 0
    if pick and not row and blink:
        arrow(ui, tx0 + sel * (size + gap) + size // 2, ty + size + 9, (0, 1), T.PINK, 4)
    if kind in LINK_KINDS:
        party = tiles[sel].get("party")
        total = (party or {}).get("max") or tiles[sel].get("max") or 2
        used = party["used"] if party else 0
        # Quem esta (acesos) e o lugar deste gabinete (o aro): o primeiro, numa
        # festa nova, ou o proximo livre, numa que ja existe; numa que ja
        # comecou, nenhum.
        filled = used if kind in ("join", "closed") else 1
        you = {"link": 0, "new": 0, "join": used}.get(kind)
        if tiles[sel].get("net"):
            # Os jogadores: este gabinete ocupa um por controle configurado
            # (take); acesos os que ja tem dono, o aro nos deste.
            take = tiles[sel].get("take", 1)
            lit = used if kind in ("join", "closed") else take
            first = used + 1 if kind == "join" else 1
            width = total * 14 - 4
            slots_row(ui, px + (pw - width) // 2, ty + size + 24 + drop, lit, total,
                      None if kind == "closed" else (first, take))
            if row and blink:
                sx = px + (pw - width) // 2
                arrow(ui, sx - 12, ty + size + 30 + drop, (-1, 0), T.PINK, 4)
                arrow(ui, sx + width + 11, ty + size + 30 + drop, (1, 0), T.PINK, 4)
        else:
            width = total * 11 - 3
            cabinet_row(ui, px + (pw - width) // 2, ty + size + 26, filled, total, you=you, w=8, h=12, gap=3)
        if host:
            # De quem e a party ou o link (o nome do gabinete que abriu).
            tiny.centered(ui, tiny.fit("HOST " + host, pw - 16), T.COMMENT, px + pw // 2, ty + size + 43 + drop)


def draw_lobby(fe, ui, now):
    """A sala de espera do link: os gabinetes da festa acendem conforme chegam,
    cada um com o nome dele (o aro rosa e este), o contador do comeco e uma
    palavra de estado. So os icones, o titulo, os nomes e os numeros: nada de
    frase."""
    lob = fe.link.lobby()
    g = fe.link_game
    if not lob or not g:
        return
    pw, ph = WW - 16, HH - 24
    px, py = 8, 12
    card(ui, (px, py, pw, ph))
    W.text(ui, fit(fe.fd.short_title(g), pw - 40), T.YELLOW, px + 8, py + 8)
    if lob["profile"].get("netplay"):
        pads_icon(ui, px + pw - 14, py + 12, True)
    else:
        globe_icon(ui, px + pw - 14, py + 12, 7, True)
    net = bool(lob["profile"].get("netplay"))
    members = len(lob["members"])
    # No net play so os gabinetes que ja entraram (cada um com os seus jogadores)
    # e, embaixo, os jogadores do jogo.
    total = max(1, members) if net else lob["max"]
    # Em pe (240 de largura), tres por linha: o nome de 12 letras cabe na caixa.
    cols = 4 if WW >= 300 else 3
    cw = (pw - 16) // cols
    rows = (total + cols - 1) // cols
    ch = 52
    y0 = py + 28
    for i in range(total):
        cx, cy = px + 8 + (i % cols) * cw, y0 + (i // cols) * (ch + 4)
        lit = i < members
        you = i + 1 == lob["number"]
        W.block(ui, (cx, cy, cw - 6, ch), T.BG_DEEP, None)
        pygame.draw.rect(ui, T.GREEN if lit else T.LINE, (cx, cy, cw - 6, ch), 1)
        cabinet_icon(ui, cx + (cw - 6) // 2 - 7, cy + 5, 14, 22, lit)
        label = "#%d" % (i + 1)
        if net and i < members:
            m = lob["members"][i]
            label = "P%d" % m["first"] if m["take"] == 1 else "P%d-%d" % (m["first"], m["first"] + m["take"] - 1)
        W.text(ui, label, T.GREEN if lit else T.LINE, cx + (cw - 6 - W.width(label)) // 2, cy + 33)
        if lit:
            # O nome do gabinete (o apelido do Setup, ou a fruta ou o bicho dele).
            name = tiny.fit(lob["members"][i].get("name") or "", cw - 10)
            tiny.text(ui, name, T.FG if you else T.COMMENT, cx + (cw - 6 - tiny.width(name)) // 2, cy + 44)
        if you:
            pygame.draw.rect(ui, T.PINK, (cx - 2, cy - 2, cw - 2, ch + 4), 1)
    y = y0 + rows * (ch + 4) + 4
    if net:
        cap = lob["capacity"]
        width = cap * 14 - 4
        slots_row(ui, px + (pw - width) // 2, y, lob["slots"], cap, (lob["first"], lob["take"]))
        y += 20
    else:
        globe_icon(ui, px + pw // 2 - 22, y + 6, 7, True)
        W.text(ui, "%d/%d" % (members, total), T.GREEN, px + pw // 2 - 10, y + 2)
        y += 22
    left = lob["left"]
    if left is not None:
        word, color = ("STARTING %d" % math.ceil(left) if left > 0 else "STARTING"), T.GREEN
    elif lob["closed"]:
        word, color = "CLOSED", T.RED
    else:
        word, color = "WAITING", T.FG
    W.text(ui, word, color, px + (pw - W.width(word)) // 2, y)
    hint = [("b2", "LEAVE")]
    if lob["role"] == "host" and not lob["fixed"] and lob["ready"] and left is None:
        hint = [("b1", "START")] + hint
    button_hint(ui, px + 8, py + ph - HINT_H - 6, hint)


def draw_transfer(fe, ui, now):
    """A copia dos arquivos do jogo do anfitriao: os dois gabinetes, a seta e
    o andamento."""
    g = fe.link_game
    pw, ph = WW - 16, 136
    px, py = 8, (HH - ph) // 2
    card(ui, (px, py, pw, ph))
    if g:
        W.text(ui, fit(fe.fd.short_title(g), pw - 16), T.YELLOW, px + 8, py + 8)
    done, total, name = fe.ov.get("progress", (0, 0, ""))
    cabinet_icon(ui, px + 24, py + 26, 18, 26, True)
    cabinet_icon(ui, px + pw - 42, py + 26, 18, 26, False)
    pygame.draw.rect(ui, T.PINK, (px + pw - 45, py + 23, 24, 32), 1)
    for i in range(5):
        on = (int(now * 4) % 6) == i
        x = px + 62 + i * 16
        pygame.draw.polygon(ui, T.GREEN if on else GREEN_DIM, [(x, py + 32), (x, py + 46), (x + 9, py + 39)])
    bar = (px + 12, py + 64, pw - 24, 12)
    pygame.draw.rect(ui, T.LINE, bar, 1)
    pct = (done / total) if total else 0
    ui.fill(T.GREEN, (bar[0] + 2, bar[1] + 2, round((bar[2] - 4) * min(1.0, pct)), bar[3] - 4))
    W.text(ui, "%d%%" % round(pct * 100), T.FG, px + (pw - W.width("%d%%" % round(pct * 100))) // 2, py + 82)
    if name:
        W.text(ui, fit(os.path.basename(name), pw - 16), T.COMMENT, px + 8, py + 96)
    button_hint(ui, px + 8, py + ph - HINT_H - 6, [("b2", "CANCEL")])


def draw_unpack(fe, ui, now):
    """A extracao de um jogo Namco empacotado (gui/fenamco.py), ou o download
    do core do RetroArch que falta (o titulo vem no ov): o jogo e a barra de
    andamento no centro da tela, com o arquivo que esta saindo do .gz (ou o
    que o download diz)."""
    g = fe.ov.get("game")
    pw, ph = WW - 16, 104
    px, py = 8, (HH - ph) // 2
    card(ui, (px, py, pw, ph))
    ui.blit(W.big(fe.ov.get("title", "EXTRACTING"), 1, W.LABEL), (px + 10, py + 8))
    if g:
        tiny.text(ui, tiny.fit(fe.fd.short_title(g).upper(), pw - 20), T.COMMENT, px + 10, py + 20)
    done, total, name = fe.ov.get("progress", (0, 0, ""))
    bar = (px + 12, py + 36, pw - 24, 12)
    pygame.draw.rect(ui, T.LINE, bar, 1)
    pct = min(1.0, done / total) if total else 0.0
    ui.fill(T.GREEN, (bar[0] + 2, bar[1] + 2, round((bar[2] - 4) * pct), bar[3] - 4))
    label = "%d%%" % round(pct * 100)
    W.text(ui, label, T.FG, px + (pw - W.width(label)) // 2, py + 52)
    if name:
        tiny.text(ui, tiny.fit(os.path.basename(name).upper(), pw - 20), T.COMMENT, px + 10, py + 66)
    button_hint(ui, px + 8, py + ph - HINT_H - 6, [("b2", "CANCEL")])


# O letreiro de um texto que nao cabe: parado com "..." por MARQUEE_HOLD
# segundos, rola ate o fim a MARQUEE_SPEED pixels por segundo, para no fim
# e volta ao comeco.
MARQUEE_HOLD, MARQUEE_SPEED = 1.6, 28.0


def marquee(ui, s, color, x, y, w, now):
    s = s.upper()
    full = W.width(s)
    if full <= w:
        W.text(ui, s, color, x, y)
        return
    travel = full - w
    run = travel / MARQUEE_SPEED
    t = now % (2 * MARQUEE_HOLD + run)
    if t < MARQUEE_HOLD:
        W.text(ui, fit(s, w - W.width("...")) + "...", color, x, y)
        return
    offset = min(travel, (t - MARQUEE_HOLD) * MARQUEE_SPEED)
    old = ui.get_clip()
    ui.set_clip(pygame.Rect(x, y - 2, w, 12).clip(old))
    W.text(ui, s, color, x - round(offset), y)
    ui.set_clip(old)


def text_img(s, color, big=False):
    """O texto numa surface (para o ticker): a letra normal ou a grande."""
    if big:
        return W.big(s, 1, W.LABEL)
    surf = pygame.Surface((W.width(s) + 1, 10), pygame.SRCALPHA)
    W.text(surf, s, color, 0, 0)
    return surf


def ticker(ui, img, x, y, w, now):
    """Um texto que nao cabe em w corre em circulo: sai pela esquerda e
    volta pela direita, depois de um espaco."""
    if img.get_width() <= w:
        ui.blit(img, (x, y))
        return
    period = img.get_width() + 40
    off = int(now * MARQUEE_SPEED) % period
    old = ui.get_clip()
    ui.set_clip(pygame.Rect(x, y - 2, w, img.get_height() + 4).clip(old))
    ui.blit(img, (x - off, y))
    ui.blit(img, (x - off + period, y))
    ui.set_clip(old)


def is_clone(fe, game):
    """O jogo e um clone (na lista com o pai, ou pelos dados do MAME)."""
    return bool(game.get("CloneOf") or (fe.rows and fe.rows[fe.cursor][1]))


def more_rows(ui, rows, x, y, right, lw, now, small=False):
    """Linhas "ROTULO valor" da pagina do jogo (small: o rotulo na fonte
    pequena e a linha mais baixa); o valor que nao cabe vira letreiro.
    Devolve o y de baixo."""
    for label, value in rows:
        if not value:
            continue
        if T.VERTICAL or small:
            tiny.text(ui, label, T.COMMENT, x, y + 2)
        else:
            W.text(ui, label, T.COMMENT, x, y)
        marquee(ui, str(value), T.FG, x + lw, y, right - x - lw, now)
        y += 11 if small else 13
    return y


def button_panel(fe, g, info):
    """O painel de 6 posicoes com os botoes do jogo onde o Buttons layout os
    poe (o mesmo do painel web); sem o Arcade Database, so os numeros."""
    web = fe.fd.web
    if info:
        return web.button_panel(info)
    try:
        count = min(web.PANEL_SIZE, int(g.get("Buttons") or 0))
    except ValueError:
        count = 0
    if not count:
        return []
    cells = [None] * web.PANEL_SIZE
    for n, pos in zip(range(1, count + 1), web.button_layout(count)):
        cells[pos - 1] = {"button": n, "color": "", "label": ""}
    return cells


def draw_button_panel(ui, cells, x, y, w):
    """Os botoes no painel como no guia dos controles: os seis juntos, em
    perspectiva, o do jogo na cor dele e a posicao livre apagada; a funcao
    fora, em cima (a fileira de cima) ou embaixo, com a linha e a seta.
    Devolve a altura."""
    r, step = 8, 21
    ry = round(r * FLAT)
    bx0 = x + (w - 2 * step) // 2
    by0 = y + 22
    for i, cell in enumerate(cells):
        col, row = i % 3, i // 3
        cx = bx0 + col * step
        cy = by0 + row * 22 - (2 if col == 1 else 0)
        color = T.LINE
        if cell:
            try:
                color = tuple(pygame.Color(cell["color"].lower()))[:3] if cell["color"] else T.PURPLE
            except ValueError:
                color = T.PURPLE
        button3d(ui, cx, cy, r, color)
        if not cell:
            continue
        text = (cell["label"] or str(cell["button"])).upper()
        text = tiny.fit(text, 70)
        tw = tiny.width(text)
        tx = {0: cx + 3 - tw, 1: cx - tw // 2, 2: cx - 3}[col]
        top, bottom = cy - ry - 3, cy + LIFT + ry + 4
        # O nome do meio uma linha mais para fora: nomes longos lado a lado
        # (LIGHT PUNCH, MIDDLE PUNCH) nao se encostam.
        out = 8 if col == 1 else 0
        if row == 0:
            ty, y0, y1, d = by0 - 16 - out, by0 - 9 - out, top, (0, 1)
        else:
            ty, y0, y1, d = bottom + 9 + out, bottom + 7 + out, bottom, (0, -1)
        tiny.text(ui, text, T.FG, tx, ty)
        pygame.draw.line(ui, T.COMMENT, (cx, y0), (cx, y1 - d[1] * 2))
        arrow(ui, cx, y1, d, T.COMMENT, 2)
    return 78


def text_box(fe, ui, box, parts, empty):
    """A caixa de texto rolavel: parts sao (cor, texto); o titulo de uma
    secao vem em rosa."""
    x, y, w, h = box
    W.block(ui, box, T.BG_DEEP, None)
    pygame.draw.rect(ui, T.LINE, box, 1)
    lines = []
    for color, text in parts or [(T.FG, empty)]:
        for para in text.split("\n"):
            lines.extend((color, line) for line in (W.wrap(para, w - 20) if para.strip() else [""]))
    shown = max(1, (h - 8) // 11 - 1)
    top = min(fe.ov.get("scroll", 0), max(0, len(lines) - shown))
    fe.ov["scroll"] = top
    for i, (color, line) in enumerate(lines[top:top + shown]):
        W.text(ui, line, color, x + 6, y + 5 + i * 11)
    if len(lines) > shown:
        W.scrollbar(ui, x + w - 7, y + 4, h - 8, top, shown, len(lines))


def page_arrow(ui, now, side):
    """A seta que pisca na borda: ha mais para aquele lado."""
    if int(now * 2.5) % 2 == 0:
        return
    cx = WW - 5 if side > 0 else 5
    arrow(ui, cx, HH // 2, (side, 0), T.PINK, 5)


def draw_more(fe, ui, now):
    """A pagina do jogo (o "+"): na 1, a capa, os dados, os botoes no painel
    e a descricao; na 2 (a direita), as fotos, mais dados e as secoes do
    arcade-history."""
    g = fe.ov["game"]
    info = fe.ov.get("info") or {}
    page = fe.ov.get("page", 0)
    W.frame(ui, {}, fit(fe.fd.short_title(g), 240) or "Game", [])
    y0 = 34
    lw = 34 if T.VERTICAL else 62       # a coluna dos rotulos
    right = SX + SW - 8                 # a direita fica a seta
    description, sections = fe.fd.web.history_parts(info.get("history"))
    if page == 0:
        bw, bh = (60, 82) if T.VERTICAL else (84, 122)
        W.block(ui, (SX, y0, bw, bh), T.BG_DEEP, T.PURPLE)
        blit_center(ui, image(fe, media(fe, g, "box") or media(fe, g, "snap"), bw - 6, bh - 6), SX, y0, bw, bh)
        pygame.draw.rect(ui, T.PINK, (SX, y0, bw, bh), 2)
        x = SX + bw + 10
        y = more_rows(ui, [
            ("YEAR", " ".join(p for p in (info.get("year") or g.get("Year"),
                                          info.get("manufacturer") or g.get("Manufacturer")) if p)),
            ("GENRE", info.get("genre") or g.get("Category")),
            ("PLAYERS", info.get("nplayers") or g.get("Players")),
            ("CONTROL", info.get("input_controls") or g.get("Control"))], x, y0 + 2, right, lw, now)
        cells = button_panel(fe, g, info)
        if cells:
            y += 2 + draw_button_panel(ui, cells, x, y + 2, min(right - x, 180))
        ty = max(y0 + bh, y) + 8
        box = (SX, ty, right - SX, HH - 12 - ty)
        if fe.ov.get("loading"):
            W.block(ui, box, T.BG_DEEP, None)
            W.glow(ui, (box[0] + 2, box[1] + 2, box[2] - 4, box[3] - 4), {"now": now})
            W.centered(ui, "LOOKING IT UP...", T.CYAN, ty + box[3] // 2 - 4)
        else:
            empty = "Not in the Arcade Database." if g["_system"]["arcade"] else \
                "No information yet. Tab > Scrape this game brings it."
            text_box(fe, ui, box, [(T.FG, description)] if description else [], empty)
        page_arrow(ui, now, 1)
        return
    # Pagina 2: as fotos que o jogo tem, lado a lado.
    pics = [p for p in (media(fe, g, k) for k in ("snap", "marquee", "box", "logo")) if p][:3]
    ph = 44 if T.VERTICAL else 50
    if pics:
        pw = (right - SX - 6 * (len(pics) - 1)) // len(pics)
        for i, path in enumerate(pics):
            px = SX + i * (pw + 6)
            W.block(ui, (px, y0, pw, ph), T.BG_DEEP, None)
            blit_center(ui, image(fe, path, pw - 4, ph - 4), px, y0, pw, ph)
            pygame.draw.rect(ui, T.LINE, (px, y0, pw, ph), 1)
        y0 += ph + 8
    parent = g.get("CloneOf")
    y = more_rows(ui, [
        ("MAKER", info.get("manufacturer") or g.get("Manufacturer")),
        ("SERIES", info.get("serie") or g.get("Series")),
        ("SCREEN", ", ".join(p for p in (info.get("screen_resolution"), info.get("screen_orientation")) if p)),
        ("STATUS", info.get("status") or g.get("Status")),
        ("LANGUAGE", info.get("languages")),
        ("SET", g["Name"] + (" (clone of %s)" % parent if parent else ""))], SX, y0, right, 40, now, small=True)
    if info.get("rate"):
        tiny.text(ui, "RATING", T.COMMENT, SX, y + 3)
        stars(ui, SX + 40, y, float(info["rate"]), 4)
        y += 11
    parts = []
    for title, body in sections:
        parts += [(T.PINK, title.upper()), (T.FG, body)]
    ty = y + 6
    if HH - 12 - ty >= 30:
        text_box(fe, ui, (SX, ty, right - SX, HH - 12 - ty), parts, "Nothing more about this game.")
    source = (info.get("history_copyright_short") or "").upper()
    if source:
        tiny.text(ui, tiny.fit(source, SW - 20), T.COMMENT, right - 4, HH - 9, right=True)
    page_arrow(ui, now, -1)


def draw_filter(fe, ui, now):
    pw, ph = 236, 196
    px, py = (WW - pw) // 2, 30
    card(ui, (px, py, pw, ph))
    ui.blit(W.big("FILTER", 1, W.LABEL), (px + (pw - W.width("FILTER")) // 2, py + 7))
    # A linha do tipo de controle (esquerda/direita), e debaixo os filtros
    # que tem jogo na romlist (fe.ov["items"], os indices em fe.lib.filters).
    y = py + 22
    on = fe.ov["sel"] == 0
    if on:
        tile_frame(ui, (px + 6, y - 2, pw - 12, 12), True, now)
        pygame.draw.rect(ui, T.PINK, (px + 6, y - 2, pw - 12, 12), 1)
    W.text(ui, "CONTROL", T.PINK, px + 10, y)
    kind = fe.ov["ctrls"][fe.ov["ctrl"]] or "All"
    lx, rx = px + 80, px + pw - 14
    arrow(ui, lx, y + 4, (-1, 0), T.CYAN if on else T.COMMENT, 4)
    arrow(ui, rx, y + 4, (1, 0), T.CYAN if on else T.COMMENT, 4)
    label = fit(kind, rx - lx - 14)
    W.text(ui, label, T.FG if on else T.COMMENT, (lx + rx - W.width(label)) // 2, y)
    pygame.draw.line(ui, T.COMMENT, (px + 8, y + 13), (px + pw - 8, y + 13))
    filters, items = fe.lib.filters, fe.ov["items"]
    rows = 12
    sel = fe.ov["sel"] - 1
    top = fe.ov.get("top", 0)
    if 0 <= sel < top:
        top = sel
    if sel >= top + rows:
        top = sel - rows + 1
    fe.ov["top"] = top
    y0 = py + 39
    for n in range(top, min(len(items), top + rows)):
        i = items[n]
        y = y0 + (n - top) * 13
        on = n == sel
        if on:
            tile_frame(ui, (px + 6, y - 2, pw - 22, 12), True, now)
            pygame.draw.rect(ui, T.PINK, (px + 6, y - 2, pw - 22, 12), 1)
        label = filters[i]["name"].replace("©", "(C)")
        W.text(ui, fit(label, pw - 52), T.FG if on else T.COMMENT, px + 26, y)
        if i == fe.flt % len(filters):
            pygame.draw.lines(ui, T.GREEN, False, [(px + 10, y + 4), (px + 13, y + 7), (px + 18, y)], 2)
    if len(items) > rows:
        W.scrollbar(ui, px + pw - 10, y0 - 2, rows * 13, top, rows, len(items))


RIBBON_WIDE = 2.2        # o azulejo com logotipo vai ate 2,2 vezes a altura
RIBBON_STEP = 112        # entre os centros (o do meio, largo, mais um vao)


def draw_ribbon(fe, ui, now):
    band_y, band_h = 70, 104
    W.block(ui, (0, band_y, WW, band_h), T.BG_DEEP, None)
    pygame.draw.line(ui, T.PINK, (0, band_y), (WW, band_y))
    pygame.draw.line(ui, T.PINK, (0, band_y + band_h - 1), (WW, band_y + band_h - 1))
    tiny.centered(ui, "GAME LIST", T.COMMENT, WW // 2, band_y + 7)
    n = len(fe.cats)
    # A tira desliza ate a romlist nova: pos corre ate fe.cat_pos (o indice
    # sem dar a volta), e cada quadrado cresce ao passar pelo meio. No meio
    # fica o sistema escolhido na tira (pick passos alem do da lista).
    pick = getattr(fe, "pick", 0)
    pos = spring(fe, "ribbon", getattr(fe, "cat_pos", fe.cat), fe.abs_now)
    base = math.floor(pos)
    tiles = []
    for k in range(-3, 5):
        d = base + k - pos
        if abs(d) > 2.6 or (n < 2 and abs(d) > 0.5):
            continue
        tiles.append((abs(d), d, (fe.cat + pick + round(base + k - getattr(fe, "cat_pos", fe.cat))) % n))
    badges = []
    for dist, d, idx in sorted(tiles, reverse=True):
        c = fe.cats[idx]
        # O tamanho segue uma curva lisa da distancia ao meio (56 no meio, 40 a
        # um passo, ~35 a dois), sem quina: o azulejo cresce aos poucos.
        sf = 32 + 24 / (1 + 2 * dist * dist)
        on = dist < 0.5
        # Os azulejos com logotipo sao fluidos: a largura acompanha a proporcao
        # do logotipo (de 1 a RIBBON_WIDE vezes a altura), que ocupa 80% dele.
        src = logo_source(c["name"])
        wf = sf
        if src is not None:
            wf = max(sf, min(RIBBON_WIDE * sf, 0.45 * sf * src.get_width() / src.get_height() / 0.8))
        # As bordas saem do centro em ponto flutuante, cada uma arredondada:
        # o azulejo cresce igual para os dois lados, sem tremer um pixel.
        cx, cy = WW / 2 + d * RIBBON_STEP, band_y + 48
        x, y = round(cx - wf / 2), round(cy - sf / 2)
        w, size = round(cx + wf / 2) - x, round(cy + sf / 2) - y
        tile_frame(ui, (x, y, w, size), on, now)
        # A borda vai do cinza ao rosa conforme chega ao meio.
        lit = max(0.0, 1.0 - dist)
        edge = tuple(round(a + (b - a) * lit) for a, b in zip(T.LINE[:3], T.PINK[:3]))
        pygame.draw.rect(ui, edge, (x, y, w, size), 2 if on else 1)
        name = system_icon(c)
        alpha = round(255 - 145 * min(1.0, dist)) if dist > 0.05 else None
        logo = system_logo(c["name"], round(wf * 0.8), round(sf * 0.8)) if src is not None else None
        if logo is not None:
            # O logotipo escrito do sistema no meio, e o icone do emulador em
            # cima da borda, no canto de baixo a direita, quase vazando.
            if alpha is not None:
                logo = logo.copy()
                logo.set_alpha(alpha)
            ui.blit(logo, (round(cx - logo.get_width() / 2), round(cy - logo.get_height() / 2)))
            badge = T.icon(name, 1) if name else None
            if badge is not None:
                # Por cima de todos os azulejos (um vizinho nao o cobre).
                if alpha is not None:
                    badge = badge.copy()
                    badge.set_alpha(max(alpha, 200))
                badges.append((badge, (x + w - round(badge.get_width() * 0.65),
                                       y + size - round(badge.get_height() * 0.65))))
            continue
        icon = ribbon_icon(c, name, sf)
        if alpha is not None:
            icon = icon.copy()
            icon.set_alpha(alpha)
        ui.blit(icon, (round(cx - icon.get_width() / 2), round(cy - icon.get_height() / 2)))
    for badge, at in badges:
        ui.blit(badge, at)
    # O nome do sistema ja esta no logotipo do azulejo; so sem logotipo ele vem escrito.
    c = fe.cats[(fe.cat + pick) % n]
    count_y = band_y + 84
    if logo_source(c["name"]) is None:
        label = fit(c["name"], WW - 20)
        ui.blit(W.big(label, 1, W.LABEL), ((WW - W.width(label)) // 2, band_y + 80))
        count_y = band_y + 93
    # Os jogos so do sistema ja na lista (o da tira ainda nao foi lido).
    if not pick:
        shown = sum(1 for g, _, extra in fe.rows if g is not None and not fe.fd.group_item(extra))
        tiny.centered(ui, "%d GAMES" % shown, T.CYAN, WW // 2, count_y)


# O logotipo escrito de cada sistema (o do Arcadeflow, config/fliperos-syslogo)
# para os azulejos da tira de romlists: feito uma vez por nome, numa thread, e
# guardado em ~/.cache; sem o tema ou sem o sistema nele, o azulejo fica so com
# o icone, como antes.
SYSLOGO = os.environ.get("FLIPEROS_SYSLOGO", "/opt/fliperos/bin/fliperos-syslogo")
SYSLOGO_CACHE = os.path.join(os.path.expanduser("~"), ".cache", "fliperos", "syslogo")
SYSLOGO_HEIGHT = 48
_logos = {}          # nome -> surface, None (sem logotipo) ou "..." (sendo feito)
_fitted = {}         # (nome, largura, altura) -> surface no tamanho do azulejo
FITTED_MAX = 400


def logo_file(name):
    """O PNG do logotipo do sistema (branco-Dracula, SYSLOGO_HEIGHT de altura),
    feito pelo fliperos-syslogo na primeira vez; None sem logotipo."""
    import subprocess
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") or "_"
    path = os.path.join(SYSLOGO_CACHE, "%s-%d.png" % (safe, SYSLOGO_HEIGHT))
    if os.path.isfile(path):
        return path
    # O temporario termina em .png: o fliperos-syslogo (Pillow) escolhe o
    # formato pela extensao.
    tmp = path[:-len(".png")] + ".tmp.png"
    try:
        os.makedirs(SYSLOGO_CACHE, exist_ok=True)
        r = subprocess.run([SYSLOGO, "png", name, tmp, str(SYSLOGO_HEIGHT), "f8f8f2"],
                           stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0 or not os.path.isfile(tmp):
        return None
    os.replace(tmp, path)
    return path


def system_logo(name, w, h):
    """O logotipo do sistema dentro de w x h, ou None (ainda sendo feito, ou sem
    logotipo)."""
    got = logo_source(name)
    if got is None:
        return None
    key = (name, w, h)
    if key not in _fitted:
        k = min(w / got.get_width(), h / got.get_height())
        size = (max(1, round(got.get_width() * k)), max(1, round(got.get_height() * k)))
        fit_keep(key, pygame.transform.smoothscale(got.convert_alpha() if pygame.display.get_surface() else got, size))
    return _fitted[key]


def fit_keep(key, img):
    """Guarda img em _fitted. Cheio, ele se esvazia antes, e nao depois: o novo
    fica (o zoom da tira passa por dezenas de tamanhos de cada sistema; esvaziar
    depois apagava o que ia ser devolvido, e o KeyError fechava o frontend)."""
    if len(_fitted) >= FITTED_MAX:
        _fitted.clear()
    _fitted[key] = img


def ribbon_icon(cat, name, size):
    """O icone do azulejo sem logotipo para um azulejo de size pixels: o do
    meio (56) no tamanho certo do desenho, e os outros reduzidos suave, pixel a
    pixel, sem o salto de uma escala para a outra."""
    px = min(56, round(size))
    key = ("icon", name or cat["name"][:1].upper(), px)
    if key not in _fitted:
        img = (T.icon(name, 2) if name else None) or W.big(cat["name"][:1].upper(), 3, W.MARQUEE)
        if px < 56:
            k = px / 56
            img = pygame.transform.smoothscale(img.convert_alpha() if pygame.display.get_surface() else img,
                                               (max(1, round(img.get_width() * k)), max(1, round(img.get_height() * k))))
        fit_keep(key, img)
    return _fitted[key]


def logo_source(name):
    """O logotipo do sistema no tamanho em que foi feito (para a proporcao), ou
    None (ainda sendo feito, ou sem logotipo). Na primeira vez, comeca a faze-lo."""
    got = _logos.get(name)
    if got is None and name not in _logos:
        _logos[name] = "..."

        def work():
            path = logo_file(name)
            surf = None
            if path:
                try:
                    surf = pygame.image.load(path)
                except (pygame.error, OSError):
                    surf = None
            _logos[name] = surf
        import threading
        threading.Thread(target=work, daemon=True).start()
        return None
    return got if isinstance(got, pygame.Surface) else None


def system_icon(cat):
    """O icone do programa da pasta (os de gui/icons)."""
    if cat.get("key") == "@arcade":
        return "frontend"         # (o joystick do FliperOS, nao o logo de um frontend)
    exe = (cat.get("exe", "") + " " + cat.get("args", "")).lower()
    for name in ("groovymame", "flycast", "pcsx2x6", "pcsx2", "dolphin", "model2", "openbor", "retroarch", "fightcade"):
        if name in exe:
            return name
    if "sm2" in exe:
        return "model2"
    if "duckstation" in exe:
        return "pcsx2"
    return None


def eye(ui, cx, cy, c, crossed=False):
    """O olho do Hide this game (riscado: escondido)."""
    pygame.draw.ellipse(ui, c, (cx - 7, cy - 4, 15, 9), 1)
    pygame.draw.circle(ui, c, (cx, cy), 2)
    if crossed:
        pygame.draw.line(ui, c, (cx - 7, cy + 5), (cx + 7, cy - 5), 2)


def option_row(ui, rect, label, on, now):
    """Uma linha do menu do Tab: o azulejo e o rotulo."""
    x, y, w, h = rect
    tile_frame(ui, rect, on, now)
    pygame.draw.rect(ui, T.PINK if on else T.LINE, rect, 2 if on else 1)
    W.text(ui, label, T.FG if on else T.COMMENT, x + 28, y + 4)


GAME_ITEMS = [("CLASSIFY", T.YELLOW), ("RENAME", T.CYAN), ("SCRAPE THIS GAME", T.GREEN),
              ("HIDE THIS GAME", T.PURPLE), ("DELETE THIS GAME", T.RED)]


def game_option(ui, i, rect, on, now):
    """Uma linha das opcoes do jogo: o icone e o rotulo."""
    label, color = GAME_ITEMS[i]
    option_row(ui, rect, label, on, now)
    ix, iy = rect[0] + 12, rect[1] + 8
    if i == 0:
        pygame.draw.polygon(ui, color, [(ix - 6, iy - 4), (ix + 2, iy - 4), (ix + 6, iy), (ix + 2, iy + 4),
                                        (ix - 6, iy + 4)])
        pygame.draw.circle(ui, T.BG_DEEP, (ix - 3, iy), 1)
    elif i == 1:
        pygame.draw.polygon(ui, color, [(ix - 5, iy + 5), (ix - 5, iy + 2), (ix + 3, iy - 6), (ix + 6, iy - 3),
                                        (ix - 2, iy + 5)])
    elif i == 2:
        ui.fill(color, (ix - 1, iy - 6, 3, 7))
        pygame.draw.polygon(ui, color, [(ix - 5, iy), (ix + 5, iy), (ix, iy + 4)])
        ui.fill(color, (ix - 6, iy + 5, 13, 2))
    elif i == 3:
        eye(ui, ix, iy, color, crossed=True)
    else:
        trash(ui, ix, iy - 1, color)


def draw_options(fe, ui, now):
    """O menu do Tab: as opcoes do jogo e, debaixo delas, as do frontend (as
    linhas 5 em diante do fliperos-frontend, OPT_*), numa lista so que rola com a
    escolhida, com os titulos; o andamento do scrape automatico fica fixo
    embaixo. O cartao tem 200 de altura: cabe inteiro no tubo."""
    g = fe.game()
    pw, ph = min(236, WW - 4), 200
    px, py = (WW - pw) // 2, max(8, (HH - ph) // 2)
    sel = fe.ov["sel"]
    card(ui, (px, py, pw, ph))
    # A lista: (y no conteudo, altura, o que e). Titulo e linha tem cada um a
    # sua altura, e a rolagem e em pixels.
    lines, y = [], 0
    lines.append((y, 22 if g else 14, "game-title"))
    y += 22 if g else 14
    for i in range(5):
        lines.append((y, 17, i))
        y += 17
    y += 4
    lines.append((y, 14, "fe-title"))
    y += 14
    for opt in range(5, 5 + len(FE_OPTIONS) - (0 if fe.commercial else 1)):
        lines.append((y, 17, opt))
        y += 17
    total = y
    # Os quadros de baixo: o do scrape automatico (onde sempre ficou) e, acima
    # dele, o do baixador de BIOS. Um que acabou sai do menu, e a lista ganha
    # o lugar dele.
    harvest = fe.harvest.visible()
    bios = getattr(fe, "bios", None)
    bios = bios.box() if bios else None
    hy = py + ph - 44
    by = hy - 34 if harvest else hy
    top = by if bios else hy if harvest else py + ph - 4
    # A janela: do alto do cartao ate o primeiro quadro.
    vx, vy, vw = px + 8, py + 8, pw - 16
    vh = top - 4 - vy
    # A escolhida sempre inteira a vista; a primeira de cada parte leva o
    # titulo junto.
    scroll = fe.ov.get("scroll", 0)
    for ly, lh, what in lines:
        if what == sel:
            top = ly
            if sel == 0:
                top = 0
            elif sel == 5:
                top = ly - 14
            scroll = min(scroll, top)
            scroll = max(scroll, ly + lh - vh)
    scroll = max(0, min(scroll, total - vh))
    # Sem linha cortada: em cima a lista para no comeco de uma linha, e
    # embaixo a que nao cabe inteira nao aparece.
    scroll = fe.ov["scroll"] = min((ly for ly, _, _ in lines if ly >= scroll), default=0)
    shown = max(ly + lh for ly, lh, _ in lines if ly + lh <= scroll + vh) - scroll
    # As linhas deixam 8 pixels a direita para a barra de rolagem.
    right = vx + vw - 14
    ui.set_clip((vx - 2, vy, vw + 4, shown))
    for ly, lh, what in lines:
        sy = vy + ly - scroll
        if sy + lh < vy or sy > vy + vh:
            continue
        if what == "game-title":
            ui.blit(W.big("GAME OPTIONS", 1, W.LABEL), (px + 10, sy))
            if g:
                tiny.text(ui, tiny.fit(g.get("Title") or g["Name"], pw - 20), T.COMMENT, px + 10, sy + 12)
        elif what == "fe-title":
            ui.blit(W.big("FRONTEND OPTIONS", 1, W.LABEL), (px + 10, sy + 2))
        elif what < 5:
            game_option(ui, what, (vx, sy, vw - 8, 16), what == sel, now)
        else:
            draw_option(fe, ui, what, (vx, sy, vw - 8, 16), what == sel, right, now)
    ui.set_clip(None)
    if total > vh:
        W.scrollbar(ui, px + pw - 7, vy, vh, scroll, vh, total)
    if harvest:
        draw_harvest(fe, ui, px + 8, hy, pw - 16)
    if bios:
        draw_bios(ui, px + 8, by, pw - 16, bios)


def chip(ui, right, y, text, lit, on):
    """O valor de uma linha do Tab, encostado a direita: aceso (ON, o modo de
    agora) ou so contornado. Devolve onde comeca."""
    w = tiny.width(text) + 8
    if lit:
        W.block(ui, (right - w, y + 3, w, 10), T.PINK if on else T.PURPLE, None)
    else:
        W.block(ui, (right - w, y + 3, w, 10), T.BG_DEEP, None)
        pygame.draw.rect(ui, T.LINE, (right - w, y + 3, w, 10), 1)
    tiny.text(ui, text, T.SPACE if lit else T.COMMENT, right - w + 4, y + 6)
    return right - w


# As linhas das opcoes do frontend, da 5 em diante (os OPT_* do
# fliperos-frontend, na mesma ordem); os minutos por ficha so com o modo
# comercial ligado.
FE_OPTIONS = [("mode", "VIEW"), ("transition", "TRANSITION"), ("clones", "SHOW CLONES"), ("hidden", "HIDDEN GAMES"),
              ("controls", "FRONTEND CONTROLS"), ("power", "POWER CLOSES GAME"),
              ("commercial", "COMMERCIAL MODE"), ("coin", "MINUTES PER COIN")]


def draw_option(fe, ui, opt, rect, on, right, now):
    """Uma linha das opcoes do frontend: o rotulo e o valor dela."""
    x, y, _, _ = rect
    what, label = FE_OPTIONS[opt - 5]
    option_row(ui, rect, "", on, now)
    W.text(ui, label, T.FG if on else T.COMMENT, x + 8, y + 4)
    if what == "mode":
        # O modo: os tres lado a lado, o de agora aceso.
        cx = right
        for mode, label in reversed((("list", "LIST"), ("full", "FULL SCREEN"), ("flow", "GRID"))):
            cx = chip(ui, cx, y, label, fe.mode == mode, on) - 3
    elif what == "transition":
        # A animacao da troca de romlist no modo de agora, entre setas.
        name = TRANSITION_NAMES[transition(fe)]
        cx = chip(ui, right - 10, y, name, True, on)
        if on:
            arrow(ui, cx - 5, y + 8, (-1, 0), T.PINK, 3)
            arrow(ui, right - 4, y + 8, (1, 0), T.PINK, 3)
    elif what == "clones":
        chip(ui, right, y, "ON" if fe.show_clones else "OFF", fe.show_clones, on)
    elif what == "hidden":
        tiny.text(ui, "%d  >" % len(fe.lib.hidden()), T.PINK if on else T.COMMENT, right, y + 6, right=True)
    elif what == "controls":
        tiny.text(ui, ">", T.PINK if on else T.COMMENT, right, y + 6, right=True)
    elif what == "power":
        chip(ui, right, y, "ON" if fe.power_exit else "OFF", fe.power_exit, on)
    elif what == "commercial":
        chip(ui, right, y, "ON" if fe.commercial else "OFF", fe.commercial, on)
    elif what == "coin":
        cx = chip(ui, right - 8, y, "%d" % fe.coin_minutes, True, on)
        if on:
            arrow(ui, cx - 5, y + 8, (-1, 0), T.PINK, 3)
            arrow(ui, right - 3, y + 8, (1, 0), T.PINK, 3)


def draw_hidden(fe, ui, now):
    """Tab > Hidden games: os jogos escondidos, com a pasta de cada um; o
    botao 1 traz o escolhido de volta."""
    pw, ph = min(236, WW - 4), 224
    px, py = (WW - pw) // 2, max(8, (HH - ph) // 2)
    card(ui, (px, py, pw, ph))
    ui.blit(W.big("HIDDEN GAMES", 1, W.LABEL), (px + 10, py + 8))
    rows, sel = fe.ov["rows"], fe.ov["sel"]
    if not rows:
        tiny.centered(ui, "NO HIDDEN GAMES", T.COMMENT, px + pw // 2, py + ph // 2)
        return
    shown = (ph - 34) // 15
    top = max(0, min(sel - shown // 2, len(rows) - shown))
    for i in range(top, min(len(rows), top + shown)):
        key, name, folder, title = rows[i]
        y = py + 26 + (i - top) * 15
        on = i == sel
        tile_frame(ui, (px + 8, y, pw - 16, 14), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (px + 8, y, pw - 16, 14), 2 if on else 1)
        eye(ui, px + 19, y + 7, T.PURPLE if on else T.LINE, crossed=True)
        label = tiny.fit(folder.upper(), 70)
        tiny.text(ui, label, T.CYAN if on else T.LINE, px + pw - 14, y + 5, right=True)
        room = pw - 16 - 28 - tiny.width(label) - 10
        if on:
            ticker(ui, text_img(title.upper(), T.FG), px + 30, y + 3, room, now)
        else:
            W.text(ui, fit(title, room), T.COMMENT, px + 30, y + 3)
    if len(rows) > shown:
        W.scrollbar(ui, px + pw - 6, py + 26, shown * 15 - 1, top, shown, len(rows))


def draw_controls(fe, ui, now):
    """Tab > Frontend options > Frontend controls: cada funcao com o comando do
    painel e a tecla dela (um traco: nenhum), o atalho que fecha o jogo (EXIT
    GAME: os botoes segurados juntos e a tecla), o formato do painel e o
    RESET, a celula escolhida acesa. Esperando o novo, a celula pisca e a
    dica diz o que fazer."""
    import feinput
    W.frame(ui, {}, "Controls", [])
    ov = fe.ov
    sel, col, wait = ov["sel"], ov["col"], ov.get("wait")
    funcs = feinput.FUNCTIONS
    exit_row, layout_row, reset_row = len(funcs), len(funcs) + 1, len(funcs) + 2
    # As colunas da tecla e do painel (em pe, mais estreitas).
    kw, pw = (58, 40) if T.VERTICAL is not None else (74, 46)
    kx = SX + SW - kw
    padx = kx - 4 - pw
    y0, rh = 40, 12
    count = PANEL_COUNT[panel_layout(fe)]
    tiny.centered(ui, "PANEL", T.CYAN if col == 0 else T.COMMENT, padx + pw // 2, 32)
    tiny.centered(ui, "KEYBOARD", T.CYAN if col == 1 else T.COMMENT, kx + kw // 2, 32)
    blink = int(now * 3) % 2

    def label(i, text, draw_icon, color):
        """O comeco da linha i: o fundo (escolhida), o icone e o nome."""
        y = y0 + i * rh
        if i == sel:
            tile_frame(ui, (SX, y, SW, rh - 1), True, now)
        icon = pygame.Surface((14, 14), pygame.SRCALPHA)
        draw_icon(icon, 7, 7, color)
        ui.blit(pygame.transform.smoothscale(icon, (10, 10)), (SX + 4, y + 1))
        W.text(ui, fit(text, padx - SX - 22), T.FG if i == sel else T.COMMENT, SX + 18, y + 2)
        return y

    def cells(i, y, values, dim=(False, False)):
        """As duas celulas (painel e tecla) da linha i; dim apaga o valor."""
        for c, (cx, cw) in enumerate(((padx, pw), (kx, kw))):
            value, lit = values[c], i == sel and c == col
            rect = (cx, y, cw, rh - 1)
            if lit and wait:
                W.block(ui, rect, T.PINK if blink else T.PURPLE, None)
                tiny.centered(ui, "?", T.SPACE, cx + cw // 2, y + 3)
                continue
            W.block(ui, rect, T.PINK if lit else T.BG_DEEP, None)
            pygame.draw.rect(ui, T.PINK if lit else T.LINE, rect, 1)
            shown = tiny.fit(value, cw - 6) if value else "-"
            tiny.centered(ui, shown, T.SPACE if lit else (T.FG if value and not dim[c] else T.LINE),
                          cx + cw // 2, y + 3)

    def wide(i, y, text, arrows=False):
        """Uma celula so, da coluna do painel ate a da tecla."""
        on = i == sel
        rect = (padx, y, kx + kw - padx, rh - 1)
        W.block(ui, rect, T.PINK if on else T.BG_DEEP, None)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, rect, 1)
        tiny.centered(ui, text, T.SPACE if on else T.FG, padx + rect[2] // 2, y + 3)
        if on and arrows:
            arrow(ui, padx + 6, y + 5, (-1, 0), T.SPACE, 3)
            arrow(ui, kx + kw - 7, y + 5, (1, 0), T.SPACE, 3)

    for i, f in enumerate(funcs):
        y = label(i, FUNCTION_NAMES[f], FUNCTION_STYLE[f][1], FUNCTION_STYLE[f][0])
        b = fe.input.binds[f]
        # Um botao que o formato do painel nao tem fica apagado.
        missing = bool(b["pad"]) and b["pad"][0] == "b" and int(b["pad"][1:]) > count
        cells(i, y, (feinput.pad_name(b["pad"]), feinput.key_name(fe.pg, b["key"])), (missing, False))
    # O atalho que fecha o jogo: os botoes segurados juntos e a tecla.
    y = label(exit_row, "EXIT GAME", exit_icon, T.RED)
    combo = "+".join(c[1:] if c[0] == "b" and c[1:].isdigit() else c.upper() for c in fe.exit_combo)
    cells(exit_row, y, (combo, fe.exit_key[0] if fe.exit_key else None))
    # O formato do painel: esquerda e direita trocam.
    y = label(layout_row, "PANEL LAYOUT", view_icon, T.YELLOW)
    wide(layout_row, y, dict(PANEL_LAYOUTS)[panel_layout(fe)], arrows=True)
    # A ultima linha: RESET e SAVE lado a lado (a coluna escolhe).
    y = y0 + reset_row * rh
    half = (SW - 4) // 2
    for c, (text, draw_icon, color) in enumerate((("RESET", reset_icon, T.ORANGE), ("SAVE", save_icon, T.GREEN))):
        lit = sel == reset_row and c == col
        rect = (SX + c * (half + 4), y, half, rh - 1)
        W.block(ui, rect, T.PINK if lit else T.BG_DEEP, None)
        pygame.draw.rect(ui, T.PINK if lit else (color if c else T.LINE), rect, 1)
        icon = pygame.Surface((14, 14), pygame.SRCALPHA)
        draw_icon(icon, 7, 7, T.SPACE if lit else color)
        tx = rect[0] + (half - W.width(text) - 14) // 2
        ui.blit(pygame.transform.smoothscale(icon, (10, 10)), (tx, y + 1))
        W.text(ui, text, T.SPACE if lit else T.FG, tx + 14, y + 2)
    if wait == "pad":
        tips = ("PRESS A PANEL CONTROL - THE SAME ONE AGAIN: NONE", "ESC: CANCEL")
    elif wait == "key":
        tips = ("PRESS A KEY - THE SAME KEY OR DELETE: NONE", "BACK ON THE PANEL: CANCEL")
    elif sel == exit_row:
        tips = ("SELECT: HOLD THE BUTTONS / PRESS THE KEY   DELETE: OFF",
                "IN A GAME THEY CLOSE IT (THE BUTTONS HELD 1 S)")
    elif sel == layout_row:
        tips = ("LEFT/RIGHT: THE SHAPE OF THE PANEL", "THE GUIDE DRAWS ONLY THE BUTTONS IT HAS")
    elif sel == reset_row and col == 1:
        tips = ("SELECT: SAVE AND LEAVE", "EACH CHANGE ALREADY WORKS   LEFT: RESET")
    elif sel == reset_row:
        tips = ("SELECT: THE FUNCTIONS GO BACK TO THE DEFAULTS", "THE EXIT SHORTCUT AND THE LAYOUT STAY")
    else:
        tips = ("SELECT: CHANGE   DELETE: NONE   LEFT/RIGHT: COLUMN",
                "A BUTTON IN USE SWAPS WITH THE OLD ONE   BACK: DONE")
    y = y0 + (reset_row + 1) * rh
    tiny.centered(ui, tips[0], T.YELLOW if wait else T.COMMENT, WW // 2, y + 3)
    tiny.centered(ui, tips[1], T.COMMENT, WW // 2, y + 10)


def draw_bios(ui, x, y, w, box):
    """O baixador de BIOS (febios.py): o que esta baixando e a barra, ou o que
    nao deu certo. Do mesmo tamanho e jeito do quadro do scrape."""
    right, color, pct, info = box
    pygame.draw.rect(ui, T.LINE, (x, y, w, 31), 1)
    W.text(ui, "BIOS DOWNLOAD", T.COMMENT, x + 8, y + 3)
    tiny.text(ui, right, getattr(T, color.upper()), x + w - 8, y + 5, right=True)
    bx, by, bw = x + 8, y + 13, w - 16
    if pct is not None:
        W.block(ui, (bx, by, bw, 6), T.BG_DEEP, None)
        if pct:
            ui.fill(T.PINK, (bx, by, round(bw * pct / 100), 6))
        pygame.draw.rect(ui, T.LINE, (bx, by, bw, 6), 1)
    tiny.text(ui, tiny.fit(info.upper(), bw), T.COMMENT, bx, y + 22)


def draw_harvest(fe, ui, x, y, w):
    """O scrape automatico (feharvest.py): a barra dos jogos que ja tem os
    dados, quantos faltam e o andamento dos torrents de logos e videos."""
    h = fe.harvest
    packs = h.pack_line()
    pygame.draw.rect(ui, T.LINE, (x, y, w, 39 if packs else 31), 1)
    # Os pacotes de logos e videos por torrent (ou um a um, os de .zip).
    if packs:
        tiny.text(ui, tiny.fit(packs, w - 16), T.YELLOW, x + 8, y + 31)
    W.text(ui, "AUTO SCRAPE", T.COMMENT, x + 8, y + 3)
    if not h.scanned:
        tiny.text(ui, "COUNTING THE GAMES...", T.COMMENT, x + w - 8, y + 5, right=True)
        return
    done = h.total - h.left
    if h.left:
        text = "%d GAMES LEFT" % h.left
    else:
        text = "ALL %d GAMES DONE" % h.total
    tiny.text(ui, text, T.CYAN if h.left else T.GREEN, x + w - 8, y + 5, right=True)
    bx, by, bw = x + 8, y + 13, w - 16
    W.block(ui, (bx, by, bw, 6), T.BG_DEEP, None)
    fill = round(bw * done / h.total) if h.total else bw
    if fill:
        ui.fill(T.GREEN if not h.left else T.PINK, (bx, by, fill, 6))
    pygame.draw.rect(ui, T.LINE, (bx, by, bw, 6), 1)
    info = "%d OF %d HAVE THEIR DATA" % (done, h.total)
    if h.current is not None:
        info = "NOW: " + fe.fd.short_title(h.current)
    if h.paused:
        info = "PAUSED: A GAME IS OPEN"
    tiny.text(ui, tiny.fit(info.upper(), bw), T.COMMENT, bx, y + 22)


LABELS = {"Category": "GENRE", "Players": "PLAYERS", "Buttons": "BUTTONS", "Control": "CONTROL", "Year": "YEAR",
          "Manufacturer": "MAKER", "Rotation": "ROTATION", "Series": "SERIES"}


def draw_classify(fe, ui, now):
    g = fe.ov["game"]
    W.frame(ui, {}, "Classify", [])
    tiny.centered(ui, tiny.fit(g.get("Title") or g["Name"], SW), T.COMMENT, WW // 2, 32)
    y0 = 42
    fields = fe.ov["fields"]
    for i, (field, values, k) in enumerate(fields):
        y = y0 + i * 20
        on = i == fe.ov["sel"]
        tile_frame(ui, (SX, y, SW, 17), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (SX, y, SW, 17), 2 if on else 1)
        W.text(ui, LABELS.get(field, field.upper()), T.YELLOW if on else T.COMMENT, SX + 8, y + 5)
        value = values[k] if values else "-"
        vx = SX + 92
        if on and values:
            pygame.draw.polygon(ui, T.PINK, [(vx - 8, y + 8), (vx - 3, y + 4), (vx - 3, y + 12)])
        W.text(ui, fit(value, SX + SW - vx - 14), T.FG, vx, y + 5)
        if on and values:
            ax = vx + W.width(fit(value, SX + SW - vx - 14)) + 4
            pygame.draw.polygon(ui, T.PINK, [(ax + 5, y + 8), (ax, y + 4), (ax, y + 12)])
    y = y0 + len(fields) * 20 + 2
    on = fe.ov["sel"] == len(fields)
    W.button(ui, "SAVE", WW // 2, y, on, w=90)
    tiny.centered(ui, "SAVED WITH THE GAME'S INFO - THE FILTERS USE IT", T.GREEN, WW // 2, y + 24)


def draw_rename(fe, ui, now):
    W.frame(ui, {}, "Rename", [])
    g = fe.game()
    value = fe.ov["value"]
    W.block(ui, (SX, 36, SW, 22), T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.PINK, (SX, 36, SW, 22), 2)
    shown = value.upper()
    while W.width(shown) > SW - 24:
        shown = shown[1:]
    w = W.text(ui, shown, T.FG, SX + 8, 43)
    pygame.draw.rect(ui, T.PINK, (SX + 9 + w, 42, 7, 10))
    tiny.text(ui, tiny.fit("ORIGINAL: " + (g.get("Title") or g["Name"]), SW), T.COMMENT, SX, 62)
    keys = fe.KEYS
    kw, kh = min(28, (SW + 4) // 10), 22   # (em pe, as teclas encolhem)
    kx0 = (WW - 10 * kw) // 2
    r0, c0 = fe.ov["key"]
    for r, row in enumerate(keys):
        for c, ch in enumerate(row):
            x, y = kx0 + c * kw, 74 + r * (kh + 3)
            on = (r, c) == (r0, c0)
            tile_frame(ui, (x, y, kw - 3, kh), on, now)
            pygame.draw.rect(ui, T.PINK if on else T.LINE, (x, y, kw - 3, kh), 2 if on else 1)
            W.text(ui, ch, T.FG if on else T.COMMENT, x + (kw - 3 - W.width(ch)) // 2 + 1, y + 7)
    y = 74 + 4 * (kh + 3)
    k = kw / 28
    for i, (label, wd, xo) in enumerate((("SPACE", round(92 * k), 0), ("DELETE", round(72 * k), round(98 * k)),
                                         ("SAVE", round(72 * k), round(176 * k)))):
        x = kx0 + xo
        on = (r0, c0) == (4, i)
        tile_frame(ui, (x, y, wd, kh), on, now)
        pygame.draw.rect(ui, T.PINK if on else (T.GREEN if label == "SAVE" else T.LINE), (x, y, wd, kh),
                         2 if on else 1)
        W.text(ui, label, T.FG if on else (T.GREEN if label == "SAVE" else T.COMMENT),
               x + (wd - W.width(label)) // 2, y + 7)


def trash(ui, cx, cy, c):
    ui.fill(c, (cx - 6, cy - 6, 13, 2))
    ui.fill(c, (cx - 2, cy - 8, 5, 2))
    pygame.draw.polygon(ui, c, [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx + 4, cy + 7), (cx - 4, cy + 7)])
    for dx in (-2, 0, 2):
        ui.fill(T.BG_DEEP, (cx + dx, cy - 1, 1, 6))


def draw_delete(fe, ui, now):
    """A pergunta antes de apagar o jogo, com os arquivos que saem."""
    import os
    g = fe.ov["game"]
    files = fe.ov["files"]
    pw, ph = min(248, WW - 6), 98
    px, py = (WW - pw) // 2, (HH - ph) // 2
    card(ui, (px, py, pw, ph))
    W.centered(ui, "DELETE THIS GAME?", T.RED, py + 10)
    tiny.centered(ui, tiny.fit(g.get("Title") or g["Name"], pw - 16), T.FG, WW // 2, py + 24)
    names = ", ".join(os.path.basename(f) + ("/" if os.path.isdir(f) else "") for f in files)
    tiny.centered(ui, tiny.fit(names, pw - 16), T.COMMENT, WW // 2, py + 34)
    tiny.centered(ui, "THE FILES CANNOT BE BROUGHT BACK", T.ORANGE, WW // 2, py + 44)
    W.button(ui, "YES", WW // 2 - 50, py + 60, fe.ov["sel"] == 0)
    W.button(ui, "NO", WW // 2 + 50, py + 60, fe.ov["sel"] == 1)


def draw_capture(fe, ui, now):
    """A escolha do atalho que fecha o jogo: a tecla (a proxima apertada) ou
    os botoes do painel segurados juntos, com o tempo que falta."""
    pw, ph = min(250, WW - 6), 110
    px, py = (WW - pw) // 2, (HH - ph) // 2
    card(ui, (px, py, pw, ph))
    mono = time.monotonic()
    if fe.overlay == "exitkey":
        W.centered(ui, "PRESS THE KEY", T.FG, py + 10)
        tiny.centered(ui, "ON THE KEYBOARD THAT CLOSES THE GAME", T.COMMENT, WW // 2, py + 24)
        # Uma tecla desenhada, piscando.
        kx, ky = WW // 2 - 16, py + 36
        W.block(ui, (kx, ky, 32, 28), T.BG_DEEP, None)
        pygame.draw.rect(ui, T.PINK if int(now * 2) % 2 else T.PURPLE, (kx, ky, 32, 28), 2)
        pygame.draw.rect(ui, T.LINE, (kx + 3, ky + 3, 26, 18), 1)
        W.text(ui, "?", T.YELLOW, kx + 12, ky + 8)
        tiny.centered(ui, "BACK ON THE PANEL: CANCEL", T.COMMENT, WW // 2, py + 72)
    else:
        W.centered(ui, "HOLD THE BUTTONS", T.FG, py + 10)
        tiny.centered(ui, "2 OR MORE TOGETHER, FOR 1 SECOND", T.COMMENT, WW // 2, py + 24)
        held = fe.ov.get("held")
        names = "+".join(c[1:] if c[0] == "b" and c[1:].isdigit() else c.upper()
                         for c in ("up", "down", "left", "right", "b1", "b2", "b3", "b4", "b5", "b6", "start", "coin")
                         if held and c in held)
        W.centered(ui, names or "...", T.YELLOW, py + 40)
        # A barra de quanto ja foi segurado.
        bx, bw = px + 30, pw - 60
        W.block(ui, (bx, py + 56, bw, 8), T.BG_DEEP, None)
        if held:
            fill = min(1.0, (mono - fe.ov.get("at", mono)) / 1.0)
            ui.fill(T.GREEN, (bx, py + 56, round(bw * fill), 8))
        pygame.draw.rect(ui, T.LINE, (bx, py + 56, bw, 8), 1)
        tiny.centered(ui, "THE SAME BUTTONS CLOSE THE GAME, HELD 1 SECOND", T.COMMENT, WW // 2, py + 72)
    wait = max(0, 8 - (mono - fe.ov.get("since", mono)))
    tiny.centered(ui, "NOTHING PRESSED: KEEPS AS IT WAS IN %d S" % math.ceil(wait), T.ORANGE, WW // 2, py + 90)


def draw_exit(fe, ui, now):
    pw, ph = 220, 74
    px, py = (WW - pw) // 2, (HH - ph) // 2
    card(ui, (px, py, pw, ph))
    W.centered(ui, "BACK TO THE FLIPEROS MENU?", T.FG, py + 12)
    W.button(ui, "YES", WW // 2 - 50, py + 40, fe.ov["sel"] == 0)
    W.button(ui, "NO", WW // 2 + 50, py + 40, fe.ov["sel"] == 1)


def draw_letter(ui, letter):
    size = 80
    x, y = (WW - size) // 2, (HH - size) // 2 + 6
    W.block(ui, (x, y, size - 2, size - 2), T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.PINK, (x, y, size - 2, size - 2), 2)
    big = W.big(letter, 7, W.MARQUEE)
    shadow = W.big(letter, 7, (0x40, 0x20, 0x70))
    lx, ly = x + (size - 2 - big.get_width()) // 2, y + (size - 2 - big.get_height()) // 2 + 2
    ui.blit(shadow, (lx + 3, ly + 3))
    ui.blit(big, (lx, ly))


def draw_toast(ui, text):
    # No alto, debaixo do titulo: embaixo ficam as informacoes e os botoes.
    w = W.width(text) + 16
    x, y = (WW - w) // 2, 30
    W.block(ui, (x, y, w, 16), T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.PINK, (x, y, w, 16), 1)
    W.text(ui, text, T.FG, x + 8, y + 4)


def bell_icon(ui, cx, cy, c):
    """O sininho de 12x12 com o centro em (cx, cy)."""
    pygame.draw.rect(ui, c, (cx - 1, cy - 6, 2, 2))
    pygame.draw.polygon(ui, c, [(cx - 3, cy - 4), (cx + 2, cy - 4), (cx + 4, cy + 1), (cx + 5, cy + 3),
                                (cx - 6, cy + 3), (cx - 5, cy + 1)])
    pygame.draw.rect(ui, c, (cx - 2, cy + 4, 3, 2))
    pygame.draw.line(ui, T.BG_DEEP, (cx - 2, cy - 3), (cx - 3, cy + 1))


def draw_notice(ui, name, title, now):
    """O aviso embaixo de que outro gabinete abriu uma party ou um link: o
    sininho (balancando) a esquerda, "NOME IS PLAYING" e, se o jogo esta na
    lista, o nome dele em letra pequena. O nome do gabinete tem ate 12 letras
    (felink.NAME_MAX): cabe em pe, com 240 de largura."""
    line = "%s IS PLAYING" % name
    w = max(W.width(line), tiny.width(tiny.fit(title, WW - 44)) if title else 0) + 32
    h = 26 if title else 18
    x, y = (WW - w) // 2, HH - h - 22
    W.block(ui, (x, y, w, h), T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.YELLOW, (x, y, w, h), 1)
    swing = (0, 1, 0, -1)[int(now * 6) % 4]
    bell_icon(ui, x + 12 + swing, y + 9, T.YELLOW)
    W.text(ui, line, T.FG, x + 24, y + 5)
    if title:
        tiny.text(ui, tiny.fit(title, WW - 44), T.COMMENT, x + 24, y + 16)


def draw(fe, now):
    """Um quadro em fe.back."""
    back = fe.back
    t = now - fe.start
    fe.bg.draw(back, t)
    ui = pygame.Surface((WW, HH), pygame.SRCALPHA)
    # O video nos tres modos, e nao com uma tela inteira por cima (a pagina
    # "+", o Classify, o Rename). Na lista, os da grade e da tela cheia param.
    fe.abs_now = now
    # A troca de romlist: a tela de antes sai por baixo do que entra.
    intro = getattr(fe, "intro", None)
    if intro is not None:
        intro.setdefault("style", transition(fe))
        if intro["style"] == "slide" or now - intro["start"] >= INTRO:
            fe.intro = None
        else:
            fe.slide = None
            leave(back, fe)
    fe.video_used = False
    fe.video_ok = fe.overlay not in ("more", "classify", "rename", "controls")
    if (fe.mode == "list" or not fe.video_ok) and getattr(fe, "grid", None) is not None and fe.grid.videos:
        fe.grid.stop()
    if not fe.rows:
        empty(fe, ui)
    elif fe.mode == "list":
        draw_list(fe, ui, t)
    elif fe.mode == "full":
        draw_full(fe, ui, back, t)
    else:
        draw_flow(fe, ui, t)
    if not fe.video_used:
        fe.player.request(None, 0, 0, now)
    slide = getattr(fe, "slide", None)
    if slide and not fe.shot and now - slide[2] < SLIDE:
        # A troca de romlist: a tela de antes sai para um lado e a nova
        # entra pelo outro (o fundo fica).
        old, side, start = slide
        p = (now - start) / SLIDE
        p = 1 - (1 - p) ** 3
        back.blit(old, (round(-side * p * WW), 0))
        back.blit(ui, (round(side * (1 - p) * WW), 0))
    else:
        fe.slide = None
        back.blit(ui, (0, 0))
        curtain_open(back, fe)
    fe.last_ui = ui
    # A tela como estava, para sair na proxima troca de romlist (sem a tira
    # nem os menus por cima).
    fe.last_screen = back.copy()
    if fe.letter and now < fe.letter[1] and fe.letter[0]:
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_letter(top, fe.letter[0])
        back.blit(top, (0, 0))
    o = fe.overlay
    if not o and now < fe.ribbon_until and fe.cats:
        # Escolhido o sistema, a tira some aos poucos (RIBBON_FADE) e a lista
        # nova entra.
        k = min(1.0, (fe.ribbon_until - now) / RIBBON_FADE)
        dim(back, round(120 * k))
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_ribbon(fe, top, t)
        if k < 1:
            top.set_alpha(round(255 * k))
        back.blit(top, (0, 0))
    if o:
        if o in ("more", "classify", "rename", "controls"):
            fe.bg.draw(back, t)
        else:
            dim(back, 160 if o != "guide" else 175)
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        if o == "guide":
            draw_guide(fe, top)
        elif o == "popup" and fe.rows:
            draw_popup(fe, top, t)
        elif o == "more":
            draw_more(fe, top, t)
        elif o == "filter":
            draw_filter(fe, top, t)
        elif o == "lobby":
            draw_lobby(fe, top, t)
        elif o == "transfer":
            draw_transfer(fe, top, t)
        elif o == "unpack":
            draw_unpack(fe, top, t)
        elif o == "options":
            draw_options(fe, top, t)
        elif o == "hidden":
            draw_hidden(fe, top, t)
        elif o == "controls":
            draw_controls(fe, top, t)
        elif o == "classify":
            draw_classify(fe, top, t)
        elif o == "rename":
            draw_rename(fe, top, t)
        elif o == "exit":
            draw_exit(fe, top, t)
        elif o == "delete":
            draw_delete(fe, top, t)
        elif o in ("exitkey", "exitpad"):
            draw_capture(fe, top, t)
        back.blit(top, (0, 0))
    if fe.toast and now < fe.toast[1]:
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_toast(top, fe.toast[0])
        back.blit(top, (0, 0))
    notice = getattr(fe, "notice", None)
    if notice and now < notice[2]:
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_notice(top, notice[0], notice[1], now)
        back.blit(top, (0, 0))
