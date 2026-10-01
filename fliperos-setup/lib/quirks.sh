# shellcheck shell=bash
# Quirks do usbhid (Setup > Quirks): correcoes do kernel para controles USB
# que chegam errados, como o encoder duplo que aparece como um jogador so.
#
# Cada quirk tem um nome dado pela pessoa e o codigo do parametro
# usbhid.quirks, "0xVENDOR:0xPRODUTO:0xFLAGS" (o sscanf do hid_quirks_init
# do kernel). /etc/fliperos/quirks.conf guarda "codigo|nome", um por linha;
# a linha do kernel recebe usbhid.quirks=codigo1,codigo2 (boot_compose). O
# kernel le no maximo 4 (MAX_USBHID_BOOT_QUIRKS) e so no boot.

QUIRKS_FILE=${QUIRKS_FILE:-$FLIPEROS_ETC/quirks.conf}
QUIRKS_MAX=4

# quirk_normalize CODIGO imprime o codigo em minusculas e sem espacos, ou
# falha se o kernel nao o aceitar.
quirk_normalize() {
  local code=${1,,}
  code=${code//[[:space:]]/}
  [[ $code =~ ^0x[0-9a-f]{1,4}:0x[0-9a-f]{1,4}:0x[0-9a-f]{1,8}$ ]] || return 1
  printf '%s\n' "$code"
}

# quirks_list imprime "codigo|nome" de cada quirk salvo, na ordem.
quirks_list() {
  [[ -f $QUIRKS_FILE ]] || return 0
  grep -E '^0x[0-9a-f]+:0x[0-9a-f]+:0x[0-9a-f]+\|' "$QUIRKS_FILE" || true
}

quirks_count() {
  local list
  list=$(quirks_list)
  [[ -n $list ]] || { echo 0; return 0; }
  printf '%s\n' "$list" | wc -l
}

# quirk_add NOME CODIGO salva um quirk. Status 1: codigo invalido; 2: ja ha
# QUIRKS_MAX; 3: o mesmo dispositivo (vendor:produto) ja tem quirk.
quirk_add() {
  local name=$1 code device list
  code=$(quirk_normalize "$2") || return 1
  device=${code%:*}
  list=$(quirks_list)
  [[ $'\n'$list == *$'\n'"$device:"* ]] && return 3
  (($(quirks_count) < QUIRKS_MAX)) || return 2
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

# quirks_cmdline LINHA troca o usbhid.quirks da linha do kernel pelo dos
# quirks salvos (ou o tira, se nao houver nenhum).
quirks_cmdline() {
  local word out=() codes
  for word in $1; do
    [[ $word == usbhid.quirks=* ]] && continue
    out+=("$word")
  done
  codes=$(quirks_list | cut -d'|' -f1 | head -n "$QUIRKS_MAX" | paste -sd, -)
  [[ -n $codes ]] && out+=("usbhid.quirks=$codes")
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
    # Hubs internos nao sao controles.
    [[ $rest == *"root hub"* ]] && continue
    printf '%s  %s\n' "$id" "${rest:-unknown device}"
  done < <(lsusb 2> /dev/null)
}
