# GroovyMAME: o release oficial do projeto para Linux (o binario ja
# compilado: o build leva mais de uma hora), com os arquivos do codigo da
# mesma tag que o release nao traz: plugins (hiscore), a fonte uismall.bdf da
# interface, bgfx, artwork, language, ctrlr, keymaps e hash (listas de
# software), em /usr/local/share/groovymame (as pastas do config/mame.ini).
#
# Vinha baixado no build da ISO: um gabinete atualizado so pela rede ficava
# com o GroovyMAME da ISO que instalou. Como pacote, ele chega pelos updates
# (updates/packages.list) e a ISO instala o mesmo .deb.
#
# O "Initializing..." sai no gabinete (config/fliperos-groovymame-quiet, a
# cada update pelo fliperos-rootfs.sh, e no build do mais novo, aqui).

PKG_NAME="fliperos-groovymame"
# O release: MAME 0.289, Switchres 2.22f. O sha256 e o do arquivo do release;
# o commit, o da tag.
GROOVYMAME_TAG="gm0289sr222f"
GROOVYMAME_SHA256="d5bd539776ace64db42301252d80be2af60b2f89862b0d4391c646083f323f62"
GROOVYMAME_COMMIT="953db38f4aaab1d75faa4ac79e1b45686214f987"
PKG_VERSION="0.289.222f"
PKG_REVISION="1fliperos1"
# O Setup > Emulators & Games baixa o release mais novo com esta mesma receita
# (config/fliperos-emulators edge): a tag mais recente, sem o sha256 nem o
# commit fixados aqui.
PKG_UPSTREAM="https://github.com/antonioginer/GroovyMAME"
PKG_COMMIT_VAR="GROOVYMAME_TAG"
PKG_EDGE_TAGS='^gm[0-9]{4}sr[0-9]+[a-z]?$'
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/antonioginer/GroovyMAME"
PKG_SUMMARY="GroovyMAME (MAME with Switchres for CRT monitors)"
PKG_DESCRIPTION="The official GroovyMAME release for Linux: MAME with Switchres, which
switches the CRT to each game's own video mode. With the plugins
(hiscore), the interface font, bgfx, artwork, language, ctrlr, keymaps
and the software lists of the same tag.

The binary goes to /usr/local/libexec/groovymame; the groovymame command
in front of it is FliperOS's."

# As bibliotecas que o binario pede (objdump -p; o Qt6 e o do depurador):
# instaladas aqui para o dpkg-shlibdeps achar os pacotes delas.
PKG_BUILD_DEPS="git ca-certificates curl python3 \
libsdl2-2.0-0 libsdl2-ttf-2.0-0 libqt6core6t64 libqt6gui6t64 libqt6widgets6t64 \
libpulse0 libasound2t64 libfontconfig1 libxi6 libgl1 libdrm2"

PKG_SHLIB_TARGETS="usr/local/libexec/groovymame"

pkg_build() {
  local file tarball src=$SRC/groovymame-src share=$STAGING/usr/local/share/groovymame
  local quiet=/opt/fliperos/bin/fliperos-groovymame-quiet
  # O arquivo do release sai da tag: gm0289sr222f -> groovymame_0289.222f_linux.tar.bz2.
  [[ $GROOVYMAME_TAG =~ ^gm([0-9]{4})sr([0-9]+[a-z]?)$ ]] || return 1
  file="groovymame_${BASH_REMATCH[1]}.${BASH_REMATCH[2]}_linux.tar.bz2"
  tarball=$SRC/$file
  curl -fsSL --retry 3 --max-time 900 -o "$tarball" \
    "$PKG_UPSTREAM/releases/download/$GROOVYMAME_TAG/$file" || return 1
  # Fixados aqui: o sha256 e o commit. No mais novo (FLIPEROS_EDGE), a tag
  # nova nao tem como estar fixada.
  if [[ -z ${FLIPEROS_EDGE:-} ]]; then
    echo "$GROOVYMAME_SHA256  $tarball" | sha256sum -c --quiet - || return 1
  fi
  # O tar do container pode nao ter o bzip2; o tarfile do Python le .tar.bz2.
  python3 -c 'import sys, tarfile; tarfile.open(sys.argv[1]).extract("groovymame", sys.argv[2])' "$tarball" "$SRC" &&
    install -Dm755 "$SRC/groovymame" "$STAGING/usr/local/libexec/groovymame" ||
    return 1
  [[ -x $quiet ]] && python3 "$quiet" "$STAGING/usr/local/libexec/groovymame" > /dev/null
  git clone -q --depth 1 --branch "$GROOVYMAME_TAG" --filter=blob:none --sparse "$PKG_UPSTREAM" "$src" ||
    return 1
  if [[ -z ${FLIPEROS_EDGE:-} && $(git -C "$src" rev-parse HEAD) != "$GROOVYMAME_COMMIT" ]]; then
    echo "tag $GROOVYMAME_TAG is no longer the pinned commit" >&2
    return 1
  fi
  git -C "$src" sparse-checkout set artwork bgfx plugins language ctrlr keymaps hash || return 1
  mkdir -p "$share/fonts"
  cp -r "$src"/{artwork,bgfx,plugins,language,ctrlr,keymaps,hash} "$share/" &&
    install -m644 "$src/uismall.bdf" "$share/fonts/uismall.bdf" ||
    return 1
  chmod -R a+rX "$share"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "0.${GROOVYMAME_TAG:3:3}" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/groovymame"
}
