# shellcheck shell=bash
# "Install to HD/SSD": video (opcional), disco, confirmacao, instalacao com
# progresso e o fim (remover a midia, reiniciar). Mesmo roteiro do
# worker_select_install/pre_install/post_install do gasetup.

screen_install() {
  local choice
  if ui_yesno "Install to HD/SSD" "Do you want to configure video?" no; then
    screen_video_setup
  fi
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
  install_unmount
  recovery_umount
  sync
  log_info "reiniciando"
  systemctl reboot
  sleep 30
}
