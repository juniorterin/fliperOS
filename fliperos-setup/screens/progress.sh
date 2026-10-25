# shellcheck shell=bash
# Tela unica de progresso: le os eventos de lib/progress.sh e redesenha so
# o que mudou, com o cursor posicionado (sem limpar a tela, sem piscar). A
# barra so anda quando a operacao anda de verdade.

PROGRESS_OK=0
PROGRESS_FAIL_STEP=""
PROGRESS_FAIL_MSG=""
# A linha de baixo da tela (vazia: o "nao desligue" das operacoes longas).
PROGRESS_FOOTER=""

# _repeat CARACTERE N
_repeat() {
  local s
  printf -v s '%*s' "$2" ''
  printf '%s' "${s// /$1}"
}

# _progress_line TEXTO LARGURA desenha uma linha da caixa, preenchida ate a
# borda para cobrir o que havia antes.
_progress_line() {
  local text=$1 inner=$2 plain
  plain=${text//$'\e'\[+([0-9;])m/}
  if ((${#plain} > inner)); then
    text=${plain:0:inner}
    plain=$text
  fi
  printf '  %s %s%*s %s\n' "$(ui_c "$C_PURPLE" "│")" "$text" $((inner - ${#plain})) "" "$(ui_c "$C_PURPLE" "│")"
}

# _progress_layout LINHAS TEM_ALVO decide o que cabe abaixo do topo num
# console de LINHAS linhas (640x240 com a fonte 8x16 sao so 15): a tela nunca
# passa da ultima linha, senao o terminal rola a cada redesenho. Sem espaco,
# saem primeiro as linhas em branco (a de cima da caixa, a do rodape, as de
# dentro) e depois as mensagens. Deixa em PL_* (0 ou 1) cada linha em branco
# e em PL_MSGS quantas mensagens.
PL_TOP=1 PL_FOOT=1 PL_GAP_MSGS=1 PL_GAP_TITLE=1 PL_GAP_TARGET=1 PL_GAP_BAR=1 PL_MSGS=3
_progress_layout() {
  local rows=$1 target=$2 name need
  PL_TOP=1 PL_FOOT=1 PL_GAP_MSGS=1 PL_GAP_TITLE=1 PL_GAP_TARGET=$target PL_GAP_BAR=1 PL_MSGS=3
  for name in PL_TOP PL_FOOT PL_GAP_MSGS PL_GAP_TITLE PL_GAP_TARGET PL_GAP_BAR PL_MSGS PL_MSGS PL_MSGS ""; do
    # As bordas, o titulo, a barra, a etapa e o rodape ficam sempre.
    need=$((UI_TOPBAR_ROWS + PL_TOP + 6 + PL_GAP_TITLE + target + PL_GAP_TARGET + PL_GAP_BAR + PL_GAP_MSGS + PL_MSGS + PL_FOOT))
    ((need <= rows)) && break
    case $name in
      PL_MSGS) PL_MSGS=$((PL_MSGS - 1)) ;;
      ?*) printf -v "$name" 0 ;;
    esac
  done
}

_progress_draw() {
  local title=$1 target=$2 pct=$3 step=$4 w inner barw full i skip
  # Na interface grafica a tela de progresso e dela (lib/ui.sh).
  ui_progress "$title" "$target" "$pct" "$step" "${PROGRESS_FOOTER:-Please wait. Do not turn off the computer.}" \
    "${@:5}" && return 0
  local footer=${PROGRESS_FOOTER:-Please wait. Do not turn off the computer.}
  shift 4
  w=$(ui_box_width)
  inner=$((w - 4))
  barw=$((inner - 6))
  [[ $pct =~ ^[0-9]+$ ]] || pct=0
  ((pct > 100)) && pct=100
  full=$((barw * pct / 100))
  _progress_layout "$UI_ROWS" "$((${#target} > 0))"
  # Com menos mensagens do que vieram, ficam as ultimas.
  skip=$(($# > PL_MSGS ? $# - PL_MSGS : 0))
  {
    # Logo abaixo do topo (2 linhas, ou 3 com o status numa linha propria).
    printf '\e[%d;1H' $((UI_TOPBAR_ROWS + 1 + PL_TOP))
    printf '  %s\n' "$(ui_c "$C_PURPLE" "╭$(_repeat ─ $((w - 2)))╮")"
    _progress_line "$(ui_c "$C_PINK" "$title")" "$inner"
    ((PL_GAP_TITLE)) && _progress_line "" "$inner"
    if [[ -n $target ]]; then
      _progress_line "$(ui_c "$C_CYAN" "Target:") $target" "$inner"
      ((PL_GAP_TARGET)) && _progress_line "" "$inner"
    fi
    _progress_line "$(ui_c "$C_PURPLE" "$(_repeat █ "$full")")$(ui_c "$C_COMMENT" "$(_repeat ░ $((barw - full)))") $(ui_c "$C_ORANGE" "$(printf '%4s' "$pct%")")" "$inner"
    ((PL_GAP_BAR)) && _progress_line "" "$inner"
    _progress_line "$step" "$inner"
    ((PL_GAP_MSGS)) && _progress_line "" "$inner"
    for ((i = 0; i < PL_MSGS; i++)); do
      if ((skip + i < $#)); then
        _progress_line "$(ui_c "$C_COMMENT" "${*:skip+i+1:1}")" "$inner"
      else
        _progress_line "" "$inner"
      fi
    done
    printf '  %s\n' "$(ui_c "$C_PURPLE" "╰$(_repeat ─ $((w - 2)))╯")"
    ((PL_FOOT)) && printf '\e[K\n'
    # Sem quebra de linha no fim, e cortado na largura do console: na ultima
    # linha, uma quebra (ou o texto dobrando) rolaria a tela.
    printf '  %s\e[K' "$(ui_c "$C_COMMENT" "${footer:0:UI_COLS-3}")"
  } > /dev/tty
}

# screen_progress TITULO ALVO le eventos da entrada padrao ate o fim.
# Resultado em PROGRESS_OK, PROGRESS_FAIL_STEP e PROGRESS_FAIL_MSG.
screen_progress() {
  local title=$1 target=$2 line rest pct=0 step="Starting" msgs=() last=""
  PROGRESS_OK=0
  PROGRESS_FAIL_STEP=""
  PROGRESS_FAIL_MSG=""
  ui_size
  ui_clear
  ui_topbar
  stty -echo < /dev/tty 2> /dev/null
  printf '\e[?25l' > /dev/tty
  _progress_draw "$title" "$target" "$pct" "$step"
  while IFS= read -r line; do
    case $line in
      "@step "*)
        rest=${line#@step }
        pct=${rest%% *}
        step=${rest#* }
        ;;
      "@pct "*) pct=${line#@pct } ;;
      "@msg "*)
        msgs+=("${line#@msg }")
        ((${#msgs[@]} > 3)) && msgs=("${msgs[@]:1}")
        ;;
      "@fail "*)
        rest=${line#@fail }
        PROGRESS_FAIL_STEP=${rest%%|*}
        PROGRESS_FAIL_MSG=${rest#*|}
        continue
        ;;
      *) continue ;;
    esac
    [[ $pct =~ ^[0-9]+$ ]] || pct=0
    ((pct > 100)) && pct=100
    # So redesenha quando algo visivel mudou.
    if [[ "$pct|$step|${msgs[*]}" != "$last" ]]; then
      last="$pct|$step|${msgs[*]}"
      _progress_draw "$title" "$target" "$pct" "$step" "${msgs[@]}"
    fi
  done
  printf '\e[?25h' > /dev/tty
  stty echo < /dev/tty 2> /dev/null
  if [[ -z $PROGRESS_FAIL_MSG && $pct == 100 ]]; then
    PROGRESS_OK=1
  elif [[ -z $PROGRESS_FAIL_MSG ]]; then
    PROGRESS_FAIL_STEP=$step
    PROGRESS_FAIL_MSG="The operation stopped before finishing (see the log)"
  fi
  ui_flush_input
  ((PROGRESS_OK))
}

# screen_progress_failed TITULO mostra a etapa e o erro e pergunta o que
# fazer. Imprime "retry" ou "return".
screen_progress_failed() {
  local title=$1 choice text
  text=$(printf 'Step:\n  %s\n\nError:\n  %s' "$PROGRESS_FAIL_STEP" "$PROGRESS_FAIL_MSG")
  while true; do
    choice=$(ui_menu "$title" "$text" retry "retry|Retry" "log|View log" "return|Return") || choice="return"
    case $choice in
      log) ui_pager "Log" "$FLIPEROS_LOG" ;;
      *)
        printf '%s\n' "$choice"
        return 0
        ;;
    esac
  done
}

# run_with_progress TITULO ALVO COMANDO... roda uma operacao da lib com a
# tela de progresso, oferecendo repetir quando falha. Status 0 = sucesso.
run_with_progress() {
  local title=$1 target=$2 choice
  shift 2
  while true; do
    screen_progress "$title" "$target" < <("$@" < /dev/null) && return 0
    choice=$(screen_progress_failed "$title failed")
    [[ $choice == retry ]] || return 1
  done
}

# Um trabalho longo que segue sem a tela (o Scrape the games): roda num unit
# do systemd, que sobrevive ao Setup fechar, com os eventos de progresso num
# arquivo; a tela so os mostra, e qualquer tecla volta ao menu.
JOBS_DIR=${JOBS_DIR:-/run/fliperos/jobs}

# job_start NOME COMANDO...: o trabalho em segundo plano (fliperos-job-NOME).
# Status 1: nao subiu.
job_start() {
  local name=$1
  shift
  mkdir -p "$JOBS_DIR"
  rm -f "$JOBS_DIR/$name.events"
  log_info "trabalho em segundo plano: $name ($*)"
  systemd-run --unit "fliperos-job-$name" --collect --quiet -p Nice=10 -p IOSchedulingClass=idle \
    -p StandardOutput="file:$JOBS_DIR/$name.events" -p StandardError="append:$FLIPEROS_LOG" \
    "$@" >> "$FLIPEROS_LOG" 2>&1
}

# job_running NOME: o trabalho ainda esta rodando?
job_running() {
  systemctl is-active --quiet "fliperos-job-$1.service" 2> /dev/null
}

# screen_job_watch NOME TITULO ALVO: a barra do trabalho ate ele terminar ou
# ate uma tecla. Status 0 = terminou bem, 1 = a pessoa saiu (ele segue),
# 2 = falhou (PROGRESS_FAIL_STEP e PROGRESS_FAIL_MSG).
screen_job_watch() {
  local name=$1 title=$2 target=$3 events="$JOBS_DIR/$1.events" line pct=0 step="Starting" rc=1
  local -a msgs=()
  PROGRESS_FAIL_STEP="" PROGRESS_FAIL_MSG=""
  ui_size
  ui_clear
  ui_topbar
  stty -echo < /dev/tty 2> /dev/null
  printf '\e[?25l' > /dev/tty
  # shellcheck disable=SC2034 # lido pelo _progress_draw
  PROGRESS_FOOTER="Any key returns to the menu; it goes on in the background."
  while true; do
    msgs=()
    while IFS= read -r line; do
      case $line in
        "@step "*)
          line=${line#@step }
          pct=${line%% *} step=${line#* }
          ;;
        "@msg "*) msgs+=("${line#@msg }") ;;
        "@fail "*)
          line=${line#@fail }
          PROGRESS_FAIL_STEP=${line%%|*} PROGRESS_FAIL_MSG=${line#*|}
          ;;
      esac
    done < "$events" 2> /dev/null
    [[ $pct =~ ^[0-9]+$ ]] || pct=0
    # As ultimas tres mensagens (com menos, todas).
    _progress_draw "$title" "$target" "$pct" "$step" "${msgs[@]:$((${#msgs[@]} > 3 ? ${#msgs[@]} - 3 : 0))}"
    if ! job_running "$name"; then
      rc=0
      [[ -n $PROGRESS_FAIL_MSG ]] && rc=2
      break
    fi
    ui_wait_key 2 && break
  done
  # shellcheck disable=SC2034
  PROGRESS_FOOTER=""
  printf '\e[?25h' > /dev/tty
  stty echo < /dev/tty 2> /dev/null
  ui_flush_input
  return "$rc"
}

# run_online TITULO ALVO COMANDO... e o run_with_progress de algo que baixa:
# sem internet, antes a oferta do Wi-Fi (screen_need_internet).
run_online() {
  screen_need_internet "$1" || return 1
  run_with_progress "$@"
}
