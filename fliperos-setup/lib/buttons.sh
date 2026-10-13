# shellcheck shell=bash
# Setup > Joysticks > Button mapping: os comandos de cada jogador, pegos um a
# um no controle, para o RetroArch e o GroovyMAME (config/fliperos-buttons).

BUTTONS=${BUTTONS:-/opt/fliperos/bin/fliperos-buttons}
# Os comandos, na ordem em que sao pedidos, e o nome na tela.
BUTTON_CONTROLS=(up down left right b1 b2 b3 b4 b5 b6 start coin)
declare -A BUTTON_LABELS=(
  [up]="UP" [down]="DOWN" [left]="LEFT" [right]="RIGHT"
  [b1]="BUTTON 1 (top row, left)" [b2]="BUTTON 2 (top row, middle)" [b3]="BUTTON 3 (top row, right)"
  [b4]="BUTTON 4 (bottom row, left)" [b5]="BUTTON 5 (bottom row, middle)" [b6]="BUTTON 6 (bottom row, right)"
  [start]="START" [coin]="COIN (insert coin)"
)

# buttons_capture SEGUNDOS espera o proximo comando de qualquer controle e
# imprime "INDICE ELEMENTO NOME". Status 1: o tempo acabou (pular).
buttons_capture() {
  "$BUTTONS" capture --timeout "$1" 2>> "$FLIPEROS_LOG"
}

# buttons_save MAPA grava os botoes no RetroArch e no GroovyMAME: o ctrlr
# fliperos e o joystickprovider sdljoy, em que o MAME numera os botoes como o
# SDL, na ordem do aparelho.
buttons_save() {
  "$BUTTONS" save "$1" >> "$FLIPEROS_LOG" 2>&1 || return 1
  ini_set "$MAME_INI" ctrlr fliperos
  ini_set "$MAME_INI" joystickprovider sdljoy
  log_info "botoes gravados: $(awk '{ print $1 }' "$1" | sort -u | wc -l) jogador(es)"
}

# ── Buttons layout ───────────────────────────────────────────────
# Setup > Joysticks > Buttons layout: onde ficam no painel (1 2 3 em cima,
# 4 5 6 embaixo) os botoes dos jogos de 1 a 5 botoes. Uma linha "BOTOES
# POSICAO..." por numero de botoes no buttons.layout; sem linha, o botao N
# do jogo fica na posicao N. O fliperos-buttons aplica (GroovyMAME, os cores
# MAME do RetroArch, Supermodel e SM2-Emu) pela tabela de quantos botoes cada
# jogo tem.

BUTTONS_MAP=${BUTTONS_MAP:-$FLIPEROS_ETC/buttons.map}
BUTTONS_LAYOUT=${BUTTONS_LAYOUT:-$FLIPEROS_ETC/buttons.layout}
GAME_BUTTONS=${GAME_BUTTONS:-/var/lib/fliperos/game-buttons.txt}
BUTTONS_LAYOUT_COUNTS=(1 2 3 4 5)
BUTTONS_POSITIONS=("Top row, left" "Top row, middle" "Top row, right"
  "Bottom row, left" "Bottom row, middle" "Bottom row, right")

# buttons_layout_get BOTOES imprime a posicao do botao 1, do 2... dos jogos
# de BOTOES botoes ("1 4 2 5"): a gravada ou o padrao.
buttons_layout_get() {
  local count=$1 saved
  saved=$(awk -v c="$count" '$1 == c { $1 = ""; sub(/^ +/, ""); print; exit }' "$BUTTONS_LAYOUT" 2> /dev/null)
  if [[ -n $saved ]]; then
    printf '%s\n' "$saved"
  else
    seq -s ' ' 1 "$count"
  fi
}

# buttons_layout_grid POSICAO... desenha o painel em duas linhas, com o
# numero do botao do jogo em cada posicao: "[1]  [3]  [ ]".
buttons_layout_grid() {
  local -a cells=(" " " " " " " " " " " ")
  local n=0 position
  for position in "$@"; do
    n=$((n + 1))
    cells[position - 1]=$n
  done
  printf '[%s]  [%s]  [%s]\n[%s]  [%s]  [%s]\n' "${cells[@]}"
}

# buttons_layout_row POSICAO... e o mesmo painel numa linha so (os menus).
buttons_layout_row() {
  buttons_layout_grid "$@" | paste -sd'|' - | sed 's/  //g; s/|/ \/ /'
}

# buttons_layout_set BOTOES POSICAO... grava o layout dos jogos de BOTOES
# botoes (o padrao tira a linha). Status 1: posicao repetida ou fora do painel.
buttons_layout_set() {
  local count=$1 position seen="" rest
  shift
  (($# == count)) || return 1
  for position in "$@"; do
    [[ $position =~ ^[1-6]$ && $seen != *"$position"* ]] || return 1
    seen+=$position
  done
  rest=$(awk -v c="$count" '$1 != c' "$BUTTONS_LAYOUT" 2> /dev/null)
  {
    [[ -z $rest ]] || printf '%s\n' "$rest"
    [[ "$*" == "$(seq -s ' ' 1 "$count")" ]] || printf '%s %s\n' "$count" "$*"
  } | sort -n > "$BUTTONS_LAYOUT.new"
  mv "$BUTTONS_LAYOUT.new" "$BUTTONS_LAYOUT"
  log_info "layout dos jogos de $count botoes: $*"
}

# buttons_layout_apply refaz a tabela de quantos botoes cada jogo tem (do
# -listxml do GroovyMAME, com os do controls.xml) e grava os botoes de novo,
# com os layouts.
buttons_layout_apply() {
  local controls
  local -a source data=()
  mapfile -t source < <(romclean_xml_args groovymame "")
  controls=$(romclean_data_find controls.xml "$ROMCLEAN_DATA") && data=(--controls-xml "$controls")
  "$ROMCLEAN" buttons "${source[@]}" "${data[@]}" --out "$GAME_BUTTONS" >> "$FLIPEROS_LOG" 2>&1 ||
    log_info "sem a tabela de botoes dos jogos (o GroovyMAME esta instalado?)"
  FLIPEROS_BUTTONS_LAYOUT=$BUTTONS_LAYOUT FLIPEROS_GAME_BUTTONS=$GAME_BUTTONS \
    "$BUTTONS" save "$BUTTONS_MAP" >> "$FLIPEROS_LOG" 2>&1
}
