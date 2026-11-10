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
