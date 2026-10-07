#!/usr/bin/env bash
# Compila o OpenBOR 3.0 build 6391 (a tag v6391), o dos paks antigos que o
# OpenBOR 4 da imagem recusa (config/fliperos-openbor), num Ubuntu 24.04 no
# Docker, e o poe em config/openbor-legacy. O binario vai no repo: assim os
# updates (que levam o config/) o entregam aos gabinetes ja instalados.
#
#   bash tools/build-openbor-legacy.sh
#
# Linka contra as bibliotecas do 24.04 (SDL2, SDL2_gfx, libpng, vorbis,
# vpx): as do runtime estao nos pacotes do fliperos-mkiso.sh e do
# tools/cabinet-update.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
out=config/openbor-legacy
mkdir -p "$out"
dir=$(pwd)
command -v cygpath > /dev/null && dir=$(cygpath -w "$dir")
MSYS_NO_PATHCONV=1 docker run --rm -i -v "$dir:/w" -w /w ubuntu:24.04 bash -s << 'EOF'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends git ca-certificates build-essential yasm pkg-config \
  libsdl2-dev libsdl2-gfx-dev libvorbis-dev libpng-dev libvpx-dev > /dev/null
git init -q /tmp/openbor
git -C /tmp/openbor fetch -q --depth 1 https://github.com/DCurrent/openbor 494708eb34e71d1afda237873907701c4ec3a569
git -C /tmp/openbor -c advice.detachedHead=false checkout -q FETCH_HEAD
cd /tmp/openbor/engine
# Tela cheia de fabrica, como o OpenBOR 4 do fliperos-mkiso.sh.
sed -i 's/^static int isFull = 0;/static int isFull = 1;/' sdl/menu.c
sed -i 's/^\([[:space:]]*savedata\.fullscreen = \)0;/\11;/' openbor.c
grep -q '^static int isFull = 1;' sdl/menu.c
grep -q 'savedata.fullscreen = 1;' openbor.c
# O GCC 13 recusa o codigo de 2019 com -Werror (e sem o -fcommon), e o
# _FORTIFY_SOURCE do Ubuntu derruba o jogo ao carregar os modelos ("buffer
# overflow detected", visto no gabinete).
sed -i 's/ -Werror / -fcommon -Wno-error -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=0 /' Makefile
grep -q -- '-fcommon -Wno-error -U_FORTIFY_SOURCE' Makefile
# O version.sh tira o numero do svn; sem ele o build sai sem numero.
cat > version.h << 'VERSION'
#ifndef VERSION_H
#define VERSION_H
#define VERSION_NAME "OpenBOR"
#define VERSION_MAJOR "3"
#define VERSION_MINOR "0"
#define VERSION_BUILD "6391"
#define VERSION "v"VERSION_MAJOR"."VERSION_MINOR" Build "VERSION_BUILD
#endif
VERSION
make -j"$(nproc)" BUILD_LINUX=1 LNXDEV=/usr/bin PREFIX= GCC_TARGET=x86_64-linux-gnu SDKPATH=/usr > /tmp/make.log 2>&1 ||
  { tail -30 /tmp/make.log; exit 1; }
install -m755 OpenBOR /w/config/openbor-legacy/OpenBOR-3.0
install -m644 ../LICENSE /w/config/openbor-legacy/LICENSE
EOF
ls -l "$out"
