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
    "Welcome to FliperOS! Choose what starts automatically when the computer turns on. You can change it later in Setup > Frontend." \
    "$(launcher_current)" "${entries[@]}") || choice=setup
  launcher_set "$choice"
  rm -f "$FLIPEROS_ETC/firstboot"
  log_info "primeiro boot concluido: $choice"
}
