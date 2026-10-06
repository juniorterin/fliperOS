# shellcheck shell=bash
# Setup do sistema instalado (worker_setup_menu do gasetup): video, audio,
# rede, frontend, latencia, scraper, ROM cleaner, quirks e atualizacao.

screen_setup_menu() {
  local choice last=video
  while true; do
    screen_reload_if_updated
    UI_STATUS=$(status_line)
    choice=$(ui_menu "Setup" "" "$last" \
      "video|Video Setup" \
      "audio|Audio Setup" \
      "network|Network Setup" \
      "frontend|Frontend" \
      "extras|Extras (Wine, Steam, Heroic)" \
      "latency|Latency (low latency mode)" \
      "scraper|Scraper (covers, videos, logos)" \
      "romcleaner|MAME ROM Cleaner" \
      "chdcleaner|MAME CHD Cleaner" \
      "freeroms|Free games (open-source homebrew)" \
      "quirks|Quirks (USB controller fixes)" \
      "joysticks|Joysticks (GunCon 2, wheel, LPT)" \
      "debug|Debug mode ($(debug_enabled && echo on || echo off))" \
      "update|System Update" \
      "return|Return") || return 0
    last=$choice
    case $choice in
      video) screen_video_setup ;;
      audio) screen_audio ;;
      network) screen_network ;;
      frontend) screen_frontend ;;
      extras) screen_extras ;;
      latency) screen_latency ;;
      scraper) screen_scraper ;;
      romcleaner) screen_rom_cleaner ;;
      chdcleaner) screen_chd_cleaner ;;
      freeroms) screen_free_roms ;;
      quirks) screen_quirks ;;
      joysticks) screen_joysticks ;;
      debug) screen_debug ;;
      update) screen_update ;;
      return) return 0 ;;
    esac
  done
}

# ── Jogos livres ─────────────────────────────────────────────────

# screen_free_roms baixa os jogos livres do config/fliperos-freeroms para as
# pastas dos cores do RetroArch (lib/freeroms.sh).
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
      "" "Setup > Scraper gets their art and descriptions."
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
    choice=$(ui_menu "Audio Setup" \
      "$(ui_fields "Default card|$card_label" "Volume|$(audio_volume)% (keyboard volume keys work too)" \
        "MAME latency|$(audio_mame_latency)")" "$last" \
      "card|Default card" \
      "volume|Volume" \
      "mixer|AlsaMixer" \
      "latency|MAME audio latency" \
      "test|Test sound" \
      "sounds|Menu sounds ($(menu_sounds_label))" \
      "return|Return") || return 0
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
    choice=$(ui_menu "Network Setup" "$(net_summary | head -6)" "$last" \
      "wifi|Connect to a Wi-Fi network" \
      "hidden|Connect to a hidden network (type the SSID)" \
      "status|Network status" \
      "return|Return") || return 0
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
  else
    ui_msg "Wi-Fi" "Could not connect to $ssid." "" "Check the password and the signal (details in the log)."
  fi
}

# ── Frontend ─────────────────────────────────────────────────────

screen_frontend() {
  local entries=() name desc current choice pkg label lines=()
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
  choice=$(ui_menu "Frontend" "Choose what starts when the computer turns on. Now: $(launcher_label "$current")." \
    "$current" "${entries[@]}") || return 0
  label=$(launcher_label "$choice")
  if ! launcher_installed "$choice" && [[ -n $(launcher_fetcher "$choice") ]]; then
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
  # As pastas de ~/roms e o comando de cada uma no frontend (lib/frontends.sh).
  ui_info "Frontend" "Putting the game folders in $label..."
  frontends_configure "$choice"
  lines=("$label will start when the computer turns on.")
  mapfile -t -O 1 lines < <(frontends_hint "$choice")
  ui_msg "Frontend" "${lines[@]}"
}

# ── Extras ───────────────────────────────────────────────────────
# Wine, Steam e Heroic: nao vem na imagem, o Setup instala pela rede
# (lib/extras.sh).

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
    if extras_installed "$choice"; then
      ui_msg "Extras" "$label is already installed."
      continue
    fi
    ui_yesno "Extras" "Download and install $label now?" yes || continue
    if run_with_progress "Installing $label" "" extras_install "$choice"; then
      ui_msg "Extras" "$label installed."
    fi
  done
}

# ── Scraper ──────────────────────────────────────────────────────

screen_scraper() {
  local found=() entries=() line key dir platform count choice targets=() source creds="" user pass media t
  local clones=0 pending=() rc
  local -a options
  if ! have "$SKYSCRAPER"; then
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
  mapfile -t found < <(scraper_detect)
  if ((${#found[@]} == 0)); then
    ui_msg "Scraper" "No ROMs were found in $ROMS_DIR." "" \
      "Copy your ROMs to the folder of the emulator (e.g. $ROMS_DIR/mame," \
      "or $ROMS_DIR/retroarch/<core> for RetroArch) and try again."
    return 0
  fi
  entries=("all|All systems (${#found[@]})")
  for line in "${found[@]}"; do
    IFS='|' read -r key dir platform count <<< "$line"
    entries+=("$line|$key - $count files ($platform)")
  done
  choice=$(ui_menu "Scraper" "Covers, screenshots, logos, videos and game information for the ROMs found." \
    all "${entries[@]}") || return 0
  if [[ $choice == all ]]; then targets=("${found[@]}"); else targets=("$choice"); fi
  source=$(ui_menu "Scraper" "Where should the data come from?" screenscraper \
    "screenscraper|ScreenScraper (free account recommended)" \
    "arcadedb|ArcadeDB (arcade games only, no account)" \
    "thegamesdb|TheGamesDB") || return 0
  if [[ $source == screenscraper ]]; then
    user=$(ui_input "ScreenScraper" "ScreenScraper user (leave empty to scrape without an account)" "$(conf_get screenscraper_user 2> /dev/null)") || return 0
    if [[ -n $user ]]; then
      pass=$(ui_input "ScreenScraper" "ScreenScraper password" "" password) || return 0
      creds="$user:$pass"
      conf_set screenscraper_user "$user"
    fi
  fi
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
      "Open Setup > Scraper again to resume (the games already fetched are kept)." \
      "Details in $FLIPEROS_LOG."
  else
    label=$(printf '%s, ' "${labels[@]}")
    ui_msg "Scraper" "Done. Game lists updated for: ${label%, }."
  fi
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
