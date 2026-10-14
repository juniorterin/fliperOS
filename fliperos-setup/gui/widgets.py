# As telas da interface grafica: uma classe para cada primitiva de
# fliperos-setup/lib/ui.sh (ui_menu, ui_radio, ui_checklist, ui_yesno,
# ui_msg, ui_input e a tela de progresso).
#
# Cada tela tem draw(surf, ctx), que desenha na tela logica de 320x240, e
# key(nome), que devolve None, ("back", None) ou ("select", valor).
#
# Como no Setup de texto, nada anima nem pisca: a tela so e redesenhada
# quando uma tecla muda alguma coisa (redesenho continuo tremula num modo
# entrelacado).

import pygame

import theme as T

ROW = 17
CONTENT_Y = 54
HINT_Y = 178
HINT_H = 34
FOOTER_Y = 214


def text(surf, font, s, color, x, y, right=False):
    img = T.font(font).render(s, False, color)
    if font == "text":
        # A Jersey 10 tem 6 linhas vazias em cima da maiuscula.
        y -= 3
    if right:
        x -= img.get_width()
    surf.blit(img, (x, y))
    return img.get_width()


def width(font, s):
    return T.font(font).size(s)[0]


def wrap(font, s, w):
    """Quebra o texto em linhas de ate w pixels, sem cortar palavras."""
    lines, line = [], ""
    for word in s.split():
        trial = word if not line else line + " " + word
        if line and width(font, trial) > w:
            lines.append(line)
            line = word
        else:
            line = trial
    if line or not lines:
        lines.append(line)
    return lines


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
        color = T.BG
    else:
        block(surf, (x, y, w, 20), T.BG_DEEP, None)
        pygame.draw.rect(surf, T.LINE, (x, y, w, 20), 1)
        color = T.FG
    text(surf, "title", label, color, cx - width("title", label) // 2, y + 6)


def frame(surf, ctx, title, keys, accent=T.PURPLE):
    """O fundo, a barra do topo, a etiqueta do titulo e a legenda das teclas."""
    surf.fill(T.BG)
    x = T.SAFE_X
    right = T.SAFE_X + T.SAFE_W
    w = text(surf, "title", "FLIPEROS", T.PURPLE, x, T.SAFE_Y + 4)
    text(surf, "text", ctx.get("version", ""), T.COMMENT, x + w + 6, T.SAFE_Y - 1)
    text(surf, "text", ctx.get("status", ""), T.CYAN, right, T.SAFE_Y - 1, right=True)
    pygame.draw.line(surf, T.COMMENT, (x, 27), (right - 1, 27))
    # Uma faixa pontilhada embaixo da linha, no lugar de um degrade.
    for px in range(x, right):
        surf.set_at((px, 28 + px % 2), T.LINE)

    tw = width("title", title.upper())
    block(surf, (x, 34, tw + 12, 14), accent)
    text(surf, "title", title.upper(), T.BG, x + 6, 37)

    kx = x
    for key, label in keys:
        kx += text(surf, "text", key, T.CYAN, kx, FOOTER_Y) + 4
        kx += text(surf, "text", label, T.COMMENT, kx, FOOTER_Y) + 12


def paragraph(surf, lines, y, color=T.FG):
    """Desenha as linhas (quebrando as longas) e devolve o y seguinte."""
    for line in lines:
        for part in wrap("text", line, T.SAFE_W) if line else [""]:
            text(surf, "text", part, color, T.SAFE_X, y)
            y += ROW
    return y


class Menu:
    """ui_menu / ui_menu_hints, ui_radio (mode="radio") e ui_checklist
    (mode="check"). entries: (valor, rotulo[, dica])."""

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
        keys = [("ENTER", "ok"), ("ESC", "back")]
        if self.mode == "check":
            keys.insert(0, ("SPACE", "mark"))
        frame(surf, ctx, self.title, keys)
        y0 = CONTENT_Y
        if self.text:
            y0 = paragraph(surf, [self.text], y0) + 4
        hints = any(e[2] for e in self.entries)
        bottom = HINT_Y - 2 if hints else FOOTER_Y - 4
        rows = max(1, (bottom - y0) // ROW)
        if self.cursor < self.top:
            self.top = self.cursor
        if self.cursor >= self.top + rows:
            self.top = self.cursor - rows + 1
        x = T.SAFE_X
        w = 176 if self.icons else T.SAFE_W - 10

        for i in range(self.top, min(len(self.entries), self.top + rows)):
            value, label, _ = self.entries[i]
            y = y0 + (i - self.top) * ROW
            selected = i == self.cursor
            if selected:
                block(surf, (x, y, w, ROW - 1), T.PINK, T.PURPLE)
            color = T.BG if selected else T.FG
            if self.mode == "menu":
                if selected:
                    pygame.draw.polygon(surf, T.BG, [(x + 5, y + 4), (x + 5, y + 12), (x + 9, y + 8)])
            else:
                on = value in self.marked
                box = (x + 4, y + 4, 8, 8)
                pygame.draw.rect(surf, color if selected else T.COMMENT, box, 1)
                if on:
                    pygame.draw.rect(surf, color if selected else T.GREEN, (x + 6, y + 6, 4, 4))
                    if not selected:
                        color = T.GREEN
            text(surf, "text", label, color, x + 16, y - 1)

        # As setas de quando a lista rola.
        ax = x + w + 4
        if self.top > 0:
            pygame.draw.polygon(surf, T.COMMENT, [(ax, y0 + 6), (ax + 6, y0 + 6), (ax + 3, y0 + 2)])
        if self.top + rows < len(self.entries):
            by = y0 + rows * ROW - 4
            pygame.draw.polygon(surf, T.COMMENT, [(ax, by - 4), (ax + 6, by - 4), (ax + 3, by)])

        if self.icons:
            px, size = 208, 96
            block(surf, (px, y0, size, size), T.BG_DEEP, T.LINE)
            pygame.draw.rect(surf, T.PURPLE, (px, y0, size, size), 2)
            img = T.icon(self.entries[self.cursor][0], 4)
            if img:
                surf.blit(img, (px + 16, y0 + 16))

        if hints:
            pygame.draw.rect(surf, T.BG_DEEP, (x, HINT_Y, T.SAFE_W, HINT_H))
            pygame.draw.rect(surf, T.LINE, (x, HINT_Y, T.SAFE_W, HINT_H), 1)
            lines = wrap("text", self.entries[self.cursor][2], T.SAFE_W - 12)[:2]
            for i, line in enumerate(lines):
                text(surf, "text", line, T.CYAN, x + 6, HINT_Y + 2 + i * 15)


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
        frame(surf, ctx, self.title, [("ENTER", "ok"), ("ESC", "back")])
        y = paragraph(surf, self.lines, CONTENT_Y) + 16
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
        accent = T.RED if self.kind == "error" else T.PURPLE
        frame(surf, ctx, self.title, [("ENTER", "ok")], accent)
        y = paragraph(surf, self.lines, CONTENT_Y) + 16
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
        frame(surf, ctx, self.title, [("ENTER", "ok"), ("ESC", "back")])
        y = paragraph(surf, self.lines, CONTENT_Y) + 8
        x = T.SAFE_X
        block(surf, (x, y, T.SAFE_W - 2, 22), T.BG_DEEP, T.LINE)
        pygame.draw.rect(surf, T.PINK, (x, y, T.SAFE_W - 2, 22), 2)
        if self.password:
            # Um quadrado por letra: o "*" da fonte e pequeno demais.
            w = len(self.value) * 9
            for i in range(len(self.value)):
                pygame.draw.rect(surf, T.FG, (x + 8 + i * 9, y + 8, 6, 6))
        else:
            w = text(surf, "text", self.value, T.FG, x + 8, y + 3)
        pygame.draw.rect(surf, T.PINK, (x + 9 + w, y + 5, 6, 12))


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
        x, y = T.SAFE_X, CONTENT_Y
        for label, state in self.steps:
            color = {"done": T.GREEN, "run": T.PINK, "fail": T.RED}.get(state, T.COMMENT)
            if state == "run":
                pygame.draw.polygon(surf, color, [(x + 4, y + 4), (x + 4, y + 12), (x + 8, y + 8)])
            elif state == "todo":
                pygame.draw.rect(surf, color, (x + 3, y + 4, 6, 6), 1)
            else:
                pygame.draw.rect(surf, color, (x + 3, y + 4, 6, 6))
            text(surf, "text", label, T.FG if state == "run" else color, x + 16, y - 1)
            y += ROW
        # A barra em blocos: 24 de 10 pixels, com 2 de espaco.
        y = 164
        full = round(self.pct * 24 / 100)
        for i in range(24):
            pygame.draw.rect(surf, T.PINK if i < full else T.LINE, (x + i * 12, y, 10, 12))
        text(surf, "title", "%d%%" % self.pct, T.PINK, x, y + 20)
        text(surf, "text", self.msg, T.CYAN, x + 44, y + 16)
