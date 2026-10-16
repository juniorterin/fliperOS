# shellcheck shell=bash
# Setup > Games > Downloader: tudo o que baixa jogos. ROM/CHD MAME torrent: o filtro
# (o mesmo do MAME ROM Cleaner, salvo so para o torrent), o link magnetico
# do romset (obrigatorio) e o dos CHDs, a pasta final e a barra do download.
# Ao abrir, e depois de mudar o filtro, avisa o que o filtro novo acrescenta
# ou apaga. A logica e a lib/downloader.sh.

screen_downloads() {
  local choice last=""
  while true; do
    choice=$(ui_menu_hints "Downloader" "Games downloaded straight to the emulator folders." "$last" \
      "torrent|ROM/CHD MAME torrent|Only the games your filter picks, from a romset magnet link." \
      "freeroms|Free games (open-source homebrew)|So the frontends have something to show." \
      "return|Return|Back to Games.") || return 0
    last=$choice
    case $choice in
      torrent) screen_downloader ;;
      freeroms) screen_free_roms ;;
      *) return 0 ;;
    esac
  done
}

screen_downloader() {
  local title="ROM/CHD MAME torrent" choice status pct state line roms chds last=""
  local -a entries
  downloader_prepare
  screen_downloader_changes
  while true; do
    status=$(downloader_status)
    pct=$(romclean_value "$status" pct)
    state=$(romclean_value "$status" state)
    line=$(romclean_value "$status" line)
    roms=$(romclean_value "$status" roms_name)
    chds=$(romclean_value "$status" chds_name)
    entries=("filter|Filter: $(downloader_filter_label)"
      "roms|ROM set magnet link (required): ${roms:-not set}"
      "chds|CHD set magnet link (optional): ${chds:-not set}"
      "dest|Download folder: $(downloader_dest_label)")
    if [[ $state == downloading ]]; then
      entries+=("watch|See the download ($pct%)")
    else
      entries+=("start|Start the download")
    fi
    entries+=("return|Return")
    choice=$(ui_menu "$title" "$(ui_fields "Status|$line")" "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      roms | chds) screen_downloader_magnet "$choice" ;;
      filter) screen_downloader_filter ;;
      dest) screen_downloader_dest ;;
      start)
        if [[ -z $roms ]]; then
          ui_msg "$title" "$(ui_bad "The ROM set magnet link is required.")" \
            "Paste it in ROM set magnet link, then Start the download."
          last=roms
        else
          screen_downloader_start
        fi
        ;;
      watch) screen_downloader_watch ;;
      *) return 0 ;;
    esac
  done
}

# screen_downloader_dest: a pasta final dos downloads, no seletor de pastas.
screen_downloader_dest() {
  local title="Downloader" target start dest text="Open the folder the games go to, then Use this folder."
  target=$(downloader_filter_get target) && [[ -n $target ]] || target=groovymame
  [[ $target == flycast ]] &&
    text="Open the folder that has (or will have) the naomi, naomi2 and atomiswave folders, then Use this folder."
  start=$(downloader_dest)
  [[ -d $start ]] || start=$ROMS_ROOT
  [[ -d $start ]] || start=/
  dest=$(ui_browse "$title" "$text" "$start" dir) || return 0
  downloader_filter_set_dest "$dest"
  if compgen -G "$DOWNLOADER_STATE/*.installed" > /dev/null; then
    ui_msg "$title" "The next downloads go to $(downloader_dest_label)." \
      "What was already downloaded stays where it is."
  fi
  return 0
}

# screen_downloader_magnet roms|chds [LINK from-browser]: cola, troca ou tira
# o link. Vindo do navegador, ja abre o campo com o link clicado nele.
screen_downloader_magnet() {
  local kind=$1 title="Downloader" what="ROM set" only magnet prompt name choice result status folder sets found rc
  local -a button=()
  [[ $kind == chds ]] && what="CHD set"
  only="only the ROMs of the games the filter chooses (with their parents, BIOS and devices) are downloaded"
  [[ $kind == chds ]] && only="only the CHDs of the games the filter chooses are downloaded"
  name=$(romclean_value "$(downloader_status)" "${kind}_name")
  if [[ -n $name && ${3:-} != from-browser ]]; then
    choice=$(ui_menu "$title" "$what: $name" replace "replace|Replace the magnet link" \
      "remove|Remove the magnet link" "cancel|Cancel") || return 0
    case $choice in
      remove)
        result="--keep"
        ui_yesno "$title" "Also delete the files this link already downloaded to the emulator folders? The ones you put there yourself stay." no &&
          result="--delete-files"
        if [[ $result == --keep ]]; then
          result=$(downloader remove "$kind" 2>> "$FLIPEROS_LOG")
        else
          result=$(downloader remove "$kind" --delete-files 2>> "$FLIPEROS_LOG")
        fi
        downloader_service_sync
        ui_msg "$title" "The $what magnet link was removed." "$(romclean_value "$result" deleted) files deleted."
        return 0
        ;;
      replace) ;;
      *) return 0 ;;
    esac
  fi
  magnet=$(downloader_default_magnet "$kind")
  prompt="Paste the magnet link of the $what (magnet:?xt=urn:btih:...)."
  [[ -n $magnet ]] && prompt="The FliperOS link of the $what is filled in: Enter uses it, or paste another."
  if [[ ${3:-} == from-browser ]]; then
    magnet=${2:-}
    prompt="The link clicked in the browser is filled in: Enter uses it."
    [[ -n $magnet ]] || prompt="No magnet link came from the browser. Paste the link of the $what, or open the browser again."
  fi
  downloader_browser_ok &&
    button=("Open the browser" "Search the web for the $what and click its magnet link: it comes back here.")
  magnet=$(ui_input "$title" "$prompt" "$magnet" long "${button[@]}")
  rc=$?
  if ((rc == 3)); then
    screen_downloader_browser "$kind"
    return 0
  fi
  ((rc == 0)) || return 0
  magnet=${magnet//[[:space:]]/}
  [[ -n $magnet ]] || return 0
  if [[ ! $magnet =~ ^magnet:\?.*xt=urn:bt(ih|mh): ]]; then
    ui_msg "$title" "$(ui_bad "That is not a magnet link.")" "It starts with magnet:?xt=urn:btih:"
    return 0
  fi
  if ! downloader_filter_get preset > /dev/null; then
    downloader_filter_default
    ui_msg "$title" "The MAME ROM Cleaner filter will be used: $only, not the whole set." "" \
      "No filter was chosen yet, so it starts with the $(romclean_preset_label cabinet) preset. Change it in Filter."
  else
    ui_msg "$title" "The MAME ROM Cleaner filter will be used: $only, not the whole set." "" \
      "Filter: $(downloader_filter_label)."
  fi
  downloader_service_on
  run_with_progress "Reading the magnet link" "$what" downloader_add "$kind" "$magnet" || {
    downloader_service_sync
    return 0
  }
  status=$(downloader_status)
  name=$(romclean_value "$status" "${kind}_name")
  folder=$(romclean_value "$status" "${kind}_folder")
  sets=$(romclean_value "$status" "${kind}_sets")
  [[ $folder == / ]] && folder="the top of the torrent" || folder="the folder $folder"
  found="$sets ROM sets found in $folder."
  [[ $kind == chds ]] && found="CHDs of $sets games found in $folder."
  ui_msg "$title" "$what: $name" "$found The rest of the torrent is never downloaded." "" \
    "Choose the Download folder, then Start the download."
  return 0
}

# screen_downloader_filter: os parametros do ROM cleaner, para o emulador
# escolhido; salvos, mostra o que muda nos links cadastrados.
screen_downloader_filter() {
  local title="Downloader filter" target entry
  local -a options=()
  while IFS= read -r entry; do
    [[ ${entry%%|*} == file ]] || options+=("$entry")
  done < <(romclean_targets)
  target=$(ui_menu "$title" "Which emulator is the romset for? Its MAME version must match the romset." \
    "$(downloader_filter_get target || echo groovymame)" "${options[@]}") || return 0
  screen_rom_cleaner_filters "$ROMCLEAN_DATA" "$target" "" downloader
  (($? == 3)) && screen_downloader_changes
  return 0
}

# screen_downloader_start [prune]: aplica o filtro aos links e abre a barra;
# com prune, apaga depois o que o downloader trouxe e o filtro deixou de fora.
screen_downloader_start() {
  local title="Downloader" result kind n bytes text=() pruned
  result=$(mktemp)
  if run_with_progress "Applying the filter" "" downloader_start "$result"; then
    while IFS=$'\t' read -r kind _ n bytes; do
      [[ $kind == roms ]] && text+=("ROMs: $n files to download, $(human_bytes "$bytes")")
      [[ $kind == chds ]] && text+=("CHDs: $n files to download, $(human_bytes "$bytes")")
    done < "$result"
    if [[ ${1:-} == prune ]]; then
      pruned=$(downloader prune 2>> "$FLIPEROS_LOG")
      while IFS=$'\t' read -r kind _ n; do
        [[ $kind == chds ]] && kind=CHDs || kind=ROMs
        ((n > 0)) && text+=("$kind: $n deleted (left out by the filter)")
      done <<< "$pruned"
    fi
    ui_msg "$title" "${text[@]}" "" "The download goes on in the background, even with a game open." \
      "When it ends, each file goes to its emulator folder."
    screen_downloader_watch
  fi
  rm -f "$result"
  return 0
}

# screen_downloader_watch: a barra do download, ate terminar ou ate uma
# tecla (o download continua).
screen_downloader_watch() {
  local status pct state line step
  local -a rest
  # Na interface grafica, a tela do download: uma barra por torrent.
  local UI_STYLE=download
  ui_size
  ui_clear
  ui_topbar
  stty -echo < /dev/tty 2> /dev/null
  printf '\e[?25l' > /dev/tty
  # shellcheck disable=SC2034 # lido pelo _progress_draw
  PROGRESS_FOOTER="Any key returns to the menu; the download goes on."
  while true; do
    status=$(downloader_status)
    pct=$(romclean_value "$status" pct)
    state=$(romclean_value "$status" state)
    line=$(romclean_value "$status" line)
    IFS=';' read -r -a rest <<< "$line"
    step=${rest[0]}
    rest=("${rest[@]:1}")
    rest=("${rest[@]# }")
    _progress_draw "Downloader" "" "${pct:-0}" "$step" "${rest[@]}"
    [[ $state == downloading ]] || break
    ui_wait_key 2 && break
  done
  # shellcheck disable=SC2034
  PROGRESS_FOOTER=""
  printf '\e[?25h' > /dev/tty
  stty echo < /dev/tty 2> /dev/null
  ui_flush_input
  [[ $state == "done" ]] && ui_msg "Downloader" "Download finished: the games are in their emulator folders." \
    "AttractPlus ROM List updates the game names in the frontend."
  return 0
}

# screen_downloader_changes: com links cadastrados e um filtro ja aplicado,
# avisa quantas ROMs e CHDs o filtro de agora (ou uma versao nova do MAME)
# acrescenta ou apaga, e aplica se a pessoa quiser.
screen_downloader_changes() {
  local title="Downloader" out list kind what n bytes choice label
  local -a rows=()
  compgen -G "$DOWNLOADER_STATE/*.plan" > /dev/null || return 0
  ui_info "$title" "Checking the filter against the magnet links..."
  list=$(mktemp)
  out=$(downloader diff --list "$list" 2>> "$FLIPEROS_LOG") || {
    rm -f "$list"
    return 0
  }
  while IFS=$'\t' read -r kind what n bytes; do
    ((n > 0)) || continue
    label=ROMs
    [[ $kind == chds ]] && label=CHDs
    if [[ $what == add ]]; then
      rows+=("$label to add|$n ($(human_bytes "$bytes") to download)")
    else
      rows+=("$label to delete|$n ($(human_bytes "$bytes") freed)")
    fi
  done <<< "$out"
  if ((${#rows[@]} == 0)); then
    rm -f "$list"
    return 0
  fi
  while true; do
    choice=$(ui_menu "$title" "The filter changed (or the MAME version). With the magnet links, it now means:"$'\n\n'"$(ui_fields "${rows[@]}")" \
      apply "apply|Apply: download the new ones, delete the ones left out" \
      "list|See the list" "later|Later") || break
    case $choice in
      list) ui_pager "$title" "$list" inicio ;;
      apply)
        screen_downloader_start prune
        break
        ;;
      *) break ;;
    esac
  done
  rm -f "$list"
  return 0
}

# screen_downloader_browser roms|chds pede o navegador ao fliperos-tty1 e
# sai do Setup; ele volta na tela do link (screen_downloader_resume).
screen_downloader_browser() {
  mkdir -p "$DOWNLOADER_STATE" 2> /dev/null
  if ! printf '%s\n' "$1" > "$DOWNLOADER_BROWSER_PENDING" || ! launcher_request browser; then
    ui_msg "Downloader" "$(ui_bad "Could not open the browser.")" "Details in $FLIPEROS_LOG."
    return 1
  fi
  rm -f "$(downloader_capture_file)"
  ui_clear
  exit "$SETUP_EXIT_LAUNCH"
}

# screen_downloader_resume: o Setup reabriu depois do navegador? Volta a
# tela do link, com o que foi clicado, e depois a do torrent.
screen_downloader_resume() {
  local kind capture magnet=""
  [[ -s $DOWNLOADER_BROWSER_PENDING ]] || return 0
  kind=$(head -n 1 "$DOWNLOADER_BROWSER_PENDING")
  rm -f "$DOWNLOADER_BROWSER_PENDING"
  [[ $kind == roms || $kind == chds ]] || return 0
  capture=$(downloader_capture_file)
  [[ -s $capture ]] && magnet=$(head -n 1 "$capture")
  rm -f "$capture"
  downloader_prepare
  screen_downloader_magnet "$kind" "$magnet" from-browser
  screen_downloader
}
