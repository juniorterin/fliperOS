# O desenho do frontend do FliperOS (gui/fliperos-frontend): os tres modos
# (lista, tela cheia, grade) e o que fica por cima deles (o guia dos
# controles, o menu do jogo, a pagina "+", os filtros, as categorias, o menu
# do Tab, o Classify, o Rename e a pergunta de sair). draw(fe, agora) desenha
# em fe.back, a tela logica de 320x240.

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


def menu_icon(surf, cx, cy, c):
    for dy in (-4, 0, 4):
        surf.fill(c, (cx - 5, cy + dy - 1, 11, 2))


def back_icon(surf, cx, cy, c):
    pygame.draw.polygon(surf, c, [(cx - 6, cy), (cx - 1, cy - 5), (cx - 1, cy + 5)])
    surf.fill(c, (cx - 1, cy - 2, 7, 4))


def chevrons(surf, cx, cy, c, up):
    s = -1 if up else 1
    for k in (-3, 2):
        y = cy + k * s
        pygame.draw.lines(surf, c, False, [(cx - 5, y - 3 * s), (cx, y + 2 * s), (cx + 5, y - 3 * s)], 2)


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


def players_icon(fe, color):
    key = ("players", color)
    if key not in fe.media:
        img = pygame.Surface((len(PLAYER_ICON[0]), len(PLAYER_ICON)), pygame.SRCALPHA)
        for y, row in enumerate(PLAYER_ICON):
            for x, c in enumerate(row):
                if c == "#":
                    img.set_at((x, y), color + (255,))
        fe.media[key] = img
    return fe.media[key]


# A pistola (o Arcadeflow nao tem icone de lightgun), no jeito do boneco
# dos jogadores: um bitmap de pixels cheios.
LIGHTGUN_ICON = (
    "......................",
    ".###################..",
    ".####################.",
    ".####################.",
    ".###################..",
    ".######...............",
    ".######.###...........",
    ".######...#...........",
    ".######.###...........",
    ".######...............",
    "..#####...............",
    "..#####...............",
    "..#####...............",
    "...####...............",
    "...####...............",
    "......................",
)


def lightgun_icon(fe, h, color):
    key = ("lightgun", h, color)
    if key not in fe.media:
        img = pygame.Surface((len(LIGHTGUN_ICON[0]), len(LIGHTGUN_ICON)), pygame.SRCALPHA)
        for y, row in enumerate(LIGHTGUN_ICON):
            for x, ch in enumerate(row):
                if ch == "#":
                    img.set_at((x, y), color + (255,))
        img = img.subsurface(img.get_bounding_rect()).copy()
        if img.get_height() > h:
            img = pygame.transform.smoothscale(img, (max(1, round(img.get_width() * h / img.get_height())), h))
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
    if game.get("Control"):
        rows.append((control_icon(fe, game, h, T.PINK), control_short(game["Control"]), T.PINK))
    parts = []
    if game.get("Buttons"):
        parts.append("%s BTN" % game["Buttons"])
    if game.get("Players") and not icons_only:
        parts.append("%sP" % game["Players"])
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


# ── Os modos ───────────────────────────────────────────────────────

def frame(fe, ui):
    cat = fe.category()
    W.frame(ui, {}, (cat or {}).get("name", "FliperOS") or "FliperOS", [])
    # O filtro em uso, pequeno, debaixo do titulo (o "All Games" nao).
    name = fe.lib.filters[fe.flt % len(fe.lib.filters)]["name"]
    if name.lower() != "all games":
        tiny.text(ui, "FILTER: " + name.replace("©", "(C)"), T.CYAN, SX, 29)


def empty(fe, ui):
    frame(fe, ui)
    flt = fe.lib.filters[fe.flt % len(fe.lib.filters)]["name"]
    W.paragraph(ui, ["No games here.", "", "Filter: " + flt,
                     "Copy games to the folders in ~/roms (the network share \\\\fliperos\\roms)."], 80)


def list_geom():
    """((x, largura, y, linhas) da lista, (x, y, largura, altura) da imagem).
    Deitado, a lista a esquerda e a imagem a direita; em pe, a imagem em
    cima, larga, e a lista embaixo."""
    if T.VERTICAL:
        return (SX, SW - 8, 200, 6), (SX, 34, SW, 112)
    px = SX + LIST_W + 14
    return (SX, LIST_W, 36, 13), (px, 36, SX + SW - px, LIST_SH)


def draw_list(fe, ui, now):
    frame(fe, ui)
    (lx, lw, y0, rows), (px, py, pw, sh) = list_geom()
    if fe.cursor < fe.top:
        fe.top = fe.cursor
    if fe.cursor >= fe.top + rows:
        fe.top = fe.cursor - rows + 1
    fe.top = max(0, min(fe.top, max(0, len(fe.rows) - rows)))
    for i in range(fe.top, min(len(fe.rows), fe.top + rows)):
        game, level, extra = fe.rows[i]
        y = y0 + (i - fe.top) * 14
        on = i == fe.cursor
        if level == 0:
            x = lx + 14 if extra else lx
            if extra:
                # O [+] do jogo pai, um pouco transparente (aberto, menos).
                opened = game["Name"] in fe.opened
                mark = pygame.Surface((10, 10), pygame.SRCALPHA)
                mark.fill(T.BG_DEEP)
                pygame.draw.rect(mark, T.PINK if opened else T.COMMENT, (0, 0, 10, 10), 1)
                mark.fill(T.PINK if opened else T.COMMENT, (2, 4, 6, 2))
                if not opened:
                    mark.fill(T.COMMENT, (4, 2, 2, 6))
                mark.set_alpha(190 if opened else 120)
                ui.blit(mark, (lx, y + 1))
            label = fe.fd.short_title(game)
            color = T.FG if game["Name"] in fe.opened else T.COMMENT
        else:
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
        if on:
            # O escolhido inteiro: o que nao cabe corre em circulo.
            ticker(ui, text_img(label.upper(), color), x, y + 2, lx + lw - x - 12, now)
        else:
            W.text(ui, fit(label, lx + lw - x - 12), color, x, y + 2)
    if len(fe.rows) > rows:
        W.scrollbar(ui, lx + lw + 4, y0, rows * 14 - 2, fe.top, rows, len(fe.rows))
    W.text(ui, "%d/%d" % (fe.cursor + 1, len(fe.rows)), T.LINE, lx + lw, y0 + rows * 14 + 1, right=True)
    # A imagem, o logo e as informacoes (a direita, ou em cima em pe).
    game = fe.game()
    y0 = py
    W.block(ui, (px, y0, pw, sh), T.BG_DEEP, T.PURPLE)
    shot = picture(fe, game, pw - 4, sh - 4)
    if shot:
        blit_center(ui, shot, px + 2, y0 + 2, pw - 4, sh - 4)
        if fe.scraping is game:
            looking(ui, px + 4, y0 + sh - 14, pw - 8)
    elif fe.scraping is game:
        # Sem nada ainda: o scrape sozinho esta buscando.
        W.glow(ui, (px + 2, y0 + 2, pw - 4, sh - 4), {"now": now})
        tiny.centered(ui, "LOOKING FOR ART...", T.CYAN, px + pw // 2, y0 + sh // 2 - 2)
    pygame.draw.rect(ui, T.PINK, (px, y0, pw, sh), 2)
    logo = image(fe, media(fe, game, "logo"), min(pw - 8, 200), 28)
    y = y0 + sh + 6
    if logo:
        blit_center(ui, logo, px, y0 + sh - 14, pw, 28)
        y = y0 + sh + 18
    else:
        # Sem logo, o titulo numa linha: o que nao cabe corre em circulo.
        ticker(ui, text_img(fe.fd.short_title(game).upper(), T.YELLOW), px, y, pw, now)
        y += 12
    W.text(ui, fit(facts_line(game), pw), T.YELLOW, px, y)
    y += 12
    # Os icones, sem texto, em duas fileiras: o genero e os jogadores (o
    # boneco e o numero); o controle e os botoes. Sem o icone, o texto
    # pequeno no lugar dele.
    rows = icon_rows(fe, game, 20, icons_only=True)
    genre = [r for r in rows if r[2] == T.CYAN]
    control = [r for r in rows if r[2] == T.PINK]
    buttons = [(buttons_icon(fe, game, 13, T.YELLOW), t, c) for _, t, c in rows if c == T.YELLOW]
    players = (game.get("Players") or "").strip()
    px_next = px
    for line in (genre, control + buttons):
        x = px_next if T.VERTICAL else px
        for img, text, color in line:
            if img:
                if x + img.get_width() > SX + SW:
                    break
                ui.blit(img, (x, y + (20 - img.get_height()) // 2))
                x += img.get_width() + 8
            else:
                label = text.upper()
                if x + tiny.width(label) > SX + SW:
                    break
                x += tiny.text(ui, label, color, x, y + 8) + 8
        if line is genre and players.isdigit() and x + 30 <= SX + SW:
            ui.blit(players_icon(fe, T.GREEN), (x, y + 2))
            W.text(ui, players, T.GREEN, x + 19, y + 6)
        if T.VERTICAL and line is genre:
            # Em pe, tudo numa fileira so: a lista vem logo embaixo.
            px_next = x + (38 if players.isdigit() else 0)
            continue
        if line or (line is genre and players.isdigit()):
            y += 24
    if T.VERTICAL:
        # Em pe, o indicador do modo comercial embaixo, a esquerda.
        if fe.commercial:
            coin_box(fe, ui, SX, HH - COIN_H - 4, now)
        return
    played = game.get("PlayedCount")
    chips = []
    if game.get("Favourite") == "1":
        chips.append(("* FAV", T.YELLOW))
    if played:
        chips.append(("PLAYED %sX" % played, T.COMMENT))
    x = px
    for text, color in chips:
        w = tiny.width(text) + 8
        W.block(ui, (x, y + 2, w, 10), T.BG_DEEP, None)
        pygame.draw.rect(ui, T.LINE, (x, y + 2, w, 10), 1)
        tiny.text(ui, text, color, x + 4, y + 5)
        x += w + 4
    # O modo comercial: o indicador debaixo dos icones dos comandos.
    if fe.commercial:
        coin_box(fe, ui, px, min(y + (16 if chips else 4), HH - COIN_H - 6), now)


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
    full_background(fe, back)
    cat = fe.category()
    W.text(ui, (cat or {}).get("name", "").upper()[:24], T.RED, SX, 12)
    W.text(ui, "%d/%d" % (fe.cursor + 1, len(fe.rows)), T.FG, SX + SW, 12, right=True)
    for i, c in enumerate(W.RAINBOW):
        pygame.draw.rect(ui, c, (SX, 24 + i, 40, 1))
    # O modo comercial: o indicador no canto de cima, a esquerda.
    if fe.commercial:
        coin_box(fe, ui, SX, 34, now)
    if fe.scraping is game:
        looking(ui, SX, 38 + COIN_H if fe.commercial else 36)
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
    arrow(ui, tx + tw // 2, ty - 7, (0, -1), T.PINK if top > 0 else T.LINE, 5)
    ui.set_clip((tx - 2, ty - 1, tw + 6, n * step - gap + 4))
    first = int(math.floor(ftop))
    for i in range(max(0, first), min(len(fe.rows), first + n + 1)):
        g = fe.rows[i][0]
        y = round(ty + (i - ftop) * step)
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
    y = round(ty + (fsel - ftop) * step)
    pygame.draw.rect(ui, T.PINK, (tx, y, tw, th), 2)
    ui.set_clip(None)
    more = top + n < len(fe.rows)
    arrow(ui, tx + tw // 2, ty + n * step + 3, (0, 1), T.PINK if more else T.LINE, 5)
    # O jogo escolhido, embaixo a esquerda (fora da coluna).
    right = tx - 8
    clone = is_clone(fe, game)
    logo = None if clone else image(fe, media(fe, game, "logo"), min(200, right - SX), 44)
    if logo:
        ui.blit(logo, (SX, HH - 62 - logo.get_height()))
    y = HH - 56
    if clone:
        # O clone: o logo seria o do pai; o nome completo dele, correndo.
        ticker(ui, text_img((game.get("Title") or game["Name"]).upper(), T.YELLOW, big=True),
               SX, y, right - SX, now)
    else:
        ui.blit(W.big(fit(fe.fd.short_title(game), right - SX), 1, W.LABEL), (SX, y))
    W.text(ui, fit(facts_line(game), right - SX), T.CYAN, SX, y + 12)
    icon_line(fe, ui, game, SX, y + 24, right, 12)


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
    frame(fe, ui)
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
        g = fe.rows[i][0]
        if i == fe.cursor:
            sel = g
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
        if fe.scraping is g:
            looking(ui, x + 2, y + th - 12, tw - 4)
    grid_videos(fe, top_row, rows_shown, tw - 2, th - 2)
    fx = round(x0 + fcol * (tw + gap))
    fy = round(y0 + (frow - ftop) * step_y)
    pygame.draw.rect(ui, T.PINK, (fx - 2, fy - 2, tw + 4, th + 4), 2)
    ui.set_clip(None)
    # No canto, a barra de rolagem com uma seta pequena em cima e embaixo.
    bx_, by_, bh_ = SX + SW - 2, y0 + 7, rows_shown * step_y - 22
    W.scrollbar(ui, bx_, by_, bh_, top_row, rows_shown, max(rows_shown, total_rows))
    arrow(ui, bx_ + 2, by_ - 4, (0, -1), T.PINK if top_row > 0 else T.LINE, 3)
    arrow(ui, bx_ + 2, by_ + bh_ + 4, (0, 1), T.PINK if top_row + rows_shown < total_rows else T.LINE, 3)
    if sel:
        # A aba debaixo das miniaturas, do lado do jogo escolhido: mais um
        # toque para aquele lado troca a romlist.
        col = fe.cursor % cols
        if len(fe.cats) > 1 and (col == cols - 1 or fe.cursor == len(fe.rows) - 1 or col == 0):
            side = 1 if (col == cols - 1 or fe.cursor == len(fe.rows) - 1) else -1
            nxt = fe.cats[(fe.cat + side) % len(fe.cats)]["name"].upper()
            bottom_tab(ui, nxt, side, x0, gw, y0 + rows_shown * step_y - 4)
    g = fe.game()
    # No modo comercial o logo, os textos e os icones sobem um pouco, os
    # icones vao em duas linhas, e o indicador fica no canto de baixo a
    # direita.
    commercial = fe.commercial
    y = HH - 52 if commercial else HH - 46
    clone = is_clone(fe, g)
    # Em pe nao ha largura para o logo, os icones e o indicador: o nome.
    narrow = commercial and getattr(fe, "vertical", False)
    logo = None if clone or narrow else image(fe, media(fe, g, "logo"), 110, 30)
    tx = SX
    if logo:
        blit_center(ui, logo, SX, y, 110, 30)
        tx = SX + 118
    elif clone:
        # O clone: o nome completo, correndo (o logo seria o do pai).
        ticker(ui, text_img((g.get("Title") or g["Name"]).upper(), T.YELLOW), SX, y + 2, 150, now)
    else:
        W.text(ui, fit(fe.fd.short_title(g), 150), T.YELLOW, SX, y + 2)
    if logo:
        W.text(ui, fit(facts_line(g), SX + SW - tx), T.CYAN, tx, y + 2)
    else:
        W.text(ui, fit(facts_line(g), 150), T.CYAN, SX + 154, y + 2)
        tx = SX
    if commercial:
        bx, by = SX + SW - COIN_W, HH - COIN_H - 8
        rows = icon_rows(fe, g, 12)
        icon_line(fe, ui, g, tx, y + 13, bx - 4, 12, rows[:2])
        icon_line(fe, ui, g, tx, y + 26, bx - 4, 12, rows[2:])
        coin_box(fe, ui, bx, by, now)
    else:
        icon_line(fe, ui, g, tx, y + 14, SX + SW, 12)


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


PANEL = [("1", T.GREEN, menu_icon, "MENU"), ("2", T.RED, back_icon, "BACK"),
         ("3", T.CYAN, lambda s, x, y, c: chevrons(s, x, y, c, True), "PAGE UP"),
         ("4", T.YELLOW, lambda s, x, y, c: star(s, x, y + 1, c), "FAVOURITE"), ("5", T.PURPLE, funnel, "FILTER"),
         ("6", T.CYAN, lambda s, x, y, c: chevrons(s, x, y, c, False), "PAGE DOWN")]


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


def draw_guide(fe, ui):
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
    jx, jy = (WW // 2, py + 70) if vertical else (px + 54, py + 70)
    pygame.draw.circle(ui, T.SPACE, (jx, jy), 21)
    pygame.draw.circle(ui, T.LINE, (jx, jy), 21, 2)
    pygame.draw.circle(ui, T.RED, (jx, jy), 9)
    pygame.draw.circle(ui, (0xff, 0xa0, 0xa0), (jx - 3, jy - 3), 3)
    for d, color in (((0, -1), T.CYAN), ((0, 1), T.CYAN), ((-1, 0), T.PINK), ((1, 0), T.PINK)):
        arrow(ui, jx + d[0] * 30, jy + d[1] * 30, d, color, 5)
    tiny.centered(ui, "GAMES", T.CYAN, jx, jy - 44)
    tiny.text(ui, "GAME LIST", T.PINK, jx - 19 - tiny.width("GAME LIST"), jy + 9)
    tiny.text(ui, "GAME LIST", T.PINK, jx + 19, jy + 9)
    tiny.centered(ui, "GAMES", T.CYAN, jx, jy + 40)
    tiny.centered(ui, "HOLD: FASTER", T.COMMENT, jx, jy + 49)
    tiny.centered(ui, "3 S: LETTER BY LETTER", T.COMMENT, jx, jy + 56)
    if vertical:
        pygame.draw.line(ui, T.LINE, (px + 10, py + 136), (px + pw - 11, py + 136))
    else:
        pygame.draw.line(ui, T.LINE, (px + 112, py + 28), (px + 112, py + ph - 26))
    # Os seis botoes juntos, como no painel; o nome de cada um fora, em cima
    # (a fileira de cima) ou embaixo, com uma linha e a seta ate ele.
    r, step = 12, 30
    if vertical:
        bx0, by0 = WW // 2 - step, py + 172
    else:
        bx0, by0 = px + 112 + (pw - 112 - 2 * step) // 2, py + 60
    ry = round(r * FLAT)
    for i, (num, color, draw_icon, label) in enumerate(PANEL):
        col, row = i % 3, i // 3
        cx = bx0 + col * step
        cy = by0 + row * 32 - (3 if col == 1 else 0)
        button3d(ui, cx, cy, r, color)
        # O desenho no topo, achatado como ele.
        icon = pygame.Surface((24, 24), pygame.SRCALPHA)
        draw_icon(icon, 12, 12, shade(color, 0.3))
        icon = pygame.transform.smoothscale(icon, (24, round(24 * FLAT)))
        ui.blit(icon, (cx - 12, cy - icon.get_height() // 2))
        text = num + " " + label
        w = tiny.width(text)
        tx = {0: cx + 3 - w, 1: cx - w // 2, 2: cx - 3}[col]
        top, bottom = cy - ry - 4, cy + LIFT + ry + 5
        if row == 0:
            ty, y0, y1, d = by0 - 30, by0 - 23, top, (0, 1)
        else:
            ty, y0, y1, d = bottom + 13, bottom + 11, bottom, (0, -1)
        tiny.text(ui, text, T.FG, tx, ty)
        pygame.draw.line(ui, T.COMMENT, (cx, y0), (cx, y1 - d[1] * 2))
        arrow(ui, cx, y1, d, T.COMMENT, 3)
    # Debaixo dos botoes (a esquerda ficam as dicas do direcional).
    hint_x = WW // 2 if vertical else px + 112 + (pw - 112) // 2
    tiny.centered(ui, "START: VIEW MODE   TAB: GAME OPTIONS", T.COMMENT, hint_x, py + ph - 30)
    msg = "PRESS ANY BUTTON TO START"
    ui.blit(W.big(msg, 1, W.LABEL), (px + (pw - W.width(msg)) // 2, py + ph - 16))


def draw_popup(fe, ui, now):
    g = fe.game()
    pw, ph = 216, 104
    px, py = (WW - pw) // 2, (HH - ph) // 2 - 4
    card(ui, (px, py, pw, ph))
    W.text(ui, fit(fe.fd.short_title(g), pw - 16), T.YELLOW, px + 8, py + 8)
    fav = g.get("Favourite") == "1"
    tiles = [("PLAY", play_icon, T.GREEN), ("UNFAVOURITE" if fav else "FAVOURITE",
                                            lambda s, x, y, c: star(s, x, y, c, 11, outline=False), T.YELLOW),
             ("MORE", plus_icon, T.CYAN)]
    size, gap = 52, 12
    tx0 = px + (pw - (3 * size + 2 * gap)) // 2
    ty = py + 24
    for i, (label, draw_icon, color) in enumerate(tiles):
        x = tx0 + i * (size + gap)
        on = i == fe.ov["sel"]
        tile_frame(ui, (x, ty, size, size), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (x, ty, size, size), 2 if on else 1)
        draw_icon(ui, x + size // 2, ty + size // 2, color if on else T.COMMENT)
    label = tiles[fe.ov["sel"]][0]
    ui.blit(W.big(label, 1, W.LABEL), (px + (pw - W.width(label)) // 2, ty + size + 10))


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
    filters = fe.lib.filters
    rows = 13
    sel = fe.ov["sel"]
    top = fe.ov.get("top", 0)
    if sel < top:
        top = sel
    if sel >= top + rows:
        top = sel - rows + 1
    fe.ov["top"] = top
    y0 = py + 22
    for i in range(top, min(len(filters), top + rows)):
        y = y0 + (i - top) * 13
        on = i == sel
        if on:
            tile_frame(ui, (px + 6, y - 2, pw - 22, 12), True, now)
            pygame.draw.rect(ui, T.PINK, (px + 6, y - 2, pw - 22, 12), 1)
        label = filters[i]["name"].replace("©", "(C)")
        W.text(ui, fit(label, pw - 52), T.FG if on else T.COMMENT, px + 26, y)
        if i == fe.flt % len(filters):
            pygame.draw.lines(ui, T.GREEN, False, [(px + 10, y + 4), (px + 13, y + 7), (px + 18, y)], 2)
    if len(filters) > rows:
        W.scrollbar(ui, px + pw - 10, y0 - 2, rows * 13, top, rows, len(filters))


def draw_ribbon(fe, ui, now):
    band_y, band_h = 70, 104
    W.block(ui, (0, band_y, WW, band_h), T.BG_DEEP, None)
    pygame.draw.line(ui, T.PINK, (0, band_y), (WW, band_y))
    pygame.draw.line(ui, T.PINK, (0, band_y + band_h - 1), (WW, band_y + band_h - 1))
    tiny.centered(ui, "GAME LIST", T.COMMENT, WW // 2, band_y + 7)
    n = len(fe.cats)
    # A tira desliza ate a romlist nova: pos corre ate fe.cat_pos (o indice
    # sem dar a volta), e cada quadrado cresce ao passar pelo meio.
    pos = ease(fe, "ribbon", getattr(fe, "cat_pos", fe.cat), fe.abs_now, speed=12.0, reach=3)
    base = math.floor(pos)
    tiles = []
    for k in range(-3, 5):
        d = base + k - pos
        if abs(d) > 2.6 or (n < 2 and abs(d) > 0.5):
            continue
        tiles.append((abs(d), d, (fe.cat + round(base + k - getattr(fe, "cat_pos", fe.cat))) % n))
    for dist, d, idx in sorted(tiles, reverse=True):
        c = fe.cats[idx]
        size = round(56 - 16 * dist if dist <= 1 else max(32, 40 - 8 * (dist - 1)))
        on = dist < 0.5
        cx = round(WW / 2 + d * 66)
        x, y = cx - size // 2, band_y + 20 + (56 - size) // 2
        tile_frame(ui, (x, y, size, size), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (x, y, size, size), 2 if on else 1)
        name = system_icon(c)
        icon = T.icon(name, 2 if size >= 44 else 1) if name else None
        if icon is None:
            icon = W.big(c["name"][:1].upper(), 3 if size >= 44 else 2, W.MARQUEE)
        if dist > 0.05:
            icon = icon.copy()
            icon.set_alpha(round(255 - 145 * min(1.0, dist)))
        blit_center(ui, icon, x, y, size, size)
    c = fe.cats[fe.cat % n]
    label = fit(c["name"], WW - 20)
    ui.blit(W.big(label, 1, W.LABEL), ((WW - W.width(label)) // 2, band_y + 80))
    count = len(fe.rows)
    tiny.centered(ui, "%d GAMES" % count, T.CYAN, WW // 2, band_y + 93)


def system_icon(cat):
    """O icone do programa da pasta (os de gui/icons)."""
    if cat.get("key") == "@arcade":
        return "frontend"         # (o joystick do FliperOS, nao o logo de um frontend)
    exe = (cat.get("exe", "") + " " + cat.get("args", "")).lower()
    for name in ("groovymame", "flycast", "pcsx2", "dolphin", "model2", "openbor", "retroarch", "fightcade"):
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


def draw_options(fe, ui, now):
    """O menu do Tab: as opcoes do jogo e, debaixo delas, as do frontend (o
    modo de exibicao, os clones, os jogos escondidos e o andamento do scrape
    automatico)."""
    g = fe.game()
    pw, ph = min(236, WW - 4), 224
    px, py = (WW - pw) // 2, max(8, (HH - ph) // 2)
    sel = fe.ov["sel"]
    card(ui, (px, py, pw, ph))
    ui.blit(W.big("GAME OPTIONS", 1, W.LABEL), (px + 10, py + 8))
    if g:
        tiny.text(ui, tiny.fit(g.get("Title") or g["Name"], pw - 20), T.COMMENT, px + 10, py + 20)
    items = [("CLASSIFY", T.YELLOW), ("RENAME", T.CYAN), ("SCRAPE THIS GAME", T.GREEN),
             ("HIDE THIS GAME", T.PURPLE), ("DELETE THIS GAME", T.RED)]
    for i, (label, color) in enumerate(items):
        y = py + 28 + i * 17
        option_row(ui, (px + 8, y, pw - 16, 16), label, i == sel, now)
        ix, iy = px + 20, y + 8
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
    # As opcoes do frontend, debaixo das do jogo: tres linhas a vista, que
    # rolam com a escolhida (as linhas 5 a 12 do fliperos-frontend, OPT_*).
    y = py + 116
    ui.blit(W.big("FRONTEND OPTIONS", 1, W.LABEL), (px + 10, y))
    y += 12
    right = px + pw - 14
    rows = [5, 6, 7, 8, 9, 10, 11] + ([12] if fe.commercial else [])
    shown = 3
    top = fe.ov.get("ftop", 0)
    if sel in rows:
        k = rows.index(sel)
        top = k if k < top else (k - shown + 1 if k >= top + shown else top)
    top = fe.ov["ftop"] = max(0, min(top, len(rows) - shown))
    for k, opt in enumerate(rows[top:top + shown]):
        draw_option(fe, ui, opt, (px + 8, y + k * 17, pw - 16, 16), sel == opt, right, now)
    if len(rows) > shown:
        W.scrollbar(ui, px + pw - 5, y, shown * 17 - 1, top, shown, len(rows))
    draw_harvest(fe, ui, px + 8, y + 2 * 17 + 20, pw - 16)


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


def draw_option(fe, ui, opt, rect, on, right, now):
    """Uma linha das opcoes do frontend: o rotulo e o valor dela."""
    x, y, _, _ = rect
    labels = {5: "VIEW", 6: "SHOW CLONES", 7: "HIDDEN GAMES", 8: "EXIT KEY", 9: "EXIT BUTTONS",
              10: "POWER CLOSES GAME", 11: "COMMERCIAL MODE", 12: "MINUTES PER COIN"}
    option_row(ui, rect, "", on, now)
    W.text(ui, labels[opt], T.FG if on else T.COMMENT, x + 8, y + 4)
    if opt == 5:
        # O modo: os tres lado a lado, o de agora aceso.
        cx = right
        for mode, label in reversed((("list", "LIST"), ("full", "FULL SCREEN"), ("flow", "GRID"))):
            cx = chip(ui, cx, y, label, fe.mode == mode, on) - 3
    elif opt == 6:
        chip(ui, right, y, "ON" if fe.show_clones else "OFF", fe.show_clones, on)
    elif opt == 7:
        tiny.text(ui, "%d  >" % len(fe.lib.hidden()), T.PINK if on else T.COMMENT, right, y + 6, right=True)
    elif opt == 8:
        key = fe.exit_key[0] if fe.exit_key else "OFF"
        chip(ui, right, y, key, bool(fe.exit_key), on)
    elif opt == 9:
        combo = "+".join(c[1:] if c[0] == "b" and c[1:].isdigit() else c.upper() for c in fe.exit_combo)
        chip(ui, right, y, combo or "OFF", bool(fe.exit_combo), on)
    elif opt == 10:
        chip(ui, right, y, "ON" if fe.power_exit else "OFF", fe.power_exit, on)
    elif opt == 11:
        chip(ui, right, y, "ON" if fe.commercial else "OFF", fe.commercial, on)
    elif opt == 12:
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
        tiny.centered(ui, "BUTTON 2 ON A CONTROLLER: CANCEL", T.COMMENT, WW // 2, py + 72)
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


def draw(fe, now):
    """Um quadro em fe.back."""
    back = fe.back
    t = now - fe.start
    fe.bg.draw(back, t)
    ui = pygame.Surface((WW, HH), pygame.SRCALPHA)
    # O video nos tres modos, e nao com uma tela inteira por cima (a pagina
    # "+", o Classify, o Rename). Na lista, os da grade e da tela cheia param.
    fe.abs_now = now
    fe.video_used = False
    fe.video_ok = fe.overlay not in ("more", "classify", "rename")
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
    fe.last_ui = ui
    if fe.letter and now < fe.letter[1] and fe.letter[0]:
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_letter(top, fe.letter[0])
        back.blit(top, (0, 0))
    o = fe.overlay
    if not o and now < fe.ribbon_until and fe.cats:
        dim(back, 120)
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_ribbon(fe, top, t)
        back.blit(top, (0, 0))
    if o:
        if o in ("more", "classify", "rename"):
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
        elif o == "options":
            draw_options(fe, top, t)
        elif o == "hidden":
            draw_hidden(fe, top, t)
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
