# shellcheck shell=bash
# Setup > Extras: o Wine, o Steam e o Heroic, que nao vem na imagem para a
# ISO caber num arquivo do GitHub. O config/fliperos-extras os instala pela
# rede, escrevendo os eventos da tela de progresso (lib/progress.sh).

EXTRAS_CMD=${EXTRAS_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-extras}

# extras_list imprime "nome|instalado (0 ou 1)|descricao".
extras_list() {
  [[ -x $EXTRAS_CMD ]] || return 1
  "$EXTRAS_CMD" list
}

extras_installed() {
  [[ -x $EXTRAS_CMD ]] && "$EXTRAS_CMD" installed "$1"
}

# extras_label NOME: a descricao da lista.
extras_label() {
  extras_list | awk -F'|' -v n="$1" '$1 == n { print $3; exit }'
}

extras_install() {
  ev_step 0 "Starting"
  if [[ ! -x $EXTRAS_CMD ]]; then
    ev_fail "the installer of the extras ($EXTRAS_CMD) is missing"
    return 1
  fi
  log_line cmd "\$ $EXTRAS_CMD install $1 --progress"
  "$EXTRAS_CMD" install "$1" --progress 2>> "$FLIPEROS_LOG"
}
