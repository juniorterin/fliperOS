#!/bin/sh
# Compila o config/fliperos-deflicker.c e o testa num Xvfb com o Mesa por
# software (llvmpipe): listras de uma linha, com e sem o filtro, pela libGL
# ligada e por dlopen/dlsym (como o SDL), em contexto de compatibilidade e
# core. Roda num Ubuntu 24.04:
#
#   docker run --rm -v "$PWD:/w:ro" -w /w ubuntu:24.04 sh tools/deflicker-test.sh
#
# Grava a biblioteca em /out se a pasta existir (para levar ao gabinete).
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends gcc libc6-dev pkg-config libdrm-dev libgl-dev libegl-dev \
  libx11-dev xvfb libgl1-mesa-dri picom imagemagick > /dev/null
b=/tmp/deflicker
mkdir -p $b
bash config/fliperos-deflicker-build config/fliperos-deflicker.c $b/libfliperos-deflicker.so
gcc -O2 -Wall -o $b/deflicker_test tests/deflicker_test.c -lGL -lEGL -lX11 -ldl
[ -d /out ] && cp $b/libfliperos-deflicker.so /out/
Xvfb :9 -screen 0 320x240x24 > /dev/null 2>&1 &
sleep 2
export DISPLAY=:9 LIBGL_ALWAYS_SOFTWARE=1
run() {
  echo "== $*"
  env "$@"
}
run $b/deflicker_test link
for mode in link dlsym; do
  for profile in compat core; do
    run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER_DEBUG=1 \
      $b/deflicker_test $mode $profile
  done
done
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER=light $b/deflicker_test link
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER=off $b/deflicker_test link
# O caminho do RetroArch: EGL com OpenGL core.
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER_DEBUG=1 $b/deflicker_test egl
# Sem modo entrelacado (aqui nao ha DRM): nada muda.
run LD_PRELOAD=$b/libfliperos-deflicker.so $b/deflicker_test link
# O desktop: o picom com o shader do config/fliperos-desktop-deflicker (sem a
# camada no programa), e a tela que o compositor pintou (import). Com o
# shader, as listras saem misturadas; sem o picom, puras.
bash config/fliperos-desktop-deflicker --shader $b/desktop.glsl
DEFLICKER_TEST_HOLD=30 $b/deflicker_test link > /dev/null &
sleep 2
screen_rows() {
  import -window root $b/root.png 2> /dev/null &&
    convert $b/root.png -crop 1x16+32+0 -depth 8 txt:- | sed -n '2,$p' | awk '{ printf " %s", $3 } END { print "" }'
}
picom --backend glx --window-shader-fg $b/desktop.glsl > $b/picom.log 2>&1 &
sleep 3
echo "== desktop, picom with the shader (top to bottom):$(screen_rows)"
pkill -x picom
sleep 1
echo "== desktop, no picom:$(screen_rows)"
