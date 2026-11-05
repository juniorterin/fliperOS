#!/usr/bin/env bash
# Os pacotes .deb do FliperOS para um gabinete atualizado pela rede: o update
# baixa a arvore do GitHub, sem os .deb que a ISO traz no repositorio local
# (/opt/fliperos/repo). Cada um da lista (updates/packages.list) que falta,
# ou que esta numa versao mais velha, vem do release "packages" do GitHub,
# conferido pelo sha256 da lista (que vem no update, conferido pelo treehash).
# Imprime o caminho de cada .deb a instalar, um por linha; o
# tools/cabinet-update.sh os passa ao apt-get com os outros pacotes.
#
#   updates/packages-sync.sh [LISTA]
#
# Na lista, "NOME<TAB>VERSAO<TAB>SHA256<TAB>QUANDO": QUANDO e "always" (vai
# para todo gabinete, como na ISO) ou "installed" (so sobe a versao de quem
# ja o tem). Um que nao baixa ou nao confere fica de fora, com um aviso.
set -uo pipefail
list=${1:-$(dirname "$0")/packages.list}
url=${FLIPEROS_PACKAGES_URL:-https://github.com/juniorterin/fliperOS/releases/download/packages}
cache=${FLIPEROS_PACKAGES_CACHE:-/var/cache/fliperos/packages}
arch=${FLIPEROS_PACKAGES_ARCH:-amd64}
[[ -f $list ]] || exit 0
mkdir -p "$cache" || exit 0

sum_of() {
  sha256sum "$1" 2> /dev/null | cut -d' ' -f1
}

while IFS=$'\t' read -r name version sum when || [[ -n $name ]]; do
  [[ -z $name || $name == \#* ]] && continue
  have=$(dpkg-query -W -f='${Version}' "$name" 2> /dev/null) || have=""
  [[ $when == installed && -z $have ]] && continue
  [[ -n $have ]] && dpkg --compare-versions "$have" ge "$version" && continue
  file=${name}_${version}_${arch}.deb
  deb=$cache/$file
  if [[ $(sum_of "$deb") != "$sum" ]]; then
    if ! curl -fsSL -m 300 -o "$deb.part" "$url/$file"; then
      rm -f "$deb.part"
      echo "warning: $name $version could not be downloaded" >&2
      continue
    fi
    if [[ $(sum_of "$deb.part") != "$sum" ]]; then
      rm -f "$deb.part"
      echo "warning: $name $version does not match its sha256" >&2
      continue
    fi
    mv -f "$deb.part" "$deb"
  fi
  printf '%s\n' "$deb"
done < "$list"
exit 0
