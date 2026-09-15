#!/usr/bin/env python3
"""Ubuntu live-to-disk installer following the gasetup workflow.

Independent implementation: select display, try live or select disk, review,
extract the ISO filesystem, configure UUIDs/initramfs, install BIOS/UEFI GRUB.
No physical disk is modified without an interactive, exact-device confirmation.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

LIVE_IMAGE = Path("/run/live/medium/live/filesystem.squashfs")
MIN_SIZE = 16 * 1024**3


def run(*args, capture=False):
    return subprocess.run([str(a) for a in args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def descendants(device):
    yield device
    for child in device.get("children", []):
        yield from descendants(child)


def rejection(device):
    if device.get("type") != "disk" or device.get("ro"):
        return "Nao e um disco gravavel"
    if int(device["size"]) < MIN_SIZE:
        return "Menos de 16 GiB"
    for part in descendants(device):
        if any(part.get("mountpoints") or []):
            return "Disco em uso (montagem, midia live ou swap)"
        if part.get("type") not in ("disk", "part"):
            return "Disco com RAID/LVM/criptografia ativa"
        sysdev = Path("/sys/class/block") / Path(part["path"]).name / "holders"
        if sysdev.exists() and any(sysdev.iterdir()):
            return "Disco com dispositivos dependentes ativos"
    return None


def inventory():
    return json.loads(run("lsblk", "--json", "--bytes", "--paths", "-o",
                          "PATH,TYPE,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS", capture=True))["blockdevices"]


def get_disk(path):
    path = os.path.realpath(path)
    for device in inventory():
        if device["path"] == path:
            why = rejection(device)
            if why:
                raise ValueError(why)
            return device
    raise ValueError("Disco nao encontrado")


def partition_path(disk, number):
    return disk + ("p" if disk[-1].isdigit() else "") + str(number)


def partition_commands(disk):
    # One GPT layout supports both BIOS and UEFI, with no NVRAM changes.
    return [
        ["wipefs", "--all", disk],
        ["parted", "--script", disk, "mklabel", "gpt",
         "mkpart", "BIOS", "1MiB", "2MiB", "set", "1", "bios_grub", "on",
         "mkpart", "EFI", "fat32", "2MiB", "514MiB", "set", "2", "esp", "on",
         "mkpart", "FliperOS", "ext4", "514MiB", "100%"],
        ["partprobe", disk], ["udevadm", "settle"],
        ["mkfs.vfat", "-F32", "-n", "FLIPERBOOT", partition_path(disk, 2)],
        ["mkfs.ext4", "-F", "-L", "FliperOS", partition_path(disk, 3)],
    ]


def boot_parameters(connector):
    if not re.fullmatch(r"(?:VGA|DVI-I|DVI-A|DP|HDMI-A)-[1-9][0-9]*", connector):
        raise ValueError("Conector invalido")
    return (f"video={connector}:e drm.edid_firmware={connector}:edid/crt15.bin "
            "radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0")


def plan(device, connector):
    return {"disk": device["path"], "model": device.get("model"),
            "serial": device.get("serial"), "bytes": device["size"],
            "erases_entire_disk": True, "source": str(LIVE_IMAGE),
            "partitions": ["1 MiB BIOS boot", "512 MiB EFI FAT32", "restante ext4 /"],
            "boot": "GRUB BIOS + UEFI removivel (Secure Boot desativado)",
            "kernel_parameters": boot_parameters(connector)}


def configure_video(root, connector):
    boot_parameters(connector)
    config = root / 'etc/fliperos'
    (config / 'connector').write_text(connector + '\n')
    xorg = config / 'xorg.conf'
    text = re.sub(r'Option "Monitor-[^"]+" "CRT15"',
                  'Option "Monitor-' + connector + '" "CRT15"', xorg.read_text())
    xorg.write_text(text)
    service = root / 'etc/systemd/system/fliperos-video-check.service'
    service.write_text(re.sub(r'--connector \S+', '--connector ' + connector, service.read_text()))


def select_connector():
    checker = Path("/usr/local/bin/fliperos-video-check")
    proc = subprocess.run([str(checker), "--json"], text=True, capture_output=True)
    report = json.loads(proc.stdout)
    active = [o for o in report["outputs"] if o["active"]]
    if not active:
        raise ValueError("Nenhuma saida ativa legivel. Consulte sudo fliperos-video-check.")
    for i, output in enumerate(active, 1):
        print(f'{i}. {output["card"]} {output["connector"]}: {output["horizontal_khz"]:.4f} kHz')
    index = int(input("Saida conectada ao CRT: ")) - 1
    if index < 0 or index >= len(active):
        raise ValueError("Selecao invalida")
    selected = active[index]
    if not 15.0 <= selected["horizontal_khz"] <= 16.0:
        raise ValueError("Saida fora de 15 kHz. Ajuste o boot/EDID antes de confirmar o CRT.")
    connector = selected["connector"]
    boot_parameters(connector)
    if sum(o["connector"] == connector for o in report["outputs"]) != 1:
        raise ValueError("Conector ambiguo entre GPUs; configurar manualmente antes de instalar")
    if input("A imagem esta visivel e estavel nesse CRT? Digite SIM: ") != "SIM":
        raise ValueError("Monitor nao confirmado")
    return connector


def install(device, connector):
    if os.geteuid() != 0:
        raise ValueError("Execute com sudo")
    if Path("/.dockerenv").exists() or "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower():
        raise ValueError("Instalacao em disco bloqueada em Docker/WSL; inicie a ISO no computador alvo")
    if not LIVE_IMAGE.is_file() or "boot=live" not in Path("/proc/cmdline").read_text().split():
        raise ValueError("Inicie pela ISO live do FliperOS")
    boot_parameters(connector)
    lock = open('/run/lock/fliperos-install.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError("Outra instalacao esta em andamento")
    for tool in ("wipefs", "parted", "partprobe", "udevadm", "mkfs.vfat", "mkfs.ext4",
                 "unsquashfs", "mount", "umount", "chroot", "blkid", "lsblk"):
        if not shutil.which(tool):
            raise ValueError("Dependencia ausente: " + tool)
    # Verify required bootloader assets BEFORE destroying a disk.
    for required in ("/usr/lib/grub/i386-pc/modinfo.sh", "/usr/lib/grub/x86_64-efi/modinfo.sh",
                     "/usr/sbin/grub-install", "/usr/sbin/update-initramfs"):
        if not Path(required).is_file():
            raise ValueError("ISO incompleta: " + required)
    run("unsquashfs", "-s", LIVE_IMAGE, capture=True)
    expected = get_disk(device["path"])
    if any(device.get(k) != expected.get(k) for k in ("path", "size", "serial", "model")):
        raise ValueError("Disco mudou desde a selecao")
    print(json.dumps(plan(device, connector), indent=2, ensure_ascii=False))
    print("TODOS os dados desse disco serao apagados. Outros discos nao serao instalados.")
    if input("Para confirmar, digite APAGAR " + device["path"] + ": ") != "APAGAR " + device["path"]:
        print("Cancelado sem alterar o disco.")
        return
    # Recheck after the human confirmation, including mount/swap/holder state.
    fresh = get_disk(device["path"])
    if any(fresh.get(k) != device.get(k) for k in ("path", "size", "serial", "model")):
        raise ValueError("Identidade do disco mudou; operacao cancelada")
    disk = device["path"]
    target = Path(tempfile.mkdtemp(prefix="fliperos-install-", dir="/mnt"))
    mounts = []
    try:
        for command in partition_commands(disk):
            run(*command)
        run("mount", partition_path(disk, 3), target)
        mounts.append(target)
        run("unsquashfs", "-f", "-d", target, LIVE_IMAGE)
        efi = target / "boot/efi"
        efi.mkdir(parents=True, exist_ok=True)
        run("mount", partition_path(disk, 2), efi)
        mounts.append(efi)
        root_uuid = run("blkid", "-s", "UUID", "-o", "value", partition_path(disk, 3), capture=True).strip()
        efi_uuid = run("blkid", "-s", "UUID", "-o", "value", partition_path(disk, 2), capture=True).strip()
        (target / "etc/fstab").write_text(
            f"UUID={root_uuid} / ext4 defaults 0 1\nUUID={efi_uuid} /boot/efi vfat umask=0077 0 2\n")
        grubdir = target / "etc/default/grub.d"
        grubdir.mkdir(exist_ok=True)
        (grubdir / "99-fliperos.cfg").write_text(
            'GRUB_CMDLINE_LINUX_DEFAULT="' + boot_parameters(connector) + '"\n'
            'GRUB_CMDLINE_LINUX=""\nGRUB_DISABLE_OS_PROBER=true\n'
            'GRUB_TERMINAL_OUTPUT=console\nGRUB_TIMEOUT=3\nGRUB_DISTRIBUTOR=FliperOS\n')
        configure_video(target, connector)
        (target / "etc/fliperos/installed").write_text("Installed from FliperOS live ISO\n")
        (target / "etc/machine-id").write_text("")
        for key in (target / "etc/ssh").glob("ssh_host_*"):
            key.unlink()
        # Isolated propagation; used only in a real live boot, never on WSL.
        for relative in ("dev", "proc", "sys", "run"):
            dest = target / relative
            dest.mkdir(exist_ok=True)
            run("mount", "--rbind", "/" + relative, dest)
            mounts.append(dest)
            run("mount", "--make-rslave", dest)
        run("chroot", target, "ssh-keygen", "-A")
        run("chroot", target, "update-initramfs", "-u", "-k", "all")
        run("chroot", target, "grub-install", "--target=i386-pc", disk)
        run("chroot", target, "grub-install", "--target=x86_64-efi", "--efi-directory=/boot/efi",
            "--bootloader-id=FliperOS", "--removable", "--no-nvram")
        run("chroot", target, "update-grub")
        print("Defina a senha do usuario fliperos para o sistema instalado:")
        run("chroot", target, "passwd", "fliperos")
        run("sync")
    finally:
        # Never delete the target tree, including when an unmount fails.
        for mount in reversed(mounts):
            result = subprocess.run(["umount", "-R", str(mount)])
            if result.returncode:
                raise OSError("Falha ao desmontar " + str(mount) + "; mantenha o sistema ligado e verifique.")
    lock.close()
    print("Instalacao concluida. Retire a midia live ao reiniciar. Valide novamente o modo ativo.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", metavar="DISK", help="Somente mostrar o plano; nenhuma escrita")
    parser.add_argument("--connector", default="VGA-1", help="Conector para --plan")
    args = parser.parse_args()
    try:
        if args.plan:
            print(json.dumps(plan(get_disk(args.plan), args.connector), indent=2, ensure_ascii=False))
            return 0
        print("FliperOS — assistente de instalacao (fluxo inspirado no GroovyArcade/gasetup)")
        print("1. Verificar monitor e testar live\n2. Verificar monitor e instalar em disco\n0. Sair")
        choice = input("Opcao: ")
        if choice not in ("1", "2"):
            return 0
        connector = select_connector()
        if choice == "1":
            if os.geteuid() != 0:
                raise ValueError("Execute com sudo para salvar a selecao de monitor")
            configure_video(Path('/'), connector)
            print("Monitor confirmado. Use fliperos-launcher como usuario fliperos para testar os emuladores.")
            return 0
        disks = [d for d in inventory() if not rejection(d)]
        for i, device in enumerate(disks, 1):
            print(f'{i}. {device["path"]} {device.get("model", "")} '
                  f'{int(device["size"]) / 1024**3:.1f} GiB serial={device.get("serial", "")}')
        if not disks:
            raise ValueError("Nenhum disco livre elegivel; discos em uso sao excluidos")
        index = int(input("Disco de destino (0 cancela): ")) - 1
        if index == -1:
            return 0
        if not 0 <= index < len(disks):
            raise ValueError("Selecao invalida")
        install(disks[index], connector)
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        print("Instalacao interrompida: " + str(exc))
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nCancelado.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
