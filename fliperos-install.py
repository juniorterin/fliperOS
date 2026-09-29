#!/usr/bin/env python3
"""Ubuntu live-to-disk installer following the gasetup workflow.

Independent implementation: select display, try live or select disk, review,
extract the ISO filesystem, configure UUIDs/initramfs, install BIOS/UEFI GRUB.
No physical disk is modified without an interactive, exact-device confirmation.
"""
import argparse
import contextlib
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
                          "PATH,TYPE,SIZE,MODEL,SERIAL,RO,MOUNTPOINTS,LABEL", capture=True))["blockdevices"]


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
    # quiet splash: sem "splash" o Plymouth nao aparece. A entrada
    # "Diagnostico" do GRUB nao leva esses dois, e continua sendo o caminho
    # com as mensagens do kernel na tela.
    return (f"video={connector}:e drm.edid_firmware={connector}:edid/crt15.bin "
            "radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0 "
            "quiet splash")


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


def autodetect_connector():
    """Fall back to cycling VGA-*/DVI-I-* connectors when none is active yet.

    Only narrows down the physical port (see fliperos-video-autodetect.py);
    the 15 kHz check below still applies to whatever it finds.
    """
    tool = Path("/usr/local/bin/fliperos-video-autodetect")
    if not tool.is_file():
        tool = Path(__file__).with_name("fliperos-video-autodetect.py")
    # So o stdout e capturado: o auto-detect conversa com a pessoa pelo stderr
    # ("Testando VGA-1", "Pressione ENTER..."), e isso precisa chegar na tela.
    proc = subprocess.run([str(tool), "--json"], text=True, stdout=subprocess.PIPE)
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise ValueError("Auto-deteccao de conector falhou (codigo %d); veja as mensagens acima."
                         % proc.returncode)
    confirmed = result.get("confirmed", [])
    if not confirmed:
        raise ValueError("Nenhum conector confirmado na auto-deteccao. Consulte sudo fliperos-video-check.")
    if len(confirmed) == 1:
        return confirmed[0]
    for i, name in enumerate(confirmed, 1):
        print(f'{i}. {name}')
    index = int(input("Mais de um conector respondeu; qual e o CRT? ")) - 1
    if not 0 <= index < len(confirmed):
        raise ValueError("Selecao invalida")
    return confirmed[index]


def select_connector():
    checker = Path("/usr/local/bin/fliperos-video-check")
    proc = subprocess.run([str(checker), "--json"], text=True, capture_output=True)
    report = json.loads(proc.stdout)
    active = [o for o in report["outputs"] if o["active"]]
    if not active:
        found = autodetect_connector()
        print("Conector " + found + " confirmado visualmente. Verificando o modo agora...")
        proc = subprocess.run([str(checker), "--json"], text=True, capture_output=True)
        report = json.loads(proc.stdout)
        active = [o for o in report["outputs"] if o["active"] and o["connector"] == found]
        if not active:
            raise ValueError(found + " nao produziu um modo ativo legivel pelo DRM; "
                              "ajuste o EDID/boot antes de instalar.")
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
    # Maiuscula/minuscula nao importa aqui: esta confirmacao nao apaga nada, e
    # "sim" digitado em minusculas abortava a instalacao inteira.
    if input("A imagem esta visivel e estavel nesse CRT? Digite SIM: ").strip().upper() != "SIM":
        raise ValueError("Monitor nao confirmado")
    return connector


# ════════════════════════════════════════════════════════════
#  Deteccao de instalacao existente + reparo (sem reparticionar)
# ════════════════════════════════════════════════════════════
def probe_marker(partition):
    """Monta uma particao rotulada FliperOS somente-leitura o tempo
    suficiente pra ler seu marcador de instalacao e o conector salvo.
    Nunca levanta excecao; retorna None pra qualquer coisa que nao seja
    uma raiz FliperOS ja concluida."""
    target = Path(tempfile.mkdtemp(prefix="fliperos-probe-", dir="/mnt"))
    try:
        subprocess.run(["mount", "-o", "ro", partition, str(target)],
                       check=True, capture_output=True)
    except subprocess.CalledProcessError:
        target.rmdir()
        return None
    try:
        marker = target / "etc/fliperos/installed"
        if not marker.is_file():
            return None
        info = {"installed": marker.read_text().strip()}
        connector = target / "etc/fliperos/connector"
        if connector.is_file():
            info["connector"] = connector.read_text().strip()
        return info
    finally:
        subprocess.run(["umount", str(target)])
        target.rmdir()


def existing_installs():
    """Discos que ja tem um FliperOS instalado: particao ext4 rotulada
    FliperOS (ver partition_commands) mais um marcador de instalacao
    legivel. Somente leitura; nada fica montado ao final."""
    found = []
    for device in inventory():
        for part in descendants(device):
            if part.get("type") != "part" or part.get("label") != "FliperOS":
                continue
            if any(part.get("mountpoints") or []):
                continue
            info = probe_marker(part["path"])
            if info is None:
                continue
            found.append({"disk": device["path"], "partition": part["path"],
                          "model": device.get("model"), "serial": device.get("serial"),
                          "bytes": device.get("size"), **info})
    return found


def service_khz(root):
    """Le --min-khz do fliperos-video-check.service sob root; usado pra
    recusar restaurar configuracoes de um perfil de monitor (15/25/31 kHz)
    diferente do que o disco alvo foi instalado."""
    service = root / "etc/systemd/system/fliperos-video-check.service"
    if not service.is_file():
        return None
    match = re.search(r'--min-khz (\S+)', service.read_text())
    return match.group(1) if match else None


@contextlib.contextmanager
def mounted_target(disk, chroot=False):
    """Monta um disco com FliperOS ja instalado pra reparo: raiz e EFI e,
    com chroot=True, tambem /dev,/proc,/sys,/run do sistema live (pra
    update-initramfs/update-grub rodarem dentro do chroot do disco alvo).
    Sempre desmonta, mesmo em erro."""
    match = next((entry for entry in existing_installs() if entry["disk"] == disk), None)
    if match is None:
        raise ValueError("Nenhuma instalacao FliperOS encontrada em " + disk)
    target = Path(tempfile.mkdtemp(prefix="fliperos-repair-", dir="/mnt"))
    mounts = []
    try:
        run("mount", match["partition"], target)
        mounts.append(target)
        efi = target / "boot/efi"
        run("mount", partition_path(disk, 2), efi)
        mounts.append(efi)
        if chroot:
            for relative in ("dev", "proc", "sys", "run"):
                dest = target / relative
                run("mount", "--rbind", "/" + relative, dest)
                mounts.append(dest)
                run("mount", "--make-rslave", dest)
        yield target
    finally:
        for mount in reversed(mounts):
            result = subprocess.run(["umount", "-R", str(mount)])
            if result.returncode:
                raise OSError("Falha ao desmontar " + str(mount) + "; mantenha o sistema ligado e verifique.")


# Arquivos "de fabrica" pro caso 2 (launcher/emulador mal configurado):
# exatamente os que fliperos-install-video.sh grava a partir de config/.
CONFIG_PATHS = (
    "etc/fliperos/xorg.conf",
    "etc/fliperos/mame/mame.ini",
    "etc/fliperos/switchres.ini",
    "etc/switchres.ini",
    "etc/fliperos/retroarch/retroarch.cfg",
    "opt/fliperos/bin/fliperos-x11-run",
    "opt/fliperos/bin/fliperos-kms-run",
    "opt/fliperos/bin/fliperos-x11-client",
    "opt/fliperos/bin/fliperos-launcher",
)

# Caso 3 (pacotes/binarios corrompidos): reextrai o squashfs por cima do
# disco, preservando ROMs, saves, identidade do host e a configuracao de
# video/launcher que ja esta correta nesse disco (senao viraria o caso 2).
PRESERVE_PREFIXES = (
    "opt/fliperos/roms", "home/fliperos", "etc/machine-id", "etc/ssh",
    "etc/fstab", "etc/fliperos/connector",
) + CONFIG_PATHS + ("etc/default/grub.d/99-fliperos.cfg", "boot")


def repair_configs(disk):
    """Caso 2: restaura os arquivos de configuracao de launcher/emuladores
    pro estado de fabrica dessa midia live, mantendo o conector que o
    disco ja tinha salvo."""
    lock = preflight()
    try:
        live_khz = service_khz(Path('/'))
        with mounted_target(disk) as target:
            target_khz = service_khz(target)
            if live_khz and target_khz and live_khz != target_khz:
                raise ValueError(
                    "Esta midia live e de outro perfil de monitor (min-khz " + live_khz +
                    ") e o disco foi instalado com min-khz " + target_khz +
                    "; inicie a ISO do perfil correto antes de restaurar configuracoes.")
            connector_file = target / "etc/fliperos/connector"
            connector = connector_file.read_text().strip() if connector_file.is_file() else "VGA-1"
            extraction = Path(tempfile.mkdtemp(prefix="fliperos-repair-src-", dir="/mnt"))
            try:
                run("unsquashfs", "-f", "-d", extraction, LIVE_IMAGE, *CONFIG_PATHS)
                for relative in CONFIG_PATHS:
                    src = extraction / relative
                    if not src.is_file():
                        continue
                    dest = target / relative
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
            finally:
                shutil.rmtree(extraction, ignore_errors=True)
            configure_video(target, connector)
    finally:
        lock.close()


def repair_video(disk, connector):
    """Caso 1: GPU trocada. Reaplica o conector detectado agora (com a
    placa nova) na raiz do disco e regrava os parametros de boot/EDID."""
    boot_parameters(connector)
    lock = preflight()
    try:
        with mounted_target(disk, chroot=True) as target:
            configure_video(target, connector)
            cfg = target / "etc/default/grub.d/99-fliperos.cfg"
            if cfg.is_file():
                cfg.write_text(re.sub(
                    r'GRUB_CMDLINE_LINUX_DEFAULT="[^"]*"',
                    'GRUB_CMDLINE_LINUX_DEFAULT="' + boot_parameters(connector) + '"',
                    cfg.read_text()))
            run("chroot", target, "update-initramfs", "-u", "-k", "all")
            run("chroot", target, "update-grub")
    finally:
        lock.close()


def preserved(relative, prefixes=PRESERVE_PREFIXES):
    return any(relative == p or relative.startswith(p + "/") for p in prefixes)


def overlay_squashfs(extraction, target):
    """Copia cada arquivo de uma extracao fresca do squashfs por cima do
    disco alvo, pulando PRESERVE_PREFIXES. So adiciona/sobrescreve; nunca
    apaga um arquivo extra que exista so no disco."""
    for path in sorted(extraction.rglob("*")):
        relative = path.relative_to(extraction).as_posix()
        if preserved(relative):
            continue
        dest = target / relative
        if path.is_symlink():
            if dest.is_symlink() or dest.exists():
                dest.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(os.readlink(path), dest)
        elif path.is_dir():
            dest.mkdir(parents=True, exist_ok=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)


def repair_packages(disk):
    """Caso 3: pacotes/binarios perdidos ou corrompidos. Reextrai o
    squashfs da midia live por cima do disco, preservando ROMs, saves,
    identidade do host e a configuracao de video/launcher atual."""
    lock = preflight()
    try:
        with mounted_target(disk, chroot=True) as target:
            extraction = Path(tempfile.mkdtemp(prefix="fliperos-repair-src-", dir="/mnt"))
            try:
                run("unsquashfs", "-f", "-d", extraction, LIVE_IMAGE)
                overlay_squashfs(extraction, target)
            finally:
                shutil.rmtree(extraction, ignore_errors=True)
            run("chroot", target, "update-initramfs", "-u", "-k", "all")
    finally:
        lock.close()


def repair_shell(disk):
    """Caso 4: shell root dentro do sistema instalado, via chroot a partir da
    midia live (equivalente ao rescue_mode do gasetup). Serve pro que os casos
    fechados nao cobrem — reinstalar um pacote, editar fstab, ver journal."""
    with mounted_target(disk, chroot=True) as target:
        print("Shell root em " + disk + " (via chroot). Digite exit pra sair e desmontar.")
        subprocess.run(["chroot", str(target), "/bin/bash", "--login"])


def preflight():
    """Checagens comuns a qualquer operacao que monta/faz chroot num disco
    real: root, boot live genuino (nao Docker/WSL2 — ver aviso no
    CLAUDE.md sobre chroot+bind-mount de /dev vazando no WSL2) e nenhuma
    outra instalacao/reparo em andamento. Retorna o lock aberto; quem
    chamar deve fechar."""
    if os.geteuid() != 0:
        raise ValueError("Execute com sudo")
    if Path("/.dockerenv").exists() or "microsoft" in Path("/proc/sys/kernel/osrelease").read_text().lower():
        raise ValueError("Bloqueado em Docker/WSL; inicie a ISO live do FliperOS no computador alvo")
    if not LIVE_IMAGE.is_file() or "boot=live" not in Path("/proc/cmdline").read_text().split():
        raise ValueError("Inicie pela ISO live do FliperOS")
    lock = open('/run/lock/fliperos-install.lock', 'w')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise ValueError("Outra instalacao ou reparo ja esta em andamento")
    for tool in ("mount", "umount", "chroot", "unsquashfs", "blkid", "lsblk"):
        if not shutil.which(tool):
            lock.close()
            raise ValueError("Dependencia ausente: " + tool)
    return lock


def install(device, connector):
    boot_parameters(connector)
    lock = preflight()
    for tool in ("wipefs", "parted", "partprobe", "udevadm", "mkfs.vfat", "mkfs.ext4"):
        if not shutil.which(tool):
            lock.close()
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
    existing = next((entry for entry in existing_installs() if entry["disk"] == device["path"]), None)
    if existing:
        print("ATENCAO: ja existe um FliperOS instalado nesse disco (instalado: " +
              existing.get("installed", "?") + "; conector salvo: " + existing.get("connector", "?") + ").")
        print("Pra trocar de GPU, restaurar configuracoes ou reinstalar pacotes sem perder ROMs, "
              "cancele e use a opcao 3 (Reparar instalacao existente) no menu principal.")
        if input("Mesmo assim apagar essa instalacao e comecar do zero? Digite SIM: ") != "SIM":
            print("Cancelado sem alterar o disco.")
            return
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


def menu_repair(found):
    for i, entry in enumerate(found, 1):
        print(f'{i}. {entry["disk"]} {entry.get("model", "")} serial={entry.get("serial", "")} '
              f'conector={entry.get("connector", "?")} instalado={entry.get("installed", "?")}')
    index = int(input("Disco a reparar (0 cancela): ")) - 1
    if index == -1:
        return 0
    if not 0 <= index < len(found):
        raise ValueError("Selecao invalida")
    disk = found[index]["disk"]
    print("O que deseja reparar?")
    print("1. GPU trocada (reconfigurar conector e parametros de boot)")
    print("2. Configuracao padrao de launcher/emuladores (restaura arquivos originais)")
    print("3. Pacotes/binarios corrompidos ou faltando (reextrai do sistema live)")
    print("4. Shell root dentro da instalacao (chroot, pra reparo manual)")
    print("0. Cancelar")
    what = input("Opcao: ")
    if what == "1":
        connector = select_connector()
        repair_video(disk, connector)
        print("Video reconfigurado nesse disco. Reinicie sem a midia live para validar.")
    elif what == "2":
        repair_configs(disk)
        print("Configuracoes de launcher/emuladores restauradas para o padrao de fabrica.")
    elif what == "3":
        print("Isso reinstala os binarios/pacotes do sistema a partir dessa midia live, "
              "preservando ROMs, saves e a configuracao de video atual.")
        if input("Digite REPARAR para confirmar: ") != "REPARAR":
            print("Cancelado.")
            return 0
        repair_packages(disk)
        print("Pacotes reinstalados nesse disco. Reinicie sem a midia live para validar.")
    elif what == "4":
        repair_shell(disk)
    else:
        print("Cancelado.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", metavar="DISK", help="Somente mostrar o plano; nenhuma escrita")
    parser.add_argument("--connector", default="VGA-1", help="Conector para --plan")
    parser.add_argument("--detect-installed", action="store_true",
                         help="Somente listar discos com FliperOS ja instalado; nenhuma escrita")
    args = parser.parse_args()
    try:
        if args.plan:
            print(json.dumps(plan(get_disk(args.plan), args.connector), indent=2, ensure_ascii=False))
            return 0
        if args.detect_installed:
            print(json.dumps(existing_installs(), indent=2, ensure_ascii=False))
            return 0
        # A midia e de instalacao, nao de uso: o squashfs live existe so pra
        # carregar este assistente. Nao ha modo "testar sem instalar".
        print("FliperOS — assistente de instalacao (fluxo inspirado no GroovyArcade/gasetup)")
        found = existing_installs()
        print("1. Verificar monitor e instalar em disco")
        if found:
            print(f"2. Reparar instalacao existente ({len(found)} disco(s) com FliperOS)")
        print("0. Sair")
        choice = input("Opcao: ")
        if choice == "2" and found:
            return menu_repair(found)
        if choice != "1":
            return 0
        connector = select_connector()
        # Disco recusado aparece com o motivo, em vez de sumir da lista: sem
        # isso, um HD em uso ou pequeno demais so gerava "nenhum disco" e a
        # pessoa nao tinha como saber o que corrigir.
        disks, refused = [], []
        for device in inventory():
            why = rejection(device)
            if not why:
                disks.append(device)
            elif device.get("type") == "disk":
                refused.append((device, why))
        installed_paths = {entry["disk"] for entry in found}
        for i, device in enumerate(disks, 1):
            flag = " [FliperOS ja instalado]" if device["path"] in installed_paths else ""
            print(f'{i}. {device["path"]} {device.get("model", "")} '
                  f'{int(device["size"]) / 1024**3:.1f} GiB serial={device.get("serial", "")}{flag}')
        for device, why in refused:
            print(f'-  {device["path"]} {device.get("model") or ""} '
                  f'{int(device["size"]) / 1024**3:.1f} GiB: indisponivel ({why})')
        if not disks:
            raise ValueError("Nenhum disco elegivel; o motivo de cada um esta listado acima")
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
