# shellcheck shell=bash
# Setup > Games > Folders > External storage > Batocera filesystem: um disco com
# a estrutura do Batocera (batocera/roms/<console>, e irmas como bios, saves,
# nvram, snap). Cada pasta de console vira um SISTEMA dos frontends, com o core
# que a pessoa escolhe, lido no lugar: nada e movido nem ligado em ~/roms. A
# tabela de nomes e config/batocera-systems.list (o nome da pasta do Batocera e
# o do console, nao o do core do RetroArch).
#
#   ~/.config/fliperos/batocera.list   SISTEMA<tab>PASTA<tab>ESCOLHA, uma por linha
#
# ESCOLHA e "retroarch/<core>" ou uma pasta de emulador do FliperOS (ps1, ps2,
# dolphin, dreamcast...). A chave do sistema nos frontends e "batocera/<nome>"
# (lib/scraper.sh: scraper_detect e scraper_attract_emulator).
#
# "Usar" o disco (batocera_use) liga tudo o que ele tem: os consoles (com o
# core padrao), cada pasta irma (bios, saves, nvram, snap/media) como atalho da
# pasta de mesmo papel em ~ e as pastas de sistemas que so o FliperOS tem
# (namco2x6, fightcade, custom-packages...), criadas ao lado dos consoles. Nada
# e escrito dentro das pastas de console.
#
#   fliperos-setup --batocera detect|scan|list|cores|set|unset|use|unuse|repair|auto|extras

BATOCERA_TABLE=${BATOCERA_TABLE:-/usr/local/share/fliperos/batocera-systems.list}
BATOCERA_LIST=${BATOCERA_LIST:-${FOLDERS_HOME:-/home/$FLIPEROS_USER}/.config/fliperos/batocera.list}
# Quantos consoles da tabela uma pasta roms/ precisa ter para ser um Batocera.
BATOCERA_MIN=${BATOCERA_MIN:-3}
# Pastas fixas do fliperos-roms que NAO vao para o disco do Batocera: o custom
# so tem os .sh gerados do Setup, presos ao ~/games do gabinete.
BATOCERA_LOCAL="custom retroarch"
# Por que o ultimo pedido foi recusado, em palavras para a tela.
BATOCERA_ERROR=""

declare -gA BATOCERA_LABEL=() BATOCERA_PLATFORM=() BATOCERA_DEFAULT=() BATOCERA_ALSO=()
BATOCERA_LOADED=""

# batocera_load: a tabela em memoria (uma vez por processo). Status 1: sem tabela.
batocera_load() {
  local name label platform default also
  [[ $BATOCERA_LOADED == "$BATOCERA_TABLE" ]] && return 0
  [[ -f $BATOCERA_TABLE ]] || return 1
  BATOCERA_LABEL=() BATOCERA_PLATFORM=() BATOCERA_DEFAULT=() BATOCERA_ALSO=()
  while IFS='|' read -r name label platform default also; do
    [[ -n $name && $name != \#* && -n $default ]] || continue
    BATOCERA_LABEL[$name]=$label
    BATOCERA_PLATFORM[$name]=$platform
    BATOCERA_DEFAULT[$name]=$default
    BATOCERA_ALSO[$name]=$also
  done < "$BATOCERA_TABLE"
  BATOCERA_LOADED=$BATOCERA_TABLE
  return 0
}

# batocera_known NOME: a tabela tem esse console?
batocera_known() {
  batocera_load || return 1
  [[ -n ${BATOCERA_LABEL[$1]:-} ]]
}

batocera_label() {
  batocera_load || return 1
  printf '%s\n' "${BATOCERA_LABEL[$1]:-$1}"
}

batocera_platform() {
  batocera_load || return 1
  printf '%s\n' "${BATOCERA_PLATFORM[$1]:-}"
}

batocera_default() {
  batocera_load || return 1
  printf '%s\n' "${BATOCERA_DEFAULT[$1]:-}"
}

# batocera_names: os nomes da tabela, um por linha.
batocera_names() {
  batocera_load || return 0
  printf '%s\n' "${!BATOCERA_LABEL[@]}" | LC_ALL=C sort
}

# batocera_score PASTA imprime quanto jogo tem a roms/ da PASTA: as entradas de
# dentro de cada pasta de console da tabela (jogos, ou pastas de jogo), sem o
# que o Batocera poe ao lado (gamelist.xml, _info.txt, images/, videos/...). As
# pastas so do FliperOS (hypseus, fightcade, namco2x6...) nao estao na tabela e
# nao contam: o batocera_use as enche de subpastas. Serve para escolher entre
# duas roms/ do mesmo disco.
batocera_score() {
  local sub
  local -a subs=()
  for sub in "$1/roms"/*/; do
    [[ -d $sub ]] || continue
    sub=${sub%/}
    batocera_known "${sub##*/}" && subs+=("$sub")
  done
  ((${#subs[@]})) || { echo 0; return 0; }
  { find "${subs[@]}" -mindepth 1 -maxdepth 1 \
    ! -name 'gamelist*.xml' ! -name _info.txt ! -name images ! -name videos ! -name manuals \
    ! -name media ! -name 'downloaded_*' ! -name '.*' -printf x 2> /dev/null || true; } | wc -c | tr -d ' '
}

# batocera_roms_folders imprime as pastas de roms/ que o fliperos-roms cria
# (config/fliperos-roms), uma por linha; sem o script, nada.
batocera_roms_folders() {
  [[ -f ${FOLDERS_SCRIPT:-} ]] || return 0
  sed -n 's/^folder "\$roms\/\([A-Za-z0-9_-]*\)[/"].*/\1/p' "$FOLDERS_SCRIPT" | awk '!seen[$0]++'
}

# batocera_detect MONTAGEM imprime a pasta raiz do Batocera filesystem do disco
# (a que tem a roms/ dentro): MONTAGEM/batocera, MONTAGEM/userdata ou a propria
# MONTAGEM, com pelo menos BATOCERA_MIN pastas de console da tabela em roms/. A
# arvore do FliperOS (MONTAGEM/fliperos, ou uma roms/ com retroarch/) nao e
# Batocera: ela tem mame, naomi e atomiswave tambem. Uma roms/ com retroarch/
# ainda e Batocera quando tem BATOCERA_MIN consoles que o fliperos-roms nao cria
# (snes, megadrive, psx...): foi a pessoa que apontou ~/roms para ela, e o
# fliperos-roms escreveu nela as pastas dele. Com duas ou mais pastas, vale a que
# tem mais jogos (batocera_score; empatadas, a primeira da lista): num disco de
# Batocera de verdade a raiz e o /userdata dele, e uma pasta batocera/ ao lado (a
# copia do esqueleto, com um jogo de exemplo por console) ganhava so por vir
# primeiro (caso de 2026-11-26). Status 1: nao ha.
batocera_detect() {
  local mount=$1 dir sub name n only best score best_score fixed=" retroarch "
  local -a found=()
  [[ -d $mount ]] || return 1
  fixed+=$(batocera_roms_folders | tr '\n' ' ')
  for dir in "$mount/batocera" "$mount/userdata" "$mount"; do
    [[ -d $dir/roms && $dir != */"${STORAGE_NAME:-fliperos}" ]] || continue
    n=0
    only=0
    for sub in "$dir/roms"/*/; do
      [[ -d $sub ]] || continue
      sub=${sub%/}
      name=${sub##*/}
      if batocera_known "$name"; then
        n=$((n + 1))
        [[ $fixed == *" $name "* ]] || only=$((only + 1))
      fi
    done
    # Com o retroarch/ a roms/ so e Batocera se o fliperos-roms nao explica as pastas
    # (e sem o script dele nao ha como saber: vale a regra de antes).
    if [[ -e $dir/roms/retroarch ]] && { [[ ! -f ${FOLDERS_SCRIPT:-} ]] || ((only < BATOCERA_MIN)); }; then
      continue
    fi
    ((n >= BATOCERA_MIN)) && found+=("$dir")
  done
  ((${#found[@]})) || return 1
  best=${found[0]}
  if ((${#found[@]} > 1)); then
    best_score=$(batocera_score "$best")
    for dir in "${found[@]:1}"; do
      score=$(batocera_score "$dir")
      if ((score > best_score)); then
        best=$dir
        best_score=$score
      fi
    done
  fi
  printf '%s\n' "$best"
}

# batocera_in_roms MONTAGEM PASTA: a PASTA e de dentro da roms/ de alguma das
# pastas que o batocera_detect olha no disco?
batocera_in_roms() {
  [[ $2 == "$1/batocera/roms/"* || $2 == "$1/userdata/roms/"* || $2 == "$1/roms/"* ]]
}

# batocera_count PASTA EXTENSOES: os arquivos da pasta (so o primeiro nivel: o
# Batocera tem images/, videos/ e gamelist.xml ao lado dos jogos) com uma das
# extensoes (".a;.b").
batocera_count() {
  local dir=$1 exts=";${2,,};" f ext n=0
  for f in "$dir"/*; do
    [[ -f $f ]] || continue
    ext=.${f##*.}
    [[ $exts == *";${ext,,};"* ]] && n=$((n + 1))
  done
  printf '%d\n' "$n"
}

# ── As escolhas (batocera.list) ──────────────────────────────────

# batocera_list_read imprime "SISTEMA<tab>PASTA<tab>ESCOLHA" das linhas que servem.
batocera_list_read() {
  local system folder choice
  [[ -f $BATOCERA_LIST ]] || return 0
  while IFS=$'\t' read -r system folder choice; do
    batocera_known "$system" && [[ $folder == /* && -n $choice ]] || continue
    printf '%s\t%s\t%s\n' "$system" "$folder" "$choice"
  done < "$BATOCERA_LIST"
  return 0
}

# batocera_list_write LINHAS: grava em ordem e so se mudou (a data do arquivo
# decide quem vence na nuvem, como o folders.list). Sem linhas e sem lista, nada.
batocera_list_write() {
  local content tmp
  content=$(LC_ALL=C sort -u <<< "$1" | sed '/^$/d')
  if [[ -f $BATOCERA_LIST ]]; then
    [[ $(< "$BATOCERA_LIST") == "$content" ]] && return 0
  else
    [[ -n $content ]] || return 0
  fi
  folders_mkdir "${BATOCERA_LIST%/*}" || return 1
  tmp=$(mktemp "$BATOCERA_LIST.XXXXXX") || return 1
  [[ -z $content ]] || printf '%s\n' "$content" > "$tmp"
  chmod 644 "$tmp"
  mv -f -- "$tmp" "$BATOCERA_LIST" || return 1
  folders_own "$BATOCERA_LIST"
  return 0
}

# batocera_entry SISTEMA imprime "PASTA<tab>ESCOLHA" do console na lista.
batocera_entry() {
  local system folder choice
  while IFS=$'\t' read -r system folder choice; do
    [[ $system == "$1" ]] || continue
    printf '%s\t%s\n' "$folder" "$choice"
    return 0
  done < <(batocera_list_read)
  return 1
}

# batocera_choice SISTEMA imprime o que abre o console (a escolha da lista).
batocera_choice() {
  local entry
  entry=$(batocera_entry "$1") || return 1
  printf '%s\n' "${entry#*$'\t'}"
}

# batocera_folder SISTEMA imprime a pasta do console.
batocera_folder() {
  local entry
  entry=$(batocera_entry "$1") || return 1
  printf '%s\n' "${entry%%$'\t'*}"
}

# batocera_valid ESCOLHA: abre alguma coisa? (retroarch/<core> ou uma pasta de
# emulador do FliperOS que o scraper_attract_emulator conhece.)
batocera_valid() {
  [[ $1 != batocera/* && -n $1 ]] && [[ -n $(scraper_attract_emulator "$1" 2> /dev/null) ]]
}

# batocera_set SISTEMA PASTA ESCOLHA grava (ou troca) o console na lista.
batocera_set() {
  local system=$1 folder=$2 choice=$3 line lines=""
  BATOCERA_ERROR=""
  if ! batocera_known "$system"; then
    BATOCERA_ERROR="$system is not a console FliperOS knows."
    return 1
  fi
  if [[ $folder != /* || ! -d $folder ]]; then
    BATOCERA_ERROR="$folder is not a folder."
    return 1
  fi
  if ! batocera_valid "$choice"; then
    BATOCERA_ERROR="$choice does not open games."
    return 1
  fi
  while IFS= read -r line; do
    [[ -n $line && ${line%%$'\t'*} != "$system" ]] && lines+=$line$'\n'
  done < <(batocera_list_read)
  lines+=$system$'\t'$folder$'\t'$choice
  batocera_list_write "$lines"
}

# batocera_unset SISTEMA tira o console da lista.
batocera_unset() {
  local line lines=""
  while IFS= read -r line; do
    [[ -n $line && ${line%%$'\t'*} != "$1" ]] && lines+=$line$'\n'
  done < <(batocera_list_read)
  batocera_list_write "$lines"
}

# ── O que abre, e com quais cores ────────────────────────────────

# batocera_zip EXTENSOES: os jogos do Batocera vem quase sempre em .zip; o
# RetroArch os abre, e a lista dos cores (.info) nao diz isso.
batocera_zip() {
  local exts=$1
  [[ ";$exts;" == *";.zip;"* ]] || exts+="${exts:+;}.zip"
  [[ ";$exts;" == *";.7z;"* ]] || exts+=";.7z"
  printf '%s\n' "$exts"
}

# batocera_emulator CHAVE imprime "nome|executavel|argumentos|extensoes" do
# console "batocera/<nome>" (o scraper_attract_emulator dele): o do que foi
# escolhido, com o nome do console na frente. Status 1: sem escolha.
batocera_emulator() {
  local system=${1#batocera/} choice name exe args exts detail
  choice=$(batocera_choice "$system") || return 1
  [[ $choice != batocera/* ]] || return 1
  IFS='|' read -r name exe args exts <<< "$(scraper_attract_emulator "$choice")"
  [[ -n $name ]] || return 1
  case $choice in
    retroarch/*)
      detail=$(scraper_core_info "${choice#retroarch/}" corename)
      detail=${detail:-${choice#retroarch/}}
      exts=$(batocera_zip "$exts")
      ;;
    *) detail=$name ;;
  esac
  name="$(batocera_label "$system") ($detail)"
  printf '%s|%s|%s|%s\n' "${name//\//-}" "$exe" "$args" "$exts"
}

# batocera_resolve CHAVE: a chave de baixo de um "batocera/<nome>" (a escolha:
# "retroarch/snes9x", "ps1"); qualquer outra chave volta como veio. Quem decide
# por chave (a BIOS, o tema, a arte) pergunta por aqui.
batocera_resolve() {
  local choice
  if [[ $1 == batocera/* ]]; then
    choice=$(batocera_choice "${1#batocera/}") || return 1
    printf '%s\n' "$choice"
  else
    printf '%s\n' "$1"
  fi
}

# batocera_info_systemids imprime "core|systemid" de cada .info (uma passada).
batocera_info_systemids() {
  awk -F' *= *' '
    FNR == 1 { core = FILENAME; sub(/.*\//, "", core); sub(/_libretro\.info$/, "", core) }
    $1 == "systemid" { v = $2; gsub(/"/, "", v); print core "|" v }
  ' "$RA_INFO_DIR"/*_libretro.info 2> /dev/null
}

# batocera_cores SISTEMA imprime as escolhas do console, "ESCOLHA|ROTULO|ESTADO|PADRAO":
# o padrao primeiro, as da tabela, e os cores do RetroArch que o .info diz serem
# do mesmo sistema. ESTADO: installed, download (o core baixa no primeiro jogo)
# ou emulator (uma pasta de emulador do FliperOS).
batocera_cores() {
  local system=$1 platform default choice core sysid label state seen=" "
  local -a list=() extra
  batocera_known "$system" || return 1
  platform=${BATOCERA_PLATFORM[$system]}
  default=${BATOCERA_DEFAULT[$system]}
  list+=("$default")
  IFS=, read -r -a extra <<< "${BATOCERA_ALSO[$system]}"
  list+=("${extra[@]}")
  while IFS='|' read -r core sysid; do
    [[ -n $core ]] || continue
    [[ $(scraper_libretro_platform "$sysid") == "$platform" ]] && list+=("retroarch/$core")
  done < <(batocera_info_systemids)
  for choice in "${list[@]}"; do
    [[ -n $choice && $seen != *" $choice "* ]] || continue
    seen+="$choice "
    case $choice in
      retroarch/*)
        core=${choice#retroarch/}
        if [[ -e $RA_CORES_DIR/${core}_libretro.so ]]; then
          state=installed
        elif [[ -f $RA_INFO_DIR/${core}_libretro.info ]]; then
          state=download
        else
          continue
        fi
        label=$(scraper_core_info "$core" corename)
        label=${label:-$core}
        ;;
      *)
        IFS='|' read -r label _ <<< "$(scraper_attract_emulator "$choice")"
        [[ -n $label ]] || continue
        state=emulator
        ;;
    esac
    printf '%s|%s|%s|%d\n' "$choice" "${label//|/ }" "$state" "$([[ $choice == "$default" ]] && echo 1 || echo 0)"
  done
  return 0
}

# batocera_scan MONTAGEM imprime os consoles do disco que o FliperOS conhece,
# "SISTEMA|ROTULO|PASTA|JOGOS|ESCOLHA|PADRAO" (ESCOLHA vazia: ainda sem core). As
# pastas que a tabela nao tem ficam de fora; batocera_unknown as conta.
# Status 1: o disco nao tem Batocera filesystem.
batocera_scan() {
  local root sub name entry choice effective exts
  batocera_load || return 1
  root=$(batocera_detect "$1") || return 1
  for sub in "$root/roms"/*/; do
    [[ -d $sub ]] || continue
    sub=${sub%/}
    name=${sub##*/}
    batocera_known "$name" || continue
    choice=""
    if entry=$(batocera_entry "$name") && [[ ${entry%%$'\t'*} == "$sub" ]]; then
      choice=${entry#*$'\t'}
    fi
    effective=${choice:-${BATOCERA_DEFAULT[$name]}}
    exts=$(scraper_attract_emulator "$effective" 2> /dev/null | cut -d'|' -f4)
    [[ $effective == retroarch/* ]] && exts=$(batocera_zip "$exts")
    printf '%s|%s|%s|%s|%s|%s\n' "$name" "${BATOCERA_LABEL[$name]}" "$sub" "$(batocera_count "$sub" "$exts")" \
      "$choice" "${BATOCERA_DEFAULT[$name]}"
  done
  return 0
}

# batocera_known_count MONTAGEM imprime quantas pastas de console da tabela o
# disco tem (so conta pastas: nao abre nenhuma, serve para a pergunta do disco novo).
batocera_known_count() {
  local root sub n=0
  root=$(batocera_detect "$1") || { echo 0; return 1; }
  for sub in "$root/roms"/*/; do
    [[ -d $sub ]] || continue
    sub=${sub%/}
    batocera_known "${sub##*/}" && n=$((n + 1))
  done
  printf '%d\n' "$n"
}

# batocera_unknown MONTAGEM imprime quantas pastas de roms/ a tabela nao tem.
batocera_unknown() {
  local root sub n=0
  root=$(batocera_detect "$1") || return 1
  for sub in "$root/roms"/*/; do
    [[ -d $sub ]] || continue
    sub=${sub%/}
    batocera_known "${sub##*/}" || n=$((n + 1))
  done
  printf '%d\n' "$n"
}

# batocera_detect_systems imprime os consoles ligados para o scraper_detect:
# "batocera/<nome>|<pasta>|<plataforma>|<jogos>", so os que tem a pasta (disco
# ligado) e jogos.
batocera_detect_systems() {
  local system folder choice exts count
  # A tabela aqui, no processo de quem chama: o que os subshells carregam
  # (batocera_list_read abaixo) nao chega nos arrays.
  batocera_load || return 0
  while IFS=$'\t' read -r system folder choice; do
    # Na pasta da rede com o servidor desligado (lib/netshare.sh), cada console
    # esperaria a montagem desistir: ficam de fora ate ele voltar.
    declare -F netshare_offline > /dev/null && netshare_offline "$folder" && continue
    [[ -d $folder ]] || continue
    exts=$(batocera_emulator "batocera/$system" | cut -d'|' -f4)
    count=$(batocera_count "$folder" "$exts")
    ((count > 0)) && printf 'batocera/%s|%s|%s|%s\n' "$system" "$folder" "${BATOCERA_PLATFORM[$system]}" "$count"
  done < <(batocera_list_read)
  return 0
}

# batocera_shown SISTEMA: onde o console esta, para as telas ("on HD: batocera/roms/snes").
batocera_shown() {
  local folder disk rest
  folder=$(batocera_folder "$1") || return 1
  disk=$(folders_mount_label "$folder")
  if [[ -n $disk ]]; then
    rest=${folder#"$FOLDERS_MOUNTS/$disk"}
    printf 'on %s%s\n' "$disk" "${rest:+: ${rest#/}}"
  else
    printf 'in %s\n' "$folder"
  fi
}

# ── Usar o disco ─────────────────────────────────────────────────

# batocera_roles imprime "pasta-do-disco pasta-de-~": o que cada irma vira.
batocera_roles() {
  printf '%s\n' "bios bios" "saves save" "save save" "nvram nvram" "media media" "snap media/snap"
}

# batocera_extras imprime as pastas de sistemas que so o FliperOS tem: as
# pastas fixas do fliperos-roms que nenhum console da tabela abre, fora as que
# ficam so no gabinete (BATOCERA_LOCAL).
batocera_extras() {
  local key name mapped=" "
  batocera_load || return 0
  for name in "${!BATOCERA_DEFAULT[@]}"; do
    for key in "${BATOCERA_DEFAULT[$name]}" ${BATOCERA_ALSO[$name]//,/ }; do
      [[ $key == retroarch/* ]] || mapped+="$key "
    done
  done
  [[ -f $FOLDERS_SCRIPT ]] || return 0
  while IFS= read -r name; do
    [[ -n $name && " $BATOCERA_LOCAL " != *" $name "* && $mapped != *" $name "* ]] && printf '%s\n' "$name"
  done < <(batocera_roms_folders)
  return 0
}

# batocera_parent_linked PASTA: alguma pasta de cima ja e um atalho? (Uma
# pasta de dentro de um link e do disco do link: nada a fazer nela.)
batocera_parent_linked() {
  local rel=$1
  while [[ $rel == */* ]]; do
    rel=${rel%/*}
    [[ -L $(folders_path "$rel") ]] && return 0
  done
  return 1
}

# batocera_auto MONTAGEM [reset]: o core padrao de cada console do disco (so os
# que ainda nao tem escolha daquela pasta; com "reset", todos). Imprime quantos.
batocera_auto() {
  local root sub name entry n=0
  batocera_load || return 1
  root=$(batocera_detect "$1") || { BATOCERA_ERROR="No Batocera folders on $1."; return 1; }
  for sub in "$root/roms"/*/; do
    [[ -d $sub ]] || continue
    sub=${sub%/}
    name=${sub##*/}
    batocera_known "$name" || continue
    if [[ ${2:-} != reset ]] && entry=$(batocera_entry "$name") && [[ ${entry%%$'\t'*} == "$sub" ]]; then
      continue
    fi
    batocera_set "$name" "$sub" "${BATOCERA_DEFAULT[$name]}" && n=$((n + 1))
  done
  printf '%d\n' "$n"
}

# batocera_rebase MONTAGEM RAIZ: os consoles da lista que estao na roms/ de
# outra pasta do Batocera do mesmo disco (a que a deteccao levava antes de
# comparar os jogos) passam para a roms/ da RAIZ, com a escolha de core da
# pessoa; o que a RAIZ nao tem sai da lista. Imprime quantos eram de outra pasta.
batocera_rebase() {
  local mount=$1 root=$2 system folder choice lines="" n=0
  while IFS=$'\t' read -r system folder choice; do
    if batocera_in_roms "$mount" "$folder" && [[ $folder != "$root/roms/"* ]]; then
      n=$((n + 1))
      [[ -d $root/roms/$system ]] || continue
      folder=$root/roms/$system
    fi
    lines+=$system$'\t'$folder$'\t'$choice$'\n'
  done < <(batocera_list_read)
  if ((n)); then
    batocera_list_write "$lines"
  fi
  printf '%d\n' "$n"
}

# batocera_sibling MONTAGEM ALVO: o alvo de um atalho e uma pasta irma (bios,
# saves, nvram, media, snap) de alguma pasta do Batocera do disco? E o que o
# batocera_use faz, de uma pasta que a deteccao ja escolheu antes de outra: o
# atalho e dele, nao uma escolha da pessoa para outro lugar.
batocera_sibling() {
  local parent=${2%/*} name=${2##*/} role
  [[ $parent == "$1/batocera" || $parent == "$1/userdata" || $parent == "$1" ]] || return 1
  while read -r role _; do
    [[ $name == "$role" ]] && return 0
  done < <(batocera_roles)
  return 1
}

# batocera_use MONTAGEM: liga o Batocera filesystem do disco (tudo o que ele
# tem). Imprime "moved=N" (consoles que estavam em outra pasta do disco),
# "systems=N", "linked=PASTAS", "extras=PASTAS", "skipped=PASTA motivo" e
# "readonly=1". Status 1: o disco nao tem Batocera filesystem.
batocera_use() {
  local mount=$1 root n role name rel src target linked="" extras="" writable=1 done_rels=" "
  BATOCERA_ERROR=""
  if ! root=$(batocera_detect "$mount"); then
    BATOCERA_ERROR="No Batocera folders on ${mount##*/}."
    return 1
  fi
  n=$(batocera_rebase "$mount" "$root")
  ((n == 0)) || printf 'moved=%d\n' "$n"
  batocera_auto "$mount" > /dev/null || return 1
  n=0
  while IFS=$'\t' read -r name rel src; do
    [[ $rel == "$root"/* ]] && n=$((n + 1))
  done < <(batocera_list_read)
  printf 'systems=%d\n' "$n"
  [[ -w $root ]] || writable=0
  if ((writable == 0)); then
    echo "readonly=1"
  else
    # As irmas: cada uma o atalho da pasta de mesmo papel em ~, a menos que ela ja
    # seja um atalho que a pessoa fez para outro lugar (fora do disco).
    while read -r name rel; do
      src=$root/$name
      [[ -d $src && $done_rels != *" $rel "* ]] || continue
      case $done_rels in *" ${rel%%/*} "*) [[ $rel == */* ]] && continue ;; esac
      if [[ -L $(folders_path "$rel") ]]; then
        target=$(folders_target "$rel" 2> /dev/null)
        if [[ -n $target && $target != "$src" && $target != "$mount/${STORAGE_NAME:-fliperos}"/* ]] &&
          ! batocera_sibling "$mount" "$target"; then
          printf 'skipped=%s already points to %s\n' "$rel" "${target/#$FOLDERS_HOME/\~}"
          continue
        fi
      fi
      # saves e nvram o FliperOS grava (as pastas de cada emulador dentro): num
      # disco de Linux elas vem do root do Batocera, e o fliperos-roms nao criava
      # ~/save/retroarch (o update 109 parava no link /opt/fliperos/saves/retroarch).
      case $rel in save | nvram) folders_own "$src" ;; esac
      if folders_link "$rel" "$src"; then
        linked+="${linked:+,}$rel"
        done_rels+="$rel "
        [[ -n $FOLDERS_KEPT ]] && echo "kept=${FOLDERS_KEPT/#$FOLDERS_HOME/\~}"
      else
        printf 'skipped=%s %s\n' "$rel" "${FOLDERS_ERROR:-could not be linked}"
      fi
    done < <(batocera_roles)
    # As pastas de sistemas que so o FliperOS tem, ao lado dos consoles: a chave
    # segue sendo ~/roms/<nome> e o resto do FliperOS nao muda.
    while IFS= read -r name; do
      [[ -n $name ]] || continue
      rel=roms/$name
      if batocera_parent_linked "$rel"; then
        printf 'skipped=%s ~/roms is already on another disk\n' "$rel"
        continue
      fi
      src=$root/roms/$name
      if [[ -L $(folders_path "$rel") && $(folders_target "$rel" 2> /dev/null) == "$src" ]]; then
        extras+="${extras:+,}$name"
        continue
      fi
      mkdir -p -- "$src" 2>> "$FLIPEROS_LOG" && folders_own "$src"
      if folders_link "$rel" "$src"; then
        extras+="${extras:+,}$name"
      else
        printf 'skipped=%s %s\n' "$rel" "${FOLDERS_ERROR:-could not be linked}"
      fi
    done < <(batocera_extras)
  fi
  [[ -z $linked ]] || printf 'linked=%s\n' "$linked"
  [[ -z $extras ]] || printf 'extras=%s\n' "$extras"
  batocera_refresh
  return 0
}

# batocera_unuse MONTAGEM: desfaz o batocera_use do disco: os atalhos de ~ que
# apontam para ele (menos a arvore fliperos/ dele, que e do Storage) voltam ao
# que eram e os consoles dele saem da lista. Nada sai do disco.
batocera_unuse() {
  local mount=$1 rel target line system folder choice failed=0 rc lines=""
  BATOCERA_ERROR=""
  while IFS= read -r rel; do
    [[ -n $rel ]] || continue
    target=$(folders_target "$rel" 2> /dev/null) || continue
    [[ $target == "$mount"/* && $target != "$mount/${STORAGE_NAME:-fliperos}"/* ]] || continue
    rc=0
    folders_unlink "$rel" || rc=$?
    if ((rc == 1)); then
      BATOCERA_ERROR=${FOLDERS_ERROR:-Could not stop using $target.}
      failed=1
    fi
  done < <(folders_customs)
  while IFS=$'\t' read -r system folder choice; do
    [[ $folder == "$mount"/* ]] || lines+=$system$'\t'$folder$'\t'$choice$'\n'
  done < <(batocera_list_read)
  batocera_list_write "$lines"
  batocera_refresh
  ((failed == 0))
}

# batocera_in_use MONTAGEM: algum console ou atalho do disco esta ligado?
batocera_in_use() {
  local mount=$1 system folder choice rel target
  while IFS=$'\t' read -r system folder choice; do
    [[ $folder == "$mount"/* ]] && return 0
  done < <(batocera_list_read)
  while IFS= read -r rel; do
    target=$(folders_target "$rel" 2> /dev/null) || continue
    [[ $target == "$mount"/* && $target != "$mount/${STORAGE_NAME:-fliperos}"/* ]] && return 0
  done < <(folders_customs)
  return 1
}

# batocera_stale MONTAGEM: o disco esta ligado (batocera.list) numa pasta do
# Batocera que nao e a que o batocera_detect escolhe hoje? Status 0: ha console
# na roms/ de outra pasta. Foi o que a deteccao de antes deixou num disco com o
# esqueleto em batocera/ e o Batocera de verdade na raiz (2026-11-26): os
# consoles, a bios e os saves ficaram no esqueleto. batocera_use liga de novo na
# pasta certa (--batocera repair, e o --storage auto de cada boot).
batocera_stale() {
  local mount=$1 root folder
  root=$(batocera_detect "$mount") || return 1
  while IFS=$'\t' read -r _ folder _; do
    batocera_in_roms "$mount" "$folder" && [[ $folder != "$root/roms/"* ]] && return 0
  done < <(batocera_list_read)
  return 1
}

# batocera_refresh: os frontends leem de novo os sistemas (a lista que o frontend
# proprio guarda em cache vai junto, pelo --systems dele).
batocera_refresh() {
  folders_cli_refresh roms
  rm -f -- "$FOLDERS_HOME/.cache/fliperos/frontend-systems" 2> /dev/null
  return 0
}

# batocera_cli detect|scan|unknown|list|cores|set|unset|auto|use|unuse|repair|extras:
# o fliperos-setup --batocera. Os discos so os de STORAGE_MOUNTS. Status 2:
# pedido errado; 1: nao deu (o motivo na saida).
batocera_cli() {
  local cmd=${1:-} mount
  case $cmd in
    detect | scan | unknown | auto | use | unuse | repair)
      mount=${2:-}
      [[ $mount == "${STORAGE_MOUNTS:-/media/$FLIPEROS_USER}"/* && $mount != *..* ]] && mountpoint -q -- "$mount" 2> /dev/null || return 2
      ;;
  esac
  case $cmd in
    detect) batocera_detect "$mount" || return 1 ;;
    scan) batocera_scan "$mount" || return 1 ;;
    unknown) batocera_unknown "$mount" || return 1 ;;
    list) batocera_list_read | tr '\t' '|' ;;
    cores) batocera_cores "${2:-}" || return 2 ;;
    extras) batocera_extras ;;
    set)
      batocera_known "${2:-}" && [[ -n ${3:-} && -n ${4:-} ]] || return 2
      if ! batocera_set "$2" "$3" "$4"; then
        echo "${BATOCERA_ERROR:-Could not save the choice (details in the log).}"
        return 1
      fi
      batocera_refresh
      ;;
    unset)
      batocera_known "${2:-}" || return 2
      batocera_unset "$2"
      batocera_refresh
      ;;
    auto)
      if ! batocera_auto "$mount" "${3:-}"; then
        echo "${BATOCERA_ERROR:-Could not choose the cores (details in the log).}"
        return 1
      fi
      batocera_refresh
      ;;
    use)
      if ! batocera_use "$mount"; then
        echo "${BATOCERA_ERROR:-Could not use the disk (details in the log).}"
        return 1
      fi
      # Quem usa o disco ja decidiu: o frontend nao pergunta dele.
      declare -F storage_settle > /dev/null && storage_settle "$mount" batocera
      ;;
    unuse)
      if ! batocera_unuse "$mount"; then
        echo "${BATOCERA_ERROR:-Could not stop using the disk (details in the log).}"
        return 1
      fi
      ;;
    repair)
      # So um disco ligado numa pasta que nao e a de hoje: liga de novo na certa.
      if ! batocera_stale "$mount"; then
        echo "Nothing to repair."
        return 0
      fi
      if ! batocera_use "$mount"; then
        echo "${BATOCERA_ERROR:-Could not use the disk (details in the log).}"
        return 1
      fi
      ;;
    *) return 2 ;;
  esac
  return 0
}
