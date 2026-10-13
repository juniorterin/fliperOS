# shellcheck shell=bash
# Setup > Emulators & Games: os emuladores do menu do desktop, quais estao
# instalados, e a instalacao dos que nao vem na imagem (o Model 2, compilado
# na maquina; o Fightcade 2, baixado do site dele; o KOF Final Attack no
# Ikemen GO, da pasta do jogo que a pessoa traz). O config/fliperos-emulators
# os instala, escrevendo os eventos da tela de progresso (lib/progress.sh).

EMULATORS_CMD=${EMULATORS_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-emulators}
KOF_CMD=${KOF_CMD:-/usr/local/bin/fliperos-kof}

# emulators_list imprime "nome|instalado (0 ou 1)|tipo|descricao" (tipo:
# image, build, fetch ou source).
emulators_list() {
  [[ -x $EMULATORS_CMD ]] || return 1
  "$EMULATORS_CMD" list
}

# emulators_field NOME CAMPO: um campo da linha do emulador.
emulators_field() {
  emulators_list | awk -F'|' -v n="$1" -v f="$2" '$1 == n { print $f; exit }'
}

# emulators_kof_find PASTA imprime a pasta do KOF Final Attack original (a
# que tem o "Final Attack.exe") achada em PASTA ou dentro dela.
emulators_kof_find() {
  [[ -x $KOF_CMD ]] && "$KOF_CMD" find "$1"
}

# emulators_install NOME [PASTA]: PASTA e a do jogo original (tipo source).
emulators_install() {
  local args=()
  ev_step 0 "Starting"
  if [[ ! -x $EMULATORS_CMD ]]; then
    ev_fail "the installer of the emulators ($EMULATORS_CMD) is missing"
    return 1
  fi
  [[ -z ${2:-} ]] || args=(--source "$2")
  log_line cmd "\$ $EMULATORS_CMD install $1 --progress ${args[*]}"
  "$EMULATORS_CMD" install "$1" --progress "${args[@]}" 2>> "$FLIPEROS_LOG"
}
