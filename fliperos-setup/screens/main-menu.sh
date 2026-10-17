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
# 1 com --desktop: aberto pelo atalho do LXDE (a interface grafica numa janela).
SETUP_DESKTOP=${SETUP_DESKTOP:-0}
# 1 com --remote: o menu aberto pelo SSH (em texto, no terminal de la).
SETUP_REMOTE=${SETUP_REMOTE:-0}

screen_live_menu() {
  local choice last=""
  while true; do
    UI_STATUS=$(status_line)
    choice=$(ui_menu_hints "FliperOS Setup" "" "$last" \
      "install|Install to HD/SSD|Copy FliperOS to a disk of this computer." \
      "recovery|Recovery Mode|Repair a FliperOS that is already installed." \
      "terminal|Terminal|The command line of the install media." \
      "shutdown|Shutdown|Power off or restart the computer.") || continue
    last=$choice
    case $choice in
      install) screen_install ;;
      recovery) screen_recovery ;;
      terminal) screen_terminal && return "$SETUP_EXIT_SHELL" ;;
      shutdown) screen_power ;;
    esac
  done
}

# screen_reload_if_updated: os arquivos do Setup mudaram em disco com ele
# aberto? Avisa e o reabre no lugar deste processo, com os mesmos argumentos.
# Chamado no comeco dos menus (o principal e o Setup).
screen_reload_if_updated() {
  [[ -n ${SETUP_STAMP:-} && $(setup_stamp) != "$SETUP_STAMP" ]] || return 0
  [[ -x $SETUP_DIR/fliperos-setup ]] || return 0
  log_info "fliperos-setup foi atualizado com a tela aberta: reabrindo"
  ui_msg "FliperOS Setup" "FliperOS Setup was updated while it was open." "" "It reopens now, with the new version."
  restore_terminal
  exec "$SETUP_DIR/fliperos-setup" "${SETUP_ARGS[@]}"
}

screen_main_menu() {
  local choice last="" start
  # Placa AMD no driver que nao e o recomendado: sugere a troca, uma vez so.
  screen_amd_driver_check
  # As BIOS que faltam aos jogos das pastas, em segundo plano (Setup > Games
  # > Downloader > Download BIOS).
  bios_auto_start
  while true; do
    screen_reload_if_updated
    UI_STATUS=$(status_line)
    # Com um jogo no boot (Setup > Games > Frontend), o item abre o jogo.
    start="frontend|Start frontend|Open the game list (the frontend chosen in Setup)."
    if [[ $(launcher_current) == game && -n $(bootgame_label) ]]; then
      start="frontend|Start $(bootgame_label)|The game that opens at boot (Setup > Games > Frontend)."
    fi
    choice=$(ui_menu_hints "FliperOS" "" "$last" \
      "$start" \
      "setup|Setup|Video, audio, network, controls, games and system." \
      "desktop|Start desktop|The LXDE desktop, for a mouse and a keyboard." \
      "shell|Exit to shell|The command line. Type fliperos-menu to come back." \
      "power|Shutdown / Reboot|Power off or restart the computer.") || continue
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

# screen_terminal limpa a tela; no shell, o MOTD (config/fliperos-motd) diz
# como voltar ao menu.
screen_terminal() {
  ui_clear
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
      "Choose one in Setup > Games > Frontend."
    return 1
  fi
  if [[ $current == game && -z $(bootgame_label) ]]; then
    ui_msg "Start frontend" "No game is set to open at boot." "" \
      "Choose one in Setup > Games > Frontend."
    return 1
  fi
  if ! launcher_installed "$current"; then
    ui_msg "Start frontend" "$(launcher_label "$current") is not installed." "" \
      "Choose another one in Setup > Games > Frontend."
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
  # Pelo SSH o launcher abriria no terminal da rede, sem o monitor.
  if ((SETUP_REMOTE == 1)); then
    ui_msg "$1" "This menu is open over the network (SSH)." "" \
      "Frontends, games and the desktop open on the cabinet screen: start them there."
    return 1
  fi
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
