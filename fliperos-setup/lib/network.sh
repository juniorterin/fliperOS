# shellcheck shell=bash
# Rede. O gasetup usa iwctl (iwd); no Ubuntu quem gerencia e o
# NetworkManager, entao aqui e nmcli. Mesmo fluxo do worker_configure_wifi:
# escolher a placa, listar as redes, pedir a senha e conectar; com o extra
# de aceitar uma rede oculta digitando o SSID.

# net_wifi_devices lista as placas Wi-Fi.
net_wifi_devices() {
  nmcli -t -f DEVICE,TYPE device status 2> /dev/null | awk -F: '$2 == "wifi" { print $1 }'
}

# net_hardware descreve o hardware de rede que o Linux enxerga, para quando
# nenhuma placa Wi-Fi aparece: placa sem driver (aparece aqui e nao no
# nmcli) ou desligada pelo rfkill (botao ou BIOS).
net_hardware() {
  local found=0 line
  while IFS= read -r line; do
    printf 'PCI: %s\n' "$line"
    found=1
  done < <(lspci 2> /dev/null | grep -iE 'network|wireless|wi-?fi|802\.11' | cut -d' ' -f2- |
    sed -E 's/^[^:]*: //')
  while IFS= read -r line; do
    printf 'USB: %s\n' "$line"
    found=1
  done < <(lsusb 2> /dev/null | grep -iE 'wireless|wi-?fi|wlan|802\.11|ralink|realtek.*(rtl8|wlan)|mediatek|atheros|tp-link' |
    sed -E 's/^.*ID [0-9a-fA-F:]+ //')
  ((found)) || echo "No network adapter besides Ethernet was found."
  if rfkill list wifi 2> /dev/null | grep -q 'blocked: yes'; then
    echo "Wi-Fi is switched off (rfkill): check the Wi-Fi key or the BIOS."
  fi
  return 0
}

# net_parse_scan le a saida de "nmcli -t -f SSID,SIGNAL,SECURITY" e imprime
# "SSID|sinal|seguranca", uma linha por rede (a de sinal mais forte quando
# o mesmo SSID aparece em mais de um ponto de acesso), da mais forte para a
# mais fraca. No modo -t o nmcli escapa ":" e "\" no SSID com "\".
net_parse_scan() {
  awk '
    {
      line = $0; ssid = ""; i = 1; n = length(line)
      while (i <= n) {
        c = substr(line, i, 1)
        if (c == "\\" && i < n) { ssid = ssid substr(line, i + 1, 1); i += 2; continue }
        if (c == ":") break
        ssid = ssid c; i++
      }
      rest = substr(line, i + 1)
      split(rest, f, ":")
      signal = f[1] + 0; sec = f[2]
      if (ssid == "" || ssid == "--") next
      if (!(ssid in best) || signal > best[ssid]) { best[ssid] = signal; security[ssid] = sec }
    }
    END { for (s in best) printf "%s|%d|%s\n", s, best[s], security[s] }' | sort -t'|' -k2,2nr
}

# net_scan PLACA imprime as redes visiveis (ver net_parse_scan).
net_scan() {
  nmcli -t -f SSID,SIGNAL,SECURITY device wifi list ifname "$1" --rescan yes 2> /dev/null | net_parse_scan
}

# net_connect PLACA SSID SENHA OCULTA conecta; OCULTA=1 para SSID escondido.
net_connect() {
  local dev=$1 ssid=$2 pass=$3 hidden=${4:-0} args
  args=(device wifi connect "$ssid" ifname "$dev")
  [[ -n $pass ]] && args+=(password "$pass")
  ((hidden)) && args+=(hidden yes)
  log_info "rede: conectando '$ssid' em $dev (oculta=$hidden)"
  nmcli --wait 45 "${args[@]}" >> "$FLIPEROS_LOG" 2>&1
}

# net_ips imprime os IPv4 das interfaces ligadas, separados por espaco (o
# titulo do menu principal do gasetup faz o mesmo com "ip -br a").
net_ips() {
  ip -4 -o addr show scope global 2> /dev/null | awk '{ split($4, a, "/"); printf "%s%s", sep, a[1]; sep = " " } END { print "" }'
}

# net_summary imprime uma linha por interface: nome, estado, conexao e IP.
net_summary() {
  local dev type state conn ip
  while IFS=: read -r dev type state conn; do
    [[ $type == loopback || $dev == lo ]] && continue
    ip=$(ip -4 -o addr show dev "$dev" scope global 2> /dev/null | awk '{ split($4, a, "/"); print a[1]; exit }')
    printf '%s (%s): %s%s%s\n' "$dev" "$type" "$state" "${conn:+, $conn}" "${ip:+, IP $ip}"
  done < <(nmcli -t -f DEVICE,TYPE,STATE,CONNECTION device status 2> /dev/null)
}
