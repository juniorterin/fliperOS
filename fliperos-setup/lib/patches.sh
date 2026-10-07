# shellcheck shell=bash
# Updates do FliperOS sem ISO nova (config/fliperos-update): os patches do
# updates/index do repo, sempre em ordem. O fliperos-tty1 ve no boot, com
# rede, se ha algum pendente e abre o fliperos-setup --update-check.

PATCH_BIN=${PATCH_BIN:-/opt/fliperos/bin/fliperos-update}
PATCH_BACKUPS=${PATCH_BACKUPS:-/var/lib/fliperos/update/backup}

# patch_pending imprime os pendentes, "N<TAB>reboot<TAB>titulo" por linha.
patch_pending() {
  "$PATCH_BIN" check 2>> "$FLIPEROS_LOG"
}

# patch_plan RESULTADO: o que o update troca, falando com a tela por
# eventos; o resumo (local/unknown<TAB>arquivo) fica em RESULTADO.
patch_plan() {
  "$PATCH_BIN" plan --progress --result "$1" 2>> "$FLIPEROS_LOG"
}

# patch_apply RESULTADO aplica os pendentes, um de cada vez, em ordem
# (applied<TAB>N<TAB>reboot<TAB>backup<TAB>titulo em RESULTADO).
patch_apply() {
  log_info "FliperOS update: applying"
  "$PATCH_BIN" apply --progress --result "$1" 2>> "$FLIPEROS_LOG"
}
