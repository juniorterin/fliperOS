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
    "amdgpu|amdgpu$([[ $saved == amdgpu ]] && echo " - current")|Adds Vulkan (PCSX2, Dolphin, Flycast). Seen on an R7 240." \
    "return|Return|Keep the driver as it is.") || return 0
  [[ $choice == return ]] && return 0
  if [[ $mode == install ]]; then
    conf_set amd_driver "$choice"
    log_info "driver AMD da instalacao: $choice"
    return 0
  fi
  [[ $choice == "$saved" && $choice == "$running" ]] && return 0
  if [[ $choice == amdgpu ]]; then
    ui_yesno "Video driver" "amdgpu was only seen on the CRT with an R7 240. After the restart you confirm the picture; with no answer in $AMD_TRIAL_SECONDS s FliperOS goes back to $running by itself. Use amdgpu?" no || return 0
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

# screen_nvidia_driver (Setup > Video Setup > Video driver numa NVIDIA):
# nouveau ou o driver da NVIDIA, baixado na primeira vez (config/fliperos-
# nvidia). A troca passa pelo mesmo teste de imagem do radeon/amdgpu.
screen_nvidia_driver() {
  local card saved running choice text
  card=$(nvidia_card) || return 0
  if is_live || ! is_installed; then
    ui_msg "Video driver" "The NVIDIA driver is installed after FliperOS is installed: Setup > Video Setup > Video driver."
    return 0
  fi
  saved=$(nvidia_driver)
  running=$(drm_card_driver "$card") || running=none
  text=$(ui_fields \
    "Card|$(drm_card_name "$card")" \
    "In use now|$running" \
    "Saved|$saved" \
    "NVIDIA driver|$(nvidia_installed && echo installed || echo "not installed (downloaded, a few hundred MB)")")
  text+=$'\n\n'"nouveau doesn't show native 15 kHz modes on every card; the NVIDIA driver does on the cards Batocera runs at 320x240."
  choice=$(ui_menu_hints "Video driver" "$text" "$saved" \
    "nouveau|nouveau$([[ $saved == nouveau ]] && echo " - current")|Open source, in the kernel. Super resolutions when the grid fails." \
    "nvidia|NVIDIA driver$([[ $saved == nvidia ]] && echo " - current")|NVIDIA's own driver: full 3D speed, native 15 kHz on more cards." \
    "return|Return|Keep the driver as it is.") || return 0
  [[ $choice == return ]] && return 0
  [[ $choice == "$saved" && $choice == "$running" ]] && return 0
  if [[ $choice == nvidia ]] && ! nvidia_installed; then
    ui_yesno "Video driver" "Download and install the NVIDIA driver for $(drm_card_name "$card")? A few hundred MB; the kernel module is compiled here (a few minutes)." yes ||
      return 0
    run_online "Installing the NVIDIA driver" "" nvidia_driver_install || return 0
  fi
  screen_amd_driver_apply "$choice"
}

# screen_video_driver: o Video driver do Video Setup, da placa que tem escolha.
screen_video_driver() {
  if [[ -n $(drm_dual_amd_cards) ]]; then
    screen_amd_driver
  else
    screen_nvidia_driver
  fi
}

# screen_amd_driver_apply DRIVER grava a escolha e a linha do kernel, poe a
# troca em teste (amd_driver_trial_start: o boot seguinte pede para
# confirmar a imagem) e oferece reiniciar (o driver so troca no boot).
screen_amd_driver_apply() {
  local driver=$1 ok=1 card running
  card=$(video_driver_card)
  running=$(drm_card_driver "$card" 2> /dev/null) || running=""
  ui_info "Video driver" "Switching to $driver..."
  video_driver_apply "$driver" || ok=0
  if ((ok)) && is_installed && ! is_live; then
    # O X muda de driver junto (o da NVIDIA tem o seu).
    xorg_generate
    boot_apply || ok=0
  fi
  if ((!ok)); then
    ui_msg "Video driver" "Could not switch the driver." "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  amd_driver_trial_start "$driver" "$running"
  speak "The $driver driver is set."
  if amd_driver_trial > /dev/null; then
    ui_yesno "Video driver" "The $driver driver is used after a restart. Then confirm the picture with Enter: with no answer in $AMD_TRIAL_SECONDS s, FliperOS goes back to $running and restarts. Restart now?" no \
      && screen_reboot_now
  else
    ui_yesno "Video driver" "The $driver driver is used after a restart. Restart now?" no \
      && screen_reboot_now
  fi
  return 0
}

# screen_amd_driver_confirm: no boot seguinte a troca (fliperos-tty1, antes
# do launcher). Enter confirma; Esc ou nenhuma resposta em
# AMD_TRIAL_SECONDS volta ao driver anterior e reinicia.
screen_amd_driver_confirm() {
  local trial previous rc
  trial=$(amd_driver_trial) || return 0
  previous=$(conf_get amd_driver_previous 2> /dev/null) || previous=radeon
  # Aberto pela entrada de volta do Limine: ja esta no anterior.
  if ! amd_driver_trial_running; then
    amd_driver_revert
    return 0
  fi
  speak "Press Enter if you can see this."
  ui_timed_confirm "Video driver" "$AMD_TRIAL_SECONDS" "I can see this" \
    "The picture now comes from the $trial driver." \
    "Press Enter (button 1) if you can see this." \
    "With no answer, FliperOS goes back to $previous and restarts."
  rc=$?
  if ((rc == 0)); then
    amd_driver_trial_confirm
    ui_msg "Video driver" "The $trial driver stays." "Change it in Setup > Video Setup > Video driver."
    # O driver da NVIDIA ficou: o grid de 320x240 diz se ele faz o nativo
    # (a troca esqueceu o resultado do outro driver).
    if [[ $trial == nvidia ]] && ui_yesno "Video driver" "Test now if the NVIDIA driver shows native 15 kHz resolutions (a 320x240 grid)?" yes; then
      VIDEO_CHANGED=0
      screen_low_dotclock_retest
      ((VIDEO_CHANGED)) && boot_apply
    fi
    return 0
  fi
  ui_info "Video driver" "Going back to the $previous driver and restarting..."
  amd_driver_revert
  screen_power_now reboot
}
