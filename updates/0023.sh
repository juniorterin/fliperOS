#!/usr/bin/env bash
# Update 23: o driver VA-API da Mesa para a tela ao vivo. O fliperos-extras
# so instalava os pacotes dela sem o ffmpeg, que a imagem ja traz (os videos
# do frontend): o mesa-va-drivers ficava de fora, e no amdgpu a captura nao
# lia a tela (hwdownload: EPERM), com o painel em "Conectando" ate cair.
set -euo pipefail
[[ -x /opt/fliperos/go2rtc/go2rtc ]] || exit 0
dpkg-query -W -f='${Status}\n' mesa-va-drivers 2> /dev/null | grep -q 'ok installed' && exit 0
if ! DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends mesa-va-drivers; then
  echo "update 23: mesa-va-drivers did not install; the web panel's Live page offers to install it again" >&2
  exit 0
fi
# O servico testa o VA-API de novo ao subir (fliperos-stream config).
systemctl try-restart fliperos-stream.service 2> /dev/null || true
