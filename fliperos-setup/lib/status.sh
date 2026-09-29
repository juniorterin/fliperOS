# shellcheck shell=bash
# Linha de status do topo da tela, no formato do titulo do mainmenu do
# gasetup: "host (IP) - N% used on /".

status_disk_used() {
  df --output=pcent / 2> /dev/null | tail -1 | tr -dc '0-9'
}

status_line() {
  local host ips used
  host=$(hostname 2> /dev/null || echo fliperos)
  ips=$(net_ips)
  [[ -n $ips ]] || ips="no network"
  if is_live; then
    printf '%s (%s)\n' "$host" "$ips"
    return
  fi
  used=$(status_disk_used)
  printf '%s (%s) - %s%% used on /\n' "$host" "$ips" "${used:-?}"
}
