# shellcheck shell=bash
# Joysticks na porta paralela (Setup > LPT joysticks): os drivers db9,
# gamecon e turbografx do kernel (Documentation/input/devices/
# joystick-parport.rst). A porta em si o kernel acha sozinho quando ela
# existe (parport_pc, pela ACPI da placa-mae ou por uma placa PCI/PCIe); o
# adaptador ligado nela nao tem como ser detectado, entao a pessoa escolhe e
# o setup grava as opcoes do modulo.
#
# fliperos.conf guarda "lpt=DRIVER PORTA VALOR..." (os numeros do parametro
# do modulo). Dali saem /etc/modprobe.d/fliperos-lpt.conf (options) e
# /etc/modules-load.d/fliperos-lpt.conf (carrega no boot).

LPT_MODPROBE_CONF=${LPT_MODPROBE_CONF:-/etc/modprobe.d/fliperos-lpt.conf}
LPT_MODULES_CONF=${LPT_MODULES_CONF:-/etc/modules-load.d/fliperos-lpt.conf}
PARPORT_SYSFS=${PARPORT_SYSFS:-/sys/bus/parport/devices}
PARPORT_PROC=${PARPORT_PROC:-/proc/sys/dev/parport}
PROC_INPUT=${PROC_INPUT:-/proc/bus/input/devices}
LPT_DRIVERS="db9 gamecon turbografx"

# lpt_types DRIVER imprime "numero|nome" dos tipos do driver: os enums de
# db9.c e gamecon.c; no turbografx o numero e o de botoes de cada joystick.
lpt_types() {
  case $1 in
    db9)
      printf '%s\n' "1|Multisystem 1-button joystick (Atari, Amiga, SMS)" \
        "2|Multisystem 2-button joystick" "3|Sega Genesis pad (3+1 buttons)" \
        "5|Sega Genesis pad (5+1 buttons)" "6|Sega Genesis pad (6+2 buttons)" \
        "7|Sega Saturn pad" "8|Multisystem 1-button (v0.8.0.2 pin-out)" \
        "9|Two Multisystem 1-button (v0.8.0.2 pin-out)" "10|Amiga CD32 pad" \
        "11|Sega Saturn pad (DPP adapter)" "12|Two Sega Saturn pads (DPP adapter)"
      ;;
    gamecon)
      printf '%s\n' "0|None" "1|SNES pad" "2|NES pad" "3|NES FourPort" \
        "4|Multisystem 1-button joystick" "5|Multisystem 2-button joystick" \
        "6|N64 pad" "7|PlayStation pad" "8|PlayStation DDR mat" "9|SNES mouse"
      ;;
    turbografx)
      printf '%s\n' "1|1 button" "2|2 buttons" "3|3 buttons" "4|4 buttons" "5|5 buttons"
      ;;
    *) return 1 ;;
  esac
}

lpt_type_label() {
  lpt_types "$1" | awk -F'|' -v n="$2" '$1 == n { print $2; exit }'
}

# lpt_options DRIVER PORTA VALOR... imprime a linha "options" do modulo, ou
# falha se o kernel nao aceitaria: db9 tem um tipo por porta, gamecon ate 5
# pads, turbografx ate 7 joysticks.
lpt_options() {
  local driver=$1 port=$2 max v
  shift 2
  [[ $port =~ ^[0-9]$ ]] || return 1
  case $driver in
    db9) max=1 ;;
    gamecon) max=5 ;;
    turbografx) max=7 ;;
    *) return 1 ;;
  esac
  (($# >= 1 && $# <= max)) || return 1
  local any=0
  for v in "$@"; do
    [[ $v =~ ^[0-9]+$ ]] || return 1
    # 0 e "nada nesta posicao" (gamecon e turbografx).
    if ((v == 0)); then
      [[ $driver != db9 ]] || return 1
      continue
    fi
    [[ -n $(lpt_type_label "$driver" "$v") ]] || return 1
    any=1
  done
  ((any)) || return 1
  local IFS=,
  case $driver in
    db9) printf 'options db9 dev=%s,%s\n' "$port" "$*" ;;
    *) printf 'options %s map=%s,%s\n' "$driver" "$port" "$*" ;;
  esac
}

# lpt_current imprime "DRIVER PORTA VALOR..." da configuracao (vazio = sem
# joystick na paralela).
lpt_current() {
  conf_get lpt 2> /dev/null || true
}

# lpt_write [RAIZ] refaz os dois arquivos a partir do fliperos.conf.
lpt_write() {
  local root=${1:-} current options
  current=$(lpt_current)
  if [[ -z $current ]]; then
    rm -f "$root$LPT_MODPROBE_CONF" "$root$LPT_MODULES_CONF"
    return 0
  fi
  # shellcheck disable=SC2086 # "DRIVER PORTA VALOR..." em palavras
  options=$(lpt_options $current) || return 1
  mkdir -p "$(dirname "$root$LPT_MODPROBE_CONF")" "$(dirname "$root$LPT_MODULES_CONF")"
  {
    echo "# Gerado pelo fliperos-setup (Setup > LPT joysticks); refeito a cada mudanca."
    echo "# O driver de impressora registraria a porta, e os de joystick a querem so"
    echo "# para eles (\"cannot grant exclusive access\")."
    echo "blacklist lp"
    echo "$options"
  } > "$root$LPT_MODPROBE_CONF"
  printf 'parport_pc\n%s\n' "${current%% *}" > "$root$LPT_MODULES_CONF"
}

# lpt_set DRIVER PORTA VALOR... grava a configuracao (status 1: invalida).
lpt_set() {
  lpt_options "$@" > /dev/null || return 1
  conf_set lpt "$*"
  lpt_write
}

lpt_disable() {
  conf_unset lpt
  lpt_write
  log_info "lpt: desligado"
}

# lpt_reload tira os drivers de joystick (e o de impressora) e carrega o da
# configuracao, que le as opcoes do modprobe.d.
lpt_reload() {
  local current driver
  # shellcheck disable=SC2086 # nomes de modulo
  run_logged modprobe -r $LPT_DRIVERS lp 2> /dev/null
  current=$(lpt_current)
  [[ -n $current ]] || return 0
  driver=${current%% *}
  run_logged modprobe parport_pc
  run_logged modprobe "$driver"
}

# lpt_ports imprime "NUMERO|parportN (endereco, modos)" das portas que o
# kernel achou.
lpt_ports() {
  local dev name n base modes
  for dev in "$PARPORT_SYSFS"/parport*; do
    [[ -e $dev ]] || continue
    name=${dev##*/}
    n=${name#parport}
    [[ $n =~ ^[0-9]+$ ]] || continue
    base=$(awk '{ printf "0x%x", $1 }' "$PARPORT_PROC/$name/base-addr" 2> /dev/null)
    modes=$(cat "$PARPORT_PROC/$name/modes" 2> /dev/null)
    printf '%s|%s (%s%s)\n' "$n" "$name" "${base:-?}" "${modes:+, $modes}"
  done
}

# lpt_devices lista os joysticks que os drivers criaram (Phys=parportN/...).
lpt_devices() {
  [[ -r $PROC_INPUT ]] || return 0
  awk 'BEGIN { RS = ""; FS = "\n" } {
    name = ""; phys = ""
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^N: Name=/) { name = substr($i, 10); gsub(/"/, "", name) }
      if ($i ~ /^P: Phys=/) phys = substr($i, 9)
    }
    if (phys ~ /^parport[0-9]/) { split(phys, p, "/"); print p[1] ": " name }
  }' "$PROC_INPUT"
}

# lpt_describe resume a configuracao para a tela.
lpt_describe() {
  local current driver port out="" v
  current=$(lpt_current)
  [[ -n $current ]] || { echo "off"; return 0; }
  read -r driver port _ <<< "$current"
  for v in ${current#* * }; do
    [[ $v == 0 ]] && continue
    out+="${out:+; }$(lpt_type_label "$driver" "$v")"
  done
  printf '%s on parport%s: %s\n' "$driver" "$port" "$out"
}
