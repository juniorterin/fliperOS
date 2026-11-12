# shellcheck shell=bash
# Setup > Joysticks > Bluetooth: o gerenciador dos controles Bluetooth
# (lib/bluetooth.sh). Sem o BlueZ (as imagens antes dele), oferece
# instalar; sem adaptador, diz o que falta.

screen_bluetooth() {
  local title="Bluetooth" status choice last="" powered paired
  status=$(bluetooth_status)
  if [[ $(bluetooth_field installed "$status") != yes ]]; then
    ui_yesno "$title" "The Bluetooth programs (BlueZ) are not installed. Install them now? It needs the network." ||
      return 0
    run_online "Installing Bluetooth" "" update_install_package bluez || return 0
    status=$(bluetooth_status)
    [[ $(bluetooth_field installed "$status") == yes ]] || return 0
  fi
  if [[ -z $(bluetooth_field adapter "$status") ]]; then
    bluetooth_do power on
    status=$(bluetooth_status)
  fi
  if [[ -z $(bluetooth_field adapter "$status") ]]; then
    ui_msg "$title" "No Bluetooth adapter was found." "" \
      "Plug in a USB Bluetooth adapter, or turn Bluetooth on in the BIOS, and try again."
    return 0
  fi
  while true; do
    powered=on
    [[ $(bluetooth_field powered "$status") == yes ]] || powered=off
    paired=$(bluetooth_field paired "$status")
    choice=$(ui_menu_hints "$title" "$(bluetooth_summary "$status")" "$last" \
      "pair|Pair a controller|Put it in pairing mode, then choose it in the list." \
      "pairall|Pair controllers automatically|Pairs every controller that is in pairing mode, one by one." \
      "devices|Paired devices (${paired:-0})|Connect, disconnect or forget a paired device." \
      "power|Bluetooth: $powered|Turn the Bluetooth adapter off or on." \
      "return|Return|Back to Joysticks.") || return 0
    last=$choice
    case $choice in
      pair) screen_bluetooth_pair ;;
      pairall) screen_bluetooth_auto ;;
      devices) screen_bluetooth_devices ;;
      power)
        if [[ $powered == on ]]; then bluetooth_do power off; else bluetooth_do power on; fi
        ;;
      return) return 0 ;;
    esac
    status=$(bluetooth_status)
  done
}

# Como por os controles mais comuns em modo de pareamento.
BLUETOOTH_HOWTO="Xbox: hold the pair button on top. PlayStation: hold Share (or Create) and PS. Switch Pro: hold the sync button. 8BitDo: hold the pair button (or Start with the mode switch set)."

# screen_bluetooth_pair: procura, mostra os achados (controles primeiro) e
# pareia o escolhido. Pareado, oferece o Button mapping do controle.
screen_bluetooth_pair() {
  local title="Pair a controller" line choice result mac
  local -a found entries
  ui_yesno "$title" "Put the controller in pairing mode (its light blinks fast), then choose Yes."$'\n\n'"$BLUETOOTH_HOWTO" ||
    return 0
  ui_info "$title" "Looking for Bluetooth devices for $BLUETOOTH_SCAN seconds..." "" "Keep the controller in pairing mode."
  mapfile -t found < <(bluetooth_scan "$BLUETOOTH_SCAN")
  entries=()
  for line in "${found[@]}"; do
    [[ $line == *"|"* ]] || continue
    IFS='|' read -r mac _ _ paired _ <<< "$line"
    [[ $paired == yes ]] && continue
    entries+=("$mac|$(bluetooth_label "$line")")
  done
  if ((${#entries[@]} == 0)); then
    ui_msg "$title" "No new Bluetooth device was found." "" "Put the controller in pairing mode and try again. $BLUETOOTH_HOWTO"
    return 0
  fi
  # UI_STYLE=list: os aparelhos numa lista de texto (nomes compridos, sem icone).
  choice=$(UI_STYLE=list ui_menu "$title" "Found $((${#entries[@]})) device(s). Which one?" "" \
    "${entries[@]}" "return|Return") || return 0
  [[ $choice == return ]] && return 0
  ui_info "$title" "Pairing $(screen_bluetooth_name "$choice" "${found[@]}")..." "" "Keep the controller in pairing mode."
  if result=$(bluetooth_pair "$choice"); then
    log_info "bluetooth: pareado $choice ($result)"
    screen_bluetooth_map "$title" "Paired: $(screen_bluetooth_name "$choice" "${found[@]}") ($result)."
  else
    ui_msg "$title" "$(ui_bad "Could not pair it.")" "${result:-}" "" "Put it in pairing mode again and try once more."
  fi
}

# screen_bluetooth_name MAC LINHA...: o nome do aparelho MAC nas linhas.
screen_bluetooth_name() {
  local mac=$1 line
  shift
  for line in "$@"; do
    [[ ${line%%|*} == "$mac" ]] && { line=${line#*|}; printf '%s\n' "${line%%|*}"; return 0; }
  done
  printf '%s\n' "$mac"
}

# screen_bluetooth_map TITULO TEXTO: diz o resultado e oferece mapear os
# botoes do controle agora (Button mapping).
screen_bluetooth_map() {
  if ui_yesno "$1" "$2 It reconnects by itself when its button is pressed."$'\n\n'"Map its buttons now (Button mapping)? A joypad that FliperOS knows takes one press."; then
    screen_buttons
  fi
}

# screen_bluetooth_auto: o "pair Bluetooth pads automatically" do Batocera.
screen_bluetooth_auto() {
  local title="Pair controllers automatically" line names=""
  local -a done
  ui_yesno "$title" "For $BLUETOOTH_AUTOPAIR seconds, every controller in pairing mode is paired. Put your controllers in pairing mode, then choose Yes."$'\n\n'"$BLUETOOTH_HOWTO" ||
    return 0
  ui_info "$title" "Pairing every controller in pairing mode for $BLUETOOTH_AUTOPAIR seconds..." "" \
    "Put the next controller in pairing mode at any time."
  mapfile -t done < <(bluetooth_autopair "$BLUETOOTH_AUTOPAIR")
  for line in "${done[@]}"; do
    [[ $line == *"|"* ]] && names+="${line#*|}, "
  done
  if [[ -z $names ]]; then
    ui_msg "$title" "No controller in pairing mode was found." "" "$BLUETOOTH_HOWTO"
    return 0
  fi
  log_info "bluetooth: pareados automaticamente: ${names%, }"
  screen_bluetooth_map "$title" "Paired: ${names%, }."
}

# screen_bluetooth_devices: os pareados; cada um conecta, desconecta ou e
# esquecido.
screen_bluetooth_devices() {
  local title="Paired devices" line choice action connected name
  local -a found entries
  while true; do
    mapfile -t found < <(bluetooth_devices)
    entries=()
    for line in "${found[@]}"; do
      [[ $line == *"|"* ]] && entries+=("${line%%|*}|$(bluetooth_label "$line")")
    done
    if ((${#entries[@]} == 0)); then
      ui_msg "$title" "No device is paired." "" "Pair one in Bluetooth > Pair a controller."
      return 0
    fi
    choice=$(UI_STYLE=list ui_menu "$title" "Choose a device." "" "${entries[@]}" \
      "forgetall|Forget all devices" "return|Return") || return 0
    case $choice in
      return) return 0 ;;
      forgetall)
        ui_yesno "$title" "Forget all ${#entries[@]} paired devices? Each one has to be paired again." no || continue
        for line in "${found[@]}"; do
          bluetooth_do remove "${line%%|*}"
        done
        log_info "bluetooth: todos os aparelhos esquecidos"
        continue
        ;;
    esac
    line=""
    for line in "${found[@]}"; do
      [[ ${line%%|*} == "$choice" ]] && break
    done
    IFS='|' read -r _ name _ _ connected <<< "$line"
    if [[ $connected == yes ]]; then
      action=$(ui_menu_hints "$name" "Connected." disconnect \
        "disconnect|Disconnect|It reconnects when its button is pressed." \
        "remove|Forget|Unpair it: it has to be paired again." \
        "return|Return|Back to Paired devices.") || continue
    else
      action=$(ui_menu_hints "$name" "Paired, not connected. Press its button to reconnect it, or:" connect \
        "connect|Connect|Turn the controller on first." \
        "remove|Forget|Unpair it: it has to be paired again." \
        "return|Return|Back to Paired devices.") || continue
    fi
    case $action in
      connect | disconnect)
        bluetooth_do "$action" "$choice" ||
          ui_msg "$name" "$(ui_bad "It did not $action.")" "" "Is the controller on and near the computer?"
        ;;
      remove)
        ui_yesno "$name" "Forget $name? It has to be paired again." no || continue
        bluetooth_do remove "$choice"
        log_info "bluetooth: esquecido $choice ($name)"
        ;;
    esac
  done
}
