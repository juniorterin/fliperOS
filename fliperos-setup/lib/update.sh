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

# As travas do apt e do dpkg: quem instala ou atualiza pacotes segura uma
# delas (outro apt-get, a App Store pelo PackageKit, uma atualizacao em
# curso).
APT_LOCKS=${APT_LOCKS:-/var/lib/dpkg/lock-frontend /var/lib/dpkg/lock /var/lib/apt/lists/lock /var/cache/apt/archives/lock}
# Quanto esperar por elas, em segundos.
APT_LOCK_WAIT=${APT_LOCK_WAIT:-300}

# update_locked: outro programa esta com uma das travas? Sao travas de
# registro (fcntl), que o flock(1) nao enxerga: tenta pega-la e solta.
update_locked() {
  # shellcheck disable=SC2086 # um arquivo por palavra
  python3 - $APT_LOCKS << 'PY'
import fcntl
import sys

for path in sys.argv[1:]:
    try:
        with open(path, 'a') as f:
            fcntl.lockf(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.lockf(f, fcntl.LOCK_UN)
    except FileNotFoundError:
        continue
    except OSError:
        sys.exit(0)
sys.exit(1)
PY
}

# update_wait_lock espera o outro programa terminar (ate APT_LOCK_WAIT). Sem
# isso o apt-get desistia na hora: "Impossivel criar acesso exclusivo".
update_wait_lock() {
  local waited=0
  while update_locked; do
    ((waited == 0)) && ev_msg "Another program is installing or updating packages: waiting for it"
    if ((waited >= APT_LOCK_WAIT)); then
      ev_fail "Another program is still using the package manager (an update, or the App Store). Try again in a few minutes."
      return 1
    fi
    sleep 3
    waited=$((waited + 3))
  done
  return 0
}

# update_install_package PACOTE instala um pacote (um frontend do
# repositorio do FliperOS, por exemplo).
update_install_package() {
  local pkg=$1 rc
  export DEBIAN_FRONTEND=noninteractive
  ev_step 2 "Updating the package lists"
  update_wait_lock || return 1
  ev_run apt-get update || return 1
  ev_step 10 "Installing $pkg"
  log_line cmd "\$ apt-get install $pkg"
  apt-get -y -o DPkg::Lock::Timeout=120 -o APT::Status-Fd=3 install "$pkg" 3>&1 >> "$FLIPEROS_LOG" 2>&1 |
    update_parse_status
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
  update_wait_lock || return 1
  ev_run apt-get update || return 1
  ev_step 10 "Downloading updates"
  log_line cmd "\$ apt-get upgrade"
  # 3>&1 antes de mandar a saida normal para o log: pelo cano so passa o
  # Status-Fd.
  apt-get -y -o DPkg::Lock::Timeout=120 -o APT::Status-Fd=3 \
    -o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confold \
    upgrade 3>&1 >> "$FLIPEROS_LOG" 2>&1 | update_parse_status
  rc=${PIPESTATUS[0]}
  if ((rc != 0)); then
    ev_fail "apt-get upgrade exited with status $rc"
    return 1
  fi
  ev_step 100 "System up to date"
}
