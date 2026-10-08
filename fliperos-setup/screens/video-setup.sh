# shellcheck shell=bash
# Video Setup: tipo de monitor, orientacao, resolucao e geometria, como o
# worker_video_menu do gasetup. Na midia so grava no fliperos.conf (o
# instalador leva para o disco); no sistema instalado aplica no boot.

VIDEO_CHANGED=0

# screen_pick_monitor [PADRAO] [required] imprime o preset escolhido.
screen_pick_monitor() {
  local def=${1:-} required=${2:-} entries=() entry text
  for entry in "${MONITOR_PRESETS[@]}"; do
    entries+=("$entry")
  done
  text="Select the monitor connected to this output."
  [[ $required == required ]] && text+=" This is needed to set the correct video mode."
  ui_menu "Monitor Type" "$text" "$def" "${entries[@]}"
}

screen_monitor_type() {
  local monitor current
  current=$(conf_get monitor 2> /dev/null) || current=$(video_suggested_monitor)
  monitor=$(screen_pick_monitor "$current") || return 0
  [[ $monitor == "$current" ]] && return 0
  video_reconfigure_monitor "$monitor" || {
    ui_msg "Monitor Type" "Could not configure $(monitor_label "$monitor")."
    return 0
  }
  VIDEO_CHANGED=1
}

screen_orientation() {
  local o current
  current=$(conf_get orientation 2> /dev/null) || current=horizontal
  o=$(ui_menu "Monitor Orientation" "How is the monitor mounted in the cabinet?" "$current" \
    "horizontal|Horizontal" \
    "vertical-cw|Vertical clockwise (rotated right)" \
    "vertical-ccw|Vertical counter-clockwise (rotated left)") || return 0
  [[ $o == "$current" ]] && return 0
  orientation_apply "$o"
  VIDEO_CHANGED=1
}

screen_resolution() {
  local conn monitor choices=() choice current w h r text
  conn=$(conf_get connector 2> /dev/null) || {
    ui_msg "Resolution" "No video output was selected by the output test." "" \
      "The resolution comes from the entry chosen in the boot menu."
    return 0
  }
  monitor=$(conf_get monitor 2> /dev/null) || monitor=generic_15
  mapfile -t choices < <(video_resolution_choices)
  if ((${#choices[@]} == 0)); then
    ui_msg "Resolution" "The $(monitor_label "$monitor") monitor doesn't need a special boot resolution." "" \
      "The monitor's own EDID defines the video mode."
    return 0
  fi
  current=$(conf_get boot_resolution 2> /dev/null) || current=""
  text="Boot resolution for $conn ($(monitor_label "$monitor"))."
  drm_card_low_dotclock "$(conf_get card 2> /dev/null)" 2> /dev/null ||
    text+=" This video card can't generate low dotclocks: only super resolutions are listed."
  choice=$(ui_menu "Resolution" "$text" "$current" "${choices[@]}" \
    "custom|Custom resolution (generates an EDID)") || return 0
  if [[ $choice == custom ]]; then
    screen_custom_resolution
    return 0
  fi
  [[ $choice == "$current" ]] && return 0
  video_set_resolution "$choice"
  xorg_generate
  VIDEO_CHANGED=1
}

# screen_custom_resolution e o worker_custom_video_mode do gasetup: testa o
# modo no grid do Switchres antes de gerar o EDID, para ninguem ficar com
# tela preta no proximo boot.
screen_custom_resolution() {
  local w h r out tmp
  w=$(ui_input "Custom resolution" "Width in pixels (e.g. 648)" "$(conf_get custom_width 2> /dev/null)") || return 0
  h=$(ui_input "Custom resolution" "Height in lines (e.g. 480)" "$(conf_get custom_height 2> /dev/null)") || return 0
  r=$(ui_input "Custom resolution" "Refresh rate in Hz (e.g. 60)" "$(conf_get custom_refresh 2> /dev/null)") || return 0
  if [[ ! $w =~ ^[0-9]+$ || ! $h =~ ^[0-9]+$ || ! $r =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    ui_msg "Custom resolution" "Width, height and refresh rate must be numbers."
    return 0
  fi
  have switchres || { ui_msg "Custom resolution" "Switchres is not installed."; return 0; }
  ui_msg "Custom resolution" "The new mode will now be tested with a grid." "" \
    "Press ESC if you can't see the grid, ENTER or Q to leave it."
  ui_clear
  GRID_TEXT="Testing ${w}x${h} ${r} Hz" switchres "$w" "$h" "$r" -s -l grid >> "$FLIPEROS_LOG" 2>&1
  ui_flush_input
  ui_yesno "Custom resolution" "Did you see the grid correctly?" no || return 0
  tmp=$(mktemp -d /tmp/fliperos-edid.XXXXXX)
  if ! (cd "$tmp" && switchres "$w" "$h" "$r" --edid --monitor "$(conf_get monitor 2> /dev/null || echo generic_15)" >> "$FLIPEROS_LOG" 2>&1); then
    rm -rf "$tmp"
    ui_msg "Custom resolution" "Switchres could not generate the EDID (see the log)."
    return 0
  fi
  out=$(find "$tmp" -name '*.bin' | head -1)
  if [[ -z $out ]]; then
    rm -rf "$tmp"
    ui_msg "Custom resolution" "Switchres did not produce an EDID file."
    return 0
  fi
  install -D -m 644 "$out" "$EDID_DIR/custom_resolution.bin"
  rm -rf "$tmp"
  conf_set custom_width "$w"
  conf_set custom_height "$h"
  conf_set custom_refresh "$r"
  video_set_custom_edid custom_resolution.bin
  xorg_generate
  VIDEO_CHANGED=1
}

# screen_geometry roda o mesmo "geometry 648 480 60" do gasetup (o
# geometry.py do Switchres, que desenha o grid e devolve o crt_range).
screen_geometry() {
  local out range w h r
  have geometry || { ui_msg "Geometry" "The geometry tool (Switchres) is not installed."; return 0; }
  read -r w h r <<< "$(geometry_mode)"
  ui_msg "Geometry" "A test grid will be shown at ${w}x${h} (${r} Hz) to adjust the picture." "" \
    "Arrows: move the picture   Page Up/Down: width" \
    "ENTER: save   ESC: cancel   DEL: reset   CTRL + key: bigger steps" "" \
    "The picture only moves down while there are blank lines below it." \
    "If it stops, use the monitor's V-POS (vertical position) adjustment."
  ui_clear
  out=$(geometry "$w" "$h" "$r" 2>&1)
  printf '%s\n' "$out" >> "$FLIPEROS_LOG"
  ui_flush_input
  range=$(geometry_parse "$out")
  if [[ -z $range ]]; then
    ui_msg "Geometry" "The adjustment was cancelled; nothing was changed."
    return 0
  fi
  geometry_apply "$range"
  ui_msg "Geometry" "Geometry saved (monitor set to custom):" "" "$range"
}

# screen_geometry_reset volta a geometria ao padrao do monitor escolhido.
screen_geometry_reset() {
  local monitor
  if ! conf_get geometry > /dev/null 2>&1; then
    ui_msg "Reset Geometry" "No geometry was saved: the monitor's default is already in use."
    return 0
  fi
  monitor=$(monitor_label "$(conf_get monitor 2> /dev/null || echo generic_15)")
  ui_yesno "Reset Geometry" "Discard the saved geometry and go back to the default of the monitor ($monitor)?" no ||
    return 0
  geometry_reset
  ui_msg "Reset Geometry" "Geometry reset: games and RetroArch use the default of the monitor ($monitor)."
}

# screen_multi_monitor: os monitores 2 e 3 nas outras saidas analogicas da
# placa (lib/multimonitor.sh). Os jogos de 2 ou 3 telas do GroovyMAME e os
# de varias placas do Flycast abrem uma tela em cada; os outros programas
# ficam no monitor 1.
screen_multi_monitor() {
  local conn choice last=2 extras=() entries summary note="" games
  conn=$(conf_get connector 2> /dev/null) || {
    ui_msg "Multiple Monitors" "No video output was selected by the output test." "" \
      "The other monitors use the same video card as monitor 1: run the output test first."
    return 0
  }
  while true; do
    mapfile -t extras < <(mm_extras)
    games=On
    mm_games_on || games=Off
    summary=$(ui_fields "Monitor 1|$conn (main)" "Monitor 2|${extras[0]:-off}" "Monitor 3|${extras[1]:-off}" \
      "Game screens|$(mm_screens | paste -sd' ' | sed 's/ /, /g')" "Multi-screen games|$games")
    note="Games with 2 or 3 screens open one screen on each monitor (GroovyMAME, Flycast)."
    [[ $games == Off ]] && note="Multi-screen games are off: every game opens on monitor 1."
    mm_pending && note="$(ui_no "The new monitors turn on after a reboot.")"
    entries=("2|Monitor 2: ${extras[0]:-off}")
    if ((${#extras[@]} > 0)); then
      ((MM_MAX > 2)) && entries+=("3|Monitor 3: ${extras[1]:-off}")
      entries+=("games|Multi-Screen Games: $games")
      entries+=("order|Game Screen Order")
      mm_pending || entries+=("identify|Identify Monitors")
    fi
    entries+=("return|Return")
    choice=$(ui_menu "Multiple Monitors" "$summary"$'\n\n'"$note" "$last" "${entries[@]}") || choice=return
    last=$choice
    case $choice in
      2 | 3) screen_mm_output "$choice" ;;
      games) screen_mm_games ;;
      order) screen_mm_order ;;
      identify) screen_mm_identify ;;
      return) break ;;
    esac
  done
}

# screen_mm_output MONITOR escolhe a saida do monitor 2 ou 3.
screen_mm_output() {
  local slot=$1 extras=() current pick choices=() c gpu
  mapfile -t extras < <(mm_extras)
  current=${extras[slot - 2]:-off}
  for c in $(mm_candidates "$current"); do
    choices+=("$c|$(mm_label "$c")")
  done
  gpu=$(conf_get gpu 2> /dev/null) || gpu="the video card"
  if ((${#choices[@]} == 0)) && [[ $current == off ]]; then
    ui_msg "Monitor $slot" "No other video output is free." "" \
      "Each arcade monitor needs its own output: another one on $gpu, or on a second video card."
    return 0
  fi
  pick=$(ui_radio "Monitor $slot" \
    "Output of monitor $slot. Analog outputs (VGA, DVI-I) of $gpu are the tested way; most cards drive two." \
    "$current" "${choices[@]}" "off|Off") || return 0
  [[ $pick == "$current" ]] && return 0
  if [[ $pick != off ]] && mm_digital "$pick" && ! ui_yesno "Monitor $slot" \
    "$(mm_entry_name "$pick") is digital: a CRT needs an active converter to VGA there, and it gets the super resolution ($(mm_kernel_spec "$pick" | sed 's/e$//')). This is experimental and not tested yet. Use it?"; then
    return 0
  fi
  if [[ $pick != off ]] && mm_other_card "$pick" && ! ui_yesno "Monitor $slot" \
    "$pick is on another video card ($(drm_card_name "${pick%%:*}")). X shows it as an output of $gpu, which draws the picture. This is experimental and not tested yet. Use it?"; then
    return 0
  fi
  if [[ $pick != off ]] && ! ui_yesno "Monitor $slot" \
    "Is an arcade monitor of the same type as monitor 1 ($(monitor_label "$(conf_get monitor 2> /dev/null || echo generic_15)")) connected to $pick? It gets the video mode of monitor 1."; then
    return 0
  fi
  mm_set_extra "$slot" "$pick"
  screen_mm_changed
}

# screen_mm_games liga ou desliga os jogos de varias telas nos extras.
screen_mm_games() {
  local current=on pick
  mm_games_on || current=off
  pick=$(ui_radio "Multi-Screen Games" \
    "Games with 2 or 3 screens: one screen on each monitor, or the whole game on monitor 1." "$current" \
    "on|On: one screen on each monitor" "off|Off: everything on monitor 1") || return 0
  [[ $pick == "$current" ]] && return 0
  mm_set_games "$pick"
  [[ $pick == on ]] && screen_mm_changed
  return 0
}

# screen_mm_order escolhe que monitor mostra cada tela dos jogos.
screen_mm_order() {
  local current pick orders=()
  mapfile -t orders < <(mm_orders)
  ((${#orders[@]} > 0)) || return 0
  current=$(mm_screens | paste -sd,)
  pick=$(ui_radio "Game Screen Order" \
    "Outputs from the first screen of a game to the last: left to right, or top to bottom (Punch-Out!!)." \
    "$current" "${orders[@]}") || return 0
  [[ $pick == "$current" ]] && return 0
  IFS=, read -r -a orders <<< "$pick"
  mm_save "${orders[@]}"
  VIDEO_CHANGED=1
}

# screen_mm_identify apaga um monitor de cada vez, na ordem das telas.
screen_mm_identify() {
  local screens=() i
  mapfile -t screens < <(mm_screens)
  for i in "${!screens[@]}"; do
    ui_info "Identify Monitors" "Game screen $((i + 1)): ${screens[i]}" "" "This monitor turns off for 3 seconds."
    speak "Screen $((i + 1)). Output $(speech_connector "${screens[i]}")."
    mm_blink "${screens[i]}"
    sleep 1
  done
  ui_flush_input
}

# screen_mm_changed: novo monitor ou monitor a menos. Os .ini do GroovyMAME
# sao refeitos para o numero de monitores; a linha do kernel e o Xorg saem
# ao fechar o Video Setup.
screen_mm_changed() {
  VIDEO_CHANGED=1
  if (($(mm_count) > 1)); then
    ui_info "Multiple Monitors" "Preparing the GroovyMAME games with 2 or 3 screens..." "" \
      "The first time this reads the whole game list: about a minute."
    mm_mame_prepare || ui_msg "Multiple Monitors" "Could not prepare the GroovyMAME games (see the log)." "" \
      "GroovyMAME prepares them when it opens the next game."
  fi
}

# screen_video_setup e o menu; ao sair, no sistema instalado, grava a linha
# do kernel e oferece reiniciar.
screen_video_setup() {
  local choice last=monitor summary
  VIDEO_CHANGED=0
  while true; do
    summary=$(ui_fields \
      "Monitor|$(monitor_label "$(conf_get monitor 2> /dev/null || echo "not set")")" \
      "Orientation|$(orientation_label "$(conf_get orientation 2> /dev/null || echo horizontal)")" \
      "Resolution|$(mode_pretty "$(conf_get boot_resolution 2> /dev/null || echo "from boot menu")")" \
      "Geometry|$(conf_get geometry > /dev/null 2>&1 && echo "adjusted" || echo "monitor default")" \
      "Monitors|$(mm_count)")
    choice=$(ui_menu "Video Setup" "$summary" "$last" \
      "monitor|Monitor Type" \
      "orientation|Monitor Orientation" \
      "resolution|Resolution" \
      "geometry|Geometry" \
      "geometry_reset|Reset Geometry" \
      "monitors|Multiple Monitors" \
      "return|Return") || choice="return"
    last=$choice
    case $choice in
      monitor) screen_monitor_type ;;
      orientation) screen_orientation ;;
      resolution) screen_resolution ;;
      geometry) screen_geometry ;;
      geometry_reset) screen_geometry_reset ;;
      monitors) screen_multi_monitor ;;
      return) break ;;
    esac
  done
  ((VIDEO_CHANGED)) || return 0
  if is_installed && ! is_live; then
    ui_info "Video Setup" "Saving the boot settings..."
    xorg_generate
    if ! boot_apply; then
      ui_msg "Video Setup" "Could not update the boot settings (see the log)."
      return 1
    fi
    if ui_yesno "Video Setup" "The new video settings are used after a reboot. Reboot now?" no; then
      screen_reboot_now
    fi
  fi
  return 0
}
