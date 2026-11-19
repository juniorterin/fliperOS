# shellcheck shell=bash
# As telas do Setup que o painel web abre no gabinete (Setup no painel >
# "Abrir no gabinete", fliperos-setup --screen NOME): as que precisam do tubo
# ou do controle na mao (a grade da geometria, os padroes de cor, o mapa dos
# botoes, os alvos da pistola...). O painel grava o pedido, o fliperos-tty1
# abre a tela e, ao sair dela, volta ao que estava na tela antes.
#
# PANEL_SCREENS: os nomes que o painel pode pedir (a lista fechada; o
# config/fliperos-web confere a mesma).
PANEL_SCREENS="setup geometry resolution monitors colour scanlines outputs driver lowdot firmware mixer buttons layout guncon axes bluetooth lpt latency oscr storage"

# panel_screen_known NOME: e um dos nomes da lista.
panel_screen_known() {
  [[ $1 =~ ^[a-z0-9]+$ && " $PANEL_SCREENS " == *" $1 "* ]]
}

# screen_audio_mixer: o AlsaMixer da placa de agora (Audio Setup > AlsaMixer),
# gravado ao sair.
screen_audio_mixer() {
  local current
  current=$(audio_current)
  ui_clear
  ui_text alsamixer -c "${current%,*}" < /dev/tty > /dev/tty 2>&1
  run_logged alsactl store "${current%,*}"
}

# screen_from_panel NOME: a tela pedida pelo painel. As do Video Setup
# terminam como ele (video_setup_leave: o Xorg, a linha do kernel e
# reiniciar). Status 2: nome que nao esta na lista.
screen_from_panel() {
  local name=${1:-} before
  panel_screen_known "$name" || return 2
  log_info "painel web: abrindo a tela $name no gabinete"
  VIDEO_CHANGED=0
  before=$(video_snapshot)
  case $name in
    setup) screen_setup_menu ;;
    geometry) screen_geometry ;;
    resolution) screen_custom_resolution ;;
    monitors) screen_multi_monitor ;;
    colour) screen_colour_calibrate "$(color_caps | sed -n 's/^range //p')" ;;
    scanlines) screen_scanlines_adjust ;;
    outputs) screen_video_retest_request ;;
    driver) screen_video_driver ;;
    lowdot) screen_low_dotclock_retest ;;
    firmware) screen_atom15 ;;
    mixer) screen_audio_mixer ;;
    buttons) screen_buttons ;;
    layout) screen_buttons_layout ;;
    guncon) screen_calibrate_guns ;;
    axes) screen_calibrate ;;
    bluetooth) screen_bluetooth ;;
    lpt) screen_lpt ;;
    latency) screen_latency ;;
    oscr) screen_oscr_firmware ;;
    storage) screen_external_storage ;;
  esac
  case $name in
    geometry | resolution | monitors | outputs | driver | lowdot | firmware) video_setup_leave "$before" ;;
  esac
  return 0
}
