# shellcheck shell=bash
# Scraper: capas, logos, videos e informacoes de cada ROM, com o Skyscraper
# (o GroovyArcade tambem o empacota). Duas fases, como o proprio Skyscraper
# pede: "gather" baixa para o cache, "generate" monta a lista do frontend.

ROMS_DIR=${ROMS_DIR:-/home/fliperos/roms}
SKYSCRAPER=${SKYSCRAPER:-Skyscraper}

# Pasta de ROMs do FliperOS -> plataforma do Skyscraper.
scraper_platform() {
  case $1 in
    mame | arcade | groovymame) echo arcade ;;
    fbneo) echo fbneo ;;
    neogeo) echo neogeo ;;
    nes | famicom) echo nes ;;
    snes | sfc) echo snes ;;
    n64) echo n64 ;;
    gb) echo gb ;;
    gbc) echo gbc ;;
    gba) echo gba ;;
    megadrive | genesis) echo megadrive ;;
    mastersystem | sms) echo mastersystem ;;
    gamegear | gg) echo gamegear ;;
    segacd | megacd) echo segacd ;;
    saturn) echo saturn ;;
    dreamcast | dc) echo dreamcast ;;
    psx | ps1) echo psx ;;
    ps2) echo ps2 ;;
    pcengine | tg16) echo pcengine ;;
    atari2600) echo atari2600 ;;
    *) return 1 ;;
  esac
}

# scraper_detect imprime "pasta|plataforma|quantidade" das pastas de ROM
# que tem arquivos e que o Skyscraper conhece.
scraper_detect() {
  local dir name platform count
  for dir in "$ROMS_DIR"/*/; do
    [[ -d $dir ]] || continue
    name=$(basename "$dir")
    platform=$(scraper_platform "$name") || continue
    count=$(find "$dir" -maxdepth 2 -type f ! -name '.*' 2> /dev/null | wc -l)
    ((count > 0)) && printf '%s|%s|%s\n' "$dir" "$platform" "$count"
  done
  return 0
}

# scraper_frontend_format imprime o formato de lista do launcher padrao.
scraper_frontend_format() {
  case $(launcher_current) in
    attractplus) echo attractmode ;;
    pegasus) echo pegasus ;;
    *) echo emulationstation ;;
  esac
}

# scraper_run PASTA PLATAFORMA FONTE VIDEOS [USUARIO:SENHA] junta e gera a
# lista de uma plataforma, falando com a tela por eventos.
scraper_run() {
  local dir=$1 platform=$2 source=$3 videos=$4 creds=${5:-} flags=unattend format args
  have "$SKYSCRAPER" || { ev_fail "Skyscraper is not installed"; return 1; }
  ((videos)) && flags+=,videos
  format=$(scraper_frontend_format)
  args=(-p "$platform" -i "$dir" --flags "$flags")
  ev_step 5 "Fetching $platform data from $source"
  local gather=("$SKYSCRAPER" "${args[@]}" -s "$source")
  [[ -n $creds ]] && gather+=(-u "$creds")
  if ! scraper_stream 5 80 runuser -u "$FLIPEROS_USER" -- "${gather[@]}"; then
    ev_fail "Skyscraper could not fetch the $platform data"
    return 1
  fi
  ev_step 85 "Building the $format game list"
  if ! ev_run runuser -u "$FLIPEROS_USER" -- "$SKYSCRAPER" "${args[@]}" -f "$format" -e "$platform"; then
    return 1
  fi
  ev_step 100 "$platform: done"
}

# scraper_stream INICIO FIM COMANDO... repassa o progresso "#N/TOTAL" que o
# Skyscraper imprime por jogo como porcentagem entre INICIO e FIM.
scraper_stream() {
  local from=$1 to=$2 line n total rc=1
  shift 2
  log_line cmd "\$ $*"
  while IFS= read -r line; do
    printf '%s\n' "$line" >> "$FLIPEROS_LOG"
    if [[ $line =~ \#([0-9]+)/([0-9]+) ]]; then
      n=${BASH_REMATCH[1]}
      total=${BASH_REMATCH[2]}
      ((total > 0)) && ev_pct $((from + (to - from) * n / total))
    elif [[ $line =~ ^Game\ \'(.+)\'\ found ]]; then
      ev_msg "Found: ${BASH_REMATCH[1]}"
    elif [[ $line == "@rc "* ]]; then
      rc=${line#@rc }
    fi
  done < <("$@" 2>&1; printf '@rc %s\n' "$?")
  ((rc == 0))
}
