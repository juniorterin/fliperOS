# As telas da interface grafica: uma classe para cada primitiva de
# fliperos-setup/lib/ui.sh (ui_menu, ui_radio, ui_checklist, ui_yesno,
# ui_msg, ui_input e a tela de progresso).
#
# Cada tela tem draw(surf, ctx), que desenha na tela logica de 320x240, e
# key(nome), que devolve None, ("back", None) ou ("select", valor).
#
# O visual e o de um fliperama: o titulo da tela num letreiro em degrade com
# as faixas do gabinete, a linha de placar (NET e DISK), o fundo de estrelas
# e, nos menus com icones, um carrossel. Tudo na Press Start 2P.

import random

import pygame

import theme as T

ROW = 14
CONTENT_Y = 40
HINT_Y = 180
FOOTER_Y = 220
RAINBOW = [T.RED, T.ORANGE, T.YELLOW, T.GREEN, T.CYAN, T.PURPLE]
MARQUEE = [T.YELLOW, T.ORANGE, T.PINK, T.PINK, T.PURPLE, T.CYAN, T.CYAN, T.CYAN]
MARQUEE_ERROR = [T.FG, T.ORANGE, T.RED, T.RED]
LABEL = [T.FG, T.YELLOW, T.YELLOW, T.ORANGE]


def text(surf, s, color, x, y, right=False):
    img = T.font().render(s, False, color)
    if right:
        x -= img.get_width()
    surf.blit(img, (x, y))
    return img.get_width()


def width(s):
    return T.font().size(s)[0]


def centered(surf, s, color, y):
    text(surf, s, color, (T.WIDTH - width(s)) // 2, y)


def wrap(s, w):
    """Quebra o texto em linhas de ate w pixels, sem cortar palavras."""
    lines, line = [], ""
    for word in s.split():
        trial = word if not line else line + " " + word
        if line and width(trial) > w:
            lines.append(line)
            line = word
        else:
            line = trial
    if line or not lines:
        lines.append(line)
    return lines


def big(s, scale, colors):
    """O texto ampliado, com uma cor por linha de pixels (colors e uma cor
    ou uma lista, de cima para baixo)."""
    mask = pygame.mask.from_surface(T.font().render(s, False, (255, 255, 255)))
    img = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    if isinstance(colors, tuple):
        colors = [colors]
    h = img.get_height()
    for y in range(h):
        color = colors[min(len(colors) - 1, y * len(colors) // h)]
        img.fill(color, (0, y, img.get_width(), 1), pygame.BLEND_RGBA_MULT)
    return pygame.transform.scale(img, (img.get_width() * scale, h * scale))


def block(surf, rect, color, shadow=T.LINE):
    """O bloco solido com a sombra dura, deslocada 2 pixels."""
    x, y, w, h = rect
    if shadow:
        pygame.draw.rect(surf, shadow, (x + 2, y + 2, w, h))
    pygame.draw.rect(surf, color, rect)


def button(surf, label, cx, y, selected, w=80):
    x = cx - w // 2
    if selected:
        block(surf, (x, y, w, 20), T.PINK, T.PURPLE)
        color = T.SPACE
    else:
        block(surf, (x, y, w, 20), T.BG_DEEP, None)
        pygame.draw.rect(surf, T.LINE, (x, y, w, 20), 1)
        color = T.FG
    text(surf, label, color, cx - width(label) // 2, y + 6)


_stars = None


def stars():
    global _stars
    if _stars is None:
        _stars = pygame.Surface((T.WIDTH, T.HEIGHT))
        _stars.fill(T.SPACE)
        rnd = random.Random(7)
        for _ in range(70):
            _stars.set_at((rnd.randrange(T.WIDTH), rnd.randrange(T.HEIGHT)),
                          rnd.choice([T.COMMENT, T.COMMENT, T.PURPLE, T.FG]))
    return _stars


def frame(surf, ctx, title, keys, error=False, score=False):
    """O fundo, o letreiro com o titulo, a linha de placar e a legenda das
    teclas. O placar (score) so aparece nos menus principais."""
    surf.blit(stars(), (0, 0))
    title = title.upper()
    scale = 2 if width(title) * 2 <= 240 else 1
    logo = big(title, scale, MARQUEE_ERROR if error else MARQUEE)
    lx = (T.WIDTH - logo.get_width()) // 2
    ly = 10 + (16 - logo.get_height()) // 2
    surf.blit(big(title, scale, (0x40, 0x20, 0x70)), (lx + scale, ly + scale))
    surf.blit(logo, (lx, ly))
    # As faixas do gabinete, dos dois lados do titulo.
    bar = lx - T.SAFE_X - 8
    if bar >= 8:
        for i, color in enumerate(RAINBOW):
            pygame.draw.rect(surf, color, (T.SAFE_X, 12 + i * 2, bar, 2))
            pygame.draw.rect(surf, color, (T.WIDTH - T.SAFE_X - bar, 12 + i * 2, bar, 2))

    if score:
        # A linha de placar: o IP e o uso do disco ("192.168.1.155 - 42%").
        ip, _, used = ctx.get("status", "").partition(" - ")
        right = T.SAFE_X + T.SAFE_W
        w = text(surf, "NET", T.RED, T.SAFE_X, 32)
        text(surf, ip, T.FG, T.SAFE_X + w + 8, 32)
        w = text(surf, used, T.FG, right, 32, right=True)
        text(surf, "DISK", T.RED, right - w - 8, 32, right=True)

    total = sum(width(k) + 8 + width(a) for k, a in keys) + 16 * (len(keys) - 1)
    x = (T.WIDTH - total) // 2
    for key, action in keys:
        x += text(surf, key, T.CYAN, x, FOOTER_Y) + 8
        x += text(surf, action, T.COMMENT, x, FOOTER_Y) + 16


def paragraph(surf, lines, y, color=T.FG):
    """Desenha as linhas centradas (quebrando as longas) e devolve o y
    seguinte."""
    for line in lines:
        for part in wrap(line, T.SAFE_W) if line else [""]:
            centered(surf, part, color, y)
            y += 12
    return y


class Menu:
    """ui_menu / ui_menu_hints, ui_radio (mode="radio") e ui_checklist
    (mode="check"). entries: (valor, rotulo[, dica]). O menu simples e um
    carrossel: o icone de cada item vem de tiles (valor -> funcao que o
    desenha), de theme.ICONS (pelo valor) ou, sem nenhum, e a inicial."""

    def __init__(self, title, entries, default=None, text="", mode="menu", marked=(), tiles=None):
        self.title = title
        self.text = text
        self.mode = mode
        self.tiles = tiles or {}
        self.entries = [(e[0], e[1], e[2] if len(e) > 2 else "") for e in entries]
        self.marked = set(marked)
        self.cursor = 0
        self.top = 0
        for i, e in enumerate(self.entries):
            if e[0] == default:
                self.cursor = i

    def key(self, k):
        n = len(self.entries)
        if self.mode == "menu":
            k = {"left": "up", "right": "down"}.get(k, k)
        if k == "up":
            self.cursor = (self.cursor - 1) % n
        elif k == "down":
            self.cursor = (self.cursor + 1) % n
        elif k == "pgup":
            self.cursor = max(0, self.cursor - 5)
        elif k == "pgdn":
            self.cursor = min(n - 1, self.cursor + 5)
        elif k == "space" and self.mode == "check":
            self.marked ^= {self.entries[self.cursor][0]}
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            if self.mode == "check":
                return ("select", sorted(self.marked))
            return ("select", self.entries[self.cursor][0])
        return None

    def draw(self, surf, ctx):
        if self.mode == "menu":
            self.draw_carousel(surf, ctx)
        else:
            self.draw_list(surf, ctx)

    def tile(self, surf, entry, x, y, scale):
        """O icone do item, de 16*scale pixels, com o canto em (x, y)."""
        value, label, _ = entry
        size = 16 * scale
        if value in self.tiles:
            self.tiles[value](surf, x, y, scale)
            return
        img = T.icon(value, scale)
        if not img:
            img = big((value if len(value) <= 2 else label[:1]).upper(), scale, MARQUEE)
        surf.blit(img, (x + (size - img.get_width()) // 2, y + (size - img.get_height()) // 2))

    def draw_carousel(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "SELECT"), ("ENTER", "OK"), ("ESC", "BACK")],
              score=self.title.startswith("FliperOS"))
        n = len(self.entries)
        shade = pygame.Surface((40, 40), pygame.SRCALPHA)
        shade.fill(T.SPACE + (130,))
        for off, cx in ((-2, 36), (2, 284), (-1, 92), (1, 228)):
            if n < abs(off) * 2 + 1:
                continue
            entry = self.entries[(self.cursor + off) % n]
            pygame.draw.rect(surf, T.BG_DEEP, (cx - 20, 68, 40, 40))
            self.tile(surf, entry, cx - 16, 72, 2)
            surf.blit(shade, (cx - 20, 68))
            pygame.draw.rect(surf, T.LINE, (cx - 20, 68, 40, 40), 1)
        block(surf, (124, 48, 72, 72), T.BG_DEEP, T.PURPLE)
        pygame.draw.rect(surf, T.PINK, (124, 48, 72, 72), 2)
        self.tile(surf, self.entries[self.cursor], 128, 52, 4)

        label = self.entries[self.cursor][1].upper()
        scale = 2 if width(label) * 2 <= T.SAFE_W else 1
        name = big(label, scale, LABEL)
        x = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, scale, (0x80, 0x30, 0x60)), (x + 2, 134))
        surf.blit(name, (x, 132))
        hint = self.entries[self.cursor][2] or self.text
        if hint != self.text:
            # O texto do menu (um status, por exemplo) fica embaixo do letreiro.
            centered(surf, self.text, T.PINK, 34)
        for i, line in enumerate(wrap(hint, T.SAFE_W)[:3]):
            centered(surf, line, T.CYAN, 158 + i * 11)

        for i in range(n):
            color = T.PINK if i == self.cursor else T.LINE
            pygame.draw.rect(surf, color, (T.WIDTH // 2 - n * 5 + 2 + i * 10, 200, 6, 6))
        if self.title == "FliperOS":
            text(surf, "V" + ctx.get("version", ""), T.LINE, T.SAFE_X + T.SAFE_W, 199, right=True)

    def draw_list(self, surf, ctx):
        keys = [("ENTER", "OK"), ("ESC", "BACK")]
        if self.mode == "check":
            keys.insert(0, ("SPACE", "MARK"))
        frame(surf, ctx, self.title, keys)
        y0 = CONTENT_Y
        if self.text:
            y0 = paragraph(surf, [self.text], y0) + 4
        hints = any(e[2] for e in self.entries)
        bottom = HINT_Y - 6 if hints else FOOTER_Y - 8
        rows = max(1, (bottom - y0) // ROW)
        if self.cursor < self.top:
            self.top = self.cursor
        if self.cursor >= self.top + rows:
            self.top = self.cursor - rows + 1
        x = T.SAFE_X + 24
        w = T.SAFE_W - 48

        for i in range(self.top, min(len(self.entries), self.top + rows)):
            value, label, _ = self.entries[i]
            y = y0 + (i - self.top) * ROW
            selected = i == self.cursor
            if selected:
                block(surf, (x, y, w, ROW - 2), T.PINK, T.PURPLE)
            color = T.SPACE if selected else T.FG
            if self.mode == "menu":
                if selected:
                    pygame.draw.polygon(surf, T.SPACE, [(x + 5, y + 2), (x + 5, y + 9), (x + 9, y + 5)])
            else:
                on = value in self.marked
                pygame.draw.rect(surf, color if selected else T.COMMENT, (x + 4, y + 2, 8, 8), 1)
                if on:
                    pygame.draw.rect(surf, color if selected else T.GREEN, (x + 6, y + 4, 4, 4))
                    if not selected:
                        color = T.GREEN
            text(surf, label, color, x + 18, y + 2)

        # As setas de quando a lista rola.
        ax = x + w + 8
        if self.top > 0:
            pygame.draw.polygon(surf, T.CYAN, [(ax, y0 + 6), (ax + 6, y0 + 6), (ax + 3, y0 + 2)])
        if self.top + rows < len(self.entries):
            by = y0 + rows * ROW - 4
            pygame.draw.polygon(surf, T.CYAN, [(ax, by - 4), (ax + 6, by - 4), (ax + 3, by)])

        if hints:
            for i, line in enumerate(wrap(self.entries[self.cursor][2], T.SAFE_W)[:3]):
                centered(surf, line, T.CYAN, HINT_Y + i * 11)


class YesNo:
    """ui_yesno e ui_choice2: a pergunta e dois botoes."""

    def __init__(self, title, lines, default="yes", yes="YES", no="NO", icon=None):
        self.title = title
        self.lines = lines
        self.labels = (yes, no)
        self.icon = icon
        self.choice = 0 if default == "yes" else 1

    def key(self, k):
        if k in ("left", "right", "up", "down"):
            self.choice ^= 1
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("select", "yes" if self.choice == 0 else "no")
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "SELECT"), ("ENTER", "OK"), ("ESC", "BACK")])
        img = T.icon(self.icon, 2) if self.icon else None
        if img:
            surf.blit(img, ((T.WIDTH - 32) // 2, 38))
        y = paragraph(surf, self.lines, 80) + 12
        button(surf, self.labels[0], 104, y, self.choice == 0)
        button(surf, self.labels[1], 216, y, self.choice == 1)


class Message:
    """ui_msg (espera o Enter) e, com kind="error", o aviso de falha."""

    def __init__(self, title, lines, kind="info"):
        self.title = title
        self.lines = lines
        self.kind = kind

    def key(self, k):
        if k in ("enter", "esc"):
            return ("back", None)
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ENTER", "OK")], self.kind == "error")
        y = paragraph(surf, self.lines, 72) + 20
        button(surf, "OK", T.WIDTH // 2, y, True)


class Input:
    """ui_input: um campo de texto. O cursor e fixo, nao pisca. Com action
    (valor, rotulo, explicacao) ha um botao embaixo do campo: as setas para
    cima e para baixo trocam entre os dois, e o Enter no botao devolve o
    valor dele."""

    def __init__(self, title, lines, value="", password=False, action=None, focus=0):
        self.title = title
        self.lines = lines
        self.value = value
        self.password = password
        self.action = action
        self.focus = focus if action else 0

    def key(self, k):
        if k == "esc":
            return ("back", None)
        if k in ("up", "down") and self.action:
            self.focus ^= 1
        elif k == "enter":
            return ("select", self.action[0] if self.focus else self.value)
        elif self.focus:
            return None
        elif k == "backspace":
            self.value = self.value[:-1]
        elif len(k) == 1:
            self.value += k
        return None

    def draw(self, surf, ctx):
        keys = [("ENTER", "OK"), ("ESC", "BACK")]
        if self.action:
            keys.insert(0, ("UP DOWN", "SELECT"))
        frame(surf, ctx, self.title, keys)
        y = paragraph(surf, self.lines, 56 if self.action else 80) + 12
        x = T.SAFE_X
        on = not self.focus
        block(surf, (x, y, T.SAFE_W - 2, 22), T.BG_DEEP, T.PURPLE if on else None)
        pygame.draw.rect(surf, T.PINK if on else T.LINE, (x, y, T.SAFE_W - 2, 22), 2 if on else 1)
        shown = "*" * len(self.value) if self.password else self.value
        # Um texto longo (um magnet link) mostra so o fim, onde se digita.
        if width(shown) > T.SAFE_W - 32:
            while width(".." + shown) > T.SAFE_W - 32:
                shown = shown[1:]
            shown = ".." + shown
        w = text(surf, shown, T.FG, x + 8, y + 7)
        if on:
            pygame.draw.rect(surf, T.PINK, (x + 9 + w, y + 6, 7, 10))
        if self.action:
            _, label, about = self.action
            button(surf, label, T.WIDTH // 2, y + 40, bool(self.focus), w=width(label) + 32)
            paragraph(surf, [about], y + 72, T.CYAN)


class Progress:
    """A tela de progresso (screens/progress.sh): os passos, a barra e a
    ultima mensagem. steps: (rotulo, "done" | "run" | "todo" | "fail")."""

    def __init__(self, title, steps, pct, msg=""):
        self.title = title
        self.steps = steps
        self.pct = pct
        self.msg = msg

    def key(self, k):
        return ("back", None) if k == "esc" else None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [])
        x, y = T.SAFE_X + 24, 56
        for label, state in self.steps:
            color = {"done": T.GREEN, "run": T.YELLOW, "fail": T.RED}.get(state, T.COMMENT)
            if state == "run":
                pygame.draw.polygon(surf, T.PINK, [(x + 2, y), (x + 2, y + 7), (x + 6, y + 3)])
            elif state == "todo":
                pygame.draw.rect(surf, color, (x + 1, y + 1, 6, 6), 1)
            else:
                pygame.draw.rect(surf, color, (x + 1, y + 1, 6, 6))
            text(surf, label, color, x + 16, y)
            y += ROW
        # A barra em blocos: 24 de 10 pixels, com 2 de espaco, uma cor do
        # arco-iris a cada 4.
        x, y = T.SAFE_X, 150
        full = round(self.pct * 24 / 100)
        for i in range(24):
            pygame.draw.rect(surf, RAINBOW[i // 4] if i < full else T.LINE, (x + i * 12, y, 10, 12))
        pct = "%d%%" % self.pct
        name = big(pct, 2, T.YELLOW)
        surf.blit(name, ((T.WIDTH - name.get_width()) // 2, y + 22))
        centered(surf, wrap(self.msg, T.SAFE_W)[0], T.CYAN, y + 48)


def round_button(surf, cx, cy, r, state, label=""):
    """Um botao do painel: "done" (ja tem), "ask" (o da vez) ou "todo"."""
    if state == "ask":
        pygame.draw.circle(surf, T.PINK, (cx, cy), r + 3)
    if state == "todo":
        pygame.draw.circle(surf, T.SPACE, (cx, cy), r)
        pygame.draw.circle(surf, T.LINE, (cx, cy), r, 1)
    else:
        pygame.draw.circle(surf, T.YELLOW if state == "ask" else T.GREEN, (cx, cy), r)
    if label:
        text(surf, label, T.COMMENT if state == "todo" else T.SPACE, cx - width(label) // 2 + 1, cy - 4)


def layout_tile(order):
    """O icone de um layout no carrossel: o painel de 3x2 com o numero do
    botao do jogo em cada posicao usada (order: a posicao de cada botao)."""
    def draw(surf, x, y, scale):
        size = 16 * scale
        for pos in range(6):
            cx = x + size * (1 + 2 * (pos % 3)) // 6
            cy = y + size * (1 + pos // 3) // 3
            if pos + 1 in order:
                round_button(surf, cx, cy, scale * 2, "done", str(order.index(pos + 1) + 1) if scale > 2 else "")
            else:
                round_button(surf, cx, cy, scale * 2, "todo")
    return draw


class Capture:
    """O Button mapping pedindo um comando: o painel desenhado, com o
    comando da vez aceso e os ja apertados em verde. controls sao up, down,
    left, right, b1 a b6, start e coin."""

    LABELS = {"up": "UP", "down": "DOWN", "left": "LEFT", "right": "RIGHT", "start": "START", "coin": "COIN"}

    def __init__(self, title, player, asking, done=(), number=1, total=12, left=8, seconds=8):
        self.title = title
        self.player = player
        self.asking = asking
        self.done = set(done)
        self.number, self.total = number, total
        self.left, self.seconds = left, seconds

    def key(self, k):
        return ("back", None) if k == "esc" else None

    def state(self, control):
        if control == self.asking:
            return "ask"
        return "done" if control in self.done else "todo"

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("WAIT", "TO SKIP IT")])
        block(surf, (24, 44, 272, 104), T.BG_DEEP, T.PURPLE)
        pygame.draw.rect(surf, T.LINE, (24, 44, 272, 104), 1)
        text(surf, "PLAYER %d" % self.player, T.PINK, 34, 53)

        for control, x in (("start", 168), ("coin", 232)):
            state = self.state(control)
            if state == "ask":
                pygame.draw.rect(surf, T.PINK, (x - 3, 48, 54, 18))
            if state == "todo":
                pygame.draw.rect(surf, T.LINE, (x, 51, 48, 12), 1)
            else:
                pygame.draw.rect(surf, T.YELLOW if state == "ask" else T.GREEN, (x, 51, 48, 12))
            label = self.LABELS[control]
            text(surf, label, T.COMMENT if state == "todo" else T.SPACE, x + 24 - width(label) // 2 + 1, 53)

        # O direcional: a alavanca no meio e uma seta para cada lado.
        cx, cy = 84, 106
        pygame.draw.circle(surf, T.LINE, (cx, cy), 15)
        pygame.draw.circle(surf, T.RED, (cx, cy), 8)
        pygame.draw.rect(surf, T.FG, (cx - 3, cy - 4, 2, 2))
        for control, dx, dy in (("up", 0, -1), ("down", 0, 1), ("left", -1, 0), ("right", 1, 0)):
            state = self.state(control)
            for grow, color in ((3, T.PINK if state == "ask" else None),
                                (0, {"ask": T.YELLOW, "done": T.GREEN}.get(state, T.LINE))):
                if color:
                    tip, base, half = 32 + grow, 21 - grow, 7 + grow
                    pygame.draw.polygon(surf, color, [
                        (cx + dx * tip, cy + dy * tip),
                        (cx + dx * base - dy * half, cy + dy * base - dx * half),
                        (cx + dx * base + dy * half, cy + dy * base + dx * half)])

        for i in range(6):
            control = "b%d" % (i + 1)
            round_button(surf, 176 + (i % 3) * 36, 92 + (i // 3) * 32, 11, self.state(control), str(i + 1))

        label = "PRESS " + self.LABELS.get(self.asking, "BUTTON " + self.asking[1:])
        name = big(label, 2, LABEL)
        x = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, 2, (0x80, 0x30, 0x60)), (x + 2, 160))
        surf.blit(name, (x, 158))
        centered(surf, "%d OF %d" % (self.number, self.total), T.CYAN, 182)
        # O tempo que falta para pular o comando, um quadrado por segundo.
        for i in range(self.seconds):
            color = T.PINK if i < self.left else T.LINE
            pygame.draw.rect(surf, color, (T.WIDTH // 2 - self.seconds * 5 + 2 + i * 10, 198, 6, 6))


class LayoutEdit:
    """O Buttons layout: escolher no proprio painel de 3x2 onde fica o
    proximo botao do jogo. order e a posicao (1 a 6) dos botoes ja postos."""

    POSITIONS = ["Top row, left", "Top row, middle", "Top row, right",
                 "Bottom row, left", "Bottom row, middle", "Bottom row, right"]

    def __init__(self, title, count, order=()):
        self.title = title
        self.count = count
        self.order = list(order)
        self.cursor = next(p for p in range(6) if p + 1 not in self.order)

    def key(self, k):
        col, row = self.cursor % 3, self.cursor // 3
        if k == "left":
            col = (col - 1) % 3
        elif k == "right":
            col = (col + 1) % 3
        elif k in ("up", "down"):
            row ^= 1
        elif k == "esc":
            return ("back", None)
        elif k == "enter" and self.cursor + 1 not in self.order:
            return ("select", self.cursor + 1)
        self.cursor = row * 3 + col
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ARROWS", "MOVE"), ("ENTER", "OK"), ("ESC", "BACK")])
        n = len(self.order) + 1
        centered(surf, "%d-BUTTON GAMES" % self.count, T.PINK, 36)
        block(surf, (64, 50, 192, 96), T.BG_DEEP, T.PURPLE)
        pygame.draw.rect(surf, T.LINE, (64, 50, 192, 96), 1)
        for pos in range(6):
            cx, cy = 112 + (pos % 3) * 48, 78 + (pos // 3) * 40
            if pos + 1 in self.order:
                if pos == self.cursor:
                    pygame.draw.circle(surf, T.PINK, (cx, cy), 18)
                round_button(surf, cx, cy, 15, "done", str(self.order.index(pos + 1) + 1))
            elif pos == self.cursor:
                round_button(surf, cx, cy, 15, "ask", str(n))
            else:
                round_button(surf, cx, cy, 15, "todo")

        label = "WHERE IS BUTTON %d?" % n
        name = big(label, 2, LABEL)
        x = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, 2, (0x80, 0x30, 0x60)), (x + 2, 160))
        surf.blit(name, (x, 158))
        centered(surf, self.POSITIONS[self.cursor], T.CYAN, 184)
        centered(surf, "Green: buttons already placed.", T.COMMENT, 198)


WHITE = (255, 255, 255)


def bullseye(surf, cx, cy):
    """O alvo: os aneis e o + do meio, onde se mira."""
    for r, color in ((18, T.RED), (13, WHITE), (8, T.RED), (3, WHITE)):
        pygame.draw.circle(surf, color, (cx, cy), r)
    pygame.draw.line(surf, T.SPACE, (cx - 24, cy), (cx + 24, cy))
    pygame.draw.line(surf, T.SPACE, (cx, cy - 24), (cx, cy + 24))


class GunTarget:
    """A calibracao do GunCon 2 pedindo os tiros num alvo. A tela e branca:
    a pistola so enxerga a tela onde ha luz, entao aqui nao ha fundo escuro
    nem letreiro. where e "top-left", "bottom-right" ou "center"."""

    SPOTS = {"top-left": (44, 40), "bottom-right": (276, 200), "center": (160, 120)}

    def __init__(self, step, steps, where, need=3, shots=0, last=""):
        self.step, self.steps = step, steps
        self.where = where
        self.need, self.shots = need, shots
        self.last = last

    def key(self, k):
        return ("back", None) if k == "esc" else None

    def draw(self, surf, ctx):
        surf.fill(WHITE)
        bullseye(surf, *self.SPOTS[self.where])
        # No alvo do centro o texto sobe, para nao ficar em cima dele.
        y = 40 if self.where == "center" else 84
        centered(surf, "GUNCON 2 CALIBRATION", T.COMMENT, y)
        label = "TARGET %d OF %d" % (self.step, self.steps)
        name = big(label, 2, [T.SPACE, T.SPACE, (0x40, 0x20, 0x70), (0x40, 0x20, 0x70)])
        surf.blit(name, ((T.WIDTH - name.get_width()) // 2, y + 14))
        if self.where == "center":
            y = 140
        centered(surf, "Aim at the + and pull the trigger", T.SPACE, y + 38)
        # Um cartucho por tiro: cheio o que falta, vazio o ja dado.
        x = T.WIDTH // 2 - self.need * 8
        for i in range(self.need):
            rect = (x + i * 16 + 3, y + 54, 9, 16)
            if i < self.shots:
                pygame.draw.rect(surf, T.LINE, rect, 1)
            else:
                pygame.draw.rect(surf, T.ORANGE, rect)
                pygame.draw.rect(surf, T.RED, (rect[0], rect[1], 9, 5))
                pygame.draw.rect(surf, T.SPACE, rect, 1)
        centered(surf, self.last, T.COMMENT, y + 76)
        if self.where != "bottom-right":
            text(surf, "ESC CANCEL", T.COMMENT, T.SAFE_X + T.SAFE_W, FOOTER_Y, right=True)
        else:
            text(surf, "ESC CANCEL", T.COMMENT, T.SAFE_X, FOOTER_Y)


class GunResult:
    """O fim da calibracao: onde o tiro de conferencia caiu em relacao ao
    centro (hit e want em % da tela), e salvar ou repetir."""

    def __init__(self, title, hit, want=(50, 50)):
        self.title = title
        self.hit, self.want = hit, want
        self.choice = 0

    def key(self, k):
        if k in ("left", "right", "up", "down"):
            self.choice ^= 1
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("select", "yes" if self.choice == 0 else "no")
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "SELECT"), ("ENTER", "OK"), ("ESC", "BACK")])
        # A tela em miniatura, com o alvo no centro e o tiro onde caiu.
        x, y, w, h = 104, 42, 112, 84
        block(surf, (x, y, w, h), T.FG, T.PURPLE)
        pygame.draw.rect(surf, T.PINK, (x, y, w, h), 2)
        cx, cy = x + w * self.want[0] // 100, y + h * self.want[1] // 100
        for r, color in ((14, T.RED), (10, T.FG), (6, T.RED), (2, T.FG)):
            pygame.draw.circle(surf, color, (cx, cy), r)
        hx, hy = x + round(w * self.hit[0] / 100), y + round(h * self.hit[1] / 100)
        pygame.draw.circle(surf, T.SPACE, (hx, hy), 4)
        pygame.draw.circle(surf, T.GREEN, (hx, hy), 3)

        off = max(abs(self.hit[0] - self.want[0]), abs(self.hit[1] - self.want[1]))
        label = "ON TARGET!" if off <= 3 else "A BIT OFF"
        name = big(label, 2, LABEL)
        nx = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, 2, (0x80, 0x30, 0x60)), (nx + 2, 138))
        surf.blit(name, (nx, 136))
        centered(surf, "Center shot at %d%% x %d%%" % self.hit, T.CYAN, 160)
        centered(surf, "(target %d%% x %d%%)" % self.want, T.COMMENT, 171)
        button(surf, "SAVE", 104, 188, self.choice == 0)
        button(surf, "RETRY", 216, 188, self.choice == 1)


class Download:
    """O download do romset em andamento (screen_downloader_watch): uma
    linha por torrent (rotulo, feito, total, peers e fracao de 0 a 1), a
    barra do total, a velocidade e o tempo que falta."""

    def __init__(self, title, parts, pct, speed, left):
        self.title = title
        self.parts = parts
        self.pct = pct
        self.speed, self.left = speed, left

    def key(self, k):
        return ("back", None)

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ANY KEY", "BACK TO THE MENU")])
        x, right = T.SAFE_X, T.SAFE_X + T.SAFE_W
        y = 38
        for label, done, total, peers, frac in self.parts:
            w = text(surf, label, T.PINK, x, y)
            text(surf, "%d PEERS" % peers, T.COMMENT, x + w + 8, y)
            w = text(surf, total, T.FG, right, y, right=True)
            w += text(surf, "OF", T.COMMENT, right - w - 8, y, right=True) + 8
            text(surf, done, T.GREEN, right - w - 8, y, right=True)
            pygame.draw.rect(surf, T.LINE, (x, y + 11, T.SAFE_W, 5))
            pygame.draw.rect(surf, T.GREEN, (x, y + 11, round(T.SAFE_W * frac), 5))
            y += 26

        # A barra do total, em blocos, e a porcentagem grande.
        full = round(self.pct * 24 / 100)
        for i in range(24):
            pygame.draw.rect(surf, RAINBOW[i // 4] if i < full else T.LINE, (x + i * 12, 96, 10, 12))
        name = big("%d%%" % self.pct, 3, T.YELLOW)
        surf.blit(name, ((T.WIDTH - name.get_width()) // 2, 118))

        for bx, label, value in ((x, "SPEED", self.speed), (168, "TIME LEFT", self.left)):
            block(surf, (bx, 152, 134, 30), T.BG_DEEP, T.PURPLE)
            pygame.draw.rect(surf, T.LINE, (bx, 152, 134, 30), 1)
            text(surf, label, T.RED, bx + 8, 157)
            text(surf, value, T.FG, bx + 8, 169)
        centered(surf, "The download goes on in the", T.CYAN, 192)
        centered(surf, "background, even with a game open.", T.CYAN, 203)


def person(surf, x, y, s, color):
    """Um jogador: a cabeca e o corpo, em 8*s por 12*s pixels."""
    pygame.draw.rect(surf, color, (x + 2 * s, y, 4 * s, 4 * s))
    pygame.draw.rect(surf, color, (x + s, y + 5 * s, 6 * s, 7 * s))


def count_color(kind, n, i):
    """A cor da figura i de um "ate n": apagada depois de n, e todas em
    amarelo quando n e 0 (qualquer quantidade)."""
    if not n:
        return T.YELLOW
    if i >= n:
        return T.LINE
    return T.CYAN if kind == "people" else T.PINK


def mini(surf, kind, data, x, y):
    """O valor de um parametro desenhado dentro do azulejo (84x20 pixels a
    partir de x, y)."""
    if kind in ("people", "dots"):
        n, top = data
        for i in range(top):
            color = count_color(kind, n, i)
            if kind == "people":
                person(surf, x + i * 10, y + 2, 1, color)
            else:
                pygame.draw.circle(surf, color, (x + 4 + i * 10, y + 8), 4)
    elif kind == "blocks":
        flags, label = data
        w = 84 // len(flags)
        for i, flag in enumerate(flags):
            pygame.draw.rect(surf, RAINBOW[i % 6] if flag else T.LINE, (x + i * w, y, w - 2, 8))
        text(surf, label, T.FG, x, y + 11)
    elif kind == "lamps":
        for i, color in enumerate((T.GREEN, T.YELLOW, T.RED)):
            pygame.draw.circle(surf, color if i < data else T.LINE, (x + 8 + i * 22, y + 9), 7)
    elif kind == "switch":
        flag, label = data
        pygame.draw.rect(surf, T.GREEN if flag else T.LINE, (x, y + 4, 24, 10))
        pygame.draw.rect(surf, T.FG, (x + (14 if flag else 0), y + 2, 10, 14))
        text(surf, label, T.FG if flag else T.COMMENT, x + 30, y + 5)
    elif kind == "screens":
        wide, tall = data
        pygame.draw.rect(surf, T.CYAN if wide else T.LINE, (x + 8, y + 3, 24, 16), 0 if wide else 1)
        pygame.draw.rect(surf, T.CYAN if tall else T.LINE, (x + 50, y, 16, 20), 0 if tall else 1)
    else:
        text(surf, data, T.GREEN if kind == "action" else T.FG, x, y + 5)


class FilterBoard:
    """Os parametros do filtro de ROMs num painel de azulejos: cada um
    mostra o proprio valor desenhado. items: (chave, titulo, tipo, dado,
    ajuda); os tipos sao os de mini()."""

    COLS, ROWS = 3, 3

    def __init__(self, title, items, cursor=0, games="", size=""):
        self.title = title
        self.items = items
        self.cursor = cursor
        self.games, self.size = games, size
        self.top = 0

    def key(self, k):
        n = len(self.items)
        step = {"left": -1, "right": 1, "up": -self.COLS, "down": self.COLS}.get(k)
        if step and 0 <= self.cursor + step < n:
            self.cursor += step
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("select", self.items[self.cursor][0])
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ARROWS", "MOVE"), ("ENTER", "CHANGE"), ("ESC", "BACK")])
        # O placar: quantos jogos passam no filtro e quanto ocupam.
        x, right = T.SAFE_X, T.SAFE_X + T.SAFE_W
        w = text(surf, "GAMES", T.RED, x, 34)
        text(surf, self.games, T.FG, x + w + 8, 34)
        w = text(surf, self.size, T.FG, right, 34, right=True)
        text(surf, "SIZE", T.RED, right - w - 8, 34, right=True)

        row = self.cursor // self.COLS
        self.top = min(max(self.top, row - self.ROWS + 1), row)
        rows = (len(self.items) + self.COLS - 1) // self.COLS
        for r in range(rows):
            color = T.PINK if r == row else T.COMMENT if self.top <= r < self.top + self.ROWS else T.LINE
            pygame.draw.rect(surf, color, (T.WIDTH // 2 - rows * 3 + r * 6, 36, 4, 4))

        for i in range(self.top * self.COLS, min(len(self.items), (self.top + self.ROWS) * self.COLS)):
            _, title, kind, data, _ = self.items[i]
            tx = x + (i % self.COLS) * 98
            ty = 48 + (i // self.COLS - self.top) * 44
            on = i == self.cursor
            block(surf, (tx, ty, 92, 40), T.BG_DEEP, T.PURPLE if on else None)
            pygame.draw.rect(surf, T.PINK if on else T.LINE, (tx, ty, 92, 40), 2 if on else 1)
            text(surf, title.upper(), T.PINK if on else T.COMMENT, tx + 4, ty + 4)
            mini(surf, kind, data, tx + 4, ty + 16)

        for i, line in enumerate(wrap(self.items[self.cursor][4], T.SAFE_W)[:2]):
            centered(surf, line, T.CYAN, 186 + i * 11)


class Stepper:
    """Um parametro de quantidade maxima (jogadores, botoes): as figuras
    acesas ate o valor. options: (valor, rotulo); o valor 0 e qualquer
    quantidade."""

    def __init__(self, title, help, options, current, kind="people"):
        self.title = title
        self.help = help
        self.options = options
        self.kind = kind
        self.cursor = [o[0] for o in options].index(current)

    def key(self, k):
        if k in ("left", "down"):
            self.cursor = max(0, self.cursor - 1)
        elif k in ("right", "up"):
            self.cursor = min(len(self.options) - 1, self.cursor + 1)
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("select", self.options[self.cursor][0])
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "CHANGE"), ("ENTER", "OK"), ("ESC", "BACK")])
        top = max(int(o[0]) for o in self.options)
        n = int(self.options[self.cursor][0])
        x0 = (T.WIDTH - (top * 32 - 8)) // 2
        for i in range(top):
            color = count_color(self.kind, n, i)
            if self.kind == "people":
                person(surf, x0 + i * 32, 56, 3, color)
            else:
                pygame.draw.circle(surf, color, (x0 + 12 + i * 32, 74), 12)
        label = self.options[self.cursor][1].upper()
        name = big(label, 2, LABEL)
        nx = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, 2, (0x80, 0x30, 0x60)), (nx + 2, 112))
        surf.blit(name, (nx, 110))
        count = len(self.options)
        for i in range(count):
            pygame.draw.rect(surf, T.PINK if i == self.cursor else T.LINE,
                             (T.WIDTH // 2 - count * 5 + 2 + i * 10, 138, 6, 6))
        for i, line in enumerate(wrap(self.help, T.SAFE_W)[:3]):
            centered(surf, line, T.CYAN, 160 + i * 11)


def control_art(surf, cx, cy, value, color):
    """O desenho de cada tipo de controle do painel (o filtro Controls)."""
    c, d = pygame.draw.circle, pygame.draw.rect
    if value in ("joy8", "joy4", "joy2"):
        c(surf, color, (cx, cy), 5)
        ways = {"joy8": [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)],
                "joy4": [(0, -1), (-1, 0), (1, 0), (0, 1)], "joy2": [(-1, 0), (1, 0)]}[value]
        for dx, dy in ways:
            d(surf, color, (cx + dx * 11 - 1, cy + dy * 11 - 1, 3, 3))
    elif value == "twin":
        for dx in (-8, 8):
            c(surf, color, (cx + dx, cy - 4), 5)
            d(surf, color, (cx + dx - 1, cy, 3, 9))
    elif value == "trackball":
        c(surf, color, (cx, cy), 11)
        c(surf, T.BG_DEEP, (cx - 4, cy - 4), 3)
    elif value == "spinner":
        c(surf, color, (cx, cy), 11, 3)
        d(surf, color, (cx - 1, cy - 11, 3, 8))
    elif value == "paddle":
        c(surf, color, (cx, cy), 11, 3)
        d(surf, color, (cx - 11, cy - 1, 23, 3))
        d(surf, T.BG_DEEP, (cx - 12, cy + 6, 25, 7))
    elif value == "positional":
        c(surf, color, (cx, cy), 12, 1)
        c(surf, color, (cx, cy), 6)
        d(surf, color, (cx + 9, cy - 9, 4, 4))
    elif value == "analog":
        pygame.draw.line(surf, color, (cx - 4, cy + 10), (cx + 5, cy - 6), 3)
        c(surf, color, (cx + 6, cy - 8), 5)
        d(surf, color, (cx - 11, cy + 9, 22, 3))
    elif value == "pedal":
        pygame.draw.polygon(surf, color, [(cx - 5, cy - 11), (cx + 5, cy - 11), (cx + 9, cy + 9), (cx - 9, cy + 9)])
        d(surf, color, (cx - 12, cy + 10, 24, 3))
    elif value == "lightgun":
        d(surf, color, (cx - 12, cy - 8, 22, 6))
        d(surf, color, (cx - 6, cy - 2, 7, 12))
        d(surf, color, (cx + 9, cy - 10, 2, 2))
    elif value == "keyboard":
        for i in range(12):
            d(surf, color, (cx - 11 + (i % 4) * 6, cy - 9 + (i // 4) * 6, 5, 5))
    else:
        d(surf, color, (cx - 8, cy - 11, 16, 22), 2)
        for dx, dy in ((-3, -5), (3, -5), (0, 0), (-3, 5), (3, 5)):
            d(surf, color, (cx + dx - 1, cy + dy - 1, 3, 3))


class ToggleGrid:
    """Um parametro de marcar varios (controles, anos) como uma grade de
    azulejos: o cursor anda pela grade e Espaco marca. art desenha cada
    opcao (surf, cx, cy, valor, cor); sem ela, o azulejo mostra o rotulo."""

    def __init__(self, title, help, options, marked, cols, art=None, cursor=0):
        self.title = title
        self.help = help
        self.options = options
        self.marked = set(marked)
        self.cols = cols
        self.art = art
        self.cursor = cursor

    def key(self, k):
        step = {"left": -1, "right": 1, "up": -self.cols, "down": self.cols}.get(k)
        if step and 0 <= self.cursor + step < len(self.options):
            self.cursor += step
        elif k == "space":
            self.marked ^= {self.options[self.cursor][0]}
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("select", sorted(self.marked))
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ARROWS", "MOVE"), ("SPACE", "MARK"), ("ENTER", "OK")])
        w = (T.SAFE_W - (self.cols - 1) * 6) // self.cols
        y0 = 38 if len(self.options) > self.cols else 76
        for i, (value, label, short) in enumerate(self.options):
            x = T.SAFE_X + (i % self.cols) * (w + 6)
            y = y0 + (i // self.cols) * 43
            marked = value in self.marked
            on = i == self.cursor
            block(surf, (x, y, w, 38), T.BG_DEEP, T.PURPLE if on else None)
            pygame.draw.rect(surf, T.PINK if on else T.GREEN if marked else T.LINE, (x, y, w, 38), 2 if on else 1)
            color = T.FG if marked else T.LINE
            if self.art:
                self.art(surf, x + w // 2, y + 19, value, color)
            else:
                text(surf, short, color, x + (w - width(short)) // 2 + 1, y + 15)
            if marked:
                pygame.draw.rect(surf, T.GREEN, (x + w - 9, y + 3, 6, 6))

        value, label, _ = self.options[self.cursor]
        label = label.upper()
        scale = 2 if width(label) * 2 <= T.SAFE_W else 1
        name = big(label, scale, LABEL if value in self.marked else [T.COMMENT])
        surf.blit(name, ((T.WIDTH - name.get_width()) // 2, 172 if scale == 2 else 176))
        for i, line in enumerate(wrap(self.help, T.SAFE_W)[:2]):
            centered(surf, line, T.CYAN, 194 + i * 11)
