#!/usr/bin/env bash
# Auditoria so de leitura de uma ISO gerada: confere que o que foi para a
# imagem e o que esta no repositorio, sem montar nada nem tocar em hardware.
#
#   tools/verify-iso.sh caminho.iso      (no container do build)
set -euo pipefail
iso=${1:?Uso: verify-iso.sh caminho.iso}
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d /tmp/fliperos-verify.XXXXXX)
fail() { echo "FALHOU: $*" >&2; exit 1; }
echo "Auditoria extraida em $work"

xorriso -osirrox on -indev "$iso" \
  -extract /boot/limine/limine.conf "$work/limine.conf" \
  -extract /live/filesystem.squashfs "$work/filesystem.squashfs" \
  -extract /boot/vmlinuz "$work/vmlinuz" \
  -extract /boot/initrd.img "$work/initrd.img" > "$work/extract.log" 2>&1

# ── Menu de boot ──────────────────────────────────────────────
version=$(sed -n 's/^FLIPEROS_VERSION="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
common=$(sed -n 's/^BOOT_COMMON="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
sed -e "s|__VERSION__|$version|g" -e "s|__COMMON__|$common|g" "$src/config/limine.conf" > "$work/limine.expected"
cmp "$work/limine.expected" "$work/limine.conf" || fail "limine.conf difere do template"
entries=$(grep -c '^/' "$work/limine.conf")
[[ $entries == 10 ]] || fail "menu de boot com $entries entradas (esperado 10)"
grep -q '^timeout: 30$' "$work/limine.conf" || fail "timer do menu de boot nao e 30 s"
echo "menu de boot: 10 entradas, 30 s, 15 kHz padrao"

# ── Kernel 15 kHz ─────────────────────────────────────────────
kernel=$(sed -n 's/^KERNEL_VERSION="\(.*\)"$/\1/p' "$src/fliperos-kernel.sh")
strings "$work/vmlinuz" | grep -q "^$kernel-15khz " || grep -aq "$kernel-15khz" "$work/vmlinuz" \
  || fail "o kernel da ISO nao e o $kernel-15khz"
echo "kernel: $kernel-15khz"

# A listagem sai uma vez para arquivo: com "set -o pipefail", um "grep -q"
# num pipe fecha a entrada, o unsquashfs leva SIGPIPE e o pipeline falha.
unsquashfs -l "$work/filesystem.squashfs" > "$work/files.txt"
unsquashfs -lls "$work/filesystem.squashfs" > "$work/links.txt" 2> /dev/null
lsinitramfs "$work/initrd.img" > "$work/initrd.txt"
has() { grep -q "squashfs-root/$1\$" "$work/files.txt" || fail "ausente na ISO: $1"; }

# ── fliperos-setup igual ao do repositorio ────────────────────
( cd "$src/fliperos-setup" && find . -type f ) | while read -r file; do
  unsquashfs -cat "$work/filesystem.squashfs" "usr/local/lib/fliperos-setup/${file#./}" > "$work/f" \
    || fail "fliperos-setup: falta $file"
  cmp -s "$src/fliperos-setup/$file" "$work/f" || fail "fliperos-setup: $file difere do repositorio"
done
grep -E 'usr/local/bin/fliperos-setup ->' "$work/links.txt" | grep -q '/usr/local/lib/fliperos-setup/fliperos-setup' \
  || fail "/usr/local/bin/fliperos-setup nao aponta para o setup"
echo "fliperos-setup: todos os arquivos conferem"

for pair in fliperos-video-check.py:usr/local/bin/fliperos-video-check \
  fliperos-limine-update.py:usr/local/sbin/fliperos-limine-update \
  config/fliperos-rebuild-edids:usr/local/sbin/fliperos-rebuild-edids \
  config/fliperos-session:opt/fliperos/bin/fliperos-session \
  config/fliperos-lxde:opt/fliperos/bin/fliperos-lxde \
  config/fliperos-sessions.conf:etc/fliperos/sessions.conf \
  config/fliperos-setup.desktop:usr/share/applications/fliperos-setup.desktop \
  config/vtrgb-dracula:etc/fliperos/vtrgb-dracula; do
  unsquashfs -cat "$work/filesystem.squashfs" "${pair#*:}" > "$work/f" || fail "ausente: ${pair#*:}"
  cmp -s "$src/${pair%%:*}" "$work/f" || fail "${pair#*:} difere de ${pair%%:*}"
done
echo "ferramentas, sessao, LXDE e paleta conferem"

# ── Programas que o setup usa ─────────────────────────────────
for path in usr/bin/gum usr/bin/antimicrox usr/bin/qjoypad usr/bin/jq usr/bin/espeak-ng usr/bin/con2fbmap \
  usr/local/bin/switchres usr/local/bin/grid usr/local/bin/geometry usr/local/bin/Skyscraper \
  usr/local/bin/limine usr/local/share/limine/limine-bios.sys usr/local/share/limine/BOOTX64.EFI \
  usr/bin/startlxde etc/switchres.ini; do
  has "$path"
done
echo "gum, antimicrox, qjoypad, switchres/grid/geometry, Skyscraper, Limine, LXDE presentes"

# O autoremove do fim de cada compilacao pode levar uma biblioteca que o
# binario usa (o Skyscraper ja perdeu a libQt6Xml assim): toda NEEDED dos
# programas compilados no build tem de existir na imagem.
for bin in usr/local/bin/switchres usr/local/bin/grid usr/local/bin/Skyscraper usr/bin/antimicrox; do
  unsquashfs -cat "$work/filesystem.squashfs" "$bin" > "$work/bin"
  for lib in $(readelf -d "$work/bin" | sed -n 's/.*(NEEDED).*\[\(.*\)\]$/\1/p'); do
    found=false
    for dir in usr/lib/x86_64-linux-gnu usr/lib usr/local/lib; do
      grep -qxF "squashfs-root/$dir/$lib" "$work/files.txt" && { found=true; break; }
    done
    $found || fail "/$bin precisa de $lib, que nao esta na imagem"
  done
done
echo "bibliotecas dos programas compilados presentes"

# ── EDIDs: um por preset e os de super resolucao, no rootfs e no initramfs ─
for edid in generic_15 arcade_15 arcade_25 arcade_31 ntsc pal vesa_480 generic_15_super_resp generic_15_super_resi; do
  has "usr/lib/firmware/edid/$edid.bin"
  grep -q "firmware/edid/$edid.bin\$" "$work/initrd.txt" || fail "EDID fora do initramfs: $edid.bin"
done
unsquashfs -cat "$work/filesystem.squashfs" usr/lib/firmware/edid/generic_15_super_resi.bin > "$work/edid.bin"
edid-decode "$work/edid.bin" > "$work/edid.txt" 2>&1 || true
grep -q 'Switchres' "$work/edid.txt" || fail "o EDID super res nao e do Switchres"
echo "EDIDs do Switchres no rootfs e no initramfs"

# ── Splash, servicos, Limine do disco instalado ───────────────
grep -q 'themes/default.plymouth' "$work/files.txt" || fail "sem tema de splash padrao"
grep -q 'plymouth/themes' "$work/initrd.txt" || fail "tema de splash fora do initramfs"
grep -q 'multi-user.target.wants/ssh.service' "$work/files.txt" || fail "ssh.service nao habilitado"
grep -E 'etc/systemd/system/default.target ->' "$work/links.txt" | grep -q 'multi-user.target' \
  || fail "default.target nao aponta para multi-user"
for unit in lightdm.service display-manager.service; do
  grep -E "etc/systemd/system/$unit ->" "$work/links.txt" | grep -q '/dev/null' || fail "$unit nao mascarado"
done
grep -E 'etc/vtrgb ->' "$work/links.txt" | grep -q 'alternatives/vtrgb' || fail "/etc/vtrgb nao e a alternativa"
for hook in etc/kernel/postinst.d etc/kernel/postrm.d etc/initramfs/post-update.d; do
  grep -E "$hook/zz-fliperos-limine ->" "$work/links.txt" | grep -q '/usr/local/sbin/fliperos-limine-update' \
    || fail "hook do Limine ausente: $hook"
done
echo "splash no initramfs, ssh, sem display manager, paleta Dracula, hooks do Limine"

xorriso -indev "$iso" -report_el_torito plain > "$work/boot.txt" 2>&1
grep -q 'BIOS' "$work/boot.txt" || fail "sem boot BIOS"
grep -q 'UEFI' "$work/boot.txt" || fail "sem boot UEFI"
echo "ISO conferida: boot BIOS e UEFI."
sha256sum "$iso"
