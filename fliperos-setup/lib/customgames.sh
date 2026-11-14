# shellcheck shell=bash
# Setup > Games > Custom games: jogos e programas que nao sao uma ROM de um
# emulador do FliperOS (um jogo de PC, um emulador trazido pela pessoa, um
# script), em grupos que os frontends mostram como sistemas.
#
# Cada grupo e uma pasta ~/roms/custom/GRUPO e cada entrada um script
# NOME.sh nela: o nome do arquivo e o que o frontend mostra. O script abre o
# jogo pelo fliperos-x11-run, num Xorg so dele no modo da entrada (o
# Switchres cria o modo; a 15 kHz 640x480 sai entrelacado), com o executor
# config/fliperos-customgame, que le o NOME.cfg ao lado: o comando (platform
# command, a entrada feita a mao), ou o jogo de um pacote (windows, native),
# com a pasta em ~/games/GRUPO/NOME. O executor sobe junto o mapa do controle
# para o teclado (NOME.key). O modo e o comando ficam tambem no cabecalho do
# .sh. Nos frontends a pasta e o sistema "custom/GRUPO" (scraper_detect),
# aberto com o sh.
#
# Os pacotes (JOGO.fliperos-customgame.zip) postos em ~/roms/custom ou em
# ~/roms/custom/GRUPO aparecem em Custom games para instalar; o zip fica onde
# estava, e o cfg do jogo instalado o anota (nao volta a lista).

CUSTOM_GAMES_DIR=${CUSTOM_GAMES_DIR:-$ROMS_DIR/custom}
CUSTOM_GAMES_RUN=${CUSTOM_GAMES_RUN:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-x11-run}
CUSTOM_GAMES_TOOL=${CUSTOM_GAMES_TOOL:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-customgame}
# As pastas dos jogos dos pacotes: ~/games/GRUPO/NOME.
CUSTOM_GAMES_GAMES=${CUSTOM_GAMES_GAMES:-$(dirname "$ROMS_DIR")/games}
# 0: a pasta do jogo instalado fica solta (sem o squashfs).
CUSTOM_GAMES_SQUASH=${CUSTOM_GAMES_SQUASH:-1}
# O Wine no comando (o do fliperos-x11-client): a camada de 32 bits.
CUSTOM_GAMES_WINE_RE='(^|[[:space:]/;&(])wine(64)?([[:space:]]|$)|\.[eE][xX][eE]([[:space:]"]|$)'
# As resolucoes da lista: 240p e 480i (a 15 kHz, entrelacado pelo Switchres).
CUSTOM_GAMES_MODES="240p|640x240@60 480i|640x480@60"

# customgames_valid_name TEXTO: serve de nome de grupo ou de entrada (vira
# nome de pasta ou de arquivo e item de lista).
customgames_valid_name() {
  [[ -n ${1//[[:space:]]/} && $1 != *[/\|]* && $1 != *$'\n'* && $1 != . && $1 != .. && $1 != .* ]]
}

# customgames_valid_command TEXTO: uma linha so.
customgames_valid_command() {
  [[ -n ${1//[[:space:]]/} && $1 != *$'\n'* ]]
}

# customgames_mode 240p|480i|LARGURAxALTURA@HZ imprime o modo do
# fliperos-x11-run. Status 1: invalido.
customgames_mode() {
  local pair
  for pair in $CUSTOM_GAMES_MODES; do
    [[ $1 == "${pair%%|*}" ]] && { printf '%s\n' "${pair#*|}"; return 0; }
  done
  [[ $1 =~ ^[1-9][0-9]{1,3}x[1-9][0-9]{1,3}@[1-9][0-9]{0,2}(\.[0-9]+)?$ ]] || return 1
  printf '%s\n' "$1"
}

# customgames_mode_label MODO: "240p", "480i" ou o proprio modo.
customgames_mode_label() {
  local pair
  for pair in $CUSTOM_GAMES_MODES; do
    [[ $1 == "${pair#*|}" ]] && { printf '%s\n' "${pair%%|*}"; return 0; }
  done
  printf '%s\n' "$1"
}

customgames_file() {
  printf '%s/%s/%s.sh\n' "$CUSTOM_GAMES_DIR" "$1" "$2"
}

# As midias que os frontends mostram de um jogo personalizado: em
# ~/media/TIPO/custom/GRUPO/NOME.ext, como as dos outros sistemas (a chave do
# sistema e custom/GRUPO). preview e o video, texto a descricao.
CUSTOM_GAMES_MEDIA=${CUSTOM_GAMES_MEDIA:-$(dirname "$ROMS_DIR")/media}
CUSTOM_GAMES_MEDIA_TYPES="snap box logo marquee preview texto"

# customgames_media_path TIPO GRUPO NOME: o arquivo da midia de exemplo
# (snap .png, preview .mp4, texto .txt).
customgames_media_path() {
  local ext=png
  [[ $1 == preview ]] && ext=mp4
  [[ $1 == texto ]] && ext=txt
  printf '%s/%s/custom/%s/%s.%s\n' "$CUSTOM_GAMES_MEDIA" "$1" "$2" "$3" "$ext"
}

# As extensoes que os frontends aceitam de cada tipo (as do fedata.py).
customgames_media_exts() {
  case $1 in
    preview) echo "mp4 mkv webm avi mov flv" ;;
    texto) echo "txt" ;;
    *) echo "png jpg jpeg webp gif" ;;
  esac
}

# customgames_media_files GRUPO NOME: os arquivos de midia do jogo que
# existem, de todos os tipos e extensoes.
customgames_media_files() {
  local kind ext
  for kind in $CUSTOM_GAMES_MEDIA_TYPES; do
    for ext in $(customgames_media_exts "$kind"); do
      [[ -f $CUSTOM_GAMES_MEDIA/$kind/custom/$1/$2.$ext ]] && printf '%s\n' "$CUSTOM_GAMES_MEDIA/$kind/custom/$1/$2.$ext"
    done
  done
  return 0
}

# customgames_media_has TIPO GRUPO NOME: o jogo ja tem esse tipo (em
# qualquer extensao: uma .jpg da pessoa vale, a .png de exemplo a esconderia).
customgames_media_has() {
  local ext
  for ext in $(customgames_media_exts "$1"); do
    [[ -f $CUSTOM_GAMES_MEDIA/$1/custom/$2/$3.$ext ]] && return 0
  done
  return 1
}

# As de exemplo que o Setup fez ficam anotadas, com o sha256 (a linha do
# sha256sum): renomear o jogo refaz as de exemplo e leva as de verdade junto,
# e apaga-lo leva so as de exemplo. Uma de exemplo trocada pela pessoa (outro
# sha256) passa a ser de verdade.
CUSTOM_GAMES_SAMPLES=${CUSTOM_GAMES_SAMPLES:-$CUSTOM_GAMES_MEDIA/.custom-samples}
CUSTOM_GAMES_MEDIA_TOOL=${CUSTOM_GAMES_MEDIA_TOOL:-${SETUP_DIR:-/usr/local/lib/fliperos-setup}/gui/custom-media.py}

customgames_media_sample() {
  [[ -f $1 && -f $CUSTOM_GAMES_SAMPLES ]] && grep -qxF "$(sha256sum "$1" | cut -d' ' -f1)  $1" "$CUSTOM_GAMES_SAMPLES"
}

customgames_media_unmark() {
  [[ -f $CUSTOM_GAMES_SAMPLES ]] || return 0
  awk -v p="$1" 'substr($0, 67) != p' "$CUSTOM_GAMES_SAMPLES" > "$CUSTOM_GAMES_SAMPLES.new" &&
    mv -f "$CUSTOM_GAMES_SAMPLES.new" "$CUSTOM_GAMES_SAMPLES"
}

# customgames_media GRUPO NOME: as pastas das midias do grupo e, do jogo, uma
# imagem, um video e um texto de exemplo com o nome dele e o caminho de cada
# arquivo, e o logotipo (gui/custom-media.py): o jogo ja aparece com arte nos
# frontends, e a pessoa ve qual arquivo trocar. So os tipos que faltam.
customgames_media() {
  local -a args=()
  local kind opt path
  customgames_media_dirs "$1"
  for kind in snap preview texto logo; do
    customgames_media_has "$kind" "$1" "$2" && continue
    case $kind in snap) opt=--snap ;; preview) opt=--video ;; texto) opt=--text ;; logo) opt=--logo ;; esac
    args+=("$opt" "$(customgames_media_path "$kind" "$1" "$2")")
  done
  ((${#args[@]})) || return 0
  while IFS= read -r path; do
    [[ -f $path ]] && sha256sum "$path" >> "$CUSTOM_GAMES_SAMPLES"
  done < <(python3 "$CUSTOM_GAMES_MEDIA_TOOL" --name "$2" --group "$1" --home "$(dirname "$CUSTOM_GAMES_MEDIA")" "${args[@]}" \
    2>> "${FLIPEROS_LOG:-/dev/null}")
  chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_SAMPLES" 2> /dev/null
  return 0
}

# customgames_media_all: as de exemplo de cada jogo que ainda nao tem (o
# System Update: os jogos postos antes delas existirem).
customgames_media_all() {
  local group name
  while IFS='|' read -r group name _; do
    customgames_media "$group" "$name"
  done < <(customgames_list)
  return 0
}

# customgames_media_rename GRUPO NOME GRUPO_NOVO NOME_NOVO: as midias de
# verdade vao para o nome novo (as que ja existem la ficam); as de exemplo,
# com o nome antigo escrito nelas, saem (customgames_media faz as novas).
customgames_media_rename() {
  local file kind ext target
  while IFS= read -r file; do
    if customgames_media_sample "$file"; then
      rm -f "$file"
      customgames_media_unmark "$file"
      continue
    fi
    # Uma de exemplo que a pessoa trocou: a anotacao velha sai.
    customgames_media_unmark "$file"
    kind=${file#"$CUSTOM_GAMES_MEDIA"/}
    kind=${kind%%/*}
    ext=${file##*.}
    target=$CUSTOM_GAMES_MEDIA/$kind/custom/$3/$4.$ext
    [[ -e $target ]] && continue
    mkdir -p "${target%/*}" && mv "$file" "$target" && chown "$FLIPEROS_USER:" "${target%/*}" "$target" 2> /dev/null
  done < <(customgames_media_files "$1" "$2")
  return 0
}

# customgames_media_drop GRUPO NOME: apaga as de exemplo do jogo (as de
# verdade ficam, a pessoa pode querer de volta).
customgames_media_drop() {
  local file
  while IFS= read -r file; do
    customgames_media_sample "$file" || continue
    rm -f "$file"
    customgames_media_unmark "$file"
  done < <(customgames_media_files "$1" "$2")
  return 0
}

# customgames_media_dirs GRUPO cria as pastas das midias do grupo (do
# jogador: aparecem no compartilhamento \\fliperos\media).
customgames_media_dirs() {
  local kind
  for kind in $CUSTOM_GAMES_MEDIA_TYPES; do
    mkdir -p "$CUSTOM_GAMES_MEDIA/$kind/custom/$1" 2> /dev/null &&
      chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_MEDIA/$kind" "$CUSTOM_GAMES_MEDIA/$kind/custom" \
        "$CUSTOM_GAMES_MEDIA/$kind/custom/$1" 2> /dev/null
  done
  return 0
}

# customgames_app GRUPO NOME: o nome da entrada para o filtro de flicker e a
# OSD (deflicker_NOME= no fliperos.conf, a linha dela em Interlaced hacks):
# custom_ e o grupo e o nome em minusculas, o resto vira _ (PC games / Pang:
# custom_pc_games_pang). O fliperos-x11-run o recebe por --app; sem ele, o
# programa seria o bash e todas as entradas dividiriam o mesmo nivel.
customgames_app() {
  local slug
  slug=$(printf '%s_%s' "$1" "$2" | LC_ALL=C tr 'A-Z' 'a-z' | LC_ALL=C sed 's/[^a-z0-9]\{1,\}/_/g; s/^_//; s/_$//')
  printf 'custom_%s\n' "$slug"
}

# customgames_field ARQUIVO mode|command le o cabecalho de uma entrada.
customgames_field() {
  sed -n "s/^# $2: //p" "$1" 2> /dev/null | head -n 1
}

# ── O cfg de cada entrada ──
# NOME.cfg ao lado do NOME.sh: linhas CHAVE=VALOR (as do
# config/fliperos-customgame: format, name, platform, exe ou command, mode,
# category, controls, buttons, players; o de um pacote, folder= e package=).

customgames_cfg() {
  printf '%s/%s/%s.cfg\n' "$CUSTOM_GAMES_DIR" "$1" "$2"
}

# customgames_cfg_field ARQUIVO CHAVE
customgames_cfg_field() {
  sed -n "s/^$2=//p" "$1" 2> /dev/null | head -n 1
}

# customgames_cfg_write ARQUIVO CHAVE=VALOR... grava o cfg inteiro (as
# chaves vazias ficam de fora), do jogador.
customgames_cfg_write() {
  local file=$1 pair
  shift
  {
    echo '# FliperOS custom game (Setup > Games > Custom games).'
    for pair in "$@"; do
      if [[ -n ${pair#*=} ]]; then printf '%s\n' "${pair//$'\n'/ }"; fi
    done
  } > "$file.new" || return 1
  chmod 644 "$file.new"
  mv -f "$file.new" "$file" || return 1
  chown "$FLIPEROS_USER:" "$file" 2> /dev/null
  return 0
}

# customgames_cfg_set ARQUIVO CHAVE VALOR troca (ou poe, ou com VALOR vazio
# tira) uma chave, mantendo as outras.
customgames_cfg_set() {
  local file=$1 key=$2 value=${3//$'\n'/ } line
  local -a pairs=()
  while IFS= read -r line; do
    [[ $line == *=* && $line != \#* ]] || continue
    [[ ${line%%=*} == "$key" ]] && continue
    pairs+=("$line")
  done < <(cat "$file" 2> /dev/null)
  pairs+=("$key=$value")
  customgames_cfg_write "$file" "${pairs[@]}"
}

# customgames_platform GRUPO NOME: windows, native (os dos pacotes),
# command (o comando digitado) ou script (um .sh posto a mao).
customgames_platform() {
  local platform
  platform=$(customgames_cfg_field "$(customgames_cfg "$1" "$2")" platform)
  [[ -z $platform && -n $(customgames_field "$(customgames_file "$1" "$2")" command) ]] && platform=command
  printf '%s\n' "${platform:-script}"
}

# customgames_entry GRUPO NOME grava o NOME.sh pelo NOME.cfg: o
# fliperos-x11-run no modo do jogo, com o nome dele (--app) e, num jogo do
# Windows (ou um comando com o wine), a camada de 32 bits (--wine).
customgames_entry() {
  local group=$1 name=$2 cfg file mode platform cmd wine=""
  cfg=$(customgames_cfg "$group" "$name")
  file=$(customgames_file "$group" "$name")
  mode=$(customgames_cfg_field "$cfg" mode)
  platform=$(customgames_cfg_field "$cfg" platform)
  cmd=$(customgames_cfg_field "$cfg" command)
  mode=$(customgames_mode "$mode") || return 1
  [[ $platform == windows || ($platform == command && $cmd =~ $CUSTOM_GAMES_WINE_RE) ]] && wine=" --wine"
  {
    echo '#!/bin/sh'
    echo '# FliperOS custom game (Setup > Games > Custom games). Edited there, or in its .cfg.'
    echo "# mode: $mode"
    [[ $platform == command ]] && echo "# command: $cmd"
    printf 'exec %q --mode %q --app %q%s %q run %q\n' "$CUSTOM_GAMES_RUN" "$mode" "$(customgames_app "$group" "$name")" \
      "$wine" "$CUSTOM_GAMES_TOOL" "$cfg"
  } > "$file.new" || return 1
  chmod 755 "$file.new"
  mv -f "$file.new" "$file" || return 1
  chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$CUSTOM_GAMES_DIR/$group" "$file" 2> /dev/null
  return 0
}

# customgames_save GRUPO NOME MODO COMANDO [GRUPO_ANTES NOME_ANTES] grava a
# entrada de um comando (editada: a de antes sai, e o mapa do controle e a
# classificacao vao junto). Status 1: nome, modo ou comando invalido.
customgames_save() {
  local group=$1 name=$2 mode cmd=$4 old_group=${5:-} old_name=${6:-} dir cfg old key
  local -a keep=()
  customgames_valid_name "$group" && customgames_valid_name "$name" && customgames_valid_command "$cmd" ||
    return 1
  mode=$(customgames_mode "$3") || return 1
  dir=$CUSTOM_GAMES_DIR/$group
  cfg=$(customgames_cfg "$group" "$name")
  old=$cfg
  [[ -n $old_name ]] && old=$(customgames_cfg "$old_group" "$old_name")
  mkdir -p "$dir" || return 1
  chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$dir" 2> /dev/null
  for key in category controls buttons players; do
    keep+=("$key=$(customgames_cfg_field "$old" "$key")")
  done
  customgames_cfg_write "$cfg" "format=1" "name=$name" "platform=command" "command=$cmd" "mode=$mode" "${keep[@]}" ||
    return 1
  customgames_entry "$group" "$name" || return 1
  if [[ -n $old_name && ($old_group != "$group" || $old_name != "$name") ]]; then
    # As midias vao junto (as de exemplo sao refeitas com o nome novo).
    customgames_media_rename "$old_group" "$old_name" "$group" "$name"
    [[ -f ${old%.cfg}.key && ! -e ${cfg%.cfg}.key ]] && mv "${old%.cfg}.key" "${cfg%.cfg}.key"
    customgames_delete "$old_group" "$old_name"
  fi
  log_info "jogo personalizado: $group / $name ($mode): $cmd"
}

# customgames_delete GRUPO NOME [folder] apaga a entrada (e o grupo, se ficou
# vazio) e as midias de exemplo dela; a de um pacote, todas (o zip as traz de
# novo). Com folder, tambem a pasta do jogo (e o squashfs dela).
customgames_delete() {
  local cfg folder="" package=""
  cfg=$(customgames_cfg "$1" "$2")
  if [[ -f $cfg ]]; then
    folder=$(customgames_cfg_field "$cfg" folder)
    package=$(customgames_cfg_field "$cfg" package)
  fi
  rm -f "$(customgames_file "$1" "$2")" "$cfg" "${cfg%.cfg}.key" || return 1
  if [[ -n $package ]]; then
    customgames_media_files "$1" "$2" | while IFS= read -r file; do
      rm -f "$file"
      customgames_media_unmark "$file"
    done
  else
    customgames_media_drop "$1" "$2"
  fi
  [[ ${3:-} == folder && -n $folder ]] && customgames_remove_folder "$folder"
  rmdir "$CUSTOM_GAMES_DIR/$1" 2> /dev/null
  log_info "jogo personalizado apagado: $1 / $2${3:+ (com a pasta $folder)}"
  return 0
}

# customgames_remove_folder PASTA apaga a pasta de um jogo instalado (so
# dentro de ~/games), empacotada ou nao, e a do grupo se ficou vazia.
customgames_remove_folder() {
  local folder base
  base=$(realpath -m -- "$CUSTOM_GAMES_GAMES") || return 1
  folder=$(realpath -m -s -- "$1") || return 1
  [[ $folder == "$base"/*/* && $folder != */.* ]] || { log_warn "pasta fora de $base: $1"; return 1; }
  if [[ -e $folder.squashfs || -n $(squashgames_list | awk -F'|' -v f="$folder" '$1 == f') ]]; then
    "$SQUASHGAMES_CMD" remove "$folder" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1 || return 1
  fi
  rm -rf -- "$folder"
  rmdir -- "${folder%/*}" 2> /dev/null
  return 0
}

# ── Os pacotes ──

# customgames_tool COMANDO...: o config/fliperos-customgame com as pastas
# daqui (as dos testes tambem).
customgames_tool() {
  python3 "$CUSTOM_GAMES_TOOL" --roms "$CUSTOM_GAMES_DIR" --games "$CUSTOM_GAMES_GAMES" --media "$CUSTOM_GAMES_MEDIA" "$@"
}

# customgames_pending [GRUPO]: os pacotes que faltam instalar,
# "ZIP|GRUPO|NOME|PLATAFORMA|ESTADO|MOTIVO" (fliperos-customgame pending);
# com GRUPO, so os da pasta dele e os de ~/roms/custom (entram nele).
customgames_pending() {
  local line
  [[ -d $CUSTOM_GAMES_DIR ]] || return 0
  while IFS= read -r line; do
    IFS='|' read -r _ g _ <<< "$line"
    [[ -z ${1:-} || -z $g || $g == "$1" ]] && printf '%s\n' "$line"
  done < <(customgames_tool pending 2>> "${FLIPEROS_LOG:-/dev/null}")
  return 0
}

# customgames_count GRUPO: quantos jogos o grupo tem.
customgames_count() {
  local file n=0
  for file in "$CUSTOM_GAMES_DIR/$1"/*.sh; do
    [[ -f $file ]] && ((n++))
  done
  printf '%s\n' "$n"
}

# customgames_snap GRUPO NOME: a imagem do jogo (a primeira que existe).
customgames_snap() {
  local ext
  for ext in $(customgames_media_exts snap); do
    [[ -f $CUSTOM_GAMES_MEDIA/snap/custom/$1/$2.$ext ]] && { printf '%s\n' "$CUSTOM_GAMES_MEDIA/snap/custom/$1/$2.$ext"; return 0; }
  done
  return 1
}

# customgames_install ZIP GRUPO [replace]: instala o pacote no GRUPO, com os
# eventos da tela de progresso: a pasta, a midia e o cfg (o
# fliperos-customgame), o NOME.sh, as midias de exemplo que faltam e a pasta
# empacotada em squashfs (sem dar, ela fica solta: o jogo abre igual).
# Status 3: o jogo ja existe (sem replace).
customgames_install() {
  local zip=$1 group=$2 replace=${3:-} info name platform cfg folder rc
  local -a opts=()
  ev_step 0 "Checking the package"
  if ! info=$(customgames_tool inspect "$zip" 2>&1); then
    ev_fail "${info:-not a FliperOS game package}"
    return 1
  fi
  name=$(sed -n 's/^name=//p' <<< "$info")
  platform=$(sed -n 's/^platform=//p' <<< "$info")
  cfg=$(customgames_cfg "$group" "$name")
  if [[ -n $replace ]]; then
    opts+=(--replace)
    # A pasta de antes, empacotada, sai antes (o zip a traz de novo).
    folder=$(customgames_cfg_field "$cfg" folder)
    [[ -n $folder && -e $folder.squashfs ]] && { customgames_remove_folder "$folder" || { ev_fail "close the game first: $folder is in use"; return 1; }; }
  fi
  if [[ $platform == windows ]] && declare -F portproton_ensure > /dev/null; then
    portproton_ensure 2 30 || return 1
  fi
  customgames_tool install "$zip" --group "$group" "${opts[@]}" --progress 30 70 2>> "${FLIPEROS_LOG:-/dev/null}"
  rc=$?
  if ((rc == 3)); then
    ev_fail "$name is already in $group"
    return 3
  fi
  ((rc == 0)) || return 1
  customgames_entry "$group" "$name" || { ev_fail "could not write $name.sh"; return 1; }
  ev_step 72 "Pictures for $name"
  customgames_media "$group" "$name"
  folder=$(customgames_cfg_field "$cfg" folder)
  if ((CUSTOM_GAMES_SQUASH)) && [[ -x $SQUASHGAMES_CMD && -d $folder ]] && ((EUID == 0)); then
    # 75 a 99: as etapas do empacotamento; uma falha so avisa.
    "$SQUASHGAMES_CMD" pack "$folder" --progress 2>> "${FLIPEROS_LOG:-/dev/null}" |
      awk '/^@(step|pct) [0-9]+/ { $2 = int(75 + $2 * 0.24); print; fflush(); next }
           /^@fail / { sub(/^@fail [^|]*\|/, ""); print "@msg Not packed: " $0; fflush() }'
  fi
  ev_step 100 "$name installed"
  log_info "pacote instalado: $zip em $group / $name"
  return 0
}

# customgames_pending_ok [GRUPO]: os pacotes que dao para instalar (sem os
# "bad").
customgames_pending_ok() {
  customgames_pending "$@" | awk -F'|' '$5 != "bad"'
}

# customgames_kind_label GRUPO NOME: "Windows 240p", "Linux 480i",
# "Command 384x224@59.6"...
customgames_kind_label() {
  local platform mode
  platform=$(customgames_platform "$1" "$2")
  mode=$(customgames_cfg_field "$(customgames_cfg "$1" "$2")" mode)
  [[ -n $mode ]] || mode=$(customgames_field "$(customgames_file "$1" "$2")" mode)
  case $platform in
    windows) platform=Windows ;;
    native) platform=Linux ;;
    command) platform=Command ;;
    *) platform=Script ;;
  esac
  printf '%s %s\n' "$platform" "$(customgames_mode_label "${mode:-?}")"
}

# customgames_pack_run ARGUMENTOS DO fliperos-customgame pack: com os
# eventos da tela de progresso (Create package).
customgames_pack_run() {
  ev_step 0 "Starting"
  customgames_tool pack "$@" --progress 0 100 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# Os generos de jogo do catver.ini (sem os de sistemas, maquinas de apostas
# e afins): a categoria de um jogo custom, como a dos jogos do MAME.
CUSTOM_GAMES_GENRES="Ball & Paddle|Board Game|Card Games|Climbing|Driving|Fighter|Maze|Misc.|MultiGame|Multiplay|Music Game|Platform|Puzzle|Quiz|Shooter|Sports|Tabletop|Whac-A-Mole"

# customgames_subgenres GENERO: as categorias "GENERO / SUB" do catver.ini.
customgames_subgenres() {
  local catver=${CUSTOM_GAMES_CATVER:-${ROMCLEAN_DATA:-/usr/local/share/fliperos/romclean}/catver.ini}
  awk -F= -v g="$1 / " '/^\[Category\]/ { c = 1; next } /^\[/ { c = 0 }
    c && NF == 2 { v = $2; sub(/\r$/, "", v); sub(/ \* Mature \*$/, "", v); if (index(v, g) == 1) print v }' \
    "$catver" 2> /dev/null | sort -u
}

# ── A ultima pasta do Create package ──
# Cada seletor de arquivo do assistente abre onde o anterior parou (a pasta
# do jogo, depois a da imagem...), tambem da proxima vez.

customgames_last_dir_file() {
  printf '%s/.config/fliperos/customgame-last-dir\n' "$(dirname "$ROMS_DIR")"
}

# customgames_last_dir: a pasta onde o ultimo seletor parou (ou ~/games, ou
# os discos ligados, ou a home).
customgames_last_dir() {
  local dir home
  home=$(dirname "$ROMS_DIR")
  dir=$(head -n 1 "$(customgames_last_dir_file)" 2> /dev/null)
  [[ -n $dir && -d $dir ]] && { printf '%s\n' "$dir"; return 0; }
  for dir in "$home/games" /media/fliperos "$home"; do
    [[ -d $dir ]] && { printf '%s\n' "$dir"; return 0; }
  done
  printf '/\n'
}

# customgames_last_dir_set PASTA|ARQUIVO
customgames_last_dir_set() {
  local dir=$1 file
  [[ -d $dir ]] || dir=$(dirname "$dir")
  file=$(customgames_last_dir_file)
  mkdir -p "$(dirname "$file")" 2> /dev/null && printf '%s\n' "$dir" > "$file" 2> /dev/null &&
    chown "$FLIPEROS_USER:" "$(dirname "$file")" "$file" 2> /dev/null
  return 0
}

# customgames_groups imprime os grupos (pastas), em ordem.
customgames_groups() {
  local dir
  for dir in "$CUSTOM_GAMES_DIR"/*/; do
    [[ -d $dir ]] && printf '%s\n' "$(basename "$dir")"
  done
  return 0
}

# customgames_list imprime "grupo|nome|modo|comando" de cada entrada. Um .sh
# posto a mao, sem o cabecalho, aparece com o modo e o comando vazios.
customgames_list() {
  local file group name
  for file in "$CUSTOM_GAMES_DIR"/*/*.sh; do
    [[ -f $file ]] || continue
    group=${file%/*}
    group=${group##*/}
    name=${file##*/}
    name=${name%.sh}
    printf '%s|%s|%s|%s\n' "$group" "$name" "$(customgames_field "$file" mode)" "$(customgames_field "$file" command)"
  done
  return 0
}

# ── Pastas de jogo em squashfs ──
# config/fliperos-squashgames (o ajudante root): a pasta vira PASTA.squashfs,
# montada no mesmo lugar com uma camada gravavel por cima. O Setup roda como
# root e chama o ajudante direto.
SQUASHGAMES_CMD=${SQUASHGAMES_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-squashgames}

# squashgames_list imprime "pasta|montada (0 ou 1)|tamanho do arquivo".
squashgames_list() {
  [[ -x $SQUASHGAMES_CMD ]] || return 0
  "$SQUASHGAMES_CMD" list
}

# squashgames_run pack|unpack PASTA: com os eventos da tela de progresso.
squashgames_run() {
  ev_step 0 "Starting"
  if [[ ! -x $SQUASHGAMES_CMD ]]; then
    ev_fail "the squashfs helper ($SQUASHGAMES_CMD) is missing"
    return 1
  fi
  log_line cmd "\$ $SQUASHGAMES_CMD $1 $2 --progress"
  "$SQUASHGAMES_CMD" "$1" "$2" --progress 2>> "$FLIPEROS_LOG"
}

# customgames_refresh regrava o script de cada entrada (o System Update,
# tools/cabinet-update.sh): pelo cfg, e as de um comando sem cfg (as de antes
# dele, e as de antes do --app, que abriam como o programa "bash") ganham o
# cfg. As postas a mao, sem o cabecalho, ficam.
customgames_refresh() {
  local group name mode cmd
  while IFS='|' read -r group name mode cmd; do
    if [[ -f $(customgames_cfg "$group" "$name") ]]; then
      customgames_entry "$group" "$name" || log_warn "jogo personalizado nao regravado: $group / $name"
      continue
    fi
    [[ -n $mode && -n $cmd ]] || continue
    customgames_save "$group" "$name" "$mode" "$cmd" > /dev/null || log_warn "jogo personalizado nao regravado: $group / $name"
  done < <(customgames_list)
  return 0
}
