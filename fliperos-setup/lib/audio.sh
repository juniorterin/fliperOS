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

# Controles que fazem o papel de volume. O PCM fica no maximo, como no
# worker_set_volume do gasetup: movido junto, ele multiplicaria a atenuacao
# do Master (80 viraria bem menos que 80).
AUDIO_VOLUME_CONTROLS="Master Front Speaker Headphone"
AUDIO_STEP=5

audio_card() {
  local card
  card=$(audio_current)
  printf '%s\n' "${card%,*}"
}

# audio_controls PLACA imprime os controles de volume que a placa tem. Placa
# so com PCM (varias USB simples) usa o proprio PCM como volume.
audio_controls() {
  local have c found=0
  have=$(amixer -c "$1" scontrols 2> /dev/null | sed -n "s/^Simple mixer control '\([^']*\)',0$/\1/p")
  for c in $AUDIO_VOLUME_CONTROLS; do
    if grep -qx "$c" <<< "$have"; then
      printf '%s\n' "$c"
      found=1
    fi
  done
  if ((!found)) && grep -qx PCM <<< "$have"; then
    echo PCM
  fi
  return 0
}

# audio_volume imprime o volume de verdade (o do mixer, que as teclas de
# volume tambem mudam); sem mixer legivel, o gravado no Setup.
audio_volume() {
  local card control pct
  card=$(audio_card)
  control=$(audio_controls "$card" | head -1)
  if [[ -n $control ]]; then
    pct=$(amixer -c "$card" sget "$control" 2> /dev/null | sed -n 's/.*\[\([0-9]\{1,3\}\)%\].*/\1/p' | head -1)
    if [[ -n $pct ]]; then
      printf '%s\n' "$pct"
      return 0
    fi
  fi
  conf_get volume 2> /dev/null || echo 80
}

# audio_set_volume PORCENTAGEM ajusta os controles de volume, deixa o PCM
# no maximo e grava o estado (vale no proximo boot).
audio_set_volume() {
  local pct=$1 card control controls
  card=$(audio_card)
  controls=$(audio_controls "$card")
  if [[ $controls != PCM ]]; then
    amixer -q -c "$card" sset PCM 100% unmute > /dev/null 2>&1 || true
  fi
  for control in $controls; do
    amixer -q -c "$card" sset "$control" "$pct%" unmute > /dev/null 2>&1 || true
  done
  run_logged alsactl store "$card" || true
  conf_set volume "$pct"
}

# audio_step up|down|mute: as teclas de volume do teclado (triggerhappy, ver
# config/fliperos-volume.triggers), em qualquer tela: KMS, X ou console. O
# estado e gravado a cada toque, porque gabinete costuma ser desligado na
# tomada.
audio_step() {
  local card control change
  case $1 in
    up) change="$AUDIO_STEP%+ unmute" ;;
    down) change="$AUDIO_STEP%-" ;;
    mute) change="toggle" ;;
    *) return 1 ;;
  esac
  card=$(audio_card)
  for control in $(audio_controls "$card"); do
    # shellcheck disable=SC2086 # "5%+ unmute" sao dois argumentos
    amixer -q -c "$card" sset "$control" $change > /dev/null 2>&1 || true
  done
  alsactl store "$card" > /dev/null 2>&1 || true
}

# ── Latencia de audio do GroovyMAME (Audio Latency MAME do gasetup) ────
# audio_latency do mame.ini: 0.0 a 50.0, 0 = o padrao do GroovyMAME. Menos
# responde mais rapido; mais evita estalos.

audio_mame_latency() {
  ini_get "$MAME_INI" audio_latency 2> /dev/null || echo 0.0
}

audio_valid_mame_latency() {
  [[ $1 =~ ^[0-9]{1,2}(\.[0-9]+)?$ ]] && awk -v v="$1" 'BEGIN { exit !(v <= 50) }'
}

audio_set_mame_latency() {
  audio_valid_mame_latency "$1" || return 1
  ini_set "$MAME_INI" audio_latency "$1"
}

# audio_test toca a voz de teste na placa escolhida.
audio_test() {
  speak_wait "Sound test. If you can hear this, the audio output is working."
}
