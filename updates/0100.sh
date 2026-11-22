#!/usr/bin/env bash
# Update 100: o desktop num monitor de 31 kHz. O xorg.conf de um gabinete que ja
# esta configurado em 31 kHz com o modo do boot vindo de um EDID (um conversor
# DisplayPort/HDMI para VGA) saiu sem modeline, e o X escolhia sozinho um modo do
# EDID fora da faixa do monitor ("fora de frequencia" ao abrir o desktop). O
# gerador (fliperos-setup/lib/xorg.sh) agora poe sempre o 640x480 de 31 kHz; aqui
# o arquivo e refeito nas maquinas que ja tem a configuracao, porque so instalar o
# gerador novo nao muda o /etc/X11/xorg.conf.d/10-fliperos.conf.
set -uo pipefail
lib=${FLIPEROS_SETUP_LIB:-/usr/local/lib/fliperos-setup/lib}
[[ -d $lib ]] || exit 0
(
  set +eu
  for f in "$lib"/*.sh; do
    # shellcheck source=/dev/null
    . "$f"
  done
  [[ $(conf_get frequency 2> /dev/null) == 31k ]] || {
    echo "xorg: not a 31 kHz monitor, nothing to redo"
    exit 0
  }
  xorg_generate || {
    echo "warning: xorg_generate failed"
    exit 0
  }
  echo "xorg: 31 kHz desktop mode written to ${XORG_CONF:-/etc/X11/xorg.conf.d/10-fliperos.conf}"
)
exit 0
