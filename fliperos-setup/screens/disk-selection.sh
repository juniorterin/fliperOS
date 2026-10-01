# shellcheck shell=bash
# Escolha do disco ("Automatically Partition", como no gasetup) e a
# confirmacao destrutiva. O disco aparece pelo modelo e tamanho, nao so pelo
# /dev/sdX; USB e removivel ficam marcados, e a propria midia de instalacao
# nunca e oferecida.

DISK_CHOSEN=""
DISK_IDENTITY=""
DISK_LABEL=""

# disk_menu_label MODELO TAMANHO CAMINHO BARRAMENTO REMOVIVEL
disk_menu_label() {
  local model=$1 size=$2 path=$3 tran=$4 rm=$5 kind=""
  [[ -n $model ]] || model="Unknown disk"
  ((${#model} > 30)) && model="${model:0:29}~"
  case $tran in
    usb) kind="USB" ;;
    nvme) kind="NVMe" ;;
    sata | ata) kind="SATA" ;;
    *) ((rm)) && kind="removable" ;;
  esac
  printf '%-30s %8s  %-13s %s\n' "$model" "$(human_size "$size")" "$path" "$kind"
}

# screen_disk_selection preenche DISK_CHOSEN, DISK_IDENTITY e DISK_LABEL.
# Status 1 = voltar.
screen_disk_selection() {
  local lines=() entries=() refused=() line path model size tran rm why choice text
  while true; do
    ui_info "Automatically Partition" "Looking for drives..."
    mapfile -t lines < <(disk_list)
    entries=()
    refused=()
    for line in "${lines[@]}"; do
      IFS='|' read -r path model size tran rm why <<< "$line"
      if [[ -z $why ]]; then
        entries+=("$path|$(disk_menu_label "$model" "$size" "$path" "$tran" "$rm")")
      else
        refused+=("$path ${model:+($model) }- $why")
      fi
    done
    text="Select the HD/SSD for the installation. The whole drive will be used."
    if ((${#refused[@]})); then
      text+=$'\n\n'"Not available:"
      for line in "${refused[@]}"; do
        text+=$'\n'"  $line"
      done
    fi
    if ((${#entries[@]} == 0)); then
      text+=$'\n\n'"No drive can receive the installation (at least 16 GiB, not in use)."
    fi
    choice=$(ui_menu "Automatically Partition" "$text" "" "${entries[@]}" \
      "rescan|Rescan drives" "details|My drive is not listed (details)" "return|Return") || return 1
    case $choice in
      rescan) continue ;;
      details)
        disk_details > "/tmp/fliperos-drives.txt" 2>&1
        ui_pager "Drives" "/tmp/fliperos-drives.txt"
        continue
        ;;
      return) return 1 ;;
    esac
    DISK_CHOSEN=$choice
    DISK_IDENTITY=$(disk_identity "$choice")
    DISK_LABEL=$(disk_describe "$choice")
    return 0
  done
}

# screen_disk_confirm pergunta antes de apagar. Status 0 = pode apagar.
screen_disk_confirm() {
  local line path model size tran rm installed="" text
  line=$(disk_list | awk -F'|' -v p="$DISK_CHOSEN" '$1 == p' | head -1)
  IFS='|' read -r path model size tran rm _ <<< "$line"
  if recovery_find 2> /dev/null | grep -q "^$DISK_CHOSEN|"; then
    installed=$'\n\n'"This drive already has FliperOS installed. To keep ROMs and settings, choose No and use Recovery Mode instead."
  fi
  text=$(printf 'All data on:\n\n  %s\n  %s\n  %s%s\n\nwill be permanently deleted.%s\n\nContinue?' \
    "${model:-Unknown disk}" "$path" "$(human_size "${size:-0}")" \
    "$([[ $tran == usb ]] && echo "  (USB)")" "$installed")
  speak "Warning. All data on the selected drive will be deleted."
  ui_yesno "WARNING" "$text" no
}
