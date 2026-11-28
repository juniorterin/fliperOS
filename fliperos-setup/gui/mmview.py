# O desenho do Matchmaker (gui/fliperos-matchmaker), no visual do modo lista
# do frontend: a faixa do titulo, a lista com os grupos de abrir e fechar como
# os clones, a barra rosa entre a lista e o painel, a imagem do jogo e as
# linhas de icones. A faixa GAME LIST da troca de pagina, a porta dupla, a
# arte dos jogos e o fundo sao os do frontend (feview, widgets): o Matchmaker
# passa a si mesmo como o "fe" deles (os campos que eles leem estao no
# fliperos-matchmaker). draw(mm, agora) desenha em mm.back, a tela de 320x240.

import os

import pygame

import fedata
import feview
import theme as T
import widgets as W

WW, HH = T.WIDTH, T.HEIGHT
ICONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "matchmaker")
IND = 14            # o recuo de um nivel da arvore (o dos clones e 26: aqui cabe mais)
PITCH = 14          # a altura de uma linha da lista (a do frontend)
_icons = {}


def icon(name):
    """Um icone de 16 bits do Matchmaker (tools/matchmaker/assets.py), ou None."""
    if name not in _icons:
        try:
            img = pygame.image.load(os.path.join(ICONS_DIR, name + ".png"))
            _icons[name] = img.convert_alpha() if pygame.display.get_surface() else img
        except (pygame.error, OSError):
            _icons[name] = None
    return _icons[name]


def blit(ui, img, x, y):
    if img is not None:
        ui.blit(img, (x, y))


def blit_w(ui, img, x, y):
    """Desenha e devolve a largura (14 sem o icone: o lugar dele fica)."""
    if img is None:
        return 14
    ui.blit(img, (x, y))
    return img.get_width()


def mid(ui, img, x, text_y):
    """O icone no meio da linha de texto de 8 px que comeca em text_y; devolve a largura."""
    if img is None:
        return 0
    ui.blit(img, (x, text_y + (8 - img.get_height()) // 2))
    return img.get_width()


def fade(color, bg, k):
    """color misturada ao fundo: k da cor (a #tag meio transparente)."""
    return tuple(round(c * k + b * (1 - k)) for c, b in zip(color[:3], bg[:3]))


def ping_icon(ms):
    if ms is None:
        return None
    return icon("ping_%d" % (4 if ms <= 40 else 3 if ms <= 80 else 2 if ms <= 130 else 1))


def ping_color(ms):
    return T.GREEN if ms <= 40 else T.YELLOW if ms <= 80 else T.ORANGE if ms <= 130 else T.RED


def person(ui, x, y, color):
    """O boneco de 8 px do numero de jogadores."""
    pygame.draw.rect(ui, color, (x + 2, y, 4, 3))
    pygame.draw.rect(ui, color, (x, y + 4, 8, 4))


def tag_text(p, w, prefix=""):
    """NICK#tag cortado em w pixels: o apelido em maiusculas e a tag em
    minusculas (o feview.fit poe tudo em maiusculas)."""
    s = prefix + "%s#%s" % (p.get("nick", "?").upper(), p.get("tag", ""))
    while s and W.width(s) > w:
        s = s[:-1]
    return s


def title_of(game):
    return fedata.short_title(game) if game and game.get("Name") else "?"


# ── A lista ───────────────────────────────────────────────────────

def geom():
    """(x, largura, y, linhas) da lista e (x, y, largura, altura) da imagem: as do frontend."""
    (lx, lw, y0, nrows), box = feview.list_geom()
    return lx, lw, y0, nrows, box


def select(ui, x, y, now):
    """A moldura rosa da linha escolhida, de x ate a ponta da lista (o icone dentro)."""
    lx, lw = geom()[:2]
    rect = (x - 4, y, lx + lw - x + 4, 12)
    feview.tile_frame(ui, rect, True, now)
    pygame.draw.rect(ui, T.PINK, rect, 1)


def rails(ui, y, level, last, outer=False):
    """Os trilhos da arvore: o de fora (nivel 2, se o grupo de cima continua)
    e o L do nivel da linha, descendo do meio do [+] de cima."""
    lx = geom()[0]
    if level == 2 and outer:
        pygame.draw.line(ui, T.LINE, (lx + 5, y - 3), (lx + 5, y + 14))
    base = lx + IND * (level - 1)
    pygame.draw.line(ui, T.LINE, (base + 5, y - 3), (base + 5, y + (5 if last else 14)))
    pygame.draw.line(ui, T.LINE, (base + 5, y + 5), (base + 11, y + 5))


def group_row(ui, y, row, on, now):
    """ONLINE NOW, LOOKING, PLAYING...: o [+] e, na ponta, quantos."""
    lx, lw = geom()[:2]
    if on:
        select(ui, lx, y, now)
    feview.expand_mark(ui, lx, y + 1, row["open"])
    color = T.FG if row["open"] or on else T.COMMENT
    W.text(ui, row["name"], color, lx + 14, y + 2)
    W.text(ui, str(row["count"]), color, lx + lw - 6, y + 2, right=True)


def game_row(ui, y, row, on, now):
    """Um jogo: o globo (aceso com gente online) e o titulo; na ponta, as
    luvas (alguem procura duelo), o boneco e quantos jogam. Dentro do ONLINE
    NOW, com o trilho; o jogo que o gabinete nao tem, apagado, com a seta de baixar."""
    lx, lw = geom()[:2]
    nested = row["kind"] == "online"
    if nested:
        rails(ui, y, 1, row.get("last", False))
    x = lx + (IND if nested else 0)
    if on:
        select(ui, x, y, now)
    live = row["players"] > 0
    blit(ui, icon("online_10" if live else "online_dim_10"), x, y + 1)
    x += 14
    right = lx + lw - 6
    tail = []
    if not row["have"]:
        tail.append(("icon", icon("rom_10")))
    elif live:
        if row["looking"]:
            tail.append(("icon", icon("gloves_10")))
        tail.append(("person", None))
        tail.append(("text", str(row["players"])))
    width = 0
    for kind, v in tail:
        width += 8 * len(v) if kind == "text" else 8 if kind == "person" else (v.get_width() if v else 0)
    width += 2 * max(0, len(tail) - 1)
    room = right - x - (width + 4 if tail else 0)
    if on:
        color = T.FG
    elif not row["have"]:
        color = T.COMMENT
    elif nested or live:
        color = T.YELLOW
    else:
        color = (0x7A, 0x88, 0xC8)
    W.text(ui, feview.fit(title_of(row["game"]), room), color, x, y + 2)
    tx = right - width
    for kind, v in tail:
        if kind == "icon":
            tx += mid(ui, v, tx, y + 2) + 2
        elif kind == "person":
            person(ui, tx, y + 2, T.CYAN)
            tx += 10
        else:
            W.text(ui, v, T.CYAN, tx, y + 2)
            tx += 8 * len(v) + 2


def player_row(ui, y, row, on, now, me_id=None):
    """Um jogador: Wi-Fi ou cabo, NICK e a #tag meio apagada; na ponta, as
    barras do ping (ou quanto da ROM ja baixou)."""
    lx, lw = geom()[:2]
    level = row.get("level", 1)
    rails(ui, y, level, row.get("last", False), row.get("outer", False))
    x = lx + IND * level
    if on:
        select(ui, x, y, now)
    p = row["player"]
    mid(ui, icon("wifi_10" if p.get("conn") == "wifi" else "cable_10"), x, y + 2)
    x += 12
    you = me_id is not None and p.get("id") == me_id
    downloading = p.get("state") == "download"
    color = T.FG if on else T.PINK if you else T.ORANGE if downloading else T.CYAN
    nick = p.get("nick", "?")
    W.text(ui, nick, color, x, y + 2)
    bg = (0x2C, 0x2C, 0x3C) if on else T.SPACE
    W.text(ui, "#" + p.get("tag", ""), fade(color, bg, 0.5), x + W.width(nick), y + 2)
    right = lx + lw - 6
    if downloading and p.get("pct") is not None:
        W.text(ui, "%d%%" % p["pct"], T.ORANGE, right, y + 2, right=True)
    else:
        img = ping_icon(p.get("rtt"))
        if img is not None:
            mid(ui, img, right - img.get_width(), y + 2)


def sub_row(ui, y, row, on, now):
    """Quem joga junto: "KIWI VS LYNX 2-1" ou "PARTY OTTER 2/2", com o [+]."""
    lx, lw = geom()[:2]
    rails(ui, y, 1, row.get("last", False))
    x = lx + IND
    if on:
        select(ui, x, y, now)
    feview.expand_mark(ui, x, y + 1, row["open"])
    right = lx + lw - 6
    W.text(ui, feview.fit(row["text"], right - (x + 14) - 8 * len(row["right"]) - 6),
           T.FG if row["open"] or on else T.COMMENT, x + 14, y + 2)
    if row["right"]:
        W.text(ui, row["right"], T.YELLOW if "-" in row["right"] else T.GREEN, right, y + 2, right=True)


def draw_rows(mm, ui, rows, cursor, now, kinds, top=0):
    """As linhas, cada uma numa parte da porta dupla (top: as primeiras
    linhas da tela que nao sao da lista, como o titulo do jogo no lobby);
    a barra rosa e o contador n/N embaixo, como no frontend."""
    lx, lw, y0, nrows, _ = geom()
    shown = nrows - top
    first = max(0, min(cursor - shown // 2, len(rows) - shown))
    for i in range(first, min(len(rows), first + shown)):
        y = y0 + (top + i - first) * PITCH
        with feview.part(mm, ui, "row", top + i - first) as s:
            kinds(s, y, rows[i], i == cursor)
    with feview.part(mm, ui, "chrome") as s:
        W.scrollbar(s, lx + lw + 4, y0, nrows * PITCH - 2, first, shown, max(shown, len(rows)))
        count = "%d/%d" % (cursor + 1, len(rows)) if rows else "0/0"
        W.text(s, count, T.LINE, lx + lw, y0 + nrows * PITCH + 1, right=True)


# ── O painel ──────────────────────────────────────────────────────

def art_box(mm, ui, game):
    """A imagem do jogo na moldura rosa com a sombra roxa (a do frontend) e o
    logo por cima da borda de baixo; devolve (x, y onde o texto comeca, largura)."""
    _, (px, py, pw, ph) = feview.list_geom()
    real = game is not None and not game.get("_missing") and game.get("_system")
    with feview.part(mm, ui, "picture") as s:
        W.block(s, (px, py, pw, ph), T.BG_DEEP, T.PURPLE)
        shot = None
        if real:
            try:
                shot = feview.picture(mm, game, pw - 4, ph - 4)
            except Exception:       # uma imagem estragada nao derruba a tela
                shot = None
        if shot is not None:
            feview.blit_center(s, shot, px + 2, py + 2, pw - 4, ph - 4)
        elif game is not None and game.get("_missing"):
            rom = icon("rom_16")
            if rom is not None:
                s.blit(rom, (px + (pw - rom.get_width()) // 2, py + (ph - rom.get_height()) // 2))
        pygame.draw.rect(s, T.PINK, (px, py, pw, ph), 2)
    logo = None
    if real:
        try:
            logo = feview.image(mm, feview.media(mm, game, "logo"), min(pw - 8, 200), 28)
        except Exception:
            logo = None
    if logo is not None:
        with feview.part(mm, ui, "logo") as s:
            feview.blit_center(s, logo, px, py + ph - 14, pw, 28)
    return px, py + ph + (18 if logo is not None else 6), pw


def panel_game(mm, ui, row):
    """O jogo da linha: a imagem, o ano e a fabricante, os icones dele e
    quantos estao online (o globo) e procuram duelo (as luvas)."""
    g = row["game"]
    px, y, pw = art_box(mm, ui, g)
    if T.VERTICAL:
        return              # em pe, so a imagem cabe em cima da lista
    with feview.part(mm, ui, "text") as s:
        if g.get("_missing"):
            W.text(s, feview.fit(title_of(g), pw), T.YELLOW, px, y)
            W.text(s, "NOT ON THIS", T.ORANGE, px, y + 14)
            W.text(s, "CABINET", T.ORANGE, px, y + 24)
            y += 36
        else:
            facts = feview.facts_line(g)
            if facts:
                W.text(s, feview.fit(facts, pw), T.YELLOW, px, y)
                y += 12
    with feview.part(mm, ui, "icons") as s:
        if not g.get("_missing"):
            try:
                strip = feview.icon_strip(mm, s, g, px, y, T.SAFE_X + T.SAFE_W)
            except Exception:
                strip = 0
            y += strip + 6 if strip else 0
        y = max(y, HH - 52)
        if row["players"]:
            x = px + blit_w(s, icon("online_14"), px, y) + 4
            W.text(s, str(row["players"]), T.CYAN, x, y + 3)
            x += 8 * len(str(row["players"])) + 10
            if row["looking"]:
                gl = icon("gloves_14")
                if gl is not None:
                    s.blit(gl, (x, y + (14 - gl.get_height()) // 2))
                    x += gl.get_width() + 4
                W.text(s, str(row["looking"]), T.PINK, x, y + 3)
        else:
            blit(s, icon("online_dim_14"), px, y)
            W.text(s, "NOBODY", T.COMMENT, px + 18, y + 3)


STATE_TEXT = {"looking": ("LOOKING", T.PINK), "playing": ("PLAYING", T.YELLOW), "party": ("IN A PARTY", T.GREEN),
              "download": ("GETTING THE ROM", T.ORANGE), "idle": ("IDLE", T.COMMENT)}


def panel_player(mm, ui, p, game, players):
    """O jogador da linha: NICK#tag, a conexao e o ping, e o que ele faz
    (contra quem joga, a party, quanto da ROM ja baixou)."""
    px, y, pw = art_box(mm, ui, game)
    if T.VERTICAL:
        return
    with feview.part(mm, ui, "text") as s:
        W.text(s, tag_text(p, pw + 8), T.YELLOW, px, y)
    with feview.part(mm, ui, "icons") as s:
        y += 16
        x = px + mid(s, icon("wifi_10" if p.get("conn") == "wifi" else "cable_10"), px, y) + 4
        rtt = p.get("rtt")
        if rtt is not None:
            x += mid(s, ping_icon(rtt), x, y) + 4
            W.text(s, "%dMS" % rtt, ping_color(rtt), x, y)
        y += 16
        st = p.get("state") or "idle"
        text, color = STATE_TEXT.get(st, STATE_TEXT["idle"])
        group = p.get("group")
        mates = [q for q in players if group and q.get("group") == group and q.get("id") != p.get("id")]
        if st == "playing" and mates:
            text = tag_text(mates[0], pw + 8, "VS ")
        elif st in ("party", "download") and group:
            text = "PARTY OF %d" % (len(mates) + 1)
        W.text(s, text if st == "playing" and mates else feview.fit(text, pw + 8), color, px, y)
        if st == "download" and p.get("pct") is not None:
            W.text(s, "ROM %d%%" % p["pct"], T.ORANGE, px, y + 14)


# ── As telas ──────────────────────────────────────────────────────

def draw_title(mm, ui, name):
    """A faixa do titulo (W.frame) com o logotipo escrito, se o nome tiver um."""
    with feview.part(mm, ui, "title") as s:
        W.frame(s, {}, name, [])
        feview.title_logo(s, name)


def centered(ui, s, color, y):
    W.text(ui, s, color, (WW - W.width(s)) // 2, y)


def draw_checking(mm, ui, now):
    """Ao abrir: a internet e o servidor sendo conferidos."""
    draw_title(mm, ui, "MATCHMAKER")
    globe = icon("online_32")
    if globe is not None:
        ui.blit(globe, ((WW - globe.get_width()) // 2, HH // 2 - 40))
    dots = int(now * 3) % 4
    centered(ui, "CONNECTING" + "." * dots + " " * (3 - dots), T.CYAN, HH // 2 + 4)


OFFLINE_TEXT = {
    "internet": ("NO INTERNET", ["THE MATCHMAKER ONLY", "WORKS ONLINE."], ["CHECK THE CABLE", "OR THE WI-FI."]),
    "server": ("SERVER OFFLINE", ["THE INTERNET IS FINE,", "BUT THE MATCHMAKER", "SERVER DOES NOT ANSWER."],
               ["TRY AGAIN IN A WHILE."]),
    "refused": ("NOT ALLOWED", ["THE SERVER DID NOT", "LET THIS CABINET IN."], ["CHANGE THE CABINET", "NAME IN SETUP."]),
}
OFFLINE_CHOICES = ("retry_32", "back_32")
OFFLINE_LABELS = ("TRY AGAIN", "BACK")


def draw_offline(mm, ui, now):
    """Sem internet, sem o servidor ou recusado: o aviso e as duas saidas,
    TRY AGAIN e BACK (as telas 14 e 14b do plano)."""
    draw_title(mm, ui, "MATCHMAKER")
    dark = pygame.Surface((WW, HH), pygame.SRCALPHA)
    dark.fill(tuple(T.SPACE[:3]) + (150,))
    ui.blit(dark, (0, 0))
    title, lines, hint = OFFLINE_TEXT.get(mm.offline, OFFLINE_TEXT["server"])
    w = min(240, WW - 16)
    x0, y0, h = (WW - w) // 2, 24, 190
    W.block(ui, (x0, y0, w, h), T.BG_DEEP, T.PURPLE)
    pygame.draw.rect(ui, T.PINK, (x0, y0, w, h), 1)
    globe, cross = icon("online_dim_32"), icon("pass_14")
    gy = y0 + 12
    if globe is not None:
        gx = (WW - globe.get_width()) // 2
        ui.blit(globe, (gx, gy))
        if cross is not None:
            ui.blit(cross, (gx + globe.get_width() - cross.get_width() + 1,
                            gy + globe.get_height() - cross.get_height() + 1))
    big = W.big(title, 2, [T.ORANGE, T.ORANGE, T.YELLOW])
    shadow = W.big(title, 2, [T.PURPLE])
    bx = (WW - big.get_width()) // 2
    ui.blit(shadow, (bx + 1, y0 + 41))
    ui.blit(big, (bx, y0 + 40))
    y = y0 + 64
    for ln in lines:
        centered(ui, ln, T.ORANGE, y)
        y += 12
    y += 4
    for ln in hint:
        centered(ui, ln, T.COMMENT, y)
        y += 12
    size, gap = 44, 10
    tx, ty = (WW - (2 * size + gap)) // 2, y0 + h - size - 22
    for i, name in enumerate(OFFLINE_CHOICES):
        x = tx + i * (size + gap)
        on = mm.offline_choice == i
        feview.tile_frame(ui, (x, ty, size, size), on, now)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (x, ty, size, size), 1)
        img = icon(name)
        if img is not None:
            ui.blit(img, (x + (size - img.get_width()) // 2, ty + (size - img.get_height()) // 2))
    centered(ui, OFFLINE_LABELS[mm.offline_choice], T.YELLOW, ty + size + 6)


def status_line(mm, ui):
    """Caiu a conexao com o servidor no meio: o aviso embaixo do painel (o
    feonline tenta de novo sozinho)."""
    if mm.status() != "online":
        _, (px, _, pw, _) = feview.list_geom()
        with feview.part(mm, ui, "text", 2) as s:
            W.text(s, feview.fit("RECONNECTING", pw), T.ORANGE, px, HH - 19)


def draw_home(mm, ui, now):
    page = mm.page()
    draw_title(mm, ui, page["name"] if page else "MATCHMAKER")
    rows = mm.rows
    if not rows:
        centered(ui, "NO ONLINE EMULATORS" if page is None else "NO GAMES", T.COMMENT, HH // 2)
        status_line(mm, ui)
        return

    def kinds(s, y, row, on):
        if row["kind"] == "group":
            group_row(s, y, row, on, now)
        else:
            game_row(s, y, row, on, now)
    draw_rows(mm, ui, rows, mm.cursor, now, kinds)
    row = rows[mm.cursor] if 0 <= mm.cursor < len(rows) else None
    if row is not None and row["kind"] != "group":
        panel_game(mm, ui, row)
    else:
        art_box(mm, ui, None)
    status_line(mm, ui)


def draw_lobby(mm, ui, now):
    """O lobby de um jogo: o titulo dele com quantos estao la, e os grupos
    LOOKING, PLAYING, IN PARTY e IDLE."""
    page = mm.page()
    draw_title(mm, ui, page["name"] if page else "MATCHMAKER")
    lx, lw, y0, _, _ = geom()
    players = mm.room()
    with feview.part(mm, ui, "row", 0) as s:
        x = lx - 2 + blit_w(s, icon("online_10" if players else "online_dim_10"), lx - 2, y0 + 1) + 4
        count = str(len(players))
        W.text(s, feview.fit(title_of(mm.lobby_game), lx + lw - 6 - x - 8 * len(count) - 6), T.YELLOW, x, y0 + 2)
        W.text(s, count, T.CYAN, lx + lw - 6, y0 + 2, right=True)
    rows = mm.rows
    me = mm.me_id()

    def kinds(s, y, row, on):
        if row["kind"] == "group":
            group_row(s, y, row, on, now)
        elif row["kind"] == "sub":
            sub_row(s, y, row, on, now)
        else:
            player_row(s, y, row, on, now, me)
    draw_rows(mm, ui, rows, mm.cursor, now, kinds, top=1)
    row = rows[mm.cursor] if 0 <= mm.cursor < len(rows) else None
    if row is not None and row["kind"] == "player":
        panel_player(mm, ui, row["player"], mm.lobby_game, players)
    else:
        art_box(mm, ui, mm.lobby_game)
    status_line(mm, ui)


SCREENS = {"checking": draw_checking, "offline": draw_offline, "home": draw_home, "lobby": draw_lobby}


def draw(mm, now):
    """Um quadro em mm.back, na ordem do feview.draw: o fundo, a tela de
    antes saindo (a porta dupla), a tela nova entrando e, por cima, a faixa
    GAME LIST enquanto a pagina e escolhida."""
    back = mm.back
    t = now - mm.start
    mm.bg.draw(back, t)
    mm.abs_now = now
    ui = pygame.Surface((WW, HH), pygame.SRCALPHA)
    intro = mm.intro
    waiting = None
    if intro is not None:
        intro.setdefault("style", "doors")
        if now < intro["start"]:
            waiting = intro.get("old")
        elif now - intro["start"] >= feview.INTRO:
            mm.intro = None
        else:
            feview.leave(back, mm)
    SCREENS[mm.screen](mm, ui, t)
    if waiting is not None and not mm.shot:
        back.blit(waiting, (0, 0))
    else:
        back.blit(ui, (0, 0))
    mm.last_screen = back.copy()
    if now < mm.ribbon_until and mm.cats:
        k = min(1.0, (mm.ribbon_until - now) / feview.RIBBON_FADE)
        feview.dim(back, round(120 * k))
        top = pygame.Surface((WW, HH), pygame.SRCALPHA)
        feview.draw_ribbon(mm, top, t)
        if k < 1:
            top.set_alpha(round(255 * k))
        back.blit(top, (0, 0))
