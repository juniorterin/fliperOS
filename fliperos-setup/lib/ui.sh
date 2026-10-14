# shellcheck shell=bash
# Camada de apresentacao: o unico arquivo de lib/ que chama o gum.
#
# Tema Dracula. As cores sao os indices 0-15 da paleta, nunca hexadecimais:
# no console do Linux (onde o setup roda no CRT) so existem 16 cores, e a
# paleta do VT e reprogramada com os tons do Dracula (/etc/console-setup/vtrgb
# no boot, e ui_init de novo). Assim o gum pinta igual no tubo e num
# terminal grafico.
#
# Pensado para 640x480i: com a fonte 8x16 sao 80x30 caracteres (64x24 em
# 512x384). Nada anima nem pisca; a tela so e redesenhada quando muda.

UI_TITLE=${UI_TITLE:-FliperOS}
# A versao ao lado do titulo. Vem do fliperos-setup, que cada update troca.
UI_VERSION=${UI_VERSION-${FLIPEROS_SETUP_VERSION:-}}
UI_STATUS=""
UI_ROWS=30
UI_COLS=80

# Indices da paleta (ver ui_palette).
C_BG=0 C_RED=1 C_GREEN=2 C_YELLOW=3 C_PURPLE=4 C_PINK=5 C_CYAN=6 C_FG=7 C_COMMENT=8 C_ORANGE=11

# Dracula, na ordem dos indices ANSI. O 11 e o laranja no lugar do amarelo
# claro: sem ele nao haveria laranja para avisos.
UI_PALETTE=(282a36 ff5555 50fa7b f1fa8c bd93f9 ff79c6 8be9fd f8f8f2
  6272a4 ff6e6e 69ff94 ffb86c d6acff ff92df a4ffff ffffff)

ui_palette() {
  local i
  if [[ ${TERM:-} == linux ]]; then
    for i in "${!UI_PALETTE[@]}"; do
      printf '\e]P%X%s' "$i" "${UI_PALETTE[i]}"
    done
  else
    for i in "${!UI_PALETTE[@]}"; do
      printf '\e]4;%d;#%s\a' "$i" "${UI_PALETTE[i]}"
    done
    printf '\e]11;#%s\a\e]10;#%s\a' "${UI_PALETTE[0]}" "${UI_PALETTE[7]}"
  fi
}

ui_init() {
  ui_palette > /dev/tty 2> /dev/null
  export GUM_CHOOSE_CURSOR="> "
  export GUM_CHOOSE_CURSOR_FOREGROUND=$C_PINK
  export GUM_CHOOSE_HEADER_FOREGROUND=$C_PURPLE
  export GUM_CHOOSE_ITEM_FOREGROUND=$C_FG
  export GUM_CHOOSE_SELECTED_FOREGROUND=$C_PINK
  export GUM_CHOOSE_CURSOR_PREFIX="[ ] "
  export GUM_CHOOSE_SELECTED_PREFIX="[x] "
  export GUM_CHOOSE_UNSELECTED_PREFIX="[ ] "
  export GUM_CONFIRM_PROMPT_FOREGROUND=$C_FG
  export GUM_CONFIRM_PROMPT_BOLD=false
  export GUM_CONFIRM_SELECTED_FOREGROUND=$C_BG
  export GUM_CONFIRM_SELECTED_BACKGROUND=$C_PINK
  export GUM_CONFIRM_UNSELECTED_FOREGROUND=$C_FG
  export GUM_CONFIRM_UNSELECTED_BACKGROUND=$C_BG
  export GUM_INPUT_PROMPT_FOREGROUND=$C_PINK
  export GUM_INPUT_CURSOR_FOREGROUND=$C_PINK
  # Cursor fixo: piscar e redesenhar a tela duas vezes por segundo, o que
  # tremula num modo entrelacado.
  export GUM_INPUT_CURSOR_MODE=static
  export GUM_INPUT_HEADER_FOREGROUND=$C_PURPLE
  export GUM_INPUT_PLACEHOLDER_FOREGROUND=$C_COMMENT
  export GUM_PAGER_BORDER_FOREGROUND=$C_PURPLE
  export GUM_PAGER_HELP_FOREGROUND=$C_COMMENT
  export GUM_PAGER_LINE_NUMBER_FOREGROUND=$C_COMMENT
  ui_sounds
  ui_gui_start
  return 0
}

# A interface grafica (gui/fliperos-gui, em pygame) e a outra saida desta
# camada: com ela no ar, cada funcao daqui manda a tela ao servidor em vez de
# chamar o gum, e as telas do Setup nao mudam. So abre no menu do gabinete
# (fliperos-menu, o --menu), nunca num "sudo fliperos-setup" digitado por SSH,
# e na midia de instalacao fica o texto. FLIPEROS_UI=text|gui (ou "ui" no
# fliperos.conf) forca um dos dois. Sem video, sem pygame ou com o servidor
# morto, tudo volta ao gum.
UI_GUI=0
UI_GUI_PID=""
UI_GUI_REPLY=""
UI_STYLE=""
UI_GUI_DIR=${UI_GUI_DIR:-/run/fliperos/gui}
UI_GUI_BIN=${UI_GUI_BIN:-${SETUP_DIR:-/usr/local/lib/fliperos-setup}/gui/fliperos-gui}
UI_DRI=${UI_DRI:-/dev/dri/card0}
# O VT que esta na tela: o teclado dele fica calado com a interface no ar.
UI_GUI_CONSOLE=${UI_GUI_CONSOLE:-/dev/tty0}

ui_gui_wanted() {
  case ${FLIPEROS_UI:-$(conf_get ui 2> /dev/null)} in
    text) return 1 ;;
    gui) return 0 ;;
  esac
  # Pelo desktop (o atalho FliperOS Setup do LXDE, --desktop): numa janela.
  ((${SETUP_DESKTOP:-0} == 1)) && [[ -n ${DISPLAY:-} ]] && return 0
  ((${SETUP_MENU_LOOP:-0} == 1)) && [[ -z ${DISPLAY:-} && -e $UI_DRI ]] && ! is_live
}

# ui_gui_alive: a interface grafica esta no ar?
ui_gui_alive() {
  ((UI_GUI)) && kill -0 "$UI_GUI_PID" 2> /dev/null
}

# ui_gui_start abre o servidor e espera ele avisar que o video abriu (o
# arquivo ready). A espera e um read com tempo num FIFO, nao um sleep.
ui_gui_start() {
  local i
  ui_gui_wanted || return 1
  [[ -x $UI_GUI_BIN ]] && have python3 || return 1
  rm -rf "$UI_GUI_DIR"
  mkdir -p "$UI_GUI_DIR" && mkfifo "$UI_GUI_DIR/req" "$UI_GUI_DIR/resp" || return 1
  # No console o video e o KMS e o teclado do VT da tela fica calado
  # enquanto a interface esta nele (UI_GUI_CONSOLE); no desktop, uma janela
  # no X. A orientacao do monitor: com ele em pe, a imagem gira.
  local driver=kmsdrm console=""
  if [[ -n ${DISPLAY:-} ]]; then
    driver=x11
  elif [[ -c $UI_GUI_CONSOLE ]]; then
    console=$UI_GUI_CONSOLE
  fi
  FLIPEROS_GUI_ORIENTATION=$(conf_get orientation 2> /dev/null || echo horizontal) \
    FLIPEROS_GUI_CONSOLE=$console \
    SDL_VIDEODRIVER=${SDL_VIDEODRIVER:-$driver} SDL_AUDIODRIVER=${SDL_AUDIODRIVER:-alsa} \
    "$UI_GUI_BIN" --serve "$UI_GUI_DIR" < /dev/null >> "$FLIPEROS_LOG" 2>&1 &
  UI_GUI_PID=$!
  for ((i = 0; i < 150; i++)); do
    if [[ -e $UI_GUI_DIR/ready ]]; then
      UI_GUI=1
      return 0
    fi
    kill -0 "$UI_GUI_PID" 2> /dev/null || break
    read -r -t 0.1 _ <> "$UI_GUI_DIR/resp"
  done
  log_info "a interface grafica nao abriu: o Setup segue em texto"
  kill "$UI_GUI_PID" 2> /dev/null
  UI_GUI_PID=""
  return 1
}

# ui_gui_call COMANDO ARGUMENTO... manda o pedido e espera a resposta: o
# status e o da tela (1 = Esc) e o texto fica em UI_GUI_REPLY. O protocolo
# esta em gui/serve.py.
ui_gui_call() {
  local IFS=$'\x1f' cmd=$1 reply="" part fd
  shift
  set -- "$cmd" "$(ui_status_short)" "$UI_VERSION" "$@"
  # Os FIFOs abertos para ler e escrever nao travam a abertura, e a espera
  # olha o servidor a cada segundo: se ele morrer no meio de uma tela, o
  # Setup nao fica parado para sempre (a tela volta como Esc).
  exec {fd}<> "$UI_GUI_DIR/req" || return 1
  printf '%s\x1e' "$*" >&"$fd"
  exec {fd}>&-
  exec {fd}<> "$UI_GUI_DIR/resp" || return 1
  while true; do
    if IFS= read -r -d $'\x1e' -t 1 -u "$fd" part; then
      reply+=$part
      break
    fi
    reply+=$part
    if ! kill -0 "$UI_GUI_PID" 2> /dev/null; then
      exec {fd}<&-
      return 1
    fi
  done
  exec {fd}<&-
  UI_GUI_REPLY=${reply#*$'\x1f'}
  return "${reply%%$'\x1f'*}"
}

# ui_gui_menu menu|radio|check TITULO TEXTO ATUAL "valor|rotulo"... e o menu
# na interface grafica, com as dicas de UI_HINTS e o estilo de UI_STYLE (um
# seletor desenhado para o ui_radio ou o ui_checklist: people, dots, controls
# ou years; o texto ignora). Imprime a escolha.
ui_gui_menu() {
  local mode=$1 title=$2 text=$3 current=$4 entry i=0
  local -a entries=()
  shift 4
  for entry in "$@"; do
    entries+=("${entry%%|*}"$'\x1d'"${entry#*|}"$'\x1d'"${UI_HINTS[i]:-}")
    i=$((i + 1))
  done
  ui_gui_call "$mode" "$title" "$text" "$current" "${UI_STYLE:-}" "${entries[@]}" || return 1
  printf '%s\n' "$UI_GUI_REPLY"
}

# ui_board TITULO TEXTO PADRAO "valor|rotulo|titulo|tipo|dado|ajuda"... e um
# menu de parametros. Na interface grafica e um painel de azulejos: cada um
# tem o titulo e o valor desenhado (o tipo e o dado sao os do mini() de
# gui/widgets.py), e a ajuda do que esta sob o cursor aparece embaixo; com
# UI_BOARD_SCORE=ARQUIVO, o placar (games= e bytes=) aparece quando ele
# fica pronto. No texto e o ui_menu com os rotulos. Imprime o valor
# escolhido; 1 = Esc.
ui_board() {
  local title=$1 text=$2 default=$3 entry key label name kind data help
  local -a plain=() items=()
  shift 3
  for entry in "$@"; do
    IFS='|' read -r key label name kind data help <<< "$entry"
    plain+=("$key|$label")
    items+=("$key"$'\x1d'"$name"$'\x1d'"$kind"$'\x1d'"$data"$'\x1d'"$help")
  done
  if ui_gui_alive; then
    ui_gui_call board "$title" "$text" "$default" "${UI_BOARD_SCORE:-}" "${items[@]}" || return 1
    printf '%s\n' "$UI_GUI_REPLY"
    return 0
  fi
  ui_menu "$title" "$text" "$default" "${plain[@]}"
}


# ui_done fecha a interface grafica e espera ela soltar o video: quem vem
# depois (um frontend, o proprio Setup reaberto) precisa dele livre.
ui_done() {
  local i
  ((UI_GUI)) || return 0
  if ui_gui_alive; then
    ui_gui_call quit
    for ((i = 0; i < 50; i++)); do
      kill -0 "$UI_GUI_PID" 2> /dev/null || break
      read -r -t 0.1 _ <> "$UI_GUI_DIR/resp"
    done
    kill "$UI_GUI_PID" 2> /dev/null
  fi
  # O teclado do console de volta mesmo se a interface caiu sem devolve-lo.
  [[ -z ${DISPLAY:-} && -c $UI_GUI_CONSOLE ]] && kbd_mode -u -C "$UI_GUI_CONSOLE" 2> /dev/null
  UI_GUI=0
  rm -rf "$UI_GUI_DIR"
  return 0
}

# ui_text COMANDO... roda um programa que desenha no terminal (alsamixer, o
# calibrador, o grid do Switchres) ou troca o modo de video: a interface
# grafica solta o video antes e o retoma depois.
ui_text() {
  local rc
  ui_gui_alive && ui_gui_call suspend
  "$@"
  rc=$?
  ui_gui_alive && ui_gui_call resume
  return "$rc"
}

# ui_orientation ORIENTACAO: o monitor mudou de orientacao (Video Setup), e
# a interface grafica gira a imagem na hora. No texto o fbcon ja girou.
ui_orientation() {
  ui_gui_alive && ui_gui_call orient "$1"
  return 0
}

# ui_wait_key SEGUNDOS espera uma tecla por esse tempo. Status 0 = apertou.
ui_wait_key() {
  if ui_gui_alive; then
    ui_gui_call keywait "$1"
    return
  fi
  read -rsn1 -t "$1" _ < /dev/tty
}

# ui_progress TITULO ALVO PORCENTO ETAPA RODAPE MENSAGEM... desenha a tela
# de progresso na interface grafica (com UI_STYLE=download, a do download do
# Downloader, uma barra por torrent). Status 1: nao ha interface grafica, e
# quem chamou (screens/progress.sh) desenha no terminal.
ui_progress() {
  ui_gui_alive || return 1
  ui_gui_call progress "$1" "$2" "$3" "$4" "$5" "${UI_STYLE:-}" "${@:6}"
  return 0
}

# ui_capture TITULO JOGADOR COMANDO NUMERO TOTAL SEGUNDOS JA_APERTADOS...
# mostra o Button mapping pedindo um comando (up, b3, start...) no painel
# desenhado e volta na hora. Status 1: nao ha interface grafica (quem chamou
# mostra o texto).
ui_capture() {
  ui_gui_alive || return 1
  ui_gui_call capture "$@"
  return 0
}

# ui_layout_pick TITULO BOTOES PADRAO POSICAO... pergunta, no painel de 3x2,
# onde fica o proximo botao do jogo (as POSICOES, de 1 a 6, sao as dos ja
# postos; PADRAO=1 deixa escolher o layout padrao). Imprime a posicao ou
# "default"; status 1 = Esc, 2 = nao ha interface grafica.
ui_layout_pick() {
  ui_gui_alive || return 2
  ui_gui_call layout "$@" || return 1
  printf '%s\n' "$UI_GUI_REPLY"
}


# ui_sounds liga ou desliga os sons do menu no gum (menu_sounds_env, em
# lib/audio.sh).
ui_sounds() {
  local line
  unset GUM_SOUND_MOVE GUM_SOUND_SELECT
  while IFS= read -r line; do
    [[ -n $line ]] && export "${line?}"
  done < <(menu_sounds_env)
  return 0
}

# ui_size le o tamanho do console, que muda quando o teste de saidas liga
# uma saida com outro modo de video.
ui_size() {
  local size
  size=$(stty size < /dev/tty 2> /dev/null) || size=""
  if [[ $size =~ ^([0-9]+)\ ([0-9]+)$ ]]; then
    UI_ROWS=${BASH_REMATCH[1]}
    UI_COLS=${BASH_REMATCH[2]}
  fi
  ((UI_ROWS > 0)) || UI_ROWS=30
  ((UI_COLS > 0)) || UI_COLS=80
}

# ui_box_width e a largura do quadro: ate 72 colunas, sempre com margem.
ui_box_width() {
  local w=$((UI_COLS - 4))
  ((w > 72)) && w=72
  ((w < 30)) && w=$((UI_COLS - 2))
  printf '%s\n' "$w"
}

# ui_c COR TEXTO imprime o texto colorido com SGR puro (sem processo novo).
ui_c() {
  local c=$1
  shift
  if ((c < 8)); then
    printf '\e[%dm%s\e[0m' $((30 + c)) "$*"
  else
    printf '\e[%dm%s\e[0m' $((82 + c)) "$*"
  fi
}

ui_clear() {
  ui_gui_alive && return 0
  printf '\e[H\e[2J\e[3J' > /dev/tty
}

# ui_status_short imprime o status sem o nome da maquina: o primeiro IP e o
# uso do disco ("192.168.1.111 - 42%").
ui_status_short() {
  local ips="" used=""
  [[ $UI_STATUS =~ \(([^\)]*)\) ]] && ips=${BASH_REMATCH[1]}
  [[ $UI_STATUS =~ ([0-9?]+%)\ used ]] && used=${BASH_REMATCH[1]}
  [[ $ips == "no network" ]] || ips=${ips%% *}
  printf '%s%s\n' "${ips:-$UI_STATUS}" "${used:+ - $used}"
}

# ui_topbar desenha o topo: titulo (com a versao, so no "FliperOS") a
# esquerda, status (IP e uso do disco) a direita e a linha. Sem espaco para
# o status inteiro ao lado do titulo vai o curto; sem espaco nem para ele
# (320x240: 40 colunas), o status ganha uma linha propria embaixo do
# titulo. UI_TOPBAR_ROWS e quantas linhas o topo ocupou.
UI_TOPBAR_ROWS=2
ui_topbar() {
  ui_gui_alive && return 0
  local title=" $UI_TITLE" version="" left right="" line2="" space
  [[ $UI_TITLE == FliperOS && -n $UI_VERSION ]] && version=" $UI_VERSION"
  left=$title$version
  UI_TOPBAR_ROWS=2
  if [[ -n $UI_STATUS ]]; then
    right="$UI_STATUS "
    ((UI_COLS - ${#left} - ${#right} >= 1)) || right="$(ui_status_short) "
    if ((UI_COLS - ${#left} - ${#right} < 1)); then
      line2=${right:0:UI_COLS}
      right=""
      UI_TOPBAR_ROWS=3
    fi
  fi
  space=$((UI_COLS - ${#left} - ${#right}))
  ((space < 0)) && space=0
  {
    ui_c "$C_PURPLE" "$title"
    [[ -n $version ]] && ui_c "$C_COMMENT" "$version"
    printf '%*s' "$space" ""
    ui_c "$C_CYAN" "$right"
    printf '\n'
    if [[ -n $line2 ]]; then
      printf '%*s' $((UI_COLS - ${#line2})) ""
      ui_c "$C_CYAN" "$line2"
      printf '\n'
    fi
    ui_c "$C_COMMENT" "$(printf '%*s' "$UI_COLS" '' | sed 's/ /─/g')"
    printf '\n'
  } > /dev/tty
}

# UI_USED_ROWS e quantas linhas a ultima ui_screen ocupou: o widget do gum
# (lista, botoes) vem logo abaixo, no que sobrar da tela.
UI_USED_ROWS=0

# ui_screen TITULO [TEXTO...] limpa a tela e desenha barra, titulo e caixa.
# Cada argumento de texto vira uma linha (vazio = linha em branco). O
# CLICOLOR_FORCE e porque a caixa passa por uma variavel: sem ele o gum, que
# nao ve um terminal na saida, tira as cores (moldura e titulo brancos).
ui_screen() {
  local title=$1 w box
  shift
  ui_size
  w=$(ui_box_width)
  if (($#)); then
    box=$(CLICOLOR_FORCE=1 gum style --border rounded --border-foreground "$C_PURPLE" --padding "0 1" \
      --margin "0 2" --width "$w" --foreground "$C_FG" \
      "$(ui_c "$C_PINK" "$title")" "" "$@")
  else
    box=$(CLICOLOR_FORCE=1 gum style --border rounded --border-foreground "$C_PURPLE" --padding "0 1" \
      --margin "0 2" --width "$w" --foreground "$C_PINK" "$title")
  fi
  ui_clear
  ui_topbar
  printf '\n%s\n\n' "$box" > /dev/tty
  UI_USED_ROWS=$((UI_TOPBAR_ROWS + 1 + $(printf '%s\n' "$box" | wc -l) + 1))
}

# ui_list_height ITENS calcula quantas linhas a lista pode ocupar abaixo da
# caixa, deixando espaco para a linha de ajuda do gum.
ui_list_height() {
  local items=$1 free
  # Sobra para a ajuda do gum (2 linhas) e, se a lista rolar, para as setas
  # da paginacao (patches/gum: uma linha antes da lista, outra depois).
  free=$((UI_ROWS - UI_USED_ROWS - 5))
  ((free < 3)) && free=3
  ((items < free)) && free=$items
  printf '%s\n' "$free"
}

# Os baloes de informacao: UI_HINTS tem o texto de cada item do proximo
# ui_menu, na ordem (ui_menu_hints o preenche). O gum do FliperOS
# (patches/gum/0004-choose-balao.patch) mostra embaixo da lista o do item
# sob o cursor; o gum sem o patch ignora as variaveis e nao mostra nada.
UI_HINTS=()
# Linhas de texto do balao numa tela baixa (320x240: 15 linhas), onde ele
# fica sem moldura, no lugar da ajuda do gum.
UI_HINT_SMALL_LINES=2

# ui_hint_small: a tela e baixa demais para o balao com moldura?
ui_hint_small() {
  ((UI_ROWS < 20))
}

# ui_hint_lines LARGURA imprime quantas linhas o maior texto de UI_HINTS
# ocupa quebrado em LARGURA colunas, sem cortar palavras.
ui_hint_lines() {
  printf '%s\n' "${UI_HINTS[@]}" | awk -v w="$1" '
    { n = 1; col = 0
      for (i = 1; i <= NF; i++) {
        l = length($i)
        if (col == 0) col = l
        else if (col + 1 + l <= w) col += 1 + l
        else { n++; col = l }
      }
      if (n > max) max = n }
    END { print max + 0 }'
}

# ui_hint_env prepara o balao do gum (as GUM_CHOOSE_HINT* de quem chama) e
# soma a UI_USED_ROWS as linhas que ele ocupa. Na tela baixa a ajuda do gum
# sai (UI_HINT_ARGS) e o balao fica com as duas linhas dela.
UI_HINT_ARGS=()
ui_hint_env() {
  local w lines
  UI_HINT_ARGS=()
  GUM_CHOOSE_HINTS=$(printf '%s\n' "${UI_HINTS[@]}")
  GUM_CHOOSE_HINT_FOREGROUND=$C_CYAN
  GUM_CHOOSE_HINT_BORDER_FOREGROUND=$C_COMMENT
  if ui_hint_small; then
    GUM_CHOOSE_HINT_BORDER=0
    GUM_CHOOSE_HINT_WIDTH=$((UI_COLS - 6))
    GUM_CHOOSE_HINT_LINES=$UI_HINT_SMALL_LINES
    UI_HINT_ARGS=(--show-help=false)
    return 0
  fi
  w=$(($(ui_box_width) - 2))
  lines=$(ui_hint_lines $((w - 4)))
  ((lines < 1)) && lines=1
  ((lines > 3)) && lines=3
  GUM_CHOOSE_HINT_BORDER=1
  GUM_CHOOSE_HINT_WIDTH=$w
  GUM_CHOOSE_HINT_LINES=$lines
  UI_USED_ROWS=$((UI_USED_ROWS + lines + 2))
}

# ui_menu_hints TITULO TEXTO PADRAO "valor|rotulo|balao"... e o ui_menu com
# um balao de informacao por item (o rotulo nao pode ter "|").
ui_menu_hints() {
  local title=$1 text=$2 default=$3 entry rest rc entries=()
  shift 3
  UI_HINTS=()
  for entry in "$@"; do
    rest=${entry#*|}
    entries+=("${entry%%|*}|${rest%%|*}")
    if [[ $rest == *"|"* ]]; then UI_HINTS+=("${rest#*|}"); else UI_HINTS+=(""); fi
  done
  ui_menu "$title" "$text" "$default" "${entries[@]}"
  rc=$?
  UI_HINTS=()
  return "$rc"
}

# ui_menu TITULO TEXTO PADRAO "valor|rotulo"... mostra o menu e imprime o
# valor escolhido. Status 1 quando a pessoa volta com Esc.
ui_menu() {
  local title=$1 text=$2 default=$3 entry labels=() values=() choice rc height i selected=""
  local -x GUM_CHOOSE_HINTS="" GUM_CHOOSE_HINT_WIDTH="" GUM_CHOOSE_HINT_LINES="" GUM_CHOOSE_HINT_BORDER=""
  local -x GUM_CHOOSE_HINT_FOREGROUND="" GUM_CHOOSE_HINT_BORDER_FOREGROUND=""
  shift 3
  if ui_gui_alive; then
    ui_gui_menu menu "$title" "$text" "$default" "$@"
    return
  fi
  for entry in "$@"; do
    values+=("${entry%%|*}")
    labels+=("${entry#*|}")
  done
  for i in "${!values[@]}"; do
    [[ ${values[i]} == "$default" ]] && selected=${labels[i]}
  done
  if [[ -n $text ]]; then
    ui_screen "$title" "$text"
  else
    ui_screen "$title"
  fi
  UI_HINT_ARGS=()
  ((${#UI_HINTS[@]})) && ui_hint_env
  height=$(ui_list_height "${#labels[@]}")
  local args=(--height "$height" --padding "0 4" --header "")
  args+=("${UI_HINT_ARGS[@]}")
  # O --selected e uma lista separada por virgulas: a virgula do rotulo vai
  # escapada, senao o cursor voltava ao primeiro item.
  [[ -n $selected ]] && args+=(--selected "${selected//,/\\,}")
  choice=$(gum choose "${args[@]}" -- "${labels[@]}" < /dev/tty 2> /dev/tty)
  rc=$?
  ((rc == 0)) || return 1
  for i in "${!labels[@]}"; do
    if [[ ${labels[i]} == "$choice" ]]; then
      printf '%s\n' "${values[i]}"
      return 0
    fi
  done
  return 1
}

# ui_radio TITULO TEXTO ATUAL "valor|rotulo"... escolhe uma opcao: a atual
# vem marcada "(*)" e com o cursor nela. Imprime o valor escolhido; status 1
# = Esc (fica a atual).
ui_radio() {
  local title=$1 text=$2 current=$3 entry entries=()
  shift 3
  if ui_gui_alive; then
    ui_gui_menu radio "$title" "$text" "$current" "$@"
    return
  fi
  for entry in "$@"; do
    if [[ ${entry%%|*} == "$current" ]]; then
      entries+=("${entry%%|*}|(*) ${entry#*|}")
    else
      entries+=("${entry%%|*}|( ) ${entry#*|}")
    fi
  done
  ui_menu "$title" "$text" "$current" "${entries[@]}"
}

# ui_checklist TITULO TEXTO MARCADOS "valor|rotulo"... escolhe varias opcoes
# (MARCADOS: os valores marcados ao abrir, separados por virgula). Espaco
# marca e desmarca, "a" marca ou desmarca todas, Enter confirma. Imprime os
# valores marcados separados por virgula (nada, se nenhum); status 1 = Esc
# (fica como estava).
ui_checklist() {
  local title=$1 text=$2 current=",$3," entry choice height i out="" selected=""
  local -a labels=() values=() args
  shift 3
  if ui_gui_alive; then
    ui_gui_menu check "$title" "$text" "${current:1:-1}" "$@"
    return
  fi
  for entry in "$@"; do
    values+=("${entry%%|*}")
    labels+=("${entry#*|}")
    if [[ $current == *",${entry%%|*},"* ]]; then
      entry=${entry#*|}
      selected+="${selected:+,}${entry//,/\\,}"
    fi
  done
  ui_screen "$title" "$text" "$(ui_dim "Space (button 3) marks, A marks all, Enter confirms.")"
  height=$(ui_list_height "${#labels[@]}")
  args=(--no-limit --height "$height" --padding "0 4" --header "")
  [[ -n $selected ]] && args+=(--selected "$selected")
  choice=$(gum choose "${args[@]}" -- "${labels[@]}" < /dev/tty 2> /dev/tty) || return 1
  for i in "${!labels[@]}"; do
    grep -qxF -- "${labels[i]}" <<< "$choice" && out+="${out:+,}${values[i]}"
  done
  printf '%s\n' "$out"
}

# ui_yesno TITULO TEXTO [padrao-nao] pergunta sim ou nao. Status 0 = Yes.
ui_yesno() {
  local title=$1 text=$2 def=${3:-yes} args=()
  if ui_gui_alive; then
    ui_gui_call yesno "$title" "$def" Yes No "$text"
    return
  fi
  ui_screen "$title" "$text"
  [[ $def == no ]] && args+=(--default=false)
  gum confirm --padding "0 4" --affirmative "Yes" --negative "No" "${args[@]}" "" < /dev/tty 2> /dev/tty
}

# ui_choice2 TITULO SIM NAO TEXTO... pergunta com dois botoes de texto
# proprio (Validate settings / Repeat test). Status 0 = primeiro botao.
ui_choice2() {
  local title=$1 yes=$2 no=$3
  shift 3
  if ui_gui_alive; then
    ui_gui_call yesno "$title" yes "$yes" "$no" "$@"
    return
  fi
  ui_screen "$title" "$@"
  gum confirm --padding "0 4" --affirmative "$yes" --negative "$no" "" < /dev/tty 2> /dev/tty
}

# ui_msg TITULO TEXTO mostra o aviso e espera o Enter.
ui_msg() {
  if ui_gui_alive; then
    ui_gui_call msg "$@"
    return 0
  fi
  ui_screen "$1" "${@:2}"
  gum choose --padding "0 4" --header "" "OK" < /dev/tty > /dev/null 2> /dev/tty
  return 0
}

# ui_info TITULO TEXTO mostra o aviso sem esperar ("aguarde...").
ui_info() {
  if ui_gui_alive; then
    ui_gui_call info "$@"
    return 0
  fi
  ui_screen "$1" "${@:2}"
}

# ui_input TITULO TEXTO [VALOR] [password|long] [BOTAO EXPLICACAO] pede um
# texto e o imprime (long: sem o limite de 400 caracteres do gum, para um
# link magnetico). Com BOTAO, a tela oferece tambem essa acao (abrir o
# navegador): na interface grafica um botao embaixo do campo, no texto um
# menu antes dele. Status 3 = a pessoa escolheu o botao.
ui_input() {
  local title=$1 text=$2 value=${3:-} mode=${4:-} action=${5:-} about=${6:-} w args choice
  if ui_gui_alive; then
    ui_gui_call input "$title" "$text" "$value" "$mode" "$action" "$about"
    case $? in
      0) printf '%s\n' "$UI_GUI_REPLY" ;;
      3) return 3 ;;
      *) return 1 ;;
    esac
    return 0
  fi
  if [[ -n $action ]]; then
    choice=$(ui_menu "$title" "$text${about:+$'\n\n'$about}" type "type|Type or paste it" "action|$action") ||
      return 1
    [[ $choice == action ]] && return 3
  fi
  ui_screen "$title" "$text"
  w=$(($(ui_box_width) - 6))
  args=(--padding "0 4" --width "$w" --value "$value" --placeholder "")
  [[ $mode == password ]] && args+=(--password)
  [[ $mode == long ]] && args+=(--char-limit 0)
  gum input "${args[@]}" < /dev/tty 2> /dev/tty
}

# ui_timed_confirm TITULO SEGUNDOS ROTULO TEXTO... espera o Enter por um
# tempo limitado. Status 0 = Enter, 124 = acabou o tempo, 1 = Esc.
ui_timed_confirm() {
  local title=$1 seconds=$2 label=$3 rc
  shift 3
  if ui_gui_alive; then
    ui_gui_call timed "$title" "$seconds" "$label" "$@"
    return
  fi
  ui_screen "$title" "$@"
  gum choose --padding "0 4" --header "" --timeout "${seconds}s" "$label" < /dev/tty > /dev/null 2> /dev/tty
  rc=$?
  case $rc in
    0) return 0 ;;
    124) return 124 ;;
    *) return 1 ;;
  esac
}

# ui_pager TITULO ARQUIVO [inicio] mostra o fim de um arquivo longo (log)
# com rolagem; com "inicio", o comeco (uma lista). O conteudo vai como
# argumento (ate 128 KB): a entrada padrao do gum tem de ser o teclado.
ui_pager() {
  local content
  if [[ ${3:-} == inicio ]]; then
    content=$(head -n 1200 "$2" 2> /dev/null)
  else
    content=$(tail -n 400 "$2" 2> /dev/null)
  fi
  if ui_gui_alive; then
    ui_gui_call pager "$1" "$content" "${3:-}"
    return 0
  fi
  ui_size
  ui_clear
  ui_topbar
  gum pager --border rounded --height $((UI_ROWS - 1 - UI_TOPBAR_ROWS)) "$content" \
    < /dev/tty > /dev/tty 2> /dev/tty
}

# ui_browse TITULO TEXTO PASTA dir|file [EXTENSAO...] navega pelas pastas a
# partir de PASTA no menu de sempre (teclado e joystick) e imprime a pasta
# escolhida ("Use this folder") ou, com file, o arquivo (so os de EXTENSAO,
# ex. .xml). Enter abre uma pasta, ".." volta. Status 1 = Esc. Nao e o gum
# file: ele ignora o --height e ocupa a tela inteira, sem a caixa do titulo.
ui_browse() {
  local title=$1 text=$2 dir=$3 mode=$4 from="" path name ext ok choice default i
  local -a exts=("${@:5}") paths entries
  dir=$(cd -- "$dir" 2> /dev/null && pwd) || dir=/
  while true; do
    paths=() entries=() default=""
    [[ $mode == dir ]] && entries+=("use|Use this folder" "newfolder|[+ Folder]")
    [[ $dir != / ]] && entries+=("up|..")
    for path in "$dir"/*/; do
      [[ -d $path ]] || continue
      path=${path%/}
      name=${path##*/}
      [[ $name == "$from" ]] && default=${#paths[@]}
      entries+=("${#paths[@]}|$name/")
      paths+=("$path")
    done
    if [[ $mode == file ]]; then
      for path in "$dir"/*; do
        [[ -f $path ]] || continue
        ok=$((${#exts[@]} == 0))
        for ext in "${exts[@]}"; do
          [[ ${path,,} == *"$ext" ]] && ok=1
        done
        ((ok)) || continue
        entries+=("${#paths[@]}|${path##*/}")
        paths+=("$path")
      done
    fi
    choice=$(ui_menu "$title" "$text"$'\n'"$(ui_c "$C_CYAN" "$dir")" "$default" "${entries[@]}") || return 1
    case $choice in
      use)
        printf '%s\n' "$dir"
        return 0
        ;;
      up)
        from=${dir##*/}
        dir=${dir%/*}
        [[ -n $dir ]] || dir=/
        ;;
      newfolder)
        # Uma pasta nova aqui dentro, e o seletor ja entra nela.
        name=$(ui_input "$title" "Name of the new folder in $dir:") || continue
        name=${name//\//}
        [[ -n $name && $name != . && $name != .. ]] || continue
        if [[ -e $dir/$name ]] && [[ ! -d $dir/$name ]]; then
          ui_msg "$title" "$(ui_bad "There is already a file named $name here.")"
        elif mkdir -p -- "$dir/$name" 2>> "${FLIPEROS_LOG:-/dev/null}"; then
          # Do dono da pasta de cima: no ~ do gabinete, o usuario, nao o root.
          chown --reference="$dir" -- "$dir/$name" 2> /dev/null
          from="" dir=${dir%/}/$name
        else
          ui_msg "$title" "$(ui_bad "Could not create the folder $name.")" "Is the disk read-only, or full?"
        fi
        ;;
      *)
        i=$choice
        if [[ -d ${paths[i]} ]]; then
          from="" dir=${paths[i]}
        else
          printf '%s\n' "${paths[i]}"
          return 0
        fi
        ;;
    esac
  done
}

# ui_flush_input descarta teclas apertadas enquanto nada era perguntado:
# um Enter dado durante a instalacao nao pode responder a pergunta seguinte.
ui_flush_input() {
  local _k
  while read -r -s -t 0.05 -n 1 _k < /dev/tty 2> /dev/null; do :; done
  return 0
}

# ui_fields "Rotulo|valor"... alinha pares em duas colunas (Testing Results).
ui_fields() {
  local entry label value width=0
  for entry in "$@"; do
    label=${entry%%|*}
    ((${#label} > width)) && width=${#label}
  done
  for entry in "$@"; do
    label=${entry%%|*}
    value=${entry#*|}
    printf '%s %s\n' "$(ui_c "$C_CYAN" "$(printf '%-*s' "$((width + 1))" "$label:")")" "$value"
  done
}

# ui_yes/ui_no/ui_warn colorem valores dos campos.
ui_yes() { ui_c "$C_GREEN" "$*"; }
ui_no() { ui_c "$C_ORANGE" "$*"; }
ui_bad() { ui_c "$C_RED" "$*"; }
ui_dim() { ui_c "$C_COMMENT" "$*"; }
