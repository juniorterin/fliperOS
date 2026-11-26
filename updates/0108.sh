#!/usr/bin/env bash
# Update 108: um HD de Batocera ligado na pasta errada. A deteccao do Batocera
# filesystem levava a primeira pasta (batocera/, userdata/ ou a raiz) que parecia
# Batocera, e recusava a roms/ da raiz quando o fliperos-roms tinha escrito o
# retroarch/ nela (a pessoa apontou ~/roms para la). Num disco com um esqueleto em
# batocera/ ao lado do Batocera de verdade, os consoles, a bios e os saves ficavam
# no esqueleto. A deteccao nova (fliperos-setup/lib/batocera.sh) escolhe a pasta
# com mais jogos; aqui o disco que ja esta ligado na outra e ligado de novo na
# certa (--batocera repair), porque instalar a biblioteca nova nao muda a
# batocera.list nem os atalhos de ~. O --storage auto do boot faz o mesmo, mas so
# no proximo boot ou ao ligar o disco.
set -uo pipefail
setup=${FLIPEROS_SETUP:-/usr/local/bin/fliperos-setup}
media=${FLIPEROS_MEDIA_ROOT:-/media/fliperos}
[[ -x $setup ]] || exit 0
for disk in "$media"/*/; do
  disk=${disk%/}
  # O atalho para a pasta ao lado (o /media/fliperos/<UUID> do disco sem rotulo)
  # e o mesmo disco.
  [[ -L $disk ]] && continue
  mountpoint -q -- "$disk" 2> /dev/null || continue
  echo "${disk##*/}: $("$setup" --batocera repair "$disk" 2>&1 | tr '\n' ' ')"
done
exit 0
