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
#   jogadores imagem video texto texto_digitado wine
# plataforma windows, native ou command; imagem/video/texto sao caminhos de
# arquivos (o painel os sobe antes); wine e o PW_WINE_USE do PortProton.

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
  while IFS= read -r group; do
    customgames_out group "$group" "$(customgames_count "$group")"
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
      "$(customgames_cfg_field "$cfg" folder)" "$(customgames_cfg_field "$cfg" package)"
  done < <(customgames_list)
  while IFS= read -r line; do
    IFS='|' read -ra f <<< "$line"
    customgames_out pending "${f[@]}"
  done < <(customgames_pending)
  customgames_out mode 240p "$(customgames_mode 240p)"
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
  R_WINE=${f[15]:-}
}

# customgames_row_errors: o que esta errado na linha de R_* (uma linha
# "CAMPO|MOTIVO" por erro; nada se ela serve). Nao grava nada.
customgames_row_errors() {
  local c exe real dest controls
  controls=" $(romclean_options controls | cut -d'|' -f1 | tr '\n' ' ') "
  customgames_valid_name "$R_GROUP" || echo "group|The group cannot be empty, start with a dot or have / or |."
  if ! customgames_valid_name "$R_NAME"; then
    echo "name|The name cannot be empty, start with a dot or have / or |."
  elif customgames_valid_name "$R_GROUP" &&
    [[ -e $(customgames_file "$R_GROUP" "$R_NAME") || -e $(customgames_cfg "$R_GROUP" "$R_NAME") ]]; then
    echo "name|$R_NAME is already in $R_GROUP."
  fi
  [[ -z $R_MODE ]] || customgames_mode "$R_MODE" > /dev/null ||
    echo "mode|Invalid video mode: use 240p, 480i or WIDTHxHEIGHT@HZ (e.g. 320x240@60)."
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
        if [[ $real == "$dest" || $real == "$dest"/* || $dest == "$real"/* ]]; then
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
  ((${#R_CATEGORY} <= 80)) || echo "category|The category is too long."
  for c in ${R_CONTROLS//,/ }; do
    [[ $controls == *" $c "* ]] || echo "controls|Unknown control: $c"
  done
  [[ -z $R_BUTTONS || $R_BUTTONS =~ ^[0-8]$ ]] || echo "buttons|Buttons: 0 to 8."
  [[ -z $R_PLAYERS || $R_PLAYERS =~ ^[1-8]$ ]] || echo "players|Players: 1 to 8."
  [[ -z $R_SNAP || -f $R_SNAP ]] || echo "snap|The picture was not found: send it again."
  [[ -z $R_VIDEO || -f $R_VIDEO ]] || echo "video|The video was not found: send it again."
  [[ -z $R_TEXT || -f $R_TEXT ]] || echo "text|The text file was not found: send it again."
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
    customgames_cfg_set "$cfg" players "$R_PLAYERS"
}

# customgames_media_set GRUPO NOME [--snap ARQ] [--video ARQ] [--text ARQ]
# [--text-string TEXTO]: a arte de verdade do jogo (a de exemplo daquele tipo
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
  mode=$(customgames_mode "${R_MODE:-240p}") || { R_WHY="invalid video mode"; return 1; }
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
      [[ -n $R_CATEGORY ]] && args+=(--category "$R_CATEGORY")
      [[ -n $R_CONTROLS ]] && args+=(--controls "$R_CONTROLS")
      [[ -n $R_BUTTONS ]] && args+=(--buttons "$R_BUTTONS")
      [[ -n $R_PLAYERS ]] && args+=(--players "$R_PLAYERS")
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
      if [[ $R_PLATFORM == windows && -n $R_WINE ]] && portproton_installed; then
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

# customgames_refresh_frontends: os grupos nos frontends (como no Setup).
customgames_refresh_frontends() {
  frontends_configure "$(launcher_current)" >> "${FLIPEROS_LOG:-/dev/null}" 2>&1
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
      category | controls | buttons | players) info[$key]=$value ;;
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
  R_GROUP=$new_group R_NAME=$new_name R_PLATFORM=command R_COMMAND=x R_MODE="" R_FOLDER="" R_EXE=""
  R_SNAP="" R_VIDEO="" R_TEXT=""
  # As informacoes conferidas como as da tabela (o nome novo, se mudou).
  if [[ $new_group/$new_name != "$group/$name" ]]; then
    [[ $platform == command ]] || return 2
    customgames_row_errors | grep -q '^\(group\|name\)|' && return 2
  fi
  customgames_row_errors | grep -q '^\(category\|controls\|buttons\|players\)|' && return 2
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
  for key in category controls buttons players; do
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
  base=$(printf '%s' "$name" | sed 's/[^A-Za-z0-9 ._()&+,-]\{1,\}/_/g')
  out=$CUSTOM_GAMES_DIR/$group/$base.fliperos-customgame.zip
  args=(--out "$out" --name "$name" --platform "$platform" --folder "$folder"
    --mode "$(customgames_cfg_field "$cfg" mode)")
  if [[ $platform == windows ]]; then args+=(--exe "$exe"); else args+=(--command "$(customgames_cfg_field "$cfg" command)"); fi
  for value in category controls buttons players; do
    [[ -n $(customgames_cfg_field "$cfg" "$value") ]] && args+=("--$value" "$(customgames_cfg_field "$cfg" "$value")")
  done
  [[ -f ${cfg%.cfg}.key ]] && args+=(--key "${cfg%.cfg}.key")
  [[ -n $exe && -f $folder/$exe.ppdb ]] && args+=(--ppdb "$folder/$exe.ppdb")
  # A arte de verdade (as de exemplo nao vao: quem instala ganha as suas).
  for value in snap preview texto; do
    for ext in $(customgames_media_exts "$value"); do
      [[ -f $CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext ]] || continue
      customgames_media_sample "$CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext" && continue
      case $value in snap) args+=(--snap) ;; preview) args+=(--video) ;; texto) args+=(--text) ;; esac
      args+=("$CUSTOM_GAMES_MEDIA/$value/custom/$group/$name.$ext")
      break
    done
  done
  customgames_pack_run "${args[@]}"
}

# customgames_install_all GRUPO: os pacotes da pasta do grupo e os de
# ~/roms/custom sem grupo (entram nele), um depois do outro; o que ja existe
# e trocado (o painel ja mostrou "update").
customgames_install_all() {
  local group=$1 row zip g state n=0 ok=0 total
  local -a rows
  mapfile -t rows < <(customgames_pending_ok "$group")
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
#   delete GRUPO NOME [folder] | group NOME | media GRUPO NOME --snap ARQ... |
#   install ZIP GRUPO [replace] [--portproton] | install-all GRUPO |
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
