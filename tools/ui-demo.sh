#!/usr/bin/env bash
# Abre uma tela do fliperos-setup num sistema falso (GPU Radeon com VGA-1,
# dois discos, rede), para conferir o layout sem hardware nem ISO:
#
#   tools/ui-demo.sh TELA [LARGURA ALTURA]
#
# Roda dentro de um tmux do tamanho pedido (80x30 = 640x480 com a fonte
# 8x16; 64x24 = 512x384) no container do tools/ui-snapshot.sh. Nenhum
# comando de sistema de verdade e executado: particionar, montar, nmcli e
# afins sao funcoes vazias aqui.
#
# As telas leem variaveis globais (resultado do teste, disco escolhido) que
# as funcoes demo_* preenchem.
# shellcheck disable=SC2034
set -o pipefail
shopt -s extglob

SRC=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
FAKE=$(mktemp -d /tmp/fliperos-demo.XXXXXX)

export DRM_SYSFS=$FAKE/drm FLIPEROS_ETC=$FAKE/etc FLIPEROS_CONF=$FAKE/etc/fliperos.conf
export FLIPEROS_LOG=$FAKE/setup.log PROC_CMDLINE=$FAKE/cmdline SWITCHRES_INI=$FAKE/etc/switchres.ini
export MAME_INI=$FAKE/etc/mame.ini XORG_CONF=$FAKE/etc/xorg.conf BOOT_DEFAULTS=$FAKE/etc/fliperos-boot
export SESSIONS_TABLE=$SRC/config/fliperos-sessions.conf SESSION_FILE=$FAKE/etc/session
export VIDEO_CHECK=$FAKE/bin/fliperos-video-check FLIPEROS_NO_SPEECH=1 PATH=$FAKE/bin:$PATH
export DISK_INVENTORY_JSON=$FAKE/lsblk.json LIVE_MEDIUM=$FAKE/nomedium SYS_BLOCK=$FAKE/sysblock

mkdir -p "$DRM_SYSFS/card0-VGA-1" "$DRM_SYSFS/card0-DVI-D-1" "$FAKE/pci/0000:01:00.0/graphics/fb0" \
  "$FAKE/drivers/radeon" "$FLIPEROS_ETC" "$FAKE/bin"
ln -s "$FAKE/drivers/radeon" "$FAKE/pci/0000:01:00.0/driver"
mkdir -p "$DRM_SYSFS/card0" && ln -s "$FAKE/pci/0000:01:00.0" "$DRM_SYSFS/card0/device"
printf 'disconnected\n' > "$DRM_SYSFS/card0-VGA-1/status"
printf '640x480i\n640x480\n' > "$DRM_SYSFS/card0-VGA-1/modes"
: > "$DRM_SYSFS/card0-VGA-1/edid"
printf 'disconnected\n' > "$DRM_SYSFS/card0-DVI-D-1/status"
: > "$DRM_SYSFS/card0-DVI-D-1/edid"
printf '%s\n' "${DEMO_CMDLINE:-boot=live fliperos.boot=15khz video=640x480iS quiet splash}" > "$PROC_CMDLINE"
cat > "$FAKE/bin/lspci" << 'EOF'
#!/bin/bash
echo '"01:00.0" "VGA compatible controller" "Advanced Micro Devices, Inc. [AMD/ATI]" "Oland [Radeon HD 8570 / R7 240/340]" "" ""'
EOF
cat > "$FAKE/bin/fliperos-video-check" << 'EOF'
#!/bin/bash
echo '{"outputs":[{"card":"/dev/dri/card0","connector":"VGA-1","active":true,"width":640,"height":480,"horizontal_khz":15.690,"vertical_hz":59.98,"interlaced":true}]}'
EOF
cat > "$FAKE/bin/hostname" << 'EOF'
#!/bin/bash
echo fliperos
EOF
cat > "$FAKE/bin/ip" << 'EOF'
#!/bin/bash
echo '2: eth0    inet 192.168.0.20/24 brd 192.168.0.255 scope global eth0'
EOF
chmod +x "$FAKE"/bin/*
cat > "$DISK_INVENTORY_JSON" << 'EOF'
{"blockdevices":[
 {"path":"/dev/sda","type":"disk","size":500107862016,"model":"Samsung SSD 870 EVO","vendor":"ATA","serial":"S1","tran":"sata","rm":false,"hotplug":false,"ro":false,"mountpoints":[null]},
 {"path":"/dev/nvme0n1","type":"disk","size":1000204886016,"model":"KINGSTON SNV2S1000G","vendor":null,"serial":"S2","tran":"nvme","rm":false,"hotplug":false,"ro":false,"mountpoints":[null]},
 {"path":"/dev/sdb","type":"disk","size":32010928128,"model":"Ultra","vendor":"SanDisk","serial":"S3","tran":"usb","rm":true,"hotplug":true,"ro":false,"mountpoints":[null],
  "children":[{"path":"/dev/sdb1","type":"part","size":32010928128,"mountpoints":["/run/live/medium"]}]}
]}
EOF
printf '\tmonitor                   arcade_15\n' > "$SWITCHRES_INI"


for f in "$SRC"/fliperos-setup/lib/*.sh "$SRC"/fliperos-setup/screens/*.sh; do
  # shellcheck source=/dev/null
  source "$f"
done
drm_set_status() { :; }
sleep() { :; }
recovery_find() { :; }
speak() { :; }

UI_STATUS="fliperos (192.168.0.20)"
ui_init

demo_progress() {
  {
    printf '@step 3 Creating the partition table\n'
    printf '@msg Partitions created on /dev/sda\n'
    printf '@step 8 Copying system files\n'
    printf '@pct 52\n'
    read -r _ < /dev/tty
  } | screen_progress "Installing FliperOS" "Samsung SSD 870 EVO (/dev/sda, 500 GB)"
}

demo_failed() {
  PROGRESS_FAIL_STEP="Installing the bootloader"
  PROGRESS_FAIL_MSG="limine: failed to open /dev/sda: Device or resource busy"
  screen_progress_failed "Installation failed"
}

demo_results() {
  OT_CONN=card0-VGA-1
  OT_FLAGS=se
  VT_STATUS=disconnected
  VT_FORCED=1
  screen_testing_results
}

demo_testing() {
  ui_timed_confirm "Testing output VGA-1" 600 "I can see this screen" \
    "$(ui_fields "Output|VGA-1" "GPU|AMD Radeon HD 8570 / R7 240/340" "Test|round 1 of 3")" "" \
    "If you can see this screen clearly, press ENTER." \
    "If nothing happens, the next output is tested in 10 seconds."
}

demo_confirm() {
  DISK_CHOSEN=/dev/sda
  screen_disk_confirm
}

demo_main() {
  UI_STATUS="fliperos (192.168.0.20) - 23% used on /"
  screen_main_menu
}

case ${1:-} in
  progress) demo_progress ;;
  failed) demo_failed ;;
  results) demo_results ;;
  testing) demo_testing ;;
  confirm) demo_confirm ;;
  main) demo_main ;;
  *) "$@" ;;
esac
