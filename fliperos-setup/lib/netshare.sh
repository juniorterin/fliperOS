# shellcheck shell=bash
# Pasta compartilhada da rede (SMB: Windows, NAS, outro Linux com Samba),
# montada so para leitura em NETSHARE_DIR. O MAME ROM Cleaner le o romset de
# la: o romset fica no computador da casa e o gabinete pega so o que usa. O
# servidor, o compartilhamento e o usuario ficam no fliperos.conf; a senha,
# so se a pessoa pedir, em NETSHARE_CRED (so o root le).

NETSHARE_DIR=${NETSHARE_DIR:-/mnt/network}
NETSHARE_CRED=${NETSHARE_CRED:-$FLIPEROS_ETC/netshare.cred}
# Por que a ultima montagem falhou, em palavras para a tela.
NETSHARE_ERROR=""

# netshare_available: o mount.cifs (cifs-utils) esta instalado?
netshare_available() {
  have mount.cifs
}

netshare_mounted() {
  mountpoint -q "$NETSHARE_DIR" 2> /dev/null
}

# netshare_source imprime o que esta montado ("//servidor/compartilhamento").
netshare_source() {
  findmnt -n -o SOURCE "$NETSHARE_DIR" 2> /dev/null
}

# netshare_credentials ARQUIVO USUARIO SENHA grava o arquivo de credenciais
# (o formato do mount.cifs e do smbclient), que so o dono le. A senha nunca
# vai na linha de comando, onde qualquer usuario a veria.
netshare_credentials() {
  (
    umask 077
    printf 'username=%s\npassword=%s\n' "$2" "$3" > "$1"
  )
}

# netshare_shares SERVIDOR USUARIO SENHA imprime as pastas compartilhadas do
# servidor, uma por linha (sem as administrativas, que terminam em $). Precisa
# do smbclient; sem ele, ou sem resposta, nada.
netshare_shares() {
  local cred rc
  have smbclient || return 1
  cred=$(mktemp) || return 1
  netshare_credentials "$cred" "$2" "$3"
  smbclient -g -L "//$1" -A "$cred" 2>> "$FLIPEROS_LOG" |
    awk -F'|' '$1 == "Disk" && $2 !~ /\$$/ { print $2 }'
  rc=${PIPESTATUS[0]}
  rm -f "$cred"
  return "$rc"
}

# netshare_explain SAIDA traduz o erro do mount.cifs.
netshare_explain() {
  case $1 in
    *"error(13)"* | *"Permission denied"*)
      echo "Wrong user or password, or this user may not open that folder." ;;
    *"error(2)"* | *"No such file"*)
      echo "That computer has no shared folder with this name." ;;
    *"error(11"[0-9]")"* | *"could not resolve"* | *"Unable to find suitable address"* | *"No route to host"* | \
      *"Host is down"* | *"timed out"*)
      echo "The computer did not answer. Check its name or IP, and that it is on and sharing files." ;;
    *) printf '%s\n' "$1" | grep -v '^[[:space:]]*$' | head -1 | cut -c1-160 ;;
  esac
}

# netshare_mount SERVIDOR COMPARTILHAMENTO USUARIO SENHA monta a pasta so
# para leitura (sem usuario: como convidado). Na falha, o motivo fica em
# NETSHARE_ERROR.
netshare_mount() {
  local host=$1 share=$2 user=$3 pass=$4 cred="" opts out uid gid
  NETSHARE_ERROR=""
  if ! netshare_available; then
    NETSHARE_ERROR="cifs-utils is not installed (Setup > System Update)."
    return 1
  fi
  netshare_umount
  mkdir -p "$NETSHARE_DIR" || return 1
  uid=$(id -u "$FLIPEROS_USER" 2> /dev/null) || uid=0
  gid=$(id -g "$FLIPEROS_USER" 2> /dev/null) || gid=0
  # actimeo: os atributos lidos na listagem valem por um minuto (o ROM
  # cleaner olha dezenas de milhares de arquivos).
  opts="ro,uid=$uid,gid=$gid,actimeo=60"
  if [[ -n $user ]]; then
    cred=$(mktemp) || return 1
    netshare_credentials "$cred" "$user" "$pass"
    opts+=",credentials=$cred"
  else
    opts+=",guest"
  fi
  log_info "Pasta da rede: //$host/$share como ${user:-convidado}"
  # Sem o nls_utf8 no kernel a montagem com iocharset falha: vale sem ele.
  if ! out=$(mount -t cifs "//$host/$share" "$NETSHARE_DIR" -o "$opts,iocharset=utf8" 2>&1) &&
    ! out=$(mount -t cifs "//$host/$share" "$NETSHARE_DIR" -o "$opts" 2>&1); then
    [[ -n $cred ]] && rm -f "$cred"
    log_error "mount.cifs //$host/$share: $out"
    NETSHARE_ERROR=$(netshare_explain "$out")
    return 1
  fi
  [[ -n $cred ]] && rm -f "$cred"
  return 0
}

# netshare_umount desmonta; ocupada, sai assim que for solta.
netshare_umount() {
  netshare_mounted || return 0
  umount "$NETSHARE_DIR" 2>> "$FLIPEROS_LOG" || umount -l "$NETSHARE_DIR" 2>> "$FLIPEROS_LOG"
}

# netshare_save SERVIDOR COMPARTILHAMENTO USUARIO [SENHA] guarda a pasta para
# a vez seguinte; a senha so se vier (senao a guardada e apagada).
netshare_save() {
  conf_set netshare_host "$1"
  conf_set netshare_share "$2"
  conf_set netshare_user "$3"
  if (($# > 3)); then
    netshare_credentials "$NETSHARE_CRED" "$3" "$4"
  else
    rm -f "$NETSHARE_CRED"
  fi
}

# netshare_saved CAMPO imprime o servidor (host), o compartilhamento (share)
# ou o usuario (user) guardados.
netshare_saved() {
  conf_get "netshare_$1" 2> /dev/null
}

# netshare_saved_password USUARIO imprime a senha guardada daquele usuario
# (status 1: nao ha).
netshare_saved_password() {
  [[ -f $NETSHARE_CRED && $(sed -n 's/^username=//p' "$NETSHARE_CRED") == "$1" ]] || return 1
  sed -n 's/^password=//p' "$NETSHARE_CRED"
}
