# shellcheck shell=bash
# Setup > Games > Folders > External storage: um disco que nao e o principal (um
# HD externo, um SSD, outro disco interno), de dois jeitos:
#   FliperOS folders     a pasta "fliperos" dele com a estrutura do FliperOS, e
#                        formatar o disco (lib/storage.sh);
#   Batocera filesystem  um disco que ja tem as roms nas pastas do Batocera
#                        (batocera/roms/<console>): cada console vira um sistema
#                        com o core escolhido (lib/batocera.sh).

screen_external_storage() {
  local title="External storage" choice last=""
  while true; do
    choice=$(ui_menu_hints "$title" "" "$last" \
      "storage|FliperOS folders|Use a disk for ROMs, BIOS, art and saves, or format it." \
      "batocera|Batocera filesystem|Use a disk that already has Batocera folders." \
      "return|Return|Back to Folders.") || return 0
    last=$choice
    case $choice in
      storage) screen_storage ;;
      batocera) screen_batocera ;;
      return) return 0 ;;
    esac
  done
}

# screen_storage (External storage > FliperOS folders): os discos secundarios
# (um HD externo, outro disco) com a pasta "fliperos" e a estrutura do FliperOS
# dentro (lib/storage.sh). Escolher um deixa usar tudo nele (as ROMs, a BIOS,
# a arte, os saves e o que se baixa; o disco principal segue como esta, com o
# que ja tinha ao lado), so preparar as pastas, ou formatar o disco; ou voltar
# ao disco principal.
screen_storage() {
  local title="FliperOS folders" line mount label fs total free usable state last="" choice what
  local -a entries
  while true; do
    entries=()
    while IFS='|' read -r mount label fs total free usable state; do
      [[ -n $mount ]] || continue
      what="$label ($fs, $(human_size "$total"), $(human_size "$free") free)"
      case $state in
        all) what+=" - in use" ;;
        some) what+=" - partly in use" ;;
      esac
      ((usable)) || what+=" - not usable"
      entries+=("$mount|$what")
    done < <(storage_list)
    if ((${#entries[@]} == 0)); then
      ui_msg "$title" "No second or external disk is connected." "" \
        "Connect a disk of $((STORAGE_MIN_BYTES / 1000000000)) GB or more: it gets a fliperos folder with the" \
        "whole folder structure, ready for ROMs, art and saves."
      return 0
    fi
    entries+=("unuse|Back to the main disk" "return|Return")
    choice=$(UI_STYLE=list ui_menu "$title" \
      "A second disk keeps the ROMs, BIOS, art and saves in a fliperos folder, next to the main disk. Pick a disk to use it or format it." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      unuse)
        ui_yesno "$title" "Go back to the main disk for the ROMs, BIOS, art and saves? Nothing is deleted from the second disk." yes || continue
        if line=$(storage_cli unuse); then
          ui_msg "$title" "The main disk is back." "" "What the second disk has stays in its fliperos folder."
        else
          ui_msg "$title" "$(ui_bad "$line")"
        fi
        ;;
      *) screen_storage_disk "$choice" ;;
    esac
  done
}

# screen_storage_disk MONTAGEM: um disco: usar para tudo, so preparar a
# estrutura, ou formatar.
screen_storage_disk() {
  local mount=$1 title="FliperOS folders" choice line state label
  label=${mount##*/}
  state=$(storage_state "$mount")
  choice=$(ui_menu_hints "$title: $label" "" use \
    "use|Use $label|Use $label/fliperos for ROMs, art, saves and downloads." \
    "prepare|Only prepare the folders|Only make the folders in $label/fliperos." \
    "format|Format this disk|Erase it and start clean, as ext4 or exFAT." \
    "return|Return|Back to the disks.") || return 0
  case $choice in
    use | prepare)
      if ! storage_usable "$mount"; then
        ui_msg "$title" "$(ui_bad "$STORAGE_ERROR")"
        return 0
      fi
      if [[ $choice == use ]]; then
        ui_yesno "$title" "Use $label for the ROMs, BIOS, art, saves and downloads? The folders in your home are kept beside, as old-." yes || return 0
      fi
      if line=$(storage_cli "$choice" "$mount"); then
        if [[ $choice == use ]]; then
          ui_msg "$title" "$label is in use." "" "ROMs, BIOS, art, saves and downloads now go to $label/fliperos." \
            "$(sed -n 's/^kept=/The folder of before stays in /p' <<< "$line" | head -n 1)"
        else
          ui_msg "$title" "$label/fliperos is ready: the whole folder structure is there."
        fi
      else
        ui_msg "$title" "$(ui_bad "$line")"
      fi
      ;;
    format) screen_storage_format "$mount" ;;
  esac
  return 0
}

# screen_storage_format MONTAGEM: apaga a particao do disco e a formata (ext4:
# o melhor para o FliperOS; exFAT: o Windows e o Mac tambem abrem). Duas
# confirmacoes, a segunda com "Cancel" na frente.
screen_storage_format() {
  local mount=$1 title="Format a disk" info model total label fs used dev batocera fmt choice out newmount warn=""
  if ! info=$(storage_cli format-info "$mount"); then
    ui_msg "$title" "$(ui_bad "$info")"
    return 0
  fi
  IFS='|' read -r model total label fs used dev batocera <<< "$info"
  ((batocera)) && warn=" It has a Batocera filesystem: all its games and saves go too."
  ui_yesno "$title" "Erase everything on $label? $model, $(human_size "$total") ($dev, $fs), with $(human_size "$used") in use. All of it is lost and cannot be brought back.$warn" no || return 0
  fmt=$(ui_menu_hints "$title" "Which format?" ext4 \
    "ext4|ext4 (best for FliperOS)|Fastest. Windows can not open it." \
    "exfat|exFAT (Windows and Mac too)|Slower and with no links: art is kept apart." \
    "return|Cancel|Leave the disk as it is.") || return 0
  [[ $fmt == return ]] && return 0
  choice=$(UI_STYLE=list ui_menu "$title" \
    "Last chance: $label ($model, $(human_size "$total")) will be erased and formatted as $fmt." cancel \
    "cancel|Cancel: keep everything" "erase|Yes, erase everything") || return 0
  [[ $choice == erase ]] || return 0
  ui_info "$title" "Formatting $label as $fmt... This takes a moment."
  if out=$(storage_cli format "$mount" "$fmt"); then
    newmount=$(sed -n 's/^mount=//p' <<< "$out" | head -n 1)
    ui_msg "$title" "The disk is formatted as $fmt." "" "It is empty, with the name ${newmount##*/}."
    if ui_yesno "$title" "Use it now for the ROMs, BIOS, art, saves and downloads?" yes; then
      if out=$(storage_cli use "$newmount"); then
        ui_msg "$title" "${newmount##*/} is in use." "" "ROMs, BIOS, art, saves and downloads now go to ${newmount##*/}/fliperos."
      else
        ui_msg "$title" "$(ui_bad "$out")"
      fi
    else
      storage_cli answer "$newmount" no > /dev/null 2>&1
    fi
  else
    ui_msg "$title" "$(ui_bad "$out")"
  fi
  return 0
}

# ── Batocera filesystem ─────────────────────────────────────────

# screen_batocera (External storage > Batocera filesystem): os discos que tem as
# roms nas pastas do Batocera.
screen_batocera() {
  local title="Batocera filesystem" mount fs n what last="" choice
  local -a entries
  while true; do
    entries=()
    while IFS= read -r mount; do
      [[ -n $mount ]] || continue
      batocera_detect "$mount" > /dev/null || continue
      fs=$(findmnt -rno FSTYPE -T "$mount" 2> /dev/null | head -n 1)
      n=$(batocera_known_count "$mount")
      what="${mount##*/} (${fs:-?}, $n consoles)"
      batocera_in_use "$mount" && what+=" - in use"
      entries+=("$mount|$what")
    done < <(storage_mounts)
    if ((${#entries[@]} == 0)); then
      ui_msg "$title" "No disk with Batocera folders was found." "" \
        "A Batocera disk keeps the games in batocera/roms/<console>," \
        "as snes, megadrive or psx. Connect it and open this again."
      return 0
    fi
    entries+=("return|Return")
    choice=$(UI_STYLE=list ui_menu "$title" \
      "Disks with the games in Batocera folders (batocera/roms/snes...). FliperOS reads them where they are: nothing is moved." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      *) screen_batocera_disk "$choice" ;;
    esac
  done
}

# screen_batocera_disk MONTAGEM: usar o disco (tudo o que ele tem), escolher o
# core de cada console, ou deixar de usar.
screen_batocera_disk() {
  local mount=$1 title="Batocera filesystem" label choice last="" out line n=0 extra
  local -a items
  label=${mount##*/}
  while true; do
    if batocera_in_use "$mount"; then
      items=("cores|Cores of the consoles|Choose what opens the games of each console." \
        "best|Best core for all|Give every console the core FliperOS prefers for it." \
        "unuse|Stop using it|Give the folders back to the main disk." \
        "return|Return|Back to the disks.")
    else
      items=("use|Use it (everything it has)|Consoles, BIOS, saves and art of this disk." \
        "return|Return|Back to the disks.")
    fi
    choice=$(ui_menu_hints "$title: $label" "" "$last" "${items[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      use)
        ui_yesno "$title" "Use the Batocera filesystem of $label? Its consoles become systems of the frontends, each with a default core you can change. Its bios, saves, nvram and snap folders become the ones of FliperOS, and FliperOS adds its own system folders beside the consoles. Nothing is copied or deleted: the folders in your home are kept beside, as old-." yes || continue
        ui_info "$title" "Setting up $label..."
        if out=$(batocera_cli use "$mount"); then
          n=$(sed -n 's/^systems=//p' <<< "$out" | head -n 1)
          local -a lines=("$label is in use." "" "${n:-0} consoles are systems of the frontends now.")
          line=$(sed -n 's/^linked=//p' <<< "$out" | head -n 1)
          [[ -n $line ]] && lines+=("Now from the disk: ${line//,/, }.")
          extra=$(sed -n 's/^extras=//p' <<< "$out" | head -n 1)
          [[ -n $extra ]] && lines+=("FliperOS folders added beside the consoles: ${extra//,/, }.")
          grep -q '^readonly=1' <<< "$out" && lines+=("" "The disk is read only: only the games are used.")
          while IFS= read -r line; do
            lines+=("Left as it was: ${line#skipped=}")
          done < <(grep '^skipped=' <<< "$out")
          lines+=("" "Choose the core of each console in Cores of the consoles.")
          ui_msg "$title" "${lines[@]}"
        else
          ui_msg "$title" "$(ui_bad "$out")"
        fi
        ;;
      cores) screen_batocera_consoles "$mount" ;;
      best)
        ui_yesno "$title" "Give every console of $label the core FliperOS prefers for it? The cores you chose are replaced." no || continue
        ui_info "$title" "Choosing the cores..."
        if out=$(batocera_cli auto "$mount" reset); then
          ui_msg "$title" "Done: $out consoles have their best core."
        else
          ui_msg "$title" "$(ui_bad "$out")"
        fi
        ;;
      unuse)
        ui_yesno "$title" "Stop using the Batocera filesystem of $label? The consoles leave the frontends and the folders of your home go back to what they were. Nothing is deleted from the disk." yes || continue
        ui_info "$title" "Putting the folders back..."
        if out=$(batocera_cli unuse "$mount"); then
          ui_msg "$title" "$label is not used anymore." "" "The games and files stay on the disk."
        else
          ui_msg "$title" "$(ui_bad "$out")"
        fi
        ;;
    esac
  done
}

# screen_batocera_consoles MONTAGEM: os consoles do disco e o core de cada um.
screen_batocera_consoles() {
  local mount=$1 title="Cores of the consoles" system label folder games choice core last="" width unknown name line
  local -a rows entries
  while true; do
    mapfile -t rows < <(batocera_scan "$mount")
    entries=()
    width=0
    for line in "${rows[@]}"; do
      IFS='|' read -r system label _ <<< "$line"
      ((${#label} >= width)) && width=$((${#label} + 1))
    done
    for line in "${rows[@]}"; do
      IFS='|' read -r system label folder games choice core <<< "$line"
      # Curta, para a tela de 15 kHz: o console e o core (a linha escolhida mostra tambem os jogos).
      entries+=("$system|$(printf '%-*s %s' "$width" "$label" "$(screen_batocera_choice_label "$system" "${choice:-$core}" "$choice")")")
    done
    unknown=$(batocera_unknown "$mount")
    ((${unknown:-0} > 0)) || unknown=""
    entries+=("return|Return")
    choice=$(UI_STYLE=list ui_menu "$title" \
      "Pick a console to choose what opens its games.${unknown:+ $unknown $( ((unknown == 1)) && echo "folder has" || echo "folders have") no emulator and $( ((unknown == 1)) && echo is || echo are) left out.}" \
      "$last" "${entries[@]}") || return 0
    last=$choice
    [[ $choice == return ]] && return 0
    name=$choice
    for line in "${rows[@]}"; do
      [[ ${line%%|*} == "$name" ]] || continue
      IFS='|' read -r system label folder _ <<< "$line"
      screen_batocera_core "$system" "$label" "$folder"
    done
  done
}

# screen_batocera_choice_label SISTEMA ESCOLHA ESCOLHIDA: o que abre o console,
# em palavras ("Snes9x", "choose a core" ainda sem escolha).
screen_batocera_choice_label() {
  local core=$2 label
  if [[ -z $3 ]]; then
    printf 'off (best: %s)\n' "$(screen_batocera_core_name "$core")"
  else
    screen_batocera_core_name "$core"
  fi
}

# screen_batocera_core_name ESCOLHA: o nome do core ou do emulador.
screen_batocera_core_name() {
  local name
  case $1 in
    retroarch/*)
      name=$(scraper_core_info "${1#retroarch/}" corename)
      printf '%s\n' "${name:-${1#retroarch/}}"
      ;;
    *)
      IFS='|' read -r name _ <<< "$(scraper_attract_emulator "$1")"
      printf '%s\n' "${name:-$1}"
      ;;
  esac
}

# screen_batocera_core SISTEMA ROTULO PASTA: a escolha do console.
screen_batocera_core() {
  local system=$1 label=$2 folder=$3 title="Core: $2" current choice last="" row what state default out
  local -a entries
  current=$(batocera_choice "$system" 2> /dev/null)
  while true; do
    entries=()
    while IFS='|' read -r row what state default; do
      [[ -n $row ]] || continue
      case $state in
        installed) state="" ;;
        download) state=" - downloads on first use" ;;
        emulator) state="" ;;
      esac
      ((default)) && state+=" - the best for it"
      [[ $row == "$current" ]] && state+=" - in use"
      entries+=("$row|$what$state")
    done < <(batocera_cores "$system")
    entries+=("off|Not used: hide this console" "return|Return")
    choice=$(UI_STYLE=list ui_menu "$title" \
      "Choose what opens the games in ${folder/#$FOLDERS_MOUNTS\//}. A core not installed downloads on the first game (needs internet)." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      off)
        batocera_cli unset "$system" > /dev/null
        current=""
        ui_msg "$title" "$label is out of the frontends." "" "Choose a core again to bring it back."
        ;;
      *)
        if out=$(batocera_cli set "$system" "$folder" "$choice"); then
          current=$choice
          ui_msg "$title" "$label opens with $(screen_batocera_core_name "$choice")."
        else
          ui_msg "$title" "$(ui_bad "$out")"
        fi
        ;;
    esac
  done
}
