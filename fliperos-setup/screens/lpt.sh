# shellcheck shell=bash
# Setup > LPT joysticks: joysticks e pads ligados na porta paralela por um
# adaptador (lib/lpt.sh). A pessoa diz qual adaptador e o que esta ligado;
# o driver carrega na hora e em todo boot.

screen_lpt() {
  local choice last=gamecon ports=() text
  while true; do
    mapfile -t ports < <(lpt_ports)
    text="Now: $(lpt_describe)."
    if ((${#ports[@]} == 0)); then
      text="$text No parallel port was found: enable it in the BIOS (Super I/O > Parallel Port) or install a PCI/PCIe parallel card."
    fi
    choice=$(ui_menu "LPT joysticks" "$text" "$last" \
      "gamecon|Gamepad adapter (NES, SNES, N64, PlayStation)" \
      "db9|DB9 adapter (Atari, Amiga, Sega)" \
      "turbografx|TurboGraFX interface (up to 7 joysticks)" \
      "found|Joysticks found now" \
      "off|Turn off" \
      "return|Return") || return 0
    last=$choice
    case $choice in
      gamecon | db9 | turbografx) screen_lpt_setup "$choice" "${ports[@]}" ;;
      found) screen_lpt_found ;;
      off)
        lpt_disable
        lpt_reload
        ui_msg "LPT joysticks" "Parallel port joysticks are off."
        ;;
      return) return 0 ;;
    esac
  done
}

# screen_lpt_port PORTA... imprime o numero da porta escolhida. Sem porta
# nenhuma, a configuracao pode ser gravada assim mesmo (parport0): vale
# quando a porta aparecer.
screen_lpt_port() {
  if (($# == 0)); then
    ui_yesno "LPT joysticks" "No parallel port was found. Save the setting anyway? It is used when the port appears (BIOS or PCI card)." no ||
      return 1
    echo 0
  elif (($# == 1)); then
    echo "${1%%|*}"
  else
    ui_menu "LPT joysticks" "Which parallel port?" "" "$@"
  fi
}

screen_lpt_setup() {
  local driver=$1 port values=() types=() cur=() choice i
  shift
  port=$(screen_lpt_port "$@") || return 0
  mapfile -t types < <(lpt_types "$driver")
  read -ra cur <<< "$(lpt_current)"
  case $driver in
    db9)
      choice=$(ui_menu "DB9 adapter" "What is connected? DB9 adapters need the port in EPP or ECP mode in the BIOS." \
        "${cur[2]:-}" "${types[@]}") || return 0
      values=("$choice")
      ;;
    gamecon)
      values=(0 0 0 0 0)
      if [[ ${cur[0]:-} == gamecon ]]; then
        for i in 0 1 2 3 4; do values[i]=${cur[i + 2]:-0}; done
      fi
      screen_lpt_pads values "${types[@]}" || return 0
      ;;
    turbografx)
      local count buttons
      count=$(ui_menu "TurboGraFX interface" "How many joysticks are connected?" 2 \
        "1|1" "2|2" "3|3" "4|4" "5|5" "6|6" "7|7") || return 0
      buttons=$(ui_menu "TurboGraFX interface" "How many buttons on each joystick?" 1 "${types[@]}") || return 0
      for ((i = 0; i < count; i++)); do values+=("$buttons"); done
      ;;
  esac
  # Os zeros do fim nao dizem nada ao driver.
  while ((${#values[@]} > 1)) && [[ ${values[-1]} == 0 ]]; do unset 'values[-1]'; done
  if ! lpt_set "$driver" "$port" "${values[@]}"; then
    ui_msg "LPT joysticks" "Choose at least one joystick or pad."
    return 0
  fi
  ui_info "LPT joysticks" "Loading the $driver driver..."
  lpt_reload
  sleep 1
  screen_lpt_found
}

# screen_lpt_pads VARIAVEL TIPO... edita os 5 pads do gamecon (cada um num
# pino de dados da porta) e devolve 1 se a pessoa cancelar.
screen_lpt_pads() {
  local -n pads=$1
  shift
  local pins=(10 11 12 13 15) entries=() slot="" choice i
  while true; do
    entries=()
    for i in 0 1 2 3 4; do
      entries+=("$i|Pad $((i + 1)) (pin ${pins[i]}): $(lpt_type_label gamecon "${pads[i]}")")
    done
    entries+=("save|Save" "cancel|Cancel")
    slot=$(ui_menu "Gamepad adapter" "Choose what is connected to each pad input of the adapter." \
      "$slot" "${entries[@]}") || return 1
    case $slot in
      save) return 0 ;;
      cancel) return 1 ;;
      *)
        choice=$(ui_menu "Pad $((slot + 1))" "" "${pads[slot]}" "$@") && pads[slot]=$choice
        ;;
    esac
  done
}

screen_lpt_found() {
  local found=() errors=()
  mapfile -t found < <(lpt_devices)
  if ((${#found[@]})); then
    ui_msg "LPT joysticks" "Joysticks on the parallel port:" "${found[@]}" "" \
      "They also move this menu (button 1 = Enter, button 2 = back)."
    return 0
  fi
  mapfile -t errors < <(dmesg 2> /dev/null | grep -E 'gamecon|db9|turbografx|parport' | tail -n 4 | cut -c1-70)
  ui_msg "LPT joysticks" "No joystick was created on the parallel port." "Setting: $(lpt_describe)" "" "${errors[@]}"
}
