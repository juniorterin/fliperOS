# shellcheck shell=bash
# Teste das saidas de video (primeira coisa na midia de instalacao), como o
# auto_configure do gatools: acende as saidas analogicas, apaga tudo e liga
# uma de cada vez, falando pelo espeak, ate a pessoa apertar ENTER na que
# aparece no monitor. Diferente do gatools, que testa todas e escolhe a
# melhor, aqui o primeiro ENTER encerra o teste: quem esta vendo a tela ja
# disse qual saida funciona.

OT_CONN=""
OT_FLAGS=""
OT_FORCED=0
OT_EDID_SIZE=0
OUTPUT_TEST_SECONDS=${OUTPUT_TEST_SECONDS:-10}
OUTPUT_TEST_ROUNDS=${OUTPUT_TEST_ROUNDS:-3}

screen_output_test() {
  local conns=() c name card gpu round rc
  mapfile -t conns < <(drm_connectors)
  if ((${#conns[@]} == 0)); then
    ui_msg "Video output test" "No video output was found." "" \
      "The settings chosen in the boot menu will be kept."
    return 1
  fi
  log_info "teste de saidas: ${conns[*]}"

  # Acende as saidas analogicas antes de qualquer coisa: um CRT sem EDID
  # pode nao receber imagem nem para ler este aviso.
  video_lights_on
  sleep 1
  speak "Starting the video output test. Each output will be tested one at a time. When you can see the screen, press Enter."
  ui_timed_confirm "Video output test" 8 "Start now" \
    "Each video output of this computer will now be tested, one at a time." "" \
    "When the test screen appears on your monitor, press ENTER." \
    "The computer will speak to tell you what is happening."

  video_all_off
  for ((round = 1; round <= OUTPUT_TEST_ROUNDS; round++)); do
    for c in "${conns[@]}"; do
      name=$(drm_name "$c")
      card=$(drm_card "$c")
      video_test_begin "$c" || continue
      video_map_console "$card"
      # Tempo para o modeset e para o CRT sincronizar antes de desenhar.
      sleep 1
      gpu=$(drm_card_name "$card")
      speak "Testing output $(speech_connector "$name"). If you can see this screen, press Enter."
      ui_timed_confirm "Testing output $name" "$OUTPUT_TEST_SECONDS" "I can see this screen" \
        "$(ui_fields "Output|$name" "GPU|$gpu" "Test|round $round of $OUTPUT_TEST_ROUNDS")" "" \
        "If you can see this screen clearly, press ENTER." \
        "If nothing happens, the next output is tested in $OUTPUT_TEST_SECONDS seconds."
      rc=$?
      if ((rc == 0)); then
        OT_CONN=$c
        OT_FORCED=$VT_FORCED
        OT_EDID_SIZE=$VT_EDID_SIZE
        OT_FLAGS=$(video_classify "$c")
        speak_stop
        log_info "teste de saidas: $name confirmada (flags $OT_FLAGS)"
        video_restore "$c" "$OT_FORCED"
        return 0
      fi
      video_test_end "$c"
    done
    ((round < OUTPUT_TEST_ROUNDS)) && speak "No output was confirmed. Testing all outputs again."
  done
  video_all_detect
  speak "No output was confirmed."
  ui_msg "Video output test" "No output was confirmed." "" \
    "The settings chosen in the boot menu will be kept." \
    "You can run the test again from the boot menu (reboot)."
  return 1
}

# screen_testing_results mostra o que o teste achou, como o "Testing
# results" do gatools (inform_user), e pede para validar ou repetir.
# Status 0 = validado.
screen_testing_results() {
  local c=$OT_CONN flags=$OT_FLAGS base name card gpu driver info w h khz hz inter
  local current="unknown" freq="unknown" lowres interlace edid detection forced edid_name
  local notes=()
  name=$(drm_name "$c")
  card=$(drm_card "$c")
  base=${flags%a}
  gpu=$(drm_card_name "$card")
  driver=$(drm_card_driver "$card" || echo unknown)

  if info=$(video_current_mode "$name"); then
    IFS='|' read -r w khz hz inter <<< "$info"
    h=${w#*x}
    w=${w%x*}
    if [[ $inter == true ]]; then
      current="${w}x${h}i @ $(printf '%.2f' "$hz") Hz"
    else
      current="${w}x${h} @ $(printf '%.2f' "$hz") Hz"
    fi
    freq="$(printf '%.2f' "$khz") kHz"
  fi

  if [[ $flags == s* ]]; then
    lowres=$(ui_yes YES)
    notes+=("Your video card supports low dotclocks: native 15 kHz resolutions will be used.")
  else
    lowres=$(ui_no "NO (super resolutions)")
    notes+=("Your video card doesn't support low dotclocks: super resolutions will be used.")
  fi
  if drm_has_interlace "$c" || [[ $inter == true ]]; then
    interlace=$(ui_yes YES)
  else
    interlace=$(ui_no NO)
  fi

  edid_name=$(edid_monitor_name "$(drm_edid_file "$c")" 2> /dev/null || true)
  case $base in
    *do)
      edid=$(ui_yes "YES (forced at boot: $edid_name)")
      detection=$(ui_yes "DETECTED ($(video_edid_monitor "$c"))")
      notes+=("The EDID chosen in the boot menu will be kept.")
      ;;
    *o)
      edid=$(ui_yes "YES (Switchres: $edid_name)")
      detection=$(ui_yes "DETECTED ($(video_edid_monitor "$c"))")
      notes+=("Found a valid Switchres EDID: no other configuration is needed.")
      ;;
    *l)
      edid=$(ui_yes "YES (${edid_name:-factory EDID})")
      detection=$(ui_no "LCD OR MODERN CRT")
      notes+=("Found a monitor that could be a LCD panel.")
      ;;
    *r)
      edid=$(ui_no NO)
      detection=$(ui_no "NOT DETECTED")
      notes+=("The arcade monitor was detected, but it didn't return any info.")
      ;;
    *e)
      edid=$(ui_no NO)
      detection=$(ui_no "NOT DETECTED")
      notes+=("The arcade monitor couldn't be natively detected." "The output will be forced at boot.")
      ;;
  esac
  if [[ $base == *e ]]; then forced=$(ui_no YES); else forced=NO; fi
  [[ $flags == *a ]] && notes+=("Your video card is an APU: interlace_force_even=1 will be set.")

  local fields
  fields=$(ui_fields "GPU|$gpu" "Driver|$driver" "Connection|$name" "Current mode|$current" \
    "Horizontal freq.|$freq" "Low resolution support|$lowres" "Interlaced modes|$interlace" \
    "EDID|$edid" "Monitor detection|$detection" "Force output at boot|$forced")
  ui_size
  if ((UI_ROWS < 28)); then
    # 512x384 (25 kHz) da 24 linhas: so os campos cabem.
    ui_choice2 "Testing Results" "Validate settings" "Repeat test" "$fields" "Validate these settings?"
  else
    ui_choice2 "Testing Results" "Validate settings" "Repeat test" \
      "$fields" "" "$(printf '%s\n' "${notes[@]}")" "" "Do you want to validate these settings?"
  fi
}

# screen_video_detection faz o teste, mostra o resultado e grava. Quando o
# monitor nao se identificou, pede o tipo (o gatools obriga a escolher).
screen_video_detection() {
  local monitor
  while true; do
    screen_output_test || return 1
    if screen_testing_results; then
      break
    fi
    video_all_off
  done
  if video_needs_monitor_choice "$OT_FLAGS"; then
    until monitor=$(screen_pick_monitor "$(video_suggested_monitor)" required); do :; done
  else
    monitor=$(video_edid_monitor "$OT_CONN")
  fi
  video_save_result "$OT_CONN" "$OT_FLAGS" "$monitor"
  speak "Video settings saved."
  return 0
}
