#!/bin/sh
# O filtro de flicker da camada do Vulkan (config/fliperos-vkfps.c) num Xvfb com
# o lavapipe: confere os tipos contra os cabecalhos de verdade, os shaders contra
# a fonte, e as listras de uma linha em cada nivel, com as camadas de validacao
# do Vulkan olhando. Roda num Ubuntu 24.04:
#
#   docker run --rm -v "$PWD:/w:ro" -w /w ubuntu:24.04 sh tools/vkfps-test.sh
#
# Grava a biblioteca em /out se a pasta existir (para levar ao gabinete).
set -eu
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq --no-install-recommends gcc libc6-dev pkg-config libdrm-dev libvulkan-dev libx11-dev \
  mesa-vulkan-drivers vulkan-validationlayers glslang-tools xvfb python3 > /dev/null
b=/tmp/vkfps
mkdir -p $b

echo "== os tipos contra vulkan_core.h"
# shellcheck disable=SC2046 # as opcoes do pkg-config, uma por palavra
gcc -O0 -Wall -fsyntax-only -DFLIPEROS_VK_CHECK $(pkg-config --cflags libdrm) config/fliperos-vkfps.c

echo "== os shaders contra a fonte"
python3 - config/fliperos-vkfps.c $b <<'PY'
import re, subprocess, sys
source, out = sys.argv[1:3]
text = open(source).read()
comment = text[text.index(' * #version 450'):text.index(' */\nstatic const uint32_t vert_spv')]
lines = [re.sub(r'^ \* ?', '', line) for line in comment.splitlines()]
glsl = '\n'.join(lines).split('\n--\n')
for name, stage, src in (('vert', 'vert', glsl[0]), ('frag', 'frag', glsl[1])):
    path = '%s/%s.%s' % (out, name, stage)
    open(path, 'w').write(src + '\n')
    subprocess.run(['glslangValidator', '-V', '--quiet', '-o', path + '.spv', path], check=True)
    built = open(path + '.spv', 'rb').read()
    words = [int.from_bytes(built[i:i + 4], 'little') for i in range(0, len(built), 4)]
    m = re.search(r'static const uint32_t %s_spv\[\] = \{(.*?)\};' % name, text, re.S)
    mine = [int(w, 16) for w in re.findall(r'0x[0-9a-fA-F]+', m.group(1))]
    # O gerador (a palavra 2) muda de versao para versao do glslang.
    words[2] = mine[2]
    assert words == mine, '%s: SPIR-V differs from the source' % name
    print(name, len(mine), 'words ok')
PY

bash config/fliperos-deflicker-build config/fliperos-vkfps.c $b/libfliperos-vkfps.so
[ -d /out ] && cp $b/libfliperos-vkfps.so /out/
gcc -O2 -Wall -o $b/vkfps_test tests/vkfps_test.c -lvulkan -lX11

# A camada instalada como na imagem.
install -D $b/libfliperos-vkfps.so /usr/local/lib/fliperos/libfliperos-vkfps.so
install -Dm644 config/fliperos-vkfps.json /usr/share/vulkan/implicit_layer.d/fliperos-vkfps.json

Xvfb :9 -screen 0 640x480x24 > /dev/null 2>&1 &
sleep 2
export DISPLAY=:9 FLIPEROS_DEFLICKER_QUIET=1 FLIPEROS_CONF=/nonexistent
fail=0
run() {
  # run NOME CLARA ESCURA VARIAVEIS...
  name=$1 light=$2 dark=$3
  shift 3
  log=$b/$name.log
  if env "$@" VK_LOADER_LAYERS_DISABLE= VK_INSTANCE_LAYERS=VK_LAYER_KHRONOS_validation $b/vkfps_test "$light" "$dark" > "$log" 2>&1; then
    status=ok
  else
    status=FAIL
    fail=1
  fi
  errors=$(grep -c 'Validation Error' "$log" || true)
  [ "$errors" = 0 ] || { status="FAIL ($errors validation errors)"; fail=1; }
  echo "$name: $status: $(grep '^lines' "$log" || tail -1 "$log")"
  [ "$status" = ok ] || grep -m5 -E 'Validation Error|^line ' "$log" | cut -c1-500
}
# Sem a camada, e com ela e sem modo entrelacado: nada muda.
run sem-camada 255 0
run sem-entrelacado 255 0 FLIPEROS_VK_FPS=1
run off 255 0 FLIPEROS_VK_FPS=1 FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER=off
# Linha clara em cima de escura e vice-versa: os pesos de cada nivel.
run medium 127 127 FLIPEROS_VK_FPS=1 FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER_DEBUG=1
run light 178 76 FLIPEROS_VK_FPS=1 FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER=light
run strong 86 168 FLIPEROS_VK_FPS=1 FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_DEFLICKER=strong
# O nivel do programa no fliperos.conf, e o FPS com a coluna do filtro.
printf 'deflicker=off\ndeflicker_vkfps_test=light\n' > $b/conf
run conf 178 76 FLIPEROS_VK_FPS=1 FLIPEROS_DEFLICKER_FORCE=1 FLIPEROS_CONF=$b/conf FLIPEROS_FPS_FILE=$b/fps
echo "fps: $(cat $b/fps 2> /dev/null || echo none)"
case $(cat $b/fps 2> /dev/null) in
  *" vkfps_test - 1") ;;
  *) echo "FPS line without the filter column"; fail=1 ;;
esac
exit $fail
