# shellcheck shell=bash
# Setup > Joysticks > Button mapping: os comandos de cada jogador, pegos um a
# um no controle, para o RetroArch e o GroovyMAME (config/fliperos-buttons).

BUTTONS=${BUTTONS:-/opt/fliperos/bin/fliperos-buttons}
# Os comandos, na ordem em que sao pedidos, e o nome na tela.
BUTTON_CONTROLS=(up down left right b1 b2 b3 b4 b5 b6 start coin)
declare -A BUTTON_LABELS=(
  [up]="UP" [down]="DOWN" [left]="LEFT" [right]="RIGHT"
  [b1]="BUTTON 1 (top row, left)" [b2]="BUTTON 2 (top row, middle)" [b3]="BUTTON 3 (top row, right)"
  [b4]="BUTTON 4 (bottom row, left)" [b5]="BUTTON 5 (bottom row, middle)" [b6]="BUTTON 6 (bottom row, right)"
  [start]="START" [coin]="COIN (insert coin)"
)

# buttons_capture SEGUNDOS espera o proximo comando de qualquer controle e
# imprime "INDICE ELEMENTO NOME". Status 1: o tempo acabou (pular).
buttons_capture() {
  "$BUTTONS" capture --timeout "$1" 2>> "$FLIPEROS_LOG"
}

# buttons_save MAPA grava os botoes no RetroArch e no GroovyMAME: o ctrlr
# fliperos e o joystickprovider sdljoy, em que o MAME numera os botoes como o
# SDL, na ordem do aparelho.
buttons_save() {
  "$BUTTONS" save "$1" >> "$FLIPEROS_LOG" 2>&1 || return 1
  ini_set "$MAME_INI" ctrlr fliperos
  ini_set "$MAME_INI" joystickprovider sdljoy
  log_info "botoes gravados: $(awk '{ print $1 }' "$1" | sort -u | wc -l) jogador(es)"
}
