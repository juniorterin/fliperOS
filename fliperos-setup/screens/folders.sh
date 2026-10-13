# shellcheck shell=bash
# Setup > Folders: as pastas de ~, das raizes as de cada emulador, core e
# tipo de arte, e a custom folder de cada uma (lib/folders.sh).

# screen_folders_label PASTA [LARGURA]: a linha da pasta numa lista. Uma
# pasta comum so mostra o nome; a que tem pastas dentro, quantas delas tem
# custom folder.
screen_folders_label() {
  local rel=$1 width=${2:-13} name=${1##*/}/ inside
  if [[ -L $FOLDERS_HOME/$rel ]]; then
    case $(folders_state "$rel") in
      custom)
        printf '%-*s custom folder: %s\n' "$width" "$name" "$(folders_target "$rel")"
        return 0
        ;;
      offline)
        printf '%-*s custom folder NOT FOUND: %s\n' "$width" "$name" "$(folders_target "$rel")"
        return 0
        ;;
    esac
  fi
  if folders_container "$rel"; then
    inside=$(folders_customs "$rel" | wc -l)
    if ((inside > 0)); then
      printf '%-*s %d custom inside\n' "$width" "$name" "$inside"
      return 0
    fi
  fi
  printf '%s\n' "$name"
}

screen_folders() {
  local title="Folders" choice last="" name restored=() entries
  while true; do
    # O que foi mexido a mao desde a ultima vez.
    mapfile -t restored < <(folders_check)
    if ((${#restored[@]})); then
      folders_populate
      for name in "${restored[@]}"; do
        ui_msg "$title" "~/$name had lost its custom folder link." "" \
          "The folder used before it (old-${name##*/}) is ~/$name again."
      done
    fi
    entries=()
    for name in $FOLDERS_NAMES; do
      entries+=("$name|$(screen_folders_label "$name")")
    done
    choice=$(ui_menu "$title" \
      "The folders FliperOS uses, in $FOLDERS_HOME. Any of them, or any folder inside (an emulator, a RetroArch core, a type of art), can have a custom folder: another folder used in its place, for when the ROMs, the art or the BIOS are on external storage (a USB disk, a second drive)." \
      "$last" "${entries[@]}" "-return|Return") || return 0
    [[ $choice == -return ]] && return 0
    last=$choice
    screen_folder "$choice"
  done
}

# screen_folder PASTA: a pasta, a custom folder dela, as duas acoes e as
# pastas de dentro.
screen_folder() {
  local rel=$1 title="Folders: ~/$1" state choice last=add old fields entries child width text
  local -a children
  while true; do
    state=$(folders_state "$rel")
    old=$(folders_old "$rel")
    fields=()
    entries=()
    case $state in
      custom)
        fields+=("Now|custom folder" "Linked to|$(folders_target "$rel")")
        entries+=("add|Change the custom folder")
        ;;
      offline)
        fields+=("Now|$(ui_no "custom folder not found (disk off?)")" "Linked to|$(folders_target "$rel")")
        entries+=("add|Change the custom folder")
        ;;
      *)
        fields+=("Now|default folder")
        entries+=("add|Add a custom folder")
        ;;
    esac
    [[ -d $old ]] && fields+=("Previous|${old/#$FOLDERS_HOME/\~}")
    [[ $state == custom || $state == offline ]] && entries+=("unlink|Unlink the custom folder")
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
    ((${#children[@]})) && text+=$'\n'"The folders inside it can each have their own custom folder."
    choice=$(ui_menu "$title" "${text:+$text$'\n\n'}$(ui_fields "${fields[@]}")" "$last" \
      "${entries[@]}" "return|Return") || return 0
    last=$choice
    case $choice in
      add) screen_folder_add "$rel" ;;
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
  local rel=$1 title="Folders: ~/$1" target state kept=()
  state=$(folders_state "$rel")
  # Sempre a partir de onde os discos estao montados.
  target=$(ui_browse "$title" \
    "The disks connected now (hard disk, SSD, USB stick). Open the folder to use in place of ~/$rel, then Use this folder." \
    "$(folders_browse_start)" dir) || return 0
  if ! folders_validate "$rel" "$target"; then
    ui_msg "$title" "$FOLDERS_ERROR"
    return 0
  fi
  if [[ $state == default && ! -L $FOLDERS_HOME/$rel ]]; then
    ui_yesno "$title" "Use $target as ~/$rel? ~/$rel becomes a link to it, and the folder used until now is renamed to old-${rel##*/}, with everything in it. Nothing is copied or deleted." yes ||
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
    "Unlink the custom folder brings the previous one back."
}

screen_folder_unlink() {
  local rel=$1 title="Folders: ~/$1" old rc=0
  old=$(folders_old "$rel")
  if [[ -d $old && ! -L $old ]]; then
    ui_yesno "$title" "Unlink the custom folder? ~/$rel goes back to the folder used before it (${old/#$FOLDERS_HOME/\~}). Nothing is deleted from the custom folder." yes ||
      return 0
  elif folders_default_link "$rel" > /dev/null; then
    ui_yesno "$title" "Unlink the custom folder? ~/$rel goes back to the FliperOS default. Nothing is deleted from the custom folder." yes ||
      return 0
  else
    ui_yesno "$title" "Unlink the custom folder? The folder used before it (${old/#$FOLDERS_HOME/\~}) is not there anymore: a new, empty ~/$rel is created. Nothing is deleted from the custom folder." yes ||
      return 0
  fi
  ui_info "$title" "Unlinking the custom folder..."
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
