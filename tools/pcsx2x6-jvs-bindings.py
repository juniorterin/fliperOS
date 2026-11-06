#!/usr/bin/env python3
"""Gera config/pcsx2x6-jvs-bindings: os botoes do arcade do PCSX2x6.

O fork nao espelha o [Pad1]: os botoes dos jogos System 246/256 vem da secao
[JVS] do PCSX2.ini, uma chave por botao (P1_Up, Tekken_LeftPunch_P1...), e sem
ela o jogo nao recebe nada. O direcional, o Start e a ficha de cada jogador
vao no papel do SDL (DPadUp, Start, Back); cada botao do jogo e "button:C:N",
o botao N de um jogo de C botoes, que cai na posicao do painel do Setup >
Joysticks > Button mapping (e do Buttons layout, onde ha): o fliperos-buttons
save grava a secao no PCSX2.ini, e o fliperos-x11-run so a primeira vez, com o
botao N na posicao N.

A lista sai do pcsx2/DEV9/ACJV_Inputs.h do fork; a ordem dos botoes de cada
jogo e a do grupo (o PS2 que o layout padrao usa, GenericInputBinding, so
separa o direcional e o Start dos botoes):

  python3 tools/pcsx2x6-jvs-bindings.py ACJV_Inputs.h config/pcsx2x6-jvs-bindings

Fica de fora o que um painel de botoes nao tem: volante (analogico), tambor,
alavancas do Zoids, o Service e o P*_Button* genericos (o fork ignora os
genericos 2 a 6 e o 1 e o ENTER do teste).
"""
import re
import sys

# O botao do PS2 -> o papel do SDL (os mesmos nomes que o x11-run poe no [Pad1]).
ROLE = {
    'Square': 'FaceWest', 'Triangle': 'FaceNorth', 'Cross': 'FaceSouth', 'Circle': 'FaceEast',
    'L1': 'LeftShoulder', 'R1': 'RightShoulder', 'L2': '+LeftTrigger', 'R2': '+RightTrigger',
    'Start': 'Start', 'Select': 'Back',
    'DPadUp': 'DPadUp', 'DPadDown': 'DPadDown', 'DPadLeft': 'DPadLeft', 'DPadRight': 'DPadRight',
}
ENTRY = re.compile(r'\{\s*"([A-Za-z0-9_]+)"\s*,\s*TRANSLATE_NOOP\([^)]*\)\s*,\s*[^,]+,\s*'
                   r'InputBindingInfo::Type::(\w+)\s*,\s*([^,]+),\s*GenericInputBinding::(\w+)')
GROUP = re.compile(r'\s*static constexpr[^=]*?\b(s_[A-Za-z0-9_]+)\s*(?:\[\])?\s*=')


def groups(text):
    out, name = {}, None
    for line in text.splitlines():
        m = GROUP.match(line)
        if m:
            name = m.group(1)
            out.setdefault(name, [])
            continue
        m = ENTRY.search(line)
        if m and name:
            out[name].append((m.group(1), m.group(4)))
    return out


def rows(text):
    g = groups(text)
    out = []
    # Direcional e Start de cada jogador (as chaves sao as proprias, sem sufixo).
    for player, group in ((1, 's_jvs_p1_button_bindings'), (2, 's_jvs_p2_button_bindings')):
        for name, generic in g[group]:
            if name.split('_', 1)[1] in ('Up', 'Down', 'Left', 'Right', 'Start'):
                out.append((name, player, ROLE[generic]))
    # Os botoes de cada jogo: {nome}_P1 e {nome}_P2 (corrida, so o P1). Cada
    # um e o botao N do jogo de C botoes (a ordem do grupo no header): a
    # posicao dele no painel vem do Buttons layout do Setup, como nos outros
    # emuladores (fliperos-buttons, pcsx2x6_save).
    for group, entries in g.items():
        if not group.startswith(('s_fight_', 's_standard_', 's_race_')):
            continue
        mapped = [name for name, generic in entries if generic in ROLE]
        for n, name in enumerate(mapped, 1):
            kind = 'button:%d:%d' % (len(mapped), n)
            out.append((name + '_P1', 1, kind))
            if not group.startswith('s_race_'):
                out.append((name + '_P2', 2, kind))
    # A ficha e o Back (Start e Back = ficha, no Button mapping do Setup).
    out.append(('Coin1', 1, 'Back'))
    out.append(('Coin2', 2, 'Back'))
    return out


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    with open(sys.argv[1], encoding='utf-8') as f:
        table = rows(f.read())
    with open(sys.argv[2], 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Gerado por tools/pcsx2x6-jvs-bindings.py (do ACJV_Inputs.h do PCSX2x6): nao editar.\n'
                '# chave da secao [JVS]<TAB>jogador<TAB>papel do SDL, ou button:C:N (o botao N do jogo\n'
                '# de C botoes, na posicao do painel que o Buttons layout do Setup dita)\n')
        for key, player, role in table:
            f.write('%s\t%d\t%s\n' % (key, player, role))
    print('%d bindings' % len(table))


if __name__ == '__main__':
    main()
