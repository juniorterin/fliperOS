# shellcheck shell=bash
# Scraper: capas, logos, videos e informacoes de cada ROM, com o Skyscraper
# (o GroovyArcade tambem o empacota). Duas fases, como o proprio Skyscraper
# pede: "gather" baixa para o cache, "generate" monta a lista do frontend.
#
# A lista vai para onde o frontend le. No Attract-Mode Plus (o frontend do
# repositorio do FliperOS) o Skyscraper precisa do .cfg do emulador em
# ~/.attract/emulators e escreve a romlist em ~/.attract/romlists e a arte
# nas pastas das linhas "artwork" desse .cfg; o Setup cria o emulador (com o
# comando que abre o jogo) e a tela (display) que faltarem, como o efc.sh do
# GroovyArcade. Para EmulationStation e Pegasus a lista e a arte ficam na
# propria pasta das ROMs (sem -g/-o o Skyscraper as poria em ~/RetroPie).

ROMS_DIR=${ROMS_DIR:-/home/fliperos/roms}
SKYSCRAPER=${SKYSCRAPER:-Skyscraper}
RA_INFO_DIR=${RA_INFO_DIR:-/opt/fliperos/retroarch/info}
RA_CORES_DIR=${RA_CORES_DIR:-/opt/fliperos/retroarch/cores}
ATTRACT_DIR=${ATTRACT_DIR:-/home/fliperos/.attract}
FLIPEROS_BIN=${FLIPEROS_BIN:-/opt/fliperos/bin}

# scraper_platform PASTA: pasta de emulador de ~/roms (fliperos-roms) ->
# plataforma do Skyscraper. Os consoles do RetroArch vem pelos cores
# (scraper_libretro_platform); so entra o que o FliperOS sabe abrir.
scraper_platform() {
  case $1 in
    mame) echo arcade ;;
    dreamcast) echo dreamcast ;;
    ps2) echo ps2 ;;
    dolphin) echo gc ;;
    *) return 1 ;;
  esac
}

# scraper_libretro_platform SYSTEMID: o systemid do .info de um core do
# RetroArch -> plataforma do Skyscraper (as que ele conhece, peas.json).
scraper_libretro_platform() {
  case $1 in
    super_nes) echo snes ;;
    nes) echo nes ;;
    mame | hbmame) echo arcade ;;
    fb_alpha) echo fba ;;
    playstation) echo psx ;;
    playstation2) echo ps2 ;;
    playstation_portable) echo psp ;;
    game_boy) echo gb ;;
    game_boy_advance) echo gba ;;
    nintendo_64) echo n64 ;;
    nds) echo nds ;;
    3ds) echo 3ds ;;
    gamecube) echo gc ;;
    virtual_boy) echo virtualboy ;;
    pokemon_mini) echo pokemini ;;
    mega_drive) echo megadrive ;;
    master_system) echo mastersystem ;;
    sega_saturn) echo saturn ;;
    dreamcast) echo dreamcast ;;
    neogeo) echo neogeo ;;
    neo_geo_cd) echo neogeocd ;;
    neo_geo_pocket) echo ngpc ;;
    pc_engine) echo pcengine ;;
    pc_fx) echo pcfx ;;
    wonderswan) echo wonderswancolor ;;
    atari_2600) echo atari2600 ;;
    atari_5200) echo atari5200 ;;
    atari_7800) echo atari7800 ;;
    atari_lynx) echo atarilynx ;;
    atari_jaguar) echo atarijaguar ;;
    atari_st) echo atarist ;;
    commodore_amiga) echo amiga ;;
    commodore_c64) echo c64 ;;
    commodore_c128) echo c128 ;;
    commodore_vic20) echo vic20 ;;
    commodore_plus4) echo plus4 ;;
    colecovision) echo coleco ;;
    intellivision) echo intellivision ;;
    vectrex) echo vectrex ;;
    odyssey2) echo videopac ;;
    channel_f) echo channelf ;;
    msx) echo msx ;;
    cpc) echo amstradcpc ;;
    zx_spectrum) echo zxspectrum ;;
    zx81) echo zx81 ;;
    sharp_x68000) echo x68000 ;;
    sharp_x1) echo x1 ;;
    pc_88) echo pc88 ;;
    pc_98) echo pc98 ;;
    dos) echo pc ;;
    3do) echo 3do ;;
    cdi) echo cdi ;;
    scummvm) echo scummvm ;;
    daphne) echo daphne ;;
    *) return 1 ;;
  esac
}

# scraper_core_info CORE CHAVE: um valor do .info do core.
scraper_core_info() {
  sed -n "s/^$2 *= *\"\(.*\)\"/\1/p" "$RA_INFO_DIR/${1}_libretro.info" 2> /dev/null | head -1
}

# scraper_count PASTA: arquivos de jogo, sem o _info.txt do fliperos-roms,
# os ocultos e o que o proprio scraper gravou (lista e media/).
scraper_count() {
  find "$1" -maxdepth 2 -type f ! -name '.*' ! -name '_info.txt' ! -name 'gamelist.xml' \
    ! -name 'metadata.pegasus.txt' ! -path "$1/media/*" 2> /dev/null | wc -l
}

# scraper_detect imprime "chave|pasta|plataforma|quantidade" das pastas com
# jogos que o Skyscraper conhece: as de ~/roms e as dos cores do RetroArch
# (~/roms/retroarch/<core>, pela plataforma do systemid do core).
scraper_detect() {
  local dir name platform count core
  for dir in "$ROMS_DIR"/*/; do
    [[ -d $dir ]] || continue
    dir=${dir%/}
    name=${dir##*/}
    platform=$(scraper_platform "$name") || continue
    count=$(scraper_count "$dir")
    ((count > 0)) && printf '%s|%s|%s|%s\n' "$name" "$dir" "$platform" "$count"
  done
  for dir in "$ROMS_DIR"/retroarch/*/; do
    [[ -d $dir ]] || continue
    dir=${dir%/}
    core=${dir##*/}
    platform=$(scraper_libretro_platform "$(scraper_core_info "$core" systemid)") || continue
    count=$(scraper_count "$dir")
    ((count > 0)) && printf 'retroarch/%s|%s|%s|%s\n' "$core" "$dir" "$platform" "$count"
  done
  return 0
}

# scraper_frontend_format imprime o formato de lista do Skyscraper: o do
# launcher padrao; sem frontend (o Setup, um emulador, o desktop), o do
# Attract-Mode Plus se ele estiver instalado.
scraper_frontend_format() {
  case $(launcher_current) in
    attractplus) echo attractmode ;;
    emulationstation) echo emulationstation ;;
    pegasus) echo pegasus ;;
    *) launcher_installed attractplus && echo attractmode || echo emulationstation ;;
  esac
}

scraper_format_label() {
  case $1 in
    attractmode) echo "Attract-Mode Plus" ;;
    pegasus) echo "Pegasus" ;;
    *) echo "EmulationStation" ;;
  esac
}

# scraper_attract_emulator CHAVE imprime "nome|executavel|argumentos|extensoes"
# do emulador do Attract-Mode que abre os jogos daquela pasta.
scraper_attract_emulator() {
  local key=$1 core name corename exts
  case $key in
    mame)
      echo "MAME|$FLIPEROS_BIN/fliperos-kms-run|groovymame [name]|.zip;.7z" ;;
    dreamcast)
      echo "Flycast|$FLIPEROS_BIN/fliperos-x11-run|flycast \"[romfilename]\"|.gdi;.cdi;.chd;.cue;.zip;.7z" ;;
    ps2)
      echo "PCSX2|$FLIPEROS_BIN/fliperos-x11-run|pcsx2 \"[romfilename]\"|.iso;.chd;.cso;.bin;.gz" ;;
    dolphin)
      echo "Dolphin|$FLIPEROS_BIN/fliperos-x11-run|dolphin-emu -e \"[romfilename]\"|.iso;.gcm;.rvz;.wbfs;.ciso;.gcz;.wad" ;;
    retroarch/*)
      core=${key#retroarch/}
      name=$(scraper_core_info "$core" systemname)
      corename=$(scraper_core_info "$core" corename)
      exts=$(scraper_core_info "$core" supported_extensions)
      [[ -n $exts ]] && exts=".${exts//|/;.}"
      name="${name:-$core} (${corename:-$core})"
      # O nome vira arquivo (.cfg, romlist): sem barra.
      echo "${name//\//-}|$FLIPEROS_BIN/fliperos-kms-run|retroarch -L $RA_CORES_DIR/${core}_libretro.so \"[romfilename]\"|$exts"
      ;;
    *) return 1 ;;
  esac
}

# scraper_attract_prepare CHAVE PASTA PLATAFORMA cria o que falta no
# Attract-Mode para a pasta (o .cfg do emulador, a pasta das romlists e a
# tela) e imprime o nome do emulador. O que ja existe fica como esta.
scraper_attract_prepare() {
  local key=$1 dir=$2 platform=$3 name exe args exts media cfg acfg t
  IFS='|' read -r name exe args exts <<< "$(scraper_attract_emulator "$key")"
  [[ -n $name ]] || return 1
  media="$ATTRACT_DIR/scraped/${key//\//-}"
  cfg="$ATTRACT_DIR/emulators/$name.cfg"
  mkdir -p "$ATTRACT_DIR/emulators" "$ATTRACT_DIR/romlists" "$media" || return 1
  if [[ ! -f $cfg ]]; then
    {
      printf '# Criado pelo FliperOS Setup (Scraper).\n'
      printf '%-20s %s\n' executable "$exe" args "$args" workdir "\$HOME" rompath "$dir/" romext "$exts" \
        system "$platform"
      for t in flyer marquee wheel; do
        printf 'artwork    %-15s %s\n' "$t" "$media/$t"
      done
      # Video junto da captura, como no efc.sh: o Skyscraper acha a pasta
      # do video na linha do snap.
      printf 'artwork    %-15s %s\n' snap "$media/snap;$media/video"
    } > "$cfg"
  fi
  # Uma tela por emulador, com o tema AdvanceMenu (legivel em 640x240).
  acfg="$ATTRACT_DIR/attract.cfg"
  if ! awk -v n="$name" '$1 == "romlist" { sub(/^[ \t]*romlist[ \t]+/, ""); if ($0 == n) f = 1 } END { exit !f }' \
    "$acfg" 2> /dev/null; then
    printf 'display\t%s\n\tlayout               AdvanceMenu\n\tromlist              %s\n\tin_cycle             yes\n\tin_menu              yes\n\n' \
      "$name" "$name" >> "$acfg"
  fi
  chown -R "$FLIPEROS_USER:" "$ATTRACT_DIR" 2> /dev/null
  printf '%s\n' "$name"
}

# scraper_run CHAVE PASTA PLATAFORMA FONTE VIDEOS [USUARIO:SENHA] junta e
# gera a lista de uma pasta, falando com a tela por eventos.
scraper_run() {
  local key=$1 dir=$2 platform=$3 source=$4 videos=$5 creds=${6:-} flags=unattend format name args gen
  have "$SKYSCRAPER" || { ev_fail "Skyscraper is not installed"; return 1; }
  ((videos)) && flags+=,videos
  format=$(scraper_frontend_format)
  args=(-p "$platform" -i "$dir" --flags "$flags")
  if [[ $format == attractmode ]]; then
    name=$(scraper_attract_prepare "$key" "$dir" "$platform") ||
      { ev_fail "Attract-Mode has no emulator for $key"; return 1; }
    gen=(-f attractmode -e "$name")
  else
    gen=(-f "$format" -g "$dir" -o "$dir/media")
  fi
  ev_step 5 "Fetching $platform data from $source"
  local gather=("$SKYSCRAPER" "${args[@]}" -s "$source")
  [[ -n $creds ]] && gather+=(-u "$creds")
  if ! scraper_stream 5 80 runuser -u "$FLIPEROS_USER" -- "${gather[@]}"; then
    ev_fail "Skyscraper could not fetch the $platform data"
    return 1
  fi
  ev_step 85 "Building the $(scraper_format_label "$format") game list"
  if ! ev_run runuser -u "$FLIPEROS_USER" -- "$SKYSCRAPER" "${args[@]}" "${gen[@]}"; then
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
