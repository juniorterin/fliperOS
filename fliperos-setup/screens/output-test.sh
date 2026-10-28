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
        speak_stop
        if drm_is_analog "$name" && drm_card_low_dotclock_testable "$card"; then
          screen_low_dotclock_test "$card" "$(video_suggested_monitor)"
        fi
        OT_FLAGS=$(video_classify "$c")
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

# screen_low_dotclock_test CARD MONITOR: uma NVIDIA (nouveau) com saida
# analogica pode gerar os dotclocks de 15 kHz com o patch 10 do kernel, mas
# cada PLL tem o seu piso. O grid sobe pelos degraus do LOWDOT_STEPS (320x240
# a 6,5 MHz, depois 384, 512 e 640 de largura): o primeiro visto fica com as
# resolucoes nativas a partir dele; quem nao viu nenhum (ou nao respondeu),
# com a super resolucao. So num monitor de 15 kHz: e o unico que recebe esses
# modos. Status 0 = a placa passou.
screen_low_dotclock_test() {
  local card=$1 monitor=$2 title="Low resolution test" gpu step width min mhz first=1
  [[ $(monitor_frequency "$monitor" 2> /dev/null) == 15k ]] || return 1
  have switchres || return 1
  gpu=$(drm_card_name "$card")
  speak "Testing native low resolutions. A grid will be shown for ${LOWDOT_TEST_SECONDS:-20} seconds. Press Enter if you can see it, or wait."
  ui_timed_confirm "$title" 8 "Start now" \
    "$gpu may be able to show native 15 kHz resolutions (320x240)." "" \
    "A test grid will now be shown for up to ${LOWDOT_TEST_SECONDS:-20} seconds." \
    "Press ENTER if you can see it. If the screen stays black, just wait." \
    "If not, a wider grid is tried (up to 640x240)."
  for step in $LOWDOT_STEPS; do
    width=${step%%:*}
    min=${step#*:}
    mhz=$(video_low_dotclock_mhz "$width")
    if ((!first)); then
      speak "Trying a wider grid."
      ui_timed_confirm "$title" 5 "Start now" \
        "Next: a ${width}x240 grid ($mhz MHz), easier for the card." "" \
        "Press ENTER if you can see it. If the screen stays black, just wait."
    fi
    first=0
    ui_clear
    GRID_TEXT="${width}x240 native" ui_text video_low_dotclock_grid "$monitor" "$width" >> "$FLIPEROS_LOG" 2>&1
    # O que o nouveau disse no grid vai para o log: o modo passa da validacao
    # (patch 10), e o que falha numa placa e o PLL do pixel clock ("unable to
    # find matching pll values" ou nada, com o VCO abaixo da faixa).
    video_low_dotclock_kernel_log >> "$FLIPEROS_LOG" 2>&1
    ui_flush_input
    speak "Did you see the grid?"
    if ui_yesno "$title" "Did you see the ${width}x240 test grid ($mhz MHz) clearly?" no; then
      video_low_dotclock_set "$card" 1 "$min"
      return 0
    fi
  done
  video_low_dotclock_set "$card" 0
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

  if [[ $flags == s* && $(video_low_dotclock_min "$card") != 0 ]]; then
    lowres=$(ui_yes "YES (from $(video_low_dotclock_min "$card") MHz)")
    notes+=("Native 15 kHz resolutions will be used from $(video_low_dotclock_min "$card") MHz. Narrower games are shown at double width, with the same picture on a CRT.")
  elif [[ $flags == s* ]]; then
    lowres=$(ui_yes YES)
    notes+=("Your video card supports low dotclocks: native 15 kHz resolutions will be used.")
  elif [[ $driver == nouveau ]]; then
    # A placa pode gerar dotclock baixo; o que falta e o nouveau (o PLL dele
    # nesta placa). O driver da NVIDIA e outra historia (o Batocera o usa).
    lowres=$(ui_no "NO (super resolutions)")
    notes+=("The native 320x240 test did not show on the nouveau driver: super resolutions will be used, with the same picture on a CRT." "Once installed, Setup > Video Setup > Video driver can switch to the NVIDIA driver.")
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

# ── Placa de video trocada, ou teste pedido (sistema instalado) ───────
# video_hw_boot_check (lib/video.sh) marca hw_changed no boot e grava um modo
# seguro; antes do launcher o fliperos-tty1 chama --hw-check, que pergunta e
# refaz o teste de saidas. O Video Setup pode pedir o teste (hw_retest) para o
# proximo boot: o teste precisa da tela livre, sem a interface grafica aberta.
HW_CHECK_MAX_ASKS=${HW_CHECK_MAX_ASKS:-3}
HW_FLAGS="hw_changed hw_old_gpu hw_safe_boot hw_check_asked hw_retest"

# screen_hw_retest_apply: o teste de saidas, e o que ele decidiu no sistema
# instalado (Xorg, linha do kernel, Limine), como o fim do Video Setup.
screen_hw_retest_apply() {
  local key
  if ! screen_video_detection; then
    ui_msg "Video output test" "The test did not finish. The video settings were not changed."
    return 1
  fi
  for key in $HW_FLAGS; do
    conf_unset "$key"
  done
  xorg_generate
  if ! boot_apply; then
    ui_msg "Video output test" "Could not update the boot settings (see the log)."
    return 1
  fi
  if ui_yesno "Video output test" "The new video settings are used after a reboot. Reboot now?" yes; then
    screen_reboot_now
  fi
  return 0
}

# screen_hw_change_check (fliperos-setup --hw-check, antes do launcher, tambem
# no modo jogo): so no sistema instalado. Roda quando a placa trocou
# (hw_changed, ou video_hw_changed se o boot nao rodou) ou o teste foi pedido
# (hw_retest). "Nao" pergunta de novo no proximo boot; depois de
# HW_CHECK_MAX_ASKS respostas, aceita a placa de agora e para de perguntar.
screen_hw_change_check() {
  local change="" old new asked text key id
  is_installed && ! is_live || return 0
  if conf_get hw_retest > /dev/null 2>&1; then
    text="You asked to test the video outputs again. Run the test now? It takes about a minute."
  else
    if conf_get hw_changed > /dev/null 2>&1; then
      change=$(video_hw_changed) ||
        change="$(conf_get hw_old_gpu 2> /dev/null || echo "the old card")|$(drm_card_name "$(video_main_card)")"
    else
      change=$(video_hw_changed) || return 0
      conf_set hw_changed 1
    fi
    old=${change%%|*}
    new=${change#*|}
    text="The video card changed: it was $old and now it is $new. FliperOS put a safe video mode on it. Redo the video output test now, to set the right resolution for this card? It takes about a minute."
  fi
  log_info "aviso de hardware de video: ${change:-teste pedido}"
  if ui_yesno "Video card changed" "$text" yes; then
    screen_hw_retest_apply
    return 0
  fi
  asked=$(conf_get hw_check_asked 2> /dev/null) || asked=0
  [[ $asked =~ ^[0-9]+$ ]] || asked=0
  asked=$((asked + 1))
  if ((asked >= HW_CHECK_MAX_ASKS)) || conf_get hw_retest > /dev/null 2>&1; then
    id=$(drm_card_id "$(video_main_card)" 2> /dev/null) && conf_set gpu_id "$id"
    for key in $HW_FLAGS; do
      conf_unset "$key"
    done
    log_info "aviso de hardware de video: dispensado"
  else
    conf_set hw_check_asked "$asked"
  fi
  return 0
}
