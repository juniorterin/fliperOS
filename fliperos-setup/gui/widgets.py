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
    (mode="check"). entries: (valor, rotulo[, dica]). Com icons=True o menu
    e um carrossel de icones (theme.ICONS, pelo valor)."""

    def __init__(self, title, entries, default=None, text="", mode="menu", marked=(), icons=False):
        self.title = title
        self.text = text
        self.mode = mode
        self.icons = icons
        self.entries = [(e[0], e[1], e[2] if len(e) > 2 else "") for e in entries]
        self.marked = set(marked)
        self.cursor = 0
        self.top = 0
        for i, e in enumerate(self.entries):
            if e[0] == default:
                self.cursor = i

    def key(self, k):
        n = len(self.entries)
        if self.icons:
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
        if self.icons:
            self.draw_carousel(surf, ctx)
        else:
            self.draw_list(surf, ctx)

    def draw_carousel(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "SELECT"), ("ENTER", "OK"), ("ESC", "BACK")],
              score=self.title.startswith("FliperOS"))
        n = len(self.entries)
        shade = pygame.Surface((40, 40), pygame.SRCALPHA)
        shade.fill(T.SPACE + (130,))
        for off, cx in ((-2, 36), (2, 284), (-1, 92), (1, 228)):
            if n < abs(off) * 2 + 1:
                continue
            value = self.entries[(self.cursor + off) % n][0]
            pygame.draw.rect(surf, T.BG_DEEP, (cx - 20, 68, 40, 40))
            img = T.icon(value, 2)
            if img:
                surf.blit(img, (cx - 16, 72))
            surf.blit(shade, (cx - 20, 68))
            pygame.draw.rect(surf, T.LINE, (cx - 20, 68, 40, 40), 1)
        block(surf, (124, 48, 72, 72), T.BG_DEEP, T.PURPLE)
        pygame.draw.rect(surf, T.PINK, (124, 48, 72, 72), 2)
        img = T.icon(self.entries[self.cursor][0], 4)
        if img:
            surf.blit(img, (128, 52))

        label = self.entries[self.cursor][1].upper()
        scale = 2 if width(label) * 2 <= T.SAFE_W else 1
        name = big(label, scale, LABEL)
        x = (T.WIDTH - name.get_width()) // 2
        surf.blit(big(label, scale, (0x80, 0x30, 0x60)), (x + 2, 134))
        surf.blit(name, (x, 132))
        for i, line in enumerate(wrap(self.entries[self.cursor][2], T.SAFE_W)[:3]):
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

    def __init__(self, title, lines, default="yes", yes="YES", no="NO"):
        self.title = title
        self.lines = lines
        self.labels = (yes, no)
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
        y = paragraph(surf, self.lines, 80) + 20
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
    """ui_input: um campo de texto. O cursor e fixo, nao pisca."""

    def __init__(self, title, lines, value="", password=False):
        self.title = title
        self.lines = lines
        self.value = value
        self.password = password

    def key(self, k):
        if k == "esc":
            return ("back", None)
        if k == "enter":
            return ("select", self.value)
        if k == "backspace":
            self.value = self.value[:-1]
        elif len(k) == 1:
            self.value += k
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ENTER", "OK"), ("ESC", "BACK")])
        y = paragraph(surf, self.lines, 80) + 12
        x = T.SAFE_X
        block(surf, (x, y, T.SAFE_W - 2, 22), T.BG_DEEP, T.PURPLE)
        pygame.draw.rect(surf, T.PINK, (x, y, T.SAFE_W - 2, 22), 2)
        shown = "*" * len(self.value) if self.password else self.value
        w = text(surf, shown, T.FG, x + 8, y + 7)
        pygame.draw.rect(surf, T.PINK, (x + 9 + w, y + 6, 7, 10))


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
