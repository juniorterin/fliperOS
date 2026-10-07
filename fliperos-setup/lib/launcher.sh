# shellcheck shell=bash
# Launcher padrao (o "frontend" do galauncher do GroovyArcade).
#
# A tabela /etc/fliperos/sessions.conf lista os launchers conhecidos:
#   nome|backend|binario|pacote|descricao
# e /etc/fliperos/session guarda o escolhido. O fliperos-session abre o
# escolhido no boot; "setup" nao abre nada e cai direto no menu.
#
# Os frontends que a pessoa cadastra ficam em sessions.custom.conf (uma
# atualizacao reescreve a tabela, nao este arquivo), no mesmo formato:
#   custom-N|kms|COMANDO|custom|ROTULO
# O COMANDO roda num "bash -c", no console como os outros frontends.

launcher_rows() {
  [[ -f $SESSIONS_TABLE ]] || return 1
  cat "$SESSIONS_TABLE" "$CUSTOM_SESSIONS" 2> /dev/null | grep -v '^[[:space:]]*#' | grep -v '^[[:space:]]*$'
}

launcher_field() {
  local name=$1 field=$2
  launcher_rows | awk -F'|' -v n="$name" -v f="$field" '$1 == n { print $f; exit }'
}

launcher_label() {
  local d
  d=$(launcher_field "$1" 5)
  printf '%s\n' "${d:-$1}"
}

# launcher_installed NOME diz se o binario do launcher existe.
launcher_installed() {
  local bin
  [[ $1 == setup ]] && return 0
  bin=$(launcher_field "$1" 3)
  launcher_custom "$1" && bin=$(launcher_custom_program "$bin")
  [[ -n $bin ]] || return 1
  [[ -x $bin ]] || have "$bin"
}

# ── Frontends da pessoa ──────────────────────────────────────────

launcher_custom() {
  [[ $(launcher_field "$1" 4) == custom ]]
}

# launcher_custom_program COMANDO imprime o programa que o comando abre: a
# primeira palavra depois das variaveis (FOO=1 programa ...), com o ~ na
# pasta da pessoa (o Setup roda como root).
launcher_custom_program() {
  local word words
  read -ra words <<< "$1"
  for word in "${words[@]}"; do
    [[ $word =~ ^[A-Za-z_][A-Za-z0-9_]*= ]] && continue
    [[ $word == "~/"* ]] && word=/home/$FLIPEROS_USER/${word#\~/}
    printf '%s\n' "$word"
    return 0
  done
}

# launcher_custom_list imprime "nome|rotulo" de cada frontend da pessoa.
launcher_custom_list() {
  local name pkg desc
  [[ -f $CUSTOM_SESSIONS ]] || return 0
  while IFS='|' read -r name _ _ pkg desc; do
    [[ $pkg == custom ]] && printf '%s|%s\n' "$name" "$desc"
  done < "$CUSTOM_SESSIONS"
  return 0
}

# launcher_custom_valid TEXTO: o rotulo ou o comando cabe numa linha da
# tabela (nao vazio, sem "|" e sem quebra de linha).
launcher_custom_valid() {
  [[ -n ${1//[[:space:]]/} && $1 != *'|'* && $1 != *$'\n'* ]]
}

# launcher_custom_save NOME ROTULO COMANDO grava (NOME vazio: um novo, e o
# nome dele sai na saida).
launcher_custom_save() {
  local name=$1 label=$2 cmd=$3 n=1 line tmp
  launcher_custom_valid "$label" && launcher_custom_valid "$cmd" || return 1
  if [[ -z $name ]]; then
    while launcher_field "custom-$n" 1 | grep -q .; do n=$((n + 1)); done
    name=custom-$n
  fi
  tmp=$(mktemp "$CUSTOM_SESSIONS.XXXXXX") || return 1
  if [[ -f $CUSTOM_SESSIONS ]]; then
    while IFS= read -r line; do
      [[ ${line%%|*} == "$name" ]] || printf '%s\n' "$line"
    done < "$CUSTOM_SESSIONS" > "$tmp"
  fi
  printf '%s|kms|%s|custom|%s\n' "$name" "$cmd" "$label" >> "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$CUSTOM_SESSIONS" || return 1
  log_info "frontend da pessoa: $name = $label ($cmd)"
  printf '%s\n' "$name"
}

# launcher_custom_delete NOME apaga; se era o que abre ao ligar, volta o menu.
launcher_custom_delete() {
  local name=$1 line tmp
  launcher_custom "$name" || return 1
  tmp=$(mktemp "$CUSTOM_SESSIONS.XXXXXX") || return 1
  while IFS= read -r line; do
    [[ ${line%%|*} == "$name" ]] || printf '%s\n' "$line"
  done < "$CUSTOM_SESSIONS" > "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$CUSTOM_SESSIONS" || return 1
  log_info "frontend da pessoa apagado: $name"
  [[ $(launcher_current) == "$name" ]] && launcher_set setup
  return 0
}

# launcher_available imprime "nome|descricao" dos launchers instalados, na
# ordem da tabela: a lista do primeiro boot e gerada do que existe de fato.
launcher_available() {
  local name desc
  while IFS='|' read -r name _ _ _ desc; do
    launcher_installed "$name" && printf '%s|%s\n' "$name" "$desc"
  done < <(launcher_rows)
  # Sem isto, o status era o da ultima linha da tabela (1, se nao instalado).
  return 0
}

launcher_all() {
  local name desc
  while IFS='|' read -r name _ _ _ desc; do
    printf '%s|%s\n' "$name" "$desc"
  done < <(launcher_rows)
}

launcher_current() {
  local s=setup
  [[ -r $SESSION_FILE ]] && s=$(tr -d '[:space:]' < "$SESSION_FILE")
  printf '%s\n' "${s:-setup}"
}

launcher_set() {
  printf '%s\n' "$1" > "$SESSION_FILE"
  conf_set launcher "$1"
  log_info "launcher padrao: $1"
}

# launcher_package NOME imprime o pacote que traz o launcher (repositorio
# do FliperOS), vazio se ele ja vem na imagem ou e baixado do site dele.
launcher_package() {
  local pkg
  pkg=$(launcher_field "$1" 4)
  [[ $pkg == fetch:* ]] || printf '%s\n' "$pkg"
}

# launcher_fetcher NOME imprime o comando que baixa o launcher do site dele
# (a coluna do pacote com "fetch:COMANDO": programa de codigo fechado, que
# nao pode vir na imagem nem no repositorio); vazio para os demais.
launcher_fetcher() {
  local pkg
  pkg=$(launcher_field "$1" 4)
  if [[ $pkg == fetch:* ]]; then
    printf '%s\n' "${FLIPEROS_BIN:-/opt/fliperos/bin}/${pkg#fetch:}"
  fi
}

# launcher_fetch NOME baixa e instala o launcher, falando com a tela de
# progresso por eventos (lib/progress.sh): o proprio comando os escreve.
launcher_fetch() {
  local cmd
  cmd=$(launcher_fetcher "$1")
  ev_step 0 "Starting"
  if [[ -z $cmd || ! -x $cmd ]]; then
    ev_fail "the installer of $(launcher_label "$1") is missing"
    return 1
  fi
  log_line cmd "\$ $cmd fetch --progress"
  "$cmd" fetch --progress 2>> "$FLIPEROS_LOG"
}

# launcher_package_available NOME: o pacote do launcher existe em algum
# repositorio que o apt conhece (o local da imagem, /opt/fliperos/repo, ou
# outro). Sem isso, tentar instalar so da "Impossivel encontrar o pacote".
launcher_package_available() {
  local pkg
  pkg=$(launcher_package "$1")
  [[ -n $pkg ]] || return 1
  apt-cache show "$pkg" > /dev/null 2>&1
}

# O launcher nao abre de dentro do setup: o setup roda como root no pty do
# sudo, e o X precisa do tty1 como terminal de controle (aberto dali, para
# no "xf86OpenConsole: VT_ACTIVATE failed: Operation not permitted").
# launcher_request grava o pedido (o padrao ou NOME) e o setup sai com
# SETUP_EXIT_LAUNCH; o laco do fliperos-tty1, no shell do login, abre o
# launcher como no boot e volta ao setup quando ele fecha.
LAUNCH_REQUEST=${LAUNCH_REQUEST:-/run/fliperos/launch}

launcher_request() {
  mkdir -p "$(dirname "$LAUNCH_REQUEST")" 2> /dev/null
  printf '%s\n' "${1:-default}" > "$LAUNCH_REQUEST" 2> /dev/null || return 1
  chmod 644 "$LAUNCH_REQUEST" 2> /dev/null
  log_info "launcher pedido: ${1:-padrao}"
}
