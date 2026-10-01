# shellcheck shell=bash
# Launcher padrao (o "frontend" do galauncher do GroovyArcade).
#
# A tabela /etc/fliperos/sessions.conf lista os launchers conhecidos:
#   nome|backend|binario|pacote|descricao
# e /etc/fliperos/session guarda o escolhido. O fliperos-session abre o
# escolhido no boot; "setup" nao abre nada e cai direto no menu.

launcher_rows() {
  [[ -f $SESSIONS_TABLE ]] || return 1
  grep -v '^[[:space:]]*#' "$SESSIONS_TABLE" | grep -v '^[[:space:]]*$'
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
  [[ -n $bin ]] || return 1
  [[ -x $bin ]] || have "$bin"
}

# launcher_available imprime "nome|descricao" dos launchers instalados, na
# ordem da tabela: a lista do primeiro boot e gerada do que existe de fato.
launcher_available() {
  local name desc
  while IFS='|' read -r name _ _ _ desc; do
    launcher_installed "$name" && printf '%s|%s\n' "$name" "$desc"
  done < <(launcher_rows)
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
# do FliperOS), vazio se ele ja vem na imagem.
launcher_package() {
  launcher_field "$1" 4
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
