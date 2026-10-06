#!/usr/bin/env bash
# Publica as paginas de docs/wiki na wiki do GitHub (o repositorio
# <repositorio>.wiki.git). As paginas sao mantidas aqui, junto do codigo; la
# os links entre paginas vao sem o ".md".
#
#   bash tools/wiki-publish.sh            publica na wiki do "origin"
#   bash tools/wiki-publish.sh --prune    idem, apagando de la as paginas que nao existem aqui
#   bash tools/wiki-publish.sh --to DIR   so grava as paginas convertidas em DIR (sem git)
#
# O GitHub so cria o repositorio da wiki quando a primeira pagina e salva
# pelo site: sem isso o clone falha com "Repository not found".
set -euo pipefail
root=$(cd "$(dirname "$0")/.." && pwd)
prune=0 to="" remote=""
while (($#)); do
  case $1 in
    --prune) prune=1; shift ;;
    --to) to=${2:?--to needs a folder}; shift 2 ;;
    *) remote=$1; shift ;;
  esac
done

# convert DESTINO grava as paginas com os links da wiki ("[x](Pagina.md)" e
# "[x](Pagina.md#secao)" viram "[x](Pagina)" e "[x](Pagina#secao)").
convert() {
  local page
  mkdir -p "$1"
  for page in "$root"/docs/wiki/*.md; do
    sed -E 's/\]\(([A-Za-z0-9_-]+)\.md(#[^)]*)?\)/](\1\2)/g' "$page" > "$1/${page##*/}"
  done
}

if [[ -n $to ]]; then
  convert "$to"
  echo "Pages written to $to"
  exit 0
fi

if [[ -z $remote ]]; then
  remote=$(git -C "$root" remote get-url origin)
  remote=${remote%.git}.wiki.git
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
if ! git clone -q "$remote" "$work/wiki" 2> "$work/err"; then
  cat "$work/err" >&2
  cat >&2 << 'EOF'

The wiki doesn't exist on GitHub yet: its repository is only created when the
first page is saved through the website. Open the repository's Wiki tab, click
"Create the first page" and save it (the content doesn't matter: it gets
replaced). Then run this script again.
EOF
  exit 1
fi

# O que so existe la (pagina criada pelo site) fica, a nao ser com --prune.
extra=()
for page in "$work"/wiki/*.md; do
  [[ -e $page ]] || continue
  [[ -f $root/docs/wiki/${page##*/} ]] || extra+=("${page##*/}")
done
convert "$work/wiki"
if ((${#extra[@]})); then
  if ((prune)); then
    (cd "$work/wiki" && rm -f -- "${extra[@]}")
    echo "Deleted from the wiki (not in docs/wiki): ${extra[*]}"
  else
    echo "Only on the wiki, left as they are (--prune deletes them): ${extra[*]}"
  fi
fi

cd "$work/wiki"
git add -A
if git diff --cached --quiet; then
  echo "The wiki already matches docs/wiki."
  exit 0
fi
# O autor e o do repositorio principal.
git -c "user.name=$(git -C "$root" config user.name)" -c "user.email=$(git -C "$root" config user.email)" \
  commit -q -m "docs/wiki from $(git -C "$root" rev-parse --short HEAD)"
git push -q origin HEAD
echo "Wiki published: $(git diff --name-only HEAD~1 HEAD 2> /dev/null | wc -l) page(s) changed"
