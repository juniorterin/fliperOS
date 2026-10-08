# shellcheck shell=bash
# Linha do kernel do sistema instalado (Limine).
#
# Os parametros ficam em /etc/default/fliperos-boot (FLIPEROS_CMDLINE), o
# equivalente do /etc/default/grub; o fliperos-limine-update leva kernel,
# initrd e menu para a ESP.

# Base de todo sistema instalado: splash, console sem apagar (o
# consoleblank=0 do GroovyArcade) e o radeon nas placas SI/CIK, que e onde
# o 15 kHz foi validado no gabinete. BOOT_SILENT: boot direto no Plymouth,
# sem mensagens do kernel e do udev nem o cursor piscando antes dele (o
# rd.udev.log-priority=3 do GA, no nome atual).
BOOT_SILENT="loglevel=3 rd.udev.log_level=3 udev.log_level=3 vt.global_cursor_default=0"
BOOT_BASE_CMDLINE="quiet splash $BOOT_SILENT consoleblank=0 radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0"

# boot_driver_params LINHA imprime os parametros de driver de uma linha do
# kernel: a entrada "Intel 15 kHz" do boot leva o i915.no_ytiled_scanout=1,
# sem o qual 480i nao funciona em Intel Gen9, e ele tem de ir junto para o
# sistema instalado.
boot_driver_params() {
  local word out=()
  for word in $1; do
    case $word in
      i915.* | nouveau.*) out+=("$word") ;;
    esac
  done
  printf '%s\n' "${out[*]}"
}

# boot_compose LINHA aplica a uma linha do kernel o que o setup decidiu:
# modo de latencia, quirks do usbhid, modo debug (boot calado ou nao),
# parametros de video do teste de saidas (se houve teste) e dos monitores
# extras, console na placa certa (fbcon=map) e orientacao.
boot_compose() {
  local line=$1 conn video orientation fb word out=() extra
  conn=$(conf_get connector 2> /dev/null) || conn=""
  video=$(conf_get kernel_video 2> /dev/null) || video=""
  orientation=$(conf_get orientation 2> /dev/null) || orientation=horizontal
  fb=$(conf_get fb_map 2> /dev/null) || fb=0
  for word in $line; do
    [[ $word == fbcon=map:* ]] && continue
    out+=("$word")
  done
  line=$(latency_cmdline "${out[*]}")
  line=$(quirks_cmdline "$line")
  line=$(debug_cmdline "$line")
  if [[ -n $conn ]]; then
    line=$(words "$(cmdline_without_video "$line") $video")
    line=$(mm_cmdline "$line")
  fi
  [[ -n $fb && $fb != 0 ]] && line="$line fbcon=map:$fb"
  while IFS= read -r extra; do
    extra=$(mm_entry_name "$extra")
    [[ $extra == "$conn" ]] && continue
    line=$(orientation_cmdline "$line" "$extra" "$orientation")
  done < <(mm_extras | sed 's/^[^:]*://' | sort -u)
  orientation_cmdline "$line" "$conn" "$orientation"
}

# boot_install_cmdline imprime a linha do kernel para um disco novo. Sem
# teste de saidas, valem os parametros de video da entrada de boot
# escolhida no menu da midia.
boot_install_cmdline() {
  local live base
  live=$(< "$PROC_CMDLINE")
  base="$BOOT_BASE_CMDLINE $(boot_driver_params "$live")"
  if ! conf_get connector > /dev/null 2>&1; then
    base="$base $(cmdline_video_params "$live")"
  fi
  boot_compose "$(words "$base")"
}

# boot_read_cmdline [ARQUIVO] imprime o FLIPEROS_CMDLINE gravado.
boot_read_cmdline() {
  local file=${1:-$BOOT_DEFAULTS}
  [[ -f $file ]] || return 1
  sed -n 's/^FLIPEROS_CMDLINE="\(.*\)"$/\1/p' "$file" | head -1
}

# boot_write_cmdline LINHA [ARQUIVO] troca so a linha, mantendo o resto.
boot_write_cmdline() {
  local line=$1 file=${2:-$BOOT_DEFAULTS} tmp
  if [[ ! -f $file ]]; then
    mkdir -p "$(dirname "$file")"
    printf '%s\n' \
      "# Parametros do kernel do FliperOS. Depois de editar a mao:" \
      "#   sudo fliperos-limine-update" \
      "FLIPEROS_CMDLINE=\"$line\"" \
      "FLIPEROS_TIMEOUT=\"3\"" > "$file"
    return
  fi
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk -v l="$line" '
    /^FLIPEROS_CMDLINE=/ { print "FLIPEROS_CMDLINE=\"" l "\""; found = 1; next }
    { print }
    END { if (!found) print "FLIPEROS_CMDLINE=\"" l "\"" }' "$file" > "$tmp" &&
    chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# boot_write_var CHAVE VALOR [ARQUIVO] troca outra variavel do
# /etc/default/fliperos-boot (FLIPEROS_QUIET, FLIPEROS_TIMEOUT).
boot_write_var() {
  local key=$1 value=$2 file=${3:-$BOOT_DEFAULTS} tmp
  [[ -f $file ]] || return 0
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk -v k="$key" -v v="$value" '
    $0 ~ "^" k "=" { print k "=\"" v "\""; found = 1; next }
    { print }
    END { if (!found) print k "=\"" v "\"" }' "$file" > "$tmp" &&
    chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# boot_apply grava no sistema instalado a linha do kernel da configuracao
# atual (modo de boot, EDID, orientacao e latencia) e atualiza o menu do
# Limine.
boot_apply() {
  local line
  line=$(boot_read_cmdline) || line=$BOOT_BASE_CMDLINE
  line=$(boot_compose "$line")
  boot_write_cmdline "$line" || return 1
  log_info "linha do kernel: $line"
  # Um EDID novo (resolucao personalizada) so vale se estiver no initramfs;
  # o hook do initramfs tambem chama o fliperos-limine-update.
  if [[ $(conf_get boot_resolution 2> /dev/null) == custom ]]; then
    run_logged update-initramfs -u -k all
  else
    run_logged "$LIMINE_UPDATE"
  fi
}
