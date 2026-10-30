#!/bin/sh
# O video de apresentacao do FliperOS (tools/video/README.md): grava as cenas
# e monta o video, tudo em Docker. A saida fica em .shots/video/out.
#
#   sh tools/video/render.sh images              as imagens Docker
#   sh tools/video/render.sh library IP          a biblioteca de amostra, do gabinete
#   sh tools/video/render.sh scenes [CENA]       as cenas do CRT (todas ou uma)
#   sh tools/video/render.sh web IP              o painel no tablet e o tubo (abre o SF2!)
#   sh tools/video/render.sh gifs [CENA]         as animacoes do site que nao sao o painel
#   sh tools/video/render.sh gifs-live IP        as animacoes do painel com o SF2 (abre o SF2!)
#   sh tools/video/render.sh compose [TRECHO]    o video final (ou so um trecho)
#   sh tools/video/render.sh all IP              tudo, em ordem
#
# FLIPEROS_USER e FLIPEROS_PASSWORD: o login do gabinete (fliperos/fliperos).
set -eu
cd "$(dirname "$0")/../.."
export MSYS_NO_PATHCONV=1
# pwd -W: o caminho do Windows no Git Bash (o Docker Desktop nao entende /c/...).
root=$(pwd -W 2> /dev/null || pwd)
work=.shots/video
mkdir -p "$work/clips" "$work/web" "$work/out"
w=$(cd "$work" && (pwd -W 2> /dev/null || pwd))
step=${1:-help}
arg=${2:-}
user=${FLIPEROS_USER:-fliperos}
pass=${FLIPEROS_PASSWORD:-fliperos}
opts="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=error"

run() {
  docker run --rm -v "$root:/repo:ro" -v "$root/fliperos-setup/gui:/g:ro" -v "$root/config:/config:ro" \
    -v "$root/tools/video:/t:ro" -v "$w:/v" "$@"
}

# cab "COMANDO": roda no gabinete, pelo ssh do container.
cab() {
  run fliperos-video sshpass -p "$pass" ssh $opts "$user@$cabinet" "$1"
}

need_cabinet() {
  cabinet=$arg
  [ -n "$cabinet" ] || { echo "Usage: render.sh $step CABINET_IP" >&2; exit 2; }
}

images() {
  docker build -q -t fliperos-guitest -f tools/Dockerfile.guitest tools
  docker build -q -t fliperos-video tools/video
  docker build -q -t fliperos-video-web -f tools/video/Dockerfile.web tools/video
}

# A biblioteca do frontend: jogos conhecidos com toda a midia (tela, capa,
# logo, marquee, video e informacao), copiados do gabinete.
library() {
  need_cabinet
  run fliperos-video sh -c "sshpass -p '$pass' scp $opts /t/pick.py /t/export.py '$user@$cabinet:/tmp/' &&
    sshpass -p '$pass' ssh $opts '$user@$cabinet' 'python3 /tmp/pick.py > /tmp/pick.txt && python3 /tmp/export.py' &&
    sshpass -p '$pass' scp $opts '$user@$cabinet:/tmp/demo.tar' /v/demo.tar"
}

# As cenas: as do Setup (def script) em tempo virtual, as do frontend
# (TIMELINE) em tempo real, com os videos dos jogos.
scenes() {
  for scene in tools/video/scenes/*.py; do
    name=$(basename "$scene" .py)
    [ -z "$arg" ] || [ "$arg" = "$name" ] || continue
    echo "== $name"
    if grep -q '^TIMELINE' "$scene"; then
      [ -f "$work/demo.tar" ] || { echo "No $work/demo.tar: run 'render.sh library IP' first." >&2; exit 1; }
      run fliperos-video bash /t/rig.sh /t/fe_rec.py "/v/clips/$name.mkv" "/t/scenes/$name.py"
    else
      run fliperos-video python3 /t/gui_rec.py "/v/clips/$name.mkv" "/t/scenes/$name.py"
    fi
  done
}

# O painel web no tablet e, ao mesmo tempo, a tela do gabinete (o go2rtc do
# painel, gravado no proprio gabinete). Abre o Street Fighter II no gabinete,
# mexe na saturacao (e volta ao valor de antes) e fecha o jogo.
web() {
  need_cabinet
  cab "rm -f /tmp/tube.mkv; nohup ffmpeg -nostdin -loglevel error -rtsp_transport tcp \
    -i rtsp://127.0.0.1:8554/cabinet60 -t 190 -an -c copy -y /tmp/tube.mkv > /tmp/tube.log 2>&1 < /dev/null &"
  sleep 2
  rm -rf "$work/web"
  mkdir -p "$work/web"
  run --shm-size=2g fliperos-video-web python3 /t/web_rec.py "http://$cabinet:8081" /v/web
  echo "Waiting for the tube recording to end..."
  # ([r]tsp: o shell que roda o pgrep nao se acha na propria linha.)
  while cab "pgrep -f '[r]tsp://127.0.0.1:8554/cabinet60 -t 190' > /dev/null"; do sleep 5; done
  run fliperos-video sshpass -p "$pass" scp $opts "$user@$cabinet:/tmp/tube.mkv" /v/clips/tube.mkv
  run fliperos-video python3 /t/sync.py
}

# As animacoes do site (website/public/screenshots/anim) que o frontend de
# verdade grava sozinho: uma cena por arquivo de tools/video/gifs, no mesmo
# formato das cenas do video (TIMELINE), e a saida em .shots/video/gifs.
gifs() {
  [ -f "$work/demo.tar" ] || { echo "No $work/demo.tar: run 'render.sh library IP' first." >&2; exit 1; }
  mkdir -p "$work/gifs"
  for scene in tools/video/gifs/*.py; do
    name=$(basename "$scene" .py)
    [ -z "$arg" ] || [ "$arg" = "$name" ] || continue
    echo "== $name"
    run fliperos-video bash /t/rig.sh /t/fe_rec.py "/v/gifs/$name.mkv" "/t/gifs/$name.py"
  done
}

# O painel web no desktop, com o Street Fighter II rodando e os botoes sendo
# apertados (controles virtuais, vpad.py): as animacoes do site em
# .shots/video/gifs/web-*.webp. Mexe no gabinete: abre o SF2 (fecha no fim) e
# solta os dois Xbox 360 do driver enquanto grava; sempre os religa.
gifs_live() {
  need_cabinet
  sudo_cab() { cab "echo '$pass' | sudo -S -p '' bash /tmp/pads.sh $1"; }
  run fliperos-video sshpass -p "$pass" scp $opts /t/vpad.py /t/pads.sh "$user@$cabinet:/tmp/"
  trap 'sudo_cab bind' EXIT
  sudo_cab unbind
  rm -rf "$work/webgifs"
  mkdir -p "$work/webgifs" "$work/gifs"
  # STOP_AT=marca e SKIP_PLAY=1 (o jogo ja aberto) servem para ensaiar.
  run --shm-size=2g -e FLIPEROS_USER="$user" -e FLIPEROS_PASSWORD="$pass" -e STOP_AT="${STOP_AT:-}" -e SKIP_PLAY="${SKIP_PLAY:-}" \
    fliperos-video-web \
    python3 /t/web_gifs.py "http://$cabinet:8081" /v/webgifs "$cabinet" || echo "the recording failed" >&2
  sudo_cab bind
  trap - EXIT
  run fliperos-video python3 /t/web_gifs_cut.py /v/webgifs /v/gifs
}

compose() {
  run -e ONLY="$arg" fliperos-video python3 /t/compose.py
  [ -n "$arg" ] || ls -la "$work/out/"fliperos-apresentacao*
}

case $step in
  images) images ;;
  library) library ;;
  scenes) scenes ;;
  web) web ;;
  gifs) gifs ;;
  gifs-live) gifs_live ;;
  compose) compose ;;
  all)
    need_cabinet
    images
    library
    arg=""
    scenes
    arg=$cabinet
    web
    arg=""
    compose
    ;;
  *) sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
