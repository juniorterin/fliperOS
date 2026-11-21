# AnyBOR (retrodiv/AnyBOR-libretro): um core do RetroArch para os jogos do
# OpenBOR (.pak), com 322 perfis de motor (3.0 de 3020 ate a 6391, 4.0 ate a
# 8023). Abre os paks pelo RetroArch do FliperOS (fliperos-kms-run), com o modo
# do CRT, save states e quatro jogadores.
#
# Este pacote nao vai na ISO (PKG_OPTIONAL): o frontend o baixa pronto quando o
# primeiro jogo da pasta openbor e aberto (config/fliperos-core fetch anybor ->
# config/fliperos-emulators, tipo package), e um gabinete que o tem sobe de
# versao pelos updates (updates/packages.list, QUANDO "installed").
#
# O core vai onde ficam os outros (/opt/fliperos/retroarch/cores) e o .info em
# /opt/fliperos/retroarch/info: o RetroArch e o scraper os acham sem configurar
# nada. O commit e fixo (sem release no projeto: um commit novo e uma versao
# nova, a data no fim do PKG_VERSION).
#
# Licenca: o core inclui o OpenBOR 3400 e 3741, cuja licenca proibe a VENDA do
# codigo ou dos binarios (LICENSES.md do projeto); o FliperOS e distribuido de
# graca, e o texto da licenca vai junto, em /usr/share/doc/fliperos-anybor.
#
# O build e autocontido (as bibliotecas vem do proprio projeto, estaticas):
# so precisa de make, gcc/g++, nasm e python3.

PKG_NAME="fliperos-anybor"
ANYBOR_COMMIT="b211fdc4b616de146b6fe594689081eeb4ae3bfd"
PKG_VERSION="0.2.48.20261120"
PKG_REVISION="1fliperos1"
PKG_OPTIONAL=1
PKG_SECTION="games"
PKG_HOMEPAGE="https://github.com/retrodiv/AnyBOR-libretro"
PKG_SUMMARY="AnyBOR (OpenBOR core for RetroArch)"
PKG_DESCRIPTION="AnyBOR, an independent libretro core for OpenBOR games (.pak), with 322
selectable engine profiles (OpenBOR 3.0 builds 3020 to 6391 and 4.0 up to
8023-dev) and automatic profile selection, so old and new paks open without
a second engine. Save states, rewind and four players.

The core goes to /opt/fliperos/retroarch/cores and its core info file to
/opt/fliperos/retroarch/info. It includes OpenBOR 3400 and 3741, whose license
forbids selling the code or the binaries: the license texts are in
/usr/share/doc/fliperos-anybor."

PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates nasm python3"

PKG_SHLIB_TARGETS="opt/fliperos/retroarch/cores/anybor_libretro.so"

pkg_build() {
  local dir=$SRC/anybor
  git init -q "$dir" \
    && git -C "$dir" fetch -q --depth 1 "$PKG_HOMEPAGE" "$ANYBOR_COMMIT" \
    && git -C "$dir" -c advice.detachedHead=false checkout -q FETCH_HEAD ||
    return 1
  # O build baixa nada: as bibliotecas estao em src/deps. O .so sai em
  # .build/dist/linux-x86_64 e na raiz.
  NUMPROC=$(nproc) make -C "$dir" &&
    [[ -f $dir/anybor_libretro.so ]] &&
    install -Dm755 "$dir/anybor_libretro.so" "$STAGING/opt/fliperos/retroarch/cores/anybor_libretro.so" &&
    install -Dm644 "$dir/anybor_libretro.info" "$STAGING/opt/fliperos/retroarch/info/anybor_libretro.info" ||
    return 1
  # A licenca (o no-sale do OpenBOR 3400/3741) vai junto do core.
  local doc=$STAGING/usr/share/doc/fliperos-anybor f
  for f in LICENSE LICENSES.md NOTICE.txt README.md CHANGELOG.md; do
    [[ -f $dir/$f ]] && install -Dm644 "$dir/$f" "$doc/$f"
  done
  [[ -d $dir/LICENSES ]] && cp -r "$dir/LICENSES" "$doc/LICENSES"
  # A versao para o Setup > Emulators & Games (config/fliperos-emulators).
  mkdir -p "$STAGING/usr/local/share/fliperos/emulator-versions.d"
  echo "$PKG_VERSION" > "$STAGING/usr/local/share/fliperos/emulator-versions.d/anybor"
  return 0
}
