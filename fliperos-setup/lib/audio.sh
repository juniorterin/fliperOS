# shellcheck shell=bash
# Audio (ALSA), como o worker_audio_menu do gasetup: placa padrao, volume,
# alsamixer. A placa escolhida vale para o sistema inteiro (/etc/asound.conf),
# inclusive para a voz do espeak.

ASOUND_CONF=${ASOUND_CONF:-/etc/asound.conf}

# audio_devices imprime "placa,dispositivo|Nome da placa - dispositivo" a
# partir do "aplay -l", como o worker_default_card do gasetup.
audio_devices() {
  local line
  line=$(LANG=C aplay -l 2> /dev/null) || return 1
  sed -nE 's/^card ([0-9]+): [^[]*\[([^]]*)\], device ([0-9]+): [^[]*\[([^]]*)\].*$/\1,\3|\2 - \4/p' <<< "$line"
}

audio_current() {
  conf_get alsa 2> /dev/null || echo "0,0"
}

# audio_set_default "PLACA,DISPOSITIVO"
audio_set_default() {
  local card=${1%,*} dev=${1#*,}
  cat > "$ASOUND_CONF" << EOF
# Gerado pelo fliperos-setup (Setup > Audio Setup > Default card).
defaults.pcm.card $card
defaults.ctl.card $card
defaults.pcm.device $dev
EOF
  conf_set alsa "$card,$dev"
  log_info "audio: placa padrao $card,$dev"
}

audio_volume() {
  conf_get volume 2> /dev/null || echo 80
}

# audio_set_volume PORCENTAGEM ajusta os controles comuns (nem toda placa
# tem todos, dai o erro ignorado em cada um) e grava o estado.
audio_set_volume() {
  local pct=$1 card control
  card=$(audio_current)
  card=${card%,*}
  for control in Master PCM Front Speaker Headphone; do
    amixer -q -c "$card" sset "$control" "$pct%" unmute > /dev/null 2>&1 || true
  done
  run_logged alsactl store "$card" || true
  conf_set volume "$pct"
}

# audio_test toca a voz de teste na placa escolhida.
audio_test() {
  speak_wait "Sound test. If you can hear this, the audio output is working."
}
