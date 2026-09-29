# shellcheck shell=bash
# System Update: apt-get update e upgrade (no lugar do pacman do gasetup),
# com o progresso real que o apt publica no APT::Status-Fd.

# update_parse_status le as linhas do Status-Fd e imprime eventos:
#   dlstatus:1:12.5:Retrieving file 1 of 20  -> download, de 10% a 50%
#   pmstatus:pacote:37.5:Installing pacote    -> instalacao, de 50% a 99%
update_parse_status() {
  local kind pkg pct text last=-1 p
  while IFS=: read -r kind pkg pct text; do
    case $kind in
      dlstatus) p=$(awk -v x="$pct" 'BEGIN { printf "%d", 10 + x * 40 / 100 }') ;;
      pmstatus) p=$(awk -v x="$pct" 'BEGIN { printf "%d", 50 + x * 49 / 100 }') ;;
      *) continue ;;
    esac
    if ((p != last)); then
      last=$p
      printf '@step %s %s\n' "$p" "${text:-$pkg}"
    fi
  done
}

# update_install_package PACOTE instala um pacote (um frontend do
# repositorio do FliperOS, por exemplo).
update_install_package() {
  local pkg=$1 rc
  export DEBIAN_FRONTEND=noninteractive
  ev_step 2 "Updating the package lists"
  ev_run apt-get update || return 1
  ev_step 10 "Installing $pkg"
  log_line cmd "\$ apt-get install $pkg"
  apt-get -y -o APT::Status-Fd=3 install "$pkg" 3>&1 >> "$FLIPEROS_LOG" 2>&1 | update_parse_status
  rc=${PIPESTATUS[0]}
  if ((rc != 0)); then
    ev_fail "apt-get install $pkg exited with status $rc"
    return 1
  fi
  ev_step 100 "$pkg installed"
}

# update_run atualiza o sistema falando com a tela por eventos.
update_run() {
  local rc
  export DEBIAN_FRONTEND=noninteractive
  ev_step 2 "Updating the package lists"
  ev_run apt-get update || return 1
  ev_step 10 "Downloading updates"
  log_line cmd "\$ apt-get upgrade"
  # 3>&1 antes de mandar a saida normal para o log: pelo cano so passa o
  # Status-Fd.
  apt-get -y -o APT::Status-Fd=3 \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold \
    upgrade 3>&1 >> "$FLIPEROS_LOG" 2>&1 | update_parse_status
  rc=${PIPESTATUS[0]}
  if ((rc != 0)); then
    ev_fail "apt-get upgrade exited with status $rc"
    return 1
  fi
  ev_step 100 "System up to date"
}
