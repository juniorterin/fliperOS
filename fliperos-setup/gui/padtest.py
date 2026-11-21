# Setup > Joysticks > Controllers / Arcade panel > Test controller: o estado de um
# controle ao vivo, para ver se cada botao, cada direcao, os analogicos e os gatilhos
# respondem. Roda sozinho (python3 padtest.py --index N ...), como a tela da calibracao
# (wheelscreen.py): o Setup suspende a interface grafica (ui_text), esta tela abre o
# video, le o controle pelo SDL (pygame) e desenha por cima do fundo animado do menu.
#
# Um painel de arcade e um esquema minimalista (LiveArcade): a alavanca (uma bolinha que vai para o
# lado apertado), os botoes do formato escolhido e COIN e START, acesos enquanto apertados. Um joypad e
# um esquema do controle do videogame escolhido no Visual layout (LiveGamepad): so aparece o que ele tem, no
# lugar de cada coisa nele (os gatilhos em barras, os ombros em barras curtas, os sticks com uma
# bolinha que anda e brilha ao apertar o stick, a cruz, os botoes com o nome e a forma dele).
#
# O controle e lido pelo mapa dele (--binds, as linhas "COMANDO ELEMENTO" do fliperos-buttons
# binds), entao um gatilho mapeado num eixo enche a barra e um botao acende, seja qual for o
# aparelho. Para sair: Esc, ou segurar o Start do controle por 1,5 s.

import argparse
import math
import os
import sys
import time

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402

T.set_orientation(os.environ.get("FLIPEROS_GUI_ORIENTATION", "horizontal"))

import background  # noqa: E402
import tiny  # noqa: E402
import widgets as W  # noqa: E402

FPS = 30
EXIT_HOLD = 1.5            # segundos com o Start apertado para sair
REST_TRIGGER = -0.5        # um eixo que repousa abaixo disso e um gatilho (vai de -1 a +1)
PRESSED = 0.5              # a partir daqui um botao, um sentido ou um gatilho conta como apertado
STICK_ON = 0.3             # a partir daqui um analogico conta como movido
TRIGGERS = (("L2", "b7"), ("R2", "b8"))
ARCADE_CONTROLS = ("up", "down", "left", "right") + tuple("b%d" % n for n in range(1, 9)) + ("start", "coin")
# Os joypads que tem desenho proprio (os mesmos do Visual layout, gui/fepads.py: PADS); um nome que
# nao e destes usa o do Xbox.
PAD_KINDS = ("xbox", "playstation", "gamecube", "snes", "nes", "dreamcast", "saturn", "megadrive", "neogeo", "n64")
KEYS = [("HOLD START", "TO EXIT")]
# O rosa apagado (o fundo de um botao aceso) e as cores do PlayStation (os simbolos do controle).
LIT = W.shade(T.PINK, 0.45)
PS_COLORS = {"tri": (0x3C, 0xC8, 0x9C), "sq": (0xF0, 0x96, 0xD0), "cir": (0xF2, 0x5C, 0x6C), "cross": (0x7C, 0xA4, 0xF4)}
# As cores de alguns botoes do controle (o B e o A do N64 e do GameCube, os C do N64).
GC_A, GC_B = (0x2E, 0xBE, 0x8A), (0xE2, 0x3A, 0x44)
N64_A, N64_B, N64_C = (0x34, 0x58, 0xCC), (0x2E, 0x9C, 0x4E), (0xF2, 0xC6, 0x2A)


def parse_binds(text):
    """{comando: elemento} das linhas "COMANDO ELEMENTO" (o que o fliperos-buttons binds imprime)."""
    out = {}
    for line in (text or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out[parts[0]] = parts[1]
    return out


def axis_of(element):
    """(sinal, eixo) de um elemento "+a2" ou "-a1"; None se nao e um eixo."""
    if element and len(element) >= 3 and element[0] in "+-" and element[1] == "a" and element[2:].isdigit():
        return (1 if element[0] == "+" else -1), int(element[2:])
    return None


def button_count(visual):
    """Quantos botoes tem o painel do visual (arcade4: 4, arcade2v: 2; sem visual, 6)."""
    digits = "".join(c for c in visual.replace("arcade", "") if c.isdigit())
    return max(1, min(8, int(digits[0]))) if digits else 6


class Pad:
    """O estado de um controle pelo mapa dele: js e um pygame Joystick (ou algo com as mesmas
    funcoes) e binds o {comando: elemento}. O repouso de cada eixo e lido ao abrir: um gatilho
    que repousa em -1 vale (v + 1) / 2, um analogico no meio vale o proprio valor."""

    def __init__(self, js, binds):
        self.js = js
        self.binds = binds
        self.rest = {}
        self.settle()

    def settle(self):
        js = self.js
        self.rest = {i: js.get_axis(i) for i in range(js.get_numaxes())}

    def value(self, element):
        """0 a 1 de um elemento do mapa: um botao ("b3"), um sentido do direcional ("h0.1") ou
        um lado de um eixo ("+a2": o gatilho, "-a1": o analogico para cima). Tecla: 0."""
        js = self.js
        if not element or element.startswith("k:"):
            return 0.0
        if element[0] == "b" and element[1:].isdigit():
            n = int(element[1:])
            return 1.0 if n < js.get_numbuttons() and js.get_button(n) else 0.0
        if element[0] == "h" and "." in element:
            hat, _, mask = element[1:].partition(".")
            if not (hat.isdigit() and mask.isdigit()) or int(hat) >= js.get_numhats():
                return 0.0
            x, y = js.get_hat(int(hat))
            bits = (1 if y > 0 else 0) | (2 if x > 0 else 0) | (4 if y < 0 else 0) | (8 if x < 0 else 0)
            return 1.0 if bits & int(mask) else 0.0
        axis = axis_of(element)
        if axis:
            sign, n = axis
            if n >= js.get_numaxes():
                return 0.0
            v, rest = js.get_axis(n), self.rest.get(n, 0.0)
            if rest <= REST_TRIGGER:                    # um gatilho: de -1 (solto) a +1 (apertado)
                return max(0.0, min(1.0, (v - rest) / (1 - rest))) if sign > 0 else 0.0
            return max(0.0, min(1.0, v * sign))
        return 0.0

    def pressed(self, control):
        return self.value(self.binds.get(control)) >= PRESSED

    def stick(self, left):
        """(x, y) de um analogico, de -1 a 1 (x para a direita, y para baixo). Pelo mapa
        (lsleft e lsup, rsleft e rsup: o sentido que o eixo toma ao ir para a esquerda e para
        cima); sem o mapa, os eixos 0 e 1 (a esquerda) ou 3 e 4 (a direita) do SDL."""
        names = ("lsleft", "lsup") if left else ("rsleft", "rsup")
        fallback = (0, 1) if left else (3, 4)
        out = []
        for name, default in zip(names, fallback):
            axis = axis_of(self.binds.get(name))
            sign, n = axis if axis else (-1, default)
            if n >= self.js.get_numaxes():
                out.append(0.0)
                continue
            out.append(max(-1.0, min(1.0, self.js.get_axis(n) * (1 if sign < 0 else -1))))
        return out[0], out[1]

    def state(self):
        """Tudo o que a tela desenha, numa vez so."""
        b = self.binds
        return {
            "pressed": {c: self.pressed(c) for c in set(b) | set(ARCADE_CONTROLS)},
            "left": self.stick(True), "right": self.stick(False),
            "triggers": {name: self.value(b.get(control)) for name, control in TRIGGERS},
            # Sair: o Start segurado (todo controle mapeado tem Start; o de voltar dos menus pode nao existir).
            "exit": self.value(b.get("start")),
        }


def triangle(ui, x, y, direction, color, rho=7, width=2):
    """Um triangulo equilatero de verdade, com o centro (o baricentro) em (x, y), apontando para
    a direcao (up, down, left, right): os tres vertices a mesma distancia do centro. width 0 enche."""
    ang = {"up": -90, "right": 0, "down": 90, "left": 180}[direction]
    pts = [(x + rho * math.cos(math.radians(ang + k)), y + rho * math.sin(math.radians(ang + k))) for k in (0, 120, 240)]
    pygame.draw.polygon(ui, color, [(round(px), round(py)) for px, py in pts], width)


def ps_symbol(ui, x, y, kind, on, s=6):
    """Os simbolos do PlayStation sem achatar (circulo redondo, quadrado e triangulo certos), nas
    cores do controle: apagados escurecidos, acesos inteiros."""
    color = PS_COLORS[kind] if on else W.shade(PS_COLORS[kind], 0.55)
    if kind == "tri":
        triangle(ui, x, y + 1, "up", color, rho=s + 1)
    elif kind == "cir":
        pygame.draw.circle(ui, color, (x, y), s, 2)
    elif kind == "cross":
        pygame.draw.line(ui, color, (x - s + 1, y - s + 1), (x + s - 1, y + s - 1), 2)
        pygame.draw.line(ui, color, (x - s + 1, y + s - 1), (x + s - 1, y - s + 1), 2)
    elif kind == "sq":
        pygame.draw.rect(ui, color, (x - s + 1, y - s + 1, 2 * s - 2, 2 * s - 2), 2)


class LiveGamepad:
    """O joypad ao vivo, em esquema minimalista: so aparece o que o controle do videogame escolhido
    tem, nos lugares dele (um metodo layout_NOME para cada um). Tudo acende em rosa enquanto apertado;
    os gatilhos sao barras verticais que enchem com o eixo; os sticks tem uma bolinha que anda com o
    eixo e brilha ao apertar o stick (L3 e R3). Os textos sao so os nomes dos botoes (A B X Y, L, R,
    Z, LT, RT...)."""

    title = "TEST CONTROLLER"

    def __init__(self, kind="xbox"):
        self.kind = kind if kind in PAD_KINDS else "xbox"
        self.pressed = {}
        self.triggers = {"L2": 0.0, "R2": 0.0}
        self.sticks = {"left": (0.0, 0.0), "right": (0.0, 0.0)}
        self.hold = 0.0

    def update(self, state, hold):
        self.pressed = state["pressed"]
        self.triggers = dict(state["triggers"])
        self.sticks = {"left": state["left"], "right": state["right"]}
        self.hold = hold

    # As pecas ------------------------------------------------------------

    def on(self, control):
        return bool(self.pressed.get(control, False))

    def box(self, ui, rect, on, radius=3):
        pygame.draw.rect(ui, LIT if on else T.BG_DEEP, rect, border_radius=radius)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, rect, 1, border_radius=radius)

    def pill(self, ui, cx, cy, w, h, on):
        self.box(ui, (cx - w // 2, cy - h // 2, w, h), on, h // 2)

    def button(self, ui, x, y, r, label, on, ring=None):
        """Um botao redondo com o nome dentro; ring e a cor do contorno do controle (o B do N64...)."""
        pygame.draw.circle(ui, LIT if on else T.BG_DEEP, (x, y), r)
        pygame.draw.circle(ui, T.PINK if on else (ring or T.LINE), (x, y), r, 2 if on or ring else 1)
        if label:
            W.text(ui, label, T.YELLOW if on else T.COMMENT, x - W.width(label) // 2, y - 4)

    def bumper(self, ui, x, y, w, h, on, side, letter):
        """O ombro: uma barra grossa e curta, a ponta de fora redonda e a de dentro reta, com a
        letra dentro."""
        outer = h // 2
        corners = dict(border_top_left_radius=outer if side < 0 else 0, border_bottom_left_radius=outer if side < 0 else 0,
                       border_top_right_radius=outer if side > 0 else 0, border_bottom_right_radius=outer if side > 0 else 0)
        rect = (x, y, w, h)
        pygame.draw.rect(ui, LIT if on else T.BG_DEEP, rect, **corners)
        pygame.draw.rect(ui, T.PINK if on else T.LINE, rect, 2 if on else 1, **corners)
        W.text(ui, letter, T.YELLOW if on else T.COMMENT, x + w // 2 - W.width(letter) // 2, y + 3)

    def bumpers(self, ui, cx, left, right, y=50, left_letter="L", right_letter="R"):
        self.bumper(ui, cx - 104, y, 90, 15, self.on(left), -1, left_letter)
        self.bumper(ui, cx + 14, y, 90, 15, self.on(right), 1, right_letter)

    def trigger(self, ui, label, value, cx, y, w=18, h=78):
        """O gatilho: uma barra vertical grossa que enche de baixo para cima com o eixo (rosa
        quando apertado), e o nome pequeno em cima."""
        on = value >= PRESSED
        tiny.centered(ui, label, T.YELLOW if on else T.COMMENT, cx, y - 10)
        pygame.draw.rect(ui, T.BG_DEEP, (cx - w // 2, y, w, h))
        fill = round(value * (h - 2))
        if fill:
            ui.fill(T.PINK if on else T.CYAN, (cx - w // 2 + 1, y + h - 1 - fill, w - 2, fill))
        pygame.draw.rect(ui, T.PINK if on else T.LINE, (cx - w // 2, y, w, h), 1)

    def triggers_lr(self, ui, cx, left="L", right="R"):
        self.trigger(ui, left, self.triggers["L2"], cx - 134, 58)
        self.trigger(ui, right, self.triggers["R2"], cx + 134, 58)

    def stick(self, ui, cx, cy, r, xy, click):
        """Um stick: o poco redondo e a bolinha que anda com o eixo (rosa quando sai do meio);
        apertar o stick a deixa branca, com o aro rosa e um brilho em volta."""
        if click:
            halo = pygame.Surface((2 * r + 16, 2 * r + 16), pygame.SRCALPHA)
            c = r + 8
            pygame.draw.circle(halo, (255, 255, 255, 40), (c, c), r + 6)
            pygame.draw.circle(halo, (255, 255, 255, 80), (c, c), r + 3)
            ui.blit(halo, (cx - c, cy - c))
        pygame.draw.circle(ui, T.BG_DEEP, (cx, cy), r)
        pygame.draw.circle(ui, T.PINK if click else T.LINE, (cx, cy), r, 2)
        x, y = xy
        px, py = cx + round(x * (r - 6)), cy + round(y * (r - 6))
        moved = max(abs(x), abs(y)) >= STICK_ON
        pygame.draw.circle(ui, W.WHITE if click else T.PINK if moved else T.COMMENT, (px, py), 5)

    def cross(self, ui, cx, cy, size=46):
        """A cruz do direcional, de bracos grossos; cada lado acende em rosa."""
        t = size // 3 + 2
        h = size // 2
        arms = {"up": (cx - t // 2, cy - h, t, h - t // 2 + 1), "down": (cx - t // 2, cy + t // 2, t, h - t // 2),
                "left": (cx - h, cy - t // 2, h - t // 2 + 1, t), "right": (cx + t // 2, cy - t // 2, h - t // 2, t)}
        for direction, rect in arms.items():
            self.box(ui, rect, self.on(direction), 2)
        pygame.draw.rect(ui, T.BG_DEEP, (cx - t // 2 + 1, cy - t // 2 + 1, t - 2, t - 2))
        pygame.draw.circle(ui, T.LINE, (cx, cy), 2)

    def diamond(self, ui, cx, cy, names, d=25, r=12):
        """Os quatro botoes em losango. names: (em cima, embaixo, a esquerda, a direita), cada um
        (controle, nome); o nome e a letra ou, no PlayStation, o simbolo (cross, cir, sq, tri)."""
        for (control, name), (dx, dy) in zip(names, ((0, -d), (0, d), (-d, 0), (d, 0))):
            on = self.on(control)
            x, y = cx + dx, cy + dy
            if name in PS_COLORS:
                pygame.draw.circle(ui, LIT if on else T.BG_DEEP, (x, y), r)
                pygame.draw.circle(ui, T.PINK if on else T.LINE, (x, y), r, 2 if on else 1)
                ps_symbol(ui, x, y, name, on)
            else:
                self.button(ui, x, y, r, name, on)

    def bean(self, ui, cx, cy, radius, start, end, thick, on, label):
        """O X e o Y do GameCube: um feijao (um arco grosso de pontas redondas, carimbando circulos
        ao longo dele) em volta do A, nos angulos do controle."""
        half = thick / 2
        steps = 48
        path = [(cx + radius * math.cos(math.radians(start + (end - start) * i / steps)),
                 cy + radius * math.sin(math.radians(start + (end - start) * i / steps))) for i in range(steps + 1)]
        for px, py in path:
            pygame.draw.circle(ui, T.PINK if on else T.LINE, (round(px), round(py)), round(half))
        for px, py in path:
            pygame.draw.circle(ui, LIT if on else T.BG_DEEP, (round(px), round(py)), round(half) - 1)
        mid = math.radians((start + end) / 2)
        W.text(ui, label, T.YELLOW if on else T.COMMENT, round(cx + radius * math.cos(mid)) - W.width(label) // 2,
               round(cy + radius * math.sin(mid)) - 4)

    # Os controles ---------------------------------------------------------

    def layout_xbox(self, ui, cx):
        """Estilo Xbox: o stick esquerdo na altura do Select e do Start, a cruz embaixo; os botoes
        em losango a direita e o stick direito embaixo; os gatilhos nas laterais."""
        self.triggers_lr(ui, cx, "LT", "RT")
        self.bumpers(ui, cx, "b3", "b6")
        self.stick(ui, cx - 82, 122, 22, self.sticks["left"], self.on("l3"))
        self.cross(ui, cx - 40, 170, 46)
        self.diamond(ui, cx + 84, 116, (("b2", "Y"), ("b4", "A"), ("b1", "X"), ("b5", "B")))
        self.stick(ui, cx + 40, 170, 22, self.sticks["right"], self.on("r3"))
        self.pill(ui, cx - 22, 122, 34, 13, self.on("coin"))
        self.pill(ui, cx + 22, 122, 34, 13, self.on("start"))

    def layout_playstation(self, ui, cx):
        """Simetrico, como o DualShock: a cruz e os botoes em cima e os dois sticks juntos embaixo."""
        self.triggers_lr(ui, cx, "L2", "R2")
        self.bumpers(ui, cx, "b3", "b6", left_letter="L1", right_letter="R1")
        self.cross(ui, cx - 84, 108, 46)
        self.diamond(ui, cx + 84, 108, (("b2", "tri"), ("b4", "cross"), ("b1", "sq"), ("b5", "cir")))
        self.pill(ui, cx - 22, 98, 30, 12, self.on("coin"))
        self.pill(ui, cx + 22, 98, 30, 12, self.on("start"))
        self.stick(ui, cx - 36, 168, 24, self.sticks["left"], self.on("l3"))
        self.stick(ui, cx + 36, 168, 24, self.sticks["right"], self.on("r3"))

    def layout_snes(self, ui, cx):
        self.bumpers(ui, cx, "b3", "b6", y=52)
        self.cross(ui, cx - 80, 124, 54)
        self.diamond(ui, cx + 80, 124, (("b2", "X"), ("b4", "B"), ("b1", "Y"), ("b5", "A")))
        self.pill(ui, cx - 24, 150, 34, 11, self.on("coin"))
        self.pill(ui, cx + 24, 150, 34, 11, self.on("start"))

    def layout_nes(self, ui, cx):
        self.cross(ui, cx - 86, 124, 56)
        self.pill(ui, cx - 24, 150, 34, 11, self.on("coin"))
        self.pill(ui, cx + 24, 150, 34, 11, self.on("start"))
        self.button(ui, cx + 56, 138, 15, "B", self.on("b4"))
        self.button(ui, cx + 96, 138, 15, "A", self.on("b5"))

    def six(self, ui, cx):
        """Os seis botoes do Mega Drive e do Saturn: X Y Z em cima, A B C embaixo."""
        for i, (top, bottom) in enumerate((("X", "A"), ("Y", "B"), ("Z", "C"))):
            x = cx + 40 + i * 32
            self.button(ui, x, 100, 12, top, self.on(("b3", "b2", "b6")[i]))
            self.button(ui, x, 132, 12, bottom, self.on(("b1", "b4", "b5")[i]))

    def layout_megadrive(self, ui, cx):
        self.cross(ui, cx - 86, 124, 56)
        self.pill(ui, cx, 160, 34, 11, self.on("start"))
        self.six(ui, cx)

    def layout_saturn(self, ui, cx):
        self.bumpers(ui, cx, "b7", "b8", y=52)
        self.cross(ui, cx - 86, 124, 56)
        self.pill(ui, cx, 160, 34, 11, self.on("start"))
        self.six(ui, cx)

    def layout_dreamcast(self, ui, cx):
        self.triggers_lr(ui, cx, "L", "R")
        self.stick(ui, cx - 82, 112, 24, self.sticks["left"], self.on("l3"))
        self.cross(ui, cx - 50, 172, 40)
        self.diamond(ui, cx + 84, 112, (("b2", "Y"), ("b4", "A"), ("b1", "X"), ("b5", "B")))
        self.pill(ui, cx, 112, 34, 12, self.on("start"))

    def layout_neogeo(self, ui, cx):
        # O stick do Neo Geo CD e digital: a bolinha vai para o lado do direcional apertado.
        dx = int(self.on("right")) - int(self.on("left"))
        dy = int(self.on("down")) - int(self.on("up"))
        self.stick(ui, cx - 82, 122, 26, (dx, dy), False)
        self.pill(ui, cx - 24, 118, 34, 11, self.on("coin"))
        self.pill(ui, cx + 24, 118, 34, 11, self.on("start"))
        for (x, y), label, control in (((cx + 54, 96), "C", "b1"), ((cx + 90, 90), "D", "b2"),
                                       ((cx + 54, 134), "A", "b4"), ((cx + 90, 128), "B", "b5")):
            self.button(ui, x, y, 13, label, self.on(control))

    def layout_gamecube(self, ui, cx):
        """O A grande no meio, o B pequeno embaixo a esquerda e os feijoes X (direita) e Y (cima) num
        arco de um diametro do A em volta dele; o Z numa barra do tamanho dos ombros; L e R analogicos."""
        self.triggers_lr(ui, cx, "L", "R")
        self.bumper(ui, cx + 14, 50, 90, 15, self.on("b6"), 1, "Z")
        self.stick(ui, cx - 86, 104, 24, self.sticks["left"], self.on("l3"))
        self.cross(ui, cx - 50, 168, 36)
        self.pill(ui, cx, 118, 30, 12, self.on("start"))
        ax, ay, ra = cx + 70, 128, 15
        d = 2 * ra
        on = self.on("b4")
        pygame.draw.circle(ui, LIT if on else T.BG_DEEP, (ax, ay), ra)
        pygame.draw.circle(ui, T.PINK if on else GC_A, (ax, ay), ra, 2)
        W.text(ui, "A", T.YELLOW if on else T.COMMENT, ax - 4, ay - 4)
        self.button(ui, ax - round(0.96 * d), ay + round(0.48 * d), round(0.32 * d), "B", self.on("b1"), GC_B)
        self.bean(ui, ax, ay, d, -130, -82, round(0.36 * d), self.on("b2"), "Y")
        self.bean(ui, ax, ay, d, -40, 10, round(0.36 * d), self.on("b5"), "X")
        self.stick(ui, cx + 30, 176, 16, self.sticks["right"], self.on("r3"))

    def layout_n64(self, ui, cx):
        """A disposicao do controle (as medidas do fepads, em diametros do A): o A azul embaixo a
        direita, o B verde acima e a esquerda dele e os quatro C num losango acima e a direita, com
        triangulos equilateros. Os C (menos o de cima e o da direita, que tem botao) seguem o stick
        direito. L e R em barras, o Z no gatilho da esquerda."""
        self.bumpers(ui, cx, "b3", "b6", y=52)
        self.trigger(ui, "Z", self.triggers["L2"], cx - 134, 58)
        self.cross(ui, cx - 92, 116, 50)
        self.stick(ui, cx - 24, 150, 22, self.sticks["left"], self.on("l3"))
        self.pill(ui, cx - 24, 108, 34, 11, self.on("start"))
        k = 28
        ax, ay = cx + 50, 184
        self.button(ui, ax, ay, 13, "A", self.on("b4"), N64_A)
        self.button(ui, ax - round(0.95 * k), ay - round(0.98 * k), 13, "B", self.on("b1"), N64_B)
        rx, ry = self.sticks["right"]
        c_on = {"up": self.on("b2") or ry <= -PRESSED, "left": rx <= -PRESSED,
                "right": self.on("b5") or rx >= PRESSED, "down": ry >= PRESSED}
        for dx, dy, direction in ((0.94, -2.41, "up"), (0.19, -1.69, "left"), (1.73, -1.65, "right"), (0.98, -0.94, "down")):
            x, y = ax + round(dx * k), ay + round(dy * k)
            on = c_on[direction]
            pygame.draw.circle(ui, LIT if on else T.BG_DEEP, (x, y), 10)
            pygame.draw.circle(ui, T.PINK if on else N64_C, (x, y), 10, 2 if on else 1)
            triangle(ui, x, y, direction, T.YELLOW if on else W.shade(N64_C, 0.7), rho=6, width=0)

    def layout(self, ui, cx):
        getattr(self, "layout_" + self.kind)(ui, cx)

    @W.landscape
    def draw(self, surf, ctx):
        """O esquema do controle escolhido, em 320x240 (em pe, a tela e encolhida pelo landscape)."""
        W.frame(surf, ctx, self.title, KEYS)
        cx = T.WIDTH // 2
        self.layout(surf, cx)
        # Segurar o Start: uma barra fina embaixo enche em vermelho ate sair.
        if self.hold > 0:
            full = round(120 * min(1.0, self.hold / EXIT_HOLD))
            pygame.draw.rect(surf, T.LINE, (cx - 60, 212, 120, 4), 1)
            surf.fill(T.RED, (cx - 59, 213, max(0, full - 2), 2))


class LiveArcade(LiveGamepad):
    """O painel de arcade ao vivo, no mesmo esquema minimalista do joypad: a alavanca a esquerda (uma
    bolinha que vai para o lado apertado), os botoes na posicao do guia do frontend (widgets.shape_geometry)
    com o numero dentro (o MVS, de 4 em linha, com as letras e as cores do Neo Geo) e COIN e START embaixo."""

    def __init__(self, visual):
        super().__init__("xbox")
        self.visual = visual if visual in W.SHAPE_LAYOUT else "arcade6"
        self.buttons = button_count(visual)

    def layout(self, ui, cx):
        import fepads
        buttons, pts, (r, lift), box = W.shape_geometry(self.visual, 1.25)
        dx = int(self.on("right")) - int(self.on("left"))
        dy = int(self.on("down")) - int(self.on("up"))
        self.stick(ui, cx - 84, 112, 30, (dx, dy), False)
        if self.visual in ("arcade6", "arcade8"):
            # Duas fileiras: o espaco de uma fileira para a outra e o mesmo de um botao para o do lado, sem
            # o arco do meio (1 2 3 em cima e 4 5 6 embaixo; no de 8 o 7 e o 8 fecham cada fileira).
            step = round(34 * 1.25)
            cols = 4 if self.visual == "arcade8" else 3
            order = [(c, 0) for c in range(3)] + [(c, 1) for c in range(3)] + ([(3, 0), (3, 1)] if cols == 4 else [])
            pts = {"b%d" % (n + 1): (round((c - (cols - 1) / 2) * step), round((row - 0.5) * step)) for n, (c, row) in enumerate(order)}
            box = (-(cols * step) // 2, -step // 2, (cols * step) // 2, step // 2)
        ox = cx + 62 - (box[0] + box[2]) // 2
        oy = 112 - (box[1] + box[3]) // 2
        neo = {role: (color, glyph) for role, _, _, _, color, glyph, _ in fepads.NEOGEO} if self.visual == "arcade4" else {}
        for n, b in enumerate(buttons):
            x, y = ox + pts[b][0], oy + pts[b][1]
            if neo:
                color, glyph = neo["abcd"[n]]
                self.button(ui, x, y, r, glyph, self.on(b), color)
            else:
                self.button(ui, x, y, r, str(n + 1), self.on(b))
        for side, control, label in ((-1, "coin", "COIN"), (1, "start", "START")):
            on = self.on(control)
            self.pill(ui, cx + side * 24, 176, 34, 12, on)
            tiny.centered(ui, label, T.YELLOW if on else T.COMMENT, cx + side * 24, 186)


class PadTest:
    def __init__(self, visual, name="", player=1, window=True):
        background.set_size(T.WIDTH, T.HEIGHT)
        self.bg = background.pick(os.environ.get("FLIPEROS_GUI_BG") or None)
        self.surf = pygame.Surface((T.WIDTH, T.HEIGHT))
        self.ui = pygame.Surface((T.WIDTH, T.HEIGHT), pygame.SRCALPHA)
        self.visual = visual
        if visual.startswith("pad:"):
            self.live = LiveGamepad(visual[4:])
        else:
            self.live = LiveArcade(visual)
        self.name = name
        self.start = time.monotonic()
        self.fixed_time = None      # os prints: um instante fixo do fundo
        self.window = None
        pygame.font.init()
        if window:
            self.open()

    def open(self):
        T.request_vsync()
        pygame.display.init()
        size, flags = T.MODE, 0
        if os.environ.get("SDL_VIDEODRIVER", "kmsdrm") == "kmsdrm":
            flags = pygame.FULLSCREEN
            modes = pygame.display.list_modes()
            if not isinstance(modes, list) or size not in modes:
                info = pygame.display.Info()
                size = (info.current_w, info.current_h)
        self.window = pygame.display.set_mode(size, flags)
        pygame.mouse.set_visible(False)

    def close(self):
        if self.window is None:
            return
        pygame.display.quit()
        try:
            import drmmaster
            drmmaster.drop()
        except Exception:
            pass
        self.window = None

    def show(self, state, hold):
        frame = T.upright(self.render(state, hold))
        pygame.transform.scale(frame, self.window.get_size(), self.window)
        pygame.display.flip()

    def render(self, state, hold=0.0):
        """O quadro na tela logica: o fundo do Setup e, por cima, a tela ao vivo."""
        t = self.fixed_time if self.fixed_time is not None else time.monotonic() - self.start
        self.ui.fill((0, 0, 0, 0))
        self.live.update(state, hold)
        self.live.draw(self.ui, {"status": ""})
        self.bg.draw(self.surf, t)
        self.surf.blit(self.ui, (0, 0))
        return self.surf


def main(argv=None):
    parser = argparse.ArgumentParser(description="FliperOS controller test")
    parser.add_argument("--index", type=int, required=True, help="the SDL index of the controller")
    parser.add_argument("--visual", default="arcade6", help="arcade6, arcade4... or pad:xbox...")
    parser.add_argument("--binds", default="", help='the "COMMAND ELEMENT" lines of fliperos-buttons binds')
    parser.add_argument("--name", default="")
    parser.add_argument("--player", type=int, default=1)
    args = parser.parse_args(argv)
    pygame.display.init()
    pygame.joystick.init()
    if args.index < 0 or args.index >= pygame.joystick.get_count():
        print("error: no controller %d" % args.index, file=sys.stderr)
        return 1
    js = pygame.joystick.Joystick(args.index)
    js.init()
    for _ in range(3):
        pygame.event.pump()
        time.sleep(0.05)
    pad = Pad(js, parse_binds(args.binds))
    screen = PadTest(args.visual, args.name or js.get_name(), max(1, args.player))
    clock = pygame.time.Clock()
    held = None
    try:
        while True:
            pygame.event.pump()
            for event in pygame.event.get():
                if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                    return 0
            state = pad.state()
            # Segurar o Start do controle por EXIT_HOLD segundos sai.
            if state["exit"] >= PRESSED:
                held = held or time.monotonic()
            else:
                held = None
            hold = time.monotonic() - held if held else 0.0
            if hold >= EXIT_HOLD:
                return 0
            screen.show(state, hold)
            clock.tick(FPS)
    finally:
        screen.close()


if __name__ == "__main__":
    sys.exit(main())
