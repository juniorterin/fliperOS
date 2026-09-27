#!/usr/bin/env bash
# ============================================================
#  FliperOS — gerador de .deb dos componentes pos-instalacao
#
#  A ISO e so o sistema base; launchers e emuladores sao instalados depois
#  pelo wizard, a partir de um repositorio APT proprio. Este script produz os
#  pacotes desse repositorio.
#
#  Uso: bash packaging/build-deb.sh [--output DIR] <pacote>...
#       bash packaging/build-deb.sh --list
#
#  Precisa rodar no MESMO Ubuntu da ISO (24.04): o binario linka contra as
#  libs da imagem, e o Depends e calculado com dpkg-shlibdeps a partir do que
#  esta instalado aqui. Compilar em outra base gera dependencia errada.
# ============================================================
set -euo pipefail

GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'
BLU='\033[0;34m'; CYN='\033[0;36m'; DIM='\033[2m'; BLD='\033[1m'; RST='\033[0m'

ok()   { echo -e "${GRN}✓${RST} $*"; }
warn() { echo -e "${YLW}⚠${RST} $*"; }
err()  { echo -e "${RED}✗${RST} $*" >&2; exit 1; }
step() { echo -e "\n${BLD}${CYN}══ $* ══${RST}"; }
info() { echo -e "${BLU}→${RST} $*"; }

ROOT=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RECIPES="$ROOT/packaging/packages"
OUTPUT="$ROOT/output/packages"
WORK=""

cleanup() { [[ -n "$WORK" && -d "$WORK" ]] && rm -rf "$WORK"; }
trap cleanup EXIT

list_recipes() {
  for recipe in "$RECIPES"/*.sh; do
    [[ -f "$recipe" ]] || continue
    basename "$recipe" .sh
  done
}

TARGETS=()
while [[ $# -gt 0 ]]; do
  case $1 in
    --output) [[ $# -ge 2 ]] || err "--output requer diretorio"; OUTPUT="$2"; shift 2 ;;
    --list)   list_recipes; exit 0 ;;
    -*)       err "Opcao desconhecida: $1" ;;
    *)        TARGETS+=("$1"); shift ;;
  esac
done

[[ ${#TARGETS[@]} -gt 0 ]] || err "Nenhum pacote pedido. Veja: --list"

if ! grep -q "24.04" /etc/os-release 2>/dev/null; then
  warn "Esta base nao parece ser Ubuntu 24.04."
  warn "O Depends sai calculado contra libs diferentes das da ISO."
fi
[[ $EUID -eq 0 ]] || err "Precisa de root pra instalar as dependencias de build"

mkdir -p "$OUTPUT"

build_one() {
  local name="$1"
  local recipe="$RECIPES/$name.sh"
  [[ -f "$recipe" ]] || err "Receita ausente: $recipe"

  # Cada receita define estas variaveis e a funcao pkg_build().
  PKG_NAME=""; PKG_VERSION=""; PKG_REVISION="1"; PKG_SUMMARY=""
  PKG_DESCRIPTION=""; PKG_SECTION="games"; PKG_HOMEPAGE=""
  PKG_BUILD_DEPS=""; PKG_RUNTIME_EXTRA=""; PKG_SHLIB_TARGETS=""
  unset -f pkg_build 2>/dev/null || true
  # shellcheck disable=SC1090
  source "$recipe"

  [[ -n "$PKG_NAME" && -n "$PKG_VERSION" ]] || err "$name: receita sem PKG_NAME/PKG_VERSION"
  declare -F pkg_build >/dev/null || err "$name: receita sem pkg_build()"

  step "Empacotando $PKG_NAME $PKG_VERSION-$PKG_REVISION"

  WORK=$(mktemp -d /tmp/fliperos-deb.XXXXXX)
  SRC="$WORK/src"; STAGING="$WORK/staging"
  mkdir -p "$SRC" "$STAGING"
  export SRC STAGING

  if [[ -n "$PKG_BUILD_DEPS" ]]; then
    info "Instalando dependencias de build"
    apt-get update -qq
    # shellcheck disable=SC2086
    apt-get install -y --no-install-recommends $PKG_BUILD_DEPS >/dev/null \
      || err "$PKG_NAME: dependencias de build falharam"
    ok "Dependencias prontas"
  fi

  info "Compilando (pode demorar)"
  # Atencao ao escrever receita: o errexit fica suspenso dentro de uma funcao
  # chamada em "|| err", e re-setar set -e num subshell nao reverte isso no
  # bash. Por isso pkg_build() encadeia os proprios passos com &&, e a
  # existencia do binario e conferida depois, em PKG_SHLIB_TARGETS.
  pkg_build || err "$PKG_NAME: build falhou"
  ok "Build concluido"

  [[ -n "$(ls -A "$STAGING")" ]] || err "$PKG_NAME: staging vazio, nada instalado"

  # Depends calculado do binario, nao escrito a mao: dpkg-shlibdeps le as libs
  # realmente linkadas. Precisa de um debian/control minimo pra funcionar.
  local shlib_deps=""
  if [[ -n "$PKG_SHLIB_TARGETS" ]]; then
    info "Calculando Depends com dpkg-shlibdeps"
    mkdir -p "$STAGING/debian"
    printf 'Source: %s\n\nPackage: %s\nArchitecture: amd64\n' \
      "$PKG_NAME" "$PKG_NAME" > "$STAGING/debian/control"
    local targets=()
    for target in $PKG_SHLIB_TARGETS; do
      [[ -e "$STAGING/$target" ]] || err "$PKG_NAME: binario esperado ausente: $target"
      targets+=("$target")
    done
    shlib_deps=$(cd "$STAGING" && dpkg-shlibdeps -O --ignore-missing-info "${targets[@]}" \
      2>/dev/null | sed 's/^shlibs:Depends=//') || true
    rm -rf "$STAGING/debian"
    [[ -n "$shlib_deps" ]] || warn "$PKG_NAME: shlibdeps vazio; conferir manualmente"
    ok "Depends: $shlib_deps"
  fi

  local depends="$shlib_deps"
  if [[ -n "$PKG_RUNTIME_EXTRA" ]]; then
    [[ -n "$depends" ]] && depends="$depends, $PKG_RUNTIME_EXTRA" || depends="$PKG_RUNTIME_EXTRA"
  fi

  local size
  size=$(du -sk "$STAGING" | cut -f1)
  mkdir -p "$STAGING/DEBIAN"
  {
    echo "Package: $PKG_NAME"
    echo "Version: $PKG_VERSION-$PKG_REVISION"
    echo "Architecture: amd64"
    echo "Maintainer: FliperOS <noreply@fliperos.invalid>"
    echo "Section: $PKG_SECTION"
    echo "Priority: optional"
    echo "Installed-Size: $size"
    [[ -n "$depends" ]]     && echo "Depends: $depends"
    [[ -n "$PKG_HOMEPAGE" ]] && echo "Homepage: $PKG_HOMEPAGE"
    echo "Description: $PKG_SUMMARY"
    while IFS= read -r line; do
      [[ -z "$line" ]] && echo " ." || echo " $line"
    done <<< "$PKG_DESCRIPTION"
  } > "$STAGING/DEBIAN/control"

  local deb="$OUTPUT/${PKG_NAME}_${PKG_VERSION}-${PKG_REVISION}_amd64.deb"
  dpkg-deb --root-owner-group --build "$STAGING" "$deb" >/dev/null \
    || err "$PKG_NAME: dpkg-deb falhou"
  ok "Gerado: $deb ($(du -h "$deb" | cut -f1))"

  rm -rf "$WORK"; WORK=""
}

for target in "${TARGETS[@]}"; do
  build_one "$target"
done

echo
ok "Pacotes em $OUTPUT"
echo -e "${DIM}Publique o repositorio com: bash packaging/make-repo.sh${RST}"
