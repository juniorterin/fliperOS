# shellcheck shell=bash
# O firmware do leitor de cartuchos (Setup > System > Cartridge reader,
# screens/setup-menu.sh): o do Open Source Cartridge Reader com o patch do
# FliperOS (patches/oscr), que manda o dump pela USB para o frontend
# (gui/femedia.py). Os .hex vem em config/oscr (tools/oscr-firmware.sh: o HW5
# com a chave de tensao e o HW5 com o modulo VSELECT) e ficam em
# OSCR_FIRMWARE_DIR. Quem grava e o avrdude, pelo bootloader do Mega na porta
# USB, como o OSCR Tool. Antes de gravar, o firmware que estava e lido para
# OSCR_BACKUP_DIR (~/oscr) e anotado no fliperos.conf (oscr_backup): o
# Restore o grava de volta.
OSCR_FIRMWARE_DIR=${OSCR_FIRMWARE_DIR:-/usr/local/share/fliperos/oscr}
OSCR_BACKUP_DIR=${OSCR_BACKUP_DIR:-/home/$FLIPEROS_USER/oscr}
OSCR_SYS_TTY=${OSCR_SYS_TTY:-/sys/class/tty}
OSCR_DEV_DIR=${OSCR_DEV_DIR:-/dev}
OSCR_AVRDUDE=${OSCR_AVRDUDE:-avrdude}
OSCR_MEDIA=${OSCR_MEDIA:-$SETUP_DIR/gui/femedia.py}

# oscr_ports imprime a porta de cada OSCR ligado: o conversor CH340 do HW5 ou
# o de um Arduino Mega (os mesmos do femedia.oscr_ports).
oscr_ports() {
  local tty node i ids
  for tty in "$OSCR_SYS_TTY"/ttyUSB* "$OSCR_SYS_TTY"/ttyACM*; do
    [[ -e $tty/device ]] || continue
    node=$(readlink -f "$tty/device")
    for ((i = 0; i < 5; i++)); do
      [[ -f $node/idVendor ]] && break
      node=${node%/*}
    done
    ids="$(cat "$node/idVendor" 2> /dev/null):$(cat "$node/idProduct" 2> /dev/null)"
    case ${ids,,} in
      1a86:7523 | 2341:0042 | 2341:0010 | 2a03:0042) printf '%s/%s\n' "$OSCR_DEV_DIR" "${tty##*/}" ;;
    esac
  done
}

# oscr_firmware VARIANTE imprime o .hex do FliperOS: hw5 (a chave de tensao)
# ou hw5-vselect (o modulo VSELECT). Status 1: nao ha.
oscr_firmware() {
  local name
  case $1 in
    hw5) name=OSCR-HW5-fliperos.hex ;;
    hw5-vselect) name=OSCR-HW5-VSELECT-fliperos.hex ;;
    *) return 1 ;;
  esac
  [[ -f $OSCR_FIRMWARE_DIR/$name ]] || return 1
  printf '%s\n' "$OSCR_FIRMWARE_DIR/$name"
}

# oscr_avrdude PORTA ARGUMENTOS...: o avrdude no bootloader do Mega (stk500v2,
# 115200), sem apagar o chip antes (-D: o bootloader regrava as paginas).
oscr_avrdude() {
  local port=$1
  shift
  "$OSCR_AVRDUDE" -p atmega2560 -c wiring -P "$port" -b 115200 -D "$@"
}

# oscr_check PORTA: o OSCR responde ao frontend (o firmware do FliperOS)?
oscr_check() {
  python3 "$OSCR_MEDIA" oscr-hello "$1"
}

# oscr_backup_file imprime o backup gravado, se o arquivo ainda existe.
oscr_backup_file() {
  local backup
  backup=$(conf_get oscr_backup) || return 1
  [[ -f $backup ]] || return 1
  printf '%s\n' "$backup"
}

# oscr_flash PORTA VARIANTE: le o firmware de agora para o backup e grava o
# do FliperOS, com os eventos de progresso (lib/progress.sh).
oscr_flash() {
  local port=$1 hex backup
  ev_step 2 "Finding the FliperOS firmware"
  hex=$(oscr_firmware "$2") || {
    ev_fail "the firmware file is missing ($OSCR_FIRMWARE_DIR)"
    return 1
  }
  mkdir -p "$OSCR_BACKUP_DIR" || {
    ev_fail "could not create $OSCR_BACKUP_DIR"
    return 1
  }
  backup=$OSCR_BACKUP_DIR/oscr-backup-$(date +%Y%m%d-%H%M%S).hex
  ev_step 5 "Saving the firmware the OSCR has now"
  ev_run oscr_avrdude "$port" -U "flash:r:$backup:i" || return 1
  [[ -s $backup ]] || {
    ev_fail "the backup came out empty"
    return 1
  }
  chown -R "$FLIPEROS_USER:" "$OSCR_BACKUP_DIR" 2> /dev/null
  conf_set oscr_backup "$backup"
  ev_msg "Backup: $backup"
  ev_step 50 "Writing the FliperOS firmware. Keep the cable in"
  ev_run oscr_avrdude "$port" -U "flash:w:$hex:i" || return 1
  ev_step 92 "Checking that the OSCR answers"
  ev_run oscr_check "$port" || return 1
  log_info "firmware do OSCR gravado: $hex em $port (backup $backup)"
  ev_step 100 "Done"
}

# oscr_restore PORTA: grava de volta o backup (o firmware de antes).
oscr_restore() {
  local port=$1 backup
  backup=$(oscr_backup_file) || {
    ev_fail "there is no backup"
    return 1
  }
  ev_step 10 "Writing the firmware back. Keep the cable in"
  ev_run oscr_avrdude "$port" -U "flash:w:$backup:i" || return 1
  log_info "firmware do OSCR de volta: $backup em $port"
  ev_step 100 "Done"
}
