# RAHasher, a ferramenta do RetroAchievements (do RALibretro) que calcula o
# hash com que o site reconhece um jogo: o mesmo rcheevos dos emuladores. O
# selo das conquistas do frontend (gui/fecheevos.py) a usa nos jogos de disco
# (PlayStation, PS2, GameCube, Dreamcast, Sega CD, Saturn, PC Engine CD...),
# cujo hash le partes do disco (o executavel de boot, a tabela de arquivos),
# tambem dentro de um CHD; os de cartucho e de arcade o frontend calcula
# sozinho.
#
# A tag e fixa: uma tag nova e uma versao nova.

PKG_NAME="fliperos-rahasher"
# A tag do RALibretro.
PKG_VERSION="1.8.4"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/RetroAchievements/RALibretro"
PKG_SUMMARY="RAHasher: the RetroAchievements game hash (CHD included)"
PKG_DESCRIPTION="RAHasher, from RetroAchievements' RALibretro: the hash that
retroachievements.org uses to recognise a game, with the same rcheevos code
as the emulators, including disc images in CHD.

FliperOS's frontend uses it to show how many achievements each disc game
has. Installed as /usr/local/bin/RAHasher."

PKG_BUILD_DEPS="build-essential git ca-certificates"

PKG_SHLIB_TARGETS="usr/local/bin/RAHasher"

pkg_build() {
  local dir=$SRC/ralibretro
  git clone -q --depth 1 --branch "$PKG_VERSION" https://github.com/RetroAchievements/RALibretro "$dir" &&
    git -C "$dir" submodule update -q --init --depth 1 src/miniz src/RAInterface src/rcheevos src/libchdr ||
    return 1
  # HAVE_CHD: o libchdr (com o zlib, o lzma e o zstd dele) entra no binario.
  make -C "$dir" -f Makefile.RAHasher HAVE_CHD=1 -j"$(nproc)" > "$SRC/build.log" 2>&1 ||
    { tail -40 "$SRC/build.log"; return 1; }
  install -Dm755 "$dir/bin64/RAHasher" "$STAGING/usr/local/bin/RAHasher"
  install -Dm644 "$dir/COPYING" "$STAGING/usr/local/share/doc/fliperos-rahasher/COPYING"
}
