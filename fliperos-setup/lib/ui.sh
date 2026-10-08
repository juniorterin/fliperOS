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
# Cada argumento de texto vira uma linha (vazio = linha em branco).
ui_screen() {
  local title=$1 w box
  shift
  ui_size
  w=$(ui_box_width)
  if (($#)); then
    box=$(gum style --border rounded --border-foreground "$C_PURPLE" --padding "0 1" \
      --margin "0 2" --width "$w" --foreground "$C_FG" \
      "$(ui_c "$C_PINK" "$title")" "" "$@")
  else
    box=$(gum style --border rounded --border-foreground "$C_PURPLE" --padding "0 1" \
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

# ui_menu TITULO TEXTO PADRAO "valor|rotulo"... mostra o menu e imprime o
# valor escolhido. Status 1 quando a pessoa volta com Esc.
ui_menu() {
  local title=$1 text=$2 default=$3 entry labels=() values=() choice rc height i selected=""
  shift 3
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
  height=$(ui_list_height "${#labels[@]}")
  local args=(--height "$height" --padding "0 4" --header "")
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
  ui_screen "$title" "$text"
  [[ $def == no ]] && args+=(--default=false)
  gum confirm --padding "0 4" --affirmative "Yes" --negative "No" "${args[@]}" "" < /dev/tty 2> /dev/tty
}

# ui_choice2 TITULO SIM NAO TEXTO... pergunta com dois botoes de texto
# proprio (Validate settings / Repeat test). Status 0 = primeiro botao.
ui_choice2() {
  local title=$1 yes=$2 no=$3
  shift 3
  ui_screen "$title" "$@"
  gum confirm --padding "0 4" --affirmative "$yes" --negative "$no" "" < /dev/tty 2> /dev/tty
}

# ui_msg TITULO TEXTO mostra o aviso e espera o Enter.
ui_msg() {
  ui_screen "$1" "${@:2}"
  gum choose --padding "0 4" --header "" "OK" < /dev/tty > /dev/null 2> /dev/tty
  return 0
}

# ui_info TITULO TEXTO mostra o aviso sem esperar ("aguarde...").
ui_info() {
  ui_screen "$1" "${@:2}"
}

# ui_input TITULO TEXTO [VALOR] [password|long] pede um texto e o imprime
# (long: sem o limite de 400 caracteres do gum, para um link magnetico).
ui_input() {
  local title=$1 text=$2 value=${3:-} mode=${4:-} w args
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
    [[ $mode == dir ]] && entries+=("use|Use this folder")
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
