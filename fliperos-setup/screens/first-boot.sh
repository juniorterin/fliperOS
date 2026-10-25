# shellcheck shell=bash
# Primeiro boot do disco instalado: escolher o que abre ao ligar. A lista
# sai dos launchers realmente instalados, mais o proprio menu do setup.

screen_first_boot() {
  local entries=() name desc choice
  while IFS='|' read -r name desc; do
    entries+=("$name|$desc")
  done < <(launcher_available)
  speak "Welcome to FliperOS. Choose what starts when the computer turns on."
  choice=$(ui_menu "Choose default launcher" \
    "Welcome to FliperOS! Choose what starts automatically when the computer turns on. You can change it later in Setup > Games > Frontend." \
    "$(launcher_current)" "${entries[@]}") || choice=setup
  launcher_set "$choice"
  screen_first_boot_live
  rm -f "$FLIPEROS_ETC/firstboot"
  log_info "primeiro boot concluido: $choice"
}

# screen_first_boot_live: a tela ao vivo do painel web ja sai instalada e
# ligada (stream=after no services.conf, pelo fliperos-extras). O ffmpeg vem
# na imagem; aqui so baixa o go2rtc. Sem internet (e sem o Wi-Fi oferecido),
# fica para o Setup > Games > Extras > Live screen.
screen_first_boot_live() {
  extras_installed stream && return 0
  if run_online "Installing Live screen" "" extras_install stream; then
    log_info "primeiro boot: tela ao vivo instalada"
    return 0
  fi
  ui_msg "Live screen" "The Live screen of the web panel could not be installed now." "" \
    "Install it later in Setup > Games > Extras > Live screen."
  return 1
}
