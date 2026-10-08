# shellcheck shell=bash
# Configuracao do Xorg para o desktop e os frontends em X.
#
# O Xorg nao escolhe sozinho o modo da linha do kernel ("640x480iS" vem da
# tabela do patch 15 kHz, sem EDID): sem modeline ele pegaria o maior modo
# da lista, que para um tubo de 15 kHz pode ser 1024x768. Por isso o modo de
# boot vira Modeline + PreferredMode. Com EDID (dongle Switchres, LCD, boot
# por EDID) o proprio EDID manda e o arquivo so desliga o descanso de tela.
#
# Com monitores extras (lib/multimonitor.sh) cada saida tem o seu Monitor,
# lado a lado na ordem das telas dos jogos, e o principal e a tela primaria:
# e nela que os programas de uma tela so abrem.

XORG_CONF=${XORG_CONF:-/etc/X11/xorg.conf.d/10-fliperos.conf}

# xorg_generate [ARQUIVO] grava a configuracao a partir do fliperos.conf.
xorg_generate() {
  local file=${1:-$XORG_CONF} monitor freq mode modeline="" name="" hsync="" conn
  local screens=() extras=() s id prev="" i
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  freq=$(monitor_frequency "$monitor" 2> /dev/null) || freq=""
  mode=$(conf_get boot_resolution 2> /dev/null) || mode=""
  conn=$(conf_get connector 2> /dev/null) || conn=""
  mapfile -t screens < <(mm_screens 2> /dev/null)
  mapfile -t extras < <(mm_extras)
  if [[ -n $freq && -n $conn ]] && modeline=$(mode_modeline "$mode"); then
    name=${modeline#\"}
    name=${name%%\"*}
    hsync=$(mode_hsync_range "$freq")
  else
    modeline=""
  fi
  mkdir -p "$(dirname "$file")"
  {
    echo "# Gerado pelo fliperos-setup a partir de /etc/fliperos/fliperos.conf."
    echo "# Refeito a cada mudanca de monitor ou resolucao; editar aqui nao adianta."
    if [[ -n $modeline ]] || ((${#extras[@]} > 0)); then
      printf 'Section "Device"\n    Identifier "GPU"\n    Driver "modesetting"\n'
      printf '    Option "Monitor-%s" "CRT"\n' "$conn"
      for i in "${!extras[@]}"; do
        printf '    Option "Monitor-%s" "CRT%d"\n' "${extras[i]}" $((i + 2))
      done
      printf 'EndSection\n\n'
      for s in "${screens[@]}"; do
        id=CRT
        for i in "${!extras[@]}"; do
          [[ ${extras[i]} == "$s" ]] && id=CRT$((i + 2))
        done
        printf 'Section "Monitor"\n    Identifier "%s"\n' "$id"
        if [[ -n $modeline ]]; then
          printf '    HorizSync %s\n    VertRefresh 49.0 - 65.0\n    Modeline %s\n' "$hsync" "$modeline"
          printf '    Option "PreferredMode" "%s"\n' "$name"
        fi
        if ((${#extras[@]} > 0)); then
          [[ $id == CRT ]] && printf '    Option "Primary" "true"\n'
          [[ -n $prev ]] && printf '    Option "RightOf" "%s"\n' "$prev"
        fi
        printf '    Option "DPMS" "false"\nEndSection\n\n'
        prev=$id
      done
      printf 'Section "Screen"\n    Identifier "Screen0"\n    Device "GPU"\n    Monitor "CRT"\n    DefaultDepth 24\n'
      if [[ -n $modeline ]]; then
        printf '    SubSection "Display"\n        Depth 24\n        Modes "%s"\n    EndSubSection\n' "$name"
      fi
      printf 'EndSection\n\n'
    fi
    cat << 'EOF'
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF
  } > "$file.new" && mv -f "$file.new" "$file"
  log_info "xorg: $file ($mode ${screens[*]:-$conn})"
}
