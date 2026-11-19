# shellcheck shell=bash
# Setup > Games > Folders: dois caminhos. Folder shortcuts: as pastas de ~, das
# raizes as de cada emulador, core e tipo de arte, e o atalho (a "custom
# folder") de cada uma para outro disco (lib/folders.sh). External storage: um
# disco inteiro, com a estrutura do FliperOS ou a do Batocera (screens/storage.sh).

screen_folders() {
  local title="Folders" choice last=""
  while true; do
    choice=$(ui_menu_hints "$title" "" "$last" \
      "shortcuts|Folder shortcuts|Formerly Link. Send a folder to another disk, like a shortcut." \
      "external|External storage|A second disk: FliperOS or Batocera folders." \
      "return|Return|Back to Games.") || return 0
    last=$choice
    case $choice in
      shortcuts) screen_folders_shortcuts ;;
      external) screen_external_storage ;;
      return) return 0 ;;
    esac
  done
}

# screen_folders_label PASTA [LARGURA]: a linha da pasta numa lista. Uma raiz
# diz o que guarda; com atalho, para onde ele vai; a que tem pastas dentro,
# quantas delas tem atalho. Curta: numa tela de 15 kHz so cabem umas 30 letras
# (a linha escolhida rola, as outras nao).
screen_folders_label() {
  local rel=$1 width=${2:-13} name=${1##*/}/ inside purpose
  purpose=$(folders_purpose "$rel")
  if [[ -L $FOLDERS_HOME/$rel ]]; then
    case $(folders_state "$rel") in
      custom)
        printf '%-*s shortcut to %s\n' "$width" "$name" "$(folders_target "$rel")"
        return 0
        ;;
      offline)
        printf '%-*s shortcut NOT FOUND (disk off?): %s\n' "$width" "$name" "$(folders_target "$rel")"
        return 0
        ;;
    esac
  fi
  if folders_container "$rel"; then
    inside=$(folders_customs "$rel" | wc -l)
    if ((inside > 0)); then
      printf '%-*s %d shortcut%s\n' "$width" "$name" "$inside" "$( ((inside > 1)) && echo s)"
      return 0
    fi
  fi
  printf '%-*s %s\n' "$width" "$name" "$purpose" | sed 's/ *$//'
}

# screen_folders_help: o que e um atalho de pasta, com um exemplo.
screen_folders_help() {
  ui_msg "Folder shortcuts" \
    "A shortcut sends a FliperOS folder to another disk. It used to be called Link: the old Link this to another folder is now Point it to a folder on another disk." "" \
    "Example: ~/roms/mame is on the disk of the cabinet, and your external hard disk has the MAME games in HD/mame. Pick roms, then mame, then Point it to a folder on another disk, and open HD/mame." "" \
    "From then on the games show up as if they were in ~/roms/mame: the frontends, the Downloader and the network share all use them." "" \
    "Nothing is copied or deleted. The folder used before stays beside it, as old-mame, and Remove the shortcut brings it back." "" \
    "Do the same for BIOS, art, saves and the folder of an emulator or of a RetroArch core. For a whole disk, use External storage instead."
}

# screen_folders_shortcuts (Folders > Folder shortcuts): a lista das pastas.
screen_folders_shortcuts() {
  local title="Folder shortcuts" choice last="" name restored=() entries
  while true; do
    # O que foi mexido a mao desde a ultima vez.
    mapfile -t restored < <(folders_check)
    if ((${#restored[@]})); then
      folders_populate
      for name in "${restored[@]}"; do
        ui_msg "$title" "~/$name had lost its shortcut." "" \
          "The folder used before it (old-${name##*/}) is ~/$name again."
      done
    fi
    entries=("help|How shortcuts work")
    for name in $FOLDERS_NAMES; do
      entries+=("$name|$(screen_folders_label "$name")")
    done
    # Pastas: na interface grafica, a lista vertical em texto.
    choice=$(UI_STYLE=list ui_menu "$title" \
      "Formerly called Link. Send a folder to another disk (USB, second drive), like a shortcut. Nothing is copied or deleted." \
      "$last" "${entries[@]}" "-return|Return") || return 0
    [[ $choice == -return ]] && return 0
    last=$choice
    if [[ $choice == help ]]; then
      screen_folders_help
    else
      screen_folder "$choice"
    fi
  done
}

# screen_folder PASTA: a pasta, o atalho dela, as duas acoes e as pastas de
# dentro.
screen_folder() {
  local rel=$1 title="Folders: ~/$1" state choice last="" old fields entries child width text
  local -a children
  while true; do
    state=$(folders_state "$rel")
    old=$(folders_old "$rel")
    fields=()
    entries=()
    case $state in
      custom)
        fields+=("Now|shortcut to another disk" "Points to|$(folders_target "$rel")")
        entries+=("link|Change where it points")
        ;;
      offline)
        fields+=("Now|$(ui_no "shortcut, but the disk is off")" "Points to|$(folders_target "$rel")")
        entries+=("link|Change where it points")
        ;;
      *)
        fields+=("Now|on this disk (the default folder)")
        entries+=("link|Point it to a folder on another disk")
        ;;
    esac
    [[ -d $old ]] && fields+=("Folder used before|${old/#$FOLDERS_HOME/\~}")
    [[ $state == custom || $state == offline ]] && entries+=("unlink|Remove the shortcut (go back to the folder on this disk)")
    mapfile -t children < <(folders_children "$rel")
    width=0
    for child in "${children[@]}"; do
      child=${child##*/}
      ((${#child} >= width)) && width=$((${#child} + 1))
    done
    for child in "${children[@]}"; do
      entries+=("$child|$(screen_folders_label "$child" "$width")")
    done
    text=$(folders_description "$rel")
    ((${#children[@]})) && text+=$'\n'"The folders inside it can each have their own shortcut."
    choice=$(UI_STYLE=list ui_menu "$title" "${text:+$text$'\n\n'}$(ui_fields "${fields[@]}")" "$last" \
      "${entries[@]}" "return|Return") || return 0
    last=$choice
    case $choice in
      link) screen_folder_add "$rel" ;;
      unlink) screen_folder_unlink "$rel" ;;
      return) return 0 ;;
      *) screen_folder "$choice" ;;
    esac
  done
}

# screen_folders_refresh PASTA: as pastas de jogos e de arte mudaram de
# lugar, o frontend padrao le de novo.
screen_folders_refresh() {
  [[ $1 == roms || $1 == roms/* || $1 == media || $1 == media/* ]] || return 0
  ui_info "Folders" "Putting the game folders in the frontend..."
  frontends_configure "$(launcher_current)"
}

screen_folder_add() {
  local rel=$1 title="Folders: ~/$1" target state kept=() n
  state=$(folders_state "$rel")
  # Sempre a partir de onde os discos estao montados.
  target=$(ui_browse "$title" \
    "The disks connected now (hard disk, SSD, USB stick). Open the folder to use in place of ~/$rel, then Use this folder." \
    "$(folders_browse_start)" dir) || return 0
  if ! folders_validate "$rel" "$target"; then
    ui_msg "$title" "$FOLDERS_ERROR"
    return 0
  fi
  # Uma pasta com varios consoles dentro (um Batocera filesystem, a roms/ de
  # outro sistema) nao e a pasta de um sistema so: os jogos nao aparecem.
  if [[ $rel == roms || $rel == roms/* ]] && n=$(folders_looks_like_systems "$target"); then
    ui_yesno "$title" "$target looks like a folder with many consoles ($n of them: snes, megadrive, psx...), not the games of ~/$rel alone. The games would not show up. To use a disk that is organized like that, go back and pick External storage > Batocera filesystem. Use it as ~/$rel anyway?" no ||
      return 0
  fi
  if [[ $state == default && ! -L $FOLDERS_HOME/$rel ]]; then
    ui_yesno "$title" "Use $target as ~/$rel? ~/$rel becomes a shortcut to it, and the folder used until now is renamed to old-${rel##*/}, with everything in it. Nothing is copied or deleted." yes ||
      return 0
  else
    ui_yesno "$title" "Use $target as ~/$rel? Nothing is copied or deleted." yes || return 0
  fi
  ui_info "$title" "Linking ~/$rel to $target..."
  if ! folders_link "$rel" "$target"; then
    ui_msg "$title" "${FOLDERS_ERROR:-Could not link the folder (details in the log).}"
    return 0
  fi
  [[ -n $FOLDERS_KEPT ]] && kept=("" "The folder used before is ${FOLDERS_KEPT/#$FOLDERS_HOME/\~}.")
  screen_folders_refresh "$rel"
  ui_msg "$title" "~/$rel is now $target." "${kept[@]}" "" \
    "Remove the shortcut brings the previous one back."
}

screen_folder_unlink() {
  local rel=$1 title="Folders: ~/$1" old rc=0
  old=$(folders_old "$rel")
  if [[ -d $old && ! -L $old ]]; then
    ui_yesno "$title" "Remove the shortcut? ~/$rel goes back to the folder used before it (${old/#$FOLDERS_HOME/\~}). Nothing is deleted from the other disk." yes ||
      return 0
  else
    ui_yesno "$title" "Remove the shortcut? The folder used before it (${old/#$FOLDERS_HOME/\~}) is not there anymore: a new, empty ~/$rel is created. Nothing is deleted from the other disk." yes ||
      return 0
  fi
  ui_info "$title" "Removing the shortcut..."
  folders_unlink "$rel" || rc=$?
  if ((rc == 1)); then
    ui_msg "$title" "${FOLDERS_ERROR:-Could not unlink the folder (details in the log).}"
    return 0
  fi
  screen_folders_refresh "$rel"
  if ((rc == 2)); then
    ui_msg "$title" "~/$rel is a new, empty folder: the one used before was not found."
  else
    ui_msg "$title" "~/$rel is the folder used before again."
  fi
}
