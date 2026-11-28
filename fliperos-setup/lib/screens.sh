# shellcheck shell=bash
# Troca de tela pelo cabo (Video Setup > Screen switch): um CRT de 15 kHz e um
# monitor de 31 kHz (um monitor de PC, um plasma EDTV) na mesma saida, um de
# cada vez. O FliperOS ve pelo EDID qual deles esta no cabo e usa o video
# daquela tela (o monitor, a resolucao, a geometria), sem reiniciar.
#
# Cada tela e um perfil em /etc/fliperos/screens/ID.conf: as chaves de video
# do fliperos.conf (video_snapshot), o EDID que a identifica e um nome. A
# "home" e o tubo de 15 kHz da ligacao (quase sempre sem EDID); as outras tem
# por id a fp do EDID (config/fliperos-ddc). O fliperos.conf tem o video da
# tela ativa (screen_active=), e o perfil dela recebe o que mudou quando ela
# sai.
#
# A seguranca do tubo manda no desenho:
#  - a linha do kernel e sempre a da home: o boot comeca no modo do tubo e o
#    31 kHz so entra depois de o EDID do outro monitor ser lido. Uma tela de
#    31 kHz que recebe 15 kHz so fica sem imagem; o contrario estraga o tubo.
#    Com outra tela ativa o boot_apply nao grava nada (fica pendente para a
#    volta da home), nem o EDID do monitor custom;
#  - a linha da home leva o modo num EDID (fliperos-screen.bin), nao no
#    video=: o modo do video= fica para sempre na lista da saida, e o frontend
#    (SDL) abriria nele no plasma. Com o EDID, trocar o drm.edid_firmware (o
#    kernel aceita com tudo ligado) e reler a saida troca a lista inteira, e o
#    SDL, o X, o Qt e o RetroArch abrem no modo preferido do EDID novo;
#  - do tubo para a tela de 31 kHz nao reinicia (ela responde no DDC, e o
#    driver le o EDID novo). Do monitor de 31 kHz de volta ao tubo no mesmo
#    boot, sim: o amdgpu e o radeon guardam o EDID ate um monitor responder no
#    DDC, e o tubo nao responde (screens_dirty). Com o gabinete desligado na
#    troca, o boot e o do tubo e nada reinicia a mais;
#  - o vigia (--screen-watch, fliperos-screen-watch.service) le o cabo 5 vezes
#    por segundo com o monitor de 31 kHz ligado. Se o cabo dele sai, o sinal e
#    cortado na hora (a saida desligada e o que esta na tela fechado: um
#    programa aberto segue no modo dele) e o gabinete reinicia no modo do tubo.
#
# Fica de fora: saida digital (um conversor de HDMI ou DisplayPort para VGA
# responde com o EDID dele, de 31 kHz, com o tubo atras), ponte DisplayPort,
# Multiple Monitors e monitor em pe.

SCREENS_DIR=${SCREENS_DIR:-$FLIPEROS_ETC/screens}
SCREEN_EDID=${SCREEN_EDID:-fliperos-screen.bin}
SCREEN_DDC=${SCREEN_DDC:-/opt/fliperos/bin/fliperos-ddc}
SCREEN_RUN=${SCREEN_RUN:-/run/fliperos}
SCREEN_PROC=${SCREEN_PROC:-/proc}
# O monitor de uma tela nova de 31 kHz: o 640x480 de 31,5 kHz do X e do VGA.
SCREEN_31K=${SCREEN_31K:-vesa_480}
SCREEN_HOME=home

screens_on() {
  [[ $(conf_get screen_switch 2> /dev/null) == on ]]
}

screens_active() {
  conf_get screen_active 2> /dev/null || echo "$SCREEN_HOME"
}

# screens_away: a troca ligada e outra tela, que nao a home, no cabo.
screens_away() {
  screens_on && [[ $(screens_active) != "$SCREEN_HOME" ]]
}

screens_file() {
  printf '%s/%s.conf\n' "$SCREENS_DIR" "$1"
}

# screens_list imprime os ids das telas, a home primeiro.
screens_list() {
  local f id
  [[ -d $SCREENS_DIR ]] || return 0
  [[ -f $(screens_file "$SCREEN_HOME") ]] && echo "$SCREEN_HOME"
  for f in "$SCREENS_DIR"/*.conf; do
    [[ -f $f ]] || continue
    id=${f##*/}
    id=${id%.conf}
    [[ $id == "$SCREEN_HOME" ]] || printf '%s\n' "$id"
  done
}

# screens_label ID: "Nome (monitor)".
screens_label() {
  local file name monitor
  file=$(screens_file "$1")
  name=$(conf_get name "$file" 2> /dev/null) || name=$1
  monitor=$(conf_get monitor "$file" 2> /dev/null) || monitor=""
  printf '%s%s\n' "$name" "${monitor:+ ($(monitor_label "$monitor"))}"
}

# screens_available: a troca serve a esta ligacao? Sem servir, imprime o
# motivo e da status 1.
screens_available() {
  local conn
  if ! conn=$(conf_get connector 2> /dev/null); then
    echo "Run the output test first (Video Setup > Test the video outputs)."
    return 1
  fi
  if ! drm_is_analog "$conn"; then
    echo "It needs the monitors on an analog output (VGA or DVI-I). On $conn a converter answers with its own 31 kHz EDID even with the tube behind it."
    return 1
  fi
  if drm_dp_bridge "$conn"; then
    echo "Not on a VGA output that comes from a DisplayPort bridge: the bridge answers for the monitor."
    return 1
  fi
  if (($(mm_count) > 1)); then
    echo "Not with Multiple Monitors: one monitor at a time on the output."
    return 1
  fi
  if [[ $(conf_get orientation 2> /dev/null || echo horizontal) != horizontal ]]; then
    echo "Only with the monitor horizontal."
    return 1
  fi
  return 0
}

# screens_home_ok: o monitor de agora pode ser a home (um CRT de 15 ou 25 kHz:
# o boot de todas as telas e o dele).
screens_home_ok() {
  local monitor freq
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  freq=$(monitor_frequency "$monitor" 2> /dev/null) || freq=""
  if [[ $freq != 15k && $freq != 25k ]]; then
    echo "Turn it on with the 15 kHz monitor on the cable and chosen in Monitor Type: every start begins in its mode."
    return 1
  fi
  return 0
}

# ── Os perfis ───────────────────────────────────────────────────

# screens_save ID: o video de agora (video_snapshot) no perfil, com o EDID e
# o nome que ele ja tinha.
screens_save() {
  local file edid name
  file=$(screens_file "$1")
  edid=$(conf_get edid "$file" 2> /dev/null) || edid=none
  name=$(conf_get name "$file" 2> /dev/null) || name=$1
  mkdir -p "$SCREENS_DIR"
  {
    printf 'edid=%s\nname=%s\n' "$edid" "$name"
    video_snapshot
  } > "$file.tmp" && mv -f "$file.tmp" "$file"
}

# screens_create ID EDID NOME MONITOR: o perfil de uma tela nova. A linha do
# kernel guardada e a de agora (a da home): ela nunca vem de outra tela.
screens_create() {
  local id=$1 edid=$2 name=$3 monitor=$4 file res kv
  file=$(screens_file "$id")
  # O nome vem do monitor: nada que quebre as linhas "a|b" dos menus.
  name=${name//[|=$'\n\t']/ }
  res=$(monitor_kernel_resolution "$monitor" 2> /dev/null) || res=""
  kv=$(conf_get kernel_video 2> /dev/null) || kv=""
  mkdir -p "$SCREENS_DIR"
  {
    printf 'edid=%s\nname=%s\nmonitor=%s\n' "$edid" "$name" "$monitor"
    printf 'frequency=%s\n' "$(monitor_frequency "$monitor" 2> /dev/null || echo lcd)"
    [[ -n $kv ]] && printf 'kernel_video=%s\n' "$kv"
    [[ -n $res ]] && printf 'boot_resolution=%s\n' "$res"
  } > "$file"
}

# screens_enable: liga a troca com o monitor de agora como home. A linha do
# kernel passa a levar o modo num EDID (vale depois de reiniciar).
screens_enable() {
  screens_available > /dev/null && screens_home_ok > /dev/null || return 1
  mkdir -p "$SCREENS_DIR"
  rm -f "$(screens_file "$SCREEN_HOME")"
  conf_set screen_switch on
  conf_set screen_active "$SCREEN_HOME"
  conf_unset screen_boot_pending
  conf_set edid none "$(screens_file "$SCREEN_HOME")"
  conf_set name "15 kHz monitor" "$(screens_file "$SCREEN_HOME")"
  screens_save "$SCREEN_HOME"
  log_info "screens: troca de tela ligada, home $(conf_get monitor 2> /dev/null)"
  boot_apply
}

# screens_disable desliga a troca. So com a home no cabo: a linha do kernel
# volta ao modo do video= dela.
screens_disable() {
  screens_on || return 0
  screens_away && return 1
  conf_set screen_switch off
  conf_unset screen_active
  conf_unset screen_boot_pending
  log_info "screens: troca de tela desligada"
  boot_apply
}

# screens_forget ID apaga o perfil de uma tela que nao esta no cabo (a home
# nao): na proxima vez ela volta como nova.
screens_forget() {
  [[ $1 != "$SCREEN_HOME" && $1 != "$(screens_active)" ]] || return 1
  [[ $1 =~ ^[0-9a-f]+$ ]] || return 1
  rm -f "$(screens_file "$1")" "$EDID_DIR/fliperos-screen-$1.bin"
}

# screens_drop (teste de saidas, placa nova): a troca desligada sem mexer na
# linha do kernel, que quem chama refaz. Com outra tela ativa, o video da
# home volta antes: o modo seguro de uma placa nova e o do tubo.
screens_drop() {
  screens_on || return 0
  if screens_away && [[ -f $(screens_file "$SCREEN_HOME") ]]; then
    conf_set screen_active "$SCREEN_HOME"
    video_snapshot_apply "$(screens_file "$SCREEN_HOME")" || true
  fi
  conf_set screen_switch off
  conf_unset screen_active
  conf_unset screen_boot_pending
  log_info "screens: troca de tela desligada ($1)"
}

# ── A linha do kernel ───────────────────────────────────────────

# screens_boot_edid grava o EDID do modo de boot da home (fliperos-screen.bin,
# que o hook leva ao initramfs). Status 0 se o arquivo mudou (o initramfs
# precisa ser refeito), 1 se ficou igual ou se nao ha o que gravar.
screens_boot_edid() {
  local mode modeline file=$EDID_DIR/$SCREEN_EDID tmp
  screens_on && ! screens_away || return 1
  mode=$(conf_get boot_resolution 2> /dev/null) || return 1
  modeline=$(mode_modeline "$mode") || return 1
  mkdir -p "$EDID_DIR"
  tmp=$(mktemp) || return 1
  if ! printf '%s\n' "$modeline" | "$EDID_MODES" "$tmp" 2>> "$FLIPEROS_LOG"; then
    rm -f "$tmp"
    return 1
  fi
  if cmp -s "$tmp" "$file"; then
    rm -f "$tmp"
    return 1
  fi
  mv -f "$tmp" "$file"
  chmod 644 "$file"
  return 0
}

# screens_edid_cmdline LINHA CONECTOR: com a troca ligada, o modo da saida sai
# do video= e vai para o EDID da home (o "e" e as opcoes ficam). Uma linha que
# ja traz um EDID para ela (monitor custom, boot por EDID) fica como esta: a
# lista de modos ja vem toda do arquivo.
screens_edid_cmdline() {
  local line=$1 conn=$2 spec opts="" flags
  if [[ -z $conn || ! -f $EDID_DIR/$SCREEN_EDID ]] || ! screens_on ||
    cmdline_get "$line" drm.edid_firmware > /dev/null ||
    ! spec=$(cmdline_video_spec "$line" "$conn"); then
    printf '%s\n' "$line"
    return
  fi
  [[ $spec == *,* ]] && opts=,${spec#*,}
  flags=${spec%%,*}
  # So o modo sai; o "e" (saida forcada) fica, e um tubo sem EDID precisa dele.
  [[ $flags =~ [0-9] ]] || { printf '%s\n' "$line"; return; }
  line=$(cmdline_set_video "$line" "$conn" "e$opts")
  cmdline_set "$line" drm.edid_firmware "$conn:edid/$SCREEN_EDID"
}

# screens_boot_ready CONECTOR: o boot que esta rodando tem o modo da saida num
# EDID, sem modo no video= (a troca foi ligada antes deste boot).
screens_boot_ready() {
  local line spec
  line=$(< "$PROC_CMDLINE")
  spec=$(cmdline_video_spec "$line" "$1") || return 0
  [[ ! ${spec%%,*} =~ [0-9] ]]
}

# ── O EDID da saida (drm.edid_firmware) ─────────────────────────

# screens_edid_entry CONECTOR VALOR: o arquivo do conector numa lista do
# drm.edid_firmware ("VGA-1:edid/a.bin,edid/b.bin"); a entrada sem conector
# vale para todos.
screens_edid_entry() {
  local conn=$1 value=${2%$'\n'} entry fallback=""
  local -a entries
  IFS=',' read -r -a entries <<< "$value"
  for entry in "${entries[@]}"; do
    if [[ $entry == *:* ]]; then
      [[ ${entry%%:*} == "$conn" ]] && { printf '%s\n' "${entry#*:}"; return 0; }
    elif [[ -n $entry ]]; then
      fallback=$entry
    fi
  done
  printf '%s\n' "$fallback"
}

screens_param_get() {
  screens_edid_entry "$1" "$(cat "$DRM_MODULE_PARAMS/edid_firmware" 2> /dev/null)"
}

# screens_param_set CONECTOR ARQUIVO troca so a entrada da saida no
# parametro do kernel (ARQUIVO vazio: tira; o kernel le o EDID do cabo).
screens_param_set() {
  local conn=$1 want=$2 value entry
  local -a entries out=()
  value=$(cat "$DRM_MODULE_PARAMS/edid_firmware" 2> /dev/null) || value=""
  IFS=',' read -r -a entries <<< "${value%$'\n'}"
  for entry in "${entries[@]}"; do
    [[ -z $entry ]] && continue
    [[ $entry == *:* && ${entry%%:*} == "$conn" ]] && continue
    out+=("$entry")
  done
  [[ -n $want ]] && out+=("$conn:$want")
  value=$(IFS=,; printf '%s' "${out[*]}")
  # Vazio vai como uma virgula: uma escrita de zero bytes nem chega ao
  # parametro, e o kernel pula as entradas vazias.
  [[ -n $value ]] || value=,
  log_info "screens: drm.edid_firmware <- $value"
  printf '%s' "$value" > "$DRM_MODULE_PARAMS/edid_firmware"
}

# screens_home_param CONECTOR: o EDID da saida na linha deste boot, a da home.
screens_home_param() {
  local value
  value=$(cmdline_get "$(< "$PROC_CMDLINE")" drm.edid_firmware 2> /dev/null) || return 0
  screens_edid_entry "$1" "$value"
}

# screens_param_for ID CONECTOR: o EDID que a tela pede. A home, o do boot;
# uma tela LCD, o do proprio monitor (nada); as outras, um EDID com o modo de
# boot dela (o mesmo Modeline do X), gravado aqui.
screens_param_for() {
  local id=$1 conn=$2 file monitor mode modeline out tmp
  if [[ $id == "$SCREEN_HOME" ]]; then
    screens_home_param "$conn"
    return 0
  fi
  file=$(screens_file "$id")
  monitor=$(conf_get monitor "$file" 2> /dev/null) || monitor=$SCREEN_31K
  [[ $monitor == lcd ]] && return 0
  mode=$(conf_get boot_resolution "$file" 2> /dev/null) ||
    mode=$(monitor_kernel_resolution "$monitor" 2> /dev/null) || mode=""
  out=fliperos-screen-$id.bin
  if modeline=$(mode_modeline "$mode" 2> /dev/null) && tmp=$(mktemp); then
    if printf '%s\n' "$modeline" | "$EDID_MODES" "$tmp" 2>> "$FLIPEROS_LOG"; then
      mkdir -p "$EDID_DIR"
      cmp -s "$tmp" "$EDID_DIR/$out" || { cp -f "$tmp" "$EDID_DIR/$out" && chmod 644 "$EDID_DIR/$out"; }
      rm -f "$tmp"
      printf 'edid/%s\n' "$out"
      return 0
    fi
    rm -f "$tmp"
  fi
  [[ -f $EDID_DIR/$monitor.bin ]] && printf 'edid/%s.bin\n' "$monitor"
  return 0
}

# ── O monitor do cabo ───────────────────────────────────────────

# screens_read CONECTOR: o EDID do cabo (fliperos-ddc read), ou "none".
screens_read() {
  local card out
  card=$(video_conf_card) || card=""
  out=$("$SCREEN_DDC" read "$card-$1" 2> /dev/null) || out=""
  printf '%s\n' "${out:-none}"
}

# screens_pick EDID: a tela do cabo (EDID e a saida do fliperos-ddc read).
# Imprime o id; status 2 quando e uma tela nova de 31 kHz (o id e a fp, ainda
# sem perfil). Na duvida, a home: 15 kHz numa tela de 31 so fica sem imagem.
screens_pick() {
  local info=$1 fp serial name hmin hmax vga60 id
  fp=$(sed -n 's/^fp=//p' <<< "$info")
  [[ $fp =~ ^[0-9a-f]{16}$ ]] || { echo "$SCREEN_HOME"; return 0; }
  # Uma tela que ja tem perfil (a home tambem pode ter EDID: o dongle do
  # Switchres no cabo do tubo).
  while IFS= read -r id; do
    [[ $(conf_get edid "$(screens_file "$id")" 2> /dev/null) == "$fp" ]] && { echo "$id"; return 0; }
  done < <(screens_list)
  serial=$(sed -n 's/^serial=//p' <<< "$info")
  name=$(sed -n 's/^name=//p' <<< "$info")
  hmin=$(sed -n 's/^hmin=//p' <<< "$info")
  hmax=$(sed -n 's/^hmax=//p' <<< "$info")
  vga60=$(sed -n 's/^vga60=//p' <<< "$info")
  # O EDID de um preset do Switchres (um dongle no cabo de um tubo): so um de
  # 31 kHz vira tela; um de 15 ou 25 kHz e um tubo, que fica na home.
  if [[ $serial == *Switchres* ]]; then
    if [[ $(monitor_frequency "$(monitor_normalize "$name")" 2> /dev/null) == 31k ]]; then
      echo "$fp"
      return 2
    fi
    echo "$SCREEN_HOME"
    return 0
  fi
  # Um monitor que aceita os 31,5 kHz do 640x480: pela faixa do EDID ou, sem
  # ela, pelo 640x480 a 60 Hz dos modos padrao.
  if [[ $hmax =~ ^[0-9]+$ && $hmin =~ ^[0-9]+$ ]] && ((hmax > 0)); then
    if ((hmin <= 31 && hmax >= 31)); then
      echo "$fp"
      return 2
    fi
  elif [[ $vga60 == 1 ]]; then
    echo "$fp"
    return 2
  fi
  echo "$SCREEN_HOME"
}

# ── A troca ─────────────────────────────────────────────────────

# screens_lock: uma troca por vez (o vigia e o tty1).
screens_lock() {
  mkdir -p "$SCREEN_RUN"
  exec {SCREEN_LOCK_FD}> "$SCREEN_RUN/screen.lock"
  flock -w 30 "$SCREEN_LOCK_FD"
}

screens_unlock() {
  [[ -n ${SCREEN_LOCK_FD:-} ]] && exec {SCREEN_LOCK_FD}>&-
  SCREEN_LOCK_FD=""
}

# screens_dirty: neste boot o kernel ja recebeu o EDID de uma tela de 31 kHz.
# O amdgpu e o radeon (sem DC) guardam o EDID da saida e so o soltam quando o
# monitor responde no DDC (visto no gabinete: o EDID trocado com o sistema
# ligado ficou na lista mesmo depois de um "detect"). O tubo nao responde: a
# volta para ele seria com os modos de 31 kHz. Por isso essa volta e por um
# boot novo, com a saida desligada ate la.
screens_dirty() {
  [[ -e $SCREEN_RUN/screen-edid-dirty ]]
}

# screens_reboot: a volta ao tubo depois de uma tela de 31 kHz neste boot.
screens_reboot() {
  log_warn "screens: de volta ao monitor de 15 kHz; reiniciando com a saida desligada"
  sync
  ${SCREEN_REBOOT:-systemctl reboot}
}

# screens_sync [force]: a tela do cabo vira a do sistema. Status 0 sem
# troca, 10 com troca (quem estava na tela precisa reabrir), 20 quando o
# gabinete vai reiniciar. force: refaz a saida mesmo sem troca (depois de o
# vigia ter cortado o sinal).
screens_sync() {
  local force=${1:-} conn card info target cur want have fp name rc=0 kernel=0
  screens_on || return 0
  screens_available > /dev/null || return 0
  conn=$(conf_get connector 2> /dev/null) || return 0
  card=$(video_conf_card) || return 0
  cur=$(screens_active)
  info=$(screens_read "$conn")
  target=$(screens_pick "$info") || rc=$?
  # O boot ainda com o modo no video= (a troca foi ligada e o gabinete nao
  # reiniciou): o 31 kHz nao pegaria, o frontend abriria no modo do tubo.
  if [[ $target != "$SCREEN_HOME" ]] && ! screens_boot_ready "$conn"; then
    log_warn "screens: tela de 31 kHz no cabo, mas este boot tem o modo no video=; reinicie para trocar"
    target=$SCREEN_HOME
    rc=0
  fi
  if ((rc == 2)); then
    fp=$(sed -n 's/^fp=//p' <<< "$info")
    name=$(sed -n 's/^name=//p' <<< "$info")
    [[ -n $name ]] || name="31 kHz monitor ${fp:0:4}"
    screens_create "$target" "$fp" "$name" "$SCREEN_31K"
    log_info "screens: tela nova $name ($fp)"
  fi
  want=$(screens_param_for "$target" "$conn")
  have=$(screens_param_get "$conn")
  [[ -n $force || $want != "$have" || $(drm_status "$card-$conn") != connected ]] && kernel=1
  if [[ $target == "$cur" ]] && ((!kernel)); then
    return 0
  fi
  # De volta ao tubo depois de uma tela de 31 kHz neste boot: o kernel ainda
  # tem os modos dela. A saida fica desligada, o video do tubo volta ao
  # fliperos.conf e o boot novo sobe no modo dele.
  if [[ $target == "$SCREEN_HOME" ]] && screens_dirty; then
    drm_set_status "$card-$conn" off
    if [[ $target != "$cur" ]]; then
      screens_save "$cur"
      conf_set screen_active "$target"
      video_snapshot_apply "$(screens_file "$target")" || log_warn "screens: perfil $target incompleto"
    fi
    if [[ $(conf_get screen_boot_pending 2> /dev/null) == 1 ]]; then
      conf_unset screen_boot_pending
      boot_apply || log_warn "screens: a linha do kernel pendente nao foi gravada"
    fi
    screens_reboot
    return 20
  fi
  # Para o tubo, o sinal cortado antes de tudo.
  ((kernel)) && drm_set_status "$card-$conn" off
  if [[ $target != "$cur" ]]; then
    screens_save "$cur"
    conf_set screen_active "$target"
    video_snapshot_apply "$(screens_file "$target")" || log_warn "screens: perfil $target incompleto"
  fi
  if ((kernel)); then
    if [[ $target != "$SCREEN_HOME" ]]; then
      mkdir -p "$SCREEN_RUN"
      : > "$SCREEN_RUN/screen-edid-dirty"
    fi
    screens_param_set "$conn" "$want"
    # O "detect" faz o driver soltar o EDID guardado (quando o monitor
    # responde no DDC) e ler o do parametro novo; o "on" forca a saida de
    # novo, como o "e" da linha do kernel.
    drm_set_status "$card-$conn" detect
    drm_set_status "$card-$conn" on
  fi
  log_info "screens: tela $target, $(screens_label "$target")"
  # O que mudou na linha do kernel com a outra tela no cabo.
  if [[ $target == "$SCREEN_HOME" && $(conf_get screen_boot_pending 2> /dev/null) == 1 ]]; then
    conf_unset screen_boot_pending
    boot_apply || log_warn "screens: a linha do kernel pendente nao foi gravada"
  fi
  return 10
}

# screens_holders imprime os PIDs que tem a placa de video aberta (o frontend,
# o jogo, o X, o Setup), menos o systemd, o logind e este processo.
screens_holders() {
  local path pid comm
  while IFS= read -r path; do
    pid=${path#"$SCREEN_PROC"/}
    pid=${pid%%/*}
    [[ $pid =~ ^[0-9]+$ ]] || continue
    ((pid == 1 || pid == $$ || pid == BASHPID)) && continue
    comm=$(cat "$SCREEN_PROC/$pid/comm" 2> /dev/null) || continue
    [[ $comm == systemd* || $comm == "(sd-pam)" ]] && continue
    printf '%s\n' "$pid"
  done < <(find "$SCREEN_PROC"/[0-9]*/fd -lname '/dev/dri/card*' 2> /dev/null) | sort -un
}

# screens_relaunch_file: o pedido para o tty1 reabrir o que estava na tela,
# no XDG_RUNTIME_DIR do jogador (o tty1 o apaga).
screens_relaunch_file() {
  local uid
  uid=$(id -u "$FLIPEROS_USER" 2> /dev/null) || uid=1000
  printf '%s\n' "${SCREEN_RELAUNCH:-/run/user/$uid/fliperos-screen-relaunch}"
}

# screens_close_screen SINAL fecha o que esta na tela (SIGKILL: o sinal sai
# agora; SIGTERM: o jogo grava, ate 3 s) e pede ao tty1 para reabrir a sessao
# que estava aberta (o frontend) ou o menu.
screens_close_screen() {
  local sig=$1 pids=() pid session="" args file n limit alive
  args=$(pgrep -a -f '(^|/)fliperos-session( |$)' 2> /dev/null | head -n 1) || args=""
  if [[ -n $args ]]; then
    session=${args#*fliperos-session}
    session=${session# }
    printf -v session 'session=%s' "${session%% *}"
  fi
  file=$(screens_relaunch_file)
  mkdir -p "${file%/*}" 2> /dev/null
  printf '%s\n' "${session:-menu}" > "$file" 2> /dev/null
  chown "$FLIPEROS_USER" "$file" 2> /dev/null
  mapfile -t pids < <(screens_holders)
  ((${#pids[@]})) || return 0
  log_info "screens: fechando o que esta na tela ($sig): ${pids[*]}"
  kill -s "$sig" "${pids[@]}" 2> /dev/null
  # Ate 3 s para o jogo gravar (SIGTERM), 1 s depois do SIGKILL.
  limit=30
  [[ $sig == KILL ]] && limit=10
  for ((n = 0; n < limit; n++)); do
    alive=0
    for pid in "${pids[@]}"; do
      [[ -e $SCREEN_PROC/$pid ]] && { alive=1; break; }
    done
    ((alive)) || return 0
    sleep 0.1
  done
  kill -s KILL "${pids[@]}" 2> /dev/null
  return 0
}

# screens_watch_event CARD CONECTOR FP: o monitor do cabo trocou (a linha do
# fliperos-ddc watch).
screens_watch_event() {
  local card=$1 conn=$2 fp=$3 cur expected info target rc=0
  cur=$(screens_active)
  expected=$(conf_get edid "$(screens_file "$cur")" 2> /dev/null) || expected=none
  [[ $fp == "$expected" ]] && return 0
  if [[ $cur != "$SCREEN_HOME" ]]; then
    # O monitor de 31 kHz saiu do cabo: o tubo pode estar chegando. O sinal
    # sai antes de qualquer outra coisa (a saida desligada e o que esta na
    # tela fechado na hora), e o modo do tubo vem depois.
    drm_set_status "$card-$conn" off
    screens_close_screen KILL
    log_warn "screens: o monitor de 31 kHz saiu do cabo, sinal cortado"
    screens_lock
    screens_sync force
    screens_unlock
    return 0
  fi
  # Da home para outra tela: so se o EDID novo pede outra tela.
  info=$(screens_read "$conn")
  target=$(screens_pick "$info") || rc=$?
  [[ $target == "$SCREEN_HOME" ]] && return 0
  screens_boot_ready "$conn" || return 0
  screens_close_screen TERM
  screens_lock
  screens_sync force
  screens_unlock
}

# screens_watch: o vigia (fliperos-screen-watch.service). Com a troca
# desligada so confere a cada 5 s se ela foi ligada.
screens_watch() {
  local conn card line got
  while true; do
    if ! screens_on || ! screens_available > /dev/null || ! conn=$(conf_get connector 2> /dev/null) ||
      ! card=$(video_conf_card) || [[ ! -x $SCREEN_DDC ]]; then
      sleep 5
      continue
    fi
    # A primeira conferencia e a mesma do tty1 antes da primeira tela (quem
    # chegar antes faz; o outro nao acha nada a trocar): nada fechado, que no
    # boot so o splash esta na tela.
    screens_lock
    screens_sync
    screens_unlock
    coproc SCREEN_DDC_PROC { exec "$SCREEN_DDC" watch "$card-$conn"; }
    while true; do
      got=0
      IFS= read -r -t 5 line <&"${SCREEN_DDC_PROC[0]}" && got=1
      if ((got)); then
        screens_watch_event "$card" "$conn" "$line"
      elif ! kill -0 "$SCREEN_DDC_PROC_PID" 2> /dev/null; then
        break
      fi
      screens_on && [[ $(conf_get connector 2> /dev/null) == "$conn" ]] || break
    done
    kill "$SCREEN_DDC_PROC_PID" 2> /dev/null
    wait "$SCREEN_DDC_PROC_PID" 2> /dev/null
    sleep 1
  done
}
