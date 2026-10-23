# shellcheck shell=bash
# Setup > System > Services: o que sobe com o computador. Cada servico fica
# em um de tres estados:
#   boot   sobe no boot (o "enabled" do systemd);
#   after  sobe uns 40 s depois do boot, com o jogo ou o frontend ja na tela
#          (config/fliperos-services-late.timer roda --services-late): o boot
#          chega antes ao que importa;
#   off    nao sobe.
# /etc/fliperos/services.conf guarda "chave=estado"; sem linha, o estado e o
# que o systemd (ou o NetworkManager, no Wi-Fi) diz agora: boot ou off.

SERVICES_CONF=${SERVICES_CONF:-$FLIPEROS_ETC/services.conf}
# O estado dos radios que o NetworkManager le ao subir.
NM_STATE=${NM_STATE:-/var/lib/NetworkManager/NetworkManager.state}
SERVICE_STATES=(boot after off)

# services_table imprime "chave|rotulo|units|ajuda". "radio:wifi" e o radio
# do Wi-Fi do NetworkManager: o NetworkManager mesmo nunca e desligado, e ele
# que liga o cabo. Um .socket so e desligado junto (a ativacao por socket
# subiria o servico na primeira conexao); quem sobe e o .service. O Pixelcade
# e o ZeDMD ficam fora: o udev os sobe quando o aparelho aparece.
services_table() {
  cat << 'EOF'
ssh|SSH|ssh.service ssh.socket|The terminal of this computer from another one (PuTTY, ssh, WinSCP).
samba|Network share|smbd.service nmbd.service|The FliperOS folder on the network, for Windows and other computers.
avahi|fliperos.local|avahi-daemon.service avahi-daemon.socket|Find this computer on the network by the name fliperos.local.
wifi|Wi-Fi|radio:wifi|The Wi-Fi radio. The network cable works either way.
netwait|Wait for network|NetworkManager-wait-online.service|The boot waits for the network to come up. Off: it goes on without it.
downloader|Downloader|fliperos-transmission.service|The torrents of Setup > Games > Downloader, in the background.
web|Web panel|fliperos-web.service|This cabinet in a browser on the same network: http://fliperos.local (user and password of Setup > System > Password).
stream|Live screen|fliperos-stream.service|The cabinet screen live in the web panel (installed in Setup > System > Extras > Live screen).
EOF
}

# A tela ao vivo so aparece na tabela depois de instalada (o go2rtc vem do
# Setup > System > Extras; o .service ja vem na imagem).
STREAM_GO2RTC=${STREAM_GO2RTC:-/opt/fliperos/go2rtc/go2rtc}

# services_minimal_state CHAVE: o estado do servico no modo jogo. Esperar a
# rede depois do boot nao serve a nada: desligado.
services_minimal_state() {
  [[ $1 == netwait ]] && echo off || echo after
}

# services_field CHAVE CAMPO (2 rotulo, 3 units, 4 ajuda).
services_field() {
  services_table | awk -F'|' -v k="$1" -v f="$2" '$1 == k { print $f; exit }'
}

# services_units CHAVE [service]: os units que existem neste sistema (com
# "service", so os .service: os que sobem).
services_units() {
  local unit
  for unit in $(services_field "$1" 3); do
    [[ $unit == radio:* ]] && continue
    [[ ${2:-} == service && $unit != *.service ]] && continue
    [[ -n $(systemctl list-unit-files --no-legend "$unit" 2> /dev/null) ]] && printf '%s\n' "$unit"
  done
  return 0
}

# services_present CHAVE: o servico existe aqui (o Wi-Fi, com o nmcli).
services_present() {
  [[ $1 != stream || -x $STREAM_GO2RTC ]] || return 1
  if [[ $(services_field "$1" 3) == radio:* ]]; then
    have nmcli
  else
    [[ -n $(services_units "$1" service) ]]
  fi
}

# services_state CHAVE imprime boot, after ou off.
services_state() {
  local key=$1 saved unit
  saved=$(sed -n "s/^$key=//p" "$SERVICES_CONF" 2> /dev/null | tail -n 1)
  case $saved in
    boot | after | off)
      printf '%s\n' "$saved"
      return 0
      ;;
  esac
  if [[ $(services_field "$key" 3) == radio:* ]]; then
    [[ $(nmcli radio wifi 2> /dev/null) == enabled ]] && echo boot || echo off
    return 0
  fi
  unit=$(services_units "$key" service | head -n 1)
  [[ -n $unit && $(systemctl is-enabled "$unit" 2> /dev/null) == enabled ]] && echo boot || echo off
}

# services_rows imprime "chave|rotulo|estado|ajuda" dos servicos que existem
# aqui, no formato do ui_grid.
services_rows() {
  local key label help
  while IFS='|' read -r key label _ help; do
    services_present "$key" && printf '%s|%s|%s|%s\n' "$key" "$label" "$(services_state "$key")" "$help"
  done < <(services_table)
  return 0
}

# services_apply CHAVE ESTADO poe o servico no estado, agora e no boot.
services_apply() {
  local key=$1 state=$2 rc=0
  local -a all=() up=()
  if [[ $(services_field "$key" 3) == radio:wifi ]]; then
    # O "after" desliga o radio so no proximo boot (services_boot): agora ele
    # fica como esta.
    case $state in
      boot) nmcli radio wifi on >> "$FLIPEROS_LOG" 2>&1 || rc=1 ;;
      off) nmcli radio wifi off >> "$FLIPEROS_LOG" 2>&1 || rc=1 ;;
    esac
    return "$rc"
  fi
  mapfile -t all < <(services_units "$key")
  mapfile -t up < <(services_units "$key" service)
  ((${#all[@]})) || return 1
  case $state in
    boot) systemctl enable --now "${up[@]}" >> "$FLIPEROS_LOG" 2>&1 || rc=1 ;;
    after) systemctl disable "${all[@]}" >> "$FLIPEROS_LOG" 2>&1 || rc=1 ;;
    off) systemctl disable --now "${all[@]}" >> "$FLIPEROS_LOG" 2>&1 || rc=1 ;;
    *) return 1 ;;
  esac
  return "$rc"
}

# services_set CHAVE ESTADO grava e aplica.
services_set() {
  local key=$1 state=$2 tmp
  [[ " ${SERVICE_STATES[*]} " == *" $state "* && -n $(services_field "$key" 1) ]] || return 1
  mkdir -p "$(dirname "$SERVICES_CONF")" || return 1
  tmp=$(mktemp "$SERVICES_CONF.XXXXXX") || return 1
  grep -v "^$key=" "$SERVICES_CONF" 2> /dev/null > "$tmp"
  printf '%s=%s\n' "$key" "$state" >> "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$SERVICES_CONF" || return 1
  log_info "servico $key: $state"
  services_apply "$key" "$state"
}

# services_save "chave=estado,..." (a resposta do ui_grid) grava os que
# mudaram. Imprime os rotulos dos que falharam.
services_save() {
  local pair key state
  local -a pairs
  IFS=',' read -ra pairs <<< "$1"
  for pair in "${pairs[@]}"; do
    key=${pair%%=*} state=${pair#*=}
    [[ $(services_state "$key") == "$state" ]] && continue
    services_set "$key" "$state" || services_field "$key" 2
  done
  return 0
}

# services_minimal tira do boot todo servico que sobe nele (o jogo direto no
# boot: Setup > Games > Frontend): "after", ou "off" na espera pela rede.
# Imprime os rotulos dos que mudaram.
services_minimal() {
  local key label
  while IFS='|' read -r key label _; do
    services_present "$key" || continue
    [[ $(services_state "$key") == boot ]] || continue
    services_set "$key" "$(services_minimal_state "$key")" && printf '%s\n' "$label"
  done < <(services_table)
  return 0
}

# services_boot (fliperos-services.service, antes do NetworkManager): o
# Wi-Fi em "after" ou "off" comeca desligado. O NetworkManager guarda o
# estado do radio entre os boots: ligado pelo --services-late, voltaria
# ligado.
services_boot() {
  local state
  state=$(sed -n 's/^wifi=//p' "$SERVICES_CONF" 2> /dev/null | tail -n 1)
  [[ $state == after || $state == off ]] || return 0
  mkdir -p "$(dirname "$NM_STATE")"
  if grep -q '^WirelessEnabled=' "$NM_STATE" 2> /dev/null; then
    sed -i 's/^WirelessEnabled=.*/WirelessEnabled=false/' "$NM_STATE"
  elif grep -q '^\[main\]' "$NM_STATE" 2> /dev/null; then
    sed -i '/^\[main\]/a WirelessEnabled=false' "$NM_STATE"
  else
    printf '[main]\nWirelessEnabled=false\n' >> "$NM_STATE"
  fi
  log_info "servicos: Wi-Fi desligado no boot ($state)"
}

# services_late (fliperos-services-late.timer, uns 40 s depois do boot):
# sobe os servicos em "after".
services_late() {
  local key
  local -a up
  while IFS='|' read -r key _; do
    [[ $(sed -n "s/^$key=//p" "$SERVICES_CONF" 2> /dev/null | tail -n 1) == after ]] || continue
    if [[ $(services_field "$key" 3) == radio:wifi ]]; then
      nmcli radio wifi on >> "$FLIPEROS_LOG" 2>&1
    else
      mapfile -t up < <(services_units "$key" service)
      ((${#up[@]})) && systemctl start --no-block "${up[@]}" >> "$FLIPEROS_LOG" 2>&1
    fi
    log_info "servicos: $key subiu depois do boot"
  done < <(services_table)
  return 0
}
