#!/usr/bin/env python3
"""Confere a traducao (config/fliperos-atom15) contra uma BIOS gravada pelo
atom-15.exe de verdade, sem precisar da original: tira o hook da imagem, refaz o
patch e compara byte a byte.

  python3 tools/atom15-check.py BIOS_DO_ATOM15.rom [15,25,31] [csync]

Uma BIOS tem direitos de quem a fez, e por isso nao entra no repositorio: leia a
sua (/sys/bus/pci/devices/.../rom ou amdvbflash -s). Em 2026-10-30, com a de um
R7 240 (6613, faixa de 15 kHz), a imagem inteira saiu igual.
"""
import importlib.machinery
import importlib.util
import struct
import sys
from pathlib import Path


def load():
    path = Path(__file__).resolve().parent.parent / 'config/fliperos-atom15'
    loader = importlib.machinery.SourceFileLoader('fliperos_atom15', str(path))
    spec = importlib.util.spec_from_loader('fliperos_atom15', loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def main():
    atom = load()
    real = Path(sys.argv[1]).read_bytes()
    ranges = {int(r) for r in (sys.argv[2] if len(sys.argv) > 2 else '15').split(',')}
    csync = len(sys.argv) > 3 and sys.argv[3] == 'csync'

    mark = real.find(atom.HOOK_MARK)
    if mark < 0:
        print('This BIOS has no ATOM-15 hook.')
        return 1
    label = atom.HOOK_LABELS
    start = mark - (label['vesa_bios_service_mod'] + 2)

    # O que o hook guardou: os servicos de video de antes dele.
    def target(name):
        at = start + label[name]
        return (struct.unpack_from('<H', real, at + 1)[0] + at + 3) & 0xffff

    b = atom.Bios(real)
    b.checksum = atom.checksum(real)
    b.standard_proc, b.vesa_proc = target('standard_bios_service'), target('vesa_bios_service')
    b.data[start:start + len(atom.HOOK)] = bytes(len(atom.HOOK))
    atom.process_vesa_modes(b, ranges, csync)
    atom.process_standard_modes(b, ranges, csync)
    atom.fix_checksum(b, atom.bios_hook(b, csync))
    mine = bytes(b.data[:b.length]) + b.tail

    diff = [i for i in range(min(len(real), len(mine))) if real[i] != mine[i]]
    print('hook at %#x, %d bytes; %d different byte(s) of %d' % (start, len(atom.HOOK), len(diff), len(real)))
    for i in diff[:40]:
        print('  %#07x: real %02x, mine %02x' % (i, real[i], mine[i]))
    return 1 if diff or len(real) != len(mine) else 0


if __name__ == '__main__':
    sys.exit(main())
