# shellcheck shell=bash
# Controle nos menus (config/fliperos-padkeys): o servico so traduz o
# controle em teclas enquanto o arquivo PADKEYS_FLAG existe, isto e,
# enquanto o setup esta na tela. Ao sair (inclusive para abrir um launcher,
# que le o controle sozinho) o setup o apaga. Dentro vai o PID do dono: se
# ele morrer sem apagar (o tty1 reiniciado), o servico ignora e apaga o
# arquivo, em vez de traduzir o controle no frontend e nos jogos.

PADKEYS_FLAG=${PADKEYS_FLAG:-/run/fliperos/padkeys}

# padkeys_on [PID]: o dono (padrao: este Setup).
padkeys_on() {
  mkdir -p "$(dirname "$PADKEYS_FLAG")" 2> /dev/null
  echo "${1:-$$}" > "$PADKEYS_FLAG" 2> /dev/null
  return 0
}

padkeys_off() {
  rm -f "$PADKEYS_FLAG" 2> /dev/null
  return 0
}
