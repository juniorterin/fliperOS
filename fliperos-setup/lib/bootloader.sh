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

# ── Driver das placas AMD SI/CIK ─────────────────────────────────
# Placas que os dois drivers aceitam (drm_card_dual_amd) usam o radeon por
# padrao, como no GroovyArcade. amd_driver= no fliperos.conf (Setup > System
# > Video driver, ou a pergunta da instalacao) troca para o amdgpu. So a
# linha do kernel escolhe: o modprobe.d nao repete o si_support/cik_support,
# senao venceria a linha (o modprobe aplica as opcoes dos arquivos depois
# das da linha) e a entrada de volta ao radeon do Limine nao valeria.
AMD_DRIVER_KEYS="radeon.si_support radeon.cik_support amdgpu.si_support amdgpu.cik_support amdgpu.dc"
AMD_MODPROBE_CONF=${AMD_MODPROBE_CONF:-/etc/modprobe.d/fliperos.conf}

amd_driver() {
  local driver
  driver=$(conf_get amd_driver 2> /dev/null) || driver=radeon
  [[ $driver == amdgpu ]] || driver=radeon
  printf '%s\n' "$driver"
}

# amd_driver_recommended: o radeon, com que o 15 kHz foi validado no CRT.
amd_driver_recommended() {
  echo radeon
}

# amd_driver_mismatch imprime "PLACA|DRIVER EM USO|RECOMENDADO" quando uma
# placa que aceita os dois drivers roda com o que nao e o recomendado.
amd_driver_mismatch() {
  local card running recommended
  recommended=$(amd_driver_recommended)
  for card in $(drm_dual_amd_cards); do
    running=$(drm_card_driver "$card") || continue
    [[ $running == "$recommended" ]] && continue
    printf '%s|%s|%s\n' "$card" "$running" "$recommended"
    return 0
  done
  return 1
}

# amd_driver_params DRIVER. No amdgpu vai o amdgpu.dc=0: o kernel 6.18 nao
# tem saida analogica (VGA, DVI-I) no codigo de video novo (DC) das GCN 1.0
# e 1.1, que so chegou no 6.19; o antigo tem, e e nele que o patch de PLL
# do kernel 15 kHz (05_linux_15khz_amdgpu_pll_fix) atua.
amd_driver_params() {
  case $1 in
    amdgpu) echo "radeon.si_support=0 radeon.cik_support=0 amdgpu.si_support=1 amdgpu.cik_support=1 amdgpu.dc=0" ;;
    *) echo "radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0" ;;
  esac
}

# amd_driver_cmdline LINHA troca os parametros de driver pelos do
# fliperos.conf. Sem amd_driver gravado a linha fica como esta.
amd_driver_cmdline() {
  local line=$1 driver key
  driver=$(conf_get amd_driver 2> /dev/null) || { printf '%s\n' "$line"; return 0; }
  for key in $AMD_DRIVER_KEYS; do
    line=$(cmdline_remove "$line" "$key")
  done
  words "$line $(amd_driver_params "$driver")"
}

# amd_driver_modprobe_clean [RAIZ] tira o si_support/cik_support que o
# fliperos.conf do modprobe.d das imagens antigas (ver AMD_DRIVER_KEYS); o
# resto das opcoes (dpm=1, som) fica.
amd_driver_modprobe_clean() {
  local file=${1:-}$AMD_MODPROBE_CONF tmp
  [[ -f $file ]] || return 0
  grep -Eq '^options (radeon|amdgpu) .*(si|cik)_support=' "$file" || return 0
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk '
    $1 == "options" && ($2 == "radeon" || $2 == "amdgpu") {
      out = "options " $2
      for (i = 3; i <= NF; i++) if ($i !~ /^(si|cik)_support=/) out = out " " $i
      if (out != "options " $2) print out
      next
    }
    { print }' "$file" > "$tmp" && chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# amd_driver_apply DRIVER grava a escolha. A linha do kernel e o initramfs
# (que leva o modprobe.d) ficam com o boot_apply, so no sistema instalado.
amd_driver_apply() {
  conf_set amd_driver "$1" || return 1
  amd_driver_modprobe_clean || return 1
  BOOT_INITRAMFS=1
  log_info "driver AMD: $1"
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
  line=$(amd_driver_cmdline "$line")
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
  # Um EDID novo (resolucao personalizada) e o modprobe.d de um driver AMD
  # trocado so valem se estiverem no initramfs; o hook do initramfs tambem
  # chama o fliperos-limine-update.
  if [[ $(conf_get boot_resolution 2> /dev/null) == custom ]] || ((${BOOT_INITRAMFS:-0})); then
    run_logged update-initramfs -u -k all
  else
    run_logged "$LIMINE_UPDATE"
  fi
}
