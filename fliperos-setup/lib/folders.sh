# shellcheck shell=bash
# Setup > Folders: as pastas da pessoa em ~ (config/fliperos-roms) e a
# "custom folder" de cada uma. Com uma, ~/<nome> vira um link para outra
# pasta (um disco externo que ja tem as ROMs) e a de antes fica ao lado, em
# ~/old-<nome>; sem ela, a de antes volta.
#
# Nada disso fica anotado: o estado e sempre o que esta no disco. Um link
# feito ou apagado a mao (SSH, a pasta da rede, o desktop) vale igual ao do
# Setup.

FOLDERS_HOME=${FOLDERS_HOME:-/home/$FLIPEROS_USER}
# As pastas que aceitam uma custom folder. A ~/config fica de fora: so tem
# links para as configuracoes, que o fliperos-roms refaz.
FOLDERS_NAMES="roms bios media splashscreen"
# Onde o fliperos-automount monta os discos: o navegador de pastas abre ali.
FOLDERS_MOUNTS=${FOLDERS_MOUNTS:-/media/$FLIPEROS_USER}
FOLDERS_SCRIPT=${FOLDERS_SCRIPT:-/opt/fliperos/bin/fliperos-roms}
# Por que a ultima troca foi recusada, em palavras para a tela.
FOLDERS_ERROR=""
# Onde ficou a pasta de antes na ultima troca (vazio: nenhuma foi guardada).
FOLDERS_KEPT=""

folders_list() {
  printf '%s\n' $FOLDERS_NAMES
}

folders_known() {
  [[ " $FOLDERS_NAMES " == *" $1 "* ]]
}

folders_path() {
  printf '%s\n' "$FOLDERS_HOME/$1"
}

folders_old() {
  printf '%s\n' "$FOLDERS_HOME/old-$1"
}

# folders_description NOME: o que vai na pasta.
folders_description() {
  case $1 in
    roms) echo "The games: one folder per emulator and one per RetroArch core." ;;
    bios) echo "The BIOS files of RetroArch and of the other emulators." ;;
    media) echo "The art and texts the frontends show (snapshots, videos, logos, covers)." ;;
    splashscreen) echo "The boot splash themes." ;;
  esac
}

# folders_state NOME imprime como a pasta esta agora:
#   default  uma pasta comum (a do FliperOS)
#   custom   um link para uma pasta que existe
#   offline  um link para uma pasta que nao esta la (o disco desligado)
#   missing  nao ha nada
folders_state() {
  local path
  path=$(folders_path "$1")
  if [[ -L $path ]]; then
    if [[ -d $path ]]; then echo custom; else echo offline; fi
  elif [[ -d $path ]]; then
    echo default
  else
    echo missing
  fi
}

# folders_target NOME imprime para onde o link aponta.
folders_target() {
  local path target
  path=$(folders_path "$1")
  [[ -L $path ]] || return 1
  target=$(readlink -- "$path") || return 1
  [[ $target == /* ]] || target=$FOLDERS_HOME/$target
  printf '%s\n' "$target"
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

# folders_check confere cada pasta e conserta o que foi mexido a mao: sem o
# link (apagado, e o login seguinte criou uma pasta nova e vazia no lugar) e
# com a ~/old-<nome> ainda la, a de antes volta para o lugar. Imprime o nome
# de cada pasta que voltou.
folders_check() {
  local name path old
  for name in $FOLDERS_NAMES; do
    path=$(folders_path "$name")
    old=$(folders_old "$name")
    [[ -d $old && ! -L $old && ! -L $path ]] || continue
    if [[ -e $path ]]; then
      [[ -d $path ]] && folders_skeleton "$path" || continue
      rm -rf -- "$path" 2>> "$FLIPEROS_LOG" || continue
    fi
    mv -- "$old" "$path" 2>> "$FLIPEROS_LOG" || continue
    log_info "Folders: $path estava sem o link, a pasta de antes ($old) voltou"
    printf '%s\n' "$name"
  done
  return 0
}

# folders_validate NOME PASTA: a PASTA serve de custom folder? Na recusa, o
# motivo fica em FOLDERS_ERROR.
folders_validate() {
  local path real target=$2
  FOLDERS_ERROR=""
  path=$(folders_path "$1")
  if [[ ! -d $target ]]; then
    FOLDERS_ERROR="$target is not a folder."
    return 1
  fi
  target=$(realpath -- "$target") || return 1
  # A pasta de agora, sem seguir o link dela: e ela que muda de nome.
  real=$(realpath -- "$FOLDERS_HOME")/$1
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

# folders_link NOME PASTA faz de ~/NOME um link para PASTA. A pasta de agora
# fica em ~/old-NOME (FOLDERS_KEPT diz onde); um link que ja havia e so
# trocado. Se ja ha uma ~/old-NOME, e ela a pasta de antes: a de agora sai se
# so tem o que o FliperOS cria sozinho, ou ganha outro nome (old-NOME-2...).
folders_link() {
  local name=$1 target=$2 path old n=2
  FOLDERS_KEPT=""
  folders_known "$name" || return 1
  folders_validate "$name" "$target" || return 1
  target=$(realpath -- "$target") || return 1
  path=$(folders_path "$name")
  old=$(folders_old "$name")
  if [[ -L $path ]]; then
    rm -f -- "$path" || return 1
  elif [[ -d $path ]]; then
    if [[ (-e $old || -L $old) ]] && folders_skeleton "$path"; then
      rm -rf -- "$path" || return 1
    else
      while [[ -e $old || -L $old ]]; do
        old=$(folders_old "$name")-$n
        n=$((n + 1))
      done
      if ! mv -- "$path" "$old" 2>> "$FLIPEROS_LOG"; then
        FOLDERS_ERROR="Could not rename ~/$name (is a game or a copy using it?)."
        return 1
      fi
      FOLDERS_KEPT=$old
    fi
  elif [[ -e $path ]]; then
    FOLDERS_ERROR="~/$name is not a folder."
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

# folders_unlink NOME tira a custom folder: a ~/old-NOME volta a ser a
# ~/NOME; se foi apagada, uma nova e criada. Nada sai da custom folder.
# Status 2: a pasta de antes nao existia e a ~/NOME e nova.
folders_unlink() {
  local name=$1 path old rc=0
  FOLDERS_ERROR=""
  folders_known "$name" || return 1
  path=$(folders_path "$name")
  old=$(folders_old "$name")
  if [[ ! -L $path ]]; then
    FOLDERS_ERROR="~/$name has no custom folder."
    return 1
  fi
  rm -f -- "$path" || return 1
  if [[ -d $old && ! -L $old ]]; then
    if ! mv -- "$old" "$path" 2>> "$FLIPEROS_LOG"; then
      FOLDERS_ERROR="Could not rename ~/old-$name (details in the log)."
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
