# shellcheck shell=bash
# Setup > Games > Folders: as pastas da pessoa em ~ (config/fliperos-roms) e a
# "custom folder" de cada uma, da raiz (~/roms) a de um emulador, de um core
# ou de um tipo de arte (~/roms/retroarch/mame2010, ~/media/snap). Com uma, a
# pasta vira um link para outra (um disco externo que ja tem as ROMs) e a de
# antes fica ao lado, com "old-" no nome (~/roms/old-mame); sem ela, a de
# antes volta.
#
# Uma pasta e dita pelo caminho dela a partir de ~ ("roms/retroarch/fbneo").
#
# Nada disso fica anotado: o estado e sempre o que esta no disco. Um link
# feito ou apagado a mao (SSH, a pasta da rede, o desktop) vale igual ao do
# Setup.

FOLDERS_HOME=${FOLDERS_HOME:-/home/$FLIPEROS_USER}
# As raizes. A ~/config fica de fora: so tem links para as configuracoes,
# que o fliperos-roms refaz.
FOLDERS_NAMES="roms bios media nvram save splashscreen"
# Onde o fliperos-automount monta os discos: o navegador de pastas abre ali.
FOLDERS_MOUNTS=${FOLDERS_MOUNTS:-/media/$FLIPEROS_USER}
FOLDERS_SCRIPT=${FOLDERS_SCRIPT:-/opt/fliperos/bin/fliperos-roms}
# Por que a ultima troca foi recusada, em palavras para a tela.
FOLDERS_ERROR=""
# Onde ficou a pasta de antes na ultima troca (vazio: nenhuma foi guardada).
FOLDERS_KEPT=""

folders_list() {
  # shellcheck disable=SC2086 # um nome por palavra
  printf '%s\n' $FOLDERS_NAMES
}

# folders_kept_name NOME: e o nome de uma pasta guardada (old-mame, e
# old2-mame quando ja havia uma old-mame)?
folders_kept_name() {
  [[ $1 == old-* || $1 == old+([0-9])-* ]]
}

# folders_known PASTA: uma raiz ou uma pasta ate dois niveis abaixo dela
# (tres na arte dos cores do RetroArch: media/snap/retroarch/mame2010), sem
# pastas ocultas nem as guardadas.
folders_known() {
  local rel=$1 part
  local -a parts
  [[ -n $rel && $rel != /* && $rel != */ && $rel != *//* ]] || return 1
  IFS=/ read -r -a parts <<< "$rel"
  ((${#parts[@]} <= 3)) || [[ ${#parts[@]} -eq 4 && $rel == media/*/retroarch/* ]] || return 1
  [[ " $FOLDERS_NAMES " == *" ${parts[0]} "* ]] || return 1
  for part in "${parts[@]}"; do
    [[ -n $part && $part != .* ]] || return 1
    folders_kept_name "$part" && return 1
  done
  return 0
}

folders_path() {
  printf '%s\n' "$FOLDERS_HOME/$1"
}

# folders_old PASTA: onde fica a pasta de antes (ao lado, com "old-").
folders_old() {
  local dir=$FOLDERS_HOME/$1
  printf '%s/old-%s\n' "${dir%/*}" "${dir##*/}"
}

# folders_description PASTA: o que vai na pasta. O texto das pastas de
# dentro e o _info.txt que o fliperos-roms deixa em cada uma.
folders_description() {
  local info
  case $1 in
    roms) echo "The games: one folder per emulator and one per RetroArch core." ;;
    bios) echo "The BIOS files of RetroArch and of the other emulators." ;;
    media) echo "The art and texts the frontends show, one folder per type." ;;
    nvram) echo "The arcade memory the MAME games keep without power: dip settings, credits, scores." ;;
    save) echo "The saves and states, one folder per emulator." ;;
    splashscreen) echo "The boot splash themes." ;;
    roms/retroarch) echo "The games of RetroArch: one folder per core." ;;
    media/*/retroarch) echo "The art of the RetroArch games: one folder per core, as in ~/roms/retroarch." ;;
    *)
      info=$FOLDERS_HOME/$1/_info.txt
      [[ -f $info ]] && head -n 1 "$info" | cut -c1-300
      ;;
  esac
  return 0
}

# folders_state PASTA imprime como a pasta esta agora:
#   default  a do FliperOS (uma pasta comum)
#   custom   um link para uma pasta que existe
#   offline  um link para uma pasta que nao esta la (o disco desligado)
#   missing  nao ha nada
folders_state() {
  local path
  path=$(folders_path "$1")
  if [[ -L $path ]]; then
    if [[ -d $path ]]; then
      echo custom
    else
      echo offline
    fi
  elif [[ -d $path ]]; then
    echo default
  else
    echo missing
  fi
}

# folders_target PASTA imprime para onde o link aponta.
folders_target() {
  local path target
  path=$(folders_path "$1")
  [[ -L $path ]] || return 1
  target=$(readlink -- "$path") || return 1
  [[ $target == /* ]] || target=${path%/*}/$target
  printf '%s\n' "$target"
}

# folders_container PASTA: tem pastas dentro que tambem aceitam uma custom
# folder? As raizes (menos a dos temas do splash), as dos cores do RetroArch
# e dos emuladores do Fightcade, e cada tipo de arte (as mesmas pastas de
# ~/roms, com a dos cores do RetroArch).
folders_container() {
  case $1 in
    roms | bios | media | roms/retroarch | roms/fightcade) return 0 ;;
    media/*/retroarch) return 0 ;;
    media/*/*) return 1 ;;
    media/*) return 0 ;;
  esac
  return 1
}

# folders_children PASTA imprime as pastas de dentro, uma por linha (o
# caminho a partir de ~). Um link sem a pasta (disco desligado) tambem.
folders_children() {
  local rel=$1 path name
  folders_container "$rel" || return 0
  for path in "$FOLDERS_HOME/$rel"/*; do
    [[ -d $path || -L $path ]] || continue
    name=${path##*/}
    folders_kept_name "$name" && continue
    printf '%s/%s\n' "$rel" "$name"
  done
  return 0
}

# folders_customs [PASTA] imprime as pastas com custom folder, da PASTA para
# dentro (sem ela: todas).
folders_customs() {
  local rel child
  local -a todo=("$@")
  # shellcheck disable=SC2206 # um nome por palavra
  (($#)) || todo=($FOLDERS_NAMES)
  for rel in "${todo[@]}"; do
    if [[ -L $FOLDERS_HOME/$rel ]]; then
      [[ $(folders_state "$rel") == default ]] || printf '%s\n' "$rel"
    fi
    while IFS= read -r child; do
      [[ -n $child ]] && folders_customs "$child"
    done < <(folders_children "$rel")
  done
  return 0
}

# folders_browse_start imprime onde o navegador de pastas abre ao escolher
# uma custom folder: sempre a pasta dos discos montados (HD, SSD, pendrive),
# tambem quando a pasta ja tem uma custom folder. Sem nenhum disco montado
# ainda, a pasta acima dela.
folders_browse_start() {
  local dir=$FOLDERS_MOUNTS
  while [[ ! -d $dir && -n ${dir%/*} ]]; do dir=${dir%/*}; done
  [[ -d $dir ]] || dir=/
  printf '%s\n' "$dir"
}

# folders_skeleton PASTA: so tem o que o fliperos-roms cria sozinho (pastas,
# os _info.txt e os temas do splash copiados da imagem)? Uma assim pode sair
# sem levar nada de ninguem.
folders_skeleton() {
  local file rest
  while IFS= read -r -d '' file; do
    rest=${file#"$1"/}
    [[ $rest == */* && -f $1/${rest%%/*}/.bundled ]] && continue
    return 1
  done < <(find "$1" -type f ! -name _info.txt -print0 2> /dev/null)
  return 0
}

# folders_own CAMINHO: o dono e a pessoa, nao o root do Setup.
folders_own() {
  ((EUID == 0)) || return 0
  chown -h "$FLIPEROS_USER:" "$1" 2>> "$FLIPEROS_LOG"
  return 0
}

# folders_populate cria o que falta dentro das pastas (fliperos-roms), em
# nome da pessoa.
folders_populate() {
  [[ -x $FOLDERS_SCRIPT ]] || return 0
  if ((EUID == 0)) && id "$FLIPEROS_USER" > /dev/null 2>&1; then
    runuser -u "$FLIPEROS_USER" -- env HOME="$FOLDERS_HOME" "$FOLDERS_SCRIPT" >> "$FLIPEROS_LOG" 2>&1
  else
    HOME=$FOLDERS_HOME "$FOLDERS_SCRIPT" >> "$FLIPEROS_LOG" 2>&1
  fi
  return 0
}

# folders_check confere as pastas e conserta o que foi mexido a mao: sem o
# link (apagado, e o login seguinte criou uma pasta nova e vazia no lugar) e
# com a "old-" ainda ao lado, a de antes volta para o lugar. Imprime cada
# pasta que voltou.
folders_check() {
  local parent rel path old name
  local -a parents=("" roms bios media roms/retroarch roms/fightcade)
  for path in "$FOLDERS_HOME"/media/*/; do
    [[ -d $path ]] || continue
    path=${path%/}
    parents+=("media/${path##*/}")
    [[ -d $path/retroarch ]] && parents+=("media/${path##*/}/retroarch")
  done
  for parent in "${parents[@]}"; do
    [[ -z $parent ]] || folders_known "$parent" || continue
    for old in "$FOLDERS_HOME${parent:+/$parent}"/old-*/; do
      old=${old%/}
      [[ -d $old && ! -L $old ]] || continue
      name=${old##*/old-}
      rel=${parent:+$parent/}$name
      folders_known "$rel" || continue
      path=$(folders_path "$rel")
      [[ -L $path ]] && continue
      if [[ -e $path ]]; then
        [[ -d $path ]] && folders_skeleton "$path" || continue
        rm -rf -- "$path" 2>> "$FLIPEROS_LOG" || continue
      fi
      mv -- "$old" "$path" 2>> "$FLIPEROS_LOG" || continue
      log_info "Folders: $path estava sem o link, a pasta de antes ($old) voltou"
      printf '%s\n' "$rel"
    done
  done
  return 0
}

# folders_validate PASTA ALVO: o ALVO serve de custom folder? Na recusa, o
# motivo fica em FOLDERS_ERROR.
folders_validate() {
  local path parent real target=$2
  FOLDERS_ERROR=""
  path=$(folders_path "$1")
  parent=${path%/*}
  if [[ ! -d $parent ]]; then
    FOLDERS_ERROR="${parent/#$FOLDERS_HOME/\~} is not there (is its disk connected?)."
    return 1
  fi
  if [[ ! -d $target ]]; then
    FOLDERS_ERROR="$target is not a folder."
    return 1
  fi
  target=$(realpath -- "$target") || return 1
  # A pasta de agora, sem seguir o link dela: e ela que muda de nome.
  real=$(realpath -- "$parent")/${path##*/}
  if [[ $target == "$real" || $target == "$real"/* ]]; then
    FOLDERS_ERROR="That folder is ~/$1 itself, or is inside it."
    return 1
  fi
  if [[ $target == / || $real == "$target"/* ]]; then
    FOLDERS_ERROR="~/$1 is inside that folder."
    return 1
  fi
  return 0
}

# folders_link PASTA ALVO faz da PASTA um link para o ALVO. A pasta de agora
# fica ao lado, com "old-" (FOLDERS_KEPT diz onde); um link que ja havia e so
# trocado. Se ja ha uma "old-", e ela a pasta de antes: a de agora sai se so
# tem o que o FliperOS cria sozinho, ou fica com outro nome (old2-...).
folders_link() {
  local rel=$1 target=$2 path old first n=2
  FOLDERS_KEPT=""
  FOLDERS_ERROR=""
  folders_known "$rel" || return 1
  folders_validate "$rel" "$target" || return 1
  target=$(realpath -- "$target") || return 1
  path=$(folders_path "$rel")
  old=$(folders_old "$rel")
  first=$old
  if [[ -L $path ]]; then
    rm -f -- "$path" || return 1
  elif [[ -d $path ]]; then
    if [[ (-e $old || -L $old) ]] && folders_skeleton "$path"; then
      rm -rf -- "$path" || return 1
    else
      while [[ -e $old || -L $old ]]; do
        old=${first%/*}/old$n-${path##*/}
        n=$((n + 1))
      done
      if ! mv -- "$path" "$old" 2>> "$FLIPEROS_LOG"; then
        FOLDERS_ERROR="Could not rename ~/$rel (is a game or a copy using it?)."
        return 1
      fi
      FOLDERS_KEPT=$old
    fi
  elif [[ -e $path ]]; then
    FOLDERS_ERROR="~/$rel is not a folder."
    return 1
  fi
  if ! ln -s -- "$target" "$path" 2>> "$FLIPEROS_LOG"; then
    # Sem o link a pasta de antes volta: nunca fica sem nenhuma.
    [[ -n $FOLDERS_KEPT ]] && mv -- "$FOLDERS_KEPT" "$path" 2>> "$FLIPEROS_LOG"
    FOLDERS_KEPT=""
    FOLDERS_ERROR="Could not create the link (details in the log)."
    return 1
  fi
  folders_own "$path"
  log_info "Folders: $path -> $target${FOLDERS_KEPT:+ (a de antes em $FOLDERS_KEPT)}"
  folders_populate
  return 0
}

# folders_unlink PASTA tira a custom folder: a "old-" ao lado volta a ser a
# pasta; se foi apagada, uma nova e criada. Nada sai da custom folder.
# Status 2: a pasta de antes nao existia e a de agora e nova.
folders_unlink() {
  local rel=$1 path old default rc=0
  FOLDERS_ERROR=""
  folders_known "$rel" || return 1
  path=$(folders_path "$rel")
  old=$(folders_old "$rel")
  if [[ ! -L $path || $(folders_state "$rel") == default ]]; then
    FOLDERS_ERROR="~/$rel has no custom folder."
    return 1
  fi
  if [[ ! -d ${path%/*} ]]; then
    FOLDERS_ERROR="~/${rel%/*} is not there (is its disk connected?)."
    return 1
  fi
  rm -f -- "$path" || return 1
  if [[ -d $old && ! -L $old ]]; then
    if ! mv -- "$old" "$path" 2>> "$FLIPEROS_LOG"; then
      FOLDERS_ERROR="Could not rename ${old/#$FOLDERS_HOME/\~} (details in the log)."
      return 1
    fi
  else
    mkdir -p -- "$path" || return 1
    folders_own "$path"
    rc=2
  fi
  log_info "Folders: $path sem custom folder (a de antes $( ((rc)) && echo "nao existia, criada" || echo "voltou"))"
  folders_populate
  return "$rc"
}
