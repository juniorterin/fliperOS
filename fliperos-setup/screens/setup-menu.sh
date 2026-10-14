# shellcheck shell=bash
# Setup do sistema instalado (worker_setup_menu do gasetup), na ordem de
# quem arruma um gabinete: a imagem, o som, a rede, os controles, os jogos
# (Games) e o resto do sistema (System). Cada item tem o seu balao de
# informacao (ui_menu_hints).

screen_setup_menu() {
  local choice last=video
  while true; do
    screen_reload_if_updated
    UI_STATUS=$(status_line)
    choice=$(ui_menu_hints "Setup" "" "$last" \
      "video|Video Setup|Monitor, orientation, resolution, geometry, extra monitors." \
      "audio|Audio Setup|Sound card, volume, MAME audio latency and menu sounds." \
      "network|Network Setup|Wi-Fi and the network status. Downloads and updates need it." \
      "joysticks|Joysticks|Button mapping, light gun, wheel, LPT and USB controller fixes." \
      "games|Games|Frontend, emulators, game folders, downloads, cleaner and art." \
      "system|System|Extras, low latency, updates, debug mode and the boot splash." \
      "return|Return|Back to the FliperOS menu.") || return 0
    last=$choice
    case $choice in
      video) screen_video_setup ;;
      audio) screen_audio ;;
      network) screen_network ;;
      joysticks) screen_joysticks ;;
      games) screen_setup_games ;;
      system) screen_setup_system ;;
      return) return 0 ;;
    esac
  done
}

# screen_setup_games (Setup > Games), na ordem de por jogos no gabinete: o
# frontend, os emuladores, as pastas, baixar, limpar o romset e a arte.
screen_setup_games() {
  local choice last=frontend
  while true; do
    screen_reload_if_updated
    choice=$(ui_menu_hints "Games" "" "$last" \
      "frontend|Frontend|The game list that starts when the computer turns on." \
      "emulators|Emulators & Games|What is installed, and install what is not in the image." \
      "folders|Folders|Where ROMs, BIOS and art are; use an external disk instead." \
      "downloader|Downloader|MAME ROM/CHD sets by torrent and free homebrew games." \
      "cleaner|Cleaner|Filter a MAME romset: only the games you want, per emulator." \
      "scraper|Scraper|Download covers, screenshots, logos and videos of the games." \
      "romlist|AttractPlus ROM List|Attract-Mode Plus lists with the real name of each game." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      frontend) screen_frontend ;;
      emulators) screen_emulators ;;
      folders) screen_folders ;;
      downloader) screen_downloads ;;
      cleaner) screen_cleaner ;;
      scraper) screen_scraper ;;
      romlist) screen_romlist ;;
      return) return 0 ;;
    esac
  done
}

# screen_setup_system (Setup > System): o que nao e imagem, som, rede,
# controle nem jogo. O Splash screen por ultimo.
screen_setup_system() {
  local choice last=extras
  while true; do
    screen_reload_if_updated
    choice=$(ui_menu_hints "System" "" "$last" \
      "extras|Extras|Wine, Steam, Heroic, Pixelcade, ZeDMD and game output tools." \
      "latency|Latency|Standard or low latency mode, and a check of this computer." \
      "update|System Update|Download and install the updates of all packages." \
      "debug|Debug mode ($(debug_enabled && echo on || echo off))|Show boot and emulator messages on screen to find a problem." \
      "splash|Splash screen|The boot screen theme, with a preview." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      extras) screen_extras ;;
      latency) screen_latency ;;
      update) screen_update ;;
      debug) screen_debug ;;
      splash) screen_splash ;;
      return) return 0 ;;
    esac
  done
}

# ── Jogos livres ─────────────────────────────────────────────────

# screen_free_roms (Setup > Games > Downloader) baixa os jogos livres do
# config/fliperos-freeroms para as pastas dos cores do RetroArch
# (lib/freeroms.sh).
screen_free_roms() {
  local title="Free games" names result out
  names=$(freeroms_list | paste -sd'|' - | sed 's/|/, /g')
  ui_yesno "$title" "$(printf 'Open-source homebrew, from the releases of each project, so the frontends have something to show:\n\n%s\n\nDownload them to ~/roms/retroarch?' "$names")" || return 0
  result=$(mktemp)
  if run_with_progress "Downloading the free games" "" freeroms_fetch "$result"; then
    out=$(cat "$result")
    # As pastas novas com jogos entram no frontend padrao.
    ui_info "$title" "Putting the games in the frontend..."
    frontends_configure "$(launcher_current)"
    ui_msg "$title" "$(romclean_value "$out" downloaded) games downloaded." \
      "$(romclean_value "$out" present) were already there; $(romclean_value "$out" skipped) are for cores that are not installed." \
      "" "Setup > Games > Scraper gets their art and descriptions."
  fi
  rm -f "$result"
}

# ── Audio ────────────────────────────────────────────────────────

screen_audio() {
  local choice last=card devices=() current card_label
  while true; do
    mapfile -t devices < <(audio_devices)
    current=$(audio_current)
    card_label="none found"
    for entry in "${devices[@]}"; do
      [[ ${entry%%|*} == "$current" ]] && card_label=${entry#*|}
    done
    choice=$(ui_menu_hints "Audio Setup" \
      "$(ui_fields "Default card|$card_label" "Volume|$(audio_volume)% (keyboard volume keys work too)" \
        "MAME latency|$(audio_mame_latency)")" "$last" \
      "card|Default card|The sound card used by the system and the emulators." \
      "volume|Volume|From 0 to 100. The keyboard volume keys work too." \
      "mixer|AlsaMixer|Every control of the sound card, one by one." \
      "latency|MAME audio latency|Lower responds faster; raise it if the sound crackles." \
      "test|Test sound|Play a sound to check the speakers." \
      "sounds|Menu sounds ($(menu_sounds_label))|A sound when the cursor moves and on Enter (your own WAVs)." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      card)
        if ((${#devices[@]} == 0)); then
          ui_msg "Default card" "No sound card was found."
          continue
        fi
        choice=$(ui_menu "Default card" "Select the sound card used by the system and the emulators." \
          "$current" "${devices[@]}") || continue
        audio_set_default "$choice"
        ;;
      volume)
        choice=$(ui_input "Volume" "Audio volume (0-100)" "$(audio_volume)") || continue
        if [[ $choice =~ ^[0-9]+$ ]] && ((choice <= 100)); then
          audio_set_volume "$choice"
        else
          ui_msg "Volume" "Type a number from 0 to 100."
        fi
        ;;
      mixer)
        ui_clear
        alsamixer -c "${current%,*}" < /dev/tty > /dev/tty 2>&1
        run_logged alsactl store "${current%,*}"
        ui_flush_input
        ;;
      latency)
        choice=$(ui_input "MAME audio latency" \
          "GroovyMAME audio latency, 0.0 to 50.0 (0 = default). Lower responds faster; raise it if the sound crackles." \
          "$(audio_mame_latency)") || continue
        audio_set_mame_latency "$choice" || ui_msg "MAME audio latency" "Type a number from 0.0 to 50.0."
        ;;
      test)
        ui_info "Test sound" "Playing a test sound..."
        audio_test
        ;;
      sounds)
        case $(menu_sounds_state) in
          missing)
            ui_msg "Menu sounds" \
              "Put move.wav (cursor) and select.wav (Enter) in $MENU_SOUNDS_DIR: on the network, the FliperOS share, folder sounds/menu." \
              "" "FliperOS doesn't come with game sounds: use your own, like a game's select screen."
            ;;
          on) menu_sounds_set off ;;
          off) menu_sounds_set on ;;
        esac
        ui_sounds
        ;;
      return) return 0 ;;
    esac
  done
}

# ── Rede ─────────────────────────────────────────────────────────

screen_network() {
  local choice last=wifi
  while true; do
    UI_STATUS=$(status_line)
    choice=$(ui_menu_hints "Network Setup" "$(net_summary | head -6)" "$last" \
      "wifi|Connect to a Wi-Fi network|Pick a network from the list and type its password." \
      "hidden|Connect to a hidden network|For a network that hides its name: type the SSID." \
      "status|Network status|The connections and the IP address of this computer." \
      "return|Return|Back to Setup.") || return 0
    last=$choice
    case $choice in
      wifi) screen_wifi 0 ;;
      hidden) screen_wifi 1 ;;
      status) ui_msg "Network status" "$(net_summary)" "" "IP: $(net_ips)" ;;
      return) return 0 ;;
    esac
  done
}

# screen_wifi OCULTA segue o worker_configure_wifi do gasetup: placa, rede,
# senha e a tentativa de conexao.
screen_wifi() {
  local hidden=$1 devs=() dev ssid pass nets=() entries=() line sig sec
  mapfile -t devs < <(net_wifi_devices)
  if ((${#devs[@]} == 0)); then
    local hw=()
    mapfile -t hw < <(net_hardware)
    ui_msg "Wi-Fi" "No Wi-Fi adapter was found. You may need additional drivers." "" \
      "Network hardware seen by Linux:" "${hw[@]}"
    return 0
  fi
  dev=${devs[0]}
  if ((${#devs[@]} > 1)); then
    for line in "${devs[@]}"; do entries+=("$line|$line"); done
    dev=$(ui_menu "Wi-Fi" "Select the Wi-Fi adapter." "" "${entries[@]}") || return 0
  fi
  if ((hidden)); then
    ssid=$(ui_input "Hidden network" "Type the network name (SSID)") || return 0
    [[ -n $ssid ]] || return 0
  else
    ui_info "Wi-Fi" "Scanning for networks on $dev..."
    mapfile -t nets < <(net_scan "$dev")
    if ((${#nets[@]} == 0)); then
      ui_msg "Wi-Fi" "No network was found. For a hidden network, use the hidden network option."
      return 0
    fi
    entries=()
    for line in "${nets[@]}"; do
      IFS='|' read -r ssid sig sec <<< "$line"
      entries+=("$ssid|$(printf '%-32s %3s%%  %s' "$ssid" "$sig" "${sec:-open}")")
    done
    ssid=$(ui_menu "Wi-Fi" "Select the network." "" "${entries[@]}") || return 0
    sec=$(printf '%s\n' "${nets[@]}" | awk -F'|' -v s="$ssid" '$1 == s { print $3; exit }')
  fi
  pass=""
  if ((hidden)) || [[ -n $sec && $sec != "--" ]]; then
    pass=$(ui_input "Wi-Fi" "Password for $ssid (leave empty for an open network)" "" password) || return 0
  fi
  ui_info "Wi-Fi" "Connecting to $ssid..."
  if net_connect "$dev" "$ssid" "$pass" "$hidden"; then
    sleep 2
    UI_STATUS=$(status_line)
    speak "Connected to the network."
    ui_msg "Wi-Fi" "Connected to $ssid." "" "IP: $(net_ips)"
    # A rede acabou de chegar: o update do FliperOS, que o boot so procura
    # com ela no ar, e oferecido ja (sem nenhum pendente, nenhuma tela). Na
    # midia de instalacao nao: o update e para o disco instalado.
    if ! is_live; then
      ui_info "FliperOS update" "Checking for FliperOS updates..."
      screen_update_check
    fi
  else
    ui_msg "Wi-Fi" "Could not connect to $ssid." "" "Check the password and the signal (details in the log)."
  fi
}

# ── Frontend ─────────────────────────────────────────────────────

screen_frontend() {
  local entries=() name desc current choice pkg label lines=() theme=()
  current=$(launcher_current)
  while IFS='|' read -r name desc; do
    if launcher_installed "$name"; then
      entries+=("$name|$desc")
    elif launcher_package_available "$name" || [[ -n $(launcher_fetcher "$name") ]]; then
      entries+=("$name|$desc (not installed)")
    else
      entries+=("$name|$desc (not available yet)")
    fi
  done < <(launcher_all)
  entries+=("+add|Add a custom frontend")
  [[ -n $(launcher_custom_list) ]] && entries+=("+edit|Edit or delete a custom frontend")
  choice=$(ui_menu "Frontend" "Choose what starts when the computer turns on. Now: $(launcher_label "$current")." \
    "$current" "${entries[@]}") || return 0
  case $choice in
    +add)
      screen_frontend_custom
      return 0
      ;;
    +edit)
      screen_frontend_custom_pick
      return 0
      ;;
  esac
  label=$(launcher_label "$choice")
  if launcher_custom "$choice" && ! launcher_installed "$choice"; then
    ui_msg "Frontend" "$label: the program $(launcher_custom_program "$(launcher_field "$choice" 3)") was not found." "" \
      "Fix its command in Edit or delete a custom frontend."
    return 0
  elif ! launcher_installed "$choice" && [[ -n $(launcher_fetcher "$choice") ]]; then
    # De codigo fechado: nao vem na imagem nem no repositorio, o Setup baixa
    # do site do proprio programa.
    ui_yesno "Frontend" "$label is not installed, and it does not come with FliperOS. Download it now from its own website?" yes ||
      return 0
    run_with_progress "Downloading $label" "" launcher_fetch "$choice" || return 0
    if ! launcher_installed "$choice"; then
      ui_msg "Frontend" "$label was downloaded, but it was not found afterwards (details in the log)."
      return 0
    fi
  elif ! launcher_installed "$choice"; then
    pkg=$(launcher_package "$choice")
    if [[ -z $pkg ]] || ! launcher_package_available "$choice"; then
      ui_msg "Frontend" "$label is not in the FliperOS repository yet." "" \
        "Choose another frontend; this one will come in a later version."
      return 0
    fi
    ui_yesno "Frontend" "$label is not installed. Install the $pkg package now?" yes || return 0
    run_with_progress "Installing $pkg" "" update_install_package "$pkg" || return 0
    if ! launcher_installed "$choice"; then
      ui_msg "Frontend" "$pkg was installed, but $label was not found."
      return 0
    fi
  fi
  launcher_set "$choice"
  # O tema padrao do Attract-Mode Plus nao vem com o FliperOS: baixado do
  # GitHub dele, se faltar. Sem ele (sem rede) as telas ficam no Basic.
  if [[ $choice == attractplus && $(scraper_attract_layout) != Arcadeflow ]]; then
    run_with_progress "Downloading the Arcadeflow theme" "" frontends_attract_theme ||
      theme=("" "The Arcadeflow theme was not downloaded: the displays use the Basic layout."
        "Choose Attract-Mode Plus here again to try once more.")
  fi
  # As pastas de ~/roms e o comando de cada uma no frontend (lib/frontends.sh).
  ui_info "Frontend" "Putting the game folders in $label..."
  frontends_configure "$choice"
  lines=("$label will start when the computer turns on.")
  mapfile -t -O 1 lines < <(frontends_hint "$choice")
  ui_msg "Frontend" "${lines[@]}" "${theme[@]}"
}

# screen_frontend_custom [NOME]: cadastra um frontend da pessoa (rotulo e
# comando), ou edita o NOME.
screen_frontend_custom() {
  local name=${1:-} label="" cmd="" title="Custom frontend"
  if [[ -n $name ]]; then
    label=$(launcher_label "$name")
    cmd=$(launcher_field "$name" 3)
  fi
  while true; do
    label=$(ui_input "$title" "Name shown in the menu." "$label") || return 0
    launcher_custom_valid "$label" && break
    ui_msg "$title" "The name cannot be empty or have a | character."
  done
  while true; do
    cmd=$(ui_input "$title" "Command that opens $label, on the console like the other frontends." \
      "$cmd" long) || return 0
    launcher_custom_valid "$cmd" && break
    ui_msg "$title" "The command cannot be empty or have a | character." "" \
      "For a pipe, put the command in a script and use the script."
  done
  if ! name=$(launcher_custom_save "$name" "$label" "$cmd"); then
    ui_msg "$title" "Could not save $label (details in the log)."
    return 0
  fi
  if ! launcher_installed "$name"; then
    ui_msg "$title" "$label was saved, but the program $(launcher_custom_program "$cmd") was not found." "" \
      "It can be fixed later in Edit or delete a custom frontend."
    return 0
  fi
  [[ $(launcher_current) == "$name" ]] && return 0
  ui_yesno "$title" "$label was saved. Start it when the computer turns on?" yes || return 0
  launcher_set "$name"
}

# screen_frontend_custom_pick: escolhe um frontend da pessoa para editar ou
# apagar.
screen_frontend_custom_pick() {
  local entries=() name label choice title="Custom frontend"
  mapfile -t entries < <(launcher_custom_list)
  ((${#entries[@]})) || return 0
  name=$(ui_menu "$title" "Choose the custom frontend to edit or delete." "" "${entries[@]}") || return 0
  label=$(launcher_label "$name")
  choice=$(ui_menu "$title" "$label"$'\n'"$(ui_dim "$(launcher_field "$name" 3)")" "edit" \
    "edit|Edit the name and the command" "delete|Delete") || return 0
  case $choice in
    edit) screen_frontend_custom "$name" ;;
    delete)
      ui_yesno "$title" "Delete $label?" no || return 0
      launcher_custom_delete "$name"
      ;;
  esac
}

# ── Extras ───────────────────────────────────────────────────────
# Wine, Steam e Heroic: nao vem na imagem, o Setup instala pela rede
# (lib/extras.sh).

# screen_extras_pixelcade: o Pixelcade ja instalado: atualizar, ou instalar o
# pacote de arte pago com o codigo da compra. Status 0 = atualizar.
screen_extras_pixelcade() {
  local choice code
  while true; do
    choice=$(ui_menu "Pixelcade" "Pixelcade is installed." update \
      "update|Download it again to update it" \
      "artpack|Install the paid art pack (license code)" \
      "return|Return") || return 1
    case $choice in
      update) return 0 ;;
      artpack)
        code=$(ui_input "Pixelcade art pack" "The license code you got when you bought the art pack from Pixelcade. It needs the network.") || continue
        code=${code//[[:space:]]/}
        [[ -n $code ]] || continue
        if run_with_progress "Installing the Pixelcade art pack" "" extras_artpack "$code"; then
          ui_msg "Pixelcade art pack" "The art pack is installed."
        fi
        ;;
      *) return 1 ;;
    esac
  done
}

screen_extras() {
  local entries=() name inst desc choice label last=wine
  while true; do
    entries=()
    while IFS='|' read -r name inst desc; do
      if ((inst)); then entries+=("$name|$desc (installed)"); else entries+=("$name|$desc"); fi
    done < <(extras_list)
    entries+=("return|Return")
    choice=$(ui_menu "Extras" "Programs that don't come with FliperOS, to keep the download small. Installing one needs the network." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    [[ $choice == return ]] && return 0
    label=$(extras_label "$choice")
    # Instalado: instalar de novo atualiza (o Pixelcade baixa o pixelweb e a
    # arte novos, o apt a versao nova do pacote).
    if [[ $choice == pixelcade ]] && extras_installed "$choice"; then
      screen_extras_pixelcade || continue
    elif extras_installed "$choice"; then
      ui_yesno "Extras" "$label is already installed. Download it again to update it?" no || continue
    else
      ui_yesno "Extras" "Download and install $label now?" yes || continue
    fi
    if run_with_progress "Installing $label" "" extras_install "$choice"; then
      ui_msg "Extras" "$label installed."
    fi
  done
}

# ── Emulators & Games ────────────────────────────────────────────
# Os emuladores do menu do desktop, com o que falta instalar, e a instalacao
# um por um dos que nao vem na imagem (lib/emulators.sh).

screen_emulators() {
  local title="Emulators & Games" entries=() name inst kind desc choice last="" label
  while true; do
    entries=()
    while IFS='|' read -r name inst kind desc; do
      if ((inst)); then
        entries+=("$name|$desc (installed)")
      else
        entries+=("$name|$desc (not installed)")
        [[ -n $last ]] || last=$name
      fi
    done < <(emulators_list)
    entries+=("return|Return")
    choice=$(ui_menu "$title" \
      "What is installed and what is not. Choose one that is not installed to install it; Model 2, Fightcade 2 and KOF Final Attack don't come in the image and need the network." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    [[ $choice == return ]] && return 0
    label=$(emulators_field "$choice" 4)
    kind=$(emulators_field "$choice" 3)
    inst=$(emulators_field "$choice" 2)
    case $kind in
      image)
        if ((inst)); then
          ui_msg "$title" "$label comes with FliperOS and is installed."
        else
          ui_msg "$title" "$label comes compiled in the FliperOS image, and this image was built without it." "" \
            "It can't be installed from here: use an image that has it."
        fi
        ;;
      source) screen_emulators_kof "$choice" "$label" "$inst" ;;
      *)
        if ((inst)); then
          ui_yesno "$title" "$label is already installed. Download it again to update it?" no || continue
        elif [[ $kind == build ]]; then
          ui_yesno "$title" "Download and build $label now? It needs the network and takes several minutes." yes ||
            continue
        else
          ui_yesno "$title" "Download and install $label now?" yes || continue
        fi
        if run_with_progress "Installing $label" "" emulators_install "$choice"; then
          ui_msg "$title" "$label installed." "" "It is in the desktop menu, in Games."
        fi
        ;;
    esac
  done
}

# screen_emulators_kof NOME ROTULO INSTALADO: o KOF Final Attack nao e
# baixado: a pessoa aponta a pasta do jogo original, e a instalacao baixa o
# patch 4:3 e o Ikemen GO e monta a copia convertida (config/fliperos-kof).
screen_emulators_kof() {
  local name=$1 label=$2 inst=$3 title="KOF Final Attack" dir game
  if ((inst)); then
    ui_yesno "$title" "$label is already installed. Install it again from the original game? The installed copy is replaced." no ||
      return 0
  fi
  ui_msg "$title" "The King of Fighters: Final Attack on Ikemen GO, in 4:3 at 320x240 for the CRT." "" \
    "The game itself is not downloaded: bring the folder of the original game (the one with Final Attack.exe) on a USB disk, over the network share or in the home folder." \
    "" "The installer downloads the 4:3 patch and Ikemen GO and makes a converted copy in ~/roms/ikemen (about 2 GB; needs the network). The original folder is not changed."
  dir=$(ui_browse "$title" "Open the folder of the original game, then Use this folder." \
    "$(folders_browse_start)" dir) || return 0
  if ! game=$(emulators_kof_find "$dir"); then
    ui_msg "$title" "No Final Attack.exe in $dir." "" "Choose the folder of the original game (MUGEN)."
    return 0
  fi
  if run_with_progress "Installing $title" "$game" emulators_install "$name" "$game"; then
    ui_msg "$title" "$title installed." "" "It is in the desktop menu, in Games; on a terminal, fliperos-kof."
  fi
}

# ── Scraper ──────────────────────────────────────────────────────

# screen_scraper (Setup > Games > Scraper): raspar com o site escolhido, a
# escolha do site (com a conta dos que pedem login) e os pacotes de arte por
# torrent (screens/mediapacks.sh).
screen_scraper() {
  local choice last=scrape source name account
  while true; do
    source=$(scraper_source_saved)
    name=$(scraper_source_field "$source" 2)
    account=$(scraper_account_label "$source")
    choice=$(ui_menu_hints "Scraper" "" "$last" \
      "scrape|Scrape the games ($name)|Covers, screenshots, logos, videos and descriptions of your ROMs." \
      "source|Scraper provider: $name, $account|Pick the scraper provider and log in to the ones that ask." \
      "torrent|Art packs by torrent|Logos and videos from torrents, only for the ROMs you have." \
      "return|Return|Back to Games.") || return 0
    last=$choice
    case $choice in
      scrape) screen_scraper_scrape ;;
      source) screen_scraper_source ;;
      torrent) screen_mediapacks ;;
      return) return 0 ;;
    esac
  done
}

# screen_scraper_source: o site de onde o Scraper busca e, nos que pedem, a
# conta: usuario e senha (ScreenScraper), a chave de API (MobyGames) ou o
# client ID e o secret (IGDB). Fica guardado para as proximas vezes
# (lib/scraper.sh).
screen_scraper_source() {
  local title="Scraper provider" line key name kind note source creds user pass old
  local -a entries=()
  while IFS='|' read -r key name kind note; do
    entries+=("$key|$name: $note")
  done < <(scraper_sources)
  source=$(ui_radio "$title" "Where the art and the game information come from. A provider that asks for an account keeps it for the next times." \
    "$(scraper_source_saved)" "${entries[@]}") || return 0
  conf_set scraper_source "$source"
  name=$(scraper_source_field "$source" 2)
  kind=$(scraper_source_field "$source" 3)
  old=$(scraper_account "$source") || old=""
  case $kind in
    login)
      user=${old%%:*}
      [[ -n $user ]] || user=$(conf_get screenscraper_user 2> /dev/null)
      user=$(ui_input "$name" "$name user (leave empty to scrape without an account)." "$user") || return 0
      user=${user//[[:space:]]/}
      if [[ -z $user ]]; then
        scraper_account_set "$source"
        ui_msg "$title" "$name will be used without an account." "" \
          "It works, with lower limits: a free account at the site scrapes more games per day."
        return 0
      fi
      pass=$(ui_input "$name" "$name password${old:+ (leave empty to keep the saved one)}." "" password) || return 0
      [[ -z $pass && $user == "${old%%:*}" ]] && pass=${old#*:}
      if [[ -z $pass ]]; then
        ui_msg "$title" "$(ui_bad "No password: the account was not saved.")"
        return 0
      fi
      creds="$user:$pass"
      ;;
    key)
      creds=$(ui_input "$name" "$name API key (from your profile at the site)${old:+; leave empty to keep the saved one}." "" long) || return 0
      creds=${creds//[[:space:]]/}
      [[ -n $creds ]] || creds=$old
      ;;
    idsecret)
      user=$(ui_input "$name" "$name client ID (a Twitch developer application)${old:+; leave empty to keep the saved one}." "") || return 0
      user=${user//[[:space:]]/}
      if [[ -n $user ]]; then
        pass=$(ui_input "$name" "$name client secret." "" password) || return 0
        pass=${pass//[[:space:]]/}
        [[ -n $pass ]] && creds="$user:$pass"
      else
        creds=$old
      fi
      ;;
    *)
      ui_msg "$title" "$name is the scraper provider now. It needs no account."
      return 0
      ;;
  esac
  if [[ -z $creds ]]; then
    ui_msg "$title" "$(ui_bad "$name only works with its key, and none was saved.")" \
      "Open Scraper provider again to type it, or pick another provider."
    return 0
  fi
  scraper_account_set "$source" "$creds"
  ui_msg "$title" "$name is the scraper provider now, with your account." "" \
    "The login is saved on this computer for the next times."
}

# screen_scraper_scrape: as pastas com jogos, o que buscar e a raspagem, com
# o site escolhido em Scraper provider.
screen_scraper_scrape() {
  local found=() entries=() line key dir platform count choice targets=() source creds="" media t
  local clones=0 pending=() rc name
  local -a options
  source=$(scraper_source_saved)
  name=$(scraper_source_field "$source" 2)
  if [[ $source != progettosnaps ]] && ! have "$SKYSCRAPER"; then
    ui_msg "Scraper" "Skyscraper is not installed."
    return 0
  fi
  # Um trabalho interrompido (desligou, fechou o Setup): retoma de onde
  # parou, com as mesmas escolhas. ESC volta sem perder o trabalho.
  mapfile -t pending < <(scraper_job_pending)
  if ((${#pending[@]})); then
    entries=()
    for line in "${pending[@]}"; do entries+=("${line%%|*}"); done
    rc=0
    ui_choice2 "Scraper" "Resume" "Start over" \
      "A scrape was interrupted. Systems left: ${entries[*]}" "" \
      "Resume where it stopped? The games already fetched are kept." || rc=$?
    if ((rc == 0)); then
      IFS='|' read -r source media clones creds <<< "$(scraper_job_options)"
      scraper_scrape_targets "$source" "$media" "$creds" "$clones" "${pending[@]}"
      return 0
    fi
    ((rc == 1)) || return 0
    scraper_job_clear
  fi
  if scraper_account_missing "$source"; then
    ui_msg "Scraper" "$(ui_bad "$name only works with an account, and none is saved.")" \
      "Type it in Scraper provider, or pick another provider there."
    return 0
  fi
  mapfile -t found < <(scraper_detect)
  if ((${#found[@]} == 0)); then
    ui_msg "Scraper" "No ROMs were found in $ROMS_DIR." "" \
      "Copy your ROMs to the folder of the emulator (e.g. $ROMS_DIR/mame," \
      "or $ROMS_DIR/retroarch/<core> for RetroArch) and try again."
    return 0
  fi
  entries=("all|All systems (${#found[@]})")
  # O valor de cada opcao do ui_menu vai ate o primeiro "|": so a chave; a
  # linha inteira volta pelo found.
  for line in "${found[@]}"; do
    IFS='|' read -r key dir platform count <<< "$line"
    entries+=("$key|$key - $count files ($platform)")
  done
  choice=$(ui_menu "Scraper" "Covers, screenshots, logos, videos and game information for the ROMs found, from $name." \
    all "${entries[@]}") || return 0
  if [[ $choice == all ]]; then
    targets=("${found[@]}")
  else
    for line in "${found[@]}"; do
      [[ ${line%%|*} == "$choice" ]] && targets=("$line")
    done
  fi
  if [[ $source == progettosnaps ]]; then
    screen_scraper_snaps "${targets[@]}"
    return 0
  fi
  creds=$(scraper_account "$source") || creds=""
  # Os tipos de midia a buscar, de marcar; a escolha fica para a proxima vez.
  mapfile -t options < <(scraper_media_options)
  media=$(ui_checklist "Scraper: Media" "Mark what to fetch. Each type goes to its folder in ~/media." \
    "$(scraper_media_saved)" "${options[@]}") || return 0
  [[ -n $media ]] || media=none
  conf_set scraper_media "$media"
  for t in "${targets[@]}"; do
    if [[ ${t%%|*} == mame ]]; then
      ui_yesno "Scraper" "Also fetch the clones of the MAME games found (other versions of the same game)? It takes longer." &&
        clones=1
      break
    fi
  done
  scraper_scrape_targets "$source" "$media" "$creds" "$clones" "${targets[@]}"
}

# screen_scraper_snaps ALVO...: o progetto-SNAPS so tem capturas de jogos de
# arcade (lib/scraper.sh). As outras pastas ficam de fora, e a escolha de
# midia guardada nao muda.
screen_scraper_snaps() {
  local t arcade=() other=() clones=0
  for t in "$@"; do
    if scraper_arcade "${t%%|*}"; then arcade+=("$t"); else other+=("${t%%|*}"); fi
  done
  if ((${#arcade[@]} == 0)); then
    ui_msg "Scraper" "progetto-SNAPS only has arcade games (MAME sets)." "" \
      "Pick an arcade folder (mame, naomi, atomiswave, model2...) or another source."
    return 0
  fi
  ((${#other[@]})) && ui_msg "Scraper" "Left out (not arcade): ${other[*]}"
  ui_yesno "Scraper" "progetto-SNAPS has the in-game screenshots of the MAME sets, in a pack of about 520 MB (plus a monthly update) that stays in $SNAPS_CACHE for the next time (about 1 GB unpacked). Logos, covers and descriptions come from the other sources. Download?" yes ||
    return 0
  for t in "${arcade[@]}"; do
    if [[ ${t%%|*} == mame ]]; then
      ui_yesno "Scraper" "Also fetch the clones of the MAME games found (other versions of the same game)?" && clones=1
      break
    fi
  done
  scraper_scrape_targets progettosnaps snap "" "$clones" "${arcade[@]}"
}

# scraper_scrape_targets FONTE MIDIA CREDENCIAIS CLONES ALVO... anota o
# trabalho e raspa pasta por pasta. Uma que falha nao para as outras e fica
# pendente para o "Resume".
scraper_scrape_targets() {
  local source=$1 media=$2 creds=$3 clones=$4 t key dir platform count failed=() labels=() label
  shift 4
  scraper_job_start "$source" "$media" "$clones" "$creds" "$@"
  for t in "$@"; do
    IFS='|' read -r key dir platform count <<< "$t"
    if run_with_progress "Scraping $platform" "$key ($count files)" \
      scraper_run "$key" "$dir" "$platform" "$source" "$media" "$creds" "$clones"; then
      scraper_job_done "$key"
      label=$(scraper_format_label "$(scraper_target "$key")")
      [[ " ${labels[*]} " == *" $label "* ]] || labels+=("$label")
    else
      failed+=("$key")
    fi
  done
  if ((${#failed[@]})); then
    ui_msg "Scraper" "Not finished: ${failed[*]}" "" \
      "Open Setup > Games > Scraper again to resume (the games already fetched are kept)." \
      "Details in $FLIPEROS_LOG."
  else
    label=$(printf '%s, ' "${labels[@]}")
    ui_msg "Scraper" "Done. Game lists updated for: ${label%, }."
  fi
}

# ── AttractPlus ROM List ─────────────────────────────────────────
# As romlists do Attract-Mode Plus das pastas de arcade, com o nome de cada
# jogo do -listxml do GroovyMAME (lib/frontends.sh).

screen_romlist() {
  local title="AttractPlus ROM List" found=() entries=() targets=() line key dir platform count name
  local picked="" result games clones unknown lines=()
  if ! launcher_installed attractplus; then
    ui_msg "$title" "Attract-Mode Plus is not installed." "" "Install it in Setup > Games > Frontend."
    return 0
  fi
  mapfile -t found < <(frontends_romlist_systems)
  if ((${#found[@]} == 0)); then
    # As pastas que nao sao de arcade ganham a tela e a lista que faltarem.
    frontends_attract
    ui_msg "$title" "No arcade games were found." "" \
      "Copy the sets to $ROMS_DIR/mame, naomi, naomi2, atomiswave, model2, model3" \
      "or to the folder of a RetroArch arcade core (mame2010, fbneo...)."
    return 0
  fi
  for line in "${found[@]}"; do
    IFS='|' read -r key dir platform count name <<< "$line"
    entries+=("$key|$name - $count files")
    picked+="${picked:+,}$key"
  done
  picked=$(ui_checklist "$title" "Game lists with the real name of each game, from the GroovyMAME list, clones and bootlegs included. Mark the folders." \
    "$picked" "${entries[@]}") || return 0
  [[ -n $picked ]] || return 0
  for line in "${found[@]}"; do
    [[ ",$picked," == *",${line%%|*},"* ]] && targets+=("$line")
  done
  ui_yesno "$title" "This replaces the game lists of these folders in Attract-Mode Plus, also a list made by the Scraper (the art stays). The \"$ATTRACT_ROMLIST_ALL\" list gets all of them together. Go on?" yes ||
    return 0
  result=$(mktemp)
  if run_with_progress "Generating the ROM lists" "" frontends_romlist "$result" "${targets[@]}"; then
    while IFS=$'\t' read -r name games clones unknown; do
      [[ $name == total ]] && continue
      line="$name: $games games"
      ((clones > 0)) && line+=" ($clones clones inside the parent's zip)"
      ((unknown > 0)) && line+=", $unknown not in the MAME list"
      lines+=("$line")
    done < "$result"
    ui_msg "$title" "${lines[@]}" "" \
      "\"$ATTRACT_ROMLIST_ALL\": $(awk -F'\t' '$1 == "total" { print $2 }' "$result") games." \
      "A game not in the MAME list keeps its file name."
  fi
  rm -f "$result"
}

# ── Modo debug ───────────────────────────────────────────────────
# lib/debug.sh: todo texto na tela (boot, frontends, emuladores) ou nenhum.

screen_debug() {
  if debug_enabled; then
    ui_yesno "Debug mode" "Debug mode is on. Turn it off? The boot goes straight to the splash again and the output of frontends and emulators is only saved in /opt/fliperos/logs." yes ||
      return 0
    debug_set off
  else
    ui_yesno "Debug mode" "Show all text? The boot menu and the kernel and system messages at boot, and the output of frontends and emulators (now hidden and saved in /opt/fliperos/logs)." no ||
      return 0
    debug_set on
  fi
  if is_installed && ! is_live; then
    ui_info "Debug mode" "Saving the boot settings..."
    if ! boot_apply; then
      ui_msg "Debug mode" "Could not update the boot settings (see /var/log/fliperos-setup.log)."
      return 1
    fi
  fi
  ui_msg "Debug mode" "Debug mode is $(debug_enabled && echo on || echo off)." "" \
    "Frontends and emulators follow it now; the boot, after a restart."
}

# ── Quirks ───────────────────────────────────────────────────────
# Quirks do usbhid com nome (lib/quirks.sh): a lista, adicionar e apagar.

screen_quirks() {
  local entries code name choice last=add
  while true; do
    entries=()
    while IFS='|' read -r code name; do
      [[ -n $code ]] && entries+=("$code|$name ($code)")
    done < <(quirks_list)
    entries+=("add|Add a quirk" "usb|USB devices connected now" "return|Return")
    choice=$(ui_menu "Quirks" "Kernel fixes for USB controllers (usbhid.quirks). Choose a quirk to delete it. Changes apply after a restart." \
      "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      add) screen_quirk_add ;;
      usb)
        {
          echo "Vendor:product in the quirk format, then the device name."
          echo
          quirks_usb_devices
        } > /tmp/fliperos-usb.txt
        ui_pager "USB devices" /tmp/fliperos-usb.txt
        ;;
      return) return 0 ;;
      *) screen_quirk_delete "$choice" ;;
    esac
  done
}

screen_quirk_add() {
  local name code rc
  if (($(quirks_count) >= QUIRKS_MAX)); then
    ui_msg "Add a quirk" "The kernel reads at most $QUIRKS_MAX quirks." "" "Delete one before adding another."
    return 0
  fi
  name=$(ui_input "Add a quirk" "Name, to recognize it in the list (e.g. Xin-Mo dual encoder)") || return 0
  code=$(ui_input "Add a quirk" "Code: 0xVENDOR:0xPRODUCT:0xFLAGS (e.g. 0x16c0:0x05e1:0x40). IDs are in Quirks > USB devices. Flags: 0x40 one device per player (dual encoders), 0x8 no GET requests, 0x400 always poll.") || return 0
  quirk_add "$name" "$code"
  rc=$?
  case $rc in
    0) screen_quirks_save "Quirk saved." ;;
    1) ui_msg "Add a quirk" "Invalid code: $code" "" \
      "Use three hexadecimal numbers starting with 0x, separated by colons:" \
      "0xVENDOR:0xPRODUCT:0xFLAGS (e.g. 0x16c0:0x05e1:0x40)." ;;
    2) ui_msg "Add a quirk" "The kernel reads at most $QUIRKS_MAX quirks." ;;
    3) ui_msg "Add a quirk" "This device (${code%:*}) already has a quirk." "" \
      "Delete it first to change its code." ;;
  esac
}

screen_quirk_delete() {
  local code=$1 name
  name=$(quirks_list | awk -F'|' -v c="$code" '$1 == c { print $2; exit }')
  ui_yesno "Delete quirk" "Delete \"$name\" ($code)?" no || return 0
  if ! quirk_delete "$code"; then
    ui_msg "Delete quirk" "Could not delete it (see /var/log/fliperos-setup.log)."
    return 0
  fi
  screen_quirks_save "Quirk deleted."
}

# screen_quirks_save MENSAGEM leva os quirks para a linha do kernel do
# sistema instalado. Na midia de instalacao eles vao junto na instalacao.
screen_quirks_save() {
  if is_installed && ! is_live; then
    ui_info "Quirks" "Saving the boot settings..."
    if ! boot_apply; then
      ui_msg "Quirks" "Could not update the boot settings (see /var/log/fliperos-setup.log)."
      return 1
    fi
  fi
  ui_msg "Quirks" "$1" "" "Restart the computer to apply it."
}

# ── Atualizacao ──────────────────────────────────────────────────

screen_update() {
  ui_yesno "System Update" "Download and install the updates of all packages now?" yes || return 0
  if run_with_progress "System Update" "" update_run; then
    ui_msg "System Update" "The system is up to date."
  fi
}
