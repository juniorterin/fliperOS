#!/usr/bin/env bash
# Publica os .deb do repositorio da ISO (packaging/build-deb.sh --list-iso) no
# release "packages" do GitHub e reescreve a updates/packages.list com a
# versao e o sha256 de cada um: e por ela que um gabinete atualizado so pela
# rede chega aos mesmos pacotes da ISO (updates/packages-sync.sh, chamado pelo
# tools/cabinet-update.sh). Roda onde o gh esta logado (no Windows, no WSL).
#
#   tools/publish-packages.sh [PASTA]     (padrao: output/packages)
#
# Um pacote novo entra na lista como "installed" (so atualiza quem ja o tem):
# depois do teste num gabinete, ele vira "always" a mao. Um .deb ja publicado
# com o mesmo nome nao e trocado: uma versao nova pede
# uma revisao nova na receita (PKG_REVISION). Depois, commit da lista e um
# update (tools/make-update.sh).
set -euo pipefail
cd "$(dirname "$0")/.."
dir=${1:-output/packages}
repo=${FLIPEROS_GH_REPO:-juniorterin/fliperOS}
tag=packages
list=updates/packages.list
die() {
  echo "publish-packages: $*" >&2
  exit 1
}

if ! gh release view "$tag" -R "$repo" > /dev/null 2>&1; then
  gh release create "$tag" -R "$repo" --title "FliperOS packages" --latest=false \
    --notes "The .deb packages of the FliperOS ISO, for cabinets updated over the network (updates/packages.list)." ||
    die "could not create the $tag release"
fi
published=$(gh release view "$tag" -R "$repo" --json assets --jq '.assets[].name')

rows=()
# publish NOME VERSAO DEB: envia o .deb (se ainda nao esta la) e guarda a
# linha da lista.
publish() {
  local name=$1 version=$2 deb=$3 file sum tmp published_sum when
  file=${deb##*/}
  [[ $file != *[+:]* ]] || die "$file: GitHub renames + and : in asset names"
  sum=$(sha256sum "$deb" | cut -d' ' -f1)
  if grep -qx "$file" <<< "$published"; then
    # O que vale e o publicado: um build refeito daqui nao e igual byte a byte.
    tmp=$(mktemp -d)
    gh release download "$tag" -R "$repo" -p "$file" -D "$tmp" || die "could not download the published $file"
    published_sum=$(sha256sum "$tmp/$file" | cut -d' ' -f1)
    rm -rf "$tmp"
    [[ $published_sum == "$sum" ]] || echo "$file: the local build differs; the published one stays"
    sum=$published_sum
    echo "$file: already published"
  else
    gh release upload "$tag" -R "$repo" "$deb" || die "could not upload $file"
    echo "$file: published"
  fi
  # O QUANDO de quem ja esta na lista fica; um pacote novo entra como
  # "installed" (nenhum gabinete o ganha ainda): ele vira "always" a mao, no
  # commit de depois do teste num gabinete.
  when=$(awk -F'\t' -v n="$name" '$1 == n { print $4; exit }' "$list" 2> /dev/null)
  rows+=("$(printf '%s\t%s\t%s\t%s' "$name" "$version" "$sum" "${when:-installed}")")
}

for recipe in $(bash packaging/build-deb.sh --list-iso); do
  # shellcheck source=/dev/null
  version=$(PKG_VERSION="" PKG_REVISION="" && . "packaging/packages/$recipe.sh" && echo "$PKG_VERSION-$PKG_REVISION")
  deb=$dir/${recipe}_${version}_amd64.deb
  [[ -f $deb ]] || die "$deb is missing: build it first (bash packaging/build-deb.sh $recipe)"
  publish "$recipe" "$version" "$deb"
done

# O kernel 15 kHz (fliperos-kernel.sh build output/kernel): a imagem e os
# headers do build de agora, se ja compilados. Cada build e um pacote novo
# (linux-image-6.18.54-15khz.N), instalado ao lado do anterior.
kernel_dir=${FLIPEROS_KERNEL_DIR:-output/kernel}
kernel_build=$(sed -n 's/^KERNEL_BUILD="\(.*\)"/\1/p' fliperos-kernel.sh)
for deb in "$kernel_dir"/linux-image-*.deb "$kernel_dir"/linux-headers-*.deb; do
  [[ -f $deb ]] || continue
  file=${deb##*/}
  name=${file%%_*}
  version=${file#*_}
  version=${version%_*}
  # So o build de agora: um .deb esquecido de um build antigo nao vai junto.
  [[ $version == *-"${kernel_build}"fliperos ]] || continue
  publish "$name" "$version" "$deb"
done

{
  echo "# Os .deb do repositorio da ISO, no release \"packages\" do GitHub, para os"
  echo "# gabinetes atualizados pela rede (updates/packages-sync.sh)."
  echo "# NOME<TAB>VERSAO<TAB>SHA256<TAB>QUANDO (always | installed)"
  echo "# Nao edite a mao: tools/publish-packages.sh a refaz."
  printf '%s\n' "${rows[@]}"
} > "$list"
echo "wrote $list"
