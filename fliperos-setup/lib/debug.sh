# shellcheck shell=bash
# Modo debug (Setup > Debug mode): mostra todo texto que o FliperOS esconde.
# Desligado (o padrao), o boot vai direto ao Plymouth (Limine quiet, kernel e
# udev calados, sem cursor) e a saida dos launchers e emuladores vai para
# /opt/fliperos/logs/<programa>.log. Ligado, o menu do Limine aparece, o boot
# mostra as mensagens do kernel e do systemd e os programas escrevem na tela.
# Os scripts de /opt/fliperos/bin olham o arquivo DEBUG_FLAG.

DEBUG_FLAG=${DEBUG_FLAG:-$FLIPEROS_ETC/debug}

debug_enabled() {
  [[ -f $DEBUG_FLAG ]]
}

# debug_cmdline LINHA tira da linha do kernel os parametros que calam o boot
# e, fora do modo debug, os poe de volta na frente.
debug_cmdline() {
  local word out=() silent=" quiet splash $BOOT_SILENT "
  for word in $1; do
    [[ $silent == *" $word "* ]] && continue
    out+=("$word")
  done
  if debug_enabled; then
    printf '%s\n' "${out[*]}"
  else
    printf '%s\n' "quiet splash $BOOT_SILENT${out[*]:+ ${out[*]}}"
  fi
}

# debug_set on|off liga ou desliga e regrava o boot (sistema instalado).
debug_set() {
  if [[ $1 == on ]]; then
    mkdir -p "$(dirname "$DEBUG_FLAG")"
    : > "$DEBUG_FLAG"
    chmod 644 "$DEBUG_FLAG"
    conf_set debug 1
    boot_write_var FLIPEROS_QUIET no
  else
    rm -f "$DEBUG_FLAG"
    conf_set debug 0
    boot_write_var FLIPEROS_QUIET yes
  fi
  log_info "modo debug: $1"
}
