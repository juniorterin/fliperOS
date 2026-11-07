# GroovyMAME compilado do codigo da tag do release oficial, com os patches do
# FliperOS (packaging/patches/groovymame): o lockstep patch, a party de dois a
# quatro gabinetes na rede local travada como um link de arcade (o
# fliperos-lockstep.ini que o gui/felink.py poe no cfg da party). Com os
# arquivos da mesma tag que o binario nao traz: plugins (hiscore), a fonte
# uismall.bdf da interface, bgfx, artwork, language, ctrlr, keymaps e hash
# (listas de software), em /usr/local/share/groovymame (as pastas do
# config/mame.ini).
#
# Ate o 0.289.222f-1fliperos1 era o binario do release (o build leva horas):
# sem o patch, so o link dos jogos que tinham placa de link.
#
# Vinha baixado no build da ISO: um gabinete atualizado so pela rede ficava
# com o GroovyMAME da ISO que instalou. Como pacote, ele chega pelos updates
# (updates/packages.list) e a ISO instala o mesmo .deb.
#
# O "Initializing..." sai no gabinete (config/fliperos-groovymame-quiet, a
# cada update pelo fliperos-rootfs.sh, e aqui).

PKG_NAME="fliperos-groovymame"
# O release: MAME 0.289, Switchres 2.22f. O commit e o da tag (o patch e
# conferido contra ele).
GROOVYMAME_TAG="gm0289sr222f"
GROOVYMAME_COMMIT="953db38f4aaab1d75faa4ac79e1b45686214f987"
PKG_VERSION="0.289.222f"
PKG_REVISION="1fliperos2"
# O Setup > Emulators & Games compila o mais novo com esta mesma receita
# (config/fliperos-emulators edge): a tag mais recente, com os mesmos patches
# (a party continua), sem o commit fixado aqui. O MAME inteiro leva horas
# num gabinete: PKG_EDGE_WAIT e o que o Setup mostra enquanto compila.
PKG_UPSTREAM="https://github.com/antonioginer/GroovyMAME"
PKG_COMMIT_VAR="GROOVYMAME_TAG"
PKG_EDGE_TAGS='^gm[0-9]{4}sr[0-9]+[a-z]?$'
PKG_EDGE_WAIT="hours: MAME is compiled with the FliperOS patches"
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/antonioginer/GroovyMAME"
PKG_SUMMARY="GroovyMAME (MAME with Switchres for CRT monitors)"
PKG_DESCRIPTION="GroovyMAME, MAME with Switchres, which switches the CRT to each game's
own video mode, built from the release's tag with FliperOS's lockstep
patch: a party of two to four machines on the local network, each one
with its own players, kept on the same frame as an arcade link board.
With the plugins (hiscore), the interface font, bgfx, artwork, language,
ctrlr, keymaps and the software lists of the same tag.

The binary goes to /usr/local/libexec/groovymame; the groovymame command
in front of it is FliperOS's."

PKG_BUILD_DEPS="build-essential git ca-certificates curl python3 pkg-config \
libsdl2-dev libsdl2-ttf-dev libfontconfig-dev libpulse-dev libasound2-dev \
libxinerama-dev libxi-dev libxrandr-dev libx11-dev libdrm-dev libgl-dev libegl-dev"

PKG_SHLIB_TARGETS="usr/local/libexec/groovymame"

# O espaco que o build do MAME inteiro ocupa (o codigo e os objetos), em GB.
GROOVYMAME_BUILD_GB=20

pkg_build() {
  local patch here jobs free src=$SRC/groovymame-src share=$STAGING/usr/local/share/groovymame
  local quiet=/opt/fliperos/bin/fliperos-groovymame-quiet bin=$STAGING/usr/local/libexec/groovymame
  here=$(dirname "${BASH_SOURCE[0]}")
  free=$(df -Pk "$SRC" | awk 'NR == 2 { print int($4 / 1048576) }')
  if ((free < GROOVYMAME_BUILD_GB)); then
    echo "building MAME needs $GROOVYMAME_BUILD_GB GB free; there are $free GB" >&2
    return 1
  fi
  git clone -q --depth 1 --branch "$GROOVYMAME_TAG" "$PKG_UPSTREAM" "$src" || return 1
  # No mais novo (FLIPEROS_EDGE) a tag nova nao tem como estar fixada.
  if [[ -z ${FLIPEROS_EDGE:-} && $(git -C "$src" rev-parse HEAD) != "$GROOVYMAME_COMMIT" ]]; then
    echo "tag $GROOVYMAME_TAG is no longer the pinned commit" >&2
    return 1
  fi
  # Todo patch tem de entrar: no commit fixado, e o mesmo em que foram
  # conferidos; num mais novo em que um nao encaixa, o pacote fica.
  for patch in "$here"/../patches/groovymame/*.patch; do
    git -C "$src" apply "$patch" || return 1
  done
  # Um processo do compilador por 1,5 GB de memoria livre (o MAME tem
  # arquivos enormes), no maximo um por nucleo.
  jobs=$(awk '/^MemAvailable:/ { print int($2 / 1572864) }' /proc/meminfo)
  ((jobs < 1)) && jobs=1
  ((jobs > $(nproc))) && jobs=$(nproc)
  # Sem o depurador de Qt e sem as ferramentas (chdman e cia.): so o
  # emulador. O binario sai com o nome do alvo, mame.
  make -C "$src" -j"$jobs" NOWERROR=1 USE_QTDEBUG=0 TOOLS=0 OPTIMIZE=3 &&
    install -Dm755 "$src/mame" "$bin" ||
    return 1
  # O container dos pacotes so tem o packaging/: sem o script, o update o roda
  # (fliperos-rootfs.sh).
  [[ -x $quiet ]] && python3 "$quiet" "$bin" > /dev/null
  mkdir -p "$share/fonts"
  cp -r "$src"/{artwork,bgfx,plugins,language,ctrlr,keymaps,hash} "$share/" &&
    install -m644 "$src/uismall.bdf" "$share/fonts/uismall.bdf" ||
    return 1
  chmod -R a+rX "$share"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "0.${GROOVYMAME_TAG:3:3}" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/groovymame"
}
