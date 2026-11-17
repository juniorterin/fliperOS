#!/usr/bin/env bash
# Rotina para levar ao GitHub os .deb das receitas da ISO que mudaram: acha o
# que mudou, compila so isso no container de empacotamento (Dockerfile.packages,
# o mesmo da CI), publica no release "packages" (tools/publish-packages.sh) e
# faz o commit + push da updates/packages.list. Roda no WSL (o gh so esta
# logado la).
#
#   tools/publish-changed-packages.sh                 so mostra o estado
#   tools/publish-changed-packages.sh --run [--bump] [NOME...]
#
# Estado de cada receita (packaging/packages/NOME.sh, as do --list-iso):
#   em dia        a versao da receita e a da lista, e nada dela mudou
#   versao nova   PKG_VERSION/PKG_REVISION diferente da lista: compila
#   pacote novo   ainda fora da lista: compila (entra como "installed")
#   sem revisao   a receita ou os patches/assets dela mudaram desde que a
#                 linha da lista foi escrita, mas a revisao e a mesma: um .deb
#                 ja publicado nao e trocado, entao precisa de --bump
#
# --bump    sobe o numero final do PKG_REVISION das "sem revisao" (e de toda
#           receita nomeada na linha de comando, para recompilar mesmo sem
#           mudanca, por exemplo por causa de uma lib nova).
# NOME...   so essas receitas.
# --force   compila mesmo com outro container rodando (CLAUDE.md, regra 6).
# --no-commit  publica, mas deixa o commit da lista para depois.
#
# Antes de compilar, confere o tools/docker-health.ps1 e o docker ps (um job
# pesado por vez). Depois do push, o que falta e um update que leve os pacotes
# aos gabinetes: updates/notes/NNNN.md + tools/make-update.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
list=updates/packages.list
out=output/packages
die() {
  echo "publish-changed-packages: $*" >&2
  exit 1
}

run="" bump="" force="" commit=1
names=()
while (($#)); do
  case $1 in
    --run) run=1 ;;
    --bump) bump=1 ;;
    --force) force=1 ;;
    --no-commit) commit="" ;;
    -h | --help)
      sed -n '2,/^set -e/p' "$0" | sed '$d; s/^# \{0,1\}//'
      exit 0
      ;;
    -*) die "unknown option: $1" ;;
    *) names+=("$1") ;;
  esac
  shift
done

mapfile -t iso < <(bash packaging/build-deb.sh --list-iso)
for name in "${names[@]}"; do
  printf '%s\n' "${iso[@]}" | grep -qx "$name" || die "$name is not an ISO recipe (bash packaging/build-deb.sh --list-iso)"
done
named=${#names[@]}
((named)) || names=("${iso[@]}")

recipe_version() {
  # shellcheck source=/dev/null
  (PKG_VERSION="" PKG_REVISION="" && . "packaging/packages/$1.sh" && echo "$PKG_VERSION-$PKG_REVISION")
}
listed_version() {
  awk -F'\t' -v n="$1" '$1 == n { print $2; exit }' "$list"
}
# inputs NOME: a receita e os patches/assets que ela le.
inputs() {
  local path
  echo "packaging/packages/$1.sh"
  for path in $(grep -oE 'packaging/(patches|assets)/[A-Za-z0-9._-]+' "packaging/packages/$1.sh" | sort -u); do
    [[ -e $path ]] && echo "$path"
  done
}
# changed_since_list NOME: a receita (ou o que ela le) mudou desde o commit
# que escreveu a linha dela na lista, contando o que ainda nao tem commit.
changed_since_list() {
  local base files old new
  base=$(git log -1 --format=%H -G "^$1"$'\t' -- "$list")
  [[ -n $base ]] || return 1
  mapfile -t files < <(inputs "$1")
  # A receita: sem comentarios e sem os metadados do modo "edge" do Setup
  # (PKG_UPSTREAM, PKG_COMMIT_VAR, PKG_EDGE_*), que nao mudam o .deb.
  old=$(recipe_body "$(git show "$base:packaging/packages/$1.sh")")
  new=$(recipe_body "$(< "packaging/packages/$1.sh")")
  [[ $old == "$new" ]] || return 0
  # Os patches e assets: qualquer diferenca conta.
  ((${#files[@]} > 1)) || return 1
  ! git diff --quiet "$base" -- "${files[@]:1}" ||
    [[ -n $(git ls-files --others --exclude-standard -- "${files[@]:1}") ]]
}
recipe_body() {
  grep -vE '^[[:space:]]*#|^PKG_(UPSTREAM|COMMIT_VAR|EDGE_[A-Z]+)=' <<< "$1"
}
bump_revision() {
  local file=packaging/packages/$1.sh rev new
  rev=$(sed -n 's/^PKG_REVISION="\(.*\)"/\1/p' "$file")
  [[ $rev =~ ^(.*[^0-9])?([0-9]+)$ ]] || die "$1: PKG_REVISION \"$rev\" does not end in a number"
  new=${BASH_REMATCH[1]}$((BASH_REMATCH[2] + 1))
  sed -i "s/^PKG_REVISION=\"$rev\"/PKG_REVISION=\"$new\"/" "$file"
  echo "$1: PKG_REVISION $rev -> $new"
}

todo=() stale=() bumped=()
printf '%-28s %-30s %-30s %s\n' PACOTE RECEITA LISTA ESTADO
for name in "${names[@]}"; do
  want=$(recipe_version "$name")
  have=$(listed_version "$name")
  if [[ -z $have ]]; then
    state="pacote novo"
    todo+=("$name")
  elif [[ $have != "$want" ]]; then
    state="versao nova"
    todo+=("$name")
  elif changed_since_list "$name"; then
    state="sem revisao"
    stale+=("$name")
  else
    state="em dia"
  fi
  printf '%-28s %-30s %-30s %s\n' "$name" "$want" "${have:--}" "$state"
done

[[ -n $run ]] || {
  ((${#stale[@]} == 0)) || echo "sem revisao: rode com --run --bump (ou suba o PKG_REVISION a mao)"
  ((${#todo[@]} + ${#stale[@]} == 0)) || echo "para compilar e publicar: $0 --run"
  exit 0
}

if [[ -n $bump ]]; then
  # As "sem revisao" e, se a receita foi nomeada, tambem a "em dia"
  # (rebuild pedido, por exemplo por uma lib nova).
  for name in "${names[@]}"; do
    printf '%s\n' "${todo[@]}" | grep -qx "$name" && continue
    if ((named)) || printf '%s\n' "${stale[@]}" | grep -qx "$name"; then
      bump_revision "$name"
      bumped+=("packaging/packages/$name.sh")
      todo+=("$name")
    fi
  done
elif ((${#stale[@]})); then
  die "${stale[*]}: changed without a new PKG_REVISION (use --bump)"
fi
((${#todo[@]})) || {
  echo "nada a publicar"
  exit 0
}

# Job pesado: memoria do Windows e um container por vez (CLAUDE.md 5 e 6).
if command -v powershell.exe > /dev/null; then
  rc=0
  powershell.exe -NoProfile -File "$(wslpath -w tools/docker-health.ps1)" || rc=$?
  case $rc in
    0) ;;
    1) die "Windows commit above 85%: do not start a heavy job, the Windows needs a restart" ;;
    2) die "Docker does not answer (Quit + reopen it once from the tray, then run again)" ;;
    *) die "WSL is hung (docker-health exit $rc): restart the WSL service as admin, or Windows" ;;
  esac
fi
busy=$(docker ps --format '{{.Names}} ({{.Image}})')
[[ -z $busy || -n $force ]] || die "another container is running, one heavy job at a time:
$busy
(--force to build anyway)"

echo "compilando: ${todo[*]}"
# Contexto so com o que o Dockerfile copia: o repositorio inteiro levaria a
# output/ (as ISOs) junto.
tar -c Dockerfile.packages packaging | docker build -q -f Dockerfile.packages -t fliperos-packages - > /dev/null
mkdir -p "$out"
docker run --rm -v "$PWD/$out:/pkg/output/packages" fliperos-packages \
  bash -c 'bash packaging/build-deb.sh "$@"; rc=$?; chown -R '"$(id -u):$(id -g)"' /pkg/output/packages 2> /dev/null; exit $rc' _ "${todo[@]}"

bash tools/publish-packages.sh "$out"

if [[ -z $commit ]]; then
  echo "publicado; falta o commit de $list ${bumped[*]}"
  exit 0
fi
if git diff --quiet -- "$list" "${bumped[@]}"; then
  echo "a lista nao mudou"
else
  msg="Pacotes publicados: $(for n in "${todo[@]}"; do printf '%s %s, ' "$n" "$(recipe_version "$n")"; done)"
  # So estes caminhos, mesmo com o indice dividido entre sessoes.
  git commit -q -m "${msg%, }" -- "$list" "${bumped[@]}"
  git push -q origin main || echo "push failed: git pull --rebase, then git push origin main"
  git log -1 --oneline
fi
echo "proximo passo: um update que leve os pacotes aos gabinetes (updates/notes/NNNN.md + tools/make-update.sh)"
