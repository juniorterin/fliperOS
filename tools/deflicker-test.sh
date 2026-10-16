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
  libx11-dev xvfb libgl1-mesa-dri picom imagemagick python3-pygame xdotool > /dev/null
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
# O nivel de cada programa e de cada core (fliperos.conf): o do programa
# (strong) passa o de todos (light); o nome da tabela do fliperos-x11-run
# (FLIPEROS_DEFLICKER_APP) passa o do processo; o core aberto passa o do
# programa; o arquivo do preview passa tudo.
printf 'deflicker=light\ndeflicker_deflicker_test=strong\ndeflicker_flycast=off\ndeflicker_mame2010=light\n' > $b/conf
echo 'void retro_init(void) {}' > $b/core.c
gcc -shared -fPIC -o $b/mame2010_libretro.so $b/core.c
echo strong > $b/level
pre="LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER_DEBUG=1 FLIPEROS_CONF=$b/conf"
run $pre $b/deflicker_test link
run $pre FLIPEROS_DEFLICKER_APP=flycast $b/deflicker_test link
run $pre DEFLICKER_TEST_DLOPEN=$b/mame2010_libretro.so $b/deflicker_test link
run $pre FLIPEROS_DEFLICKER_APP=flycast FLIPEROS_DEFLICKER_FILE=$b/level $b/deflicker_test link
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
pkill -f deflicker_test || true

# O preview do Setup (fliperos-setup/gui/flicker-preview.py) numa tela de
# 640x480: o quadro do SDL passa pela camada (o log "filtering"), a seta
# troca o nivel no arquivo, que a camada rele, e o Enter grava o escolhido.
# As listras de cima (uma linha sim, outra nao) na tela, a cada nivel.
pkill Xvfb || true
sleep 1
Xvfb :9 -screen 0 640x480x24 > /dev/null 2>&1 &
sleep 2
stripe_rows() {
  import -window root $b/preview.png 2> /dev/null &&
    convert $b/preview.png -crop 1x6+100+60 -depth 8 txt:- | sed -n '2,$p' | awk '{ printf " %s", $3 } END { print "" }'
}
cp $b/preview.png /out/ 2> /dev/null || true
LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER_DEBUG=1 \
  FLIPEROS_DEFLICKER_FILE=$b/preview-level python3 fliperos-setup/gui/flicker-preview.py \
  --level medium --out $b/preview-out --title "Flycast" 2> $b/preview.log &
sleep 4
echo "== preview, medium:$(stripe_rows)"
[ -d /out ] && cp $b/preview.png /out/preview-medium.png
xdotool key Left
sleep 2
echo "== preview, light:$(stripe_rows)"
xdotool key Left
sleep 2
echo "== preview, off:$(stripe_rows)"
[ -d /out ] && cp $b/preview.png /out/preview-off.png
xdotool key Right Right Right
sleep 2
echo "== preview, strong:$(stripe_rows)"
xdotool key Return
sleep 2
echo "== preview level file: $(cat $b/preview-level), chosen: $(cat $b/preview-out 2> /dev/null)"
grep -m1 filtering $b/preview.log || { echo "the preview frame did not go through the layer"; cat $b/preview.log; }
