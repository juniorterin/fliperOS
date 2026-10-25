#!/usr/bin/env bash
# Update 22: o buttons.cfg do RetroArch refeito de novo do mapa salvo: o do
# update 21 bloqueava tambem o lado sem uso das direcoes, e no driver
# linuxraw o direcional do Xbox 360 so anda por ele. O do update 21:
# deixava "nul" no lado sem uso de cada bind, e o RetroArch usava ali o do
# perfil automatico do controle: num painel que se diz Xbox 360, o botao 2
# apertava junto o 5 no MAME 2010 (config/fliperos-buttons, RA_NONE_BTN).
set -euo pipefail
map=/etc/fliperos/buttons.map
buttons=/opt/fliperos/bin/fliperos-buttons
[[ -s $map && -x $buttons ]] || exit 0
"$buttons" save "$map" > /dev/null
