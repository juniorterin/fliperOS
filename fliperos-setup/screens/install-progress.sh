# shellcheck shell=bash
# "Install to HD/SSD": video (opcional), disco, confirmacao, instalacao com
# progresso e o fim (remover a midia, reiniciar). Mesmo roteiro do
# worker_select_install/pre_install/post_install do gasetup.

screen_install() {
  local choice
  if ui_yesno "Install to HD/SSD" "Do you want to configure video?" no; then
    screen_video_setup
  fi
  # Placa AMD que aceita radeon e amdgpu: a pessoa escolhe (sem escolha,
  # a tela nao aparece), se ainda nao escolheu no Video Setup.
  conf_get amd_driver > /dev/null 2>&1 || screen_amd_driver install
  while true; do
    screen_disk_selection || return 0
    screen_disk_confirm || continue
    log_info "instalacao: $DISK_CHOSEN ($DISK_LABEL)"
    while true; do
      if screen_progress "Installing FliperOS" "$DISK_LABEL" \
        < <(install_run "$DISK_CHOSEN" "$DISK_IDENTITY" < /dev/null); then
        screen_install_done
        return 0
      fi
      speak "The installation failed."
      choice=$(screen_progress_failed "Installation failed")
      case $choice in
        retry) continue ;;
        *) return 1 ;;
      esac
    done
  done
}

screen_install_done() {
  speak "Installation completed successfully. Remove the installation disc or USB drive."
  ui_msg "Installation complete" "Installation completed successfully." "" \
    "Remove the installation CD/DVD/USB."
  if ui_yesno "Installation complete" "Reboot now?" yes; then
    screen_reboot_now
  fi
}

# screen_reboot_now desmonta o que o setup montou, sincroniza e reinicia.
screen_reboot_now() {
  ui_info "Rebooting" "Syncing the drives and rebooting..."
  screen_power_now reboot
}

# screen_power_now reboot|poweroff: desmonta, sincroniza, solta a interface
# grafica e o terminal e so entao pede o reboot (ou o desligamento). Com a
# limpeza do trap de EXIT ainda por fazer quando o SIGTERM do desligamento
# chegava, a sessao do tty1 (sudo, sudo, bash) segurava o reboot ate o
# SIGKILL, 90 s depois. No fim o bash vira um sleep, que o SIGTERM encerra.
screen_power_now() {
  install_unmount
  recovery_umount
  sync
  log_info "desligando: $1"
  restore_terminal
  trap - EXIT
  systemctl "$1" >> "$FLIPEROS_LOG" 2>&1
  exec sleep 60
}
