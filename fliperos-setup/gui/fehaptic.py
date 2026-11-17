"""Retorno haptico (vibracao) nos controles modernos: o gabinete "responde" ao
que a pessoa faz no menu, nos frontends e ao abrir e fechar um jogo.

Um so lugar para os padroes (PATTERNS) e para as duas maneiras de tocar:

  Pad / pads()   o evdev direto (force feedback FF_RUMBLE), sem dependencias:
                 o fliperos-haptic (abrir/fechar frontend e jogo), o
                 fliperos-padkeys (o menu do Setup).
  Buzzer         o pygame do frontend (Joystick.rumble), no controle que a
                 pessoa esta usando.

So controles de verdade entram: joypad (botao de sul, sem ser mouse) que
anuncia FF_RUMBLE. Volante (tem o centramento), pistola, painel de
arcade e teclado nao vibram. Nada vibra com haptic=off.

haptic= do /etc/fliperos/fliperos.conf (ou FLIPEROS_HAPTIC):
  on (o padrao) | low (metade da forca) | high | off
"""
import fcntl
import glob
import os
import re
import struct
import time

CONF = os.environ.get("FLIPEROS_CONF", "/etc/fliperos/fliperos.conf")

# Cada passo: (atraso ms, duracao ms, forte, fraco). O motor "forte" e o
# grave, de baixa frequencia; o "fraco" e o agudo, que da o clique: um tique
# de menu e so o agudo, um baque e o grave. Valores de 0 a 65535. Todos os
# passos de um padrao sobem de uma vez, cada um com o proprio atraso (o
# kernel guarda ate 16 efeitos por controle: padroes de ate 4 passos).
PATTERNS = {
    # Andar numa lista: um clique seco, quase so o agudo.
    "tick": ((0, 16, 0, 0x3800),),
    # Trocar de sistema/aba: um clique mais cheio.
    "step": ((0, 24, 0x1800, 0x4800),),
    # Aceitar (botao 1, Start): um toque firme.
    "select": ((0, 30, 0x3800, 0x5000),),
    # Voltar (botao 2): dois cliques leves, "desfazendo".
    "back": ((0, 16, 0, 0x3000), (55, 16, 0, 0x2400)),
    # Algo abre (frontend, menu): sobe, de leve a firme.
    "open": ((0, 40, 0x0c00, 0x1800), (50, 40, 0x1c00, 0x2800), (100, 70, 0x3400, 0x3400)),
    # Algo fecha: desce, de firme a leve (o inverso).
    "close": ((0, 60, 0x3000, 0x3000), (80, 40, 0x1c00, 0x2000), (130, 36, 0x0c00, 0x1000)),
    # O jogo comeca: da partida, sobe e termina num baque.
    "start": ((0, 50, 0x1400, 0x2400), (70, 50, 0x2400, 0x3400), (140, 100, 0x6800, 0x4000)),
    # O jogo terminou (fechado de proposito): o baque se desfaz em dois ecos.
    "end": ((0, 80, 0x5000, 0x2800), (120, 50, 0x2800, 0x1400), (210, 40, 0x1000, 0x0800)),
    # O jogo caiu logo depois de abrir, ou o que foi pedido nao da: tres
    # trancos secos.
    "error": ((0, 60, 0x5800, 0x5800), (110, 60, 0x5800, 0x5800), (220, 60, 0x5800, 0x5800)),
    # A ficha: um estalo agudo e um grave curto.
    "coin": ((0, 26, 0, 0x6000), (46, 34, 0x4800, 0x1000)),
}

# Um jogo que fecha antes disto, depois de abrir, provavelmente nao abriu:
# o aviso e o de erro, e nao o de fim.
CRASH_SECONDS = 6.0
# Dois tiques seguidos mais perto que isto viram um so (segurando o direcional
# a lista anda mais rapido do que a mao sente).
MIN_GAP = 0.07

EV_KEY, EV_FF = 0x01, 0x15
FF_RUMBLE, FF_AUTOCENTER = 0x50, 0x61
BTN_LEFT, BTN_SOUTH = 0x110, 0x130
FF_EFFECT_SIZE = 48           # struct ff_effect no x86_64
WHEEL_NAME = re.compile(rb"wheel|racing|driving|steering|formula", re.I)
EVENT = struct.Struct("llHHi")


def level(env=None):
    """A forca pedida (0 = desligado): haptic= do fliperos.conf."""
    value = (env if env is not None else os.environ.get("FLIPEROS_HAPTIC", "")).strip().lower()
    if not value:
        try:
            with open(CONF) as f:
                for line in f:
                    if line.startswith("haptic="):
                        value = line.split("=", 1)[1].strip().lower()
        except OSError:
            pass
    return {"off": 0.0, "0": 0.0, "no": 0.0, "false": 0.0, "low": 0.5, "high": 1.5}.get(value, 1.0)


def steps(event, scale=1.0):
    """Os passos de um padrao na forca de scale (a forca nunca passa do
    maximo); evento desconhecido, nenhum."""
    return [(d, ms, min(0xffff, int(s * scale)), min(0xffff, int(w * scale)))
            for d, ms, s, w in PATTERNS.get(event, ())]


def duration(event):
    return max((d + ms for d, ms, _s, _w in PATTERNS.get(event, ())), default=0) / 1000.0


def classify(program, last):
    """O que e este comando do fliperos-kms-run/x11-run: "frontend" (um
    frontend, que abre e fecha), "game" (um jogo: o ultimo argumento e o
    arquivo dele, ou o set do GroovyMAME/Model 2) ou "" (o menu de um
    emulador, uma ferramenta: sem aviso)."""
    name = os.path.basename(program)
    if name in ("fliperos-frontend", "attractplus", "attract", "emulationstation", "es-de",
                "pegasus", "pegasus-fe") or name.startswith("custom-"):
        return "frontend"
    if name in ("groovymame", "fliperos-model2"):
        return "" if last.startswith("-") else "game"
    return "game" if os.path.isfile(last) else ""


# ── evdev (linux/input.h) ───────────────────────────────────────────

def _ioc(direction, nr, size):
    return (direction << 30) | (size << 16) | (ord("E") << 8) | nr


EVIOCGNAME = _ioc(2, 0x06, 256)
EVIOCSFF = _ioc(1, 0x80, FF_EFFECT_SIZE)
EVIOCRMFF = _ioc(1, 0x81, 4)


def _bits(fd, ev, length):
    buf = bytearray(length)
    try:
        fcntl.ioctl(fd, _ioc(2, 0x20 + ev, length), buf)
    except OSError:
        return set()
    return {i * 8 + b for i, byte in enumerate(buf) for b in range(8) if byte >> b & 1}


def _effect(length, delay, strong, weak):
    """Um struct ff_effect de rumble (id -1: o kernel da um)."""
    head = struct.pack("<HhHHHHH", FF_RUMBLE, -1, 0, 0, 0, length, delay) + b"\0\0"
    return bytearray((head + struct.pack("<HH", strong, weak)).ljust(FF_EFFECT_SIZE, b"\0"))


class Pad:
    """Um controle que vibra, aberto pelo evdev. Levanta OSError/ValueError se
    o aparelho nao e um joypad com rumble."""

    def __init__(self, path):
        self.path = path
        self.ids = []
        self.fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
        self.last = 0.0
        try:
            name = bytearray(256)
            fcntl.ioctl(self.fd, EVIOCGNAME, name)
            self.name = bytes(name).split(b"\0")[0]
            ff = _bits(self.fd, EV_FF, 0x80)
            keys = _bits(self.fd, EV_KEY, 0x300)
            if (FF_RUMBLE not in ff or FF_AUTOCENTER in ff or WHEEL_NAME.search(self.name)
                    or BTN_LEFT in keys or BTN_SOUTH not in keys):
                raise ValueError("nao e um joypad com rumble")
        except (OSError, ValueError):
            os.close(self.fd)
            raise

    def play(self, event, scale=1.0, now=None):
        """Toca o padrao (o que tocava antes para). Devolve False se foi
        engolido pelo intervalo minimo ou nao ha o que tocar."""
        now = time.monotonic() if now is None else now
        plan = steps(event, scale)
        if not plan or now - self.last < MIN_GAP:
            return False
        self.last = now
        self.clear()
        try:
            for delay, ms, strong, weak in plan:
                buf = _effect(ms, delay, strong, weak)
                fcntl.ioctl(self.fd, EVIOCSFF, buf)
                eid = struct.unpack_from("<h", buf, 2)[0]
                self.ids.append(eid)
                os.write(self.fd, EVENT.pack(0, 0, EV_FF, eid, 1))
        except OSError:
            self.clear()
            return False
        return True

    def clear(self):
        for eid in self.ids:
            try:
                fcntl.ioctl(self.fd, EVIOCRMFF, eid)
            except OSError:
                pass
        self.ids = []

    def close(self):
        self.clear()
        try:
            os.close(self.fd)
        except OSError:
            pass


def pads(root="/dev/input"):
    """Todos os controles que vibram agora."""
    found = []
    for path in sorted(glob.glob(os.path.join(root, "event*")), key=lambda p: int(p.rsplit("event", 1)[1])):
        try:
            found.append(Pad(path))
        except (OSError, ValueError):
            continue
    return found


def play_all(event, wait=True):
    """Toca event em todos os controles; com wait, segura os controles
    abertos ate acabar (fechar apaga os efeitos no kernel). Devolve quantos."""
    scale = level()
    if not scale or event not in PATTERNS:
        return 0
    found = pads()
    n = sum(1 for p in found if p.play(event, scale))
    if wait and n:
        time.sleep(duration(event) + 0.05)
    for p in found:
        p.close()
    return n


# ── pygame (o frontend) ─────────────────────────────────────────────

class Buzzer:
    """O haptico do frontend: toca no controle que a pessoa esta usando
    (Joystick.rumble do pygame). Os padroes de mais de um passo andam por
    pump(), chamado a cada quadro. Sem rumble no controle, nao faz nada."""

    def __init__(self):
        self.scale = level()
        self.queue = []            # (hora, joystick, forte, fraco, ms)
        self.last = {}             # joystick -> hora do ultimo toque
        self.pad = None            # o controle que apertou por ultimo (None: teclado)

    def use(self, joystick):
        self.pad = joystick

    def feel(self, event, joystick=None):
        joystick = joystick or self.pad
        if joystick is None or not self.scale:
            return
        now = time.monotonic()
        if now - self.last.get(joystick, 0) < MIN_GAP:
            return
        self.last[joystick] = now
        # Um padrao novo substitui o que ainda esperava na fila deste controle.
        self.queue = [q for q in self.queue if q[1] is not joystick]
        for delay, ms, strong, weak in steps(event, self.scale):
            self.queue.append((now + delay / 1000.0, joystick, strong / 65535.0, weak / 65535.0, ms))
        self.pump()

    def pump(self):
        now = time.monotonic()
        keep = []
        for item in self.queue:
            when, joystick, strong, weak, ms = item
            if when > now:
                keep.append(item)
                continue
            try:
                joystick.rumble(strong, weak, ms)
            except Exception:
                # Sem rumble (ou controle que saiu): este controle fica quieto.
                self.last[joystick] = float("inf")
        self.queue = keep


# O que cada acao do frontend (feinput.FUNCTIONS) faz sentir.
ACTION_EVENT = {"up": "tick", "down": "tick", "left": "step", "right": "step", "b1": "select",
                "start": "select", "b2": "back", "tab": "step", "coin": "coin"}


def action_event(action):
    return ACTION_EVENT.get(action, "tick" if action in ("b3", "b4", "b5", "b6") else "")
