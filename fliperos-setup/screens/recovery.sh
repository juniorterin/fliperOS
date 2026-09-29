# shellcheck shell=bash
# Recovery Mode (worker_rescue_menu do gasetup): terminal dentro do sistema
# instalado, reinstalar o bootloader, levar a configuracao de video desta
# sessao (placa trocada) e restaurar os arquivos do sistema.

screen_recovery() {
  local found=() entries=() line disk part conn monitor choice
  ui_info "Recovery Mode" "Looking for FliperOS installations..."
  mapfile -t found < <(recovery_find)
  if ((${#found[@]} == 0)); then
    ui_msg "Recovery Mode" "No FliperOS installation was found on this computer."
    return 0
  fi
  for line in "${found[@]}"; do
    IFS="|" read -r disk _ conn monitor <<< "$line"
    entries+=("$disk|$(disk_describe "$disk")${conn:+ - $conn}${monitor:+, $monitor}")
  done
  if ((${#found[@]} == 1)); then
    disk=${found[0]%%|*}
  else
    disk=$(ui_menu "Recovery Mode" "Select the installation to repair." "" "${entries[@]}" "return|Return") || return 0
    [[ $disk == return ]] && return 0
  fi
  while true; do
    choice=$(ui_menu "Recovery Mode" "FliperOS on $(disk_describe "$disk")" shell \
      "shell|Open a terminal in the installed system" \
      "bootloader|Reinstall the bootloader" \
      "video|Apply this session's video settings (new video card)" \
      "restore|Restore system files (keeps ROMs and settings)" \
      "return|Return") || return 0
    case $choice in
      shell) screen_recovery_shell "$disk" ;;
      bootloader)
        ui_yesno "Reinstall the bootloader" "Limine will be installed again on $disk (BIOS and UEFI)." yes &&
          run_with_progress "Reinstalling the bootloader" "$(disk_describe "$disk")" recovery_bootloader "$disk" &&
          ui_msg "Recovery Mode" "The bootloader was reinstalled."
        ;;
      video)
        ui_yesno "Video settings" "$(printf 'The installed system will use the video settings of this session:\n\n%s' \
          "$(ui_fields "Output|$(conf_get connector 2> /dev/null || echo "boot menu")" \
            "Monitor|$(conf_get monitor 2> /dev/null || echo "not set")")")" yes &&
          run_with_progress "Applying video settings" "$(disk_describe "$disk")" recovery_video "$disk" &&
          ui_msg "Recovery Mode" "The video settings were applied."
        ;;
      restore)
        ui_yesno "Restore system files" "$(printf 'All system files will be copied again from this media.\n\nROMs, saves, network, audio and video settings are kept.\n\nContinue?')" no &&
          run_with_progress "Restoring system files" "$(disk_describe "$disk")" recovery_restore "$disk" &&
          ui_msg "Recovery Mode" "The system files were restored."
        ;;
      return) return 0 ;;
    esac
  done
}

screen_recovery_shell() {
  local disk=$1
  if ! recovery_mount "$disk"; then
    ui_msg "Recovery Mode" "Could not mount the installed system (see the log)."
    return 0
  fi
  ui_clear
  printf '%s\n\n' "Root shell inside the FliperOS installed on $disk. Type 'exit' to return." > /dev/tty
  chroot "$RECOVERY_TARGET" /bin/bash --login < /dev/tty > /dev/tty 2>&1
  recovery_umount
  ui_flush_input
}
