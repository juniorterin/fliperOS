# shellcheck shell=bash
# Primeiro boot do disco instalado. Nada a escolher para o que abre ao ligar:
# e o frontend do FliperOS (Setup > Games > Frontend troca). Um assistente
# curto deixa o gabinete pronto: a internet pelo Wi-Fi, quando o cabo nao a
# traz e ha uma placa Wi-Fi; os controles do painel (Button mapping); e a
# tela ao vivo do painel web, que precisa da internet.

screen_first_boot() {
  speak "Welcome to FliperOS."
  launcher_installed fliperos && launcher_set fliperos
  screen_first_boot_wifi
  screen_first_boot_controls
  screen_first_boot_live
  rm -f "$FLIPEROS_ETC/firstboot"
  log_info "primeiro boot concluido: $(launcher_current)"
}

# screen_first_boot_wifi: sem internet pelo cabo e com uma placa Wi-Fi, o
# Wi-Fi (de novo, se nao conectou, ate a pessoa dizer que nao). Com o cabo
# trazendo a internet, ou sem placa Wi-Fi, nada aparece.
screen_first_boot_wifi() {
  local i ask="There is no internet on the network cable. Connect to a Wi-Fi network now?"
  net_online && return 0
  # O cabo ou o Wi-Fi que veio da instalacao ainda subindo.
  if net_connecting; then
    ui_info "Welcome to FliperOS" "Waiting for the network to connect..."
    for ((i = 0; i < 15; i++)); do
      sleep 1
      net_online && return 0
    done
  fi
  [[ -n $(net_wifi_devices) ]] || return 0
  log_info "primeiro boot: sem internet, Wi-Fi oferecido"
  while ! net_online; do
    ui_yesno "Welcome to FliperOS" "$ask (Later: Setup > Network Setup.)" yes || return 0
    screen_wifi 0 quiet
    ask="Still no internet. Try a Wi-Fi network again?"
  done
}

# screen_first_boot_controls: o Button mapping (Setup > Joysticks), que todos
# os emuladores e o frontend usam. Um mapa que ja existe fica.
screen_first_boot_controls() {
  [[ -s $BUTTONS_MAP ]] && return 0
  speak "Now the controls."
  ui_msg "Welcome to FliperOS" "Now the controls: press each control of the panel when asked, so every emulator and the FliperOS frontend know them." "" \
    "Do it again later in Setup > Joysticks > Button mapping."
  screen_buttons
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
