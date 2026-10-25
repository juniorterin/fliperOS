#!/usr/bin/env bash
# Update 28: o som da tela ao vivo ja ligado. Com a tela ao vivo instalada e
# o ajuste nunca mexido (sem stream_audio no fliperos.conf), liga pelo Setup,
# que o desliga sozinho se o loopback nao abrir nesta placa. Quem o desligou
# continua desligado. Os jogos abertos depois saem com som na transmissao.
set -euo pipefail
conf=/etc/fliperos/fliperos.conf
setup=/usr/local/bin/fliperos-setup
[[ -x /opt/fliperos/go2rtc/go2rtc && -x $setup ]] || exit 0
grep -q '^stream_audio=' "$conf" 2> /dev/null && exit 0
"$setup" --setting stream_audio on > /dev/null 2>&1 || true
