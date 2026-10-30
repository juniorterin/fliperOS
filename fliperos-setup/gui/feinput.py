# Os controles do frontend do FliperOS: o painel (o mapa do Setup >
# Joysticks > Button mapping, /etc/fliperos/buttons.map) e o teclado. Cada
# comando do painel e cada tecla fazem a funcao que o Tab > Frontend options >
# Frontend controls deu a eles (frontend.json controls; sem nada, a de sempre:
# o botao 1 escolhe, o 2 volta...). Tudo vira acoes, com o nome da funcao:
# up, down, left, right, b1 a b6, start, tab; e coin (a ficha, sempre ela),
# esc e delete, e as letras e o apagar quando ha texto sendo digitado.
#
# O mapa tem uma linha por comando: "JOGADOR COMANDO INDICE ELEMENTO NOME",
# com o elemento como o SDL o ve: bN (botao), hN.D (direcional digital,
# D = 1 cima, 2 direita, 4 baixo, 8 esquerda), +aN / -aN (um eixo) ou k:NOME
# (a tecla do MAME de um encoder que se diz teclado). Sem o mapa, um controle
# comum: o direcional, o analogico e os botoes 0 a 5.

import os
import time

MAP = os.environ.get("FLIPEROS_BUTTONS_MAP", "/etc/fliperos/buttons.map")
CONTROLS = ("up", "down", "left", "right", "b1", "b2", "b3", "b4", "b5", "b6", "start", "coin")
# As funcoes do frontend, na ordem da tela do Frontend controls. O nome e a
# acao (b1 escolhe, b2 volta, b3/b6 pagina, b4 favorito, b5 filtros, start o
# modo, tab as opcoes); cada uma tem um comando do painel e uma tecla, ou nada.
FUNCTIONS = ("up", "down", "left", "right", "b1", "b2", "b3", "b6", "b4", "b5", "start", "tab")
# Os comandos do painel que uma funcao pode ter: a ficha fica com as fichas
# do modo comercial.
PAD = CONTROLS[:-1]
# As teclas do MAME de um encoder que se diz teclado, sem k: no mapa: o
# painel e elas (como sempre foi), e nao o teclado.
MAME_KEYS = {"LCONTROL": "b1", "LALT": "b2", "SPACE": "b3", "LSHIFT": "b4", "Z": "b5", "X": "b6",
             "1": "start", "5": "coin"}
# Os nomes do MAME que o pygame chama de outro jeito.
KEY_ALIAS = {"LCONTROL": "left ctrl", "RCONTROL": "right ctrl", "LALT": "left alt", "RALT": "right alt",
             "LSHIFT": "left shift", "RSHIFT": "right shift", "ENTER": "return", "ESC": "escape",
             "DEL": "delete", "INSERT": "insert", "PGUP": "page up", "PGDN": "page down",
             "BACKSPACE": "backspace", "ENTER_PAD": "enter"}
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


def default_binds(pg):
    """O mapa das funcoes de sempre: {funcao: {"pad": comando, "key": tecla do pygame}}."""
    keys = {"up": pg.K_UP, "down": pg.K_DOWN, "left": pg.K_LEFT, "right": pg.K_RIGHT, "b1": pg.K_RETURN,
            "b2": pg.K_ESCAPE, "b3": pg.K_PAGEUP, "b6": pg.K_PAGEDOWN, "b4": pg.K_f, "b5": None,
            "start": pg.K_v, "tab": pg.K_TAB}
    return {f: {"pad": None if f == "tab" else f, "key": keys[f]} for f in FUNCTIONS}


def load_binds(pg, saved):
    """O mapa gravado (frontend.json controls) por cima do de sempre. Um
    comando ou uma tecla em duas funcoes fica so na primeira."""
    binds = default_binds(pg)
    if not isinstance(saved, dict):
        return binds
    for f in FUNCTIONS:
        b = saved.get(f)
        if not isinstance(b, dict):
            continue
        if "pad" in b and (b["pad"] is None or b["pad"] in PAD):
            binds[f]["pad"] = b["pad"]
        if "key" in b and (b["key"] is None or (isinstance(b["key"], int) and not isinstance(b["key"], bool))):
            binds[f]["key"] = b["key"]
    for kind in ("pad", "key"):
        seen = set()
        for f in FUNCTIONS:
            if binds[f][kind] in seen:
                binds[f][kind] = None
            elif binds[f][kind] is not None:
                seen.add(binds[f][kind])
    return binds


def assign(binds, function, kind, value):
    """A funcao passa a ter value (kind "pad": o comando do painel; "key": a
    tecla). Quem o tinha fica com o que ela tinha antes: cada botao e cada
    tecla fazem uma coisa so. O mesmo de agora de novo, ou None, a deixa sem
    nada. Devolve (o novo valor, a funcao que trocou com ela ou None)."""
    old = binds[function][kind]
    if value == old:
        value = None
    other = None
    if value is not None:
        other = next((f for f in FUNCTIONS if f != function and binds[f][kind] == value), None)
        if other:
            binds[other][kind] = old
    binds[function][kind] = value
    return value, other


def pad_name(control):
    """O comando do painel na tela: BUTTON 1 a 6, START, COIN e as direcoes."""
    if control is None:
        return None
    return "BUTTON " + control[1:] if control[0] == "b" and control[1:].isdigit() else control.upper()


def key_name(pg, key):
    """A tecla na tela (RETURN, PAGE UP, LEFT CTRL)."""
    if key is None:
        return None
    try:
        return (pg.key.name(key) or "?").upper()
    except (AttributeError, TypeError, ValueError):
        return "?"


def panel_keyboard(pg, rows):
    """As teclas do painel (um encoder que se diz teclado): {tecla: comando}.
    Os k:NOME do mapa; sem nenhum, as teclas do MAME de cada botao."""
    named = [(c, e[2:]) for c, _, e in rows if e.startswith("k:")]
    if not named:
        named = [(c, n) for n, c in MAME_KEYS.items()]
    keys = {}
    for control, name in named:
        try:
            code = pg.key.key_code(KEY_ALIAS.get(name, name.lower()))
        except (AttributeError, ValueError, TypeError):
            continue
        keys.setdefault(code, control)
    return keys


class Input:
    """Le os eventos do pygame e mantem o que esta apertado agora. poll()
    devolve as acoes apertadas desde a ultima chamada; held(acao) diz ha
    quanto tempo a acao esta segura (None se solta)."""

    def __init__(self, pygame, binds=None):
        self.pg = pygame
        self.rows = read_map() or DEFAULT
        self.sticks = []
        self.down = {}             # acao -> hora em que foi apertada
        self.loose = {}            # acao solta -> quando a soltura vale
        self.sources = {}          # acao -> fontes que a seguram (teclado, botoes)
        self.text = False          # digitando: as teclas viram letras
        # Escolhendo uma tecla (a que fecha o jogo, a de uma funcao): cada
        # tecla vira "key:CODIGO" (o do pygame), e nao a acao dela.
        self.capture = False
        # Escolhendo o comando do painel de uma funcao: cada comando apertado
        # vira "pad:COMANDO", e nao a funcao dele.
        self.capture_pad = False
        self.panel_keys = panel_keyboard(pygame, self.rows)
        self.bind(binds or default_binds(pygame))
        self.open()

    def bind(self, binds):
        """As funcoes de cada comando do painel e de cada tecla (default_binds)."""
        self.binds = binds
        self.pad_fn = {b["pad"]: f for f, b in binds.items() if b["pad"]}
        self.key_fn = {b["key"]: f for f, b in binds.items() if b["key"] is not None}

    def pad_action(self, control):
        return "coin" if control == "coin" else self.pad_fn.get(control)

    def pad_press(self, control, source, out):
        """Um comando do painel: o estado dele (os botoes do atalho que fecha o
        jogo sao os do painel) e a funcao dele."""
        self.press("pad:" + control, source, out if self.capture_pad else [])
        action = self.pad_action(control)
        if action and not self.capture_pad:
            self.press(action, source, out)

    def pad_release(self, control, source):
        self.release("pad:" + control, source)
        action = self.pad_action(control)
        if action:
            self.release(action, source)

    def pad_held(self):
        """Os comandos do painel segurados agora."""
        return {c for c in CONTROLS if self.held("pad:" + c) is not None}

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
                control = self.panel_keys.get(ev.key)
                if control:
                    self.pad_press(control, ("k", ev.key), out)
                elif self.key_fn.get(ev.key):
                    self.press(self.key_fn[ev.key], ("k", ev.key), out)
                if not self.text:
                    # O Esc de um teclado de verdade, alem da funcao dele: no
                    # modo comercial so ele (o operador) fecha o frontend. O
                    # Delete apaga (o atalho, a tecla de uma funcao).
                    if ev.key == pg.K_ESCAPE:
                        out.append("esc")
                    elif ev.key == pg.K_DELETE:
                        out.append("delete")
            elif ev.type == pg.KEYUP:
                control = self.panel_keys.get(ev.key)
                if control:
                    self.pad_release(control, ("k", ev.key))
                elif self.key_fn.get(ev.key):
                    self.release(self.key_fn[ev.key], ("k", ev.key))
            elif ev.type == pg.JOYBUTTONDOWN:
                for c in self.match("b%d" % ev.button, self.index(ev)):
                    self.pad_press(c, ("b", ev.joy, ev.button), out)
            elif ev.type == pg.JOYBUTTONUP:
                for c in self.match("b%d" % ev.button, self.index(ev)):
                    self.pad_release(c, ("b", ev.joy, ev.button))
            elif ev.type == pg.JOYHATMOTION:
                x, y = ev.value
                bits = (1 if y > 0 else 0) | (4 if y < 0 else 0) | (2 if x > 0 else 0) | (8 if x < 0 else 0)
                joy = self.index(ev)
                for d in (1, 2, 4, 8):
                    for c in self.match("h%d.%d" % (ev.hat, d), joy):
                        if bits & d:
                            self.pad_press(c, ("h", joy, ev.hat, d), out)
                        else:
                            self.pad_release(c, ("h", joy, ev.hat, d))
            elif ev.type == pg.JOYAXISMOTION:
                joy = self.index(ev)
                for sign, on in (("+", ev.value > AXIS_ON), ("-", ev.value < -AXIS_ON)):
                    for c in self.match("%sa%d" % (sign, ev.axis), joy):
                        if on:
                            self.pad_press(c, ("a", joy, ev.axis, sign), out)
                        else:
                            self.pad_release(c, ("a", joy, ev.axis, sign))
            elif ev.type in (getattr(pg, "JOYDEVICEADDED", -1), getattr(pg, "JOYDEVICEREMOVED", -2)):
                self.open()
        return out

    def held(self, action):
        t = self.down.get(action)
        return None if t is None else time.monotonic() - t
