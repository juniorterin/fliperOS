# shellcheck shell=bash
# Menus principais. Na midia de instalacao e o "FliperOS Setup" (o
# isomainmenu do gasetup); no sistema instalado, o mainmenu que aparece
# quando o frontend fecha.

# Codigo de saida do setup quando a pessoa pede o terminal.
SETUP_EXIT_SHELL=10

screen_live_menu() {
  local choice last=install
  while true; do
    UI_STATUS=$(status_line)
    choice=$(ui_menu "FliperOS Setup" "" "$last" \
      "install|Install to HD" \
      "recovery|Recovery Mode" \
      "terminal|Terminal" \
      "shutdown|Shutdown") || continue
    last=$choice
    case $choice in
      install) screen_install ;;
      recovery) screen_recovery ;;
      terminal) screen_terminal && return "$SETUP_EXIT_SHELL" ;;
      shutdown) screen_power ;;
    esac
  done
}

screen_main_menu() {
  local choice last=frontend
  while true; do
    UI_STATUS=$(status_line)
    choice=$(ui_menu "FliperOS" "" "$last" \
      "frontend|Start frontend" \
      "setup|Setup (video, audio, network...)" \
      "desktop|Start desktop" \
      "shell|Exit to shell" \
      "power|Shutdown / Reboot") || continue
    last=$choice
    case $choice in
      frontend) screen_start_frontend ;;
      setup) screen_setup_menu ;;
      desktop) screen_start_desktop ;;
      shell) screen_terminal && return "$SETUP_EXIT_SHELL" ;;
      power) screen_power ;;
    esac
  done
}

screen_terminal() {
  ui_clear
  printf '%s\n\n' "To return to the setup, type:  sudo fliperos-setup" > /dev/tty
  return 0
}

screen_power() {
  local choice
  choice=$(ui_menu "Shutdown / Reboot" "" poweroff \
    "poweroff|Power off" \
    "reboot|Reboot" \
    "return|Return") || return 0
  case $choice in
    poweroff)
      ui_yesno "Power off" "Really power off the computer?" no || return 0
      ui_info "Power off" "Powering off..."
      install_unmount
      recovery_umount
      sync
      systemctl poweroff
      sleep 30
      ;;
    reboot)
      ui_yesno "Reboot" "Really reboot the computer?" no || return 0
      screen_reboot_now
      ;;
  esac
}

# screen_start_frontend abre o launcher padrao como o usuario do sistema e
# volta ao menu quando ele fecha (worker_start_fe do gasetup).
screen_start_frontend() {
  local current
  current=$(launcher_current)
  if [[ $current == setup ]]; then
    ui_msg "Start frontend" "No frontend is set: FliperOS starts in this menu." "" \
      "Choose one in Setup > Frontend."
    return 0
  fi
  if ! launcher_installed "$current"; then
    ui_msg "Start frontend" "$(launcher_label "$current") is not installed." "" \
      "Choose another one in Setup > Frontend."
    return 0
  fi
  ui_clear
  printf '\e[?25l' > /dev/tty
  launcher_exec < /dev/tty > /dev/tty 2>&1
  printf '\e[?25h' > /dev/tty
  ui_palette > /dev/tty
  ui_flush_input
}

screen_start_desktop() {
  if ! launcher_installed lxde; then
    ui_msg "Start desktop" "The LXDE desktop is not installed."
    return 0
  fi
  ui_clear
  launcher_exec lxde < /dev/tty > /dev/tty 2>&1
  ui_palette > /dev/tty
  ui_flush_input
}
