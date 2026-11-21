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
  # Som estereo ou mono, logo depois do video.
  screen_install_sound
  # O apelido do gabinete para a party e o link (opcional: Esc pula).
  screen_cabinet_name install
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

# screen_install_sound: a etapa de som do instalador, estereo ou mono. O mono e
# para o gabinete com uma caixa so, que perderia metade do som em estereo. A
# escolha vai no fliperos.conf e no asound.conf que a instalacao leva para o
# disco (install_configure_video e install_configure_user); depois, em Setup >
# Audio Setup > Stereo or mono. Esc deixa estereo, que e o padrao.
screen_install_sound() {
  local choice
  speak "Now the sound."
  choice=$(ui_menu "Install to HD/SSD" "Sound: is this a stereo (two speakers) or a mono (one speaker) cabinet? Change it later in Setup > Audio Setup." \
    "$(audio_output_mode)" "stereo|Stereo (two speakers)" "mono|Mono (one speaker)") || return 0
  audio_set_output "$choice" || return 0
  log_info "instalacao: som $choice"
}

screen_install_done() {
  # O sistema roda da propria midia de instalacao: depois que a pessoa a tira,
  # um programa que nao esteja na memoria da erro de leitura (Input/output
  # error) no terminal. Por isso o que o fim precisa vai antes do aviso: o
  # disco novo desmontado e sincronizado, e os programas do reinicio lidos
  # uma vez (na memoria, rodam sem a midia).
  install_unmount
  recovery_umount
  sync
  screen_power_warm
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
  # Sem o systemctl (a midia do sistema ao vivo foi tirada e ele nao estava na
  # memoria), o pedido vai direto ao kernel, so com o que o proprio bash faz.
  systemctl "$1" >> "$FLIPEROS_LOG" 2>&1 || screen_power_hard "$1"
  exec sleep 60
}

# screen_power_warm: roda uma vez, de graca, cada programa que o reinicio usa
# depois da midia tirada (o systemctl, o sleep, o stty, o sync, o rm...): na
# memoria, eles abrem sem a midia.
screen_power_warm() {
  systemctl --version > /dev/null 2>&1
  sleep 0 > /dev/null 2>&1
  sync
  stty -a < /dev/tty > /dev/null 2>&1
  kbd_mode < /dev/tty > /dev/null 2>&1
  rm -f /nonexistent-fliperos-warm
  mountpoint -q / > /dev/null 2>&1
  return 0
}

# screen_power_hard reboot|poweroff: o pedido direto ao kernel (sysrq), sem
# nenhum programa: o disco novo ja esta desmontado e sincronizado, e o sistema
# ao vivo nao guarda nada. So o bash: o echo e um comando dele.
screen_power_hard() {
  log_info "desligando direto pelo kernel: $1"
  echo 1 > "${SYSRQ_ENABLE:-/proc/sys/kernel/sysrq}" 2> /dev/null
  echo s >> "${SYSRQ_TRIGGER:-/proc/sysrq-trigger}" 2> /dev/null
  echo u >> "${SYSRQ_TRIGGER:-/proc/sysrq-trigger}" 2> /dev/null
  if [[ $1 == poweroff ]]; then
    echo o >> "${SYSRQ_TRIGGER:-/proc/sysrq-trigger}" 2> /dev/null
  else
    echo b >> "${SYSRQ_TRIGGER:-/proc/sysrq-trigger}" 2> /dev/null
  fi
  return 0
}
