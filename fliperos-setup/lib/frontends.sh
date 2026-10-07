# shellcheck shell=bash
# Os sistemas do FliperOS nos frontends (Pegasus, EmulationStation-DE): as
# pastas de ~/roms com jogos e o comando de cada uma, os mesmos do
# Attract-Mode (scraper_detect e scraper_attract_emulator, lib/scraper.sh).
# O Setup grava ao escolher ou instalar o frontend.

PEGASUS_DIR=${PEGASUS_DIR:-/home/fliperos/.config/pegasus-frontend}
ESDE_DIR=${ESDE_DIR:-/home/fliperos/ES-DE}

# frontends_systems imprime "chave|pasta|plataforma|nome|executavel|argumentos|extensoes"
# das pastas com jogos (argumentos e extensoes no formato do Attract-Mode:
# [name], "[romfilename]", .zip;.7z).
frontends_systems() {
  local key dir platform name exe args exts
  while IFS='|' read -r key dir platform _; do
    IFS='|' read -r name exe args exts <<< "$(scraper_attract_emulator "$key")"
    [[ -n $name ]] && printf '%s|%s|%s|%s|%s|%s|%s\n' "$key" "$dir" "$platform" "$name" "$exe" "$args" "$exts"
  done < <(scraper_detect)
  return 0
}

# frontends_pegasus_launch "EXECUTAVEL ARGUMENTOS" troca os marcadores do
# Attract-Mode pelos do Pegasus.
frontends_pegasus_launch() {
  local cmd=$1
  cmd=${cmd//\[romfilename\]/\{file.path\}}
  printf '%s\n' "${cmd//\[name\]/\{file.basename\}}"
}

# frontends_esde_command "EXECUTAVEL ARGUMENTOS": os do ES-DE (%ROM% ja vem
# entre aspas).
frontends_esde_command() {
  local cmd=$1
  cmd=${cmd//\"\[romfilename\]\"/%ROM%}
  printf '%s\n' "${cmd//\[name\]/%BASENAME%}"
}

# frontends_pegasus: um metadata.pegasus.txt por pasta (coleção, extensões e
# o comando) e a lista das pastas. Um metadata.pegasus.txt do Skyscraper
# (com os jogos) fica; so ganha o launch, se nao tiver.
frontends_pegasus() {
  local key dir platform name exe args exts meta dirs=()
  while IFS='|' read -r key dir platform name exe args exts; do
    meta="$dir/metadata.pegasus.txt"
    if [[ ! -f $meta ]]; then
      {
        printf '# Gerado pelo FliperOS Setup (Frontend).\n'
        printf 'collection: %s\nshortname: %s\n' "$name" "${key//\//-}"
        printf 'extensions: %s\n' "$(sed 's/^\.//; s/;\./, /g' <<< "$exts")"
        printf 'launch: %s\n' "$(frontends_pegasus_launch "$exe $args")"
      } > "$meta"
    elif ! grep -qE '^(launch|command):' "$meta"; then
      sed -i "/^collection:/a launch: $(frontends_pegasus_launch "$exe $args" | sed 's/[\/&]/\\&/g')" "$meta"
    fi
    chown "$FLIPEROS_USER:" "$meta" 2> /dev/null
    dirs+=("$dir")
  done < <(frontends_systems)
  mkdir -p "$PEGASUS_DIR"
  printf '%s\n' "${dirs[@]}" > "$PEGASUS_DIR/game_dirs.txt"
  frontends_pegasus_240p
  chown -R "$FLIPEROS_USER:" "$PEGASUS_DIR" 2> /dev/null
  log_info "Pegasus: ${#dirs[@]} pasta(s) de jogos"
}

# ── 240p ──────────────────────────────────────────────────────────
# Num tubo de 15 kHz os frontends rodam em 320x240, e o padrao de cada um e
# desenhado para 720 linhas ou mais: o texto fica com 4 a 8 pixels. As
# configuracoes abaixo ja ficam gravadas, uma vez so (o que a pessoa mudar
# depois, no proprio frontend, fica): o FliperOS anota no fliperos.conf que
# ja gravou. Com o frontend aberto nada e gravado (ele regrava o arquivo ao
# fechar); fica para a vez seguinte.

# Os temas do FliperOS: o do Pegasus (config/pegasus-theme-fliperos) e o do
# ES-DE (config/esde-theme-fliperos), os dois com a lista em letra de 12
# pixels e a imagem do jogo.
PEGASUS_THEME=${PEGASUS_THEME:-/usr/share/pegasus-frontend/themes/fliperos-240p}
ESDE_THEME=${ESDE_THEME:-/usr/share/es-de/themes/fliperos-240p-es-de}

# frontends_crt: o monitor escolhido no Setup e de 15 kHz?
frontends_crt() {
  [[ $(conf_get frequency 2> /dev/null) == 15* ]]
}

# frontends_240p grava a configuracao de 240p dos frontends instalados que
# ainda nao a tem. Chamado logo antes de abrir um launcher (fliperos-setup
# --session-start, quando nenhum frontend esta aberto) e no
# tools/cabinet-update.sh: assim ela nao depende de a pessoa passar de novo
# pelo Setup > Frontend.
frontends_240p() {
  frontends_crt || return 0
  if launcher_installed emulationstation && [[ $(conf_get esde_240p 2> /dev/null) != 1 ]]; then
    frontends_esde_240p
    # A pasta e do usuario: criada aqui (pelo root), o ES-DE nao gravaria nela.
    chown "$FLIPEROS_USER:" "$ESDE_DIR" 2> /dev/null
    chown -R "$FLIPEROS_USER:" "$ESDE_DIR/settings" 2> /dev/null
  fi
  if launcher_installed pegasus && [[ $(conf_get pegasus_240p 2> /dev/null) != 1 ]]; then
    frontends_pegasus_240p
    chown -R "$FLIPEROS_USER:" "$PEGASUS_DIR" 2> /dev/null
  fi
  return 0
}

# frontends_pegasus_240p: o tema FliperOS 240p (lista em letra de 12 pixels e
# a imagem do jogo), tela cheia e sem mouse.
frontends_pegasus_240p() {
  frontends_crt && [[ -f $PEGASUS_THEME/theme.qml ]] || return 0
  [[ $(conf_get pegasus_240p 2> /dev/null) == 1 ]] && return 0
  pgrep -x pegasus-fe > /dev/null 2>&1 && return 0
  pegasus_setting general.theme "$PEGASUS_THEME/"
  pegasus_setting general.fullscreen true
  pegasus_setting general.input-mouse-support false
  conf_set pegasus_240p 1
  log_info "Pegasus: configuracao de 240p gravada (tema $PEGASUS_THEME)"
}

# pegasus_setting CHAVE VALOR grava uma opcao no settings.txt do Pegasus
# ("chave: valor").
pegasus_setting() {
  local file="$PEGASUS_DIR/settings.txt"
  mkdir -p "$PEGASUS_DIR"
  if [[ -f $file ]] && grep -q "^${1//./\\.}:" "$file"; then
    sed -i "s|^${1//./\\.}:.*|$1: $2|" "$file"
  else
    printf '%s: %s\n' "$1" "$2" >> "$file"
  fi
}

# frontends_esde_240p: o tema FliperOS 240p (o ES-DE o conhece pelo nome da
# pasta; o video do jogo, se houver, entra no lugar da imagem). Sem o
# desfoque do fundo do menu e sem o aviso de versao nova.
frontends_esde_240p() {
  frontends_crt && [[ -f $ESDE_THEME/theme.xml ]] || return 0
  [[ $(conf_get esde_240p 2> /dev/null) == 1 ]] && return 0
  pgrep -x es-de > /dev/null 2>&1 && return 0
  esde_setting Theme "${ESDE_THEME##*/}"
  esde_setting ThemeAspectRatio automatic
  esde_setting ApplicationUpdaterFrequency never
  esde_setting MenuBlurBackground false bool
  conf_set esde_240p 1
  log_info "ES-DE: configuracao de 240p gravada (tema $ESDE_THEME)"
}

# ES-DE: os tipos de arte dele (subpastas de MediaDirectory/<sistema>) e as
# pastas de ~/media (lib/scraper.sh). O "marquee" do ES-DE e o logo.
ESDE_MEDIA_LINKS="screenshots:snap videos:preview marquees:logo covers:box"

# frontends_esde: os sistemas em custom_systems/es_systems.xml e, no
# es_settings.xml, a pasta das ROMs e a da arte (~/media/.es-de, com um
# link por tipo para ~/media).
frontends_esde() {
  local key dir platform name exe args exts n=0 systems=()
  mkdir -p "$ESDE_DIR/custom_systems" "$ESDE_DIR/settings"
  {
    printf '<?xml version="1.0"?>\n<!-- Gerado pelo FliperOS Setup (Frontend). -->\n<systemList>\n'
    while IFS='|' read -r key dir platform name exe args exts; do
      printf '  <system>\n    <name>%s</name>\n    <fullname>%s</fullname>\n    <path>%s</path>\n' \
        "${key//\//-}" "$(xml_escape "$name")" "$dir"
      exts=${exts//;/ }
      printf '    <extension>%s %s</extension>\n' "$exts" "${exts^^}"
      printf '    <command label="%s">%s</command>\n' "$(xml_escape "$name")" \
        "$(xml_escape "$(frontends_esde_command "$exe $args")")"
      printf '    <platform>%s</platform>\n    <theme>%s</theme>\n  </system>\n' "$platform" "$platform"
      systems+=("${key//\//-}|$platform")
      n=$((n + 1))
    done < <(frontends_systems)
    printf '</systemList>\n'
  } > "$ESDE_DIR/custom_systems/es_systems.xml"
  for key in "${systems[@]}"; do
    # shellcheck disable=SC2086 # um par por palavra
    media_farm "$MEDIA_DIR/.es-de/${key%%|*}" "${key#*|}" $ESDE_MEDIA_LINKS
  done
  esde_setting ROMDirectory "$ROMS_DIR"
  esde_setting MediaDirectory "$MEDIA_DIR/.es-de"
  frontends_esde_240p
  chown -R "$FLIPEROS_USER:" "$ESDE_DIR" 2> /dev/null
  log_info "ES-DE: $n sistema(s)"
}

# esde_setting NOME VALOR [string|bool] grava uma opcao no es_settings.xml.
esde_setting() {
  local settings="$ESDE_DIR/settings/es_settings.xml" kind=${3:-string} line
  line="<$kind name=\"$1\" value=\"$2\" />"
  mkdir -p "$ESDE_DIR/settings"
  if [[ ! -f $settings ]]; then
    printf '<?xml version="1.0"?>\n%s\n' "$line" > "$settings"
  elif grep -q "name=\"$1\"" "$settings"; then
    sed -i "s|<$kind name=\"$1\" value=\"[^\"]*\" />|$line|" "$settings"
  else
    printf '%s\n' "$line" >> "$settings"
  fi
}

ATTRACTPLUS=${ATTRACTPLUS:-attractplus}

# frontends_attract: o emulador e a tela de cada pasta no Attract-Mode Plus
# (os mesmos que o scraper cria; o que ja existe fica). Uma tela sem lista
# de jogos ganha a que o proprio Attract-Mode monta dos arquivos da pasta
# (--build-romlist); a do Scraper, com titulo, ano e arte, fica.
frontends_attract() {
  local key dir platform name n=0
  while IFS='|' read -r key dir platform _; do
    name=$(scraper_attract_prepare "$key" "$dir" "$platform") || continue
    n=$((n + 1))
    if [[ ! -s $ATTRACT_DIR/romlists/$name.txt ]] && have "$ATTRACTPLUS"; then
      runuser -u "$FLIPEROS_USER" -- "$ATTRACTPLUS" --build-romlist "$name" -o "$name" >> "$FLIPEROS_LOG" 2>&1
    fi
  done < <(frontends_systems)
  log_info "Attract-Mode Plus: $n sistema(s)"
}

# ── ROM List do Attract-Mode Plus ────────────────────────────────
# Setup > AttractPlus ROM List: a romlist de cada pasta de arcade com o nome
# de verdade de cada jogo (o --build-romlist do Attract-Mode so poe o nome
# do arquivo), do -listxml do GroovyMAME (fliperos-romclean romlist). A
# pasta do core mame2010 le primeiro o XML do 0.139. Uma romlist a mais,
# ATTRACT_ROMLIST_ALL, junta todas numa tela so.
ATTRACT_ROMLIST_ALL=${ATTRACT_ROMLIST_ALL:-Arcade}

# frontends_romlist_systems imprime "chave|pasta|plataforma|quantidade|emulador"
# das pastas de arcade com jogos.
frontends_romlist_systems() {
  local key dir platform count name
  while IFS='|' read -r key dir platform count; do
    scraper_arcade "$key" || continue
    IFS='|' read -r name _ <<< "$(scraper_attract_emulator "$key")"
    [[ -n $name ]] && printf '%s|%s|%s|%s|%s\n' "$key" "$dir" "$platform" "$count" "$name"
  done < <(scraper_detect)
  return 0
}

# frontends_romlist RESULTADO SISTEMA... (linhas do frontends_romlist_systems)
# cria o emulador e a tela que faltam e grava as romlists, falando com a tela
# de progresso. RESULTADO ganha "emulador<TAB>jogos<TAB>clones<TAB>fora do XML"
# por pasta e "total<TAB>jogos". Os clones sem arquivo proprio (romset
# merged) so entram no MAME: o GroovyMAME abre o jogo pelo nome e acha o
# clone no zip do pai; os outros emuladores abrem o arquivo.
frontends_romlist() {
  local result=$1 line key dir platform count name xml catver
  local -a specs=() source=()
  shift
  ev_step 0 "Preparing Attract-Mode Plus"
  for line in "$@"; do
    IFS='|' read -r key dir platform count name <<< "$line"
    name=$(scraper_attract_prepare "$key" "$dir" "$platform") || continue
    xml=main
    [[ $key == retroarch/mame2010 && -f $MAME2010_XML ]] && xml=alt
    specs+=(--system "$name|$dir|$xml|$([[ $key == mame ]] && echo 1 || echo 0)")
  done
  ((${#specs[@]})) || ev_fail "No arcade folder with games" || return 1
  scraper_attract_display "$ATTRACT_ROMLIST_ALL"
  mapfile -t source < <(romclean_xml_args groovymame)
  [[ -f $MAME2010_XML ]] && source+=(--alt-xml "$MAME2010_XML" --alt-cache "$ROMCLEAN_CACHE/romclean-mame2010.json")
  catver=$(romclean_data_find catver.ini "$ROMS_DIR/mame") && source+=(--catver "$catver")
  log_info "AttractPlus ROM List: $*"
  if ! "$ROMCLEAN" romlist "${source[@]}" "${specs[@]}" --out "$ATTRACT_DIR/romlists" \
    --combined "$ATTRACT_ROMLIST_ALL" --progress --result "$result" 2>> "$FLIPEROS_LOG"; then
    ev_fail "Could not read the GroovyMAME game list (details in the log)"
    return 1
  fi
  chown -R "$FLIPEROS_USER:" "$ATTRACT_DIR" 2> /dev/null
  return 0
}

# frontends_configure NOME grava os sistemas no frontend (os que precisam).
frontends_configure() {
  case $1 in
    attractplus) frontends_attract ;;
    pegasus) frontends_pegasus ;;
    emulationstation) frontends_esde ;;
  esac
  return 0
}

# frontends_hint NOME imprime as linhas a mais da mensagem final do Setup >
# Frontend, para quem nao usa as pastas dos emuladores do FliperOS: o
# Fightcade tem as ROMs dele (config/fliperos-roms) e nao sai com Esc.
frontends_hint() {
  case $1 in
    fightcade)
      printf '%s\n' "" "Its ROMs go in $ROMS_DIR/fightcade, one folder per emulator." \
        "It needs a keyboard and a mouse; Ctrl+W closes it."
      ;;
  esac
  return 0
}

# xml_escape TEXTO: &, < e > para XML.
xml_escape() {
  local s=$1
  s=${s//&/&amp;}
  s=${s//</&lt;}
  printf '%s\n' "${s//>/&gt;}"
}
