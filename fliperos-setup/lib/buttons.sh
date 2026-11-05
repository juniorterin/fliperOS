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

# buttons_used MAPA INDICE ELEMENTO imprime "NOME JOGADOR" do comando que ja
# tem esse elemento do controle no mapa; nada se ele esta livre.
buttons_used() {
  local p control
  read -r p control < <(awk -v i="$2" -v e="$3" '$3 == i && $4 == e { print $1, $2; exit }' "$1" 2> /dev/null) ||
    return 0
  printf '%s %s\n' "${BUTTON_LABELS[$control]:-$control}" "$p"
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

# buttons_attract poe o controle do mapa no input_map do Attract-Mode Plus.
# O save ja grava, mas so num attract.cfg que exista: o Attract-Mode
# instalado (ou aberto pela primeira vez) depois do Button mapping o recebe
# aqui, a cada abertura (fliperos-setup --session-start).
buttons_attract() {
  [[ -r $BUTTONS_MAP && -x $BUTTONS ]] || return 0
  "$BUTTONS" attract "$BUTTONS_MAP" >> "$FLIPEROS_LOG" 2>&1
  return 0
}

# buttons_players_line imprime os jogadores de agora: os do Button mapping que
# tem o controle ligado (fliperos-buttons players) e quantos controles ha. Solta
# um controle, o jogador dele sai da conta; ligado de volta, volta. Vazio sem
# mapa. buttons_players_connected imprime so quantos controles estao ligados
# (de 1 a 4), a sugestao de "How many players?".
buttons_players_line() {
  local out mapped connected active
  [[ -x $BUTTONS && -r $BUTTONS_MAP ]] || return 0
  out=$("$BUTTONS" players "$BUTTONS_MAP" 2> /dev/null) || return 0
  mapped=$(sed -n 's/^mapped=//p' <<< "$out")
  connected=$(sed -n 's/^connected=//p' <<< "$out")
  active=$(sed -n 's/^active=//p' <<< "$out")
  [[ -n $mapped && $mapped != 0 ]] || return 0
  printf 'Players now: %s of %s mapped (controllers connected: %s)\n' "$active" "$mapped" "$connected"
}

buttons_players_connected() {
  local n
  n=$("$BUTTONS" players "${BUTTONS_MAP:-/nonexistent}" 2> /dev/null | sed -n 's/^connected=//p')
  [[ $n =~ ^[0-9]+$ ]] || n=2
  ((n < 1)) && n=1
  ((n > 4)) && n=4
  printf '%s\n' "$n"
}

# buttons_keyboard JOGADORES grava, no lugar do controle, as teclas padrao do
# MAME de cada jogador em todos os emuladores: o encoder que se diz teclado
# (I-PAC e afins) ja vem nesse layout, e nada precisa ser apertado.
buttons_keyboard() {
  "$BUTTONS" keyboard --players "$1" >> "$FLIPEROS_LOG" 2>&1 || return 1
  ini_set "$MAME_INI" ctrlr fliperos
  ini_set "$MAME_INI" joystickprovider sdljoy
  log_info "botoes gravados: teclado no layout do MAME, $1 jogador(es)"
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
# A do core mame2010 do RetroArch (o fliperos-kms-run a acha por este nome).
GAME_BUTTONS_MAME2010=${GAME_BUTTONS%.txt}-mame2010.txt
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
# com os layouts. O core mame2010 do RetroArch tem a tabela dele, do XML do
# MAME 0.139, que numera os botoes de alguns jogos de outro jeito (Tekken 3:
# 1 2 4 5); o XML do GroovyMAME vai junto como o MAME mais novo.
buttons_layout_apply() {
  local controls word
  local -a source old newer=() data=()
  mapfile -t source < <(romclean_xml_args groovymame "")
  controls=$(romclean_data_find controls.xml "$ROMCLEAN_DATA") && data=(--controls-xml "$controls")
  "$ROMCLEAN" buttons "${source[@]}" "${data[@]}" --out "$GAME_BUTTONS" >> "$FLIPEROS_LOG" 2>&1 ||
    log_info "sem a tabela de botoes dos jogos (o GroovyMAME esta instalado?)"
  if [[ -f $MAME2010_XML ]]; then
    mapfile -t old < <(romclean_xml_args mame2010 "")
    for word in "${source[@]}"; do
      case $word in
        --xml | --xml-command | --cache) newer+=("--newer-${word#--}") ;;
        *) newer+=("$word") ;;
      esac
    done
    "$ROMCLEAN" buttons "${old[@]}" "${newer[@]}" "${data[@]}" --out "$GAME_BUTTONS_MAME2010" >> "$FLIPEROS_LOG" 2>&1 ||
      log_info "sem a tabela de botoes dos jogos do MAME 2010"
  fi
  FLIPEROS_BUTTONS_LAYOUT=$BUTTONS_LAYOUT FLIPEROS_GAME_BUTTONS=$GAME_BUTTONS \
    "$BUTTONS" save "$BUTTONS_MAP" >> "$FLIPEROS_LOG" 2>&1
}

# A GunCon 2 (Setup > Joysticks > GunCon 2), tudo no fliperos.conf:
# - gun_flash: o flash da tela no tiro, como o GCON2 FLASH do RePlayOS. Uma
#   pistola de CRT so acha a mira onde a tela tem luz; numa parte escura o
#   tiro saia na mira guardada ou fora da tela. As camadas OpenGL e Vulkan dos
#   emuladores (config/fliperos-deflicker.c, config/fliperos-vkfps.c) o leem:
#   pulse (o padrao, dois quadros claros no tiro), hold (claro com o gatilho
#   apertado) ou off;
# - gun_flash_level e os ajustes do driver da tabela (gun_table), e
#   gun_offscreen_reload.
# O fliperos-guncon2-calibrate poe os do driver quando a pistola chega, e aqui
# na hora (--params).
GUNCON2_CALIBRATE=${GUNCON2_CALIBRATE:-/usr/local/bin/fliperos-guncon2-calibrate}

# gun_table: chave|rotulo|minimo|maximo|padrao|passo|ajuda. O padrao de cada um
# do driver e o do driver (config/guncon2-patches).
gun_table() {
  cat << 'TABLE'
flash_level|Flash brightness (%)|10|100|100|10|Lower is calmer; too low and the gun misses it.
flash_ms|Flash wait (ms)|30|300|100|10|How long a dark shot waits for the flash.
hold_ms|Dark hold (ms)|0|1000|150|50|How long the aim stays put without light.
edge_pct|Edge band (%)|0|30|12|1|Losing light this near an edge is off screen.
TABLE
}

gun_field() {
  gun_table | awk -F'|' -v k="$1" -v n="$2" '$1 == k { print $n; exit }'
}

# gun_get CHAVE: o valor gravado, ou o padrao.
gun_get() {
  local value
  value=$(conf_get "gun_$1" 2> /dev/null) || value=""
  [[ $value =~ ^[0-9]+$ ]] || value=$(gun_field "$1" 5)
  printf '%s\n' "$value"
}

# gun_apply: os ajustes do driver na hora.
gun_apply() {
  [[ -x $GUNCON2_CALIBRATE ]] && "$GUNCON2_CALIBRATE" --params >> "$FLIPEROS_LOG" 2>&1
  return 0
}

# gun_set CHAVE VALOR: grava dentro da faixa e aplica. Status 1 = chave ou
# valor invalido.
gun_set() {
  local key=$1 value=$2 min max
  min=$(gun_field "$key" 3)
  max=$(gun_field "$key" 4)
  [[ -n $min && $value =~ ^[0-9]+$ ]] || return 1
  ((value < min)) && value=$min
  ((value > max)) && value=$max
  conf_set "gun_$key" "$value"
  gun_apply
  log_info "GunCon 2: $key=$value"
}

gunflash_mode() {
  local mode
  mode=$(conf_get gun_flash 2> /dev/null)
  [[ $mode == off || $mode == hold ]] && echo "$mode" || echo pulse
}

gunflash_set() {
  [[ $1 =~ ^(off|pulse|hold)$ ]] || return 2
  conf_set gun_flash "$1"
  gun_apply
  log_info "GunCon 2: flash $1"
}

gun_reload_on() {
  [[ $(conf_get gun_offscreen_reload 2> /dev/null) != off ]]
}

gun_reload_set() {
  [[ $1 == on || $1 == off ]] || return 2
  conf_set gun_offscreen_reload "$1"
  gun_apply
}

# gun_reset: tudo de volta ao padrao (a calibracao fica).
gun_reset() {
  local key
  for key in flash flash_level flash_ms hold_ms edge_pct offscreen_reload; do
    conf_unset "gun_$key"
  done
  # O driver nao tem "sem linha": os padroes dele de novo.
  conf_set gun_hold_ms "$(gun_field hold_ms 5)"
  conf_set gun_edge_pct "$(gun_field edge_pct 5)"
  conf_set gun_offscreen_reload on
  gun_apply
}

# gun_connected: a GunCon 2 ligada agora (o calibrador acha o evento dela).
gun_connected() {
  [[ -x $CALIBRATE ]] && [[ -n $("$CALIBRATE" list gun 2> /dev/null) ]]
}
