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

# downloader_service_on: o servico ligado (e no boot), antes de cadastrar um
# link.
downloader_service_on() {
  systemctl enable --now "$DOWNLOADER_SERVICE" >> "$FLIPEROS_LOG" 2>&1
}

# downloader_service_sync: o servico ligado enquanto houver um link
# cadastrado ou um pacote de arte baixando (lib/mediapacks.sh), desligado
# sem nenhum.
downloader_service_sync() {
  if compgen -G "$DOWNLOADER_STATE/*.json" > /dev/null ||
    compgen -G "${MEDIAPACKS_STATE:-/var/lib/fliperos/mediapacks}/*.json" > /dev/null; then
    downloader_service_on
  else
    systemctl disable --now "$DOWNLOADER_SERVICE" >> "$FLIPEROS_LOG" 2>&1 || true
  fi
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

# downloader_status imprime o andamento ("chave=valor": pct, state, line,
# roms_name, chds_name).
downloader_status() {
  downloader status 2>> "$FLIPEROS_LOG" || printf '%s\n' pct=0 state=none "line=The downloader did not answer"
}

# downloader_start RESULTADO: aplica o filtro e comeca (eventos de
# progresso); "tipo<TAB>wanted<TAB>arquivos<TAB>bytes" vai para RESULTADO.
downloader_start() {
  log_info "Downloader: aplicando o filtro"
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
