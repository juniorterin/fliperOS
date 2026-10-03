# shellcheck shell=bash
# MAME ROM Cleaner (Setup): de uma pasta com um romset do MAME, move para a
# pasta do MAME os jogos que passam nos filtros (com o pai, a BIOS e os
# dispositivos de que precisam) e depois pergunta se apaga o que sobrou na
# origem. Os filtros seguem o MAME Smart ROM Sorter; a logica e o
# config/fliperos-romclean, pelo XML da versao do MAME do romset.

ROMCLEAN=${ROMCLEAN:-/opt/fliperos/bin/fliperos-romclean}
# O XML do MAME 2010 (0.139), do core mame2010 do RetroArch (o build e o
# cabinet-update.sh o baixam: fliperos-romclean fetch-mame2010).
MAME2010_XML=${MAME2010_XML:-/usr/local/share/fliperos/mame2010.xml.xz}
ROMS_ROOT=${ROMS_ROOT:-/home/fliperos/roms}
GROOVYMAME=${GROOVYMAME:-groovymame}

# Os filtros, na ordem da tela: chave e valores, o primeiro e o do preset
# "custom" ao comecar. players e buttons: 0 = qualquer.
ROMCLEAN_KEYS=(arcade status orientation players buttons controls clones betas years psx vector chd)
declare -A ROMCLEAN_VALUES=(
  [arcade]="yes no"
  [status]="imperfect working all"
  [orientation]="any horizontal vertical"
  [players]="2 1 4 0"
  [buttons]="6 4 3 2 8 0"
  [controls]="joystick joystick,trackball,spinner joystick,lightgun joystick,spinner,pedal,analog any"
  [clones]="1g1r keep none"
  [betas]="no yes"
  [years]="any 1970-1979 1980-1989 1990-1999 2000-2099 1980-1999"
  [psx]="no only"
  [vector]="yes no"
  [chd]="yes no"
)

# romclean_preset NOME imprime os filtros do preset (chave=valor por linha):
# cabinet (painel de joystick, 2 jogadores e 6 botoes, uma versao por jogo),
# working (tudo o que funciona) e psx (so a placa do PlayStation, como o
# romset do MAME 2010 que roda o 3D bem).
romclean_preset() {
  local key
  declare -A v=()
  for key in "${ROMCLEAN_KEYS[@]}"; do
    v[$key]=${ROMCLEAN_VALUES[$key]%% *}
  done
  case $1 in
    cabinet) ;;
    working) v[status]=working v[players]=0 v[buttons]=0 v[controls]=any v[clones]=keep ;;
    psx) v[players]=0 v[buttons]=0 v[controls]=any v[psx]=only ;;
    *) return 1 ;;
  esac
  for key in "${ROMCLEAN_KEYS[@]}"; do
    printf '%s=%s\n' "$key" "${v[$key]}"
  done
}

# romclean_next CHAVE VALOR imprime o valor seguinte da chave (volta ao
# primeiro depois do ultimo).
romclean_next() {
  local -a list
  local i
  read -r -a list <<< "${ROMCLEAN_VALUES[$1]}"
  for i in "${!list[@]}"; do
    if [[ ${list[i]} == "$2" ]]; then
      printf '%s\n' "${list[(i + 1) % ${#list[@]}]}"
      return 0
    fi
  done
  printf '%s\n' "${list[0]}"
}

# romclean_label CHAVE VALOR imprime o item da tela ("Players: up to 2").
romclean_label() {
  local v=$2
  case $1 in
    arcade) [[ $v == yes ]] && v="arcade only (no consoles, computers)" || v="everything" ;;
    status)
      case $v in
        imperfect) v="working and imperfect" ;;
        working) v="working only" ;;
        *) v="all, even not working" ;;
      esac
      ;;
    orientation) [[ $v == any ]] && v="horizontal and vertical" ;;
    players | buttons) [[ $v == 0 ]] && v="any" || v="up to $v" ;;
    controls)
      case $v in
        joystick) v="joystick and buttons" ;;
        joystick,trackball,spinner) v="joystick, trackball, spinner" ;;
        joystick,lightgun) v="joystick and light gun" ;;
        joystick,spinner,pedal,analog) v="joystick, wheel and pedals" ;;
      esac
      ;;
    clones)
      case $v in
        1g1r) v="best version of each game" ;;
        keep) v="keep all" ;;
        *) v="parents only" ;;
      esac
      ;;
    betas) [[ $v == no ]] && v="remove" || v="keep" ;;
    years) [[ $v == any ]] && v="all" ;;
    psx) [[ $v == only ]] && v="only those" || v="any hardware" ;;
    vector | chd) [[ $v == yes ]] && v="keep" || v="remove" ;;
  esac
  case $1 in
    arcade) printf 'Games: %s\n' "$v" ;;
    status) printf 'Emulation: %s\n' "$v" ;;
    orientation) printf 'Screen: %s\n' "$v" ;;
    players) printf 'Players: %s\n' "$v" ;;
    buttons) printf 'Buttons: %s\n' "$v" ;;
    controls) printf 'Controls: %s\n' "$v" ;;
    clones) printf 'Clones: %s\n' "$v" ;;
    betas) printf 'Bootlegs, prototypes: %s\n' "$v" ;;
    years) printf 'Years: %s\n' "$v" ;;
    psx) printf 'PlayStation-based hardware: %s\n' "$v" ;;
    vector) printf 'Vector games: %s\n' "$v" ;;
    chd) printf 'Games that need a CHD: %s\n' "$v" ;;
  esac
}

# romclean_args CHAVE=VALOR... imprime as opcoes do fliperos-romclean, uma
# por linha (para o mapfile).
romclean_args() {
  local kv key value
  for kv in "$@"; do
    key=${kv%%=*} value=${kv#*=}
    case $key in
      arcade) [[ $value == yes ]] && echo --arcade-only ;;
      status) printf '%s\n' --status "$value" ;;
      orientation) printf '%s\n' --orientation "$value" ;;
      players) printf '%s\n' --max-players "$value" ;;
      buttons) printf '%s\n' --max-buttons "$value" ;;
      controls) printf '%s\n' --controls "$value" ;;
      clones) printf '%s\n' --clones "$value" ;;
      betas) [[ $value == no ]] && printf '%s\n' --no-bootlegs --no-prototypes ;;
      years) [[ $value != any ]] && printf '%s\n' --years "$value" ;;
      psx) [[ $value == only ]] && printf '%s\n' --only psx ;;
      vector | chd) [[ $value == no ]] && printf '%s\n' --exclude "$key" ;;
    esac
  done
  return 0
}

# romclean_default_source PASTA imprime o XML provavel do romset: o do MAME
# 2010 numa pasta que tem "2010" no nome, senao o do GroovyMAME instalado.
romclean_default_source() {
  if [[ ${1,,} == *2010* && -f $MAME2010_XML ]]; then
    echo mame2010
  else
    echo groovymame
  fi
}

# romclean_default_dest FONTE imprime a pasta do MAME daquele romset: a do
# core mame2010 do RetroArch para o MAME 2010, senao ~/roms/mame.
romclean_default_dest() {
  if [[ $1 == mame2010 && -d $ROMS_ROOT/retroarch/mame2010 ]]; then
    printf '%s\n' "$ROMS_ROOT/retroarch/mame2010"
  else
    printf '%s\n' "$ROMS_ROOT/mame"
  fi
}

# romclean_flycast_mode DESTINO: os sets arcade do Flycast (Naomi,
# Atomiswave) ficam na pasta do MAME; indo para ela, vao junto (move), senao
# ficam onde estao (keep). Apagados, nunca.
romclean_flycast_mode() {
  if [[ $(realpath -m -- "$1") == "$(realpath -m -- "$ROMS_ROOT/mame")" ]]; then
    echo move
  else
    echo keep
  fi
}

# romclean_source_label FONTE imprime o nome da fonte do XML para a tela.
romclean_source_label() {
  case $1 in
    groovymame) echo "GroovyMAME $(groovymame_version)" ;;
    mame2010) echo "MAME 2010 (0.139)" ;;
    *) echo "$1" ;;
  esac
}

# groovymame_version imprime a versao do GroovyMAME instalado (0.289).
groovymame_version() {
  "$GROOVYMAME" -version 2> /dev/null | awk 'NR == 1 { print $1; exit }'
}

# romclean_scan ORIGEM FONTE DESTINO PLANO OPCAO... le o XML (groovymame = o
# -listxml do GroovyMAME, mame2010 = o do core, ou um arquivo) e escreve o
# plano; imprime o resumo do fliperos-romclean (chave=valor).
romclean_scan() {
  local folder=$1 source=$2 dest=$3 plan=$4 xml=$2
  shift 4
  case $source in
    groovymame)
      "$GROOVYMAME" -listxml 2> /dev/null |
        "$ROMCLEAN" scan --xml - --roms "$folder" --dest "$dest" --plan "$plan" "$@"
      return
      ;;
    mame2010) xml=$MAME2010_XML ;;
  esac
  "$ROMCLEAN" scan --xml "$xml" --roms "$folder" --dest "$dest" --plan "$plan" "$@"
}

# romclean_value RESUMO CHAVE imprime um valor do resumo do scan.
romclean_value() {
  sed -n "s/^$2=//p" <<< "$1" | tail -1
}

# romclean_list PLANO move|rest imprime os sets daquela parte do plano, um
# por linha: nome e titulo (cortado, para caber em 80 colunas e a lista no
# limite do ui_pager).
romclean_list() {
  awk -F'\t' -v k="$2" '$1 == k && !seen[$2]++ { printf "%-16s %s\n", $2, substr($5, 1, 58) }' "$1"
}

# romclean_apply PLANO move|delete-rest: move o que passou para a pasta do
# MAME, ou apaga o que sobrou na origem.
romclean_apply() {
  log_info "ROM cleaner: $2 ($(sed -n 's/^# roms\t//p' "$1") -> $(sed -n 's/^# dest\t//p' "$1"))"
  "$ROMCLEAN" apply "$1" "$2"
}

# human_bytes N imprime o tamanho legivel (1.2 GB).
human_bytes() {
  awk -v b="$1" 'BEGIN { split("B KB MB GB TB", u); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf (i == 1 ? "%d %s\n" : "%.1f %s\n"), b, u[i] }'
}
