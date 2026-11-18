# shellcheck shell=bash
# Setup > System > Storage: um disco secundario (um HD externo, um SSD ou
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

# storage_mounts imprime os discos de dados montados (um por linha): as pastas
# de /media/fliperos que sao pontos de montagem.
storage_mounts() {
  local dir
  for dir in "$STORAGE_MOUNTS"/*/; do
    dir=${dir%/}
    [[ -d $dir ]] && mountpoint -q -- "$dir" 2> /dev/null && printf '%s\n' "$dir"
  done
  return 0
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
  fs=$(findmnt -rno FSTYPE -T "$mount" 2> /dev/null | head -n 1)
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
    fs=$(findmnt -rno FSTYPE -T "$mount" 2> /dev/null | head -n 1)
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
  ((failed == 0))
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

# storage_cli list|prepare MONTAGEM|use MONTAGEM|unuse: o fliperos-setup
# --storage. Status 2: pedido errado; 1: nao deu (o motivo na saida).
storage_cli() {
  local mount
  case ${1:-} in
    list) storage_list ;;
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
