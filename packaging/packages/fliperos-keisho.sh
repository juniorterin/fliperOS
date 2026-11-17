# Keisho (Sega Model 1, 2 e 3; ate novembro de 2026 se chamava SM2-Emu), com
# OpenGL e Vulkan, em X11 pelo fliperos-x11-run, e os patches do FliperOS
# (packaging/patches/keisho). O Setup escolhe o Vulkan ou o OpenGL pelo driver
# da placa (lib/emulators.sh, graphics_backend no keisho.ini). Substitui o
# Supermodel no Model 3 e o build no gabinete (config/fliperos-sm2emu) no
# Model 2.
#
# Com o games.xml (os jogos que ele reconhece) em /usr/local/share/keisho,
# onde o binario o procura (../share/keisho). O commit e fixo: o patch e
# conferido contra ele, e um commit novo e uma versao nova (a data no fim).

PKG_NAME="fliperos-keisho"
KEISHO_COMMIT="d7c7dd885bcf46bfc67c30ce70fa6fedb0866168"
PKG_VERSION="0.9.63.20261116"
PKG_REVISION="1fliperos1"
# O Setup > Emulators & Games compila o Keisho mais novo no gabinete com esta
# mesma receita, no ultimo commit do projeto (config/fliperos-emulators edge).
PKG_UPSTREAM="https://github.com/Keisho-Emu/Keisho"
PKG_COMMIT_VAR="KEISHO_COMMIT"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/Keisho-Emu/Keisho"
PKG_SUMMARY="Keisho (Sega Model 1, 2 and 3) with Vulkan"
PKG_DESCRIPTION="Keisho, the Sega Model 1, Model 2 and Model 3 arcade emulator (formerly
SM2-Emu), with Vulkan and OpenGL video, its game list (games.xml) and
FliperOS's light gun patch.

Installed in /usr/local, like the other FliperOS emulators."

# Os do README do projeto, mais o Vulkan; o SDL3, o HarfBuzz e o pugixml
# vendidos em 3rdparty/ usam os do sistema quando ha (bem mais rapido).
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake ninja-build glslc \
libgl-dev libegl-dev libvulkan-dev libpugixml-dev libcurl4-openssl-dev \
libharfbuzz-dev libfontconfig-dev \
libx11-dev libxext-dev libxrandr-dev libxcursor-dev \
libxi-dev libxfixes-dev libxss-dev libxrender-dev libxtst-dev \
libasound2-dev libpulse-dev libudev-dev \
libwayland-dev libwayland-bin libxkbcommon-dev libdecor-0-dev"

PKG_SHLIB_TARGETS="usr/local/bin/keisho"
# O Vulkan pode ser aberto na hora (dlopen) e nao aparecer no shlibdeps.
PKG_RUNTIME_EXTRA="libvulkan1"
# Compila o emulador e o SDL3 dele: mais que os outros.
PKG_EDGE_WAIT="10 to 20 minutes"

pkg_build() {
  local here patch dir=$SRC/keisho
  here=$(dirname "${BASH_SOURCE[0]}")
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 "$PKG_UPSTREAM" "$KEISHO_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD \
    && git -C "$dir" submodule update -q --init --recursive --depth 1 ||
    return 1
  # Todo patch tem de entrar: o commit e o mesmo em que foram conferidos.
  for patch in "$here"/../patches/keisho/*.patch; do
    [[ -f $patch ]] || continue
    git -C "$dir" apply "$patch" || return 1
  done
  cmake -S "$dir" -B "$dir/build" -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/usr/local -DSM2_BUILD_TESTS=OFF -DSM2_BUILD_VULKAN=ON \
    -DSM2_ENABLE_VALIDATION=OFF -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON &&
    cmake --build "$dir/build" -j"$(nproc)" &&
    DESTDIR=$STAGING cmake --install "$dir/build" ||
    return 1
  # O menu do LXDE ja tem o Model 2 e o Model 3 do FliperOS
  # (config/applications); o lancador do projeto seria um terceiro item.
  rm -rf "$STAGING/usr/local/share/applications"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  git -C "$dir" log -1 --format='%cs %h' > "$STAGING/usr/local/share/fliperos/emulator-versions.d/keisho"
}
