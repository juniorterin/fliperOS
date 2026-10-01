# shellcheck shell=bash
# Menus principais. Na midia de instalacao e o "FliperOS Setup" (o
# isomainmenu do gasetup); no sistema instalado, o mainmenu que aparece
# quando o frontend fecha.

# Codigos de saida do setup: a pessoa pediu o terminal, ou pediu um
# launcher, que o fliperos-tty1 abre (lib/launcher.sh).
SETUP_EXIT_SHELL=10
SETUP_EXIT_LAUNCH=20
# 1 com --menu, que so o laco do fliperos-tty1 (fliperos-menu) passa.
SETUP_MENU_LOOP=${SETUP_MENU_LOOP:-0}

screen_live_menu() {
  local choice last=install
  while true; do
    UI_STATUS=$(status_line)
    choice=$(ui_menu "FliperOS Setup" "" "$last" \
      "install|Install to HD/SSD" \
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
      frontend) screen_start_frontend && return "$SETUP_EXIT_LAUNCH" ;;
      setup) screen_setup_menu ;;
      desktop) screen_start_desktop && return "$SETUP_EXIT_LAUNCH" ;;
      shell) screen_terminal && return "$SETUP_EXIT_SHELL" ;;
      power) screen_power ;;
    esac
  done
}

screen_terminal() {
  ui_clear
  printf '%s\n\n' "To return to the menu, type:  fliperos-menu" > /dev/tty
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

# screen_start_frontend pede o launcher padrao (worker_start_fe do gasetup).
# Status 0: o pedido foi gravado e o setup deve sair com SETUP_EXIT_LAUNCH;
# o fliperos-tty1 abre o launcher e reabre o setup quando ele fecha.
screen_start_frontend() {
  local current
  current=$(launcher_current)
  if [[ $current == setup ]]; then
    ui_msg "Start frontend" "No frontend is set: FliperOS starts in this menu." "" \
      "Choose one in Setup > Frontend."
    return 1
  fi
  if ! launcher_installed "$current"; then
    ui_msg "Start frontend" "$(launcher_label "$current") is not installed." "" \
      "Choose another one in Setup > Frontend."
    return 1
  fi
  screen_launch "Start frontend" default
}

screen_start_desktop() {
  if ! launcher_installed lxde; then
    ui_msg "Start desktop" "The LXDE desktop is not installed."
    return 1
  fi
  screen_launch "Start desktop" lxde
}

# screen_launch TITULO NOME grava o pedido do launcher (lib/launcher.sh).
# So o laco do fliperos-tty1 (--menu) abre o pedido; num "sudo
# fliperos-setup" digitado no shell ninguem o abriria.
screen_launch() {
  if ((SETUP_MENU_LOOP != 1)); then
    ui_msg "$1" "This setup was opened from the shell." "" \
      "Leave it and type  fliperos-menu  to start from the FliperOS menu."
    return 1
  fi
  if ! launcher_request "$2"; then
    ui_msg "$1" "Could not start it (see /var/log/fliperos-setup.log)."
    return 1
  fi
  ui_clear
  return 0
}
