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

# ── O apelido do gabinete ────────────────────────────────────────
# Setup > System > Cabinet name (e na instalacao): o nome que os outros
# gabinetes da rede local veem na party e no link (cabinet_name= no
# fliperos.conf, que o gui/felink.py le). Sem apelido, uma fruta ou um bicho,
# sempre o mesmo para a maquina. A limpeza e o nome de fabrica sao os do
# felink: o mesmo codigo que mostra o nome.
CABINET_NAME_MAX=12

# cabinet_name_py FUNCAO [TEXTO] chama felink.FUNCAO: clean (o TEXTO limpo),
# default (a fruta ou o bicho desta maquina) ou current (o que os outros veem).
cabinet_name_py() {
  python3 - "$SETUP_DIR/gui" "$FLIPEROS_CONF" "$@" << 'PY' 2>> "$FLIPEROS_LOG"
import sys
sys.path.insert(0, sys.argv[1])
import felink
conf, what = sys.argv[2], sys.argv[3]
ident = felink.machine_id()
if what == "clean":
    print(felink.clean_name(sys.argv[4]))
elif what == "default":
    print(felink.default_name(ident))
else:
    print(felink.cabinet_name(ident, conf))
PY
}

# cabinet_name_set TEXTO grava o apelido (limpo); vazio volta ao de fabrica.
cabinet_name_set() {
  local name
  name=$(cabinet_name_py clean "$1") || return 1
  if [[ -n $name ]]; then
    conf_set cabinet_name "$name"
  else
    conf_unset cabinet_name
  fi
}

# ── As configuracoes sem tela (o painel web) ─────────────────────
# fliperos-setup --settings imprime os ajustes que o painel web
# (config/fliperos-web) mostra, um por linha:
#   chave|grupo|rotulo|tipo|valor|opcoes|ajuda
# tipo choice (opcoes "valor=Rotulo;..."), number (opcoes "min..max:passo"),
# text (opcoes: o tamanho maximo) ou action (um botao, sem valor nem opcoes:
# o --setting recebe 1).
# fliperos-setup --setting CHAVE VALOR muda um deles pelas mesmas funcoes das
# telas do Setup. Os grupos saem na ordem do Setup: Video (e as telas dele),
# Audio, GunCon 2, a tela ao vivo, System, Services e Power.
#
# O monitor e a resolucao de boot tambem estao aqui: com outro monitor (ou um
# preset errado) o gabinete fica sem imagem, e o painel, que nao precisa da
# tela, e o caminho de volta. O driver de video fica so no Setup: a troca
# pede uma confirmacao na tela (amd_driver_trial).

# marquee_overlay_enabled: o marquee do jogo para o OBS (config/fliperos-pixelcade
# grava o estado, o painel web mostra a pagina).
marquee_overlay_enabled() {
  [[ $(conf_get marquee_overlay 2> /dev/null) == on ]]
}

# settings_opts: as linhas "nome|descricao" da entrada como as opcoes
# "nome=descricao;..." de um ajuste de escolha.
settings_opts() {
  local name desc opts=""
  while IFS='|' read -r name desc; do
    [[ -n $name ]] && opts+="${opts:+;}$name=${desc//[;=|]/ }"
  done
  printf '%s\n' "$opts"
}

settings_list() {
  local name desc key label state allowed help opts min max step entry monitor res value
  # ── Video (Setup > Video Setup) ──
  # O monitor: o preset ou, com o custom do Geometry ativo, o custom (escolher
  # um preset o desfaz, como no Monitor Type).
  monitor=$(conf_get monitor 2> /dev/null) || monitor=""
  opts=$(for entry in "${MONITOR_PRESETS[@]}"; do printf '%s\n' "$entry"; done | settings_opts)
  if [[ -n $monitor ]] && video_custom_active; then
    label=$(monitor_label "$monitor")
    opts="custom=Custom crt_range (on ${label//[;=|]/ });$opts"
    monitor=custom
  fi
  printf 'monitor|Video|Monitor type|choice|%s|%s|The monitor model or its frequencies (15, 25 or 31 kHz): Switchres, MAME and RetroArch follow it, and it picks the boot resolution. It counts after a restart.\n' \
    "$monitor" "$opts"
  # A resolucao de boot (o modo do console, do Setup, do frontend e do
  # desktop), so depois do teste de saidas, que escolheu a saida.
  if conf_get connector > /dev/null 2>&1; then
    res=$(conf_get boot_resolution 2> /dev/null) || res=""
    opts=$(video_resolution_rows | settings_opts)
    if [[ $res == custom ]]; then
      opts="custom=Custom $(conf_get custom_width 2> /dev/null)x$(conf_get custom_height 2> /dev/null) $(conf_get custom_refresh 2> /dev/null) Hz (made on the cabinet)${opts:+;$opts}"
    elif [[ -n $res && ";$opts" != *";$res="* ]]; then
      opts="$res=$(mode_pretty "$res")${opts:+;$opts}"
    elif [[ -z $res && -n $opts ]]; then
      opts="=From the monitor (EDID);$opts"
    fi
    [[ -n $opts ]] &&
      printf 'resolution|Video|Boot resolution|choice|%s|%s|The video mode of the boot, the menus, the frontend and the desktop (the games pick their own). It counts after a restart.\n' \
        "$res" "$opts"
  fi
  # O video de antes da ultima troca (aqui ou no Video Setup): a volta quando
  # o monitor novo fica sem imagem.
  if label=$(video_previous_label); then
    printf 'video.previous|Video|Back to the previous monitor|action|||Back to %s: the monitor and resolution before the last change. Use it when the picture did not come back. It counts after a restart.\n' \
      "${label//|/ }"
  fi
  printf 'orientation|Video|Monitor orientation|choice|%s|horizontal=Horizontal;vertical-cw=Vertical clockwise (rotated right);vertical-ccw=Vertical counter-clockwise (rotated left)|How the monitor is mounted in the cabinet. The boot is prepared again (about a minute); everything follows it after a restart.\n' \
    "$(conf_get orientation 2> /dev/null || echo horizontal)"
  if (($(mm_count) > 1)); then
    printf 'mm_games|Video|Multi-screen games|choice|%s|on=One screen on each monitor;off=Everything on monitor 1|Games with 2 or 3 screens. Counts after a restart.\n' \
      "$(mm_games_on && echo on || echo off)"
  fi
  printf 'osd|Video|On-screen menu|choice|%s|on=On;off=Off|Volume, filter, geometry and colour over any game: hold Start and Down for a second (Frontend controls > OSD MENU changes it), or press Pause on a keyboard or Play/Pause on a remote.\n' \
    "$([[ $(conf_get osd 2> /dev/null) == off ]] && echo off || echo on)"
  # Video Setup > Colour calibration.
  while IFS='|' read -r key label min max _ step help; do
    printf 'color.%s|Colour|%s|number|%s|%s..%s:%s|%s\n' "$key" "$label" "$(color_get "$key")" "$min" "$max" "$step" "$help"
  done < <(color_table)
  if [[ $(color_caps | sed -n 's/^range //p') != none ]]; then
    printf 'color.range|Colour|RGB range|choice|%s|default=Card default;full=Full (0-255);limited=Limited (16-235)|Full for a PC monitor or CRT, limited for a TV that expects 16-235.\n' \
      "$(r=$(color_range); echo "${r:-default}")"
  fi
  printf 'color.reset|Colour|Back to the defaults|action|||Every colour setting back to the default: the picture exactly as the card sends it.\n'
  # Video Setup > Scanlines, so com um monitor de 31 kHz.
  if scanlines_available; then
    printf 'scanlines|Scanlines|Scanlines|choice|%s|off=Off;on=On|Dark gaps between the game lines, as on a 15 kHz tube. Counts at once, even in a game that is open.\n' \
      "$(scanlines_on && echo on || echo off)"
    while IFS='|' read -r key label min max _ step help; do
      printf 'scanline.%s|Scanlines|%s|number|%s|%s..%s:%s|%s\n' "$key" "$label" "$(scanline_get "$key")" "$min" "$max" "$step" "$help"
    done < <(scanline_table)
    printf 'scanline.reset|Scanlines|Back to the defaults|action|||Darkness, thickness, line height and boost back to the default.\n'
  fi
  # Video Setup > Interlaced hacks.
  while IFS='|' read -r key label state help allowed; do
    opts=""
    [[ ,$allowed, == *,240p,* ]] && opts+="240p=640x240;"
    [[ ,$allowed, == *,filter,* ]] && opts+="filter=Interlaced filter;"
    [[ ,$allowed, == *,pure,* ]] && opts+="pure=Interlaced pure;"
    printf 'mode480.%s|Interlaced hacks|%s|choice|%s|%s|%s\n' "$key" "$label" "$state" "${opts%;}" "$help"
    printf 'deflicker.%s|Interlaced hacks|%s: filter level|choice|%s|light=Light;medium=Medium;strong=Strong|The flicker filter level when Interlaced filter is marked.\n' \
      "$key" "$label" "$(mode480_level "$key")"
  done < <(mode480_rows)
  # ── Audio (Setup > Audio Setup; o volume fica no Frontend) ──
  opts=$(audio_devices | while IFS='|' read -r name desc; do printf '%s|%s\n' "${name/,/_}" "$desc"; done | settings_opts)
  if [[ -n $opts ]]; then
    name=$(audio_current)
    printf 'audio_card|Audio|Sound card|choice|%s|%s|The card used by the system and the emulators. Games opened after the change use it.\n' \
      "${name/,/_}" "$opts"
  fi
  printf 'audio_output|Audio|Stereo or mono|choice|%s|stereo=Stereo;mono=Mono|Mono plays the same sound on both speakers: use it with a single speaker. Games opened after the change use it.\n' \
    "$(audio_output_mode)"
  printf 'mame_latency|Audio|MAME audio latency|number|%s|0..50:0.5|GroovyMAME audio latency (0 = default). Lower responds faster; raise it if the sound crackles.\n' \
    "$(audio_mame_latency)"
  printf 'menu_sounds|Audio|Menu sounds|choice|%s|on=On;off=Off|All the menu sounds on or off. Each event has its own sound and volume, in the Setup (Audio > Menu sounds).\n' \
    "$(menu_sounds_state)"
  printf 'audio.test|Audio|Test sound|action|||A voice on the cabinet speakers: if it is heard, the sound card is the right one.\n'
  # ── GunCon 2 (Setup > Joysticks > GunCon 2), menos a calibracao (os alvos na tela) ──
  printf 'gun_flash|GunCon 2|Screen flash|choice|%s|pulse=Pulse (two light frames on each shot);hold=Hold (light while the trigger is held);off=Off|A CRT gun only finds its aim where the screen is lit: the flash lights it on a shot, so dark parts hit and off screen reloads. Counts at once, even in a game that is open.\n' \
    "$(gunflash_mode)"
  while IFS='|' read -r key label min max _ step help; do
    printf 'gun.%s|GunCon 2|%s|number|%s|%s..%s:%s|%s\n' "$key" "$label" "$(gun_get "$key")" "$min" "$max" "$step" "$help"
  done < <(gun_table)
  printf 'gun_offscreen_reload|GunCon 2|Off-screen reload button|choice|%s|on=On;off=Off|Off the screen the trigger also presses the reload button of Flycast, RetroArch and Keisho.\n' \
    "$(gun_reload_on && echo on || echo off)"
  printf 'gun.reset|GunCon 2|Back to the defaults|action|||Flash, numbers and the reload button back to the defaults. The calibration stays.\n'
  # ── Joysticks > Controller light (lib/buttons.sh) ──
  opts=$(padcolor_table | while IFS='|' read -r name label value; do printf '%s|%s\n' "$value" "$label"; done | settings_opts)
  value=$(padcolor_get)
  # Uma cor fora da tabela (#RRGGBB digitado a mao) continua escolhida.
  [[ ";$opts;" == *";$value="* || $value == off ]] || opts="$value=#$value;$opts"
  printf 'padcolor|Joysticks|Controller light|choice|%s|%s;off=Off|The light colour of DualSense, DualShock 4 and 8BitDo Ultimate 2 (an 8BitDo on Bluetooth saves it once plugged in by USB cable). Off: the controller keeps its own.\n' \
    "$value" "$opts"
  # ── Joysticks > Haptic events (lib/buttons.sh) ──
  printf 'haptic|Joysticks|Haptic strength|choice|%s|low=Low;on=On;high=High;off=Off|The force of every vibration of modern controllers (low is half, high one and a half; off silences every event, also game start and end).\n' \
    "$(haptic_strength_get)"
  opts="off=Off;$(haptic_presets | awk -F'|' '{ print $1 "|" $1 ": " $2 }' | settings_opts)"
  while IFS='|' read -r key label _ help; do
    printf 'haptic.%s|Joysticks|Haptic: %s|choice|%s|%s|%s Picking a preset plays it on the connected controllers.\n' \
      "$key" "$label" "$(haptic_get "$key")" "$opts" "$help"
  done < <(haptic_events)
  # ── A tela ao vivo (config/fliperos-stream) e o marquee para o OBS ──
  if [[ -x $STREAM_GO2RTC ]]; then
    printf 'stream_audio|Live screen|Live screen sound|choice|%s|off=Off;on=On|A copy of the sound for the live screen (an ALSA loopback on the card clock). Games opened after the change get it.\n' \
      "$(audio_stream_enabled && echo on || echo off)"
    printf 'stream_quality|Live screen|Live screen quality|choice|%s|light=Light (weak Wi-Fi);normal=Normal;high=High;max=Maximum (network cable)|The picture of the live screen: more quality takes more network and CPU. It counts from the next connection.\n' \
      "$(conf_get stream_quality 2> /dev/null | grep -xE 'light|high|max' || echo normal)"
  fi
  printf 'marquee_overlay|Live screen|Marquee overlay for OBS|choice|%s|off=Off;on=On|The marquee of the game on screen as a page for an OBS Browser Source (the address is on the Live page of the panel).\n' \
    "$(marquee_overlay_enabled && echo on || echo off)"
  # ── System (Setup > System, e o Frontend de Setup > Games) ──
  name=$(cabinet_name_py default 2> /dev/null) || name=""
  printf 'cabinet_name|System|Cabinet name|text|%s|%s|The name the other cabinets on the network see in party and link play. Up to %s letters and numbers; empty: %s.\n' \
    "$(conf_get cabinet_name 2> /dev/null)" "$CABINET_NAME_MAX" "$CABINET_NAME_MAX" "${name:-a fruit or animal name}"
  opts=$(launcher_available | settings_opts)
  # O jogo direto no boot, quando um ja foi escolhido (no Setup ou na pagina do
  # jogo no painel web).
  if [[ -s $BOOTGAME_FILE ]]; then
    name=$(bootgame_label)
    opts+=";game=A game: ${name//[;=|]/ }"
  fi
  # O boot pela midia, quando um drive ja foi escolhido (Setup > Games > Frontend).
  if conf_get boot_media > /dev/null; then
    opts+=";physical=Boot from media"
  fi
  printf 'launcher|System|What starts when the cabinet turns on|choice|%s|%s|The default launcher (Setup > Games > Frontend). To open one game, use Open at power on on its page in Frontend. Counts from the next boot.\n' \
    "$(launcher_current)" "$opts"
  opts=$(splash_list | settings_opts)
  if [[ -n $opts ]]; then
    printf 'splash|System|Boot splash|choice|%s|%s|The picture while the cabinet boots (Setup > Splash screen, where the preview is). The boot image is rebuilt: about a minute.\n' \
      "$(splash_current 2> /dev/null)" "$opts"
  fi
  printf 'latency|System|Latency mode|choice|%s|standard=Standard;low=Low latency|The emulator settings apply now; the kernel settings after a restart.\n' \
    "$(latency_mode)"
  printf 'debug|System|Debug mode|choice|%s|off=Off;on=On (show all text)|Frontends and emulators follow it now; the boot, after a restart.\n' \
    "$(debug_enabled && echo on || echo off)"
  # ── Services (Setup > System > Services) ──
  while IFS='|' read -r key label state help; do
    printf 'service.%s|Services|%s|choice|%s|boot=Boot;after=After boot;off=Off|%s\n' "$key" "$label" "$state" "$help"
  done < <(services_rows)
  # ── Power, por ultimo ──
  printf 'power.reboot|Power|Restart the cabinet|action|||The game on screen closes and the cabinet restarts. The panel comes back in about a minute.\n'
  printf 'power.poweroff|Power|Turn off the cabinet|action|||The game on screen closes and the cabinet turns off. It is turned on again at the cabinet.\n'
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
  local key=$1 value=$2 name before
  case $key in
    launcher)
      if [[ $value == game && -s $BOOTGAME_FILE ]]; then
        launcher_set game
        return 0
      fi
      if [[ $value == physical ]] && conf_get boot_media > /dev/null; then
        launcher_set physical
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
    monitor)
      # Como o Video Setup > Monitor Type: o mesmo preset com o custom ativo
      # volta a ele (o Reset Geometry); outro preset refaz o modo de boot.
      # "custom" so e valor enquanto ja esta em uso (o crt_range e feito no tubo
      # ou digitado na Geometria).
      if [[ $value == custom ]]; then
        video_custom_active && return 0
        return 2
      fi
      monitor_known "$value" || return 2
      name=$(conf_get monitor 2> /dev/null) || name=""
      [[ $value == "$name" ]] && ! video_custom_active && ! video_boot_mode_missing && return 0
      before=$(video_snapshot)
      if [[ $value == "$name" ]]; then
        geometry_reset
      else
        video_reconfigure_monitor "$value" || return 1
      fi
      video_snapshot_keep "$before"
      settings_video
      ;;
    resolution)
      # Como o Video Setup > Resolution, sem a personalizada (ela testa o modo
      # na grade, no tubo): um modo da lista, que o monitor de agora aceita.
      conf_get connector > /dev/null 2>&1 || return 2
      name=$(conf_get boot_resolution 2> /dev/null) || name=""
      [[ $value == "$name" ]] && return 0
      [[ -n $value ]] && video_resolution_rows | cut -d"|" -f1 | grep -qxF -- "$value" || return 2
      before=$(video_snapshot)
      video_set_resolution "$value" || return 1
      video_snapshot_keep "$before"
      settings_video
      ;;
    video.previous)
      video_previous_restore || return 2
      settings_video
      ;;
    cabinet_name)
      value=$(printf '%s' "$value" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
      ((${#value} <= CABINET_NAME_MAX)) || return 2
      cabinet_name_set "$value"
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
    audio_output)
      audio_set_output "$value" || return 2
      ;;
    mame_latency)
      audio_set_mame_latency "$value" || return 2
      ;;
    gun_flash)
      gunflash_set "$value" || return 2
      ;;
    gun_offscreen_reload)
      gun_reload_set "$value" || return 2
      ;;
    padcolor)
      padcolor_set "$value" || return 2
      ;;
    haptic)
      haptic_strength_set "$value" || return 2
      ;;
    haptic.*)
      haptic_set "${key#haptic.}" "$value" || return 2
      ;;
    gun.reset)
      gun_reset
      ;;
    gun.*)
      [[ -n $(gun_field "${key#gun.}" 3) ]] || return 2
      gun_set "${key#gun.}" "$value" || return 2
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
    level.*)
      # A OSD (config/fliperos-osd): o nivel pelo nome do programa aberto ou
      # do core, que a camada conhece; a linha "other" e a dos outros.
      [[ " $DEFLICKER_LEVELS " == *" $value "* ]] || return 2
      name=$(mode480_key_of "${key#level.}")
      if [[ $value == off ]]; then
        mode480_set "$name" pure || return 2
      else
        mode480_set "$name" filter "$value" || return 2
      fi
      ;;
    osd)
      [[ $value == on || $value == off ]] || return 2
      conf_set osd "$value"
      ;;
    osd_combo)
      # O atalho da OSD (Frontend controls > OSD MENU): os comandos do Button
      # mapping, "start+down" ou de jogadores diferentes "1:start+2:start";
      # vazio, nenhum. A OSD o rele sozinha.
      [[ -z $value || $value =~ ^([0-9]+:)?[a-z0-9]+(\+([0-9]+:)?[a-z0-9]+)*$ ]] || return 2
      conf_set osd_combo "$value"
      ;;
    osd_key)
      # As teclas dela, como codigos do evdev ("119,164,201,207"); vazio, 0.
      [[ -z $value || $value =~ ^[0-9]+(,[0-9]+)*$ ]] || return 2
      conf_set osd_key "${value:-0}"
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
    scanlines)
      scanlines_available && scanlines_set_on "$value" || return 2
      ;;
    scanline.reset)
      scanlines_available || return 2
      scanline_reset
      ;;
    scanline.*)
      # A camada GL ou Vulkan do jogo aberto rele do fliperos.conf.
      scanlines_available && scanline_set "${key#scanline.}" "$value" || return 2
      ;;
    *) return 2 ;;
  esac
}

# ── O resto do Setup no painel web ───────────────────────────────
# O Setup do painel (config/web/setup.js) mostra a arvore inteira do Setup.
# Daqui: os itens que so aparecem em alguns gabinetes (os mesmos do Video
# Setup e do Joysticks) e o que da para mudar de longe sem tela: Quirks,
# Folders, os frontends da pessoa, Bluetooth, System Update e a AttractPlus
# ROM List. O que precisa do tubo o painel abre no gabinete
# (screens/panel.sh, --screen).

# setup_driver_hint: a dica do Video driver quando a placa tem escolha (AMD
# que aceita os dois drivers, ou NVIDIA). Status 1: sem escolha.
setup_driver_hint() {
  if [[ -n $(drm_dual_amd_cards) ]]; then
    echo "radeon (tested on the CRT) or amdgpu (with Vulkan)."
  elif nvidia_card > /dev/null; then
    echo "nouveau or NVIDIA's own driver (native 15 kHz, 3D speed)."
  else
    return 1
  fi
}

# setup_lowdot_hint: a dica do Low resolutions, o grid de dotclock baixo com
# uma NVIDIA (nouveau) na saida principal, ou numa DisplayPort (o conversor
# decide). Status 1: nao se aplica.
setup_lowdot_hint() {
  local conn
  conn=$(conf_get connector 2> /dev/null) || conn=""
  if [[ $conn == DP-* ]] && drm_output_low_dotclock_testable "$(video_conf_card)" "$conn" 2> /dev/null; then
    echo "Test if the DisplayPort converter shows native 15 kHz modes."
  elif drm_card_low_dotclock_testable "$(conf_get card 2> /dev/null)" 2> /dev/null; then
    echo "NVIDIA: test if this card shows native 15 kHz modes."
  else
    return 1
  fi
}

# setup_firmware_hint: o ATOM-15, so numa placa AMD e no sistema instalado.
setup_firmware_hint() {
  is_installed && ! is_live && atom15_card > /dev/null 2>&1 || return 1
  echo "15 kHz from power on. Rewrites the card's BIOS: at your own risk."
}

# setup_items: "item|ID|0 ou 1" dos itens que dependem do gabinete e
# "info|ID|TEXTO" do que o painel mostra junto de um item.
setup_items() {
  local hint
  printf 'item|scanlines|%d\n' "$(scanlines_available && echo 1 || echo 0)"
  hint=$(setup_driver_hint) && printf 'item|driver|1\ninfo|driver|%s\n' "$hint" || echo "item|driver|0"
  hint=$(setup_lowdot_hint) && printf 'item|lowdot|1\ninfo|lowdot|%s\n' "$hint" || echo "item|lowdot|0"
  hint=$(setup_firmware_hint) && printf 'item|firmware|1\ninfo|firmware|%s\n' "$hint" || echo "item|firmware|0"
  printf 'item|bluetooth|%d\n' "$(bluetooth_present && echo 1 || echo 0)"
  printf 'item|romlist|%d\n' "$(launcher_installed attractplus && echo 1 || echo 0)"
  printf 'info|monitors|%s\n' "$(mm_count)"
  printf 'info|buttons|%s\n' "$(buttons_players_line 2> /dev/null | tr '\n|' '  ')"
  printf 'info|lpt|%s\n' "$(lpt_current)"
  printf 'info|latency|%s\n' "$(latency_mode)"
  return 0
}

# quirks_cli list|devices|add NOME CODIGO|delete CODIGO (Setup > System >
# Quirks): add e delete levam os quirks para a linha do kernel, como as telas.
# Status: 1 codigo invalido, 2 pedido errado (ou ja ha 4 do usbhid: "max" na
# saida), 3 o dispositivo ja tem quirk.
quirks_cli() {
  local rc
  case ${1:-} in
    list) quirks_list ;;
    devices) quirks_usb_devices | sed 's/  /|/' ;;
    add)
      [[ -n ${3:-} ]] || return 1
      quirk_add "${2:-}" "$3"
      rc=$?
      ((rc == 2)) && echo "max=$QUIRKS_MAX"
      ((rc == 0)) || return "$rc"
      settings_boot
      ;;
    delete)
      quirks_list | cut -d'|' -f1 | grep -qxF -- "${2:-}" || return 2
      quirk_delete "$2" || return 1
      settings_boot
      ;;
    *) return 2 ;;
  esac
}

# folders_cli list [PASTA] | link PASTA ALVO | unlink PASTA | shown PASTA (Setup >
# Games > Folders). list: "pasta|estado|alvo|tem pastas dentro|descricao" das
# raizes, ou das pastas de dentro da PASTA. link e unlink imprimem o motivo de uma
# recusa (status 1) e, com as pastas de jogos ou de arte, refazem o frontend.
# cloud-export e cloud-restore: a lista das custom folders do backup na nuvem
# (lib/folders.sh); cloud-restore imprime "restored=PASTA" de cada uma.
folders_cli() {
  local rel rc=0
  case ${1:-} in
    list)
      if [[ -n ${2:-} ]]; then
        folders_known "$2" || return 2
        rel=$(folders_children "$2")
      else
        rel=$(folders_list)
      fi
      while IFS= read -r rel; do
        [[ -n $rel ]] || continue
        printf '%s|%s|%s|%d|%s\n' "$rel" "$(folders_state "$rel")" "$(folders_target "$rel" 2> /dev/null)" \
          "$(folders_container "$rel" && echo 1 || echo 0)" "$(folders_description "$rel" | tr '|\n' '  ')"
      done <<< "$rel"
      printf 'start|%s\n' "$(folders_browse_start)"
      ;;
    link)
      folders_known "${2:-}" && [[ -n ${3:-} ]] || return 2
      if ! folders_link "$2" "$3"; then
        echo "${FOLDERS_ERROR:-Could not link the folder (details in the log).}"
        return 1
      fi
      [[ -n $FOLDERS_KEPT ]] && echo "kept=${FOLDERS_KEPT/#$FOLDERS_HOME/\~}"
      folders_cli_refresh "$2"
      ;;
    unlink)
      folders_known "${2:-}" || return 2
      folders_unlink "$2" || rc=$?
      if ((rc == 1)); then
        echo "${FOLDERS_ERROR:-Could not unlink the folder (details in the log).}"
        return 1
      fi
      ((rc == 2)) && echo "new=1"
      folders_cli_refresh "$2"
      ;;
    shown)
      # Como a pasta aparece nos textos: o caminho, e onde ela esta de verdade
      # quando e um atalho para outro disco (folders_shown).
      folders_known "${2:-}" || return 2
      folders_shown "$2"
      ;;
    cloud-export)
      # O backup na nuvem (config/fliperos-cloud), antes de cada passada.
      folders_cloud_export
      ;;
    cloud-restore)
      # Depois de receber da nuvem: as custom folders que faltam aqui.
      local refresh=""
      while IFS= read -r rel; do
        [[ -n $rel ]] || continue
        echo "restored=$rel"
        [[ -n $refresh || ! ($rel == roms* || $rel == media*) ]] || refresh=$rel
      done < <(folders_cloud_restore)
      [[ -z $refresh ]] || folders_cli_refresh "$refresh"
      ;;
    *) return 2 ;;
  esac
  return 0
}

# folders_cli_refresh PASTA: as pastas de jogos e de arte mudaram de lugar,
# o frontend padrao le de novo (o screen_folders_refresh sem a tela).
folders_cli_refresh() {
  [[ $1 == roms || $1 == roms/* || $1 == media || $1 == media/* ]] || return 0
  frontends_configure "$(launcher_current)" >> "$FLIPEROS_LOG" 2>&1
  return 0
}

# frontends_cli list|save NOME ROTULO COMANDO|delete NOME (Setup > Games >
# Frontend > a custom frontend). list: "nome|rotulo|comando|instalado".
# save com NOME vazio cria um novo e imprime o nome dele. Status 2: pedido
# errado; 1: rotulo ou comando que nao serve.
frontends_cli() {
  local name label
  case ${1:-} in
    list)
      while IFS='|' read -r name label; do
        [[ -n $name ]] || continue
        printf '%s|%s|%s|%d\n' "$name" "$label" "$(launcher_field "$name" 3)" \
          "$(launcher_installed "$name" && echo 1 || echo 0)"
      done < <(launcher_custom_list)
      ;;
    save)
      [[ -z ${2:-} ]] || launcher_custom "$2" || return 2
      launcher_custom_save "${2:-}" "${3:-}" "${4:-}" || return 1
      ;;
    delete)
      launcher_custom "${2:-}" || return 2
      launcher_custom_delete "$2"
      ;;
    *) return 2 ;;
  esac
}

# bluetooth_cli status|devices|scan [SEGUNDOS]|pair MAC|connect MAC|
# disconnect MAC|remove MAC|power on|off (Setup > Joysticks > Bluetooth).
# Os aparelhos: "MAC|NOME|ICONE|pareado|conectado". Status 2: pedido errado.
bluetooth_cli() {
  local mac_re='^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$'
  case ${1:-} in
    status) bluetooth_status ;;
    devices) bluetooth_devices ;;
    scan)
      [[ -z ${2:-} || ${2:-} =~ ^[0-9]{1,2}$ ]] || return 2
      bluetooth_scan "${2:-$BLUETOOTH_SCAN}"
      ;;
    pair)
      [[ ${2:-} =~ $mac_re ]] || return 2
      bluetooth_pair "$2"
      ;;
    connect | disconnect | remove)
      [[ ${2:-} =~ $mac_re ]] || return 2
      bluetooth_do "$1" "$2"
      ;;
    power)
      [[ ${2:-} == on || ${2:-} == off ]] || return 2
      bluetooth_do power "$2"
      ;;
    *) return 2 ;;
  esac
}

# system_update_cli: o System Update sem tela (Setup > System > System
# Update), com os eventos de progresso.
system_update_cli() {
  update_run || return 1
  ev_step 100 "The system is up to date"
}

# romlists_cli: a AttractPlus ROM List de todas as pastas de arcade, sem
# perguntar (a tela deixa escolher as pastas), com os eventos de progresso.
romlists_cli() {
  local result line
  local -a found
  launcher_installed attractplus || { ev_fail "Attract-Mode Plus is not installed"; return 2; }
  mapfile -t found < <(frontends_romlist_systems)
  if ((${#found[@]} == 0)); then
    frontends_attract
    ev_fail "No arcade games were found"
    return 1
  fi
  result=$(mktemp)
  frontends_romlist "$result" "${found[@]}" || { rm -f "$result"; return 1; }
  while IFS=$'\t' read -r line _; do
    [[ -n $line && $line != total ]] && ev_msg "$line: $(awk -F'\t' -v n="$line" '$1 == n { print $2 }' "$result") games"
  done < "$result"
  ev_step 100 "$(awk -F'\t' '$1 == "total" { print $2 }' "$result") games in the lists"
  rm -f "$result"
}
