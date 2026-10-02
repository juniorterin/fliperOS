# shellcheck shell=bash
# Tela unica de progresso: le os eventos de lib/progress.sh e redesenha so
# o que mudou, com o cursor posicionado (sem limpar a tela, sem piscar). A
# barra so anda quando a operacao anda de verdade.

PROGRESS_OK=0
PROGRESS_FAIL_STEP=""
PROGRESS_FAIL_MSG=""

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

_progress_draw() {
  local title=$1 target=$2 pct=$3 step=$4 w inner barw full i
  shift 4
  w=$(ui_box_width)
  inner=$((w - 4))
  barw=$((inner - 6))
  full=$((barw * pct / 100))
  {
    # Logo abaixo do topo (2 linhas, ou 3 com o status numa linha propria).
    printf '\e[%d;1H' $((UI_TOPBAR_ROWS + 2))
    printf '  %s\n' "$(ui_c "$C_PURPLE" "╭$(_repeat ─ $((w - 2)))╮")"
    _progress_line "$(ui_c "$C_PINK" "$title")" "$inner"
    _progress_line "" "$inner"
    if [[ -n $target ]]; then
      _progress_line "$(ui_c "$C_CYAN" "Target:") $target" "$inner"
      _progress_line "" "$inner"
    fi
    _progress_line "$(ui_c "$C_PURPLE" "$(_repeat █ "$full")")$(ui_c "$C_COMMENT" "$(_repeat ░ $((barw - full)))") $(ui_c "$C_ORANGE" "$(printf '%4s' "$pct%")")" "$inner"
    _progress_line "" "$inner"
    _progress_line "$step" "$inner"
    _progress_line "" "$inner"
    for i in 0 1 2; do
      if ((i < $#)); then
        _progress_line "$(ui_c "$C_COMMENT" "${*:i+1:1}")" "$inner"
      else
        _progress_line "" "$inner"
      fi
    done
    printf '  %s\n' "$(ui_c "$C_PURPLE" "╰$(_repeat ─ $((w - 2)))╯")"
    printf '\n  %s\e[K\n' "$(ui_c "$C_COMMENT" "Please wait. Do not turn off the computer.")"
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
    choice=$(ui_menu "$title" "$text" retry "log|View log" "retry|Retry" "return|Return") || choice="return"
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
