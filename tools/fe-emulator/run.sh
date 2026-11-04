#!/bin/sh
# O emulador do frontend do FliperOS: o fliperos-frontend do repositorio num
# container, visto no navegador (docs/wiki/Frontend-emulator.md).
#
#   sh tools/fe-emulator/run.sh          abre (cria a imagem na primeira vez)
#   sh tools/fe-emulator/run.sh reset    apaga a pasta pessoal de mentira e abre
#   sh tools/fe-emulator/run.sh stop     fecha
#   sh tools/fe-emulator/run.sh log      o que os gabinetes da rede abriram (Ctrl+C sai)
#
# FE_EMU_PORT (6080) e a porta do navegador; FE_EMU_SIZE (960x720) o tamanho
# da tela. O frontend e lido do repositorio a cada abertura: mudou o codigo,
# feche o frontend (Esc na lista) e ele abre de novo ja com a mudanca.
set -eu
cd "$(dirname "$0")/../.."
# pwd -W: o caminho do Windows no Git Bash (o Docker Desktop nao entende /c/...).
root=$(pwd -W 2> /dev/null || pwd)
port=${FE_EMU_PORT:-6080}
name=fliperos-fe-emulator
url="http://localhost:$port/vnc.html?autoconnect=1&resize=scale"

if [ "${1:-}" = log ]; then
  exec docker logs -f $name 2>&1 | grep --line-buffered "fe-emulator:"
fi
docker rm -f $name > /dev/null 2>&1 || true
case ${1:-} in
  stop) exit 0 ;;
  reset) docker volume rm $name-home > /dev/null 2>&1 || true ;;
esac

docker build -q -t $name tools/fe-emulator > /dev/null
demo=
[ -s .shots/video/demo.tar ] && demo="-v $root/.shots/video/demo.tar:/demo.tar:ro"
# A 55436/udp em todas as interfaces: o broadcast da presenca dos gabinetes
# chega da rede (o Windows pode pedir para liberar o Docker no firewall).
# shellcheck disable=SC2086
MSYS_NO_PATHCONV=1 docker run -d --name $name -p "127.0.0.1:$port:6080" -p 55436:55436/udp \
  -e FE_EMU_PORT="$port" -e FE_EMU_SIZE="${FE_EMU_SIZE:-960x720}" \
  -v "$root/fliperos-setup/gui:/g:ro" -v "$root/config:/config:ro" $demo \
  -v $name-home:/emu-home $name > /dev/null

echo "Abrindo... (a primeira vez com a biblioteca de amostra leva ~1 min)"
until docker logs $name 2>&1 | grep -q "fe-emulator: pronto"; do
  if [ "$(docker inspect -f '{{.State.Running}}' $name)" != true ]; then
    docker logs $name; exit 1
  fi
  sleep 1
done
echo "Frontend em $url"
case $(uname -s) in
  MINGW*|MSYS*|CYGWIN*) start "" "$url" ;;
  Darwin) open "$url" ;;
  *) xdg-open "$url" > /dev/null 2>&1 || true ;;
esac
