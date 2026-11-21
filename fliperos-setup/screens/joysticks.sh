# shellcheck shell=bash
# Setup > Joysticks: os controles e paineis de arcade, um de cada vez (Controllers
# / Arcade panel: o player, o mapa, o layout dos botoes por numero de botoes do
# jogo e o visual de cada um, lib/buttons.sh), os controles Bluetooth
# (screens/bluetooth.sh), a calibracao do GunCon 2 e de volante/pedais/analogico
# (config/fliperos-calibrate). Os joysticks da porta paralela (lpt.sh), a
# vibracao e a luz dos joypads ficam dentro de Controllers / Arcade panel. Os
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
      "controllers|Controllers / Arcade panel|Player, mapping, buttons layout and visual of each one." \
      "${bt[@]}" \
      "guncon|GunCon 2 (light gun)|Calibration, screen flash and how the gun reads dark parts." \
      "axes|Wheels, pedals and analog sticks|Set the range and the center of each axis." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      controllers) screen_controllers ;;
      bluetooth) screen_bluetooth ;;
      guncon) screen_guncon ;;
      axes) screen_calibrate axes ;;
      return) return 0 ;;
    esac
  done
}

# screen_padcolor: a cor da luz dos controles que a mostram ao Linux
# (lib/buttons.sh, config/fliperos-padcolor); muda na hora nos ligados.
screen_padcolor() {
  local title="Controller light" choice current name label hex value
  local -a entries=()
  current=$(padcolor_get)
  choice=custom
  [[ $current == off ]] && choice=off
  while IFS='|' read -r name label hex; do
    if [[ $hex == fliperos ]]; then
      entries+=("$name|$label|8BitDo: purple roulette, purple/pink rings in games.")
    else
      entries+=("$name|$label|#$hex on the controller light.")
    fi
    [[ $hex == "$current" ]] && choice=$name
  done < <(padcolor_table)
  entries+=("custom|Other colour|Type the colour as RRGGBB (like 7a00ff)."
    "off|Off|FliperOS leaves the light as the controller sets it."
    "return|Return|Back to Joysticks.")
  choice=$(ui_menu_hints "$title" \
    "$(padcolor_status)" \
    "$choice" "${entries[@]}") || return 0
  case $choice in
    return) return 0 ;;
    off)
      padcolor_set off
      ui_msg "$title" "Off. A controller already lit keeps its colour until it connects again."
      ;;
    custom)
      value=$(ui_input "$title" "The colour as RRGGBB, like 7a00ff (the FliperOS purple)." \
        "$([[ $current =~ ^[0-9a-f]{6}$ ]] && echo "$current")") || return 0
      padcolor_set "$value" || ui_msg "$title" "Not a colour: $value. Six digits 0-9 and a-f, like 7a00ff."
      ;;
    *)
      padcolor_set "$(padcolor_table | awk -F'|' -v n="$choice" '$1 == n {print $3}')"
      ;;
  esac
  [[ ${PADCOLOR_PROFILE:-0} == 1 ]] && ui_msg "$title" \
    "The 8BitDo had no profile, so it got profile 1 with this colour and its buttons as they are. Press its profile button once to use it."
  return 0
}

# screen_haptic: a vibracao dos controles modernos (lib/buttons.sh, config/
# fliperos-haptic): a forca geral e o preset de cada evento do menu e dos
# frontends. Escolher um preset o toca nos controles ligados.
screen_haptic() {
  local title="Haptic events" choice last="" key label default hint
  local -a entries
  while true; do
    entries=("haptic-strength|Strength: $(haptic_strength_get)|Overall force: low, on, high or off (off silences every event, also game start and end).")
    while IFS='|' read -r key label default hint; do
      entries+=("haptic-$key|$label: $(haptic_label "$(haptic_get "$key")")|$hint")
    done < <(haptic_events)
    entries+=("return|Return|Back to Joysticks.")
    choice=$(ui_menu_hints "$title" \
      "Vibration needs a controller with rumble (Xbox, 8BitDo, DualSense...). Pick an event, then a preset: it plays at once." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      haptic-strength) screen_haptic_strength ;;
      haptic-*) screen_haptic_event "${choice#haptic-}" ;;
    esac
  done
}

# screen_haptic_strength: haptic= (on e o padrao).
screen_haptic_strength() {
  local choice
  choice=$(ui_menu_hints "Haptic strength" "Half, normal or one and a half times the force of every vibration." \
    "$(haptic_strength_get)" \
    "low|Low|Half the force." \
    "on|On|The normal force." \
    "high|High|One and a half times the force." \
    "off|Off|No vibration at all.") || return 0
  haptic_strength_set "$choice"
}

# screen_haptic_event CHAVE: os presets para este evento ("off" e os que o
# fliperos-haptic conhece, cada um com a dica).
screen_haptic_event() {
  local key=$1 label name hint default choice
  local -a entries=()
  while IFS='|' read -r name label default hint; do
    [[ $name == "$key" ]] && break
  done < <(haptic_events)
  entries+=("haptic-off|Off|No vibration for this event.")
  while IFS='|' read -r name hint; do
    entries+=("haptic-$name|$name$([[ $name == "$default" ]] && echo ' (default)')|${hint:-A preset.}")
  done < <(haptic_presets)
  choice=$(ui_menu_hints "$label" "Pick the vibration for this event." "haptic-$(haptic_get "$key")" "${entries[@]}") || return 0
  haptic_set "$key" "${choice#haptic-}"
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

# ── Controllers / Arcade panel ───────────────────────────────────

# screen_controllers: Setup > Joysticks > Controllers / Arcade panel. Um submenu com o que
# se faz com os controles: mapear os controles (as oito vagas de player, abaixo), o encoder
# de teclado do MAME (P1 e P2 sem mapear nada), o LPT (painel de arcade na porta paralela),
# a vibracao e a luz dos joypads.
screen_controllers() {
  local title="Controllers / Arcade panel" choice last=""
  while true; do
    choice=$(ui_menu_hints "$title" "Set up the controllers and what goes with them." "$last" \
      "map|Map controllers|Give each player a controller and set it up." \
      "kbenc|Keyboard encoder: $(buttons_keyboard_on && echo on || echo off)|Players 1 and 2 on a MAME keys USB encoder." \
      "lpt|Add LPT joysticks|Panels and joysticks on the parallel port." \
      "haptic|Haptic events|Joypad vibration in the games." \
      "lights|Lights: $(padcolor_name)|The colour of the joypad lights." \
      "return|Return|Back to Joysticks.") || return 0
    last=$choice
    case $choice in
      map) screen_controllers_map ;;
      kbenc) screen_keyboard_encoder ;;
      lpt) screen_lpt ;;
      haptic) screen_haptic ;;
      lights) screen_padcolor ;;
      return) return 0 ;;
    esac
  done
}

# screen_controllers_map: Map controllers. Oito vagas, Player 1 a Player 8, duas por linha, cada
# uma um cartao com o controle que e dela (o desenho dele e o nome; BT: Bluetooth) ou vazia.
# Ao entrar numa vaga o Setup pede para apertar um botao do controle que sera aquele player
# (screen_controller_slot): o controle apertado toma a vaga (se ela era de outro, os dois
# trocam) e abre o menu dele (screen_controller). Com o encoder de teclado ligado, P1 e P2 sao
# dele. Um teclado USB nao e um controle. A lista se refaz sozinha quando um controle e ligado
# ou tirado (status 124 da interface). A dica de cada vaga e "VISUAL: tipo, ligacao": o visual
# e o desenho do cartao.
screen_controllers_map() {
  local title="Map controllers" choice last="" text rc p tag hint line kind
  local index guid name bus player visual mapped
  local -a devices entries
  while true; do
    mapfile -t devices < <(buttons_devices)
    entries=()
    for ((p = 1; p <= 8; p++)); do
      tag="P$p (empty)"
      hint="Empty. Press ENTER, then a button on the controller that will be player $p."
      for line in "${devices[@]}"; do
        IFS='|' read -r index guid name bus player visual mapped <<< "$line"
        [[ $player == "$p" ]] || continue
        tag="P$p"
        [[ $bus == bluetooth ]] && tag+=" BT"
        tag+=" $name"
        kind=$(buttons_type_name "$([[ -n $visual ]] && buttons_visual_kind "$visual")")
        hint="${visual:+$visual: }$kind, $([[ $bus == bluetooth ]] && echo Bluetooth || echo USB)"
        break
      done
      if [[ $tag == "P$p (empty)" ]] && ((p <= 2)) && buttons_keyboard_on; then
        tag="P$p Keyboard encoder"
        hint="$(buttons_keyboard_visual): Arcade panel, MAME keys"
      fi
      entries+=("$p|$tag|$hint")
    done
    text="Pick a player and press a button on the controller that will be it."
    rc=0
    choice=$(UI_STYLE=slots ui_menu_hints "$title" "$text" "$last" "${entries[@]}") || rc=$?
    if ((rc == 124)); then
      last=$choice
      continue
    fi
    ((rc == 0)) || return 0
    last=$choice
    # "assign:VAGA:INDICE": a GUI viu um controle segurado num cartao vazio (a barra encheu).
    if [[ $choice == assign:* ]]; then
      IFS=: read -r _ last index <<< "$choice"
      screen_controller_slot "$last" "$index"
    elif [[ $choice =~ ^[0-9]+$ ]]; then
      screen_controller_slot "$choice"
    fi
  done
}

# screen_controller_slot JOGADOR [INDICE]: o Player N. Com INDICE (o controle que a tela das vagas
# viu segurado ate a barra encher), ele toma a vaga sem perguntar: se a vaga era de outro, os
# dois trocam, e a lista das vagas se refaz com o cartao dele. So se o controle ainda nao esta
# pronto (sem mapa ou sem visual) o menu dele abre, para configurar; pronto, fica na lista. Sem INDICE, uma vaga com controle abre o menu dele; uma vazia,
# no Setup em texto (sem a barra), pede para apertar um botao do controle que sera esse player. Um
# controle sem mapa nao toma a vaga sem ser configurado: oferece o tipo, o layout e o mapeamento.
screen_controller_slot() {
  local n=$1 title="Player $1" line="" index guid name bus player visual mapped got rc=0 found out
  line=$(buttons_devices | awk -F'|' -v p="$n" '$5 == p { print; exit }')
  # P1 e P2 do encoder de teclado: o menu dele, nao ha controle para apertar.
  if [[ -z $line ]] && ((n <= 2)) && buttons_keyboard_on; then
    screen_keyboard_encoder
    return 0
  fi
  if [[ ${2:-} =~ ^[0-9]+$ ]]; then
    index=$2
  elif [[ -n $line ]]; then
    screen_controller "$line"
    return 0
  elif ui_gui_alive; then
    # Na interface grafica a vaga vazia se define segurando um botao: nada a fazer aqui.
    return 0
  else
    ui_info "$title" "$(ui_c "$C_PINK" "Press a button on the controller that will be player $n")" "" \
      "Esc goes back."
    padkeys_off
    got=$(ui_capture_wait buttons_capture 600) || rc=$?
    padkeys_on
    ui_flush_input
    ((rc == 0)) || return 0
    read -r index _ <<< "$got"
  fi
  found=$(buttons_devices | awk -F'|' -v i="$index" '$1 == i { print; exit }')
  if [[ -z $found ]]; then
    ui_msg "$title" "That controller is not in the list. Try again."
    return 0
  fi
  IFS='|' read -r index guid name bus player visual mapped <<< "$found"
  if [[ $player != "$n" ]]; then
    out=$(buttons_set_player "$index" "$n") || true
    case $out in
      ok) buttons_apply || ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG." ;;
      error=unmapped)
        if ui_yesno "$title" "$name has no mapping yet, and a player needs one. Set it up now?"; then
          screen_controller_guided "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$n"
        fi
        ;;
      *)
        ui_msg "$title" "$(ui_bad "Could not change the player.")" "Details in $FLIPEROS_LOG."
        return 0
        ;;
    esac
  fi
  found=$(buttons_devices | awk -F'|' -v i="$index" -v g="$guid" '$1 == i && $2 == g { print; exit }')
  [[ -n $found ]] || return 0
  IFS='|' read -r _ _ _ _ _ visual mapped <<< "$found"
  # Segurado na barra e ja configurado (mapa e visual): a vaga so muda de cartao, sem entrar nele.
  [[ -n ${2:-} && $mapped == 1 && -n $visual ]] && return 0
  screen_controller "$found"
  return 0
}

# screen_controller LINHA: o menu de um controle (a linha do buttons_devices): o
# player, o mapa, o layout dos botoes dos jogos e o visual (o desenho do guia do
# frontend, se ele for o P1). Cada um muda sozinho, sem passar pelos outros.
screen_controller() {
  local line=$1 title choice last="" index guid name bus player visual mapped text shown kind
  local -a entries
  IFS='|' read -r index guid name bus player visual mapped <<< "$line"
  title=$name
  while true; do
    # O controle agora (o player e o visual mudam aqui dentro).
    line=$(buttons_devices | awk -F'|' -v i="$index" -v g="$guid" '$1 == i && $2 == g { print; exit }')
    if [[ -z $line ]]; then
      ui_msg "$title" "This controller is not connected any more."
      return 0
    fi
    IFS='|' read -r index guid name bus player visual mapped <<< "$line"
    shown=${player:-none}
    entries=()
    # Na ordem em que se faz: o player, o tipo (painel de arcade ou joypad), o layout
    # visual desse tipo e so depois o mapeamento.
    kind=""
    [[ -n $visual ]] && kind=$(buttons_visual_kind "$visual")
    entries+=("player|Player: $shown|Which player it is. If it is taken, they swap.")
    entries+=("type|Type: $(buttons_type_name "$kind")|Arcade panel or joypad. Set it first.")
    entries+=("visual|Visual layout: $([[ -n $visual ]] && buttons_visual_field "$visual" 1 || echo "not set")|The drawing the frontend guide uses for player 1.")
    entries+=("mapping|Mapping: $([[ $mapped == 1 ]] && echo done || echo "not mapped")|Press each control when asked, or change just one button.")
    [[ $kind == pad ]] || entries+=("layout|Buttons layout (games of 1 to 5 buttons)|Where the buttons of 1 to 5-button games go on the panel.")
    entries+=("padtest|Test controller|See every button, stick and trigger answer live.")
    text="$([[ $bus == bluetooth ]] && echo "A Bluetooth controller" || echo "A USB controller"). Each item is set on its own."
    choice=$(ui_menu_hints "$title" "$text" "$last" "${entries[@]}" "return|Return|Back to the controllers.") || return 0
    last=$choice
    case $choice in
      player) screen_controller_player "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$mapped" ;;
      type) screen_controller_type "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$mapped" ;;
      visual) screen_controller_visual "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$mapped" ;;
      mapping) screen_controller_mapping "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$mapped" ;;
      layout) screen_buttons_layout ;;
      padtest) screen_controller_test "$title" "$index" "$name" "$bus" "$visual" ;;
      return) return 0 ;;
    esac
  done
}

# screen_controller_test TITULO INDICE NOME BARRAMENTO VISUAL: o testador do controle
# (gui/padtest.py): cada botao, direcao, analogico e gatilho acende ao vivo, pelo mapa dele. Um
# joypad mostra tambem os gatilhos (a barra enche com o eixo) e os analogicos (o ponto anda); um
# painel, a alavanca e os botoes do formato dele. Sai com o Esc ou segurando o Start. A
# tela e desenhada pela interface grafica: no Setup em texto (SSH) nao ha o que mostrar.
screen_controller_test() {
  local title=$1 index=$2 name=$3 bus=$4 visual=$5 binds bg rc=0
  if ! ui_gui_alive; then
    ui_msg "$title" "The controller test is drawn by the graphical Setup, on the monitor." "" \
      "It is not available in the text Setup."
    return 0
  fi
  [[ -n $visual ]] || visual=$([[ $bus == bluetooth ]] && echo pad:playstation || echo arcade6)
  binds=$(buttons_binds "$index" 2> /dev/null) || binds=""
  if [[ -z $binds ]]; then
    ui_msg "$title" "$name is not mapped yet: the test shows its raw buttons and axes." "" \
      "Map it for the right buttons, sticks and triggers."
  fi
  bg=$(cat "$(dirname "$UI_GUI_DIR")/gui-background" 2> /dev/null)
  ui_clear
  padkeys_off
  FLIPEROS_GUI_BG=$bg FLIPEROS_GUI_ORIENTATION=$(conf_get orientation 2> /dev/null || echo horizontal) \
    ui_text python3 "$SETUP_DIR/gui/padtest.py" --index "$index" --visual "$visual" --binds "$binds" \
    --name "$name" < /dev/tty > /dev/tty 2>> "$FLIPEROS_LOG" || rc=1
  padkeys_on
  ui_palette > /dev/tty
  ui_flush_input
  ((rc == 0)) || ui_msg "$title" "$(ui_bad "The controller test could not open.")" "Details in $FLIPEROS_LOG."
}

# screen_controller_player TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL MAPA: o
# player do controle (nenhum ou de 1 a 8; o Bluetooth tambem "Automatic": o proximo
# livre pela ordem de conexao). Quem tem o player troca com ele (se o controle nao
# tinha player, o outro fica sem, com o mapa guardado). Um controle sem mapa nao
# recebe player: oferece mapear.
screen_controller_player() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 mapped=$8 choice out p
  local -a entries=("-|No player")
  for ((p = 1; p <= 8; p++)); do
    entries+=("$p|Player $p")
  done
  [[ $bus == bluetooth ]] && entries+=("auto|Automatic: the next free player")
  choice=$(ui_radio "$title" "Which player is $name? If another controller has it, the two swap (if $name has no player, the other is left with none, its mapping kept)." \
    "${player:--}" "${entries[@]}") || return 0
  [[ $choice == "${player:--}" ]] && return 0
  out=$(buttons_set_player "$index" "$choice") || true
  case $out in
    ok)
      buttons_apply || ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG."
      case $choice in
        -) ui_msg "$title" "$name has no player now. Its mapping is kept." ;;
        auto) ui_msg "$title" "$name takes the next free player when it connects." ;;
        *) ui_msg "$title" "$name is player $choice. The emulators use it from the next game." ;;
      esac
      ;;
    error=unmapped)
      if ui_yesno "$title" "$name has no mapping yet, and a player needs one. Map it now?"; then
        # Na ordem: o tipo, o layout visual e so entao o mapeamento (com o player pedido).
        screen_controller_guided "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$choice"
      fi
      ;;
    *) ui_msg "$title" "$(ui_bad "Could not change the player.")" "Details in $FLIPEROS_LOG." ;;
  esac
}

# screen_controller_guided TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL JOGADOR_NOVO: o
# controle configurado do comeco, na ordem: o tipo (painel de arcade ou joypad), o layout
# visual desse tipo e so entao o mapeamento. Cada passo comeca no que o controle ja tem (o
# Esc em qualquer um para tudo). Usado quando o mapeamento e pedido por outro caminho, como
# dar um player a um controle que ainda nao tem mapa.
screen_controller_guided() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 want=$8 kind choice
  kind=arcade
  if [[ $bus != keyboard ]]; then
    kind=$(screen_controller_pick_type "$title" "$name" "$bus" "$visual") || return 0
    [[ $kind == return ]] && return 0
  fi
  choice=$(screen_controller_pick_visual "$title" "$name" "$bus" "$visual" "$kind") || return 0
  [[ $choice == return ]] && return 0
  buttons_set_visual "$index" "$choice" > /dev/null || true
  screen_controller_map_all "$title" "$index" "$guid" "$name" "$bus" "$player" "$choice" "$want"
}

# screen_controller_mapping TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL MAPA: o
# mapa do controle (para todos os emuladores): todos os botoes, um so, ou os botoes
# da interface (aceitar e voltar dos menus).
screen_controller_mapping() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 mapped=$8 choice last=""
  local -a entries
  while true; do
    entries=("map|Map all buttons|Press each control when asked.")
    if ((mapped)); then
      entries+=("one|Change one button|Pick a control and press its new button."
        "menu|Menu buttons|The buttons that accept and go back in the menus.")
    fi
    choice=$(ui_menu_hints "$title" "$name: the mapping is used by all the emulators." "$last" "${entries[@]}" \
      "return|Return|Back to the controller.") || return 0
    last=$choice
    case $choice in
      map)
        screen_controller_map_all "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" ""
        return 0
        ;;
      one) screen_controller_one_button "$title" "$index" "$name" "$player" "$visual" ;;
      menu) screen_controller_menu_buttons "$title" "$index" "$name" "$player" "$visual" ;;
      return) return 0 ;;
    esac
  done
}

# screen_controller_pick_type TITULO NOME BARRAMENTO VISUAL: o tipo do controle, um painel
# de arcade ou um joypad (um seletor < desenho > na interface grafica); imprime arcade, pad
# ou return. Comeca no tipo do visual de agora (sem visual, o joypad num Bluetooth).
screen_controller_pick_type() {
  local title=$1 name=$2 bus=$3 visual=$4 current=arcade
  if [[ -n $visual ]]; then
    current=$(buttons_visual_kind "$visual")
  elif [[ $bus == bluetooth ]]; then
    current=pad
  fi
  UI_STYLE=type ui_menu_hints "$title" "What is $name: an arcade panel or a joypad?" "$current" \
    "arcade|Arcade panel|A stick and buttons: an arcade encoder or JAMMA." \
    "pad|Joypad|A console controller, on USB or Bluetooth." \
    "return|Return|Back to the controller."
}

# screen_controller_pick_visual TITULO NOME BARRAMENTO ATUAL [TIPO]: o menu dos visuais do
# TIPO (arcade: os formatos de painel; pad: os joypads dos videogames; sem TIPO, o do visual
# de agora); imprime o escolhido. Um teclado so tem os de painel.
screen_controller_pick_visual() {
  local title=$1 name=$2 bus=$3 current=$4 kind=${5:-} entry
  local -a entries=()
  if [[ -z $kind ]]; then
    kind=arcade
    [[ -n $current ]] && kind=$(buttons_visual_kind "$current")
  fi
  [[ $bus == keyboard ]] && kind=arcade
  for entry in "${BUTTONS_VISUALS[@]}"; do
    [[ $(buttons_visual_kind "${entry%%|*}") == "$kind" ]] && entries+=("$entry")
  done
  # O atual so se for do mesmo tipo; senao o primeiro (o painel de 6 botoes, o PlayStation).
  if [[ -z $current || $(buttons_visual_kind "$current") != "$kind" ]]; then
    current=${entries[0]%%|*}
  fi
  # UI_STYLE=visual: na interface grafica, um seletor < desenho > (esquerda e direita
  # trocam o painel ou o joypad).
  UI_STYLE=visual ui_menu_hints "$title" "$name: the frontend guide draws this when it is player 1." \
    "$current" "${entries[@]}" "return|Return|Back to the controller."
}

# screen_controller_type TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL MAPA: o tipo do
# controle, antes do layout e do mapeamento. Mudar o tipo leva direto a escolher o layout
# visual dele (um painel ou um joypad); o mesmo tipo nao muda nada.
screen_controller_type() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 mapped=$8 kind
  kind=$(screen_controller_pick_type "$title" "$name" "$bus" "$visual") || return 0
  [[ $kind == return ]] && return 0
  if [[ -n $visual && $(buttons_visual_kind "$visual") == "$kind" ]]; then
    return 0
  fi
  screen_controller_visual "$title" "$index" "$guid" "$name" "$bus" "$player" "$visual" "$mapped" "$kind"
}

# screen_controller_visual TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL MAPA [TIPO]: o
# visual do controle, entre os do tipo dele (sem tipo ainda, pergunta o tipo antes). Pode
# faltar mapear: os botoes novos de um painel maior, ou tudo (de painel para joypad);
# oferece na hora.
screen_controller_visual() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 mapped=$8 kind=${9:-} choice out
  if [[ -z $kind ]]; then
    if [[ -n $visual ]]; then
      kind=$(buttons_visual_kind "$visual")
    elif [[ $bus == keyboard ]]; then
      kind=arcade
    else
      kind=$(screen_controller_pick_type "$title" "$name" "$bus" "") || return 0
      [[ $kind == return ]] && return 0
    fi
  fi
  choice=$(screen_controller_pick_visual "$title" "$name" "$bus" "$visual" "$kind") || return 0
  [[ $choice == return || $choice == "$visual" ]] && return 0
  out=$(buttons_set_visual "$index" "$choice") || true
  case $out in
    error=*)
      ui_msg "$title" "$(ui_bad "Could not change the visual layout.")" "Details in $FLIPEROS_LOG."
      return 0
      ;;
  esac
  buttons_apply || true
  case $out in
    none) ui_msg "$title" "Saved. The frontend guide draws $(buttons_visual_field "$choice" 1) when $name is player 1." ;;
    all)
      if ((mapped)); then
        ui_yesno "$title" "$(buttons_visual_field "$choice" 1) needs its own mapping. Map $name now?" &&
          screen_controller_map_all "$title" "$index" "$guid" "$name" "$bus" "$player" "$choice" ""
      else
        ui_msg "$title" "Saved. $name has no mapping yet: use Mapping when you are ready."
      fi
      ;;
    buttons*)
      if ui_yesno "$title" "$(buttons_visual_field "$choice" 1) has buttons the mapping does not: ${out#buttons }. Map them now?"; then
        screen_controller_map_missing "$title" "$index" "$name" "$player" "$choice" ${out#buttons }
      fi
      ;;
  esac
}

# screen_keyboard_encoder: o encoder de teclado (I-PAC e afins), que manda as teclas
# padrao do MAME de dois jogadores. Ligado, ele e o P1 e o P2 em todos os emuladores,
# sem mapear nada (quem era P1 ou P2 passa para o proximo player livre); desligado,
# saem so os dois jogadores de teclado. Com ele ligado, tambem escolhe o visual e a
# posicao dos botoes dos jogos (o visual do P1 e o do guia do frontend).
screen_keyboard_encoder() {
  local title="Keyboard encoder" choice last="" on visual out
  local -a entries
  while true; do
    entries=()
    if buttons_keyboard_on; then
      on=1
      visual=$(buttons_keyboard_visual)
      entries+=("toggle|MAME keyboard encoder: on|On: P1 and P2 use the MAME keys in all emulators.")
      entries+=("layout|Buttons layout (games of 1 to 5 buttons)|Where the buttons of 1 to 5-button games go on the panel.")
      entries+=("visual|Visual layout: $(buttons_visual_field "${visual:-arcade6}" 1)|The drawing the frontend guide uses for player 1.")
    else
      on=0
      entries+=("toggle|MAME keyboard encoder: off|Turn it on if the encoder sends the MAME keys.")
    fi
    choice=$(ui_menu_hints "$title" "An arcade encoder that acts as a USB keyboard and sends the MAME keys of two players (player 1: arrows, Ctrl, Alt, Space, Shift, Z, X, 1 start, 5 coin). On, nothing needs mapping." \
      "$last" "${entries[@]}" "return|Return|Back to the controllers.") || return 0
    last=$choice
    case $choice in
      toggle)
        if ((on)); then
          out=$(buttons_set_keyboard mame off "Keyboard encoder") || true
          [[ $out == ok ]] || { ui_msg "$title" "$(ui_bad "Could not turn the encoder off.")" "Details in $FLIPEROS_LOG."; continue; }
          buttons_apply || true
          ui_msg "$title" "The encoder is off: players 1 and 2 are free."
        else
          out=$(buttons_set_keyboard mame on "Keyboard encoder") || true
          [[ $out == ok ]] || { ui_msg "$title" "$(ui_bad "Could not turn the encoder on.")" "Details in $FLIPEROS_LOG."; continue; }
          buttons_apply || ui_msg "$title" "$(ui_bad "Could not save the keys.")" "Details in $FLIPEROS_LOG."
          ui_msg "$title" "The encoder is on: players 1 and 2 use the MAME keys in all the emulators." "" \
            "A controller that was player 1 or 2 moved to the next free player."
        fi
        ;;
      layout) screen_buttons_layout ;;
      visual)
        choice=$(screen_controller_pick_visual "$title" "The keyboard encoder" keyboard "$visual") || continue
        [[ $choice == return || $choice == "$visual" ]] && continue
        out=$(buttons_set_visual -1 "$choice") || true
        if [[ $out == error=* ]]; then
          ui_msg "$title" "$(ui_bad "Could not change the visual layout.")" "Details in $FLIPEROS_LOG."
        else
          buttons_apply || true
          ui_msg "$title" "Saved. The frontend guide draws $(buttons_visual_field "$choice" 1) when the encoder is player 1."
        fi
        ;;
      return) return 0 ;;
    esac
  done
}

# screen_controller_map_all TITULO INDICE GUID NOME BARRAMENTO JOGADOR VISUAL JOGADOR_NOVO:
# o mapa de todos os botoes do visual do controle (o painel com os botoes dele ou o
# mapeador de joypad do Batocera), os botoes da interface, e grava. O player e o que
# ele tem (ou JOGADOR_NOVO, o que a pessoa acabou de pedir); sem player o mapa fica
# guardado e oferece dar o proximo livre. Um controle sem visual escolhe um antes.
screen_controller_map_all() {
  local title=$1 index=$2 guid=$3 name=$4 bus=$5 player=$6 visual=$7 want=$8
  local kind nbuttons=6 map shown target out next
  if [[ -z $visual ]]; then
    # Sem tipo ainda: o tipo (painel ou joypad), depois o layout dele, e so entao o mapeamento.
    kind=arcade
    if [[ $bus != keyboard ]]; then
      kind=$(screen_controller_pick_type "$title" "$name" "$bus" "") || return 0
      [[ $kind == return ]] && return 0
    fi
    visual=$(screen_controller_pick_visual "$title" "$name" "$bus" "" "$kind") || return 0
    [[ $visual == return ]] && return 0
    buttons_set_visual "$index" "$visual" > /dev/null || true
  fi
  kind=$(buttons_visual_kind "$visual")
  [[ $kind == arcade ]] && nbuttons=$(buttons_visual_count "$visual")
  if [[ $bus == bluetooth ]]; then
    target=bt
  else
    target=${want:-${player:--}}
    [[ $target == auto ]] && target=${player:--}
  fi
  shown=${want:-${player:-$(buttons_next_player)}}
  [[ $shown =~ ^[0-9]+$ ]] || shown=$(buttons_next_player)
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
    if buttons_store "$map" "$target" "$index" "$guid" && { buttons_apply || [[ ! -s $BUTTONS_MAP ]]; }; then
      case $target in
        bt) ui_msg "$title" "Saved. It takes the next free player when it connects (now player $shown)." ;;
        -)
          next=$(buttons_next_player)
          if ui_yesno "$title" "Saved without a player. Make $name player $next?"; then
            out=$(buttons_set_player "$index" "$next") || true
            [[ $out == ok ]] && buttons_apply
          fi
          ;;
        *) ui_msg "$title" "Saved as player $target. The emulators use it from the next game." ;;
      esac
    else
      ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG."
    fi
  fi
  rm -f "$map"
}

# screen_controller_capture_one TITULO JOGADOR INDICE NOME TIPO BOTOES COMANDO: pede um
# comando so (o painel ou o joypad desenhado) e poe o elemento apertado em
# CONTROLLER_ELEMENT. Status 1: nada apertado (pulado); 3: o Esc.
screen_controller_capture_one() {
  local title=$1 p=$2 index=$3 name=$4 kind=$5 nbuttons=$6 control=$7 got rc=0 label
  CONTROLLER_ELEMENT=""
  padkeys_off
  rm -f "$BUTTONS_CANCEL"
  if [[ $kind == pad ]]; then
    label=$(buttons_pad_label "$control" generic)
    ui_pad_capture "$title" "$p" "$control" 1 generic "$name" ||
      ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press $label")" "" "Hold any button to skip it, Esc cancels."
    got=$(ui_capture_wait buttons_capture "$PAD_TIMEOUT" "$PAD_HOLD" "$index") || rc=$?
  else
    ui_capture "$title" "$p" "$control" 1 1 8 "$nbuttons" ||
      ui_info "$title" "$(ui_c "$C_PINK" "Player $p: press ${BUTTON_LABELS[$control]:-$control}")" "" \
        "Wait 8 seconds to skip it, Esc cancels."
    got=$(ui_capture_wait buttons_capture 8 "" "$index") || rc=$?
  fi
  padkeys_on
  rm -f "$BUTTONS_CANCEL"
  ui_flush_input
  ((rc == 0)) || return "$rc"
  read -r _ CONTROLLER_ELEMENT _ <<< "$got"
}

# screen_controller_set_button TITULO INDICE COMANDO: o botao que acabou de ser
# apertado (CONTROLLER_ELEMENT) no COMANDO do controle; avisa se ja e de outro.
screen_controller_set_button() {
  local title=$1 index=$2 control=$3 out label
  out=$(buttons_set_button "$index" "$control" "$CONTROLLER_ELEMENT") || true
  case $out in
    ok) buttons_apply || ui_msg "$title" "$(ui_bad "Could not save the mapping.")" "Details in $FLIPEROS_LOG." ;;
    error=used:*)
      label=${BUTTON_LABELS[${out#error=used:}]:-${out#error=used:}}
      ui_msg "$title" "That button is already $label." "Press another one."
      ;;
    *) ui_msg "$title" "$(ui_bad "Could not change the button.")" "Details in $FLIPEROS_LOG." ;;
  esac
}

# screen_controller_one_button TITULO INDICE NOME JOGADOR VISUAL: a lista dos comandos
# do controle com o botao de cada um; o escolhido espera o novo botao.
screen_controller_one_button() {
  local title=$1 index=$2 name=$3 player=$4 visual=$5 kind n control element choice last="" rc shown
  local -A current
  local -a entries controls
  kind=$(buttons_visual_kind "$visual")
  n=$(buttons_visual_count "$visual")
  shown=${player:-$(buttons_next_player)}
  while true; do
    current=()
    while read -r control element; do
      current[$control]=$element
    done < <(buttons_binds "$index")
    if [[ $kind == pad ]]; then
      controls=("${PAD_CONTROLS[@]}")
    else
      read -r -a controls <<< "$(buttons_arcade_controls "$n")"
    fi
    entries=()
    for control in "${controls[@]}"; do
      if [[ $kind == pad ]]; then
        entries+=("$control|${PAD_LABELS[$control]:-$control}: ${current[$control]:-none}")
      else
        entries+=("$control|${BUTTON_LABELS[$control]:-$control}: ${current[$control]:-none}")
      fi
    done
    choice=$(ui_menu "$title" "Pick the control to change, then press its new button." "$last" "${entries[@]}" \
      "return|Return") || return 0
    [[ $choice == return ]] && return 0
    last=$choice
    rc=0
    screen_controller_capture_one "$title" "$shown" "$index" "$name" "$kind" "$n" "$choice" || rc=$?
    case $rc in
      0) screen_controller_set_button "$title" "$index" "$choice" ;;
      3) ui_msg "$title" "Cancelled: nothing was changed." ;;
      *) ui_msg "$title" "Nothing was pressed: nothing was changed." ;;
    esac
  done
}

# screen_controller_map_missing TITULO INDICE NOME JOGADOR VISUAL COMANDO...: so os
# comandos que faltam (os botoes novos de um painel maior), um por vez.
screen_controller_map_missing() {
  local title=$1 index=$2 name=$3 player=$4 visual=$5 control rc shown n
  shift 5
  n=$(buttons_visual_count "$visual")
  shown=${player:-$(buttons_next_player)}
  for control in "$@"; do
    rc=0
    screen_controller_capture_one "$title" "$shown" "$index" "$name" arcade "$n" "$control" || rc=$?
    case $rc in
      0) screen_controller_set_button "$title" "$index" "$control" ;;
      3) ui_msg "$title" "Cancelled: the rest was not mapped."; return 0 ;;
    esac
  done
}

# screen_controller_menu_buttons TITULO INDICE NOME JOGADOR VISUAL: o botao de aceitar e o
# de voltar dos menus (screen_buttons_interface), sem refazer o resto do mapa.
screen_controller_menu_buttons() {
  local title=$1 index=$2 name=$3 player=$4 visual=$5 kind shown map control element which changed=0
  kind=$(buttons_visual_kind "$visual")
  shown=${player:-$(buttons_next_player)}
  map=$(mktemp)
  while read -r control element; do
    printf '%s %s %s %s %s\n' "$shown" "$control" "$index" "$element" "$name" >> "$map"
  done < <(buttons_binds "$index")
  BUTTONS_CANCELLED=0
  rm -f "$BUTTONS_CANCEL"
  padkeys_off
  screen_buttons_interface "$title" "$shown" "$map" "$index" "$name" "$kind"
  padkeys_on
  rm -f "$BUTTONS_CANCEL"
  ui_flush_input
  if ((BUTTONS_CANCELLED)); then
    ui_msg "$title" "Cancelled: nothing was changed."
    rm -f "$map"
    return 0
  fi
  # So o que foi apertado vira linha accept ou cancel no fim do mapa de trabalho.
  for which in accept cancel; do
    element=$(awk -v w="$which" '$2 == w { e = $4 } END { print e }' "$map")
    [[ -n $element ]] || continue
    CONTROLLER_ELEMENT=$element
    screen_controller_set_button "$title" "$index" "$which" && changed=1
  done
  rm -f "$map"
  ((changed)) && ui_msg "$title" "Saved. The menus use these buttons from now on."
  return 0
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

# screen_buttons_layout: de cada numero de botoes (1 a 5), onde ficam no
# painel os botoes do jogo (lib/buttons.sh). O painel e o do Button mapping:
# sem ele nao ha o que arrumar.
screen_buttons_layout() {
  local title="Buttons layout" count choice last="" entries=()
  local -a order
  if [[ ! -s $BUTTONS_MAP ]]; then
    ui_msg "$title" "The panel is not mapped yet." "" \
      "Map a controller first (Controllers / Arcade panel): the layout moves the buttons mapped there."
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
      "Where the buttons of a game go on the panel, by how many buttons the game uses." \
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
# (screen_calibrate_guns). O controle como teclado (padkeys) fica desligado
# enquanto ele roda: girar o volante virava seta (ESC [ D), o calibrador lia o
# ESC como cancelar e saia sozinho (gabinete de um usuario, 2026-11-16).
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
  ui_yesno "$title" "Move every axis to its limits (wheel lock to lock, each pedal all the way), then release the pedals. Hold any button of the controller to go on. Then a test of the buttons and of the force feedback." \
    || return 0
  ui_clear
  # Na interface grafica, a tela do calibrador e a dela (gui/wheelscreen.py),
  # em pe se o monitor esta, com o fundo animado que o menu sorteou.
  local gui=0 bg=""
  if ui_gui_alive; then
    gui=1
    bg=$(cat "$(dirname "$UI_GUI_DIR")/gui-background" 2> /dev/null)
  fi
  padkeys_off
  local rc=0
  FLIPEROS_CALIBRATE_GUI=$gui FLIPEROS_GUI_DIR=$SETUP_DIR/gui FLIPEROS_GUI_BG=$bg \
    FLIPEROS_GUI_ORIENTATION=$(conf_get orientation 2> /dev/null || echo horizontal) \
    ui_text "$CALIBRATE" axes "$dev" < /dev/tty > /dev/tty 2>&1 || rc=1
  padkeys_on
  ui_palette > /dev/tty
  ui_flush_input
  if ((rc == 0)); then
    log_info "calibracao axes salva: $dev"
    ui_msg "$title" "Calibration saved. It is applied again every time the controller is connected."
  else
    ui_msg "$title" "Nothing was saved."
  fi
  ui_flush_input
}
