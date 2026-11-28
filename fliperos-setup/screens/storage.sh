# shellcheck shell=bash
# Setup > Games > Folders > External storage: um disco que nao e o principal (um
# HD externo, um SSD, outro disco interno), de dois jeitos:
#   FliperOS folders     a pasta "fliperos" dele com a estrutura do FliperOS, e
#                        formatar o disco (lib/storage.sh);
#   Batocera filesystem  um disco que ja tem as roms nas pastas do Batocera
#                        (batocera/roms/<console>): cada console vira um sistema
#                        com o core escolhido (lib/batocera.sh).
# E a pasta de outro computador (Network folder: um NAS, o RetroNAS, um
# Windows), montada como mais um disco e usada de um dos dois jeitos
# (lib/netshare.sh).

screen_external_storage() {
  local title="External storage" choice last=""
  while true; do
    choice=$(ui_menu_hints "$title" "" "$last" \
      "storage|FliperOS folders|Use a disk for ROMs, BIOS, art and saves, or format it." \
      "batocera|Batocera filesystem|Use a disk that already has Batocera folders." \
      "netshare|Network folder|Play from a folder shared by a NAS, RetroNAS or a PC." \
      "return|Return|Back to Folders.") || return 0
    last=$choice
    case $choice in
      storage) screen_storage ;;
      batocera) screen_batocera ;;
      netshare) screen_netshares ;;
      return) return 0 ;;
    esac
  done
}

# screen_netshares (External storage > Network folder): as pastas da rede
# guardadas, cada uma montada em /media/fliperos/NOME a cada boot, e a de
# guardar uma nova.
screen_netshares() {
  local title="Network folder" name host share user mount state what last="" choice
  local -a entries
  if ! netshare_available; then
    ui_msg "$title" "$(ui_bad "cifs-utils is not installed.")" "Setup > System > System Update brings it."
    return 0
  fi
  while true; do
    entries=()
    # O nome e o estado (o //servidor/pasta esta na tela de cada uma: aqui
    # nao cabe numa linha de 240p).
    while IFS='|' read -r name host share user mount state; do
      [[ -n $name ]] || continue
      what=$name
      if netshare_offline "$mount"; then
        what+=" - not answering"
      elif netshare_in_use "$mount"; then
        what+=" - in use"
      fi
      entries+=("$name|$what")
    done < <(netshare_list)
    entries+=("add|Add a network folder" "return|Return")
    choice=$(UI_STYLE=list ui_menu "$title" \
      "Folders of another computer (NAS, RetroNAS, PC). They open at every boot like one more disk, and the games play from there." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      add) screen_netshare_add ;;
      *) screen_netshare_one "$choice" ;;
    esac
  done
}

# screen_netshare_add pergunta o computador, o usuario, a senha e a pasta
# compartilhada, guarda e monta (lib/netshare.sh), e leva ao que fazer com ela.
screen_netshare_add() {
  local title="Network folder" host user pass="" share out
  host=$(ui_input "$title" "The computer that shares the folder: its IP or name (192.168.1.10)." "") || return 0
  host=${host#"${host%%[!/\\]*}"}
  host=${host%%[/\\]*}
  [[ -n $host ]] || return 0
  user=$(ui_input "$title" "Your user name on $host (empty: as a guest, no password)." "") || return 0
  if [[ -n $user ]]; then
    pass=$(ui_input "$title" "Password of $user on $host. It stays on this machine, where only the system reads it." \
      "" password) || return 0
  fi
  share=$(screen_netshare_pick_share "$title" "$host" "$user" "$pass" "") || return 0
  ui_info "$title" "Opening //$host/$share..."
  if ! out=$(printf '%s\n' "$pass" | netshare_cli add "$host" "$share" "$user"); then
    ui_msg "$title" "$(ui_bad "Could not open //$host/$share.")" "$out" "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  screen_netshare_next "$(sed -n 's/^mount=//p' <<< "$out" | head -n 1)" new
}

# screen_netshare_pick_share TITULO SERVIDOR USUARIO SENHA PADRAO imprime a
# pasta compartilhada escolhida: da lista do servidor, ou digitada quando ele
# nao lista. Status 1 = desistiu.
screen_netshare_pick_share() {
  local title=$1 host=$2 share s
  local -a shares=() entries=()
  ui_info "$title" "Looking for the shared folders of $host..."
  mapfile -t shares < <(netshare_shares "$host" "$3" "$4")
  if ((${#shares[@]})); then
    for s in "${shares[@]}"; do
      entries+=("$s|$s")
    done
    share=$(UI_STYLE=list ui_menu "$title" "Which shared folder of $host?" "$5" "${entries[@]}") || return 1
  else
    share=$(ui_input "$title" "The name of the shared folder on $host (what comes after \\\\$host\\)." "$5") || return 1
  fi
  [[ -n $share ]] || return 1
  printf '%s\n' "$share"
}

# screen_netshare_next MONTAGEM [new]: o que fazer com a pasta, pelo que ela
# tem: as pastas do Batocera (a copia que o RetroNAS faz, o compartilhamento
# de um Batocera) vao para o Batocera filesystem; a pasta fliperos, para
# FliperOS folders; o resto, para um atalho de pasta.
screen_netshare_next() {
  local mount=$1 title="Network folder" name
  [[ -n $mount ]] || return 0
  name=${mount##*/}
  case $(netshare_layout "$mount") in
    batocera)
      ui_yesno "$title" "${2:+$name is ready. }It has Batocera folders (batocera/roms/snes...). Use its consoles now, in Batocera filesystem?" yes &&
        screen_batocera_disk "$mount"
      ;;
    fliperos)
      ui_yesno "$title" "${2:+$name is ready. }It has the FliperOS folders. Use it for the ROMs, BIOS, art and saves now?" yes &&
        screen_storage_disk "$mount"
      ;;
    *)
      ui_msg "$title" "${2:+$name is ready, in $mount.}" "" \
        "To play from it, point a ROM folder to a folder in it:" \
        "Games > Folders > Folder shortcuts. Or keep a fliperos folder there with" \
        "External storage > FliperOS folders."
      ;;
  esac
  return 0
}

# screen_netshare_one NOME: usar a pasta guardada, ou esquece-la.
screen_netshare_one() {
  local name=$1 title="Network folder" line mount host share choice out
  line=$(netshare_list | awk -F'|' -v n="$name" '$1 == n' | head -n 1)
  [[ -n $line ]] || return 0
  IFS='|' read -r _ host share _ mount _ <<< "$line"
  choice=$(ui_menu_hints "$title: $name" "//$host/$share" use \
    "use|Use it|Play its games: Batocera folders, FliperOS folders..." \
    "remove|Forget this folder|Stop opening it here. Nothing leaves the server." \
    "return|Return|Back to the network folders.") || return 0
  case $choice in
    use)
      if netshare_offline "$mount"; then
        ui_msg "$title" "$(ui_bad "$host is not answering.")" "Turn it on (or check its address) and try again."
        return 0
      fi
      screen_netshare_next "$mount"
      ;;
    remove)
      ui_yesno "$title" "Forget //$host/$share? FliperOS stops opening it; nothing is deleted on $host." no || return 0
      if out=$(netshare_cli remove "$name"); then
        ui_msg "$title" "$name is no longer opened here."
      else
        ui_msg "$title" "$(ui_bad "$out")"
      fi
      ;;
  esac
  return 0
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
      fs=$(storage_findmnt FSTYPE "$mount")
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
