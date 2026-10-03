# shellcheck shell=bash
# Jogos livres (Setup > Free games): homebrew de codigo aberto para as pastas
# de ~/roms, para os frontends nao comecarem vazios. A lista (endereco,
# sha256 e licenca de cada um) e o config/fliperos-freeroms.

FREEROMS=${FREEROMS:-/opt/fliperos/bin/fliperos-freeroms}

# freeroms_list imprime "Titulo (core, licenca)" de cada jogo.
freeroms_list() {
  "$FREEROMS" list | awk -F'\t' '{ printf "%s (%s, %s)\n", $3, $1, $4 }'
}

# freeroms_fetch baixa o que falta, falando com a tela de progresso por
# eventos (lib/progress.sh); o resultado (downloaded=, present=, skipped=,
# failed=) fica em ARQUIVO.
freeroms_fetch() {
  local result=$1
  ev_step 0 "Starting"
  "$FREEROMS" fetch --progress 2>> "$FLIPEROS_LOG" | tee "$result"
  return "${PIPESTATUS[0]}"
}
