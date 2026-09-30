# shellcheck shell=bash
# Setup > Latency: o modo de latencia e a conferencia da maquina contra a
# recomendacao do modo de baixa latencia.

screen_latency() {
  local choice last mode verdict missing analog fields
  mode=$(latency_mode)
  last=$mode
  analog=$(hw_analog_outputs)
  while true; do
    mode=$(latency_mode)
    if hw_low_latency_ok; then
      verdict=$(ui_yes "This computer is ready for low latency mode.")
    else
      verdict=$(ui_no "Below the low latency recommendation.")
    fi
    fields=$(ui_fields \
      "Mode|$(latency_label "$mode")" \
      "CPU|$(hw_cpu_model)" \
      "Cores|$(hw_cpu_cores) cores, $(hw_cpu_threads) threads, $(hw_mhz_label "$(hw_cpu_max_mhz)")" \
      "Instructions|$(hw_level_label "$(hw_cpu_level)")" \
      "Memory|$(hw_ram_label "$(hw_ram_mb)")" \
      "GPU|$(hw_gpu)" \
      "Analog out|${analog:-none (needs a VGA adapter)}")
    choice=$(ui_menu "Latency" "$fields"$'\n\n'"$verdict" "$last" \
      "standard|Standard (any hardware)$([[ $mode == standard ]] && echo " - current")" \
      "low|Low latency (modern CPUs)$([[ $mode == low ]] && echo " - current")" \
      "check|Check this computer" \
      "ideal|Recommended hardware" \
      "return|Return") || return 0
    last=$choice
    case $choice in
      standard | low)
        if [[ $choice == low ]] && ! hw_low_latency_ok; then
          missing=$(hw_low_latency_missing)
          ui_yesno "Low latency" "This computer is below the recommendation: $missing. Games may stutter. Enable low latency mode anyway?" no || continue
        fi
        screen_latency_apply "$choice"
        ;;
      check) screen_latency_check ;;
      ideal) screen_latency_ideal ;;
      return) return 0 ;;
    esac
  done
}

# screen_latency_apply MODO grava o modo, a linha do kernel e oferece
# reiniciar (o preempt= e o polling do USB so valem no proximo boot).
screen_latency_apply() {
  local mode=$1 ok=1
  ui_info "Latency" "Applying $(latency_label "$mode") mode..."
  latency_apply "$mode" || ok=0
  if ((ok)) && is_installed; then
    boot_apply || ok=0
  fi
  if ((!ok)); then
    ui_msg "Latency" "Could not apply every setting." "" "Details in $FLIPEROS_LOG."
    return 0
  fi
  speak "$(latency_label "$mode") mode is on."
  ui_yesno "Latency" "$(latency_label "$mode") mode is on. The emulator settings apply now; the kernel settings apply after a restart. Restart now?" no \
    && run_logged systemctl reboot
  return 0
}

screen_latency_check() {
  local rows=() mark label have need
  while IFS='|' read -r mark label have need; do
    if [[ $mark == ok ]]; then
      rows+=("$label|$(ui_yes "$have")")
    else
      rows+=("$label|$(ui_no "$have") (need $need)")
    fi
  done < <(hw_low_latency_check)
  if hw_low_latency_ok; then
    ui_msg "Check this computer" "$(ui_fields "${rows[@]}")" "" \
      "$(ui_yes "Low latency mode is recommended for this computer.")"
  else
    ui_msg "Check this computer" "$(ui_fields "${rows[@]}")" "" \
      "$(ui_no "Use Standard mode, or expect stutter in low latency mode.")"
  fi
}

screen_latency_ideal() {
  ui_msg "Recommended hardware" \
    "$(ui_c "$C_CYAN" "Standard mode (any game up to PS1 and most arcade)")" \
    "64-bit CPU with 2 cores, 4 GB RAM, 16 GB disk" \
    "" \
    "$(ui_c "$C_CYAN" "Low latency mode")" \
    "CPU with AVX2 (Intel 4th gen / AMD Ryzen or newer)" \
    "4 threads, 3.0 GHz or more, 4 GB RAM (8 GB better)" \
    "" \
    "$(ui_c "$C_CYAN" "Everything (PS2, Model 3, Dreamcast)")" \
    "4 cores with AVX2 (Core i7-7700, Ryzen 5 3600 or newer)" \
    "16 GB RAM, SSD" \
    "" \
    "GPU: an AMD card with VGA or DVI-I output. At CRT resolutions" \
    "even the R7 240 is above what PCSX2 needs."
}
