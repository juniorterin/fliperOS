"""Fala com o monitor de uma VM do tools/vm-test.py que esta rodando:

    python3 tools/vm-monitor.py SOCKET shot NOME     foto do video em /audit/NOME.png
    python3 tools/vm-monitor.py SOCKET key TECLA...  teclas (ret, esc, down, n, ...)

Serve para conduzir a interface tela a tela: fotografar, olhar, decidir.
"""
from pathlib import Path
import importlib.util
import socket
import sys
import time

spec = importlib.util.spec_from_file_location('vmtest', Path(__file__).with_name('vm-test.py'))


def ppm_to_png(ppm, png):
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ppm_to_png(ppm, png)


def send(sock_path, command):
    s = socket.socket(socket.AF_UNIX)
    s.connect(sock_path)
    s.settimeout(2)
    s.sendall(command.encode() + b'\n')
    time.sleep(.5)
    try:
        s.recv(65536)
    except socket.timeout:
        pass
    s.close()


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    sock, action, args = sys.argv[1], sys.argv[2], sys.argv[3:]
    if action == 'shot':
        ppm = Path('/audit') / (args[0] + '.ppm')
        ppm.unlink(missing_ok=True)
        send(sock, 'screendump ' + str(ppm))
        for _ in range(50):
            if ppm.exists() and ppm.stat().st_size:
                break
            time.sleep(.2)
        time.sleep(.5)
        ppm_to_png(ppm, ppm.with_suffix('.png'))
        print(ppm.with_suffix('.png'))
    elif action == 'key':
        for key in args:
            send(sock, 'sendkey ' + key)
            time.sleep(.3)
    return 0


if __name__ == '__main__':
    sys.exit(main())
