# shellcheck shell=bash
# O que a maquina tem (CPU, memoria, GPU) e se ela esta dentro da
# recomendacao do modo de baixa latencia (Setup > Latency).
#
# A recomendacao e a mesma do README ("Latencia"): o modo de baixa latencia
# liga o frame delay automatico e os preemptive frames do RetroArch, que
# gastam CPU a cada quadro. O que conta e a CPU; a GPU pesa pouco nas
# resolucoes de um CRT.

# Minimos do modo de baixa latencia. O nivel e o x86-64-v3 (AVX2, FMA,
# BMI2): Intel Core de 4a geracao (Haswell, 2013) ou AMD Ryzen em diante.
HW_LOW_MIN_LEVEL=3
HW_LOW_MIN_THREADS=4
HW_LOW_MIN_MHZ=3000
# MemTotal de um PC com 4 GB fica abaixo de 4096 MB (memoria reservada).
HW_LOW_MIN_RAM_MB=3500

hw_cpu_model() {
  local model
  model=$(awk -F': *' '/^model name/ { print $2; exit }' "$PROC_CPUINFO" 2> /dev/null)
  model=$(words "$model")
  printf '%s\n' "${model:-Unknown CPU}"
}

hw_cpu_threads() {
  local n
  n=$(grep -c '^processor' "$PROC_CPUINFO" 2> /dev/null)
  ((n > 0)) || n=1
  printf '%s\n' "$n"
}

# hw_cpu_cores conta os nucleos fisicos (pares physical id/core id); sem
# essas linhas (VM), vale o numero de threads.
hw_cpu_cores() {
  local n
  n=$(awk -F': *' '
    /^physical id/ { p = $2 }
    /^core id/ { seen[p "/" $2] = 1 }
    END { n = 0; for (k in seen) n++; print n }' "$PROC_CPUINFO" 2> /dev/null)
  ((n > 0)) || n=$(hw_cpu_threads)
  printf '%s\n' "$n"
}

# hw_cpu_max_mhz imprime o clock maximo (turbo incluido) em MHz, ou 0 se a
# maquina nao diz (VM sem cpufreq).
hw_cpu_max_mhz() {
  local khz mhz
  if [[ -r $CPU_SYSFS/cpu0/cpufreq/cpuinfo_max_freq ]]; then
    khz=$(< "$CPU_SYSFS/cpu0/cpufreq/cpuinfo_max_freq")
    if [[ $khz =~ ^[0-9]+$ ]] && ((khz > 0)); then
      printf '%s\n' $((khz / 1000))
      return 0
    fi
  fi
  mhz=$(awk -F': *' '/^cpu MHz/ { v = int($2); if (v > m) m = v } END { print m + 0 }' "$PROC_CPUINFO" 2> /dev/null)
  printf '%s\n' "${mhz:-0}"
}

# hw_cpu_level imprime o nivel x86-64 (1 a 4) pelas flags da CPU, como o
# glibc classifica: v2 = SSE4.2/POPCNT, v3 = AVX2/FMA/BMI2, v4 = AVX-512.
hw_cpu_level() {
  local flags f level=1
  flags=" $(awk -F': *' '/^flags/ { print $2; exit }' "$PROC_CPUINFO" 2> /dev/null) "
  for f in cx16 lahf_lm popcnt sse4_1 sse4_2 ssse3; do
    [[ $flags == *" $f "* ]] || { printf '%s\n' "$level"; return 0; }
  done
  level=2
  for f in avx avx2 bmi1 bmi2 f16c fma abm movbe xsave; do
    [[ $flags == *" $f "* ]] || { printf '%s\n' "$level"; return 0; }
  done
  level=3
  for f in avx512f avx512bw avx512cd avx512dq avx512vl; do
    [[ $flags == *" $f "* ]] || { printf '%s\n' "$level"; return 0; }
  done
  printf '4\n'
}

hw_level_label() {
  case $1 in
    4) echo "x86-64-v4 (AVX-512)" ;;
    3) echo "x86-64-v3 (AVX2)" ;;
    2) echo "x86-64-v2 (SSE4.2)" ;;
    *) echo "x86-64 (no AVX2)" ;;
  esac
}

hw_ram_mb() {
  local kb
  kb=$(awk '/^MemTotal:/ { print $2; exit }' "$PROC_MEMINFO" 2> /dev/null)
  [[ $kb =~ ^[0-9]+$ ]] || kb=0
  printf '%s\n' $((kb / 1024))
}

# hw_mhz_label 4200 -> "4.2 GHz"; 0 -> "unknown".
hw_mhz_label() {
  if (($1 > 0)); then
    awk -v m="$1" 'BEGIN { printf "%.1f GHz\n", m / 1000 }'
  else
    echo "unknown"
  fi
}

# hw_ram_label 15890 -> "16 GB" (arredonda como a etiqueta do pente).
hw_ram_label() {
  awk -v m="$1" 'BEGIN { printf "%d GB\n", int((m + 700) / 1024) }'
}

# hw_cards lista as placas de video (card0, card1...).
hw_cards() {
  local path name
  for path in "$DRM_SYSFS"/card[0-9]*; do
    name=${path##*/}
    [[ $name =~ ^card[0-9]+$ ]] && printf '%s\n' "$name"
  done | sort -V
}

# hw_gpu imprime "nome (driver)" da placa do teste de saidas, ou da primeira.
hw_gpu() {
  local card
  card=$(conf_get card 2> /dev/null) || card=$(hw_cards | head -1)
  if [[ -z $card ]]; then
    echo "No GPU found"
    return 0
  fi
  printf '%s (%s)\n' "$(drm_card_name "$card")" "$(drm_card_driver "$card" || echo "no driver")"
}

# hw_analog_outputs lista as saidas analogicas (VGA, DVI-I), que ligam o CRT
# sem conversor.
hw_analog_outputs() {
  local conn out=()
  while IFS= read -r conn; do
    drm_is_analog "$(drm_name "$conn")" && out+=("$(drm_name "$conn")")
  done < <(drm_connectors)
  local IFS=,
  printf '%s\n' "${out[*]}"
}

# hw_low_latency_check imprime uma linha por requisito do modo de baixa
# latencia: "ok|rotulo|a maquina tem|o minimo" ou "low|...". Clock
# desconhecido (VM) nao reprova.
hw_low_latency_check() {
  local level threads mhz ram
  level=$(hw_cpu_level)
  threads=$(hw_cpu_threads)
  mhz=$(hw_cpu_max_mhz)
  ram=$(hw_ram_mb)
  _hw_row $((level >= HW_LOW_MIN_LEVEL)) "CPU instructions" \
    "$(hw_level_label "$level")" "$(hw_level_label "$HW_LOW_MIN_LEVEL")"
  _hw_row $((threads >= HW_LOW_MIN_THREADS)) "CPU threads" "$threads" "$HW_LOW_MIN_THREADS or more"
  _hw_row $((mhz == 0 || mhz >= HW_LOW_MIN_MHZ)) "Max clock" \
    "$(hw_mhz_label "$mhz")" "$(hw_mhz_label "$HW_LOW_MIN_MHZ") or more"
  _hw_row $((ram >= HW_LOW_MIN_RAM_MB)) "Memory" "$(hw_ram_label "$ram")" "4 GB or more"
}

# _hw_row PASSOU ROTULO TEM MINIMO (PASSOU = 1 ou 0).
_hw_row() {
  local mark=low
  (($1)) && mark=ok
  printf '%s|%s|%s|%s\n' "$mark" "$2" "$3" "$4"
}

# hw_low_latency_ok: status 0 quando a maquina cumpre todos os requisitos.
# A saida e lida inteira: com pipefail, um "grep -q" no pipe fecha a entrada
# no primeiro achado, o produtor leva SIGPIPE e o resultado se inverte.
hw_low_latency_ok() {
  local rows
  rows=$'\n'$(hw_low_latency_check)
  [[ $rows != *$'\n'low\|* ]]
}

# hw_low_latency_missing imprime o que falta, numa linha ("CPU threads: 2,
# need 4 or more; ...").
hw_low_latency_missing() {
  hw_low_latency_check | awk -F'|' '$1 == "low" { printf "%s%s: %s, need %s", sep, $2, $3, $4; sep = "; " } END { print "" }'
}
