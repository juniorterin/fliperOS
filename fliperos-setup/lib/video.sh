# shellcheck shell=bash
# Teste de saidas e configuracao de video, portados do gatools do
# GroovyArcade (video/video.sh): test_all_connectors, test_connector,
# configure_from_connector e inform_user. Nada aqui chama o gum; as telas
# (screens/output-test.sh, screens/testing-results.sh) conduzem a conversa.
#
# Letras de resultado, as mesmas do gatools:
#   s  a placa gera dotclock baixo (radeon, amdgpu; nouveau que passou no grid)
#   o  achou um EDID do Switchres na saida
#   d  o EDID foi forcado na linha do kernel (drm.edid_firmware)
#   l  EDID de fabrica: LCD ou CRT moderno
#   r  monitor visto pela pessoa, sem EDID
#   e  monitor visto so depois de forcar a saida ligada
#   x  sem monitor
#   a  GPU integrada (APU): exige interlace_force_even no Switchres

DRM_MODULE_PARAMS=${DRM_MODULE_PARAMS:-/sys/module/drm/parameters}
FBCON_SYSFS=${FBCON_SYSFS:-/sys/class/graphics/fbcon}

# Estado do teste da saida atual (preenchido por video_test_begin).
VT_STATUS=""
VT_EDID_SIZE=0
VT_FORCED=0

# video_lights_on forca as saidas analogicas ligadas, como o "Lights on,
# test 1!" do gatools: sem isso um CRT sem EDID pode nao receber imagem nem
# para ver a primeira mensagem.
video_lights_on() {
  local c
  for c in $(drm_connectors); do
    drm_is_analog "$(drm_name "$c")" && drm_set_status "$c" on
  done
  return 0
}

video_all_off() {
  local c
  for c in $(drm_connectors); do
    drm_set_status "$c" off
  done
  return 0
}

video_all_detect() {
  local c
  for c in $(drm_connectors); do
    drm_set_status "$c" detect
  done
  return 0
}

# video_test_begin CONECTOR liga so esta saida para a pessoa olhar. Status 1
# quando nao ha o que testar: saida digital sem nada ligado.
video_test_begin() {
  local c=$1 name
  name=$(drm_name "$c")
  VT_FORCED=0
  drm_set_status "$c" detect
  VT_STATUS=$(drm_status "$c")
  VT_EDID_SIZE=$(drm_edid_size "$c")
  log_info "test: $name status=$VT_STATUS edid=${VT_EDID_SIZE}B"
  if [[ $VT_STATUS != connected ]]; then
    if ! drm_is_analog "$name"; then
      drm_set_status "$c" off
      return 1
    fi
    # Analogica sem deteccao: forca ligada. Um CRT de arcade nao tem EDID
    # nem, muitas vezes, a carga que o DAC usa para detectar monitor.
    drm_set_status "$c" on
    VT_FORCED=1
  fi
  return 0
}

# video_test_end CONECTOR desliga a saida testada e espera o monitor perder
# o sincronismo antes da proxima, como o gatools faz.
video_test_end() {
  drm_set_status "$1" off
  sleep "${VIDEO_TEST_GAP:-2}"
}

# video_classify CONECTOR imprime as letras do resultado da saida confirmada.
video_classify() {
  local c=$1 card flags=""
  card=$(drm_card "$c")
  drm_card_low_dotclock "$card" && flags=s
  if [[ $VT_STATUS == connected ]] && ((VT_EDID_SIZE > 0)); then
    if edid_is_switchres "$(drm_edid_file "$c")"; then
      if cmdline_get "$(< "$PROC_CMDLINE")" drm.edid_firmware > /dev/null; then
        flags+="do"
      else
        flags+=o
      fi
    else
      flags+=l
    fi
  elif ((VT_FORCED)); then
    flags+=e
  else
    flags+=r
  fi
  drm_card_is_apu "$card" && flags+=a
  printf '%s\n' "$flags"
}

# video_map_console CARD leva o console para o framebuffer da placa, como o
# con2fbmap do gatools: com duas placas, uma saida da segunda so mostra o
# teste se o console estiver nela.
video_map_console() {
  local fb cards
  cards=$(drm_connectors | sed 's/-.*//' | sort -u | wc -l)
  ((cards > 1)) || return 0
  fb=$(drm_card_fb "$1") || return 0
  have con2fbmap || return 0
  con2fbmap "$(fgconsole 2> /dev/null || echo 1)" "$fb" >> "$FLIPEROS_LOG" 2>&1 || true
}

# speech_connector NOME soletra o conector para a voz ("V G A 1").
speech_connector() {
  local name=$1 kind num
  kind=${name%-*}
  num=${name##*-}
  case $kind in
    DP) printf 'Display Port %s\n' "$num" ;;
    eDP) printf 'embedded Display Port %s\n' "$num" ;;
    Virtual) printf 'virtual output %s\n' "$num" ;;
    *) printf '%s %s\n' "$(sed 's/-//g; s/\(.\)/\1 /g; s/ *$//' <<< "$kind")" "$num" ;;
  esac
}

# video_reconfigure_monitor MONITOR troca o monitor e, se o teste de saidas
# ja escolheu a saida, recalcula os parametros de video para ele.
video_reconfigure_monitor() {
  local monitor=$1 conn flags params
  video_apply_monitor "$monitor"
  conn=$(conf_get connector 2> /dev/null) || return 0
  flags=$(conf_get detection 2> /dev/null) || return 0
  params=$(video_kernel_params "$conn" "$flags" "$monitor") || return 1
  conf_set kernel_video "$params"
  conf_set boot_resolution "$(video_boot_resolution "$params" || true)"
}

# video_restore CONECTOR FORCADA devolve as saidas ao automatico e deixa a
# escolhida ligada se foi preciso forcar (como o gatools depois do teste).
video_restore() {
  video_all_detect
  [[ $2 == 1 ]] && drm_set_status "$1" on
  return 0
}

# video_edid_monitor CONECTOR imprime o preset gravado no EDID do Switchres.
video_edid_monitor() {
  local name
  name=$(edid_monitor_name "$(drm_edid_file "$1")") || return 1
  monitor_normalize "$name"
}

# video_needs_monitor_choice FLAGS: sem EDID do Switchres (ou com um EDID
# forcado no boot), a pessoa escolhe o monitor, como no gatools.
video_needs_monitor_choice() {
  local base=${1%a}
  [[ ! $base =~ ^s?o$ ]]
}

# video_suggested_monitor imprime o preset mais provavel pela entrada de
# boot escolhida, para deixar o cursor do menu nele.
video_suggested_monitor() {
  case $(boot_profile 2>/dev/null) in
    15khz | intel | nvidia | edid-progressive | edid-interlaced) echo generic_15 ;;
    25khz) echo arcade_25 ;;
    31khz) echo arcade_31 ;;
    ntsc) echo ntsc ;;
    pal) echo pal ;;
    svga) echo lcd ;;
    *) echo generic_15 ;;
  esac
}

# video_kernel_params NOME FLAGS MONITOR imprime os parametros de video do
# kernel para o sistema, como o configure_from_connector do gatools:
#   - LCD: nenhum (vale o EDID do proprio monitor);
#   - EDID do Switchres (o, l): nenhum, o EDID manda;
#   - EDID forcado no boot (d) ou boot por EDID: EDID do preset na saida;
#   - sem EDID (r, e): o modo de boot do preset; super resolucao se a placa
#     nao gera dotclock baixo; "e" no fim se foi preciso forcar a saida.
video_kernel_params() {
  local conn=$1 flags=$2 monitor=$3 base enabled="" res="" fw
  base=${flags%a}
  [[ $monitor == lcd ]] && return 0
  [[ $base =~ ^s?e$ ]] && enabled=e
  if [[ $base =~ ^[er]$ ]]; then
    res=$(monitor_kernel_resolution "$monitor" 60 i super) || return 1
  elif [[ $base =~ ^s[er]$ ]]; then
    res=$(monitor_kernel_resolution "$monitor" 60 i) || return 1
  fi
  if [[ $base == *d* ]]; then
    fw=""
    [[ -r $DRM_MODULE_PARAMS/edid_firmware ]] && fw=$(< "$DRM_MODULE_PARAMS/edid_firmware")
    fw=${fw##*:}
    [[ -n $fw ]] || fw=edid/$monitor.bin
    echo "video=$conn:e drm.edid_firmware=$conn:$fw"
  elif cmdline_get "$(< "$PROC_CMDLINE")" drm.edid_firmware > /dev/null; then
    echo "video=$conn:e drm.edid_firmware=$conn:edid/$monitor.bin"
  elif [[ -n $res ]]; then
    echo "video=$conn:$res$enabled"
  elif [[ -n $enabled ]]; then
    echo "video=$conn:e"
  fi
  return 0
}

# video_boot_resolution PARAMS imprime o modo (640x480iS) de um conjunto de
# parametros, ou nada se o modo vem de EDID.
video_boot_resolution() {
  local word spec
  for word in $1; do
    if [[ $word == video=*:* ]]; then
      spec=${word#video=*:}
      spec=${spec%%,*}
      spec=${spec%e}
      [[ $spec =~ ^[0-9]+x[0-9]+ ]] && { echo "$spec"; return 0; }
    fi
  done
  return 1
}

# video_apply_monitor MONITOR grava o monitor no Switchres, no MAME e no
# fliperos.conf (set_monitor do gatools). Com o monitor custom ativo (o
# crt_range0 do Geometry) e o mesmo preset, o Switchres continua no custom;
# outro preset o desfaz, porque o crt_range foi feito em cima do anterior.
video_apply_monitor() {
  local monitor=$1 sr=$1
  if [[ $(conf_get monitor 2> /dev/null) != "$monitor" ]]; then
    video_custom_drop
  elif video_custom_active; then
    sr=custom
  fi
  ini_set "$SWITCHRES_INI" monitor "$sr"
  [[ -f $MAME_INI ]] && ini_set "$MAME_INI" monitor "$monitor"
  conf_set monitor "$monitor"
  conf_set frequency "$(monitor_frequency "$monitor" || echo lcd)"
  video_mame_aspect
  log_info "monitor: $monitor"
}

# video_mame_aspect grava o formato da tela no mame.ini: 4:3 num CRT, como o
# gasetup do GroovyArcade (-aspect "4:3"); "auto" num LCD. Com "auto" o
# GroovyMAME tira o formato do modo atual, e num boot em 640x240 (8:3) o
# Switchres dobrava a largura de todo jogo (384x224 virava 768x224, o
# aspect_corrector de modeline.cpp).
video_mame_aspect() {
  local monitor
  [[ -f $MAME_INI ]] || return 0
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  ini_set "$MAME_INI" aspect "$([[ $monitor == lcd ]] && echo auto || echo 4:3)"
}

# video_mame_monitor poe no mame.ini o monitor do Setup. Um mame.ini refeito
# (o -createconfig com o config/mame.ini por cima) volta ao arcade_15 de
# fabrica, e o GroovyMAME usava a faixa dele (16,14 kHz no gabinete) com o
# Switchres e o Setup em outro monitor.
video_mame_monitor() {
  local monitor
  [[ -f $MAME_INI ]] || return 0
  monitor=$(conf_get monitor 2> /dev/null) || return 0
  [[ -n $monitor ]] && ini_set "$MAME_INI" monitor "$monitor"
  return 0
}

# Chaves do fliperos.conf que dependem da placa e da saida: e o que o
# Recovery Mode leva para o disco quando a placa foi trocada. A orientacao
# e do gabinete, nao da placa, e so vai se foi escolhida nesta sessao.
VIDEO_CONF_KEYS="gpu driver card connector detection forced low_dotclock_pci low_dotclock_min kernel_video boot_resolution fb_map
  monitor frequency geometry custom_width custom_height custom_refresh screens"
VIDEO_CONF_KEEP="orientation"

# video_retroarch_super [ARQUIVO] grava a largura dos modos do CRT SwitchRes
# do RetroArch: nativa (0, como no GroovyArcade) quando a placa gera
# dotclock baixo — o "s" no comeco do resultado do teste de saidas —, e a
# super resolucao 2560 so nas que nao geram (Intel, NVIDIA). Em 2560 o
# RetroArch desenha as notificacoes nessa largura e no tubo elas saem
# espremidas (o que aconteceu no gabinete, com uma R7 240).
video_retroarch_super() {
  local file=${1:-$RETROARCH_CFG} flags card width=2560
  flags=$(conf_get detection 2> /dev/null) || flags=""
  card=$(conf_get card 2> /dev/null) || card=""
  if [[ $flags == s* ]]; then
    width=0
  elif [[ -z $flags && -n $card ]] && drm_card_low_dotclock "$card" 2> /dev/null; then
    width=0
  fi
  rcfg_set "$file" crt_switch_resolution_super "$width"
}

# Os degraus do teste de dotclock baixo (screen_low_dotclock_test), do mais
# exigente para o PLL ao mais leve: "LARGURA:MINIMO". O grid sai em
# LARGURAx240, e o primeiro que a pessoa ve decide o dotclock_min. Cada PLL de
# NVIDIA tem o seu piso: uma GTX 980 Ti no nouveau ficou preta em 6,5 e 6,8 MHz
# e mostrou tudo de 7,15 MHz para cima. O minimo fica um pouco abaixo do clock
# do degrau (384x240 sai a 7,8 MHz) para o proprio modo testado passar; o que
# fica abaixo dele o Switchres, o MAME e o RetroArch dobram na largura (320
# vira 640), com a mesma imagem no tubo.
LOWDOT_STEPS=${LOWDOT_STEPS:-"320:0 384:7.7 512:10.3 640:12.9"}

# video_low_dotclock_mhz LARGURA [kHz]: o pixel clock aproximado de um modo
# dessa largura (o Switchres poe uns 30% de apagamento horizontal), em MHz
# com uma casa. Para o texto do teste e para comparar com o dotclock_min.
video_low_dotclock_mhz() {
  awk -v w="$1" -v k="${2:-15.66}" 'BEGIN { printf "%.1f\n", w * 1.3 * k / 1000 }'
}

# video_low_dotclock_grid MONITOR [LARGURA] mostra o grid do Switchres em
# LARGURAx240 (320: uns 6,5 MHz num monitor de 15 kHz, o modo mais exigente
# para o PLL da placa) com dotclock_min 0. Com o tubo sem imagem ninguem acha
# a tecla: o timeout devolve o console sozinho, com SIGINT para o Switchres
# restaurar o modo.
video_low_dotclock_grid() {
  timeout -s INT -k 5 "${LOWDOT_TEST_SECONDS:-20}" \
    switchres "${2:-320}" 240 60 -s -m "$1" --dotclock_min 0 -l grid
}

# video_low_dotclock_kernel_log: as ultimas linhas do kernel sobre o driver
# de video e o PLL, para o log do Setup depois do grid.
DMESG_CMD=${DMESG_CMD:-dmesg}
video_low_dotclock_kernel_log() {
  echo "dotclock baixo: o kernel depois do grid:"
  "$DMESG_CMD" 2> /dev/null | grep -iE 'nouveau|pll|drm' | tail -n 20
  return 0
}

# video_low_dotclock_set CARD 1|0 [MINIMO] grava a placa que passou no grid
# e o dotclock_min do degrau visto (0: o 320x240 nativo), ou a esquece (a
# outra placa que estava gravada tambem: so vale uma).
video_low_dotclock_set() {
  local pci
  if [[ $2 == 1 ]]; then
    pci=$(drm_card_pci "$1") || return 1
    conf_set low_dotclock_pci "$pci"
    conf_set low_dotclock_min "${3:-0}"
  else
    conf_unset low_dotclock_pci
    conf_unset low_dotclock_min
  fi
  log_info "dotclock baixo: $1 -> $2${3:+ (dotclock_min $3)}"
}

# video_low_dotclock_min CARD: o dotclock_min que a placa precisa (MHz). 0
# nas que geram tudo (radeon, amdgpu, a NVIDIA que mostrou o 320x240); o
# degrau do teste numa NVIDIA que so mostrou um modo mais largo.
video_low_dotclock_min() {
  local min=0
  case $(drm_card_driver "$1" 2> /dev/null) in
    nouveau | nvidia)
      if drm_card_low_dotclock "$1"; then
        min=$(conf_get low_dotclock_min 2> /dev/null) || min=0
      fi
      ;;
  esac
  printf '%s\n' "${min:-0}"
}

# video_dotclock_min_ours VALOR: um dotclock_min que o proprio Setup grava
# (0, o 25.0 da super resolucao ou um degrau do teste), que pode trocar. Um
# valor que a pessoa escolheu fica.
video_dotclock_min_ours() {
  local step
  case $1 in "" | 0 | 0.0 | 25 | 25.0) return 0 ;; esac
  for step in $LOWDOT_STEPS; do
    [[ $1 == "${step#*:}" ]] && return 0
  done
  return 1
}

# video_low_dotclock_apply refaz o resultado do teste de saidas com ou sem
# o "s", depois de o grid ser repetido no Video Setup: modo de boot,
# dotclock_min do Switchres e do MAME e a largura do RetroArch.
video_low_dotclock_apply() {
  local card conn flags monitor
  card=$(conf_get card 2> /dev/null) || return 1
  conn=$(conf_get connector 2> /dev/null) || return 1
  flags=$(conf_get detection 2> /dev/null) || return 1
  monitor=$(conf_get monitor 2> /dev/null) || monitor=generic_15
  flags=${flags#s}
  drm_card_low_dotclock "$card" && flags=s$flags
  video_save_result "$card-$conn" "$flags" "$monitor"
}

# video_save_result CONECTOR FLAGS MONITOR grava o resultado validado do
# teste de saidas para o instalador e para o sistema instalado.
video_save_result() {
  local c=$1 flags=$2 monitor=$3 card name base params min
  card=$(drm_card "$c")
  name=$(drm_name "$c")
  base=${flags%a}
  params=$(video_kernel_params "$name" "$flags" "$monitor") || return 1
  # Outra placa ou outra saida principal: os monitores extras sao escolhidos
  # de novo (Video Setup > Multiple Monitors).
  if [[ $(conf_get card 2> /dev/null) != "$card" || $(conf_get connector 2> /dev/null) != "$name" ]]; then
    conf_unset screens
  fi
  conf_set gpu "$(drm_card_name "$card")"
  conf_set driver "$(drm_card_driver "$card" || echo unknown)"
  conf_set card "$card"
  conf_set connector "$name"
  conf_set detection "$flags"
  conf_set forced "$([[ $base =~ ^s?e$ ]] && echo 1 || echo 0)"
  conf_set kernel_video "$params"
  conf_set boot_resolution "$(video_boot_resolution "$params" || true)"
  # Saida numa segunda placa: o console do sistema instalado tem de ir para
  # o framebuffer dela desde o boot (fbcon=map).
  conf_set fb_map "$(drm_card_fb "$card" 2> /dev/null || echo 0)"
  video_apply_monitor "$monitor"
  # Sem dotclock baixo, o Switchres e o MAME trabalham com super resolucao.
  if [[ $base =~ ^[er]$ ]]; then
    ini_set "$SWITCHRES_INI" dotclock_min 25.0
    [[ -f $MAME_INI ]] && ini_set "$MAME_INI" dotclock_min 25.0
  elif [[ $base == s* ]]; then
    # O minimo da placa: 0, ou o degrau do grid numa NVIDIA. Troca o que o
    # Setup gravou antes (o 25.0 de um teste sem o grid, outro degrau); um
    # valor proprio da pessoa fica.
    min=$(video_low_dotclock_min "$card")
    video_dotclock_min_ours "$(ini_get "$SWITCHRES_INI" dotclock_min 2> /dev/null)" &&
      ini_set "$SWITCHRES_INI" dotclock_min "$min"
    [[ -f $MAME_INI ]] && video_dotclock_min_ours "$(ini_get "$MAME_INI" dotclock_min 2> /dev/null)" &&
      ini_set "$MAME_INI" dotclock_min "$min"
  fi
  if [[ $flags == *a ]]; then
    ini_set "$SWITCHRES_INI" interlace_force_even 1
  fi
  video_retroarch_super
  log_info "resultado: $name flags=$flags monitor=$monitor params=$params"
}

# video_current_mode CONECTOR imprime "LARGURAxALTURA|kHz|Hz|entrelacado" do
# modo ativo, lido pelo fliperos-video-check (CRTC atual via DRM).
video_current_mode() {
  local name=$1 json
  [[ -x $VIDEO_CHECK ]] || return 1
  json=$("$VIDEO_CHECK" --json --connector "$name" 2> /dev/null) || true
  [[ -n $json ]] || return 1
  jq -r --arg c "$name" '
    [.outputs[] | select(.connector == $c and .active)][0]
    | select(. != null)
    | "\(.width)x\(.height)|\(.horizontal_khz)|\(.vertical_hz)|\(.interlaced)"' <<< "$json" 2> /dev/null |
    grep . || return 1
}

# ── Orientacao ───────────────────────────────────────────────────
# Mesmo efeito do worker_select_monitor_orientation do gasetup: console
# girado (fbcon), panel_orientation no video= do conector e ror/rol no MAME.

orientation_label() {
  case $1 in
    horizontal) echo "Horizontal" ;;
    vertical-cw) echo "Vertical clockwise" ;;
    vertical-ccw) echo "Vertical counter-clockwise" ;;
    *) echo "$1" ;;
  esac
}

# orientation_short ORIENTACAO: o nome curto, para o resumo do Video Setup.
orientation_short() {
  case $1 in
    horizontal) echo "horizontal" ;;
    vertical-cw) echo "vertical CW" ;;
    vertical-ccw) echo "vertical CCW" ;;
    *) echo "$1" ;;
  esac
}

# orientation_fbcon ORIENTACAO imprime o valor do fbcon rotate.
orientation_fbcon() {
  case $1 in
    vertical-cw) echo 1 ;;
    vertical-ccw) echo 3 ;;
    *) echo 0 ;;
  esac
}

orientation_panel() {
  case $1 in
    vertical-cw) echo right_side_up ;;
    vertical-ccw) echo left_side_up ;;
  esac
}

# orientation_apply ORIENTACAO grava a orientacao e gira o console agora.
orientation_apply() {
  local o=$1
  conf_set orientation "$o"
  if [[ -f $MAME_INI ]]; then
    ini_set "$MAME_INI" ror 0
    ini_set "$MAME_INI" rol 0
    ini_set "$MAME_INI" autoror 0
    ini_set "$MAME_INI" autorol 0
    case $o in
      vertical-cw) ini_set "$MAME_INI" ror 1 ;;
      vertical-ccw) ini_set "$MAME_INI" rol 1 ;;
    esac
  fi
  printf '%s' "$(orientation_fbcon "$o")" > "$FBCON_SYSFS/rotate_all" 2> /dev/null || true
  log_info "orientacao: $o"
}

# ── Console em pe ────────────────────────────────────────────────
# Em pe, o console no modo de boot (640x240) tem so 30 colunas de texto, com
# letras largas: as 240 linhas viram a largura. O console vai em 640x480i
# (60 colunas, letras na proporcao), e o menu e o frontend trocam para o
# 640x240 deles. Sem EDID o kernel so conhece o modo do video=: o EDID do
# FliperOS (VERTICAL_EDID) traz os dois, com os tempos do Switchres para o
# monitor do Video Setup (config/fliperos-edid-modes).
VERTICAL_EDID=${VERTICAL_EDID:-fliperos-vertical.bin}
EDID_MODES=${EDID_MODES:-/opt/fliperos/bin/fliperos-edid-modes}

# vertical_edid grava o EDID com 640x240 e 640x480i do monitor. Status 1 (e
# sem o arquivo) se o monitor nao tem o 480 entrelacado (um de 31 kHz).
vertical_edid() {
  local monitor m240 m480
  monitor=$(conf_get monitor 2> /dev/null) || monitor=generic_15
  rm -f "$EDID_DIR/$VERTICAL_EDID"
  have switchres || return 1
  m240=$(switchres 640 240 60 --monitor "$monitor" --calc 2>&1 | sed -n 's/.*Modeline //p' | head -1)
  m480=$(switchres 640 480 60 --monitor "$monitor" --calc 2>&1 | sed -n 's/.*Modeline //p' | head -1)
  [[ -n $m240 && $m480 == *interlace* ]] || return 1
  mkdir -p "$EDID_DIR"
  printf '%s\n%s\n' "$m240" "$m480" | "$EDID_MODES" "$EDID_DIR/$VERTICAL_EDID" 2>> "$FLIPEROS_LOG"
}

# vertical_console_cmdline LINHA CONECTOR ORIENTACAO: em pe, com o EDID do
# FliperOS gravado, o modo do console vira 640x480i (as letras S e e do
# video= ficam) e o drm.edid_firmware aponta para ele. Uma linha que ja traz
# um EDID (o boot por EDID, a super resolucao) fica como esta.
vertical_console_cmdline() {
  local line=$1 conn=$2 o=$3 spec mode rest
  if [[ $o != vertical-* || -z $conn || ! -f $EDID_DIR/$VERTICAL_EDID ]] ||
    cmdline_get "$line" drm.edid_firmware > /dev/null ||
    ! spec=$(cmdline_video_spec "$line" "$conn"); then
    printf '%s\n' "$line"
    return
  fi
  mode=${spec%%,*}
  rest=${spec#"$mode"}
  [[ $mode =~ ^[0-9]+x[0-9]+(@[0-9.]+)?i?(.*)$ ]] || { printf '%s\n' "$line"; return; }
  line=$(cmdline_set_video "$line" "$conn" "640x480i${BASH_REMATCH[2]}$rest")
  cmdline_set "$line" drm.edid_firmware "$conn:edid/$VERTICAL_EDID"
}

# orientation_boot ORIENTACAO: o que o boot precisa para a orientacao (o
# EDID do console em pe, o splash girado) e o initramfs refeito uma vez.
orientation_boot() {
  local o=$1 changed=0
  if [[ $o == vertical-* ]]; then
    ev_step 10 "The console for a vertical monitor"
    vertical_edid && changed=1
  fi
  ev_step 30 "The boot screen"
  splash_orientation "$o" && changed=1
  ((changed)) || return 0
  ev_step 50 "Rebuilding the initramfs"
  run_logged "$UPDATE_INITRAMFS" -u
}

# orientation_cmdline LINHA CONECTOR ORIENTACAO acerta fbcon=rotate e o
# panel_orientation do conector na linha do kernel.
orientation_cmdline() {
  local line=$1 conn=$2 o=$3 panel word out=()
  for word in $line; do
    [[ $word == fbcon=rotate:* ]] && continue
    out+=("$word")
  done
  line=${out[*]}
  if [[ -n $conn ]]; then
    line=$(cmdline_remove_video_option "$line" "$conn" panel_orientation)
  fi
  if [[ $o != horizontal && -n $o ]]; then
    line="$line fbcon=rotate:$(orientation_fbcon "$o")"
    panel=$(orientation_panel "$o")
    [[ -n $conn && -n $panel ]] && line=$(cmdline_set_video_option "$line" "$conn" panel_orientation "$panel")
  fi
  printf '%s\n' "$line"
}

# ── Resolucao de boot ────────────────────────────────────────────

# video_resolution_choices imprime "modo|descricao" validos para o monitor
# configurado e a placa da saida escolhida.
video_resolution_choices() {
  local monitor freq card low=1 min=0 khz=15.66 edid240=0
  monitor=$(conf_get monitor) || monitor=generic_15
  freq=$(monitor_frequency "$monitor") || return 1
  card=$(conf_get card) || card=""
  if [[ -n $card ]]; then
    drm_card_low_dotclock "$card" || low=0
    min=$(video_low_dotclock_min "$card")
    # O i915 nao tem o 240p progressivo largo na tabela do kernel: ele vem de
    # um EDID do FliperOS (super240_edid).
    [[ $freq == 15k && $(drm_card_driver "$card") == i915 ]] && edid240=1
  fi
  case $freq in 25k) khz=25 ;; 31k) khz=31.5 ;; esac
  # Numa NVIDIA que so mostrou um degrau mais largo no grid, sem os modos de
  # boot abaixo do minimo dela (o 320x240 na GTX 980 Ti).
  monitor_resolutions "$freq" "$low" "$edid240" | awk -F'|' -v min="$min" -v k="$khz" '
    { w = $1; sub(/x.*/, "", w) }
    min + 0 == 0 || w * 1.3 * k / 1000 >= min + 0'
}

# video_set_resolution MODO troca o modo de boot da saida configurada,
# mantendo o "e" (saida forcada) e as opcoes como panel_orientation.
video_set_resolution() {
  local mode=$1 conn params spec opts="" enabled=""
  conn=$(conf_get connector) || return 1
  # O 240p largo da Intel nao esta na tabela do kernel: vai por um EDID.
  if [[ $mode == "$SUPER240_MODE" ]]; then
    super240_edid || return 1
    video_set_custom_edid "$SUPER240_EDID" "$mode"
    return
  fi
  params=$(conf_get kernel_video) || params=""
  if spec=$(cmdline_video_spec "$params" "$conn"); then
    [[ $spec == *,* ]] && opts=,${spec#*,}
    spec=${spec%%,*}
    [[ $spec == *e ]] && enabled=e
  fi
  [[ $(conf_get forced) == 1 ]] && enabled=e
  params=$(cmdline_without_video "$params")
  params=$(cmdline_set_video "$params" "$conn" "$mode$enabled$opts")
  conf_set kernel_video "$params"
  conf_set boot_resolution "$mode"
  log_info "resolucao de boot: $mode ($params)"
}

# video_set_custom_edid EDID [MODO] troca o modo de boot por um EDID proprio
# (resolucao personalizada, gerada pelo Switchres; ou o MODO do FliperOS,
# como o 1280x240p da Intel).
video_set_custom_edid() {
  local edid=$1 label=${2:-custom} conn params
  conn=$(conf_get connector) || return 1
  params=$(conf_get kernel_video) || params=""
  params=$(cmdline_without_video "$params")
  params="video=$conn:e drm.edid_firmware=$conn:edid/$edid ${params}"
  conf_set kernel_video "${params% }"
  conf_set boot_resolution "$label"
}

# O 240p progressivo da Intel i915, que nao gera dotclock abaixo de 25 MHz:
# 1280x240 a 15,66 kHz (26 MHz), os tempos horizontais do 1280x480i e os
# verticais do 640x240 da tabela do kernel. O kernel so conhece o modo da
# linha video=; o EDID do FliperOS (config/fliperos-edid-modes) o traz.
SUPER240_MODE=1280x240p
SUPER240_EDID=${SUPER240_EDID:-fliperos-1280x240.bin}

# super240_edid grava o EDID com o modo 1280x240p. Entra no initramfs pelo
# fliperos-edid-hook (boot_apply refaz o initramfs).
super240_edid() {
  local modeline
  modeline=$(mode_modeline "$SUPER240_MODE") || return 1
  mkdir -p "$EDID_DIR"
  printf '%s\n' "$modeline" | "$EDID_MODES" "$EDID_DIR/$SUPER240_EDID" 2>> "$FLIPEROS_LOG"
}

# ── Geometria ────────────────────────────────────────────────────
# O gasetup chama "geometry 648 480 60" (o geometry.py do Switchres) e
# grava o crt_range final como monitor custom. 648 e nao 640 para o
# Switchres criar um modo novo em vez de reaproveitar o do boot.

# geometry_parse SAIDA imprime o crt_range final (vazio se abortou).
# geometry_mode imprime "LARGURA ALTURA HZ" do teste de geometria: a
# resolucao escolhida no Video Setup (o grid tem de estar no modo que o
# monitor vai mostrar; um 640x480 entrelacado quase nao tem linha sobrando
# para descer a imagem), ou 640x480@60 sem escolha.
geometry_mode() {
  local res w="" h="" r=60 whr
  res=$(conf_get boot_resolution 2> /dev/null) || res=""
  if [[ $res == custom ]]; then
    w=$(conf_get custom_width 2> /dev/null) || w=""
    h=$(conf_get custom_height 2> /dev/null) || h=""
    r=$(conf_get custom_refresh 2> /dev/null) || r=60
  elif whr=$(mode_whr "$res" 2> /dev/null); then
    read -r w h r <<< "$whr"
  elif [[ $res =~ ^([0-9]+)x([0-9]+) ]]; then
    w=${BASH_REMATCH[1]}
    h=${BASH_REMATCH[2]}
    [[ $res =~ @([0-9.]+) ]] && r=${BASH_REMATCH[1]}
  fi
  if [[ ! $w =~ ^[0-9]+$ || ! $h =~ ^[0-9]+$ ]]; then
    w=640
    h=480
  fi
  [[ $r =~ ^[0-9]+(\.[0-9]+)?$ ]] || r=60
  printf '%s %s %s\n' "$w" "$h" "$r"
}

# geometry_grid_mode imprime o modo em que o grid abre: o de geometry_mode
# com 8 pixels a mais na largura, como o "geometry 648 480 60" do gasetup.
# No modo exato do boot o Switchres reaproveita o modo que esta na tela: o
# primeiro grid abre, mas a cada seta o geometry.py fecha o grid e o abre de
# novo com outra geometria, o Switchres tem de trocar o modo em uso e o
# geometry.py caia na primeira seta. As linhas e o refresh ficam os do boot.
geometry_grid_mode() {
  local w h r
  read -r w h r <<< "$(geometry_mode)"
  printf '%s %s %s\n' "$((w + 8))" "$h" "$r"
}

geometry_parse() {
  sed -n 's/^.*Final crt_range: //p' <<< "$1" | tail -1
}

# geometry_aborted SAIDA: a pessoa saiu com ESC (o geometry.py escreve
# "Aborted!"). Sem isso e sem crt_range, o geometry.py caiu com um erro.
geometry_aborted() {
  grep -q '^Aborted!' <<< "$1"
}

geometry_apply() {
  local range=$1
  [[ -n $range ]] || return 1
  ini_set "$SWITCHRES_INI" monitor custom
  ini_set "$SWITCHRES_INI" crt_range0 "$range"
  # Como o gasetup: o GroovyMAME passa a ler o switchres.ini, em vez de
  # duplicar o crt_range no mame.ini.
  [[ -f $MAME_INI ]] && ini_set "$MAME_INI" switchres_ini 1
  conf_set geometry "$range"
  log_info "geometria: $range"
}

# geometry_reset desfaz o geometry_apply: o Switchres volta ao preset do
# monitor escolhido. Vale para o GroovyMAME (switchres_ini 1, como no
# GroovyArcade) e para o modo 4 do RetroArch, que leem o mesmo arquivo.
geometry_reset() {
  local monitor
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  [[ -n $monitor && $monitor != custom ]] || monitor=generic_15
  ini_set "$SWITCHRES_INI" crt_range0 auto
  conf_unset geometry
  video_apply_monitor "$monitor"
  log_info "geometria: padrao do monitor $monitor"
}

# ── Monitor custom ───────────────────────────────────────────────
# "Custom" no Monitor Type e o monitor custom do Switchres: um crt_range0
# proprio (feito no Geometry ou digitado) no lugar das faixas do preset. O
# preset continua no fliperos.conf (monitor=) como base: dele saem o modo de
# boot, o EDID e a faixa do Xorg. O crt_range fica em geometry=.

video_custom_active() {
  conf_get geometry > /dev/null 2>&1
}

# video_custom_drop desfaz o custom sem mexer no monitor do Switchres.
video_custom_drop() {
  video_custom_active || return 0
  ini_set "$SWITCHRES_INI" crt_range0 auto
  conf_unset geometry
  log_info "monitor custom desfeito"
}

# video_monitor_label imprime o monitor do Video Setup, com o custom.
video_monitor_label() {
  local monitor
  monitor=$(conf_get monitor 2> /dev/null) || { echo "not set"; return 0; }
  if video_custom_active; then
    printf 'Custom (on %s)\n' "$(monitor_label "$monitor")"
  else
    monitor_label "$monitor"
  fi
}

# geometry_cli status|reset|set RANGE: a geometria pelo painel web, pelas
# mesmas funcoes das telas. status imprime monitor=, label=, range= (o
# crt_range salvo; vazio, o do preset vale), preset= e tool= (1: o grid do
# Switchres existe). set grava um crt_range digitado, como o Custom monitor:
# status 2 se nao e um crt_range (ou o monitor e LCD), 3 se e de outra faixa
# de frequencia que a do monitor escolhido.
geometry_cli() {
  local base range rfreq bfreq
  base=$(conf_get monitor 2> /dev/null) || base=""
  case ${1:-} in
    status)
      printf 'monitor=%s\nlabel=%s\nrange=%s\npreset=%s\ntool=%s\n' "$base" "$(video_monitor_label 2> /dev/null)" \
        "$(conf_get geometry 2> /dev/null)" "$(video_preset_range "$base" 2> /dev/null)" "$(have geometry && echo 1 || echo 0)"
      ;;
    reset)
      conf_get geometry > /dev/null 2>&1 || return 0
      geometry_reset
      ;;
    set)
      range=${2//[[:space:]]/}
      [[ -n $base && $base != lcd ]] && crt_range_valid "$range" || return 2
      rfreq=$(crt_range_frequency "$range") || return 2
      bfreq=$(monitor_frequency "$base") || return 2
      [[ $rfreq == "$bfreq" ]] || return 3
      geometry_apply "$range"
      ;;
    *) return 2 ;;
  esac
}

# crt_range_valid RANGE: os 16 valores de um crt_range do Switchres,
# HfreqMin-HfreqMax,VfreqMin-VfreqMax, os seis porches/sync, as duas
# polaridades e as quatro contagens de linhas.
crt_range_valid() {
  local n='[0-9]+(\.[0-9]+)?'
  [[ $1 =~ ^$n-$n,$n-$n(,$n){6},[01],[01](,[0-9]+){4}$ ]]
}

# crt_range_frequency RANGE imprime 15k, 25k ou 31k pela frequencia
# horizontal minima (em Hz, como no switchres.ini).
crt_range_frequency() {
  local hmin=${1%%-*}
  hmin=${hmin%%.*}
  [[ $hmin =~ ^[0-9]+$ ]] || return 1
  if ((hmin >= 14000 && hmin < 20000)); then
    echo 15k
  elif ((hmin >= 20000 && hmin < 28000)); then
    echo 25k
  elif ((hmin >= 28000 && hmin < 40000)); then
    echo 31k
  else
    return 1
  fi
}

# video_preset_range MONITOR imprime o primeiro crt_range do preset (o que o
# Switchres mostra em "Monitor range"), para comecar a digitar dele.
video_preset_range() {
  local w h r
  have switchres || return 1
  read -r w h r <<< "$(geometry_mode)"
  switchres "$w" "$h" "$r" -c -v -m "$1" 2>&1 |
    sed -n 's/^Switchres: Monitor range //p' | head -1 | grep .
}

# ── Jogos de 480 linhas num tubo de 15 kHz ───────────────────────
# Setup > Video Setup > 480i hacks: o metodo de cada aplicacao para o que tem
# 480 linhas, numa tabela de tres colunas:
#   240p    o hack de 640x240 progressivo (sem flicker, metade das linhas)
#   filter  480i com o filtro de flicker (config/fliperos-deflicker.c), no
#           nivel da aplicacao (light, medium, strong)
#   pure    480i sem o filtro (nitido, com o flicker)
# Gravado no fliperos.conf: mode480_PROGRAMA=240p|filter|pure, que o
# fliperos-x11-run (o modo), o fliperos-fightcade e o
# fliperos-desktop-deflicker leem, e deflicker_PROGRAMA=nivel|off, que a
# camada le (PROGRAMA e o nome do comando na tabela do fliperos-x11-run, ou
# o core do RetroArch sem o _libretro.so). deflicker_level_PROGRAMA guarda o
# ultimo nivel escolhido. A linha "other" e o deflicker= de todo o resto
# (jogos personalizados, programas fora da tabela).
DEFLICKER_LEVELS="off light medium strong"
MODE480_VALUES="240p filter pure"
RA_CORES=${RA_CORES:-/opt/fliperos/retroarch/cores}
RA_HOME=${RA_HOME:-/home/$FLIPEROS_USER/.config/retroarch}
FIGHTCADE_DIR=${FIGHTCADE_DIR:-/opt/fliperos/fightcade}
DEFLICKER_LIB=${DEFLICKER_LIB:-/usr/local/lib/fliperos/libfliperos-deflicker.so}
DEFLICKER_X11_RUN=${DEFLICKER_X11_RUN:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-x11-run}

# mode480_table: chave|rotulo|programas|permitidas|padrao|tipo|ajuda.
# tipo: x11 (fliperos-x11-run), mame (o interlace do mame.ini), core:NOME
# (o switchres.ini do core no RetroArch, NOME = o do core nas pastas de
# config), fightcade, desktop, other. O padrao e o que cada um ja fazia.
mode480_table() {
  cat << 'TABLE'
flycast|Flycast|flycast|240p,filter,pure|240p|x11|Dreamcast, Naomi, Atomiswave.
pcsx2|PCSX2|pcsx2|240p,filter,pure|240p|x11|PlayStation 2.
duckstation|DuckStation|duckstation|240p,filter,pure|240p|x11|PlayStation (the few 480i games, like Tekken 3 menus or Tobal 2).
dolphin|Dolphin|dolphin-emu|240p,filter,pure|240p|x11|GameCube and Wii.
laserdisc|Hypseus Singe|hypseus singe|240p,filter,pure|240p|x11|Laserdisc games.
model3|Supermodel|supermodel|240p,filter,pure|240p|x11|Sega Model 3 (384 lines).
model2|SM2-Emu|sm2-emu fliperos-model2|240p,filter,pure|240p|x11|Sega Model 2 (384 lines).
groovymame|GroovyMAME|groovymame|240p,filter,pure|filter|mame|Arcade games with more than 240 lines. 240p: Switchres never picks an interlaced mode.
psx|RetroArch PS1|pcsx_rearmed|240p,filter,pure|filter|core:PCSX-ReARMed|PlayStation games in high resolution (PCSX ReARMed core).
mame2010|RA MAME 2010|mame2010|240p,filter,pure|240p|core:MAME 2010|Arcade games with more than 240 lines in the MAME 2010 core.
snes|RetroArch SNES|snes9x|240p,filter,pure|filter|core:Snes9x|The few interlaced SNES games (Snes9x core).
megadrive|RA Mega Drive|genesis_plus_gx|240p,filter,pure|filter|core:Genesis Plus GX|Interlaced Mega Drive games, like Sonic 2 split screen (Genesis Plus GX core).
fbneo|RetroArch FBNeo|fbneo|240p,filter,pure|filter|core:FinalBurn Neo|Arcade games with more than 240 lines in the FBNeo core.
fightcade|Fightcade Flycast|fightcade-flycast|240p,filter,pure|240p|fightcade|Flycast matches in Fightcade 2.
desktop|Desktop|desktop|filter,pure|filter|desktop|The LXDE desktop, when Screen Resolution puts it in a 480-line mode.
other|Other programs|other|filter,pure|filter|other|Custom games and any other program in a 480i mode.
TABLE
}

# mode480_field CHAVE N: o campo N da linha da chave.
mode480_field() {
  mode480_table | awk -F'|' -v k="$1" -v n="$2" '$1 == k { print $n; exit }'
}

# mode480_installed CHAVE: a aplicacao esta neste computador?
mode480_installed() {
  local kind prog
  kind=$(mode480_field "$1" 6)
  case $kind in
    core:*) [[ -f $RA_CORES/$(mode480_field "$1" 3)_libretro.so ]] ;;
    fightcade) [[ -x $FIGHTCADE_DIR/fightcade ]] ;;
    desktop) [[ -x ${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-lxde ]] ;;
    other) return 0 ;;
    *)
      for prog in $(mode480_field "$1" 3); do
        if have "$prog" || [[ -x ${FLIPEROS_BIN:-/opt/fliperos/bin}/$prog ]]; then
          return 0
        fi
      done
      return 1
      ;;
  esac
}

# mode480_state CHAVE: 240p, filter ou pure.
mode480_state() {
  local prog state
  read -r prog _ <<< "$(mode480_field "$1" 3)"
  if [[ $prog == other ]]; then
    [[ $(deflicker_level) == off ]] && echo pure || echo filter
    return 0
  fi
  state=$(conf_get "mode480_$prog" 2> /dev/null) || state=""
  [[ -n $state && " $MODE480_VALUES " == *" $state "* ]] || state=$(mode480_field "$1" 5)
  printf '%s\n' "$state"
}

# mode480_level CHAVE: o nivel do filtro da aplicacao (light, medium ou
# strong): o ultimo escolhido, mesmo com ela em 240p ou pure.
mode480_level() {
  local prog level
  read -r prog _ <<< "$(mode480_field "$1" 3)"
  if [[ $prog == other ]]; then
    level=$(conf_get deflicker_level 2> /dev/null) || level=$(conf_get deflicker 2> /dev/null) || level=""
  else
    level=$(conf_get "deflicker_level_$prog" 2> /dev/null) || level=""
  fi
  [[ -n $level && " light medium strong " == *" $level "* ]] || level=medium
  printf '%s\n' "$level"
}

# mode480_rows: as linhas da tabela no formato do ui_grid.
mode480_rows() {
  local key label allowed help state now
  while IFS='|' read -r key label _ allowed _ _ help; do
    state=$(mode480_state "$key")
    case $state in
      240p) now="Now: 640x240." ;;
      filter) now="Now: 480i, filter $(mode480_level "$key")." ;;
      *) now="Now: 480i, no filter." ;;
    esac
    mode480_installed "$key" || now+=" Not installed."
    printf '%s|%s|%s|%s|%s\n' "$key" "$label" "$state" "$help $now" "$allowed"
  done < <(mode480_table)
}

# mode480_set CHAVE ESTADO [NIVEL] grava e aplica. NIVEL so vale no filter
# (sem ele, o ultimo escolhido).
mode480_set() {
  local key=$1 state=$2 level=${3:-} kind prog value
  kind=$(mode480_field "$key" 6)
  [[ -n $kind && " $MODE480_VALUES " == *" $state "* && ,$(mode480_field "$key" 4), == *,"$state",* ]] || return 1
  [[ -n $level ]] || level=$(mode480_level "$key")
  [[ " light medium strong " == *" $level "* ]] || return 1
  value=$level
  [[ $state == pure ]] && value=off
  for prog in $(mode480_field "$key" 3); do
    if [[ $kind == other ]]; then
      conf_set deflicker "$value"
      conf_set deflicker_level "$level"
    else
      conf_set "mode480_$prog" "$state"
      conf_set "deflicker_$prog" "$value"
      conf_set "deflicker_level_$prog" "$level"
    fi
  done
  case $kind in
    mame)
      [[ -f $MAME_INI ]] && ini_set "$MAME_INI" interlace "$([[ $state == 240p ]] && echo 0 || echo 1)"
      ;;
    core:*) mode480_core_ini "${kind#core:}" "$([[ $state == 240p ]] && echo 0 || echo 1)" ;;
  esac
  log_info "480i: $key = $state ($level)"
}

# mode480_core_ini NOME 0|1 grava o switchres.ini do core: o CRT SwitchRes
# do RetroArch o le por cima do /etc/switchres.ini. Sem o cabecalho
# "# FliperOS", as atualizacoes nao o regravam (fliperos-rootfs.sh).
mode480_core_ini() {
  local name=$1 dir file
  dir="$RA_HOME/config/$name"
  file="$dir/$name.switchres.ini"
  mkdir -p "$dir" || return 1
  printf '# Setup > Video Setup > 480i hacks: interlace 0 = 240p, 1 = 480i.\ninterlace %s\n' "$2" > "$file" || return 1
  chown "$FLIPEROS_USER:" "$RA_HOME/config" "$dir" "$file" 2> /dev/null || true
}

# mode480_save "chave=estado,..." (a resposta do ui_grid) grava as linhas
# que mudaram. O nivel de uma linha vem de MODE480_LEVEL_chave (escolhido
# no dialogo do filtro), ou fica o que ja estava.
mode480_save() {
  local pair key state var
  local -a pairs
  IFS=',' read -ra pairs <<< "$1"
  for pair in "${pairs[@]}"; do
    key=${pair%%=*} state=${pair#*=}
    var=MODE480_LEVEL_$key
    [[ $(mode480_state "$key") == "$state" && -z ${!var:-} ]] && continue
    mode480_set "$key" "$state" "${!var:-}" || return 1
  done
}

deflicker_level() {
  local level
  level=$(conf_get deflicker 2> /dev/null)
  if [[ -n $level && " $DEFLICKER_LEVELS " == *" $level "* ]]; then
    printf '%s\n' "$level"
  else
    echo medium
  fi
}

# deflicker_set off|light|medium|strong: o nivel de todo o resto (a linha
# "other" da tabela); vale no proximo jogo aberto.
deflicker_set() {
  [[ " $DEFLICKER_LEVELS " == *" $1 "* ]] || return 1
  if [[ $1 == off ]]; then
    mode480_set other pure
  else
    mode480_set other filter "$1"
  fi
}

# ── Calibracao de cor ────────────────────────────────────────────
# Setup > Video Setup > Colour calibration: os parametros no fliperos.conf
# (color_CHAVE=), que o config/fliperos-color.c poe na placa: a tabela de
# gama (LUT) de cada CRTC, a matriz de cor (CTM) quando a placa tem e a
# faixa RGB do conector. Sem CTM, a saturacao e o matiz vao por software
# (color_ctm=sw): a camada config/fliperos-deflicker.c nos programas OpenGL,
# o picom no desktop. Aplicado no boot (fliperos-tty1), em cada programa
# aberto (fliperos-kms-run, fliperos-x11-run/-client) e ao gravar.
COLOR_BIN=${COLOR_BIN:-/usr/local/bin/fliperos-color}

# color_table: chave|rotulo|minimo|maximo|padrao|passo|ajuda.
color_table() {
  cat << 'TABLE'
brightness|Brightness|-50|50|0|1|Moves the whole picture up or down: raise it if dark greys are lost in black.
contrast|Contrast|50|150|100|1|Spreads or squeezes the picture around the middle grey.
gamma|Gamma|50|200|100|5|The middle greys: above 1.00 they get brighter, below darker. Black and white stay.
temperature|Colour temperature|4000|10000|6500|100|The colour of white: 6500 K is neutral, 9300 K bluish (many arcade monitors), 5000 K warm.
red_gain|Red gain|0|150|100|1|How strong red is in bright colours (the drive of the red gun).
green_gain|Green gain|0|150|100|1|How strong green is in bright colours (the drive of the green gun).
blue_gain|Blue gain|0|150|100|1|How strong blue is in bright colours (the drive of the blue gun).
red_offset|Red black level|-50|50|0|1|Red in the dark parts (the cutoff of the red gun): fixes a tinted black.
green_offset|Green black level|-50|50|0|1|Green in the dark parts (the cutoff of the green gun): fixes a tinted black.
blue_offset|Blue black level|-50|50|0|1|Blue in the dark parts (the cutoff of the blue gun): fixes a tinted black.
red_gamma|Red gamma|50|200|100|5|The middle tones of red only.
green_gamma|Green gamma|50|200|100|5|The middle tones of green only.
blue_gamma|Blue gamma|50|200|100|5|The middle tones of blue only.
saturation|Saturation|0|200|100|2|How strong the colours are: 0 is black and white.
hue|Hue|-180|180|0|2|Turns every colour around the colour wheel.
TABLE
}

# color_field CHAVE N: o campo N da linha da chave.
color_field() {
  color_table | awk -F'|' -v k="$1" -v n="$2" '$1 == k { print $n; exit }'
}

# color_get CHAVE: o valor gravado, ou o padrao.
color_get() {
  local value
  value=$(conf_get "color_$1" 2> /dev/null) || value=""
  [[ $value =~ ^-?[0-9]+$ ]] || value=$(color_field "$1" 5)
  printf '%s\n' "$value"
}

# color_set CHAVE VALOR: grava (dentro da faixa do parametro). Status 1 =
# chave ou valor invalido.
color_set() {
  local key=$1 value=$2 min max
  min=$(color_field "$key" 3)
  max=$(color_field "$key" 4)
  [[ -n $min && $value =~ ^-?[0-9]+$ ]] || return 1
  ((value < min)) && value=$min
  ((value > max)) && value=$max
  conf_set "color_$key" "$value"
}

# color_pretty CHAVE VALOR: o valor como a tela mostra (1.00, 6500 K, +5).
color_pretty() {
  case $1 in
    gamma | *_gamma) printf '%d.%02d\n' "$(($2 / 100))" "$(($2 % 100))" ;;
    temperature) printf '%s K\n' "$2" ;;
    contrast | *_gain | saturation) printf '%s%%\n' "$2" ;;
    hue) printf '%s°\n' "$2" ;;
    *) (($2 > 0)) && printf '+%s\n' "$2" || printf '%s\n' "$2" ;;
  esac
}

# color_caps: o que a placa tem, como o "fliperos-color caps" ("lut 256",
# "ctm no", "range output_csc"); sem o programa, nada.
color_caps() {
  [[ -x $COLOR_BIN ]] || { printf 'lut 0\nctm no\nrange none\n'; return 0; }
  "$COLOR_BIN" caps 2> /dev/null || true
}

# color_range: full, limited ou "" (o da placa, sem mexer).
color_range() {
  local value
  value=$(conf_get color_range 2> /dev/null) || value=""
  [[ $value == full || $value == limited ]] || value=""
  printf '%s\n' "$value"
}

color_range_set() {
  case $1 in
    full | limited) conf_set color_range "$1" ;;
    "") conf_unset color_range ;;
    *) return 1 ;;
  esac
}

# color_apply grava se a matriz vai pelo hardware ou por software e poe tudo
# na placa (o dono do video tem de estar livre: a interface grafica solta,
# ui_text). CAPS: a saida do color_caps (sem ela, pergunta).
color_apply() {
  local caps=${1:-}
  [[ -n $caps ]] || caps=$(color_caps)
  if grep -qx 'ctm yes' <<< "$caps"; then
    conf_set color_ctm hw
  else
    conf_set color_ctm sw
  fi
  [[ -x $COLOR_BIN ]] || return 0
  "$COLOR_BIN" apply >> "$FLIPEROS_LOG" 2>&1
}

# color_reset volta tudo ao padrao (a imagem como a placa manda).
color_reset() {
  local key
  while IFS='|' read -r key _; do
    conf_unset "color_$key"
  done < <(color_table)
  conf_unset color_range
}

# color_changed: algum parametro fora do padrao?
color_changed() {
  local key
  while IFS='|' read -r key _ _ _ default _; do
    [[ $(color_get "$key") == "$default" ]] || return 0
  done < <(color_table)
  [[ -n $(color_range) ]]
}
