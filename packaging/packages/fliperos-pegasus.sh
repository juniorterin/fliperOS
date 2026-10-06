# Pegasus Frontend — build KMS (Qt eglfs), como o pacote do GroovyArcade
# (gitlab.com/groovyarcade/packages, package/pegasus-frontend).
#
# A mesma tag (weekly_2024w38), o gamepad e a bateria pelo SDL e o patch do
# proprio Pegasus para o KMS (etc/rpi4/kms_launch_fix.diff): ao abrir um
# jogo ele solta a tela (o eglfs), para o emulador pegar o DRM, e a retoma
# quando ele fecha. O patch usa cabecalhos privados do Qt (o eglfs), dai o
# qtbase5-private-dev.

PKG_NAME="fliperos-pegasus"
PKG_VERSION="0.16+2024w38"
PKG_REVISION="1fliperos1"
PKG_SECTION="games"
PKG_HOMEPAGE="https://pegasus-frontend.org"
PKG_SUMMARY="Pegasus Frontend (KMS/eglfs build for CRT)"
PKG_DESCRIPTION="Graphical frontend for launching emulators, with QML themes.

This build runs on the console, without Xorg (Qt eglfs, KMS platform), and
releases the screen when a game opens, like the GroovyArcade package."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates \
qtbase5-dev qtbase5-dev-tools qtbase5-private-dev qt5-qmake qtdeclarative5-dev \
qtmultimedia5-dev libqt5svg5-dev qttools5-dev-tools libsdl2-dev libgl-dev"

PKG_SHLIB_TARGETS="usr/bin/pegasus-fe"

# Os modulos QML e os plugins que o tema padrao usa: o dpkg-shlibdeps nao os
# ve (sao carregados em tempo de execucao). O eglfs/KMS vem no libqt5gui5.
PKG_RUNTIME_EXTRA="qml-module-qtquick2, qml-module-qtquick-window2, qml-module-qtquick-layouts, \
qml-module-qtquick-controls, qml-module-qtquick-controls2, qml-module-qtgraphicaleffects, \
qml-module-qtmultimedia, qml-module-qt-labs-folderlistmodel, libqt5svg5, libqt5multimedia5-plugins, libqt5sql5-sqlite, \
qt5-image-formats-plugins, gstreamer1.0-libav, gstreamer1.0-plugins-good"

pkg_build() {
  local qmake=/usr/lib/qt5/bin/qmake
  git clone --depth 1 --branch weekly_2024w38 --recursive \
      https://github.com/mmatyas/pegasus-frontend.git "$SRC/pegasus" \
    && patch -d "$SRC/pegasus" -Np1 < "$SRC/pegasus/etc/rpi4/kms_launch_fix.diff" \
    && mkdir -p "$SRC/pegasus/build" \
    && (cd "$SRC/pegasus/build" \
      && "$qmake" .. QMAKE_LIBS_LIBDL=-ldl USE_SDL_GAMEPAD=1 USE_SDL_POWER=1 \
        INSTALL_BINDIR=/usr/bin INSTALL_DOCDIR=/usr/share/doc/pegasus-frontend \
        INSTALL_ICONDIR=/usr/share/pixmaps INSTALL_DESKTOPDIR=/usr/share/applications \
        INSTALL_APPSTREAMDIR=/usr/share/metainfo \
      && make -j"$(nproc)" \
      && make INSTALL_ROOT="$STAGING" install)
}
