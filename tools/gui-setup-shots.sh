#!/bin/sh
# Roda telas de verdade do fliperos-setup na interface grafica, num sistema
# falso (tools/ui-demo.sh), e grava um PNG de cada tela mostrada em
# .shots/gui-setup:
#
#   sh tools/gui-setup-shots.sh NOME TELA "TECLAS"
#   sh tools/gui-setup-shots.sh main main "right enter esc"
#
# TELA e uma das demonstracoes do ui-demo.sh ou uma funcao screen_*. As
# teclas sao apertadas em ordem, uma por quadro; quando acabam, o processo e
# encerrado pelo tempo (as telas ficam esperando uma resposta).
set -eu

if [ "${GUI_SHOTS_IN:-0}" != 1 ]; then
  cd "$(dirname "$0")/.."
  mkdir -p .shots/gui-setup
  root=$(pwd -W 2> /dev/null || pwd)
  MSYS_NO_PATHCONV=1 exec docker run --rm -e GUI_SHOTS_IN=1 \
    -v "$root:/w:ro" -v "$root/.shots/gui-setup:/out" -w /w \
    fliperos-guitest sh tools/gui-setup-shots.sh "$@"
fi

name=$1 screen=$2 keys=${3:-}
mkdir -p "/out/$name"
rm -f "/out/$name"/*.png
export FLIPEROS_UI=gui FLIPEROS_GUI_HEADLESS=1 FLIPEROS_GUI_BG=stars
export FLIPEROS_GUI_KEYS="$keys" FLIPEROS_GUI_SHOTS="/out/$name"
export UI_GUI_DIR=/tmp/fliperos-gui UI_GUI_BIN=/w/fliperos-setup/gui/fliperos-gui
timeout "${GUI_SHOTS_TIMEOUT:-8}" bash tools/ui-demo.sh "$screen" < /dev/null > /dev/null 2>&1 || true
ls "/out/$name" | grep -c 640x240 | sed "s|^|$name: |"
