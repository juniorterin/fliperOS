#!/usr/bin/env bash
# ============================================================
#  FliperOS Setup Script v0.2
#  Ubuntu 22.04 / 24.04 LTS — Arcade CRT 15kHz
#  Uso: sudo bash fliperos-setup.sh [--fase N] [--dry-run]
# ============================================================

set -euo pipefail

# ── Cores de terminal ────────────────────────────────────────
GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'
BLU='\033[0;34m'; CYN='\033[0;36m'; DIM='\033[2m'
BLD='\033[1m'; RST='\033[0m'

FLIPEROS_VERSION="0.6"
FLIPEROS_USER="${SUDO_USER:-fliperos}"
INSTALL_DIR="/opt/fliperos"
LOG_FILE="/var/log/fliperos-setup.log"
DRY_RUN=false
FASE_ALVO=""

# ── Args ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --fase) [[ $# -ge 2 ]] || { echo "--fase requer valor"; exit 2; }; FASE_ALVO="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=true;   shift   ;;
    --user) [[ $# -ge 2 ]] || { echo "--user requer valor"; exit 2; }; FLIPEROS_USER="$2"; shift 2 ;;
    *) echo "Uso: sudo bash fliperos-setup.sh [--fase 1-5] [--dry-run] [--user <nome>]"; exit 1 ;;
  esac
done

# ── Helpers ──────────────────────────────────────────────────
log()  { echo -e "${DIM}[$(date +%H:%M:%S)]${RST} $*" | tee -a "$LOG_FILE"; }
ok()   { echo -e "${GRN}✓${RST} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YLW}⚠${RST} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}✗${RST} $*" | tee -a "$LOG_FILE"; exit 1; }
info() { echo -e "${BLU}→${RST} $*" | tee -a "$LOG_FILE"; }
step() { echo -e "\n${BLD}${CYN}══ $* ══${RST}" | tee -a "$LOG_FILE"; }

run() {
  if $DRY_RUN; then
    echo -e "${DIM}[DRY-RUN]${RST} $*"
  else
    eval "$*" >> "$LOG_FILE" 2>&1 || err "Falhou: $*"
  fi
}

banner() {
  echo -e "${GRN}"
  cat << 'EOF'
  ███████╗██╗     ██╗██████╗ ███████╗██████╗  ██████╗ ███████╗
  ██╔════╝██║     ██║██╔══██╗██╔════╝██╔══██╗██╔═══██╗██╔════╝
  █████╗  ██║     ██║██████╔╝█████╗  ██████╔╝██║   ██║███████╗
  ██╔══╝  ██║     ██║██╔═══╝ ██╔══╝  ██╔══██╗██║   ██║╚════██║
  ██║     ███████╗██║██║     ███████╗██║  ██║╚██████╔╝███████║
  ╚═╝     ╚══════╝╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
EOF
  echo -e "${RST}${DIM}  Ubuntu CRT 15kHz — Setup v${FLIPEROS_VERSION}${RST}\n"
}

# ── Verificações pré-instalação ───────────────────────────────
check_prereqs() {
  step "Verificações do sistema"

  [[ $EUID -eq 0 ]] || err "Execute com sudo: sudo bash $0"

  # Distro
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
      warn "Distro detectada: $ID. FliperOS foi testado no Ubuntu 22.04/24.04."
    else
      ok "Ubuntu $VERSION_ID detectado"
    fi
  fi

  # GPU
  GPU_INFO=$(lspci 2>/dev/null | grep -i "vga\|3d\|display" | head -1 || echo "desconhecida")
  info "GPU: $GPU_INFO"
  if echo "$GPU_INFO" | grep -qi "radeon\|r7\|r9\|cape verde\|amd"; then
    ok "GPU AMD detectada — driver radeon recomendado"

  elif echo "$GPU_INFO" | grep -qi "nvidia"; then
    warn "GPU NVIDIA detectada — suporte a modelines CRT via VGA é limitado"

  else
    warn "GPU não identificada como AMD/Radeon — verificar compatibilidade manual"

  fi

  info "Conectores DRM (a presenca nao confirma a frequencia):"
  for status in /sys/class/drm/card*-*/status; do
    [[ -f "$status" ]] || continue
    info "${status%/status}: $(cat "$status")"
  done

  # RAM mínima
  RAM_MB=$(awk '/MemTotal/ {printf "%d", $2/1024}' /proc/meminfo)
  if [[ $RAM_MB -lt 2048 ]]; then
    warn "RAM: ${RAM_MB}MB — recomendado mínimo 4GB para emuladores 3D"
  else
    ok "RAM: ${RAM_MB}MB"
  fi

  # Usuário alvo
  if id "$FLIPEROS_USER" &>/dev/null; then
    ok "Usuário '$FLIPEROS_USER' encontrado"
  else
    warn "Usuário '$FLIPEROS_USER' não existe — será criado na fase 1"
  fi
}

# ════════════════════════════════════════════════════════════
#  FASE 1 — Base do sistema
# ════════════════════════════════════════════════════════════
fase1_base() {
  step "FASE 1 — Base Ubuntu mínima"

  info "Atualizando repositórios..."
  run "apt-get update -qq"
  run "apt-get upgrade -y -qq"

  info "Instalando pacotes essenciais..."
  run "apt-get install -y --no-install-recommends \
    xserver-xorg-core \
    xinit \
    x11-xserver-utils \
    libdrm-dev \
    libdrm2 pciutils libdrm-tests edid-decode pkg-config \
    libgbm-dev \
    libgbm1 \
    mesa-vulkan-drivers \
    mesa-utils \
    libsdl2-2.0-0 \
    libsdl2-dev \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    python3 \
    libfontconfig1-dev \
    libxrandr-dev \
    libxi-dev \
    libxext-dev \
    joystick \
    dialog \
    whiptail \
    alsa-utils"

  info "Removendo snaps desnecessários..."
  run "systemctl disable --now snapd.service snapd.socket 2>/dev/null || true"
  run "apt-get remove -y --purge snapd 2>/dev/null || true"
  run "apt-get autoremove -y -qq"

  # Criar usuário fliperos se não existir
  if ! id "$FLIPEROS_USER" &>/dev/null; then
    info "Criando usuário '$FLIPEROS_USER'..."
    run "useradd -m -s /bin/bash -G video,audio,input,dialout '$FLIPEROS_USER'"
    ok "Usuário '$FLIPEROS_USER' criado"
  else
    info "Adicionando '$FLIPEROS_USER' aos grupos necessários..."
    run "usermod -aG video,audio,input,dialout '$FLIPEROS_USER'"
  fi

  # Diretório de instalação
  run "mkdir -p '$INSTALL_DIR'/{bin,config,roms,bios,scripts,logs}"
  run "chown -R '$FLIPEROS_USER':'$FLIPEROS_USER' '$INSTALL_DIR'"

  ok "Fase 1 concluída"
}

# ════════════════════════════════════════════════════════════
#  FASE 2 — Driver radeon + parâmetros de boot
# ════════════════════════════════════════════════════════════
fase2_driver() {
  step "FASE 2 — EDID no initramfs + GRUB"
  # Refuse conflicting legacy options instead of silently overriding user boot settings.
  if grep -Eq 'nomodeset|video=|drm.edid_firmware=|modprobe.blacklist=amdgpu' /etc/default/grub; then
    err "Remova parametros de video antigos de /etc/default/grub antes da fase 2"
  fi
  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh"
  mkdir -p /etc/default/grub.d
  cat > /etc/default/grub.d/99-fliperos.cfg <<'GRUB'
GRUB_CMDLINE_LINUX_DEFAULT="${GRUB_CMDLINE_LINUX_DEFAULT} video=VGA-1:e drm.edid_firmware=VGA-1:edid/crt15.bin radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0"
GRUB_TERMINAL_OUTPUT=console
GRUB_DISABLE_OS_PROBER=true
GRUB
  run "update-initramfs -u -k all"
  run "update-grub"
  ok "EDID configurado; confirmar modo ativo apos reiniciar"
}

fase3_switchres() {
  step "FASE 3 — SwitchRes2"

  SWITCHRES_DIR="/tmp/switchres-build"
  info "Clonando SwitchRes2..."
  run "rm -rf '$SWITCHRES_DIR'"
  run "git clone --depth=1 https://github.com/antonioginer/switchres '$SWITCHRES_DIR'"

  info "Compilando SwitchRes2 com suporte KMS e XRandR..."
  # Projeto usa makefile proprio (sem CMakeLists.txt) — build via make direto.
  run "make -C '$SWITCHRES_DIR' -j$(nproc) all"
  run "make -C '$SWITCHRES_DIR' install PREFIX=/usr/local"
  run "install -m755 '$SWITCHRES_DIR/switchres' /usr/local/bin/switchres"
  run "ldconfig"

  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh"
  run "systemctl daemon-reload"
  # Teste rápido")")/fliperos-install-video.sh"
  run "systemctl daemon-reload"
  # Teste rápido (sem -s para não alterar display atual)
  info "Testando geração de modeline 320x240@60..."
  if switchres 320 240 60 --monitor arcade_15 --calc 2>/dev/null | grep -q "Modeline"; then
    ok "SwitchRes2 gera modelines corretamente"
  else
    warn "Não foi possível testar SwitchRes2 agora — verificar após reiniciar com driver radeon"
  fi

  ok "Fase 3 concluída"
}

# ════════════════════════════════════════════════════════════
#  FASE 4 — GroovyMAME
# ════════════════════════════════════════════════════════════
fase4_groovymame() {
  step "FASE 4 — GroovyMAME"

  info "Instalando dependências de build do MAME..."
  run "apt-get install -y --no-install-recommends \
    libsdl2-dev \
    libsdl2-ttf-dev \
    libsdl2-image-dev \
    libxinerama-dev \
    libxi-dev \
    libxext-dev \
    libfontconfig-dev \
    libpulse-dev \
    libflac-dev \
    libjpeg-dev \
    libpng-dev \
    libasound2-dev \
    python3-dev"

  GMAME_DIR="/tmp/groovymame-build"
  info "Clonando GroovyMAME (pode demorar — repo grande)..."
  if [[ -d "$GMAME_DIR/.git" ]]; then
    run "git -C '$GMAME_DIR' pull --ff-only"
  else
    run "rm -rf '$GMAME_DIR'"
    run "git clone --depth=1 https://github.com/antonioginer/GroovyMAME '$GMAME_DIR'"
  fi

  info "Compilando GroovyMAME com SwitchRes integrado..."
  info "(isso leva 20-40 min dependendo do hardware)"
  run "make -C '$GMAME_DIR' -j$(nproc) \
    NOWERROR=1 \
    NO_USE_PORTAUDIO=1 \
    SWITCHRES=1 \
    SDL_INI_PATH=/etc/fliperos/mame \
    TARGET=mame \
    SUBTARGET=arcade"

  run "install -m755 '$GMAME_DIR/mamearcade' /usr/local/bin/groovymame"
  ok "GroovyMAME instalado em /usr/local/bin/groovymame"

  install -Dm644 "$(dirname "$(realpath "$0")")/config/mame.ini" /etc/fliperos/mame/mame.ini
  mkdir -p /etc/fliperos/mame


  run "chown -R '$FLIPEROS_USER':'$FLIPEROS_USER' /etc/fliperos/mame"
  ok "mame.ini configurado em /etc/fliperos/mame/"
  ok "Fase 4 concluída"
}

# ════════════════════════════════════════════════════════════
#  FASE 5 — Autologin + Launcher bash
# ════════════════════════════════════════════════════════════
fase5_launcher() {
  step "FASE 5 — Autologin TTY1 + Launcher"

  # Autologin TTY1
  info "Configurando autologin para '$FLIPEROS_USER' no TTY1..."
  mkdir -p /etc/systemd/system/getty@tty1.service.d
  cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << UNIT
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin ${FLIPEROS_USER} --noclear %I \$TERM
UNIT
  run "systemctl daemon-reload"
  ok "Autologin TTY1 configurado"

  # .bash_profile → launcher ao entrar no TTY1
  PROFILE_FILE="/home/$FLIPEROS_USER/.bash_profile"
  cat > "$PROFILE_FILE" << 'PROFILE'
# FliperOS — iniciar launcher automaticamente no TTY1
if [[ -z "$DISPLAY" && "$(tty)" == "/dev/tty1" ]]; then
  exec /opt/fliperos/bin/fliperos-launcher
fi
PROFILE
  run "chown '$FLIPEROS_USER':'$FLIPEROS_USER' '$PROFILE_FILE'"
  ok ".bash_profile configurado"

  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh"
  ok "Fase 5 concluída"
}

# ════════════════════════════════════════════════════════════
#  RESUMO FINAL
# ════════════════════════════════════════════════════════════
resumo_final() {
  echo -e "\n${GRN}${BLD}══════════════════════════════════════════════${RST}"
  echo -e "${GRN}${BLD}  FliperOS Setup Concluído!${RST}"
  echo -e "${GRN}${BLD}══════════════════════════════════════════════${RST}\n"

  echo -e "${BLD}Próximos passos:${RST}"
  echo -e "  ${GRN}1${RST} Reiniciar o sistema para aplicar driver radeon + parâmetros de boot"
  echo -e "  ${GRN}2${RST} Verificar sinal CRT: ${CYN}sudo fliperos-video-check --connector VGA-1${RST}"
  echo -e "  ${GRN}3${RST} Colocar ROMs em: ${CYN}/opt/fliperos/roms/{mame,ps2,dreamcast,model3}/${RST}"
  echo -e "  ${GRN}4${RST} O launcher inicia automaticamente após login no TTY1\n"

  echo -e "${DIM}Log completo: $LOG_FILE${RST}"
  echo -e "${DIM}Configurações: /etc/fliperos/${RST}"
  echo -e "${DIM}Binários: /opt/fliperos/bin/${RST}\n"
}

# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
if $DRY_RUN; then
  case "$FASE_ALVO" in ""|all|[1-5]) ;; *) echo "Fase invalida"; exit 2 ;; esac
  echo "SIMULACAO: nenhuma alteracao sera executada."
  echo "Fases: 1 dependencias; 2 EDID/GRUB; 3 Switchres; 4 GroovyMAME; 5 launcher."
  echo "Selecao: ${FASE_ALVO:-all}; usuario: $FLIPEROS_USER"
  exit 0
fi
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

banner
check_prereqs

# Executar fase específica ou todas
case "$FASE_ALVO" in
  ""|"all")
    fase1_base
    fase2_driver
    fase3_switchres
    fase4_groovymame
    fase5_launcher
    resumo_final
    ;;
  1) fase1_base      ;;
  2) fase2_driver    ;;
  3) fase3_switchres ;;
  4) fase4_groovymame;;
  5) fase5_launcher  ;;
  *) err "Fase inválida: $FASE_ALVO (válido: 1-5 ou all)" ;;
esac
