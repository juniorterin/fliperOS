# shellcheck shell=bash
# Eventos de progresso das operacoes longas (instalacao, atualizacao,
# scraper, reparo). A operacao roda sem tela e escreve na saida padrao:
#   @step PORCENTAGEM TEXTO   etapa nova
#   @pct PORCENTAGEM          so a porcentagem
#   @msg TEXTO                mensagem curta para o historico da tela
#   @fail ETAPA|ERRO          falhou (o detalhe esta no log)
# e a tela de progresso (screens/progress.sh) le e desenha. Assim nenhuma
# operacao destrutiva depende da interface.

PROGRESS_STEP=""

ev_step() {
  PROGRESS_STEP=$2
  printf '@step %s %s\n' "$1" "$2"
  log_info "progresso: [$1%] $2"
}

ev_pct() {
  printf '@pct %s\n' "$1"
}

ev_msg() {
  printf '@msg %s\n' "$*"
  log_info "progresso: $*"
}

ev_fail() {
  printf '@fail %s|%s\n' "$PROGRESS_STEP" "$1"
  log_error "falhou em '$PROGRESS_STEP': $1"
  return 1
}

# ev_run roda o comando mandando a saida para o log; na falha, a ultima
# linha que o comando escreveu vira a mensagem de erro da tela.
ev_run() {
  local out rc
  log_line cmd "\$ $*"
  out=$("$@" 2>&1)
  rc=$?
  [[ -n $out ]] && printf '%s\n' "$out" >> "$FLIPEROS_LOG"
  ((rc == 0)) && return 0
  log_line cmd "  -> saiu com $rc"
  out=$(printf '%s\n' "$out" | grep -v '^[[:space:]]*$' | tail -1 | cut -c1-200)
  ev_fail "${out:-$1 exited with status $rc}"
  return 1
}
