# shellcheck shell=bash
# Setup > Games > Extras: o Wine, o Steam e o Heroic, que nao vem na imagem para a
# ISO caber num arquivo do GitHub, o Pixelcade (codigo fechado) e o ZeDMD. O
# config/fliperos-extras os instala pela rede, escrevendo os eventos da tela
# de progresso (lib/progress.sh).

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

# extras_note NOME: o aviso antes de instalar; extras_done NOME: o de depois.
# O ZeDMD so conecta com o firmware 5.1 ou mais novo (o libzedmd 0.10 do
# dmdserver): o 3.x, o 4.x e o 5.0, os do Batocera 41, nunca respondem
# (docs/wiki/Frontends.md, ZeDMD firmware version).
extras_note() {
  case $1 in
    zedmd) echo "ZeDMD needs firmware 5.1.0 or newer. Older ones (3.x, 4.x, 5.0, which work on Batocera 41) don't connect. The display shows its version on its logo at power on. How to update: FliperOS wiki, Frontends page." ;;
  esac
}

extras_done() {
  case $1 in
    zedmd) echo "If the display stays on its logo, its firmware is older than 5.1: update it (FliperOS wiki, Frontends page)." ;;
  esac
}

# extras_artpack CODIGO: o pacote de arte pago do Pixelcade, com o codigo de
# licenca da compra (config/fliperos-pixelcade artpack).
PIXELCADE_CMD=${PIXELCADE_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-pixelcade}
extras_artpack() {
  ev_step 0 "Starting"
  if [[ ! -x $PIXELCADE_CMD ]]; then
    ev_fail "the Pixelcade helper ($PIXELCADE_CMD) is missing"
    return 1
  fi
  # O codigo nao vai para o log.
  log_line cmd "\$ $PIXELCADE_CMD artpack <code> --progress"
  "$PIXELCADE_CMD" artpack "$1" --progress 2>> "$FLIPEROS_LOG"
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
