#!/bin/sh
# Grava os prints da interface grafica (fliperos-setup/gui) em .shots/gui:
# para cada tela, NN-nome-640x240.png (o quadro que vai para a placa) e
# NN-nome-crt.png (como aparece no tubo 4:3).
#
#   docker build -t fliperos-guitest -f tools/Dockerfile.guitest tools
#   sh tools/gui-shots.sh
#
# Dentro do container (GUI_SHOTS_IN=1) grava; fora, chama o Docker.
set -eu

if [ "${GUI_SHOTS_IN:-0}" != 1 ]; then
  cd "$(dirname "$0")/.."
  mkdir -p .shots/gui
  # pwd -W: o caminho do Windows no Git Bash (o Docker Desktop nao entende
  # /c/...).
  root=$(pwd -W 2> /dev/null || pwd)
  MSYS_NO_PATHCONV=1 exec docker run --rm -e GUI_SHOTS_IN=1 \
    -v "$root:/w:ro" -v "$root/.shots/gui:/out" -w /w \
    fliperos-guitest sh tools/gui-shots.sh
fi

n=0
shot() {
  name=$1 screen=$2 keys=${3:-}
  n=$((n + 1))
  python3 fliperos-setup/gui/fliperos-gui --demo "$screen" --keys "$keys" \
    --shot "/out/$(printf '%02d' "$n")-$name"
  echo "$(printf '%02d' "$n")-$name"
}

shot main main
shot main-setup main "right"
shot live live
shot setup setup
shot setup-games setup "right right right right"
shot video video "right right"
shot joysticks joysticks
shot buttons-players players
shot buttons-capture capture
shot layout layout
shot layout-edit layoutedit "right"
shot power power
shot radio monitor "down down"
shot checklist emulators
shot yesno poweroff
shot progress install
shot error error
shot input wifi
