# PCSX2 (PlayStation 2): o AppImage oficial, extraido em /opt/pcsx2 (sem
# precisar de FUSE), com o comando pcsx2 na frente. O PCSX2 atual exige SDL3,
# Qt 6.10, plutosvg, ryml e Shaderc, que o Ubuntu 24.04 nao tem (o Qt dele e o
# 6.4): o AppImage traz as bibliotecas dele. Qt nao tem backend KMS
# suportado: fica em X11 via fliperos-x11-run.
#
# Vinha baixado no build da ISO: um gabinete atualizado so pela rede ficava
# com o PCSX2 da ISO que instalou. Como pacote, ele chega pelos updates
# (updates/packages.list) e a ISO instala o mesmo .deb.

PKG_NAME="fliperos-pcsx2"
PCSX2_TAG="v2.8.2"
PCSX2_SHA256="0c46bb6a88aa2782b10853a7b07cf3387ba99cbef2b966372cd2315b8571abea"
PKG_VERSION="2.8.2"
PKG_REVISION="1fliperos1"
# O Setup > Emulators & Games baixa o PCSX2 mais novo com esta mesma receita
# (config/fliperos-emulators edge): o ultimo release estavel do projeto (as
# tags tambem marcam os builds noturnos), sem o sha256 fixado aqui.
PKG_UPSTREAM="https://github.com/PCSX2/pcsx2"
PKG_COMMIT_VAR="PCSX2_TAG"
PKG_EDGE_RELEASE=1
PKG_SECTION="games"
PKG_HOMEPAGE="https://pcsx2.net"
PKG_SUMMARY="PCSX2 (PlayStation 2), the official AppImage"
PKG_DESCRIPTION="PCSX2, the PlayStation 2 emulator: the official AppImage extracted in
/opt/pcsx2, with its own libraries, and the pcsx2 command in front of it."

PKG_BUILD_DEPS="ca-certificates curl"

# As bibliotecas vem dentro do AppImage: nada para o dpkg-shlibdeps.
PKG_SHLIB_TARGETS=""

pkg_build() {
  local image=$SRC/pcsx2.AppImage
  curl -fsSL --retry 3 --max-time 900 -o "$image" \
    "$PKG_UPSTREAM/releases/download/$PCSX2_TAG/pcsx2-$PCSX2_TAG-linux-appimage-x64-Qt.AppImage" || return 1
  # Fixado aqui: o sha256. No mais novo (FLIPEROS_EDGE), nao tem como estar.
  if [[ -z ${FLIPEROS_EDGE:-} ]]; then
    echo "$PCSX2_SHA256  $image" | sha256sum -c --quiet - || return 1
  fi
  chmod +x "$image"
  (cd "$SRC" && "$image" --appimage-extract > /dev/null) || return 1
  mkdir -p "$STAGING/opt" "$STAGING/usr/local/bin"
  mv "$SRC/squashfs-root" "$STAGING/opt/pcsx2" || return 1
  chmod -R a+rX "$STAGING/opt/pcsx2"
  printf '#!/bin/sh\nexec /opt/pcsx2/AppRun "$@"\n' > "$STAGING/usr/local/bin/pcsx2"
  chmod 755 "$STAGING/usr/local/bin/pcsx2"
  # Icone do menu do LXDE (config/applications/fliperos-pcsx2.desktop).
  install -Dm644 "$STAGING/opt/pcsx2/PCSX2.png" "$STAGING/usr/local/share/pixmaps/pcsx2.png" || return 1
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "${PCSX2_TAG#v}" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/pcsx2"
}
