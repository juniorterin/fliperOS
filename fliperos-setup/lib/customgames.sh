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
    printf 'exec %q --mode %q bash -c %q\n' "$CUSTOM_GAMES_RUN" "$mode" "$cmd"
  } > "$file.new" || return 1
  chmod 755 "$file.new"
  mv -f "$file.new" "$file" || return 1
  chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$dir" "$file" 2> /dev/null
  if [[ -n $old_name && ($old_group != "$group" || $old_name != "$name") ]]; then
    customgames_delete "$old_group" "$old_name"
  fi
  log_info "jogo personalizado: $group / $name ($mode): $cmd"
}

# customgames_delete GRUPO NOME apaga a entrada (e o grupo, se ficou vazio).
customgames_delete() {
  rm -f "$(customgames_file "$1" "$2")" || return 1
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
