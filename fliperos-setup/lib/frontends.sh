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
# pelo Setup > Games > Frontend.
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
# link por tipo para a pasta do sistema em ~/media).
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
      printf '    <platform>%s</platform>\n    <theme>%s</theme>\n  </system>\n' "$platform" \
        "$(frontends_esde_theme "$key" "$platform")"
      systems+=("$key")
      n=$((n + 1))
    done < <(frontends_systems)
    printf '</systemList>\n'
  } > "$ESDE_DIR/custom_systems/es_systems.xml"
  for key in "${systems[@]}"; do
    # shellcheck disable=SC2086 # um par por palavra
    media_farm "$MEDIA_DIR/.es-de/${key//\//-}" "$key" $ESDE_MEDIA_LINKS
  done
  esde_setting ROMDirectory "$ROMS_DIR"
  esde_setting MediaDirectory "$MEDIA_DIR/.es-de"
  frontends_esde_240p
  chown -R "$FLIPEROS_USER:" "$ESDE_DIR" 2> /dev/null
  log_info "ES-DE: $n sistema(s)"
}

# frontends_esde_theme CHAVE PLATAFORMA imprime a pasta do sistema nos temas
# do ES-DE (o logo e o fundo dele). A plataforma e a do Skyscraper, e para
# ele o Model 2, o Model 3 e os cores de MAME sao "arcade": com ela no
# <theme>, todos saiam com o logo de arcade. Os temas tem model2, model3,
# mame, fbneo e fba; os cores de MAME ficam com o do MAME (a pasta do
# GroovyMAME segue com o de arcade), o FBNeo com o dele.
frontends_esde_theme() {
  case $1 in
    model2 | model3) echo "$1" ;;
    retroarch/fbneo*) echo fbneo ;;
    retroarch/*)
      if [[ $(scraper_core_info "${1#retroarch/}" systemid) =~ ^(mame|hbmame)$ ]]; then
        echo mame
      else
        echo "$2"
      fi
      ;;
    *) echo "$2" ;;
  esac
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
ARCADEFLOW=${ARCADEFLOW:-/opt/fliperos/bin/fliperos-arcadeflow}

# frontends_attract_theme baixa o Arcadeflow, o tema padrao das telas do
# Attract-Mode Plus (nao vem com o FliperOS: config/fliperos-arcadeflow),
# falando com a tela de progresso por eventos. Ja instalado, nao faz nada.
frontends_attract_theme() {
  [[ $(scraper_attract_layout) == Arcadeflow ]] && return 0
  ev_step 0 "Starting"
  "$ARCADEFLOW" fetch --progress 2>> "$FLIPEROS_LOG"
}

# frontends_attract: o emulador e a tela de cada pasta no Attract-Mode Plus
# (os mesmos que o scraper cria; o que ja existe fica). Uma tela sem lista
# de jogos ganha a que o proprio Attract-Mode monta dos arquivos da pasta
# (--build-romlist); a do Scraper, com titulo, ano e arte, fica.
frontends_attract() {
  local key dir platform n=0
  frontends_attract_prune
  while IFS='|' read -r key dir platform _; do
    frontends_attract_system "$key" "$dir" "$platform" > /dev/null || continue
    n=$((n + 1))
  done < <(frontends_systems)
  frontends_attract_empty
  frontends_attract_defaults
  frontends_arcadeflow_sync
  frontends_arcadeflow_systems
  log_info "Attract-Mode Plus: $n sistema(s)"
}

# frontends_arcadeflow_systems: o logotipo de cada tela no menu de telas do
# Arcadeflow, que o acha pelo nome da tela entre os sistemas que ele conhece:
# "Model 2" ele conhece; "Supermodel" e "Arcade (various) (MAME 2010
# (0.139))", nao. Diz ao tema (config/fliperos-arcadeflow systems) de que
# sistema e cada tela do FliperOS, com os nomes dele: a placa do emulador
# (Model 3, GameCube), o FBNeo no core dele e, nos outros, a plataforma da
# pasta ou o nome do sistema do core. Um core de MAME ganha um sistema so
# dele ("TELA<tab>TITULO|..."), com a arte do MAME e o resto do nome por cima.
frontends_arcadeflow_systems() {
  local key platform name core corename systems title
  [[ -f $ATTRACT_DIR/layouts/Arcadeflow/data_systems.txt ]] || return 0
  while IFS='|' read -r key _ platform name _; do
    title=""
    case $key in
      mame) systems=mame ;;
      model2) systems="sega model 2" ;;
      model3) systems="sega model 3" ;;
      naomi2) systems="naomi 2" ;;
      dolphin) systems=gamecube ;;
      retroarch/*)
        core=${key#retroarch/}
        corename=$(scraper_core_info "$core" corename)
        systems="$platform|$(scraper_core_info "$core" systemname)"
        if [[ $platform == arcade || $platform == fba ]]; then
          case ${corename,,} in
            mame*)
              # Um core de MAME e um MAME a parte, com o nome dele sem a
              # versao ("MAME 2010 (0.139)": MAME 2010): nao outro "MAME" ao
              # lado do do GroovyMAME.
              systems="mame|arcade"
              title=${corename%% (*}
              ;;
            *finalburn*neo* | fbneo*) systems="fbneo|arcade" ;;
            *) systems="arcade" ;;
          esac
        fi
        ;;
      *) systems=$platform ;;
    esac
    printf '%s%s|%s\n' "$name" "${title:+$'\t'$title}" "$systems"
  done < <(frontends_systems) | "$ARCADEFLOW" systems 2>> "$FLIPEROS_LOG"
  return 0
}

# frontends_attract_defaults: os padroes do FliperOS no Attract-Mode Plus, a
# cada abertura do launcher (fliperos-setup --session-start) e ao gravar as
# telas. Nao com ele aberto.
# - Toda tela no Arcadeflow (com o tema instalado): as que estao no Basic ou
#   no BasicPlus, o layout que o Attract-Mode Plus da as telas que ele mesmo
#   cria. A de outro layout, escolhido pela pessoa, fica.
# - O que o tema instalado ainda nao recebeu do FliperOS: as opcoes e a linha
#   que mostra a lista de clones de um jogo (fliperos-arcadeflow prefs).
frontends_attract_defaults() {
  local acfg
  pgrep -x "${ATTRACTPLUS##*/}" > /dev/null 2>&1 && return 0
  [[ $(scraper_attract_layout) == Arcadeflow ]] || return 0
  "$ARCADEFLOW" prefs 2>> "$FLIPEROS_LOG"
  for acfg in "$ATTRACT_DIR/attract.cfg" "$ATTRACT_DIR/config/displays.cfg"; do
    [[ -f $acfg ]] && grep -qE '^[[:space:]]+layout[[:space:]]+Basic(Plus)?[[:space:]]*$' "$acfg" || continue
    sed -i -E 's/^([[:space:]]+layout[[:space:]]+)Basic(Plus)?[[:space:]]*$/\1Arcadeflow/' "$acfg"
    chown "$FLIPEROS_USER:" "$acfg" 2> /dev/null
    log_info "Attract-Mode Plus: telas de ${acfg##*/} no Arcadeflow"
  done
  return 0
}

# frontends_attract_empty: a romlist sem nenhum jogo sai (com o banco do
# Arcadeflow e as telas dela), e depois o emulador sem romlist.
# Na primeira execucao o Attract-Mode Plus cria um emulador, uma romlist e
# uma tela para cada programa que acha no sistema (mame, flycast, pcsx2...),
# com a pasta de ROMs dele e nao a do FliperOS: telas vazias ao lado das do
# Setup. As colecoes do Arcadeflow ("AF ...") sao dele. Sem o Attract-Mode
# Plus instalado nao ha quem monte a lista, e nada sai; nao com ele aberto.
frontends_attract_empty() {
  local list name cfg acfg display
  local -A used=()
  have "$ATTRACTPLUS" || return 0
  pgrep -x "${ATTRACTPLUS##*/}" > /dev/null 2>&1 && return 0
  for list in "$ATTRACT_DIR"/romlists/*.txt; do
    [[ -f $list ]] || continue
    name=${list##*/}
    name=${name%.txt}
    [[ $name == "AF "* ]] && continue
    grep -qv -e '^#' -e '^[[:space:]]*$' "$list" && continue
    rm -f "${list%.txt}".{txt,db1,db2,tag}
    for acfg in "$ATTRACT_DIR/attract.cfg" "$ATTRACT_DIR/config/displays.cfg"; do
      [[ -f $acfg ]] || continue
      while IFS= read -r display; do
        scraper_attract_display_remove "$acfg" "$display"
      done < <(scraper_attract_romlist_displays "$acfg" "$name")
    done
    log_info "Attract-Mode Plus: romlist $name vazia, apagada"
  done
  # Fica o emulador com romlist do nome dele e o que aparece na coluna
  # Emulator de outra (a lista ATTRACT_ROMLIST_ALL, as colecoes).
  for list in "$ATTRACT_DIR"/romlists/*.txt; do
    [[ -f $list ]] || continue
    name=${list##*/}
    used[${name%.txt}]=1
  done
  while IFS= read -r name; do
    used[$name]=1
  done < <(cat "$ATTRACT_DIR"/romlists/*.txt 2> /dev/null | awk -F';' '!/^#/ && $3 != "" { sub(/\r$/, "", $3); print $3 }' | sort -u)
  for cfg in "$ATTRACT_DIR"/emulators/*.cfg; do
    [[ -f $cfg ]] || continue
    name=${cfg##*/}
    name=${name%.cfg}
    [[ -n ${used[$name]:-} ]] && continue
    rm -f "$cfg"
    log_info "Attract-Mode Plus: emulador $name sem romlist, removido"
  done
  return 0
}

# frontends_attract_prune: uma pasta que ficou sem jogos sai do Attract-Mode
# Plus. O emulador que o Setup criou para ela, a tela, a romlist (com o banco
# do Arcadeflow) e os jogos dela na lista ATTRACT_ROMLIST_ALL sao apagados; a
# tela seguia la, com jogos que nao abrem. Um emulador da pessoa (sem o
# cabecalho do Setup) e uma pasta que nao existe agora (um disco fora) ficam.
# Nao com o Attract-Mode aberto.
frontends_attract_prune() {
  local cfg name dir acfg all rest
  pgrep -x "${ATTRACTPLUS##*/}" > /dev/null 2>&1 && return 0
  for cfg in "$ATTRACT_DIR"/emulators/*.cfg; do
    [[ -f $cfg ]] && head -1 "$cfg" | grep -q '^# Criado pelo FliperOS Setup' || continue
    dir=$(awk '$1 == "rompath" { sub(/^rompath[ \t]+/, ""); print; exit }' "$cfg")
    dir=${dir%/}
    [[ -n $dir && -d $dir ]] || continue
    (($(scraper_count "$dir") > 0)) && continue
    name=${cfg##*/}
    name=${name%.cfg}
    rm -f "$cfg" "$ATTRACT_DIR/romlists/$name".{txt,db1,db2,tag}
    for acfg in "$ATTRACT_DIR/attract.cfg" "$ATTRACT_DIR/config/displays.cfg"; do
      scraper_attract_display_remove "$acfg" "$name"
    done
    all="$ATTRACT_DIR/romlists/$ATTRACT_ROMLIST_ALL.txt"
    if [[ -f $all ]]; then
      rest=$(awk -F';' -v e="$name" 'NR == 1 || $3 != e' "$all"; printf x)
      printf '%s' "${rest%x}" > "$all"
    fi
    log_info "Attract-Mode Plus: $name sem jogos, saiu das telas"
  done
  return 0
}

# O Arcadeflow nao le o titulo, o ano e o genero da romlist a cada vez: guarda
# o que leu em romlists/<emulador>.db1 e depois so acrescenta os jogos que
# faltam nele. Uma romlist refeita (ROM List, Scraper) seguia na tela com o
# nome do arquivo de antes, sem ano nem fabricante.
# frontends_arcadeflow_sync esvazia o .db1 mais velho que a romlist: o tema le
# de novo todos os jogos dela ao abrir a tela, e o .db2 (favoritos, vezes
# jogadas, ultima vez) fica. Sem .db2 o .db1 sai, e o tema refaz os dois. Nao
# com o Attract-Mode aberto (o tema regrava o banco); fica para a vez
# seguinte, no fliperos-setup --session-start.
frontends_arcadeflow_sync() {
  local list db n=0
  pgrep -x "${ATTRACTPLUS##*/}" > /dev/null 2>&1 && return 0
  for list in "$ATTRACT_DIR"/romlists/*.txt; do
    db=${list%.txt}.db1
    [[ -f $db ]] || continue
    if [[ ! $list -nt $db ]]; then
      frontends_arcadeflow_fill "$list" "$db"
      continue
    fi
    if [[ -f ${list%.txt}.db2 ]]; then
      printf 'return({\n})\n' > "$db"
    else
      rm -f "$db"
    fi
    n=$((n + 1))
  done
  ((n)) && log_info "Arcadeflow: $n romlist(s) para ler de novo"
  return 0
}

# frontends_arcadeflow_fill ROMLIST DB1: o scraper do Arcadeflow troca o
# titulo, o ano, o fabricante, o genero, os jogadores, a rotacao, o controle e
# os botoes do jogo pelo que o ArcadeDB responde, e sem resposta grava vazio:
# o jogo raspado ficava sem nome e sem os indicadores do topo (jogadores,
# controle, botoes). O campo vazio no .db1 volta a ter o valor da romlist; o
# que o scraper preencheu fica. Reescreve no lugar, so se houver o que mudar.
frontends_arcadeflow_fill() {
  local list=$1 db=$2 tmp
  grep -q '^      z_[a-z]* = ""$' "$db" || return 0
  tmp=$(mktemp) || return 0
  if awk -v list="$list" '
    BEGIN {
      col["z_title"] = 2; col["z_year"] = 5; col["z_manufacturer"] = 6; col["z_category"] = 7
      col["z_players"] = 8; col["z_rotation"] = 9; col["z_control"] = 10; col["z_buttons"] = 17
      while ((getline line < list) > 0) {
        sub(/\r$/, "", line)
        if (line ~ /^#/ || split(line, f, ";") < 2) continue
        for (key in col) {
          v = f[col[key]]
          gsub(/"/, "\047", v)
          if (v != "" && v !~ /\\/) val[f[1], key] = v
        }
      }
    }
    /^   "[^"]+" : [{]$/ { name = $0; sub(/^   "/, "", name); sub(/" : [{]$/, "", name) }
    /^      z_[a-z]+ = ""$/ && ((name, $1) in val) { printf "      %s = \"%s\"\n", $1, val[name, $1]; next }
    { print }' "$db" > "$tmp" && ! cmp -s "$tmp" "$db"; then
    cat "$tmp" > "$db"
    log_info "Arcadeflow: ${db##*/} com os campos da romlist de volta"
  fi
  rm -f "$tmp"
  return 0
}

# O modo de video do console, "LARGURA,ALTURA": o do boot, em que os
# frontends em KMS abrem (config/fliperos-kms-run).
FB_SIZE=${FLIPEROS_FB_SIZE:-/sys/class/graphics/fb0/virtual_size}

# frontends_arcadeflow_screen: num tubo de 15 kHz em modo de pixel largo
# (640x240) o Arcadeflow desenha em 4:3 e a imagem e esticada ate a largura
# do modo (config/fliperos-arcadeflow screen); em outro modo ou monitor,
# volta ao tamanho da tela. O modo e o do console agora ou, sem ele, o
# escolhido no Video Setup. A cada abertura do launcher (fliperos-setup
# --session-start): o modo de boot pode ter mudado.
frontends_arcadeflow_screen() {
  local w="" h=""
  [[ -f $ATTRACT_DIR/layouts/Arcadeflow/layout.nut ]] || return 0
  if ! frontends_crt; then
    "$ARCADEFLOW" screen 2>> "$FLIPEROS_LOG"
    return 0
  fi
  [[ -r $FB_SIZE ]] && IFS=', ' read -r w h _ < "$FB_SIZE"
  [[ $w =~ ^[1-9][0-9]*$ && $h =~ ^[1-9][0-9]*$ ]] || read -r w h _ <<< "$(geometry_mode)"
  "$ARCADEFLOW" screen "$w" "$h" 2>> "$FLIPEROS_LOG"
  return 0
}

# frontends_attract_system CHAVE PASTA PLATAFORMA: o emulador, a tela e (se
# faltar) a lista de jogos de uma pasta; imprime o nome do emulador.
frontends_attract_system() {
  local name
  name=$(scraper_attract_prepare "$1" "$2" "$3") || return 1
  if [[ ! -s $ATTRACT_DIR/romlists/$name.txt ]] && have "$ATTRACTPLUS"; then
    runuser -u "$FLIPEROS_USER" -- "$ATTRACTPLUS" --build-romlist "$name" -o "$name" >> "$FLIPEROS_LOG" 2>&1
  else
    frontends_attract_refresh "$1" "$2" "$name"
  fi
  printf '%s\n' "$name"
}

# frontends_attract_refresh CHAVE PASTA EMULADOR: a lista que ja existe segue
# a pasta. O jogo copiado depois de a lista ser feita entra nela, com o nome
# do arquivo (como no --build-romlist), e o que saiu da pasta sai da lista; as
# outras linhas ficam como estao (o titulo e o ano do Scraper). Vale o romext
# do emulador, na pasta e nao nas de dentro dela, como o Attract-Mode le.
# A lista de arcade com os nomes de verdade (ROM List, Scraper) nao: ela nao
# tem os BIOS da pasta e tem os clones sem arquivo de um romset merged; quem
# a refaz e o Setup > Games > AttractPlus ROM List. Uma pasta que nao existe agora
# (um disco fora) ou sem nenhum jogo nao mexe na lista.
frontends_attract_refresh() {
  local key=$1 dir=$2 name=$3 list cfg exts tmp
  list="$ATTRACT_DIR/romlists/$name.txt"
  cfg="$ATTRACT_DIR/emulators/$name.cfg"
  [[ -s $list && -f $cfg && -d $dir ]] || return 0
  if scraper_arcade "$key" && awk -F';' '!/^#/ && NF > 1 && $2 != $1 { f = 1; exit } END { exit !f }' "$list"; then
    return 0
  fi
  exts=$(awk '$1 == "romext" { sub(/^romext[ \t]+/, ""); sub(/[ \t\r]+$/, ""); print; exit }' "$cfg")
  [[ -n $exts ]] || return 0
  tmp=$(mktemp) || return 0
  if find -H "$dir" -maxdepth 1 -type f ! -name '.*' ! -name '*;*' -printf '%f\n' 2> /dev/null | LC_ALL=C sort |
    awk -v exts="$exts" -v list="$list" -v emulator="$name" '
      BEGIN { n = split(tolower(exts), ext, ";"); fields = 21 }
      {
        for (i = 1; i <= n; i++) {
          l = length(ext[i])
          if (l && length($0) > l && tolower(substr($0, length($0) - l + 1)) == ext[i]) {
            rom = substr($0, 1, length($0) - l)
            if (!(rom in have)) { have[rom] = 1; order[++roms] = rom }
            break
          }
        }
      }
      END {
        if (!roms) exit 1
        while ((getline line < list) > 0) {
          if (line ~ /^#/) {
            if (!lines) fields = split(line, f, ";")
          } else if (line !~ /^[ \t\r]*$/) {
            split(line, f, ";")
            if (!(f[1] in have)) continue
            seen[f[1]] = 1
          }
          out[++lines] = line
        }
        for (i = 1; i <= lines; i++) print out[i]
        for (i = 1; i <= roms; i++) {
          if (order[i] in seen) continue
          line = order[i] ";" order[i] ";" emulator
          for (j = 3; j < fields; j++) line = line ";"
          print line
        }
      }' > "$tmp" && ! cmp -s "$tmp" "$list"; then
    cat "$tmp" > "$list"
    log_info "Attract-Mode Plus: lista $name acertada com a pasta ($(grep -cv '^#' "$list") jogos)"
  fi
  rm -f "$tmp"
  return 0
}

# ── ROM List do Attract-Mode Plus ────────────────────────────────
# Setup > Games > AttractPlus ROM List: a romlist de cada pasta de arcade com o nome
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
  # As outras pastas com jogos (consoles, as de arcade nao marcadas): o
  # emulador, a tela e a lista que faltarem, para todo sistema aparecer.
  frontends_attract
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

# frontends_hint NOME imprime as linhas a mais da mensagem final do Setup > Games >
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
