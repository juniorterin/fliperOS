# shellcheck shell=bash
# Caminhos, log e deteccao do ambiente (midia live ou sistema instalado).
#
# Todo caminho de sistema passa por uma variavel sobrescrevivel: os testes
# apontam para arvores falsas (sysfs, /etc) em vez do sistema real.

# O sistema e pt_BR, mas os numeros que o setup le e escreve (kHz, Hz,
# tamanhos) usam ponto: sem isto o printf '%.2f' do bash recusa "59.98".
export LC_NUMERIC=C

FLIPEROS_ETC=${FLIPEROS_ETC:-/etc/fliperos}
FLIPEROS_CONF=${FLIPEROS_CONF:-$FLIPEROS_ETC/fliperos.conf}
FLIPEROS_LOG=${FLIPEROS_LOG:-/var/log/fliperos-setup.log}
FLIPEROS_USER=${FLIPEROS_USER:-fliperos}
DRM_SYSFS=${DRM_SYSFS:-/sys/class/drm}
PROC_CMDLINE=${PROC_CMDLINE:-/proc/cmdline}
LIVE_IMAGE=${LIVE_IMAGE:-/run/live/medium/live/filesystem.squashfs}
SWITCHRES_INI=${SWITCHRES_INI:-/etc/switchres.ini}
MAME_INI=${MAME_INI:-$FLIPEROS_ETC/mame/mame.ini}
XORG_CONF=${XORG_CONF:-/etc/X11/xorg.conf.d/10-fliperos.conf}
BOOT_DEFAULTS=${BOOT_DEFAULTS:-/etc/default/fliperos-boot}
LIMINE_UPDATE=${LIMINE_UPDATE:-/usr/local/sbin/fliperos-limine-update}
VIDEO_CHECK=${VIDEO_CHECK:-/usr/local/bin/fliperos-video-check}
SESSIONS_TABLE=${SESSIONS_TABLE:-$FLIPEROS_ETC/sessions.conf}
SESSION_FILE=${SESSION_FILE:-$FLIPEROS_ETC/session}
EDID_DIR=${EDID_DIR:-/lib/firmware/edid}

log_line() {
  local level=$1
  shift
  mkdir -p "$(dirname "$FLIPEROS_LOG")" 2>/dev/null
  printf '%s [%s] %s\n' "$(date '+%F %T')" "$level" "$*" >> "$FLIPEROS_LOG" 2>/dev/null
  return 0
}

log_info()  { log_line info "$@"; }
log_warn()  { log_line warn "$@"; }
log_error() { log_line error "$@"; }

# run_logged roda o comando mandando a saida para o log; devolve o status.
run_logged() {
  log_line cmd "\$ $*"
  "$@" >> "$FLIPEROS_LOG" 2>&1
  local rc=$?
  ((rc)) && log_line cmd "  -> saiu com $rc"
  return "$rc"
}

# is_live diz se o sistema atual e a midia de instalacao.
is_live() {
  local word
  for word in $(< "$PROC_CMDLINE"); do
    [[ $word == boot=live ]] && return 0
  done
  return 1
}

is_installed() {
  [[ -f $FLIPEROS_ETC/installed ]]
}

# boot_profile e a entrada escolhida no menu do Limine (fliperos.boot=15khz,
# ntsc, edid-interlaced...). Vazia no sistema instalado.
boot_profile() {
  local word
  for word in $(< "$PROC_CMDLINE"); do
    if [[ $word == fliperos.boot=* ]]; then
      printf '%s\n' "${word#fliperos.boot=}"
      return 0
    fi
  done
  return 1
}

# human_size formata bytes como o usuario le na etiqueta do disco (GB).
human_size() {
  local bytes=$1
  if ((bytes >= 1000000000000)); then
    awk -v b="$bytes" 'BEGIN { printf "%.1f TB\n", b / 1e12 }'
  elif ((bytes >= 1000000000)); then
    awk -v b="$bytes" 'BEGIN { printf "%.0f GB\n", b / 1e9 }'
  else
    awk -v b="$bytes" 'BEGIN { printf "%.0f MB\n", b / 1e6 }'
  fi
}

# words junta as palavras de uma linha com um espaco so, sem sobras nas
# pontas (a linha do kernel e montada por pedacos).
words() {
  local -a w
  read -r -a w <<< "$*"
  printf '%s\n' "${w[*]}"
}

# have diz se o programa existe.
have() {
  command -v "$1" > /dev/null 2>&1
}
