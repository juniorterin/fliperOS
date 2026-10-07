# shellcheck shell=bash
# Setup > Downloader > ROM/CHD MAME torrent: o romset do MAME e a colecao de CHDs por link
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
# cadastrado, desligado sem nenhum.
downloader_service_sync() {
  if compgen -G "$DOWNLOADER_STATE/*.json" > /dev/null; then
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
