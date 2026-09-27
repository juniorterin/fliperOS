# Attract-Mode Plus — build DRM/KMS.
#
# Por que o pacote e nosso e nao o upstream: o USE_DRM=1 do Makefile e
# descrito como "alternative to X11" e vem comentado por padrao. Build DRM e
# build X11 sao mutuamente exclusivos, e este pacote e o DRM de proposito —
# o FliperOS roda no console, sem servidor grafico. Quem quiser attractplus
# dentro do Xorg precisa de outro build.
#
# O SFML nao entra como dependencia: o projeto compila o proprio, de
# extlibs/SFML, que e onde esta o backend DRM (WindowImplDRM/DRMContext).

PKG_NAME="fliperos-attractplus"
PKG_VERSION="3.2.3"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/oomek/attractplus"
PKG_SUMMARY="Attract-Mode Plus (build KMS/DRM para CRT)"
PKG_DESCRIPTION="Frontend grafico para lancar emuladores, compilado com
USE_DRM=1: desenha direto no KMS/DRM, sem Xorg.

Este build nao roda dentro de uma sessao X — no attractplus o caminho DRM
substitui o X11, nao convive com ele.

Inclui o tema AdvanceMenu, que reproduz a aparencia do AdvanceMENU (lista de
texto com snapshot) e se dimensiona pela resolucao, para ficar legivel em
640x240."

# cmake entra porque o SFML embarcado e compilado por cmake, nao pelo make
# do attractplus (regra sfmlbuild do Makefile).
# Duas coisas que o Compile.md do upstream nao lista e o build exige:
# ogg/vorbis/flac (modulo Audio do SFML embarcado, o cmake dele para em
# "Could NOT find Vorbis") e expat (src/scraper_base.cpp inclui expat.h).
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake \
libopenal-dev zlib1g-dev libfreetype-dev libjpeg-dev \
libogg-dev libvorbis-dev libflac-dev \
libexpat1-dev \
libavformat-dev libavcodec-dev libswscale-dev libavutil-dev libswresample-dev \
libgl-dev libglu1-mesa-dev libegl-dev libdrm-dev libgbm-dev \
libarchive-dev libcurl4-openssl-dev libudev-dev"

# O dispatcher de sessao procura por este binario; e tambem o que da o Depends.
PKG_SHLIB_TARGETS="usr/bin/attractplus"

# Os passos sao encadeados com && de proposito: o errexit do driver fica
# suspenso dentro de uma funcao chamada em "|| err", entao sem o && um make
# que falhasse deixaria o "make install" rodar em cima de um build quebrado.
pkg_build() {
  # extlibs/SFML vem no proprio repositorio, nao como submodulo, entao o
  # clone raso basta.
  git clone --depth 1 --branch "$PKG_VERSION" \
      https://github.com/oomek/attractplus.git "$SRC/attractplus" \
    && make -C "$SRC/attractplus" USE_DRM=1 prefix=/usr -j"$(nproc)" \
    && make -C "$SRC/attractplus" install USE_DRM=1 prefix=/usr DESTDIR="$STAGING" \
    && cp -r "$(dirname "${BASH_SOURCE[0]}")/../assets/attractplus-layouts/AdvanceMenu" \
             "$STAGING/usr/share/attractplus/layouts/AdvanceMenu"
}
