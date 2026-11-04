#!/bin/sh
# Quatro Super Street Fighter II: The Tournament Battle ligados em corrente
# (cps2comm, MAME PR #9699), sem janela, num container: ficha e Start em cada
# um, e a tela de cada maquina gravada em PNG (12 por segundo) do comeco do
# torneio em diante. Saida: OUT/cab1..cab4/ssf2tb/NNNN.png e OUT/cabN.log.
#
#   docker run --rm -v ROMS:/roms:ro -v "$PWD/tools/link-tests:/t:ro" -v OUT:/out fliperos-linktest sh /t/ssf2tb-tournament.sh
#
# A corrente: a cabeca escuta e nao conecta; cada uma das outras conecta na
# anterior; a cauda nao escuta. A placa so liga o link com a Machine
# Configuration "Communication" em Enable (o .cfg, com os dois pontos na tag).
#
# Os quadros nascem em /tmp e so vao para OUT no fim: gravar direto numa pasta
# do Windows montada no container deixou as quatro a 1/10 da velocidade.
# Com a ficha no quadro 3600, a tela de entrada vem no PNG ~80, a chave do
# torneio (BATTLE 1, diferente em cada maquina) no ~300 e as lutas no ~390.
set -e
DEST=${OUT:-/out}
OUT=/tmp/ssf2tb
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy XDG_RUNTIME_DIR=/tmp
COIN=${COIN:-3600}                # o quadro da ficha: o boot com NVRAM nova demora
for n in 1 2 3 4; do
  d=$OUT/cab$n
  rm -rf "$d"; mkdir -p "$d/cfg" "$d/nvram"
  cat > "$d/cfg/ssf2tb.cfg" <<EOF
<?xml version="1.0"?>
<mameconfig version="10"><system name="ssf2tb"><input>
<port tag=":comm:CFG" type="CONFIG" mask="1" defvalue="0" value="1" />
</input></system></mameconfig>
EOF
  # Uma ficha, Start, e o soco para escolher o lutador (o mesmo em todas: o
  # cursor de cada maquina comeca num lutador diferente).
  cat > "$d/rec.lua" <<EOF
return {press = {{$COIN, "Coin 1"}, {$((COIN + 40)), "1 Player Start"}, {$((COIN + 400)), "P1 Button 1"},
                 {$((COIN + 460)), "P1 Button 1"}, {$((COIN + 520)), "P1 Button 1"}},
        shots = {$((COIN - 120)), $((COIN + 2300)), 5}, exit = $((COIN + 2350))}
EOF
done
run() {
  n=$1; shift
  d=$OUT/cab$n
  REC_FILE=$d/rec.lua mame ssf2tb -rompath /roms -video none -sound none -noswitchres -throttle \
    -cfg_directory "$d/cfg" -nvram_directory "$d/nvram" -snapshot_directory "$d" -snapname "%g/%i" \
    -autoboot_script /t/rec.lua "$@" > "$OUT/cab$n.log" 2>&1 &
}
run 1 -comm_localhost 0.0.0.0 -comm_localport 1234 -comm_remotehost ""
sleep 1
run 2 -comm_localhost 0.0.0.0 -comm_localport 1235 -comm_remotehost 127.0.0.1 -comm_remoteport 1234
sleep 1
run 3 -comm_localhost 0.0.0.0 -comm_localport 1236 -comm_remotehost 127.0.0.1 -comm_remoteport 1235
sleep 1
run 4 -comm_localhost "" -comm_remotehost 127.0.0.1 -comm_remoteport 1236
wait
mkdir -p "$DEST"
for n in 1 2 3 4; do
  echo "cab$n: $(ls "$OUT/cab$n/ssf2tb" 2>/dev/null | wc -l) frames"
  grep -i -E "nofield|error" "$OUT/cab$n.log" | head -3
  rm -rf "$DEST/cab$n"
  cp -r "$OUT/cab$n" "$OUT/cab$n.log" "$DEST/"
done
