# shellcheck shell=bash
# Setup > Joysticks > Button mapping: os comandos de cada jogador, pegos um a
# um no controle, para o RetroArch e o GroovyMAME (config/fliperos-buttons).

BUTTONS=${BUTTONS:-/opt/fliperos/bin/fliperos-buttons}
# Os comandos de um painel de arcade (ou JAMMA), na ordem em que sao pedidos,
# e o nome na tela; os botoes vao de 1 ao numero de botoes do painel
# (buttons_arcade_controls). 1 2 3 7 em cima, 4 5 6 8 embaixo.
BUTTON_CONTROLS=(up down left right b1 b2 b3 b4 b5 b6 start coin)
BUTTONS_MAX=8
declare -A BUTTON_LABELS=(
  [up]="UP" [down]="DOWN" [left]="LEFT" [right]="RIGHT"
  [b1]="BUTTON 1 (top row, left)" [b2]="BUTTON 2 (top row, middle)" [b3]="BUTTON 3 (top row, right)"
  [b4]="BUTTON 4 (bottom row, left)" [b5]="BUTTON 5 (bottom row, middle)" [b6]="BUTTON 6 (bottom row, right)"
  [b7]="BUTTON 7 (top row, last)" [b8]="BUTTON 8 (bottom row, last)"
  [start]="START" [coin]="COIN (insert coin)"
)

# O joypad, na ordem e com os nomes do mapeador do Batocera
# (GuiInputConfig do batocera-emulationstation): os quatro botoes pela
# posicao (sul, leste, norte, oeste), Start e Select, o direcional, os
# ombros, os analogicos (cima e esquerda), os gatilhos, os cliques dos
# analogicos e o hotkey. Cada um no comando do mapa (fliperos-buttons): o
# botao de oeste e o 1, o de norte o 2, os ombros o 3 e o 6, o de sul o 4, o
# de leste o 5, os gatilhos o 7 e o 8; o Select e a ficha.
PAD_CONTROLS=(b4 b5 b2 b1 start coin up down left right b3 b6 lsup lsleft rsup rsleft b7 b8 l3 r3 hotkey)
declare -A PAD_LABELS=(
  [b4]="SOUTH" [b5]="EAST" [b2]="NORTH" [b1]="WEST" [start]="START" [coin]="SELECT"
  [up]="D-PAD UP" [down]="D-PAD DOWN" [left]="D-PAD LEFT" [right]="D-PAD RIGHT"
  [b3]="LEFT SHOULDER" [b6]="RIGHT SHOULDER" [lsup]="LEFT ANALOG UP" [lsleft]="LEFT ANALOG LEFT"
  [rsup]="RIGHT ANALOG UP" [rsleft]="RIGHT ANALOG LEFT" [b7]="LEFT TRIGGER" [b8]="RIGHT TRIGGER"
  [l3]="LEFT STICK PRESS" [r3]="RIGHT STICK PRESS" [hotkey]="HOTKEY"
)
# O nome que o botao tem no controle, pelo tipo (fliperos-buttons identify).
declare -A PAD_GLYPHS=(
  [xbox:b4]=A [xbox:b5]=B [xbox:b2]=Y [xbox:b1]=X [xbox:b3]=LB [xbox:b6]=RB [xbox:b7]=LT [xbox:b8]=RT
  [xbox:coin]=BACK [xbox:start]=START [xbox:hotkey]=GUIDE
  [playstation:b4]=CROSS [playstation:b5]=CIRCLE [playstation:b2]=TRIANGLE [playstation:b1]=SQUARE
  [playstation:b3]=L1 [playstation:b6]=R1 [playstation:b7]=L2 [playstation:b8]=R2
  [playstation:coin]=SELECT [playstation:start]=START [playstation:hotkey]=PS
  [nintendo:b4]=B [nintendo:b5]=A [nintendo:b2]=X [nintendo:b1]=Y [nintendo:b3]=L [nintendo:b6]=R
  [nintendo:b7]=ZL [nintendo:b8]=ZR [nintendo:coin]=- [nintendo:start]=+ [nintendo:hotkey]=HOME
)
# Segurar um botao esse tempo pula o comando, como no Batocera.
PAD_HOLD=1
PAD_TIMEOUT=10

# buttons_arcade_controls BOTOES imprime os comandos de um painel de BOTOES
# botoes (1 a 8), na ordem em que sao pedidos.
buttons_arcade_controls() {
  local n out="up down left right"
  for ((n = 1; n <= $1; n++)); do
    out+=" b$n"
  done
  printf '%s start coin\n' "$out"
}

# buttons_pad_label COMANDO TIPO: o nome do comando no joypad, com o do
# controle entre parenteses quando o tipo e conhecido ("SOUTH (A)").
buttons_pad_label() {
  local glyph=${PAD_GLYPHS[$2:$1]:-}
  printf '%s%s\n' "${PAD_LABELS[$1]:-$1}" "${glyph:+ ($glyph)}"
}

# buttons_panel_count imprime quantos botoes o painel mapeado tem (o maior
# botao de um jogador arcade do mapa); 6 sem mapa.
buttons_panel_count() {
  local n
  n=$(awk '$2 == "kind" && $4 == "pad" { pad[$1] = 1 }
    $2 ~ /^b[1-8]$/ { b[$1] = (substr($2, 2) + 0 > b[$1] ? substr($2, 2) + 0 : b[$1]) }
    END { for (p in b) if (!(p in pad) && b[p] > max) max = b[p]; print max + 0 }' "$BUTTONS_MAP" 2> /dev/null)
  [[ $n =~ ^[1-8]$ ]] || n=6
  printf '%s\n' "$n"
}

# buttons_next_player: o primeiro jogador que nenhum controle fixo do mapa usa
# (o que um controle Bluetooth tomaria agora).
buttons_next_player() {
  awk '$2 == "bt" { auto[$1] = 1 } $1 ~ /^[0-9]+$/ { used[$1] = 1 }
    END { for (p = 1; p <= 8; p++) if (!(p in used) || (p in auto)) { print p; exit } }' "$BUTTONS_MAP" 2> /dev/null |
    grep . || echo 1
}

# buttons_list: os controles ligados, "INDICE|GUID|NOME|usb ou
# bluetooth|JOGADOR" (fliperos-buttons list; o jogador do mapa agora).
buttons_list() {
  "$BUTTONS" list "$BUTTONS_MAP" 2>> "$FLIPEROS_LOG"
}

# buttons_store NOVO JOGADOR INDICE GUID poe no mapa o controle recem-pego
# (linhas "JOGADOR CONTROLE INDICE ELEMENTO NOME" em NOVO). Num controle
# Bluetooth (JOGADOR bt) vira o perfil do aparelho em BUTTONS_BT_MAP, pelo
# GUID: o jogador dele e a ordem de conexao (fliperos-buttons save). Num
# fixo, sai o que o mapa tinha desse jogador e desse controle; o outro
# controle que era desse jogador fica com o numero antigo deste (troca), ou
# sai do mapa se este nao tinha numero. Os Bluetooth do mapa saem tambem: o
# save os poe de novo.
buttons_store() {
  local new=$1 player=$2 index=$3 guid=$4 old
  if [[ $player == bt ]]; then
    {
      grep -v -i "^$guid " "$BUTTONS_BT_MAP" 2> /dev/null
      awk -v g="$guid" '{ name = ""; for (i = 5; i <= NF; i++) name = name (i > 5 ? " " : "") $i
        print tolower(g), $2, $4, name }' "$new"
    } > "$BUTTONS_BT_MAP.new" && mv "$BUTTONS_BT_MAP.new" "$BUTTONS_BT_MAP"
    log_info "botoes: perfil Bluetooth $guid gravado"
    return 0
  fi
  # O numero que este controle tinha (o jogador fixo com ele).
  old=$(awk -v i="$index" '$2 == "bt" { auto[$1] = 1 } $3 == i && !($1 in auto) { print $1; exit }' \
    "$BUTTONS_MAP" 2> /dev/null)
  {
    awk -v p="$player" -v i="$index" -v o="$old" '
      FNR == NR { if ($2 == "bt") auto[$1] = 1; else if ($3 == i) mine[$1] = 1; next }
      ($1 in auto) || ($1 in mine) { next }
      $1 == p { if (o == "" || o == p) next; $1 = o }
      { print }' "$BUTTONS_MAP" "$BUTTONS_MAP" 2> /dev/null
    awk -v p="$player" '{ $1 = p; print }' "$new"
  } > "$BUTTONS_MAP.new"
  mv "$BUTTONS_MAP.new" "$BUTTONS_MAP"
  log_info "botoes: controle $index no jogador $player${old:+ (era o $old)}"
}

# buttons_capture SEGUNDOS [SEGURAR [CONTROLE]] espera o proximo comando de
# qualquer controle (ou so do CONTROLE, o indice do SDL) e imprime "INDICE
# ELEMENTO NOME". Status 1: o tempo acabou (pular); 2: segurado SEGURAR
# segundos (pular, o "hold to skip" do Batocera); 3: o Esc da tela
# (BUTTONS_CANCEL, o arquivo que a interface grafica cria), cancelar.
BUTTONS_CANCEL=${BUTTONS_CANCEL:-${UI_GUI_DIR:-/run/fliperos/gui}/cancel}
buttons_capture() {
  local -a extra=()
  [[ -n ${2:-} ]] && extra+=(--hold "$2")
  [[ -n ${3:-} ]] && extra+=(--device "$3")
  "$BUTTONS" capture --timeout "$1" --cancel "$BUTTONS_CANCEL" "${extra[@]}" 2>> "$FLIPEROS_LOG"
}

# buttons_identify INDICE: o controle como o SDL o conhece (name=, type=,
# known=, linhas "bind CONTROLE ELEMENTO"; fliperos-buttons identify).
buttons_identify() {
  "$BUTTONS" identify "$1" 2>> "$FLIPEROS_LOG"
}

# buttons_used MAPA INDICE ELEMENTO imprime "NOME JOGADOR" do comando que ja
# tem esse elemento do controle no mapa; nada se ele esta livre.
buttons_used() {
  local p control kind label
  read -r p control kind < <(awk -v i="$2" -v e="$3" '
    $2 == "kind" { kind[$1] = $4; next }
    $3 == i && $4 == e && !found { found = $1 " " $2 }
    END { if (found != "") { split(found, f, " "); print f[1], f[2], (f[1] in kind ? kind[f[1]] : "arcade") } }' \
    "$1" 2> /dev/null) || return 0
  [[ -n $p ]] || return 0
  label=${BUTTON_LABELS[$control]:-$control}
  [[ $kind == pad || -z ${BUTTON_LABELS[$control]:-} ]] && label=${PAD_LABELS[$control]:-$control}
  printf '%s %s\n' "$label" "$p"
}

# buttons_save MAPA grava os botoes no RetroArch e no GroovyMAME: o ctrlr
# fliperos e o joystickprovider sdljoy, em que o MAME numera os botoes como o
# SDL, na ordem do aparelho.
buttons_save() {
  FLIPEROS_BUTTONS_MAP=$BUTTONS_MAP FLIPEROS_BUTTONS_BT_MAP=$BUTTONS_BT_MAP \
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
# Os controles Bluetooth, pelo aparelho (fliperos-buttons: o jogador e a
# ordem de conexao).
BUTTONS_BT_MAP=${BUTTONS_BT_MAP:-$FLIPEROS_ETC/buttons-bt.map}
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

# A cor da luz dos controles (config/fliperos-padcolor): padcolor= no
# fliperos.conf, RRGGBB ou "off" (a luz fica como o controle a acende).
PADCOLOR=${PADCOLOR:-/opt/fliperos/bin/fliperos-padcolor}
PADCOLOR_DEFAULT=bd93f9

# padcolor_table: nome|Rotulo|RRGGBB, as cores do Dracula (o tema do FliperOS).
padcolor_table() {
  printf '%s\n' \
    "purple|Purple (FliperOS)|bd93f9" \
    "pink|Pink|ff79c6" \
    "red|Red|ff5555" \
    "orange|Orange|ffb86c" \
    "yellow|Yellow|f1fa8c" \
    "green|Green|50fa7b" \
    "cyan|Cyan|8be9fd" \
    "white|White|ffffff"
}

# padcolor_get: o valor de agora (RRGGBB em minusculas, ou off).
padcolor_get() {
  local color
  color=$(conf_get padcolor 2> /dev/null)
  color=${color,,}
  [[ $color == off || $color =~ ^[0-9a-f]{6}$ ]] || color=$PADCOLOR_DEFAULT
  echo "$color"
}

# padcolor_name: o rotulo da cor de agora (o da tabela, ou #RRGGBB, ou Off).
padcolor_name() {
  local color name label hex
  color=$(padcolor_get)
  [[ $color == off ]] && { echo Off; return 0; }
  while IFS='|' read -r name label hex; do
    [[ $hex == "$color" ]] && { echo "$label"; return 0; }
  done < <(padcolor_table)
  echo "#$color"
}

# padcolor_status: a linha do topo da tela da cor, pelo que esta ligado agora
# (fliperos-padcolor list): quais controles mudam, o 8BitDo que esta so no
# Bluetooth (muda pelo cabo uma vez) ou nenhum.
padcolor_status() {
  local kind name
  local -a lit=() bt=()
  [[ -x $PADCOLOR ]] && while read -r kind name; do
    case $kind in
      led | 8bitdo) lit+=("$name") ;;
      bluetooth) bt+=("$name") ;;
    esac
  done < <("$PADCOLOR" list 2> /dev/null)
  if ((${#lit[@]})); then
    printf 'Changes now: %s.' "$(IFS=,; echo "${lit[*]}" | sed 's/,/, /g')"
    ((${#bt[@]})) && printf ' %s on Bluetooth: plug it in by USB cable once to save the colour in it.' "${bt[0]}"
  elif ((${#bt[@]})); then
    printf '%s is on Bluetooth: plug it in by USB cable once and the colour is saved in it.' "${bt[0]}"
  else
    printf 'No controller connected has a light FliperOS can change. It works on DualSense, DualShock 4 and 8BitDo Ultimate 2 (by cable once).'
  fi
  echo
}

# padcolor_set COR: grava (RRGGBB, #RRGGBB ou off) e acende os controles
# ligados agora; os que conectarem depois pegam a cor pela regra do udev.
padcolor_set() {
  local color=${1#\#}
  color=${color,,}
  [[ $color == off || $color =~ ^[0-9a-f]{6}$ ]] || return 2
  if [[ $color == "$PADCOLOR_DEFAULT" ]]; then
    conf_unset padcolor
  else
    conf_set padcolor "$color"
  fi
  [[ $color != off && -x $PADCOLOR ]] && FLIPEROS_PADCOLOR=$color "$PADCOLOR" all > /dev/null 2>&1
  log_info "Controller light: $color"
  return 0
}
