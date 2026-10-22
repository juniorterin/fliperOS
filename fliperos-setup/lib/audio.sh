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
  conf_set alsa "$1"
  audio_write_conf
  log_info "audio: placa padrao $1"
}

# ── Nivelador de volume ──────────────────────────────────────────
# Setup > Audio Setup > Volume leveler, desligado de fabrica: um compressor
# (o SC4 do swh-plugins, LADSPA) no "default" do ALSA, por onde passam todos
# os emuladores. Aproxima o volume de um sistema do de outro: o que bate em
# 0 dB sai em -9, o que fica em -30 sai em -24. Sem lookahead: nao atrasa o
# som. Controles do SC4, na ordem: RMS/pico, ataque (ms), release (ms),
# limiar (dB), razao, joelho (dB), ganho de compensacao (dB).
AUDIO_LEVELER_PLUGIN=${AUDIO_LEVELER_PLUGIN:-/usr/lib/ladspa/sc4_1882.so}
AUDIO_LEVELER_CONTROLS="0 20 400 -20 4 6 6"

# audio_leveler_enabled: o nivelador esta ligado (e o plugin existe).
audio_leveler_enabled() {
  [[ $(conf_get audio_leveler 2> /dev/null) == on && -f $AUDIO_LEVELER_PLUGIN ]]
}

# audio_leveler_available: o swh-plugins esta instalado.
audio_leveler_available() {
  [[ -f $AUDIO_LEVELER_PLUGIN ]]
}

# audio_leveler_set on|off liga ou desliga e regrava o asound.conf. Status 1:
# o plugin nao esta instalado (nada muda).
audio_leveler_set() {
  if [[ $1 == on ]] && ! audio_leveler_available; then
    return 1
  fi
  conf_set audio_leveler "$1"
  audio_write_conf
  log_info "audio: nivelador de volume $1"
}

# ── O som da tela ao vivo ────────────────────────────────────────
# Live screen sound (o painel web, config/fliperos-stream), desligado de
# fabrica: uma copia de tudo o que toca vai para um loopback do ALSA
# (snd-aloop, a placa FliperOSLoop), que o ffmpeg da transmissao grava. A
# copia so entra no asound.conf com o loopback aberto: sem ele o "default" nao
# abriria e tudo ficaria mudo. Visto no gabinete (2026-10-22, HDA Intel):
#   - o dmix padrao do loopback nao abre ("Sample format non available") e o
#     multi so abre com os dois dmix iguais: os dois vao escritos, no mesmo
#     formato, taxa e periodo (S16_LE, 48000, 1024/4096, o padrao do dmix);
#   - o timer_source na placa deixava o loopback ocupado (EBUSY) e o hrtimer
#     nao abre: fica o timer padrao (jiffies), 31 s sem nenhum xrun nem
#     buraco no som.
# Ao ligar, o "default" e testado (0,1 s de silencio); se nao abrir (uma placa
# que nao aceita S16_LE), volta como estava.
AUDIO_TEE_RATE=48000 AUDIO_TEE_PERIOD=1024 AUDIO_TEE_BUFFER=4096
AUDIO_LOOP_ID=${AUDIO_LOOP_ID:-FliperOSLoop}
AUDIO_LOOP_MODPROBE=${AUDIO_LOOP_MODPROBE:-/etc/modprobe.d/fliperos-aloop.conf}
AUDIO_LOOP_LOAD=${AUDIO_LOOP_LOAD:-/etc/modules-load.d/fliperos-aloop.conf}
AUDIO_PROC_CARDS=${AUDIO_PROC_CARDS:-/proc/asound/cards}

audio_stream_enabled() {
  [[ $(conf_get stream_audio 2> /dev/null) == on ]]
}

# audio_card_id PLACA: o nome da placa no ALSA (o /proc/asound/cards), que
# nao muda quando a ordem das placas muda.
audio_card_id() {
  sed -nE "s/^ *$1 \[([^] ]+) *\].*/\1/p" "$AUDIO_PROC_CARDS" 2> /dev/null | head -n 1
}

# audio_loop_ready: o loopback esta aberto agora.
audio_loop_ready() {
  grep -qE "\[$AUDIO_LOOP_ID *\]" "$AUDIO_PROC_CARDS" 2> /dev/null
}

# audio_default_plays: o "default" abre e toca (0,1 s de silencio).
audio_default_plays() {
  head -c $((AUDIO_TEE_RATE / 10 * 4)) /dev/zero |
    aplay -q -D default -f S16_LE -r "$AUDIO_TEE_RATE" -c 2 -t raw >> "$FLIPEROS_LOG" 2>&1
}

# audio_stream_off_now MOTIVO: o som da transmissao desligado, o asound.conf
# sem a copia.
audio_stream_off_now() {
  log_error "audio: $1; o som da tela ao vivo fica desligado"
  rm -f "$AUDIO_LOOP_LOAD" "$AUDIO_LOOP_MODPROBE"
  modprobe -r snd-aloop 2> /dev/null
  conf_set stream_audio off
  audio_write_conf
}

# audio_stream_set on|off: o modulo do loopback (agora e nos proximos boots)
# e o asound.conf de novo. Status 1: o loopback nao abriu, ou o "default" com
# a copia nao tocou (o som da transmissao fica desligado, o resto como antes).
audio_stream_set() {
  if [[ $1 == on ]]; then
    printf 'options snd-aloop index=10 id=%s pcm_substreams=1\n' "$AUDIO_LOOP_ID" > "$AUDIO_LOOP_MODPROBE" || return 1
    echo snd-aloop > "$AUDIO_LOOP_LOAD" || return 1
    # O modulo de antes podia estar no timer_source da placa (o que deixava o
    # loopback ocupado): aberto de novo com as opcoes daqui.
    modprobe -r snd-aloop 2> /dev/null
    modprobe snd-aloop >> "$FLIPEROS_LOG" 2>&1
    if ! audio_loop_ready; then
      audio_stream_off_now "o loopback (snd-aloop) nao abriu"
      return 1
    fi
    conf_set stream_audio on
    audio_write_conf
    if ! audio_default_plays; then
      audio_stream_off_now "o default nao tocou com a copia"
      return 1
    fi
  else
    rm -f "$AUDIO_LOOP_LOAD" "$AUDIO_LOOP_MODPROBE"
    conf_set stream_audio off
    audio_write_conf
  fi
  log_info "audio: som da tela ao vivo $1"
}

# audio_stream_check (a cada sessao, antes do frontend ou do jogo): com a copia
# no asound.conf e o loopback fora (o modulo nao subiu neste boot), o
# asound.conf sem ela, para o som nao sumir.
audio_stream_check() {
  grep -q fliperos_tee "$ASOUND_CONF" 2> /dev/null || return 0
  audio_loop_ready && return 0
  log_error "audio: o loopback do som da tela ao vivo nao esta aberto; o asound.conf fica sem a copia"
  audio_write_conf
}

# audio_write_conf grava o /etc/asound.conf: a placa padrao e, com o
# nivelador ligado, o "default" passando pelo compressor antes do dmix da
# placa (o plug converte o formato dos dois lados). O plug do lado da placa
# vai em bloco: escrito "plug:dmix:0,0", o ALSA le o ",0" como um segundo
# argumento do plug, nada abre o default e tudo fica mudo. Com o som da tela
# ao vivo, a saida e o fliperos_tee: o mesmo som no dmix da placa e no do
# loopback (o route copia os 2 canais para os 4 do multi).
audio_write_conf() {
  local current card dev out tee=0
  current=$(audio_current)
  card=${current%,*} dev=${current#*,}
  out="dmix:$card,$dev"
  if audio_stream_enabled && audio_loop_ready; then
    tee=1 out=fliperos_tee
  fi
  {
    echo "# Gerado pelo fliperos-setup (Setup > Audio Setup)."
    echo "defaults.pcm.card $card"
    echo "defaults.ctl.card $card"
    echo "defaults.pcm.device $dev"
    if ((tee)); then
      cat << EOF

# Live screen sound: o som de tudo tambem no loopback que a transmissao grava.
# Os dois dmix iguais (formato, taxa, periodo): o multi so abre assim.
pcm.fliperos_card {
    type dmix
    ipc_key 58201
    ipc_perm 0666
    slave {
        pcm "hw:$card,$dev"
        format S16_LE
        rate $AUDIO_TEE_RATE
        channels 2
        period_size $AUDIO_TEE_PERIOD
        buffer_size $AUDIO_TEE_BUFFER
    }
}
pcm.fliperos_loop {
    type dmix
    ipc_key 58202
    ipc_perm 0666
    slave {
        pcm "hw:$AUDIO_LOOP_ID,0,0"
        format S16_LE
        rate $AUDIO_TEE_RATE
        channels 2
        period_size $AUDIO_TEE_PERIOD
        buffer_size $AUDIO_TEE_BUFFER
    }
}
pcm.fliperos_tee {
    type route
    slave.pcm {
        type multi
        slaves.a { pcm "fliperos_card" channels 2 }
        slaves.b { pcm "fliperos_loop" channels 2 }
        bindings.0 { slave a channel 0 }
        bindings.1 { slave a channel 1 }
        bindings.2 { slave b channel 0 }
        bindings.3 { slave b channel 1 }
    }
    ttable.0.0 1
    ttable.1.1 1
    ttable.0.2 1
    ttable.1.3 1
}
EOF
      audio_leveler_enabled || printf '%s\n' 'pcm.!default {' '    type plug' '    slave.pcm "fliperos_tee"' '}'
    fi
    if audio_leveler_enabled; then
      cat << EOF

# Volume leveler: o compressor SC4 (swh-plugins) no som de tudo.
pcm.!default {
    type plug
    slave.pcm "fliperos_leveler"
}
pcm.fliperos_leveler {
    type ladspa
    slave.pcm {
        type plug
        slave.pcm "$out"
    }
    path "${AUDIO_LEVELER_PLUGIN%/*}"
    plugins [ {
        label sc4
        input { controls [ ${AUDIO_LEVELER_CONTROLS} ] }
    } ]
}
EOF
    fi
  } > "$ASOUND_CONF"
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
# tomada. Tambem get (imprime o volume) e set PORCENTAGEM: o painel web
# (config/fliperos-web).
audio_step() {
  local card control change
  case $1 in
    up) change="$AUDIO_STEP%+ unmute" ;;
    down) change="$AUDIO_STEP%-" ;;
    mute) change="toggle" ;;
    get)
      audio_volume
      return 0
      ;;
    set)
      [[ ${2:-} =~ ^[0-9]{1,3}$ ]] || return 1
      ((10#$2 <= 100)) || return 1
      audio_set_volume "$((10#$2))"
      return 0
      ;;
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

# ── Sons do menu ─────────────────────────────────────────────────
# O gum do FliperOS (patches/gum/0002-sons-do-menu.patch) toca
# GUM_SOUND_MOVE quando o cursor anda e GUM_SOUND_SELECT no Enter. Os sons
# sao da pessoa (o FliperOS nao traz sons de jogo): move.wav e select.wav
# nesta pasta, que na rede e o compartilhamento FliperOS, sounds/menu.
MENU_SOUNDS_DIR=${MENU_SOUNDS_DIR:-/opt/fliperos/sounds/menu}

# menu_sounds_state imprime on, off ou missing (nem move.wav nem select.wav
# na pasta). Com os arquivos la, liga sozinho; o Setup desliga.
menu_sounds_state() {
  if [[ ! -f $MENU_SOUNDS_DIR/move.wav && ! -f $MENU_SOUNDS_DIR/select.wav ]]; then
    echo missing
  elif [[ $(conf_get menu_sounds) == off ]]; then
    echo off
  else
    echo on
  fi
}

# menu_sounds_label imprime o estado para o menu: on, off ou "no sound
# files".
menu_sounds_label() {
  local state
  state=$(menu_sounds_state)
  [[ $state == missing ]] && state="no sound files"
  printf '%s\n' "$state"
}

# menu_sounds_set on|off liga ou desliga os sons do menu.
menu_sounds_set() {
  conf_set menu_sounds "$1"
}

# menu_sounds_env imprime as variaveis do gum dos sons que existem, uma por
# linha (GUM_SOUND_MOVE=...), se os sons estiverem ligados.
menu_sounds_env() {
  [[ $(menu_sounds_state) == on ]] || return 0
  [[ -f $MENU_SOUNDS_DIR/move.wav ]] && echo "GUM_SOUND_MOVE=$MENU_SOUNDS_DIR/move.wav"
  [[ -f $MENU_SOUNDS_DIR/select.wav ]] && echo "GUM_SOUND_SELECT=$MENU_SOUNDS_DIR/select.wav"
  return 0
}
