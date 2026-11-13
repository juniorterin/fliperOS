# shellcheck shell=bash
# Backup na nuvem (Setup > Cloud backup e o painel web): os recordes, saves e
# configuracoes do jogador numa nuvem pelo rclone. Quem faz e o
# config/fliperos-cloud, que roda como o jogador (o rclone.conf e os arquivos
# sao dele); aqui so o chamamos.

CLOUD_TOOL=${CLOUD_TOOL:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-cloud}
CLOUD_HOME=${CLOUD_HOME:-/home/$FLIPEROS_USER}
# Os destinos: "tipo|rotulo|campos" (campos vazios: o login pelo site, so
# pelo painel web, que tem um navegador).
CLOUD_KINDS=(
  "drive|Google Drive|"
  "dropbox|Dropbox|"
  "webdav|WebDAV (Nextcloud, ownCloud...)|url user pass"
  "sftp|SFTP (a PC or NAS)|host port user pass"
  "mega|MEGA|user pass"
)

# cloud_run ARGUMENTO...: o fliperos-cloud como o jogador.
cloud_run() {
  local uid
  if [[ $EUID -eq 0 ]] && uid=$(id -u "$FLIPEROS_USER" 2> /dev/null) && ((uid != 0)); then
    runuser -u "$FLIPEROS_USER" -- env HOME="$CLOUD_HOME" XDG_RUNTIME_DIR="/run/user/$uid" "$CLOUD_TOOL" "$@"
  else
    "$CLOUD_TOOL" "$@"
  fi
}

# cloud_status CHAVE: um campo do "fliperos-cloud status" (installed, remote,
# auto, what, last, result).
cloud_status() {
  cloud_run status 2> /dev/null | sed -n "s/^$1=//p" | head -1
}

# cloud_label: uma linha para o menu.
cloud_label() {
  local remote
  [[ -x $CLOUD_TOOL ]] || { echo "not available"; return 0; }
  [[ $(cloud_status installed) == 1 ]] || { echo "rclone not installed"; return 0; }
  remote=$(cloud_status remote)
  [[ -n $remote ]] || { echo "no account"; return 0; }
  echo "$(cloud_kind_label "$remote")$([[ $(cloud_status auto) == on ]] && echo ", by itself")"
}

cloud_kind_label() {
  local entry
  for entry in "${CLOUD_KINDS[@]}"; do
    [[ ${entry%%|*} == "$1" ]] && { cut -d'|' -f2 <<< "$entry"; return 0; }
  done
  echo "$1"
}

cloud_kind_fields() {
  local entry
  for entry in "${CLOUD_KINDS[@]}"; do
    [[ ${entry%%|*} == "$1" ]] && { cut -d'|' -f3 <<< "$entry"; return 0; }
  done
}

# cloud_install: o rclone pelo apt, com a tela de progresso.
cloud_install() {
  update_install_package rclone
}

# As chaves do fliperos.conf que sao gosto da pessoa e vao de um gabinete para
# outro pela nuvem. O que e do hardware (monitor, placa, driver, geometria,
# cor, modo de boot) fica o de cada maquina.
CLOUD_CONF_KEYS='^(bios_auto|cabinet_name|deflicker.*|mode480_.*|level\..*|gun_.*|latency|launcher|marquee_overlay|menu_sounds|netshare_.*|osd.*|scanlines|scraper_.*|splash|stream_audio|stream_quality|volume|esde_240p|pegasus_240p|screens)$'

# cloud_restore PASTA (fliperos-setup --cloud-restore, root): as configuracoes
# do sistema que desceram da nuvem (config/fliperos-cloud, sync_system) no
# lugar, so as que vieram mais novas que as daqui. Do fliperos.conf, so as
# chaves de CLOUD_CONF_KEYS. Os botoes trocados vao para os emuladores.
cloud_restore() {
  local stage=$1 rel src dst key value buttons=0
  [[ -d $stage ]] || return 1
  while IFS= read -r -d '' src; do
    rel=${src#"$stage"/}
    dst=$FLIPEROS_ETC/$rel
    case $rel in
      .. | ../* | */../* | *..) continue ;;
    esac
    [[ -f $dst && ! $src -nt $dst ]] && continue
    if [[ $rel == fliperos.conf ]]; then
      while IFS='=' read -r key value; do
        [[ -n $key && $key != \#* && $key =~ $CLOUD_CONF_KEYS ]] || continue
        [[ $(conf_get "$key" 2> /dev/null) == "$value" ]] && continue
        conf_set "$key" "$value"
      done < "$src"
      touch -r "$src" "$FLIPEROS_CONF" 2> /dev/null
    else
      install -D -m 644 "$src" "$dst" || continue
      touch -r "$src" "$dst"
      [[ $rel == buttons*.map || $rel == buttons.layout ]] && buttons=1
    fi
    log_info "nuvem: $rel restaurado"
  done < <(find "$stage" -type f -print0)
  if ((buttons)) && [[ -x ${BUTTONS:-} && -f ${BUTTONS_MAP:-} ]]; then
    "$BUTTONS" save "$BUTTONS_MAP" >> "$FLIPEROS_LOG" 2>&1 || log_info "nuvem: os botoes nao foram para os emuladores"
  fi
  return 0
}
