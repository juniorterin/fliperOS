#!/usr/bin/env bash
# Limine: de onde vem, o que vai pro rootfs e como vira ISO hibrida.
# Unico lugar com a versao fixada; usado pelo fliperos-mkiso.sh e pelas
# ferramentas de auditoria em tools/.
#
#   fliperos-limine.sh fetch DESTINO
#   fliperos-limine.sh rootfs RAIZ LIMINE_DIR
#   fliperos-limine.sh iso LIMINE_DIR ISO_DIR SAIDA.iso VOLID
set -euo pipefail

# O Ubuntu 24.04 nao empacota o Limine. O ramo "-binary" do upstream traz os
# binarios de boot prontos e o fonte do utilitario "limine" (um .c so). O
# commit confere que a tag nao foi movida depois de fixada aqui.
LIMINE_VERSION="11.4.1"
LIMINE_COMMIT="5be26a73d7b7b4d4477d18be94e1d16e615adf56"
LIMINE_REPO="https://github.com/limine-bootloader/limine.git"

src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)

usage() {
  sed -n '6,8p' "${BASH_SOURCE[0]}" | sed 's/^# *//' >&2
  exit 2
}

fetch() {
  local dest=$1 head
  git clone --quiet --depth=1 --branch "v${LIMINE_VERSION}-binary" "$LIMINE_REPO" "$dest"
  head=$(git -C "$dest" rev-parse HEAD)
  if [[ "$head" != "$LIMINE_COMMIT" ]]; then
    echo "Limine v${LIMINE_VERSION}: commit $head, expected $LIMINE_COMMIT" >&2
    exit 1
  fi
  # Estatico: o mesmo binario roda no container do build e no sistema
  # instalado, sem depender da glibc de nenhum dos dois.
  make -C "$dest" --quiet LDFLAGS=-static
}

rootfs() {
  local root=$1 limine=$2 file hook
  [[ -d "$root/etc" ]] || { echo "Invalid rootfs: $root" >&2; exit 2; }
  # O instalador grava o Limine no disco a partir destes arquivos, do PROPRIO
  # sistema instalado: o estagio 2 do bios-install e o limine-bios.sys da ESP
  # precisam ser da mesma versao.
  install -Dm755 "$limine/limine" "$root/usr/local/bin/limine"
  for file in limine-bios.sys BOOTX64.EFI LICENSE; do
    install -Dm644 "$limine/$file" "$root/usr/local/share/limine/$file"
  done
  install -Dm755 "$src/fliperos-limine-update.py" "$root/usr/local/sbin/fliperos-limine-update"
  # Equivalente dos hooks do update-grub: kernel novo, kernel removido e
  # initramfs regravado (EDID, tema do splash) chegam a ESP sozinhos.
  for hook in etc/kernel/postinst.d etc/kernel/postrm.d etc/initramfs/post-update.d; do
    mkdir -p "$root/$hook"
    ln -sfn /usr/local/sbin/fliperos-limine-update "$root/$hook/zz-fliperos-limine"
  done
}

iso() {
  local limine=$1 iso_dir=$2 output=$3 volid=$4 file
  [[ -f "$iso_dir/boot/limine/limine.conf" ]] \
    || { echo "Missing $iso_dir/boot/limine/limine.conf" >&2; exit 1; }
  mkdir -p "$iso_dir/EFI/BOOT"
  for file in limine-bios.sys limine-bios-cd.bin limine-uefi-cd.bin LICENSE; do
    cp "$limine/$file" "$iso_dir/boot/limine/"
  done
  cp "$limine/BOOTX64.EFI" "$iso_dir/EFI/BOOT/"
  rm -f "$output"
  # Receita do USAGE.md do Limine: El Torito BIOS, imagem EFI tambem exposta
  # como particao e MBR protetivo, pra mesma imagem bootar como CD e como
  # pendrive gravado byte a byte.
  xorriso -as mkisofs -R -r -J -V "$volid" \
    -b boot/limine/limine-bios-cd.bin -no-emul-boot -boot-load-size 4 -boot-info-table \
    -hfsplus -apm-block-size 2048 \
    --efi-boot boot/limine/limine-uefi-cd.bin -efi-boot-part --efi-boot-image \
    --protective-msdos-label "$iso_dir" -o "$output"
  # Sem isto a ISO so boota em BIOS como CD; e o que faz o pendrive bootar.
  "$limine/limine" bios-install "$output"
}

case "${1:-}" in
  fetch)  [[ $# -eq 2 ]] || usage; fetch "$2" ;;
  rootfs) [[ $# -eq 3 ]] || usage; rootfs "$2" "$3" ;;
  iso)    [[ $# -eq 5 ]] || usage; iso "$2" "$3" "$4" "$5" ;;
  *) usage ;;
esac
