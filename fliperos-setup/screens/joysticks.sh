# shellcheck shell=bash
# Setup > Joysticks: calibracao do GunCon 2 e de volante/pedais/analogico
# (config/fliperos-calibrate) e os joysticks da porta paralela (lpt.sh).

CALIBRATE=${CALIBRATE:-/opt/fliperos/bin/fliperos-calibrate}

screen_joysticks() {
  local choice last=guncon
  while true; do
    choice=$(ui_menu "Joysticks" "" "$last" \
      "guncon|Calibrate GunCon 2 (light gun)" \
      "axes|Calibrate wheel, pedals or analog stick" \
      "lpt|LPT joysticks (parallel port)" \
      "return|Return") || return 0
    last=$choice
    case $choice in
      guncon) screen_calibrate guncon ;;
      axes) screen_calibrate axes ;;
      lpt) screen_lpt ;;
      return) return 0 ;;
    esac
  done
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
