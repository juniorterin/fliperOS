# Os controles do frontend do FliperOS: o painel (o mapa do Setup >
# Joysticks > Button mapping, /etc/fliperos/buttons.map) e o teclado (as
# setas e as teclas do MAME de cada botao, para encoders que se dizem
# teclado). Tudo vira acoes: up, down, left, right, b1 a b6, start, coin,
# tab, e as letras e o apagar quando ha texto sendo digitado.
#
# O mapa tem uma linha por comando: "JOGADOR COMANDO INDICE ELEMENTO NOME",
# com o elemento como o SDL o ve: bN (botao), hN.D (direcional digital,
# D = 1 cima, 2 direita, 4 baixo, 8 esquerda) e +aN / -aN (um eixo). Sem o
# mapa, um controle comum: o direcional, o analogico e os botoes 0 a 5.

import os
import time

MAP = os.environ.get("FLIPEROS_BUTTONS_MAP", "/etc/fliperos/buttons.map")
CONTROLS = ("up", "down", "left", "right", "b1", "b2", "b3", "b4", "b5", "b6", "start", "coin")
AXIS_ON = 0.55
# O microswitch de um direcional de fliperama repica ao fechar e ao abrir: o
# contato solta e volta em poucos milissegundos, e cada volta seria mais um
# item (apertar pulava dois, soltar pulava mais um). Uma soltura so vale
# depois desse tempo sem o contato voltar, como no fliperos-padkeys do menu.
DEBOUNCE = 0.06


def read_map(path=MAP):
    """[(controle, indice do joystick, elemento)] de todos os jogadores."""
    rows = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4 and parts[1] in CONTROLS and parts[2].isdigit():
                    rows.append((parts[1], int(parts[2]), parts[3]))
    except OSError:
        pass
    return rows


DEFAULT = [("b1", -1, "b0"), ("b2", -1, "b1"), ("b3", -1, "b2"), ("b4", -1, "b3"), ("b5", -1, "b4"),
           ("b6", -1, "b5"), ("coin", -1, "b6"), ("start", -1, "b7"),
           ("up", -1, "h0.1"), ("down", -1, "h0.4"), ("left", -1, "h0.8"), ("right", -1, "h0.2"),
           ("up", -1, "-a1"), ("down", -1, "+a1"), ("left", -1, "-a0"), ("right", -1, "+a0")]


class Input:
    """Le os eventos do pygame e mantem o que esta apertado agora. poll()
    devolve as acoes apertadas desde a ultima chamada; held(acao) diz ha
    quanto tempo a acao esta segura (None se solta)."""

    def __init__(self, pygame):
        self.pg = pygame
        self.rows = read_map() or DEFAULT
        self.sticks = []
        self.down = {}             # acao -> hora em que foi apertada
        self.loose = {}            # acao solta -> quando a soltura vale
        self.sources = {}          # acao -> fontes que a seguram (teclado, botoes)
        self.text = False          # digitando: as teclas viram letras
        # Escolhendo a tecla que fecha o jogo: cada tecla vira "key:CODIGO"
        # (o do pygame), e nao a acao dela.
        self.capture = False
        k = pygame
        self.keys = {k.K_UP: "up", k.K_DOWN: "down", k.K_LEFT: "left", k.K_RIGHT: "right",
                     k.K_RETURN: "b1", k.K_KP_ENTER: "b1", k.K_LCTRL: "b1",
                     k.K_ESCAPE: "b2", k.K_LALT: "b2",
                     k.K_SPACE: "b3", k.K_PAGEUP: "b3", k.K_LSHIFT: "b4", k.K_f: "b4",
                     k.K_z: "b5", k.K_x: "b6", k.K_PAGEDOWN: "b6",
                     k.K_1: "start", k.K_5: "coin", k.K_TAB: "tab", k.K_v: "start"}
        self.open()

    def open(self):
        pg = self.pg
        pg.joystick.init()
        self.sticks = []
        self.order = {}            # instance_id do SDL -> indice do controle (o do mapa)
        for i in range(pg.joystick.get_count()):
            try:
                j = pg.joystick.Joystick(i)
                j.init()
                self.sticks.append(j)
                self.order[j.get_instance_id()] = i
            except pg.error:
                pass

    def index(self, ev):
        """O indice do controle do evento, na ordem do SDL (a do mapa)."""
        iid = getattr(ev, "instance_id", getattr(ev, "joy", 0))
        return self.order.get(iid, iid)

    def close(self):
        """Solta os controles (o jogo vai abri-los)."""
        self.pg.joystick.quit()
        self.down.clear()
        self.sources.clear()
        self.loose.clear()

    def press(self, action, source, out):
        held = self.sources.setdefault(action, set())
        if not held:
            if self.loose.pop(action, None) is None:
                self.down[action] = time.monotonic()
                out.append(action)
            # Voltou antes de DEBOUNCE: era o repique da chave, o mesmo toque.
        held.add(source)

    def release(self, action, source):
        held = self.sources.get(action)
        if held is None:
            return
        held.discard(source)
        if not held:
            # A soltura so vale depois de DEBOUNCE sem a chave voltar.
            self.loose[action] = time.monotonic() + DEBOUNCE

    def settle(self):
        """As solturas que passaram de DEBOUNCE sem o contato voltar."""
        now = time.monotonic()
        for action, when in list(self.loose.items()):
            if now >= when:
                del self.loose[action]
                self.down.pop(action, None)

    def match(self, element, joy, value=None):
        """As acoes de um elemento do controle joy."""
        return [c for c, j, e in self.rows if e == element and j in (-1, joy)]

    def poll(self):
        pg = self.pg
        out = []
        self.settle()
        for ev in pg.event.get():
            if ev.type == pg.QUIT:
                out.append("quit")
            elif ev.type == pg.KEYDOWN:
                if self.capture:
                    out.append("key:%d" % ev.key)
                    continue
                if self.text:
                    if ev.key == pg.K_BACKSPACE:
                        out.append("backspace")
                        continue
                    if ev.key in (pg.K_RETURN, pg.K_KP_ENTER, pg.K_ESCAPE, pg.K_UP, pg.K_DOWN, pg.K_LEFT,
                                  pg.K_RIGHT):
                        pass
                    elif ev.unicode and ev.unicode.isprintable():
                        out.append("char:" + ev.unicode)
                        continue
                action = self.keys.get(ev.key)
                if action:
                    self.press(action, ("k", ev.key), out)
            elif ev.type == pg.KEYUP:
                action = self.keys.get(ev.key)
                if action:
                    self.release(action, ("k", ev.key))
            elif ev.type == pg.JOYBUTTONDOWN:
                for a in self.match("b%d" % ev.button, self.index(ev)):
                    self.press(a, ("b", ev.joy, ev.button), out)
            elif ev.type == pg.JOYBUTTONUP:
                for a in self.match("b%d" % ev.button, self.index(ev)):
                    self.release(a, ("b", ev.joy, ev.button))
            elif ev.type == pg.JOYHATMOTION:
                x, y = ev.value
                bits = (1 if y > 0 else 0) | (4 if y < 0 else 0) | (2 if x > 0 else 0) | (8 if x < 0 else 0)
                joy = self.index(ev)
                for d in (1, 2, 4, 8):
                    for a in self.match("h%d.%d" % (ev.hat, d), joy):
                        if bits & d:
                            self.press(a, ("h", joy, ev.hat, d), out)
                        else:
                            self.release(a, ("h", joy, ev.hat, d))
            elif ev.type == pg.JOYAXISMOTION:
                joy = self.index(ev)
                for sign, on in (("+", ev.value > AXIS_ON), ("-", ev.value < -AXIS_ON)):
                    for a in self.match("%sa%d" % (sign, ev.axis), joy):
                        if on:
                            self.press(a, ("a", joy, ev.axis, sign), out)
                        else:
                            self.release(a, ("a", joy, ev.axis, sign))
            elif ev.type in (getattr(pg, "JOYDEVICEADDED", -1), getattr(pg, "JOYDEVICEREMOVED", -2)):
                self.open()
        return out

    def held(self, action):
        t = self.down.get(action)
        return None if t is None else time.monotonic() - t
