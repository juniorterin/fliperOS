# Odin (Sega Hikaru e os arcades 3D da Gaelco: ATV Track, Smashing Drive,
# Football Power, Radikal Bikers, Speed Up, Surf Planet), o emulador de baixo
# nivel do Tovarichtch (um fork do Valkyrie), com OpenGL 4.3 ou Vulkan, em X11
# pelo fliperos-x11-run.
#
# Este pacote nao vai na ISO (PKG_OPTIONAL): o Setup o baixa pronto quando o
# primeiro jogo da pasta odin e aberto (config/fliperos-emulators, tipo
# package), e um gabinete que o tem sobe de versao pelos updates
# (updates/packages.list, QUANDO "installed"). Como o do hbgroovymame, mas
# compila em minutos, nao em horas.
#
# O comando que o frontend abre e o config/fliperos-odin (vem com o sistema);
# este pacote traz o programa (/usr/local/bin/odin) e os dados dele
# (/usr/local/share/odin: os shaders e os filtros de CRT, onde o binario os
# procura, ../share/odin). O commit e fixo: sem release no projeto, e um commit
# novo e uma versao nova (a data no fim do PKG_VERSION).
#
# Compilado sem -march=native (ODIN_NATIVE=OFF): o .deb roda em qualquer CPU
# x86-64 dos gabinetes, nao so na do build.

PKG_NAME="fliperos-odin"
ODIN_COMMIT="666943d8a7683d922685596f6feba7340e95b3fe"
PKG_VERSION="0.1.1.20261118"
PKG_REVISION="1fliperos1"
PKG_OPTIONAL=1
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/Tovarichtch/Odin"
PKG_SUMMARY="Odin (Sega Hikaru and Gaelco 3D arcade emulator)"
PKG_DESCRIPTION="Odin, the low level emulator of the Sega Hikaru (Air Trix, Brave
Firefighters, Planet Harriers, NASCAR Arcade, Star Wars Racer Arcade, Cyber
Troopers Virtual-On Force) and of the Gaelco 3D boards (ATV Track, Smashing
Drive, Football Power, Radikal Bikers, Speed Up, Surf Planet), with OpenGL
4.3 or Vulkan video. Its games live in ~/roms/odin.

The program goes to /usr/local/bin/odin and its data to /usr/local/share/odin;
the fliperos-odin command in front of it is FliperOS's."

# Os do INSTALL do projeto; o SDL3, o GLEW, o jansson e os headers do Vulkan
# vem de 3rdparty/ (o Ubuntu 24.04 nao tem o SDL3), compilados junto, e
# ficam dentro do binario (SDL_STATIC).
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates cmake ninja-build gawk \
glslang-tools libgl-dev libegl-dev libvulkan-dev \
libx11-dev libxext-dev libxrandr-dev libxcursor-dev libxi-dev libxfixes-dev \
libxss-dev libxrender-dev libxtst-dev libxkbcommon-dev \
libasound2-dev libpulse-dev libudev-dev"

PKG_SHLIB_TARGETS="usr/local/bin/odin"
# O Vulkan e aberto na hora (dlopen): nao aparece no shlibdeps.
PKG_RUNTIME_EXTRA="libvulkan1"

pkg_build() {
  local here patch dir=$SRC/odin
  here=$(dirname "${BASH_SOURCE[0]}")
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 https://github.com/Tovarichtch/Odin "$ODIN_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD \
    && git -C "$dir" submodule update -q --init --recursive --depth 1 ||
    return 1
  # Todo patch tem de entrar: o commit e o mesmo em que foram conferidos.
  for patch in "$here"/../patches/odin/*.patch; do
    [[ -f $patch ]] || continue
    git -C "$dir" apply "$patch" || return 1
  done
  # Sem CMAKE_BUILD_TYPE: o Release desliga os asserts (INSTALL do projeto).
  cmake -S "$dir" -B "$dir/build" -G Ninja -DCMAKE_INSTALL_PREFIX=/usr/local \
    -DODIN_NATIVE=OFF -DODIN_BUNDLED_LIBS=ON \
    -DODIN_VERSION="$PKG_VERSION" &&
    cmake --build "$dir/build" -j"$(nproc)" &&
    DESTDIR=$STAGING cmake --install "$dir/build" ||
    return 1
  # O menu do LXDE tem o do FliperOS (config/applications/fliperos-odin.desktop):
  # o do projeto seria um segundo item, que abre fora do CRT.
  rm -rf "$STAGING/usr/local/share/applications"
  # O icone do menu do desktop.
  install -Dm644 "$dir/dist/odin.png" "$STAGING/usr/local/share/pixmaps/odin.png"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "$PKG_VERSION" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/odin"
}
