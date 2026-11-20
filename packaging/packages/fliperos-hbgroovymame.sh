# hbgroovymame: o HBMAME (MAME com os hacks e os homebrews dos arcades, de
# Robbbert) com o Switchres do GroovyMAME, para o CRT de 15 kHz trocar para o
# modo de cada jogo como no groovymame. O HBMAME usa a pasta ~/roms/hbmame; o
# GroovyMAME, a ~/roms/mame.
#
# O fonte e o do HBMAME na tag fixada, com os arquivos novos do GroovyMAME da
# tag gm0289sr222f (o Switchres, o emusync, o lz4: packaging/patches/hbgroovymame/
# groovymame-files.txt) e o diff dele sobre o MAME 0.289 portado para o codigo
# do HBMAME: o Switchres, o emusync e a interface (0001), o asio novo e os
# headers que o HBMAME nao traz mais (0002) e a sincronia de audio, com o
# modulo de som do OSD que mede a placa de som (0003). E o lockstep patch do
# FliperOS do groovymame (packaging/patches/groovymame, o mesmo arquivo): a
# party de dois a quatro gabinetes tambem nos jogos da pasta hbmame.
#
# Este pacote nao vai na ISO (PKG_OPTIONAL): o Setup o baixa pronto quando
# chega um jogo na pasta hbmame (config/fliperos-emulators, tipo package), e
# um gabinete que o tem sobe de versao pelos updates (updates/packages.list,
# QUANDO "installed"). O build do MAME inteiro leva horas.
#
# O comando hbgroovymame e o config/fliperos-groovymame (mesmo arquivo, o nome
# decide): vem com o sistema, e este pacote traz o binario, os arquivos do
# HBMAME e as pastas dele (packaging/assets/hbgroovymame/paths.ini).

PKG_NAME="fliperos-hbgroovymame"
# O HBMAME 0.289.6 (a tag tag2896) e o GroovyMAME gm0289sr222f (Switchres 2.22f)
# sobre o mesmo MAME 0.289. Os commits sao os das tags: os patches sao
# conferidos contra eles.
HBMAME_TAG="tag2896"
HBMAME_COMMIT="fa040eced0dea161bb4e5d55bdbcb85aaf8de632"
GROOVYMAME_TAG="gm0289sr222f"
GROOVYMAME_COMMIT="953db38f4aaab1d75faa4ac79e1b45686214f987"
PKG_VERSION="0.289.6"
PKG_REVISION="1fliperos1"
PKG_OPTIONAL=1
PKG_SECTION="games"
PKG_HOMEPAGE="https://hbmame.1emulation.com/"
PKG_SUMMARY="HBMAME with Switchres for CRT monitors (hbgroovymame)"
PKG_DESCRIPTION="HBMAME, the MAME of arcade hacks and homebrews, with GroovyMAME's
Switchres, which switches the CRT to each game's own video mode. Its games
live in ~/roms/hbmame, apart from GroovyMAME's ~/roms/mame.

With the plugins (hiscore), bgfx, artwork, language, ctrlr and the software
lists of the same tag.

The binary goes to /usr/local/libexec/hbgroovymame; the hbgroovymame command
in front of it is FliperOS's."

PKG_BUILD_DEPS="build-essential git ca-certificates curl python3 pkg-config \
libsdl2-dev libsdl2-ttf-dev libfontconfig-dev libpulse-dev libasound2-dev \
libxinerama-dev libxi-dev libxrandr-dev libx11-dev libdrm-dev libgl-dev libegl-dev"

PKG_SHLIB_TARGETS="usr/local/libexec/hbgroovymame"

# O espaco que o build do MAME inteiro ocupa (o codigo e os objetos), em GB.
HBMAME_BUILD_GB=22

pkg_build() {
  local patch here jobs free built dir
  local src=$SRC/hbmame-src gm=$SRC/groovymame-src share=$STAGING/usr/local/share/hbgroovymame
  local bin=$STAGING/usr/local/libexec/hbgroovymame
  here=$(dirname "${BASH_SOURCE[0]}")/../patches/hbgroovymame
  free=$(df -Pk "$SRC" | awk 'NR == 2 { print int($4 / 1048576) }')
  if ((free < HBMAME_BUILD_GB)); then
    echo "building HBMAME needs $HBMAME_BUILD_GB GB free; there are $free GB" >&2
    return 1
  fi
  git clone -q --depth 1 --branch "$HBMAME_TAG" https://github.com/Robbbert/hbmame "$src" || return 1
  git clone -q --depth 1 --branch "$GROOVYMAME_TAG" https://github.com/antonioginer/GroovyMAME "$gm" || return 1
  if [[ $(git -C "$src" rev-parse HEAD) != "$HBMAME_COMMIT" ]]; then
    echo "tag $HBMAME_TAG is no longer the pinned commit" >&2
    return 1
  fi
  if [[ $(git -C "$gm" rev-parse HEAD) != "$GROOVYMAME_COMMIT" ]]; then
    echo "tag $GROOVYMAME_TAG is no longer the pinned commit" >&2
    return 1
  fi
  # Os arquivos novos do GroovyMAME (o Switchres, o emusync, o lz4) e depois
  # os patches, na ordem: todos tem de entrar.
  tar -c -C "$gm" -T "$here/groovymame-files.txt" | tar -x -C "$src" || return 1
  for patch in "$here"/*.patch "$here/../groovymame/0001-lockstep-patch.patch"; do
    git -C "$src" apply "$patch" || return 1
  done
  rm -rf "$gm"
  # Um processo do compilador por 1,5 GB de memoria livre (o MAME tem
  # arquivos enormes), no maximo um por nucleo.
  jobs=$(awk '/^MemAvailable:/ { print int($2 / 1572864) }' /proc/meminfo)
  ((jobs < 1)) && jobs=1
  ((jobs > $(nproc))) && jobs=$(nproc)
  # Sem o depurador de Qt e sem as ferramentas: so o emulador. O binario sai
  # com o nome do alvo, hbmame.
  make -C "$src" -j"$jobs" TARGET=hbmame NOWERROR=1 USE_QTDEBUG=0 TOOLS=0 SYMBOLS=0 NO_SYMBOLS=1 \
    DEPRECATED=0 OPTIMIZE=3 || return 1
  built=$(ls "$src/hbmame" "$src/hbmame64" 2> /dev/null | head -n 1)
  [[ -n $built ]] && install -Dm755 "$built" "$bin" || return 1
  # Os arquivos do mesmo HBMAME que o binario nao traz.
  mkdir -p "$share/fonts"
  for dir in artwork bgfx ctrlr hash language plugins; do
    [[ -d $src/$dir ]] && cp -r "$src/$dir" "$share/"
  done
  install -m644 "$src/uismall.bdf" "$share/fonts/uismall.bdf" &&
    install -m644 "$here/../../assets/hbgroovymame/paths.ini" "$share/paths.ini" ||
    return 1
  chmod -R a+rX "$share"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "$PKG_VERSION" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/hbgroovymame"
  # O que fica por fazer na maquina: a pasta do .ini (do usuario, o hbmame.ini
  # e refeito a cada jogo) e o "Initializing..." fora do binario
  # (config/fliperos-groovymame-quiet).
  mkdir -p "$STAGING/DEBIAN"
  cat > "$STAGING/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
install -d -o 1000 -g 1000 /etc/fliperos/hbmame 2> /dev/null || install -d /etc/fliperos/hbmame
# O hbmame.ini sai do mame.ini do sistema e do paths.ini: o comando
# hbgroovymame o refaz ao abrir o proximo jogo.
rm -f /etc/fliperos/hbmame/hbmame.ini
quiet=/opt/fliperos/bin/fliperos-groovymame-quiet
if [ -x "$quiet" ]; then
  python3 "$quiet" /usr/local/libexec/hbgroovymame > /dev/null 2>&1 || true
fi
exit 0
EOF
  chmod 755 "$STAGING/DEBIAN/postinst"
}
