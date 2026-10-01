"""Controle falso (uinput) para testar o fliperos-padkeys na VM:

    python3 vm-fakepad.py down down a

cria um gamepad, espera o servico acha-lo (ele procura a cada 2 s) e aperta
os botoes em ordem, um por segundo.
"""
import fcntl
import os
import struct
import sys
import time


def _ioc(direction, kind, nr, size):
    return (direction << 30) | (size << 16) | (ord(kind) << 8) | nr


UI_SET_EVBIT = _ioc(1, 'U', 100, 4)
UI_SET_KEYBIT = _ioc(1, 'U', 101, 4)
UI_DEV_SETUP = _ioc(1, 'U', 3, 92)
UI_DEV_CREATE = _ioc(0, 'U', 1, 0)
UI_DEV_DESTROY = _ioc(0, 'U', 2, 0)
BUTTONS = {'a': 0x130, 'b': 0x131, 'start': 0x13b,
           'up': 0x220, 'down': 0x221, 'left': 0x222, 'right': 0x223}
EVENT = struct.Struct('llHHi')

fd = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK)
fcntl.ioctl(fd, UI_SET_EVBIT, 1)
for code in BUTTONS.values():
    fcntl.ioctl(fd, UI_SET_KEYBIT, code)
fcntl.ioctl(fd, UI_DEV_SETUP, struct.pack('HHHH80sI', 0x03, 0x045e, 0x028e, 1, b'FliperOS test pad', 0))
fcntl.ioctl(fd, UI_DEV_CREATE)
time.sleep(4)
for name in sys.argv[1:]:
    for value in (1, 0):
        os.write(fd, EVENT.pack(0, 0, 1, BUTTONS[name], value) + EVENT.pack(0, 0, 0, 0, 0))
        time.sleep(0.15)
    print('apertou', name, flush=True)
    time.sleep(1)
fcntl.ioctl(fd, UI_DEV_DESTROY)
