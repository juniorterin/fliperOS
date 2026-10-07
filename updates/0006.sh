#!/usr/bin/env bash
# Update 6: o splash padrao passa a ser o fliperos-text (o tema de terminal
# animado). So troca quem ainda esta no padrao antigo (fliperos) sem ter
# escolhido um tema no Setup > Splash screen.
set -euo pipefail
themes=/usr/share/plymouth/themes
file=$themes/fliperos-text/fliperos-text.plymouth
[[ -f $file ]] || exit 0
[[ $(readlink -f "$themes/default.plymouth" 2> /dev/null) == "$themes/fliperos/fliperos.plymouth" ]] || exit 0
grep -q '^splash=' /etc/fliperos/fliperos.conf 2> /dev/null && exit 0
echo "== Boot splash: fliperos-text"
update-alternatives --install "$themes/default.plymouth" default.plymouth "$file" 100 > /dev/null
update-alternatives --set default.plymouth "$file" > /dev/null
update-initramfs -u > /dev/null || echo "warning: update-initramfs failed; the old splash stays until it runs"
