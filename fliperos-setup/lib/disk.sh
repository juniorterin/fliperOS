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
# ou com dependentes ativos; e a propria midia de instalacao. Disquete nem
# aparece. O fabricante sai quando e so um codigo ("ATA", ou o "0x1af4"
# do virtio, que nao tem modelo).
disk_list() {
  local live
  live=$(disk_live_device 2> /dev/null) || live=""
  # Cada disco e avaliado dentro de um try: um campo estranho num deles (um
  # leitor de cartao sem midia, um tamanho vazio) nao pode sumir com os
  # outros da lista, como acontecia quando o jq parava no primeiro erro.
  disk_inventory | jq -r --arg live "$live" --argjson min "$DISK_MIN_BYTES" '
    def tree: ., (.children // [] | .[] | tree);
    def text: if . == null then "" else tostring | gsub("^\\s+|\\s+$"; "") end;
    .blockdevices[]
    | select(.type == "disk")
    | select((.path // "" | test("^/dev/(loop|ram|zram|sr|fd)")) | not)
    | . as $d
    | try (
        ($d.size // 0 | tonumber? // 0) as $size
        | ([$d | tree | .mountpoints // [] | .[] | select(. != null)] | length) as $mounted
        | ([$d | tree | select(.type != "disk" and .type != "part")] | length) as $complex
        | (if ($d.path == $live) then "Installation media (this USB/DVD)"
           elif ($d.ro == true or $d.ro == "1") then "Read-only"
           elif ($size == 0) then "No media"
           elif ($size < $min) then "Smaller than 16 GiB"
           elif ($mounted > 0) then "In use (mounted or swap)"
           elif ($complex > 0) then "Has RAID/LVM/encryption"
           else "" end) as $why
        | ([$d.vendor, $d.model] | map(text)
            | map(select(. != "" and . != "ATA" and (test("^0x[0-9a-fA-F]+$") | not)))
            | join(" ")) as $name
        | [ $d.path,
            (if $name == "" and ($d.path | test("^/dev/vd")) then "Virtual disk" else $name end),
            ($size | tostring),
            ($d.tran | text),
            (if ($d.rm == true or $d.rm == "1" or $d.hotplug == true or $d.hotplug == "1" or $d.tran == "usb") then "1" else "0" end),
            $why ] | join("|")
      ) catch ([$d.path, ($d.model | text), "0", "", "0", "Could not read this drive"] | join("|"))' |
    while IFS='|' read -r path model size tran rm why; do
      if [[ -z $why ]] && disk_has_holders "$path"; then
        why="Has active dependent devices"
      fi
      printf '%s|%s|%s|%s|%s|%s\n' "$path" "$model" "$size" "$tran" "$rm" "$why"
    done
}

# disk_details imprime tudo o que o Linux ve de discos, para quando um HD ou
# SSD nao aparece na lista: o lsblk completo, as mensagens do kernel sobre
# as controladoras e o que costuma esconder um disco.
disk_details() {
  echo "Drives seen by Linux:"
  echo
  lsblk -o NAME,TYPE,SIZE,TRAN,MODEL,FSTYPE,MOUNTPOINTS 2>&1
  echo
  echo "Storage controllers:"
  lspci 2> /dev/null | grep -iE 'sata|ahci|raid|nvme|non-volatile|ide|storage' || echo "  (none found by lspci)"
  echo
  echo "Kernel messages about drives:"
  dmesg 2> /dev/null | grep -iE 'ahci|nvme|ata[0-9]+:|sd[a-z]+\]|raid|vmd|rst' | tail -n 40
  echo
  echo "A drive missing from this list is not visible to Linux. The usual causes:"
  echo "- BIOS SATA mode set to RAID or Intel RST/Optane: change it to AHCI."
  echo "- NVMe behind Intel VMD: disable VMD in the BIOS."
  echo "- Loose data or power cable."
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
# testes conferem o layout sem tocar em disco nenhum). O wipefs do disco so
# apaga as assinaturas dele; as particoes novas caem em cima de dados
# antigos, entao as assinaturas delas saem tambem, e a de BIOS boot (1 MiB)
# e zerada: um resto de sistema de arquivos ali faz o Limine recusar.
disk_partition_commands() {
  local disk=$1 p1 p2 p3
  p1=$(disk_partition_path "$disk" 1)
  p2=$(disk_partition_path "$disk" 2)
  p3=$(disk_partition_path "$disk" 3)
  printf '%s\n' \
    "wipefs --all $disk" \
    "parted --script $disk mklabel gpt mkpart BIOS 1MiB 2MiB set 1 bios_grub on mkpart EFI fat32 2MiB 1026MiB set 2 esp on mkpart FliperOS ext4 1026MiB 100%" \
    "partprobe $disk" \
    "udevadm settle" \
    "wipefs --all $p1 $p2 $p3" \
    "dd if=/dev/zero of=$p1 bs=1M count=1 conv=fsync status=none" \
    "mkfs.vfat -F32 -n FLIPERBOOT $p2" \
    "mkfs.ext4 -F -L FliperOS $p3"
}
