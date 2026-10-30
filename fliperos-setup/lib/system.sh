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
# tipo choice (opcoes "valor=Rotulo;..."), number (opcoes "min..max:passo")
# ou action (um botao, sem valor nem opcoes: o --setting recebe 1).
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
  # O jogo direto no boot, quando um ja foi escolhido (no Setup ou na pagina do
  # jogo no painel web).
  if [[ -s $BOOTGAME_FILE ]]; then
    name=$(bootgame_label)
    opts+=";game=A game: ${name//[;=|]/ }"
  fi
  printf 'launcher|System|What starts when the cabinet turns on|choice|%s|%s|The default launcher (Setup > Games > Frontend). To open one game, use Open at power on on its page in Frontend. Counts from the next boot.\n' \
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
    printf 'stream_quality|System|Live screen quality|choice|%s|light=Light (weak Wi-Fi);normal=Normal;high=High;max=Maximum (network cable)|The picture of the live screen: more quality takes more network and CPU. It counts from the next connection.\n' \
      "$(conf_get stream_quality 2> /dev/null | grep -xE 'light|high|max' || echo normal)"
  fi
  printf 'marquee_overlay|System|Marquee overlay for OBS|choice|%s|off=Off;on=On|The marquee of the game on screen as a page for an OBS Browser Source (the address is on the Live page of the panel).\n' \
    "$(marquee_overlay_enabled && echo on || echo off)"
  # Video Setup: o que nao deixa o gabinete sem imagem.
  printf 'orientation|Video|Monitor orientation|choice|%s|horizontal=Horizontal;vertical-cw=Vertical clockwise (rotated right);vertical-ccw=Vertical counter-clockwise (rotated left)|How the monitor is mounted in the cabinet. The boot is prepared again (about a minute); everything follows it after a restart.\n' \
    "$(conf_get orientation 2> /dev/null || echo horizontal)"
  opts=""
  while IFS='|' read -r name desc; do
    opts+="${opts:+;}$name=${desc//[;=|]/ }"
  done < <(splash_list)
  if [[ -n $opts ]]; then
    printf 'splash|Video|Boot splash|choice|%s|%s|The picture while the cabinet boots (Setup > Splash screen, where the preview is). The boot image is rebuilt: about a minute.\n' \
      "$(splash_current 2> /dev/null)" "$opts"
  fi
  if (($(mm_count) > 1)); then
    printf 'mm_games|Video|Multi-screen games|choice|%s|on=One screen on each monitor;off=Everything on monitor 1|Games with 2 or 3 screens. Counts after a restart.\n' \
      "$(mm_games_on && echo on || echo off)"
  fi
  # Audio Setup (o volume fica no Frontend, no gabinete desenhado).
  opts=""
  while IFS='|' read -r name desc; do
    opts+="${opts:+;}${name/,/_}=${desc//[;=|]/ }"
  done < <(audio_devices)
  if [[ -n $opts ]]; then
    name=$(audio_current)
    printf 'audio_card|Audio|Sound card|choice|%s|%s|The card used by the system and the emulators. Games opened after the change use it.\n' \
      "${name/,/_}" "$opts"
  fi
  printf 'mame_latency|Audio|MAME audio latency|number|%s|0..50:0.5|GroovyMAME audio latency (0 = default). Lower responds faster; raise it if the sound crackles.\n' \
    "$(audio_mame_latency)"
  printf 'audio.test|Audio|Test sound|action|||A voice on the cabinet speakers: if it is heard, the sound card is the right one.\n'
  printf 'power.reboot|Power|Restart the cabinet|action|||The game on screen closes and the cabinet restarts. The panel comes back in about a minute.\n'
  printf 'power.poweroff|Power|Turn off the cabinet|action|||The game on screen closes and the cabinet turns off. It is turned on again at the cabinet.\n'
  while IFS='|' read -r key label state help; do
    printf 'service.%s|Services|%s|choice|%s|boot=Boot;after=After boot;off=Off|%s\n' "$key" "$label" "$state" "$help"
  done < <(services_rows)
  while IFS='|' read -r key label state help allowed; do
    opts=""
    [[ ,$allowed, == *,240p,* ]] && opts+="240p=640x240;"
    [[ ,$allowed, == *,filter,* ]] && opts+="filter=480i filter;"
    [[ ,$allowed, == *,pure,* ]] && opts+="pure=480i pure;"
    printf 'mode480.%s|480i hacks|%s|choice|%s|%s|%s\n' "$key" "$label" "$state" "${opts%;}" "$help"
    printf 'deflicker.%s|480i hacks|%s: filter level|choice|%s|light=Light;medium=Medium;strong=Strong|The flicker filter level when 480i filter is marked.\n' \
      "$key" "$label" "$(mode480_level "$key")"
  done < <(mode480_rows)
  while IFS='|' read -r key label min max _ step help; do
    printf 'color.%s|Colour|%s|number|%s|%s..%s:%s|%s\n' "$key" "$label" "$(color_get "$key")" "$min" "$max" "$step" "$help"
  done < <(color_table)
  if [[ $(color_caps | sed -n 's/^range //p') != none ]]; then
    printf 'color.range|Colour|RGB range|choice|%s|default=Card default;full=Full (0-255);limited=Limited (16-235)|Full for a PC monitor or CRT, limited for a TV that expects 16-235.\n' \
      "$(r=$(color_range); echo "${r:-default}")"
  fi
  printf 'color.reset|Colour|Back to the defaults|action|||Every colour setting back to the default: the picture exactly as the card sends it.\n'
}

# settings_boot: a linha do kernel de novo (o debug, a latencia), como as
# telas: so no sistema instalado.
settings_boot() {
  is_installed && ! is_live || return 0
  boot_apply
}

# settings_video: o Xorg e a linha do kernel de novo, como ao fechar o Video
# Setup com algo mudado (vale no proximo boot).
settings_video() {
  is_installed && ! is_live || return 0
  xorg_generate
  boot_apply
}

# settings_set CHAVE VALOR. Status 2: chave ou valor que nao existe.
settings_set() {
  local key=$1 value=$2 name
  case $key in
    launcher)
      if [[ $value == game && -s $BOOTGAME_FILE ]]; then
        launcher_set game
        return 0
      fi
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
    stream_quality)
      [[ $value =~ ^(light|normal|high|max)$ && -x $STREAM_GO2RTC ]] || return 2
      conf_set stream_quality "$value"
      ;;
    marquee_overlay)
      [[ $value == on || $value == off ]] || return 2
      conf_set marquee_overlay "$value"
      # Os avisos dos frontends (os scripts do ES-DE, o plugin do Attract-Mode
      # Plus), que sem Pixelcade nem ZeDMD ainda nao estao la; como o jogador,
      # para os arquivos do ES-DE continuarem dele.
      # E o jogo que ja esta aberto (ligado no meio de uma live): sem
      # isto, a pagina so mostrava algo no proximo jogo.
      if [[ $value == on && -x $FLIPEROS_BIN/fliperos-pixelcade ]]; then
        runuser -u "$FLIPEROS_USER" -- "$FLIPEROS_BIN/fliperos-pixelcade" frontends >> "$FLIPEROS_LOG" 2>&1 || true
        runuser -u "$FLIPEROS_USER" -- env XDG_RUNTIME_DIR="/run/user/$(id -u "$FLIPEROS_USER")" \
          "$FLIPEROS_BIN/fliperos-pixelcade" now >> "$FLIPEROS_LOG" 2>&1 || true
      fi
      # Os detectores de placar do Fightcade (config/fliperos-versus) so eram
      # baixados ao instalar o Pixelcade ou o ZeDMD: sem eles o marquee e a
      # previa do painel nunca tinham placar. Em segundo plano (leva segundos
      # e o pedido nao espera), so se ainda nao estao la.
      if [[ $value == on && -x $FLIPEROS_BIN/fliperos-versus ]]; then
        local detectors
        detectors=$(getent passwd "$FLIPEROS_USER" | cut -d: -f6)/.local/share/fliperos/versus-detectors
        compgen -G "$detectors/*.inf" > /dev/null || {
          runuser -u "$FLIPEROS_USER" -- "$FLIPEROS_BIN/fliperos-versus" fetch >> "$FLIPEROS_LOG" 2>&1 < /dev/null &
          disown
        }
      fi
      ;;
    orientation)
      [[ $value =~ ^(horizontal|vertical-cw|vertical-ccw)$ ]] || return 2
      [[ $value == "$(conf_get orientation 2> /dev/null || echo horizontal)" ]] && return 0
      # Como o Video Setup > Monitor Orientation: o console agora, o boot (o
      # splash girado, o console em pe), os filtros de ROMs e, ao sair, o
      # Xorg e a linha do kernel.
      orientation_apply "$value"
      orientation_boot "$value" || return 1
      downloader_filter_orientation
      settings_video
      ;;
    splash)
      [[ -n $value ]] && splash_list | cut -d"|" -f1 | grep -qxF "$value" || return 2
      [[ $value == "$(splash_current 2> /dev/null)" ]] && return 0
      splash_set "$value"
      ;;
    mm_games)
      [[ ($value == on || $value == off) && $(mm_count) -gt 1 ]] || return 2
      mm_set_games "$value"
      # Os .ini do GroovyMAME para os jogos de varias telas (screen_mm_changed).
      [[ $value == off ]] || mm_mame_prepare || log_info "settings: mm_mame_prepare falhou"
      settings_video
      ;;
    audio_card)
      [[ $value =~ ^[0-9]+_[0-9]+$ ]] && audio_devices | cut -d"|" -f1 | grep -qxF "${value/_/,}" || return 2
      audio_set_default "${value/_/,}"
      ;;
    mame_latency)
      audio_set_mame_latency "$value" || return 2
      ;;
    audio.test)
      audio_test
      ;;
    power.reboot | power.poweroff)
      # Depois da resposta: o painel recebe o 200 antes de o gabinete sair.
      systemd-run --on-active=2 --unit=fliperos-web-power systemctl "${key#power.}" >> "$FLIPEROS_LOG" 2>&1
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
    color.reset)
      color_reset
      color_apply > /dev/null 2>&1 || true
      ;;
    color.range)
      [[ $value == default ]] && value=""
      color_range_set "$value" || return 2
      color_apply > /dev/null 2>&1 || true
      ;;
    color.*)
      color_set "${key#color.}" "$value" || return 2
      # Na placa agora, mesmo com um jogo aberto (o fliperos-color usa o
      # descritor do dono do video); a saturacao e o matiz por software, a
      # camada GL do jogo rele do fliperos.conf.
      color_apply > /dev/null 2>&1 || true
      ;;
    *) return 2 ;;
  esac
}
