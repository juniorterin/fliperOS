# shellcheck shell=bash
# O ATOM-15 na BIOS da placa AMD (Setup > Video Setup > Card firmware,
# screens/atom15.sh): a placa ja sai em 15 kHz do POST ate o sistema subir. O
# patch e o config/fliperos-atom15; quem le e grava a BIOS e o amdvbflash, que a
# AMD nao publica e por isso nao vem na imagem nem e baixado: a pessoa poe o
# arquivo em ATOM15_DIR.
#
# Como a troca de driver (lib/bootloader.sh), mas agora o que se testa e o
# firmware: gravada a BIOS nova, o boot seguinte pede a confirmacao
# (screen_atom15_confirm, antes do launcher). Sem resposta, volta a BIOS
# original e reinicia. A vigia do boot (fliperos-atom15-guard.service,
# atom15_boot) cobre a tela que nao chega a abrir e o boot de teste que travou
# e foi desligado no botao. Uma placa que nao passa nem do POST nao chega ate
# aqui: disso nada no sistema protege, e o aviso diz.
#
# Em ATOM15_DIR (a pasta da pessoa, ~/vbios) ficam o backup, a BIOS com o patch
# e o log; em ATOM15_STATE, a copia da BIOS original de que a volta depende e a
# marca do teste. Estado no fliperos.conf: atom15_trial (em teste),
# atom15_trial_boots, atom15_applied (a soma da BIOS confirmada) e atom15_backup
# (o arquivo do backup).
ATOM15_BIN=${ATOM15_BIN:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-atom15}
ATOM15_STATE=${ATOM15_STATE:-/var/lib/fliperos/atom15}
ATOM15_DIR=${ATOM15_DIR:-/home/$FLIPEROS_USER/vbios}
ATOM15_SECONDS=${ATOM15_SECONDS:-90}
ATOM15_GRACE=${ATOM15_GRACE:-300}
ATOM15_EFIVARS=${ATOM15_EFIVARS:-/sys/firmware/efi/efivars}
ATOM15_DEBUGFS=${ATOM15_DEBUGFS:-/sys/kernel/debug/dri}

# atom15_where ARQUIVO: onde esta um arquivo, para a tela: a pasta numa linha e o
# nome em outra (a tela de 320 pontos corta uma linha sem espacos).
atom15_where() {
  local path=${1/#\/home\/$FLIPEROS_USER\//\~\/}
  printf '%s/\n%s' "${path%/*}" "${path##*/}"
}

# atom15_card: a placa principal, se for AMD com BIOS propria.
atom15_card() {
  local card id
  card=$(video_main_card) || return 1
  [[ -n $card ]] || return 1
  id=$(drm_card_id "$card") || return 1
  [[ $id == 1002:* ]] || return 1
  printf '%s\n' "$card"
}

# atom15_device CARD: o id da placa, como o da imagem (6613).
atom15_device() {
  local id
  id=$(drm_card_id "$1") || return 1
  printf '%s\n' "${id#*:}"
}

atom15_trial_active() {
  [[ -e $ATOM15_STATE/trial ]]
}

atom15_applied() {
  conf_get atom15_applied > /dev/null 2>&1
}

# atom15_secure_boot: com o Secure Boot ligado o kernel nao deixa o amdvbflash
# falar com a placa. O ultimo byte da variavel diz.
atom15_secure_boot() {
  local var
  for var in "$ATOM15_EFIVARS"/SecureBoot-*; do
    [[ -r $var ]] || continue
    [[ $(od -An -tu1 -j4 -N1 "$var" 2> /dev/null | tr -d ' ') == 1 ]] && return 0
  done
  return 1
}

# atom15_flasher: a copia do amdvbflash que o root roda (a pasta da pessoa nao
# fica dona do que roda como root). Sem o arquivo, status 1.
atom15_flasher() {
  local given=$ATOM15_DIR/amdvbflash own=$ATOM15_STATE/amdvbflash
  if [[ -f $given ]]; then
    install -D -m 700 -o root -g root "$given" "$own" 2>> "$FLIPEROS_LOG" ||
      install -D -m 700 "$given" "$own" 2>> "$FLIPEROS_LOG" || return 1
  fi
  [[ -x $own ]] || return 1
  printf '%s\n' "$own"
}

# atom15_adapter CARD: "numero tamanho teste" da placa na lista do amdvbflash.
atom15_adapter() {
  local pci flasher bus dev out
  pci=$(drm_card_pci "$1") || return 1
  flasher=$(atom15_flasher) || return 1
  bus=${pci#*:}
  dev=${bus#*:}
  bus=${bus%%:*}
  dev=${dev%%.*}
  out=$(timeout 60 "$flasher" -i 2>> "$FLIPEROS_LOG" < /dev/null) || return 1
  printf '%s\n' "$out" >> "$FLIPEROS_LOG"
  "$ATOM15_BIN" adapter "$bus" "$dev" <<< "$out" 2>> "$FLIPEROS_LOG"
}

# atom15_read ADAPTADOR ARQUIVO: le a BIOS da placa.
atom15_read() {
  local flasher
  flasher=$(atom15_flasher) || return 1
  rm -f "$2"
  timeout 120 "$flasher" -s "$1" "$2" >> "$FLIPEROS_LOG" 2>&1 < /dev/null && [[ -s $2 ]]
}

atom15_info() {
  "$ATOM15_BIN" info "$1" 2>> "$FLIPEROS_LOG" | sed -n "s/^$2=//p"
}

# atom15_user_copy ORIGEM DESTINO: um arquivo na pasta da pessoa.
atom15_user_copy() {
  install -d "$ATOM15_DIR" 2>> "$FLIPEROS_LOG" || return 1
  chown "$FLIPEROS_USER:" "$ATOM15_DIR" 2> /dev/null
  install -m 644 "$1" "$2" 2>> "$FLIPEROS_LOG" || return 1
  chown "$FLIPEROS_USER:" "$2" 2> /dev/null
  return 0
}

# atom15_rom_switch 0|1 ROM: liga e desliga a leitura do arquivo rom do PCI.
atom15_rom_switch() {
  printf '%s' "$1" > "$2"
}

# atom15_kernel_read CARD ARQUIVO: a copia da BIOS que o kernel tem, sem o
# amdvbflash: a do amdgpu no debugfs ou o arquivo rom do PCI. E a BIOS deste boot:
# diz o que a placa tem, mas nunca e gravada de volta (isso so a leitura do chip).
atom15_kernel_read() {
  local card=$1 out=$2 pci path rom
  pci=$(drm_card_pci "$card") || pci=none
  for path in "$ATOM15_DEBUGFS/$pci/amdgpu_vbios" "$ATOM15_DEBUGFS/${card#card}/amdgpu_vbios"; do
    [[ -r $path ]] || continue
    cat "$path" > "$out" 2>> "$FLIPEROS_LOG" && [[ -s $out ]] && return 0
  done
  rom=$DRM_SYSFS/$card/device/rom
  [[ -e $rom ]] || return 1
  atom15_rom_switch 1 "$rom" 2>> "$FLIPEROS_LOG" || return 1
  cat "$rom" > "$out" 2>> "$FLIPEROS_LOG"
  atom15_rom_switch 0 "$rom" 2>> "$FLIPEROS_LOG"
  [[ -s $out ]]
}

# atom15_belongs CARD ARQUIVO: a imagem e uma ATOMBIOS desta placa?
atom15_belongs() {
  local device
  device=$(atom15_device "$1") || device=""
  if [[ $(atom15_info "$2" device) != "$device" || -z $device ]]; then
    ATOM15_ERROR="The BIOS that was read does not belong to this card (or is not an ATOMBIOS)."
    return 1
  fi
}

# atom15_read_checked CARD ADAPTADOR ARQUIVO: le o chip duas vezes e confere.
# Status 1 sem o arquivo, com o motivo em ATOM15_ERROR.
atom15_read_checked() {
  local card=$1 adapter=$2 file=$3 again=$3.again
  if ! atom15_read "$adapter" "$file" || ! atom15_read "$adapter" "$again"; then
    ATOM15_ERROR="The flash tool could not read the BIOS of this card."
    rm -f "$file" "$again"
    return 1
  fi
  if ! cmp -s "$file" "$again"; then
    ATOM15_ERROR="Two reads of the BIOS came out different: the read cannot be trusted."
    rm -f "$file" "$again"
    return 1
  fi
  rm -f "$again"
  atom15_belongs "$card" "$file" || {
    rm -f "$file"
    return 1
  }
}

# atom15_save_original IMAGEM DEVICE: a leitura do chip, sem o patch, vira o
# backup (ATOM15_DIR e ATOM15_STATE), com o caminho em ATOM15_RESULT. Uma copia
# que ja existe nao e trocada.
atom15_save_original() {
  local image=$1 device=$2 sum dest
  sum=$(sha256sum "$image" | cut -c1-8)
  dest=$ATOM15_DIR/original-$device-$sum.rom
  # Outra placa nesta maquina, sem nada em teste: a copia antiga nao vale mais.
  cmp -s "$image" "$ATOM15_STATE/original.rom" || cp "$image" "$ATOM15_STATE/original.rom"
  [[ -e $dest ]] || atom15_user_copy "$image" "$dest" || {
    ATOM15_ERROR="Could not write the backup to $ATOM15_DIR."
    return 1
  }
  if ! cmp -s "$dest" "$ATOM15_STATE/original.rom"; then
    ATOM15_ERROR="The backup in $ATOM15_DIR does not match the BIOS that was read."
    return 1
  fi
  sync
  conf_set atom15_backup "$dest"
  ATOM15_RESULT=$dest
}

# atom15_backup CARD ADAPTADOR: a BIOS original da placa, antes de gravar. Status
# 1 com o motivo em ATOM15_ERROR.
ATOM15_ERROR=""
ATOM15_RESULT=""
atom15_backup() {
  local card=$1 adapter=$2 first rc=0
  install -d -m 700 "$ATOM15_STATE" 2>> "$FLIPEROS_LOG" || {
    ATOM15_ERROR="Could not create $ATOM15_STATE."
    return 1
  }
  first=$ATOM15_STATE/read1.rom
  atom15_read_checked "$card" "$adapter" "$first" || return 1
  if [[ $(atom15_info "$first" patched) == 1 ]]; then
    ATOM15_ERROR="This card already has an ATOM-15 BIOS. The patch has to start from the original one."
    rc=1
  else
    atom15_save_original "$first" "$(atom15_device "$card")" || rc=1
  fi
  rm -f "$first"
  return "$rc"
}

# atom15_inspect CARD: ao abrir o item, le a BIOS da placa e guarda uma copia, para
# que o menu diga o que esta la e nao o que o Setup lembra (a placa pode ter vindo
# com o ATOM-15). Com o amdvbflash le o chip, senao a copia do kernel. So uma
# leitura do chip sem o patch, fora de um teste, pode virar a original; o resto vai
# para card-DEVICE-SOMA.rom. Status 1 quando nao deu para ler. Deixa:
#   ATOM15_FIRMWARE   atom15, other ou vazio
#   ATOM15_READ_FROM  chip, kernel ou vazio
#   ATOM15_COPY       a copia em ATOM15_DIR (vazio com o motivo em ATOM15_ERROR)
#   ATOM15_COPY_NEW   1 se a copia foi feita agora
ATOM15_FIRMWARE=""
ATOM15_READ_FROM=""
ATOM15_COPY=""
ATOM15_COPY_NEW=0
atom15_inspect() {
  local card=$1 file adapter device sum dest
  ATOM15_FIRMWARE="" ATOM15_READ_FROM="" ATOM15_COPY="" ATOM15_COPY_NEW=0 ATOM15_ERROR=""
  install -d -m 700 "$ATOM15_STATE" 2>> "$FLIPEROS_LOG" || {
    ATOM15_ERROR="Could not create $ATOM15_STATE."
    return 1
  }
  file=$ATOM15_STATE/card.rom
  rm -f "$file"
  if atom15_flasher > /dev/null; then
    read -r adapter _ <<< "$(atom15_adapter "$card")"
    [[ -n $adapter ]] && atom15_read_checked "$card" "$adapter" "$file" && ATOM15_READ_FROM=chip
  fi
  if [[ -z $ATOM15_READ_FROM ]]; then
    if atom15_kernel_read "$card" "$file" && atom15_belongs "$card" "$file"; then
      ATOM15_READ_FROM=kernel
      ATOM15_ERROR=""
    else
      [[ -n $ATOM15_ERROR ]] || ATOM15_ERROR="The system has no copy of this card's BIOS."
      log_warn "atom15: sem leitura da BIOS: $ATOM15_ERROR"
      rm -f "$file"
      return 1
    fi
  fi

  device=$(atom15_device "$card")
  sum=$(sha256sum "$file" | cut -c1-8)
  ATOM15_FIRMWARE=other
  [[ $(atom15_info "$file" patched) == 1 ]] && ATOM15_FIRMWARE=atom15
  log_info "atom15: placa lida ($ATOM15_READ_FROM, $sum): $ATOM15_FIRMWARE"
  if [[ $ATOM15_READ_FROM == chip && $ATOM15_FIRMWARE == other ]] && ! atom15_trial_active; then
    # O chip e a verdade: uma marca antiga de "aplicado" nao vale mais.
    conf_unset atom15_applied
    dest=$ATOM15_DIR/original-$device-$sum.rom
    [[ -e $dest ]] || ATOM15_COPY_NEW=1
    if atom15_save_original "$file" "$device"; then
      ATOM15_COPY=$ATOM15_RESULT
    else
      ATOM15_COPY_NEW=0
    fi
  else
    dest=$ATOM15_DIR/card-$device-$sum.rom
    if [[ -e $dest ]]; then
      ATOM15_COPY=$dest
    elif atom15_user_copy "$file" "$dest"; then
      ATOM15_COPY=$dest
      ATOM15_COPY_NEW=1
    else
      ATOM15_ERROR="Could not write the backup to $ATOM15_DIR."
    fi
  fi
  rm -f "$file"
  return 0
}

# atom15_prepare RANGES: faz a BIOS com o patch a partir da original. O caminho
# na pasta da pessoa em ATOM15_RESULT (o log ao lado), o motivo em ATOM15_ERROR.
atom15_prepare() {
  local ranges=$1 device out
  device=$(atom15_info "$ATOM15_STATE/original.rom" device)
  out=$ATOM15_DIR/atom15-$device-${ranges//,/-}khz.rom
  if ! ATOM15_ERROR=$("$ATOM15_BIN" patch "$ATOM15_STATE/original.rom" "$ATOM15_STATE/patched.rom" --ranges "$ranges" \
    --log "$ATOM15_STATE/patched.log" 2>&1); then
    log_warn "atom15: patch recusado: $ATOM15_ERROR"
    return 1
  fi
  ATOM15_ERROR=""
  atom15_user_copy "$ATOM15_STATE/patched.rom" "$out" || {
    ATOM15_ERROR="Could not write to $ATOM15_DIR."
    return 1
  }
  atom15_user_copy "$ATOM15_STATE/patched.log" "${out%.rom}.log" || true
  ATOM15_RESULT=$out
}

# atom15_write ADAPTADOR IMAGEM: grava e le de volta para conferir. O amdvbflash
# sem -f confere o id da placa na imagem e, sem a entrada padrao, desiste em vez
# de esperar uma resposta que ninguem veria. Sem timeout: cortar a gravacao no
# meio e o jeito certo de perder a placa. Status 0 so com a placa igual a imagem.
atom15_write() {
  local adapter=$1 image=$2 flasher back
  flasher=$(atom15_flasher) || return 1
  back=$ATOM15_STATE/readback.rom
  log_info "atom15: gravando $image na placa $adapter ($(sha256sum "$image" | cut -c1-16))"
  "$flasher" -p "$adapter" "$image" >> "$FLIPEROS_LOG" 2>&1 < /dev/null
  log_info "atom15: amdvbflash -p terminou com $?"
  atom15_read "$adapter" "$back" || return 1
  # A leitura vem do tamanho da memoria da placa: confere o que foi gravado.
  if ! cmp -s -n "$(stat -c %s "$image")" "$image" "$back"; then
    log_warn "atom15: a placa nao ficou igual a $image"
    rm -f "$back"
    return 1
  fi
  rm -f "$back"
  sync
  return 0
}

# atom15_flash_trial CARD ADAPTADOR: grava a BIOS com o patch e comeca o teste.
# A marca do teste vai antes da gravacao: se a luz cair no meio, o boot seguinte
# (se houver) volta a original, sem perguntar (a marca "flashed" so vem depois de
# a gravacao conferir). Gravacao que nao confere volta na hora.
atom15_flash_trial() {
  local adapter=$2
  conf_set atom15_trial_boots 0
  conf_set atom15_trial 1
  install -d -m 700 "$ATOM15_STATE"
  : > "$ATOM15_STATE/trial"
  sync
  if atom15_write "$adapter" "$ATOM15_STATE/patched.rom"; then
    : > "$ATOM15_STATE/flashed"
    sync
    return 0
  fi
  log_warn "atom15: a gravacao nao conferiu, de volta a original"
  atom15_write "$adapter" "$ATOM15_STATE/original.rom" && atom15_trial_clear
  return 1
}

# atom15_flashed: a BIOS em teste foi gravada inteira e conferida?
atom15_flashed() {
  [[ -e $ATOM15_STATE/flashed ]]
}

atom15_trial_clear() {
  local key
  rm -f "$ATOM15_STATE/trial" "$ATOM15_STATE/flashed"
  for key in atom15_trial atom15_trial_boots; do
    conf_unset "$key"
  done
  sync
}

atom15_confirm() {
  log_info "atom15: BIOS confirmada"
  conf_set atom15_applied "$(sha256sum "$ATOM15_STATE/patched.rom" 2> /dev/null | cut -c1-16)"
  atom15_trial_clear
}

# atom15_revert: a BIOS original de volta na placa, com o teste em andamento ou
# a pedido. Um so por vez, a tela e a vigia podem chegar juntas. O teste so sai
# com a placa conferida: se a gravacao falha, o proximo boot tenta de novo.
# Status 0: voltou (ou a outra ja voltou). Reiniciar fica com quem chama.
atom15_revert() {
  local card adapter
  (
    flock 9
    if [[ ${1:-} == trial ]] && ! atom15_trial_active; then
      exit 0
    fi
    if [[ ! -s $ATOM15_STATE/original.rom ]]; then
      log_warn "atom15: sem a copia da BIOS original em $ATOM15_STATE"
      exit 1
    fi
    card=$(atom15_card) || exit 1
    read -r adapter _ <<< "$(atom15_adapter "$card")"
    [[ -n $adapter ]] || exit 1
    log_warn "atom15: de volta a BIOS original"
    atom15_write "$adapter" "$ATOM15_STATE/original.rom" || exit 1
    conf_unset atom15_applied
    atom15_trial_clear
  ) 9> "$ATOM15_STATE/lock"
}

# atom15_boot: a vigia, no boot (fliperos-atom15-guard.service). So roda com a
# marca do teste.
atom15_boot() {
  local boots
  atom15_trial_active || return 0
  boots=$(conf_get atom15_trial_boots 2> /dev/null) || boots=0
  [[ $boots =~ ^[0-9]+$ ]] || boots=0
  boots=$((boots + 1))
  conf_set atom15_trial_boots "$boots"
  sync
  # O boot de teste anterior nem confirmou nem voltou: travou.
  if ((boots < 2)); then
    # A tela de confirmacao abre antes do launcher; se ate aqui ela nao
    # resolveu (nao abriu ou ninguem a viu), volta a original.
    sleep "$ATOM15_GRACE"
    atom15_trial_active || return 0
  fi
  if atom15_revert trial; then
    run_logged systemctl reboot
  else
    log_warn "atom15: nao foi possivel voltar a BIOS original (de novo no proximo boot)"
  fi
  return 0
}
