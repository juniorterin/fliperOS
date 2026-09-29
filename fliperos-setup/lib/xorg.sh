# shellcheck shell=bash
# Configuracao do Xorg para o desktop e os frontends em X.
#
# O Xorg nao escolhe sozinho o modo da linha do kernel ("640x480iS" vem da
# tabela do patch 15 kHz, sem EDID): sem modeline ele pegaria o maior modo
# da lista, que para um tubo de 15 kHz pode ser 1024x768. Por isso o modo de
# boot vira Modeline + PreferredMode. Com EDID (dongle Switchres, LCD, boot
# por EDID) o proprio EDID manda e o arquivo so desliga o descanso de tela.

XORG_CONF=${XORG_CONF:-/etc/X11/xorg.conf.d/10-fliperos.conf}

# xorg_generate [ARQUIVO] grava a configuracao a partir do fliperos.conf.
xorg_generate() {
  local file=${1:-$XORG_CONF} monitor freq mode modeline name hsync conn
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  freq=$(monitor_frequency "$monitor" 2> /dev/null) || freq=""
  mode=$(conf_get boot_resolution 2> /dev/null) || mode=""
  conn=$(conf_get connector 2> /dev/null) || conn=""
  mkdir -p "$(dirname "$file")"
  {
    echo "# Gerado pelo fliperos-setup a partir de /etc/fliperos/fliperos.conf."
    echo "# Refeito a cada mudanca de monitor ou resolucao; editar aqui nao adianta."
    if [[ -n $freq && -n $conn ]] && modeline=$(mode_modeline "$mode"); then
      name=${modeline#\"}
      name=${name%%\"*}
      hsync=$(mode_hsync_range "$freq")
      cat << EOF
Section "Device"
    Identifier "GPU"
    Driver "modesetting"
    Option "Monitor-$conn" "CRT"
EndSection

Section "Monitor"
    Identifier "CRT"
    HorizSync $hsync
    VertRefresh 49.0 - 65.0
    Modeline $modeline
    Option "PreferredMode" "$name"
    Option "DPMS" "false"
EndSection

Section "Screen"
    Identifier "Screen0"
    Device "GPU"
    Monitor "CRT"
    DefaultDepth 24
    SubSection "Display"
        Depth 24
        Modes "$name"
    EndSubSection
EndSection

EOF
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
  log_info "xorg: $file ($mode $conn)"
}
