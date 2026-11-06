# Supermodel (Sega Model 3), SDL2 + OpenGL, em X11 pelo fliperos-x11-run (o
# projeto nao tem caminho KMS/DRM). Com o Games.xml (os jogos que ele
# reconhece) e a configuracao padrao em /usr/local/share/supermodel.
#
# Era compilado no chroot da ISO, do master do dia: um gabinete atualizado so
# pela rede ficava com o Supermodel da ISO que instalou. Como pacote, ele
# chega pelos updates (updates/packages.list) e a ISO instala o mesmo .deb. O
# commit e fixo; um commit novo e uma versao nova (a data no fim).

PKG_NAME="fliperos-supermodel"
SUPERMODEL_COMMIT="5db27c33ade2d70f837057737963f89fdf40ccd8"
PKG_VERSION="0.3a.20261106"
PKG_REVISION="1fliperos1"
# O Setup > Emulators & Games compila o Supermodel mais novo no gabinete com
# esta mesma receita, no ultimo commit do projeto (config/fliperos-emulators edge).
PKG_UPSTREAM="https://github.com/trzy/Supermodel"
PKG_COMMIT_VAR="SUPERMODEL_COMMIT"
PKG_SECTION="games"
PKG_HOMEPAGE="https://www.supermodel3.com"
PKG_SUMMARY="Supermodel (Sega Model 3)"
PKG_DESCRIPTION="Supermodel, the Sega Model 3 arcade emulator, with SDL2 and OpenGL, its
game list (Games.xml) and default configuration.

Installed in /usr/local, where the FliperOS image always had it."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates \
libsdl2-dev libsdl2-net-dev libglu1-mesa-dev zlib1g-dev"

PKG_SHLIB_TARGETS="usr/local/bin/supermodel"

pkg_build() {
  local dir=$SRC/supermodel
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 "$PKG_UPSTREAM" "$SUPERMODEL_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD ||
    return 1
  # Makefile proprio (sem CMake), como o README do projeto manda no Linux.
  make -C "$dir" -f Makefiles/Makefile.UNIX -j"$(nproc)" &&
    install -Dm755 "$dir/bin/supermodel" "$STAGING/usr/local/bin/supermodel" ||
    return 1
  mkdir -p "$STAGING/usr/local/share/supermodel"
  cp -r "$dir/Config" "$dir/Assets" "$STAGING/usr/local/share/supermodel/" || return 1
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  git -C "$dir" log -1 --format='%cs %h' > "$STAGING/usr/local/share/fliperos/emulator-versions.d/supermodel"
}
