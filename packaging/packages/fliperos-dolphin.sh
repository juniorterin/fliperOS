# Dolphin (GameCube, Wii, Triforce) na versao estavel, com os patches do
# FliperOS (packaging/patches/dolphin): o net play aberto pela linha de
# comando (--netplay host|join), que o frontend usa.
#
# Era compilado no chroot da ISO: um gabinete atualizado so pela rede ficava
# com o Dolphin da ISO que instalou, sem o net play. Como pacote, ele chega
# pelos updates (updates/packages.list) e a ISO instala o mesmo .deb. A
# distribuicao oficial para Linux e o Flatpak, que traria o runtime do KDE
# (~1 GB); sem atualizacao automatica nem estatisticas.

PKG_NAME="fliperos-dolphin"
PKG_VERSION="2609"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://dolphin-emu.org"
PKG_SUMMARY="Dolphin (GameCube/Wii) with command-line net play"
PKG_DESCRIPTION="Dolphin, the GameCube and Wii emulator, in its stable release, with
FliperOS's patch that opens net play from the command line
(--netplay host|join) for the frontend. Vulkan and OpenGL video.

Installed in /usr/local, where the FliperOS image always had it."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake \
qt6-base-dev qt6-base-private-dev libqt6svg6-dev \
libavcodec-dev libavformat-dev libavutil-dev libswscale-dev \
libxi-dev libxrandr-dev libudev-dev libevdev-dev libsfml-dev libminiupnpc-dev \
libmbedtls-dev libcurl4-openssl-dev libhidapi-dev libsystemd-dev libbluetooth-dev \
libasound2-dev libpulse-dev libpugixml-dev libbz2-dev libzstd-dev liblzo2-dev \
libpng-dev libusb-1.0-0-dev gettext \
libegl-dev libgl-dev libgles-dev libwayland-dev libvulkan-dev"

PKG_SHLIB_TARGETS="usr/local/bin/dolphin-emu usr/local/bin/dolphin-tool"
# O plugin de video do Qt e o Vulkan sao abertos na hora (dlopen).
PKG_RUNTIME_EXTRA="qt6-qpa-plugins, libvulkan1"

pkg_build() {
  local here patch dir=$SRC/dolphin
  here=$(dirname "${BASH_SOURCE[0]}")
  git clone -q --depth 1 --branch "$PKG_VERSION" https://github.com/dolphin-emu/dolphin "$dir" \
    && git -C "$dir" submodule update -q --init --recursive --depth 1 ||
    return 1
  # A versao e fixa: todo patch tem de entrar.
  for patch in "$here"/../patches/dolphin/*.patch; do
    git -C "$dir" apply "$patch" || return 1
  done
  # Sem os -dev do EGL/GL o cmake so avisa e o Dolphin sai sem o video OpenGL
  # ("Failed to initialize video backend!" no gabinete, 4 de novembro de 2026).
  cmake -S "$dir" -B "$dir/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DENABLE_AUTOUPDATE=OFF -DENABLE_ANALYTICS=OFF -DENABLE_TESTS=OFF -DENABLE_VULKAN=ON &&
    cmake --build "$dir/build" -j"$(nproc)" &&
    DESTDIR="$STAGING" cmake --install "$dir/build" ||
    return 1
  # O atalho do proprio Dolphin abriria o emulador no X do desktop; o do
  # FliperOS passa pelo fliperos-launch. O icone fica.
  rm -f "$STAGING/usr/local/share/applications/dolphin-emu.desktop"
  install -Dm644 "$dir/Data/dolphin-emu.png" "$STAGING/usr/local/share/pixmaps/dolphin-emu.png"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "$PKG_VERSION" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/dolphin"
}
