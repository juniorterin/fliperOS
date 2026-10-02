# shellcheck shell=bash
# Setup > MAME ROM Cleaner: a pasta com o romset (seletor de pastas), a
# versao do MAME dele (o XML), os filtros (presets como os do MAME Smart ROM
# Sorter), a previa, mover o que passou para a pasta do MAME e perguntar se
# apaga o que sobrou na origem. A logica e a lib/romclean.sh.

screen_rom_cleaner() {
  local title="MAME ROM Cleaner" folder source start entries
  start=$ROMS_ROOT
  [[ -d $start ]] || start=/
  folder=$(ui_browse "$title" "Open the folder with the romset, then Use this folder." "$start" dir) || return 0
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
  screen_rom_cleaner_filters "$folder" "$source"
}

# screen_rom_cleaner_filters ORIGEM FONTE: o preset, cada filtro (Enter passa
# para o valor seguinte, joystick incluso) e o destino; depois a previa.
screen_rom_cleaner_filters() {
  local folder=$1 source=$2 title="MAME ROM Cleaner" last=preset preset=cabinet dest key line choice entries
  local -A opt=()
  local -a args kv
  dest=$(romclean_default_dest "$source")
  while IFS= read -r line; do
    opt[${line%%=*}]=${line#*=}
  done < <(romclean_preset "$preset")
  while true; do
    entries=("preset|Preset: $(screen_rom_cleaner_preset_label "$preset")")
    for key in "${ROMCLEAN_KEYS[@]}"; do
      entries+=("$key|$(romclean_label "$key" "${opt[$key]}")")
    done
    entries+=("dest|To: $dest" "scan|Continue" "return|Return")
    choice=$(ui_menu "$title" \
      "Choose what goes to the MAME folder (Enter changes). The parent, BIOS and devices of those games go too." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      preset)
        case $preset in
          cabinet) preset=working ;;
          working) preset=psx ;;
          *) preset=cabinet ;;
        esac
        while IFS= read -r line; do
          opt[${line%%=*}]=${line#*=}
        done < <(romclean_preset "$preset")
        ;;
      dest)
        line=$(ui_browse "$title" "Choose the MAME folder the games go to." "$ROMS_ROOT" dir) && dest=$line
        ;;
      scan)
        kv=()
        for key in "${ROMCLEAN_KEYS[@]}"; do
          kv+=("$key=${opt[$key]}")
        done
        mapfile -t args < <(romclean_args "${kv[@]}")
        screen_rom_cleaner_run "$folder" "$source" "$dest" "${args[@]}"
        return 0
        ;;
      *)
        opt[$choice]=$(romclean_next "$choice" "${opt[$choice]}")
        preset=custom
        ;;
    esac
  done
}

# screen_rom_cleaner_preset_label NOME imprime o nome do preset para a tela.
screen_rom_cleaner_preset_label() {
  case $1 in
    cabinet) echo "Joystick cabinet (2 players, 6 buttons)" ;;
    working) echo "Everything that works" ;;
    psx) echo "PlayStation-based hardware (Tekken 3...)" ;;
    *) echo "Custom" ;;
  esac
}

# screen_rom_cleaner_run ORIGEM FONTE DESTINO OPCAO...: le o XML, mostra o
# que vai, move e pergunta se apaga o que sobrou.
screen_rom_cleaner_run() {
  local folder=$1 source=$2 dest=$3 title="MAME ROM Cleaner" plan list summary move rest fields choice result same=0
  shift 3
  plan=$(mktemp) list=$(mktemp)
  ui_info "$title" "Reading the MAME XML and the folder..." "With GroovyMAME this takes about a minute."
  if ! summary=$(romclean_scan "$folder" "$source" "$dest" "$plan" "$@" 2>> "$FLIPEROS_LOG"); then
    ui_msg "$title" "$(ui_bad "Could not read the XML or the folder.")" "Details in $FLIPEROS_LOG."
    rm -f "$plan" "$list"
    return 0
  fi
  if [[ $(romclean_value "$summary" sets) == 0 ]]; then
    ui_msg "$title" "No set of this MAME version in $folder." "Is it the right folder, and the right version?"
    rm -f "$plan" "$list"
    return 0
  fi
  [[ $(cd -- "$folder" && pwd -P) == $(cd -- "$dest" 2> /dev/null && pwd -P) ]] && same=1
  move=$(romclean_value "$summary" move)
  rest=$(romclean_value "$summary" rest)
  fields=$(ui_fields \
    "From|$folder" \
    "MAME|$(romclean_source_label "$source")" \
    "Sets found|$(romclean_value "$summary" sets)" \
    "MAME folder|$dest" \
    "Going there|$move ($(human_bytes "$(romclean_value "$summary" move_bytes)"), $(romclean_value "$summary" needed) as parent, BIOS or device)" \
    "Left over|$rest ($(human_bytes "$(romclean_value "$summary" rest_bytes)"))" \
    "Not in the XML|$(romclean_value "$summary" unknown) (left alone)")
  romclean_list "$plan" move > "$list"
  (($(wc -l < "$list") > 1200)) && printf '\n... and %d more.\n' $(($(wc -l < "$list") - 1200)) >> "$list"
  while ((!same && move > 0)); do
    choice=$(ui_menu "$title" "$fields" move \
      "move|Move them to $dest" \
      "list|See the list" \
      "cancel|Cancel") || choice=cancel
    case $choice in
      list) ui_pager "$title" "$list" inicio ;;
      move)
        ui_info "$title" "Moving $move sets to $dest..."
        result=$(romclean_apply "$plan" move 2>> "$FLIPEROS_LOG")
        ui_msg "$title" "$(romclean_value "$result" moved) files moved to $dest." \
          "$(romclean_value "$result" skipped) were already there."
        break
        ;;
      *)
        rm -f "$plan" "$list"
        return 0
        ;;
    esac
  done
  if ((same)); then
    ui_msg "$title" "$fields" "" "This is the MAME folder already: the games that passed stay in it."
  elif ((move == 0)); then
    ui_msg "$title" "$fields" "" "No game passed the filters: nothing to move."
  fi
  if ((rest > 0)); then
    if ui_yesno "$title" "$rest sets didn't pass the filters and are still in $folder ($(human_bytes "$(romclean_value "$summary" rest_bytes)")). Delete them for good? This can't be undone." no; then
      result=$(romclean_apply "$plan" delete-rest 2>> "$FLIPEROS_LOG")
      ui_msg "$title" "$(romclean_value "$result" deleted) files deleted."
    fi
  fi
  rm -f "$plan" "$list"
}
