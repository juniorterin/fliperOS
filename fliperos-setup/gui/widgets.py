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


import time

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


def frame(surf, ctx, title, keys, error=False, score=False):
    """O letreiro com o titulo, a linha de placar e a legenda das teclas,
    numa tela transparente (o fundo animado fica por baixo). O placar
    (score) so aparece nos menus principais."""
    surf.fill((0, 0, 0, 0))
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
        # Cada um com o icone na frente: a rede e o disco.
        surf.blit(T.small_icon("net"), (T.SAFE_X, 32))
        w = text(surf, "NET", T.RED, T.SAFE_X + 12, 32) + 12
        text(surf, ip, T.FG, T.SAFE_X + w + 8, 32)
        if used:
            w = text(surf, used, T.FG, right, 32, right=True)
            w += text(surf, "DISK", T.RED, right - w - 8, 32, right=True) + 8
            surf.blit(T.small_icon("disk"), (right - w - 12, 32))

    total = sum(width(k) + 8 + width(a) for k, a in keys) + 16 * (len(keys) - 1)
    x = (T.WIDTH - total) // 2
    for key, action in keys:
        x += text(surf, key, T.CYAN, x, FOOTER_Y) + 8
        x += text(surf, action, T.COMMENT, x, FOOTER_Y) + 16


def flow(lines, color=T.FG):
    """As linhas prontas para desenhar: (texto, cor), com as longas
    quebradas. Uma linha pode ser um texto (com quebras de linha dentro) ou
    um par (texto, cor)."""
    out = []
    for line in lines:
        line, c = line if isinstance(line, tuple) else (line, color)
        for piece in line.split("\n"):
            out += [(part, c) for part in wrap(piece, T.SAFE_W)] if piece.strip() else [("", c)]
    return out


def paragraph(surf, lines, y, color=T.FG, bottom=None):
    """Desenha as linhas centradas (quebrando as longas) e devolve o y
    seguinte. Com bottom, o texto que nao cabe ate ali aperta as linhas e,
    se ainda assim nao couber, e cortado."""
    parts = flow(lines, color)
    pitch = 12
    if bottom is not None and len(parts) * pitch > bottom - y:
        pitch = 10
        parts = parts[:max(1, (bottom - y) // pitch)]
    for part, c in parts:
        centered(surf, part, c, y)
        y += pitch
    return y


def body(surf, lines, button_h=20):
    """O texto de uma pergunta ou de um aviso: comeca mais embaixo quando e
    curto. Devolve o y do botao."""
    count = len(flow(lines))
    y = paragraph(surf, lines, 80 if count <= 5 else 40, bottom=FOOTER_Y - 12 - button_h - 8)
    return min(y + 12, FOOTER_Y - 12 - button_h)


class Menu:
    """ui_menu / ui_menu_hints, ui_radio (mode="radio") e ui_checklist
    (mode="check"). entries: (valor, rotulo[, dica]). O menu simples e um
    carrossel: o icone de cada item vem de tiles (valor -> funcao que o
    desenha), de theme.ICONS (pelo valor) ou, sem nenhum, e a inicial."""

    def __init__(self, title, entries, default=None, text="", mode="menu", marked=(), tiles=None, vertical=False):
        self.title = title
        self.text = text
        self.mode = mode
        # UI_STYLE=list: a lista vertical em texto, mesmo curta (as pastas).
        self.vertical = vertical
        self.tiles = tiles or {}
        self.entries = [(e[0], e[1], e[2] if len(e) > 2 else "") for e in entries]
        self.marked = set(marked)
        self.cursor = 0
        self.top = 0
        # A transicao do carrossel: (inicio, lado) enquanto os icones deslizam.
        self.slide = None
        for i, e in enumerate(self.entries):
            if e[0] == default:
                self.cursor = i

    def key(self, k):
        n = len(self.entries)
        if self.carousel():
            k = {"left": "up", "right": "down"}.get(k, k)
        if k in ("a", "A") and self.mode == "check":
            # Marca todas ou, com todas marcadas, nenhuma.
            values = {e[0] for e in self.entries}
            self.marked = set() if self.marked >= values else values
        elif k == "up":
            self.cursor = (self.cursor - 1) % n
            self.slide = (time.monotonic(), -1)
        elif k == "down":
            self.cursor = (self.cursor + 1) % n
            self.slide = (time.monotonic(), 1)
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

    def notes(self):
        """As linhas do texto do menu que ficam em cima do carrossel: um
        status de varias linhas ou, quando os itens tem dica, qualquer texto.
        Sem dicas, um texto curto vai no lugar da dica."""
        if not self.text:
            return []
        lines = flow([self.text])
        if any(e[2] for e in self.entries) or len(lines) > 3:
            return lines
        return []

    def tick(self):
        """Redesenhar enquanto o carrossel desliza."""
        return "redraw" if self.slide else None

    def carousel(self):
        """O menu cabe no carrossel? Uma lista longa (pastas, redes) ou um
        texto grande (uma tabela) ficam melhor na lista, e as pastas sempre."""
        return (not self.vertical and self.mode == "menu" and len(self.entries) <= 12
                and len(self.notes()) <= 5)

    def draw(self, surf, ctx):
        if self.carousel():
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
        if not img and not (value.isdigit() and value in label):
            # Sem icone com o nome: o do tipo do item, ou o do assunto do menu.
            img = T.icon(T.guess(self.title, value, label), scale)
        if not img:
            img = big((value if len(value) <= 2 else label[:1]).upper(), scale, MARQUEE)
        surf.blit(img, (x + (size - img.get_width()) // 2, y + (size - img.get_height()) // 2))

    def draw_carousel(self, surf, ctx):
        frame(surf, ctx, self.title, [("< >", "SELECT"), ("ENTER", "OK"), ("ESC", "BACK")],
              score=self.title.startswith("FliperOS"))
        n = len(self.entries)
        notes = self.notes()
        # Com mais de uma linha de texto em cima, o carrossel encolhe: o
        # icone do meio passa de 64 para 48 pixels.
        scale = 4 if len(notes) <= 1 else 3
        size = 16 * scale + 8
        top = 48 if len(notes) <= 1 else 36 + len(notes) * 10
        for i, (line, _) in enumerate(notes):
            centered(surf, line, T.PINK, 34 + i * 10)

        # A transicao: a fila de icones desliza ate o novo item parar sob a
        # moldura, em 0,16 s, freando no fim.
        dx = 0
        if self.slide:
            p = (time.monotonic() - self.slide[0]) / 0.16
            if p < 1:
                dx = round(self.slide[1] * 64 * (1 - p) ** 2)
            else:
                self.slide = None
        mid = top + size // 2
        shade = pygame.Surface((40, 40), pygame.SRCALPHA)
        shade.fill(T.SPACE + (130,))
        # Os vizinhos deslizam so dentro da margem de overscan.
        surf.set_clip((T.SAFE_X, 0, T.SAFE_W, T.HEIGHT))
        for off, cx in ((-2, 36), (2, 284), (-1, 92), (1, 228)):
            # Com poucos itens, cada um aparece uma vez so (os da direita
            # primeiro).
            if n < abs(off) * 2 + (1 if off < 0 else 0):
                continue
            entry = self.entries[(self.cursor + off) % n]
            cx += dx
            pygame.draw.rect(surf, T.BG_DEEP, (cx - 20, mid - 20, 40, 40))
            self.tile(surf, entry, cx - 16, mid - 16, 2)
            surf.blit(shade, (cx - 20, mid - 20))
            pygame.draw.rect(surf, T.LINE, (cx - 20, mid - 20, 40, 40), 1)
        surf.set_clip(None)
        left = (T.WIDTH - size) // 2
        block(surf, (left, top, size, size), T.BG_DEEP, T.PURPLE)
        # O icone que chega aparece so dentro da moldura.
        surf.set_clip((left + 2, top + 2, size - 4, size - 4))
        self.tile(surf, self.entries[self.cursor], left + 4 + dx, top + 4, scale)
        surf.set_clip(None)
        pygame.draw.rect(surf, T.PINK, (left, top, size, size), 2)

        y = top + size + 12
        label, hint = self.entries[self.cursor][1], self.entries[self.cursor][2]
        if not hint and ": " in label:
            # "Filter: Arcade classics": o nome grande e o valor na dica.
            label, hint = label.split(": ", 1)
        label = label.upper()
        if width(label) * 2 <= T.SAFE_W:
            name = big(label, 2, LABEL)
            x = (T.WIDTH - name.get_width()) // 2
            surf.blit(big(label, 2, (0x80, 0x30, 0x60)), (x + 2, y + 2))
            surf.blit(name, (x, y))
        else:
            # Um rotulo longo: letra pequena, em ate duas linhas.
            parts = wrap(label, T.SAFE_W)[:2]
            for i, part in enumerate(parts):
                centered(surf, part, T.YELLOW, y + 4 - 5 * (len(parts) - 1) + i * 10)
        hint = hint or ("" if notes else self.text)
        y += 26 if scale == 4 else 22
        for i, line in enumerate(wrap(hint, T.SAFE_W)[:3]):
            if y + i * 11 <= FOOTER_Y - 12:
                centered(surf, line, T.CYAN, y + i * 11)

        if scale == 4:
            for i in range(n):
                color = T.PINK if i == self.cursor else T.LINE
                pygame.draw.rect(surf, color, (T.WIDTH // 2 - n * 5 + 2 + i * 10, 200, 6, 6))
        if self.title == "FliperOS" and ctx.get("version"):
            text(surf, "V" + ctx["version"], T.LINE, T.SAFE_X + T.SAFE_W, 199, right=True)

    def draw_list(self, surf, ctx):
        keys = [("ENTER", "OK"), ("ESC", "BACK")]
        if self.mode == "check":
            keys.insert(0, ("SPACE", "MARK"))
        frame(surf, ctx, self.title, keys)
        y0 = CONTENT_Y
        hints = any(e[2] for e in self.entries)
        bottom = HINT_Y - 6 if hints else FOOTER_Y - 8
        if not hints and any(width(e[1]) > T.SAFE_W - 46 for e in self.entries):
            # Ha rotulos cortados: sobra espaco para o do cursor, inteiro.
            bottom -= 24
        if self.text:
            # O texto deixa pelo menos tres linhas para a lista.
            y0 = paragraph(surf, [self.text], y0, bottom=bottom - 3 * ROW - 4) + 4
        rows = max(1, (bottom - y0) // ROW)
        if self.cursor < self.top:
            self.top = self.cursor
        if self.cursor >= self.top + rows:
            self.top = self.cursor - rows + 1
        x = T.SAFE_X + 8
        w = T.SAFE_W - 24
        full = ""

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
            # O rotulo que nao cabe e cortado; o do cursor aparece inteiro
            # embaixo, no lugar da dica.
            if width(label) > w - 22:
                if selected:
                    full = label
                while width(label + "..") > w - 22:
                    label = label[:-1]
                label += ".."
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
        elif full:
            for i, line in enumerate(wrap(full, T.SAFE_W)[:2]):
                centered(surf, line, T.CYAN, bottom + 6 + i * 10)


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
        w = max(80, max(width(label) for label in self.labels) + 16)
        if 2 * w + 16 <= T.SAFE_W:
            y = body(surf, self.lines)
            button(surf, self.labels[0], T.WIDTH // 2 - w // 2 - 8, y, self.choice == 0, w)
            button(surf, self.labels[1], T.WIDTH // 2 + w // 2 + 8, y, self.choice == 1, w)
        else:
            # Rotulos longos: um botao embaixo do outro.
            y = body(surf, self.lines, 46)
            w = min(w, T.SAFE_W)
            button(surf, self.labels[0], T.WIDTH // 2, y, self.choice == 0, w)
            button(surf, self.labels[1], T.WIDTH // 2, y + 26, self.choice == 1, w)


class Message:
    """ui_msg (espera o Enter) e, com kind="error", o aviso de falha. Com
    wait=False e o ui_info: so o texto, sem botao (um "aguarde...")."""

    def __init__(self, title, lines, kind="info", wait=True):
        self.title = title
        self.lines = lines
        self.kind = kind
        self.wait = wait

    def key(self, k):
        if k in ("enter", "esc"):
            return ("back", None)
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ENTER", "OK")] if self.wait else [], self.kind == "error")
        y = body(surf, self.lines)
        if self.wait:
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
        # O tempo anda sozinho: um quadrado a menos por segundo (tick).
        self.start = time.monotonic()

    def key(self, k):
        return ("back", None) if k == "esc" else None

    def tick(self):
        left = max(0, self.seconds - int(time.monotonic() - self.start))
        if left != self.left:
            self.left = left
            return "redraw"
        return None

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

    def __init__(self, title, count, order=(), default=False):
        self.title = title
        self.count = count
        self.order = list(order)
        self.cursor = next(p for p in range(6) if p + 1 not in self.order)
        # default: Espaco, no primeiro botao, escolhe o layout padrao.
        self.default = default

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
        elif k == "space" and not self.order and self.default:
            return ("select", "default")
        elif k == "enter" and self.cursor + 1 not in self.order:
            return ("select", self.cursor + 1)
        self.cursor = row * 3 + col
        return None

    def draw(self, surf, ctx):
        keys = [("ARROWS", "MOVE"), ("ENTER", "OK"), ("ESC", "BACK")]
        if self.default and not self.order:
            keys = [("ARROWS", "MOVE"), ("ENTER", "OK"), ("SPACE", "DEFAULT")]
        frame(surf, ctx, self.title, keys)
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
            if total:
                text(surf, "%d PEERS" % peers, T.COMMENT, x + w + 8, y)
                w = text(surf, total, T.FG, right, y, right=True)
                w += text(surf, "OF", T.COMMENT, right - w - 8, y, right=True) + 8
                text(surf, done, T.GREEN, right - w - 8, y, right=True)
            else:
                # Sem tamanho: o estado ("DONE", "NOT STARTED").
                text(surf, done, T.GREEN if frac else T.COMMENT, right, y, right=True)
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

    def __init__(self, title, items, cursor=0, games="", size="", note="", score=""):
        self.title = title
        self.items = items
        self.cursor = cursor
        self.games, self.size = games, size
        self.note = note
        self.top = 0
        # score: o arquivo que a contagem do Setup escreve (games=, bytes=);
        # ate ele aparecer, o placar diz que esta contando.
        self.score = score
        self.checked = 0
        if score and not games:
            self.games, self.size = "...", "..."

    def tick(self):
        if not self.score or time.monotonic() - self.checked < 0.5:
            return None
        self.checked = time.monotonic()
        try:
            with open(self.score, encoding="utf-8") as f:
                values = dict(line.strip().split("=", 1) for line in f if "=" in line)
        except OSError:
            return None
        self.score = ""
        games, size = values.get("games", ""), values.get("bytes", "")
        if not games.isdigit():
            self.games = self.size = ""
            return "redraw"
        self.games = "{:,}".format(int(games))
        n = int(size) if size.isdigit() else 0
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1000 or unit == "TB":
                break
            n /= 1000
        self.size = ("%d %s" % (n, unit)) if unit == "B" else ("%.1f %s" % (n, unit))
        return "redraw"

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
        x, right = T.SAFE_X, T.SAFE_X + T.SAFE_W
        row = self.cursor // self.COLS
        self.top = min(max(self.top, row - self.ROWS + 1), row)
        rows = (len(self.items) + self.COLS - 1) // self.COLS
        if self.games:
            # O placar: quantos jogos passam no filtro e quanto ocupam.
            w = text(surf, "GAMES", T.RED, x, 34)
            text(surf, self.games, T.FG, x + w + 8, 34)
            w = text(surf, self.size, T.FG, right, 34, right=True)
            text(surf, "SIZE", T.RED, right - w - 8, 34, right=True)
        elif self.note:
            # Sem o placar, a linha do que esta sendo filtrado (so o comeco).
            note = self.note.split(". ")[0]
            while width(note) > T.SAFE_W - 8 * (rows + 1):
                note = note[:-1]
            text(surf, note, T.COMMENT, x, 34)
        # Uma marca por linha de azulejos: onde o cursor esta no painel.
        for r in range(rows):
            color = T.PINK if r == row else T.COMMENT if self.top <= r < self.top + self.ROWS else T.LINE
            px = T.WIDTH // 2 - rows * 3 + r * 6 if self.games else right - (rows - r) * 6
            pygame.draw.rect(surf, color, (px, 36, 4, 4))

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


class Grid:
    """ui_grid: uma tabela de marcar, uma marca por linha (os servicos em
    Boot, After boot ou Off). rows: (chave, rotulo, coluna marcada, ajuda,
    valores permitidos separados por virgula, ou nada para todos); columns:
    (valor, rotulo). As setas de cima e de baixo andam pelas linhas (a lista
    rola quando nao cabe), as dos lados (ou Espaco) mudam a marca entre as
    colunas que a linha aceita; Enter grava tudo. ask: marcar essa coluna
    numa linha devolve ("ask", chave e marcas, uma linha cada) na hora.
    live: toda mudanca devolve assim (quem chamou grava na hora), e Enter so
    sai."""

    PITCH = 12

    def __init__(self, title, text, columns, rows, ask="", cursor="", live=False):
        self.live = live
        self.title = title
        self.text = text
        self.columns = columns
        values = [c[0] for c in columns]
        everything = list(range(len(values)))
        self.rows = [(row[0], row[1], row[3]) for row in rows]
        self.allowed = []
        self.state = []
        for row in rows:
            allowed = [values.index(v) for v in (row[4] if len(row) > 4 else "").split(",") if v in values]
            allowed = allowed or everything
            self.allowed.append(allowed)
            state = values.index(row[2]) if row[2] in values else allowed[0]
            self.state.append(state if state in allowed else allowed[0])
        keys = [row[0] for row in rows]
        self.cursor = keys.index(cursor) if cursor in keys else 0
        self.ask = values.index(ask) if ask in values else -1
        self.top = 0

    def marks(self):
        return ",".join("%s=%s" % (row[0], self.columns[s][0]) for row, s in zip(self.rows, self.state))

    def move(self, step):
        allowed = self.allowed[self.cursor]
        i = allowed.index(self.state[self.cursor])
        before = self.state[self.cursor]
        self.state[self.cursor] = allowed[(i + step) % len(allowed)]
        if self.live and self.state[self.cursor] != before or self.state[self.cursor] == self.ask:
            return ("ask", self.rows[self.cursor][0] + "\n" + self.marks())
        return None

    def key(self, k):
        if k == "up":
            self.cursor = max(0, self.cursor - 1)
        elif k == "down":
            self.cursor = min(len(self.rows) - 1, self.cursor + 1)
        elif k == "left":
            return self.move(-1)
        elif k in ("right", "space"):
            return self.move(1)
        elif k == "esc":
            return ("back", None)
        elif k == "enter":
            return ("back", None) if self.live else ("select", self.marks())
        return None

    def draw(self, surf, ctx):
        if self.live:
            frame(surf, ctx, self.title, [("< >", "MARK, SAVED"), ("ESC", "BACK")])
        else:
            frame(surf, ctx, self.title, [("< >", "MARK"), ("ENTER", "SAVE"), ("ESC", "BACK")])
        # A coluna dos nomes e, a direita, uma coluna por estado.
        col_w = 52
        x0 = T.SAFE_X + T.SAFE_W - col_w * len(self.columns)
        y = CONTENT_Y
        if self.text:
            for line in wrap(self.text, T.SAFE_W)[:2]:
                centered(surf, line, T.COMMENT, y)
                y += 11
            y += 4
        for i, (_, label) in enumerate(self.columns):
            for j, part in enumerate(wrap(label.upper(), col_w - 4)[:2]):
                cx = x0 + i * col_w + col_w // 2
                text(surf, part, T.CYAN, cx - width(part) // 2, y + j * 9)
        y += 22
        room = HINT_Y - 6 - y
        pitch = min(18, room // max(1, len(self.rows)))
        shown = len(self.rows)
        if pitch < self.PITCH:
            # Nao cabe: a lista rola, com a linha escolhida sempre a vista.
            pitch = self.PITCH
            shown = max(1, room // pitch)
            self.top = min(max(self.top, self.cursor - shown + 1), self.cursor)
            if self.top > 0:
                text(surf, "^", T.COMMENT, T.SAFE_X - 12, y + 1)
            if self.top + shown < len(self.rows):
                text(surf, "v", T.COMMENT, T.SAFE_X - 12, y + (shown - 1) * pitch + 1)
        else:
            self.top = 0
        for r in range(self.top, min(len(self.rows), self.top + shown)):
            label = self.rows[r][1]
            on = r == self.cursor
            if on:
                block(surf, (T.SAFE_X - 4, y - 3, T.SAFE_W + 8, pitch - 2), T.BG_DEEP, T.PURPLE)
                pygame.draw.rect(surf, T.PINK, (T.SAFE_X - 4, y - 3, T.SAFE_W + 8, pitch - 2), 1)
            name = label.upper()
            while name and width(name) > x0 - T.SAFE_X - 6:
                name = name[:-1]
            text(surf, name, T.FG if on else T.COMMENT, T.SAFE_X, y + 1)
            for c in range(len(self.columns)):
                cx = x0 + c * col_w + col_w // 2
                box = (cx - 5, y, 10, 10)
                if c not in self.allowed[r]:
                    # A coluna que a linha nao tem.
                    pygame.draw.line(surf, T.LINE, (cx - 3, y + 5), (cx + 2, y + 5))
                elif self.state[r] == c:
                    pygame.draw.rect(surf, T.GREEN, box)
                else:
                    pygame.draw.rect(surf, T.PINK if on else T.LINE, box, 1)
            y += pitch
        for i, line in enumerate(wrap(self.rows[self.cursor][2], T.SAFE_W)[:3]):
            centered(surf, line, T.CYAN, HINT_Y + i * 11)


class Timed(Message):
    """ui_timed_confirm: o aviso que espera o Enter por um tempo. tick()
    devolve ("timeout", None) quando o tempo acaba."""

    def __init__(self, title, lines, label, seconds):
        super().__init__(title, lines)
        self.label = label.upper()
        self.deadline = time.monotonic() + seconds
        self.left = seconds

    def key(self, k):
        if k == "enter":
            return ("select", None)
        return ("back", None) if k == "esc" else None

    def tick(self):
        left = max(0, int(self.deadline - time.monotonic() + 0.999))
        if left <= 0:
            return ("timeout", None)
        if left != self.left:
            self.left = left
            return "redraw"
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("ENTER", "OK"), ("ESC", "BACK")])
        y = body(surf, self.lines, 34)
        button(surf, self.label, T.WIDTH // 2, y, True, w=min(T.SAFE_W, width(self.label) + 32))
        centered(surf, "%d s" % self.left, T.COMMENT, y + 26)


class Pager:
    """ui_pager: um texto longo (um log, uma lista) com rolagem. As linhas
    largas demais quebram no meio."""

    ROWS, COLS = 17, 36

    def __init__(self, title, content, start=False):
        self.title = title
        self.lines = []
        for line in content.split("\n"):
            line = line.expandtabs(4)
            self.lines += [line[i:i + self.COLS] for i in range(0, len(line), self.COLS)] or [""]
        self.top = 0 if start else max(0, len(self.lines) - self.ROWS)

    def key(self, k):
        last = max(0, len(self.lines) - self.ROWS)
        step = {"up": -1, "down": 1, "pgup": -self.ROWS, "pgdn": self.ROWS, "left": -self.ROWS,
                "right": self.ROWS}.get(k)
        if step:
            self.top = min(last, max(0, self.top + step))
        elif k in ("enter", "esc"):
            return ("back", None)
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [("UP DOWN", "SCROLL"), ("ENTER", "BACK")])
        pygame.draw.rect(surf, T.BG_DEEP, (T.SAFE_X - 4, 34, T.SAFE_W + 8, self.ROWS * 10 + 6))
        for i, line in enumerate(self.lines[self.top:self.top + self.ROWS]):
            text(surf, line, T.FG, T.SAFE_X, 38 + i * 10)
        if len(self.lines) > self.ROWS:
            # A barra do lado: onde a janela esta no texto.
            h = self.ROWS * 10
            size = max(8, h * self.ROWS // len(self.lines))
            pos = (h - size) * self.top // (len(self.lines) - self.ROWS)
            pygame.draw.rect(surf, T.PINK, (T.SAFE_X + T.SAFE_W + 1, 37 + pos, 2, size))


class Live:
    """A tela de progresso do Setup (screens/progress.sh), redesenhada a
    cada evento: o alvo, a barra, a etapa e as ultimas mensagens."""

    def __init__(self, title, target, pct, step, footer, msgs):
        self.title = title
        self.target = target
        self.pct = pct
        self.step = step
        self.footer = footer
        self.msgs = msgs

    def key(self, k):
        return None

    def draw(self, surf, ctx):
        frame(surf, ctx, self.title, [])
        x = T.SAFE_X
        for i, part in enumerate(wrap(self.target, T.SAFE_W)[:2] if self.target else []):
            centered(surf, part, T.CYAN, 34 + i * 10)
        full = round(self.pct * 24 / 100)
        for i in range(24):
            pygame.draw.rect(surf, RAINBOW[i // 4] if i < full else T.LINE, (x + i * 12, 56, 10, 12))
        name = big("%d%%" % self.pct, 3, T.YELLOW)
        surf.blit(name, ((T.WIDTH - name.get_width()) // 2, 76))
        y = paragraph(surf, [self.step], 110, T.FG, bottom=134) + 6
        for msg in self.msgs[-3:]:
            centered(surf, wrap(msg, T.SAFE_W)[0], T.COMMENT, y)
            y += 12
        parts = wrap(self.footer, T.SAFE_W)[:2]
        for i, part in enumerate(parts):
            centered(surf, part, T.COMMENT, FOOTER_Y - 11 * (len(parts) - 1) + i * 11)


HOURGLASS = """
FFFFFFFFF
.FYYYYYF.
.FYYYYYF.
..FYYYF..
...FYF...
....F....
...F.F...
..F...F..
.F..Y..F.
.FYYYYYF.
FFFFFFFFF
"""
_hourglass = None


def hourglass(surf, t, cx=T.SAFE_X + T.SAFE_W - 8, cy=T.HEIGHT - 20):
    """A ampulheta do canto: o Setup esta trabalhando. A areia escorre
    parada e, a cada segundo, ela vira (gira 180 graus em 0,4 s)."""
    global _hourglass
    if _hourglass is None:
        rows = HOURGLASS.split()
        _hourglass = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch != ".":
                    _hourglass.set_at((x, y), T.ICON_COLORS[ch])
        _hourglass = pygame.transform.scale(_hourglass, (_hourglass.get_width() * 2, _hourglass.get_height() * 2))
    phase = t % 1.0
    angle = 0 if phase < 0.6 else (phase - 0.6) / 0.4 * 180
    img = pygame.transform.rotate(_hourglass, -angle)
    surf.blit(img, (cx - img.get_width() // 2, cy - img.get_height() // 2))
