# shellcheck shell=bash
# Discos: inventario, o que pode receber a instalacao e o particionamento.
#
# Um so layout GPT serve para BIOS e UEFI sem mexer na NVRAM (validado em
# VM): 1 MiB de BIOS boot (estagio 2 do Limine), 1 GiB de ESP FAT32 (o
# Limine so le FAT, entao kernel e initrd moram nela) e o resto em ext4.

DISK_MIN_BYTES=${DISK_MIN_BYTES:-$((16 * 1024 * 1024 * 1024))}
LIVE_MEDIUM=${LIVE_MEDIUM:-/run/live/medium}

# disk_inventory imprime o JSON do lsblk (um ponto so para os testes
# trocarem por um arquivo).
disk_inventory() {
  if [[ -n ${DISK_INVENTORY_JSON:-} ]]; then
    cat "$DISK_INVENTORY_JSON"
    return
  fi
  lsblk --json --bytes --paths \
    -o PATH,TYPE,SIZE,MODEL,VENDOR,SERIAL,TRAN,RM,HOTPLUG,RO,MOUNTPOINTS,LABEL
}

# disk_live_device imprime o disco de onde a midia live foi iniciada.
disk_live_device() {
  local src parent
  src=$(findmnt -n -o SOURCE "$LIVE_MEDIUM" 2> /dev/null) || return 1
  [[ -n $src ]] || return 1
  parent=$(lsblk -no PKNAME "$src" 2> /dev/null | head -1)
  if [[ -n $parent ]]; then
    printf '/dev/%s\n' "$parent"
  else
    printf '%s\n' "$src"
  fi
}

# disk_list imprime uma linha por disco:
#   caminho|modelo|tamanho em bytes|barramento|removivel|motivo da recusa
# (motivo vazio = disco elegivel). Recusa como o instalador anterior: disco
# pequeno, somente leitura, montado (midia live, swap), com RAID/LVM/cripto
# ou com dependentes ativos; e a propria midia de instalacao.
disk_list() {
  local live
  live=$(disk_live_device 2> /dev/null) || live=""
  disk_inventory | jq -r --arg live "$live" --argjson min "$DISK_MIN_BYTES" '
    def tree: ., (.children // [] | .[] | tree);
    .blockdevices[]
    | select(.type == "disk")
    | select((.path | test("^/dev/(loop|ram|zram|sr)")) | not)
    | . as $d
    | ([$d | tree | .mountpoints // [] | .[] | select(. != null)] | length) as $mounted
    | ([$d | tree | select(.type != "disk" and .type != "part")] | length) as $complex
    | (if ($d.path == $live) then "Installation media (this USB/DVD)"
       elif ($d.ro == true or $d.ro == "1") then "Read-only"
       elif (($d.size | tonumber) < $min) then "Smaller than 16 GiB"
       elif ($mounted > 0) then "In use (mounted or swap)"
       elif ($complex > 0) then "Has RAID/LVM/encryption"
       else "" end) as $why
    | [ $d.path,
        ([$d.vendor, $d.model] | map(select(. != null) | gsub("^\\s+|\\s+$"; ""))
          | map(select(. != "" and . != "ATA")) | join(" ")),
        ($d.size | tostring),
        ($d.tran // ""),
        (if ($d.rm == true or $d.rm == "1" or $d.hotplug == true or $d.hotplug == "1" or $d.tran == "usb") then "1" else "0" end),
        $why ] | join("|")' |
    while IFS='|' read -r path model size tran rm why; do
      if [[ -z $why ]] && disk_has_holders "$path"; then
        why="Has active dependent devices"
      fi
      printf '%s|%s|%s|%s|%s|%s\n' "$path" "$model" "$size" "$tran" "$rm" "$why"
    done
}

# disk_has_holders DISCO: disco ou particao com dependente ativo (dm, md).
disk_has_holders() {
  local name=${1##*/} dir
  for dir in "${SYS_BLOCK:-/sys/block}/$name/holders" "${SYS_BLOCK:-/sys/block}/$name"/"$name"*/holders; do
    [[ -d $dir ]] || continue
    [[ -n $(ls -A "$dir" 2> /dev/null) ]] && return 0
  done
  return 1
}

# disk_describe CAMINHO imprime "Modelo (caminho, tamanho, USB)".
disk_describe() {
  local line path model size tran rm
  line=$(disk_list | awk -F'|' -v p="$1" '$1 == p' | head -1)
  [[ -n $line ]] || { echo "$1"; return; }
  IFS='|' read -r path model size tran rm _ <<< "$line"
  [[ -n $model ]] || model="Unknown disk"
  local extra=""
  ((rm)) && extra=", removable"
  [[ $tran == usb ]] && extra=", USB"
  printf '%s (%s, %s%s)\n' "$model" "$path" "$(human_size "$size")" "$extra"
}

# disk_identity CAMINHO imprime tamanho, serial e modelo, para conferir que
# o disco nao mudou entre a escolha e a gravacao.
disk_identity() {
  disk_inventory | jq -r --arg p "$1" '
    .blockdevices[] | select(.path == $p) | [.size, .serial, .model] | map(tostring) | join("|")'
}

# disk_partition_path DISCO N: nvme0n1 e mmcblk0 levam "p" antes do numero.
disk_partition_path() {
  local disk=$1 n=$2
  if [[ $disk =~ [0-9]$ ]]; then
    printf '%sp%s\n' "$disk" "$n"
  else
    printf '%s%s\n' "$disk" "$n"
  fi
}

# disk_partition_commands DISCO imprime os comandos, um por linha (os
# testes conferem o layout sem tocar em disco nenhum).
disk_partition_commands() {
  local disk=$1
  printf '%s\n' \
    "wipefs --all $disk" \
    "parted --script $disk mklabel gpt mkpart BIOS 1MiB 2MiB set 1 bios_grub on mkpart EFI fat32 2MiB 1026MiB set 2 esp on mkpart FliperOS ext4 1026MiB 100%" \
    "partprobe $disk" \
    "udevadm settle" \
    "mkfs.vfat -F32 -n FLIPERBOOT $(disk_partition_path "$disk" 2)" \
    "mkfs.ext4 -F -L FliperOS $(disk_partition_path "$disk" 3)"
}
