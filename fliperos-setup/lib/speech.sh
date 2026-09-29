# shellcheck shell=bash
# Narracao com espeak-ng, como o log_and_tell do gatools: no teste de saidas
# a tela pode estar escura, e a voz e o que diz o que esta acontecendo.

SPEECH_VOICE=${SPEECH_VOICE:-en-us}
SPEECH_PID=""

speech_available() {
  have espeak-ng && [[ ${FLIPEROS_NO_SPEECH:-0} != 1 ]]
}

# speak TEXTO fala sem bloquear; uma fala nova interrompe a anterior.
speak() {
  speech_available || return 0
  speak_stop
  espeak-ng -v "$SPEECH_VOICE" -s 150 "$*" > /dev/null 2>&1 &
  SPEECH_PID=$!
  log_info "voz: $*"
}

# speak_wait TEXTO fala e espera terminar.
speak_wait() {
  speech_available || return 0
  speak_stop
  log_info "voz: $*"
  espeak-ng -v "$SPEECH_VOICE" -s 150 "$*" > /dev/null 2>&1
}

speak_stop() {
  if [[ -n $SPEECH_PID ]]; then
    kill "$SPEECH_PID" 2> /dev/null
    wait "$SPEECH_PID" 2> /dev/null
    SPEECH_PID=""
  fi
  return 0
}
