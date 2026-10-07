# shellcheck shell=bash
# Setup > MAME ROM Cleaner: onde esta o romset (uma pasta daqui ou uma pasta
# da rede), para que emulador ele e (GroovyMAME, Flycast, MAME 2010), a tela
# dos parametros (Enter num parametro abre as opcoes dele, de escolher uma ou
# de marcar varias, e volta com a escolha), a previa e a copia para a pasta
# do emulador. A logica e a lib/romclean.sh; a pasta da rede, lib/netshare.sh.

screen_rom_cleaner() {
  local title="MAME ROM Cleaner" folder target xml="" had=0 options
  netshare_mounted && had=1
  folder=$(screen_rom_cleaner_source) || {
    screen_rom_cleaner_close "$had"
    return 0
  }
  if [[ -d $folder ]]; then
    mapfile -t options < <(romclean_targets)
    if target=$(ui_menu "$title" "Which emulator is this romset for? Folder: $folder" \
      "$(romclean_default_target "$folder")" "${options[@]}"); then
      if [[ $target != file ]] || xml=$(ui_browse "$title" "Choose the XML file (from mame -listxml)." \
        "$(dirname -- "$folder")" file .xml .xml.xz); then
        screen_rom_cleaner_filters "$folder" "$target" "$xml"
      fi
    fi
  fi
  screen_rom_cleaner_close "$had"
}

# screen_rom_cleaner_close JA_ESTAVA: a pasta da rede que esta tela montou
# sai com ela.
screen_rom_cleaner_close() {
  (($1)) || netshare_umount
  return 0
}

# screen_rom_cleaner_source imprime a pasta do romset: escolhida nas pastas
# desta maquina ou numa pasta compartilhada da rede (montada so para
# leitura). Status 1 = desistiu.
screen_rom_cleaner_source() {
  local title=${1:-MAME ROM Cleaner} what=${2:-romset} choice start
  local -a entries
  while true; do
    entries=("local|A folder on this machine (disk, USB drive)")
    netshare_mounted && entries+=("mounted|The network folder $(netshare_source)")
    netshare_available && entries+=("network|A shared folder on the network (Windows, NAS)")
    if ((${#entries[@]} == 1)); then
      choice=local
    else
      choice=$(ui_menu "$title" "Where is the $what?" "" "${entries[@]}") || return 1
    fi
    case $choice in
      mounted) start=$NETSHARE_DIR ;;
      network)
        screen_netshare_connect "$title" || continue
        start=$NETSHARE_DIR
        ;;
      *)
        start=$ROMS_ROOT
        [[ -d $start ]] || start=/
        ;;
    esac
    ui_browse "$title" "Open the folder with the $what, then Use this folder." "$start" dir && return 0
    ((${#entries[@]} == 1)) && return 1
  done
}

# ── MAME CHD Cleaner ──────────────────────────────────────────────

# screen_chd_cleaner: onde estao os CHDs (uma pasta daqui ou da rede, com uma
# subpasta por jogo), de que emulador sao e, pelos jogos que ja estao na
# pasta de ROMs dele, a copia so dos CHDs que eles usam (lib/romclean.sh).
screen_chd_cleaner() {
  local title="MAME CHD Cleaner" folder target xml="" had=0 options
  netshare_mounted && had=1
  folder=$(screen_rom_cleaner_source "$title" "CHD collection") || {
    screen_rom_cleaner_close "$had"
    return 0
  }
  if [[ -d $folder ]]; then
    mapfile -t options < <(romclean_targets)
    if target=$(ui_menu "$title" "Which emulator are these CHDs for? Its ROM folder says which games need one." \
      "$(romclean_default_target "$folder")" "${options[@]}"); then
      if [[ $target != file ]] || xml=$(ui_browse "$title" "Choose the XML file (from mame -listxml)." \
        "$(dirname -- "$folder")" file .xml .xml.xz); then
        screen_chd_cleaner_run "$folder" "$target" "$xml"
      fi
    fi
  fi
  screen_rom_cleaner_close "$had"
}

# screen_chd_cleaner_run ORIGEM ALVO XML: le o XML e a pasta de ROMs, mostra
# quantos jogos usam CHD, quantos foram achados e o tamanho, e copia (ou
# move, de uma pasta em que da para gravar).
screen_chd_cleaner_run() {
  local folder=$1 target=$2 xml=$3 title="MAME CHD Cleaner" clones=no dest plan list summary rc
  local games move missing bytes free fields choice result line where action verb past
  local -a rows entries args
  dest=$(romclean_default_dest "$target")
  plan=$(mktemp) list=$(mktemp)
  while true; do
    where=$(romclean_chd_label "$target" "$dest")
    ui_info "$title" "Reading the MAME XML, $where and the CHD folder..." \
      "The first time with each MAME version takes about a minute."
    args=()
    [[ $clones == yes ]] && args=(--clones)
    summary=$(romclean_chd_scan "$folder" "$target" "$xml" "$dest" "$plan" "${args[@]}" 2> "$list")
    rc=$?
    cat "$list" >> "$FLIPEROS_LOG"
    if ((rc != 0)); then
      ui_msg "$title" "$(ui_bad "The CHD folder could not be read.")" \
        "$(grep -v '^[[:space:]]*$' "$list" | tail -n 1 | cut -c1-200)" "" "Details in $FLIPEROS_LOG."
      break
    fi
    games=$(romclean_value "$summary" games)
    move=$(romclean_value "$summary" move)
    missing=$(romclean_value "$summary" missing)
    bytes=$(romclean_value "$summary" move_bytes)
    free=$(romclean_value "$summary" free_bytes)
    rows=("CHDs from|$folder" "Games|$games in $where use a CHD"
      "Found|$move CHD folders, $(human_bytes "$bytes")")
    ((missing > 0)) && rows+=("Not found|the CHD of $missing games")
    if ((bytes > free)); then
      rows+=("Free space|$(ui_bad "$(human_bytes "$free"): not enough")")
    else
      rows+=("Free space|$(human_bytes "$free")")
    fi
    fields=$(ui_fields "${rows[@]}")
    entries=()
    if ((move > 0)); then
      entries+=("copy|Copy them")
      [[ -w $folder ]] && entries+=("move|Move them (out of the CHD folder)")
      entries+=("list|See the list")
    fi
    ((missing > 0)) && entries+=("missing|See what was not found")
    entries+=("clones|CHDs of the clones inside the zips too: $clones" "dest|ROM folder: $where" "cancel|Cancel")
    ((games == 0)) && fields+=$'\n\n'"No game there uses a CHD. Copy the games first (MAME ROM Cleaner)."
    choice=$(ui_menu "$title" "$fields" "${entries[0]%%|*}" "${entries[@]}") || break
    case $choice in
      list)
        romclean_list "$plan" move > "$list"
        ui_pager "$title" "$list" inicio
        ;;
      missing)
        awk -F'\t' '$1 == "missing" { printf "%-16s %s\n", $2, $3 }' "$plan" > "$list"
        ui_pager "$title" "$list" inicio
        ;;
      clones) [[ $clones == yes ]] && clones=no || clones=yes ;;
      dest) line=$(ui_browse "$title" "Choose the ROM folder the games are in." "$ROMS_ROOT" dir) && dest=$line ;;
      copy | move)
        action=$choice verb=Copy past=copied
        [[ $action == move ]] && verb=Move past=moved
        if ((bytes > free)) && [[ $action == copy ]]; then
          ui_msg "$title" "$(ui_bad "Not enough free space for $(human_bytes "$bytes").")"
          continue
        fi
        if run_with_progress "$verb the CHDs" "$where" romclean_transfer "$plan" "$action"; then
          result=$(cat "$plan.result" 2> /dev/null)
          ui_msg "$title" "$(romclean_value "$result" "$past") CHD folders $past." \
            "$(romclean_value "$result" skipped) were already there."
        fi
        break
        ;;
      *) break ;;
    esac
  done
  rm -f "$plan" "$plan.result" "$list"
  return 0
}

# screen_netshare_connect TITULO pergunta o computador, o usuario, a senha e
# a pasta compartilhada, e a monta. Status 1 = desistiu ou nao abriu.
screen_netshare_connect() {
  local title=$1 host user pass="" share saved=0 s
  local -a shares=() entries=()
  host=$(ui_input "$title" "The computer that shares the folder: its IP or name (192.168.1.10)." \
    "$(netshare_saved host)") || return 1
  host=${host#"${host%%[!/\\]*}"}
  host=${host%%[/\\]*}
  [[ -n $host ]] || return 1
  user=$(ui_input "$title" "Your user name on $host (empty: as a guest, no password)." \
    "$(netshare_saved user)") || return 1
  if [[ -n $user ]]; then
    if [[ $host == "$(netshare_saved host)" ]] && pass=$(netshare_saved_password "$user") &&
      ui_yesno "$title" "Use the password saved for $user?"; then
      saved=1
    else
      pass=$(ui_input "$title" "Password of $user on $host." "" password) || return 1
    fi
  fi
  ui_info "$title" "Looking for the shared folders of $host..."
  mapfile -t shares < <(netshare_shares "$host" "$user" "$pass")
  if ((${#shares[@]})); then
    for s in "${shares[@]}"; do
      entries+=("$s|$s")
    done
    share=$(ui_menu "$title" "Which shared folder of $host?" "$(netshare_saved share)" "${entries[@]}") || return 1
  else
    share=$(ui_input "$title" "The name of the shared folder on $host (what comes after \\\\$host\\)." \
      "$(netshare_saved share)") || return 1
  fi
  [[ -n $share ]] || return 1
  ui_info "$title" "Opening //$host/$share..."
  if ! netshare_mount "$host" "$share" "$user" "$pass"; then
    ui_msg "$title" "$(ui_bad "Could not open //$host/$share.")" "$NETSHARE_ERROR" "" "Details in $FLIPEROS_LOG."
    return 1
  fi
  if [[ -n $user ]] && { ((saved)) || ui_yesno "$title" \
    "Save this password for the next time? It stays on this machine, where only the system reads it." no; }; then
    netshare_save "$host" "$share" "$user" "$pass"
  else
    netshare_save "$host" "$share" "$user"
  fi
  return 0
}

# screen_rom_cleaner_pick CHAVE VALOR abre as opcoes do parametro (de
# escolher uma ou de marcar varias) e imprime a escolha nova. Status 1 = Esc.
screen_rom_cleaner_pick() {
  local key=$1 value=$2 title="ROM Cleaner: ${ROMCLEAN_TITLE[$1]}"
  local -a options
  mapfile -t options < <(romclean_options "$key")
  if [[ ${ROMCLEAN_TYPE[$key]} == check ]]; then
    ui_checklist "$title" "${ROMCLEAN_HELP[$key]}" "$value" "${options[@]}"
  else
    ui_radio "$title" "${ROMCLEAN_HELP[$key]}" "$value" "${options[@]}"
  fi
}

# screen_rom_cleaner_filters ORIGEM ALVO XML [downloader]: a tela dos
# parametros (o preset, cada filtro, copiar ou mover e o destino) e, no
# Continue, a previa. No modo downloader (Setup > Downloader > Filter) abre
# com o filtro salvo e o Save o grava; status 3 = salvou.
screen_rom_cleaner_filters() {
  local folder=$1 target=$2 xml=$3 mode=${4:-} title="MAME ROM Cleaner" last=preset preset=cabinet transfer=copy
  local dest key line choice value writable=0
  local -A opt=()
  local -a entries args kv presets
  [[ $mode == downloader ]] && title="Downloader filter"
  ui_info "$title" "Looking for catver.ini, nplayers.ini and controls.xml..."
  romclean_data_load "$folder"
  dest=$(romclean_default_dest "$target")
  # De uma pasta so de leitura (a da rede) so da para copiar.
  [[ -w $folder && $mode != downloader ]] && writable=1
  while IFS= read -r line; do
    opt[${line%%=*}]=${line#*=}
  done < <(romclean_preset "$preset" "$target")
  if [[ $mode == downloader && $(downloader_filter_get target) == "$target" ]]; then
    preset=$(downloader_filter_get preset)
    dest=$(downloader_filter_get dest)
    for key in "${ROMCLEAN_KEYS[@]}"; do
      line=$(grep -m1 "^$key=" "$DOWNLOADER_STATE/filter.kv") && opt[$key]=${line#*=}
    done
  fi
  presets=("cabinet|$(romclean_preset_label cabinet)" "working|$(romclean_preset_label working)"
    "psx|$(romclean_preset_label psx)" "all|$(romclean_preset_label all)")
  while true; do
    entries=("preset|Preset: $(romclean_preset_label "$preset")")
    for key in "${ROMCLEAN_KEYS[@]}"; do
      romclean_visible "$key" "$target" && entries+=("$key|$(romclean_label "$key" "${opt[$key]}")")
    done
    ((writable)) && entries+=("transfer|$(romclean_label transfer "$transfer")")
    entries+=("dest|To: $(romclean_dest_label "$target" "$dest")" "data|Data files: $ROMCLEAN_DATA_LABEL")
    if [[ $mode == downloader ]]; then
      entries+=("save|Save the filter" "return|Return")
      line="Magnet links -> $(romclean_target_label "$target"). Enter opens a parameter."
    else
      entries+=("scan|Continue" "return|Return")
      line="$folder -> $(romclean_target_label "$target"). Enter opens a parameter."
    fi
    choice=$(ui_menu "$title" "$line" "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      save)
        kv=()
        for key in "${ROMCLEAN_KEYS[@]}"; do
          kv+=("$key=${opt[$key]}")
        done
        downloader_filter_save "$target" "$dest" "$preset" "${kv[@]}"
        return 3
        ;;
      preset)
        value=$(ui_radio "$title" "Start from a preset; each parameter can be changed after." "$preset" \
          "${presets[@]}") || continue
        preset=$value
        while IFS= read -r line; do
          opt[${line%%=*}]=${line#*=}
        done < <(romclean_preset "$preset" "$target")
        ;;
      transfer) value=$(screen_rom_cleaner_pick transfer "$transfer") && transfer=$value ;;
      dest)
        line=$(ui_browse "$title" "Choose the folder the games go to." "$ROMS_ROOT" dir) && dest=$line
        ;;
      data)
        ui_msg "$title" "$(ui_fields "catver.ini|${ROMCLEAN_CATVER:-not found (no category filters)}" \
          "nplayers.ini|${ROMCLEAN_NPLAYERS:-not found (no play mode filter)}" \
          "controls.xml|${ROMCLEAN_CONTROLS:-not found (buttons as MAME says)}")" "" \
          "Put them in the romset folder, the one above it, or $ROMCLEAN_DATA."
        ;;
      scan)
        kv=()
        for key in "${ROMCLEAN_KEYS[@]}"; do
          kv+=("$key=${opt[$key]}")
        done
        mapfile -t args < <(romclean_args "$target" "${kv[@]}")
        screen_rom_cleaner_run "$folder" "$target" "$xml" "$dest" "$transfer" "${args[@]}"
        # 2 = voltar aos parametros.
        (($? == 2)) || return 0
        ;;
      *)
        if value=$(screen_rom_cleaner_pick "$choice" "${opt[$choice]}"); then
          opt[$choice]=$value
          preset=custom
        fi
        ;;
    esac
  done
}

# screen_rom_cleaner_run ORIGEM ALVO XML DESTINO copy|move FILTRO...: le o
# XML, mostra o que vai, copia ou move e, depois de mover, pergunta se apaga
# o que sobrou. Status 2 = voltar aos parametros.
screen_rom_cleaner_run() {
  local folder=$1 target=$2 xml=$3 dest=$4 transfer=$5 title="MAME ROM Cleaner"
  local plan list summary move rest bytes free fields choice result verb=Copy rc
  local -a rows
  shift 5
  [[ $transfer == move ]] && verb=Move
  plan=$(mktemp) list=$(mktemp)
  ui_info "$title" "Reading the MAME XML and the folder..." "The first time with each MAME version takes about a minute."
  # O que o fliperos-romclean reclama vai para o log e, na falha, a ultima
  # linha vai para a tela: "nao deu" sem o motivo nao ajuda ninguem.
  summary=$(romclean_scan "$folder" "$target" "$xml" "$dest" "$plan" "$@" 2> "$list")
  rc=$?
  cat "$list" >> "$FLIPEROS_LOG"
  if ((rc != 0)); then
    ui_msg "$title" "$(ui_bad "The romset could not be read.")" \
      "$(grep -v '^[[:space:]]*$' "$list" | tail -n 1 | cut -c1-200)" "" "Details in $FLIPEROS_LOG."
    rm -f "$plan" "$list"
    return 2
  fi
  if [[ $(romclean_value "$summary" sets) == 0 ]]; then
    ui_msg "$title" "No set of this MAME version in $folder." "Is it the right folder, and the right emulator?"
    rm -f "$plan" "$list"
    return 2
  fi
  move=$(romclean_value "$summary" move)
  rest=$(romclean_value "$summary" rest)
  bytes=$(romclean_value "$summary" move_bytes)
  free=$(romclean_value "$summary" free_bytes)
  rows=("From|$folder ($(romclean_value "$summary" sets) sets)"
    "To|$(romclean_dest_label "$target" "$dest")"
    "Going|$move sets, $(human_bytes "$bytes") ($(romclean_value "$summary" needed) as parent, BIOS or device)")
  if ((bytes > free)); then
    rows+=("Free space|$(ui_bad "$(human_bytes "$free"): not enough")")
  else
    rows+=("Free space|$(human_bytes "$free")")
  fi
  [[ $transfer == move ]] && rows+=("Left over|$rest sets ($(human_bytes "$(romclean_value "$summary" rest_bytes)"))")
  (($(romclean_value "$summary" unknown) > 0)) &&
    rows+=("Not in the XML|$(romclean_value "$summary" unknown) (left alone)")
  fields=$(ui_fields "${rows[@]}")
  romclean_list "$plan" move > "$list"
  (($(wc -l < "$list") > 1200)) && printf '\n... and %d more.\n' $(($(wc -l < "$list") - 1200)) >> "$list"
  if ((move == 0)); then
    ui_msg "$title" "$fields" "" "No game passed the filters."
    rm -f "$plan" "$list"
    return 2
  fi
  while true; do
    choice=$(ui_menu "$title" "$fields" go \
      "go|$verb them" \
      "list|See the list" \
      "filters|Change the parameters" \
      "cancel|Cancel") || choice=filters
    case $choice in
      list) ui_pager "$title" "$list" inicio ;;
      go)
        if ((bytes > free)) && [[ $transfer == copy ]]; then
          ui_msg "$title" "$(ui_bad "Not enough free space for $(human_bytes "$bytes").")" \
            "Change the parameters to take fewer games."
          continue
        fi
        break
        ;;
      filters)
        rm -f "$plan" "$list"
        return 2
        ;;
      *)
        rm -f "$plan" "$list"
        return 0
        ;;
    esac
  done
  if run_with_progress "$verb the games" "$(romclean_dest_label "$target" "$dest")" romclean_transfer "$plan" "$transfer"; then
    result=$(cat "$plan.result" 2> /dev/null)
    if [[ $transfer == move ]]; then
      ui_msg "$title" "$(romclean_value "$result" moved) sets moved." \
        "$(romclean_value "$result" skipped) were already there."
    else
      ui_msg "$title" "$(romclean_value "$result" copied) sets copied." \
        "$(romclean_value "$result" skipped) were already there."
    fi
    if [[ $transfer == move ]] && ((rest > 0)) && ui_yesno "$title" \
      "$rest sets didn't pass the filters and are still in $folder ($(human_bytes "$(romclean_value "$summary" rest_bytes)")). Delete them for good? This can't be undone." no; then
      result=$(romclean_apply "$plan" delete-rest 2>> "$FLIPEROS_LOG")
      ui_msg "$title" "$(romclean_value "$result" deleted) files deleted."
    fi
  fi
  rm -f "$plan" "$plan.result" "$list"
  return 0
}
