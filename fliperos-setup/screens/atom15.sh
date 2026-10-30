# shellcheck shell=bash
# Video Setup > Card firmware: o ATOM-15 na BIOS da placa AMD (lib/atom15.sh).

# screen_atom15_blocked: o que impede de mexer na BIOS aqui. Imprime o motivo.
screen_atom15_blocked() {
  if ! is_installed || is_live; then
    echo "This needs the installed system, not the install media."
  elif ((SETUP_REMOTE == 1)) || [[ -n ${DISPLAY:-} ]]; then
    echo "Do this at the cabinet, from the FliperOS menu (not over SSH or inside the desktop): you have to watch the screen at the next boot."
  elif atom15_secure_boot; then
    echo "Secure Boot is on, and the flash tool does not work with it. Turn it off in the computer's setup first."
  elif [[ -n $(amd_driver_trial) ]]; then
    echo "A video driver change is still waiting for confirmation. Finish that first."
  elif [[ ! -x $ATOM15_BIN ]]; then
    echo "The patch tool is not installed on this system (a FliperOS update brings it)."
  else
    return 1
  fi
  return 0
}

# screen_atom15_warning: os avisos, e quem assume o risco e a pessoa. O padrao de
# cada pergunta e nao.
screen_atom15_warning() {
  local title="Card firmware: RISK"
  ui_msg "$title" "$(ui_bad "This rewrites the BIOS chip of your video card.")" "" \
    "A bad result can leave the card DEAD: no picture at all, not even at power on. FliperOS cannot repair that." "" \
    "Fixing it then takes a second video card (usually not the one on the motherboard) or a chip programmer."
  ui_msg "$title" "What it gives you: a picture on the CRT from the moment the computer powers on, instead of out-of-range signals until the system starts." "" \
    "What it does not change: games and menus. Those already run at 15 kHz without this." "" \
    "ATOM-15 is an experimental community tool, not made by AMD or the card's maker. The warranty is gone, if there was any."
  if [[ -d /sys/firmware/efi ]]; then
    ui_msg "$title" "$(ui_bad "This computer boots in UEFI mode.")" "" \
      "ATOM-15 is not guaranteed there. The computer's setup screen can stay black, and a patched BIOS loses the signature of its EFI part: a bricked R9 380 has been reported that way."
  fi
  ui_yesno "$title" "You take this risk yourself: nobody is responsible for a damaged card but you. Do you accept it?" no
}

# screen_atom15_ranges: as faixas do patch, pela frequencia do monitor. Imprime
# 15, 25, 31 ou 15,31.
screen_atom15_ranges() {
  local current
  case $(conf_get frequency 2> /dev/null) in
    25*) current=25 ;;
    31*) current=31 ;;
    *) current=15 ;;
  esac
  ui_radio "Card firmware" "Frequencies your monitor accepts. A wrong choice can harm the monitor at each power on." "$current" \
    "15|15 kHz only" \
    "25|25 kHz only" \
    "31|31 kHz only" \
    "15,31|15 and 31 kHz (multisync)"
}

# screen_atom15_apply: backup, patch, gravacao e o reboot do teste.
screen_atom15_apply() {
  local title="Card firmware" card adapter romsize test backup ranges size
  if atom15_trial_active; then
    ui_msg "$title" "A firmware test is still open: restore the original BIOS first."
    return 0
  fi
  screen_atom15_warning || return 0
  card=$(atom15_card) || {
    ui_msg "$title" "No AMD video card was found as the main card."
    return 0
  }
  if ! atom15_flasher > /dev/null; then
    ui_msg "$title" "The flash tool is missing. It is AMD's and FliperOS may not ship it." "" \
      "Get amdvbflash for Linux (64 bit) yourself, for example from the TechPowerUp forums, and put the file here:" \
      "$(atom15_where "$ATOM15_DIR/amdvbflash")" "" "It is a closed program that runs as root: use a copy you trust."
    install -d "$ATOM15_DIR" 2>> "$FLIPEROS_LOG" && chown "$FLIPEROS_USER:" "$ATOM15_DIR" 2> /dev/null
    return 0
  fi
  ui_info "$title" "Asking the flash tool about the card..."
  read -r adapter romsize test <<< "$(atom15_adapter "$card")"
  if [[ -z $adapter ]]; then
    ui_msg "$title" "The flash tool does not list this card, or did not run. Nothing was changed." "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  if [[ $test != pass && $test != - ]]; then
    ui_msg "$title" "The flash tool reports a problem with the card's BIOS chip ($test). Nothing was changed."
    return 0
  fi

  ui_info "$title" "Reading the card's BIOS (twice, to compare)..."
  if ! atom15_backup "$card" "$adapter"; then
    ui_msg "$title" "Nothing was changed." "" "$ATOM15_ERROR" "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  backup=$ATOM15_RESULT
  ui_msg "$title" "$(ui_yes "Backup of the original BIOS saved:")" "$(atom15_where "$backup")" "" \
    "Copy it off this computer (USB stick, network): if the card dies, this machine may not show a picture to reach it."

  ranges=$(screen_atom15_ranges) || return 0
  if ! atom15_prepare "$ranges"; then
    ui_msg "$title" "This BIOS cannot be patched. The card was not changed." "" "$ATOM15_ERROR"
    return 0
  fi
  size=$(stat -c %s "$ATOM15_STATE/patched.rom" 2> /dev/null) || size=0
  if [[ ${romsize:-0} -gt 0 && $size -gt $romsize ]]; then
    ui_msg "$title" "The patched BIOS ($size bytes) is larger than the card's chip ($romsize bytes). The card was not changed."
    return 0
  fi

  ui_msg "$title" "The test after flashing:" "" \
    "1. The computer restarts. WATCH THE SCREEN from the first second: the startup screens must be stable on the tube." \
    "2. Then a question asks if it worked. Answer in $ATOM15_SECONDS seconds." \
    "3. With no answer, or with No, FliperOS flashes the original BIOS back and restarts."
  ui_yesno "$title" "Last question. Flash the patched BIOS now? Do not turn the computer off while it runs." no || {
    ui_msg "$title" "Nothing was flashed. The files stay in $ATOM15_DIR."
    return 0
  }

  ui_info "$title" "Flashing. DO NOT TURN THE COMPUTER OFF..."
  speak "Flashing. Do not turn the computer off."
  if ! atom15_flash_trial "$card" "$adapter"; then
    if atom15_trial_active; then
      ui_msg "$title" "$(ui_bad "The flash failed and the original could not be confirmed either.")" "" \
        "DO NOT turn the computer off yet. The backup is here:" "$(atom15_where "$backup")" "" "Details in $FLIPEROS_LOG."
    else
      ui_msg "$title" "The flash did not check out, and the original BIOS was written back and checked." "" "Details in $FLIPEROS_LOG."
    fi
    return 0
  fi
  ui_msg "$title" "$(ui_yes "Flashed and checked.")" "" "Press OK to restart now, and watch the screen."
  screen_power_now reboot
}

# screen_atom15_restore: a BIOS original de volta, a pedido.
screen_atom15_restore() {
  local title="Card firmware" backup
  if [[ ! -s $ATOM15_STATE/original.rom ]]; then
    ui_msg "$title" "There is no copy of an original BIOS on this system."
    return 0
  fi
  backup=$(conf_get atom15_backup 2> /dev/null) || backup=$ATOM15_STATE/original.rom
  ui_yesno "$title" "Flash the original BIOS back to the card? From:"$'\n'"$(atom15_where "$backup")" no || return 0
  ui_info "$title" "Flashing the original BIOS. DO NOT TURN THE COMPUTER OFF..."
  if atom15_revert; then
    ui_msg "$title" "$(ui_yes "The original BIOS is back on the card.")" "" "Press OK to restart."
    screen_power_now reboot
  else
    ui_msg "$title" "$(ui_bad "Could not flash the original BIOS.")" "" "Do not turn the computer off yet." "The backup is here:" "$(atom15_where "$backup")" "" "Details in $FLIPEROS_LOG."
  fi
}

# screen_atom15: o menu. Sem nada que impeca, aplicar e voltar; onde ficam os
# arquivos aparece sempre.
screen_atom15() {
  local title="Card firmware" why card status backup choice last="" entries
  if why=$(screen_atom15_blocked); then
    ui_msg "$title" "$why"
    return 0
  fi
  if ! card=$(atom15_card); then
    ui_msg "$title" "ATOM-15 is for AMD/ATI video cards, and the main card here is another one."
    return 0
  fi
  while true; do
    status="Original BIOS (as far as FliperOS knows)"
    atom15_applied && status="ATOM-15 applied"
    backup="none yet"
    conf_get atom15_backup > /dev/null 2>&1 && backup="in $(atom15_where "$ATOM15_DIR/x" | head -1)"
    entries=("apply|Apply ATOM-15|Backup, patch, flash, restart and test. At your own risk.")
    [[ -s $ATOM15_STATE/original.rom ]] &&
      entries+=("restore|Restore the original BIOS|Flash the backup back to the card.")
    entries+=("return|Return|Back to Video Setup.")
    choice=$(ui_menu_hints "$title" "$(ui_fields "Card|$(drm_card_name "$card")" "Firmware|$status" "Backup|$backup")" "$last" \
      "${entries[@]}") || return 0
    last=$choice
    case $choice in
      apply) screen_atom15_apply ;;
      restore) screen_atom15_restore ;;
      return) return 0 ;;
    esac
  done
}

# screen_atom15_confirm: no boot seguinte a gravacao (fliperos-tty1, antes do
# launcher). So o Enter fica com a BIOS nova; Esc ou nenhuma resposta volta a
# original e reinicia.
screen_atom15_confirm() {
  local title="Card firmware test" backup rc
  atom15_trial_active || return 0
  backup=$(conf_get atom15_backup 2> /dev/null) || backup=$ATOM15_STATE/original.rom
  rc=1
  if atom15_flashed; then
    speak "Did the startup screens look right? Press Enter to keep the new firmware."
    ui_timed_confirm "$title" "$ATOM15_SECONDS" "It worked: keep it" \
      "Were the startup screens stable on the tube, from the first second (the computer's logo, the boot menu)?" \
      "Press Enter (button 1) ONLY if they were." \
      "With Esc or no answer, the original BIOS is flashed back and the computer restarts."
    rc=$?
  fi
  if ((rc == 0)); then
    atom15_confirm
    ui_msg "$title" "$(ui_yes "ATOM-15 stays on the card.")" "" "Your original BIOS is here:" "$(atom15_where "$backup")" "" \
      "Keep a copy off this computer. Setup > Video Setup > Card firmware puts it back."
    return 0
  fi
  ui_info "$title" "Flashing the original BIOS back. DO NOT TURN THE COMPUTER OFF..."
  speak "Flashing the original firmware back. Do not turn the computer off."
  if atom15_revert trial; then
    ui_info "$title" "The original BIOS is back on the card. Restarting..."
    screen_power_now reboot
  else
    ui_msg "$title" "$(ui_bad "Could not flash the original BIOS.")" "" "It will be tried again at the next start." \
      "The backup is here:" "$(atom15_where "$backup")" "" "Details in $FLIPEROS_LOG."
  fi
}
