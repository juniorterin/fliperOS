#!/usr/bin/env python3
"""Controles Xbox 360 virtuais (uinput) para gravar o painel web com o
gabinete "jogando": cada controle do Button mapping ganha um aparelho com o
mesmo VID/PID e os mesmos eixos de um xpad de verdade, e os botoes sao
apertados por comandos no stdin. Roda no gabinete, sem dependencias.

    python3 vpad.py [MAPA]          MAPA: /etc/fliperos/buttons.map

Comandos (um por linha; a resposta e "ok"):

    down P CONTROLE[,CONTROLE...]   aperta (P e o jogador, 1 a 4)
    up P CONTROLE[,CONTROLE...]     solta
    tap P CONTROLE[,...] SEGUNDOS   aperta, espera e solta
    release                         solta tudo
    quit                            solta tudo e some

Os CONTROLES sao os do mapa: up down left right b1..b6 start coin. O que cada
um aperta (botao, hat ou eixo) vem do proprio mapa, entao a tecla de moeda e
a que o jogador de verdade usaria.

Os controles de verdade precisam estar soltos do driver (o render.sh gifs-live
faz isso e depois os religa): o SDL conta os controles na ordem em que
aparecem, e o mapa fala em indice 0 e 1. Quando o stdin fecha ou o processo
recebe SIGTERM, tudo e solto e os aparelhos somem.
"""
import fcntl
import os
import signal
import struct
import sys
import time

EV_SYN, EV_KEY, EV_ABS = 0x00, 0x01, 0x03
ABS_HAT0X, ABS_HAT0Y = 0x10, 0x11
# Os botoes de um xpad, na ordem em que o SDL os numera (b0, b1...).
BUTTONS = [0x130, 0x131, 0x133, 0x134, 0x136, 0x137, 0x13a, 0x13b, 0x13c, 0x13d, 0x13e]
# Os eixos: X Y Z RX RY RZ (a0..a5). Z e RZ sao os gatilhos, de 0 a 255.
AXES = {0: (-32768, 32767, 16, 128), 1: (-32768, 32767, 16, 128), 2: (0, 255, 0, 0),
        3: (-32768, 32767, 16, 128), 4: (-32768, 32767, 16, 128), 5: (0, 255, 0, 0)}
HATS = {ABS_HAT0X: (-1, 1, 0, 0), ABS_HAT0Y: (-1, 1, 0, 0)}
# O bit de cada direcao do hat do SDL: 1 cima, 2 direita, 4 baixo, 8 esquerda.
HAT_BITS = {1: (ABS_HAT0Y, -1), 2: (ABS_HAT0X, 1), 4: (ABS_HAT0Y, 1), 8: (ABS_HAT0X, -1)}
EVENT = struct.Struct("llHHi")


def _iow(nr, size):
    return (1 << 30) | (size << 16) | (ord("U") << 8) | nr


UI_DEV_CREATE = (ord("U") << 8) | 1
UI_DEV_DESTROY = (ord("U") << 8) | 2
UI_SET_EVBIT, UI_SET_KEYBIT, UI_SET_ABSBIT = _iow(100, 4), _iow(101, 4), _iow(103, 4)


def read_map(path):
    """{jogador: {controle: (indice do aparelho, elemento)}} do buttons.map."""
    players = {}
    with open(path) as f:
        for line in f:
            part = line.split()
            if len(part) >= 4 and part[0].isdigit() and part[2].isdigit():
                players.setdefault(int(part[0]), {})[part[1]] = (int(part[2]), part[3])
    return players


class Pad:
    def __init__(self, number):
        self.fd = os.open("/dev/uinput", os.O_WRONLY | os.O_NONBLOCK)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_KEY)
        fcntl.ioctl(self.fd, UI_SET_EVBIT, EV_ABS)
        for code in BUTTONS:
            fcntl.ioctl(self.fd, UI_SET_KEYBIT, code)
        lows, highs, fuzz, flat = [0] * 64, [0] * 64, [0] * 64, [0] * 64
        for axis, (low, high, fz, fl) in {**AXES, **HATS}.items():
            fcntl.ioctl(self.fd, UI_SET_ABSBIT, axis)
            lows[axis], highs[axis], fuzz[axis], flat[axis] = low, high, fz, fl
        # struct uinput_user_dev: o nome, o id (USB, Microsoft, Xbox 360), os limites.
        os.write(self.fd, struct.pack("80sHHHHi", b"Microsoft X-Box 360 pad", 0x03, 0x045e, 0x028e, 0x0114, 0)
                 + struct.pack("64i", *highs) + struct.pack("64i", *lows) + struct.pack("64i", *fuzz)
                 + struct.pack("64i", *flat))
        fcntl.ioctl(self.fd, UI_DEV_CREATE)
        self.held = set()          # os elementos apertados
        self.number = number

    def send(self, kind, code, value):
        now = time.time()
        os.write(self.fd, EVENT.pack(int(now), int((now % 1) * 1e6), kind, code, value))

    def sync(self):
        self.send(EV_SYN, 0, 0)

    def set(self, element, on):
        """Aperta ou solta um elemento do mapa (b3, h0.1, +a5, -a0)."""
        if on:
            self.held.add(element)
        else:
            self.held.discard(element)
        if element[0] == "b":
            self.send(EV_KEY, BUTTONS[int(element[1:])], 1 if on else 0)
        elif element[0] == "h":
            bit = int(element.split(".")[1])
            axis, sign = HAT_BITS[bit]
            others = [HAT_BITS[int(e.split(".")[1])][1] for e in self.held if e[0] == "h" and HAT_BITS[int(e.split(".")[1])][0] == axis]
            self.send(EV_ABS, axis, (sign if on else (others[0] if others else 0)))
        else:
            axis = int(element[2:])
            low, high = AXES[axis][0], AXES[axis][1]
            self.send(EV_ABS, axis, (high if element[0] == "+" else low) if on else (low if low == 0 else 0))
        self.sync()

    def release(self):
        for element in list(self.held):
            self.set(element, False)

    def close(self):
        try:
            self.release()
            fcntl.ioctl(self.fd, UI_DEV_DESTROY)
        except OSError:
            pass
        os.close(self.fd)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/etc/fliperos/buttons.map"
    players = read_map(path)
    # Um aparelho por indice do mapa, criados na ordem (o SDL os numera assim).
    pads = {}
    for index in sorted({i for binds in players.values() for i, _ in binds.values()}):
        pads[index] = Pad(index)
        time.sleep(0.4)

    def finish(*_):
        for pad in pads.values():
            pad.close()
        os._exit(0)

    signal.signal(signal.SIGTERM, finish)
    signal.signal(signal.SIGHUP, finish)
    print("ready %d" % len(pads), flush=True)
    for line in sys.stdin:
        word = line.split()
        if not word:
            continue
        if word[0] == "quit":
            break
        if word[0] == "release":
            for pad in pads.values():
                pad.release()
        elif word[0] in ("down", "up", "tap") and len(word) >= 3:
            binds = players.get(int(word[1]), {})
            for control in word[2].split(","):
                if control in binds and binds[control][0] in pads:
                    pads[binds[control][0]].set(binds[control][1], word[0] != "up")
            if word[0] == "tap":
                time.sleep(float(word[3]) if len(word) > 3 else 0.12)
                for control in word[2].split(","):
                    if control in binds and binds[control][0] in pads:
                        pads[binds[control][0]].set(binds[control][1], False)
        print("ok", flush=True)
    finish()


if __name__ == "__main__":
    main()
