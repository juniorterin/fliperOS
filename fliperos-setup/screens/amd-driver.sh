# shellcheck shell=bash
# Setup > Video Setup > Video driver, e a mesma pergunta na instalacao: radeon ou
# amdgpu nas placas AMD que aceitam os dois (drm_card_dual_amd em lib/drm.sh,
# amd_driver_* em lib/bootloader.sh). O radeon e o recomendado: foi com ele
# que o 15 kHz foi validado no gabinete.

# screen_amd_driver [install]. Com "install" (e sempre na midia de
# instalacao, onde o Video Setup tambem abre) so grava a escolha no
# fliperos.conf (install_configure_video a leva ao disco novo) e nao diz
# nada quando a placa nao tem escolha.
screen_amd_driver() {
  local mode=${1:-} cards card names="" saved running choice text
  is_live && mode=install
  cards=$(drm_dual_amd_cards)
  if [[ -z $cards ]]; then
    [[ $mode == install ]] && return 0
    ui_msg "Video driver" "No video card here works with both AMD drivers." "" \
      "Only the AMD HD 7000, R7/R9 200 and 300 series (GCN 1.0 and 1.1) can choose:" \
      "older cards use radeon and newer ones amdgpu, with nothing to set."
    return 0
  fi
  for card in $cards; do
    names+="${names:+, }$(drm_card_name "$card")"
  done
  saved=$(amd_driver)
  running=$(drm_card_driver "${cards%%$'\n'*}") || running=none
  text=$(ui_fields \
    "Card|$names" \
    "In use now|$running" \
    "Saved|$saved")
  text+=$'\n\n'"$(ui_yes "Recommended: radeon, the driver tested on the CRT.")"
  [[ $mode == install ]] && text+=$'\n'"You can change it later in Setup > Video Setup > Video driver."
  choice=$(ui_menu_hints "Video driver" "$text" "$saved" \
    "radeon|radeon (recommended)$([[ $saved == radeon ]] && echo " - current")|Tested at 15 kHz on the CRT. OpenGL only, no Vulkan." \
    "amdgpu|amdgpu$([[ $saved == amdgpu ]] && echo " - current")|Adds Vulkan (PCSX2, Dolphin, Flycast). Not tested on the CRT." \
    "return|Return|Keep the driver as it is.") || return 0
  [[ $choice == return ]] && return 0
  if [[ $mode == install ]]; then
    conf_set amd_driver "$choice"
    log_info "driver AMD da instalacao: $choice"
    return 0
  fi
  [[ $choice == "$saved" && $choice == "$running" ]] && return 0
  if [[ $choice == amdgpu ]]; then
    ui_yesno "Video driver" "amdgpu is not tested on the CRT yet. If there is no picture after the restart, press a key while it boots and pick \"FliperOS - radeon driver\" in the boot menu. Use amdgpu?" no || return 0
  fi
  screen_amd_driver_apply "$choice"
}

# screen_amd_driver_check: uma vez so (amd_driver_checked no fliperos.conf),
# no menu principal do sistema instalado. Se a placa roda com o driver que
# nao e o recomendado, sugere a troca. Quem ja escolheu o driver no Setup ou
# na instalacao (amd_driver=) nao e perguntado.
screen_amd_driver_check() {
  local card running recommended
  is_installed && ! is_live || return 0
  conf_get amd_driver_checked > /dev/null 2>&1 && return 0
  conf_set amd_driver_checked 1
  conf_get amd_driver > /dev/null 2>&1 && return 0
  IFS='|' read -r card running recommended <<< "$(amd_driver_mismatch)" || return 0
  [[ -n $card ]] || return 0
  log_info "driver AMD: $card em $running, recomendado $recommended"
  ui_yesno "Video driver" "Your $(drm_card_name "$card") is running on the $running driver. $recommended is recommended: it is the one tested at 15 kHz on the CRT. Switch to $recommended? (You can change it later in Setup > Video Setup > Video driver.)" yes || return 0
  screen_amd_driver_apply "$recommended"
}

# screen_amd_driver_apply DRIVER grava a escolha, a linha do kernel e o
# initramfs, e oferece reiniciar (o driver so troca no proximo boot).
screen_amd_driver_apply() {
  local driver=$1 ok=1
  ui_info "Video driver" "Switching to $driver. Rebuilding the boot files takes a minute..."
  amd_driver_apply "$driver" || ok=0
  if ((ok)) && is_installed && ! is_live; then
    boot_apply || ok=0
  fi
  if ((!ok)); then
    ui_msg "Video driver" "Could not switch the driver." "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  speak "The $driver driver is set."
  ui_yesno "Video driver" "The $driver driver is used after a restart. Restart now?" no \
    && screen_reboot_now
  return 0
}
