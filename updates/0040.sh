#!/usr/bin/env bash
# Update 40: o monitor custom (Geometry) com o modo do Switchres no boot. Quem
# ja tem um crt_range salvo (geometry= no fliperos.conf) ficou com o modo de
# boot da tabela do kernel; o EDID do Switchres (fliperos-custom.bin), o
# Modeline do Xorg e a linha do kernel so se refazem pelas funcoes da lib, e
# o EDID pede o initramfs refeito (boot_apply). Sem geometria salva, nada muda.
set -euo pipefail
conf=/etc/fliperos/fliperos.conf
lib=/usr/local/lib/fliperos-setup/lib
grep -q '^geometry=' "$conf" 2> /dev/null || exit 0
(
  set +eu
  for f in "$lib"/*.sh; do
    # shellcheck source=/dev/null
    . "$f"
  done
  custom_boot_refresh
  boot_apply || { echo "boot_apply failed (see /var/log/fliperos-setup.log)"; exit 1; }
  ls -l /lib/firmware/edid/fliperos-custom.bin 2> /dev/null || echo "custom EDID: none (the table mode stays)"
)
