# shellcheck shell=bash
# Quirks (Setup > System > Quirks): correcoes do kernel para dispositivos USB
# que chegam errados. Dois tipos, pelo formato do codigo:
#
#   usbhid.quirks       "0xVENDOR:0xPRODUTO:0xFLAGS" (o sscanf do
#                       hid_quirks_init do kernel): controles, encoders,
#                       pistolas, teclados e mouses, como o encoder duplo que
#                       aparece como um jogador so. O kernel le no maximo 4
#                       (MAX_USBHID_BOOT_QUIRKS).
#   usb-storage.quirks  "VENDOR:PRODUTO:LETRAS", sem 0x (o parse_quirks do
#                       usb-storage): discos e pendrives, como o "u" que
#                       desliga o UAS de um adaptador SATA que trava.
#
# Cada quirk tem um nome dado pela pessoa. /etc/fliperos/quirks.conf guarda
# "codigo|nome", um por linha; a linha do kernel recebe um parametro por tipo
# (boot_compose). Os dois so valem no boot.

QUIRKS_FILE=${QUIRKS_FILE:-$FLIPEROS_ETC/quirks.conf}
QUIRKS_MAX=4
QUIRK_HID_RE='^0x[0-9a-f]{1,4}:0x[0-9a-f]{1,4}:0x[0-9a-f]{1,8}$'
QUIRK_STORAGE_RE='^[0-9a-f]{4}:[0-9a-f]{4}:[a-z]+$'

# quirk_normalize CODIGO imprime o codigo em minusculas e sem espacos, ou
# falha se o kernel nao o aceitar.
quirk_normalize() {
  local code=${1,,}
  code=${code//[[:space:]]/}
  [[ $code =~ $QUIRK_HID_RE || $code =~ $QUIRK_STORAGE_RE ]] || return 1
  printf '%s\n' "$code"
}

# quirk_type CODIGO imprime usbhid ou usb-storage.
quirk_type() {
  [[ $1 == 0x* ]] && echo usbhid || echo usb-storage
}

# quirks_list [TIPO] imprime "codigo|nome" de cada quirk salvo (do TIPO), na
# ordem.
quirks_list() {
  [[ -f $QUIRKS_FILE ]] || return 0
  case ${1:-} in
    usbhid) grep -E '^0x[0-9a-f]+:0x[0-9a-f]+:0x[0-9a-f]+\|' "$QUIRKS_FILE" ;;
    usb-storage) grep -E '^[0-9a-f]{4}:[0-9a-f]{4}:[a-z]+\|' "$QUIRKS_FILE" ;;
    *) grep -E '^(0x[0-9a-f]+:0x[0-9a-f]+:0x[0-9a-f]+|[0-9a-f]{4}:[0-9a-f]{4}:[a-z]+)\|' "$QUIRKS_FILE" ;;
  esac
  return 0
}

# quirks_count [TIPO]: quantos quirks salvos (do TIPO).
quirks_count() {
  local list
  list=$(quirks_list "${1:-}")
  [[ -n $list ]] || { echo 0; return 0; }
  printf '%s\n' "$list" | wc -l
}

# quirk_add NOME CODIGO salva um quirk. Status 1: codigo invalido; 2: ja ha
# QUIRKS_MAX do usbhid; 3: o mesmo dispositivo (vendor:produto) ja tem quirk
# desse tipo.
quirk_add() {
  local name=$1 code device type list
  code=$(quirk_normalize "$2") || return 1
  device=${code%:*}
  type=$(quirk_type "$code")
  list=$(quirks_list "$type")
  [[ $'\n'$list == *$'\n'"$device:"* ]] && return 3
  if [[ $type == usbhid ]] && (($(quirks_count usbhid) >= QUIRKS_MAX)); then
    return 2
  fi
  # O nome e so para a lista: uma linha, sem o separador.
  name=${name//[|$'\n'$'\t']/ }
  name=$(printf '%s' "$name" | sed 's/^ *//; s/ *$//')
  [[ -n $name ]] || name=$device
  mkdir -p "$(dirname "$QUIRKS_FILE")"
  printf '%s|%s\n' "$code" "$name" >> "$QUIRKS_FILE" || return 1
  chmod 644 "$QUIRKS_FILE"
  log_info "quirk: + $code ($name)"
}

# quirk_delete CODIGO apaga o quirk.
quirk_delete() {
  local code=$1 tmp
  [[ -f $QUIRKS_FILE ]] || return 1
  tmp=$(mktemp "$QUIRKS_FILE.XXXXXX") || return 1
  if ! awk -F'|' -v c="$code" '$1 != c' "$QUIRKS_FILE" > "$tmp"; then
    rm -f "$tmp"
    return 1
  fi
  chmod 644 "$tmp"
  mv -f "$tmp" "$QUIRKS_FILE" || return 1
  log_info "quirk: - $code"
}

# quirks_cmdline LINHA troca o usbhid.quirks e o usb-storage.quirks da linha
# do kernel pelos dos quirks salvos (ou os tira, se nao houver nenhum).
quirks_cmdline() {
  local word out=() codes
  for word in $1; do
    [[ $word == usbhid.quirks=* || $word == usb-storage.quirks=* ]] && continue
    out+=("$word")
  done
  codes=$(quirks_list usbhid | cut -d'|' -f1 | head -n "$QUIRKS_MAX" | paste -sd, -)
  [[ -n $codes ]] && out+=("usbhid.quirks=$codes")
  codes=$(quirks_list usb-storage | cut -d'|' -f1 | paste -sd, -)
  [[ -n $codes ]] && out+=("usb-storage.quirks=$codes")
  printf '%s\n' "${out[*]}"
}

# quirks_usb_devices lista os dispositivos USB ligados agora, com o
# vendor:produto ja no formato do codigo.
quirks_usb_devices() {
  local line id rest
  while IFS= read -r line; do
    [[ $line =~ ID\ ([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\ ?(.*)$ ]] || continue
    id="0x${BASH_REMATCH[1],,}:0x${BASH_REMATCH[2],,}"
    rest=${BASH_REMATCH[3]}
    # Os hubs internos nao precisam de quirk.
    [[ $rest == *"root hub"* ]] && continue
    printf '%s  %s\n' "$id" "${rest:-unknown device}"
  done < <(lsusb 2> /dev/null)
}
