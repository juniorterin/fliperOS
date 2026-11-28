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
echo '01:00.0 "VGA compatible controller" "Advanced Micro Devices, Inc. [AMD/ATI]" "Oland PRO [Radeon R7 240/340 / Radeon 520]" -r87 "Advanced Micro Devices, Inc. [AMD/ATI]" "Device 0b0c"'
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

# Setup > System > Services sem systemd: a tabela de um gabinete.
demo_services() {
  services_rows() {
    printf '%s\n' "ssh|SSH|boot|$(services_field ssh 4)" "samba|Network share|after|$(services_field samba 4)" \
      "avahi|fliperos.local|boot|$(services_field avahi 4)" "wifi|Wi-Fi|off|$(services_field wifi 4)" \
      "downloader|Downloader|after|$(services_field downloader 4)"
  }
  services_save() { :; }
  screen_services
}

# Video Setup > Interlaced hacks num gabinete de 15 kHz, com tudo instalado e
# alguns programas ja entrelacados.
demo_mode480() {
  export RA_HOME=$FAKE/retroarch
  mode480_installed() { return 0; }
  conf_set frequency 15k
  mode480_set flycast filter medium
  mode480_set pcsx2 filter strong
  mode480_set psx pure
  screen_mode480
}

# Video Setup > Colour calibration com uma placa como a do gabinete (tabela
# de gama, sem CTM, output_csc).
demo_colour() {
  COLOR_BIN=$FAKE/bin/fliperos-color
  printf '#!/bin/sh\n[ "$1" = caps ] && printf "lut 256\\nctm no\\nrange output_csc\\n"\nexit 0\n' > "$COLOR_BIN"
  chmod +x "$COLOR_BIN"
  conf_set color_brightness 3
  conf_set color_temperature 9300
  screen_colour
}

# Setup > Games > Folders > External storage: um HD externo com um Batocera
# filesystem (batocera/roms/<console>, bios, saves) e outro, comum, de 500 GB;
# em ~ uma pasta de ROMs com um atalho para o primeiro.
demo_external() {
  local media=$FAKE/media home=$FAKE/home name n
  FOLDERS_HOME=$home FOLDERS_MOUNTS=$media STORAGE_MOUNTS=$media STORAGE_STATE=$FAKE/state FOLDERS_SCRIPT=$FAKE/none
  BATOCERA_TABLE=$SRC/config/batocera-systems.list BATOCERA_LIST=$home/.config/fliperos/batocera.list
  RA_INFO_DIR=$FAKE/info RA_CORES_DIR=$FAKE/cores ROMS_DIR=$home/roms CUSTOM_GAMES_PACKAGES=$home/roms/custom-packages
  mkdir -p "$home/roms/mame" "$home/bios" "$home/media" "$FAKE/info" "$FAKE/cores" "$media/TOSHIBA" "$home/.config/fliperos"
  for name in snes megadrive psx atomiswave naomi gba n64 mame dreamcast neogeo atari2600 pcengine; do
    mkdir -p "$media/BATOCERA/batocera/roms/$name"
    for n in 1 2 3; do : > "$media/BATOCERA/batocera/roms/$name/game$n.zip"; done
  done
  mkdir -p "$media/BATOCERA/batocera/roms/zzz-unknown" "$media/BATOCERA/batocera/bios" "$media/BATOCERA/batocera/saves"
  printf 'display_name = "%s"\ncorename = "%s"\nsystemid = "%s"\nsupported_extensions = "%s"\n' \
    Snes9x Snes9x super_nes "smc|sfc" > "$FAKE/info/snes9x_libretro.info"
  printf 'display_name = "%s"\ncorename = "%s"\nsystemid = "%s"\nsupported_extensions = "%s"\n' \
    bsnes bsnes super_nes "smc|sfc" > "$FAKE/info/bsnes_libretro.info"
  printf 'display_name = "%s"\ncorename = "%s"\nsystemid = "%s"\nsupported_extensions = "%s"\n' \
    "Genesis Plus GX" "Genesis Plus GX" mega_drive "md|bin" > "$FAKE/info/genesis_plus_gx_libretro.info"
  # Os cores que a tabela prefere para os consoles da demonstracao.
  while IFS='|' read -r name corename sysid exts; do
    printf 'display_name = "%s"\ncorename = "%s"\nsystemid = "%s"\nsupported_extensions = "%s"\n' \
      "$corename" "$corename" "$sysid" "$exts" > "$FAKE/info/${name}_libretro.info"
  done << 'EOF'
stella|Stella|atari_2600|a26|bin
mgba|mGBA|game_boy_advance|gba|gb
pcsx_rearmed|PCSX-ReARMed|playstation|cue|bin|chd
mupen64plus_next|Mupen64Plus-Next|nintendo_64|n64|z64
mednafen_pce_fast|Beetle PCE Fast|pc_engine|pce|chd
fbneo|FinalBurn Neo|neogeo|zip
EOF
  : > "$FAKE/cores/snes9x_libretro.so"
  : > "$FAKE/cores/genesis_plus_gx_libretro.so"
  cat > "$FAKE/bin/mountpoint" << 'EOF'
#!/bin/bash
for last; do :; done
case "$last" in /tmp/fliperos-demo.*/media/*) exit 0 ;; esac
exit 1
EOF
  cat > "$FAKE/bin/df" << 'EOF'
#!/bin/bash
for last; do :; done
size=500107862016
case "$last" in */BATOCERA) size=1000204886016 ;; esac
case "$*" in *size*) echo Size; echo "$size" ;; *avail*) echo Avail; echo "$((size * 6 / 10))" ;; esac
EOF
  cat > "$FAKE/bin/findmnt" << 'EOF'
#!/bin/bash
for last; do :; done
case "$*" in
  *UUID*) echo "UUID-${last##*/}" ;;
  *FSTYPE*) case "$last" in */BATOCERA) echo ntfs ;; *) echo exfat ;; esac ;;
esac
EOF
  chmod +x "$FAKE/bin/mountpoint" "$FAKE/bin/df" "$FAKE/bin/findmnt"
  folders_cli_refresh() { :; }
  frontends_configure() { :; }
}

demo_folders() { demo_external; screen_folders; }
demo_external_hub() { demo_external; screen_external_storage; }
# O mesmo menu, com o azulejo do Batocera filesystem ja escolhido (o harness nao fotografa uma troca de selecao).
demo_external_hub_batocera() {
  demo_external
  eval "$(declare -f ui_menu_hints | sed '1s/ui_menu_hints/ui_menu_hints_real/')"
  ui_menu_hints() { ui_menu_hints_real "$1" "$2" batocera "${@:4}"; }
  screen_external_storage
}
# Formatar: a confirmacao, a escolha do formato e a ultima chance, sem formatar nada.
demo_format() {
  demo_external
  storage_cli() {
    case $1 in
      format-info) echo "WD Elements 25A2|1000204886016|TOSHIBA|exfat|612345678901|/dev/sdb1|0" ;;
      *) echo "demo: nothing is formatted" ;;
    esac
  }
  screen_storage_format "$FAKE/media/TOSHIBA"
}
# External storage com o azulejo da Network folder ja escolhido.
demo_external_hub_netshare() {
  demo_external
  eval "$(declare -f ui_menu_hints | sed '1s/ui_menu_hints/ui_menu_hints_real/')"
  ui_menu_hints() { ui_menu_hints_real "$1" "$2" netshare "${@:4}"; }
  screen_external_storage
}
# Network folder: duas pastas guardadas (uma em uso, outra com o computador
# desligado), sem montar nada.
demo_netshare_fake() {
  demo_external
  netshare_available() { return 0; }
  netshare_list() {
    printf '%s\n' "retronas|192.168.1.20|retronas|retronas|$FAKE/media/retronas|mounted" \
      "ps2|192.168.1.20|ps2|retronas|$FAKE/media/ps2|waiting"
  }
  netshare_offline() { [[ $1 == */ps2 ]]; }
  netshare_in_use() { [[ $1 == */retronas ]]; }
}
demo_netshares() { demo_netshare_fake; screen_netshares; }
demo_netshare_one() { demo_netshare_fake; screen_netshare_one retronas; }
demo_storage() { demo_external; screen_storage; }
demo_batocera() { demo_external; screen_batocera; }
# O Batocera filesystem ja ligado: os consoles com o core de cada um.
demo_batocera_used() {
  demo_external
  batocera_use "$FAKE/media/BATOCERA" > /dev/null
  screen_batocera_disk "$FAKE/media/BATOCERA"
}
demo_cores() {
  demo_external
  batocera_use "$FAKE/media/BATOCERA" > /dev/null
  screen_batocera_consoles "$FAKE/media/BATOCERA"
}
demo_shortcuts() {
  demo_external
  folders_link roms/mame "$FAKE/media/TOSHIBA" > /dev/null 2>&1
  screen_folders_shortcuts
}

case ${1:-} in
  mode480) demo_mode480 ;;
  colour) demo_colour ;;
  progress) demo_progress ;;
  failed) demo_failed ;;
  results) demo_results ;;
  testing) demo_testing ;;
  confirm) demo_confirm ;;
  main) demo_main ;;
  services) demo_services ;;
  *) "$@" ;;
esac
