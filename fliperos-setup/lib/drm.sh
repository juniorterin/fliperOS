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

# drm_card_low_dotclock CARD: radeon e amdgpu geram os dotclocks de 15 kHz
# (6 a 15 MHz) sempre (gatools card_supports_low_dot_clock). O nouveau so os
# aceita com o patch 10 do kernel, e cada PLL de NVIDIA tem o seu piso: vale
# para a placa que passou num degrau do grid (low_dotclock_pci no
# fliperos.conf, com o low_dotclock_min do degrau, gravados pelo teste de
# saidas ou pelo Video Setup). As demais precisam de super resolucao.
drm_card_low_dotclock() {
  local pci
  case $(drm_card_driver "$1") in
    radeon | amdgpu) return 0 ;;
    nouveau | nvidia)
      pci=$(drm_card_pci "$1") || return 1
      [[ -n $pci && $(conf_get low_dotclock_pci 2> /dev/null) == "$pci" ]]
      return
      ;;
  esac
  return 1
}

# drm_card_low_dotclock_testable CARD: placa em que o grid de dotclock baixo
# vale a pena: o nouveau. Na Intel o driver nao tem o patch, e o KMS do
# driver da NVIDIA so aceita os modos progressivos do EDID (o Switchres nao
# cria os seus: "Kernel doesn't supports user modes"); nele os modos do jogo
# sao os do Xorg.
drm_card_low_dotclock_testable() {
  [[ $(drm_card_driver "$1") == nouveau ]]
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

# drm_cards lista as placas (card0, card1...), sem os conectores.
drm_cards() {
  local path
  for path in "$DRM_SYSFS"/card[0-9]*; do
    [[ ${path##*/} == *-* || ! -e $path/device ]] && continue
    printf '%s\n' "${path##*/}"
  done | sort -V
}

# drm_card_dual_amd CARD: a placa funciona com o radeon e com o amdgpu. Sao
# as GCN 1.0 e 1.1 (SI e CIK: HD 7000, HD 8000, R7/R9 200 e 300, APUs
# Kaveri e Kabini); as mais antigas so tem o radeon e as mais novas so o
# amdgpu. Quem responde e a tabela de PCI IDs dos proprios modulos: o
# modprobe -R resolve o modalias da placa e lista quem a aceita.
drm_card_dual_amd() {
  local alias mods
  alias=$(cat "$DRM_SYSFS/$1/device/modalias" 2> /dev/null) || return 1
  [[ $alias == pci:v00001002* ]] || return 1
  mods=$'\n'$(modprobe -R "$alias" 2> /dev/null)$'\n'
  [[ $mods == *$'\nradeon\n'* && $mods == *$'\namdgpu\n'* ]]
}

drm_dual_amd_cards() {
  local card
  for card in $(drm_cards); do
    drm_card_dual_amd "$card" && printf '%s\n' "$card"
  done
  return 0
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

# ── O que a placa roda (OpenGL) ──────────────────────────────────
# Uma Intel HD de 1a geracao (Ironlake) so da OpenGL 2.1 e ES 2.0: o que pede
# OpenGL 3 nao abre. O Setup marca esses itens com "(not supported)" (o X
# vermelho da interface grafica) e avisa antes de abri-los.

# gpu_gl_levels imprime "GL ES" da placa principal, lidos do eglinfo do Mesa
# (o maior OpenGL, core ou de compatibilidade, e o OpenGL ES; 0 se nao ha).
# Status 1 se nao da para saber (sem eglinfo, ou o EGL nao abre).
gpu_gl_levels() {
  local eglinfo=${FLIPEROS_EGLINFO:-eglinfo} out core="" compat="" es=""
  command -v "$eglinfo" > /dev/null || return 1
  out=$(timeout 8 "$eglinfo" -B -p gbm 2> /dev/null) || return 1
  [[ $out == *"profile version"* ]] || return 1
  [[ $out =~ OpenGL\ core\ profile\ version:\ ([0-9]+\.[0-9]+) ]] && core=${BASH_REMATCH[1]}
  [[ $out =~ OpenGL\ compatibility\ profile\ version:\ ([0-9]+\.[0-9]+) ]] && compat=${BASH_REMATCH[1]}
  [[ $out =~ OpenGL\ ES\ profile\ version:\ OpenGL\ ES\ ([0-9]+\.[0-9]+) ]] && es=${BASH_REMATCH[1]}
  printf '%s %s\n' "${core:-${compat:-0}}" "${es:-0}"
}

# gpu_needs GL_MINIMO [OU]: a placa nao da o OpenGL minimo. Imprime o motivo
# ("Needs OpenGL 3.3 or Vulkan, and this video card gives OpenGL 2.1 and
# OpenGL ES 2.0") e devolve 0; devolve 1 se da, ou se nao da para saber. OU
# e o que mais serve ("or Vulkan"): uma placa com Vulkan tem OpenGL 4 de
# qualquer jeito.
gpu_needs() {
  local need=$1 alt=${2:-} gl es extra=""
  [[ -n ${GPU_GL_CACHE:-} ]] || GPU_GL_CACHE=$(gpu_gl_levels 2> /dev/null) || GPU_GL_CACHE=unknown
  [[ $GPU_GL_CACHE == unknown ]] && return 1
  read -r gl es <<< "$GPU_GL_CACHE"
  awk -v g="$gl" -v n="$need" 'BEGIN { exit !(g + 0 >= n + 0) }' && return 1
  awk -v e="$es" 'BEGIN { exit !(e + 0 > 0) }' && extra=" and OpenGL ES $es"
  printf 'Needs OpenGL %s%s, and this video card gives OpenGL %s%s\n' "$need" "${alt:+ $alt}" "$gl" "$extra"
}

# gpu_unsupported_label ROTULO MOTIVO imprime o rotulo de um menu com o
# motivo e a marca: "480i hacks (Needs OpenGL 3.0, ...) (not supported)".
gpu_unsupported_label() {
  printf '%s (%s) (not supported)\n' "$1" "$2"
}

# gpu_unsupported_ok TITULO ROTULO MOTIVO: avisa que o item nao roda nesta
# placa e pergunta se abre mesmo assim (o padrao e nao).
gpu_unsupported_ok() {
  ui_yesno "$1" "$2 is not supported on this video card. $3. Open it anyway?" no
}
