# xemu-chihiro: o xemu com a placa Sega Chihiro (o arcade em cima do hardware
# do Xbox: Outrun 2 e 2 SP, House of the Dead III, Virtua Cop 3, Ghost Squad,
# Crazy Taxi High Roller, Wangan Midnight Maximum Tune 1 e 2, Ollie King,
# Gundam Battle Operating Simulator), o fork do Tovarichtch do xemu.
#
# Este pacote nao vai na ISO (PKG_OPTIONAL): o Setup o baixa pronto quando o
# primeiro jogo da pasta chihiro e aberto (config/fliperos-emulators, tipo
# package), e um gabinete que o tem sobe de versao pelos updates
# (updates/packages.list, QUANDO "installed"). Como o odin.
#
# O comando que o frontend abre e o config/fliperos-chihiro (vem com o
# sistema); este pacote traz so o programa, /usr/local/bin/xemu-chihiro (com
# esse nome para nao tomar o lugar de um xemu do Xbox, que e outro programa).
# O commit e fixo: o projeto nao tem release deste fork, e um commit novo e uma
# versao nova (a data no fim do PKG_VERSION).
#
# Compilado como o build.sh do projeto manda no Linux: -march=x86-64-v2 (qualquer
# CPU x86-64 de 2009 em diante, o i7-870 inclusive), sem LTO.
#
# Quem roda ele precisa de OpenGL 4.0 ou mais (o renderizador padrao) ou
# Vulkan; um Intel HD antigo (Ironlake, GL 2.1) nao abre.

PKG_NAME="fliperos-xemu-chihiro"
XEMU_CHIHIRO_COMMIT="e66fe47cdaa781966ffd9a7112200ade04c1a531"
PKG_VERSION="0.8.134.20261003"
PKG_REVISION="1fliperos1"
PKG_OPTIONAL=1
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/Tovarichtch/xemu"
PKG_SUMMARY="xemu with the Sega Chihiro arcade board (Tovarichtch fork)"
PKG_DESCRIPTION="The xemu emulator with the Sega Chihiro arcade board, from the
Tovarichtch fork: OutRun 2 and 2 SP, The House of the Dead III, Virtua Cop 3,
Ghost Squad, Crazy Taxi High Roller, Wangan Midnight Maximum Tune 1 and 2,
Ollie King and Gundam Battle Operating Simulator. Its games live in
~/roms/chihiro (Chihiro netboot images, .bin) and its BIOS in ~/bios/chihiro.

The program goes to /usr/local/bin/xemu-chihiro; the fliperos-chihiro command
in front of it is FliperOS's."

# Os do debian/control do projeto (o libglib2.0-dev vem com o libslirp-dev) e os
# do SDL3, que o meson baixa e compila junto (subprojects/sdl3.wrap, o Ubuntu
# 24.04 nao o tem): as bibliotecas de X11, som e entrada que ele usa e as do
# Wayland, que o meson.build dele exige no Linux mesmo sem usar (a build
# falha com "wayland-client not found").
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates curl cmake ninja-build \
python3 python3-pip python3-venv python3-tomli python3-yaml flex bison \
libepoxy-dev libpixman-1-dev libsamplerate0-dev zlib1g-dev libssl-dev libpcap-dev \
libslirp-dev libvulkan-dev libusb-1.0-0-dev libcurl4-gnutls-dev libpipewire-0.3-dev \
libgl-dev libegl-dev libdrm-dev libgbm-dev libwayland-dev libwayland-bin wayland-protocols \
libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxfixes-dev \
libxss-dev libxrender-dev libxtst-dev libxkbcommon-dev \
libasound2-dev libpulse-dev libudev-dev libdbus-1-dev"

PKG_SHLIB_TARGETS="usr/local/bin/xemu-chihiro"
# O Vulkan e aberto na hora (volk, dlopen): nao aparece no shlibdeps.
PKG_RUNTIME_EXTRA="libvulkan1"

pkg_build() {
  local here patch dir=$SRC/xemu
  here=$(dirname "${BASH_SOURCE[0]}")
  # So o commit (sem o historico de 128 mil commits do xemu); os submodulos
  # (roms/ do QEMU) nao entram: o build.sh so faz o i386-softmmu.
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 https://github.com/Tovarichtch/xemu "$XEMU_CHIHIRO_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD ||
    return 1
  # Todo patch tem de entrar: o commit e o mesmo em que foram conferidos.
  for patch in "$here"/../patches/xemu-chihiro/*.patch; do
    [[ -f $patch ]] || continue
    git -C "$dir" apply "$patch" || return 1
  done
  # O scripts/xemu-version.sh le o XEMU_VERSION (sem o .git de um clone cheio).
  echo "$PKG_VERSION" > "$dir/XEMU_VERSION"
  # O build.sh do projeto: configure + make + dist/xemu.
  (cd "$dir" && ./build.sh -j"$(nproc)" --disable-docs) || return 1
  install -Dm755 "$dir/dist/xemu" "$STAGING/usr/local/bin/xemu-chihiro" &&
    install -Dm644 "$dir/dist/LICENSE.txt" "$STAGING/usr/local/share/doc/fliperos-xemu-chihiro/LICENSE.txt" &&
    install -Dm644 "$dir/ui/icons/xemu_256x256.png" "$STAGING/usr/local/share/pixmaps/xemu-chihiro.png" ||
    return 1
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "$PKG_VERSION" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/xemu-chihiro"
}
