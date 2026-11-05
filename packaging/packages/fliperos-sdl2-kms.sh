# SDL2 com os patches de KMS do GroovyArcade, so para o GroovyMAME.
#
# O GroovyMAME no console (sem Xorg) troca o modo de cada jogo assim: o
# Switchres pendura o modo no conector (o ATTACHMODE do patch 06 do kernel)
# e o SDL troca para ele. O SDL do Ubuntu le a lista de modos uma vez so e
# ficava no modo do boot (packaging/patches/sdl2). O pacote do GroovyArcade
# (gitlab.com/groovyarcade/packages, package/sdl2) troca o SDL do sistema; este
# fica numa pasta propria, que o config/fliperos-groovymame poe no
# LD_LIBRARY_PATH: o resto do sistema segue com o SDL do Ubuntu.
#
# O fonte e o do proprio Ubuntu (apt-get source), com o mesmo build do
# pacote dele: so os dois patches mudam.

PKG_NAME="fliperos-sdl2-kms"
PKG_VERSION="2.30.0"
PKG_REVISION="1fliperos1"
PKG_SECTION="libs"
PKG_HOMEPAGE="https://www.libsdl.org"
PKG_SUMMARY="SDL2 with the GroovyArcade KMS mode patches, for GroovyMAME"
PKG_DESCRIPTION="Ubuntu's SDL2 with two patches from GroovyArcade: the KMS/DRM
backend re-reads the connector modes on every query, so it sees the mode
Switchres adds for each game, and restores the original mode when the window
closes.

Installed in /usr/local/lib/fliperos/sdl2-kms, loaded only by GroovyMAME."

PKG_BUILD_DEPS="dpkg-dev devscripts"

PKG_SHLIB_TARGETS="usr/local/lib/fliperos/sdl2-kms/libSDL2-2.0.so.0"

pkg_build() {
  local here patch dir lib
  here=$(dirname "${BASH_SOURCE[0]}")
  # As dependencias de build sao as do pacote do Ubuntu (deb-src).
  sed -i 's/^Types: deb$/Types: deb deb-src/' /etc/apt/sources.list.d/ubuntu.sources \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get build-dep -y -qq libsdl2 > /dev/null \
    && (cd "$SRC" && apt-get source -qq libsdl2) ||
    return 1
  dir=$(ls -d "$SRC/libsdl2-$PKG_VERSION"*/ | head -1)
  [[ -d $dir ]] || return 1
  for patch in "$here"/../patches/sdl2/*.patch; do
    patch -d "$dir" -Np1 --no-backup-if-mismatch < "$patch" || return 1
  done
  (cd "$dir" && DEB_BUILD_OPTIONS="nocheck nodoc parallel=$(nproc)" \
    dpkg-buildpackage -b -uc -us -Pnocheck,nodoc > "$SRC/build.log" 2>&1) ||
    { tail -40 "$SRC/build.log"; return 1; }
  # A do pacote libsdl2-2.0-0 (ja sem os simbolos de depuracao).
  lib=$(find "$dir/debian/libsdl2-2.0-0" -name 'libSDL2-2.0.so.0.*' -type f | head -1)
  [[ -f $lib ]] && install -Dm644 "$lib" "$STAGING/usr/local/lib/fliperos/sdl2-kms/libSDL2-2.0.so.0"
}
