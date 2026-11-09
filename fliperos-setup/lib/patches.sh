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

# patch_notes ARQUIVO: o changelog dos updates pendentes (o titulo e as
# notas de cada um, updates/notes/NNNN.md no commit dele). Status 1: nada.
patch_notes() {
  "$PATCH_BIN" notes > "$1" 2>> "$FLIPEROS_LOG" && [[ -s $1 ]]
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

# patch_versions: os updates que se pode escolher (fliperos-update versions):
# level=, base=, latest=, hold=, reboot= e "N<TAB>estado<TAB>reboot<TAB>titulo"
# do mais novo ao mais velho.
patch_versions() {
  "$PATCH_BIN" versions 2>> "$FLIPEROS_LOG"
}

# patch_goto N RESULTADO: leva o gabinete ao update N (ou latest), para
# frente ou para tras, falando com a tela por eventos (back/applied<TAB>N<TAB>
# reboot... em RESULTADO).
patch_goto() {
  log_info "FliperOS version: going to update $1"
  "$PATCH_BIN" goto "$1" --progress --result "$2" 2>> "$FLIPEROS_LOG"
}
