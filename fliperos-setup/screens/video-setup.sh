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
      "Geometry|$(conf_get geometry > /dev/null 2>&1 && echo "adjusted" || echo "monitor default")")
    choice=$(ui_menu "Video Setup" "$summary" "$last" \
      "monitor|Monitor Type" \
      "orientation|Monitor Orientation" \
      "resolution|Resolution" \
      "geometry|Geometry" \
      "geometry_reset|Reset Geometry" \
      "return|Return") || choice="return"
    last=$choice
    case $choice in
      monitor) screen_monitor_type ;;
      orientation) screen_orientation ;;
      resolution) screen_resolution ;;
      geometry) screen_geometry ;;
      geometry_reset) screen_geometry_reset ;;
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
