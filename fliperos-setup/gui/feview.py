# O desenho do frontend do FliperOS (gui/fliperos-frontend): os tres modos
# (lista, tela cheia, grade) e o que fica por cima deles (o guia dos
# controles, o menu do jogo, a pagina "+", os filtros, as categorias, o menu
# do Tab, o Classify, o Rename e a pergunta de sair). draw(fe, agora) desenha
# em fe.back, a tela logica de 320x240.

import math
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
CACHE = 400               # imagens e caminhos guardados (os mais antigos saem)


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
        pw = SX + SW - (SX + LIST_W + 14)
        out += [(shot, pw - 4, LIST_SH - 4, "cover"), (logo, pw - 8, 28, "fit")]
    elif fe.mode == "full":
        right = SX + SW - THUMB[0] - 8
        out += [(shot, WW, HH, "cover"), (shot, THUMB[0] - 2, THUMB[1] - 2, "cover"),
                (logo, min(200, right - SX), 44, "fit")]
    else:
        out += [(cover, 48, 70, "fit"), (cover, 64, 92, "fit"), (logo, 110, 30, "fit")]
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


# ── Os icones do Arcadeflow ────────────────────────────────────────
# O genero, o controle e os botoes de cada jogo com os icones do Arcadeflow
# (~/.attract/layouts/Arcadeflow/metapics): o Setup o baixa para o
# Attract-Mode Plus, e eles nao podem vir na imagem (sem licenca). Sem o
# Arcadeflow, as linhas ficam so com o texto. O icone do genero tem o nome
# da categoria do MAME sem pontuacao ("Fighter / Versus" e fighterversus.png);
# sem ele, o do genero principal (fighter.png).

def af_path(fe, kind, name):
    import os
    base = os.path.join(fe.fd.web.attract_dir(), "layouts", "Arcadeflow", "metapics", kind, name + ".png")
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


def control_icon(fe, game, h, color):
    c = (game.get("Control") or "").lower()
    name = None
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


def icon_line(fe, ui, game, x, y, right, h=10):
    """Os icones lado a lado numa linha (a tela cheia e a grade)."""
    for img, text, color in icon_rows(fe, game, h):
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


def draw_list(fe, ui, now):
    frame(fe, ui)
    lx, lw, y0, rows = SX, LIST_W, 36, 13
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
                opened = game["Name"] in fe.opened
                W.block(ui, (lx, y + 1, 10, 10), T.BG_DEEP, None)
                pygame.draw.rect(ui, T.PINK if opened else T.COMMENT, (lx, y + 1, 10, 10), 1)
                ui.fill(T.PINK if opened else T.COMMENT, (lx + 2, y + 5, 6, 2))
                if not opened:
                    ui.fill(T.COMMENT, (lx + 4, y + 3, 2, 6))
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
        W.text(ui, fit(label, lx + lw - x - 12), color, x, y + 2)
    if len(fe.rows) > rows:
        W.scrollbar(ui, lx + lw + 4, y0, rows * 14 - 2, fe.top, rows, len(fe.rows))
    W.text(ui, "%d/%d" % (fe.cursor + 1, len(fe.rows)), T.LINE, lx + lw, y0 + rows * 14 + 1, right=True)
    # A direita: a imagem, o logo e as informacoes.
    game = fe.game()
    px = lx + lw + 14
    pw = SX + SW - px
    sh = LIST_SH
    W.block(ui, (px, y0, pw, sh), T.BG_DEEP, T.PURPLE)
    shot = picture(fe, game, pw - 4, sh - 4)
    if shot:
        blit_center(ui, shot, px + 2, y0 + 2, pw - 4, sh - 4)
    elif fe.scraping is game:
        # Sem nada ainda: o scrape sozinho esta buscando.
        W.glow(ui, (px + 2, y0 + 2, pw - 4, sh - 4), {"now": now})
        tiny.centered(ui, "LOOKING FOR ART...", T.CYAN, px + pw // 2, y0 + sh // 2 - 2)
    pygame.draw.rect(ui, T.PINK, (px, y0, pw, sh), 2)
    logo = image(fe, media(fe, game, "logo"), pw - 8, 28)
    y = y0 + sh + 6
    if logo:
        blit_center(ui, logo, px, y0 + sh - 14, pw, 28)
        y = y0 + sh + 18
    else:
        for line in W.wrap(fe.fd.short_title(game).upper(), pw)[:2]:
            W.text(ui, line, T.YELLOW, px, y)
            y += 10
        y += 2
    W.text(ui, fit(facts_line(game), pw), T.YELLOW, px, y)
    y += 12
    # Os icones, sem texto, em duas fileiras: o genero e os jogadores (o
    # boneco e o numero); o controle e os botoes. Sem o icone (Arcadeflow
    # nao baixado), o texto pequeno no lugar dele.
    rows = icon_rows(fe, game, 20, icons_only=True)
    genre = [r for r in rows if r[2] == T.CYAN]
    control = [r for r in rows if r[2] == T.PINK]
    buttons = [(buttons_icon(fe, game, 13, T.YELLOW), t, c) for _, t, c in rows if c == T.YELLOW]
    players = (game.get("Players") or "").strip()
    for line in (genre, control + buttons):
        x = px
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
        if line or (line is genre and players.isdigit()):
            y += 24
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


def full_shade(fe):
    """O escuro em cima e embaixo da imagem da tela cheia (feito uma vez)."""
    key = ("full_shade",)
    if key not in fe.media:
        shade = pygame.Surface((WW, HH), pygame.SRCALPHA)
        for y in range(HH):
            a = int(120 * (1 - y / 40)) if y < 40 else (int(165 * min(1, (y - 125) / 60)) if y > 125 else 0)
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


def draw_full(fe, ui, back, now):
    game = fe.game()
    snap = picture(fe, game, WW, HH)
    if snap:
        back.blit(snap, (0, 0))
        back.blit(full_shade(fe), (0, 0))
    cat = fe.category()
    W.text(ui, (cat or {}).get("name", "").upper()[:24], T.RED, SX, 12)
    W.text(ui, "%d/%d" % (fe.cursor + 1, len(fe.rows)), T.FG, SX + SW, 12, right=True)
    for i, c in enumerate(W.RAINBOW):
        pygame.draw.rect(ui, c, (SX, 24 + i, 40, 1))
    # A lista na direita: quatro miniaturas empilhadas, a do jogo escolhido
    # acesa, com uma seta em cima e embaixo enquanto ha mais jogos para
    # aquele lado. A coluna e a moldura rosa deslizam ate o lugar novo.
    (tw, th), gap, n = THUMB, 4, 4
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
            for j, line in enumerate(W.wrap(fe.fd.short_title(g).upper(), tw - 6)[:4]):
                tiny.text(ui, tiny.fit(line, tw - 6), T.FG if on else T.COMMENT, tx + 3, y + 5 + j * 8)
        pygame.draw.rect(ui, T.LINE, (tx, y, tw, th), 1)
        if g.get("Favourite") == "1":
            star(ui, tx + tw - 6, y + 6, T.YELLOW, 4)
    y = round(ty + (fsel - ftop) * step)
    pygame.draw.rect(ui, T.PINK, (tx, y, tw, th), 2)
    ui.set_clip(None)
    more = top + n < len(fe.rows)
    arrow(ui, tx + tw // 2, ty + n * step + 3, (0, 1), T.PINK if more else T.LINE, 5)
    # O jogo escolhido, embaixo a esquerda (fora da coluna).
    right = tx - 8
    logo = image(fe, media(fe, game, "logo"), min(200, right - SX), 44)
    if logo:
        ui.blit(logo, (SX, 178 - logo.get_height()))
    y = 184
    ui.blit(W.big(fit(fe.fd.short_title(game), right - SX), 1, W.LABEL), (SX, y))
    W.text(ui, fit(facts_line(game), right - SX), T.CYAN, SX, y + 12)
    icon_line(fe, ui, game, SX, y + 24, right, 12)


def draw_flow(fe, ui, now):
    frame(fe, ui)
    cols, tw, th, gap = 5, 50, 72, 8
    x0 = (WW - (cols * tw + (cols - 1) * gap)) // 2
    # A janela de duas fileiras acompanha o cursor.
    row, top_row = fe.cursor // cols, fe.top // cols
    if row < top_row:
        top_row = row
    elif row > top_row + 1:
        top_row = row - 1
    fe.top = top_row * cols
    first = fe.top
    sel = None
    for i in range(first, min(len(fe.rows), first + 2 * cols)):
        r, c = divmod(i - first, cols)
        x, y = x0 + c * (tw + gap), 36 + r * (th + 6)
        g = fe.rows[i][0]
        if i == fe.cursor:
            sel = (g, x, y)
            continue
        pygame.draw.rect(ui, T.BG_DEEP, (x, y, tw, th))
        img = image(fe, media(fe, g, "box") or media(fe, g, "snap"), tw - 2, th - 2)
        if img:
            blit_center(ui, img, x, y, tw, th)
        else:
            for k, line in enumerate(W.wrap(fe.fd.short_title(g).upper(), tw - 6)[:5]):
                tiny.text(ui, tiny.fit(line, tw - 6), T.COMMENT, x + 3, y + 6 + k * 8)
        dim = pygame.Surface((tw, th), pygame.SRCALPHA)
        dim.fill(T.SPACE + (90,))
        ui.blit(dim, (x, y))
        pygame.draw.rect(ui, T.LINE, (x, y, tw, th), 1)
        if g.get("Favourite") == "1":
            star(ui, x + tw - 6, y + 6, T.YELLOW, 4)
    if sel:
        g, x, y = sel
        bw, bh = 72, 100
        bx = max(SX, min(x + tw // 2 - bw // 2, SX + SW - bw))
        # Nao cobre a linha do filtro, debaixo do titulo.
        by = max(36, min(y + th // 2 - bh // 2, 188 - bh))
        tile_frame(ui, (bx, by, bw, bh), True, now)
        img = image(fe, media(fe, g, "box") or media(fe, g, "snap"), bw - 8, bh - 8)
        if img:
            blit_center(ui, img, bx, by, bw, bh)
        else:
            for k, line in enumerate(W.wrap(fe.fd.short_title(g).upper(), bw - 8)[:6]):
                W.text(ui, fit(line, bw - 8), T.FG, bx + 4, by + 8 + k * 11)
        pygame.draw.rect(ui, T.PINK, (bx, by, bw, bh), 2)
        # A aba na borda: mais um toque para aquele lado troca a romlist.
        col = fe.cursor % cols
        if len(fe.cats) > 1 and (col == cols - 1 or fe.cursor == len(fe.rows) - 1 or col == 0):
            side = 1 if (col == cols - 1 or fe.cursor == len(fe.rows) - 1) else -1
            nxt = fe.cats[(fe.cat + side) % len(fe.cats)]["name"].upper()
            edge_tab(ui, nxt, side)
    g = fe.game()
    y = 194
    logo = image(fe, media(fe, g, "logo"), 110, 30)
    tx = SX
    if logo:
        blit_center(ui, logo, SX, y, 110, 30)
        tx = SX + 118
    else:
        W.text(ui, fit(fe.fd.short_title(g), 150), T.YELLOW, SX, y + 2)
        tx = SX
    if logo:
        W.text(ui, fit(facts_line(g), SX + SW - tx), T.CYAN, tx, y + 2)
        icon_line(fe, ui, g, tx, y + 14, SX + SW, 12)
    else:
        W.text(ui, fit(facts_line(g), 150), T.CYAN, SX + 154, y + 2)
        icon_line(fe, ui, g, SX, y + 14, SX + SW, 12)


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


def draw_guide(fe, ui):
    pw, ph = SW, 162
    px, py = SX, (HH - ph) // 2 + 6
    card(ui, (px, py, pw, ph))
    title = "CONTROLS"
    ui.blit(W.big(title, 1, W.LABEL), (px + 10, py + 9))
    for i, c in enumerate(W.RAINBOW):
        pygame.draw.rect(ui, c, (px + 18 + W.width(title), py + 10 + i, pw - 28 - W.width(title), 1))
    jx, jy = px + 54, py + 70
    pygame.draw.circle(ui, T.SPACE, (jx, jy), 21)
    pygame.draw.circle(ui, T.LINE, (jx, jy), 21, 2)
    pygame.draw.circle(ui, T.RED, (jx, jy), 9)
    pygame.draw.circle(ui, (0xff, 0xa0, 0xa0), (jx - 3, jy - 3), 3)
    for d, color in (((0, -1), T.CYAN), ((0, 1), T.CYAN), ((-1, 0), T.PINK), ((1, 0), T.PINK)):
        arrow(ui, jx + d[0] * 30, jy + d[1] * 30, d, color, 5)
    tiny.centered(ui, "GAMES", T.CYAN, jx, jy - 44)
    tiny.text(ui, "ROMLIST", T.PINK, jx - 46, jy + 9)
    tiny.text(ui, "ROMLIST", T.PINK, jx + 19, jy + 9)
    tiny.centered(ui, "GAMES", T.CYAN, jx, jy + 40)
    tiny.centered(ui, "HOLD: FASTER", T.COMMENT, jx, jy + 49)
    tiny.centered(ui, "3 S: LETTER BY LETTER", T.COMMENT, jx, jy + 56)
    pygame.draw.line(ui, T.LINE, (px + 112, py + 28), (px + 112, py + ph - 26))
    bx0, by0 = px + 112 + (pw - 112 - 2 * 48) // 2, py + 52
    for i, (num, color, draw_icon, label) in enumerate(PANEL):
        col, row = i % 3, i // 3
        cx = bx0 + col * 48
        cy = by0 + row * 44 - (3 if col == 1 else 0)
        pygame.draw.circle(ui, T.SPACE, (cx + 2, cy + 2), 14)
        pygame.draw.circle(ui, color, (cx, cy), 14)
        pygame.draw.circle(ui, T.SPACE, (cx, cy), 14, 1)
        draw_icon(ui, cx, cy, T.SPACE)
        tiny.centered(ui, num + " " + label, T.FG, cx, cy + 19)
    # Debaixo dos botoes (a esquerda ficam as dicas do direcional).
    tiny.centered(ui, "START: VIEW MODE   TAB: GAME OPTIONS", T.COMMENT, px + 112 + (pw - 112) // 2, py + ph - 30)
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


def draw_more(fe, ui, now):
    g = fe.ov["game"]
    info = fe.ov.get("info") or {}
    W.frame(ui, {}, fit(fe.fd.short_title(g), 240) or "Game", [])
    y0 = 34
    bw, bh = 84, 122
    W.block(ui, (SX, y0, bw, bh), T.BG_DEEP, T.PURPLE)
    blit_center(ui, image(fe, media(fe, g, "box") or media(fe, g, "snap"), bw - 6, bh - 6), SX, y0, bw, bh)
    pygame.draw.rect(ui, T.PINK, (SX, y0, bw, bh), 2)
    x = SX + bw + 10
    y = y0 + 2
    rows = [("YEAR", " ".join(p for p in (info.get("year") or g.get("Year"),
                                          info.get("manufacturer") or g.get("Manufacturer")) if p)),
            ("GENRE", info.get("genre") or g.get("Category")), ("SERIES", info.get("serie") or g.get("Series")),
            ("PLAYERS", info.get("nplayers") or g.get("Players")),
            ("CONTROL", info.get("input_controls") or g.get("Control"))]
    for label, value in rows:
        if not value:
            continue
        W.text(ui, label, T.COMMENT, x, y)
        W.text(ui, fit(str(value), SX + SW - x - 62), T.FG, x + 62, y)
        y += 13
    if info.get("rate"):
        W.text(ui, "RATING", T.COMMENT, x, y + 2)
        stars(ui, x + 62, y + 1, float(info["rate"]), 5)
        y += 16
    keys = [p.split(":") for p in (info.get("buttons_colors") or "").split(";")]
    keys = [k for k in keys if len(k) >= 3 and k[0].startswith("P1_") and k[2]]
    for i, (_, color, label) in enumerate(keys[:6]):
        bx = x + (i % 2) * 104
        by = y + (i // 2) * 10
        try:
            c = pygame.Color(color.lower())
        except ValueError:
            c = pygame.Color(T.COMMENT)
        pygame.draw.circle(ui, c, (bx + 3, by + 3), 3)
        tiny.text(ui, tiny.fit(label, 92), T.FG, bx + 9, by + 1)
    ty = y0 + bh + 8
    th = 228 - ty
    W.block(ui, (SX, ty, SW, th), T.BG_DEEP, None)
    pygame.draw.rect(ui, T.LINE, (SX, ty, SW, th), 1)
    if fe.ov.get("loading"):
        W.glow(ui, (SX + 2, ty + 2, SW - 4, th - 4), {"now": now})
        W.centered(ui, "LOOKING IT UP...", T.CYAN, ty + th // 2 - 4)
        return
    text = (info.get("history") or "").replace("\r", "")
    text = re.sub(r"\n{2,}", "\n", text).strip()
    if not text:
        text = "No information yet. Tab > Scrape this game brings it." if not g["_system"]["arcade"] else \
            "Not in the Arcade Database."
    lines = []
    for para in text.split("\n"):
        lines.extend(W.wrap(para, SW - 20) if para.strip() else [""])
    shown = (th - 8) // 11 - 1
    top = min(fe.ov.get("scroll", 0), max(0, len(lines) - shown))
    fe.ov["scroll"] = top
    for i, line in enumerate(lines[top:top + shown]):
        W.text(ui, line, T.FG, SX + 6, ty + 5 + i * 11)
    if len(lines) > shown:
        W.scrollbar(ui, SX + SW - 7, ty + 4, th - 8, top, shown, len(lines))
    source = "ARCADE DATABASE - SAVED" if info else ""
    if info.get("history_copyright_short"):
        source = info["history_copyright_short"].upper()
    tiny.text(ui, tiny.fit(source, SW - 20), T.COMMENT, SX + SW - 12, ty + th - 9, right=True)


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
    tiny.centered(ui, "ROMLIST", T.COMMENT, WW // 2, band_y + 7)
    n = len(fe.cats)
    for off, size in ((-2, 32), (2, 32), (-1, 40), (1, 40), (0, 56)):
        if n < 2 and off:
            continue
        c = fe.cats[(fe.cat + off) % n]
        cx = WW // 2 + off * 66
        x, y = cx - size // 2, band_y + 20 + (56 - size) // 2
        tile_frame(ui, (x, y, size, size), off == 0, now)
        pygame.draw.rect(ui, T.PINK if off == 0 else T.LINE, (x, y, size, size), 2 if off == 0 else 1)
        name = system_icon(c)
        icon = T.icon(name, 2 if size >= 44 else 1) if name else None
        if icon is None:
            icon = W.big(c["name"][:1].upper(), 3 if size >= 44 else 2, W.MARQUEE)
        if off:
            icon = icon.copy()
            icon.set_alpha(110)
        blit_center(ui, icon, x, y, size, size)
    c = fe.cats[fe.cat % n]
    label = fit(c["name"], WW - 20)
    ui.blit(W.big(label, 1, W.LABEL), ((WW - W.width(label)) // 2, band_y + 80))
    count = len(fe.rows)
    tiny.centered(ui, "%d GAMES" % count, T.CYAN, WW // 2, band_y + 93)


def system_icon(cat):
    """O icone do programa da pasta (os de gui/icons)."""
    if cat.get("key") == "@arcade":
        return "attractplus"
    exe = (cat.get("exe", "") + " " + cat.get("args", "")).lower()
    for name in ("groovymame", "flycast", "pcsx2", "dolphin", "model2", "openbor", "retroarch", "fightcade"):
        if name in exe:
            return name
    if "sm2" in exe:
        return "model2"
    if "duckstation" in exe:
        return "pcsx2"
    return None


def draw_options(fe, ui, now):
    """O menu do Tab: as opcoes do jogo e, abaixo de uma linha, as do
    frontend (o modo de exibicao)."""
    g = fe.game()
    pw, ph = 236, 196
    px, py = (WW - pw) // 2, 30
    card(ui, (px, py, pw, ph))
    ui.blit(W.big("GAME OPTIONS", 1, W.LABEL), (px + 10, py + 8))
    if g:
        tiny.text(ui, tiny.fit(g.get("Title") or g["Name"], pw - 20), T.COMMENT, px + 10, py + 20)
    items = [("CLASSIFY", "GENRE, PLAYERS, BUTTONS, CONTROL, YEAR", T.YELLOW),
             ("RENAME", "THE NAME SHOWN IN THE LISTS", T.CYAN),
             ("SCRAPE THIS GAME", "PICTURES AND TEXT, NOW", T.GREEN)]
    for i, (label, about, color) in enumerate(items):
        y = py + 30 + i * 30
        on = i == fe.ov["sel"]
        tile_frame(ui, (px + 8, y, pw - 16, 26), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (px + 8, y, pw - 16, 26), 2 if on else 1)
        ix, iy = px + 22, y + 13
        if i == 0:
            pygame.draw.polygon(ui, color, [(ix - 7, iy - 5), (ix + 3, iy - 5), (ix + 8, iy), (ix + 3, iy + 5),
                                            (ix - 7, iy + 5)])
            pygame.draw.circle(ui, T.BG_DEEP, (ix - 3, iy), 2)
        elif i == 1:
            pygame.draw.polygon(ui, color, [(ix - 6, iy + 6), (ix - 6, iy + 2), (ix + 4, iy - 8), (ix + 8, iy - 4),
                                            (ix - 2, iy + 6)])
        else:
            ui.fill(color, (ix - 1, iy - 8, 3, 9))
            pygame.draw.polygon(ui, color, [(ix - 6, iy - 1), (ix + 6, iy - 1), (ix, iy + 5)])
            ui.fill(color, (ix - 7, iy + 6, 15, 2))
        W.text(ui, label, T.FG if on else T.COMMENT, px + 36, y + 5)
        tiny.text(ui, about, color if on else T.LINE, px + 36, y + 17)
    # A linha e as opcoes do frontend.
    y = py + 122
    pygame.draw.line(ui, T.LINE, (px + 8, y), (px + pw - 9, y))
    for i, c in enumerate(W.RAINBOW):
        pygame.draw.rect(ui, c, (px + 8, y + 1 + i, 24, 1))
    ui.blit(W.big("FRONTEND OPTIONS", 1, W.LABEL), (px + 10, y + 10))
    y += 26
    on = fe.ov["sel"] == 3
    tile_frame(ui, (px + 8, y, pw - 16, 40), on, now)
    pygame.draw.rect(ui, T.PINK if on else T.LINE, (px + 8, y, pw - 16, 40), 2 if on else 1)
    W.text(ui, "VIEW MODE", T.FG if on else T.COMMENT, px + 16, y + 6)
    # Os tres modos lado a lado; o de agora aceso.
    x = px + 16
    for mode, label in (("list", "LIST"), ("full", "FULL SCREEN"), ("flow", "GRID")):
        cur = fe.mode == mode
        w = tiny.width(label) + 10
        if cur:
            W.block(ui, (x, y + 20, w, 12), T.PINK if on else T.PURPLE, None)
        else:
            pygame.draw.rect(ui, T.LINE, (x, y + 20, w, 12), 1)
        tiny.text(ui, label, T.SPACE if cur else T.COMMENT, x + 5, y + 23)
        x += w + 6
    if on:
        tiny.text(ui, "< >", T.PINK, px + pw - 16, y + 8, right=True)


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
    kw, kh = 28, 22
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
    for i, (label, wd, xo) in enumerate((("SPACE", 92, 0), ("DELETE", 72, 98), ("SAVE", 72, 176))):
        x = kx0 + xo
        on = (r0, c0) == (4, i)
        tile_frame(ui, (x, y, wd, kh), on, now)
        pygame.draw.rect(ui, T.PINK if on else (T.GREEN if label == "SAVE" else T.LINE), (x, y, wd, kh),
                         2 if on else 1)
        W.text(ui, label, T.FG if on else (T.GREEN if label == "SAVE" else T.COMMENT),
               x + (wd - W.width(label)) // 2, y + 7)


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
    # O video so na lista e na tela cheia, e nao com uma tela inteira por
    # cima (a pagina "+", o Classify, o Rename).
    fe.abs_now = now
    fe.video_used = False
    fe.video_ok = fe.mode in ("list", "full") and fe.overlay not in ("more", "classify", "rename")
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
    back.blit(ui, (0, 0))
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
        elif o == "classify":
            draw_classify(fe, top, t)
        elif o == "rename":
            draw_rename(fe, top, t)
        elif o == "exit":
            draw_exit(fe, top, t)
        back.blit(top, (0, 0))
    if fe.toast and now < fe.toast[1]:
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        draw_toast(top, fe.toast[0])
        back.blit(top, (0, 0))
