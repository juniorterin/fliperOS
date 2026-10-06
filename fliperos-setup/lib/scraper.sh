# shellcheck shell=bash
# Scraper: capas, logos, videos e informacoes de cada ROM, com o Skyscraper
# (o GroovyArcade tambem o empacota). Duas fases, como o proprio Skyscraper
# pede: "gather" baixa para o cache, "generate" monta a lista do frontend.
#
# A arte e os textos vao para ~/media (media_farm, abaixo), de onde todos os
# frontends leem; a lista vai para onde o frontend a procura. Com o
# GroovyMAME de launcher, a pasta do MAME so ganha a arte: o mame.ini e o
# ui.ini ja procuram em ~/media/<tipo>/arcade. No Attract-Mode Plus (o
# frontend do repositorio do FliperOS) o Skyscraper precisa do .cfg do
# emulador em ~/.attract/emulators e escreve a romlist em ~/.attract/romlists
# e a arte nas pastas das linhas "artwork" desse .cfg; o Setup cria o
# emulador (com o comando que abre o jogo) e a tela (display) que faltarem,
# como o efc.sh do GroovyArcade. O ES-DE le a lista de
# ~/ES-DE/gamelists/<sistema> e o Pegasus a da propria pasta das ROMs.

ROMS_DIR=${ROMS_DIR:-/home/fliperos/roms}
SKYSCRAPER=${SKYSCRAPER:-Skyscraper}
RA_INFO_DIR=${RA_INFO_DIR:-/opt/fliperos/retroarch/info}
RA_CORES_DIR=${RA_CORES_DIR:-/opt/fliperos/retroarch/cores}
ATTRACT_DIR=${ATTRACT_DIR:-/home/fliperos/.attract}
FLIPEROS_BIN=${FLIPEROS_BIN:-/opt/fliperos/bin}
# Onde ficava a arte da lista de jogos do GroovyMAME antes do ~/media
# (scraper_media_migrate).
MAME_SCRAPED=${MAME_SCRAPED:-/home/fliperos/.mame/scraped/mame}

# ── Midia ─────────────────────────────────────────────────────────
# ~/media tem uma pasta por tipo e, dentro, uma por sistema (a plataforma do
# Skyscraper: arcade, snes, dreamcast...):
#   snap     capturas da tela       logo     logos (wheel)
#   preview  videos                 box      capas e flyers
#   marquee  marquees               texto    descricoes (.txt)
# O Skyscraper e o ES-DE usam subpastas de nome fixo por sistema
# (screenshots, covers...): para eles, ~/media/.skyscraper/<sistema> e
# ~/media/.es-de/<sistema do ES-DE> sao links com esses nomes para as
# pastas daqui. O Attract-Mode le pelas linhas "artwork" do emulador e o
# GroovyMAME pelo mame.ini e o ui.ini (config/).
MEDIA_DIR=${MEDIA_DIR:-/home/fliperos/media}
MEDIA_TYPES="snap preview logo box marquee texto"
# subpasta do Skyscraper:tipo
SCRAPER_MEDIA_LINKS="screenshots:snap videos:preview wheels:logo covers:box marquees:marquee"

# media_system PLATAFORMA cria a pasta do sistema em cada tipo de ~/media.
media_system() {
  local t
  for t in $MEDIA_TYPES; do
    mkdir -p "$MEDIA_DIR/$t/$1" || return 1
    chown "$FLIPEROS_USER:" "$MEDIA_DIR" "$MEDIA_DIR/$t" "$MEDIA_DIR/$t/$1" 2> /dev/null
  done
  return 0
}

# media_farm PASTA PLATAFORMA SUBPASTA:TIPO... cria as pastas do sistema
# (media_system) e, em PASTA (dois niveis abaixo de ~/media), um link
# relativo por SUBPASTA para a do tipo. Uma SUBPASTA que ja e pasta de
# verdade fica.
media_farm() {
  local farm=$1 platform=$2 pair link
  shift 2
  media_system "$platform" || return 1
  mkdir -p "$farm" || return 1
  for pair in "$@"; do
    link="$farm/${pair%%:*}"
    [[ -d $link && ! -L $link ]] && continue
    ln -sfn "../../${pair#*:}/$platform" "$link" || return 1
  done
  chown -h "$FLIPEROS_USER:" "$MEDIA_DIR" "$(dirname "$farm")" "$farm" "$farm"/* 2> /dev/null
  return 0
}

# scraper_media PLATAFORMA imprime a pasta de midia do Skyscraper (-o) para
# o sistema.
scraper_media() {
  local farm="$MEDIA_DIR/.skyscraper/$1"
  # shellcheck disable=SC2086 # um par por palavra
  media_farm "$farm" "$1" $SCRAPER_MEDIA_LINKS || return 1
  printf '%s\n' "$farm"
}

# media_link_dir LINK PASTA faz de LINK um link para PASTA. Se LINK era uma
# pasta, o que tem nela vai para PASTA (sem sobrescrever) antes; se sobrar
# algo, ela fica.
media_link_dir() {
  local link=$1 real=$2
  [[ -L $link ]] && return 0
  mkdir -p "$real" "$(dirname "$link")" || return 1
  if [[ -d $link ]]; then
    find "$link" -mindepth 1 -maxdepth 1 -exec mv -n -t "$real" {} + 2> /dev/null
    rmdir "$link" 2> /dev/null || return 0
  fi
  ln -s "$real" "$link"
}

# media_move PASTA PLATAFORMA SUBPASTA:TIPO... passa o que tem em
# PASTA/SUBPASTA para ~/media/TIPO/PLATAFORMA, sem sobrescrever; as pastas
# que ficarem vazias saem.
media_move() {
  local old=$1 platform=$2 pair sub
  shift 2
  [[ -d $old && ! -L $old ]] || return 0
  for pair in "$@"; do
    sub="$old/${pair%%:*}"
    [[ -d $sub && ! -L $sub ]] || continue
    mkdir -p "$MEDIA_DIR/${pair#*:}/$platform" || continue
    find "$sub" -mindepth 1 -maxdepth 1 -exec mv -n -t "$MEDIA_DIR/${pair#*:}/$platform" {} + 2> /dev/null
    rmdir "$sub" 2> /dev/null
    chown -R "$FLIPEROS_USER:" "$MEDIA_DIR/${pair#*:}/$platform" 2> /dev/null
    log_info "Midia: $sub -> $MEDIA_DIR/${pair#*:}/$platform"
  done
  rmdir "$old" 2> /dev/null
  return 0
}

# scraper_media_migrate passa para ~/media a arte de antes dele: a da lista
# do GroovyMAME (~/.mame/scraped/mame), a do Attract-Mode
# (~/.attract/scraped/<pasta>) e a do EmulationStation e do Pegasus
# (<pasta das ROMs>/media). As listas antigas apontam para la: o Scraper as
# refaz do cache. Roda no tools/cabinet-update.sh.
scraper_media_migrate() {
  local key dir platform
  # shellcheck disable=SC2086 # um par por palavra
  media_move "$MAME_SCRAPED" arcade $SCRAPER_MEDIA_LINKS
  rm -f "$MAME_SCRAPED/gamelist.xml"
  rmdir "$MAME_SCRAPED" "$(dirname "$MAME_SCRAPED")" 2> /dev/null
  while IFS='|' read -r key dir platform _; do
    # shellcheck disable=SC2086
    media_move "$dir/media" "$platform" $SCRAPER_MEDIA_LINKS
    media_move "$ATTRACT_DIR/scraped/${key//\//-}" "$platform" snap:snap video:preview wheel:logo flyer:box \
      marquee:marquee
  done < <(scraper_detect)
  rmdir "$ATTRACT_DIR/scraped" 2> /dev/null
  return 0
}

# scraper_texts LISTA PLATAFORMA grava a descricao de cada jogo da lista
# (gamelist.xml ou metadata.pegasus.txt) em ~/media/texto/PLATAFORMA/<rom>.txt.
# No Attract-Mode o proprio Skyscraper as grava la (o overview do emulador e
# um link).
scraper_texts() {
  local list=$1 dest="$MEDIA_DIR/texto/$2" n
  [[ -f $list ]] || return 0
  mkdir -p "$dest" || return 0
  n=$(python3 - "$list" "$dest" << 'PY'
import os, re, sys
import xml.etree.ElementTree as ET

lst, dest = sys.argv[1], sys.argv[2]
games = []
if lst.endswith('.xml'):
    for g in ET.parse(lst).getroot().iter('game'):
        games.append((g.findtext('path') or '', g.findtext('desc') or ''))
else:
    # Pegasus: "chave: valor", continuacao recuada e " ." entre paragrafos.
    cur = key = None
    with open(lst, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line[:1] in (' ', '\t'):
                if cur is not None and key == 'description':
                    text = line.strip()
                    cur['description'] += '\n' + ('' if text == '.' else text)
                continue
            m = re.match(r'([^:#\s][^:]*):\s?(.*)$', line)
            key = m.group(1).strip() if m else None
            if key == 'game':
                cur = {'file': '', 'description': ''}
                games.append(cur)
            elif cur is not None and key in ('file', 'description'):
                cur[key] = m.group(2)
    games = [(g['file'], g['description']) for g in games]
n = 0
for path, desc in games:
    desc = desc.strip()
    if path and desc:
        name = os.path.splitext(os.path.basename(path))[0]
        with open(os.path.join(dest, name + '.txt'), 'w', encoding='utf-8') as f:
            f.write(desc + '\n')
        n += 1
print(n)
PY
  ) || n=0
  chown -R "$FLIPEROS_USER:" "$dest" 2> /dev/null
  log_info "Textos: $n em $dest"
}

# scraper_platform PASTA: pasta de emulador de ~/roms (fliperos-roms) ->
# plataforma do Skyscraper. Os consoles do RetroArch vem pelos cores
# (scraper_libretro_platform); so entra o que o FliperOS sabe abrir.
scraper_platform() {
  case $1 in
    mame) echo arcade ;;
    dreamcast) echo dreamcast ;;
    # Os arcades do Flycast, uma pasta por sistema (MAME ROM Cleaner).
    naomi | naomi2 | atomiswave) echo "$1" ;;
    # Supermodel: os .zip do MAME, que o Skyscraper procura como arcade.
    model3) echo arcade ;;
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

# scraper_target CHAVE imprime para onde vai a lista da pasta: a lista de
# jogos do proprio GroovyMAME (mameui) quando ele e o launcher padrao e a
# pasta e a do MAME; senao o formato do launcher padrao (o EmulationStation
# do FliperOS e o ES-DE); sem frontend (o Setup, um emulador, o desktop), o
# Attract-Mode Plus se estiver instalado.
scraper_target() {
  local launcher
  launcher=$(launcher_current)
  if [[ $launcher == groovymame && $1 == mame ]]; then
    echo mameui
    return
  fi
  case $launcher in
    attractplus) echo attractmode ;;
    emulationstation) echo esde ;;
    pegasus) echo pegasus ;;
    *) launcher_installed attractplus && echo attractmode || echo esde ;;
  esac
}

scraper_format_label() {
  case $1 in
    mameui) echo "GroovyMAME" ;;
    attractmode) echo "Attract-Mode Plus" ;;
    pegasus) echo "Pegasus" ;;
    esde) echo "ES-DE" ;;
    *) echo "EmulationStation" ;;
  esac
}

# scraper_attract_emulator CHAVE imprime "nome|executavel|argumentos|extensoes"
# do emulador do Attract-Mode que abre os jogos daquela pasta.
scraper_attract_emulator() {
  local key=$1 core name corename exts
  case $key in
    mame)
      echo "MAME|$FLIPEROS_BIN/fliperos-x11-run|groovymame [name]|.zip;.7z" ;;
    dreamcast)
      echo "Flycast|$FLIPEROS_BIN/fliperos-x11-run|flycast \"[romfilename]\"|.gdi;.cdi;.chd;.cue;.zip;.7z" ;;
    naomi)
      echo "Naomi|$FLIPEROS_BIN/fliperos-x11-run|flycast \"[romfilename]\"|.zip;.7z" ;;
    naomi2)
      echo "Naomi 2|$FLIPEROS_BIN/fliperos-x11-run|flycast \"[romfilename]\"|.zip;.7z" ;;
    atomiswave)
      echo "Atomiswave|$FLIPEROS_BIN/fliperos-x11-run|flycast \"[romfilename]\"|.zip;.7z" ;;
    model3)
      echo "Supermodel|$FLIPEROS_BIN/fliperos-x11-run|supermodel \"[romfilename]\"|.zip" ;;
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
# tela) e imprime o nome do emulador. Um .cfg do Setup e refeito (a arte
# passou para ~/media); um mudado pelo Attract-Mode ou a mao fica.
scraper_attract_prepare() {
  local key=$1 dir=$2 platform=$3 name exe args exts media cfg acfg
  IFS='|' read -r name exe args exts <<< "$(scraper_attract_emulator "$key")"
  [[ -n $name ]] || return 1
  media=$MEDIA_DIR
  cfg="$ATTRACT_DIR/emulators/$name.cfg"
  mkdir -p "$ATTRACT_DIR/emulators" "$ATTRACT_DIR/romlists" || return 1
  media_system "$platform" || return 1
  if [[ ! -f $cfg ]] || head -1 "$cfg" | grep -q '^# Criado pelo FliperOS Setup'; then
    {
      printf '# Criado pelo FliperOS Setup (Scraper).\n'
      printf '%-20s %s\n' executable "$exe" args "$args" workdir "\$HOME" rompath "$dir/" romext "$exts" \
        system "$platform"
      printf 'artwork    %-15s %s\n' flyer "$media/box/$platform" marquee "$media/marquee/$platform" \
        wheel "$media/logo/$platform"
      # Video junto da captura, como no efc.sh: o Skyscraper acha a pasta
      # do video na linha do snap.
      printf 'artwork    %-15s %s\n' snap "$media/snap/$platform;$media/preview/$platform"
    } > "$cfg"
  fi
  # A descricao de cada jogo: o Skyscraper a grava (e o Attract-Mode a le) em
  # scraper/<emulador>/overview, um link para ~/media/texto.
  media_link_dir "$ATTRACT_DIR/scraper/$name/overview" "$MEDIA_DIR/texto/$platform"
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

# ── Retomada ──────────────────────────────────────────────────────
# O Skyscraper so grava o cache no fim de cada execucao: um desligamento no
# meio perdia tudo. Os jogos vao em lotes (SCRAPER_CHUNK por execucao, com
# --includefrom), e o trabalho fica anotado em SCRAPER_JOB_DIR:
#   options        "fonte|midia|clones|usuario:senha" (so o root le; midia e
#                  a lista de tipos, ou 0/1 = videos num trabalho antigo)
#   pending        as pastas que faltam, uma linha do scraper_detect cada
#   done.<pasta>   os arquivos da pasta atual que ja estao no cache
# O Setup > Scraper oferece retomar enquanto houver pasta pendente.
SCRAPER_JOB_DIR=${SCRAPER_JOB_DIR:-/var/lib/fliperos/scraper}
SCRAPER_CHUNK=${SCRAPER_CHUNK:-20}
# Onde ficam os clones (arquivos de referencia) da pasta do MAME. Fora do
# ~/.skyscraper: com a pasta ja existindo, o Skyscraper nao copia os
# arquivos dele na primeira vez (peas.json) e para.
SCRAPER_STAGE=${SCRAPER_STAGE:-/home/fliperos/.cache/fliperos-scraper}
GROOVYMAME=${GROOVYMAME:-groovymame}

# scraper_job_start FONTE MIDIA CLONES CREDENCIAIS ALVO... anota um trabalho.
scraper_job_start() {
  local source=$1 videos=$2 clones=$3 creds=$4
  shift 4
  rm -rf "$SCRAPER_JOB_DIR"
  mkdir -p "$SCRAPER_JOB_DIR" && chmod 700 "$SCRAPER_JOB_DIR" || return 1
  (
    umask 077
    printf '%s|%s|%s|%s\n' "$source" "$videos" "$clones" "$creds" > "$SCRAPER_JOB_DIR/options"
  )
  printf '%s\n' "$@" > "$SCRAPER_JOB_DIR/pending"
}

scraper_job_pending() {
  [[ -s $SCRAPER_JOB_DIR/pending && -f $SCRAPER_JOB_DIR/options ]] && cat "$SCRAPER_JOB_DIR/pending"
}

scraper_job_options() {
  cat "$SCRAPER_JOB_DIR/options" 2> /dev/null
}

# scraper_job_done CHAVE tira a pasta do trabalho; sem nada pendente, o
# trabalho acaba.
scraper_job_done() {
  local key=$1
  [[ -f $SCRAPER_JOB_DIR/pending ]] || return 0
  awk -F'|' -v k="$key" '$1 != k' "$SCRAPER_JOB_DIR/pending" > "$SCRAPER_JOB_DIR/pending.new"
  mv -f "$SCRAPER_JOB_DIR/pending.new" "$SCRAPER_JOB_DIR/pending"
  rm -f "$SCRAPER_JOB_DIR/done.${key//\//-}"
  [[ -s $SCRAPER_JOB_DIR/pending ]] || scraper_job_clear
}

scraper_job_clear() {
  rm -rf "$SCRAPER_JOB_DIR"
}

# ── Clones ───────────────────────────────────────────────────────
# Num romset merged os clones (mvscu, mvscj...) estao dentro do zip do pai e
# nao tem arquivo: o Skyscraper nao os veria. Para a lista do GroovyMAME e a
# do Attract-Mode (que acham o jogo pelo nome), a pasta raspada passa a ser
# uma copia de referencias: os arquivos de verdade (links) e um arquivo
# pequeno com o nome de cada clone dos jogos que existem.

# scraper_clones_input PASTA imprime a pasta com os jogos e os clones.
scraper_clones_input() {
  local dir=$1 stage="$SCRAPER_STAGE/mame" f clone parent
  rm -rf "$stage"
  mkdir -p "$stage" || return 1
  for f in "$dir"/*.zip "$dir"/*.7z; do
    [[ -e $f ]] && ln -s "$f" "$stage/${f##*/}"
  done
  while read -r clone parent; do
    [[ -e $stage/$parent.zip || -e $stage/$parent.7z ]] || continue
    [[ -e $stage/$clone.zip || -e $stage/$clone.7z ]] && continue
    # Conteudo diferente por clone: o cache do Skyscraper usa o hash.
    printf 'FliperOS: %s, clone de %s\n' "$clone" "$parent" > "$stage/$clone.zip"
  done < <(runuser -u "$FLIPEROS_USER" -- "$GROOVYMAME" -listclones 2> /dev/null | awk 'NR > 1 && NF == 2 { print $1, $2 }')
  chown -R "$FLIPEROS_USER:" "$SCRAPER_STAGE" 2> /dev/null
  printf '%s\n' "$stage"
}

# ── Tipos de midia ────────────────────────────────────────────────
# O que o Scraper busca, pelos nomes das pastas de ~/media. A pessoa marca na
# tela (Setup > Scraper) e a escolha fica no fliperos.conf (scraper_media);
# sem escolha, tudo menos os videos, que ocupam muito mais.
SCRAPER_MEDIA_DEFAULT="snap,logo,box,marquee,texto"

# scraper_media_options imprime "tipo|rotulo" de cada tipo, para a tela.
scraper_media_options() {
  printf '%s\n' "snap|Screenshots (snap)" "logo|Logos (logo)" "box|Box art and flyers (box)" \
    "marquee|Marquees (marquee)" "texto|Descriptions (texto)" "preview|Videos (preview: much more disk space)"
}

# scraper_media_saved imprime a escolha guardada (ou o padrao).
scraper_media_saved() {
  conf_get scraper_media 2> /dev/null || printf '%s\n' "$SCRAPER_MEDIA_DEFAULT"
}

# scraper_media_list VALOR imprime a lista de tipos: a propria lista, ou a
# de um trabalho anotado antes desta escolha, que so dizia videos sim (1) ou
# nao (0).
scraper_media_list() {
  case $1 in
    1) printf '%s\n' "$SCRAPER_MEDIA_DEFAULT,preview" ;;
    0 | "") printf '%s\n' "$SCRAPER_MEDIA_DEFAULT" ;;
    *) printf '%s\n' "$1" ;;
  esac
}

# scraper_media_has LISTA TIPO
scraper_media_has() {
  [[ ",$1," == *",$2,"* ]]
}

# Os tipos ja buscados para cada pasta ("chave=lista"). O Skyscraper nao
# volta a um jogo que ja esta no cache: um tipo de arte marcado agora e que
# a pasta ainda nao tinha so chega aos jogos ja raspados com o --refresh.
SCRAPER_MEDIA_STATE=${SCRAPER_MEDIA_STATE:-/var/lib/fliperos/scraper-media}

# scraper_media_fetched CHAVE imprime os tipos ja buscados para a pasta. Sem
# registro, o padrao: o que o Scraper buscava antes de haver escolha (numa
# pasta nunca raspada o --refresh nao custa nada).
scraper_media_fetched() {
  conf_get "$1" "$SCRAPER_MEDIA_STATE" 2> /dev/null || printf '%s\n' "$SCRAPER_MEDIA_DEFAULT"
}

# scraper_media_adds ANTES AGORA: a escolha de agora tem algum tipo de arte
# que a de antes nao tinha?
scraper_media_adds() {
  local t
  for t in snap logo box marquee preview; do
    scraper_media_has "$2" "$t" && ! scraper_media_has "$1" "$t" && return 0
  done
  return 1
}

# scraper_media_record CHAVE LISTA junta a lista aos tipos ja buscados da
# pasta.
scraper_media_record() {
  local have t
  have=$(scraper_media_fetched "$1")
  for t in snap logo box marquee preview texto; do
    scraper_media_has "$2" "$t" && ! scraper_media_has "$have" "$t" && have+=",$t"
  done
  conf_set "$1" "$have" "$SCRAPER_MEDIA_STATE"
}

# scraper_media_flags LISTA imprime as flags do Skyscraper: so baixa os tipos
# marcados.
scraper_media_flags() {
  local flags=unattend
  scraper_media_has "$1" preview && flags+=,videos
  scraper_media_has "$1" snap || flags+=,noscreenshots
  scraper_media_has "$1" box || flags+=,nocovers
  scraper_media_has "$1" logo || flags+=,nowheels
  scraper_media_has "$1" marquee || flags+=,nomarquees
  printf '%s\n' "$flags"
}

# scraper_artwork [LISTA] imprime o artwork.xml do Setup: cada imagem dos
# tipos marcados como veio (captura, capa, logo, marquee), cada uma na sua
# pasta. O padrao do Skyscraper monta a captura com a capa e o logo por cima
# e nao exporta os dois; a lista do GroovyMAME e as telas do Attract-Mode
# montam sozinhas.
scraper_artwork() {
  local media=${1:-$SCRAPER_MEDIA_DEFAULT} file="$SCRAPER_STAGE/artwork.xml" pair
  mkdir -p "$SCRAPER_STAGE" || return 1
  {
    printf '<?xml version="1.0" encoding="UTF-8"?>\n<artwork>\n'
    for pair in snap:screenshot box:cover logo:wheel marquee:marquee; do
      scraper_media_has "$media" "${pair%%:*}" && printf '  <output type="%s"/>\n' "${pair#*:}"
    done
    printf '</artwork>\n'
  } > "$file"
  chown -R "$FLIPEROS_USER:" "$SCRAPER_STAGE" 2> /dev/null
  chmod 644 "$file"
  printf '%s\n' "$file"
}

# scraper_files CHAVE PASTA lista os jogos da pasta (as extensoes do
# emulador da pasta), um por linha.
scraper_files() {
  local key=$1 dir=$2 exts e args=()
  IFS='|' read -r _ _ _ exts <<< "$(scraper_attract_emulator "$key")"
  for e in ${exts//;/ }; do
    args+=(-o -iname "*$e")
  done
  ((${#args[@]})) || return 0
  find "$dir" -maxdepth 1 \( -type f -o -type l \) \( "${args[@]:1}" \) 2> /dev/null | sort
}

# scraper_run CHAVE PASTA PLATAFORMA FONTE MIDIA [USUARIO:SENHA] [CLONES]
# junta (em lotes, retomando o que ja foi) e gera a lista de uma pasta,
# falando com a tela por eventos. MIDIA: os tipos a buscar
# (scraper_media_list). Um tipo de arte que a pasta ainda nao tinha faz
# buscar de novo os jogos que ja estao no cache.
scraper_run() {
  local key=$1 dir=$2 platform=$3 source=$4 media creds=${6:-} clones=${7:-0} refresh=0
  local flags format name exe cmd args gen input done_file chunk farm list="" files=() todo=() i n from to
  have "$SKYSCRAPER" || { ev_fail "Skyscraper is not installed"; return 1; }
  media=$(scraper_media_list "$5")
  flags=$(scraper_media_flags "$media")
  scraper_media_adds "$(scraper_media_fetched "$key")" "$media" && refresh=1
  format=$(scraper_target "$key")
  # O ES-DE quer o caminho do jogo relativo a pasta do sistema ("./x.zip").
  [[ $format == esde ]] && flags+=,relative
  input=$dir
  if [[ $key == mame && $clones == 1 && $format =~ ^(mameui|attractmode)$ ]]; then
    ev_msg "Looking for the clones of the games found"
    input=$(scraper_clones_input "$dir") || { ev_fail "Could not list the MAME clones"; return 1; }
  fi
  # A arte da pasta que ficou de antes do ~/media vai para la primeiro.
  # shellcheck disable=SC2086 # um par por palavra
  media_move "$dir/media" "$platform" $SCRAPER_MEDIA_LINKS
  farm=$(scraper_media "$platform") || { ev_fail "Could not create the folders in $MEDIA_DIR"; return 1; }
  args=(-p "$platform" -i "$input" --flags "$flags")
  case $format in
    attractmode)
      name=$(scraper_attract_prepare "$key" "$dir" "$platform") ||
        { ev_fail "Attract-Mode has no emulator for $key"; return 1; }
      gen=(-f attractmode -e "$name")
      ;;
    # A lista do GroovyMAME e a do proprio MAME: do gamelist.xml so saem os
    # textos.
    mameui)
      gen=(-f emulationstation -g "$farm" -o "$farm")
      list="$farm/gamelist.xml"
      ;;
    esde)
      gen=(-f esde -g "$ESDE_DIR/gamelists/${key//\//-}" -o "$farm")
      list="$ESDE_DIR/gamelists/${key//\//-}/gamelist.xml"
      ;;
    pegasus)
      # O metadata.pegasus.txt que o Skyscraper grava leva o comando da
      # pasta (lib/frontends.sh), senao o Pegasus lista e nao abre.
      IFS='|' read -r _ exe cmd _ <<< "$(scraper_attract_emulator "$key")"
      gen=(-f pegasus -g "$dir" -o "$farm" -e "$(frontends_pegasus_launch "$exe $cmd")")
      list="$dir/metadata.pegasus.txt"
      ;;
    *) gen=(-f "$format" -g "$dir" -o "$farm") ;;
  esac
  # O que ainda nao esta no cache, em lotes; cada lote gravado fica anotado.
  mkdir -p "$SCRAPER_JOB_DIR"
  done_file="$SCRAPER_JOB_DIR/done.${key//\//-}"
  touch "$done_file"
  mapfile -t files < <(scraper_files "$key" "$input")
  mapfile -t todo < <(printf '%s\n' "${files[@]}" | grep -vxF -f "$done_file" | grep -v '^$')
  if ((${#files[@]} > ${#todo[@]})); then
    ev_msg "Resuming: $((${#files[@]} - ${#todo[@]})) of ${#files[@]} games already fetched"
  fi
  ev_step 5 "Fetching $platform data from $source"
  # O lote fica fora da pasta do trabalho (so do root): o Skyscraper roda
  # como o usuario.
  chunk=$(mktemp /tmp/fliperos-scraper.XXXXXX) || { ev_fail "No space for the scraper"; return 1; }
  chmod 644 "$chunk"
  n=${#todo[@]}
  for ((i = 0; i < n; i += SCRAPER_CHUNK)); do
    printf '%s\n' "${todo[@]:i:SCRAPER_CHUNK}" > "$chunk"
    from=$((5 + 75 * i / n))
    to=$((5 + 75 * (i + SCRAPER_CHUNK < n ? i + SCRAPER_CHUNK : n) / n))
    local gather=("$SKYSCRAPER" "${args[@]}" -s "$source" --includefrom "$chunk")
    [[ -n $creds ]] && gather+=(-u "$creds")
    ((refresh)) && gather+=(--refresh)
    if ! scraper_stream "$from" "$to" runuser -u "$FLIPEROS_USER" -- "${gather[@]}"; then
      rm -f "$chunk"
      ev_fail "Skyscraper could not fetch the $platform data"
      return 1
    fi
    cat "$chunk" >> "$done_file"
  done
  rm -f "$chunk"
  ev_step 85 "Building the $(scraper_format_label "$format") game list"
  gen+=(-a "$(scraper_artwork "$media")")
  if [[ $format == esde ]]; then
    mkdir -p "$ESDE_DIR/gamelists/${key//\//-}"
    chown -R "$FLIPEROS_USER:" "$ESDE_DIR" 2> /dev/null
  fi
  if ! ev_run runuser -u "$FLIPEROS_USER" -- "$SKYSCRAPER" "${args[@]}" "${gen[@]}"; then
    return 1
  fi
  # As descricoes em ~/media/texto, se marcadas (no Attract-Mode quem as
  # grava e o proprio Skyscraper, junto da lista).
  [[ -n $list ]] && scraper_media_has "$media" texto && scraper_texts "$list" "$platform"
  scraper_media_record "$key" "$media"
  # O sistema no ES-DE, com a arte de ~/media (lib/frontends.sh).
  [[ $format == esde ]] && frontends_esde
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
