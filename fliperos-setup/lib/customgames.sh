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
# Os pacotes (JOGO.fliperos-customgame.zip) ficam numa pasta so,
# ~/roms/custom-packages: o Install games os lista (os instalados tambem,
# com o grupo) e pergunta o grupo ao instalar; o Create package grava nela.
# Depois de instalar, a pessoa escolhe se o zip fica (o cfg do jogo o anota)
# ou sai.

CUSTOM_GAMES_DIR=${CUSTOM_GAMES_DIR:-$ROMS_DIR/custom}
CUSTOM_GAMES_PACKAGES=${CUSTOM_GAMES_PACKAGES:-$ROMS_DIR/custom-packages}
CUSTOM_GAMES_RUN=${CUSTOM_GAMES_RUN:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-x11-run}
CUSTOM_GAMES_TOOL=${CUSTOM_GAMES_TOOL:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-customgame}
# As pastas dos jogos dos pacotes: ~/games/GRUPO/NOME.
CUSTOM_GAMES_GAMES=${CUSTOM_GAMES_GAMES:-$(dirname "$ROMS_DIR")/games}
# 0: a pasta do jogo instalado fica solta (sem o squashfs).
CUSTOM_GAMES_SQUASH=${CUSTOM_GAMES_SQUASH:-1}
# O Wine no comando (o do fliperos-x11-client): a camada de 32 bits.
CUSTOM_GAMES_WINE_RE='(^|[[:space:]/;&(])wine(64)?([[:space:]]|$)|\.[eE][xX][eE]([[:space:]"]|$)'
# As resolucoes da lista: 240p, 240p-hack e 480i (a 15 kHz, entrelacado pelo
# Switchres). 240p-hack ("240p hack (Mugen)"): 240p no tubo, com o jogo vendo
# uma tela de 640x480 (fliperos-x11-run --mode MODO/TELA), para o jogo do
# Windows que so abre em 640x480 (o MUGEN em tela cheia).
CUSTOM_GAMES_MODES="240p|640x240@60 240p-hack|640x240@60/640x480 480i|640x480@60"

# customgames_valid_name TEXTO: serve de nome de grupo ou de entrada (vira
# nome de pasta ou de arquivo e item de lista).
customgames_valid_name() {
  [[ -n ${1//[[:space:]]/} && $1 != *[/\|]* && $1 != *$'\n'* && $1 != . && $1 != .. && $1 != .* ]]
}

# customgames_valid_command TEXTO: uma linha so.
customgames_valid_command() {
  [[ -n ${1//[[:space:]]/} && $1 != *$'\n'* ]]
}

# customgames_mode 240p|240p-hack|480i|LARGURAxALTURA@HZ[/LxA] imprime o modo do
# fliperos-x11-run. Status 1: invalido.
customgames_mode() {
  local pair
  for pair in $CUSTOM_GAMES_MODES; do
    [[ $1 == "${pair%%|*}" ]] && { printf '%s\n' "${pair#*|}"; return 0; }
  done
  [[ $1 =~ ^[1-9][0-9]{1,3}x[1-9][0-9]{1,3}@[1-9][0-9]{0,2}(\.[0-9]+)?(/[1-9][0-9]{1,3}x[1-9][0-9]{1,3})?$ ]] || return 1
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
    logo) echo "png jpg jpeg webp" ;;
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
# category, controls, buttons, players, year, developer; o de um pacote, folder= e package=).

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
  mode=$(customgames_mode "${mode:-480i}") || return 1
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
  for key in category controls buttons players year developer; do
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
# novo). Com folder, tambem a pasta do jogo (e o squashfs dela), antes de
# tudo: em uso (o jogo aberto), status 1 e nada sai (da para tentar de novo).
customgames_delete() {
  local cfg folder="" package="" rc
  cfg=$(customgames_cfg "$1" "$2")
  if [[ -f $cfg ]]; then
    folder=$(customgames_cfg_field "$cfg" folder)
    package=$(customgames_cfg_field "$cfg" package)
  fi
  if [[ ${3:-} == folder && -n $folder ]]; then
    customgames_remove_folder "$folder"
    rc=$?
    # 2: a pasta fica fora de ~/games (nao e do FliperOS): so a entrada sai.
    ((rc == 1)) && return 1
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
  rmdir "$CUSTOM_GAMES_DIR/$1" 2> /dev/null
  log_info "jogo personalizado apagado: $1 / $2${3:+ (com a pasta $folder)}"
  return 0
}

# customgames_remove_folder PASTA apaga a pasta de um jogo instalado (so
# dentro de ~/games), empacotada ou nao, e a do grupo se ficou vazia. Status
# 1: nao saiu (o squashfs em uso); 2: fora de ~/games (fica).
customgames_remove_folder() {
  local folder base
  base=$(realpath -m -- "$CUSTOM_GAMES_GAMES") || return 1
  folder=$(realpath -m -s -- "$1") || return 1
  [[ $folder == "$base"/*/* && $folder != */.* ]] || { log_warn "pasta fora de $base: $1"; return 2; }
  if [[ -e $folder.squashfs || -n $(squashgames_list | awk -F'|' -v f="$folder" '$1 == f') ]]; then
    "$SQUASHGAMES_CMD" remove "$folder" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1 || return 1
  fi
  rm -rf -- "$folder"
  rmdir -- "${folder%/*}" 2> /dev/null
  return 0
}

# ── Apagar um grupo inteiro ──
# Antes o grupo so saia quando o ultimo jogo saia, e so se a pasta
# ~/roms/custom/GRUPO ficasse vazia (um pacote ou outro arquivo la o
# segurava); um grupo vazio nao saia nunca.

# customgames_group_own NOME: um arquivo da pasta do grupo que e do FliperOS
# ou do sistema (as entradas, os .tmp de uma gravacao cortada, o lixo que o
# Windows e o macOS deixam pelo compartilhamento).
customgames_group_own() {
  local low=${1,,}
  case $low in
    *.sh | *.cfg | *.key | *.tmp | *.new | *.part | thumbs.db | desktop.ini | .ds_store | ._* | .directory | .icon | .logo.png) return 0 ;;
  esac
  return 1
}

# customgames_group_info GRUPO: o que apagar o grupo leva, em CHAVE=VALOR:
# games= (os jogos), folders= (os que tem a pasta em ~/games), packages= (os
# .fliperos-customgame.zip da pasta dele), others= (quantos arquivos de outro
# tipo) e other= (os nomes dos primeiros, separados por " / ").
customgames_group_info() {
  local group=$1 dir g name file base games=0 folders=0 packages=0 others=0 other=""
  dir=$CUSTOM_GAMES_DIR/$group
  while IFS='|' read -r g name _; do
    [[ $g == "$group" ]] || continue
    ((games++))
    [[ -n $(customgames_cfg_field "$(customgames_cfg "$group" "$name")" folder) ]] && ((folders++))
  done < <(customgames_list)
  while IFS= read -r -d '' file; do
    base=${file##*/}
    if [[ ${base,,} == *.fliperos-customgame.zip && -f $file ]]; then
      ((packages++))
    elif ! customgames_group_own "$base"; then
      ((others++))
      ((others <= 5)) && other+="${other:+ / }$base"
    fi
  done < <(find -H "$dir" -mindepth 1 -maxdepth 1 -print0 2> /dev/null | LC_ALL=C sort -z)
  printf 'games=%s\nfolders=%s\npackages=%s\nothers=%s\nother=%s\n' "$games" "$folders" "$packages" "$others" "$other"
}

# customgames_package_keep ZIP: um pacote fora da pasta deles (o de um grupo
# que vai sair, os de antes dela) vai para ~/roms/custom-packages e imprime
# onde ficou. Ja havendo um com esse nome la: o mesmo arquivo sai (imprime o
# de la), outro ganha "(GRUPO)" no nome (GRUPO: a pasta de onde veio).
customgames_package_keep() {
  local zip=$1 group base stem dest n=2
  group=${zip%/*}
  group=${group##*/}
  base=${zip##*/}
  stem=${base:0:${#base}-24}
  customgames_packages_dir
  dest=$CUSTOM_GAMES_PACKAGES/$base
  if [[ -e $dest ]]; then
    cmp -s -- "$zip" "$dest" && { rm -f -- "$zip"; printf '%s\n' "$dest"; return 0; }
    dest="$CUSTOM_GAMES_PACKAGES/$stem ($group).fliperos-customgame.zip"
    while [[ -e $dest ]]; do
      dest="$CUSTOM_GAMES_PACKAGES/$stem ($group $n).fliperos-customgame.zip"
      ((n++))
    done
  fi
  mv -- "$zip" "$dest" && chown "$FLIPEROS_USER:" "$dest" 2> /dev/null
  printf '%s\n' "$dest"
  return 0
}

# customgames_packages_dir: a pasta dos pacotes, criada (do jogador: aparece
# no compartilhamento \\fliperos\roms).
customgames_packages_dir() {
  [[ -d $CUSTOM_GAMES_PACKAGES ]] && return 0
  mkdir -p "$CUSTOM_GAMES_PACKAGES" 2> /dev/null &&
    chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_PACKAGES" 2> /dev/null
  return 0
}

# customgames_packages_migrate: os pacotes de antes da pasta deles (soltos em
# ~/roms/custom e nas pastas dos grupos) vao para ~/roms/custom-packages, e o
# cfg do jogo instalado de um deles passa a apontar o zip no lugar novo (o
# mv guarda o tamanho e a data: ele continua instalado). O System Update e a
# tela Custom games chamam; sem pacote fora do lugar, nada muda.
customgames_packages_migrate() {
  local zip dest cfg
  local -a zips=()
  [[ -d $CUSTOM_GAMES_DIR ]] || return 0
  mapfile -d '' -t zips < <(find -H "$CUSTOM_GAMES_DIR" -mindepth 1 -maxdepth 2 -type f \
    -iname '*.fliperos-customgame.zip' -not -path '*/.*' -print0 2> /dev/null)
  ((${#zips[@]})) || return 0
  for zip in "${zips[@]}"; do
    dest=$(customgames_package_keep "$zip")
    for cfg in "$CUSTOM_GAMES_DIR"/*/*.cfg; do
      [[ -f $cfg && $(customgames_cfg_field "$cfg" package) == "$zip" ]] || continue
      customgames_cfg_set "$cfg" package "$dest"
    done
    log_info "pacote movido para a pasta dos pacotes: $zip -> $dest"
  done
  return 0
}

# customgames_package_delete ZIP: apaga um pacote da pasta deles (o jogo
# instalado dele fica; o cfg deixa de apontar o zip). Status 2: o ZIP nao e
# um pacote da pasta.
customgames_package_delete() {
  local zip=$1 base real cfg
  base=$(realpath -m -- "$CUSTOM_GAMES_PACKAGES") || return 2
  real=$(realpath -m -s -- "$zip") || return 2
  [[ $real == "$base"/* && ${real,,} == *.zip && -f $real ]] || return 2
  rm -f -- "$real" || return 1
  for cfg in "$CUSTOM_GAMES_DIR"/*/*.cfg; do
    [[ -f $cfg && $(customgames_cfg_field "$cfg" package) == "$real" ]] || continue
    customgames_cfg_set "$cfg" package "" && customgames_cfg_set "$cfg" package_stamp ""
  done
  log_info "pacote apagado: $real"
  return 0
}

# O ultimo grupo em que um pacote foi instalado: o Install games o traz
# marcado na proxima vez.
customgames_last_group_file() {
  printf '%s/.config/fliperos/customgame-last-group\n' "$(dirname "$ROMS_DIR")"
}

# customgames_last_group: o ultimo grupo usado que ainda existe (ou nada).
customgames_last_group() {
  local group
  group=$(head -n 1 "$(customgames_last_group_file)" 2> /dev/null)
  [[ -n $group && -d $CUSTOM_GAMES_DIR/$group ]] && printf '%s\n' "$group"
  return 0
}

customgames_last_group_set() {
  local file
  file=$(customgames_last_group_file)
  mkdir -p "$(dirname "$file")" 2> /dev/null && printf '%s\n' "$1" > "$file" 2> /dev/null &&
    chown "$FLIPEROS_USER:" "$(dirname "$file")" "$file" 2> /dev/null
  return 0
}

# customgames_group_delete GRUPO [all]: apaga cada jogo do grupo (como o
# Delete de um jogo), a pasta ~/roms/custom/GRUPO com o que sobrou nela e as
# pastas vazias das midias e de ~/games. Um pacote que esteja na pasta do
# grupo vai para ~/roms/custom-packages; com all, ele e as pastas dos jogos
# (e as midias que a pessoa pos) saem tambem. Os pacotes da pasta deles
# ficam sempre. Com os eventos da tela de progresso. Status 1: a pasta de
# algum jogo nao saiu (o jogo aberto): o grupo fica, com ele.
customgames_group_delete() {
  local group=$1 all=${2:-} dir g name zip kind n=0 total
  local -a names=()
  dir=$CUSTOM_GAMES_DIR/$group
  customgames_valid_name "$group" && [[ -d $dir ]] || return 2
  while IFS='|' read -r g name _; do
    [[ $g == "$group" ]] && names+=("$name")
  done < <(customgames_list)
  total=${#names[@]}
  for name in "${names[@]}"; do
    ev_step $((90 * n / (total ? total : 1))) "Deleting $name"
    ((n++))
    if ! customgames_delete "$group" "$name" "$([[ $all == all ]] && echo folder)"; then
      ev_fail "could not delete the folder of $name: close the game and try again"
      return 1
    fi
  done
  ev_step 92 "Deleting the group $group"
  if [[ -d $dir ]]; then
    while IFS= read -r -d '' zip; do
      if [[ $all == all ]]; then rm -f -- "$zip"; else customgames_package_keep "$zip" > /dev/null; fi
    done < <(find -H "$dir" -mindepth 1 -maxdepth 1 -type f -iname '*.fliperos-customgame.zip' -print0 2> /dev/null)
    # Um link (a pasta do grupo em outro disco) sai so ele.
    rm -rf -- "$dir"
  fi
  for kind in $CUSTOM_GAMES_MEDIA_TYPES; do
    if [[ $all == all ]]; then
      rm -rf -- "$CUSTOM_GAMES_MEDIA/$kind/custom/$group"
    else
      rmdir -- "$CUSTOM_GAMES_MEDIA/$kind/custom/$group" 2> /dev/null
    fi
  done
  rmdir -- "$CUSTOM_GAMES_GAMES/$group" 2> /dev/null
  log_info "grupo de jogos personalizados apagado: $group ($total jogos${all:+, com as pastas e os pacotes})"
  ev_step 100 "$group deleted"
  return 0
}

# ── Os pacotes ──

# customgames_tool COMANDO...: o config/fliperos-customgame com as pastas
# daqui (as dos testes tambem).
customgames_tool() {
  python3 "$CUSTOM_GAMES_TOOL" --roms "$CUSTOM_GAMES_DIR" --games "$CUSTOM_GAMES_GAMES" --media "$CUSTOM_GAMES_MEDIA" \
    --packages "$CUSTOM_GAMES_PACKAGES" "$@"
}

# customgames_found PASTA: o que veio com a pasta de um jogo na estrutura do
# pacote (fliperos-customgame found) em CG_FOUND_FOLDER (a pasta do jogo: a
# de dentro, quando PASTA e o zip aberto), CG_FOUND_SNAP, CG_FOUND_LOGO (o
# JOGO.logo.png, .jpg ou .webp), CG_FOUND_VIDEO, CG_FOUND_TEXT, CG_FOUND_KEY,
# CG_FOUND_PPDB, CG_FOUND_YEAR, CG_FOUND_DEVELOPER, CG_FOUND_EXE e CG_FOUND_RUNNER
# (o exe= e o runner= do JOGO.cfg, dentro da pasta do jogo).
customgames_found() {
  local line key value
  CG_FOUND_FOLDER=$1 CG_FOUND_SNAP="" CG_FOUND_VIDEO="" CG_FOUND_TEXT="" CG_FOUND_KEY="" CG_FOUND_PPDB=""
  CG_FOUND_EXE="" CG_FOUND_RUNNER="" CG_FOUND_YEAR="" CG_FOUND_DEVELOPER="" CG_FOUND_LOGO=""
  while IFS= read -r line; do
    key=${line%%=*} value=${line#*=}
    case $key in
      folder) [[ -d $value ]] && CG_FOUND_FOLDER=$value ;;
      snap) CG_FOUND_SNAP=$value ;;
      logo) CG_FOUND_LOGO=$value ;;
      video) CG_FOUND_VIDEO=$value ;;
      text) CG_FOUND_TEXT=$value ;;
      key) CG_FOUND_KEY=$value ;;
      ppdb) CG_FOUND_PPDB=$value ;;
      cfg_exe) CG_FOUND_EXE=$value ;;
      cfg_runner) CG_FOUND_RUNNER=$value ;;
      cfg_year) CG_FOUND_YEAR=$value ;;
      cfg_developer) CG_FOUND_DEVELOPER=$value ;;
    esac
  done < <(customgames_tool found "$1" 2>> "${FLIPEROS_LOG:-/dev/null}")
  return 0
}

# customgames_pending: os pacotes de ~/roms/custom-packages,
# "ZIP|GRUPO|NOME|PLATAFORMA|ESTADO|MOTIVO" (fliperos-customgame pending:
# ESTADO new, update, installed, com GRUPO, ou bad).
customgames_pending() {
  [[ -d $CUSTOM_GAMES_PACKAGES ]] || return 0
  customgames_tool pending 2>> "${FLIPEROS_LOG:-/dev/null}"
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
  local zip=$1 group=$2 replace=${3:-} info name cfg folder rc
  local -a opts=()
  ev_step 0 "Checking the package"
  if ! info=$(customgames_tool inspect "$zip" 2>&1); then
    ev_fail "${info:-not a FliperOS game package}"
    return 1
  fi
  name=$(sed -n 's/^name=//p' <<< "$info")
  cfg=$(customgames_cfg "$group" "$name")
  if [[ -n $replace ]]; then
    opts+=(--replace)
    # A pasta de antes, empacotada, sai antes (o zip a traz de novo).
    folder=$(customgames_cfg_field "$cfg" folder)
    [[ -n $folder && -e $folder.squashfs ]] && { customgames_remove_folder "$folder" || { ev_fail "close the game first: $folder is in use"; return 1; }; }
  fi
  # O PortProton de um jogo do Windows: a tela o pergunta e instala antes
  # (screen_portproton_need); sem ele o jogo abre pelo Wine do sistema.
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
  # 75 a 99: as etapas do empacotamento; uma falha so avisa.
  customgames_squash "$(customgames_cfg_field "$cfg" folder)" 75 99
  customgames_last_group_set "$group"
  ev_step 100 "$name installed"
  log_info "pacote instalado: $zip em $group / $name"
  return 0
}

# customgames_squash PASTA INICIO FIM: a pasta de um jogo instalado em
# squashfs (CUSTOM_GAMES_SQUASH), com as etapas entre INICIO e FIM %. Sem dar,
# ela fica solta: o jogo abre igual, e a tela so ganha um aviso.
customgames_squash() {
  local folder=$1 start=$2 end=$3
  ((CUSTOM_GAMES_SQUASH)) && [[ -x $SQUASHGAMES_CMD && -d $folder ]] && ((EUID == 0)) || return 0
  "$SQUASHGAMES_CMD" pack "$folder" --progress 2>> "${FLIPEROS_LOG:-/dev/null}" |
    awk -v s="$start" -v e="$end" '/^@(step|pct) [0-9]+/ { $2 = int(s + $2 * (e - s) / 100); print; fflush(); next }
         /^@fail / { sub(/^@fail [^|]*\|/, ""); print "@msg Not packed: " $0; fflush() }'
  return 0
}

# ── O PortProton (os jogos do Windows) ──
# config/fliperos-portproton: instalado so quando o primeiro jogo custom do
# Windows aparece (criar um pacote ou instalar um), na home do jogador.
CUSTOM_GAMES_PORTPROTON=${CUSTOM_GAMES_PORTPROTON:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-portproton}

portproton_installed() {
  [[ -x $CUSTOM_GAMES_PORTPROTON ]] && "$CUSTOM_GAMES_PORTPROTON" check > /dev/null 2>&1
}

# portproton_ensure INICIO FIM: dentro de uma tela de progresso, instala o
# PortProton se falta, com as etapas dele entre INICIO e FIM %.
portproton_ensure() {
  local start=$1 end=$2 rc
  portproton_installed && return 0
  if [[ ! -x $CUSTOM_GAMES_PORTPROTON ]]; then
    ev_fail "the PortProton installer ($CUSTOM_GAMES_PORTPROTON) is missing"
    return 1
  fi
  ev_step "$start" "Installing PortProton (Windows games)"
  "$CUSTOM_GAMES_PORTPROTON" install --progress 2>> "${FLIPEROS_LOG:-/dev/null}" |
    awk -v s="$start" -v e="$end" '/^@(step|pct) [0-9]+/ { $2 = int(s + $2 * (e - s) / 100); print; fflush(); next }
      { print; fflush() }'
  rc=${PIPESTATUS[0]}
  ((rc == 0)) && portproton_installed && return 0
  ((rc == 0)) && ev_fail "PortProton did not start (details in /var/log/fliperos-setup.log)"
  return 1
}

# portproton_run_install: so a instalacao, com a tela de progresso.
portproton_run_install() {
  ev_step 0 "Starting"
  portproton_ensure 0 100 || return 1
  ev_step 100 "PortProton installed"
}

# customgames_pending_ok: os pacotes por instalar (new) e os que mudaram
# desde a instalacao (update).
customgames_pending_ok() {
  customgames_pending | awk -F'|' '$5 == "new" || $5 == "update"'
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

# ── O icone de cada grupo ──
# GRUPO/.icon guarda o nome de um desenho (os de gui/theme.py, os mesmos
# px-NOME do painel web): o azulejo do grupo no Setup, o cabecalho dele no
# painel e o azulejo dele na tira do frontend o mostram. Sem o arquivo, o
# grupo fica com o desenho padrao. "nome|rotulo", na ordem do seletor.
CUSTOM_GAMES_ICONS=(
  "games|Gamepad" "customgames|Game box" "arcade|Arcade cabinet" "pad|Joypad" "joysticks|Joystick" "guncon|Light gun"
  "axes|Wheel" "keyboard|Keyboard" "emulators|Emulator" "video|Monitor" "audio|Sound" "disk|Disk" "chip|Chip"
  "desktop|Desktop PC" "network|Network" "cloud|Cloud" "lab|Lab flask" "physical|Disc" "achievements|Trophy"
)

# customgames_icon_valid NOME: um dos desenhos da lista.
customgames_icon_valid() {
  local entry
  for entry in "${CUSTOM_GAMES_ICONS[@]}"; do
    [[ ${entry%%|*} == "$1" ]] && return 0
  done
  return 1
}

# customgames_group_icon GRUPO imprime o desenho escolhido (nada: o padrao).
customgames_group_icon() {
  local icon
  icon=$(head -n 1 "$CUSTOM_GAMES_DIR/$1/.icon" 2> /dev/null | tr -d '[:space:]')
  customgames_icon_valid "$icon" && printf '%s\n' "$icon"
  return 0
}

# customgames_group_icon_set GRUPO [ICONE] grava o desenho do grupo (sem ICONE
# o grupo volta ao padrao). Status 2: grupo ou desenho que nao serve.
customgames_group_icon_set() {
  local group=$1 icon=${2:-} file
  customgames_valid_name "$group" && [[ -d $CUSTOM_GAMES_DIR/$group ]] || return 2
  file=$CUSTOM_GAMES_DIR/$group/.icon
  if [[ -z $icon ]]; then
    rm -f -- "$file"
    return 0
  fi
  customgames_icon_valid "$icon" || return 2
  printf '%s\n' "$icon" > "$file.new" && mv -f "$file.new" "$file" || return 1
  chown "$FLIPEROS_USER:" "$file" 2> /dev/null
  return 0
}

# ── O logotipo de cada grupo ──
# GRUPO/.logo.png: o logotipo de uma cor so que o marquee e a tira do frontend
# mostram do grupo, como o dos sistemas (config/fliperos-syslogo desenha o do
# grupo no lugar do da fonte, com o mesmo nome, na cor de quem o pede). Ou e o
# desenho de uma imagem da pessoa (so o desenho conta: o canal alfa, ou o que
# difere do fundo), ou e um dos logotipos que o FliperOS ja tem (a lista do
# syslogo), para quem nao quer subir o seu.
CUSTOM_GAMES_SYSLOGO=${CUSTOM_GAMES_SYSLOGO:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-syslogo}

# customgames_logo_list imprime "nome<TAB>rotulo" de cada logotipo da lista.
customgames_logo_list() {
  [[ -f $CUSTOM_GAMES_SYSLOGO ]] || return 0
  python3 "$CUSTOM_GAMES_SYSLOGO" list 2> /dev/null
  return 0
}

# customgames_group_logo GRUPO: o grupo tem o logotipo (status 0).
customgames_group_logo() {
  [[ -f $CUSTOM_GAMES_DIR/$1/.logo.png ]]
}

# customgames_group_logo_set GRUPO [IMAGEM | system:NOME] grava o logotipo do
# grupo: o desenho da IMAGEM (um arquivo) ou o logotipo NOME da lista; sem o
# segundo, o grupo fica sem logotipo (o icone volta). Status 2: o grupo, o
# arquivo ou o nome nao servem; 1: a imagem nao abre ou nao tem desenho.
customgames_group_logo_set() {
  local group=$1 source=${2:-} file tmp
  customgames_valid_name "$group" && [[ -d $CUSTOM_GAMES_DIR/$group ]] || return 2
  file=$CUSTOM_GAMES_DIR/$group/.logo.png
  if [[ -z $source ]]; then
    rm -f -- "$file"
    return 0
  fi
  [[ -f $CUSTOM_GAMES_SYSLOGO ]] || return 1
  tmp=$file.new
  if [[ $source == system:* ]]; then
    [[ -n ${source#system:} ]] || return 2
    python3 "$CUSTOM_GAMES_SYSLOGO" copy "${source#system:}" "$tmp" > /dev/null 2>&1 || { rm -f "$tmp"; return 2; }
  else
    [[ -f $source ]] || return 2
    python3 "$CUSTOM_GAMES_SYSLOGO" import "$source" "$tmp" > /dev/null 2>> "${FLIPEROS_LOG:-/dev/null}" ||
      { rm -f "$tmp"; return 1; }
  fi
  mv -f "$tmp" "$file" || return 1
  chmod 644 "$file"
  chown "$FLIPEROS_USER:" "$file" 2> /dev/null
  log_info "logotipo do grupo $group: ${source##*/}"
  return 0
}

# ── Renomear um grupo ──
# O nome do grupo e a pasta ~/roms/custom/GRUPO, a chave do sistema nos
# frontends, a pasta ~/games/GRUPO dos jogos instalados, as midias em
# ~/media/TIPO/custom/GRUPO, o nome do filtro de flicker e da OSD de cada jogo
# (custom_GRUPO_NOME) e os favoritos e as partidas do frontend do FliperOS:
# tudo vai junto, o logotipo e o icone do grupo tambem (estao na pasta dele).

# customgames_move_dir ANTES DEPOIS: mv que serve a troca so de maiusculas num
# disco que nao as distingue (a pasta de DEPOIS ja e a de ANTES).
customgames_move_dir() {
  if [[ -e $2 ]]; then
    mv -- "$1" "$1.rename.$$" && mv -- "$1.rename.$$" "$2"
  else
    mv -- "$1" "$2"
  fi
}

# customgames_games_move ANTES DEPOIS: a pasta ~/games/GRUPO muda de nome. Com
# pastas em squashfs dentro, o ajudante as desmonta, move e monta de novo (um
# jogo aberto segura a pasta: status 1 e nada muda).
customgames_games_move() {
  if [[ -n $(squashgames_list 2> /dev/null | awk -F'|' -v d="$1/" 'index($1, d) == 1 { print; exit }') ]]; then
    "$SQUASHGAMES_CMD" rename-dir "$1" "$2" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1
  else
    customgames_move_dir "$1" "$2"
  fi
}

# customgames_app_move APP_ANTES APP_NOVO: o filtro de flicker e o perfil da
# OSD de um jogo seguem o nome novo (customgames_app muda com o grupo).
customgames_app_move() {
  local prefix value profiles=${FLIPEROS_OSD_PROFILES:-/etc/fliperos/osd-profiles.conf}
  [[ $1 == "$2" ]] && return 0
  for prefix in deflicker_ deflicker_level_ mode480_; do
    if value=$(conf_get "$prefix$1" 2> /dev/null); then
      conf_set "$prefix$2" "$value" && conf_unset "$prefix$1"
    fi
  done
  [[ -f $profiles ]] && sed -i -e "s/^emu:$1\t/emu:$2\t/" -e "s#^game:$1/#game:$2/#" "$profiles"
  return 0
}

# customgames_group_running GRUPO: um jogo do grupo esta aberto (o executor
# tem o cfg dele na linha de comando: "fliperos-customgame run .../GRUPO/X.cfg").
customgames_group_running() {
  local pid cmd
  command -v pgrep > /dev/null || return 1
  for pid in $(pgrep -f fliperos-customgame 2> /dev/null); do
    cmd=$(tr '\0' ' ' < "/proc/$pid/cmdline" 2> /dev/null)
    [[ $cmd == *" run $CUSTOM_GAMES_DIR/$1/"* ]] && return 0
  done
  return 1
}

# customgames_group_rename GRUPO NOVO: o grupo passa a se chamar NOVO.
# Status 2: um dos nomes nao serve ou o grupo nao existe; 3: ja ha um grupo
# com o nome novo; 4: ~/games/NOVO tem outra coisa; 1: nao deu (um jogo do
# grupo esta aberto: a pasta dele nao pode andar, e o squashfs dele seria
# remontado por cima da camada que o jogo usa); em 3, 4 e 1 nada mudou.
customgames_group_rename() {
  local old=$1 new=$2 games=$CUSTOM_GAMES_GAMES home g name cfg folder kind src dst file
  local -a names=()
  customgames_valid_name "$old" && customgames_valid_name "$new" && [[ -d $CUSTOM_GAMES_DIR/$old ]] || return 2
  [[ $old == "$new" ]] && return 0
  [[ -e $CUSTOM_GAMES_DIR/$new && ! $CUSTOM_GAMES_DIR/$new -ef $CUSTOM_GAMES_DIR/$old ]] && return 3
  customgames_group_running "$old" && return 1
  while IFS='|' read -r g name _; do
    [[ $g == "$old" ]] && names+=("$name")
  done < <(customgames_list)
  # As pastas dos jogos instalados: a primeira coisa, porque e a que pode falhar.
  if [[ -d $games/$old ]]; then
    rmdir -- "$games/$new" 2> /dev/null
    [[ -e $games/$new && ! $games/$new -ef $games/$old ]] && return 4
    customgames_games_move "$games/$old" "$games/$new" || return 1
  fi
  if ! customgames_move_dir "$CUSTOM_GAMES_DIR/$old" "$CUSTOM_GAMES_DIR/$new"; then
    [[ -d $games/$new ]] && customgames_games_move "$games/$new" "$games/$old"
    return 1
  fi
  # As midias de exemplo trazem o nome antigo escrito: saem, e as de verdade
  # (as da pessoa) vao para a pasta nova, onde as de exemplo sao refeitas.
  for name in "${names[@]}"; do
    customgames_media_drop "$old" "$name"
  done
  for kind in $CUSTOM_GAMES_MEDIA_TYPES; do
    src=$CUSTOM_GAMES_MEDIA/$kind/custom/$old dst=$CUSTOM_GAMES_MEDIA/$kind/custom/$new
    [[ -d $src ]] || continue
    if [[ -e $dst && ! $dst -ef $src ]]; then
      find "$src" -mindepth 1 -maxdepth 1 -exec mv -n -t "$dst" {} + 2> /dev/null
      rmdir -- "$src" 2> /dev/null
    else
      customgames_move_dir "$src" "$dst"
    fi
  done
  # O cfg de cada jogo (a pasta dele em ~/games), o script (o nome do filtro) e
  # os ajustes que levam esse nome.
  for name in "${names[@]}"; do
    cfg=$(customgames_cfg "$new" "$name")
    if [[ -f $cfg ]]; then
      folder=$(customgames_cfg_field "$cfg" folder)
      [[ $folder == "$games/$old/"* ]] && customgames_cfg_set "$cfg" folder "$games/$new/${folder#"$games/$old/"}"
      customgames_entry "$new" "$name" || log_warn "jogo personalizado nao regravado: $new / $name"
    fi
    customgames_app_move "$(customgames_app "$old" "$name")" "$(customgames_app "$new" "$name")"
    customgames_media "$new" "$name"
  done
  customgames_media_dirs "$new"
  # O frontend do FliperOS: favoritos (a chave do sistema) e partidas.
  home=$(dirname "$ROMS_DIR")
  file=$home/.config/fliperos/favourites
  if [[ -f $file ]]; then
    OLD="custom/$old" NEW="custom/$new" awk -F'\t' 'BEGIN { OFS = "\t" } $1 == ENVIRON["OLD"] { $1 = ENVIRON["NEW"] } { print }' \
      "$file" > "$file.new" && cat "$file.new" > "$file"
    rm -f "$file.new"
  fi
  src=$home/.local/share/fliperos/stats/$old dst=$home/.local/share/fliperos/stats/$new
  [[ -d $src && ! -e $dst ]] && mv -- "$src" "$dst"
  rm -f -- "$home/.local/share/fliperos/lists/$old.txt"
  [[ $(customgames_last_group_peek) == "$old" ]] && customgames_last_group_set "$new"
  log_info "grupo de jogos personalizados renomeado: $old -> $new (${#names[@]} jogos)"
  return 0
}

# customgames_last_group_peek: o ultimo grupo usado, mesmo se ja nao existe.
customgames_last_group_peek() {
  head -n 1 "$(customgames_last_group_file)" 2> /dev/null
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
  # E o submenu Games > Custom games do desktop.
  customgames_desktop
  return 0
}

# ── O painel web: fliperos-setup --customgames ───────────────────
# config/fliperos-web (Setup > Games > Custom games no painel): a lista, o
# cadastro de um jogo ou de muitos (a tabela), editar, apagar, os pacotes e
# as pastas em squashfs. Os jogos de uma pasta (Windows ou Linux) sao
# copiados para ~/games/GRUPO/NOME (fliperos-customgame add), como os de um
# pacote.
#
# As linhas da tabela (check e bulk) vem num arquivo, uma por jogo, com os
# campos separados pelo caractere 0x1f (o tab juntaria campos vazios no read):
#   grupo nome plataforma pasta exe comando modo categoria controles botoes
#   jogadores imagem video texto texto_digitado wine key ppdb runner logo ano
#   desenvolvedora joystick
# plataforma windows, native ou command; imagem/video/texto sao caminhos de
# arquivos (o painel os sobe antes, ou sao os que vieram com a pasta, na
# estrutura do pacote); wine e o PW_WINE_USE do PortProton; key e ppdb, o
# JOGO.key e o JOGO.ppdb que vieram com a pasta; joystick 1: o jogo ja aceita
# o joystick, o .key do jogo (ou do pacote) fica vazio e vale no lugar do key.

CUSTOM_GAMES_SEP=$'\x1f'

# customgames_out CAMPO...: uma linha do describe, os campos separados por tab
# (os tabs de dentro viram espaco).
customgames_out() {
  local out="" f tab=$'\t'
  for f in "$@"; do
    out+="${out:+$tab}${f//$tab/ }"
  done
  printf '%s\n' "$out"
}

# customgames_describe: tudo o que a pagina mostra e os dropdowns dela.
customgames_describe() {
  local group name cfg file platform mode cmd line value label
  local -a f
  # Os pacotes de antes da pasta deles vao para ela (uma vez).
  customgames_packages_migrate
  customgames_packages_dir
  while IFS= read -r group; do
    customgames_out group "$group" "$(customgames_count "$group")" "$(customgames_group_icon "$group")"       "$(customgames_group_logo "$group" && echo 1)"
  done < <(customgames_groups)
  while IFS='|' read -r group name _; do
    cfg=$(customgames_cfg "$group" "$name")
    file=$(customgames_file "$group" "$name")
    platform=$(customgames_platform "$group" "$name")
    mode=$(customgames_cfg_field "$cfg" mode)
    [[ -n $mode ]] || mode=$(customgames_field "$file" mode)
    cmd=$(customgames_cfg_field "$cfg" command)
    [[ -n $cmd ]] || cmd=$(customgames_field "$file" command)
    customgames_out game "$group" "$name" "$platform" "$mode" "$(customgames_cfg_field "$cfg" category)" \
      "$(customgames_cfg_field "$cfg" controls)" "$(customgames_cfg_field "$cfg" buttons)" \
      "$(customgames_cfg_field "$cfg" players)" "$cmd" "$(customgames_cfg_field "$cfg" exe)" \
      "$(customgames_cfg_field "$cfg" folder)" "$(customgames_cfg_field "$cfg" package)" \
      "$(customgames_cfg_field "$cfg" runner)" "$(customgames_cfg_field "$cfg" year)" \
      "$(customgames_cfg_field "$cfg" developer)"
  done < <(customgames_list)
  while IFS= read -r line; do
    IFS='|' read -ra f <<< "$line"
    customgames_out pending "${f[@]}"
  done < <(customgames_pending)
  customgames_out mode 240p "$(customgames_mode 240p)"
  customgames_out mode 240p-hack "$(customgames_mode 240p-hack)"
  customgames_out mode 480i "$(customgames_mode 480i)"
  IFS='|' read -ra f <<< "$CUSTOM_GAMES_GENRES"
  for value in "${f[@]}"; do
    customgames_out genre "$value"
    while IFS= read -r line; do
      customgames_out sub "$line"
    done < <(customgames_subgenres "$value")
  done
  while IFS='|' read -r value label; do
    customgames_out control "$value" "$label"
  done < <(romclean_options controls)
  for value in "${CUSTOM_GAMES_ICONS[@]}"; do
    customgames_out icon "${value%%|*}" "${value#*|}"
  done
  while IFS=$'	' read -r value label; do
    customgames_out logo "$value" "$label"
  done < <(customgames_logo_list)
  while IFS='|' read -r value line label; do
    customgames_out squash "$value" "$line" "$label"
  done < <(squashgames_list 2> /dev/null)
  if portproton_installed; then
    customgames_out portproton 1
    while IFS='|' read -r value label; do
      [[ -n $value ]] && customgames_out wine "$value" "$label"
    done < <("$CUSTOM_GAMES_PORTPROTON" versions 2>> "${FLIPEROS_LOG:-/dev/null}")
  else
    customgames_out portproton 0
  fi
  customgames_out games "$CUSTOM_GAMES_GAMES"
  customgames_out free "$(customgames_free "$CUSTOM_GAMES_GAMES")"
  customgames_out packages "$CUSTOM_GAMES_PACKAGES"
  customgames_out lastgroup "$(customgames_last_group)"
  return 0
}

# customgames_free PASTA: os bytes livres no disco dela (ou da que existe
# acima dela).
customgames_free() {
  local dir=$1
  while [[ -n $dir && $dir != / && ! -d $dir ]]; do dir=$(dirname "$dir"); done
  df -B1 --output=avail "${dir:-/}" 2> /dev/null | tail -n 1 | tr -d ' '
}

# customgames_row_fields LINHA: os campos de uma linha da tabela em R_*.
customgames_row_fields() {
  local -a f
  IFS=$CUSTOM_GAMES_SEP read -r -a f <<< "$1"
  R_GROUP=${f[0]:-} R_NAME=${f[1]:-} R_PLATFORM=${f[2]:-} R_FOLDER=${f[3]:-} R_EXE=${f[4]:-}
  R_COMMAND=${f[5]:-} R_MODE=${f[6]:-} R_CATEGORY=${f[7]:-} R_CONTROLS=${f[8]:-} R_BUTTONS=${f[9]:-}
  R_PLAYERS=${f[10]:-} R_SNAP=${f[11]:-} R_VIDEO=${f[12]:-} R_TEXT=${f[13]:-} R_TEXT_STRING=${f[14]:-}
  R_WINE=${f[15]:-} R_KEY=${f[16]:-} R_PPDB=${f[17]:-} R_RUNNER=${f[18]:-} R_LOGO=${f[19]:-}
  R_YEAR=${f[20]:-} R_DEVELOPER=${f[21]:-} R_JOYSTICK=${f[22]:-}
}

# customgames_row_errors [package]: o que esta errado na linha de R_* (uma
# linha "CAMPO|MOTIVO" por erro; nada se ela serve). Com package, a linha e
# a de um pacote a criar (Create package do painel): sem grupo, so Windows
# ou Linux. Nao grava nada.
customgames_row_errors() {
  local c exe real dest controls package=${1:-}
  controls=" $(romclean_options controls | cut -d'|' -f1 | tr '\n' ' ') "
  [[ -n $package ]] || customgames_valid_name "$R_GROUP" ||
    echo "group|The group cannot be empty, start with a dot or have / or |."
  if ! customgames_valid_name "$R_NAME"; then
    echo "name|The name cannot be empty, start with a dot or have / or |."
  elif [[ -z $package ]] && customgames_valid_name "$R_GROUP" &&
    [[ -e $(customgames_file "$R_GROUP" "$R_NAME") || -e $(customgames_cfg "$R_GROUP" "$R_NAME") ]]; then
    echo "name|$R_NAME is already in $R_GROUP."
  fi
  [[ -z $R_MODE ]] || customgames_mode "$R_MODE" > /dev/null ||
    echo "mode|Invalid video mode: use 240p, 240p-hack, 480i or WIDTHxHEIGHT@HZ (e.g. 320x240@60)."
  [[ -n $package && $R_PLATFORM == command ]] && echo "platform|A package is a Windows or a Linux game."
  case $R_PLATFORM in
    command)
      customgames_valid_command "$R_COMMAND" || echo "command|The command cannot be empty."
      ;;
    windows | native)
      if [[ -z $R_FOLDER || ! -d $R_FOLDER ]]; then
        echo "folder|Not a folder: ${R_FOLDER:-(empty)}"
      else
        real=$(realpath -- "$R_FOLDER")
        dest=$(realpath -m -- "$CUSTOM_GAMES_GAMES/$R_GROUP/$R_NAME")
        if [[ -z $package ]] && [[ $real == "$dest" || $real == "$dest"/* || $dest == "$real"/* ]]; then
          echo "folder|The game folder cannot be copied into itself: pick the folder of this game only."
        fi
        if [[ $R_PLATFORM == windows ]]; then
          exe=$(realpath -m -- "$real/$R_EXE")
          if [[ -z $R_EXE || $exe != "$real"/* || ! -f $exe ]]; then
            echo "exe|Pick the .exe that opens the game, inside its folder."
          fi
        else
          customgames_valid_command "$R_COMMAND" || echo "command|The command cannot be empty (e.g. ./game.x86_64)."
        fi
      fi
      ;;
    *) echo "platform|The type is Windows, Linux or Command." ;;
  esac
  # Uma linha colada de um .cfg ("command=groovymame ..."): o bash recusa (command=( e uma atribuicao).
  [[ $R_COMMAND != command=* ]] || echo "command|The command starts with \"command=\": type only what runs the game, without that."
  ((${#R_CATEGORY} <= 80)) || echo "category|The category is too long."
  for c in ${R_CONTROLS//,/ }; do
    [[ $controls == *" $c "* ]] || echo "controls|Unknown control: $c"
  done
  [[ -z $R_BUTTONS || $R_BUTTONS =~ ^[0-8]$ ]] || echo "buttons|Buttons: 0 to 8."
  [[ -z $R_PLAYERS || $R_PLAYERS =~ ^[1-8]$ ]] || echo "players|Players: 1 to 8."
  [[ -z ${R_YEAR:-} || $R_YEAR =~ ^(19|20)[0-9]{2}$ ]] || echo "year|Year: four digits (1900 to 2099)."
  ((${#R_DEVELOPER} <= 80)) || echo "developer|The developer is too long."
  [[ -z $R_SNAP || -f $R_SNAP ]] || echo "snap|The picture was not found: send it again."
  [[ -z $R_VIDEO || -f $R_VIDEO ]] || echo "video|The video was not found: send it again."
  [[ -z $R_TEXT || -f $R_TEXT ]] || echo "text|The text file was not found: send it again."
  [[ -z ${R_LOGO:-} || -f $R_LOGO ]] || echo "logo|The logo was not found: send it again."
  [[ -z ${R_KEY:-} || -f $R_KEY ]] || echo "key|The .key file was not found: pick the folder again."
  [[ -z ${R_PPDB:-} || -f $R_PPDB ]] || echo "ppdb|The .ppdb file was not found: pick the folder again."
  case ${R_RUNNER:-} in
    "" | portproton | wine | wine-staging) ;;
    *) echo "runner|The runner is PortProton, Wine or Wine Staging." ;;
  esac
  return 0
}

# customgames_check ARQUIVO: "error|LINHA|CAMPO|MOTIVO" de cada erro (as
# linhas contam de 1; dois jogos com o mesmo nome no mesmo grupo tambem),
# bytes= (o que sera copiado) e free= (o livre em ~/games). Nao grava nada.
customgames_check() {
  local file=$1 line n=0 bytes=0 err key size
  local -A seen=()
  [[ -f $file ]] || return 2
  while IFS= read -r line || [[ -n $line ]]; do
    ((n++))
    customgames_row_fields "$line"
    while IFS= read -r err; do
      [[ -n $err ]] && printf 'error|%d|%s\n' "$n" "$err"
    done < <(customgames_row_errors)
    key="$R_GROUP/$R_NAME"
    if [[ -n ${seen[$key]:-} ]]; then
      printf 'error|%d|name|%s is twice in the table (row %s).\n' "$n" "$R_NAME" "${seen[$key]}"
    else
      seen[$key]=$n
    fi
    if [[ $R_PLATFORM == windows || $R_PLATFORM == native ]] && [[ -d $R_FOLDER ]]; then
      size=$(du -sb -- "$R_FOLDER" 2> /dev/null | cut -f1)
      bytes=$((bytes + ${size:-0}))
    fi
  done < "$file"
  printf 'bytes=%s\nfree=%s\n' "$bytes" "$(customgames_free "$CUSTOM_GAMES_GAMES")"
}

# customgames_set_info GRUPO NOME: a categoria, os controles, os botoes e os
# jogadores de R_* no cfg (os vazios saem).
customgames_set_info() {
  local cfg
  cfg=$(customgames_cfg "$1" "$2")
  customgames_cfg_set "$cfg" category "$R_CATEGORY" &&
    customgames_cfg_set "$cfg" controls "$R_CONTROLS" &&
    customgames_cfg_set "$cfg" buttons "$R_BUTTONS" &&
    customgames_cfg_set "$cfg" players "$R_PLAYERS" &&
    customgames_cfg_set "$cfg" year "${R_YEAR:-}" &&
    customgames_cfg_set "$cfg" developer "${R_DEVELOPER:-}"
}

# customgames_media_set GRUPO NOME [--snap ARQ] [--video ARQ] [--text ARQ]
# [--logo ARQ] [--text-string TEXTO]: a arte de verdade do jogo (a de exemplo daquele tipo
# sai).
customgames_media_set() {
  local group=$1 name=$2
  shift 2
  (($#)) || return 0
  customgames_media_dirs "$group"
  customgames_tool media --group "$group" --name "$name" "$@" 2>> "${FLIPEROS_LOG:-/dev/null}"
}

# customgames_row_media: as opcoes da arte de R_* para o fliperos-customgame
# (em R_MEDIA).
customgames_row_media() {
  R_MEDIA=()
  [[ -n $R_SNAP ]] && R_MEDIA+=(--snap "$R_SNAP")
  [[ -n $R_VIDEO ]] && R_MEDIA+=(--video "$R_VIDEO")
  [[ -n $R_TEXT ]] && R_MEDIA+=(--text "$R_TEXT")
  [[ -n ${R_LOGO:-} ]] && R_MEDIA+=(--logo "$R_LOGO")
  [[ -n $R_TEXT_STRING ]] && R_MEDIA+=(--text-string "$R_TEXT_STRING")
  return 0
}

# customgames_add_row INICIO FIM: grava o jogo de R_* (as etapas de um jogo
# de uma pasta entre INICIO e FIM %, na saida). Na falha, status 1 e o
# motivo em R_WHY.
customgames_add_row() {
  local start=$1 end=$2 mode err folder rc copy_end
  local -a args
  R_WHY=""
  mode=$(customgames_mode "${R_MODE:-480i}") || { R_WHY="invalid video mode"; return 1; }
  customgames_row_media
  case $R_PLATFORM in
    command)
      customgames_save "$R_GROUP" "$R_NAME" "$mode" "$R_COMMAND" || { R_WHY="could not save $R_NAME"; return 1; }
      customgames_set_info "$R_GROUP" "$R_NAME"
      customgames_media_set "$R_GROUP" "$R_NAME" "${R_MEDIA[@]}"
      ;;
    windows | native)
      args=(--group "$R_GROUP" --name "$R_NAME" --platform "$R_PLATFORM" --folder "$R_FOLDER" --mode "$mode")
      if [[ $R_PLATFORM == windows ]]; then args+=(--exe "$R_EXE"); else args+=(--command "$R_COMMAND"); fi
      [[ $R_PLATFORM == windows && -n ${R_RUNNER:-} ]] && args+=(--runner "$R_RUNNER")
      # O JOGO.key e o JOGO.ppdb que vieram com a pasta (a estrutura do pacote);
      # com o joystick ja habilitado no jogo, o .key fica vazio.
      if [[ ${R_JOYSTICK:-} == 1 ]]; then args+=(--joystick); elif [[ -n ${R_KEY:-} ]]; then args+=(--key "$R_KEY"); fi
      [[ -n ${R_PPDB:-} && $R_PLATFORM == windows ]] && args+=(--ppdb "$R_PPDB")
      [[ -n $R_CATEGORY ]] && args+=(--category "$R_CATEGORY")
      [[ -n $R_CONTROLS ]] && args+=(--controls "$R_CONTROLS")
      [[ -n $R_BUTTONS ]] && args+=(--buttons "$R_BUTTONS")
      [[ -n $R_PLAYERS ]] && args+=(--players "$R_PLAYERS")
      [[ -n ${R_YEAR:-} ]] && args+=(--year "$R_YEAR")
      [[ -n ${R_DEVELOPER:-} ]] && args+=(--developer "$R_DEVELOPER")
      # A copia ate 85% da faixa; o squashfs no resto.
      copy_end=$((start + (end - start) * 85 / 100))
      customgames_media_dirs "$R_GROUP"
      err=$(mktemp)
      customgames_tool add "${args[@]}" "${R_MEDIA[@]}" --progress "$start" "$copy_end" 2> "$err" | grep -v '^@fail '
      rc=${PIPESTATUS[0]}
      if ((rc != 0)); then
        cat "$err" >> "${FLIPEROS_LOG:-/dev/null}"
        if ((rc == 3)); then R_WHY="$R_NAME is already in $R_GROUP"; else R_WHY=$(tail -n 1 "$err"); fi
        rm -f "$err"
        return 1
      fi
      rm -f "$err"
      customgames_entry "$R_GROUP" "$R_NAME" || { R_WHY="could not write $R_NAME.sh"; return 1; }
      folder=$(customgames_cfg_field "$(customgames_cfg "$R_GROUP" "$R_NAME")" folder)
      # O Wine que o PortProton usa neste jogo (o EXE.ppdb ao lado do .exe).
      if [[ $R_PLATFORM == windows && -n $R_WINE && ${R_RUNNER:-portproton} == portproton ]] && portproton_installed; then
        "$CUSTOM_GAMES_PORTPROTON" edit-db "$folder/$R_EXE" "PW_WINE_USE=$R_WINE" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1 ||
          log_warn "PortProton: PW_WINE_USE nao gravado em $folder/$R_EXE"
      fi
      customgames_squash "$folder" "$copy_end" "$end"
      ;;
    *)
      R_WHY="unknown type: $R_PLATFORM"
      return 1
      ;;
  esac
  customgames_media "$R_GROUP" "$R_NAME"
  log_info "jogo personalizado do painel: $R_GROUP / $R_NAME ($R_PLATFORM)"
  return 0
}

# customgames_refresh_frontends: os grupos nos frontends (como no Setup) e os
# jogos no menu do desktop.
customgames_refresh_frontends() {
  frontends_configure "$(launcher_current)" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1
  customgames_desktop
  return 0
}

# ── O menu do desktop (LXDE): Games > Custom games ──
# Uma entrada por jogo em ~/.local/share/applications (fliperos-APP.desktop,
# a categoria X-FliperOS-Custom) e o submenu Custom games dentro de Games
# (~/.config/menus/applications-merged). A entrada abre pelo fliperos-launch
# custom: o desktop fecha, o jogo abre no modo dele e o desktop volta.
CUSTOM_GAMES_APPS=${CUSTOM_GAMES_APPS:-$(dirname "$ROMS_DIR")/.local/share/applications}
CUSTOM_GAMES_MENUS=${CUSTOM_GAMES_MENUS:-$(dirname "$ROMS_DIR")/.config/menus/applications-merged}
CUSTOM_GAMES_DIRECTORIES=${CUSTOM_GAMES_DIRECTORIES:-$(dirname "$ROMS_DIR")/.local/share/desktop-directories}
CUSTOM_GAMES_LAUNCH=${CUSTOM_GAMES_LAUNCH:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-launch}

# customgames_home_dir PASTA: cria a pasta (dentro da home) e as que faltam
# acima dela, do jogador.
customgames_home_dir() {
  local dir=$1 home
  local -a made=()
  home=$(dirname "$ROMS_DIR")
  while [[ ! -d $dir && $dir == "$home"/* ]]; do
    made+=("$dir")
    dir=$(dirname "$dir")
  done
  mkdir -p "$1" 2> /dev/null || return 1
  ((${#made[@]})) && chown "$FLIPEROS_USER:" "${made[@]}" 2> /dev/null
  return 0
}

# customgames_desktop_arg TEXTO: um argumento do Exec= entre aspas (o
# padrao das entradas do desktop: \ " ` $ com barra, % dobrado).
customgames_desktop_arg() {
  local s=$1
  s=${s//\\/\\\\} s=${s//\"/\\\"} s=${s//\`/\\\`} s=${s//\$/\\\$} s=${s//%/%%}
  printf '"%s"' "$s"
}

# customgames_desktop: refaz as entradas do menu e o submenu (sem jogo
# nenhum, o submenu sai).
customgames_desktop() {
  local group name entry icon app n=0 menu=$CUSTOM_GAMES_MENUS/fliperos-custom-games.menu
  local directory=$CUSTOM_GAMES_DIRECTORIES/fliperos-custom-games.directory
  rm -f "$CUSTOM_GAMES_APPS"/fliperos-custom_*.desktop 2> /dev/null
  while IFS='|' read -r group name _; do
    [[ -n $name ]] || continue
    ((n++ == 0)) && { customgames_home_dir "$CUSTOM_GAMES_APPS" || return 0; }
    icon=$(customgames_snap "$group" "$name") || icon=applications-games
    app=$(customgames_app "$group" "$name")
    entry=$CUSTOM_GAMES_APPS/fliperos-$app.desktop
    {
      echo "[Desktop Entry]"
      echo "Type=Application"
      printf 'Name=%s\n' "$name"
      printf 'Comment=%s, a custom game. Opens on the CRT; the desktop comes back when it closes\n' "$group"
      printf 'Exec=%s custom %s\n' "$CUSTOM_GAMES_LAUNCH" "$(customgames_desktop_arg "$(customgames_file "$group" "$name")")"
      printf 'Icon=%s\n' "$icon"
      echo "Terminal=false"
      echo "Categories=Game;X-FliperOS-Custom;"
    } > "$entry"
    chown "$FLIPEROS_USER:" "$entry" 2> /dev/null
  done < <(customgames_list)
  if ((n == 0)); then
    rm -f "$menu" "$directory"
    return 0
  fi
  customgames_home_dir "$CUSTOM_GAMES_MENUS" && cat > "$menu" << 'EOF'
<!DOCTYPE Menu PUBLIC "-//freedesktop//DTD Menu 1.0//EN" "http://www.freedesktop.org/standards/menu-spec/menu-1.0.dtd">
<!-- FliperOS: Games > Custom games (Setup > Games > Custom games). -->
<Menu>
  <Name>Applications</Name>
  <Menu>
    <Name>Games</Name>
    <Menu>
      <Name>Custom games</Name>
      <Directory>fliperos-custom-games.directory</Directory>
      <Include><Category>X-FliperOS-Custom</Category></Include>
    </Menu>
    <Exclude><Category>X-FliperOS-Custom</Category></Exclude>
  </Menu>
</Menu>
EOF
  customgames_home_dir "$CUSTOM_GAMES_DIRECTORIES" && printf '%s\n' "[Desktop Entry]" "Type=Directory" "Name=Custom games" \
    "Icon=applications-games" > "$directory"
  chown "$FLIPEROS_USER:" "$menu" "$directory" 2> /dev/null
  return 0
}

# customgames_bulk ARQUIVO [--portproton]: grava cada linha da tabela, com
# os eventos da tela de progresso e "@row N ok" ou "@row N fail MOTIVO" por
# linha. Com --portproton e algum jogo do Windows, o PortProton antes. Os
# frontends sao refeitos uma vez, no fim. Status 1: alguma linha falhou.
customgames_bulk() {
  local file=$1 pp=${2:-} line n=0 total ok=0 start=2 a b why windows=0 games
  local -a rows
  [[ -f $file ]] || return 2
  mapfile -t rows < "$file"
  total=${#rows[@]}
  ((total)) || return 2
  games=games
  ((total == 1)) && games=game
  ev_step 0 "Checking $total $games"
  for line in "${rows[@]}"; do
    customgames_row_fields "$line"
    [[ $R_PLATFORM == windows ]] && windows=1
  done
  if [[ $pp == --portproton ]] && ((windows)) && ! portproton_installed; then
    portproton_ensure 2 30 ||
      ev_msg "PortProton was not installed: the Windows games open with the system's Wine, if there is one."
    start=30
  fi
  for line in "${rows[@]}"; do
    ((n++))
    customgames_row_fields "$line"
    a=$((start + (95 - start) * (n - 1) / total))
    b=$((start + (95 - start) * n / total))
    ev_step "$a" "Adding ${R_NAME:-row $n} ($n of $total)"
    why=$(customgames_row_errors | head -n 1)
    if [[ -n $why ]]; then
      echo "@row $n fail ${why#*|}"
      continue
    fi
    if customgames_add_row "$a" "$b"; then
      echo "@row $n ok"
      ((ok++))
    else
      echo "@row $n fail ${R_WHY:-could not add $R_NAME}"
    fi
  done
  if ((ok)); then
    ev_step 96 "Putting the games in the frontend"
    customgames_refresh_frontends
  fi
  if ((ok < total)); then
    ev_step 100 "$ok of $total $games added"
    ev_fail "$((total - ok)) of $total $games $( ((total - ok == 1)) && echo was || echo were) not added"
    return 1
  fi
  ev_step 100 "$total $games added"
  return 0
}

# customgames_edit CHAVE=VALOR...: um jogo mudado pelo painel (group e name
# dizem qual). O de um comando muda de nome, grupo, comando e modo (como o
# Edit do Setup); os outros so o modo e as informacoes (category, controls,
# buttons, players), como o Information and video mode. Status 2: jogo ou
# valor que nao serve.
customgames_edit() {
  local pair key value group="" name="" new_group="" new_name="" cmd="" mode="" platform cfg file
  local have_cmd=0 have_mode=0
  local -A info=()
  for pair in "$@"; do
    key=${pair%%=*} value=${pair#*=}
    case $key in
      group) group=$value ;;
      name) name=$value ;;
      new_group) new_group=$value ;;
      new_name) new_name=$value ;;
      command) cmd=$value have_cmd=1 ;;
      mode) mode=$value have_mode=1 ;;
      category | controls | buttons | players | year | developer) info[$key]=$value ;;
      *) return 2 ;;
    esac
  done
  customgames_valid_name "$group" && customgames_valid_name "$name" || return 2
  file=$(customgames_file "$group" "$name")
  [[ -f $file ]] || return 2
  platform=$(customgames_platform "$group" "$name")
  [[ $platform == script ]] && return 2
  new_group=${new_group:-$group} new_name=${new_name:-$name}
  if ((have_mode)); then
    mode=$(customgames_mode "$mode") || return 2
  fi
  R_CATEGORY=${info[category]-} R_CONTROLS=${info[controls]-} R_BUTTONS=${info[buttons]-} R_PLAYERS=${info[players]-}
  R_YEAR=${info[year]-} R_DEVELOPER=${info[developer]-}
  R_GROUP=$new_group R_NAME=$new_name R_PLATFORM=command R_COMMAND=x R_MODE="" R_FOLDER="" R_EXE=""
  R_SNAP="" R_VIDEO="" R_TEXT="" R_LOGO="" R_KEY="" R_PPDB=""
  # As informacoes conferidas como as da tabela (o nome novo, se mudou).
  if [[ $new_group/$new_name != "$group/$name" ]]; then
    [[ $platform == command ]] || return 2
    customgames_row_errors | grep -q '^\(group\|name\)|' && return 2
  fi
  customgames_row_errors | grep -q '^\(category\|controls\|buttons\|players\|year\|developer\)|' && return 2
  cfg=$(customgames_cfg "$group" "$name")
  if [[ $platform == command ]]; then
    ((have_cmd)) || cmd=$(customgames_cfg_field "$cfg" command)
    [[ -n $cmd ]] || cmd=$(customgames_field "$file" command)
    ((have_mode)) || mode=$(customgames_cfg_field "$cfg" mode)
    [[ -n $mode ]] || mode=$(customgames_field "$file" mode)
    customgames_valid_command "$cmd" || return 2
    customgames_save "$new_group" "$new_name" "$mode" "$cmd" "$group" "$name" || return 1
    group=$new_group name=$new_name
    cfg=$(customgames_cfg "$group" "$name")
  elif ((have_mode)); then
    customgames_cfg_set "$cfg" mode "$mode" && customgames_entry "$group" "$name" || return 1
  fi
  for key in category controls buttons players year developer; do
    [[ -n ${info[$key]+set} ]] && { customgames_cfg_set "$cfg" "$key" "${info[$key]}" || return 1; }
  done
  customgames_media "$group" "$name"
  customgames_refresh_frontends
  return 0
}

# customgames_pack_game GRUPO NOME: o pacote de um jogo instalado (o Make a
# package of it do Setup), com a arte de verdade dele, em
# ~/roms/custom/GRUPO/NOME.fliperos-customgame.zip; com os eventos de
# progresso.
customgames_pack_game() {
  local group=$1 name=$2 cfg platform folder exe base out value ext
  local -a args
  cfg=$(customgames_cfg "$group" "$name")
  platform=$(customgames_cfg_field "$cfg" platform)
  [[ $platform == windows || $platform == native ]] || { ev_fail "only Windows and Linux games are packed"; return 2; }
  folder=$(customgames_cfg_field "$cfg" folder)
  exe=$(customgames_cfg_field "$cfg" exe)
  out=$(customgames_package_out "$name")
  args=(--out "$out" --name "$name" --platform "$platform" --folder "$folder"
    --mode "$(customgames_cfg_field "$cfg" mode)")
  if [[ $platform == windows ]]; then args+=(--exe "$exe"); else args+=(--command "$(customgames_cfg_field "$cfg" command)"); fi
  [[ $platform == windows && -n $(customgames_cfg_field "$cfg" runner) ]] && args+=(--runner "$(customgames_cfg_field "$cfg" runner)")
  for value in category controls buttons players year developer; do
    [[ -n $(customgames_cfg_field "$cfg" "$value") ]] && args+=("--$value" "$(customgames_cfg_field "$cfg" "$value")")
  done
  [[ -f ${cfg%.cfg}.key ]] && args+=(--key "${cfg%.cfg}.key")
  [[ -n $exe && -f $folder/$exe.ppdb ]] && args+=(--ppdb "$folder/$exe.ppdb")
  # A arte de verdade (as de exemplo nao vao: quem instala ganha as suas).
  for value in snap preview texto logo; do
    for ext in $(customgames_media_exts "$value"); do
      [[ -f $CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext ]] || continue
      customgames_media_sample "$CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext" && continue
      case $value in snap) args+=(--snap) ;; preview) args+=(--video) ;; texto) args+=(--text) ;; logo) args+=(--logo) ;; esac
      args+=("$CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext")
      break
    done
  done
  customgames_pack_run "${args[@]}"
}

# ── Criar um pacote pelo painel (a area Criar pacote) ──
# Uma linha como as da tabela (customgames_row_fields), sem grupo: o pacote
# vai para a pasta dos pacotes e aparece no Install games.

# customgames_create_check ARQUIVO: "error|1|CAMPO|MOTIVO" de cada erro,
# out= (o zip que sera feito), exists= (1: ja ha um com esse nome), bytes=
# (a pasta do jogo) e free= (o livre na pasta dos pacotes). Nao grava nada.
customgames_create_check() {
  local file=$1 line err out size
  [[ -f $file ]] || return 2
  IFS= read -r line < "$file" || [[ -n $line ]] || return 2
  customgames_row_fields "$line"
  while IFS= read -r err; do
    [[ -n $err ]] && printf 'error|1|%s\n' "$err"
  done < <(customgames_row_errors package)
  out=""
  customgames_valid_name "$R_NAME" && out=$(customgames_package_out "$R_NAME")
  size=0
  [[ -d $R_FOLDER ]] && size=$(du -sb -- "$R_FOLDER" 2> /dev/null | cut -f1)
  printf 'out=%s\nexists=%d\nbytes=%s\nfree=%s\n' "$out" "$([[ -n $out && -e $out ]] && echo 1 || echo 0)" \
    "${size:-0}" "$(customgames_free "$CUSTOM_GAMES_PACKAGES")"
}

# customgames_test ARQUIVO: o jogo da linha (o Testar do Criar pacote)
# aberto sem instalar, da pasta dele: o cfg em ~/roms/custom/.test/NOME.cfg
# (uma pasta escondida: nao e grupo nem sistema) e, na saida, app= (o nome
# para o filtro, a OSD e o log) e o comando do fliperos-x11-run, uma palavra
# por linha (o painel o manda ao tty1). O NOME.key de la, que o menu na tela
# faz durante o teste, vai no pacote. Status 1, com o motivo: a linha nao
# serve.
customgames_test() {
  local file=$1 line why dir cfg mode app real
  local -a pairs argv
  [[ -f $file ]] || return 2
  IFS= read -r line < "$file" || [[ -n $line ]] || return 2
  customgames_row_fields "$line"
  why=$(customgames_row_errors package | head -n 1)
  [[ -z $why ]] || { printf '%s\n' "${why#*|}"; return 1; }
  dir=$CUSTOM_GAMES_DIR/.test
  mkdir -p "$dir" && chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$dir" 2> /dev/null
  cfg=$dir/$R_NAME.cfg
  mode=$(customgames_mode "${R_MODE:-480i}")
  real=$(realpath -- "$R_FOLDER")
  pairs=("format=1" "name=$R_NAME" "platform=$R_PLATFORM" "mode=$mode" "folder=$real")
  if [[ $R_PLATFORM == windows ]]; then pairs+=("exe=$R_EXE" "runner=${R_RUNNER:-}"); else pairs+=("command=$R_COMMAND"); fi
  customgames_cfg_write "$cfg" "${pairs[@]}" || { echo "could not write $cfg"; return 1; }
  # O .key que veio com a pasta comeca o teste (o menu na tela o mostra). Com o
  # joystick ja habilitado no jogo, o .key do teste e vazio: o menu na tela nao
  # abre sozinho pedindo o mapa do controle, como no jogo do pacote.
  if [[ ${R_JOYSTICK:-} == 1 ]]; then
    : > "$dir/$R_NAME.key" && chown "$FLIPEROS_USER:" "$dir/$R_NAME.key" 2> /dev/null
  else
    [[ -n ${R_KEY:-} && -f $R_KEY && ! -f $dir/$R_NAME.key ]] && cp -- "$R_KEY" "$dir/$R_NAME.key" &&
      chown "$FLIPEROS_USER:" "$dir/$R_NAME.key" 2> /dev/null
  fi
  app=$(customgames_app .test "$R_NAME")
  argv=("$CUSTOM_GAMES_RUN" --mode "$mode" --app "$app")
  [[ $R_PLATFORM == windows ]] && argv+=(--wine)
  argv+=("$CUSTOM_GAMES_TOOL" run "$cfg")
  log_info "jogo custom testado pelo painel: $R_NAME ($real)"
  printf 'app=%s\n' "$app"
  printf '%s\n' "${argv[@]}"
}

# customgames_test_key NOME: o .key que o teste do NOME fez (ou nada).
customgames_test_key() {
  [[ -f $CUSTOM_GAMES_DIR/.test/$1.key ]] && printf '%s\n' "$CUSTOM_GAMES_DIR/.test/$1.key"
  return 0
}

# customgames_create ARQUIVO [replace]: o pacote da linha, com os eventos da
# tela de progresso (o .key do teste, se a pasta nao trouxe um, vai junto;
# o teste sai depois). Status 3: ja ha um pacote com esse nome (sem replace).
customgames_create() {
  local file=$1 replace=${2:-} line out why mode key var
  local -a args
  [[ -f $file ]] || return 2
  IFS= read -r line < "$file" || [[ -n $line ]] || return 2
  customgames_row_fields "$line"
  ev_step 0 "Checking ${R_NAME:-the game}"
  why=$(customgames_row_errors package | head -n 1)
  [[ -z $why ]] || { ev_fail "${why#*|}"; return 1; }
  out=$(customgames_package_out "$R_NAME")
  if [[ -e $out && $replace != replace ]]; then
    ev_fail "$(basename "$out") already exists in ~/roms/custom-packages"
    return 3
  fi
  mode=$(customgames_mode "${R_MODE:-480i}")
  # O joystick ja habilitado no jogo: o .key do pacote e vazio (o da pasta e o do teste ficam de fora).
  if [[ ${R_JOYSTICK:-} == 1 ]]; then
    R_KEY=""
  else
    [[ -n ${R_KEY:-} ]] || R_KEY=$(customgames_test_key "$R_NAME")
  fi
  args=(--out "$out" --name "$R_NAME" --platform "$R_PLATFORM" --folder "$R_FOLDER" --mode "$mode")
  [[ ${R_JOYSTICK:-} == 1 ]] && args+=(--joystick)
  if [[ $R_PLATFORM == windows ]]; then args+=(--exe "$R_EXE"); else args+=(--command "$R_COMMAND"); fi
  [[ $R_PLATFORM == windows && -n ${R_RUNNER:-} ]] && args+=(--runner "$R_RUNNER")
  for key in CATEGORY:category CONTROLS:controls BUTTONS:buttons PLAYERS:players YEAR:year DEVELOPER:developer SNAP:snap VIDEO:video TEXT:text LOGO:logo \
    KEY:key PPDB:ppdb TEXT_STRING:text-string; do
    var=R_${key%%:*}
    [[ -n ${!var:-} ]] || continue
    [[ $key == PPDB:ppdb && ($R_PLATFORM != windows || ${R_RUNNER:-portproton} != portproton) ]] && continue
    args+=("--${key#*:}" "${!var}")
  done
  customgames_tool pack "${args[@]}" --progress 0 100 2>> "${FLIPEROS_LOG:-/dev/null}"
  [[ -f $out ]] || return 1
  rm -f -- "$CUSTOM_GAMES_DIR/.test/$R_NAME.cfg" "$CUSTOM_GAMES_DIR/.test/$R_NAME.key"
  rmdir -- "$CUSTOM_GAMES_DIR/.test" 2> /dev/null
  log_info "pacote criado pelo painel: $out"
  return 0
}

# customgames_package_out NOME: o zip do pacote de NOME, na pasta dos
# pacotes (o nome do arquivo sem os caracteres que um disco do Windows
# recusa); a pasta e criada.
customgames_package_out() {
  local base
  base=$(printf '%s' "$1" | sed 's/[^A-Za-z0-9 ._()&+,-]\{1,\}/_/g')
  customgames_packages_dir
  printf '%s/%s.fliperos-customgame.zip\n' "$CUSTOM_GAMES_PACKAGES" "$base"
}

# customgames_install_all GRUPO: os pacotes novos da pasta dos pacotes no
# GRUPO, um depois do outro; os que mudaram desde a instalacao (update)
# trocam o jogo no grupo onde ele esta.
customgames_install_all() {
  local group=$1 row zip g state n=0 ok=0 total
  local -a rows
  mapfile -t rows < <(customgames_pending_ok)
  total=${#rows[@]}
  ((total)) || { ev_step 100 "Nothing to install"; return 0; }
  for row in "${rows[@]}"; do
    IFS='|' read -r zip g _ _ state _ <<< "$row"
    ((n++))
    ev_msg "Package $n of $total: $(basename "$zip")"
    if customgames_install "$zip" "${g:-$group}" "$([[ $state == update ]] && echo replace)"; then
      ((ok++))
    fi
  done
  customgames_refresh_frontends
  ((ok == total)) || { ev_fail "$((total - ok)) of $total packages were not installed"; return 1; }
  return 0
}

# customgames_cli SUBCOMANDO...: o fliperos-setup --customgames.
#   describe | check ARQ | bulk ARQ [--portproton] | edit CHAVE=VALOR... |
#   delete GRUPO NOME [folder] | group NOME | group-info NOME |
#   group-icon GRUPO [ICONE] | group-logo GRUPO [IMAGEM | system:NOME] | group-rename GRUPO NOVO |
#   group-delete NOME [all] | media GRUPO NOME --snap ARQ... |
#   install ZIP GRUPO [replace] [--portproton] | install-all GRUPO |
#   package-delete ZIP | check-create ARQ | create ARQ [replace] | test ARQ |
#   pack GRUPO NOME | squash pack|unpack PASTA | portproton
# Status 2: subcomando ou argumento que nao serve.
customgames_cli() {
  local sub=${1:-} rc zip group replace pp
  shift
  case $sub in
    describe) customgames_describe ;;
    check) customgames_check "${1:-}" ;;
    bulk) customgames_bulk "${1:-}" "${2:-}" ;;
    edit) customgames_edit "$@" ;;
    delete)
      customgames_valid_name "${1:-}" && customgames_valid_name "${2:-}" || return 2
      [[ -e $(customgames_file "$1" "$2") || -e $(customgames_cfg "$1" "$2") ]] || return 2
      customgames_delete "$1" "$2" "$([[ ${3:-} == folder ]] && echo folder)" || return 1
      customgames_refresh_frontends
      ;;
    group)
      customgames_valid_name "${1:-}" || return 2
      mkdir -p "$CUSTOM_GAMES_DIR/$1" && chown "$FLIPEROS_USER:" "$CUSTOM_GAMES_DIR" "$CUSTOM_GAMES_DIR/$1" 2> /dev/null
      customgames_media_dirs "$1"
      ;;
    group-info)
      customgames_valid_name "${1:-}" && [[ -d $CUSTOM_GAMES_DIR/$1 ]] || return 2
      customgames_group_info "$1"
      ;;
    group-icon) customgames_group_icon_set "${1:-}" "${2:-}" ;;
    group-logo) customgames_group_logo_set "${1:-}" "${2:-}" ;;
    group-rename)
      customgames_group_rename "${1:-}" "${2:-}"
      rc=$?
      ((rc == 0)) && customgames_refresh_frontends
      return $rc
      ;;
    package-delete) customgames_package_delete "${1:-}" ;;
    check-create) customgames_create_check "${1:-}" ;;
    test) customgames_test "${1:-}" ;;
    create)
      [[ -z ${2:-} || $2 == replace ]] || return 2
      customgames_create "${1:-}" "${2:-}"
      ;;
    group-delete)
      customgames_valid_name "${1:-}" && [[ -d $CUSTOM_GAMES_DIR/$1 ]] || return 2
      [[ -z ${2:-} || $2 == all ]] || return 2
      customgames_group_delete "$1" "${2:-}"
      rc=$?
      customgames_refresh_frontends
      return $rc
      ;;
    media)
      customgames_valid_name "${1:-}" && customgames_valid_name "${2:-}" && [[ -e $(customgames_file "$1" "$2") ]] || return 2
      customgames_media_set "$@" || return 1
      customgames_media "$1" "$2"
      ;;
    install)
      zip=${1:-} group=${2:-} replace="" pp=""
      shift 2 2> /dev/null
      for rc in "$@"; do
        case $rc in replace) replace=replace ;; --portproton) pp=1 ;; esac
      done
      [[ -f $zip ]] && customgames_valid_name "$group" || return 2
      if ((pp)) && customgames_tool inspect "$zip" 2> /dev/null | grep -qx 'platform=windows' && ! portproton_installed; then
        portproton_ensure 0 100 || ev_msg "PortProton was not installed: the game opens with the system's Wine, if there is one."
      fi
      customgames_install "$zip" "$group" $replace
      rc=$?
      ((rc == 0)) && customgames_refresh_frontends
      return $rc
      ;;
    install-all)
      customgames_valid_name "${1:-}" || return 2
      customgames_install_all "$1"
      ;;
    pack)
      customgames_valid_name "${1:-}" && customgames_valid_name "${2:-}" && [[ -f $(customgames_cfg "$1" "$2") ]] || return 2
      customgames_pack_game "$1" "$2"
      ;;
    squash)
      [[ ${1:-} == pack || ${1:-} == unpack ]] && [[ -d ${2:-} ]] || return 2
      squashgames_run "$1" "$2"
      ;;
    portproton) portproton_run_install ;;
    *) return 2 ;;
  esac
}
