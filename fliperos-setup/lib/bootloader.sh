# shellcheck shell=bash
# Linha do kernel do sistema instalado (Limine).
#
# Os parametros ficam em /etc/default/fliperos-boot (FLIPEROS_CMDLINE), o
# equivalente do /etc/default/grub; o fliperos-limine-update leva kernel,
# initrd e menu para a ESP.

# Base de todo sistema instalado: splash, console sem apagar (o
# consoleblank=0 do GroovyArcade) e o radeon nas placas SI/CIK, que e onde
# o 15 kHz foi validado no gabinete. BOOT_SILENT: boot direto no Plymouth,
# sem mensagens do kernel e do udev nem o cursor piscando antes dele (o
# rd.udev.log-priority=3 do GA, no nome atual).
BOOT_SILENT="loglevel=3 rd.udev.log_level=3 udev.log_level=3 vt.global_cursor_default=0"
BOOT_BASE_CMDLINE="quiet splash $BOOT_SILENT consoleblank=0 radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0"

# boot_driver_params LINHA imprime os parametros de driver de uma linha do
# kernel: a entrada "Intel 15 kHz" do boot leva o i915.no_ytiled_scanout=1,
# sem o qual 480i nao funciona em Intel Gen9, e ele tem de ir junto para o
# sistema instalado.
boot_driver_params() {
  local word out=()
  for word in $1; do
    case $word in
      i915.* | nouveau.*) out+=("$word") ;;
    esac
  done
  printf '%s\n' "${out[*]}"
}

# ── Driver das placas AMD SI/CIK ─────────────────────────────────
# Placas que os dois drivers aceitam (drm_card_dual_amd) usam o radeon por
# padrao, como no GroovyArcade. amd_driver= no fliperos.conf (Setup > System
# > Video driver, ou a pergunta da instalacao) troca para o amdgpu. So a
# linha do kernel escolhe: o modprobe.d nao repete o si_support/cik_support,
# senao venceria a linha (o modprobe aplica as opcoes dos arquivos depois
# das da linha) e a entrada de volta ao radeon do Limine nao valeria.
AMD_DRIVER_KEYS="radeon.si_support radeon.cik_support amdgpu.si_support amdgpu.cik_support amdgpu.dc"
AMD_MODPROBE_CONF=${AMD_MODPROBE_CONF:-/etc/modprobe.d/fliperos.conf}

amd_driver() {
  local driver
  driver=$(conf_get amd_driver 2> /dev/null) || driver=radeon
  [[ $driver == amdgpu ]] || driver=radeon
  printf '%s\n' "$driver"
}

# amd_driver_recommended: o radeon, com que o 15 kHz foi validado no CRT.
amd_driver_recommended() {
  echo radeon
}

# amd_driver_mismatch imprime "PLACA|DRIVER EM USO|RECOMENDADO" quando uma
# placa que aceita os dois drivers roda com o que nao e o recomendado.
amd_driver_mismatch() {
  local card running recommended
  recommended=$(amd_driver_recommended)
  for card in $(drm_dual_amd_cards); do
    running=$(drm_card_driver "$card") || continue
    [[ $running == "$recommended" ]] && continue
    printf '%s|%s|%s\n' "$card" "$running" "$recommended"
    return 0
  done
  return 1
}

# amd_driver_params DRIVER. No amdgpu vai o amdgpu.dc=0: o kernel 6.18 nao
# tem saida analogica (VGA, DVI-I) no codigo de video novo (DC) das GCN 1.0
# e 1.1, que so chegou no 6.19; o antigo tem, e e nele que o patch de PLL
# do kernel 15 kHz (05_linux_15khz_amdgpu_pll_fix) atua.
amd_driver_params() {
  case $1 in
    amdgpu) echo "radeon.si_support=0 radeon.cik_support=0 amdgpu.si_support=1 amdgpu.cik_support=1 amdgpu.dc=0" ;;
    *) echo "radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0" ;;
  esac
}

# amd_driver_cmdline LINHA troca os parametros de driver pelos do
# fliperos.conf. Sem amd_driver gravado a linha fica como esta.
amd_driver_cmdline() {
  local line=$1 driver key
  driver=$(conf_get amd_driver 2> /dev/null) || { printf '%s\n' "$line"; return 0; }
  for key in $AMD_DRIVER_KEYS; do
    line=$(cmdline_remove "$line" "$key")
  done
  words "$line $(amd_driver_params "$driver")"
}

# amd_driver_modprobe_clean [RAIZ] tira o si_support/cik_support que o
# fliperos.conf do modprobe.d das imagens antigas (ver AMD_DRIVER_KEYS); o
# resto das opcoes (dpm=1, som) fica. AMD_MODPROBE_CHANGED=1 quando mudou
# (o initramfs leva o modprobe.d e tem de ser refeito).
amd_driver_modprobe_clean() {
  local file=${1:-}$AMD_MODPROBE_CONF tmp
  [[ -f $file ]] || return 0
  grep -Eq '^options (radeon|amdgpu) .*(si|cik)_support=' "$file" || return 0
  AMD_MODPROBE_CHANGED=1
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk '
    $1 == "options" && ($2 == "radeon" || $2 == "amdgpu") {
      out = "options " $2
      for (i = 3; i <= NF; i++) if ($i !~ /^(si|cik)_support=/) out = out " " $i
      if (out != "options " $2) print out
      next
    }
    { print }' "$file" > "$tmp" && chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# amd_driver_apply DRIVER grava a escolha. A linha do kernel (e o
# initramfs, se o modprobe.d mudou) ficam com o boot_apply, so no sistema
# instalado.
amd_driver_apply() {
  conf_set amd_driver "$1" || return 1
  AMD_MODPROBE_CHANGED=0
  amd_driver_modprobe_clean || return 1
  ((AMD_MODPROBE_CHANGED)) && BOOT_INITRAMFS=1
  log_info "driver AMD: $1"
}

# ── Driver das placas NVIDIA ─────────────────────────────────────
# nouveau (o padrao, ja no kernel) ou o driver da NVIDIA, baixado do apt
# pelo config/fliperos-nvidia. Os dois ficam instalados e a linha do kernel
# escolhe (nvidia_driver= no fliperos.conf), como no radeon/amdgpu: a troca
# passa pelo mesmo teste de imagem e o Limine tem a entrada de volta ao
# nouveau. O modeset e o fbdev do nvidia-drm sao o KMS e o console dele:
# o RetroArch, o Switchres e o modo de boot do kernel 15 kHz saem por ali.
NVIDIA_CMD=${NVIDIA_CMD:-${FLIPEROS_BIN:-/opt/fliperos/bin}/fliperos-nvidia}
NVIDIA_DRIVER_KEYS="modprobe.blacklist nvidia-drm.modeset nvidia-drm.fbdev"
NVIDIA_MODULES="nvidia,nvidia_drm,nvidia_modeset,nvidia_uvm"

# nvidia_card: a primeira placa NVIDIA (vendor 0x10de).
nvidia_card() {
  local card
  for card in $(drm_cards); do
    [[ $(cat "$DRM_SYSFS/$card/device/vendor" 2> /dev/null) == 0x10de ]] && { echo "$card"; return 0; }
  done
  return 1
}

# nvidia_device CARD: o PCI ID da placa, sem o 0x (17c8).
nvidia_device() {
  local id
  id=$(cat "$DRM_SYSFS/$1/device/device" 2> /dev/null) || return 1
  printf '%s\n' "${id#0x}"
}

nvidia_driver() {
  local driver
  driver=$(conf_get nvidia_driver 2> /dev/null) || driver=nouveau
  [[ $driver == nvidia ]] || driver=nouveau
  printf '%s\n' "$driver"
}

nvidia_installed() {
  [[ -x $NVIDIA_CMD ]] && "$NVIDIA_CMD" installed
}

# nvidia_driver_params DRIVER: o que a linha do kernel leva para ele.
nvidia_driver_params() {
  case $1 in
    nvidia) echo "modprobe.blacklist=nouveau nvidia-drm.modeset=1 nvidia-drm.fbdev=1" ;;
    *) echo "modprobe.blacklist=$NVIDIA_MODULES" ;;
  esac
}

# nvidia_driver_cmdline LINHA troca os parametros de driver pelos do
# fliperos.conf. Sem nvidia_driver gravado (nunca trocado) a linha fica.
nvidia_driver_cmdline() {
  local line=$1 driver key
  driver=$(conf_get nvidia_driver 2> /dev/null) || { printf '%s\n' "$line"; return 0; }
  for key in $NVIDIA_DRIVER_KEYS; do
    line=$(cmdline_remove "$line" "$key")
  done
  words "$line $(nvidia_driver_params "$driver")"
}

# nvidia_driver_install [--progress]: baixa e instala o driver desta placa.
nvidia_driver_install() {
  local card
  ev_step 0 "Starting"
  card=$(nvidia_card) || { ev_fail "no NVIDIA card here"; return 1; }
  if [[ ! -x $NVIDIA_CMD ]]; then
    ev_fail "the NVIDIA driver installer ($NVIDIA_CMD) is missing"
    return 1
  fi
  log_line cmd "\$ $NVIDIA_CMD install $(nvidia_device "$card") --progress"
  "$NVIDIA_CMD" install "$(nvidia_device "$card")" --progress 2>> "$FLIPEROS_LOG"
}

# nvidia_driver_apply DRIVER grava a escolha. O teste de dotclock baixo e
# de um driver: trocado, ele e esquecido (o Video Setup o repete). O Xorg
# muda de driver junto (xorg_generate).
nvidia_driver_apply() {
  conf_set nvidia_driver "$1" || return 1
  # Ate o grid passar de novo, super resolucao: o modo de boot nativo do
  # outro driver pode nao dar imagem neste.
  if conf_get low_dotclock_pci > /dev/null 2>&1; then
    conf_unset low_dotclock_pci
    conf_unset low_dotclock_min
    video_low_dotclock_apply || log_warn "driver NVIDIA: o video nao foi refeito"
  fi
  BOOT_INITRAMFS=1
  log_info "driver NVIDIA: $1"
}

# video_driver_apply DRIVER: a troca de qualquer placa (a volta do teste).
video_driver_apply() {
  case $1 in
    nouveau | nvidia) nvidia_driver_apply "$1" ;;
    *) amd_driver_apply "$1" ;;
  esac
}

# video_driver_card: a placa que tem escolha de driver (AMD SI/CIK ou NVIDIA).
video_driver_card() {
  local card
  card=$(drm_dual_amd_cards | head -1)
  [[ -n $card ]] || card=$(nvidia_card) || return 1
  printf '%s\n' "$card"
}

# ── Teste da troca de driver ─────────────────────────────────────
# Como a troca de resolucao do Windows: trocado o driver, o boot seguinte
# pede para confirmar a imagem (screen_amd_driver_confirm, 15 s, antes do
# launcher); sem resposta, volta ao driver anterior e reinicia. A vigia do
# boot (fliperos-driver-trial.service, amd_driver_trial_boot) cobre a tela
# que nao chega a abrir, e um boot de teste que nao terminou (travou e foi
# desligado no botao) volta ao anterior no boot seguinte. Estado no
# fliperos.conf: amd_driver_trial (em teste), amd_driver_previous e
# amd_driver_trial_boots.
AMD_TRIAL_GRACE=${AMD_TRIAL_GRACE:-120}
AMD_TRIAL_SECONDS=${AMD_TRIAL_SECONDS:-15}

amd_driver_trial() {
  conf_get amd_driver_trial 2> /dev/null
}

# amd_driver_trial_clear [ARQUIVO]
amd_driver_trial_clear() {
  local file=${1:-$FLIPEROS_CONF} key
  for key in amd_driver_trial amd_driver_previous amd_driver_trial_boots; do
    conf_unset "$key" "$file"
  done
}

# amd_driver_trial_start NOVO ANTERIOR [ARQUIVO]: ANTERIOR e o driver com
# que a placa roda agora, o que se sabe que da imagem.
amd_driver_trial_start() {
  local file=${3:-$FLIPEROS_CONF}
  amd_driver_trial_clear "$file"
  [[ -n $2 && $1 != "$2" ]] || return 0
  conf_set amd_driver_trial "$1" "$file"
  conf_set amd_driver_previous "$2" "$file"
  conf_set amd_driver_trial_boots 0 "$file"
  log_info "driver AMD em teste: $1 (anterior $2)"
}

amd_driver_trial_confirm() {
  log_info "driver AMD confirmado: $(amd_driver_trial)"
  amd_driver_trial_clear
}

# amd_driver_trial_running: a placa roda com o driver em teste? Pela
# entrada de volta do Limine ela pode ter aberto com o anterior.
amd_driver_trial_running() {
  local trial card
  trial=$(amd_driver_trial) || return 1
  card=$(video_driver_card) || return 1
  [[ $(drm_card_driver "$card") == "$trial" ]]
}

# amd_driver_revert volta ao driver anterior (linha do kernel e menu do
# Limine) e encerra o teste. Reiniciar fica com quem chama.
amd_driver_revert() {
  local previous
  previous=$(conf_get amd_driver_previous 2> /dev/null)
  log_warn "driver AMD: $(amd_driver_trial) sem confirmacao, de volta a ${previous:-?}"
  amd_driver_trial_clear
  [[ -n $previous ]] || return 1
  video_driver_apply "$previous" || return 1
  is_installed && ! is_live || return 0
  xorg_generate
  boot_apply
}

# nvidia_driver_boot_check: no boot. O driver da NVIDIA escolhido, mas sem o
# modulo para este kernel (um kernel novo que o DKMS nao compilou): com o
# nouveau na lista negra nao haveria imagem. Tenta o DKMS; sem modulo, volta
# ao nouveau e reinicia.
nvidia_driver_boot_check() {
  [[ $(nvidia_driver) == nvidia ]] || return 0
  nvidia_installed && return 0
  log_warn "driver NVIDIA: sem modulo para $(uname -r), tentando o DKMS"
  run_logged dkms autoinstall
  nvidia_installed && { run_logged modprobe nvidia_drm; return 0; }
  log_warn "driver NVIDIA: sem modulo, de volta ao nouveau"
  nvidia_driver_apply nouveau || return 1
  xorg_generate
  boot_apply && run_logged systemctl reboot
}

# amd_driver_trial_boot: no boot (fliperos-driver-trial.service).
amd_driver_trial_boot() {
  local boots
  nvidia_driver_boot_check
  amd_driver_trial > /dev/null || return 0
  # Aberto pela entrada de volta do menu do Limine: a pessoa ja escolheu o
  # anterior, e ele e o que esta rodando; nao ha o que reiniciar.
  if ! amd_driver_trial_running; then
    amd_driver_revert
    return 0
  fi
  boots=$(conf_get amd_driver_trial_boots 2> /dev/null) || boots=0
  [[ $boots =~ ^[0-9]+$ ]] || boots=0
  boots=$((boots + 1))
  conf_set amd_driver_trial_boots "$boots"
  # O boot de teste anterior nem confirmou nem voltou: travou.
  if ((boots >= 2)); then
    amd_driver_revert && run_logged systemctl reboot
    return 0
  fi
  # A tela de confirmacao abre antes do launcher; se ate aqui ela nao
  # resolveu (a tela nao abriu), volta ao anterior.
  sleep "$AMD_TRIAL_GRACE"
  amd_driver_trial > /dev/null || return 0
  amd_driver_revert && run_logged systemctl reboot
  return 0
}

# boot_compose LINHA aplica a uma linha do kernel o que o setup decidiu:
# modo de latencia, quirks do usbhid, modo debug (boot calado ou nao),
# parametros de video do teste de saidas (se houve teste) e dos monitores
# extras, console na placa certa (fbcon=map) e orientacao.
boot_compose() {
  local line=$1 conn video orientation fb word out=() extra
  conn=$(conf_get connector 2> /dev/null) || conn=""
  video=$(conf_get kernel_video 2> /dev/null) || video=""
  orientation=$(conf_get orientation 2> /dev/null) || orientation=horizontal
  fb=$(conf_get fb_map 2> /dev/null) || fb=0
  for word in $line; do
    [[ $word == fbcon=map:* ]] && continue
    out+=("$word")
  done
  line=$(latency_cmdline "${out[*]}")
  line=$(amd_driver_cmdline "$line")
  line=$(nvidia_driver_cmdline "$line")
  line=$(quirks_cmdline "$line")
  line=$(debug_cmdline "$line")
  line=$(i8042_cmdline "$line")
  if [[ -n $conn ]]; then
    line=$(words "$(cmdline_without_video "$line") $video")
    line=$(mm_cmdline "$line")
  fi
  [[ -n $fb && $fb != 0 ]] && line="$line fbcon=map:$fb"
  while IFS= read -r extra; do
    extra=$(mm_entry_name "$extra")
    [[ $extra == "$conn" ]] && continue
    line=$(orientation_cmdline "$line" "$extra" "$orientation")
  done < <(mm_extras | sed 's/^[^:]*://' | sort -u)
  line=$(orientation_cmdline "$line" "$conn" "$orientation")
  # Em pe, o console em 640x480i com o EDID dos dois modos (lib/video.sh).
  vertical_console_cmdline "$line" "$conn" "$orientation"
}

# Placa-mae sem a porta do mouse PS/2 (AUX): o kernel espera por ela uns 2 s
# a cada boot e avisa no log deste boot. Com o i8042.noaux ele nem tenta; o
# teclado PS/2 segue funcionando. Nunca sai sozinho da linha: com ele o
# aviso some.
I8042_NOAUX_HINT="If AUX port is really absent please use the 'i8042.noaux' option"
KERNEL_LOG=${KERNEL_LOG:-dmesg}

# i8042_noaux_needed: o kernel deste boot pediu o i8042.noaux. Sem o -q: ele
# sairia no aviso, o dmesg morreria com SIGPIPE e o pipefail daria falha.
i8042_noaux_needed() {
  $KERNEL_LOG 2> /dev/null | grep -F "$I8042_NOAUX_HINT" > /dev/null
}

# i8042_cmdline LINHA acrescenta o i8042.noaux quando o kernel o pediu.
i8042_cmdline() {
  if [[ " $1 " != *" i8042.noaux "* ]] && i8042_noaux_needed; then
    printf '%s i8042.noaux\n' "$1"
  else
    printf '%s\n' "$1"
  fi
}

# boot_i8042_check (uma vez por boot, pelo --services-late): grava o
# i8042.noaux no sistema instalado quando falta, para o proximo boot.
boot_i8042_check() {
  local line
  is_installed && ! is_live || return 0
  line=$(boot_read_cmdline) || return 0
  [[ " $line " == *" i8042.noaux "* ]] && return 0
  i8042_noaux_needed || return 0
  log_info "i8042: porta AUX ausente, i8042.noaux na linha do kernel"
  boot_apply
}

# boot_install_cmdline imprime a linha do kernel para um disco novo. Sem
# teste de saidas, valem os parametros de video da entrada de boot
# escolhida no menu da midia.
boot_install_cmdline() {
  local live base
  live=$(< "$PROC_CMDLINE")
  base="$BOOT_BASE_CMDLINE $(boot_driver_params "$live")"
  if ! conf_get connector > /dev/null 2>&1; then
    base="$base $(cmdline_video_params "$live")"
  fi
  boot_compose "$(words "$base")"
}

# boot_read_cmdline [ARQUIVO] imprime o FLIPEROS_CMDLINE gravado.
boot_read_cmdline() {
  local file=${1:-$BOOT_DEFAULTS}
  [[ -f $file ]] || return 1
  sed -n 's/^FLIPEROS_CMDLINE="\(.*\)"$/\1/p' "$file" | head -1
}

# boot_write_cmdline LINHA [ARQUIVO] troca so a linha, mantendo o resto.
boot_write_cmdline() {
  local line=$1 file=${2:-$BOOT_DEFAULTS} tmp
  if [[ ! -f $file ]]; then
    mkdir -p "$(dirname "$file")"
    printf '%s\n' \
      "# Parametros do kernel do FliperOS. Depois de editar a mao:" \
      "#   sudo fliperos-limine-update" \
      "FLIPEROS_CMDLINE=\"$line\"" \
      "FLIPEROS_TIMEOUT=\"3\"" > "$file"
    return
  fi
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk -v l="$line" '
    /^FLIPEROS_CMDLINE=/ { print "FLIPEROS_CMDLINE=\"" l "\""; found = 1; next }
    { print }
    END { if (!found) print "FLIPEROS_CMDLINE=\"" l "\"" }' "$file" > "$tmp" &&
    chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# boot_write_var CHAVE VALOR [ARQUIVO] troca outra variavel do
# /etc/default/fliperos-boot (FLIPEROS_QUIET, FLIPEROS_TIMEOUT).
boot_write_var() {
  local key=$1 value=$2 file=${3:-$BOOT_DEFAULTS} tmp
  [[ -f $file ]] || return 0
  tmp=$(mktemp "$file.XXXXXX") || return 1
  awk -v k="$key" -v v="$value" '
    $0 ~ "^" k "=" { print k "=\"" v "\""; found = 1; next }
    { print }
    END { if (!found) print k "=\"" v "\"" }' "$file" > "$tmp" &&
    chmod 644 "$tmp" && mv -f "$tmp" "$file"
}

# boot_menu_timeout LAUNCHER: os segundos do menu (escondido) do Limine
# (FLIPEROS_TIMEOUT). Com o jogo direto no boot, 1: o boot mais curto, e uma
# tecla segurada ainda abre o menu (o kernel anterior, o driver radeon, o
# diagnostico). Com os outros launchers, os 3 de sempre. So reescreve o menu
# quando o valor muda.
boot_menu_timeout() {
  local want=3 now
  [[ $1 == game ]] && want=1
  [[ -f $BOOT_DEFAULTS ]] || return 0
  now=$(sed -n 's/^FLIPEROS_TIMEOUT="\(.*\)"$/\1/p' "$BOOT_DEFAULTS" | head -1)
  [[ $now == "$want" ]] && return 0
  boot_write_var FLIPEROS_TIMEOUT "$want" || return 1
  log_info "menu do Limine: ${want} s"
  if is_installed && ! is_live; then
    run_logged "$LIMINE_UPDATE"
  fi
  return 0
}

# boot_apply grava no sistema instalado a linha do kernel da configuracao
# atual (modo de boot, EDID, orientacao e latencia) e atualiza o menu do
# Limine.
boot_apply() {
  local line
  line=$(boot_read_cmdline) || line=$BOOT_BASE_CMDLINE
  line=$(boot_compose "$line")
  boot_write_cmdline "$line" || return 1
  log_info "linha do kernel: $line"
  # Um EDID novo (resolucao personalizada) e o modprobe.d de um driver AMD
  # trocado so valem se estiverem no initramfs; o hook do initramfs tambem
  # chama o fliperos-limine-update.
  if [[ $(conf_get boot_resolution 2> /dev/null) == custom ]] || ((${BOOT_INITRAMFS:-0})); then
    run_logged update-initramfs -u -k all
  else
    run_logged "$LIMINE_UPDATE"
  fi
}
