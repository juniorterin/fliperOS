#!/usr/bin/env python3
"""Gera config/romclean/flycast-controls.tsv: os controles e os botoes de
cada jogo de Naomi, Naomi 2 e Atomiswave, como o Flycast os conhece.

O XML do MAME da a quase todos esses jogos o painel generico da placa JVS
(joystick de 8 direcoes e 6 botoes), ate aos de volante. O Flycast, que e
quem os roda, tem a tabela de cada um (core/hw/naomi/naomi_roms.cpp e
naomi_roms_input.h, github.com/flyinghead/flycast, GPL-2); o ROM Cleaner a
usa nos filtros de controles e de botoes (config/fliperos-romclean):

    tools/flycast-controls.py [--commit HASH] [--source PASTA]
        [--output config/romclean/flycast-controls.tsv]

Cada linha e "set<TAB>controles<TAB>botoes". Controles: as familias do
fliperos-romclean que os eixos do jogo pedem (paddle e o volante ou o
guidao, pedal, analog) ou lightgun; "-" e o painel de joystick e botoes.
O trackball e o teclado o Flycast liga pelo nome gravado na ROM, nao pelo
set: desses jogos fica o que o XML do MAME diz.
"""
import argparse
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMMIT = '80471d57b02606f53828daa916de6ecc94ca1877'
URL = 'https://raw.githubusercontent.com/flyinghead/flycast/%s/core/hw/naomi/%s'

COMMENT = re.compile(r'//[^\n]*|/\*.*?\*/', re.S)
DESCRIPTOR = re.compile(r'^\s*static\s+InputDescriptors\s+(\w+)\s*=\s*(\w*)', re.M)
BUTTON = re.compile(r'\{\s*(?:NAOMI|AWAVE)_BTN(\d+)_KEY')
AXIS = re.compile(r'\{\s*"([^"]*)"\s*,\s*(?:Full|Half)\b')
RELOAD = re.compile(r'\{\s*(?:NAOMI|AWAVE)_RELOAD_KEY\s*,\s*""\s*\}')
WHEEL = re.compile(r'handle|wheel|steer', re.I)
PEDAL = re.compile(r'accel|brake|pedal|clutch', re.I)


def read_source(name, commit, folder):
    if folder:
        return (Path(folder) / name).read_text(encoding='utf-8', errors='replace')
    with urllib.request.urlopen(URL % (commit, name), timeout=120) as resp:
        return resp.read().decode('utf-8', errors='replace')


def read_descriptors(text):
    """{descritor: (familias, botoes)} do naomi_roms_input.h."""
    text = COMMENT.sub('', text)
    found = list(DESCRIPTOR.finditer(text))
    out = {}
    for index, match in enumerate(found):
        name, macro = match.group(1), match.group(2)
        body = text[match.end():found[index + 1].start() if index + 1 < len(found) else len(text)]
        families = set()
        # INPUT_3_BUTTONS(...), AW_5_BUTTONS(...): joystick e N botoes.
        count = re.search(r'_(\d+)_BUTTONS?$', macro)
        if count:
            buttons = int(count.group(1))
        else:
            buttons = len(set(BUTTON.findall(body)))
            for axis in AXIS.findall(body):
                if axis:
                    families.add('paddle' if WHEEL.search(axis) else 'pedal' if PEDAL.search(axis) else 'analog')
        # A pistola: o descritor de lightgun ou o botao de recarregar dela.
        if 'lightgun' in name or RELOAD.search(body):
            families.add('lightgun')
        out[name] = (families, buttons)
    return out


def read_games(text):
    """[(set, descritor)] da tabela Games do naomi_roms.cpp."""
    text = COMMENT.sub('', text)
    text = text[text.index('Games[]'):]
    games, depth, start, quoted = [], 0, 0, False
    for pos, char in enumerate(text):
        if char == '"':
            quoted = not quoted
        elif quoted:
            continue
        elif char == '{':
            depth += 1
            if depth == 2:
                start = pos
        elif char == '}':
            depth -= 1
            if depth == 1:
                entry = text[start:pos]
                name = re.search(r'"([^"]*)"', entry)
                inputs = re.search(r'&\s*(\w+_inputs)\b', entry)
                if name and inputs:
                    games.append((name.group(1).lower(), inputs.group(1)))
            elif depth == 0:
                break
    return games


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--commit', default=COMMIT)
    parser.add_argument('--source', help='a pasta core/hw/naomi do Flycast ja baixado (o do --commit)')
    parser.add_argument('--output', default=str(ROOT / 'config/romclean/flycast-controls.tsv'))
    args = parser.parse_args()
    descriptors = read_descriptors(read_source('naomi_roms_input.h', args.commit, args.source))
    games = read_games(read_source('naomi_roms.cpp', args.commit, args.source))
    lines = []
    for name, inputs in sorted(set(games)):
        if inputs not in descriptors:
            raise SystemExit('%s: no descriptor %s in naomi_roms_input.h' % (name, inputs))
        families, buttons = descriptors[inputs]
        lines.append('%s\t%s\t%d' % (name, ','.join(sorted(families)) or '-', buttons))
    if not lines:
        raise SystemExit('no games found: has the Flycast table changed?')
    tmp = '%s.%d.tmp' % (args.output, os.getpid())
    with open(tmp, 'w', encoding='utf-8', newline='\n') as f:
        f.write('# flycast\t%s\n' % args.commit)
        f.write('# set\tcontrols\tbuttons\n')
        f.write(''.join(line + '\n' for line in lines))
    os.replace(tmp, args.output)
    print('games=%d' % len(lines))


if __name__ == '__main__':
    main()
