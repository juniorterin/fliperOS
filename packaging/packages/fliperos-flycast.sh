# Flycast (Dreamcast, Naomi, Naomi 2, Atomiswave) com os patches do FliperOS
# (packaging/patches/flycast): sem a tela de loading entre o frontend e o jogo,
# e o GGPO de dois a quatro gabinetes na rede local (network:GGPOPeers, que o
# gui/felink.py passa na party), cada um com os seus controles, com a rede do
# GGPO atendida a cada 1 ms (0003), e nao uma vez por quadro, e as maquinas a
# ate um quadro uma da outra (0004).
#
# Era compilado no chroot da ISO, do master do dia: um gabinete atualizado so
# pela rede ficava com o Flycast da ISO que instalou. Como pacote, ele chega
# pelos updates (updates/packages.list) e a ISO instala o mesmo .deb. O commit
# e fixo: o patch e conferido contra ele, e um commit novo e uma versao nova
# (a data no fim do PKG_VERSION, para subir sempre).

PKG_NAME="fliperos-flycast"
FLYCAST_COMMIT="7adbf3caef251b153e348df3f469a0f35878339d"
# O Setup > Emulators & Games compila o Flycast mais novo no gabinete com esta
# mesma receita, no ultimo commit do projeto (config/fliperos-emulators edge).
PKG_UPSTREAM="https://github.com/flyinghead/flycast"
PKG_COMMIT_VAR="FLYCAST_COMMIT"
PKG_VERSION="2.7.20261031"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/flyinghead/flycast"
PKG_SUMMARY="Flycast (Dreamcast, Naomi, Atomiswave) with Vulkan"
PKG_DESCRIPTION="Flycast, the Dreamcast, Naomi, Naomi 2 and Atomiswave emulator, with
Vulkan and OpenGL video and FliperOS's patches: no loading screen between
the frontend and the game, and GGPO rollback between two to four machines
on the local network, each one with its own controllers (up to four
players).

Installed in /usr/local, where the FliperOS image always had it."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake \
libcurl4-openssl-dev libminiupnpc-dev libzip-dev libao-dev libpng-dev \
libsdl2-dev libudev-dev libvulkan-dev libdrm-dev libgbm-dev libegl-dev libgl-dev \
libx11-dev libxext-dev libxi-dev libxrandr-dev libasound2-dev libpulse-dev"

PKG_SHLIB_TARGETS="usr/local/bin/flycast"
# O Vulkan e aberto na hora (dlopen).
PKG_RUNTIME_EXTRA="libvulkan1"

pkg_build() {
  local here patch dir=$SRC/flycast
  here=$(dirname "${BASH_SOURCE[0]}")
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 https://github.com/flyinghead/flycast "$FLYCAST_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD \
    && git -C "$dir" submodule update -q --init --recursive --depth 1 ||
    return 1
  # Todo patch tem de entrar: o commit e o mesmo em que foram conferidos.
  for patch in "$here"/../patches/flycast/*.patch; do
    git -C "$dir" apply "$patch" || return 1
  done
  cmake -S "$dir" -B "$dir/build" -DCMAKE_BUILD_TYPE=Release -DUSE_VULKAN=ON &&
    cmake --build "$dir/build" -j"$(nproc)" ||
    return 1
  install -Dm755 "$dir/build/flycast" "$STAGING/usr/local/bin/flycast"
  # Icone do menu do LXDE (config/applications/fliperos-flycast.desktop).
  install -Dm644 "$dir/shell/linux/flycast.png" "$STAGING/usr/local/share/pixmaps/flycast.png"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  git -C "$dir" log -1 --format='%cs %h' > "$STAGING/usr/local/share/fliperos/emulator-versions.d/flycast"
}
