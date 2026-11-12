# shellcheck shell=bash
# Setup > Joysticks > Bluetooth: os controles Bluetooth pelo
# config/fliperos-bluetooth (o bluetoothctl do BlueZ): parear (um ou todos
# os que estiverem em modo de pareamento, como o Batocera), conectar,
# desconectar, esquecer e ligar ou desligar o adaptador. Pareado, o
# controle e de confianca: volta sozinho a cada boot, ao apertar o botao dele.

BLUETOOTH=${BLUETOOTH:-/opt/fliperos/bin/fliperos-bluetooth}
BLUETOOTH_SCAN=${BLUETOOTH_SCAN:-15}
BLUETOOTH_AUTOPAIR=${BLUETOOTH_AUTOPAIR:-30}
BLUETOOTH_SYSFS=${BLUETOOTH_SYSFS:-/sys/class/bluetooth}

# bluetooth_present: ha um adaptador Bluetooth (o hciN do kernel, de um
# dongle USB ou da placa-mae). Sem ele o Setup nem mostra o Bluetooth.
bluetooth_present() {
  compgen -G "$BLUETOOTH_SYSFS/hci*" > /dev/null
}

# bluetooth_status imprime as linhas "chave=valor" do fliperos-bluetooth
# status (installed, adapter, powered, paired, connected).
bluetooth_status() {
  "$BLUETOOTH" status 2>> "$FLIPEROS_LOG" || echo "installed=no"
}

# bluetooth_field CHAVE STATUS: o valor de uma linha do status.
bluetooth_field() {
  sed -n "s/^$1=//p" <<< "$2" | head -n 1
}

# bluetooth_summary STATUS: a linha do menu ("Adapter: hci0 (on). Paired: 2,
# connected: 1.").
bluetooth_summary() {
  local status=$1 powered=off
  [[ $(bluetooth_field powered "$status") == yes ]] && powered=on
  printf 'Adapter: %s (%s). Paired: %s, connected: %s.\n' "$(bluetooth_field adapter "$status")" "$powered" \
    "$(bluetooth_field paired "$status")" "$(bluetooth_field connected "$status")"
}

# bluetooth_scan SEGUNDOS: os aparelhos achados, "MAC|NOME|ICONE|pareado|conectado".
bluetooth_scan() {
  "$BLUETOOTH" scan "$1" 2>> "$FLIPEROS_LOG"
}

# bluetooth_devices: os pareados, no mesmo formato.
bluetooth_devices() {
  "$BLUETOOTH" devices 2>> "$FLIPEROS_LOG"
}

# bluetooth_pair MAC: pareia, confia e conecta; imprime o resultado.
bluetooth_pair() {
  "$BLUETOOTH" pair "$1" 2>> "$FLIPEROS_LOG"
}

# bluetooth_autopair SEGUNDOS: pareia todo controle em modo de pareamento
# que aparecer nesse tempo; imprime "MAC|NOME" de cada um.
bluetooth_autopair() {
  "$BLUETOOTH" autopair "$1" 2>> "$FLIPEROS_LOG"
}

# bluetooth_do connect|disconnect|remove|power MAC|on|off
bluetooth_do() {
  "$BLUETOOTH" "$1" "$2" >> "$FLIPEROS_LOG" 2>&1
}

# bluetooth_label LINHA: o rotulo de um aparelho no menu ("8BitDo Pro 2
# (controller, connected)").
bluetooth_label() {
  local mac name icon paired connected notes=()
  IFS='|' read -r mac name icon paired connected <<< "$1"
  [[ $icon == input-gaming || $icon == input-joystick ]] && notes+=(controller)
  [[ $connected == yes ]] && notes+=(connected)
  [[ $paired == yes && $connected != yes ]] && notes+=(paired)
  if ((${#notes[@]})); then
    printf '%s (%s)\n' "$name" "$(IFS=,; echo "${notes[*]}" | sed 's/,/, /g')"
  else
    printf '%s\n' "$name"
  fi
}
