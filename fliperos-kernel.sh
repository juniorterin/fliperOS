#!/usr/bin/env bash
# Kernel 15 kHz do FliperOS: kernel.org LTS + patches D0023R (os mesmos do
# pacote linux-15khz do GroovyArcade), empacotado em .deb.
#
#   fliperos-kernel.sh key            imprime a chave do cache
#   fliperos-kernel.sh build SAIDA    compila e deixa os .deb em SAIDA
#
# Roda no container do build (Ubuntu 24.04, o mesmo da ISO), nunca direto no
# WSL. A chave muda quando muda a versao, um patch ou este script: o
# fliperos-mkiso.sh reaproveita os .deb de um build anterior com a mesma
# chave, porque compilar o kernel e a etapa mais demorada da ISO.
set -euo pipefail

KERNEL_VERSION="6.18.54"
KERNEL_SERIES="${KERNEL_VERSION%.*}"
LOCALVERSION="-15khz"
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
patches="$src/patches/kernel-15khz/$KERNEL_SERIES"

key() {
  [[ -d $patches ]] || { echo "Sem patches para $KERNEL_SERIES em $patches" >&2; exit 1; }
  printf '%s-%s\n' "$KERNEL_VERSION" \
    "$(cat "$patches"/*.patch "${BASH_SOURCE[0]}" | sha256sum | cut -c1-12)"
}

build() {
  local out=$1 work seed pkg
  mkdir -p "$out"
  work=$(mktemp -d /tmp/fliperos-kernel.XXXXXX)
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends \
    build-essential bc bison flex libssl-dev libelf-dev libncurses-dev \
    rsync cpio kmod dwarves zstd xz-utils wget ca-certificates python3 libdw-dev debhelper \
    > /dev/null

  cd "$work"
  # Semente do .config: o do kernel generico do proprio Ubuntu 24.04, que ja
  # liga todos os drivers de video e o drm.edid_firmware. Vem do pacote
  # linux-buildinfo (o linux-image so traz o vmlinuz).
  pkg=$(apt-cache depends linux-image-generic | awk '/Depends:/{print $2; exit}')
  pkg=${pkg/linux-image-/linux-buildinfo-}
  apt-get download "$pkg" > /dev/null
  dpkg-deb -x "$pkg"_*.deb seed
  seed=$(find seed -type f -name config | head -1)
  [[ -n $seed ]] || { echo "Semente do .config nao encontrada em $pkg" >&2; exit 1; }

  wget -q "https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VERSION%%.*}.x/linux-$KERNEL_VERSION.tar.xz"
  tar xf "linux-$KERNEL_VERSION.tar.xz"
  cp "$seed" "linux-$KERNEL_VERSION/.config"
  cd "linux-$KERNEL_VERSION"
  for p in "$patches"/*.patch; do
    echo "Aplicando $(basename "$p")"
    patch -p1 --forward < "$p"
  done

  # Kernel proprio, sem Secure Boot: sem assinatura de modulo e sem os
  # certificados da Canonical (arquivos que so existem na arvore deles). Sem
  # informacao de depuracao: com ela o build leva horas e gera um pacote
  # -dbg de gigabytes.
  ./scripts/config --set-str LOCALVERSION "$LOCALVERSION"
  ./scripts/config --set-str SYSTEM_TRUSTED_KEYS ""
  ./scripts/config --set-str SYSTEM_REVOCATION_KEYS ""
  ./scripts/config --disable MODULE_SIG --disable MODULE_SIG_ALL
  ./scripts/config --disable DEBUG_INFO --disable DEBUG_INFO_DWARF5 \
    --disable DEBUG_INFO_DWARF_TOOLCHAIN_DEFAULT --disable DEBUG_INFO_BTF --enable DEBUG_INFO_NONE
  # O que o FliperOS precisa de fato: EDID por firmware (entradas EDID do
  # boot e resolucao personalizada) e console girado (monitor vertical).
  ./scripts/config --enable DRM_LOAD_EDID_FIRMWARE --enable FRAMEBUFFER_CONSOLE_ROTATION
  # Fora o que um PC de gabinete nao usa e que pesa no tempo de build:
  # captura de TV e webcam, drivers staging, redes de datacenter (InfiniBand,
  # Mellanox, Chelsio, QLogic), barramento CAN, ISDN, ATM, radioamador, NFC,
  # modems WWAN e sensores industriais (IIO). Video, audio, USB, Bluetooth,
  # Wi-Fi, rede comum e controles ficam como no kernel do Ubuntu.
  for opt in MEDIA_SUPPORT STAGING INFINIBAND NET_VENDOR_MELLANOX NET_VENDOR_CHELSIO \
    NET_VENDOR_QLOGIC CAN ISDN ATM HAMRADIO NFC WWAN IIO; do
    ./scripts/config --disable "$opt"
  done
  make olddefconfig > /dev/null
  for opt in DRM_LOAD_EDID_FIRMWARE FRAMEBUFFER_CONSOLE_ROTATION; do
    grep -q "^CONFIG_$opt=y" .config || { echo "CONFIG_$opt ficou desligado" >&2; exit 1; }
  done

  make -j"$(nproc)" bindeb-pkg KDEB_PKGVERSION="$KERNEL_VERSION-1fliperos" KDEB_CHANGELOG_DIST=noble \
    > "$work/make.log" 2>&1 || {
    tail -40 "$work/make.log" >&2
    exit 1
  }
  cd "$work"
  cp linux-image-*"$LOCALVERSION"*.deb linux-headers-*"$LOCALVERSION"*.deb "$out/"
  ls -la "$out"
  rm -rf "$work"
}

case ${1:-} in
  key) key ;;
  build) [[ $# -eq 2 ]] || { echo "Uso: $0 build SAIDA" >&2; exit 2; }; build "$2" ;;
  *) sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^# *//' >&2; exit 2 ;;
esac
