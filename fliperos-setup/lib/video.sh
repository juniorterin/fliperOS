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
  local monitor=$1 conn flags params card
  video_apply_monitor "$monitor"
  conn=$(conf_get connector 2> /dev/null) || return 0
  flags=$(conf_get detection 2> /dev/null) || return 0
  # Em HDMI ou DVI-D, LCD e CRT pedem resultados diferentes (video_output_flags).
  if drm_is_tmds "$conn" && card=$(conf_get card 2> /dev/null); then
    video_save_result "$card-$conn" "$flags" "$monitor"
    return
  fi
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
    15khz | intel | intel240 | nvidia | edid-progressive | edid-interlaced) echo generic_15 ;;
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
#   - EDID do Switchres (o): nenhum, o EDID manda;
#   - EDID forcado no boot (d) ou boot por EDID: EDID do preset na saida;
#   - sem EDID (r, e): o modo de boot do preset; super resolucao se a placa
#     nao gera dotclock baixo; "e" no fim se foi preciso forcar a saida;
#   - EDID de fabrica com um monitor de CRT escolhido (l): um conversor
#     DisplayPort/HDMI para VGA devolve o EDID dele, de modos de 31 kHz, e a
#     saida seria tomada por LCD. Um modo "video=" nao basta: o SDL (o
#     frontend, o Setup) abre o primeiro modo da lista, o de 48 kHz do EDID, e
#     o Switchres devolve a tela a ele quando um jogo fecha. Troca-se o EDID
#     por um de 15 kHz do Switchres, como a entrada "EDID progressive" do boot.
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
  elif [[ $(cmdline_get "$(< "$PROC_CMDLINE")" drm.edid_firmware 2> /dev/null) == *"$SUPER240_EDID" ]]; then
    # A entrada "Intel 15 kHz 240p" do boot: o EDID do FliperOS com o
    # 1280x240 progressivo segue para o sistema (e nao o do preset).
    echo "video=$conn:e drm.edid_firmware=$conn:edid/$SUPER240_EDID"
  elif cmdline_get "$(< "$PROC_CMDLINE")" drm.edid_firmware > /dev/null; then
    echo "video=$conn:e drm.edid_firmware=$conn:edid/$monitor.bin"
  elif [[ $base =~ ^s?l$ ]]; then
    fw=$monitor.bin
    [[ $MONITORS_15K == *" $monitor "* ]] && fw=generic_15_super_resp.bin
    echo "video=$conn:e drm.edid_firmware=$conn:edid/$fw"
  elif [[ -n $res ]]; then
    echo "video=$conn:$res$enabled"
  elif [[ -n $enabled ]]; then
    echo "video=$conn:e"
  fi
  return 0
}

# video_boot_mode_missing: o fliperos.conf gravado antes de o "l" ganhar um
# modo de boot (um conversor com EDID proprio e um CRT escolhido) esta sem
# kernel_video, e o menu sobe a 48 kHz. Status 0 quando o modo de agora
# existe e o gravado nao: escolher o mesmo monitor de novo o regrava.
video_boot_mode_missing() {
  local conn flags monitor params
  conn=$(conf_get connector 2> /dev/null) || return 1
  flags=$(conf_get detection 2> /dev/null) || return 1
  monitor=$(conf_get monitor 2> /dev/null) || return 1
  [[ -z $(conf_get kernel_video 2> /dev/null) ]] || return 1
  params=$(video_kernel_params "$conn" "$flags" "$monitor" 2> /dev/null) || return 1
  [[ -n $params ]]
}

# video_boot_resolution PARAMS imprime o modo (640x480iS) de um conjunto de
# parametros, ou nada se o modo vem de EDID.
video_boot_resolution() {
  local word spec
  # O 240p da Intel vem de um EDID, nao de um modo da linha video=.
  [[ $1 == *"drm.edid_firmware="*"$SUPER240_EDID"* ]] && { echo "$SUPER240_MODE"; return 0; }
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
    geometry_res_clear
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
VIDEO_CONF_KEYS="gpu gpu_id driver card connector detection forced low_dotclock_pci low_dotclock_min kernel_video boot_resolution fb_map
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

# video_output_flags CARD NOME FLAGS MONITOR: o resultado do teste para esta
# saida. Um CRT em HDMI ou DVI-D (por um conversor ativo) nao recebe dotclock
# baixo, mesmo de uma placa que o gera: sem o "s", ele fica na super resolucao.
# Num LCD o modo vem do EDID dele, e o "s" fica como a placa manda.
video_output_flags() {
  local card=$1 name=$2 flags=$3 monitor=$4
  if drm_is_tmds "$name"; then
    flags=${flags#s}
    [[ $monitor == lcd ]] && drm_card_low_dotclock "$card" && flags=s$flags
  fi
  printf '%s\n' "$flags"
}

# video_save_result CONECTOR FLAGS MONITOR grava o resultado validado do
# teste de saidas para o instalador e para o sistema instalado.
video_save_result() {
  local c=$1 flags=$2 monitor=$3 card name base params min id
  card=$(drm_card "$c")
  name=$(drm_name "$c")
  flags=$(video_output_flags "$card" "$name" "$flags" "$monitor")
  base=${flags%a}
  params=$(video_kernel_params "$name" "$flags" "$monitor") || return 1
  # Outra placa ou outra saida principal: os monitores extras sao escolhidos
  # de novo (Video Setup > Multiple Monitors).
  if [[ $(conf_get card 2> /dev/null) != "$card" || $(conf_get connector 2> /dev/null) != "$name" ]]; then
    conf_unset screens
  fi
  conf_set gpu "$(drm_card_name "$card")"
  # O ID do PCI: com ele o sistema instalado percebe que a placa foi trocada
  # (video_hw_changed).
  if id=$(drm_card_id "$card"); then
    conf_set gpu_id "$id"
  else
    conf_unset gpu_id
  fi
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
  # Sem dotclock baixo, o Switchres e o MAME trabalham com super resolucao,
  # tambem quando o modo de boot vem de um EDID.
  if [[ $base =~ ^(e|r|o|do|l)$ && $monitor != lcd ]]; then
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

# ── Troca de hardware de video ───────────────────────────────────
# Trocar a placa de video (ou a CPU que tem GPU) deixa o fliperos.conf, o
# Switchres, o RetroArch e a linha do kernel com os valores da placa antiga:
# um 320x240 numa Intel, que nao gera esse clock, nao da imagem. O boot
# percebe a troca (video_hw_boot_check, sem tela) e grava um modo seguro para
# a placa nova; o aviso antes do launcher (screen_hw_change_check) refaz o
# teste de saidas. O Recovery Mode da midia continua como ultimo recurso.

# video_main_card imprime a placa que o boot usa (a VGA de boot da BIOS), ou
# a primeira.
video_main_card() {
  local card
  for card in $(drm_cards); do
    [[ $(cat "$DRM_SYSFS/$card/device/boot_vga" 2> /dev/null) == 1 ]] && { printf '%s\n' "$card"; return 0; }
  done
  drm_cards | head -n 1
}

# video_hw_changed: a placa principal do fliperos.conf nao esta mais aqui.
# Status 0 e imprime "NOME ANTIGO|NOME NOVO" se trocou; 1 se e a mesma ou se
# nao ha o que comparar (sem teste de saidas feito, ou sem placa). Uma placa a
# mais ou a menos que nao e a principal (uma GPU de CPU nova com a AMD ainda
# la) nao conta. Instalacao antiga, sem gpu_id: vale o driver; se ele bate,
# e a mesma placa e o ID fica gravado.
video_hw_changed() {
  local saved_id saved_driver card id driver first
  conf_get card > /dev/null 2>&1 || return 1
  saved_id=$(conf_get gpu_id 2> /dev/null) || saved_id=""
  saved_driver=$(conf_get driver 2> /dev/null) || saved_driver=""
  first=$(video_main_card)
  [[ -n $first ]] || return 1
  for card in $(drm_cards); do
    id=$(drm_card_id "$card" 2> /dev/null) || id=""
    driver=$(drm_card_driver "$card" 2> /dev/null) || driver=""
    if [[ -n $saved_id ]]; then
      [[ $id == "$saved_id" ]] && return 1
    elif [[ -n $driver && $driver == "$saved_driver" ]]; then
      [[ -n $id ]] && conf_set gpu_id "$id"
      return 1
    fi
  done
  printf '%s|%s\n' "$(conf_get gpu 2> /dev/null || echo "the old card")" "$(drm_card_name "$first")"
  return 0
}

# video_hw_safe_connector CARD imprime a primeira saida analogica da placa
# (cardN-VGA-1): o modo seguro so existe para CRT. Status 1 sem ela.
video_hw_safe_connector() {
  local c
  for c in $(drm_connectors); do
    [[ $(drm_card "$c") == "$1" ]] && drm_is_analog "$(drm_name "$c")" && { printf '%s\n' "$c"; return 0; }
  done
  return 1
}

# video_hw_boot_check (no boot, fliperos-driver-trial.service, sem tela): a
# placa trocou. Marca o aviso (hw_changed) e grava para a placa nova o modo
# que ela aguenta (nativo se gera dotclock baixo, super resolucao se nao),
# na primeira saida analogica, com o monitor que ja estava; depois reinicia
# UMA vez (hw_safe_boot guarda o ID da placa e impede o laco). Sem saida
# analogica, ou com monitor LCD, so marca o aviso.
video_hw_boot_check() {
  local id card conn monitor flags change tries
  is_installed && ! is_live || return 0
  conf_get card > /dev/null 2>&1 || return 0
  # A placa pode demorar a aparecer no sysfs (o servico nao espera o udev).
  for ((tries = 0; tries < ${HW_BOOT_WAIT:-20}; tries++)); do
    [[ -n $(drm_cards) ]] && break
    sleep 0.5
  done
  change=$(video_hw_changed) || return 0
  card=$(video_main_card)
  id=$(drm_card_id "$card" 2> /dev/null) || id=unknown
  [[ $(conf_get hw_safe_boot 2> /dev/null) == "$id" ]] && return 0
  log_warn "placa de video trocada: ${change/|/ -> }"
  # O nome da placa antiga, para o aviso: o modo seguro grava o da nova.
  conf_set hw_old_gpu "${change%%|*}"
  conf_set hw_changed 1
  # A saida analogica da placa nova so aparece com o amdgpu.dc=0 (a Tonga,
  # lib/bootloader.sh): reinicia uma vez com ele antes de procurar a saida
  # (hw_dc_boot impede o laco).
  if amdgpu_dc_pending && [[ $(conf_get hw_dc_boot 2> /dev/null) != "$id" ]]; then
    conf_set hw_dc_boot "$id"
    boot_apply || return 1
    run_logged systemctl reboot
    return 0
  fi
  conf_set hw_safe_boot "$id"
  monitor=$(conf_get monitor 2> /dev/null) || monitor=generic_15
  conn=$(video_hw_safe_connector "$card") || return 0
  [[ $monitor == lcd ]] && return 0
  flags=e
  drm_card_low_dotclock "$card" && flags=se
  # O que era da placa antiga: os monitores extras e o degrau do grid da NVIDIA.
  conf_unset screens
  conf_unset low_dotclock_pci
  conf_unset low_dotclock_min
  video_save_result "$conn" "$flags" "$monitor" || return 1
  xorg_generate
  boot_apply || return 1
  run_logged systemctl reboot
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
  if ((changed)); then
    ev_step 50 "Rebuilding the initramfs"
    ev_run "$UPDATE_INITRAMFS" -u || return 1
  fi
  # A tela de progresso so da a operacao por feita com o 100%.
  ev_step 100 "The boot is ready"
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
    drm_output_low_dotclock "$card" "$(conf_get connector 2> /dev/null)" || low=0
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

# video_connector_modes [CARD CONECTOR] imprime "modo|descricao" dos modos que
# o kernel lista na saida (o EDID do monitor, mais o modo da linha video=),
# sem repetir. E a lista de um monitor que nao tem tabela propria (LCD, VESA):
# o que a saida mostra e o que o hardware comporta.
video_connector_modes() {
  local card=${1:-} conn=${2:-}
  [[ -n $card ]] || card=$(conf_get card) || return 1
  [[ -n $conn ]] || conn=$(conf_get connector) || return 1
  drm_modes "$card-$conn" | awk '
    /^[0-9]+x[0-9]+i?$/ && !seen[$0]++ {
      label = $0
      if (sub(/i$/, "", label)) label = label " interlaced"
      print $0 "|" label
    }'
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
  video_custom_active && custom_boot_refresh
  return 0
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

# ── O modo de boot do monitor custom ─────────────────────────────
# O Switchres (jogos, RetroArch) calcula o modo com o crt_range0; o modo de
# boot (console, Setup, frontend, desktop) vem da tabela fixa do kernel, com
# outros porches e sync: com o custom ativo, o frontend e o desktop ficavam
# deslocados em relacao aos jogos. O Xorg e o kernel (por um EDID) passam a
# usar a modeline que o Switchres calcula para o mesmo modo.
CUSTOM_EDID=${CUSTOM_EDID:-fliperos-custom.bin}

# custom_modeline MODO imprime a modeline (formato do Xorg) que o Switchres
# calcula para o modo de boot da tabela (640x480iS...) com o switchres.ini de
# agora. Status 1 sem Switchres ou se ele devolve outro tamanho ou outro
# entrelacamento: o modo da tabela fica.
custom_modeline() {
  local mode=$1 table name w h r line want_i=0
  have switchres || return 1
  table=$(mode_modeline "$mode") || return 1
  [[ $table == *Interlace* ]] && want_i=1
  name=${table#\"}
  name=${name%%\"*}
  read -r w h r <<< "$(mode_whr "$mode")"
  line=$(switchres "$w" "$h" "$r" --ini "$SWITCHRES_INI" --calc 2>&1 | grep -m1 'Modeline "') || return 1
  awk -v name="$name" -v w="$w" -v h="$h" -v want_i="$want_i" '{
    if ($2 != w || $6 != h) exit 1
    i = 0; hs = "-HSync"; vs = "-VSync"
    for (n = 10; n <= NF; n++) {
      f = tolower($n)
      if (f == "interlace") i = 1
      else if (f == "+hsync") hs = "+HSync"
      else if (f == "-hsync") hs = "-HSync"
      else if (f == "+vsync") vs = "+VSync"
      else if (f == "-vsync") vs = "-VSync"
    }
    if (i != want_i) exit 1
    printf "\"%s\" %s %s %s %s %s %s %s %s %s%s %s %s\n", name, $1, $2, $3, $4, $5, $6, $7, $8, $9, (i ? " Interlace" : ""), hs, vs
  }' <<< "${line##*\" }"
}

# custom_edid grava o EDID com a modeline do Switchres para o modo de boot
# (entra no initramfs pelo fliperos-edid-hook; boot_apply o refaz). Sem o
# monitor custom, ou sem uma modeline, apaga o arquivo e devolve status 1.
custom_edid() {
  local mode modeline
  rm -f "$EDID_DIR/$CUSTOM_EDID"
  video_custom_active || return 1
  mode=$(conf_get boot_resolution 2> /dev/null) || return 1
  modeline=$(custom_modeline "$mode") || return 1
  mkdir -p "$EDID_DIR"
  printf '%s\n' "$modeline" | "$EDID_MODES" "$EDID_DIR/$CUSTOM_EDID" 2>> "$FLIPEROS_LOG"
}

# custom_edid_cmdline LINHA CONECTOR: com o EDID do custom gravado, o video=
# da saida analogica fica so com as opcoes (o "e" e o panel_orientation) e o
# drm.edid_firmware aponta para ele: o modo preferido passa a ser o do
# Switchres, nao o da tabela do kernel. Uma linha que ja traz um EDID (boot
# por EDID, 240p da Intel, console em pe) fica como esta.
custom_edid_cmdline() {
  local line=$1 conn=$2 spec opts=""
  if [[ -z $conn || ! -f $EDID_DIR/$CUSTOM_EDID ]] || ! drm_is_analog "$conn" || ! video_custom_active ||
    cmdline_get "$line" drm.edid_firmware > /dev/null ||
    ! spec=$(cmdline_video_spec "$line" "$conn"); then
    printf '%s\n' "$line"
    return
  fi
  [[ $spec == *,* ]] && opts=,${spec#*,}
  line=$(cmdline_set_video "$line" "$conn" "e$opts")
  cmdline_set "$line" drm.edid_firmware "$conn:edid/$CUSTOM_EDID"
}

# custom_boot_refresh refaz o que depende do crt_range0: o EDID do kernel e
# o Modeline do Xorg (o desktop). Vale no proximo boot.
custom_boot_refresh() {
  custom_edid || true
  if [[ -f ${XORG_CONF:-/nonexistent} ]]; then
    xorg_generate || true
  fi
  return 0
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
  custom_boot_refresh
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
  geometry_res_clear
  video_apply_monitor "$monitor"
  custom_boot_refresh
  log_info "geometria: padrao do monitor $monitor"
}

# ── Geometria por resolucao ──────────────────────────────────────
# A OSD guarda a geometria de cada resolucao que o jogo usa, em
# geometry_<LARGURA>x<ALTURA><p|i>= (640x480i, 320x240p...) no fliperos.conf:
# so os tres ajustes, "H_SIZE:H_SHIFT:V_SHIFT" (1.050:3:-2), que o Switchres
# aplica em cima do monitor em uso. Sem a chave vale o crt_range de todas.

geometry_res_key_valid() {
  [[ ${1:-} =~ ^[0-9]+x[0-9]+[pi]$ ]]
}

geometry_res_value_valid() {
  [[ ${1:-} =~ ^[0-9]+(\.[0-9]+)?:-?[0-9]+:-?[0-9]+$ ]]
}

# geometry_res_list imprime "RESOLUCAO=H_SIZE:H_SHIFT:V_SHIFT", uma por linha.
geometry_res_list() {
  local line
  [[ -f $FLIPEROS_CONF ]] || return 0
  while IFS= read -r line || [[ -n $line ]]; do
    [[ $line == geometry_*=* ]] && printf '%s\n' "${line#geometry_}"
  done < "$FLIPEROS_CONF"
  return 0
}

# geometry_res_clear esquece a geometria de todas as resolucoes (outro
# monitor, ou a geometria de volta ao padrao).
geometry_res_clear() {
  local item
  while IFS= read -r item; do
    conf_unset "geometry_${item%%=*}"
  done < <(geometry_res_list)
  return 0
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
  custom_boot_refresh
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

# geometry_cli status|reset|set RANGE|set-res RES AJUSTES|reset-res RES: a
# geometria pelo painel web e pela OSD, pelas mesmas funcoes das telas. status
# imprime monitor=, label=, range= (o crt_range salvo; vazio, o do preset
# vale), preset=, tool= (1: o grid do Switchres existe) e resolutions= (as
# geometrias por resolucao, "640x480i=1.050:3:-2" separadas por espaco). set
# grava um crt_range digitado, como o Custom monitor: status 2 se nao e um
# crt_range (ou o monitor e LCD), 3 se e de outra faixa de frequencia que a do
# monitor escolhido. set-res/reset-res guardam e apagam a geometria de uma
# resolucao (status 2 se a resolucao ou os ajustes estao mal escritos); reset
# apaga tambem as de todas as resolucoes.
geometry_cli() {
  local base range rfreq bfreq
  base=$(conf_get monitor 2> /dev/null) || base=""
  case ${1:-} in
    status)
      printf 'monitor=%s\nlabel=%s\nrange=%s\npreset=%s\ntool=%s\nresolutions=%s\n' "$base" "$(video_monitor_label 2> /dev/null)" \
        "$(conf_get geometry 2> /dev/null)" "$(video_preset_range "$base" 2> /dev/null)" "$(have geometry && echo 1 || echo 0)" \
        "$(geometry_res_list | paste -sd' ' -)"
      ;;
    reset)
      if conf_get geometry > /dev/null 2>&1; then
        geometry_reset
        geometry_boot_apply
      else
        geometry_res_clear
      fi
      ;;
    set-res)
      geometry_res_key_valid "${2:-}" && geometry_res_value_valid "${3:-}" || return 2
      conf_set "geometry_$2" "$3"
      ;;
    reset-res)
      geometry_res_key_valid "${2:-}" || return 2
      conf_unset "geometry_$2"
      ;;
    set)
      range=${2//[[:space:]]/}
      [[ -n $base && $base != lcd ]] && crt_range_valid "$range" || return 2
      rfreq=$(crt_range_frequency "$range") || return 2
      bfreq=$(monitor_frequency "$base") || return 2
      [[ $rfreq == "$bfreq" ]] || return 3
      geometry_apply "$range" && geometry_boot_apply
      ;;
    *) return 2 ;;
  esac
}

# geometry_boot_apply: sem a tela do Video Setup (o painel web), grava logo a
# linha do kernel e o initramfs com o EDID do custom, no sistema instalado.
geometry_boot_apply() {
  is_installed && ! is_live || return 0
  boot_apply
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

# ── Jogos entrelacados num tubo de 15 kHz ────────────────────────
# Setup > Video Setup > Interlaced hacks: o metodo de cada aplicacao para o
# que tem mais de 240 linhas (480, 448, 384...), numa tabela de tres colunas:
#   240p    o hack de 640x240 progressivo (sem flicker, metade das linhas)
#   filter  entrelacado com o filtro de flicker (config/fliperos-deflicker.c),
#           no nivel da aplicacao (light, medium, strong)
#   pure    entrelacado sem o filtro (nitido, com o flicker)
# O filtro liga em qualquer modo entrelacado (o flag do modo no DRM ou no
# xrandr), de qualquer altura, nao so no 640x480i.
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
pcsx2x6|PCSX2x6|pcsx2x6|240p,filter,pure|240p|x11|Namco System 246/256 arcade games.
duckstation|DuckStation|duckstation|240p,filter,pure|240p|x11|PlayStation (the few interlaced games, like Tekken 3 menus or Tobal 2).
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
desktop|Desktop|desktop|filter,pure|filter|desktop|The LXDE desktop, when Screen Resolution puts it in an interlaced mode.
other|Other programs|other|filter,pure|filter|other|Custom games and any other program in an interlaced mode.
TABLE
}

# mode480_field CHAVE N: o campo N da linha da chave.
mode480_field() {
  mode480_table | awk -F'|' -v k="$1" -v n="$2" '$1 == k { print $n; exit }'
}

# mode480_key_of PROGRAMA: a chave da linha do programa ou do core na tabela;
# fora dela, a "other".
mode480_key_of() {
  local key
  key=$(mode480_table | awk -F'|' -v p="$1" '{ n = split($3, a, " "); for (i = 1; i <= n; i++) if (a[i] == p) { print $1; exit } }')
  printf '%s\n' "${key:-other}"
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
      filter) now="Now: interlaced, filter $(mode480_level "$key")." ;;
      *) now="Now: interlaced, no filter." ;;
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
  log_info "Interlaced: $key = $state ($level)"
}

# mode480_core_ini NOME 0|1 grava o switchres.ini do core: o CRT SwitchRes
# do RetroArch o le por cima do /etc/switchres.ini. Sem o cabecalho
# "# FliperOS", as atualizacoes nao o regravam (fliperos-rootfs.sh).
mode480_core_ini() {
  local name=$1 dir file
  dir="$RA_HOME/config/$name"
  file="$dir/$name.switchres.ini"
  mkdir -p "$dir" || return 1
  printf '# Setup > Video Setup > Interlaced hacks: interlace 0 = 240p, 1 = interlaced.\ninterlace %s\n' "$2" > "$file" || return 1
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

# ── Scanlines num monitor de 31 kHz ──────────────────────────────
# Setup > Video Setup > Scanlines, so com um monitor de 31 kHz: num jogo de
# 240 linhas dobrado para 480, a ultima linha da tela de cada linha do jogo
# escurece, como o espaco entre as linhas de um tubo de 15 kHz. As camadas
# config/fliperos-deflicker.c (OpenGL) e config/fliperos-vkfps.c (Vulkan) leem
# no fliperos.conf scanlines=on|off e scanlines_CHAVE=, so com frequency=31k (o
# monitor trocado para 15 kHz nao fica com elas), e o mudado vale na hora,
# mesmo com o jogo aberto. O preview (gui/scanline-preview.py) passa os
# valores pelo arquivo de FLIPEROS_SCANLINES_FILE.

# scanline_table: chave|rotulo|minimo|maximo|padrao|passo|ajuda (a mesma
# forma do color_table; o passo e o das setas do preview).
scanline_table() {
  cat << 'TABLE'
strength|Darkness|5|100|50|5|How dark the gaps between the game lines are.
thickness|Thickness|10|90|50|10|The dark part of each game line (only with 3+ screen lines per game line).
height|Line height|0|8|0|1|Screen lines per game line. 0 = automatic: 2 at 480 lines, none at 240.
brightness|Brightness boost|100|200|115|5|Makes up for the light the dark lines take away.
TABLE
}

scanline_field() {
  scanline_table | awk -F'|' -v k="$1" -v n="$2" '$1 == k { print $n; exit }'
}

# scanline_get CHAVE: o valor gravado, ou o padrao.
scanline_get() {
  local value
  value=$(conf_get "scanlines_$1" 2> /dev/null) || value=""
  [[ $value =~ ^[0-9]+$ ]] || value=$(scanline_field "$1" 5)
  printf '%s\n' "$value"
}

# scanline_set CHAVE VALOR: grava dentro da faixa (a altura 1 vira 2: uma
# linha da tela por linha do jogo nao deixa espaco entre elas). Status 1 =
# chave ou valor invalido.
scanline_set() {
  local key=$1 value=$2 min max
  min=$(scanline_field "$key" 3)
  max=$(scanline_field "$key" 4)
  [[ -n $min && $value =~ ^[0-9]+$ ]] || return 1
  ((value < min)) && value=$min
  ((value > max)) && value=$max
  [[ $key == height && $value == 1 ]] && value=2
  conf_set "scanlines_$key" "$value"
}

# scanline_pretty CHAVE VALOR: o valor como a tela mostra.
scanline_pretty() {
  case $1 in
    height) (($2 == 0)) && echo "Automatic" || printf '%s screen lines\n' "$2" ;;
    *) printf '%s%%\n' "$2" ;;
  esac
}

# scanlines_available: o monitor e de 31 kHz?
scanlines_available() {
  [[ $(conf_get frequency 2> /dev/null) == 31k ]]
}

scanlines_on() {
  [[ $(conf_get scanlines 2> /dev/null) == on ]]
}

# scanlines_set_on on|off
scanlines_set_on() {
  [[ $1 == on || $1 == off ]] || return 1
  conf_set scanlines "$1"
  log_info "Scanlines: $1"
}

# scanline_reset: os ajustes voltam ao padrao (ligadas ou nao, fica como esta).
scanline_reset() {
  local key
  while IFS='|' read -r key _; do
    conf_unset "scanlines_$key"
  done < <(scanline_table)
}
