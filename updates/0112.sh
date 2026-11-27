#!/usr/bin/env bash
# Update 112: ~/save e ~/nvram ligados a um disco Batocera ext4 eram pastas do
# root (as do Batocera), e o fliperos-roms do login nao criava as de cada
# emulador dentro (~/save/retroarch). O link /opt/fliperos/saves/retroarch
# ficava quebrado, o RetroArch nao gravava os saves e o update 109 parava no
# install -d dele. O batocera_use novo da as duas ao fliperos ao ligar o disco;
# aqui, as de um disco que ja esta ligado (instalar a biblioteca nova nao o liga
# de novo). So a pasta, sem -R: o que o Batocera gravou dentro fica como esta.
set -uo pipefail
home=${FLIPEROS_HOME:-/home/fliperos}
user=${FLIPEROS_USER:-fliperos}
media=${FLIPEROS_MEDIA_ROOT:-/media/$user}
id "$user" > /dev/null 2>&1 || exit 0
for rel in save nvram; do
  [[ -L $home/$rel ]] || continue
  target=$(readlink -f -- "$home/$rel") || continue
  [[ $target == "$media"/* && -d $target ]] || continue
  [[ $(stat -c %U -- "$target") == "$user" ]] && continue
  chown "$user:" "$target" && echo "~/$rel: $target now belongs to $user"
done
# As pastas de cada emulador (~/save/retroarch...), como no login.
if [[ -x /opt/fliperos/bin/fliperos-roms ]]; then
  runuser -u "$user" -- env HOME="$home" /opt/fliperos/bin/fliperos-roms > /dev/null 2>&1 || true
fi
exit 0
