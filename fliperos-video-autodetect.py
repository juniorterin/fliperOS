#!/usr/bin/env python3
"""Find which analog connector (VGA-*/DVI-I-*) is wired to the CRT.

Ported from GroovyArcade's gatools (video/video.sh test_connector /
test_all_connectors): force each forceable connector on, ask the human to
confirm they see something within a timeout, then move on. Unlike
fliperos-video-check.py this WRITES to /sys/class/drm/*/status; it never
proves a 15 kHz timing by itself, it only narrows down the physical port.
Run fliperos-video-check afterwards (fliperos-install.py already does) to
confirm the resulting mode is actually within range.

Assumes a single GPU; on multi-GPU rigs the console tty may not be mapped to
the card under test, so a "confirmed" prompt might not reach the screen.

Exit codes: 0 = exactly one connector confirmed, 1 = none confirmed,
2 = more than one confirmed (ambiguous, needs a manual choice).
"""
import argparse
import glob
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

FORCEABLE = re.compile(r'^(VGA|DVI-I)-[1-9][0-9]*$')
DEFAULT_TIMEOUT = 6.0
OFF_SETTLE = 2.0


def list_connectors():
    return sorted(Path(p) for p in glob.glob('/sys/class/drm/card[0-9]*-*'))


def connector_name(path):
    # "card0-DVI-I-1" -> "DVI-I-1" (split once: card index never has a dash)
    return path.name.split('-', 1)[1]


def classify(name, edid_size, status):
    """Pure classification, independent of hardware access. For tests."""
    if edid_size > 0 and status == 'connected':
        return 'edid_present'
    if FORCEABLE.match(name):
        return 'forceable'
    return 'skip'


def say(message, voice):
    print(message)
    if voice:
        subprocess.run(['espeak-ng', '-s', '120', message],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_enter(timeout):
    print(f'  Pressione ENTER se a imagem aparecer (aguardando {timeout:.0f}s)...')
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        sys.stdin.readline()
        return True
    return False


def test_connector(path, voice, timeout):
    name = connector_name(path)
    status_file = path / 'status'
    edid_file = path / 'edid'
    say(f'Testando {name}', voice)
    try:
        status_file.write_text('detect')
    except OSError as exc:
        say(f'{name}: nao foi possivel testar ({exc})', voice)
        return 'skip', False
    status = status_file.read_text().strip()
    edid_size = edid_file.stat().st_size if edid_file.exists() else 0
    kind = classify(name, edid_size, status)
    if kind == 'edid_present':
        say(f'{name}: ja tem um monitor digital com EDID valido, pulando', voice)
        return kind, False
    if kind == 'skip':
        return kind, False
    say(f'{name}: ligando', voice)
    status_file.write_text('on')
    confirmed = wait_for_enter(timeout)
    if confirmed:
        say(f'{name}: confirmado', voice)
    else:
        say(f'{name}: nada visto, desligando', voice)
        status_file.write_text('off')
        time.sleep(OFF_SETTLE)
    return kind, confirmed


def autodetect(voice, timeout):
    say('Vamos testar cada saida de video. Aperte ENTER quando ver algo na tela.', voice)
    confirmed, edid_present = [], []
    for path in list_connectors():
        kind, ok = test_connector(path, voice, timeout)
        if ok:
            confirmed.append(connector_name(path))
        elif kind == 'edid_present':
            edid_present.append(connector_name(path))
    say('Teste concluido.', voice)
    return confirmed, edid_present


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--no-voz', action='store_true', help='Desativa narracao por voz (espeak-ng)')
    parser.add_argument('--timeout', type=float, default=DEFAULT_TIMEOUT,
                         help='Segundos de espera por conector (padrao %(default)s)')
    args = parser.parse_args()
    if not 0 < args.timeout <= 60:
        parser.error('Timeout deve estar entre 0 e 60 segundos')
    if os.geteuid() != 0:
        print('Execute com sudo: precisa escrever em /sys/class/drm', file=sys.stderr)
        return 1
    if Path('/.dockerenv').exists() or 'microsoft' in Path('/proc/sys/kernel/osrelease').read_text().lower():
        print('Auto-deteccao de video bloqueada em Docker/WSL; nao ha DRM real.', file=sys.stderr)
        return 1
    voice = not args.no_voz and shutil.which('espeak-ng') is not None
    confirmed, edid_present = autodetect(voice, args.timeout)
    if args.json:
        print(json.dumps({'confirmed': confirmed, 'edid_present': edid_present}, ensure_ascii=False))
    else:
        if confirmed:
            print('Conectores confirmados: ' + ', '.join(confirmed))
        else:
            print('Nenhum conector confirmado.')
        if edid_present:
            print('Conectores com monitor digital (EDID valido, nao testados): ' + ', '.join(edid_present))
        print('Isso identifica a porta, nao confirma 15 kHz. Rode fliperos-video-check em seguida.')
    if len(confirmed) == 1:
        return 0
    return 1 if not confirmed else 2


if __name__ == '__main__':
    raise SystemExit(main())
