#!/usr/bin/env bash
# Fotografa uma tela do fliperos-setup em texto, num tmux de tamanho fixo:
#
#   tools/ui-snapshot.sh TELA [LARGURA ALTURA] [TECLAS...]
#
# Ex.: tools/ui-snapshot.sh screen_live_menu 80 30
#      tools/ui-snapshot.sh results 64 24
# Precisa de tmux e gum (container fliperos-uitest).
set -euo pipefail
screen=$1
width=${2:-80}
height=${3:-30}
shift $(($# >= 3 ? 3 : $#))
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
session=demo$$
tmux new-session -d -s "$session" -x "$width" -y "$height" \
  "TERM=xterm-256color bash $src/tools/ui-demo.sh $screen; sleep 60"
sleep 2
for key in "$@"; do
  tmux send-keys -t "$session" "$key"
  sleep 1
done
tmux capture-pane -p -t "$session"
tmux kill-session -t "$session"
