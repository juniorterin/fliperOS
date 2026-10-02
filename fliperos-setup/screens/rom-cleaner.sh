# shellcheck shell=bash
# Setup > MAME ROM Cleaner: a pasta das ROMs (seletor de pastas), a versao
# do MAME do romset (o XML dela), as regras, a previa e entao mover (o
# padrao, para "<pasta>-removed") ou apagar. A logica e a lib/romclean.sh.

screen_rom_cleaner() {
  local title="MAME ROM Cleaner" folder source start entries
  start=$ROMS_ROOT
  [[ -d $start ]] || start=/
  folder=$(ui_browse "$title" "Open the ROMs folder, then Use this folder." "$start" dir) || return 0
  [[ -d $folder ]] || return 0

  entries=("groovymame|$(romclean_source_label groovymame), this system's MAME")
  [[ -f $MAME2010_XML ]] && entries+=("mame2010|MAME 2010 (0.139), the RetroArch mame2010 core")
  entries+=("file|Another XML file (from mame -listxml)")
  source=$(ui_menu "$title" "Which MAME version is this romset for? Its XML says what each set is. Folder: $folder" \
    "$(romclean_default_source "$folder")" "${entries[@]}") || return 0
  if [[ $source == file ]]; then
    source=$(ui_browse "$title" "Choose the XML file (from mame -listxml)." "$(dirname -- "$folder")" file \
      .xml .xml.xz) || return 0
  fi
  screen_rom_cleaner_rules "$folder" "$source"
}

# screen_rom_cleaner_rules PASTA FONTE: marca as regras (Enter marca e
# desmarca, joystick incluso) e segue para a previa.
screen_rom_cleaner_rules() {
  local folder=$1 source=$2 title="MAME ROM Cleaner" last="" entry key mark choice rules entries
  local -A on=()
  while true; do
    entries=()
    for entry in "${ROMCLEAN_RULES[@]}"; do
      key=${entry%%|*}
      mark="[ ]"
      [[ -n ${on[$key]:-} ]] && mark="[x]"
      entries+=("$key|$mark ${entry#*|}")
    done
    entries+=("scan|Continue" "return|Return")
    choice=$(ui_menu "$title" \
      "Mark what to remove (Enter marks or unmarks). The parent, BIOS and devices of the games that stay always stay." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      scan)
        rules=()
        for entry in "${ROMCLEAN_RULES[@]}"; do
          key=${entry%%|*}
          [[ -n ${on[$key]:-} ]] && rules+=("$key")
        done
        if ((${#rules[@]} == 0)); then
          ui_msg "$title" "Mark at least one rule."
          continue
        fi
        screen_rom_cleaner_run "$folder" "$source" "${rules[@]}"
        return 0
        ;;
      *)
        if [[ -n ${on[$choice]:-} ]]; then
          unset "on[$choice]"
        else
          on[$choice]=1
        fi
        ;;
    esac
  done
}

# screen_rom_cleaner_run PASTA FONTE REGRA...: le o XML, mostra o que sai e
# move ou apaga.
screen_rom_cleaner_run() {
  local folder=$1 source=$2 title="MAME ROM Cleaner" plan list summary remove dest choice result n
  shift 2
  plan=$(mktemp) list=$(mktemp)
  ui_info "$title" "Reading the MAME XML and the folder..." "With GroovyMAME this takes about a minute."
  if ! summary=$(romclean_scan "$folder" "$source" "$plan" "$@" 2>> "$FLIPEROS_LOG"); then
    ui_msg "$title" "$(ui_bad "Could not read the XML or the folder.")" "Details in $FLIPEROS_LOG."
    rm -f "$plan" "$list"
    return 0
  fi
  if [[ $(romclean_value "$summary" sets) == 0 ]]; then
    ui_msg "$title" "No set of this MAME version in $folder." "Is it the right folder, and the right version?"
    rm -f "$plan" "$list"
    return 0
  fi
  remove=$(romclean_value "$summary" remove)
  dest=$(romclean_dest "$folder")
  local fields
  fields=$(ui_fields \
    "Folder|$folder" \
    "MAME|$(romclean_source_label "$source")" \
    "Sets found|$(romclean_value "$summary" sets)" \
    "Stay|$(romclean_value "$summary" keep) ($(romclean_value "$summary" needed) only because games need them)" \
    "Go|$remove ($(human_bytes "$(romclean_value "$summary" bytes)"))" \
    "Not in the XML|$(romclean_value "$summary" unknown) (left as they are)")
  if ((remove == 0)); then
    ui_msg "$title" "$fields" "" "Nothing to remove."
    rm -f "$plan" "$list"
    return 0
  fi
  romclean_list "$plan" > "$list"
  n=$(wc -l < "$list")
  ((n > 1200)) && printf '\n... and %d more.\n' $((n - 1200)) >> "$list"
  while true; do
    choice=$(ui_menu "$title" "$fields" move \
      "move|Move them to $dest" \
      "list|See the list" \
      "delete|Delete them for good" \
      "cancel|Cancel") || choice=cancel
    case $choice in
      list) ui_pager "$title" "$list" inicio ;;
      move)
        result=$(romclean_apply "$plan" move "$dest" 2>> "$FLIPEROS_LOG")
        ui_msg "$title" "$(romclean_value "$result" moved) files moved to $dest." \
          "To bring one back, move it to $folder again."
        break
        ;;
      delete)
        ui_yesno "$title" "Delete the $remove sets for good? This can't be undone." no || continue
        result=$(romclean_apply "$plan" delete 2>> "$FLIPEROS_LOG")
        ui_msg "$title" "$(romclean_value "$result" deleted) files deleted."
        break
        ;;
      cancel) break ;;
    esac
  done
  rm -f "$plan" "$list"
}
