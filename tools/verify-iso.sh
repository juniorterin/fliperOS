#!/usr/bin/env bash
# Read-only ISO content verification; no loop mount or hardware access.
set -euo pipefail
iso=${1:?Uso: verify-iso.sh caminho.iso}
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d /tmp/fliperos-verify.XXXXXX)
echo "Auditoria extraida em $work"
xorriso -osirrox on -indev "$iso" \
    -extract /boot/grub/grub.cfg "$work/grub.cfg" \
    -extract /live/filesystem.squashfs "$work/filesystem.squashfs" \
    -extract /boot/initrd.img "$work/initrd.img" > "$work/extract.log" 2>&1
# O build substitui __MONITOR_LABEL__ pelo rotulo do perfil, entao comparar
# com o template cru sempre falharia. A comparacao e feita contra o template
# com a mesma substituicao aplicada, e o rotulo sai do proprio arquivo da ISO.
label=$(grep -oE 'CRT [0-9]+kHz' "$work/grub.cfg" | head -1)
[[ -n "$label" ]] || { echo "grub.cfg da ISO sem rotulo de monitor" >&2; exit 1; }
sed "s|__MONITOR_LABEL__|${label}|g" "$src/config/grub.cfg" > "$work/grub.expected"
cmp "$work/grub.expected" "$work/grub.cfg"
echo "grub.cfg: confere com o template ($label)"
unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/fliperos-video-check > "$work/check.py"
cmp "$src/fliperos-video-check.py" "$work/check.py"
unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/fliperos-install > "$work/install.py"
cmp "$src/fliperos-install.py" "$work/install.py"
unsquashfs -cat "$work/filesystem.squashfs" usr/lib/firmware/edid/crt15.bin > "$work/edid.bin"
cmp "$src/crt15-edid.bin" "$work/edid.bin"
edid-decode --check "$work/edid.bin" > "$work/edid.txt"
# O perfil ativo governa a faixa de kHz que install-video.sh injeta no
# service, entao a comparacao precisa reproduzir a mesma injecao.
unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/profile > "$work/profile"
profile=$(tr -d '[:space:]' < "$work/profile")
case "$profile" in
    15khz) min_khz=15.0; max_khz=16.0 ;;
    25khz) min_khz=24.5; max_khz=25.5 ;;
    31khz) min_khz=31.0; max_khz=32.0 ;;
    *) echo "Perfil invalido na ISO: $profile" >&2; exit 1 ;;
esac
echo "perfil de monitor na ISO: $profile"
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/fliperos-video-check.service > "$work/check.service"
sed "s|--connector VGA-1 --wait 15|--connector VGA-1 --wait 15 --min-khz $min_khz --max-khz $max_khz|" \
    "$src/config/fliperos-video-check.service" > "$work/check.expected"
cmp "$work/check.expected" "$work/check.service"
lsinitramfs "$work/initrd.img" | grep 'firmware/edid/crt15.bin'

# Ferramentas e configuracao pos-instalacao: sem isso a ISO boota mas o
# usuario nao tem como escolher sessao nem reconfigurar video.
for path in usr/local/bin/fliperos-config \
            opt/fliperos/bin/fliperos-session \
            etc/fliperos/sessions.conf; do
    unsquashfs -cat "$work/filesystem.squashfs" "$path" > /dev/null \
        || { echo "Ausente na ISO: $path" >&2; exit 1; }
done
echo "ferramentas de configuracao presentes"

# A listagem sai uma vez para arquivo: com "set -o pipefail", um "grep -q"
# num pipe fecha a entrada, o unsquashfs leva SIGPIPE e o pipeline e
# considerado falho mesmo tendo encontrado o que procurava.
unsquashfs -l "$work/filesystem.squashfs" > "$work/files.txt"

# O splash so aparece se o tema estiver marcado como default.
grep -q 'themes/default.plymouth' "$work/files.txt" \
    || { echo "Sem tema de splash default definido" >&2; exit 1; }
# E so aparece de fato se o tema tambem estiver DENTRO do initramfs: o KMS
# roda antes do rootfs real, igual ao caso do EDID.
lsinitramfs "$work/initrd.img" > "$work/initrd.txt"
grep -q 'plymouth/themes' "$work/initrd.txt" \
    || { echo "Tema de splash ausente no initramfs" >&2; exit 1; }
echo "tema de splash default definido e presente no initramfs"

# SSH e o unico acesso quando o CRT nao mostra nada.
grep -q 'multi-user.target.wants/ssh.service' "$work/files.txt" \
    || { echo "ssh.service nao habilitado no boot" >&2; exit 1; }
echo "ssh habilitado no boot"

xorriso -indev "$iso" -report_el_torito plain > "$work/boot.txt" 2>&1
grep 'BIOS' "$work/boot.txt"
grep 'UEFI' "$work/boot.txt"
echo "ISO: arquivos conferidos, EDID valido no rootfs e presente no initramfs, boot BIOS+UEFI."
sha256sum "$iso"
