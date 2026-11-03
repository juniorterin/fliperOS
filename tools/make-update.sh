#!/usr/bin/env bash
# Publica o commit atual como o proximo update do FliperOS: acrescenta
# "N<TAB>commit<TAB>treehash<TAB>reboot<TAB>titulo" ao updates/index, faz o
# commit dele e o push. Os gabinetes perguntam no proximo boot com rede
# (config/fliperos-update) e aplicam os updates sempre em ordem.
#
#   tools/make-update.sh "Title shown on the cabinet" [--reboot]
#
# O commit atual tem de estar no origin/main (o gabinete o baixa do
# GitHub). Passos extras so deste update vao em updates/NNNN.sh, no mesmo
# commit; o changelog dele, obrigatorio, em updates/notes/NNNN.md (o gabinete
# o mostra antes de perguntar se aplica). O push posta o update no grupo do
# Telegram: com o docs/telegram/update-NNNN.md (portugues, fotos) se existir,
# senao com o titulo e o changelog. Roda onde houver python3 de Linux
# (no Windows, pelo WSL).
set -euo pipefail
cd "$(dirname "$0")/.."
die() {
  echo "make-update: $*" >&2
  exit 1
}
title=${1:?Uso: tools/make-update.sh "titulo" [--reboot]}
[[ $title != *$'\t'* ]] || die "the title cannot have a tab"
reboot=no
[[ ${2:-} == --reboot ]] && reboot=yes
git=$(type -P git)

[[ -z $("$git" status --porcelain --untracked-files=no) ]] || die "commit the changes first"
"$git" fetch -q origin
commit=$("$git" rev-parse HEAD)
[[ $commit == "$("$git" rev-parse origin/main)" ]] || die "HEAD is not origin/main: push (or pull) first"
last=$(awk -F'\t' '/^[0-9]/ { n = $1 } END { print n + 0 }' updates/index)
n=$((last + 1))
script=$(printf 'updates/%04d.sh' "$n")
if [[ -f $script ]] && ! "$git" cat-file -e "$commit:$script" 2> /dev/null; then
  die "$script is not in the commit"
fi
# O changelog do update, que o gabinete mostra antes de perguntar se aplica
# (fliperos-update notes): sem ele, o update nao sai.
notes=$(printf 'updates/notes/%04d.md' "$n")
"$git" cat-file -e "$commit:$notes" 2> /dev/null ||
  die "write $notes (what changes, in English, shown on the cabinet) and commit it first"

# O treehash da arvore que o gabinete baixa (o git archive do commit, como
# o tar do GitHub), pela mesma funcao do fliperos-update. Sem o autocrlf:
# no Windows ele poria CRLF onde o .gitattributes nao fixa LF, e o hash nao
# bateria com o tar do GitHub.
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
"$git" -c core.autocrlf=false archive --format=tar "$commit" | tar x -C "$tmp"
tree=$(python3 - "$tmp" << 'PY'
import importlib.machinery
import importlib.util
import sys

loader = importlib.machinery.SourceFileLoader('fliperos_update', 'config/fliperos-update')
spec = importlib.util.spec_from_loader('fliperos_update', loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
print(module.treehash(sys.argv[1]))
PY
)

printf '%d\t%s\t%s\t%s\t%s\n' "$n" "$commit" "$tree" "$reboot" "$title" >> updates/index
# O push posta o update no grupo do Telegram (.github/workflows/telegram.yml):
# o texto tem de passar antes, ou o update sai sem o aviso.
if ! python3 tools/telegram-post.py --dry-run --update "$n" > /dev/null; then
  "$git" checkout -q -- updates/index
  die "the Telegram text of update $n does not pass (python3 tools/telegram-post.py --dry-run --update $n)"
fi
printf 'Update %d: %s\n\nPublica o commit %s como o update %d (updates/index).\n' \
  "$n" "$title" "${commit:0:7}" "$n" > "$tmp/msg"
"$git" add updates/index
"$git" commit -q -F "$tmp/msg"
"$git" push -q origin main
echo "Update $n published: ${commit:0:7} ($title)"
