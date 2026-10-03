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
  chown -R "$FLIPEROS_USER:" "$PEGASUS_DIR" 2> /dev/null
  log_info "Pegasus: ${#dirs[@]} pasta(s) de jogos"
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
  chown -R "$FLIPEROS_USER:" "$ESDE_DIR" 2> /dev/null
  log_info "ES-DE: $n sistema(s)"
}

# esde_setting NOME VALOR grava uma opcao de texto no es_settings.xml.
esde_setting() {
  local settings="$ESDE_DIR/settings/es_settings.xml" line
  line="<string name=\"$1\" value=\"$2\" />"
  if [[ ! -f $settings ]]; then
    printf '<?xml version="1.0"?>\n%s\n' "$line" > "$settings"
  elif grep -q "name=\"$1\"" "$settings"; then
    sed -i "s|<string name=\"$1\" value=\"[^\"]*\" />|$line|" "$settings"
  else
    printf '%s\n' "$line" >> "$settings"
  fi
}

# frontends_attract: o emulador e a tela de cada pasta no Attract-Mode Plus
# (os mesmos que o scraper cria; o que ja existe fica).
frontends_attract() {
  local key dir platform n=0
  while IFS='|' read -r key dir platform _; do
    scraper_attract_prepare "$key" "$dir" "$platform" > /dev/null && n=$((n + 1))
  done < <(frontends_systems)
  log_info "Attract-Mode Plus: $n sistema(s)"
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

# xml_escape TEXTO: &, < e > para XML.
xml_escape() {
  local s=$1
  s=${s//&/&amp;}
  s=${s//</&lt;}
  printf '%s\n' "${s//>/&gt;}"
}
