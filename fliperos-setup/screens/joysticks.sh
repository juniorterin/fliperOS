# shellcheck shell=bash
# Setup > Joysticks: calibracao do GunCon 2 e de volante/pedais/analogico
# (config/fliperos-calibrate) e os joysticks da porta paralela (lpt.sh).

CALIBRATE=${CALIBRATE:-/opt/fliperos/bin/fliperos-calibrate}

screen_joysticks() {
  local choice last=guncon
  while true; do
    choice=$(ui_menu "Joysticks" "" "$last" \
      "buttons|Button mapping (RetroArch and GroovyMAME)" \
      "guncon|Calibrate GunCon 2 (light gun)" \
      "axes|Calibrate wheel, pedals or analog stick" \
      "lpt|LPT joysticks (parallel port)" \
      "return|Return") || return 0
    last=$choice
    case $choice in
      buttons) screen_buttons ;;
      guncon) screen_calibrate guncon ;;
      axes) screen_calibrate axes ;;
      lpt) screen_lpt ;;
      return) return 0 ;;
    esac
  done
}

# screen_buttons: quantos jogadores e, de cada um, os comandos na ordem do
# painel, pegos no proprio controle (o primeiro comando diz qual controle e
# o do jogador). Sem apertar nada por um tempo, o comando fica de fora. O
# controle como teclado do menu fica desligado enquanto isso: os botoes
# apertados nao podem responder o menu.
screen_buttons() {
  local title="Button mapping" players p control dev name got index element tries summary map n
  players=$(ui_menu "$title" \
    "Map the panel for RetroArch and GroovyMAME, one player at a time: press each control when asked. How many players?" \
    2 "1|1 player" "2|2 players" "3|3 players" "4|4 players" "return|Return") || return 0
  [[ $players == return ]] && return 0
  map=$(mktemp)
  padkeys_off
  for ((p = 1; p <= players; p++)); do
    dev="" n=0
    for control in "${BUTTON_CONTROLS[@]}"; do
      n=$((n + 1))
      for ((tries = 0; tries < 3; tries++)); do
        ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press ${BUTTON_LABELS[$control]}")" "" \
          "$n of ${#BUTTON_CONTROLS[@]}. Wait 8 seconds to skip it."
        got=$(buttons_capture 8) || break
        read -r index element name <<< "$got"
        if [[ -z $dev || $index == "$dev" ]]; then
          dev=$index
          printf '%s %s %s %s %s\n' "$p" "$control" "$index" "$element" "$name" >> "$map"
          sleep 0.3
          break
        fi
        ui_info "$title" "That was another controller." "Press it on the controller of player $p."
        sleep 1.5
      done
    done
  done
  padkeys_on
  ui_flush_input
  if [[ ! -s $map ]]; then
    ui_msg "$title" "Nothing was pressed: nothing was changed."
    rm -f "$map"
    return 0
  fi
  summary=$(awk '{ print $1 }' "$map" | sort | uniq -c | awk '{ printf "player %s: %d of 12, ", $2, $1 }')
  if ui_yesno "$title" "Save the mapping for RetroArch and GroovyMAME? Controls mapped: ${summary%, }."; then
    if buttons_save "$map"; then
      ui_msg "$title" "Saved. RetroArch and GroovyMAME use it from the next game."
    else
      ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG."
    fi
  fi
  rm -f "$map"
}

# screen_calibrate guncon|axes escolhe o controle e roda o calibrador, que
# desenha a propria tela (a pistola precisa da tela branca).
screen_calibrate() {
  local kind=$1 found=() entries=() line path name dev title
  [[ $kind == guncon ]] && title="GunCon 2" || title="Calibration"
  mapfile -t found < <("$CALIBRATE" list "${kind/guncon/gun}" 2> /dev/null)
  if ((${#found[@]} == 0)); then
    if [[ $kind == guncon ]]; then
      ui_msg "$title" "No GunCon 2 was found." "" "Connect it to a USB port and try again."
    else
      ui_msg "$title" "No wheel, pedals or analog stick was found." "" "Connect it and try again."
    fi
    return 0
  fi
  for line in "${found[@]}"; do
    IFS='|' read -r path name _ <<< "$line"
    entries+=("$path|$name (${path##*/})")
  done
  if ((${#entries[@]} == 1)); then
    dev=${found[0]%%|*}
  else
    dev=$(ui_menu "$title" "Which one?" "" "${entries[@]}") || return 0
  fi
  if [[ $kind == guncon ]]; then
    ui_yesno "$title" "The screen turns white with a target in each corner. Aim at the + in the middle of each target and pull the trigger 3 times; then one shot in the center checks the result." \
      || return 0
  else
    ui_yesno "$title" "Move every axis to its limits (wheel to both sides, each pedal all the way), then leave everything at rest. The values show live on the screen." \
      || return 0
  fi
  ui_clear
  if "$CALIBRATE" "${kind/guncon/guncon2}" "$dev" < /dev/tty > /dev/tty 2>&1; then
    ui_palette > /dev/tty
    log_info "calibracao $kind salva: $dev"
    ui_msg "$title" "Calibration saved. It is applied again every time the controller is connected."
  else
    ui_palette > /dev/tty
    ui_msg "$title" "Nothing was saved."
  fi
  ui_flush_input
}
