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
cmp "$src/config/grub.cfg" "$work/grub.cfg"
unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/fliperos-video-check > "$work/check.py"
cmp "$src/fliperos-video-check.py" "$work/check.py"
unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/fliperos-install > "$work/install.py"
cmp "$src/fliperos-install.py" "$work/install.py"
unsquashfs -cat "$work/filesystem.squashfs" usr/lib/firmware/edid/crt15.bin > "$work/edid.bin"
cmp "$src/crt15-edid.bin" "$work/edid.bin"
edid-decode --check "$work/edid.bin" > "$work/edid.txt"
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/fliperos-video-check.service > "$work/check.service"
cmp "$src/config/fliperos-video-check.service" "$work/check.service"
lsinitramfs "$work/initrd.img" | grep 'firmware/edid/crt15.bin'
xorriso -indev "$iso" -report_el_torito plain > "$work/boot.txt" 2>&1
grep 'BIOS' "$work/boot.txt"
grep 'UEFI' "$work/boot.txt"
echo "ISO: arquivos conferidos, EDID valido no rootfs e presente no initramfs, boot BIOS+UEFI."
sha256sum "$iso"
