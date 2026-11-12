# shellcheck shell=bash
# Setup > Joysticks: os botoes do painel ou do joypad (lib/buttons.sh), os
# controles Bluetooth (screens/bluetooth.sh), o layout dos botoes por numero
# de botoes do jogo, a calibracao do GunCon 2 e de volante/pedais/analogico
# (config/fliperos-calibrate) e os joysticks da porta paralela (lpt.sh). Os
# quirks USB ficam em System (screen_quirks): valem para qualquer aparelho.

CALIBRATE=${CALIBRATE:-/opt/fliperos/bin/fliperos-calibrate}

screen_joysticks() {
  local choice last=""
  local -a bt
  while true; do
    # O Bluetooth so com um adaptador (dongle USB ou da placa-mae).
    bt=()
    bluetooth_present && bt=("bluetooth|Bluetooth|Pair, connect and forget Bluetooth controllers.")
    choice=$(ui_menu_hints "Joysticks" "$(buttons_players_line)" "$last" \
      "buttons|Button mapping (all emulators)|Arcade panel or joypad: press each control when asked." \
      "${bt[@]}" \
      "layout|Buttons layout (games of 1 to 5 buttons)|Where the buttons of 1 to 5-button games go on the panel." \
      "guncon|GunCon 2 (light gun)|Calibration, screen flash and how the gun reads dark parts." \
      "axes|Calibrate wheel, pedals or analog stick|Set the range and the center of each axis." \
      "lpt|LPT joysticks (parallel port)|Arcade sticks and console pads wired to the parallel port." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      buttons) screen_buttons ;;
      bluetooth) screen_bluetooth ;;
      layout) screen_buttons_layout ;;
      guncon) screen_guncon ;;
      axes) screen_calibrate axes ;;
      lpt) screen_lpt ;;
      return) return 0 ;;
    esac
  done
}

# screen_guncon: tudo da GunCon 2 num menu (lib/buttons.sh): a calibracao, o
# flash da tela no tiro, os ajustes do driver em numeros e a recarga fora da
# tela.
screen_guncon() {
  local title="GunCon 2" choice last="" key reload summary
  local -a fields
  while true; do
    reload=On
    gun_reload_on || reload=Off
    fields=("Gun|$(gun_connected && echo connected || echo "not connected")" "Screen flash|$(gunflash_mode)")
    while IFS='|' read -r key _; do
      fields+=("$(gun_field "$key" 2)|$(gun_get "$key")")
    done < <(gun_table)
    fields+=("Off-screen reload button|$reload")
    summary=$(ui_fields "${fields[@]}")
    choice=$(ui_menu_hints "$title" "$summary" "$last" \
      "calibrate|Calibrate|Shoot the targets so the gun hits where it points." \
      "flash|Screen flash: $(gunflash_mode)|The screen lights up on a shot, so the gun sees dark parts too." \
      "values|Settings in numbers|Flash brightness and wait, dark hold, edge band." \
      "reload|Off-screen reload button: $reload|Off screen the trigger also reloads (Flycast, RetroArch)." \
      "reset|Back to the defaults|Flash, numbers and reload; the calibration stays." \
      "return|Return|Back to Joysticks.") || return 0
    last=$choice
    case $choice in
      calibrate) screen_calibrate_guns ;;
      flash) screen_gunflash ;;
      values) screen_gun_values ;;
      reload)
        if [[ $reload == On ]]; then gun_reload_set off; else gun_reload_set on; fi
        ;;
      reset)
        ui_yesno "$title" "Flash, numbers and the reload button back to the defaults? The calibration stays." no || continue
        gun_reset
        ;;
      return) return 0 ;;
    esac
  done
}

# screen_gunflash: o flash da tela no tiro.
screen_gunflash() {
  local choice
  choice=$(ui_menu_hints "Screen flash" \
    "A CRT gun only finds its aim where the screen is lit. The flash lights it on a shot." "$(gunflash_mode)" \
    "pulse|Pulse (recommended)|Two light frames per shot: dark parts hit, off screen reloads." \
    "hold|Hold|The screen stays light while the trigger is held." \
    "off|Off|No flash: a dark shot can miss or reload." \
    "return|Return|Back to GunCon 2.") || return 0
  [[ $choice == return ]] && return 0
  gunflash_set "$choice"
}

# screen_gun_values: cada ajuste pelo numero (gun_table).
screen_gun_values() {
  local key label min max help choice value last=""
  local -a entries
  while true; do
    entries=()
    while IFS='|' read -r key label min max _ _ help; do
      entries+=("$key|$label: $(gun_get "$key")|$help ($min to $max)")
    done < <(gun_table)
    entries+=("return|Return|Back to GunCon 2.")
    choice=$(ui_menu_hints "GunCon 2 settings" "Changes count right away, even in a game that is open." "$last" "${entries[@]}") ||
      return 0
    last=$choice
    [[ $choice == return ]] && return 0
    value=$(ui_input "$(gun_field "$choice" 2)" \
      "$(gun_field "$choice" 7) From $(gun_field "$choice" 3) to $(gun_field "$choice" 4)." \
      "$(gun_get "$choice")") || continue
    gun_set "$choice" "$value" || ui_msg "GunCon 2 settings" "Not a number: $value"
  done
}

# screen_buttons: os controles ligados numa lista; o escolhido diz qual
# jogador ele e (de 1 ao numero de controles ligados) e o tipo: painel de
# arcade ou JAMMA (com quantos botoes, de 1 a 8) ou joypad (o mapeador do
# Batocera). Um controle Bluetooth nao tem numero: os Bluetooth tomam os
# jogadores livres pela ordem em que conectam (fliperos-buttons). Pego e
# salvo, volta a lista para o proximo. O encoder que se diz teclado tambem
# esta na lista.
screen_buttons() {
  local title="Button mapping" choice last="" line index guid name bus player text tag rc
  local -a devices entries
  while true; do
    mapfile -t devices < <(buttons_list)
    entries=()
    for line in "${devices[@]}"; do
      IFS='|' read -r index guid name bus player <<< "$line"
      [[ $index =~ ^[0-9]+$ ]] || continue
      # O jogador e o BT na frente: um nome comprido e cortado na lista.
      tag="--"
      [[ -n $player ]] && tag="P$player"
      [[ $bus == bluetooth ]] && tag+=" BT"
      entries+=("$index|$tag $name")
    done
    if ((${#entries[@]})); then
      text="Choose a controller to map: ${#entries[@]} connected (P = player, -- = not mapped). Wired ones come first; Bluetooth (BT) ones take the players left, by the order they connect."
    else
      text="No controller is connected. Connect one (Bluetooth: Joysticks > Bluetooth) and come back."
    fi
    # UI_STYLE=controllers: na interface grafica, a lista com o icone de com
    # fio ou sem fio (o "BT") em cada controle.
    # Um controle ligado, pareado ou tirado com a lista na tela: ela se refaz
    # (status 124, com o item que estava sob o cursor).
    rc=0
    choice=$(UI_STYLE=controllers ui_menu "$title" "$text" "$last" "${entries[@]}" \
      "keyboard|Keyboard encoder (MAME default keys)" "return|Return") || rc=$?
    if ((rc == 124)); then
      last=$choice
      continue
    fi
    ((rc == 0)) || return 0
    case $choice in
      return) return 0 ;;
      keyboard)
        screen_buttons_keyboard
        continue
        ;;
    esac
    last=$choice
    for line in "${devices[@]}"; do
      [[ ${line%%|*} == "$choice" ]] && break
    done
    IFS='|' read -r index guid name bus player <<< "$line"
    screen_buttons_device "$title" "$index" "$guid" "$name" "$bus" "$player" "${#entries[@]}"
  done
}

# screen_buttons_device TITULO INDICE GUID NOME BARRAMENTO JOGADOR LIGADOS: o
# jogador do controle (o Bluetooth nao escolhe), o tipo e os comandos; no
# fim pergunta se grava (buttons_store e buttons_save).
screen_buttons_device() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 current=$6 count=$7 player kind nbuttons=0 p map shown
  local -a entries
  if [[ $bus == bluetooth ]]; then
    player=bt
    shown=${current:-$(buttons_next_player)}
  else
    ((count < 1)) && count=1
    ((count > 8)) && count=8
    ((current > count)) && count=$current
    entries=()
    for ((p = 1; p <= count; p++)); do
      entries+=("$p|Player $p")
    done
    player=$(ui_menu "$title" "Which player is $name?" "${current:-1}" "${entries[@]}" "return|Return") || return 0
    [[ $player =~ ^[0-9]+$ ]] || return 0
    shown=$player
  fi
  kind=$(ui_menu_hints "$title" "$name: what kind of controller is it?" "$([[ $bus == bluetooth ]] && echo pad || echo arcade)" \
    "arcade|Arcade stick or JAMMA panel|A stick and 1 to 8 buttons, on an encoder or a JAMMA board." \
    "pad|Joypad (console controller)|Xbox, PlayStation, Nintendo, 8BitDo...: USB or Bluetooth." \
    "return|Return|Back to the controllers.") || return 0
  case $kind in
    arcade)
      entries=()
      for ((p = 1; p <= BUTTONS_MAX; p++)); do
        entries+=("$p|$p button$( ((p > 1)) && echo s)")
      done
      # UI_STYLE=panel: na interface grafica, o painel de cada numero desenhado.
      nbuttons=$(UI_STYLE=panel ui_menu "$title" "How many buttons does it have? Start and Coin do not count." \
        "$(buttons_panel_count)" "${entries[@]}" "return|Return") || return 0
      [[ $nbuttons =~ ^[1-8]$ ]] || return 0
      ;;
    pad) ;;
    *) return 0 ;;
  esac
  map=$(mktemp)
  BUTTONS_SUMMARY="" BUTTONS_CANCELLED=0
  rm -f "$BUTTONS_CANCEL"
  padkeys_off
  if [[ $kind == pad ]]; then
    screen_buttons_pad "$title" "$shown" "$map" "$index" "$name"
  else
    screen_buttons_arcade "$title" "$shown" "$nbuttons" "$map" "$index" "$name"
  fi
  # Depois do controle, os botoes da interface: o de aceitar e o de voltar.
  if ((!BUTTONS_CANCELLED)) && [[ -n $BUTTONS_SUMMARY ]]; then
    screen_buttons_interface "$title" "$shown" "$map" "$index" "$name" "$kind"
  fi
  padkeys_on
  rm -f "$BUTTONS_CANCEL"
  ui_flush_input
  # O Esc na captura: nada muda.
  if ((BUTTONS_CANCELLED)); then
    ui_msg "$title" "Cancelled: nothing was changed."
    rm -f "$map"
    return 0
  fi
  if [[ -z $BUTTONS_SUMMARY ]]; then
    ui_msg "$title" "Nothing was pressed: nothing was changed."
    rm -f "$map"
    return 0
  fi
  if ui_yesno "$title" "Save $name for all emulators? Controls mapped: ${BUTTONS_SUMMARY%, }."; then
    buttons_store "$map" "$player" "$index" "$guid"
    if buttons_save "$BUTTONS_MAP"; then
      if [[ $player == bt ]]; then
        ui_msg "$title" "Saved. It takes the next free player when it connects (now player $shown)."
      else
        ui_msg "$title" "Saved as player $player. The emulators use it from the next game."
      fi
    else
      ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG."
    fi
  fi
  rm -f "$map"
}

# screen_buttons_interface TITULO JOGADOR MAPA INDICE NOME TIPO: os botoes da
# interface, o de aceitar (verde) e o de voltar (vermelho) nos menus do
# Setup, do frontend do FliperOS e do Attract-Mode (linhas accept e cancel no
# mapa). Sem apertar nada por 10 s fica o padrao: num joypad o de sul e o de
# leste, num painel o botao 1 e o 2. So botoes valem, e o de voltar nao pode
# ser o de aceitar.
screen_buttons_interface() {
  local title=$1 p=$2 map=$3 dev=$4 name=$5 kind=$6 which got rc element accept="" def
  local -A defaults=([accept]=b1 [cancel]=b2)
  [[ $kind == pad ]] && defaults=([accept]=b4 [cancel]=b5)
  for which in accept cancel; do
    while true; do
      # Sem o nome de posicao (sul, leste): a pessoa olha o proprio controle
      # (GameCube, Xbox, PlayStation...) e aperta o que quer.
      ui_confirm_capture "$title" "$p" "$which" 10 ||
        ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press the button that $([[ $which == accept ]] &&
          echo "accepts (green)" || echo "goes back (red)") in the menus")" "" \
          "Wait 10 seconds to keep the usual one, Esc cancels."
      rc=0
      got=$(ui_capture_wait buttons_capture 10 "" "$dev") || rc=$?
      if ((rc == 3)); then
        BUTTONS_CANCELLED=1
        return 0
      fi
      if ((rc != 0)); then
        # O padrao: o botao do mapa nesse papel.
        def=$(awk -v p="$p" -v c="${defaults[$which]}" '$1 == p && $2 == c { print $4; exit }' "$map")
        [[ $which == accept ]] && accept=$def
        break
      fi
      read -r _ element _ <<< "$got"
      if [[ ! $element =~ ^b[0-9]+$ || ($which == cancel && $element == "$accept") ]]; then
        ui_info "$title" "Use another button." "The menus need a button, and Back cannot be the same as Accept."
        sleep 1.5
        continue
      fi
      printf '%s %s %s %s %s\n' "$p" "$which" "$dev" "$element" "$name" >> "$map"
      [[ $which == accept ]] && accept=$element
      sleep 0.3
      break
    done
  done
}

# screen_buttons_arcade TITULO JOGADOR BOTOES MAPA INDICE NOME: os comandos
# de um painel de BOTOES botoes no controle INDICE, no painel desenhado (o
# comando da vez aceso na interface grafica, um X piscando no texto). So o
# controle escolhido conta; sem apertar nada por 8 s, o comando fica de
# fora. Poe em BUTTONS_SUMMARY quantos foram pegos.
screen_buttons_arcade() {
  local title=$1 p=$2 nbuttons=$3 map=$4 dev=$5 name=$6 control got index element tries used n=0 total rc
  local -a controls pressed=()
  read -r -a controls <<< "$(buttons_arcade_controls "$nbuttons")"
  total=${#controls[@]}
  printf '%s kind %s arcade %s\n' "$p" "$dev" "$name" >> "$map"
  for control in "${controls[@]}"; do
    n=$((n + 1))
    for ((tries = 0; tries < 3; tries++)); do
      ui_capture "$title" "$p" "$control" "$n" "$total" 8 "$nbuttons" "${pressed[@]}" ||
        ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press ${BUTTON_LABELS[$control]}")" "" \
          "$n of $total. Wait 8 seconds to skip it, Esc cancels."
      rc=0
      got=$(ui_capture_wait buttons_capture 8 "" "$dev") || rc=$?
      if ((rc == 3)); then
        BUTTONS_CANCELLED=1
        return 0
      fi
      ((rc == 0)) || break
      read -r index element _ <<< "$got"
      # Um botao so faz uma coisa: o que ja foi dado a outro comando nao vale.
      used=$(buttons_used "$map" "$index" "$element")
      if [[ -n $used ]]; then
        ui_info "$title" "That one is already ${used% *}." "Press another control for ${BUTTON_LABELS[$control]}."
        sleep 1.5
        continue
      fi
      printf '%s %s %s %s %s\n' "$p" "$control" "$dev" "$element" "$name" >> "$map"
      pressed+=("$control")
      sleep 0.3
      break
    done
  done
  ((${#pressed[@]})) || return 0
  BUTTONS_SUMMARY="player $p: ${#pressed[@]} of $total, "
}

# screen_buttons_pad TITULO JOGADOR MAPA INDICE NOME: o mapeador de joypad do
# Batocera (GuiInputConfig) no controle INDICE: a lista de todos os comandos
# com o desenho de cada um, pedidos na ordem dele (sul, leste, norte, oeste,
# Start, Select, direcional, ombros, analogicos, gatilhos, cliques e hotkey).
# O comando vale ao soltar, e segurar qualquer botao 1 s pula o da vez (sem
# nada por 10 s tambem). Antes, o SDL diz o tipo do controle (o desenho dos
# botoes) e, num controle que ele conhece, oferece o layout inteiro
# (screen_buttons_pad_known). Sem hotkey no fim, oferece o Select, como o
# Batocera. Poe em BUTTONS_SUMMARY quantos foram pegos.
screen_buttons_pad() {
  local title=$1 p=$2 map=$3 dev=$4 name=$5 control type got index element tries used n=0 rc label
  local total=${#PAD_CONTROLS[@]} count=0 coin=""
  local -a done=()
  if screen_buttons_pad_known "$title" "$p" "$dev" "$name" "$map"; then
    BUTTONS_SUMMARY="player $p: known layout, "
    return 0
  fi
  ((BUTTONS_CANCELLED)) && return 0
  type=${BUTTONS_PAD_TYPE:-generic}
  printf '%s kind %s pad %s\n' "$p" "$dev" "$name" >> "$map"
  for control in "${PAD_CONTROLS[@]}"; do
    n=$((n + 1))
    for ((tries = 0; tries < 3; tries++)); do
      label=$(buttons_pad_label "$control" "$type")
      ui_pad_capture "$title" "$p" "$control" "$n" "$type" "$name" "${done[@]}" ||
        ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press $label")" "" "$n of $total. Hold any button to skip it, Esc cancels."
      rc=0
      got=$(ui_capture_wait buttons_capture "$PAD_TIMEOUT" "$PAD_HOLD" "$dev") || rc=$?
      if ((rc == 3)); then
        BUTTONS_CANCELLED=1
        return 0
      fi
      if ((rc != 0)); then
        # Pulado: segurado, ou nada por PAD_TIMEOUT segundos.
        done+=("$control=-")
        break
      fi
      read -r index element _ <<< "$got"
      used=$(buttons_used "$map" "$index" "$element")
      if [[ -n $used ]]; then
        ui_info "$title" "That one is already ${used% *}." "Press another control for $label."
        sleep 1.5
        continue
      fi
      printf '%s %s %s %s %s\n' "$p" "$control" "$dev" "$element" "$name" >> "$map"
      done+=("$control=$element")
      count=$((count + 1))
      [[ $control == coin ]] && coin=$element
      sleep 0.2
      break
    done
  done
  if [[ " ${done[*]} " == *" hotkey=-"* && -n $coin ]]; then
    padkeys_on
    ui_flush_input
    if ui_yesno "$title" "No hotkey button was given. Use SELECT as the hotkey?"; then
      printf '%s hotkey %s %s %s\n' "$p" "$dev" "$coin" "$name" >> "$map"
    fi
    padkeys_off
  fi
  ((count)) || return 0
  BUTTONS_SUMMARY="player $p: $count of $total, "
}

# screen_buttons_pad_known TITULO JOGADOR INDICE NOME MAPA: o controle pelo
# SDL (fliperos-buttons identify). Guarda o tipo dele em BUTTONS_PAD_TYPE; se
# o banco do SDL o conhece, pergunta se fica o layout dele, como o
# EmulationStation faz com um controle conhecido. Status 0: o layout foi
# posto no mapa.
screen_buttons_pad_known() {
  local title=$1 p=$2 dev=$3 name=$4 map=$5 info choice kind control element
  BUTTONS_PAD_TYPE=generic
  info=$(buttons_identify "$dev") || return 1
  kind=$(sed -n 's/^type=//p' <<< "$info")
  [[ $kind =~ ^(xbox|playstation|nintendo|generic)$ ]] && BUTTONS_PAD_TYPE=$kind
  [[ $(sed -n 's/^known=//p' <<< "$info") == 1 ]] || return 1
  padkeys_on
  choice=$(ui_menu_hints "$title" "$name: FliperOS knows this controller and where each of its buttons is." use \
    "use|Use its layout|Each button where the controller has it: nothing more to press." \
    "map|Map each button|Press each control when asked, as in Batocera.") || choice=cancel
  padkeys_off
  if [[ $choice == cancel ]]; then
    BUTTONS_CANCELLED=1
    return 2
  fi
  [[ $choice == use ]] || return 1
  printf '%s kind %s pad %s\n' "$p" "$dev" "$name" >> "$map"
  while read -r control element; do
    printf '%s %s %s %s %s\n' "$p" "$control" "$dev" "$element" "$name" >> "$map"
  done < <(sed -n 's/^bind //p' <<< "$info")
  return 0
}

# screen_buttons_keyboard: o encoder que se diz teclado, no layout do MAME
# (lib/buttons.sh): so o numero de jogadores, nada a apertar.
screen_buttons_keyboard() {
  local title="Button mapping" players
  players=$(ui_menu "$title" \
    "The MAME default keys for each player in all emulators (player 1: arrows, Ctrl, Alt, Space, Shift, Z, X, 1 start, 5 coin). How many players?" \
    "" "1|1 player" "2|2 players" "3|3 players" "4|4 players" "return|Return") || return 0
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
  local title="Buttons layout" count choice last="" entries=()
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

# screen_calibrate_guns: a calibracao das GunCon 2. Pergunta quantos jogadores
# tem pistola (de 1 ao numero de pistolas ligadas) e calibra uma por uma: com
# mais de uma ligada, quem atira primeiro diz qual e a do jogador. A faixa de
# cada pistola vale pela porta USB dela (fliperos-calibrate).
screen_calibrate_guns() {
  local tty=${GUN_TTY:-/dev/tty}
  local title="GunCon 2" found=() paths=() remaining=() entries=() line path players p i dev tmp label saved=0 gui=0
  mapfile -t found < <("$CALIBRATE" list gun 2> /dev/null)
  if ((${#found[@]} == 0)); then
    ui_msg "$title" "No GunCon 2 was found." "" "Connect it to a USB port and try again."
    return 0
  fi
  for line in "${found[@]}"; do
    paths+=("${line%%|*}")
  done
  players=1
  if ((${#paths[@]} > 1)); then
    for ((i = 1; i <= ${#paths[@]}; i++)); do
      entries+=("$i|$i player$(((i > 1)) && echo s)")
    done
    players=$(ui_menu "$title" "${#paths[@]} guns are connected. How many players? Each one is calibrated in turn." \
      "${#paths[@]}" "${entries[@]}" "return|Return") || return 0
    [[ $players == return ]] && return 0
  fi
  ui_yesno "$title" "The screen turns white with a target in each corner. Aim at the + in the middle of each target and pull the trigger 3 times; then one shot in the center checks the result." \
    || return 0
  ui_gui_alive && gui=1
  remaining=("${paths[@]}")
  for ((p = 1; p <= players; p++)); do
    label=""
    ((players > 1)) && label="Player $p"
    if ((${#remaining[@]} == 1)); then
      dev=${remaining[0]}
    else
      tmp=$(mktemp)
      ui_clear
      if ! ui_text env FLIPEROS_GUN_LABEL="$label" "$CALIBRATE" trigger "$tmp" "${remaining[@]}" < "$tty" > "$tty" 2>&1; then
        rm -f "$tmp"
        ui_palette > "$tty"
        break
      fi
      dev=$(< "$tmp")
      rm -f "$tmp"
    fi
    ui_clear
    if FLIPEROS_CALIBRATE_GUI=$gui FLIPEROS_GUI_DIR=$SETUP_DIR/gui \
      ui_text "$CALIBRATE" guncon2 "$dev" ${label:+"$label"} < "$tty" > "$tty" 2>&1; then
      saved=$((saved + 1))
      log_info "calibracao guncon salva: $dev ${label:+($label)}"
    else
      ui_palette > "$tty"
      break
    fi
    for i in "${!remaining[@]}"; do
      [[ ${remaining[i]} == "$dev" ]] && unset 'remaining[i]'
    done
    remaining=("${remaining[@]}")
  done
  ui_palette > "$tty"
  if ((saved == players)); then
    ui_msg "$title" "Calibration saved ($saved gun$(((saved > 1)) && echo s)). It is applied again every time a gun is connected."
  elif ((saved > 0)); then
    ui_msg "$title" "Saved for $saved of $players guns. Run it again for the rest."
  else
    ui_msg "$title" "Nothing was saved."
  fi
  ui_flush_input
}

# screen_calibrate axes escolhe o volante, pedal ou analogico e roda o
# calibrador, que desenha a propria tela. A pistola tem a sua
# (screen_calibrate_guns).
screen_calibrate() {
  local found=() entries=() line path name dev title="Calibration"
  mapfile -t found < <("$CALIBRATE" list axes 2> /dev/null)
  if ((${#found[@]} == 0)); then
    ui_msg "$title" "No wheel, pedals or analog stick was found." "" "Connect it and try again."
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
  ui_yesno "$title" "Move every axis to its limits (wheel to both sides, each pedal all the way), then leave everything at rest. The values show live on the screen." \
    || return 0
  ui_clear
  if ui_text "$CALIBRATE" axes "$dev" < /dev/tty > /dev/tty 2>&1; then
    ui_palette > /dev/tty
    log_info "calibracao axes salva: $dev"
    ui_msg "$title" "Calibration saved. It is applied again every time the controller is connected."
  else
    ui_palette > /dev/tty
    ui_msg "$title" "Nothing was saved."
  fi
  ui_flush_input
}
