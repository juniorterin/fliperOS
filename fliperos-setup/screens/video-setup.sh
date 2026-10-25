# shellcheck shell=bash
# Video Setup: tipo de monitor, orientacao, resolucao e geometria, como o
# worker_video_menu do gasetup. Na midia so grava no fliperos.conf (o
# instalador leva para o disco); no sistema instalado aplica no boot.

VIDEO_CHANGED=0

# screen_pick_monitor [PADRAO] [required] [custom] imprime o preset
# escolhido; com "custom", tambem a entrada do monitor custom, logo depois
# do Generic 15.7 kHz.
screen_pick_monitor() {
  local def=${1:-} required=${2:-} custom=${3:-} entries=() entry text
  for entry in "${MONITOR_PRESETS[@]}"; do
    entries+=("$entry")
    [[ $custom == custom && ${entry%%|*} == generic_15 ]] && entries+=("custom|Custom - your own crt_range")
  done
  text="Select the monitor connected to this output."
  [[ $required == required ]] && text+=" This is needed to set the correct video mode."
  ui_menu "Monitor Type" "$text" "$def" "${entries[@]}"
}

screen_monitor_type() {
  local monitor current def
  current=$(conf_get monitor 2> /dev/null) || current=$(video_suggested_monitor)
  def=$current
  video_custom_active && def=custom
  monitor=$(screen_pick_monitor "$def" "" custom) || return 0
  if [[ $monitor == custom ]]; then
    screen_custom_monitor
    return 0
  fi
  if video_custom_active; then
    ui_yesno "Monitor Type" "Use the $(monitor_label "$monitor") preset and discard your custom crt_range?" no ||
      return 0
    # O mesmo preset de base: so volta a ele (o Reset Geometry).
    if [[ $monitor == "$current" ]]; then
      geometry_reset
      return 0
    fi
  fi
  [[ $monitor == "$current" ]] && return 0
  video_reconfigure_monitor "$monitor" || {
    ui_msg "Monitor Type" "Could not configure $(monitor_label "$monitor")."
    return 0
  }
  VIDEO_CHANGED=1
}

# screen_custom_monitor: o monitor custom do Switchres, um crt_range0 no
# lugar das faixas do preset de agora (que segue dando o modo de boot). O
# crt_range sai do Geometry (o grid parte do monitor em uso) ou e digitado,
# como os publicados para cada modelo de monitor.
screen_custom_monitor() {
  local base how
  base=$(conf_get monitor 2> /dev/null) || base=""
  if [[ -z $base ]]; then
    ui_msg "Custom monitor" "Choose the monitor model (or the closest one) first." "" \
      "The custom crt_range is built on top of it: the boot resolution still comes from that preset."
    return 0
  fi
  if [[ $base == lcd ]]; then
    ui_msg "Custom monitor" "A crt_range is for CRT monitors; the LCD preset uses the monitor's own EDID."
    return 0
  fi
  how=$(ui_menu "Custom monitor" "Your own crt_range0 (the monitor's timings) on top of $(monitor_label "$base"). The boot resolution still comes from that preset." grid \
    "grid|Make it with the test grid (Geometry)" \
    "type|Type a crt_range") || return 0
  case $how in
    grid) screen_geometry ;;
    type) screen_crt_range_input "$base" ;;
  esac
}

# screen_crt_range_input BASE: um crt_range digitado, da mesma faixa (15, 25
# ou 31 kHz) do preset de base, senao o modo de boot nao casaria com ele.
screen_crt_range_input() {
  local base=$1 range rfreq bfreq
  range=$(conf_get geometry 2> /dev/null) || range=$(video_preset_range "$base") || range=""
  range=$(ui_input "Custom monitor" "crt_range0: 16 values separated by commas, as in switchres.ini (HfreqMin-HfreqMax,VfreqMin-VfreqMax, 6 porch/sync values, 2 polarities, 4 line limits)" "$range") ||
    return 0
  range=${range//[[:space:]]/}
  [[ -n $range ]] || return 0
  if ! crt_range_valid "$range"; then
    ui_msg "Custom monitor" "That is not a crt_range; nothing was changed." "" \
      "Example: 15625-16200,49.5-65,2.0,4.7,8.0,0.064,0.192,1.024,0,0,192,288,448,576"
    return 0
  fi
  rfreq=$(crt_range_frequency "$range") || rfreq=""
  bfreq=$(monitor_frequency "$base") || bfreq=""
  if [[ -z $rfreq || $rfreq != "$bfreq" ]]; then
    ui_msg "Custom monitor" "This crt_range is for ${rfreq:-an unknown} frequency, but $(monitor_label "$base") boots at ${bfreq:-?}." "" \
      "Choose a preset of the same frequency first, then Custom."
    return 0
  fi
  geometry_apply "$range"
  ui_msg "Custom monitor" "Saved: the monitor is now $(video_monitor_label)." "" "$range"
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
  ui_orientation "$o"
  # O boot em pe tambem: o splash girado e o console em 640x480i (o
  # initramfs e refeito: uns segundos).
  run_with_progress "Monitor Orientation" "Preparing the boot" orientation_boot "$o"
  # Os filtros de ROMs seguem o monitor: so os jogos desta orientacao.
  downloader_filter_orientation
  ui_msg "Monitor Orientation" "$(orientation_label "$o") saved." "" \
    "The ROM filters (Cleaner and Downloader) now take only the $(romclean_screen_orientation) games."
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
  # Na interface grafica, a lista vertical: os modos se leem e se comparam
  # melhor um embaixo do outro do que no carrossel.
  choice=$(UI_STYLE=list ui_menu "Resolution" "$text" "$current" "${choices[@]}" \
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
  GRID_TEXT="Testing ${w}x${h} ${r} Hz" ui_text switchres "$w" "$h" "$r" -s -l grid >> "$FLIPEROS_LOG" 2>&1
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
  read -r w h r <<< "$(geometry_grid_mode)"
  ui_msg "Geometry" "A test grid will be shown at ${w}x${h} (${r} Hz) to adjust the picture." "" \
    "Arrows: move the picture   Page Up/Down: width" \
    "ENTER: save   ESC: cancel   DEL: reset   CTRL + key: bigger steps" "" \
    "The picture only moves down while there are blank lines below it." \
    "If it stops, use the monitor's V-POS (vertical position) adjustment."
  ui_clear
  out=$(ui_text geometry "$w" "$h" "$r" 2>&1)
  printf '%s\n' "$out" >> "$FLIPEROS_LOG"
  ui_flush_input
  range=$(geometry_parse "$out")
  if [[ -z $range ]]; then
    if geometry_aborted "$out"; then
      ui_msg "Geometry" "The adjustment was cancelled; nothing was changed."
    else
      ui_msg "Geometry" "The geometry tool stopped with an error; nothing was changed." "" \
        "$(grep . <<< "$out" | tail -1)" "" "Details in $FLIPEROS_LOG."
    fi
    return 0
  fi
  geometry_apply "$range"
  ui_msg "Geometry" "Saved: the monitor is now $(video_monitor_label)." "" "$range"
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
  local conn choice last="" extras=() entries summary note="" games
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
# screen_mode480: o metodo de cada aplicacao para os jogos de 480 linhas
# (lib/video.sh, mode480_*), na tabela com uma marca por linha, como a dos
# servicos. Cada mudanca e gravada na hora (UI_GRID_LIVE), sem Enter: marcar
# "480i filter" abre antes o nivel do filtro daquela aplicacao
# (screen_deflicker_level), com o preview, e cancelar deixa a linha como
# estava. A tabela volta na mesma linha; Esc sai.
screen_mode480() {
  local title="480i hacks" text result key state level
  local -a rows
  text="How each program shows 480-line games. Changes save at once."
  [[ $(conf_get frequency 2> /dev/null) == 15* ]] ||
    text="Not a 15 kHz monitor: these only count on one."
  key=""
  while true; do
    mapfile -t rows < <(mode480_rows)
    result=$(UI_GRID_LIVE=1 UI_GRID_CURSOR=$key ui_grid "$title" "$text" \
      "240p|640x240;filter|480i filter;pure|480i pure" "${rows[@]}")
    (($? == 2)) || return 0
    key=${result%%$'\n'*}
    state=$(tr ',' '\n' <<< "${result#*$'\n'}" | sed -n "s/^$key=//p")
    level=""
    if [[ $state == filter ]]; then
      level=$(screen_deflicker_level "$key" "$(mode480_level "$key")") || continue
      if [[ $level == off ]]; then
        state=pure level=""
      fi
    fi
    mode480_set "$key" "$state" "$level" ||
      ui_msg "$title" "$(ui_bad "Could not save (see /var/log/fliperos-setup.log).")"
  done
}

# screen_colour: a calibracao de cor (lib/video.sh, color_*): na tela com
# os padroes de teste, ou parametro por parametro em numeros (o caminho pelo
# SSH), e o voltar ao padrao.
screen_colour() {
  local title="Colour calibration" caps choice last="" lut ctm range summary
  caps=$(color_caps)
  lut=$(sed -n 's/^lut //p' <<< "$caps")
  ctm=$(sed -n 's/^ctm //p' <<< "$caps")
  range=$(sed -n 's/^range //p' <<< "$caps")
  if [[ ! -x $COLOR_BIN ]]; then
    ui_msg "$title" "The colour calibration is not installed on this system (a FliperOS update builds it)."
    return 0
  fi
  while true; do
    summary="Gamma table: $([[ ${lut:-0} -gt 0 ]] && echo "$lut points" || echo "none")."
    summary+=" Saturation and hue: $([[ $ctm == yes ]] && echo "by the card" || echo "by software (games, menus, desktop; not the text console)")."
    [[ ${range:-none} != none ]] && summary+=" RGB range: $range."
    choice=$(ui_menu_hints "$title" "$summary" "$last" \
      "calibrate|Calibrate on the screen|Test patterns; the arrows change each setting on the tube." \
      "values|Settings in numbers|Each setting by its number (also over SSH)." \
      "reset|Back to the defaults|The picture exactly as the card sends it." \
      "return|Return|Back to Video Setup.") || return 0
    last=$choice
    case $choice in
      calibrate) screen_colour_calibrate "$range" ;;
      values) screen_colour_values "$range" ;;
      reset)
        ui_yesno "$title" "Every colour setting back to the default?" no || continue
        color_reset
        ui_text color_apply "$caps"
        ui_msg "$title" "Back to the defaults."
        ;;
      return) return 0 ;;
    esac
  done
}

# screen_colour_calibrate FAIXA: o calibrador (gui/color-calibrate.py) no
# modo do Video Setup, pelo fliperos-x11-run com a camada da matriz de cor.
screen_colour_calibrate() {
  local range=${1:-none} dir w h r key value rc
  if ((SETUP_REMOTE == 1)) || [[ -n ${DISPLAY:-} ]]; then
    ui_msg "Colour calibration" "The test patterns open on the cabinet screen, from the FliperOS menu (not over SSH or inside the desktop)." \
      "" "Over SSH, use Settings in numbers."
    return 0
  fi
  dir=$(mktemp -d) || return 0
  color_table > "$dir/table"
  {
    while IFS='|' read -r key _; do
      printf 'color_%s=%s\n' "$key" "$(color_get "$key")"
    done < <(color_table)
    [[ -n $(color_range) ]] && printf 'color_range=%s\n' "$(color_range)"
  } > "$dir/color.conf"
  read -r w h r <<< "$(geometry_mode)"
  ui_text env FLIPEROS_COLOR_FILE="$dir/color.conf" \
    "$DEFLICKER_X11_RUN" --mode "${w}x${h}@${r}" python3 "$SETUP_DIR/gui/color-calibrate.py" \
    --table "$dir/table" --conf "$dir/color.conf" --out "$dir/out" --range "$range" --bin "$COLOR_BIN" \
    >> "$FLIPEROS_LOG" 2>&1
  rc=$?
  ui_flush_input
  if ((rc == 0)) && [[ -s $dir/out ]]; then
    color_reset
    while IFS='=' read -r key value; do
      key=${key#color_}
      if [[ $key == range ]]; then
        color_range_set "$value"
      else
        color_set "$key" "$value"
      fi
    done < "$dir/out"
    ui_text color_apply
    ui_msg "Colour calibration" "Saved: it counts everywhere from now on."
  else
    # O X que fechou devolve a tabela de antes; a matriz e a faixa tambem.
    ui_text color_apply
  fi
  rm -rf "$dir"
}

# screen_colour_values FAIXA: cada parametro pelo numero.
screen_colour_values() {
  local range=${1:-none} key label min max help choice value last=""
  local -a entries
  while true; do
    entries=()
    while IFS='|' read -r key label min max _ _ help; do
      entries+=("$key|$label: $(color_pretty "$key" "$(color_get "$key")")|$help ($min to $max)")
    done < <(color_table)
    value=$(color_range)
    [[ $range != none ]] &&
      entries+=("range|RGB range: ${value:-card default}|Full for a PC monitor or CRT, limited for a TV that expects 16-235.")
    entries+=("return|Return|Back.")
    choice=$(ui_menu_hints "Colour settings" "Changes count right away." "$last" "${entries[@]}") || return 0
    last=$choice
    case $choice in
      return) return 0 ;;
      range)
        value=$(ui_radio "RGB range" "Full for a PC monitor or CRT; limited only for a TV that expects 16-235." \
          "$(r=$(color_range); echo "${r:-default}")" "default|Card default" "full|Full (0-255)" \
          "limited|Limited (16-235)") || continue
        [[ $value == default ]] && value=""
        color_range_set "$value"
        ;;
      *)
        value=$(ui_input "$(color_field "$choice" 2)" \
          "$(color_field "$choice" 7) From $(color_field "$choice" 3) to $(color_field "$choice" 4)." \
          "$(color_get "$choice")") || continue
        color_set "$choice" "$value" || { ui_msg "Colour settings" "Not a number: $value"; continue; }
        ;;
    esac
    ui_text color_apply
  done
}

# screen_deflicker_level CHAVE NIVEL: o nivel do filtro de uma aplicacao.
# Imprime light, medium, strong ou off (o preview com o filtro desligado);
# status 1 = cancelado.
screen_deflicker_level() {
  local key=$1 level=$2 label choice
  label=$(mode480_field "$key" 2)
  while true; do
    choice=$(ui_radio "Flicker filter: $label" \
      "In 480i a thin line exists in one field only and flickers. The filter blends each line with its neighbour: no flicker, a little softer." \
      "$level" \
      "preview|Preview on the screen (arrows change the level)" \
      "light|Light (sharpest)" \
      "medium|Medium (two lines averaged, like RePlayOS)" \
      "strong|Strong (no flicker at all)") || return 1
    if [[ $choice != preview ]]; then
      printf '%s\n' "$choice"
      return 0
    fi
    if choice=$(screen_deflicker_preview "$label" "$level"); then
      printf '%s\n' "$choice"
      return 0
    fi
  done
}

# screen_deflicker_preview ROTULO NIVEL abre o preview (gui/flicker-preview.py)
# em 640x480 no monitor, pelo fliperos-x11-run com a camada do filtro: as
# setas trocam o nivel na hora, Enter fica com ele. Imprime o escolhido.
screen_deflicker_preview() {
  local label=$1 level=$2 dir out rc
  if ((SETUP_REMOTE == 1)) || [[ -n ${DISPLAY:-} ]]; then
    ui_msg "Flicker filter" "The preview opens on the cabinet screen, from the FliperOS menu (not over SSH or inside the desktop)."
    return 1
  fi
  if [[ ! -f $DEFLICKER_LIB ]]; then
    ui_msg "Flicker filter" "The filter is not installed on this system (a FliperOS update builds it)."
    return 1
  fi
  dir=$(mktemp -d) || return 1
  out=$dir/chosen
  ui_text env FLIPEROS_DEFLICKER_FILE="$dir/level" FLIPEROS_DEFLICKER_FORCE="$([[ $(conf_get frequency 2> /dev/null) == 15* ]] && echo 0 || echo 1)" \
    "$DEFLICKER_X11_RUN" --mode 640x480@60 python3 "$SETUP_DIR/gui/flicker-preview.py" \
    --level "$level" --out "$out" --title "$label" >> "$FLIPEROS_LOG" 2>&1
  rc=$?
  ui_flush_input
  if ((rc == 0)) && [[ -s $out ]]; then
    cat "$out"
  else
    rc=1
  fi
  rm -rf "$dir"
  return "$rc"
}

screen_video_setup() {
  local choice last="" summary monitors=()
  VIDEO_CHANGED=0
  # Video driver so aparece com uma placa AMD que aceita os dois drivers.
  local driver=()
  [[ -n $(drm_dual_amd_cards) ]] &&
    driver=("driver|Video driver|radeon (tested on the CRT) or amdgpu (with Vulkan).")
  while true; do
    # Ate 5 linhas na interface grafica, ou o carrossel de icones vira lista:
    # a orientacao vai junto da resolucao, e Monitors so com mais de um.
    monitors=()
    (($(mm_count) > 1)) && monitors=("Monitors|$(mm_count)")
    summary=$(ui_fields \
      "Monitor|$(video_monitor_label)" \
      "Resolution|$(mode_pretty "$(conf_get boot_resolution 2> /dev/null || echo "boot menu")"), $(orientation_short "$(conf_get orientation 2> /dev/null || echo horizontal)")" \
      "Geometry|$(conf_get geometry > /dev/null 2>&1 && echo "adjusted" || echo "monitor default")" \
      "${monitors[@]}")
    choice=$(ui_menu_hints "Video Setup" "$summary" "$last" \
      "monitor|Monitor Type|The monitor model or its frequencies (15, 25 or 31 kHz)." \
      "orientation|Monitor Orientation|Horizontal, or vertical for a rotated monitor." \
      "resolution|Resolution|The resolution of the menus and the frontend." \
      "geometry|Geometry|Center and size the picture on the tube, with a test grid." \
      "geometry_reset|Reset Geometry|Undo the geometry: back to the monitor preset." \
      "monitors|Multiple Monitors|A second and a third monitor, for multi-screen games." \
      "mode480|480i hacks|For each program: 640x240, 480i with the flicker filter, or pure 480i." \
      "colour|Colour calibration|Brightness, contrast, gamma, each gun, colour and hue." \
      "${driver[@]}" \
      "return|Return|Save and leave. New video settings need a reboot.") || choice="return"
    last=$choice
    case $choice in
      monitor) screen_monitor_type ;;
      orientation) screen_orientation ;;
      resolution) screen_resolution ;;
      geometry) screen_geometry ;;
      geometry_reset) screen_geometry_reset ;;
      monitors) screen_multi_monitor ;;
      mode480) screen_mode480 ;;
      colour) screen_colour ;;
      driver) screen_amd_driver ;;
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
