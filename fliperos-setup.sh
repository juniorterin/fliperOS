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
MONITOR_PROFILE="15khz"

# ── Args ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --fase) [[ $# -ge 2 ]] || { echo "--fase requer valor"; exit 2; }; FASE_ALVO="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=true;   shift   ;;
    --user) [[ $# -ge 2 ]] || { echo "--user requer valor"; exit 2; }; FLIPEROS_USER="$2"; shift 2 ;;
    --monitor-profile)
      [[ $# -ge 2 ]] || { echo "--monitor-profile requer valor"; exit 2; }
      case "$2" in
        15khz|25khz|31khz) MONITOR_PROFILE="$2" ;;
        *) echo "--monitor-profile invalido: $2 (15khz, 25khz ou 31khz)"; exit 2 ;;
      esac
      shift 2 ;;
    *) echo "Uso: sudo bash fliperos-setup.sh [--fase 1-6] [--dry-run] [--user <nome>] [--monitor-profile 15khz|25khz|31khz]"; exit 1 ;;
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
    espeak-ng \
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
  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh" / "$MONITOR_PROFILE"
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

  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh" / "$MONITOR_PROFILE"
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
  # SUBTARGET=arcade nao existe mais (MAME unificou os subtargets ha um
  # tempo); o binario resultante agora se chama so "mame".
  run "make -C '$GMAME_DIR' -j$(nproc) \
    NOWERROR=1 \
    NO_USE_PORTAUDIO=1 \
    USE_QTDEBUG=0 \
    SWITCHRES=1 \
    SDL_INI_PATH=/etc/fliperos/mame \
    TARGET=mame"

  run "install -m755 '$GMAME_DIR/mame' /usr/local/bin/groovymame"
  ok "GroovyMAME instalado em /usr/local/bin/groovymame"

  install -Dm644 "$(dirname "$(realpath "$0")")/config/mame.ini" /etc/fliperos/mame/mame.ini
  mkdir -p /etc/fliperos/mame


  run "chown -R '$FLIPEROS_USER':'$FLIPEROS_USER' /etc/fliperos/mame"
  ok "mame.ini configurado em /etc/fliperos/mame/"
  ok "Fase 4 concluída"
}

# ════════════════════════════════════════════════════════════
#  FASE 6 — RetroArch (KMS/DRM), Flycast (KMS), PCSX2, Supermodel
# ════════════════════════════════════════════════════════════
fase6_emuladores() {
  step "FASE 6 — RetroArch/Flycast (KMS) + PCSX2/Supermodel (X11)"

  info "Instalando dependencias de build (RetroArch KMS + Flycast + PCSX2 + Supermodel)..."
  run "apt-get install -y --no-install-recommends \
    libegl1-mesa-dev libgles2-mesa-dev libudev-dev \
    libcurl4-openssl-dev libminiupnpc-dev libzip-dev libao-dev libpng-dev \
    qt6-base-dev qt6-tools-dev qt6-tools-dev-tools qt6-multimedia-dev \
    libqt6svg6-dev libgtk-3-dev libaio-dev liblzma-dev libpcap0.8-dev \
    libglew-dev zlib1g-dev"

  # RetroArch em KMS/DRM puro — flags validadas manualmente antes de
  # entrar aqui (ver comentario em build_retroarch_chroot() no
  # fliperos-mkiso.sh): sem X11/Wayland/SDL, so o driver KMS compilado.
  RA_DIR="/tmp/retroarch-build"
  info "Clonando e compilando RetroArch (KMS/DRM)..."
  run "rm -rf '$RA_DIR'"
  run "git clone --depth=1 https://github.com/libretro/RetroArch '$RA_DIR'"
  run "cd '$RA_DIR' && ./configure --enable-kms --enable-egl --disable-x11 --disable-wayland --disable-sdl --disable-sdl2"
  run "make -C '$RA_DIR' -j$(nproc)"
  run "make -C '$RA_DIR' install"

  mkdir -p /etc/fliperos/retroarch/autoconfig /etc/fliperos/retroarch/cores
  RA_AUTOCONFIG_DIR="/tmp/ra-autoconfig"
  run "rm -rf '$RA_AUTOCONFIG_DIR'"
  run "git clone --depth=1 https://github.com/libretro/retroarch-joypad-autoconfig '$RA_AUTOCONFIG_DIR'"
  run "cp -a '$RA_AUTOCONFIG_DIR/udev' /etc/fliperos/retroarch/autoconfig/"

  info "Compilando cores libretro (NES/SNES/Mega Drive/GBA/PS1/mame2010)..."
  for repo in libretro/libretro-fceumm libretro/snes9x libretro/Genesis-Plus-GX \
              libretro/mgba libretro/pcsx_rearmed libretro/mame2010-libretro; do
    core_dir="/tmp/core-$(basename "$repo")"
    run "rm -rf '$core_dir'"
    run "git clone --depth=1 --recursive https://github.com/$repo '$core_dir'"
    if [[ -f "$core_dir/libretro/Makefile" ]]; then
      run "make -C '$core_dir/libretro' -f Makefile -j$(nproc)"
      run "find '$core_dir/libretro' -maxdepth 2 -name '*_libretro.so' -exec cp {} /etc/fliperos/retroarch/cores/ \\;"
    elif [[ -f "$core_dir/Makefile.libretro" ]]; then
      run "make -C '$core_dir' -f Makefile.libretro -j$(nproc)"
      run "find '$core_dir' -maxdepth 2 -name '*_libretro.so' -exec cp {} /etc/fliperos/retroarch/cores/ \\;"
    else
      run "make -C '$core_dir' -f Makefile -j$(nproc)"
      run "find '$core_dir' -maxdepth 2 -name '*_libretro.so' -exec cp {} /etc/fliperos/retroarch/cores/ \\;"
    fi
  done
  install -Dm644 "$(dirname "$(realpath "$0")")/config/retroarch.cfg" /etc/fliperos/retroarch/retroarch.cfg
  ok "RetroArch instalado (KMS/DRM) com cores e autoconfig de joypad"

  # Flycast — standalone, KMS via SDL_VIDEODRIVER=kmsdrm em runtime (sem
  # flag de build especifica, ver fliperos-kms-run).
  FC_DIR="/tmp/flycast-build"
  info "Clonando e compilando Flycast (Dreamcast)..."
  run "rm -rf '$FC_DIR'"
  run "git clone --depth=1 https://github.com/flyinghead/flycast '$FC_DIR'"
  run "cd '$FC_DIR' && git submodule update --init --recursive"
  run "cmake -B '$FC_DIR/build' -S '$FC_DIR' -DCMAKE_BUILD_TYPE=Release -DUSE_VULKAN=OFF"
  run "cmake --build '$FC_DIR/build' -j$(nproc)"
  run "install -m755 '$FC_DIR/build/flycast' /usr/local/bin/flycast"
  ok "Flycast instalado (KMS)"

  # PCSX2 — Qt-only, sem caminho KMS suportado; fica em X11.
  PS_DIR="/tmp/pcsx2-build"
  info "Clonando e compilando PCSX2 (PS2, X11 — build mais longo do grupo)..."
  run "rm -rf '$PS_DIR'"
  run "git clone --depth=1 --recursive https://github.com/PCSX2/pcsx2 '$PS_DIR'"
  run "cmake -B '$PS_DIR/build' -S '$PS_DIR' -DCMAKE_BUILD_TYPE=Release"
  run "cmake --build '$PS_DIR/build' -j$(nproc)"
  run "find '$PS_DIR/build' -maxdepth 3 -iname 'pcsx2*' -type f -executable -exec install -m755 {} /usr/local/bin/pcsx2 \\; -quit"
  ok "PCSX2 instalado (X11)"

  # Supermodel — SDL2+OpenGL, sem caminho KMS documentado; fica em X11.
  SM_DIR="/tmp/supermodel-build"
  info "Clonando e compilando Supermodel (Model 3, X11)..."
  run "rm -rf '$SM_DIR'"
  run "git clone --depth=1 https://github.com/trzy/Supermodel '$SM_DIR'"
  run "cmake -B '$SM_DIR/build' -S '$SM_DIR' -DCMAKE_BUILD_TYPE=Release -DNET_BOARD=OFF"
  run "cmake --build '$SM_DIR/build' -j$(nproc)"
  run "find '$SM_DIR/build' -maxdepth 2 -iname 'supermodel' -type f -executable -exec install -m755 {} /usr/local/bin/supermodel \\; -quit"
  ok "Supermodel instalado (X11)"

  ok "Fase 6 concluída"
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

  bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh" / "$MONITOR_PROFILE"
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
  case "$FASE_ALVO" in ""|all|[1-6]) ;; *) echo "Fase invalida"; exit 2 ;; esac
  echo "SIMULACAO: nenhuma alteracao sera executada."
  echo "Fases: 1 dependencias; 2 EDID/GRUB; 3 Switchres; 4 GroovyMAME; 5 launcher; 6 RetroArch/Flycast/PCSX2/Supermodel."
  echo "Selecao: ${FASE_ALVO:-all}; usuario: $FLIPEROS_USER; monitor: $MONITOR_PROFILE"
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
    fase6_emuladores
    resumo_final
    ;;
  1) fase1_base      ;;
  2) fase2_driver    ;;
  3) fase3_switchres ;;
  4) fase4_groovymame;;
  5) fase5_launcher  ;;
  6) fase6_emuladores;;
  *) err "Fase inválida: $FASE_ALVO (válido: 1-6 ou all)" ;;
esac
