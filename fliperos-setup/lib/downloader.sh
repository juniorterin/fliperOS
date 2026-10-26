# shellcheck shell=bash
# Setup > Games > Downloader > ROM/CHD MAME torrent: o romset do MAME e a colecao de CHDs por link
# magnetico (um link para cada), baixando so o que o filtro do MAME ROM
# Cleaner escolhe. O download e do Transmission (servico
# fliperos-transmission); a logica, o config/fliperos-downloader. Aqui ficam
# o filtro salvo e o servico.

DOWNLOADER=${DOWNLOADER:-/opt/fliperos/bin/fliperos-downloader}
DOWNLOADER_STATE=${DOWNLOADER_STATE:-/var/lib/fliperos/downloader}
DOWNLOADER_SERVICE=fliperos-transmission.service
# Os links que vem na imagem (config/fliperos-downloader-magnets).
DOWNLOADER_MAGNETS=${DOWNLOADER_MAGNETS:-/usr/local/share/fliperos/downloader-magnets}

# downloader ARGS... roda o fliperos-downloader com o estado desta maquina.
downloader() {
  FLIPEROS_DOWNLOADER_STATE=$DOWNLOADER_STATE "$DOWNLOADER" "$@"
}

# downloader_default_magnet roms|chds imprime o link que vem na imagem
# (vazio sem ele).
downloader_default_magnet() {
  [[ -f $DOWNLOADER_MAGNETS ]] || return 0
  awk -F'\t' -v k="$1" '$1 == k { print $2; exit }' "$DOWNLOADER_MAGNETS"
}

# downloader_prepare: a pasta do estado e do usuario, porque o servico (do
# usuario) grava nela quando um download termina.
downloader_prepare() {
  install -d -m 755 "$DOWNLOADER_STATE" 2> /dev/null || mkdir -p "$DOWNLOADER_STATE"
  chown "$FLIPEROS_USER:" "$DOWNLOADER_STATE" 2> /dev/null || true
}

# downloader_service_on: o servico no ar, antes de cadastrar um link ou de
# comecar um download. So sobe assim, quando um download e pedido: nunca no
# boot (o fliperos-rootfs.sh tira o "enabled" de versoes anteriores), e sai
# sozinho quando o ultimo torrent termina (o session-close do
# config/fliperos-downloader).
downloader_service_on() {
  systemctl start "$DOWNLOADER_SERVICE" >> "$FLIPEROS_LOG" 2>&1
}

# downloader_service_sync: sem nenhum link cadastrado nem pacote de arte
# baixando (lib/mediapacks.sh), o servico sai.
downloader_service_sync() {
  compgen -G "$DOWNLOADER_STATE/*.json" > /dev/null && return 0
  compgen -G "${MEDIAPACKS_STATE:-/var/lib/fliperos/mediapacks}/*.json" > /dev/null && return 0
  systemctl stop "$DOWNLOADER_SERVICE" >> "$FLIPEROS_LOG" 2>&1 || true
}

# downloader_filter_get CHAVE imprime um valor do filtro salvo (target,
# dest, preset ou um parametro do ROM cleaner). Status 1 = sem filtro.
downloader_filter_get() {
  [[ -f $DOWNLOADER_STATE/filter.kv ]] || return 1
  sed -n "s/^$1=//p" "$DOWNLOADER_STATE/filter.kv" | tail -1
}

downloader_filter_label() {
  local preset
  preset=$(downloader_filter_get preset) || {
    echo "not chosen yet"
    return 0
  }
  printf '%s, %s\n' "$(romclean_preset_label "$preset")" "$(romclean_target_label "$(downloader_filter_get target)")"
}

# downloader_filter_save ALVO DESTINO PRESET CHAVE=VALOR...: grava o filtro
# (filter.kv, para a tela) e as opcoes do fliperos-romclean que ele vira:
# filter.scan (as ROMs: o XML, os arquivos de dados, os destinos e os
# filtros) e filter.chds (o XML e as pastas de ROMs onde entram os CHDs).
downloader_filter_save() {
  local target=$1 dest=$2 preset=$3 f dir
  shift 3
  downloader_prepare
  {
    printf '%s\n' "target=$target" "dest=$dest" "preset=$preset" "$@"
  } > "$DOWNLOADER_STATE/filter.kv"
  {
    romclean_xml_args "$target" ""
    romclean_data_args
    romclean_target_args "$target" "$dest"
    romclean_args "$target" "$@"
  } > "$DOWNLOADER_STATE/filter.scan"
  {
    romclean_xml_args "$target" ""
    while IFS= read -r dir; do
      printf '%s\n' --roms "$dir"
    done < <(romclean_chd_folders "$target" "$dest")
  } > "$DOWNLOADER_STATE/filter.chds"
  for f in filter.kv filter.scan filter.chds; do
    chown "$FLIPEROS_USER:" "$DOWNLOADER_STATE/$f" 2> /dev/null || true
  done
  log_info "Downloader: filtro salvo ($target, $preset, $dest)"
}

# downloader_filter_default: o preset "Joystick cabinet" do GroovyMAME, para
# um link cadastrado antes de escolher o filtro.
downloader_filter_default() {
  local -a kv
  romclean_data_load "$ROMCLEAN_DATA"
  mapfile -t kv < <(romclean_preset cabinet groovymame)
  downloader_filter_save groovymame "$(romclean_default_dest groovymame)" cabinet "${kv[@]}"
}

# downloader_dest imprime a pasta final dos downloads: a escolhida em
# Download folder (gravada no filtro) ou a padrao do emulador.
downloader_dest() {
  local dest target
  target=$(downloader_filter_get target) && [[ -n $target ]] || target=groovymame
  dest=$(downloader_filter_get dest) && [[ -n $dest ]] || dest=$(romclean_default_dest "$target")
  printf '%s\n' "$dest"
}

downloader_dest_label() {
  local target
  target=$(downloader_filter_get target) && [[ -n $target ]] || target=groovymame
  romclean_dest_label "$target" "$(downloader_dest)"
}

# downloader_filter_set_dest PASTA: troca so a pasta final do filtro salvo
# (sem filtro ainda, comeca pelo preset padrao).
downloader_filter_set_dest() {
  local -a kv
  downloader_filter_get preset > /dev/null || downloader_filter_default
  romclean_data_load "$ROMCLEAN_DATA"
  mapfile -t kv < <(grep -vE '^(target|dest|preset)=' "$DOWNLOADER_STATE/filter.kv")
  downloader_filter_save "$(downloader_filter_get target)" "$1" "$(downloader_filter_get preset)" "${kv[@]}"
}

# downloader_cli status|add TIPO LINK|start|remove TIPO [--delete-files]: o
# Downloader sem tela, pelas mesmas funcoes da tela do Setup (o painel web,
# config/fliperos-web, fliperos-setup --downloader). O start nao apaga nada
# (o prune so vem do Setup, depois de mudar o filtro).
downloader_cli() {
  local result kind
  downloader_prepare
  case ${1:-} in
    status)
      downloader_status
      printf 'filter=%s\n' "$(downloader_filter_label)"
      for kind in roms chds; do
        printf 'default_%s=%s\n' "$kind" "$(downloader_default_magnet "$kind")"
      done
      ;;
    add)
      [[ ${2:-} == roms || ${2:-} == chds ]] && [[ ${3:-} == magnet:\?* ]] || return 2
      downloader_service_on
      downloader_add "$2" "$3" || {
        downloader_service_sync
        return 1
      }
      ;;
    start)
      downloader_filter_get preset > /dev/null || {
        echo "No filter yet: choose it in Setup > Games > Downloader." >&2
        return 3
      }
      result=$(mktemp)
      downloader_start "$result" || {
        rm -f "$result"
        return 1
      }
      cat "$result"
      rm -f "$result"
      ;;
    remove)
      [[ ${2:-} == roms || ${2:-} == chds ]] || return 2
      if [[ ${3:-} == --delete-files ]]; then
        downloader remove "$2" --delete-files 2>> "$FLIPEROS_LOG"
      else
        downloader remove "$2" 2>> "$FLIPEROS_LOG"
      fi
      downloader_service_sync
      ;;
    *) return 2 ;;
  esac
}

# downloader_status imprime o andamento ("chave=valor": pct, state, line,
# roms_name, chds_name).
downloader_status() {
  downloader status 2>> "$FLIPEROS_LOG" || printf '%s\n' pct=0 state=none "line=The downloader did not answer"
}

# downloader_start RESULTADO: aplica o filtro e comeca (eventos de
# progresso); "tipo<TAB>wanted<TAB>arquivos<TAB>bytes" vai para RESULTADO.
downloader_start() {
  log_info "Downloader: aplicando o filtro"
  # Um download parado por um desligamento continua daqui.
  downloader_service_on
  downloader start --progress --result "$1" 2>> "$FLIPEROS_LOG"
}

# downloader_add TIPO LINK: cadastra o link e le a lista de arquivos dele
# (eventos de progresso).
downloader_add() {
  log_info "Downloader: link novo ($1)"
  downloader add "$1" "$2" --progress 2>> "$FLIPEROS_LOG"
}

# O navegador do Downloader (config/fliperos-browser): o Setup sai, o
# fliperos-tty1 abre o Falkon e, com ele fechado, o Setup reabre na tela do
# magnet link (screen_downloader_resume) com o link que foi clicado.
DOWNLOADER_BROWSER_PENDING=${DOWNLOADER_BROWSER_PENDING:-$DOWNLOADER_STATE/browser}
DOWNLOADER_BROWSER=${DOWNLOADER_BROWSER:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-browser}

# downloader_capture_file: onde o fliperos-magnet, como o usuario do
# gabinete, guarda o link clicado.
downloader_capture_file() {
  printf '%s/fliperos-magnet\n' "${DOWNLOADER_CAPTURE_DIR:-/run/user/$(id -u "$FLIPEROS_USER" 2> /dev/null || echo 1000)}"
}

# downloader_browser_ok: da para abrir o navegador daqui? So no menu do
# gabinete (quem abre e o fliperos-tty1) e com o Falkon instalado.
downloader_browser_ok() {
  ((${SETUP_MENU_LOOP:-0} == 1)) && have falkon && [[ -x $DOWNLOADER_BROWSER ]]
}

# downloader_filter_orientation: a orientacao do monitor mudou (Setup > Video
# Setup > Monitor Orientation). O filtro Screen do Downloader passa a ser o do
# monitor novo (romclean_screen_orientation); o preset "all", que e nao
# filtrar, fica como esta. Sem filtro salvo, nada.
downloader_filter_orientation() {
  local target dest preset line
  local -a kv=()
  [[ -f $DOWNLOADER_STATE/filter.kv ]] || return 0
  preset=$(downloader_filter_get preset)
  [[ $preset == all ]] && return 0
  target=$(downloader_filter_get target)
  dest=$(downloader_filter_get dest)
  while IFS= read -r line; do
    case $line in
      target=* | dest=* | preset=*) continue ;;
      orientation=*) line="orientation=$(romclean_screen_orientation)" ;;
    esac
    kv+=("$line")
  done < "$DOWNLOADER_STATE/filter.kv"
  romclean_data_load "$ROMCLEAN_DATA"
  downloader_filter_save "$target" "$dest" "$preset" "${kv[@]}"
}

# romclean_count_job ALVO DESTINO ORIGEM XML CHAVE=VALOR... conta quantos jogos
# o filtro em edicao escolhe e quanto ocupam (games=N, bytes=N), para o
# placar do painel do filtro. Sem ORIGEM e o Downloader: o filtro sobre a
# lista do torrent de ROMs (downloader count); com ela, o Cleaner: a previa
# do romset da pasta (romclean_scan). Pode demorar: roda em segundo plano.
romclean_count_job() {
  local target=$1 dest=$2 folder=$3 xml=$4 summary scan
  local -a args
  shift 4
  mapfile -t args < <(romclean_args "$target" "$@")
  if [[ -z $folder ]]; then
    scan=$(mktemp) || return 1
    {
      romclean_xml_args "$target" ""
      romclean_data_args
      romclean_target_args "$target" "$dest"
      printf '%s\n' "${args[@]}"
    } > "$scan"
    downloader count --scan "$scan" 2>> "$FLIPEROS_LOG"
    rm -f "$scan"
    return
  fi
  summary=$(romclean_scan "$folder" "$target" "$xml" "$dest" /dev/null "${args[@]}" 2>> "$FLIPEROS_LOG") || return 1
  printf 'games=%s\nbytes=%s\n' "$(romclean_value "$summary" move)" "$(romclean_value "$summary" move_bytes)"
}

# romclean_count_stop PID para a contagem (e o que ela abriu: o
# fliperos-downloader e o fliperos-romclean) quando o painel fecha antes.
romclean_count_stop() {
  local child
  for child in $(pgrep -P "$1" 2> /dev/null); do
    romclean_count_stop "$child"
  done
  kill "$1" 2> /dev/null
  return 0
}

# ── Download BIOS ─────────────────────────────────────────────────
# Setup > Games > Downloader > Download BIOS: as BIOS que faltam para os
# jogos de cada pasta de ~/roms, baixadas uma a uma do pacote de referencia
# (config/fliperos-bios-pack, um torrent do archive.org; a logica e o
# config/fliperos-bios). A checagem roda sozinha, em segundo plano, a cada
# vez que o menu do FliperOS abre (bios_auto_start), e na hora pela tela.
BIOS_TOOL=${BIOS_TOOL:-/opt/fliperos/bin/fliperos-bios}
BIOS_STATE=${BIOS_STATE:-/var/lib/fliperos/bios}
BIOS_PACK=${BIOS_PACK:-/usr/local/share/fliperos/bios-pack}

# bios_tool ARGS... roda o fliperos-bios com o estado e o pacote daqui.
bios_tool() {
  FLIPEROS_BIOS_STATE=$BIOS_STATE FLIPEROS_BIOS_PACK=$BIOS_PACK "$BIOS_TOOL" "$@"
}

# bios_core_firmware CORE imprime os firmwares que o .info do core lista
# (o caminho dentro da pasta system do RetroArch, que e a ~/bios), um por
# linha. Os opcionais tambem: sem eles o core usa uma BIOS imitada (HLE),
# pior que a de verdade, ou nao abre parte dos jogos (Sega CD, FDS).
bios_core_firmware() {
  awk -F' *= *' '$1 ~ /^firmware[0-9]+_path$/ { v = $2; gsub(/^"|"[[:space:]]*$/, "", v); if (v != "") print v }' \
    "$RA_INFO_DIR/${1}_libretro.info" 2> /dev/null
}

# bios_standalone PASTA imprime a subpasta de ~/bios e os arquivos do
# pacote que o emulador daquela pasta de ~/roms le, fora do RetroArch.
bios_standalone() {
  case $1 in
    # PCSX2: uma BIOS basta; a dos EUA (v1.60) e a europeia.
    ps2) echo "ps2 scph39001.bin SCPH30004R.bin" ;;
    # Flycast (Dreamcast.BiosPath).
    dreamcast) echo "dc dc/dc_boot.bin dc_flash.bin" ;;
  esac
  return 0
}

# bios_arcade_dest CHAVE PASTA imprime onde vao as BIOS e os dispositivos
# dos sets do MAME de uma pasta de arcade (onde o emulador os procura), ou
# nada numa pasta que nao e de sets do MAME.
bios_arcade_dest() {
  case $1 in
    mame) printf '%s\n' "$BIOS_ROOT/mame" ;;
    naomi | naomi2 | atomiswave) printf '%s\n' "$BIOS_ROOT/dc" ;;
    # O core FBNeo procura tambem na system/fbneo.
    retroarch/fbneo) printf '%s\n' "$BIOS_ROOT/fbneo" ;;
    # Os outros cores de MAME so as acham junto dos jogos.
    retroarch/*) scraper_arcade "$1" && printf '%s\n' "$2" ;;
  esac
  return 0
}

# bios_folders imprime "chave|pasta" de cada pasta de ~/roms com jogos.
bios_folders() {
  local dir key
  for dir in "$ROMS_ROOT"/*/ "$ROMS_ROOT"/retroarch/*/; do
    dir=${dir%/}
    key=${dir#"$ROMS_ROOT"/}
    # As do Fightcade (com os sets dele) e as de Custom games ficam de fora.
    [[ $key == retroarch || $key == fightcade || $key == custom ]] && continue
    scraper_has_files "$dir" && printf '%s|%s\n' "$key" "$dir"
  done
  return 0
}

# bios_plan ARQUIVO grava o "wants" do fliperos-bios (o que cada pasta com
# jogos pede, config/fliperos-bios). Eventos de progresso.
bios_plan() {
  local out=$1 key dir path sub files file dest name xml_key
  local -a source folder_args
  local -A arcade=() by_xml=()
  : > "$out"
  ev_step 0 "Looking at the game folders"
  while IFS='|' read -r key dir; do
    if [[ $key == retroarch/* ]]; then
      while IFS= read -r path; do
        printf 'fw\t%s\t%s\t%s\n' "$key" "$path" "$BIOS_ROOT/$path"
      done < <(bios_core_firmware "${key#retroarch/}") >> "$out"
    else
      read -r sub files <<< "$(bios_standalone "$key")"
      for file in $files; do
        printf 'fw\t%s\t%s\t%s\n' "$key" "$file" "$BIOS_ROOT/$sub/${file##*/}"
      done >> "$out"
    fi
    dest=$(bios_arcade_dest "$key" "$dir")
    [[ -n $dest ]] || continue
    arcade[$dir]="$key|$dest"
    # O XML do MAME de cada pasta: o do core mame2010 na dele, o do
    # GroovyMAME nas outras.
    xml_key=groovymame
    [[ $key == retroarch/mame2010 && -f $MAME2010_XML ]] && xml_key=mame2010
    by_xml[$xml_key]+="$dir"$'\n'
  done < <(bios_folders)
  # As BIOS e os dispositivos dos sets de cada pasta de arcade (com o XML
  # em cache, segundos; sem ele, o -listxml do GroovyMAME, um minuto).
  for xml_key in "${!by_xml[@]}"; do
    [[ $xml_key == groovymame ]] && ! have "$GROOVYMAME" && continue
    ev_step 10 "Reading the game list of $(romclean_target_label "$xml_key")"
    mapfile -t source < <(romclean_xml_args "$xml_key" "")
    folder_args=()
    while IFS= read -r dir; do
      [[ -n $dir ]] && folder_args+=(--folder "$dir")
    done <<< "${by_xml[$xml_key]}"
    while IFS=$'\t' read -r dir name; do
      [[ -n ${arcade[$dir]:-} && -n $name ]] || continue
      key=${arcade[$dir]%%|*}
      dest=${arcade[$dir]#*|}
      # A que ja esta junto dos jogos tambem vale (no GroovyMAME, as duas
      # pastas estao no rompath).
      printf 'set\t%s\t%s\t%s\t%s\t%s\t%s\n' "$key" "$name" "$dest/$name.zip" "$dest/$name.7z" \
        "$dir/$name.zip" "$dir/$name.7z"
    done < <(nice -n 10 "$ROMCLEAN" uses "${source[@]}" "${folder_args[@]}" --by-folder 2>> "$FLIPEROS_LOG") >> "$out"
  done
  return 0
}

# bios_check RESULTADO [--refresh]: a checagem da tela (eventos de
# progresso); o resumo do fliperos-bios vai para RESULTADO.
bios_check() {
  local result=$1 wants line rc
  shift
  wants=$(mktemp) || {
    ev_fail "No space for the list of BIOS"
    return 1
  }
  bios_plan "$wants"
  log_info "Download BIOS: $(grep -c '' "$wants") BIOS pedidas pelas pastas"
  # O andamento do fliperos-bios vai de 30 a 100% (antes, as pastas).
  bios_tool check --wants "$wants" --owner "$BIOS_ROOT" --progress --result "$result" "$@" 2>> "$FLIPEROS_LOG" |
    while IFS= read -r line; do
      if [[ $line =~ ^@step\ ([0-9]+)\ (.*)$ ]]; then
        printf '@step %d %s\n' $((30 + BASH_REMATCH[1] * 7 / 10)) "${BASH_REMATCH[2]}"
      elif [[ $line == @* ]]; then
        printf '%s\n' "$line"
      fi
    done
  rc=${PIPESTATUS[0]}
  rm -f "$wants"
  return "$rc"
}

# bios_cli status|list|check [--refresh]|auto on|off: Download BIOS sem tela
# (fliperos-setup --bios, o painel web). status: auto= e o resumo da ultima
# checagem (last.kv); list: o last.tsv; check: a checagem com eventos de
# progresso e, no fim, o resumo. Status 2: pedido errado.
bios_cli() {
  local result rc
  case ${1:-} in
    status)
      printf 'auto=%s\n' "$([[ $(conf_get bios_auto 2> /dev/null) == off ]] && echo off || echo on)"
      # Sem nenhuma checagem ainda, so o auto.
      cat "$BIOS_STATE/last.kv" 2> /dev/null || true
      ;;
    list) cat "$BIOS_STATE/last.tsv" 2> /dev/null || true ;;
    check)
      [[ -z ${2:-} || $2 == --refresh ]] || return 2
      if [[ ! -x $BIOS_TOOL ]]; then
        ev_fail "The BIOS downloader ($BIOS_TOOL) is missing"
        return 1
      fi
      mkdir -p "$BIOS_STATE"
      result=$(mktemp) || return 1
      bios_check "$result" ${2:+"$2"}
      rc=$?
      cat "$result" 2> /dev/null
      rm -f "$result"
      return "$rc"
      ;;
    auto)
      case ${2:-} in
        on)
          conf_set bios_auto on
          # A proxima abertura do menu checa de novo.
          rm -f "$BIOS_STATE/stamp"
          ;;
        off) conf_set bios_auto off ;;
        *) return 2 ;;
      esac
      ;;
    *) return 2 ;;
  esac
}

# bios_stamp imprime a marca das pastas de jogos e de BIOS (a data de cada
# uma muda quando um arquivo entra ou sai), do pacote e dos emuladores: a
# checagem automatica so roda quando ela muda.
bios_stamp() {
  {
    cat "$BIOS_PACK" 2> /dev/null
    find -L "$ROMS_ROOT" "$BIOS_ROOT" -maxdepth 2 -type d -printf '%p %T@\n' 2> /dev/null
    stat -L -c '%n %Y' "$RA_INFO_DIR" "$MAME2010_XML" "$(command -v "$GROOVYMAME")" 2> /dev/null
  } | md5sum | cut -d' ' -f1
}

# bios_auto: a checagem automatica (fliperos-setup --bios-check, que o menu
# abre em segundo plano). So quando as pastas mudaram desde a ultima; sem
# rede, de novo dali a 10 minutos. Desligada com bios_auto=off.
bios_auto() {
  local wants out rc
  [[ $(conf_get bios_auto 2> /dev/null) == off || ! -x $BIOS_TOOL ]] && return 0
  mkdir -p "$BIOS_STATE"
  [[ -f $BIOS_STATE/stamp && $(< "$BIOS_STATE/stamp") == "$(bios_stamp)" ]] && return 0
  [[ -n $(find "$BIOS_STATE/failed" -mmin -10 2> /dev/null) ]] && return 0
  wants=$(mktemp) || return 1
  bios_plan "$wants" > /dev/null
  out=$(bios_tool check --wants "$wants" --owner "$BIOS_ROOT" --no-wait 2>> "$FLIPEROS_LOG")
  rc=$?
  rm -f "$wants"
  if ((rc == 0)) && [[ $(romclean_value "$out" failed) == 0 || -n $(romclean_value "$out" busy) ]]; then
    rm -f "$BIOS_STATE/failed"
    # A marca de depois: as BIOS que chegaram mudaram a data da ~/bios.
    bios_stamp > "$BIOS_STATE/stamp"
    [[ $(romclean_value "$out" downloaded) =~ ^[1-9] ]] &&
      log_info "Download BIOS (automatico): $(romclean_value "$out" downloaded) BIOS baixadas"
  else
    touch "$BIOS_STATE/failed"
  fi
  return 0
}

# bios_auto_start: a checagem automatica, solta do menu (o menu segue na
# tela, e ela continua mesmo que um jogo abra).
bios_auto_start() {
  is_live && return 0
  [[ $(conf_get bios_auto 2> /dev/null) == off || ! -x $BIOS_TOOL ]] && return 0
  setsid -f nice -n 19 "$SETUP_DIR/fliperos-setup" --bios-check < /dev/null >> "$FLIPEROS_LOG" 2>&1
  return 0
}
