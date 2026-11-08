# shellcheck shell=bash
# Primeiro boot do disco instalado. Nada a escolher para o que abre ao ligar:
# e o frontend do FliperOS (Setup > Games > Frontend troca). Um assistente
# curto deixa o gabinete pronto: a internet pelo Wi-Fi, quando o cabo nao a
# traz e ha uma placa Wi-Fi; os updates publicados depois da ISO, que ja
# entram aqui; os controles do painel (Button mapping); e a
# tela ao vivo do painel web, que precisa da internet.

screen_first_boot() {
  speak "Welcome to FliperOS."
  launcher_installed fliperos && launcher_set fliperos
  screen_first_boot_wifi
  screen_first_boot_update
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

# screen_first_boot_update: os updates publicados depois da ISO, logo que ha
# internet e antes do resto do assistente, para os controles e o resto ja
# abrirem na versao nova. Num disco recem-instalado nada foi mudado a mao:
# aplica sem perguntar. Com o Setup novo em disco, ele se reabre com os
# mesmos argumentos e o assistente recomeca (o Wi-Fi conectado nao aparece
# de novo); FLIPEROS_FIRSTBOOT_UPDATED impede uma segunda volta. Um update
# que pede reinicio reinicia, e o primeiro boot continua no proximo boot.
screen_first_boot_update() {
  local title="Welcome to FliperOS" list result reboot n
  ((${FLIPEROS_FIRSTBOOT_UPDATED:-0})) && return 0
  net_online || return 0
  list=$(patch_pending) || return 0
  [[ -n $list ]] || return 0
  log_info "primeiro boot: updates pendentes: $(cut -f1 <<< "$list" | paste -sd' ')"
  result=$(mktemp)
  if ! run_with_progress "Updating FliperOS" "" patch_apply "$result"; then
    rm -f "$result"
    ui_msg "$title" "$(ui_bad "The FliperOS update did not finish.")" \
      "It is offered again at the next boot. Log: /var/log/fliperos-update.log."
    return 0
  fi
  reboot=$(awk -F'\t' '$1 == "applied" && $3 == "yes" { print "yes"; exit }' "$result")
  n=$(awk -F'\t' '$1 == "applied" { n = $2 } END { print n }' "$result")
  rm -f "$result"
  log_info "primeiro boot: update ${n:-?} aplicado (reboot=${reboot:-no})"
  if [[ $reboot == yes ]]; then
    ui_info "$title" "FliperOS is up to date (update $n)." "Restarting to finish; the setup continues afterwards."
    sleep 3
    screen_power_now reboot
  fi
  ui_info "$title" "FliperOS is up to date (update $n)." "The setup continues with the new version..."
  sleep 2
  restore_terminal
  export FLIPEROS_FIRSTBOOT_UPDATED=1
  exec "$SETUP_DIR/fliperos-setup" "${SETUP_ARGS[@]}"
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
