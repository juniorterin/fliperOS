# shellcheck shell=bash
# Setup > Games > Folders > External storage > FliperOS folders: um disco
# secundario (um HD externo, um SSD ou
# outro disco interno, montado sozinho pelo fliperos-automount em
# /media/fliperos/ROTULO) com a estrutura de pastas do FliperOS dentro de
# uma pasta "fliperos" dele:
#
#   /media/fliperos/DISCO/fliperos/roms  bios  media  nvram  save
#
# Cada uma com o que o fliperos-roms cria (uma pasta por emulador e por core
# do RetroArch, uma por tipo de arte...). Ligar um disco ("Use it") faz de
# cada uma a "custom folder" da pasta de mesmo nome em ~ (lib/folders.sh):
# tudo o que o FliperOS baixa (o Downloader, o Scraper, os pacotes de arte) e
# grava (saves, nvram) passa a ir para ele, junto do disco principal: o que
# ja estava em ~ fica ao lado, com "old-" no nome, e "Stop using it" o
# devolve. A estrutura nasce sozinha no disco quando ele e ligado
# (fliperos-automount chama --storage prepare), sem mudar nada em ~.
#
#   fliperos-setup --storage list              "MONTAGEM|ROTULO|FS|TOTAL|LIVRE|PODE|ESTADO"
#   fliperos-setup --storage prepare MONTAGEM  cria a estrutura (nao liga)
#   fliperos-setup --storage use MONTAGEM      cria e liga as cinco pastas
#   fliperos-setup --storage unuse             devolve as cinco pastas ao disco principal
#   fliperos-setup --storage offer MONTAGEM    anota o disco para o frontend perguntar (abaixo)
#   fliperos-setup --storage answer MONTAGEM yes|no [batocera]   a resposta do frontend
#   fliperos-setup --storage auto MONTAGEM     o que o fliperos-automount faz com um disco novo
#   fliperos-setup --storage format MONTAGEM ext4|exfat   apaga a particao e a formata
#
# O disco novo: o fliperos-automount chama --storage auto, que poe o disco que
# serve e ainda nao esta em uso na fila (offer); o frontend (gui/festorage.py)
# le a fila em STORAGE_STATE/offer e pergunta, uma vez so por disco, se a
# pessoa quer usa-lo para tudo. A resposta (--storage answer: "yes" liga como
# "use", "no" so registra) guarda o disco em STORAGE_STATE/answered, pelo UUID
# do sistema de arquivos: ele nao pergunta mais, e o disco segue em Setup >
# Games > Folders > External storage para quando a pessoa quiser.
#
# Um disco com um Batocera filesystem (lib/batocera.sh) nao ganha a pasta
# "fliperos" (nada e escrito nele sem a pessoa pedir): a oferta e do tipo
# "batocera" ("MONTAGEM|ROTULO|FS|TOTAL|ID|batocera|CONSOLES"), e a resposta
# "yes" liga o Batocera filesystem (batocera_use). O ID dela e "batocera:UUID":
# quem ja respondeu a pergunta do FliperOS para o mesmo disco recebe esta, uma vez.
#
# PODE: 1 se o disco serve (gravavel, de arquivos de verdade, com no minimo
# STORAGE_MIN_BYTES: 8 GB; um pendrive pequeno nao ganha pasta); ESTADO: all
# (as cinco pastas dele ja sao as de ~), some (algumas) ou none.

STORAGE_NAME=${STORAGE_NAME:-fliperos}
STORAGE_KINDS="roms bios media nvram save"
STORAGE_MIN_BYTES=${STORAGE_MIN_BYTES:-8000000000}
STORAGE_MOUNTS=${STORAGE_MOUNTS:-${FOLDERS_MOUNTS:-/media/$FLIPEROS_USER}}
# Por que o ultimo pedido foi recusado, em palavras para a tela.
STORAGE_ERROR=""
# O rotulo de um disco formatado aqui (11 letras: o maximo do exFAT).
STORAGE_LABEL=${STORAGE_LABEL:-FliperOS-HD}
STORAGE_SQUASH_LIST=${FLIPEROS_SQUASH_LIST:-/etc/fliperos/squashgames.list}
# A fila do frontend (offer, legivel por todos) e os discos ja respondidos
# (answered, um UUID por linha).
STORAGE_STATE=${STORAGE_STATE:-/var/lib/fliperos/storage}

# storage_mounts imprime os discos de dados montados (um por linha): as pastas
# de /media/fliperos que sao pontos de montagem.
storage_mounts() {
  local dir
  for dir in "$STORAGE_MOUNTS"/*/; do
    dir=${dir%/}
    # O atalho para a pasta ao lado (o /media/fliperos/<UUID> do disco sem
    # rotulo, config/fliperos-automount) e o mesmo disco: aparecia duas vezes,
    # a segunda "sem uso".
    [[ -L $dir && $(readlink -- "$dir") != */* ]] && continue
    # Uma pasta da rede guardada (lib/netshare.sh) com o servidor desligado:
    # abrir esperaria a montagem desistir; fica de fora ate ele voltar.
    declare -F netshare_offline > /dev/null && netshare_offline "$dir" && continue
    [[ -d $dir ]] && mountpoint -q -- "$dir" 2> /dev/null && printf '%s\n' "$dir"
  done
  return 0
}

# storage_findmnt CAMPO CAMINHO: o CAMPO (FSTYPE, SOURCE, UUID) do sistema de
# arquivos onde o CAMINHO esta. Uma pasta da rede guardada (lib/netshare.sh)
# tem dois um sobre o outro, o autofs e o cifs: vale o de cima, a ultima linha.
storage_findmnt() {
  findmnt -rno "$1" -T "$2" 2> /dev/null | tail -n 1
}

# storage_size_of MONTAGEM CAMPO: total ou livre, em bytes.
storage_size_of() {
  df -B1 --output="$2" -- "$1" 2> /dev/null | tail -n 1 | tr -d ' '
}

# storage_usable MONTAGEM: o disco serve? (status 0). O motivo fica em
# STORAGE_ERROR.
storage_usable() {
  local mount=$1 fs total
  STORAGE_ERROR=""
  mountpoint -q -- "$mount" 2> /dev/null || { STORAGE_ERROR="$mount is not a mounted disk."; return 1; }
  fs=$(storage_findmnt FSTYPE "$mount")
  case $fs in
    iso9660 | udf | squashfs | overlay | tmpfs | ramfs)
      STORAGE_ERROR="A $fs disk can't hold the folders."
      return 1
      ;;
  esac
  [[ -w $mount ]] || { STORAGE_ERROR="$mount is read only."; return 1; }
  total=$(storage_size_of "$mount" size)
  if [[ ! $total =~ ^[0-9]+$ ]] || ((total < STORAGE_MIN_BYTES)); then
    STORAGE_ERROR="The disk is smaller than $((STORAGE_MIN_BYTES / 1000000000)) GB."
    return 1
  fi
  return 0
}

# storage_dir MONTAGEM: a pasta "fliperos" do disco.
storage_dir() {
  printf '%s/%s\n' "$1" "$STORAGE_NAME"
}

# storage_state MONTAGEM: all, some ou none (quantas das cinco pastas de ~
# apontam para as pastas deste disco).
storage_state() {
  local kind dir n=0 total=0
  dir=$(storage_dir "$1")
  for kind in $STORAGE_KINDS; do
    total=$((total + 1))
    [[ $(folders_target "$kind" 2> /dev/null) == "$dir/$kind" ]] && n=$((n + 1))
  done
  if ((n == total)); then echo all; elif ((n)); then echo some; else echo none; fi
}

# storage_list: os discos, "MONTAGEM|ROTULO|FS|TOTAL|LIVRE|PODE|ESTADO".
storage_list() {
  local mount label fs usable
  while IFS= read -r mount; do
    [[ -n $mount ]] || continue
    label=${mount##*/}
    fs=$(storage_findmnt FSTYPE "$mount")
    usable=0
    storage_usable "$mount" && usable=1
    printf '%s|%s|%s|%s|%s|%d|%s\n' "$mount" "${label//|/ }" "${fs:-?}" "$(storage_size_of "$mount" size)" \
      "$(storage_size_of "$mount" avail)" "$usable" "$(storage_state "$mount")"
  done < <(storage_mounts)
  return 0
}

# storage_prepare MONTAGEM: cria a pasta "fliperos" do disco com as cinco
# pastas e o que o fliperos-roms poe em cada uma (uma pasta por emulador e por
# core, uma por tipo de arte...), do dono certo. Nada em ~ muda. Status 1: o
# disco nao serve.
storage_prepare() {
  local mount=$1 dir kind
  storage_usable "$mount" || return 1
  dir=$(storage_dir "$mount")
  for kind in $STORAGE_KINDS; do
    mkdir -p -- "$dir/$kind" 2>> "$FLIPEROS_LOG" || { STORAGE_ERROR="Could not create $dir/$kind."; return 1; }
  done
  if ((EUID == 0)) && id "$FLIPEROS_USER" > /dev/null 2>&1; then
    # Um disco de Linux (ext4, btrfs...) guarda o dono; os FAT/exFAT/NTFS ja
    # vem montados como a pessoa.
    chown "$FLIPEROS_USER:" "$dir" "$dir"/* 2> /dev/null || true
  fi
  if [[ -x $FOLDERS_SCRIPT ]]; then
    local -a env=(HOME="$FOLDERS_HOME" FLIPEROS_ROMS="$dir/roms" FLIPEROS_BIOS="$dir/bios" FLIPEROS_MEDIA="$dir/media"
      FLIPEROS_NVRAM="$dir/nvram" FLIPEROS_SAVE="$dir/save")
    if ((EUID == 0)) && id "$FLIPEROS_USER" > /dev/null 2>&1; then
      runuser -u "$FLIPEROS_USER" -- env "${env[@]}" "$FOLDERS_SCRIPT" >> "$FLIPEROS_LOG" 2>&1
    else
      env "${env[@]}" "$FOLDERS_SCRIPT" >> "$FLIPEROS_LOG" 2>&1
    fi
  fi
  log_info "Storage: estrutura em $dir"
  return 0
}

# storage_use MONTAGEM: prepara o disco e faz das cinco pastas de ~ links para
# as dele (folders_link: a de antes fica ao lado, com "old-"). Imprime
# "kept=PASTA" de cada uma guardada. Status 1: o disco nao serve ou uma pasta
# nao deu.
storage_use() {
  local mount=$1 dir kind failed=0
  storage_prepare "$mount" || return 1
  dir=$(storage_dir "$mount")
  for kind in $STORAGE_KINDS; do
    [[ $(folders_target "$kind" 2> /dev/null) == "$dir/$kind" ]] && continue
    if folders_link "$kind" "$dir/$kind"; then
      [[ -n $FOLDERS_KEPT ]] && echo "kept=${FOLDERS_KEPT/#$FOLDERS_HOME/\~}"
    else
      STORAGE_ERROR=${FOLDERS_ERROR:-Could not use $dir/$kind.}
      failed=1
      break
    fi
  done
  folders_cli_refresh roms
  ((failed == 0)) || return 1
  # Quem usa o disco ja decidiu: o frontend nao pergunta dele.
  storage_settle "$mount"
  return 0
}

# storage_unuse: as pastas de ~ que apontam para uma pasta "fliperos" de um
# disco voltam ao que eram (folders_unlink); nada sai do disco.
storage_unuse() {
  local kind target failed=0 rc
  for kind in $STORAGE_KINDS; do
    target=$(folders_target "$kind" 2> /dev/null) || continue
    [[ $target == */"$STORAGE_NAME/$kind" ]] || continue
    rc=0
    folders_unlink "$kind" || rc=$?
    if ((rc == 1)); then
      STORAGE_ERROR=${FOLDERS_ERROR:-Could not stop using $target.}
      failed=1
    fi
  done
  folders_cli_refresh roms
  ((failed == 0))
}

# ── O disco novo: a pergunta do frontend ─────────────────────────
# storage_id MONTAGEM imprime o que identifica o disco: o UUID do sistema de
# arquivos (sem ele, o rotulo e o tamanho).
storage_id() {
  local id
  id=$(storage_findmnt UUID "$1")
  [[ -n $id ]] || id="${1##*/}-$(storage_size_of "$1" size)"
  printf '%s\n' "${id//|/ }"
}

# storage_answered ID: o disco ja foi respondido?
storage_answered() {
  grep -qxF -- "$1" "$STORAGE_STATE/answered" 2> /dev/null
}

# storage_unoffer MONTAGEM tira o disco da fila do frontend.
storage_unoffer() {
  local file=$STORAGE_STATE/offer tmp
  [[ -f $file ]] || return 0
  tmp=$(mktemp "$STORAGE_STATE/.offer.XXXXXX" 2> /dev/null) || return 0
  awk -F'|' -v mount="$1" '$1 != mount' "$file" > "$tmp"
  if [[ -s $tmp ]]; then
    chmod 644 "$tmp"
    mv -f -- "$tmp" "$file"
  else
    rm -f -- "$tmp" "$file"
  fi
  return 0
}

# storage_settle MONTAGEM [batocera] guarda o disco como respondido (o
# frontend nao pergunta mais dele) e o tira da fila. Com "batocera", e a
# pergunta do Batocera filesystem (outra chave: batocera:UUID). Nunca falha:
# e so um registro.
storage_settle() {
  local id
  id=$(storage_id "$1")
  [[ ${2:-} == batocera ]] && id="batocera:$id"
  if mkdir -p "$STORAGE_STATE" 2> /dev/null && ! storage_answered "$id"; then
    printf '%s\n' "$id" >> "$STORAGE_STATE/answered" 2> /dev/null
  fi
  storage_unoffer "$1"
  return 0
}

# storage_offer MONTAGEM poe o disco na fila do frontend ("MONTAGEM|ROTULO|FS|
# TOTAL|ID" em STORAGE_STATE/offer) se ele serve, ainda nao esta em uso e nunca
# foi respondido. Status 1: nada a perguntar.
storage_offer() {
  local mount=$1 id fs
  storage_usable "$mount" || return 1
  [[ $(storage_state "$mount") == none ]] || return 1
  id=$(storage_id "$mount")
  storage_answered "$id" && return 1
  mkdir -p "$STORAGE_STATE" 2> /dev/null || return 1
  chmod 755 "$STORAGE_STATE" 2> /dev/null
  # Outro disco no mesmo lugar (o antigo saiu sem resposta): fica o de agora.
  storage_unoffer "$mount"
  fs=$(storage_findmnt FSTYPE "$mount")
  printf '%s|%s|%s|%s|%s\n' "$mount" "${mount##*/}" "${fs:-?}" "$(storage_size_of "$mount" size)" "$id" \
    >> "$STORAGE_STATE/offer" || return 1
  chmod 644 "$STORAGE_STATE/offer" 2> /dev/null
  log_info "Storage: $mount espera a resposta do frontend"
  return 0
}

# storage_fs_ok MONTAGEM: o sistema de arquivos pode guardar jogos (nao e um
# CD, uma imagem ou a memoria)? Um disco so de leitura serve para ler.
storage_fs_ok() {
  case $(storage_findmnt FSTYPE "$1") in
    iso9660 | udf | squashfs | overlay | tmpfs | ramfs) return 1 ;;
  esac
  return 0
}

# storage_offer_batocera MONTAGEM poe o Batocera filesystem do disco na fila do
# frontend ("MONTAGEM|ROTULO|FS|TOTAL|ID|batocera|CONSOLES") se o disco tem um,
# ainda nao esta ligado e a pergunta nunca foi respondida. Status 1: nada a
# perguntar.
storage_offer_batocera() {
  local mount=$1 id fs n
  batocera_detect "$mount" > /dev/null || return 1
  storage_fs_ok "$mount" || return 1
  batocera_in_use "$mount" && return 1
  id="batocera:$(storage_id "$mount")"
  storage_answered "$id" && return 1
  mkdir -p "$STORAGE_STATE" 2> /dev/null || return 1
  chmod 755 "$STORAGE_STATE" 2> /dev/null
  storage_unoffer "$mount"
  fs=$(storage_findmnt FSTYPE "$mount")
  n=$(batocera_known_count "$mount")
  printf '%s|%s|%s|%s|%s|batocera|%s\n' "$mount" "${mount##*/}" "${fs:-?}" "$(storage_size_of "$mount" size)" "$id" "$n" \
    >> "$STORAGE_STATE/offer" || return 1
  chmod 644 "$STORAGE_STATE/offer" 2> /dev/null
  log_info "Storage: $mount tem um Batocera filesystem e espera a resposta do frontend"
  return 0
}

# storage_auto MONTAGEM: o que o fliperos-automount faz com um disco montado: o
# que tem um Batocera filesystem nao ganha nada (so a pergunta do frontend);
# os outros ganham a estrutura do FliperOS e a pergunta de uso. Um Batocera
# filesystem ligado numa pasta que a deteccao nao escolhe mais (batocera_stale)
# e ligado de novo na certa.
storage_auto() {
  local mount=$1
  if batocera_detect "$mount" > /dev/null; then
    if batocera_stale "$mount"; then
      batocera_use "$mount" > /dev/null 2>&1 || true
    fi
    storage_offer_batocera "$mount"
    return
  fi
  storage_prepare "$mount" && storage_offer "$mount"
}

# storage_answer MONTAGEM yes|no [batocera]: a resposta do frontend. "yes" liga
# o disco (storage_use, ou batocera_use no tipo batocera); com "no" so fica
# registrado. Dos dois jeitos o disco nao pergunta de novo.
storage_answer() {
  local mount=$1 rc=0
  if [[ ${3:-} == batocera ]]; then
    if [[ $2 == yes ]]; then
      batocera_use "$mount" > /dev/null || { STORAGE_ERROR=$BATOCERA_ERROR; rc=1; }
    fi
    storage_settle "$mount" batocera
    return "$rc"
  fi
  if [[ $2 == yes ]]; then
    storage_use "$mount" || rc=$?
  fi
  storage_settle "$mount"
  return "$rc"
}

# ── Formatar ─────────────────────────────────────────────────────
# storage_device MONTAGEM imprime o dispositivo da particao montada (/dev/sdb1).
storage_device() {
  storage_findmnt SOURCE "$1"
}

# storage_parent_disk DISPOSITIVO: o disco inteiro de uma particao (/dev/sdb1
# -> /dev/sdb); um disco sem particao e ele mesmo.
storage_parent_disk() {
  local parent
  parent=$(lsblk -no PKNAME "$1" 2> /dev/null | head -n 1)
  if [[ -n $parent ]]; then
    printf '/dev/%s\n' "$parent"
  else
    printf '%s\n' "$1"
  fi
}

# storage_system_disks imprime os discos do sistema: o de /, o de /boot e da
# ESP e o da midia de instalacao.
storage_system_disks() {
  local where src
  for where in / /boot /boot/efi /cdrom "${LIVE_MEDIUM:-/run/live/medium}"; do
    src=$(storage_findmnt SOURCE "$where")
    [[ $src == /dev/* ]] || continue
    storage_parent_disk "$src"
  done | sort -u
}

# storage_format_check MONTAGEM: a particao pode ser formatada? (Status 0.) O
# motivo da recusa fica em STORAGE_ERROR, em palavras para a tela.
storage_format_check() {
  local mount=$1 dev disk type sys
  STORAGE_ERROR=""
  mountpoint -q -- "$mount" 2> /dev/null || { STORAGE_ERROR="$mount is not a mounted disk."; return 1; }
  dev=$(storage_device "$mount")
  type=$([[ $dev == /dev/* ]] && lsblk -rno TYPE "$dev" 2> /dev/null | head -n 1)
  case $type in
    part | disk) ;;
    *) STORAGE_ERROR="The disk behind ${mount##*/} could not be found."; return 1 ;;
  esac
  disk=$(storage_parent_disk "$dev")
  while IFS= read -r sys; do
    if [[ $sys == "$disk" ]]; then
      STORAGE_ERROR="This disk also has the FliperOS system or the installation media: it can't be formatted here."
      return 1
    fi
  done < <(storage_system_disks)
  if [[ $(storage_state "$mount") != none ]]; then
    STORAGE_ERROR="The FliperOS folders are using this disk. Choose Back to the main disk first."
    return 1
  fi
  if declare -F batocera_in_use > /dev/null && batocera_in_use "$mount"; then
    STORAGE_ERROR="The Batocera filesystem of this disk is in use. Stop using it first."
    return 1
  fi
  if grep -qF -- "$mount/" "$STORAGE_SQUASH_LIST" 2> /dev/null; then
    STORAGE_ERROR="A packed game folder (Custom games) lives on this disk. Unpack it first."
    return 1
  fi
  if [[ $(lsblk -rno RO "$dev" 2> /dev/null | head -n 1) == 1 ]]; then
    STORAGE_ERROR="This disk is read only."
    return 1
  fi
  if disk_has_holders "$disk"; then
    STORAGE_ERROR="Something else (RAID, LVM, encryption) is using this disk."
    return 1
  fi
  return 0
}

# storage_format_info MONTAGEM imprime "MODELO|TOTAL|ROTULO|FS|USADO|DISPOSITIVO|BATOCERA":
# o que a tela de confirmacao diz do que vai ser apagado.
storage_format_info() {
  local mount=$1 dev disk model total avail fs batocera=0
  dev=$(storage_device "$mount")
  disk=$(storage_parent_disk "$dev")
  model=$(lsblk -dno MODEL "$disk" 2> /dev/null | sed 's/ *$//' | head -n 1)
  total=$(storage_size_of "$mount" size)
  avail=$(storage_size_of "$mount" avail)
  fs=$(storage_findmnt FSTYPE "$mount")
  batocera_detect "$mount" > /dev/null && batocera=1
  [[ $total =~ ^[0-9]+$ && $avail =~ ^[0-9]+$ ]] || { total=0; avail=0; }
  printf '%s|%s|%s|%s|%s|%s|%d\n' "${model:-Unknown disk}" "$total" "${mount##*/}" "${fs:-?}" "$((total - avail))" "$dev" "$batocera"
}

# storage_format MONTAGEM ext4|exfat: apaga a particao do disco e a formata.
# Desmonta, limpa a assinatura antiga, cria o sistema de arquivos e deixa o
# fliperos-automount montar de novo. Imprime "mount=NOVA-MONTAGEM". Status 1: o
# motivo em STORAGE_ERROR.
storage_format() {
  local mount=$1 fs=${2:-} dev tool newmount i
  STORAGE_ERROR=""
  case $fs in
    ext4) tool=mkfs.ext4 ;;
    exfat) tool=mkfs.exfat ;;
    *) STORAGE_ERROR="Unknown format: ${fs:-none}."; return 1 ;;
  esac
  if ! command -v "$tool" > /dev/null 2>&1; then
    STORAGE_ERROR="$tool is not installed. System Update brings it."
    return 1
  fi
  storage_format_check "$mount" || return 1
  dev=$(storage_device "$mount")
  log_info "Storage: formatando $dev ($mount) como $fs"
  if ! umount -- "$mount" 2>> "$FLIPEROS_LOG"; then
    STORAGE_ERROR="Could not unmount ${mount##*/} (is a game or a file open on it?)."
    return 1
  fi
  if ! wipefs -a -- "$dev" >> "$FLIPEROS_LOG" 2>&1; then
    STORAGE_ERROR="Could not erase the old file system (details in the log)."
    return 1
  fi
  if [[ $fs == ext4 ]]; then
    "$tool" -F -m 0 -L "$STORAGE_LABEL" "$dev" >> "$FLIPEROS_LOG" 2>&1
  else
    "$tool" -L "$STORAGE_LABEL" "$dev" >> "$FLIPEROS_LOG" 2>&1
  fi || { STORAGE_ERROR="Could not format the disk (details in the log)."; return 1; }
  udevadm settle 2>> "$FLIPEROS_LOG"
  # O fliperos-automount monta de novo (e prepara a estrutura): o udev avisa.
  udevadm trigger --action=add --name-match="$dev" 2>> "$FLIPEROS_LOG"
  for ((i = 0; i < 30; i++)); do
    newmount=$(findmnt -rno TARGET -S "$dev" 2> /dev/null | head -n 1)
    [[ -n $newmount ]] && break
    sleep 1
  done
  if [[ -z $newmount ]] && id "$FLIPEROS_USER" > /dev/null 2>&1; then
    runuser -u "$FLIPEROS_USER" -- udisksctl mount --no-user-interaction -b "$dev" >> "$FLIPEROS_LOG" 2>&1
    newmount=$(findmnt -rno TARGET -S "$dev" 2> /dev/null | head -n 1)
  fi
  if [[ $newmount != "$STORAGE_MOUNTS"/* ]]; then
    STORAGE_ERROR="The disk was formatted, but did not mount again. Unplug it and plug it back."
    return 1
  fi
  # Um disco de Linux guarda o dono: a raiz dele passa a ser da pessoa.
  [[ $fs == ext4 ]] && chown "$FLIPEROS_USER:" "$newmount" 2> /dev/null
  printf 'mount=%s\n' "$newmount"
  return 0
}

# storage_cli list|prepare MONTAGEM|use MONTAGEM|unuse|offer MONTAGEM|answer
# MONTAGEM yes|no [batocera]|auto MONTAGEM|format-info MONTAGEM|format MONTAGEM
# ext4|exfat: o fliperos-setup --storage. Status 2: pedido errado; 1: nao deu
# (o motivo na saida).
storage_cli() {
  local mount
  case ${1:-} in
    list) storage_list ;;
    offer)
      mount=${2:-}
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      storage_offer "$mount" || return 1
      ;;
    auto)
      mount=${2:-}
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      storage_auto "$mount" || return 1
      ;;
    answer)
      mount=${2:-}
      [[ ${3:-} == yes || ${3:-} == no ]] || return 2
      [[ -z ${4:-} || ${4:-} == batocera ]] || return 2
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      if ! storage_answer "$mount" "$3" "${4:-}"; then
        echo "${STORAGE_ERROR:-Could not use the disk (details in the log).}"
        return 1
      fi
      ;;
    format-info)
      mount=${2:-}
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      if ! storage_format_check "$mount"; then
        echo "$STORAGE_ERROR"
        return 1
      fi
      storage_format_info "$mount"
      ;;
    format)
      mount=${2:-}
      [[ ${3:-} == ext4 || ${3:-} == exfat ]] || return 2
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      if ! storage_format "$mount" "$3"; then
        echo "${STORAGE_ERROR:-Could not format the disk (details in the log).}"
        return 1
      fi
      ;;
    prepare | use)
      mount=${2:-}
      [[ $mount == "$STORAGE_MOUNTS"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      if ! "storage_$1" "$mount"; then
        echo "${STORAGE_ERROR:-Could not use the disk (details in the log).}"
        return 1
      fi
      ;;
    unuse)
      if ! storage_unuse; then
        echo "${STORAGE_ERROR:-Could not stop using the disk (details in the log).}"
        return 1
      fi
      ;;
    *) return 2 ;;
  esac
  return 0
}
