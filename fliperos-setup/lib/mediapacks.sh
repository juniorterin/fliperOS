# shellcheck shell=bash
# Setup > Games > Scraper > Art packs by torrent: logos e videos de pacotes
# em torrent, so os dos jogos que estao nas pastas de ~/roms. O download e do
# Transmission do Downloader (servico fliperos-transmission) e a logica, o
# config/fliperos-mediapacks. Aqui ficam a lista dos pacotes e as pastas de
# jogos de cada um.

MEDIAPACKS=${MEDIAPACKS:-/opt/fliperos/bin/fliperos-mediapacks}
MEDIAPACKS_STATE=${MEDIAPACKS_STATE:-/var/lib/fliperos/mediapacks}
# Os pacotes que vem na imagem (config/fliperos-media-torrents) e os da
# pessoa, no mesmo formato: "id<TAB>tipo<TAB>pastas<TAB>link<TAB>nome". Um
# da pessoa com o id de um da imagem vale no lugar dele (o link trocado).
MEDIAPACKS_LIST=${MEDIAPACKS_LIST:-/usr/local/share/fliperos/media-torrents}
MEDIAPACKS_USER=${MEDIAPACKS_USER:-$FLIPEROS_ETC/media-torrents}
MEDIAPACKS_TYPES="logo preview snap box marquee"

# mediapacks ARGS... roda o fliperos-mediapacks com o estado desta maquina.
mediapacks() {
  FLIPEROS_MEDIAPACKS_STATE=$MEDIAPACKS_STATE "$MEDIAPACKS" "$@"
}

# mediapacks_prepare: a pasta do estado e do usuario, porque o servico (do
# usuario) grava nela quando um download termina.
mediapacks_prepare() {
  install -d -m 755 "$MEDIAPACKS_STATE" 2> /dev/null || mkdir -p "$MEDIAPACKS_STATE"
  chown "$FLIPEROS_USER:" "$MEDIAPACKS_STATE" 2> /dev/null || true
}

# mediapacks_list imprime "id<TAB>tipo<TAB>pastas<TAB>link<TAB>nome<TAB>origem"
# de cada pacote: os da imagem na ordem dela (origem image, ou changed com o
# link da pessoa) e depois os da pessoa (user).
mediapacks_list() {
  local user=$MEDIAPACKS_USER
  [[ -f $user ]] || user=/dev/null
  [[ -f $MEDIAPACKS_LIST ]] || return 0
  awk -F'\t' -v OFS='\t' '
    /^#/ || NF < 5 { next }
    FILENAME == ARGV[1] { mine[$1] = $0; order[++n] = $1; next }
    ($1 in mine) { print mine[$1], "changed"; seen[$1] = 1; next }
    { print $0, "image" }
    END { for (i = 1; i <= n; i++) if (!(order[i] in seen)) print mine[order[i]], "user" }
  ' "$user" "$MEDIAPACKS_LIST"
}

# mediapacks_get ID imprime a linha do pacote (status 1 sem ele).
mediapacks_get() {
  mediapacks_list | awk -F'\t' -v id="$1" '$1 == id { print; f = 1 } END { exit !f }'
}

mediapacks_type_label() {
  case $1 in
    logo) echo "logos" ;;
    preview) echo "videos" ;;
    snap) echo "screenshots" ;;
    box) echo "box art" ;;
    marquee) echo "marquees" ;;
    *) echo "$1" ;;
  esac
}

# mediapacks_keys PASTAS imprime a linha do scraper_detect
# ("chave|pasta|plataforma|quantidade") de cada pasta com jogos do pacote.
# PASTAS: chaves de ~/roms separadas por virgula; @arcade-cores = os cores
# de arcade do RetroArch, @arcade = toda pasta de arcade. A tela guarda o
# scraper_detect em MEDIAPACKS_FOUND, para nao contar os jogos a cada linha.
mediapacks_keys() {
  local folders=",$1," line key
  while IFS= read -r line; do
    key=${line%%|*}
    [[ -n $key ]] || continue
    if [[ $folders == *",$key,"* ]] ||
      { [[ $folders == *",@arcade,"* ]] && scraper_arcade "$key"; } ||
      { [[ $folders == *",@arcade-cores,"* && $key == retroarch/* ]] && scraper_arcade "$key"; }; then
      printf '%s\n' "$line"
    fi
  done <<< "${MEDIAPACKS_FOUND:-$(scraper_detect)}"
}

# mediapacks_games PASTAS: quantos arquivos de jogo ha nas pastas do pacote.
mediapacks_games() {
  mediapacks_keys "$1" | awk -F'|' '{ n += $4 } END { print n + 0 }'
}

# mediapacks_link_ok LINK: um link magnetico ou o endereco de um .torrent.
mediapacks_link_ok() {
  [[ $1 =~ ^magnet:\?.*xt=urn:bt(ih|mh): || $1 =~ ^https?://[^[:space:]]+$ ]]
}

# mediapacks_save ID TIPO PASTAS LINK NOME grava o pacote na lista da pessoa
# (troca o de mesmo id).
mediapacks_save() {
  local id=$1 tmp
  mkdir -p "$(dirname "$MEDIAPACKS_USER")"
  tmp=$(mktemp "$MEDIAPACKS_USER.XXXXXX") || return 1
  [[ -f $MEDIAPACKS_USER ]] && awk -F'\t' -v id="$id" '$1 != id' "$MEDIAPACKS_USER" > "$tmp"
  printf '%s\t%s\t%s\t%s\t%s\n' "$id" "$2" "$3" "$4" "${5//$'\t'/ }" >> "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$MEDIAPACKS_USER"
  log_info "Pacotes de arte: $id ($2, $3) gravado"
}

# mediapacks_add TIPO PASTAS LINK NOME: um pacote novo da pessoa; o id sai
# do link. Imprime o id.
mediapacks_add() {
  local id
  id="user-$(printf '%s' "$3" | sha1sum | cut -c1-10)"
  mediapacks_save "$id" "$1" "$2" "$3" "$4" || return 1
  printf '%s\n' "$id"
}

# mediapacks_forget ID tira o pacote da lista da pessoa (o da imagem volta a
# ter o link dela) e cancela o download dele.
mediapacks_forget() {
  local tmp
  mediapacks cancel "$1" 2>> "$FLIPEROS_LOG" || true
  [[ -f $MEDIAPACKS_USER ]] || return 0
  tmp=$(mktemp "$MEDIAPACKS_USER.XXXXXX") || return 1
  awk -F'\t' -v id="$1" '$1 != id' "$MEDIAPACKS_USER" > "$tmp"
  chmod 644 "$tmp"
  mv -f "$tmp" "$MEDIAPACKS_USER"
}

# mediapacks_status imprime o andamento ("chave=valor": pct, state, line e
# "pack.ID=estado|pct|texto" de cada pacote).
mediapacks_status() {
  mediapacks status 2>> "$FLIPEROS_LOG" || printf '%s\n' pct=0 state=none "line=The downloader did not answer"
}

# mediapacks_finish: o que ja baixou vai para as pastas de arte (o servico
# faz o mesmo sozinho quando um torrent termina).
mediapacks_finish() {
  mediapacks finish >> "$FLIPEROS_LOG" 2>&1
}

# mediapacks_start ID RESULTADO: le o torrent e poe para baixar os arquivos
# dos jogos que estao nas pastas do pacote e ainda nao tem a arte (eventos
# de progresso). RESULTADO recebe "chave=valor": games (jogos sem a arte),
# kept (ja tinham), files e bytes (o que vai baixar).
mediapacks_start() {
  local id=$1 result=$2 row type folders link label key dir tmp rc
  local -a keys=() args=()
  row=$(mediapacks_get "$id") || { ev_fail "This pack is not in the list"; return 1; }
  IFS=$'\t' read -r _ type folders link label _ <<< "$row"
  mapfile -t keys < <(mediapacks_keys "$folders")
  if ((${#keys[@]} == 0)); then
    ev_fail "No ROMs in the folders of this pack (${folders//,/, })"
    return 1
  fi
  ev_step 0 "Listing the games of ${#keys[@]} folders"
  tmp=$(mktemp -d) || { ev_fail "No space for the list of games"; return 1; }
  for row in "${keys[@]}"; do
    IFS='|' read -r key dir _ <<< "$row"
    media_system "$key" || { rm -rf "$tmp"; ev_fail "Could not create the folders in $MEDIA_DIR"; return 1; }
    scraper_files "$key" "$dir" | sed 's|.*/||; s|\.[^.]*$||' > "$tmp/${key//\//-}"
    args+=(--target "$key" "$tmp/${key//\//-}" "$MEDIA_DIR/$type/$key")
  done
  log_info "Pacotes de arte: $id ($label) para ${#keys[@]} pastas"
  mediapacks start "$id" --link "$link" --type "$type" "${args[@]}" --progress --result "$result" \
    2>> "$FLIPEROS_LOG"
  rc=$?
  rm -rf "$tmp"
  return "$rc"
}

# mediapacks_auto: o scrape automatico do frontend do FliperOS
# (fliperos-setup --mediapacks auto). Poe para baixar os pacotes de toda
# pasta com jogos, so os arquivos dos jogos que ainda nao tem a arte, como o
# "Download every pack" da tela; o pacote que ja esta baixando fica como
# esta. Imprime "id<TAB>jogos sem a arte<TAB>arquivos" de cada um. Um pacote
# de .zip por letra (os videos do MAME, GB cada) vem uma letra de cada vez:
# o config/fliperos-mediapacks tira dela o que e dos jogos e a apaga antes
# da proxima.
mediapacks_auto() {
  local status id folders st result out started=0
  MEDIAPACKS_FOUND=$(scraper_detect)
  [[ -n $MEDIAPACKS_FOUND ]] || return 0
  downloader_prepare
  mediapacks_prepare
  status=$(mediapacks_status)
  if [[ $(romclean_value "$status" state) == ready ]]; then
    mediapacks_finish
    status=$(mediapacks_status)
  fi
  # O fd 3: o mediapacks_start nao le a lista no lugar do teclado.
  while IFS=$'\t' read -r id _ folders _ <&3; do
    (($(mediapacks_games "$folders") > 0)) || continue
    st=$(romclean_value "$status" "pack.$id")
    [[ ${st%%|*} == downloading ]] && continue
    if ((!started)); then
      downloader_service_on
      started=1
    fi
    result=$(mktemp) || return 1
    # Os erros vao para o log (o mediapacks_start os manda para la).
    mediapacks_start "$id" "$result" > /dev/null < /dev/null
    out=$(cat "$result")
    rm -f "$result"
    printf '%s\t%s\t%s\n' "$id" "$(romclean_value "$out" games)" "$(romclean_value "$out" files)"
  done 3< <(mediapacks_list)
  mediapacks_finish
  downloader_service_sync
  return 0
}
