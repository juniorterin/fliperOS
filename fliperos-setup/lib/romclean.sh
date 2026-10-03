# shellcheck shell=bash
# MAME ROM Cleaner (Setup): de uma pasta com um romset do MAME (no disco, num
# pendrive ou numa pasta da rede), copia ou move para a pasta do emulador os
# jogos que passam nos filtros, com o pai, a BIOS e os dispositivos de que
# precisam. Funciona como o ROMLister: os filtros vem do XML da versao do
# MAME do romset mais o catver.ini, o nplayers.ini e o controls.xml. A logica
# e o config/fliperos-romclean; aqui ficam os parametros da tela (cada um com
# as opcoes de escolher uma, "radio", ou de marcar varias, "check"), os
# presets e os destinos de cada emulador.

ROMCLEAN=${ROMCLEAN:-/opt/fliperos/bin/fliperos-romclean}
# O XML do MAME 2010 (0.139), do core mame2010 do RetroArch (o build e o
# cabinet-update.sh o baixam: fliperos-romclean fetch-mame2010).
MAME2010_XML=${MAME2010_XML:-/usr/local/share/fliperos/mame2010.xml.xz}
ROMS_ROOT=${ROMS_ROOT:-/home/fliperos/roms}
BIOS_ROOT=${BIOS_ROOT:-/home/fliperos/bios}
GROOVYMAME=${GROOVYMAME:-groovymame}
# catver.ini, nplayers.ini e controls.xml: junto do romset (a pasta dele, a
# de cima ou a subpasta folders) ou nesta pasta do sistema.
ROMCLEAN_DATA=${ROMCLEAN_DATA:-/usr/local/share/fliperos/romclean}
# O que o fliperos-romclean leu do XML (um minuto com o do GroovyMAME).
ROMCLEAN_CACHE=${ROMCLEAN_CACHE:-/var/cache/fliperos}

# Os filtros, na ordem da tela. "transfer" (copiar ou mover) tambem e um
# parametro da tela, mas nao e filtro.
ROMCLEAN_KEYS=(arcade status genres mature players modes buttons controls orientation lines clones region
  bootlegs prototypes decades vector chd hardware systems flycast)
declare -A ROMCLEAN_TYPE=(
  [arcade]=radio [status]=radio [genres]=check [mature]=radio [players]=radio [modes]=check [buttons]=radio
  [controls]=check [orientation]=check [lines]=check [clones]=radio [region]=radio [bootlegs]=radio
  [prototypes]=radio [decades]=check [vector]=radio [chd]=radio [hardware]=check [systems]=check
  [flycast]=radio [transfer]=radio
)
declare -A ROMCLEAN_TITLE=(
  [arcade]="Games" [status]="Emulation" [genres]="Categories" [mature]="Adult games" [players]="Players"
  [modes]="Play mode" [buttons]="Buttons" [controls]="Controls" [orientation]="Screen" [lines]="Resolution"
  [clones]="Clones" [region]="Region" [bootlegs]="Bootlegs and hacks" [prototypes]="Prototypes"
  [decades]="Years" [vector]="Vector games" [chd]="Games with CHD" [hardware]="Hardware" [systems]="Systems"
  [flycast]="Naomi and Atomiswave" [transfer]="Transfer"
)
# O que cada parametro pergunta (o texto da tela de escolha).
# Uma linha cada: numa tela de 240 linhas sobra pouco para a lista.
declare -A ROMCLEAN_HELP=(
  [arcade]="Which machines of the romset?"
  [status]="How well MAME must emulate the game."
  [genres]="Mark the categories to take (catver.ini)."
  [mature]="Games marked Mature in catver.ini."
  [players]="The most players a game may have."
  [modes]="Mark how two or more play (nplayers.ini)."
  [buttons]="The most buttons a game may use per player."
  [controls]="Mark what the panel has. Button-only games always pass."
  [orientation]="Mark the screen orientations to take."
  [lines]="Mark the resolutions. Only Low is progressive on a 15 kHz CRT."
  [clones]="Which versions of each game?"
  [region]="With one version per game, the region that wins."
  [bootlegs]="Bootlegs and hacks."
  [prototypes]="Prototypes, betas and location tests."
  [decades]="Mark the decades to take."
  [vector]="Vector games (Asteroids, Tempest...)."
  [chd]="Games that need a CHD (a disk image)."
  [hardware]="Mark to take only these boards. None marked: any board."
  [systems]="Mark the Flycast systems to take."
  [flycast]="They run better in Flycast (choose it as the emulator)."
  [transfer]="Move takes the files out of the romset."
)

# Os generos do catver.ini ("nome|nome (quantos)") e os que comecam marcados,
# e os arquivos de dados achados (romclean_data_load).
ROMCLEAN_GENRES=()
ROMCLEAN_GENRES_DEFAULT=""
ROMCLEAN_CATVER="" ROMCLEAN_NPLAYERS="" ROMCLEAN_CONTROLS=""
ROMCLEAN_DATA_LABEL=""

# romclean_options CHAVE imprime as opcoes do parametro, "valor|rotulo" por
# linha.
romclean_options() {
  case $1 in
    arcade)
      printf '%s\n' "yes|Arcade machines only (coin-operated)" \
        "no|Everything in the romset (consoles, computers...)"
      ;;
    status) printf '%s\n' "working|Working only" "imperfect|Working and imperfect" "all|All (even not working)" ;;
    genres) ((${#ROMCLEAN_GENRES[@]})) && printf '%s\n' "${ROMCLEAN_GENRES[@]}" ;;
    mature | bootlegs | prototypes) printf '%s\n' "no|Remove" "yes|Keep" ;;
    players) printf '%s\n' "0|Any" "1|Up to 1" "2|Up to 2" "3|Up to 3" "4|Up to 4" "6|Up to 6" "8|Up to 8" ;;
    modes)
      printf '%s\n' "single|1 player only" "alt|2 or more (taking turns)" "sim|2 or more (at the same time)" \
        "unknown|Unknown (not in nplayers.ini)"
      ;;
    buttons)
      printf '%s\n' "0|Any" "1|Up to 1" "2|Up to 2" "3|Up to 3" "4|Up to 4" "5|Up to 5" "6|Up to 6" "8|Up to 8"
      ;;
    controls)
      printf '%s\n' "joy8|8-way joystick" "joy4|4-way joystick" "joy2|2-way joystick" \
        "twin|Twin sticks (two per player)" "trackball|Trackball" "spinner|Spinner (dial, 360 wheel)" \
        "paddle|Paddle (270 wheel)" "positional|Rotary joystick" "analog|Analog stick (yoke, flight stick)" \
        "pedal|Pedals" "lightgun|Light gun" "keyboard|Keyboard (keypad)" "mahjong|Mahjong (hanafuda, gambling panel)"
      ;;
    orientation) printf '%s\n' "horizontal|Horizontal" "vertical|Vertical" ;;
    lines)
      printf '%s\n' "15|Low (up to 288 lines: 15 kHz)" "25|Medium (about 384 lines: 25 kHz)" \
        "31|High (480 lines or more)"
      ;;
    clones) printf '%s\n' "1g1r|Best version of each game" "none|Parents only" "keep|All versions" ;;
    region)
      printf '%s\n' "world|World (then USA, Europe... Japan last)" "usa|USA" "europe|Europe" "japan|Japan" \
        "brazil|Brazil"
      ;;
    decades) printf '%s\n' "1970|1970s" "1980|1980s" "1990|1990s" "2000|2000s" "2010|2010s" "2020|2020s" ;;
    vector) printf '%s\n' "yes|Keep" "no|Remove" ;;
    chd) printf '%s\n' "yes|Keep" "no|Remove" "only|Only those" ;;
    hardware)
      printf '%s\n' "neogeo|Neo-Geo" "cps1|Capcom CPS-1" "cps2|Capcom CPS-2" "cps3|Capcom CPS-3" \
        "psx|PlayStation-based (ZN, System 11 and 12...)" "midway|Midway T/W/X/Y-unit (Mortal Kombat)"
      ;;
    systems) printf '%s\n' "naomi|Naomi" "naomi2|Naomi 2" "atomiswave|Atomiswave" ;;
    flycast) printf '%s\n' "no|Leave them to Flycast" "yes|Take them for this emulator too" ;;
    transfer) printf '%s\n' "copy|Copy (the romset stays as it is)" "move|Move (out of the romset)" ;;
    *) return 1 ;;
  esac
}

# romclean_all CHAVE imprime todos os valores do parametro, separados por
# virgula.
romclean_all() {
  romclean_options "$1" | cut -d'|' -f1 | paste -sd, -
}

# romclean_is_all CHAVE VALOR: todas as opcoes estao marcadas?
romclean_is_all() {
  local n have
  n=$(romclean_options "$1" | wc -l)
  have=$(tr ',' '\n' <<< "$2" | grep -c .)
  ((n > 0 && have >= n))
}

# romclean_visible CHAVE ALVO: o parametro aparece para este emulador? Os que
# dependem de um arquivo de dados so aparecem com ele.
romclean_visible() {
  case $1 in
    genres | mature) [[ -n $ROMCLEAN_CATVER ]] ;;
    modes) [[ -n $ROMCLEAN_NPLAYERS ]] ;;
    systems) [[ $2 == flycast ]] ;;
    flycast | hardware) [[ $2 != flycast ]] ;;
    *) return 0 ;;
  esac
}

# romclean_preset NOME [ALVO] imprime os parametros do preset (chave=valor
# por linha): cabinet (painel de joystick, 2 jogadores e 6 botoes, uma versao
# por jogo), working (tudo o que funciona), psx (so a placa do PlayStation,
# como o romset do MAME 2010 que roda o 3D bem) e all (sem filtro). No
# Flycast a emulacao que conta e a dele: o status do MAME nao filtra.
romclean_preset() {
  local key
  declare -A v=(
    [arcade]=yes [status]=imperfect [genres]="$ROMCLEAN_GENRES_DEFAULT" [mature]=no [players]=2
    [modes]="$(romclean_all modes)" [buttons]=6 [controls]=joy8,joy4,joy2,twin
    [orientation]="$(romclean_all orientation)" [lines]="$(romclean_all lines)" [clones]=1g1r [region]=world
    [bootlegs]=no [prototypes]=no [decades]="$(romclean_all decades)" [vector]=yes [chd]=yes [hardware]=""
    [systems]="$(romclean_all systems)" [flycast]=no
  )
  case $1 in
    cabinet) ;;
    working)
      v[status]=working v[players]=0 v[buttons]=0 v[controls]=$(romclean_all controls) v[clones]=keep
      v[mature]=yes v[genres]=$(romclean_all genres) v[bootlegs]=yes v[prototypes]=yes
      ;;
    psx) v[players]=0 v[buttons]=0 v[controls]=$(romclean_all controls) v[hardware]=psx ;;
    all)
      v[arcade]=no v[status]=all v[players]=0 v[buttons]=0 v[controls]=$(romclean_all controls) v[clones]=keep
      v[mature]=yes v[genres]=$(romclean_all genres) v[bootlegs]=yes v[prototypes]=yes
      ;;
    *) return 1 ;;
  esac
  if [[ ${2:-} == flycast ]]; then
    v[status]=all v[hardware]=""
  fi
  for key in "${ROMCLEAN_KEYS[@]}"; do
    printf '%s=%s\n' "$key" "${v[$key]}"
  done
}

romclean_preset_label() {
  case $1 in
    cabinet) echo "Joystick cabinet (2 players, 6 buttons)" ;;
    working) echo "Everything that works" ;;
    psx) echo "PlayStation-based hardware (Tekken 3...)" ;;
    all) echo "Everything (no filter)" ;;
    *) echo "Custom" ;;
  esac
}

# romclean_summary CHAVE VALOR imprime a escolha do parametro em poucas
# palavras: o rotulo da opcao (sem o parentese) ou, numa lista de marcar, os
# rotulos marcados, "all", ou "N of M" quando nao cabem.
romclean_summary() {
  local key=$1 value=$2 v label out="" n=0 total=0
  local -A labels=()
  local -a picked
  while IFS='|' read -r v label; do
    labels[$v]=${label%% (*}
    total=$((total + 1))
  done < <(romclean_options "$key")
  if [[ ${ROMCLEAN_TYPE[$key]} == radio ]]; then
    printf '%s\n' "${labels[$value]:-$value}"
    return 0
  fi
  IFS=, read -r -a picked <<< "$value"
  for v in "${picked[@]}"; do
    [[ -n ${labels[$v]:-} ]] || continue
    out+="${out:+, }${labels[$v]}"
    n=$((n + 1))
  done
  if ((n == 0)); then
    case $key in
      controls) echo "buttons only" ;;
      hardware) echo "any" ;;
      *) echo "all" ;;
    esac
  elif ((n == total)); then
    echo "all"
  elif ((${#out} > 60)); then
    echo "$n of $total"
  else
    printf '%s\n' "$out"
  fi
}

# romclean_label CHAVE VALOR imprime o item da tela ("Players: Up to 2").
romclean_label() {
  printf '%s: %s\n' "${ROMCLEAN_TITLE[$1]}" "$(romclean_summary "$1" "$2")"
}

# romclean_regions ESCOLHA imprime a ordem das regioes do 1g1r.
romclean_regions() {
  case $1 in
    usa) echo "USA,World,Europe,Brazil,Hispanic,Oceania,Asia,Japan,Unknown" ;;
    europe) echo "Europe,World,USA,Brazil,Hispanic,Oceania,Asia,Japan,Unknown" ;;
    japan) echo "Japan,World,USA,Europe,Asia,Brazil,Hispanic,Oceania,Unknown" ;;
    brazil) echo "Brazil,World,USA,Europe,Hispanic,Oceania,Asia,Japan,Unknown" ;;
    *) echo "World,USA,Europe,Brazil,Hispanic,Oceania,Asia,Japan,Unknown" ;;
  esac
}

# romclean_args ALVO CHAVE=VALOR... imprime os filtros como opcoes do
# fliperos-romclean, uma por linha (para o mapfile). Numa lista de marcar,
# todas marcadas (ou nenhuma) e nao filtrar; nos controles, nenhuma e "so
# botoes".
romclean_args() {
  local target=$1 kv key value
  shift
  for kv in "$@"; do
    key=${kv%%=*} value=${kv#*=}
    romclean_visible "$key" "$target" || continue
    if [[ ${ROMCLEAN_TYPE[$key]:-} == check && ! $key =~ ^(controls|hardware|systems)$ ]] &&
      { [[ -z $value ]] || romclean_is_all "$key" "$value"; }; then
      continue
    fi
    case $key in
      arcade) [[ $value == yes ]] && echo --arcade-only ;;
      status) printf '%s\n' --status "$value" ;;
      genres) printf '%s\n' --categories "$value" ;;
      mature) [[ $value == no ]] && echo --no-mature ;;
      players) printf '%s\n' --max-players "$value" ;;
      modes) printf '%s\n' --play-modes "$value" ;;
      buttons) printf '%s\n' --max-buttons "$value" ;;
      controls)
        if romclean_is_all controls "$value"; then
          printf '%s\n' --controls any
        else
          printf '%s\n' --controls "$value"
        fi
        ;;
      orientation) printf '%s\n' --orientation "$value" ;;
      lines) printf '%s\n' --scan-rates "$value" ;;
      clones) printf '%s\n' --clones "$value" ;;
      region) printf '%s\n' --regions "$(romclean_regions "$value")" ;;
      bootlegs) [[ $value == no ]] && echo --no-bootlegs ;;
      prototypes) [[ $value == no ]] && echo --no-prototypes ;;
      decades) printf '%s\n' --decades "$value" ;;
      vector) [[ $value == no ]] && printf '%s\n' --exclude vector ;;
      chd)
        [[ $value == no ]] && printf '%s\n' --exclude chd
        [[ $value == only ]] && printf '%s\n' --only chd
        ;;
      hardware) [[ -n $value ]] && printf '%s\n' --hardware "$value" ;;
      # No Flycast so entram os sistemas dele: nenhum marcado vale todos.
      systems) printf '%s\n' --systems "${value:-$(romclean_all systems)}" ;;
      flycast) [[ $value == no ]] && printf '%s\n' --exclude flycast ;;
    esac
  done
  return 0
}

# ── Arquivos de dados ─────────────────────────────────────────────

# romclean_data_find NOME PASTA imprime o arquivo (sem diferenciar maiusculas)
# achado na pasta do romset, na de cima, na subpasta folders (onde a
# interface do MAME os guarda) ou na pasta do sistema.
romclean_data_find() {
  local name=$1 folder=$2 dir file
  local -a dirs=("$folder" "$(dirname -- "$folder")" "$folder/folders" "$ROMCLEAN_DATA")
  # Primeiro pelo nome exato: listar a pasta do romset (dezenas de milhares
  # de arquivos, talvez pela rede) so se for preciso.
  for dir in "${dirs[@]}"; do
    if [[ -f $dir/$name ]]; then
      printf '%s\n' "$dir/$name"
      return 0
    fi
  done
  for dir in "${dirs[@]}"; do
    [[ -d $dir ]] || continue
    file=$(find "$dir" -maxdepth 1 -type f -iname "$name" 2> /dev/null | head -1)
    if [[ -n $file ]]; then
      printf '%s\n' "$file"
      return 0
    fi
  done
  return 1
}

# romclean_data_load PASTA procura os tres arquivos e le o que eles oferecem
# a tela: os generos do catver.ini (ROMCLEAN_GENRES, os marcados em
# ROMCLEAN_GENRES_DEFAULT) e a versao de cada um (ROMCLEAN_DATA_LABEL).
romclean_data_load() {
  local folder=$1 kind a b c args=() found=() missing=()
  ROMCLEAN_CATVER=$(romclean_data_find catver.ini "$folder") || ROMCLEAN_CATVER=""
  ROMCLEAN_NPLAYERS=$(romclean_data_find nplayers.ini "$folder") || ROMCLEAN_NPLAYERS=""
  ROMCLEAN_CONTROLS=$(romclean_data_find controls.xml "$folder") || ROMCLEAN_CONTROLS=""
  ROMCLEAN_GENRES=() ROMCLEAN_GENRES_DEFAULT="" ROMCLEAN_DATA_LABEL=""
  mapfile -t args < <(romclean_data_args)
  [[ -n $ROMCLEAN_CATVER ]] || missing+=("catver.ini")
  [[ -n $ROMCLEAN_NPLAYERS ]] || missing+=("nplayers.ini")
  [[ -n $ROMCLEAN_CONTROLS ]] || missing+=("controls.xml")
  if ((${#args[@]})); then
    while IFS=$'\t' read -r kind a b c; do
      case $kind in
        "# catver") found+=("catver.ini $a") ;;
        "# nplayers") found+=("nplayers.ini $a") ;;
        "# controls") found+=("controls.xml $a") ;;
        genre)
          ROMCLEAN_GENRES+=("$a|$a ($b)")
          [[ $c == 1 ]] && ROMCLEAN_GENRES_DEFAULT+="${ROMCLEAN_GENRES_DEFAULT:+,}$a"
          ;;
      esac
    done < <("$ROMCLEAN" options "${args[@]}" 2>> "$FLIPEROS_LOG")
  fi
  ROMCLEAN_DATA_LABEL=$(romclean_join "${found[@]}")
  ROMCLEAN_DATA_LABEL=${ROMCLEAN_DATA_LABEL:-none}
  ((${#missing[@]})) && ROMCLEAN_DATA_LABEL+=" (missing: $(romclean_join "${missing[@]}"))"
  return 0
}

# romclean_join ITEM... imprime os itens separados por ", ".
romclean_join() {
  local out="" item
  for item in "$@"; do
    out+="${out:+, }$item"
  done
  printf '%s\n' "$out"
}

# romclean_data_args imprime as opcoes dos arquivos de dados achados.
romclean_data_args() {
  [[ -n $ROMCLEAN_CATVER ]] && printf '%s\n' --catver "$ROMCLEAN_CATVER"
  [[ -n $ROMCLEAN_NPLAYERS ]] && printf '%s\n' --nplayers "$ROMCLEAN_NPLAYERS"
  [[ -n $ROMCLEAN_CONTROLS ]] && printf '%s\n' --controls-xml "$ROMCLEAN_CONTROLS"
  return 0
}

# ── Emuladores ────────────────────────────────────────────────────
# O alvo diz de que versao do MAME e o romset (o XML) e para onde os jogos
# vao: groovymame (o MAME deste sistema), flycast (o mesmo romset, so Naomi,
# Naomi 2 e Atomiswave, uma pasta por sistema), mame2010 (o 0.139 do core do
# RetroArch) ou file (outro XML).

# romclean_targets imprime "alvo|rotulo" dos emuladores da tela.
romclean_targets() {
  printf '%s\n' "groovymame|$(romclean_target_label groovymame)" "flycast|$(romclean_target_label flycast)"
  [[ -f $MAME2010_XML ]] && printf '%s\n' "mame2010|$(romclean_target_label mame2010)"
  printf '%s\n' "file|Another MAME version (choose the XML from mame -listxml)"
}

romclean_target_label() {
  case $1 in
    groovymame) echo "GroovyMAME $(groovymame_version)" ;;
    flycast) echo "Flycast (Naomi, Naomi 2, Atomiswave)" ;;
    mame2010) echo "MAME 2010 (0.139), the RetroArch mame2010 core" ;;
    *) echo "$1" ;;
  esac
}

# romclean_default_target PASTA imprime o emulador provavel do romset: o
# MAME 2010 numa pasta que tem "2010" no nome, o Flycast numa de Naomi ou
# Atomiswave, senao o GroovyMAME instalado.
romclean_default_target() {
  local name=${1,,}
  if [[ $name == *2010* && -f $MAME2010_XML ]]; then
    echo mame2010
  elif [[ ${name##*/} =~ naomi|atomiswave|flycast ]]; then
    echo flycast
  else
    echo groovymame
  fi
}

# romclean_default_dest ALVO imprime a pasta dos jogos daquele emulador: a do
# core mame2010 do RetroArch para o MAME 2010, ~/roms (com uma pasta por
# sistema dentro) para o Flycast, senao ~/roms/mame.
romclean_default_dest() {
  case $1 in
    flycast) printf '%s\n' "$ROMS_ROOT" ;;
    mame2010)
      if [[ -d $ROMS_ROOT/retroarch/mame2010 ]]; then
        printf '%s\n' "$ROMS_ROOT/retroarch/mame2010"
      else
        printf '%s\n' "$ROMS_ROOT/mame"
      fi
      ;;
    *) printf '%s\n' "$ROMS_ROOT/mame" ;;
  esac
}

# romclean_dest_label ALVO DESTINO imprime para onde vai cada coisa, com a
# home abreviada ("~/roms/mame (BIOS: ~/bios/mame)") para caber na tela.
romclean_dest_label() {
  local bios dest=$2 home="/home/$FLIPEROS_USER"
  bios=$(romclean_bios_dest "$1" "$2")
  [[ $1 == flycast ]] && dest+="/{naomi,naomi2,atomiswave}"
  [[ -n $bios ]] && dest+=" (BIOS: $bios)"
  printf '%s\n' "${dest//$home\//\~/}"
}

# romclean_bios_dest ALVO DESTINO imprime a pasta das BIOS e dos
# dispositivos: ~/bios/dc no Flycast (onde ele as procura) e ~/bios/mame no
# GroovyMAME quando os jogos vao para ~/roms/mame (as duas estao no rompath;
# as BIOS fora da pasta dos jogos nao viram "jogo" nos frontends). Vazio: vao
# com os jogos (o core mame2010 as quer junto, e numa pasta escolhida a mao
# o conjunto fica inteiro).
romclean_bios_dest() {
  case $1 in
    flycast) printf '%s\n' "$BIOS_ROOT/dc" ;;
    groovymame | file)
      [[ $(realpath -m -- "$2") == "$(realpath -m -- "$ROMS_ROOT/mame")" ]] && printf '%s\n' "$BIOS_ROOT/mame"
      ;;
  esac
  return 0
}

# romclean_target_args ALVO DESTINO imprime as opcoes de destino do
# fliperos-romclean, uma por linha.
romclean_target_args() {
  local target=$1 dest=$2 bios system
  bios=$(romclean_bios_dest "$target" "$dest")
  if [[ $target == flycast ]]; then
    printf '%s\n' --dest "$dest/naomi" --no-devices
    for system in naomi naomi2 atomiswave; do
      printf '%s\n' --route "$system=$dest/$system"
    done
  else
    printf '%s\n' --dest "$dest"
  fi
  [[ -n $bios ]] && printf '%s\n' --bios-dest "$bios"
  return 0
}

# groovymame_version imprime a versao do GroovyMAME instalado (0.289).
groovymame_version() {
  "$GROOVYMAME" -version 2> /dev/null | awk 'NR == 1 { print $1; exit }'
}

# romclean_scan ORIGEM ALVO XML DESTINO PLANO FILTRO... le o XML do alvo (o
# -listxml do GroovyMAME, o do core mame2010 ou o arquivo XML) e escreve o
# plano; imprime o resumo do fliperos-romclean (chave=valor).
romclean_scan() {
  local folder=$1 target=$2 xml=$3 dest=$4 plan=$5
  local -a source data where
  shift 5
  mapfile -t source < <(romclean_xml_args "$target" "$xml")
  mapfile -t data < <(romclean_data_args)
  mapfile -t where < <(romclean_target_args "$target" "$dest")
  "$ROMCLEAN" scan "${source[@]}" --roms "$folder" "${where[@]}" --plan "$plan" "${data[@]}" "$@"
}

# romclean_xml_args ALVO XML imprime as opcoes do XML do alvo, uma por linha:
# o -listxml do GroovyMAME (com o cache da versao dele), o do core mame2010
# ou o arquivo escolhido.
romclean_xml_args() {
  local version
  case $1 in
    groovymame | flycast)
      printf '%s\n' --xml-command "$GROOVYMAME -listxml"
      version=$(groovymame_version)
      [[ -n $version ]] && printf '%s\n' --cache "$ROMCLEAN_CACHE/romclean-groovymame-$version.json"
      ;;
    mame2010) printf '%s\n' --xml "$MAME2010_XML" --cache "$ROMCLEAN_CACHE/romclean-mame2010.json" ;;
    *) printf '%s\n' --xml "$2" ;;
  esac
  return 0
}

# ── CHDs ─────────────────────────────────────────────────────────
# O MAME CHD Cleaner: os CHDs costumam vir numa colecao a parte, enorme. Ele
# olha os jogos que ja estao na pasta de ROMs do emulador e copia, da pasta
# dos CHDs, so os dos jogos que usam disco (fliperos-romclean chds).

# romclean_chd_folders ALVO DESTINO imprime as pastas de ROMs do emulador
# onde os CHDs entram, uma por linha (no Flycast, as de Naomi e Naomi 2: os
# jogos de GD-ROM; o Atomiswave nao tem disco).
romclean_chd_folders() {
  case $1 in
    flycast) printf '%s\n' "$2/naomi" "$2/naomi2" ;;
    *) printf '%s\n' "$2" ;;
  esac
}

# romclean_chd_label ALVO DESTINO imprime essas pastas para a tela.
romclean_chd_label() {
  local dest=$2 home="/home/$FLIPEROS_USER"
  [[ $1 == flycast ]] && dest+="/{naomi,naomi2}"
  printf '%s\n' "${dest//$home\//\~/}"
}

# romclean_chd_scan ORIGEM ALVO XML DESTINO PLANO [--clones] le o XML do alvo
# e as pastas de ROMs e escreve o plano dos CHDs a copiar; imprime o resumo
# (games=, move=, move_bytes=, missing=, free_bytes=).
romclean_chd_scan() {
  local folder=$1 target=$2 xml=$3 dest=$4 plan=$5 dir
  local -a source where=()
  shift 5
  mapfile -t source < <(romclean_xml_args "$target" "$xml")
  while IFS= read -r dir; do
    where+=(--roms "$dir")
  done < <(romclean_chd_folders "$target" "$dest")
  "$ROMCLEAN" chds "${source[@]}" --chds "$folder" "${where[@]}" --plan "$plan" "$@"
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

# romclean_apply PLANO copy|move|delete-rest: copia ou move o que passou para
# a pasta do emulador, ou apaga o que sobrou na origem. Imprime o resultado
# (copied=, moved= ou deleted=, skipped= e errors=).
romclean_apply() {
  log_info "ROM cleaner: $2 ($(sed -n 's/^# roms\t//p' "$1") -> $(sed -n 's/^# dest\t//p' "$1"))"
  "$ROMCLEAN" apply "$1" "$2"
}

# romclean_transfer PLANO copy|move: o mesmo, falando com a tela de progresso
# por eventos (lib/progress.sh); o resultado fica em PLANO.result.
romclean_transfer() {
  log_info "ROM cleaner: $2 ($(sed -n 's/^# roms\t//p' "$1") -> $(sed -n 's/^# dest\t//p' "$1"))"
  ev_step 0 "Starting"
  "$ROMCLEAN" apply "$1" "$2" --progress --result "$1.result" 2>> "$FLIPEROS_LOG"
}

# human_bytes N imprime o tamanho legivel (1.2 GB).
human_bytes() {
  awk -v b="$1" 'BEGIN { split("B KB MB GB TB", u); i = 1
    while (b >= 1024 && i < 5) { b /= 1024; i++ }
    printf (i == 1 ? "%d %s\n" : "%.1f %s\n"), b, u[i] }'
}
