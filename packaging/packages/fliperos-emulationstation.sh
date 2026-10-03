# EmulationStation Desktop Edition (ES-DE) — build para o KMS, como o
# pacote do GroovyArcade (o do AUR com -DDEINIT_ON_LAUNCH=on): ao abrir um
# jogo o ES-DE solta a tela (o SDL), para o emulador pegar o DRM, e a
# retoma quando ele fecha. No console o SDL desenha pelo kmsdrm.
#
# O binario e o es-de; /usr/bin/emulationstation (o nome da tabela de
# sessoes do FliperOS) e um atalho para ele.

PKG_NAME="fliperos-emulationstation"
PKG_VERSION="3.5.0"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://es-de.org"
PKG_SUMMARY="EmulationStation Desktop Edition (build KMS para CRT)"
PKG_DESCRIPTION="Frontend grafico para lancar emuladores, com temas e listas de
jogos raspados.

Este build solta a tela ao abrir um jogo (DEINIT_ON_LAUNCH), para rodar no
console sem Xorg, como o pacote do GroovyArcade."

# As do guia de build do ES-DE para o Ubuntu (INSTALL-DEV.md), mais o BlueZ
# (o 3.5 o procura no cmake: controles Bluetooth).
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake gettext \
libharfbuzz-dev libicu-dev libsdl2-dev libavcodec-dev libavfilter-dev libavformat-dev libavutil-dev \
libfreeimage-dev libfreetype-dev libgit2-dev libcurl4-openssl-dev libpugixml-dev libasound2-dev \
libgl1-mesa-dev libpoppler-cpp-dev libbluetooth-dev"

PKG_SHLIB_TARGETS="usr/bin/es-de"

pkg_build() {
  git clone --depth 1 --branch "v$PKG_VERSION" https://gitlab.com/es-de/emulationstation-de.git "$SRC/es-de" \
    && cmake -S "$SRC/es-de" -B "$SRC/es-de/build" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr \
      -DDEINIT_ON_LAUNCH=on \
    && cmake --build "$SRC/es-de/build" -j"$(nproc)" \
    && DESTDIR="$STAGING" cmake --install "$SRC/es-de/build" \
    && ln -s es-de "$STAGING/usr/bin/emulationstation"
}
