# shellcheck shell=bash
# Setup > Games > Custom games: jogos e programas que nao sao uma ROM de um
# emulador do FliperOS (um jogo de PC, um emulador trazido pela pessoa, um
# script), em grupos que os frontends mostram como sistemas.
#
# Cada grupo e uma pasta ~/roms/custom/GRUPO e cada entrada um script
# NOME.sh nela: o nome do arquivo e o que o frontend mostra. O script abre o
# comando pelo fliperos-x11-run, num Xorg so dele no modo da entrada (o
# Switchres cria o modo; a 15 kHz 640x480 sai entrelacado). O modo e o
# comando ficam tambem no cabecalho, para o Setup editar. Nos frontends a
# pasta e o sistema "custom/GRUPO" (scraper_detect), aberto com o sh.

CUSTOM_GAMES_DIR=${CUSTOM_GAMES_DIR:-$ROMS_DIR/custom}
CUSTOM_GAMES_RUN=${CUSTOM_GAMES_RUN:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-x11-run}
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

# customgames_save GRUPO NOME MODO COMANDO [GRUPO_ANTES NOME_ANTES] grava a
# entrada (editada: a de antes sai). Status 1: nome, modo ou comando invalido.
customgames_save() {
  local group=$1 name=$2 mode cmd=$4 old_group=${5:-} old_name=${6:-} file dir
  customgames_valid_name "$group" && customgames_valid_name "$name" && customgames_valid_command "$cmd" ||
    return 1
  mode=$(customgames_mode "$3") || return 1
  dir=$CUSTOM_GAMES_DIR/$group
  file=$(customgames_file "$group" "$name")
  mkdir -p "$dir" || return 1
  {
    echo '#!/bin/sh'
    echo '# FliperOS custom game (Setup > Games > Custom games). Edited there, or here.'
    echo "# mode: $mode"
    echo "# command: $cmd"
    printf 'exec %q --mode %q --app %q bash -c %q\n' "$CUSTOM_GAMES_RUN" "$mode" "$(customgames_app "$group" "$name")" "$cmd"
  } > "$file.new" || return 1
  chmod 755 "$file.new"
  mv -f "$file.new" "$file" || return 1
  chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$dir" "$file" 2> /dev/null
  if [[ -n $old_name && ($old_group != "$group" || $old_name != "$name") ]]; then
    # As midias vao junto (as de exemplo sao refeitas com o nome novo).
    customgames_media_rename "$old_group" "$old_name" "$group" "$name"
    customgames_delete "$old_group" "$old_name"
  fi
  log_info "jogo personalizado: $group / $name ($mode): $cmd"
}

# customgames_delete GRUPO NOME apaga a entrada (e o grupo, se ficou vazio)
# e as midias de exemplo dela.
customgames_delete() {
  rm -f "$(customgames_file "$1" "$2")" || return 1
  customgames_media_drop "$1" "$2"
  rmdir "$CUSTOM_GAMES_DIR/$1" 2> /dev/null
  log_info "jogo personalizado apagado: $1 / $2"
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

# customgames_refresh regrava o script de cada entrada com o cabecalho (o
# System Update, tools/cabinet-update.sh): as gravadas antes do --app abriam
# como o programa "bash". As postas a mao, sem o cabecalho, ficam.
customgames_refresh() {
  local group name mode cmd
  while IFS='|' read -r group name mode cmd; do
    [[ -n $mode && -n $cmd ]] || continue
    customgames_save "$group" "$name" "$mode" "$cmd" > /dev/null || log_warn "jogo personalizado nao regravado: $group / $name"
  done < <(customgames_list)
  return 0
}
