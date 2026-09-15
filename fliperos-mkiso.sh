#!/usr/bin/env bash
# ============================================================
#  FliperOS mkiso v0.6
#  Gera uma ISO Ubuntu customizada com FliperOS pré-instalado
#  Base: Ubuntu 24.04 LTS minimal (noble)
#  Uso: sudo bash fliperos-mkiso.sh [/caminho/saida.iso] [--skip-switchres]
#       [--skip-groovymame] [--skip-retroarch] [--skip-flycast]
#       [--skip-pcsx2] [--skip-supermodel] [--with-15khz-kernel]
#       [--monitor-profile 15khz|25khz|31khz]
#  No Windows, execute somente dentro do container Docker.
# ============================================================

set -euo pipefail
if grep -qi microsoft /proc/sys/kernel/osrelease && [[ ! -f /.dockerenv ]]; then
  echo "Build direto no WSL recusado. Use Dockerfile.fliperos (CLAUDE.md)." >&2; exit 1
fi

GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'
BLU='\033[0;34m'; CYN='\033[0;36m'; DIM='\033[2m'
BLD='\033[1m'; RST='\033[0m'

FLIPEROS_VERSION="0.6"
UBUNTU_CODENAME="noble"
UBUNTU_MIRROR="http://archive.ubuntu.com/ubuntu"
WORK_DIR=$(mktemp -d /tmp/fliperos-iso-build.XXXXXX)
CHROOT_DIR="$WORK_DIR/chroot"
ISO_DIR="$WORK_DIR/iso"
OUTPUT_ISO="/tmp/fliperos-${FLIPEROS_VERSION}.iso"
ARCH="amd64"
LOG_FILE="/var/log/fliperos-mkiso.log"
SKIP_SWITCHRES=false
SKIP_GROOVYMAME=false
SKIP_RETROARCH=false
SKIP_FLYCAST=false
SKIP_PCSX2=false
SKIP_SUPERMODEL=false
WITH_15KHZ_KERNEL=false
KERNEL_15KHZ_VERSION="6.12.104"
MONITOR_PROFILE="15khz"

# ── Args ─────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case $1 in
    --output)
      [[ $# -ge 2 && -n "${2:-}" ]] || { echo "Erro: --output requer caminho."; exit 1; }
      OUTPUT_ISO="$2"; shift 2 ;;
    --skip-switchres)  SKIP_SWITCHRES=true; shift ;;
    --skip-groovymame) SKIP_GROOVYMAME=true; shift ;;
    --skip-retroarch)  SKIP_RETROARCH=true; shift ;;
    --skip-flycast)    SKIP_FLYCAST=true; shift ;;
    --skip-pcsx2)      SKIP_PCSX2=true; shift ;;
    --skip-supermodel) SKIP_SUPERMODEL=true; shift ;;
    --with-15khz-kernel) WITH_15KHZ_KERNEL=true; shift ;;
    --monitor-profile)
      [[ $# -ge 2 ]] || { echo "Erro: --monitor-profile requer valor."; exit 1; }
      case "$2" in
        15khz|25khz|31khz) MONITOR_PROFILE="$2" ;;
        *) echo "Erro: --monitor-profile invalido: $2 (15khz, 25khz ou 31khz)"; exit 1 ;;
      esac
      shift 2 ;;
    /*.iso|*.iso)     OUTPUT_ISO="$1"; shift ;;
    *) echo "Uso: sudo bash fliperos-mkiso.sh [/saida.iso] [--skip-switchres] [--skip-groovymame] [--skip-retroarch] [--skip-flycast] [--skip-pcsx2] [--skip-supermodel] [--with-15khz-kernel] [--monitor-profile 15khz|25khz|31khz]"; exit 1 ;;
  esac
done

[[ $EUID -eq 0 ]] || { echo "Execute com sudo."; exit 1; }

log()  { echo -e "${DIM}[$(date +%H:%M:%S)]${RST} $*" | tee -a "$LOG_FILE"; }
ok()   { echo -e "${GRN}✓${RST} $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YLW}⚠${RST} $*" | tee -a "$LOG_FILE"; }
err()  { echo -e "${RED}✗${RST} $*" | tee -a "$LOG_FILE"; exit 1; }
info() { echo -e "${BLU}→${RST} $*" | tee -a "$LOG_FILE"; }
step() { echo -e "\n${BLD}${CYN}══ $* ══${RST}" | tee -a "$LOG_FILE"; }

# ── Dependências do host ──────────────────────────────────────
check_host_deps() {
  step "Verificando dependências do host"
  local DEPS=(debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools dosfstools)
  local MISSING=()
  for D in "${DEPS[@]}"; do
    dpkg -s "$D" &>/dev/null && ok "$D" || MISSING+=("$D")
  done
  if [[ ${#MISSING[@]} -gt 0 ]]; then
    info "Instalando: ${MISSING[*]}"
    apt-get install -y "${MISSING[@]}" >> "$LOG_FILE" 2>&1
    ok "Dependências instaladas"
  fi
}

# ── Montar pseudo-filesystems (seguro para WSL2) ──────────────
mount_chroot() {
  # Cria /dev virtual mínimo sem expor o /dev real do host
  mount -t tmpfs tmpfs "$CHROOT_DIR/dev"

  # Dispositivos essenciais para apt/debootstrap dentro do chroot
  mknod -m 666 "$CHROOT_DIR/dev/null"    c 1 3
  mknod -m 666 "$CHROOT_DIR/dev/zero"    c 1 5
  mknod -m 666 "$CHROOT_DIR/dev/random"  c 1 8
  mknod -m 666 "$CHROOT_DIR/dev/urandom" c 1 9
  mknod -m 666 "$CHROOT_DIR/dev/tty"     c 5 0
  ln -s pts/ptmx "$CHROOT_DIR/dev/ptmx"
  mkdir -p "$CHROOT_DIR/dev/pts" "$CHROOT_DIR/dev/shm"
  mount -t devpts devpts "$CHROOT_DIR/dev/pts" -o newinstance,gid=5,mode=620,ptmxmode=666
  mount -t tmpfs  tmpfs  "$CHROOT_DIR/dev/shm"

  mount -t proc  proc   "$CHROOT_DIR/proc"
  mount -t sysfs sysfs  "$CHROOT_DIR/sys"
  mount -t tmpfs tmpfs  "$CHROOT_DIR/tmp"
  ok "Pseudo-filesystems montados (WSL2-safe)"
}

# ── Desmontar chroot ──────────────────────────────────────────
unmount_chroot() {
  info "Desmontando pseudo-filesystems..."
  for MP in dev/pts dev/shm proc sys tmp dev; do
    if mountpoint -q "$CHROOT_DIR/$MP"; then umount "$CHROOT_DIR/$MP" || return 1; fi
  done
  # dev montado com tmpfs — precisa desmontar por último

  ok "Desmontado"
}

# ── Debootstrap ───────────────────────────────────────────────
build_rootfs() {
  step "Debootstrap — Ubuntu $UBUNTU_CODENAME"
  [[ "$CHROOT_DIR" == /tmp/fliperos-iso-build.*/chroot ]] || err "Rootfs fora do workspace"
  mkdir -p "$CHROOT_DIR"
  info "Download do sistema base (~300MB)..."
  debootstrap \
    --arch="$ARCH" \
    --variant=minbase \
    --components="main,restricted,universe" \
    "$UBUNTU_CODENAME" "$CHROOT_DIR" "$UBUNTU_MIRROR" >> "$LOG_FILE" 2>&1
  ok "Debootstrap concluído"
  mount_chroot
}

# ── Configurar chroot ─────────────────────────────────────────
# Heredoc com 'CHROOT_SCRIPT' (aspas) = sem expansão pelo bash do host.
# As variáveis do host são injetadas via sed depois de escrito o arquivo.
configure_chroot() {
  step "Configurando sistema dentro do chroot"
  cp /etc/resolv.conf "$CHROOT_DIR/etc/resolv.conf"
  printf '#!/bin/sh\nexit 101\n' > "$CHROOT_DIR/usr/sbin/policy-rc.d"
  chmod +x "$CHROOT_DIR/usr/sbin/policy-rc.d"

  # EDID customizado (metodo D0023R/linux_kernel_15khz — "no kernel patch
  # required"): declara pro kernel o modo fixo do perfil de monitor
  # escolhido (--monitor-profile), sem depender da negociacao DDC/EDID
  # real com um CRT fixed-frequency. O nome instalado (crt15.bin) fica
  # fixo pros tres perfis de proposito — so o CONTEUDO muda (ver README).
  local SCRIPT_SRC EDID_SRC
  SCRIPT_SRC="$(dirname "$(realpath "$0")")"
  case "$MONITOR_PROFILE" in
    15khz) EDID_SRC="crt15-edid.bin" ;;
    25khz) EDID_SRC="crt25-edid.bin" ;;
    31khz) EDID_SRC="crt31-edid.bin" ;;
  esac
  if [[ -f "$SCRIPT_SRC/$EDID_SRC" ]]; then
    mkdir -p "$CHROOT_DIR/lib/firmware/edid"
    cp "$SCRIPT_SRC/$EDID_SRC" "$CHROOT_DIR/lib/firmware/edid/crt15.bin"
    ok "EDID customizado copiado ($MONITOR_PROFILE): /lib/firmware/edid/crt15.bin"
  else
    err "EDID obrigatorio ausente"
  fi

  # Kernel generico (apt) por padrao; com --with-15khz-kernel o kernel
  # patcheado e compilado em build_15khz_kernel_chroot() mais adiante, entao
  # nao instala linux-image-generic aqui (copy_kernel() pegaria o kernel
  # errado se os dois coexistissem).
  local KERNEL_APT_PKGS="linux-image-generic linux-headers-generic"
  $WITH_15KHZ_KERNEL && KERNEL_APT_PKGS=""

  cat > "$CHROOT_DIR/tmp/fliperos-chroot-setup.sh" << 'CHROOT_SCRIPT'
#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8

cat > /etc/apt/sources.list << SOURCES
deb __MIRROR__ __CODENAME__ main restricted universe multiverse
deb __MIRROR__ __CODENAME__-updates main restricted universe multiverse
deb __MIRROR__ __CODENAME__-security main restricted universe multiverse
SOURCES

apt-get update -qq

# live-boot necessário para boot=live no kernel da ISO
apt-get install -y --no-install-recommends \
  __KERNEL_PKGS__ \
  live-boot live-boot-initramfs-tools \
  grub-pc-bin grub-efi-amd64-bin grub2-common \
  locales tzdata systemd systemd-sysv udev sudo bash \
  coreutils util-linux e2fsprogs dosfstools parted \
  wget curl git ca-certificates \
  xserver-xorg-core xinit x11-xserver-utils \
  libdrm2 libgbm1 mesa-vulkan-drivers mesa-utils \
  libsdl2-2.0-0 libsdl2-dev build-essential cmake \
  libdrm-dev libgbm-dev libxrandr-dev libxi-dev libxext-dev libfontconfig1-dev \
  joystick dialog whiptail alsa-utils linux-firmware \
  xserver-xorg-video-radeon xserver-xorg-video-amdgpu \
  openssh-server network-manager wpasupplicant iw python3 pciutils libdrm-tests edid-decode squashfs-tools \
  espeak-ng

systemctl enable ssh
mkdir -p /etc/systemd/system/ssh.service.d
printf '[Service]\nExecStartPre=/usr/bin/ssh-keygen -A\n' > /etc/systemd/system/ssh.service.d/keys.conf
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
systemctl enable NetworkManager

locale-gen pt_BR.UTF-8
update-locale LANG=pt_BR.UTF-8
ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
dpkg-reconfigure -f noninteractive tzdata

useradd -m -s /bin/bash -G video,audio,input,dialout,sudo fliperos
echo "fliperos:fliperos" | chpasswd
cat > /etc/sudoers.d/fliperos << SUDOERS
fliperos ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /usr/sbin/reboot, /usr/sbin/poweroff
SUDOERS
chmod 440 /etc/sudoers.d/fliperos

echo "fliperos" > /etc/hostname
cat > /etc/hosts << HOSTS
127.0.0.1 localhost
127.0.1.1 fliperos
HOSTS


# Garante que o EDID customizado entre no initramfs — o KMS early-boot
# do driver radeon roda antes do rootfs real, entao o arquivo tem que
# estar dentro do initramfs, nao so no rootfs (ver README do
# D0023R/linux_kernel_15khz, secao "Custom EDID method").
if [[ -f /lib/firmware/edid/crt15.bin ]]; then
  cat > /etc/initramfs-tools/hooks/fliperos-edid << 'HOOK'
#!/bin/sh
PREREQ=""
prereqs() { echo "$PREREQ"; }
case "$1" in prereqs) prereqs; exit 0 ;; esac
. /usr/share/initramfs-tools/hook-functions
mkdir -p "$DESTDIR/lib/firmware/edid"
cp /lib/firmware/edid/crt15.bin "$DESTDIR/lib/firmware/edid/crt15.bin"
HOOK
  chmod +x /etc/initramfs-tools/hooks/fliperos-edid
fi

update-initramfs -u -k all

mkdir -p /opt/fliperos/{bin,config,roms/{mame,ps2,dreamcast,model3},bios,logs}
mkdir -p /etc/fliperos/mame
chown -R fliperos:fliperos /opt/fliperos

chown -R fliperos:fliperos /etc/fliperos/mame

mkdir -p /etc/systemd/system/getty@tty1.service.d
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << UNIT
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin fliperos --noclear %I \$TERM
UNIT





cat > /usr/local/bin/fliperos-postinstall << 'POST'
#!/bin/bash
set -e
SDIR="/opt/fliperos"
[[ -f "$SDIR/fliperos-setup.sh" ]] || { echo "fliperos-setup.sh nao encontrado"; exit 1; }
bash "$SDIR/fliperos-setup.sh" --fase 3
bash "$SDIR/fliperos-setup.sh" --fase 4
bash "$SDIR/fliperos-setup.sh" --fase 6
POST
chmod +x /usr/local/bin/fliperos-postinstall

apt-get remove -y --purge snapd apport whoopsie 2>/dev/null || true
apt-get autoremove -y -qq
apt-get clean
rm -rf /var/lib/apt/lists/*

echo "CHROOT_SETUP_DONE"
CHROOT_SCRIPT

  # Injetar mirror e codename
  sed -i \
    -e "s|__MIRROR__|${UBUNTU_MIRROR}|g" \
    -e "s|__CODENAME__|${UBUNTU_CODENAME}|g" \
    -e "s|__KERNEL_PKGS__|${KERNEL_APT_PKGS}|g" \
    "$CHROOT_DIR/tmp/fliperos-chroot-setup.sh"

  chmod +x "$CHROOT_DIR/tmp/fliperos-chroot-setup.sh"
  chroot "$CHROOT_DIR" /tmp/fliperos-chroot-setup.sh 2>&1 | tee -a "$LOG_FILE" | grep -v "^$"
  ok "Chroot configurado"
}

# ── Copiar scripts FliperOS ───────────────────────────────────
copy_fliperos_scripts() {
  step "Copiando scripts FliperOS"
  local SCRIPT_SRC
  SCRIPT_SRC="$(dirname "$(realpath "$0")")"
  for S in fliperos-setup.sh fliperos-detect.sh fliperos-mkiso.sh fliperos-install-video.sh fliperos-video-check.py fliperos-install.py crt15-edid.bin crt25-edid.bin crt31-edid.bin; do
    if [[ -f "$SCRIPT_SRC/$S" ]]; then
      cp "$SCRIPT_SRC/$S" "$CHROOT_DIR/opt/fliperos/"
      chmod +x "$CHROOT_DIR/opt/fliperos/$S"
      ok "Copiado: $S"
    else
      warn "Nao encontrado: $S"
    fi
  done
}

# ── Compilar SwitchRes2 no chroot ─────────────────────────────
build_switchres_chroot() {
  if $SKIP_SWITCHRES; then
    warn "SwitchRes2 pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando SwitchRes2 no chroot"
  cat > "$CHROOT_DIR/tmp/build-switchres.sh" << 'SRSCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends \
  libdrm-dev libgbm-dev libxrandr-dev libxi-dev libxext-dev pkg-config git build-essential
git clone --depth=1 https://github.com/antonioginer/switchres /tmp/srs
# Projeto usa makefile proprio (sem CMakeLists.txt) — build via make direto.
make -C /tmp/srs -j$(nproc) all
make -C /tmp/srs install PREFIX=/usr/local
install -m755 /tmp/srs/switchres /usr/local/bin/switchres
ldconfig
rm -rf /tmp/srs
echo "SwitchRes2 OK"
SRSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-switchres.sh"
  chroot "$CHROOT_DIR" /tmp/build-switchres.sh >> "$LOG_FILE" 2>&1 \
    && ok "SwitchRes2 compilado" \
    || err "SwitchRes2 falhou; ISO nao sera publicada como completa"
}

# ── Compilar GroovyMAME no chroot ─────────────────────────────
build_groovymame_chroot() {
  if $SKIP_GROOVYMAME; then
    warn "GroovyMAME pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando GroovyMAME no chroot (SWITCHRES=1)"
  cat > "$CHROOT_DIR/tmp/build-groovymame.sh" << 'GMSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends \
  libsdl2-dev libsdl2-ttf-dev libsdl2-image-dev \
  libxinerama-dev libxi-dev libxext-dev libfontconfig-dev \
  libpulse-dev libflac-dev libjpeg-dev libpng-dev \
  libasound2-dev python3-dev
git clone --depth=1 https://github.com/antonioginer/GroovyMAME /tmp/groovymame-build
# SUBTARGET=arcade nao existe mais (MAME unificou os subtargets ha um
# tempo); o binario resultante agora se chama so "mame".
make -C /tmp/groovymame-build -j$(nproc) \
  NOWERROR=1 \
  NO_USE_PORTAUDIO=1 \
  USE_QTDEBUG=0 \
  SWITCHRES=1 \
  SDL_INI_PATH=/etc/fliperos/mame \
  TARGET=mame
install -m755 /tmp/groovymame-build/mame /usr/local/bin/groovymame
rm -rf /tmp/groovymame-build
echo "GroovyMAME OK"
GMSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-groovymame.sh"
  chroot "$CHROOT_DIR" /tmp/build-groovymame.sh >> "$LOG_FILE" 2>&1 \
    && ok "GroovyMAME compilado" \
    || err "GroovyMAME falhou; use --skip-groovymame explicitamente para ISO de diagnostico"
}

# ── Compilar RetroArch em KMS/DRM, sem X11 ────────────────────
# Flags validadas num container Ubuntu 24.04 descartavel antes de entrar
# aqui: --enable-kms --enable-egl --disable-x11 --disable-wayland
# --disable-sdl --disable-sdl2 builda limpo (config.h confirma
# HAVE_KMS/HAVE_EGL/HAVE_GBM=1, sem HAVE_X11/HAVE_WAYLAND) e o binario
# resultante reporta "KMS: yes", "EGL: yes", "udev: yes" em --features.
# Por isso RetroArch/Flycast usam fliperos-kms-run (sem Xorg), diferente
# de PCSX2/Supermodel que continuam em fliperos-x11-run.
build_retroarch_chroot() {
  if $SKIP_RETROARCH; then
    warn "RetroArch pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando RetroArch (KMS/DRM, sem X11) no chroot"
  cat > "$CHROOT_DIR/tmp/build-retroarch.sh" << 'RASCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends \
  libegl1-mesa-dev libgles2-mesa-dev libudev-dev

git clone --depth=1 https://github.com/libretro/RetroArch /tmp/retroarch
cd /tmp/retroarch
./configure --enable-kms --enable-egl --disable-x11 --disable-wayland \
  --disable-sdl --disable-sdl2
make -j"$(nproc)"
make install
cd /
rm -rf /tmp/retroarch

mkdir -p /etc/fliperos/retroarch/autoconfig /etc/fliperos/retroarch/cores

# Perfis de autoconfig de joypad (deteccao automatica por vendor/product ID).
git clone --depth=1 https://github.com/libretro/retroarch-joypad-autoconfig /tmp/ra-autoconfig
cp -a /tmp/ra-autoconfig/udev /etc/fliperos/retroarch/autoconfig/
rm -rf /tmp/ra-autoconfig

# Cores libretro pre-instalados: NES/SNES/Mega Drive/GBA (essenciais
# 8/16-bit), PS1 e um core de arcade leve (mame2010, complementar ao
# GroovyMAME standalone que continua sendo o caminho principal de arcade).
build_core() {
  local repo="$1" name dir mk
  name="$(basename "$repo")"
  dir="/tmp/core-${name}"
  git clone --depth=1 --recursive "https://github.com/${repo}" "$dir"
  if [[ -f "$dir/libretro/Makefile" ]]; then
    dir="$dir/libretro"; mk="Makefile"
  elif [[ -f "$dir/Makefile.libretro" ]]; then
    mk="Makefile.libretro"
  else
    mk="Makefile"
  fi
  make -C "$dir" -f "$mk" -j"$(nproc)"
  find "$dir" -maxdepth 2 -name '*_libretro.so' -exec cp {} /etc/fliperos/retroarch/cores/ \;
  rm -rf "/tmp/core-${name}"
}
build_core libretro/libretro-fceumm
build_core libretro/snes9x
build_core libretro/Genesis-Plus-GX
build_core libretro/mgba
build_core libretro/pcsx_rearmed
build_core libretro/mame2010-libretro

echo "RetroArch OK"
RASCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-retroarch.sh"
  chroot "$CHROOT_DIR" /tmp/build-retroarch.sh >> "$LOG_FILE" 2>&1 \
    && ok "RetroArch compilado (KMS/DRM) com cores e autoconfig de joypad" \
    || err "RetroArch falhou; use --skip-retroarch explicitamente para ISO sem ele"
}

# ── Compilar Flycast (Dreamcast), KMS via SDL2 kmsdrm ─────────
# Recipe identica a testada no container de validacao: precisa de
# 'git submodule update --init --recursive' (nao vem no clone raso) e das
# deps de build abaixo. Saida em KMS/DRM vem so de rodar com
# SDL_VIDEODRIVER=kmsdrm (ver fliperos-kms-run) — libsdl2 do Ubuntu ja
# vem com esse driver, nao precisa recompilar SDL2. USE_VULKAN=OFF porque
# adiciona deps novas (glslang/SPIRV) sem necessidade pro caminho OpenGL
# via EGL/GBM ja validado.
build_flycast_chroot() {
  if $SKIP_FLYCAST; then
    warn "Flycast pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando Flycast (Dreamcast, KMS 640x240) no chroot"
  cat > "$CHROOT_DIR/tmp/build-flycast.sh" << 'FCSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends \
  libcurl4-openssl-dev libminiupnpc-dev libzip-dev libao-dev libpng-dev
git clone --depth=1 https://github.com/flyinghead/flycast /tmp/flycast
cd /tmp/flycast
git submodule update --init --recursive
cmake -B build -DCMAKE_BUILD_TYPE=Release -DUSE_VULKAN=OFF
cmake --build build -j"$(nproc)"
install -m755 build/flycast /usr/local/bin/flycast
cd /
rm -rf /tmp/flycast
echo "Flycast OK"
FCSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-flycast.sh"
  chroot "$CHROOT_DIR" /tmp/build-flycast.sh >> "$LOG_FILE" 2>&1 \
    && ok "Flycast compilado (KMS)" \
    || err "Flycast falhou; use --skip-flycast explicitamente para ISO sem ele"
}

# ── Compilar PCSX2 (PS2), X11 ──────────────────────────────────
# Qt nao tem backend KMS/DRM suportado oficialmente (so um plugin eglfs
# experimental que o proprio PCSX2 nao testa) — fica em X11 via
# fliperos-x11-run, igual o launcher ja espera. Build mais pesado do
# grupo (Qt6 + C++ grande).
build_pcsx2_chroot() {
  if $SKIP_PCSX2; then
    warn "PCSX2 pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando PCSX2 (PS2, X11) no chroot — build mais longo do grupo"
  cat > "$CHROOT_DIR/tmp/build-pcsx2.sh" << 'PSSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends \
  qt6-base-dev qt6-tools-dev qt6-tools-dev-tools qt6-multimedia-dev \
  libqt6svg6-dev libgtk-3-dev libaio-dev liblzma-dev libpcap0.8-dev \
  libudev-dev
git clone --depth=1 --recursive https://github.com/PCSX2/pcsx2 /tmp/pcsx2
cd /tmp/pcsx2
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
find build -maxdepth 3 -iname 'pcsx2*' -type f -executable \
  -exec install -m755 {} /usr/local/bin/pcsx2 \; -quit
cd /
rm -rf /tmp/pcsx2
echo "PCSX2 OK"
PSSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-pcsx2.sh"
  chroot "$CHROOT_DIR" /tmp/build-pcsx2.sh >> "$LOG_FILE" 2>&1 \
    && ok "PCSX2 compilado" \
    || err "PCSX2 falhou; use --skip-pcsx2 explicitamente para ISO sem ele"
}

# ── Compilar Supermodel (Sega Model 3), X11 ───────────────────
# SDL2+OpenGL, sem caminho KMS/DRM documentado pelo projeto — fica em
# X11 via fliperos-x11-run.
build_supermodel_chroot() {
  if $SKIP_SUPERMODEL; then
    warn "Supermodel pulado — compile apos o boot: sudo fliperos-postinstall"
    return
  fi
  step "Compilando Supermodel (Model 3, X11) no chroot"
  cat > "$CHROOT_DIR/tmp/build-supermodel.sh" << 'SMSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends libglew-dev zlib1g-dev
git clone --depth=1 https://github.com/trzy/Supermodel /tmp/supermodel
cd /tmp/supermodel
cmake -B build -DCMAKE_BUILD_TYPE=Release -DNET_BOARD=OFF
cmake --build build -j"$(nproc)"
find build -maxdepth 2 -iname 'supermodel' -type f -executable \
  -exec install -m755 {} /usr/local/bin/supermodel \; -quit
cd /
rm -rf /tmp/supermodel
echo "Supermodel OK"
SMSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-supermodel.sh"
  chroot "$CHROOT_DIR" /tmp/build-supermodel.sh >> "$LOG_FILE" 2>&1 \
    && ok "Supermodel compilado" \
    || err "Supermodel falhou; use --skip-supermodel explicitamente para ISO sem ele"
}

# ── Compilar kernel 15kHz patcheado (opt-in) ──────────────────
# Kernel vanilla kernel.org + patches D0023R/linux_kernel_15khz
# vendorizados em patches/kernel-15khz/ (ver README la dentro). So roda
# com --with-15khz-kernel; sem a flag, o kernel continua sendo o
# linux-image-generic normal com o metodo EDID-only (ver configure_chroot).
# A semente de .config vem do proprio kernel noble (baixado sem instalar,
# so pra extrair o .config ja ajustado) em vez de defconfig do zero.
build_15khz_kernel_chroot() {
  if ! $WITH_15KHZ_KERNEL; then
    return
  fi
  step "Compilando kernel 15kHz patcheado ($KERNEL_15KHZ_VERSION) no chroot"
  local KERNEL_MINOR="${KERNEL_15KHZ_VERSION%.*}"
  local KERNEL_MAJOR="${KERNEL_15KHZ_VERSION%%.*}"
  cat > "$CHROOT_DIR/tmp/build-15khz-kernel.sh" << 'KERNELSCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends \
  libncurses-dev bison flex libssl-dev libelf-dev bc \
  rsync cpio kmod fakeroot dwarves zstd xz-utils

mkdir -p /usr/src/fliperos-kernel
cd /usr/src/fliperos-kernel

# Semente de .config: baixa so o pacote de buildinfo do kernel noble (sem
# instalar/rodar postinst) e reaproveita o .config ja ajustado pela
# Canonical, em vez de partir de defconfig do zero. O Ubuntu separou o
# linux-buildinfo-<versao> do linux-image-<versao> pra nao inflar o
# pacote de imagem assinado — confirmado testando os dois pacotes reais
# do noble antes de escrever isso: linux-image-*-generic hoje so tem o
# vmlinuz, o .config mora em /usr/lib/linux/<versao>/config dentro do
# linux-buildinfo-*-generic (nao mais em /boot/config-<versao>).
REALPKG=$(apt-cache depends linux-image-generic | awk '/Depends:/{print $2; exit}')
BUILDINFO_PKG="${REALPKG/linux-image-/linux-buildinfo-}"
apt-get download "$BUILDINFO_PKG"
dpkg-deb -x "${BUILDINFO_PKG}"*.deb /usr/src/fliperos-kernel/genericpkg
CONFIG_SEED=$(find /usr/src/fliperos-kernel/genericpkg -type f \( -name 'config' -o -name 'config-*' \) | head -1)
[[ -n "$CONFIG_SEED" ]] || { echo "config-seed nao encontrado" >&2; exit 1; }

wget -q "https://cdn.kernel.org/pub/linux/kernel/v__KERNEL_MAJOR__.x/linux-__KERNEL_VERSION__.tar.xz"
tar xf "linux-__KERNEL_VERSION__.tar.xz"
cp "$CONFIG_SEED" "linux-__KERNEL_VERSION__/.config"
rm -rf /usr/src/fliperos-kernel/genericpkg "${BUILDINFO_PKG}"*.deb
cd "linux-__KERNEL_VERSION__"

for P in /opt/fliperos/kernel-patches/__KERNEL_MINOR__/*.patch; do
  echo "Aplicando $(basename "$P")"
  patch -p1 < "$P"
done

# Kernel proprio nao e assinado (sem Secure Boot) — desliga assinatura de
# modulo/certificados do Ubuntu (referenciam arquivo que nao existe fora
# da arvore deles) e BTF/pahole (irrelevante pro caso de uso, e uma fonte
# comum de falha de build ao reaproveitar um .config do Ubuntu).
./scripts/config --set-str LOCALVERSION "-15khz"
./scripts/config --disable SYSTEM_TRUSTED_KEYS
./scripts/config --disable SYSTEM_REVOCATION_KEYS
./scripts/config --disable MODULE_SIG
./scripts/config --disable DEBUG_INFO_BTF
make olddefconfig
make -j"$(nproc)" bindeb-pkg

cd /usr/src/fliperos-kernel
apt-get install -y ./linux-image-*.deb ./linux-headers-*.deb
rm -rf /usr/src/fliperos-kernel/linux-__KERNEL_VERSION__ \
       /usr/src/fliperos-kernel/*.tar.xz /usr/src/fliperos-kernel/*.deb \
       /usr/src/fliperos-kernel/*.buildinfo /usr/src/fliperos-kernel/*.changes
echo "KERNEL_15KHZ_OK"
KERNELSCRIPT
  sed -i \
    -e "s|__KERNEL_VERSION__|${KERNEL_15KHZ_VERSION}|g" \
    -e "s|__KERNEL_MAJOR__|${KERNEL_MAJOR}|g" \
    -e "s|__KERNEL_MINOR__|${KERNEL_MINOR}|g" \
    "$CHROOT_DIR/tmp/build-15khz-kernel.sh"
  chmod +x "$CHROOT_DIR/tmp/build-15khz-kernel.sh"
  chroot "$CHROOT_DIR" /tmp/build-15khz-kernel.sh >> "$LOG_FILE" 2>&1 \
    && ok "Kernel 15kHz compilado (${KERNEL_15KHZ_VERSION}-15khz)" \
    || err "Build do kernel 15kHz falhou; rode sem --with-15khz-kernel para ISO EDID-only"
}

# ── squashfs ──────────────────────────────────────────────────
create_squashfs() {
  step "Criando squashfs"
  mkdir -p "$ISO_DIR/live"
  rm -f "$ISO_DIR/live/filesystem.squashfs"
  mksquashfs "$CHROOT_DIR" "$ISO_DIR/live/filesystem.squashfs" \
    -comp zstd -Xcompression-level 6 -wildcards \
    -no-progress -e "proc/*" "sys/*" "dev/*" "tmp/*" "run/*" \
    2>&1 | tail -3 | tee -a "$LOG_FILE"
  ok "squashfs: $(du -sh "$ISO_DIR/live/filesystem.squashfs" | cut -f1)"
}

# ── Kernel e initrd ───────────────────────────────────────────
copy_kernel() {
  step "Copiando kernel e initrd"
  mkdir -p "$ISO_DIR/boot/grub"
  local VMLINUZ INITRD
  VMLINUZ=$(find "$CHROOT_DIR/boot" -name "vmlinuz-*" | sort -V | tail -1)
  INITRD=$(find  "$CHROOT_DIR/boot" -name "initrd.img-*" | sort -V | tail -1)
  [[ -z "$VMLINUZ" ]] && err "vmlinuz nao encontrado"
  [[ -z "$INITRD"  ]] && err "initrd nao encontrado"
  cp "$VMLINUZ" "$ISO_DIR/boot/vmlinuz"
  cp "$INITRD"  "$ISO_DIR/boot/initrd.img"
  ok "Kernel: $(basename "$VMLINUZ")"
  ok "Initrd: $(basename "$INITRD")"
}

# ── GRUB config ───────────────────────────────────────────────
create_grub_config() {
  local MONITOR_LABEL
  case "$MONITOR_PROFILE" in
    15khz) MONITOR_LABEL="CRT 15kHz" ;;
    25khz) MONITOR_LABEL="CRT 25kHz" ;;
    31khz) MONITOR_LABEL="CRT 31kHz" ;;
  esac
  install -Dm644 "$(dirname "$(realpath "$0")")/config/grub.cfg" "$ISO_DIR/boot/grub/grub.cfg"
  sed -i "s|__MONITOR_LABEL__|${MONITOR_LABEL}|g" "$ISO_DIR/boot/grub/grub.cfg"
}

# ── Gerar ISO (BIOS + EFI via grub-mkrescue) ──────────────────
# grub-mkrescue substitui o antigo par grub-mkstandalone+xorriso manual:
# um core image "i386-pc" com o modulo "normal" (obrigatorio pro menu)
# estoura o teto de ~480KB do formato — nao e' questao de --format, o
# teto e do proprio conceito de core image embutido do i386-pc. O
# grub-mkrescue contorna isso gerando um core minimo que so localiza o
# filesystem e carrega o resto (normal/video/menu) do disco em tempo de
# boot, e ja cobre El Torito BIOS + EFI hibrido sem loop mount.
create_iso() {
  step "Gerando ISO: $OUTPUT_ISO"
  mkdir -p "$(dirname "$OUTPUT_ISO")"
  grub-mkrescue -o "$OUTPUT_ISO" "$ISO_DIR" \
    -- -volid "FLIPEROS_${FLIPEROS_VERSION//./_}" \
    >> "$LOG_FILE" 2>&1
  [[ -f "$OUTPUT_ISO" ]] || err "ISO nao gerada"
  ok "ISO pronta: $OUTPUT_ISO ($(du -sh "$OUTPUT_ISO" | cut -f1))"
}

# ── Cleanup ───────────────────────────────────────────────────
cleanup() {
  info "Limpando..."
  unmount_chroot
  # --one-file-system garante que nao sai dos limites do diretorio
  [[ "$WORK_DIR" == /tmp/fliperos-iso-build.* ]] || err "Workspace invalido"
  if findmnt -rn -o TARGET | grep -F "$WORK_DIR/"; then err "Mounts restantes; limpeza recusada"; fi
  rm -rf --one-file-system "$WORK_DIR"
  ok "Limpeza concluida"
}

# ── Resumo ────────────────────────────────────────────────────
summary() {
  echo -e "\n${GRN}${BLD}ISO gerada com sucesso!${RST}"
  echo -e "  Arquivo : ${CYN}$OUTPUT_ISO${RST}"
  echo -e "  Tamanho : ${CYN}$(du -sh "$OUTPUT_ISO" | cut -f1)${RST}"
  echo -e "  Monitor : ${CYN}$MONITOR_PROFILE${RST}"
  echo -e "\n  Gravar em USB:"
  echo -e "  ${CYN}sudo dd if=$OUTPUT_ISO of=/dev/sdX bs=4M status=progress oflag=sync${RST}"
  echo -e "\n  Login: fliperos / fliperos"
  $SKIP_SWITCHRES  && echo -e "  ${YLW}SwitchRes nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $SKIP_GROOVYMAME && echo -e "  ${YLW}GroovyMAME nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $SKIP_RETROARCH  && echo -e "  ${YLW}RetroArch nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $SKIP_FLYCAST    && echo -e "  ${YLW}Flycast nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $SKIP_PCSX2      && echo -e "  ${YLW}PCSX2 nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $SKIP_SUPERMODEL && echo -e "  ${YLW}Supermodel nao incluido — execute apos boot: sudo fliperos-postinstall${RST}"
  $WITH_15KHZ_KERNEL && echo -e "  ${CYN}Kernel 15kHz patcheado: ${KERNEL_15KHZ_VERSION}-15khz (D0023R) — KMS/switchres sem X${RST}"
  $WITH_15KHZ_KERNEL && echo -e "  ${YLW}Kernel proprio nao assinado — desabilite Secure Boot na UEFI${RST}"
  echo -e "  ${DIM}Log: $LOG_FILE${RST}\n"
}

# ── Main ──────────────────────────────────────────────────────
trap 'exit 130' INT
trap 'exit 143' TERM
build_exit() {
  local result=$?
  if (( result != 0 )); then unmount_chroot || true; fi
  exit "$result"
}
trap build_exit EXIT

mkdir -p "$(dirname "$LOG_FILE")"
echo "FliperOS mkiso v${FLIPEROS_VERSION} - $(date)" > "$LOG_FILE"

echo -e "${GRN}${BLD}FliperOS mkiso v${FLIPEROS_VERSION}${RST}"
echo -e "${DIM}Ubuntu $UBUNTU_CODENAME — monitor: $MONITOR_PROFILE — saida: $OUTPUT_ISO${RST}\n"

mkdir -p "$ISO_DIR"

[[ -c /dev/null ]] || err "/dev/null invalido; build recusado"
check_host_deps
build_rootfs
configure_chroot
copy_fliperos_scripts
cp -a "$(dirname "$(realpath "$0")")/config" "$CHROOT_DIR/opt/fliperos/"
cp -a "$(dirname "$(realpath "$0")")/patches/kernel-15khz" "$CHROOT_DIR/opt/fliperos/kernel-patches"
bash "$(dirname "$(realpath "$0")")/fliperos-install-video.sh" "$CHROOT_DIR" "$MONITOR_PROFILE"
chroot "$CHROOT_DIR" update-initramfs -u -k all
build_switchres_chroot
build_groovymame_chroot
build_retroarch_chroot
build_flycast_chroot
build_pcsx2_chroot
build_supermodel_chroot
build_15khz_kernel_chroot
rm -f "$CHROOT_DIR/usr/sbin/policy-rc.d"
unmount_chroot
create_squashfs
copy_kernel
create_grub_config
create_iso
cleanup
summary
