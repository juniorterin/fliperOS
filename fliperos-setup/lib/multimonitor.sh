# shellcheck shell=bash
# Varios monitores: ate tres CRTs, um em cada saida analogica (VGA, DVI-I) da
# placa do monitor principal. O fliperos.conf guarda as saidas na ordem das
# telas dos jogos (screens=DVI-I-1,VGA-1,DVI-I-2: a tela 1, a 2 e a 3, da
# esquerda para a direita ou de cima para baixo). Sem a chave, so o monitor
# do teste de saidas (connector=).
#
#  - boot: os extras ganham o modo do principal, forcados ligados;
#  - X: um Monitor por saida, lado a lado nessa ordem (lib/xorg.sh);
#  - GroovyMAME: um .ini por jogo de varias telas com o numscreens
#    (config/fliperos-mame-screens), e o comando groovymame poe cada janela
#    na saida certa;
#  - KMS (RetroArch, frontends): so o principal fica ligado (--outputs main),
#    porque eles abrem na primeira saida conectada, que pode ser um extra.

MM_MAX=3
MAME_SCREENS=${MAME_SCREENS:-/opt/fliperos/bin/fliperos-mame-screens}

# mm_screens imprime as saidas, uma por linha, na ordem das telas dos jogos.
mm_screens() {
  local conn list
  conn=$(conf_get connector 2> /dev/null) || return 1
  list=$(conf_get screens 2> /dev/null) || list=""
  if [[ ,$list, != *",$conn,"* ]]; then
    printf '%s\n' "$conn"
    return 0
  fi
  tr ',' '\n' <<< "$list" | grep .
}

mm_count() {
  local n
  n=$(mm_screens 2> /dev/null | grep -c .)
  printf '%s\n' "$((n > 0 ? n : 1))"
}

# mm_extras imprime as saidas alem da principal, na ordem das telas.
mm_extras() {
  local conn s
  conn=$(conf_get connector 2> /dev/null) || return 0
  while IFS= read -r s; do
    [[ $s == "$conn" ]] || printf '%s\n' "$s"
  done < <(mm_screens)
}

# mm_candidates [ATUAL] imprime as saidas analogicas da placa do principal
# livres para um monitor extra (ATUAL, a do proprio monitor, conta como livre).
mm_candidates() {
  local keep=${1:-} card conn used c name
  card=$(conf_get card 2> /dev/null) || return 0
  conn=$(conf_get connector 2> /dev/null) || return 0
  used=",$(mm_screens | paste -sd,),"
  for c in $(drm_connectors); do
    [[ $(drm_card "$c") == "$card" ]] || continue
    name=$(drm_name "$c")
    drm_is_analog "$name" || continue
    [[ $name == "$conn" ]] && continue
    [[ $name != "$keep" && $used == *",$name,"* ]] && continue
    printf '%s\n' "$name"
  done
}

# mm_save SAIDA... grava a ordem das telas; so o principal apaga a chave.
mm_save() {
  local list
  if (($# <= 1)); then
    conf_unset screens
    log_info "monitores: so o principal"
    return 0
  fi
  list=$(IFS=,; printf '%s' "$*")
  conf_set screens "$list"
}

# mm_set_extra MONITOR SAIDA|off troca a saida do monitor 2 ou 3. As telas
# que ficam mantem a ordem; uma saida nova entra no fim.
mm_set_extra() {
  local slot=$1 name=$2 conn s list=() extras=() keep=()
  conn=$(conf_get connector) || return 1
  mapfile -t extras < <(mm_extras)
  if [[ $name == off ]]; then
    unset 'extras[slot-2]'
  else
    extras[slot - 2]=$name
  fi
  for s in "${extras[@]}"; do
    [[ -n $s ]] && keep+=("$s")
  done
  while IFS= read -r s; do
    [[ $s == "$conn" || " ${keep[*]} " == *" $s "* ]] && list+=("$s")
  done < <(mm_screens)
  for s in "${keep[@]}"; do
    [[ " ${list[*]} " == *" $s "* ]] || list+=("$s")
  done
  mm_save "${list[@]}"
}

# mm_orders imprime "a,b,c|a, b, c" para cada ordem possivel das telas.
mm_orders() {
  local s=() a b c
  mapfile -t s < <(mm_screens)
  case ${#s[@]} in
    2)
      printf '%s|%s\n' "${s[0]},${s[1]}" "${s[0]}, ${s[1]}" "${s[1]},${s[0]}" "${s[1]}, ${s[0]}"
      ;;
    3)
      for a in "${s[@]}"; do
        for b in "${s[@]}"; do
          [[ $b == "$a" ]] && continue
          for c in "${s[@]}"; do
            [[ $c == "$a" || $c == "$b" ]] && continue
            printf '%s|%s\n' "$a,$b,$c" "$a, $b, $c"
          done
        done
      done
      ;;
  esac
}

# mm_kernel_spec imprime o video= dos extras: o modo de boot do principal, ou
# o do preset quando o principal vem de EDID, sempre forcado ligado (um CRT
# de arcade nao tem EDID nem, muitas vezes, a carga que o DAC detecta).
mm_kernel_spec() {
  local params mode monitor card super=""
  params=$(conf_get kernel_video 2> /dev/null) || params=""
  if ! mode=$(video_boot_resolution "$params"); then
    monitor=$(conf_get monitor 2> /dev/null) || monitor=generic_15
    card=$(conf_get card 2> /dev/null) || card=""
    [[ -n $card ]] && ! drm_card_low_dotclock "$card" && super=super
    mode=$(monitor_kernel_resolution "$monitor" 60 i $super) || mode=""
  fi
  printf '%se\n' "$mode"
}

# mm_cmdline LINHA acrescenta o video= de cada monitor extra.
mm_cmdline() {
  local line=$1 spec s
  spec=$(mm_kernel_spec)
  while IFS= read -r s; do
    line=$(cmdline_set_video "$line" "$s" "$spec")
  done < <(mm_extras)
  printf '%s\n' "$line"
}

# mm_booted SAIDA: o boot atual ja tem o modo dela. Sem isso, ligar a saida
# daria o modo padrao do kernel (31 kHz), que um CRT de 15 kHz nao aguenta.
mm_booted() {
  [[ " $(< "$PROC_CMDLINE") " == *" video=$1:"* ]]
}

# mm_pending: ha monitor extra escolhido que so liga no proximo boot.
mm_pending() {
  local s
  while IFS= read -r s; do
    mm_booted "$s" || return 0
  done < <(mm_extras)
  return 1
}

# mm_outputs main|all liga so o principal (programas em KMS) ou todos (X).
mm_outputs() {
  local want=$1 card s c
  card=$(conf_get card 2> /dev/null) || return 0
  while IFS= read -r s; do
    c=$card-$s
    [[ -e $DRM_SYSFS/$c/status ]] && mm_booted "$s" || continue
    if [[ $want == main ]]; then
      [[ $(drm_status "$c") == disconnected ]] || drm_set_status "$c" off
    else
      [[ $(drm_status "$c") == connected ]] || drm_set_status "$c" on
    fi
  done < <(mm_extras)
  return 0
}

# mm_blink SAIDA apaga o monitor por uns segundos e o liga de novo, para a
# pessoa ver qual e qual.
mm_blink() {
  local name=$1 card c restore=on
  card=$(conf_get card 2> /dev/null) || return 1
  c=$card-$name
  [[ -e $DRM_SYSFS/$c/status ]] || return 1
  if [[ $name == "$(conf_get connector 2> /dev/null)" && $(conf_get forced 2> /dev/null) != 1 ]]; then
    restore=detect
  fi
  drm_set_status "$c" off
  sleep "${MM_BLINK_SECONDS:-3}"
  drm_set_status "$c" "$restore"
}

# mm_mame_prepare gera os .ini dos jogos de varias telas para o numero de
# monitores atual. Na primeira vez le o XML inteiro do GroovyMAME (cerca de
# um minuto); o comando groovymame o refaz sozinho se faltar.
mm_mame_prepare() {
  local n
  n=$(mm_count)
  ((n > 1)) || return 0
  [[ -x $MAME_SCREENS ]] || return 0
  run_logged "$MAME_SCREENS" "$n"
}
