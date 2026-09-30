# shellcheck shell=bash
# Modos de latencia (Setup > Latency). Documentado no README, secao
# "Latencia".
#
# standard (padrao, qualquer maquina) e o que o GroovyArcade ja faz, mais o
# polling de 1 ms do USB:
#   - kernel com mitigations=off audit=0 (a linha padrao do GA) e
#     usbhid.jspoll/kbpoll/mousepoll=1 (controle lido a 1000 Hz, nao 125 Hz);
#   - CPU no governador "performance" enquanto o frontend ou o emulador
#     roda, e de volta ao anterior quando fecha (cpu_governor.sh do galauncher);
#   - GroovyMAME com lowlatency, autoframedelay e framedelay 0 (automatico);
#   - RetroArch com 2 imagens na swapchain (espera o flip no KMS), video sem
#     thread e leitura dos controles o mais tarde possivel.
#
# low (CPUs modernas) acrescenta:
#   - preempt=full: o kernel 6.18 e PREEMPT_DYNAMIC; com isto ele vira o que
#     era o kernel lowlatency do Ubuntu, sem trocar de kernel;
#   - CPU em "performance" o tempo todo, desde o boot;
#   - RetroArch com frame delay automatico e preemptive frames (1 quadro):
#     tira o atraso interno do jogo, rodando de novo o ultimo quadro quando a
#     entrada muda. Gasta CPU a cada quadro, por isso a recomendacao de
#     hardware (lib/hardware.sh).

LATENCY_BASE_PARAMS="mitigations=off audit=0 usbhid.jspoll=1 usbhid.kbpoll=1 usbhid.mousepoll=1"
LATENCY_LOW_PARAMS="preempt=full"
# Parametros que o modo controla: saem da linha antes de o modo atual
# entrar de novo (trocar de low para standard tira o preempt=full).
LATENCY_KEYS="mitigations audit usbhid.jspoll usbhid.kbpoll usbhid.mousepoll preempt"

latency_mode() {
  local mode
  mode=$(conf_get latency 2> /dev/null) || mode=standard
  [[ $mode == low ]] || mode=standard
  printf '%s\n' "$mode"
}

latency_label() {
  case $1 in
    low) echo "Low latency" ;;
    *) echo "Standard" ;;
  esac
}

# latency_params MODO imprime os parametros do kernel do modo. Com
# usb_poll=default no fliperos.conf fica o polling original do USB (para
# um controle que se comporte mal lido a 1000 Hz).
latency_params() {
  local word out=()
  for word in $LATENCY_BASE_PARAMS; do
    [[ $word == usbhid.* && $(conf_get usb_poll 2> /dev/null) == default ]] && continue
    out+=("$word")
  done
  if [[ $1 == low ]]; then
    for word in $LATENCY_LOW_PARAMS; do out+=("$word"); done
  fi
  printf '%s\n' "${out[*]}"
}

# latency_cmdline LINHA [MODO] troca na linha do kernel os parametros de
# latencia pelos do modo (o gravado, se nao vier).
latency_cmdline() {
  local line=$1 mode=${2:-$(latency_mode)} key
  for key in $LATENCY_KEYS; do
    line=$(cmdline_remove "$line" "$key")
  done
  words "$line $(latency_params "$mode")"
}

# latency_emulators MODO grava as chaves de latencia do RetroArch e do
# GroovyMAME. As do modo standard sao as mesmas de config/retroarch.cfg e
# config/mame.ini.
latency_emulators() {
  local mode=$1 on=false
  [[ $mode == low ]] && on=true
  rcfg_set "$RETROARCH_CFG" video_max_swapchain_images 2
  rcfg_set "$RETROARCH_CFG" video_threaded false
  rcfg_set "$RETROARCH_CFG" input_poll_type_behavior 2
  rcfg_set "$RETROARCH_CFG" video_frame_delay 0
  rcfg_set "$RETROARCH_CFG" video_frame_delay_auto "$on"
  rcfg_set "$RETROARCH_CFG" run_ahead_enabled false
  rcfg_set "$RETROARCH_CFG" run_ahead_frames 1
  rcfg_set "$RETROARCH_CFG" preemptive_frames_enable "$on"
  if [[ -f $MAME_INI ]]; then
    ini_set "$MAME_INI" lowlatency 1
    ini_set "$MAME_INI" autoframedelay 1
    ini_set "$MAME_INI" framedelay 0
  fi
}

# ── Governador da CPU ────────────────────────────────────────────
# Escrito direto no sysfs (o cpupower do Ubuntu depende do pacote
# linux-tools do kernel, que o kernel 15 kHz nao tem).

latency_governor_files() {
  local f
  for f in "$CPU_SYSFS"/cpufreq/policy*/scaling_governor; do
    [[ -f $f ]] && printf '%s\n' "$f"
  done
}

latency_governor() {
  local f
  f=$(latency_governor_files | head -1)
  [[ -n $f ]] || return 1
  tr -d '[:space:]' < "$f"
  printf '\n'
}

# latency_set_governor NOME troca todas as politicas que aceitam o nome.
latency_set_governor() {
  local f available
  while IFS= read -r f; do
    available=" $(cat "${f%/*}/scaling_available_governors" 2> /dev/null) "
    [[ $available == *" $1 "* ]] || continue
    printf '%s' "$1" > "$f" 2> /dev/null || log_warn "governador $1 recusado em $f"
  done < <(latency_governor_files)
  return 0
}

# latency_default_governor e o do boot deste kernel: schedutil (acpi-cpufreq)
# ou powersave (intel_pstate/amd-pstate ativos, que ajustam sozinhos).
latency_default_governor() {
  local f available
  f=$(latency_governor_files | head -1)
  [[ -n $f ]] || return 1
  available=" $(cat "${f%/*}/scaling_available_governors" 2> /dev/null) "
  if [[ $available == *" schedutil "* ]]; then
    echo schedutil
  else
    echo powersave
  fi
}

# latency_session_start: antes do frontend/emulador. Guarda o governador
# atual (so o primeiro, se sessoes se aninharem) e liga o performance.
latency_session_start() {
  local current
  current=$(latency_governor) || return 0
  if [[ ! -f $LATENCY_STATE ]]; then
    mkdir -p "$(dirname "$LATENCY_STATE")"
    printf '%s\n' "$current" > "$LATENCY_STATE"
  fi
  latency_set_governor performance
}

# latency_session_end: devolve o governador guardado, exceto no modo low,
# em que a CPU fica em performance o tempo todo.
latency_session_end() {
  local saved
  [[ -f $LATENCY_STATE ]] || return 0
  saved=$(< "$LATENCY_STATE")
  rm -f "$LATENCY_STATE"
  [[ $(latency_mode) == low ]] && return 0
  [[ -n $saved ]] && latency_set_governor "$saved"
  return 0
}

# latency_boot: no boot (fliperos-latency.service), o modo low ja liga o
# performance.
latency_boot() {
  [[ $(latency_mode) == low ]] || return 0
  latency_set_governor performance
}

# latency_apply MODO grava o modo e aplica o que vale na hora (emuladores e
# CPU). A linha do kernel fica com quem chama (boot_apply), porque so vale
# no sistema instalado e depois de reiniciar.
latency_apply() {
  local mode=$1 gov
  conf_set latency "$mode"
  latency_emulators "$mode" || return 1
  if [[ $mode == low ]]; then
    latency_set_governor performance
  elif gov=$(latency_default_governor); then
    latency_set_governor "$gov"
  fi
  log_info "latencia: modo $mode"
}
