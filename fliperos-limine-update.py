#!/usr/bin/env python3
"""Equivalente do update-grub para o Limine do sistema instalado.

O Limine so le FAT e ISO9660, e a raiz e ext4: o kernel em /boot fica
invisivel pra ele. Este script copia o kernel mais novo, e o anterior como
reserva, pra ESP e regrava o menu. Os hooks de kernel e de initramfs o chamam
sozinho; a mao, so depois de editar /etc/default/fliperos-boot.
"""
import filecmp
import os
from pathlib import Path
import re
import shutil
import sys

BOOT = Path("/boot")
ESP = Path("/boot/efi")
DEFAULTS = Path("/etc/default/fliperos-boot")
FSTAB = Path("/etc/fstab")
INSTALLED = Path("/etc/fliperos/installed")
# Caminhos dentro da ESP. O limine.conf fica ao lado do limine-bios.sys, num
# dos diretorios que o Limine procura sozinho (BIOS e UEFI).
KERNEL_DIR = "fliperos"
CONFIG = "limine/limine.conf"
# O atual e um de reserva. Com initrd de ~125 MiB, dois kernels mais a copia
# de um terceiro durante a troca ficam em ~420 MiB na ESP de 1 GiB.
KEEP = 2


def version_key(version):
    """Ordem natural: 6.12.104-15khz vem depois de 6.8.0-45-generic."""
    return [int(part) if part.isdigit() else part
            for part in re.split(r"(\d+)", version)]


def kernels(boot):
    """Versoes com kernel E initrd em /boot, da mais nova pra mais antiga.
    Kernel cujo initrd ainda nao existe (o initramfs pode sair depois, por
    trigger do dpkg) fica de fora ate o hook do initramfs rodar."""
    found = [path.name[len("vmlinuz-"):] for path in boot.glob("vmlinuz-*")]
    ready = [v for v in found if (boot / ("initrd.img-" + v)).is_file()]
    return sorted(ready, key=version_key, reverse=True)


def read_defaults(text):
    return dict(re.findall(r'^(FLIPEROS_\w+)="([^"]*)"[ \t]*$', text, re.M))


def root_device(fstab):
    for line in fstab.splitlines():
        fields = line.split()
        if len(fields) >= 2 and not fields[0].startswith("#") and fields[1] == "/":
            return fields[0]
    raise ValueError("Sem entrada para / no /etc/fstab")


def entry(title, comment, version, cmdline):
    # textmode: em BIOS o Limine entrega o kernel em modo texto VGA, como o
    # GRUB fazia, em vez de escolher um modo VBE qualquer (sempre acima de
    # 15 kHz) ate o KMS aplicar o EDID. Em UEFI a opcao e ignorada.
    return ("/%s\n"
            "    comment: %s\n"
            "    protocol: linux\n"
            "    path: boot():/%s/vmlinuz-%s\n"
            "    module_path: boot():/%s/initrd.img-%s\n"
            "    textmode: yes\n"
            "    cmdline: %s\n"
            % (title, comment, KERNEL_DIR, version, KERNEL_DIR, version, cmdline))


def render(versions, root, cmdline, timeout):
    normal = " ".join(["root=" + root, "ro"] + cmdline.split())
    # Mesmo video/EDID do CRT, so sem o splash: o caminho com as mensagens do
    # kernel na tela quando o tema do Plymouth falha.
    verbose = " ".join(p for p in normal.split() if p not in ("quiet", "splash"))
    text = ("# Gerado por fliperos-limine-update; editar aqui nao adianta.\n"
            "# Parametros do kernel: /etc/default/fliperos-boot\n"
            "timeout: %s\n"
            # Boot direto no Plymouth, sem menu nem "Loading kernel": a
            # contagem continua, invisivel, e uma tecla nela revela o menu
            # (a entrada de diagnostico).
            "quiet: yes\n"
            # Menu em modo texto: igual ao "terminal_output console" do GRUB.
            "graphics: no\n"
            "interface_branding: FliperOS\n\n" % timeout)
    text += entry("FliperOS", "Kernel " + versions[0], versions[0], normal)
    if len(versions) > 1:
        text += "\n" + entry("FliperOS - kernel anterior",
                             "Kernel " + versions[1] + ", reserva se o atual falhar",
                             versions[1], normal)
    text += "\n" + entry("FliperOS - Diagnostico (sem splash)",
                         "Mensagens do kernel na tela; mesmo video do CRT",
                         versions[0], verbose)
    return text


def replace(dest, write):
    """Grava num .new e troca de nome: queda de energia no meio deixa o
    arquivo antigo inteiro, nunca um pela metade."""
    tmp = dest.with_name(dest.name + ".new")
    write(tmp)
    with open(tmp, "rb") as handle:
        os.fsync(handle.fileno())
    os.replace(tmp, dest)


def update(boot, esp, root, cmdline, timeout):
    versions = kernels(boot)[:KEEP]
    if not versions:
        raise ValueError("Nenhum kernel com initrd em " + str(boot))
    target = esp / KERNEL_DIR
    target.mkdir(parents=True, exist_ok=True)
    wanted = set()
    for version in versions:
        for name in ("vmlinuz-" + version, "initrd.img-" + version):
            wanted.add(name)
            if not (target / name).is_file() or not filecmp.cmp(boot / name, target / name, shallow=False):
                replace(target / name, lambda tmp, src=boot / name: shutil.copyfile(src, tmp))
    config = esp / CONFIG
    config.parent.mkdir(parents=True, exist_ok=True)
    text = render(versions, root, cmdline, timeout)
    replace(config, lambda tmp: tmp.write_text(text))
    # So depois do menu novo: ate aqui o menu antigo ainda aponta pra eles.
    for stale in target.iterdir():
        if stale.name not in wanted:
            stale.unlink()
    return versions


def main():
    if os.geteuid() != 0:
        print("Execute com sudo", file=sys.stderr)
        return 1
    if not INSTALLED.is_file():
        # Chroot do build e midia live tambem rodam update-initramfs, e os
        # hooks disparam; ali nao existe ESP instalada pra atualizar.
        return 0
    if not os.path.ismount(ESP):
        print("fliperos-limine-update: /boot/efi nao esta montada; o Limine continua "
              "com o kernel antigo. Monte-a e rode: sudo fliperos-limine-update", file=sys.stderr)
        return 1
    try:
        defaults = read_defaults(DEFAULTS.read_text())
        versions = update(BOOT, ESP, root_device(FSTAB.read_text()),
                          defaults.get("FLIPEROS_CMDLINE", ""),
                          defaults.get("FLIPEROS_TIMEOUT", "3"))
    except (OSError, ValueError) as exc:
        print("fliperos-limine-update: " + str(exc), file=sys.stderr)
        return 1
    print("Limine: kernel " + " + reserva ".join(versions))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
