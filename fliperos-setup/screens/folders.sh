# shellcheck shell=bash
# Setup > Folders: as pastas de ~ e a custom folder de cada uma
# (lib/folders.sh).

# screen_folders_label NOME: a linha da pasta na lista.
screen_folders_label() {
  case $(folders_state "$1") in
    custom) printf '%-13s custom folder: %s\n' "$1" "$(folders_target "$1")" ;;
    offline) printf '%-13s custom folder NOT FOUND: %s\n' "$1" "$(folders_target "$1")" ;;
    *) printf '%-13s default folder\n' "$1" ;;
  esac
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
          "The folder used before it (~/old-$name) is ~/$name again."
      done
    fi
    entries=()
    for name in $FOLDERS_NAMES; do
      entries+=("$name|$(screen_folders_label "$name")")
    done
    choice=$(ui_menu "$title" \
      "The folders FliperOS uses, in $FOLDERS_HOME. Choose one to give it a custom folder: another folder used in its place, for when the ROMs, the art or the BIOS are on external storage (a USB disk, a second drive)." \
      "$last" "${entries[@]}" "-return|Return") || return 0
    [[ $choice == -return ]] && return 0
    last=$choice
    screen_folder "$choice"
  done
}

# screen_folder NOME: a pasta, a custom folder dela e as duas acoes.
screen_folder() {
  local name=$1 title="Folders: ~/$1" state choice old fields entries
  while true; do
    state=$(folders_state "$name")
    old=$(folders_old "$name")
    fields=("Folder|$(folders_path "$name")")
    entries=()
    case $state in
      custom)
        fields+=("Now|custom folder" "Linked to|$(folders_target "$name")")
        entries+=("add|Change the custom folder")
        ;;
      offline)
        fields+=("Now|$(ui_no "custom folder not found (disk off?)")" "Linked to|$(folders_target "$name")")
        entries+=("add|Change the custom folder")
        ;;
      *)
        fields+=("Now|default folder")
        entries+=("add|Add a custom folder")
        ;;
    esac
    [[ -d $old ]] && fields+=("Previous|$old")
    [[ $state == custom || $state == offline ]] && entries+=("unlink|Unlink the custom folder")
    choice=$(ui_menu "$title" "$(folders_description "$name")"$'\n\n'"$(ui_fields "${fields[@]}")" add \
      "${entries[@]}" "return|Return") || return 0
    case $choice in
      add) screen_folder_add "$name" ;;
      unlink) screen_folder_unlink "$name" ;;
      return) return 0 ;;
    esac
  done
}

# screen_folders_refresh NOME: as pastas de jogos e de arte mudaram de lugar,
# o frontend padrao le de novo.
screen_folders_refresh() {
  [[ $1 == roms || $1 == media ]] || return 0
  ui_info "Folders" "Putting the game folders in the frontend..."
  frontends_configure "$(launcher_current)"
}

screen_folder_add() {
  local name=$1 title="Folders: ~/$1" start=/ target state kept=() path
  state=$(folders_state "$name")
  [[ -d /media ]] && start=/media
  path=$(find "$FOLDERS_MOUNTS" -mindepth 1 -maxdepth 1 -type d -print -quit 2> /dev/null)
  [[ -n $path ]] && start=$FOLDERS_MOUNTS
  target=$(ui_browse "$title" \
    "Open the folder to use in place of ~/$name, then Use this folder. The disks are in $FOLDERS_MOUNTS." \
    "$start" dir) || return 0
  if ! folders_validate "$name" "$target"; then
    ui_msg "$title" "$FOLDERS_ERROR"
    return 0
  fi
  if [[ $state == default ]]; then
    ui_yesno "$title" "Use $target as ~/$name? ~/$name becomes a link to it, and the folder used until now is renamed to ~/old-$name, with everything in it. Nothing is copied or deleted." yes ||
      return 0
  else
    ui_yesno "$title" "Use $target as ~/$name? Nothing is copied or deleted." yes || return 0
  fi
  ui_info "$title" "Linking ~/$name to $target..."
  if ! folders_link "$name" "$target"; then
    ui_msg "$title" "${FOLDERS_ERROR:-Could not link the folder (details in the log).}"
    return 0
  fi
  [[ -n $FOLDERS_KEPT ]] && kept=("" "The folder used before is ~/${FOLDERS_KEPT##*/}.")
  screen_folders_refresh "$name"
  ui_msg "$title" "~/$name is now $target." "${kept[@]}" "" \
    "The folders FliperOS expects that were missing in it have been created." \
    "Unlink the custom folder brings the previous one back."
}

screen_folder_unlink() {
  local name=$1 title="Folders: ~/$1" old rc=0
  old=$(folders_old "$name")
  if [[ -d $old && ! -L $old ]]; then
    ui_yesno "$title" "Unlink the custom folder? ~/$name goes back to the folder used before it (~/old-$name). Nothing is deleted from the custom folder." yes ||
      return 0
  else
    ui_yesno "$title" "Unlink the custom folder? The folder used before it (~/old-$name) is not there anymore: a new, empty ~/$name is created. Nothing is deleted from the custom folder." yes ||
      return 0
  fi
  ui_info "$title" "Unlinking the custom folder..."
  folders_unlink "$name" || rc=$?
  if ((rc == 1)); then
    ui_msg "$title" "${FOLDERS_ERROR:-Could not unlink the folder (details in the log).}"
    return 0
  fi
  screen_folders_refresh "$name"
  if ((rc == 2)); then
    ui_msg "$title" "~/$name is a new, empty folder: the one used before was not found."
  else
    ui_msg "$title" "~/$name is the folder used before again."
  fi
}
