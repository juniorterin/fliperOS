# shellcheck shell=bash
# Conectores DRM e placas de video, via sysfs. O teste de saidas do
# GroovyArcade (gatools video.sh) liga e desliga as saidas escrevendo em
# /sys/class/drm/cardN-CONECTOR/status: "on" forca ligada, "off" forca
# desligada e "detect" devolve ao automatico.

# drm_connectors lista as entradas cardN-CONECTOR, ordenadas por placa e
# nome. Writeback nao e saida de tela.
drm_connectors() {
  local path name
  for path in "$DRM_SYSFS"/card[0-9]*-*; do
    [[ -e $path/status ]] || continue
    name=${path##*/}
    [[ $name == *-Writeback-* ]] && continue
    printf '%s\n' "$name"
  done | sort -V
}

# drm_name card0-VGA-1 -> VGA-1
drm_name() {
  printf '%s\n' "${1#card*-}"
}

# drm_card card0-VGA-1 -> card0
drm_card() {
  printf '%s\n' "${1%%-*}"
}

drm_status() {
  local f=$DRM_SYSFS/$1/status s=unknown
  [[ -r $f ]] && s=$(< "$f")
  printf '%s\n' "$s"
}

drm_set_status() {
  log_info "drm: $1 status <- $2"
  printf '%s' "$2" > "$DRM_SYSFS/$1/status" 2>/dev/null
}

drm_edid_file() {
  printf '%s\n' "$DRM_SYSFS/$1/edid"
}

drm_edid_size() {
  local f=$DRM_SYSFS/$1/edid
  if [[ -f $f ]]; then
    wc -c < "$f" | tr -d ' '
  else
    echo 0
  fi
}

# drm_is_analog NOME: so as saidas analogicas sao forcadas a ligar; digital
# sem monitor nao tem o que mostrar (mesma regra do gatools).
drm_is_analog() {
  case $1 in
    VGA-* | DVI-I-* | DVI-A-*) return 0 ;;
  esac
  return 1
}

# drm_modes CONECTOR lista os modos que o kernel aceita na saida.
drm_modes() {
  cat "$DRM_SYSFS/$1/modes" 2>/dev/null
}

# drm_has_interlace CONECTOR diz se a saida tem modo entrelacado na lista
# (o kernel 15 kHz poe o modo da linha de comando, ex. 640x480i).
drm_has_interlace() {
  drm_modes "$1" | grep -q 'i$'
}

drm_card_driver() {
  local link
  link=$(readlink -f "$DRM_SYSFS/$1/device/driver" 2>/dev/null) || return 1
  [[ -n $link ]] || return 1
  printf '%s\n' "${link##*/}"
}

drm_card_pci() {
  local link
  link=$(readlink -f "$DRM_SYSFS/$1/device" 2>/dev/null) || return 1
  printf '%s\n' "${link##*/}"
}

# drm_card_name CARD imprime o nome curto da GPU, como o short_gpu_name do
# gatools ("Radeon HD 5450" em vez da linha inteira do lspci). A linha do
# "lspci -mm" e: 01:00.0 "classe" "fabricante" "dispositivo" -rREV
# "fabricante da placa" "placa" — o slot sem aspas, entao, separando por
# aspas, o fabricante e o 4o campo e o dispositivo o 6o.
drm_card_name() {
  local pci line vendor device
  pci=$(drm_card_pci "$1") || { echo "Unknown GPU"; return; }
  line=$(lspci -mms "$pci" 2>/dev/null)
  vendor=$(awk -F'"' '{print $4}' <<< "$line")
  device=$(awk -F'"' '{print $6}' <<< "$line")
  gpu_short_name "$vendor" "$device"
}

# gpu_short_name FABRICANTE DISPOSITIVO (campos do lspci -mm).
gpu_short_name() {
  local vendor=$1 device=$2 inner
  case $vendor in
    "Advanced Micro Devices"* | ATI* | "AMD"*)
      # Cedar [Radeon HD 5000/6000/7350/8350 Series] -> Radeon HD 5000/...
      if [[ $device =~ \[([^]]+)\] ]]; then
        inner=${BASH_REMATCH[1]}
        printf 'AMD %s\n' "$inner"
      else
        printf 'AMD %s\n' "$device"
      fi
      ;;
    NVIDIA*)
      if [[ $device =~ \[([^]]+)\] ]]; then
        printf 'NVIDIA %s\n' "${BASH_REMATCH[1]}"
      else
        printf 'NVIDIA %s\n' "$device"
      fi
      ;;
    Intel*) printf 'Intel %s\n' "$device" ;;
    "") echo "Unknown GPU" ;;
    *) printf '%s %s\n' "$vendor" "$device" ;;
  esac
}

# drm_card_low_dotclock CARD: so radeon e amdgpu geram os dotclocks de 15 kHz
# (6 a 15 MHz). As demais precisam de super resolucao (gatools
# card_supports_low_dot_clock).
drm_card_low_dotclock() {
  case $(drm_card_driver "$1") in
    radeon | amdgpu) return 0 ;;
  esac
  return 1
}

# drm_card_is_apu CARD usa o mesmo sinal do gatools: o lspci -v mostra
# "Onboard IGD" para a GPU integrada.
drm_card_is_apu() {
  local pci
  pci=$(drm_card_pci "$1") || return 1
  lspci -vs "$pci" 2>/dev/null | grep -q "Onboard IGD"
}

# drm_card_fb CARD imprime o numero do framebuffer da placa (fbN).
drm_card_fb() {
  local fb
  for fb in "$DRM_SYSFS/$1"/device/graphics/fb[0-9]*; do
    [[ -e $fb ]] || continue
    printf '%s\n' "${fb##*/fb}"
    return 0
  done
  return 1
}

# ── EDID ─────────────────────────────────────────────────────────
# Os descritores de 18 bytes ficam em 54, 72, 90 e 108. Descritor de texto:
# tres zeros, o tipo no quarto byte (0xFF numero de serie, 0xFC nome) e o
# texto do sexto byte em diante, terminado por 0x0A. O Switchres grava
# "Switchres200" no numero de serie e o preset do monitor no nome.

_edid_text() {
  local file=$1 tag=$2 bytes off i c text
  [[ -s $file ]] || return 1
  read -r -a bytes <<< "$(od -An -v -tu1 -N128 "$file" | tr -s ' \n' ' ')"
  ((${#bytes[@]} >= 128)) || return 1
  for off in 54 72 90 108; do
    if ((bytes[off] == 0 && bytes[off + 1] == 0 && bytes[off + 2] == 0 && bytes[off + 3] == tag)); then
      text=""
      for ((i = off + 5; i < off + 18; i++)); do
        c=${bytes[i]}
        ((c == 10 || c == 0)) && break
        local ch
        printf -v ch '%b' "\\$(printf '%03o' "$c")"
        text+=$ch
      done
      printf '%s\n' "${text%"${text##*[![:space:]]}"}"
      return 0
    fi
  done
  return 1
}

edid_serial_text() { _edid_text "$1" 255; }
edid_monitor_name() { _edid_text "$1" 252; }

edid_is_switchres() {
  local serial
  serial=$(edid_serial_text "$1") || return 1
  [[ $serial == *Switchres* ]]
}
