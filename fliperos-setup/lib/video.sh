# shellcheck shell=bash
# Teste de saidas e configuracao de video, portados do gatools do
# GroovyArcade (video/video.sh): test_all_connectors, test_connector,
# configure_from_connector e inform_user. Nada aqui chama o gum; as telas
# (screens/output-test.sh, screens/testing-results.sh) conduzem a conversa.
#
# Letras de resultado, as mesmas do gatools:
#   s  a placa gera dotclock baixo (radeon, amdgpu)
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
# fliperos.conf (set_monitor do gatools).
video_apply_monitor() {
  local monitor=$1
  ini_set "$SWITCHRES_INI" monitor "$monitor"
  [[ -f $MAME_INI ]] && ini_set "$MAME_INI" monitor "$monitor"
  conf_set monitor "$monitor"
  conf_set frequency "$(monitor_frequency "$monitor" || echo lcd)"
  log_info "monitor: $monitor"
}

# Chaves do fliperos.conf que dependem da placa e da saida: e o que o
# Recovery Mode leva para o disco quando a placa foi trocada. A orientacao
# e do gabinete, nao da placa, e so vai se foi escolhida nesta sessao.
VIDEO_CONF_KEYS="gpu driver card connector detection forced kernel_video boot_resolution fb_map
  monitor frequency geometry custom_width custom_height custom_refresh"
VIDEO_CONF_KEEP="orientation"

# video_save_result CONECTOR FLAGS MONITOR grava o resultado validado do
# teste de saidas para o instalador e para o sistema instalado.
video_save_result() {
  local c=$1 flags=$2 monitor=$3 card name base params
  card=$(drm_card "$c")
  name=$(drm_name "$c")
  base=${flags%a}
  params=$(video_kernel_params "$name" "$flags" "$monitor") || return 1
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
  fi
  if [[ $flags == *a ]]; then
    ini_set "$SWITCHRES_INI" interlace_force_even 1
  fi
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
  local monitor freq card low=1
  monitor=$(conf_get monitor) || monitor=generic_15
  freq=$(monitor_frequency "$monitor") || return 1
  card=$(conf_get card) || card=""
  if [[ -n $card ]] && ! drm_card_low_dotclock "$card"; then
    low=0
  fi
  monitor_resolutions "$freq" "$low"
}

# video_set_resolution MODO troca o modo de boot da saida configurada,
# mantendo o "e" (saida forcada) e as opcoes como panel_orientation.
video_set_resolution() {
  local mode=$1 conn params spec opts="" enabled=""
  conn=$(conf_get connector) || return 1
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

# video_set_custom_edid EDID troca o modo de boot por um EDID proprio
# (resolucao personalizada, gerada pelo Switchres).
video_set_custom_edid() {
  local edid=$1 conn params
  conn=$(conf_get connector) || return 1
  params=$(conf_get kernel_video) || params=""
  params=$(cmdline_without_video "$params")
  params="video=$conn:e drm.edid_firmware=$conn:edid/$edid ${params}"
  conf_set kernel_video "${params% }"
  conf_set boot_resolution "custom"
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

geometry_parse() {
  sed -n 's/^.*Final crt_range: //p' <<< "$1" | tail -1
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
