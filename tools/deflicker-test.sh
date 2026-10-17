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
  libx11-dev libxrandr-dev xvfb libgl1-mesa-dri picom imagemagick python3-pygame xdotool > /dev/null
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

# O FPS para o painel web (config/fliperos-web): a camada grava a cada
# segundo "pid fps programa core filtrando", mesmo sem filtrar.
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_FPS_FILE=$b/fps FLIPEROS_DEFLICKER_APP=flycast \
  DEFLICKER_TEST_LOOP=3 $b/deflicker_test link > /dev/null
echo "== fps file: $(cat $b/fps)"
# O screenshot do painel web: com o pedido em $XDG_RUNTIME_DIR, o quadro
# (antes do filtro, de cima para baixo) vira fliperos-shot.ppm e o pedido sai.
mkdir -p $b/xdg
touch $b/xdg/fliperos-shot-request
run LD_PRELOAD=$b/libfliperos-deflicker.so XDG_RUNTIME_DIR=$b/xdg FLIPEROS_DEFLICKER_FORCE=1 \
  DEFLICKER_TEST_LOOP=1 $b/deflicker_test link > /dev/null
echo "== shot: $(head -c 15 $b/xdg/fliperos-shot.ppm | tr '\n' ' ')request: $(ls $b/xdg/fliperos-shot-request 2> /dev/null || echo gone)"
python3 -c "
d = open('$b/xdg/fliperos-shot.ppm', 'rb').read().split(b'\n', 3)[3]
print('== shot rows (red, top to bottom):', [d[y * 64 * 3] for y in range(16)])"

# A calibracao de cor (config/fliperos-color.c): a tabela de gama de 5
# pontos de cada canal e a matriz, com os padroes e com cada parametro.
bash config/fliperos-deflicker-build config/fliperos-color.c $b/fliperos-color
lut() {
  printf '%s\n' "$@" > $b/color.conf
  echo "== lut $*"
  $b/fliperos-color lut 5 --conf $b/color.conf
}
lut
lut color_brightness=10 color_contrast=150
lut color_gamma=200 color_red_gain=50 color_blue_offset=10
lut color_temperature=9300
lut color_saturation=0 color_hue=0
lut color_hue=180 color_saturation=999
# No X (o Xvfb): a tabela de gama de cada CRTC, se ele tiver.
printf 'color_gamma=150\n' > $b/color.conf
$b/fliperos-color x11 --conf $b/color.conf; echo "== x11 exit $?"
# Sem CTM, a saturacao e o matiz pela camada (color_ctm=sw), mesmo sem modo
# entrelacado; listras vermelhas: sem saturacao, o vermelho vira o cinza da
# luminancia dele (0.213 = 54).
printf 'color_ctm=sw\ncolor_saturation=0\ndeflicker=off\n' > $b/conf
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_CONF=$b/conf DEFLICKER_TEST_RED=1 $b/deflicker_test link
printf 'color_ctm=hw\ncolor_saturation=0\ndeflicker=off\n' > $b/conf
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_CONF=$b/conf DEFLICKER_TEST_RED=1 $b/deflicker_test link
printf 'color_saturation=0\n' > $b/color-live
run LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_CONF=/dev/null FLIPEROS_COLOR_FILE=$b/color-live \
  DEFLICKER_TEST_RED=1 $b/deflicker_test link
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

# O calibrador de cor (fliperos-setup/gui/color-calibrate.py) em 640x480:
# cada padrao de teste (em /out), as setas mudam o arquivo que a camada
# rele (a saturacao por software) e o Enter grava os valores.
cat > $b/table << 'EOF'
brightness|Brightness|-50|50|0|1|Moves the whole picture up or down.
saturation|Saturation|0|200|100|2|How strong the colours are.
EOF
printf 'color_brightness=0\ncolor_saturation=100\n' > $b/cal.conf
LD_PRELOAD=$b/libfliperos-deflicker.so FLIPEROS_COLOR_FILE=$b/cal.conf FLIPEROS_CONF=/dev/null \
  python3 fliperos-setup/gui/color-calibrate.py --table $b/table --conf $b/cal.conf --out $b/cal.out \
  --range output_csc --bin $b/fliperos-color 2> $b/cal.log &
sleep 4
for i in 1 2 3 4 5 6; do
  [ -d /out ] && import -window root /out/calibrate-$i.png 2> /dev/null
  xdotool key Right
  sleep 1
done
# Brilho +3, saturacao 0 (50 toques de 2): o arquivo muda na hora.
xdotool key Down Right Right Right Down
for i in $(seq 1 50); do xdotool key Left; done
sleep 2
echo "== calibrator file: $(tr '\n' ' ' < $b/cal.conf)"
xdotool key space
sleep 2
[ -d /out ] && import -window root /out/calibrate-saturation0.png 2> /dev/null
xdotool key Return
sleep 2
echo "== calibrator saved: $(tr '\n' ' ' < $b/cal.out 2> /dev/null)"
