# shellcheck shell=bash
# Presets de monitor e modos de boot, portados do gatools do GroovyArcade
# (video/monitor.sh). Os ids sao os presets do Switchres; para cada um o
# build gera /lib/firmware/edid/<id>.bin (ver fliperos-rebuild-edids).

# Mesma lista e mesma ordem do menu_select_monitor do gatools.
MONITOR_PRESETS=(
  "generic_15|Generic 15.7 kHz"
  "h9110|Hantarex MTC 9110"
  "polo|Hantarex Polo"
  "pstar|Hantarex Polostar 25"
  "m2929|Makvision 2929D"
  "ntsc|NTSC TV - 60 Hz/525 15.734 kHz (60 Hz only)"
  "pal|PAL TV - 50 Hz/625 15.625 kHz (50 Hz only)"
  "d9200|Wells Gardner D9200"
  "d9400|Wells Gardner D9400"
  "d9800|Wells Gardner D9800"
  "k7000|Wells Gardner K7000"
  "k7131|Wells Gardner 25K7131"
  "m3129|Wei-Ya M3129"
  "ms2930|Nanao MS-2930, MS-2931"
  "ms929|Nanao MS9-29"
  "arcade_15|Arcade 15.7 kHz - standard resolution"
  "arcade_15ex|Arcade 15.7-16.5 kHz - extended resolution"
  "arcade_25|Arcade 25.0 kHz - medium resolution"
  "arcade_31|Arcade 31.5 kHz - high resolution"
  "arcade_15_25|Arcade 15.7/25.0 kHz - dual-sync"
  "arcade_15_25_31|Arcade 15.7/25.0/31.5 kHz - tri-sync"
  "r666b|Rodotron 666B-29"
  "pc_31_120|PC CRT 31 kHz/120 Hz"
  "pc_70_120|PC CRT 70 kHz/120 Hz"
  "vesa_480|VESA GTF 640 x 480"
  "vesa_600|VESA GTF 800 x 600"
  "vesa_768|VESA GTF 1024 x 768"
  "vesa_1024|VESA GTF 1280 x 1024"
  "lcd|LCD"
)

MONITORS_15K=" generic_15 arcade_15 arcade_15ex k7000 k7131 h9110 polo "
MONITORS_25K=" arcade_25 arcade_15_25 ms929 "
MONITORS_31K=" arcade_31 arcade_15_31 arcade_15_25_31 m2929 d9200 d9400 d9800 m3129 pstar ms2930 r666b pc_31_120 vesa_480 "

monitor_label() {
  local entry
  for entry in "${MONITOR_PRESETS[@]}"; do
    if [[ ${entry%%|*} == "$1" ]]; then
      printf '%s\n' "${entry#*|}"
      return 0
    fi
  done
  printf '%s\n' "$1"
  return 1
}

monitor_known() {
  local entry
  for entry in "${MONITOR_PRESETS[@]}"; do
    [[ ${entry%%|*} == "$1" ]] && return 0
  done
  return 1
}

# monitor_frequency MONITOR imprime 15k, 25k ou 31k (vazio para LCD/VESA).
# E a monitor_type do gatools, que tambem poe NTSC e PAL em 15k.
monitor_frequency() {
  local m=$1
  if [[ $MONITORS_15K == *" $m "* || $m == pal || $m == ntsc ]]; then
    echo 15k
  elif [[ $MONITORS_25K == *" $m "* ]]; then
    echo 25k
  elif [[ $MONITORS_31K == *" $m "* ]]; then
    echo 31k
  else
    return 1
  fi
}

# monitor_kernel_resolution MONITOR [REFRESH] [p|i] [super] imprime o modo de
# boot no formato do kernel 15 kHz ("640x480iS": i = entrelacado, S = tabela
# de baixo dotclock do patch). E a monitor_to_kernel_resolution do gatools.
# "super" pede super resolucao, para placa que nao gera dotclock baixo.
# Status 1 para LCD (vale o EDID do proprio monitor), 2 para desconhecido.
monitor_kernel_resolution() {
  local m=$1 vfreq=${2:-60} frame=${3:-p} super=${4:-}
  if [[ $MONITORS_15K == *" $m "* ]]; then
    if [[ -n $super ]]; then
      echo 1280x480iS
      return 0
    fi
    _res_15k "$vfreq" "$frame"
  elif [[ $m == pal ]]; then
    _res_15k 50 "$frame"
  elif [[ $m == ntsc ]]; then
    echo 720x480iS
  elif [[ $MONITORS_25K == *" $m "* ]]; then
    if [[ -n $super ]]; then
      echo 800x600iS
      return 0
    fi
    [[ $vfreq == 60 ]] || return 1
    if [[ $frame == i ]]; then echo 800x600iS; else echo 512x384S; fi
  elif [[ $MONITORS_31K == *" $m "* ]]; then
    echo 640x480S
  elif [[ $m == vesa_600 ]]; then
    echo 800x600
  elif [[ $m == pc_70_120 || $m == vesa_768 ]]; then
    echo 1024x768
  elif [[ $m == vesa_1024 ]]; then
    echo 1280x1024
  elif [[ $m == lcd ]]; then
    return 1
  else
    return 2
  fi
}

_res_15k() {
  case "$1:$2" in
    60:p) echo 320x240S ;;
    60:i) echo 640x480iS ;;
    50:p) echo 384x288S ;;
    50:i) echo 768x576iS ;;
    *) return 1 ;;
  esac
}

# monitor_resolutions FREQ [lowdotclock] lista "modo|descricao" dos modos de
# boot da faixa, na tabela fixa do patch do kernel. Sem suporte a dotclock
# baixo na placa (Intel, NVIDIA), sobram so as super resolucoes, como o
# gatools faz ao cair em "super resolutions will be used instead".
monitor_resolutions() {
  local freq=$1 low=${2:-1}
  case $freq in
    15k)
      if ((low)); then
        printf '%s\n' \
          "320x240S|320x240 60 Hz progressive" \
          "384x288S|384x288 50 Hz progressive" \
          "640x240S|640x240 60 Hz progressive" \
          "640x480iS|640x480 60 Hz interlaced" \
          "720x480iS|720x480 60 Hz interlaced" \
          "768x576iS|768x576 50 Hz interlaced"
      fi
      echo "1280x480iS|1280x480 60 Hz interlaced (super resolution)"
      ;;
    25k)
      ((low)) && echo "512x384S|512x384 59 Hz progressive"
      echo "800x600iS|800x600 60 Hz interlaced"
      ((low)) && echo "1024x768iS|1024x768 50 Hz interlaced"
      ;;
    31k)
      echo "640x480S|640x480 60 Hz progressive"
      ;;
  esac
  return 0
}

# monitor_normalize corrige o nome lido do EDID: o descritor de nome tem
# espaco para 12 letras, e "arcade_15_25_31" chega cortado.
monitor_normalize() {
  local name=${1//[[:space:]]/}
  case $name in
    arcade_15_25_) echo arcade_15_25_31 ;;
    *) echo "$name" ;;
  esac
}

# Modelines da tabela fixa do patch 15 kHz (drm_modes_low_dotclock.c), no
# formato do Xorg. O desktop (LXDE) usa o mesmo modo do boot, e o Xorg nao
# escolhe sozinho um modo de linha de comando do kernel.
mode_modeline() {
  case $1 in
    320x240S) echo '"320x240" 6.514 320 333 364 416 240 241 244 261 -HSync -VSync' ;;
    384x288S) echo '"384x288" 7.809 384 400 437 499 288 291 294 313 -HSync -VSync' ;;
    640x240S) echo '"640x240" 13.013 640 666 727 831 240 241 244 261 -HSync -VSync' ;;
    640x480iS) echo '"640x480i" 13.038 640 666 727 831 480 483 489 523 Interlace -HSync -VSync' ;;
    648x480iS) echo '"648x480i" 13.210 648 674 736 842 480 483 489 523 Interlace -HSync -VSync' ;;
    720x480iS) echo '"720x480i" 14.657 720 749 818 935 480 483 489 523 Interlace -HSync -VSync' ;;
    768x576iS) echo '"768x576i" 15.627 768 799 872 997 576 583 589 627 Interlace -HSync -VSync' ;;
    800x576iS) echo '"800x576i" 16.302 800 833 910 1040 576 583 589 627 Interlace -HSync -VSync' ;;
    1280x480iS) echo '"1280x480i" 26.108 1280 1332 1455 1664 480 483 489 523 Interlace -HSync -VSync' ;;
    512x384S) echo '"512x384" 15.973 512 525 589 640 384 391 396 426 -HSync -VSync' ;;
    800x600iS) echo '"800x600i" 24.930 800 820 920 1000 600 687 697 831 Interlace -HSync -VSync' ;;
    1024x768iS) echo '"1024x768i" 31.968 1024 1050 1178 1280 768 855 865 999 Interlace -HSync -VSync' ;;
    640x480S) echo '"640x480" 25.452 640 664 760 808 480 491 493 525 -HSync -VSync' ;;
    *) return 1 ;;
  esac
}

# mode_hsync_range FREQ imprime a faixa HorizSync do Xorg para a faixa.
mode_hsync_range() {
  case $1 in
    15k) echo "15.0 - 16.5" ;;
    25k) echo "24.0 - 26.0" ;;
    31k) echo "30.0 - 32.0" ;;
    *) return 1 ;;
  esac
}

# mode_pretty "640x480iS" -> "640x480i"
mode_pretty() {
  local m=${1%S}
  printf '%s\n' "$m"
}
