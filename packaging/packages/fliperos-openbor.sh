# OpenBOR (beat 'em ups), SDL2, em X11 pelo fliperos-x11-run. O binario vai
# para /usr/local/lib/openbor/OpenBOR; o comando openbor (config/
# fliperos-openbor, pelo fliperos-rootfs.sh) entra na pasta dos Paks antes e
# escolhe entre ele e o 3.0 dos paks antigos.
#
# Era compilado no chroot da ISO: um gabinete atualizado so pela rede ficava
# com o OpenBOR da ISO que instalou. Como pacote, ele chega pelos updates
# (updates/packages.list) e a ISO instala o mesmo .deb. As tags antigas nao
# tem o CMake: o commit e o do master, fixo; um commit novo e uma versao nova.

PKG_NAME="fliperos-openbor"
OPENBOR_COMMIT="787b6770409935137579715febf80cf7a529b748"
PKG_VERSION="7533.20260922"
PKG_REVISION="1fliperos1"
# O Setup > Emulators & Games compila o OpenBOR mais novo no gabinete com esta
# mesma receita, no ultimo commit do projeto (config/fliperos-emulators edge).
PKG_UPSTREAM="https://github.com/DCurrent/openbor"
PKG_COMMIT_VAR="OPENBOR_COMMIT"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/DCurrent/openbor"
PKG_SUMMARY="OpenBOR (beat 'em up engine), full screen by default"
PKG_DESCRIPTION="OpenBOR, the beat 'em up engine, opening in full screen in the pak
selector and in the game (the window mode showed only the middle of a
game at 2x on a 15 kHz screen).

Installed in /usr/local/lib/openbor, where the FliperOS image always had it."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake ninja-build \
libsdl2-dev libvorbis-dev libpng-dev libvpx-dev libsdl2-gfx-dev"

PKG_SHLIB_TARGETS="usr/local/lib/openbor/OpenBOR"

pkg_build() {
  local dir=$SRC/openbor
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 "$PKG_UPSTREAM" "$OPENBOR_COMMIT" \
    && git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD ||
    return 1
  # Tela cheia de fabrica, no seletor de paks (engine/sdl/menu.c, isFull) e
  # no jogo (sem o Saves/default.cfg): em janela o OpenBOR abre em 2x de
  # tamanho fixo (640x480 num modo de 320x240, so o meio aparece, visto no
  # gabinete); em tela cheia (SDL_WINDOW_FULLSCREEN_DESKTOP) escala para o
  # modo. O menu de video dele ainda troca. Se o codigo mudou e a troca nao
  # pega, o build para.
  sed -i 's/^static int isFull = 0;/static int isFull = 1;/' "$dir/engine/sdl/menu.c" &&
    sed -i 's/^\([[:space:]]*savedata\.fullscreen = \)0;/\11;/' "$dir/engine/openbor.c" &&
    grep -q '^static int isFull = 1;' "$dir/engine/sdl/menu.c" &&
    grep -q 'savedata.fullscreen = 1;' "$dir/engine/openbor.c" ||
    { echo "error: patch failed: the full screen default no longer fits OpenBOR" >&2; return 1; }
  cmake -S "$dir" -B "$dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_LINUX=ON -DTARGET_ARCH=AMD64 &&
    cmake --build "$dir/build" --parallel &&
    install -Dm755 "$dir/engine/releases/LINUX/OpenBOR" "$STAGING/usr/local/lib/openbor/OpenBOR" &&
    install -Dm644 "$dir/engine/resources/OpenBOR_Icon_128x128.png" "$STAGING/usr/local/share/pixmaps/openbor.png" ||
    return 1
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  git -C "$dir" log -1 --format='%h' > "$STAGING/usr/local/share/fliperos/emulator-versions.d/openbor"
}
