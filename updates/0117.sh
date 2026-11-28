#!/usr/bin/env bash
# Update 117: o fliperos-setup --systems passou a dizer, no fim de cada linha, o
# que abre os jogos do sistema (a escolha de um console do Batocera filesystem:
# batocera/snes -> retroarch/snes9x). O net play, o link, a party e as paginas do
# Matchmaker decidem por ela. O frontend guarda a resposta em
# ~/.cache/fliperos/frontend-systems e so a refaz quando uma pasta muda: a de
# antes, sem o campo, seguiria valendo. Aqui ela sai (como o batocera_refresh de
# lib/batocera.sh faz) e o frontend a refaz na proxima abertura.
set -uo pipefail
home=${FLIPEROS_HOME:-/home/fliperos}
cache=$home/.cache/fliperos/frontend-systems
if [[ -f $cache ]]; then
  rm -f -- "$cache" && echo "frontend-systems cache removed: the frontend reads the systems again"
fi
exit 0
