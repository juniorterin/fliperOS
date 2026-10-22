# shellcheck shell=bash
# Setup > System > Password: a senha do usuario do gabinete (fliperos), a
# mesma no login, no sudo, no SSH e no compartilhamento da rede. O Samba tem
# a senha dele (o smbpasswd do fliperos-mkiso.sh): as duas mudam juntas.

PASSWORD_MIN=4

# password_valid SENHA: pelo menos PASSWORD_MIN caracteres, numa linha.
password_valid() {
  ((${#1} >= PASSWORD_MIN)) && [[ $1 != *$'\n'* ]]
}

# password_set SENHA troca a senha do FLIPEROS_USER. A senha so passa pela
# entrada dos programas (printf e um builtin: nao aparece no ps) e nunca vai
# para o log. Status 1: senha invalida ou o chpasswd falhou; 2: a do sistema
# mudou e a do Samba nao.
password_set() {
  local pass=$1 user=$FLIPEROS_USER
  password_valid "$pass" || return 1
  printf '%s:%s\n' "$user" "$pass" | chpasswd 2>> "$FLIPEROS_LOG" || return 1
  log_info "senha de $user trocada"
  have smbpasswd || return 0
  if ! printf '%s\n%s\n' "$pass" "$pass" | smbpasswd -s -a "$user" >> "$FLIPEROS_LOG" 2>&1; then
    log_info "smbpasswd falhou: a senha do Samba ficou a de antes"
    return 2
  fi
  return 0
}

# ── As configuracoes sem tela (o painel web) ─────────────────────
# fliperos-setup --settings imprime os ajustes que o painel web
# (config/fliperos-web) mostra, um por linha:
#   chave|grupo|rotulo|tipo|valor|opcoes|ajuda
# tipo choice (opcoes "valor=Rotulo;...") ou number (opcoes "min..max:passo").
# fliperos-setup --setting CHAVE VALOR muda um deles pelas mesmas funcoes das
# telas do Setup. Ficam de fora o que pode deixar o gabinete sem imagem
# (monitor, resolucao, driver de video): esses so pelo Setup, na tela.

# marquee_overlay_enabled: o marquee do jogo para o OBS (config/fliperos-pixelcade
# grava o estado, o painel web mostra a pagina).
marquee_overlay_enabled() {
  [[ $(conf_get marquee_overlay 2> /dev/null) == on ]]
}

settings_list() {
  local name desc key label state allowed help opts min max step
  opts=""
  while IFS='|' read -r name desc; do
    opts+="${opts:+;}$name=${desc//[;=|]/ }"
  done < <(launcher_available)
  printf 'launcher|System|What starts when the cabinet turns on|choice|%s|%s|The default launcher (Setup > Games > Frontend). Counts from the next boot.\n' \
    "$(launcher_current)" "$opts"
  printf 'latency|System|Latency mode|choice|%s|standard=Standard;low=Low latency|The emulator settings apply now; the kernel settings after a restart.\n' \
    "$(latency_mode)"
  printf 'debug|System|Debug mode|choice|%s|off=Off;on=On (show all text)|Frontends and emulators follow it now; the boot, after a restart.\n' \
    "$(debug_enabled && echo on || echo off)"
  if audio_leveler_available; then
    printf 'leveler|System|Volume leveler|choice|%s|off=Off;on=On|Brings loud and quiet systems closer to the same volume.\n' \
      "$(audio_leveler_enabled && echo on || echo off)"
  fi
  printf 'menu_sounds|System|Menu sounds|choice|%s|on=On;off=Off|The WAV files in sounds/menu, when there are any.\n' \
    "$(menu_sounds_state | sed 's/missing/off/')"
  # A tela ao vivo (config/fliperos-stream): o som, so depois de instalada.
  if [[ -x $STREAM_GO2RTC ]]; then
    printf 'stream_audio|System|Live screen sound|choice|%s|off=Off;on=On|A copy of the sound for the live screen (an ALSA loopback on the card clock). Games opened after the change get it.\n' \
      "$(audio_stream_enabled && echo on || echo off)"
  fi
  printf 'marquee_overlay|System|Marquee overlay for OBS|choice|%s|off=Off;on=On|The marquee of the game on screen as a page for an OBS Browser Source (the address is on the Live page of the panel).\n' \
    "$(marquee_overlay_enabled && echo on || echo off)"
  while IFS='|' read -r key label state help; do
    printf 'service.%s|Services|%s|choice|%s|boot=Boot;after=After boot;off=Off|%s\n' "$key" "$label" "$state" "$help"
  done < <(services_rows)
  while IFS='|' read -r key label state help allowed; do
    opts=""
    [[ ,$allowed, == *,240p,* ]] && opts+="240p=640x240;"
    [[ ,$allowed, == *,filter,* ]] && opts+="filter=480i filter;"
    [[ ,$allowed, == *,pure,* ]] && opts+="pure=480i pure;"
    printf 'mode480.%s|480i games|%s|choice|%s|%s|%s\n' "$key" "$label" "$state" "${opts%;}" "$help"
    printf 'deflicker.%s|480i games|%s: filter level|choice|%s|light=Light;medium=Medium;strong=Strong|The flicker filter level when 480i filter is marked.\n' \
      "$key" "$label" "$(mode480_level "$key")"
  done < <(mode480_rows)
  while IFS='|' read -r key label min max _ step help; do
    printf 'color.%s|Colour|%s|number|%s|%s..%s:%s|%s\n' "$key" "$label" "$(color_get "$key")" "$min" "$max" "$step" "$help"
  done < <(color_table)
  if [[ $(color_caps | sed -n 's/^range //p') != none ]]; then
    printf 'color.range|Colour|RGB range|choice|%s|default=Card default;full=Full (0-255);limited=Limited (16-235)|Full for a PC monitor or CRT, limited for a TV that expects 16-235.\n' \
      "$(r=$(color_range); echo "${r:-default}")"
  fi
}

# settings_boot: a linha do kernel de novo (o debug, a latencia), como as
# telas: so no sistema instalado.
settings_boot() {
  is_installed && ! is_live || return 0
  boot_apply
}

# settings_set CHAVE VALOR. Status 2: chave ou valor que nao existe.
settings_set() {
  local key=$1 value=$2 name
  case $key in
    launcher)
      while IFS='|' read -r name _; do
        if [[ $name == "$value" ]]; then
          launcher_set "$value"
          return 0
        fi
      done < <(launcher_available)
      return 2
      ;;
    latency)
      [[ $value == standard || $value == low ]] || return 2
      latency_apply "$value" && settings_boot
      ;;
    debug)
      [[ $value == on || $value == off ]] || return 2
      debug_set "$value"
      settings_boot
      ;;
    leveler)
      [[ $value == on || $value == off ]] || return 2
      audio_leveler_set "$value"
      ;;
    menu_sounds)
      [[ $value == on || $value == off ]] || return 2
      menu_sounds_set "$value"
      ;;
    stream_audio)
      [[ ($value == on || $value == off) && -x $STREAM_GO2RTC ]] || return 2
      audio_stream_set "$value"
      ;;
    marquee_overlay)
      [[ $value == on || $value == off ]] || return 2
      conf_set marquee_overlay "$value"
      # Os avisos dos frontends (os scripts do ES-DE, o plugin do Attract-Mode
      # Plus), que sem Pixelcade nem ZeDMD ainda nao estao la; como o jogador,
      # para os arquivos do ES-DE continuarem dele.
      if [[ $value == on && -x $FLIPEROS_BIN/fliperos-pixelcade ]]; then
        runuser -u "$FLIPEROS_USER" -- "$FLIPEROS_BIN/fliperos-pixelcade" frontends >> "$FLIPEROS_LOG" 2>&1 || true
      fi
      ;;
    service.*)
      [[ -n $(services_field "${key#service.}" 1) && " ${SERVICE_STATES[*]} " == *" $value "* ]] || return 2
      services_set "${key#service.}" "$value"
      ;;
    mode480.*)
      [[ -n $(mode480_field "${key#mode480.}" 1) ]] || return 2
      mode480_set "${key#mode480.}" "$value" || return 2
      ;;
    deflicker.*)
      [[ -n $(mode480_field "${key#deflicker.}" 1) && " light medium strong " == *" $value "* ]] || return 2
      mode480_set "${key#deflicker.}" "$(mode480_state "${key#deflicker.}")" "$value"
      ;;
    color.range)
      [[ $value == default ]] && value=""
      color_range_set "$value" || return 2
      color_apply > /dev/null 2>&1 || true
      ;;
    color.*)
      color_set "${key#color.}" "$value" || return 2
      # Na placa agora; com um jogo aberto (dono do video), no proximo.
      color_apply > /dev/null 2>&1 || true
      ;;
    *) return 2 ;;
  esac
}
