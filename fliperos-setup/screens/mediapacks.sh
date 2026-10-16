# shellcheck shell=bash
# Setup > Games > Scraper > Art packs by torrent: a lista dos pacotes (os da
# imagem ja preenchidos e os que a pessoa acrescenta), cada um com as pastas
# de jogos dele. So baixa com ROMs nessas pastas, e so a arte dos jogos que
# estao nelas. A logica e a lib/mediapacks.sh.

screen_mediapacks() {
  local title="Art packs by torrent" choice last="" status id type folders link label origin games st state
  local -a entries ready
  # As pastas com jogos, uma vez por abertura da tela (lib/mediapacks.sh).
  MEDIAPACKS_FOUND=$(scraper_detect)
  if [[ -z $MEDIAPACKS_FOUND ]]; then
    ui_msg "$title" "No ROMs were found in $ROMS_DIR." "" \
      "A pack only brings the art of the games you have: copy your ROMs to the" \
      "emulator folders first (Setup > Games > Folders shows where)."
    return 0
  fi
  downloader_prepare
  mediapacks_prepare
  while true; do
    status=$(mediapacks_status)
    if [[ $(romclean_value "$status" state) == ready ]]; then
      ui_info "$title" "Saving the downloaded files to $MEDIA_DIR..."
      mediapacks_finish
      status=$(mediapacks_status)
    fi
    entries=()
    ready=()
    state=""
    while IFS=$'\t' read -r id type folders link label origin; do
      games=$(mediapacks_games "$folders")
      st=$(romclean_value "$status" "pack.$id")
      if ((games == 0)); then
        entries+=("$id|$label: no ROMs in ${folders//,/, }")
      elif [[ ${st%%|*} == downloading ]]; then
        state=downloading
        st=${st#*|}
        entries+=("$id|$label: ${st%%|*}%, ${st#*|}")
      else
        ready+=("$id")
        if [[ -n $st ]]; then
          entries+=("$id|$label: ${st##*|}")
        else
          entries+=("$id|$label: $games ROMs")
        fi
      fi
    done < <(mediapacks_list)
    ((${#ready[@]})) && entries+=("all|Download every pack that has ROMs")
    [[ $state == downloading ]] && entries+=("watch|See the download ($(romclean_value "$status" pct)%)")
    entries+=("add|Add a torrent" "return|Return")
    choice=$(ui_menu "$title" "Logos and videos from torrents, only for the ROMs you have. What is already in ~/media stays." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      add) screen_mediapacks_add ;;
      watch) screen_mediapacks_watch ;;
      all)
        for id in "${ready[@]}"; do screen_mediapacks_start "$id" quiet; done
        screen_mediapacks_watch
        ;;
      *) screen_mediapacks_pack "$choice" ;;
    esac
  done
}

# screen_mediapacks_pack ID: o pacote, as pastas dele com ROMs e o que da
# para fazer com ele.
screen_mediapacks_pack() {
  local id=$1 title="Art pack" row type folders link label origin st state text choice new key count with
  local -a keys entries rows
  while true; do
    row=$(mediapacks_get "$id") || return 0
    IFS=$'\t' read -r _ type folders link label origin <<< "$row"
    mapfile -t keys < <(mediapacks_keys "$folders")
    with=""
    for row in "${keys[@]}"; do
      IFS='|' read -r key _ _ count <<< "$row"
      with+="${with:+, }$key ($count)"
    done
    st=$(romclean_value "$(mediapacks_status)" "pack.$id")
    state=${st%%|*}
    text=${st##*|}
    rows=("Pack|$label" "Art|$(mediapacks_type_label "$type"), to ~/media/$type" "Folders|${folders//,/, }"
      "With ROMs|${with:-none}" "Link|${link:0:54}")
    [[ -n $st ]] && rows+=("Status|$text")
    entries=()
    if [[ $state == downloading ]]; then
      entries+=("watch|See the download" "cancel|Cancel the download")
    elif ((${#keys[@]})); then
      entries+=("start|Download the $(mediapacks_type_label "$type") of the ROMs found")
    fi
    entries+=("link|Change the link")
    [[ $origin == changed ]] && entries+=("reset|Use the FliperOS link again")
    [[ $origin == user ]] && entries+=("remove|Remove this pack")
    entries+=("return|Return")
    text=$(ui_fields "${rows[@]}")
    ((${#keys[@]})) || text+=$'\n\n'"$(ui_no "No ROMs in these folders: there is nothing to download.")"
    choice=$(ui_menu "$title" "$text" "${entries[0]%%|*}" "${entries[@]}") || return 0
    case $choice in
      start)
        screen_mediapacks_start "$id"
        ;;
      watch) screen_mediapacks_watch ;;
      cancel)
        ui_yesno "$title" "Cancel the download of $label? What it already downloaded is thrown away." no &&
          mediapacks cancel "$id" 2>> "$FLIPEROS_LOG"
        ;;
      link)
        new=$(ui_input "$title" "The magnet link or the address of the .torrent file of $label." "$link" long) || continue
        new=${new//[[:space:]]/}
        [[ -n $new && $new != "$link" ]] || continue
        if ! mediapacks_link_ok "$new"; then
          ui_msg "$title" "$(ui_bad "That is not a magnet link nor the address of a .torrent file.")" \
            "It starts with magnet:?xt=urn:btih: or with http."
          continue
        fi
        mediapacks cancel "$id" 2>> "$FLIPEROS_LOG"
        mediapacks_save "$id" "$type" "$folders" "$new" "$label"
        ;;
      reset) mediapacks_forget "$id" ;;
      remove)
        ui_yesno "$title" "Remove $label from the list? The art it already brought stays." no || continue
        mediapacks_forget "$id"
        return 0
        ;;
      *) return 0 ;;
    esac
  done
}

# screen_mediapacks_start ID [quiet]: le o torrent, marca os arquivos dos
# jogos das pastas e comeca. Sem quiet, diz o que vai baixar e abre a barra.
screen_mediapacks_start() {
  local id=$1 quiet=${2:-} title="Art pack" row type label result out files games kept what
  row=$(mediapacks_get "$id") || return 0
  IFS=$'\t' read -r _ type _ _ label _ <<< "$row"
  what=$(mediapacks_type_label "$type")
  downloader_service_on
  result=$(mktemp)
  if run_with_progress "Reading the torrent" "$label" mediapacks_start "$id" "$result" && [[ -z $quiet ]]; then
    out=$(cat "$result")
    files=$(romclean_value "$out" files)
    games=$(romclean_value "$out" games)
    kept=$(romclean_value "$out" kept)
    if ((${files:-0} > 0)); then
      ui_msg "$title" "$label: $files files to download ($(human_bytes "$(romclean_value "$out" bytes)"))." \
        "$games games have no $what yet; $kept already have it. The rest of the torrent is never downloaded." "" \
        "The download goes on in the background, even with a game open." \
        "When it ends, the $what of each game goes to ~/media/$type."
      screen_mediapacks_watch
    elif ((${games:-0} == 0)); then
      ui_msg "$title" "Nothing to download: the $kept games already have their $what."
    else
      ui_msg "$title" "None of the $games games without $what is in this pack."
    fi
  fi
  rm -f "$result"
  mediapacks_finish
  return 0
}

# screen_mediapacks_watch: a barra dos downloads, ate terminarem ou ate uma
# tecla (o download continua). O que termina vai para as pastas de arte.
screen_mediapacks_watch() {
  local status pct state line step
  local -a rest
  ui_size
  ui_clear
  ui_topbar
  stty -echo < /dev/tty 2> /dev/null
  printf '\e[?25l' > /dev/tty
  # shellcheck disable=SC2034 # lido pelo _progress_draw
  PROGRESS_FOOTER="Any key returns to the menu; the download goes on."
  while true; do
    status=$(mediapacks_status)
    state=$(romclean_value "$status" state)
    if [[ $state == ready ]]; then
      _progress_draw "Art packs" "" 100 "Saving the files to $MEDIA_DIR"
      mediapacks_finish
      status=$(mediapacks_status)
      state=$(romclean_value "$status" state)
      [[ $state == ready ]] && break
    fi
    pct=$(romclean_value "$status" pct)
    line=$(romclean_value "$status" line)
    IFS=';' read -r -a rest <<< "$line"
    step=${rest[0]}
    rest=("${rest[@]:1}")
    rest=("${rest[@]# }")
    _progress_draw "Art packs" "" "${pct:-0}" "$step" "${rest[@]}"
    [[ $state == downloading ]] || break
    ui_wait_key 2 && break
  done
  # shellcheck disable=SC2034
  PROGRESS_FOOTER=""
  printf '\e[?25h' > /dev/tty
  stty echo < /dev/tty 2> /dev/null
  ui_flush_input
  [[ $state == "done" ]] && ui_msg "Art packs" "Download finished: the art is in $MEDIA_DIR, in the folder of each type." \
    "The frontends find it by the name of the game."
  return 0
}

# screen_mediapacks_add: um torrent da pessoa, com o tipo de arte e as pastas
# de jogos dele.
screen_mediapacks_add() {
  local title="Add a torrent" type folders link label line key count id t
  local -a entries=()
  for t in $MEDIAPACKS_TYPES; do
    entries+=("$t|$(mediapacks_type_label "$t") (~/media/$t)")
  done
  type=$(ui_menu "$title" "What does the torrent have? One file per game with the name of the ROM (sf2.png, sf2.mp4), loose or inside .zip files." \
    logo "${entries[@]}") || return 0
  entries=("@arcade|Every arcade folder (MAME, Naomi, Model 2, the arcade cores)")
  while IFS='|' read -r key _ _ count; do
    [[ -n $key ]] && entries+=("$key|$key - $count files")
  done <<< "$MEDIAPACKS_FOUND"
  folders=$(UI_STYLE=list ui_menu "$title" "Which games is it for?" "@arcade" "${entries[@]}") || return 0
  link=$(ui_input "$title" "Paste the magnet link or the address of the .torrent file." "" long) || return 0
  link=${link//[[:space:]]/}
  [[ -n $link ]] || return 0
  if ! mediapacks_link_ok "$link"; then
    ui_msg "$title" "$(ui_bad "That is not a magnet link nor the address of a .torrent file.")" \
      "It starts with magnet:?xt=urn:btih: or with http."
    return 0
  fi
  label=${link##*/}
  label=${label%.torrent}
  [[ $link == magnet:* ]] && label="My $(mediapacks_type_label "$type")"
  label=$(ui_input "$title" "A name for this pack." "${label:0:40}") || return 0
  [[ -n $label ]] || label="My $(mediapacks_type_label "$type")"
  id=$(mediapacks_add "$type" "$folders" "$link" "$label") || return 0
  screen_mediapacks_pack "$id"
}
