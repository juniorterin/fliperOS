# shellcheck shell=bash
# Pasta compartilhada da rede (SMB: Windows, NAS, RetroNAS, outro Linux com
# Samba, o compartilhamento de um Batocera), de dois jeitos:
#
# - De passagem, so para leitura em NETSHARE_DIR: o MAME ROM Cleaner le o
#   romset de la (o romset fica no computador da casa e o gabinete pega so o
#   que usa). O servidor, o compartilhamento e o usuario ficam no
#   fliperos.conf; a senha, so se a pessoa pedir, em NETSHARE_CRED (so o root le).
#
# - Guardada (Setup > Games > Folders > External storage > Network folder):
#   montada de vez em /media/fliperos/NOME, como um disco a mais. La ela
#   aparece em tudo o que ja olha os discos (FliperOS folders, Batocera
#   filesystem, Folder shortcuts, o painel web), e os jogos sao lidos da rede,
#   no lugar. Cada uma e um par de unidades do systemd (NOME.mount e
#   NOME.automount, em NETSHARE_UNITS, marcadas com "# fliperos-netshare"): o
#   automount monta no primeiro acesso, entao um servidor que liga depois do
#   gabinete funciona sem reiniciar. Nada vai para o /etc/fstab: uma linha
#   errada la para o boot, e apagar uma pasta e apagar dois arquivos. A senha
#   fica em NETSHARE_CRED_DIR/NOME.cred (so o root le).
#
#   fliperos-setup --netshare list                       "NOME|SERVIDOR|PASTA|USUARIO|MONTAGEM|ESTADO|EMUSO"
#   fliperos-setup --netshare shares SERVIDOR [USUARIO]  as pastas compartilhadas (senha na entrada)
#   fliperos-setup --netshare add SERVIDOR PASTA [USUARIO]   guarda e monta (senha na entrada): "mount=..."
#   fliperos-setup --netshare remove NOME                esquece a pasta (nada sai do servidor)
#   fliperos-setup --netshare layout MONTAGEM            batocera, fliperos, other ou offline
#
# ESTADO: mounted (montada), waiting (espera o primeiro acesso) ou offline (nem
# o automount esta de pe); EMUSO: 1 quando os jogos usam a pasta.

NETSHARE_DIR=${NETSHARE_DIR:-/mnt/network}
NETSHARE_CRED=${NETSHARE_CRED:-$FLIPEROS_ETC/netshare.cred}
NETSHARE_UNITS=${NETSHARE_UNITS:-/etc/systemd/system}
NETSHARE_CRED_DIR=${NETSHARE_CRED_DIR:-$FLIPEROS_ETC/netshares}
# Quanto a montagem espera o servidor (segundos): um servidor desligado nao
# prende quem abre a pasta mais que isso.
NETSHARE_TIMEOUT=${NETSHARE_TIMEOUT:-15}
# Por que a ultima montagem falhou, em palavras para a tela.
NETSHARE_ERROR=""
# O que o netshare_offline ja perguntou neste processo (MONTAGEM -> on/off).
declare -gA NETSHARE_OFFLINE=()

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
    NETSHARE_ERROR="cifs-utils is not installed (Setup > System > System Update)."
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
  if ! netshare_try "//$host/$share" "$NETSHARE_DIR" "$opts"; then
    [[ -n $cred ]] && rm -f "$cred"
    return 1
  fi
  [[ -n $cred ]] && rm -f "$cred"
  return 0
}

# netshare_try ORIGEM PASTA OPCOES monta a ORIGEM na PASTA com as OPCOES e o
# que mais der: sem o nls_utf8 no kernel a montagem com iocharset falha (vale
# sem ele), e um servidor antigo so com SMB1 (o NAS velho, o Windows XP)
# responde "Host is down" ou "Operation not supported" ao SMB2 de hoje (vale
# com vers=1.0). As opcoes que montaram ficam em NETSHARE_OPTS; na falha, o
# motivo em NETSHARE_ERROR.
netshare_try() {
  local src=$1 dir=$2 opts=$3 out
  NETSHARE_OPTS=""
  if mount -t cifs "$src" "$dir" -o "$opts,iocharset=utf8" > /dev/null 2>&1; then
    NETSHARE_OPTS="$opts,iocharset=utf8"
    return 0
  fi
  if out=$(mount -t cifs "$src" "$dir" -o "$opts" 2>&1); then
    NETSHARE_OPTS=$opts
    return 0
  fi
  case $out in
    *"error(112)"* | *"error(95)"* | *"Operation not supported"*)
      if mount -t cifs "$src" "$dir" -o "$opts,vers=1.0" > /dev/null 2>&1; then
        log_info "Pasta da rede: $src so com SMB1 (vers=1.0)"
        NETSHARE_OPTS="$opts,vers=1.0"
        return 0
      fi
      ;;
  esac
  log_error "mount.cifs $src: $out"
  NETSHARE_ERROR=$(netshare_explain "$out")
  return 1
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

# ── As pastas guardadas (montadas de vez em /media/fliperos) ──────

# netshare_root: onde as pastas guardadas sao montadas (a mesma pasta dos
# discos que o fliperos-automount monta).
netshare_root() {
  printf '%s\n' "${NETSHARE_ROOT:-${STORAGE_MOUNTS:-/media/$FLIPEROS_USER}}"
}

# netshare_escape CAMINHO: o nome de unidade do systemd do caminho (o mesmo
# do systemd-escape --path): "/" vira "-", o que nao e letra, numero, ":" ou
# "_" (e o "." do comeco) vira \xNN.
netshare_escape() {
  local path=${1#/} out="" c i
  path=${path%/}
  for ((i = 0; i < ${#path}; i++)); do
    c=${path:i:1}
    case $c in
      /) out+=- ;;
      [A-Za-z0-9:_]) out+=$c ;;
      .) if ((i == 0)); then out+='\x2e'; else out+=.; fi ;;
      *)
        printf -v c '\\x%02x' "'$c"
        out+=$c
        ;;
    esac
  done
  printf '%s\n' "$out"
}

# netshare_units imprime os .mount das pastas guardadas, um por linha.
netshare_units() {
  local unit
  for unit in "$NETSHARE_UNITS"/*.mount; do
    [[ -f $unit ]] && grep -qx '# fliperos-netshare' "$unit" 2> /dev/null && printf '%s\n' "$unit"
  done
  return 0
}

# netshare_unit_field UNIDADE CAMPO: What, Where ou user (da linha "# user=").
netshare_unit_field() {
  case $2 in
    user) sed -n 's/^# user=//p' "$1" | head -n 1 ;;
    *) sed -n "s/^$2=//p" "$1" | head -n 1 ;;
  esac
}

# netshare_state MONTAGEM: mounted, waiting (o automount espera o primeiro
# acesso) ou offline (nem o automount esta ativo).
netshare_state() {
  if findmnt -rn -t cifs,smb3 -M "$1" > /dev/null 2>&1; then
    echo mounted
  elif findmnt -rn -t autofs -M "$1" > /dev/null 2>&1; then
    echo waiting
  else
    echo offline
  fi
}

# netshare_list: as pastas guardadas, "NOME|SERVIDOR|PASTA|USUARIO|MONTAGEM|ESTADO".
netshare_list() {
  local unit what where user host share
  while IFS= read -r unit; do
    what=$(netshare_unit_field "$unit" What)
    where=$(netshare_unit_field "$unit" Where)
    [[ $what == //*/* && -n $where ]] || continue
    user=$(netshare_unit_field "$unit" user)
    host=${what#//}
    share=${host#*/}
    host=${host%%/*}
    printf '%s|%s|%s|%s|%s|%s\n' "${where##*/}" "$host" "$share" "$user" "$where" "$(netshare_state "$where")"
  done < <(netshare_units)
  return 0
}

# netshare_find CAMPO VALOR imprime o .mount da pasta guardada com esse nome
# (name), essa origem (source: //servidor/pasta) ou essa montagem (where).
netshare_find() {
  local unit what where
  while IFS= read -r unit; do
    what=$(netshare_unit_field "$unit" What)
    where=$(netshare_unit_field "$unit" Where)
    case $1 in
      name) [[ ${where##*/} == "$2" ]] ;;
      source) [[ ${what,,} == "${2,,}" ]] ;;
      where) [[ $where == "$2" ]] ;;
      *) false ;;
    esac && { printf '%s\n' "$unit"; return 0; }
  done < <(netshare_units)
  return 1
}

# netshare_new_name PASTA SERVIDOR imprime um nome livre em netshare_root
# (letras, numeros e _): o da pasta compartilhada; com outro disco ou outra
# pasta ja com ele, o do servidor junto, ou um numero.
netshare_new_name() {
  local base=${1//[^A-Za-z0-9_]/_} host=${2//[^A-Za-z0-9_]/_} root cand i
  root=$(netshare_root)
  [[ -n ${base//_/} ]] || base=network
  for cand in "$base" "${base}_$host" "${base}_2" "${base}_3" "${base}_4" "${base}_5"; do
    [[ -e $root/$cand || -L $root/$cand ]] && continue
    netshare_find name "$cand" > /dev/null && continue
    printf '%s\n' "$cand"
    return 0
  done
  for ((i = 6; ; i++)); do
    [[ -e $root/${base}_$i ]] || { printf '%s_%d\n' "$base" "$i"; return 0; }
  done
}

# netshare_write_units ORIGEM MONTAGEM OPCOES USUARIO grava o .mount e o
# .automount da pasta. O automount entra no remote-fs.target (o boot nao
# espera a rede por ele) e nao desmonta por ficar parada.
netshare_write_units() {
  local src=$1 where=$2 opts=$3 user=$4 base
  base=$NETSHARE_UNITS/$(netshare_escape "$where")
  mkdir -p "$NETSHARE_UNITS" || return 1
  printf '%s\n' "# fliperos-netshare" "# user=$user" \
    "# Setup > Games > Folders > External storage > Network folder (fliperos-setup --netshare)." \
    "[Unit]" "Description=FliperOS network folder $src" "Wants=network-online.target" \
    "After=network-online.target" "" "[Mount]" "What=$src" "Where=$where" "Type=cifs" "Options=$opts" \
    "TimeoutSec=$NETSHARE_TIMEOUT" > "$base.mount" || return 1
  printf '%s\n' "# fliperos-netshare" "[Unit]" "Description=FliperOS network folder $src (mounted on first use)" "" \
    "[Automount]" "Where=$where" "TimeoutIdleSec=0" "" "[Install]" "WantedBy=remote-fs.target" \
    > "$base.automount" || return 1
  chmod 644 "$base.mount" "$base.automount"
}

# netshare_add SERVIDOR PASTA USUARIO SENHA guarda a pasta e a monta em
# netshare_root/NOME (ja guardada: troca o usuario e a senha). Monta primeiro
# numa pasta de passagem, para saber que entra e com quais opcoes; so entao
# grava as unidades e liga o automount. Imprime "mount=MONTAGEM". Na falha,
# nada fica e o motivo esta em NETSHARE_ERROR.
netshare_add() {
  local host=$1 share=$2 user=$3 pass=$4 src unit name where base tmp cred="" auth opts uid gid
  NETSHARE_ERROR=""
  host=${host#"${host%%[!/\\]*}"}
  host=${host%%[/\\]*}
  share=${share#"${share%%[!/\\]*}"}
  share=${share%"${share##*[!/\\]}"}
  if [[ -z $host || -z $share || $host == *[[:space:],]* || $share == *,* ]]; then
    NETSHARE_ERROR="Give the computer (its IP or name) and the shared folder."
    return 1
  fi
  if ! netshare_available; then
    NETSHARE_ERROR="cifs-utils is not installed (Setup > System > System Update)."
    return 1
  fi
  src="//$host/$share"
  if unit=$(netshare_find source "$src"); then
    where=$(netshare_unit_field "$unit" Where)
    name=${where##*/}
  else
    name=$(netshare_new_name "$share" "$host")
    where=$(netshare_root)/$name
  fi
  uid=$(id -u "$FLIPEROS_USER" 2> /dev/null) || uid=0
  gid=$(id -g "$FLIPEROS_USER" 2> /dev/null) || gid=0
  # Gravavel (o Batocera filesystem cria as pastas do FliperOS ao lado dos
  # consoles, e os saves podem ficar la): o servidor decide o que deixa.
  opts="rw,uid=$uid,gid=$gid,file_mode=0664,dir_mode=0775,actimeo=60"
  tmp=$(mktemp -d "${TMPDIR:-/tmp}/fliperos-netshare.XXXXXX") || return 1
  auth=guest
  if [[ -n $user ]]; then
    cred=$(mktemp) || { rmdir -- "$tmp"; return 1; }
    netshare_credentials "$cred" "$user" "$pass"
    auth="credentials=$cred"
  fi
  log_info "Pasta da rede: guardando $src como ${user:-convidado} em $where"
  if ! netshare_try "$src" "$tmp" "$opts,$auth"; then
    [[ -n $cred ]] && rm -f -- "$cred"
    rmdir -- "$tmp" 2> /dev/null
    return 1
  fi
  umount "$tmp" 2>> "$FLIPEROS_LOG" || umount -l "$tmp" 2>> "$FLIPEROS_LOG"
  rmdir -- "$tmp" 2> /dev/null
  [[ -n $cred ]] && rm -f -- "$cred"
  # As opcoes que montaram (o iocharset, o vers=1.0), com a senha de vez.
  opts+=${NETSHARE_OPTS#"$opts,$auth"}
  if [[ -n $user ]]; then
    mkdir -p "$NETSHARE_CRED_DIR" && chmod 700 "$NETSHARE_CRED_DIR" || return 1
    netshare_credentials "$NETSHARE_CRED_DIR/$name.cred" "$user" "$pass"
    opts+=",credentials=$NETSHARE_CRED_DIR/$name.cred"
  else
    rm -f -- "${NETSHARE_CRED_DIR:?}/${name:?}.cred"
    opts+=",guest"
  fi
  base=$(netshare_escape "$where")
  # Ja guardada e montada: sai antes, para montar com o usuario novo.
  systemctl stop "$base.automount" "$base.mount" > /dev/null 2>&1
  if ! netshare_write_units "$src" "$where" "$opts" "$user"; then
    NETSHARE_ERROR="Could not save the network folder in $NETSHARE_UNITS."
    return 1
  fi
  systemctl daemon-reload 2>> "$FLIPEROS_LOG"
  if ! systemctl enable --now "$base.automount" >> "$FLIPEROS_LOG" 2>&1; then
    netshare_forget "$where"
    NETSHARE_ERROR="The system did not take the network folder (details in the log)."
    return 1
  fi
  # O primeiro acesso monta (e confere que o automount esta de pe).
  timeout "$((NETSHARE_TIMEOUT + 5))" ls -- "$where" > /dev/null 2>> "$FLIPEROS_LOG"
  if [[ $(netshare_state "$where") != mounted ]]; then
    netshare_forget "$where"
    NETSHARE_ERROR="It opened once, but did not mount in $where (details in the log)."
    return 1
  fi
  unset NETSHARE_KNOWN
  NETSHARE_OFFLINE[$where]=on
  printf 'mount=%s\n' "$where"
  return 0
}

# netshare_forget MONTAGEM desliga e apaga as unidades e a senha da pasta.
netshare_forget() {
  local where=$1 base
  [[ $where == /*/* ]] || return 1
  base=$(netshare_escape "$where")
  systemctl disable --now "$base.automount" >> "$FLIPEROS_LOG" 2>&1
  systemctl stop "$base.mount" >> "$FLIPEROS_LOG" 2>&1
  # Ocupada (um jogo aberto nela): sai assim que for solta.
  findmnt -rn -M "$where" > /dev/null 2>&1 && umount -l "$where" 2>> "$FLIPEROS_LOG"
  rm -f -- "${NETSHARE_UNITS:?}/${base:?}.mount" "${NETSHARE_UNITS:?}/${base:?}.automount" \
    "${NETSHARE_CRED_DIR:?}/${where##*/}.cred"
  systemctl daemon-reload 2>> "$FLIPEROS_LOG"
  rmdir -- "$where" 2> /dev/null
  unset NETSHARE_KNOWN
  unset "NETSHARE_OFFLINE[$where]"
  return 0
}

# netshare_in_use MONTAGEM: os jogos usam a pasta (o Batocera filesystem dela,
# a estrutura do FliperOS nela, um atalho de pasta para dentro dela)?
netshare_in_use() {
  declare -F batocera_in_use > /dev/null && batocera_in_use "$1" && return 0
  declare -F storage_state > /dev/null && [[ $(storage_state "$1") != none ]] && return 0
  return 1
}

# netshare_remove NOME esquece a pasta guardada (nada sai do servidor). Em
# uso, recusa: o motivo em NETSHARE_ERROR.
netshare_remove() {
  local unit where
  NETSHARE_ERROR=""
  if ! unit=$(netshare_find name "$1"); then
    NETSHARE_ERROR="There is no network folder called $1."
    return 1
  fi
  where=$(netshare_unit_field "$unit" Where)
  if netshare_in_use "$where"; then
    NETSHARE_ERROR="The games use ${where##*/}. Stop using it first (Batocera filesystem, FliperOS folders or Folder shortcuts)."
    return 1
  fi
  log_info "Pasta da rede: esquecendo $(netshare_unit_field "$unit" What) ($where)"
  netshare_forget "$where"
}

# netshare_reachable SERVIDOR: o servidor atende o SMB (porta 445, ou a 139
# dos antigos)? Desligado, a 445 nao responde em 2 segundos e a 139 nem e
# tentada; ligado sem a 445, a recusa e na hora.
netshare_reachable() {
  local rc=0
  # shellcheck disable=SC2016 # o $0/$1 sao do bash de dentro
  timeout 2 bash -c 'exec 3<> "/dev/tcp/$0/$1"' "$1" 445 2> /dev/null || rc=$?
  ((rc == 0)) && return 0
  ((rc == 124)) && return 1
  # shellcheck disable=SC2016
  timeout 2 bash -c 'exec 3<> "/dev/tcp/$0/$1"' "$1" 139 2> /dev/null
}

# netshare_offline PASTA: a PASTA e de uma pasta guardada cujo servidor nao
# responde agora? Quem passa por muitas pastas (os consoles do Batocera
# filesystem, a lista dos discos) pergunta antes: com o servidor desligado,
# cada acesso esperaria NETSHARE_TIMEOUT segundos. Montada, nunca; a resposta
# vale para o processo todo.
netshare_offline() {
  local dir=$1 line where host
  # As pastas guardadas, lidas uma vez por processo ("MONTAGEM|SERVIDOR"): o
  # Batocera filesystem pergunta de cada um dos consoles.
  if [[ -z ${NETSHARE_KNOWN+x} ]]; then
    NETSHARE_KNOWN=$(netshare_list | awk -F'|' '{ print $5 "|" $2 }')
  fi
  [[ -n $NETSHARE_KNOWN ]] || return 1
  while IFS='|' read -r where host; do
    [[ -n $where && ($dir == "$where" || $dir == "$where"/*) ]] || continue
    if [[ -z ${NETSHARE_OFFLINE[$where]:-} ]]; then
      NETSHARE_OFFLINE[$where]=on
      if [[ $(netshare_state "$where") != mounted ]] && ! netshare_reachable "$host"; then
        NETSHARE_OFFLINE[$where]=off
      fi
    fi
    [[ ${NETSHARE_OFFLINE[$where]} == off ]]
    return
  done <<< "$NETSHARE_KNOWN"
  return 1
}

# netshare_layout MONTAGEM: o que a pasta tem, para a tela dizer o que fazer
# com ela: batocera (as pastas do Batocera: batocera/roms/<console>, como a
# copia que o RetroNAS faz), fliperos (a pasta fliperos de External storage)
# ou other.
netshare_layout() {
  if declare -F batocera_detect > /dev/null && batocera_detect "$1" > /dev/null; then
    echo batocera
  elif [[ -d $1/${STORAGE_NAME:-fliperos}/roms ]]; then
    echo fliperos
  else
    echo other
  fi
}

# netshare_cli list|shares|add|remove|layout: o fliperos-setup --netshare. A
# senha vem na entrada padrao (nunca na linha de comando, onde qualquer um a
# veria). Status 2: pedido errado; 1: nao deu (o motivo na saida).
netshare_cli() {
  local pass=""
  case ${1:-} in
    shares | add) [[ -t 0 ]] || IFS= read -r pass || true ;;
  esac
  local line mount
  case ${1:-} in
    list)
      # Mais o EMUSO (1: os jogos usam a pasta), para o painel.
      while IFS= read -r line; do
        IFS='|' read -r _ _ _ _ mount _ <<< "$line"
        printf '%s|%d\n' "$line" "$(netshare_in_use "$mount" && echo 1 || echo 0)"
      done < <(netshare_list)
      ;;
    shares)
      [[ -n ${2:-} ]] || return 2
      netshare_shares "$2" "${3:-}" "$pass" || { echo "No answer from $2."; return 1; }
      ;;
    add)
      [[ -n ${2:-} && -n ${3:-} ]] || return 2
      if ! netshare_add "$2" "$3" "${4:-}" "$pass"; then
        echo "${NETSHARE_ERROR:-Could not open //$2/$3 (details in the log).}"
        return 1
      fi
      ;;
    remove)
      [[ ${2:-} =~ ^[A-Za-z0-9_]+$ ]] || return 2
      if ! netshare_remove "$2"; then
        echo "$NETSHARE_ERROR"
        return 1
      fi
      ;;
    layout)
      [[ -n ${2:-} ]] && netshare_find where "$2" > /dev/null || return 2
      # Com o servidor desligado, olhar a pasta esperaria a montagem desistir.
      if netshare_offline "$2"; then
        echo offline
      else
        netshare_layout "$2"
      fi
      ;;
    *) return 2 ;;
  esac
  return 0
}
