# EmulationStation Desktop Edition (ES-DE) — build para o KMS, como o
# pacote do GroovyArcade (o do AUR com -DDEINIT_ON_LAUNCH=on): ao abrir um
# jogo o ES-DE solta a tela (o SDL), para o emulador pegar o DRM, e a
# retoma quando ele fecha. No console o SDL desenha pelo kmsdrm.
#
# O binario e o es-de; /usr/bin/emulationstation (o nome da tabela de
# sessoes do FliperOS) e um atalho para ele.

PKG_NAME="fliperos-emulationstation"
PKG_VERSION="3.5.0"
PKG_REVISION="1fliperos2"
PKG_SECTION="games"
PKG_HOMEPAGE="https://es-de.org"
PKG_SUMMARY="EmulationStation Desktop Edition (KMS build for CRT)"
PKG_DESCRIPTION="Graphical frontend for launching emulators, with themes and
scraped game lists.

This build releases the screen when a game opens (DEINIT_ON_LAUNCH), to run
on the console without Xorg, like the GroovyArcade package."

# As do guia de build do ES-DE para o Ubuntu (INSTALL-DEV.md), mais o BlueZ
# (o 3.5 o procura no cmake: controles Bluetooth).
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake gettext \
libharfbuzz-dev libicu-dev libsdl2-dev libavcodec-dev libavfilter-dev libavformat-dev libavutil-dev \
libfreeimage-dev libfreetype-dev libgit2-dev libcurl4-openssl-dev libpugixml-dev libasound2-dev \
libgl1-mesa-dev libpoppler-cpp-dev libbluetooth-dev"

PKG_SHLIB_TARGETS="usr/bin/es-de"

pkg_build() {
  local here patch
  here=$(dirname "${BASH_SOURCE[0]}")
  git clone --depth 1 --branch "v$PKG_VERSION" https://gitlab.com/es-de/emulationstation-de.git "$SRC/es-de" ||
    return 1
  # Os nossos patches (packaging/patches/emulationstation), cada um com o
  # motivo no proprio cabecalho: o esticado horizontal do 640x240.
  for patch in "$here"/../patches/emulationstation/*.patch; do
    patch -d "$SRC/es-de" -p1 < "$patch" || return 1
  done
  cmake -S "$SRC/es-de" -B "$SRC/es-de/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr \
      -DDEINIT_ON_LAUNCH=on \
    && cmake --build "$SRC/es-de/build" -j"$(nproc)" \
    && DESTDIR="$STAGING" cmake --install "$SRC/es-de/build" \
    && ln -s es-de "$STAGING/usr/bin/emulationstation"
}
