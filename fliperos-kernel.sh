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
# O build: sobe a cada patch novo ou mudado, e o kernel vira 6.18.54-15khz.N,
# um pacote novo (linux-image-6.18.54-15khz.N) instalado ao lado do anterior,
# que o Limine guarda como "previous kernel". Com o mesmo nome o pacote seria
# trocado no lugar, sem kernel para voltar; e com a mesma versao os gabinetes
# nem viam a troca (o patch 10 chegou na 0.20 com a versao da 0.8.1). O
# KERNEL_PATCHES_SHA256 e o dos patches deste build: o teste falha se eles
# mudam sem o KERNEL_BUILD subir (tests/test_build.py).
KERNEL_BUILD="2"
KERNEL_PATCHES_SHA256="82262372e1e29199f2b4e3fc0dc8c1e764388c8884d88ebad40d89ab78024dba"
LOCALVERSION="-15khz"
((KERNEL_BUILD > 1)) && LOCALVERSION="-15khz.$KERNEL_BUILD"
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
patches="$src/patches/kernel-15khz/$KERNEL_SERIES"

key() {
  [[ -d $patches ]] || { echo "No patches for $KERNEL_SERIES in $patches" >&2; exit 1; }
  printf '%s-%s\n' "$KERNEL_VERSION" \
    "$(cat "$patches"/*.patch "${BASH_SOURCE[0]}" | sha256sum | cut -c1-12)"
}

build() {
  local out=$1 work seed pkg
  # Patch novo ou mudado sem um KERNEL_BUILD novo: os gabinetes nao veriam o
  # kernel (a mesma versao de antes).
  if [[ $(cat "$patches"/*.patch | sha256sum | cut -d' ' -f1) != "$KERNEL_PATCHES_SHA256" ]]; then
    echo "The kernel patches changed: raise KERNEL_BUILD and update KERNEL_PATCHES_SHA256" >&2
    exit 1
  fi
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
  [[ -n $seed ]] || { echo ".config seed not found in $pkg" >&2; exit 1; }

  wget -q "https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_VERSION%%.*}.x/linux-$KERNEL_VERSION.tar.xz"
  tar xf "linux-$KERNEL_VERSION.tar.xz"
  cp "$seed" "linux-$KERNEL_VERSION/.config"
  cd "linux-$KERNEL_VERSION"
  for p in "$patches"/*.patch; do
    echo "Applying $(basename "$p")"
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
  # Sem o ftrace: a cada modulo carregado ele procura no kallsyms cada funcao
  # do modulo (test_for_valid_rec), uma busca linear por vez. No amdgpu sao
  # uns 4 s com o boot inteiro parado; no i915, 0,6 dos 0,86 s da carga. O
  # STACK_TRACER do Ubuntu religaria o FUNCTION_TRACER (select).
  ./scripts/config --disable FUNCTION_TRACER --disable STACK_TRACER
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
    grep -q "^CONFIG_$opt=y" .config || { echo "CONFIG_$opt ended up disabled" >&2; exit 1; }
  done
  ! grep -q '^CONFIG_DYNAMIC_FTRACE=y' .config || { echo "CONFIG_DYNAMIC_FTRACE ended up enabled" >&2; exit 1; }

  make -j"$(nproc)" bindeb-pkg KDEB_PKGVERSION="$KERNEL_VERSION-${KERNEL_BUILD}fliperos" KDEB_CHANGELOG_DIST=noble \
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
  build) [[ $# -eq 2 ]] || { echo "Usage: $0 build OUTPUT" >&2; exit 2; }; build "$2" ;;
  *) sed -n '5,6p' "${BASH_SOURCE[0]}" | sed 's/^# *//' >&2; exit 2 ;;
esac
