# shellcheck shell=bash
# Setup > Splash screen: a lista dos temas de ~/splashscreen, a previa de
# cada um na tela e o do boot (lib/splash.sh).

screen_splash() {
  local title="Splash screen" choice last current entry name label items
  local -a themes
  while true; do
    mapfile -t themes < <(splash_list)
    if ((${#themes[@]} == 0)); then
      ui_msg "$title" "No theme was found in $SPLASH_DIR." \
        "Each theme is a folder with its .plymouth file (on the network, the splashscreen share)." \
        "" "More themes: $SPLASH_MORE_URL"
      return 0
    fi
    current=$(splash_current) || current=""
    items=()
    for entry in "${themes[@]}"; do
      name=${entry%%|*}
      label=${entry#*|}
      [[ $name == "$current" ]] && label="$label (current)"
      items+=("$name|$label")
    done
    choice=$(ui_menu "$title" \
      "$(printf '%s\n' "The boot screen. The themes are the folders in ~/splashscreen (on the network, the splashscreen share): pick one to see a preview or to use it at boot." \
        "More themes: $SPLASH_MORE_URL")" \
      "${last:-$current}" "${items[@]}" "-return|Return") || return 0
    [[ $choice == -return ]] && return 0
    last=$choice
    screen_splash_theme "$choice"
  done
}

# screen_splash_theme NOME: previa e "usar no boot".
screen_splash_theme() {
  local name=$1 title="Splash screen" choice text
  text="Theme: $name ($(splash_source "$name"))"
  [[ $name == "$(splash_current)" ]] && text+=$'\n'"It is the boot splash now."
  while true; do
    choice=$(ui_menu "$title" "$text" preview "preview|Preview (${SPLASH_PREVIEW_SECONDS} seconds)" \
      "use|Use at boot" "return|Return") || return 0
    case $choice in
      preview)
        # O plymouthd toma a tela inteira: no desktop ele brigaria com o X.
        if [[ -n ${DISPLAY:-} ]]; then
          ui_msg "$title" "The preview takes the whole screen: open the Setup from the FliperOS menu, not from the desktop."
          continue
        fi
        ui_clear
        splash_preview "$name" || ui_msg "$title" "$(ui_bad "The preview did not open.")" "Log: $FLIPEROS_LOG"
        ui_flush_input
        ;;
      use)
        ui_info "$title" "Setting $name as the boot splash. The boot image is rebuilt: about a minute..."
        if splash_set "$name"; then
          ui_msg "$title" "$name is the boot splash from the next boot on."
          return 0
        fi
        ui_msg "$title" "$(ui_bad "The splash was not changed.")" "Log: $FLIPEROS_LOG"
        ;;
      return) return 0 ;;
    esac
  done
}
