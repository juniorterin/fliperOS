# shellcheck shell=bash
# Setup > Joysticks: os botoes do painel (lib/buttons.sh), o layout deles por
# numero de botoes do jogo, a calibracao do GunCon 2 e de volante/pedais/analogico
# (config/fliperos-calibrate) e os joysticks da porta paralela (lpt.sh). Os
# quirks USB ficam em System (screen_quirks): valem para qualquer aparelho.

CALIBRATE=${CALIBRATE:-/opt/fliperos/bin/fliperos-calibrate}

screen_joysticks() {
  local choice last=guncon
  while true; do
    choice=$(ui_menu_hints "Joysticks" "" "$last" \
      "buttons|Button mapping (all emulators)|Teach FliperOS the panel: press each control when asked." \
      "layout|Buttons layout (games of 1 to 5 buttons)|Where the buttons of 1 to 5-button games go on the panel." \
      "guncon|Calibrate GunCon 2 (light gun)|Shoot the targets so the gun hits where it points." \
      "axes|Calibrate wheel, pedals or analog stick|Set the range and the center of each axis." \
      "lpt|LPT joysticks (parallel port)|Arcade sticks and console pads wired to the parallel port." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      buttons) screen_buttons ;;
      layout) screen_buttons_layout ;;
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
  local title="Button mapping" kind players p control dev name got index element tries summary map n
  local -a pressed
  kind=$(ui_menu_hints "$title" "What is wired to the panel?" panel \
    "panel|Controllers (press each control)|Joystick encoders and pads: press each control when asked." \
    "keyboard|Keyboard encoder (MAME default keys)|An encoder that types keys (I-PAC and others) in the MAME layout." \
    "return|Return|Back to Joysticks.") || return 0
  case $kind in
    keyboard)
      screen_buttons_keyboard
      return 0
      ;;
    return) return 0 ;;
  esac
  players=$(ui_menu "$title" \
    "Map the panel for all emulators, one player at a time: press each control when asked. How many players?" \
    2 "1|1 player" "2|2 players" "3|3 players" "4|4 players" "return|Return") || return 0
  [[ $players == return ]] && return 0
  map=$(mktemp)
  padkeys_off
  for ((p = 1; p <= players; p++)); do
    dev="" n=0 pressed=()
    for control in "${BUTTON_CONTROLS[@]}"; do
      n=$((n + 1))
      for ((tries = 0; tries < 3; tries++)); do
        # Na interface grafica, o painel desenhado com o comando da vez aceso.
        ui_capture "$title" "$p" "$control" "$n" "${#BUTTON_CONTROLS[@]}" 8 "${pressed[@]}" ||
          ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press ${BUTTON_LABELS[$control]}")" "" \
            "$n of ${#BUTTON_CONTROLS[@]}. Wait 8 seconds to skip it."
        got=$(buttons_capture 8) || break
        read -r index element name <<< "$got"
        if [[ -z $dev || $index == "$dev" ]]; then
          dev=$index
          printf '%s %s %s %s %s\n' "$p" "$control" "$index" "$element" "$name" >> "$map"
          pressed+=("$control")
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
  if ui_yesno "$title" "Save the mapping for all emulators? Controls mapped: ${summary%, }."; then
    if buttons_save "$map"; then
      ui_msg "$title" "Saved. The emulators use it from the next game."
    else
      ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG."
    fi
  fi
  rm -f "$map"
}

# screen_buttons_keyboard: o encoder que se diz teclado, no layout do MAME
# (lib/buttons.sh): so o numero de jogadores, nada a apertar.
screen_buttons_keyboard() {
  local title="Button mapping" players
  players=$(ui_menu "$title" \
    "The MAME default keys for each player in all emulators (player 1: arrows, Ctrl, Alt, Space, Shift, Z, X, 1 start, 5 coin). How many players?" \
    2 "1|1 player" "2|2 players" "3|3 players" "4|4 players" "return|Return") || return 0
  [[ $players == return ]] && return 0
  ui_info "$title" "Saving the keys for all emulators..."
  if buttons_keyboard "$players"; then
    ui_msg "$title" "Saved. The emulators use the MAME keys from the next game." "" \
      "Players 3 and 4 have keys for the stick and buttons 1 to 3 only, as in MAME."
  else
    ui_msg "$title" "$(ui_bad "Could not save the keys.")" "Details in $FLIPEROS_LOG."
  fi
}

# screen_buttons_layout: de cada numero de botoes (1 a 5), onde ficam no
# painel os botoes do jogo (lib/buttons.sh). O painel e o do Button mapping:
# sem ele nao ha o que arrumar.
screen_buttons_layout() {
  local title="Buttons layout" count choice last=1 entries=()
  local -a order
  if [[ ! -s $BUTTONS_MAP ]]; then
    ui_msg "$title" "The panel is not mapped yet." "" \
      "Do Button mapping first: the layout moves the buttons mapped there."
    return 0
  fi
  while true; do
    entries=()
    for count in "${BUTTONS_LAYOUT_COUNTS[@]}"; do
      read -r -a order <<< "$(buttons_layout_get "$count")"
      entries+=("$count|$count-button games   $(buttons_layout_row "${order[@]}")")
    done
    # UI_STYLE=layout: na interface grafica, o painel de cada um como icone.
    choice=$(UI_STYLE=layout ui_menu "$title" \
      "Where the buttons of a game go on the panel, by how many buttons the game uses. For GroovyMAME, the MAME cores of RetroArch, Model 2 and Model 3." \
      "$last" "${entries[@]}" "return|Return") || return 0
    [[ $choice == return ]] && return 0
    last=$choice
    screen_buttons_layout_edit "$choice"
  done
}

# screen_buttons_layout_edit BOTOES: a posicao de cada botao do jogo, um a
# um, com o painel desenhado ate ali; no fim confirma e aplica.
screen_buttons_layout_edit() {
  local count=$1 title n position choice plural=s
  local -a order=() entries grid
  ((count == 1)) && plural=""
  title="Buttons layout: $count-button games"
  for ((n = 1; n <= count; n++)); do
    entries=()
    for position in 1 2 3 4 5 6; do
      [[ " ${order[*]} " == *" $position "* ]] || entries+=("$position|${BUTTONS_POSITIONS[position - 1]}")
    done
    ((n > 1)) || entries+=("default|Default layout (button 1 at the top left, in order)")
    # Na interface grafica a posicao e escolhida no proprio painel.
    if choice=$(ui_layout_pick "$title" "$count" "$((n == 1))" "${order[@]}"); then
      :
    elif (($? == 1)); then
      return 0
    else
      mapfile -t grid < <(buttons_layout_grid "${order[@]}")
      choice=$(ui_menu "$title" "${grid[0]}"$'\n'"${grid[1]}"$'\n\n'"Where is BUTTON $n of the game?" \
        "${entries[0]%%|*}" "${entries[@]}") || return 0
    fi
    if [[ $choice == default ]]; then
      read -r -a order <<< "$(seq -s ' ' 1 "$count")"
      break
    fi
    order+=("$choice")
  done
  mapfile -t grid < <(buttons_layout_grid "${order[@]}")
  ui_yesno "$title" "${grid[0]}"$'\n'"${grid[1]}"$'\n\n'"Use this layout in the games of $count button$plural?" ||
    return 0
  if ! buttons_layout_set "$count" "${order[@]}"; then
    ui_msg "$title" "$(ui_bad "Could not save the layout.")" "Details in $FLIPEROS_LOG."
    return 0
  fi
  ui_info "$title" "Applying the layout to the games..." "" \
    "The first time it reads the GroovyMAME game list: about a minute."
  if buttons_layout_apply; then
    ui_msg "$title" "Saved. The games use it from the next one opened."
  else
    ui_msg "$title" "$(ui_bad "Could not apply the layout.")" "Details in $FLIPEROS_LOG."
  fi
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
  # Na interface grafica, a calibracao da pistola tambem e desenhada nela
  # (gui/gunscreen.py); a interface solta o video para o calibrador (ui_text).
  local gui=0
  ui_gui_alive && gui=1
  if FLIPEROS_CALIBRATE_GUI=$gui FLIPEROS_GUI_DIR=$SETUP_DIR/gui \
    ui_text "$CALIBRATE" "${kind/guncon/guncon2}" "$dev" < /dev/tty > /dev/tty 2>&1; then
    ui_palette > /dev/tty
    log_info "calibracao $kind salva: $dev"
    ui_msg "$title" "Calibration saved. It is applied again every time the controller is connected."
  else
    ui_palette > /dev/tty
    ui_msg "$title" "Nothing was saved."
  fi
  ui_flush_input
}
