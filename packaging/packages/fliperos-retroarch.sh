# RetroArch so KMS/DRM (sem X11 nem Wayland), com o Vulkan e os patches do
# FliperOS (packaging/patches/retroarch): o khr_display (Vulkan sem X) troca o
# modo do CRT que o CRT SwitchRes gera.
#
# Era compilado no chroot da ISO, do master do dia: um gabinete atualizado
# so pela rede ficava com o RetroArch da ISO que instalou, sem o patch. Como
# pacote, ele chega pelos updates (updates/packages.list) e a ISO instala o
# mesmo .deb. O commit e fixo: o patch e conferido contra ele, e um commit
# novo e uma versao nova (a data no fim do PKG_VERSION, para subir sempre).
#
# Os cores, os .info e os perfis de controle seguem fora do pacote, em
# /opt/fliperos/retroarch, do usuario fliperos (o Online Updater os troca).

PKG_NAME="fliperos-retroarch"
RA_COMMIT="7d2e95318b380d7c39ef8025aedd9eace9b64446"
# O Setup > Emulators & Games compila o RetroArch mais novo no gabinete com
# esta mesma receita, no ultimo commit do projeto (config/fliperos-emulators edge).
PKG_UPSTREAM="https://github.com/libretro/RetroArch"
PKG_COMMIT_VAR="RA_COMMIT"
PKG_VERSION="1.22.2.20261105"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://www.retroarch.com"
PKG_SUMMARY="RetroArch for KMS/DRM (no X11), Vulkan with CRT mode switching"
PKG_DESCRIPTION="RetroArch built for the console: KMS/DRM, EGL and Vulkan, without X11
or Wayland, and with FliperOS's patch that makes the Vulkan khr_display
context switch the CRT mode that CRT SwitchRes generates.

Installed in /usr/local, where the FliperOS image always had it."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates \
libegl1-mesa-dev libgles2-mesa-dev libudev-dev libsdl2-dev libvulkan-dev \
libdrm-dev libgbm-dev libfontconfig1-dev"

PKG_SHLIB_TARGETS="usr/local/bin/retroarch"
# O Vulkan e aberto na hora (dlopen): o dpkg-shlibdeps nao o ve.
PKG_RUNTIME_EXTRA="libvulkan1"

pkg_build() {
  local here patch dir=$SRC/retroarch
  here=$(dirname "${BASH_SOURCE[0]}")
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 https://github.com/libretro/RetroArch "$RA_COMMIT" \
    && git -C "$dir" checkout -q FETCH_HEAD ||
    return 1
  # Todo patch tem de entrar: o commit e o mesmo em que foram conferidos.
  for patch in "$here"/../patches/retroarch/*.patch; do
    git -C "$dir" apply "$patch" || return 1
  done
  (cd "$dir" && ./configure --prefix=/usr/local --enable-kms --enable-egl --disable-x11 --disable-wayland \
    --disable-sdl --enable-sdl2 --enable-vulkan) &&
    make -C "$dir" -j"$(nproc)" &&
    make -C "$dir" install DESTDIR="$STAGING" ||
    return 1
  # O atalho do proprio RetroArch abriria o binario no X do desktop, onde este
  # build nao roda; o do FliperOS passa pelo fliperos-launch.
  rm -f "$STAGING/usr/local/share/applications/com.libretro.RetroArch.desktop"
  # A marca do patch do Vulkan (o fliperos-kms-run so usa o Vulkan com ela) e a
  # versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  touch "$STAGING/usr/local/share/fliperos/retroarch-vulkan-crt"
  git -C "$dir" log -1 --format='%cs %h' > "$STAGING/usr/local/share/fliperos/emulator-versions.d/retroarch"
}
