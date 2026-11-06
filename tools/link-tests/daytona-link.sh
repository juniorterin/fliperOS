#!/bin/sh
# Quatro Daytona USA ligados em anel (m2comm do MAME), sem janela, num
# container, para a animacao do site: o carro 1 e o master, os outros sao
# escravos com o numero do carro. Ficha e Start em cada um, o acelerador no
# fundo na corrida, e a tela de cada maquina gravada em PNG. Saida:
# OUT/cab1..cabN/daytona/NNNN.png, OUT/cabN.log (as linhas SHOT dizem o quadro
# de cada PNG) e OUT/nvram/carN (a NVRAM de cada carro, feita uma vez).
#
#   docker run --rm -v ROMS:/roms:ro -v "$PWD/tools/link-tests:/t:ro" -v OUT:/out fliperos-linktest sh /t/daytona-link.sh
#
# ROMS: daytona.zip e segabill.zip. A NVRAM de um escravo vem do menu de teste
# (como em docs/research/linked-cabinets.md): Service Mode, Green x9, Start
# (Game System), Green x8 (Link ID), Blue x2 (Slave), Red, Yellow x(N-1) (o
# carro), Red x7 (Exit), Start, Service Mode desligado. O master usa a NVRAM
# nova (Link ID Master, carro 1).
#
# O anel: cada um escuta na porta 15110+N e conecta no seguinte. O master sobe
# primeiro: ele espera em "Network checking" sem limite e, 4 s depois de achar
# o vizinho, manda o pacote de contagem a cada quadro ate ele dar a volta. Os
# escravos sobem logo depois, juntos: um escravo que espera demais mostra
# CANCELLED e desliga a placa, e quem ja estava ligado fica esperando o
# quadro dele para sempre (-comm_framesync faz cada um esperar o VSYNC do
# master a cada quadro). Com o link pronto as quatro andam juntas, e o rec.lua
# conta os quadros a partir dele (o byte 0 da memoria do link em 1 e o 3 com
# o numero de gabinetes, por 30 quadros: o teste de memoria do boot tambem
# escreve ali), entao o PNG k de todas e o mesmo instante. -verbose poe no
# log as mensagens M2COMM (listen, connect, link established - id N of M).
# LIMIT: os segundos ate desistir de uma maquina travada.
set -e
DEST=${OUT:-/out}
OUT=/tmp/daytona
CARS=${CARS:-4}
EVERY=${EVERY:-5}                 # um PNG a cada EVERY quadros (11,5 por segundo; 30 para ver o roteiro)
FROM=${FROM:-1}                   # o primeiro quadro gravado, contado do link pronto
END=${END:-5000}                  # o ultimo quadro
COIN=${COIN:-600}                 # a ficha, contada do link pronto
STARTS=${STARTS:-"640 1240 1840"} # os Start: entrar, a pista, o cambio
ACC=${ACC:-2400}                  # o acelerador no fundo daqui em diante
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy XDG_RUNTIME_DIR=/tmp
MAME="mame daytona -rompath /roms -video none -sound none -noswitchres -nothrottle"
rm -rf "$OUT"; mkdir -p "$OUT" "$DEST/nvram"

slave_nvram() {
  n=$1
  d=$OUT/nv$n
  mkdir -p "$d/nvram"
  f=930
  press() { k=0; while [ $k -lt "$2" ]; do echo "{$f, 'press', '$1'},"; f=$((f + 24)); k=$((k + 1)); done; }
  {
    echo "return {{$f, 'on', 'Service Mode'},"
    f=$((f + 120))
    press 'VR4 (Green)' 9; press '1 Player Start' 1; f=$((f + 60))
    press 'VR4 (Green)' 8; press 'VR2 (Blue)' 2; press 'VR1 (Red)' 1; press 'VR3 (Yellow)' $((n - 1))
    echo "{$f, 'shot'},"
    press 'VR1 (Red)' 7; press '1 Player Start' 1; f=$((f + 60))
    echo "{$f, 'off', 'Service Mode'},"
    echo "{$((f + 1500)), 'shot'}, {$((f + 1560)), 'exit'}}"
  } > "$d/seq.lua"
  SEQ_FILE=$d/seq.lua $MAME -nvram_directory "$d/nvram" -snapshot_directory "$d" -snapname "car$n-%i" \
    -autoboot_script /t/seq.lua > "$d.log" 2>&1
  rm -rf "$DEST/nvram/car$n"
  cp -r "$d/nvram" "$DEST/nvram/car$n"
  cp "$d"/car$n-*.png "$DEST/nvram/" 2>/dev/null || true
  echo "car $n: nvram $(ls "$d/nvram/daytona" | tr '\n' ' ')"
}

n=2
while [ $n -le "$CARS" ]; do
  [ -d "$DEST/nvram/car$n" ] || slave_nvram $n &
  n=$((n + 1))
done
wait

for n in $(seq 1 "$CARS"); do
  d=$OUT/cab$n
  mkdir -p "$d/nvram"
  [ $n = 1 ] || cp -r "$DEST/nvram/car$n/." "$d/nvram/"
  {
    echo "return {anchor = {cpu = ':maincpu', bytes = {{0x01a00000, 1}, {0x01a00003, $CARS}}, frames = 30}, preshots = 120,"
    echo "  press = {{$COIN, 'Coin 1'}"
    for s in $STARTS; do echo "    , {$s, '1 Player Start'}"; done
    echo "  }, set = {{$ACC, 'P1 Pedal 1', 0xe0}},"
    echo "  shots = {$FROM, $END, $EVERY}, exit = $END}"
  } > "$d/rec.lua"
done

run() {
  n=$1
  next=$((n % CARS + 1))
  d=$OUT/cab$n
  REC_FILE=$d/rec.lua timeout "${LIMIT:-1800}" $MAME -verbose -comm_framesync -nvram_directory "$d/nvram" -snapshot_directory "$d" -snapname "%g/%i" \
    -comm_localhost 0.0.0.0 -comm_localport $((15110 + n)) -comm_remotehost 127.0.0.1 -comm_remoteport $((15110 + next)) \
    -autoboot_script /t/rec.lua > "$OUT/cab$n.log" 2>&1 &
}
run 1                                   # o master primeiro, os escravos juntos logo depois
sleep 2
for n in $(seq 2 "$CARS"); do run $n; done
wait
for n in $(seq 1 "$CARS"); do
  echo "cab$n: $(ls "$OUT/cab$n/daytona" 2>/dev/null | wc -l) frames, $(grep ANCHOR "$OUT/cab$n.log")"
  grep -i -E "nofield|error" "$OUT/cab$n.log" | head -3
  rm -rf "$DEST/cab$n"
  cp -r "$OUT/cab$n" "$OUT/cab$n.log" "$DEST/"
done
