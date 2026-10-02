#!/usr/bin/env bash
# ============================================================
#  FliperOS mkiso v0.7
#  Gera a midia de instalacao do FliperOS (Ubuntu 24.04 + kernel 15 kHz)
#  Uso: sudo bash fliperos-mkiso.sh [--output /caminho/saida.iso]
#       [--skip-switchres] [--skip-groovymame] [--skip-retroarch]
#       [--skip-flycast] [--skip-pcsx2] [--skip-supermodel]
#       [--skip-dolphin] [--skip-hypseus] [--skip-openbor]
#       [--skip-wine] [--skip-steam] [--skip-heroic]
#       [--skip-skyscraper] [--skip-input-drivers] [--skip-wheel-drivers]
#       [--kernel-cache DIR] [--repo DIR] [--splash fliperos|evangelion|none]
#       [--wifi-ssid NOME --wifi-psk SENHA]
#  No Windows, execute somente dentro do container Docker.
# ============================================================

set -euo pipefail
if grep -qi microsoft /proc/sys/kernel/osrelease && [[ ! -f /.dockerenv ]]; then
  echo "Build direto no WSL recusado. Use Dockerfile.fliperos (CLAUDE.md)." >&2; exit 1
fi

GRN='\033[0;32m'; YLW='\033[1;33m'; RED='\033[0;31m'
BLU='\033[0;34m'; CYN='\033[0;36m'; DIM='\033[2m'
BLD='\033[1m'; RST='\033[0m'

FLIPEROS_VERSION="0.7"
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
SKIP_DOLPHIN=false
SKIP_HYPSEUS=false
SKIP_OPENBOR=false
SKIP_WINE=false
SKIP_STEAM=false
SKIP_HEROIC=false
SKIP_SKYSCRAPER=false
# Kernel 15 kHz (fliperos-kernel.sh): compilar leva a maior parte do build,
# entao os .deb ficam num cache chaveado por versao e patches. Com o
# diretorio /output montado (o jeito documentado de rodar), o cache fica la.
KERNEL_CACHE=""
[[ -d /output ]] && KERNEL_CACHE="/output/kernel-cache"
# Repositorio dos frontends (packaging/build-deb.sh + make-repo.sh): vai
# para dentro da imagem como fonte local do apt.
FLIPEROS_REPO=""
[[ -d /output/repo ]] && FLIPEROS_REPO="/output/repo"
SPLASH_THEME="fliperos"
SKIP_INPUT_DRIVERS=false
# Volante: hid-tmff2 (Thrustmaster T150/T300/TX/T248...) e new-lg4ff
# (Logitech, com force feedback completo; substitui o hid-logitech do
# kernel) vem sempre; --skip-wheel-drivers os deixa de fora.
WITH_WHEEL_DRIVERS=true
# Wi-Fi opcional gravado na imagem: numa maquina sem cabo de rede, e o unico
# jeito de ela subir acessivel por SSH sem interacao no console.
WIFI_SSID=""
WIFI_PSK=""
# ID do "Evangelion UI Plymouth Theme" no Pling. A URL de download e assinada
# com JWT e expira, entao e resolvida pela API no momento do build.
EVANGELION_PLING_ID="2354544"

# Versoes fixadas do que nao existe no Ubuntu 24.04. O hash confere que o
# arquivo baixado e o mesmo que foi testado.
# Gum: as telas do fliperos-setup.
GUM_VERSION="2.0.2"
GUM_SHA256="9aad8600d9d280d91544439f35db4c9583cc0201bb718ac6afcc0f4989ea945b"
# AntiMicroX (joystick -> teclado/mouse), como no GroovyArcade. O noble so
# tem o qjoypad; o antimicrox vem do .deb oficial do projeto.
ANTIMICROX_VERSION="3.6.1"
ANTIMICROX_SHA256="033cfdf7651d59fcc372c0fab38df0257508c9722dbebd8931aec3df45983948"
# Switchres: a mesma versao do pacote switchres do GroovyArcade.
SWITCHRES_TAG="v2.2.1"
# Skyscraper (Setup > Scraper): o fork mantido, o mesmo do pacote do
# GroovyArcade. O commit confere que a tag nao foi movida.
SKYSCRAPER_TAG="3.21.0"
SKYSCRAPER_COMMIT="8a95bb924f094e0f111fc188e66022903ea9f7d4"
# PCSX2: o AppImage oficial (o codigo atual nao compila com as bibliotecas
# do Ubuntu 24.04; ver build_pcsx2_chroot).
PCSX2_VERSION="2.8.2"
# RetroArch: informacoes dos cores e perfis de controle de fabrica (o
# Online Updater atualiza os dois depois, na pasta do usuario).
RA_CORE_INFO_COMMIT="5a74858ab2f7a50cebb5a6330895bc38899531c0"
RA_AUTOCONFIG_COMMIT="3579625fa24e61c86c48d03de9d5f9fd7b323a16"
# Hypseus Singe (laserdisc): a serie 3 exige SDL3, que o noble nao tem.
HYPSEUS_TAG="v2.12.1"
# OpenBOR: as tags antigas nao tem o CMake; o commit e o do master.
OPENBOR_COMMIT="787b6770409935137579715febf80cf7a529b748"
# Dolphin (GameCube/Wii): a versao estavel.
DOLPHIN_TAG="2609"
# Heroic Games Launcher (GOG, Epic e Amazon): o .deb oficial.
HEROIC_VERSION="2.22.3"
HEROIC_SHA256="f89eed7e0eb900fbe3051edfedbe7532db14328241cbf8c1fb766462dfc0b849"
PCSX2_SHA256="0c46bb6a88aa2782b10853a7b07cf3387ba99cbef2b966372cd2315b8571abea"

# ── Args ─────────────────────────────────────────────────────
usage() {
  sed -n '5,12p' "$0" | sed 's/^# *//'
}
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
    --skip-dolphin)    SKIP_DOLPHIN=true; shift ;;
    --skip-hypseus)    SKIP_HYPSEUS=true; shift ;;
    --skip-openbor)    SKIP_OPENBOR=true; shift ;;
    --skip-wine)       SKIP_WINE=true; shift ;;
    --skip-steam)      SKIP_STEAM=true; shift ;;
    --skip-heroic)     SKIP_HEROIC=true; shift ;;
    --skip-skyscraper) SKIP_SKYSCRAPER=true; shift ;;
    --skip-input-drivers) SKIP_INPUT_DRIVERS=true; shift ;;
    --skip-wheel-drivers) WITH_WHEEL_DRIVERS=false; shift ;;
    # Compatibilidade: era opcional antes; agora e o padrao.
    --with-wheel-drivers) WITH_WHEEL_DRIVERS=true; shift ;;
    --kernel-cache)
      [[ $# -ge 2 && -n "${2:-}" ]] || { echo "Erro: --kernel-cache requer diretorio."; exit 1; }
      KERNEL_CACHE="$2"; shift 2 ;;
    --repo)
      [[ $# -ge 2 && -n "${2:-}" ]] || { echo "Erro: --repo requer diretorio."; exit 1; }
      FLIPEROS_REPO="$2"; shift 2 ;;
    --wifi-ssid)
      [[ $# -ge 2 && -n "${2:-}" ]] || { echo "Erro: --wifi-ssid requer valor."; exit 1; }
      WIFI_SSID="$2"; shift 2 ;;
    --wifi-psk)
      [[ $# -ge 2 && -n "${2:-}" ]] || { echo "Erro: --wifi-psk requer valor."; exit 1; }
      WIFI_PSK="$2"; shift 2 ;;
    --splash)
      [[ $# -ge 2 ]] || { echo "Erro: --splash requer valor."; exit 1; }
      case "$2" in
        fliperos|evangelion|none) SPLASH_THEME="$2" ;;
        *) echo "Erro: --splash invalido: $2 (fliperos, evangelion ou none)"; exit 1 ;;
      esac
      shift 2 ;;
    /*.iso|*.iso)     OUTPUT_ISO="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) usage; exit 1 ;;
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
  # git/gcc/libc6-dev/make: o Limine vem do upstream e o utilitario "limine"
  # e compilado no build (ver fliperos-limine.sh).
  local DEPS=(debootstrap squashfs-tools xorriso git gcc libc6-dev make)
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
  # Sem /dev/fd o "<(...)" do bash falha: o dkms (hooks do kernel) avisava
  # "/dev/fd/63: No such file or directory".
  ln -s /proc/self/fd   "$CHROOT_DIR/dev/fd"
  ln -s /proc/self/fd/0 "$CHROOT_DIR/dev/stdin"
  ln -s /proc/self/fd/1 "$CHROOT_DIR/dev/stdout"
  ln -s /proc/self/fd/2 "$CHROOT_DIR/dev/stderr"
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

  # O kernel NAO vem do apt: e o 15 kHz, instalado a partir dos .deb do
  # fliperos-kernel.sh em install_15khz_kernel(). Com o linux-image-generic
  # junto, o copy_kernel() poderia pegar o kernel errado.
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

# live-boot necessário para boot=live no kernel da ISO. O LXDE e as
# ferramentas de joystick/diagnostico sao as do GroovyArcade (htop, evtest,
# joy2key, qjoypad, hwinfo, lshw, read-edid, i2c-tools). O LXDE vem pelos
# componentes do metapacote lxde menos os terminais: o lxterminal e o xterm
# (o x-terminal-emulator padrao, com fontes bitmap que a imagem nem tem) nao
# desenhavam as bordas do Gum. O terminal e o Alacritty. Sem o metapacote,
# nada depende do lxterminal e o autoremove nao leva o desktop junto.
# fbset traz o con2fbmap do teste de saidas; jq e rsync sao do fliperos-setup;
# triggerhappy le as teclas de volume em qualquer tela (fliperos-rootfs.sh);
# as engines murrine e pixbuf sao do GTK 2 do tema Dracula, o librsvg2
# desenha os icones SVG do menu e o gxmessage (GTK 3) e a confirmacao do
# fliperos-launch antes de fechar o desktop. usbutils (lsusb) mostra o
# vendor:produto dos controles em Setup > Quirks. systemd-timesyncd acerta o
# relogio pela rede: no gabinete o relogio da BIOS estava 2 meses atrasado e
# o apt recusava todo repositorio ("not valid yet"). A App Store do LXDE e o
# GNOME Software (o App Center do Ubuntu 24.04 depende do snap, que nao vai
# na imagem), com o plugin de Flatpak; o portal GTK da as janelas de abrir
# arquivo aos apps Flatpak.
apt-get install -y --no-install-recommends \
  live-boot live-boot-initramfs-tools \
  locales tzdata systemd systemd-sysv udev sudo bash \
  coreutils util-linux e2fsprogs dosfstools parted \
  wget curl git ca-certificates jq rsync fbset zstd \
  xserver-xorg-core xserver-xorg-input-libinput xinit x11-xserver-utils x11-utils \
  libdrm2 libgbm1 mesa-vulkan-drivers mesa-utils \
  libsdl2-2.0-0 libsdl2-dev build-essential cmake \
  libdrm-dev libgbm-dev libxrandr-dev libxi-dev libxext-dev libfontconfig1-dev \
  joystick alsa-utils linux-firmware \
  dkms evtest \
  kbd console-setup \
  xserver-xorg-video-radeon xserver-xorg-video-amdgpu \
  openssh-server network-manager wpasupplicant iw python3 pciutils usbutils libdrm-tests edid-decode squashfs-tools \
  systemd-timesyncd \
  gnome-software gnome-software-plugin-flatpak flatpak xdg-desktop-portal-gtk \
  samba samba-common-bin avahi-daemon avahi-utils udisks2 wireless-regdb \
  plymouth plymouth-label fonts-dejavu-core \
  lxde-core lxsession openbox-lxde-session lxpolkit lxappearance lxappearance-obconf lxde-icon-theme \
  lxhotkey-gtk lxinput lxrandr lxsession-edit galculator gpicview mousepad xarchiver alacritty \
  gnome-themes-extra gtk2-engines-murrine gtk2-engines-pixbuf librsvg2-common gxmessage \
  htop joy2key qjoypad hwinfo lshw read-edid i2c-tools mc \
  espeak-ng triggerhappy zsh

# Flathub como fonte de Flatpak da App Store, para o sistema todo.
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo \
  || echo "AVISO: Flathub nao foi adicionado (sem rede no build?)"

systemctl enable ssh
# As host keys sao apagadas abaixo pra que cada instalacao gere as suas, e
# precisam ser regeradas no boot. O ssh.service do Ubuntu ja traz
# "ExecStartPre=/usr/sbin/sshd -t", e drop-in SOMA comandos DEPOIS dos do
# pacote — sem host key o "sshd -t" falha com "no hostkeys available" e o
# servico morre antes de chegar no keygen. A linha ExecStartPre vazia zera a
# lista herdada pra reordenar: gerar a chave primeiro, validar depois.
mkdir -p /etc/systemd/system/ssh.service.d
cat > /etc/systemd/system/ssh.service.d/keys.conf << 'SSHKEYS'
[Service]
ExecStartPre=
ExecStartPre=/usr/bin/ssh-keygen -A
ExecStartPre=/usr/sbin/sshd -t
SSHKEYS
rm -f /etc/ssh/ssh_host_*
truncate -s 0 /etc/machine-id
systemctl enable NetworkManager

# Compartilhamento do acervo pela rede (equivalente ao share [GroovyArcade]
# do gasetup): o smb.conf e o config/smb.conf, que o fliperos-rootfs.sh poe.
systemctl enable smbd
systemctl enable nmbd
systemctl enable avahi-daemon

# O lxde puxa o lightdm como dependencia obrigatoria, e ele briga com o
# modelo de sessao daqui: quem inicia a sessao e o login da tty1, nao um
# display manager. Pior, o lightdm falhando em loop trava o boot — o
# plymouth-quit e ordenado depois do display-manager, entao nunca roda, e o
# plymouth-quit-wait espera sem limite. "mask" e nao "disable" porque ele
# tambem e puxado como dependencia de display-manager.service.
systemctl mask lightdm
systemctl mask light-locker 2>/dev/null || true
# Mascarar "lightdm" nao basta: o postinst dele cria display-manager.service
# apontando direto pro unit file, o que passa por cima da mascara no nome. E o
# graphical.target puxa display-manager.service. Dai o alvo padrao tem de ser
# multi-user: aqui nao existe display manager, a sessao sai do login da tty1
# (o LXDE tambem, via startlxde no xinit, nao via greeter).
systemctl set-default multi-user.target
# ln -sf em vez de "systemctl mask": o postinst do lightdm ja criou esse
# symlink, e o mask se recusa a sobrescrever um arquivo existente. Apontar
# pra /dev/null e exatamente o que mascarar faz.
ln -sf /dev/null /etc/systemd/system/display-manager.service

# Rede de seguranca: mesmo com o lightdm fora, nada deve poder pendurar o boot
# indefinidamente esperando o splash sair.
mkdir -p /etc/systemd/system/plymouth-quit-wait.service.d
printf '[Unit]\nJobTimeoutSec=20\n[Service]\nTimeoutStartSec=20\n' \
  > /etc/systemd/system/plymouth-quit-wait.service.d/timeout.conf

locale-gen pt_BR.UTF-8
update-locale LANG=pt_BR.UTF-8

# O locale sozinho NAO define o layout do teclado: sem isto o console fica em
# "us", e num ABNT2 acento, c-cedilha, / e ? saem errados — justamente ao
# digitar senha. /etc/default/keyboard e o mecanismo do Ubuntu e vale pro
# console e pro Xorg de uma vez; o wizard troca por aqui.
cat > /etc/default/keyboard << 'KEYBOARD'
XKBMODEL="pc105"
XKBLAYOUT="br"
XKBVARIANT="abnt2"
XKBOPTIONS=""
BACKSPACE="guess"
KEYBOARD
ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
dpkg-reconfigure -f noninteractive tzdata

# render: acesso a /dev/dri/renderD* (KMS sem X). netdev: NetworkManager sem root.
# plugdev: montar pendrive via udisks2. tty: console.
useradd -m -s /bin/bash -G video,render,audio,input,dialout,tty,plugdev,netdev,games,sudo fliperos
echo "fliperos:fliperos" | chpasswd
printf 'fliperos\nfliperos\n' | smbpasswd -s -a fliperos
cat > /etc/sudoers.d/fliperos << SUDOERS
fliperos ALL=(ALL) NOPASSWD: /sbin/poweroff, /sbin/reboot, /usr/sbin/reboot, /usr/sbin/poweroff
SUDOERS
chmod 440 /etc/sudoers.d/fliperos

echo "fliperos" > /etc/hostname
cat > /etc/hosts << HOSTS
127.0.0.1 localhost
127.0.1.1 fliperos
HOSTS

mkdir -p /opt/fliperos/{bin,config,roms/{mame,ps2,dreamcast,model3},bios,logs}
mkdir -p /etc/fliperos/mame
chown -R fliperos:fliperos /opt/fliperos

chown -R fliperos:fliperos /etc/fliperos/mame

mkdir -p /etc/systemd/system/getty@tty1.service.d
# Login automatico calado: sem o "fliperos login: (automatic login)"
# (--skip-login), sem o /etc/issue e limpando o que o kernel deixou na tela.
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << UNIT
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin fliperos --skip-login --noissue %I \$TERM
UNIT

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
    "$CHROOT_DIR/tmp/fliperos-chroot-setup.sh"

  chmod +x "$CHROOT_DIR/tmp/fliperos-chroot-setup.sh"
  chroot "$CHROOT_DIR" /tmp/fliperos-chroot-setup.sh 2>&1 | tee -a "$LOG_FILE" | grep -v "^$"
  ok "Chroot configurado"
}

# ── Arquivos do FliperOS ──────────────────────────────────────
# fliperos-setup, sessao de boot, LXDE, paleta do console (fliperos-rootfs.sh).
install_fliperos_files() {
  step "Instalando o fliperos-setup e a configuracao do FliperOS"
  FLIPEROS_ROOTFS_CHROOT=1 bash "$(dirname "$(realpath "$0")")/fliperos-rootfs.sh" "$CHROOT_DIR" \
    >> "$LOG_FILE" 2>&1 || err "fliperos-rootfs.sh falhou (ver $LOG_FILE)"
  ok "fliperos-setup em /usr/local/lib/fliperos-setup"
  # Tema Dracula do LXDE (GTK fixado por commit + Openbox), baixado aqui no
  # container do build, que tem o git.
  bash "$(dirname "$(realpath "$0")")/fliperos-dracula.sh" "$CHROOT_DIR" \
    >> "$LOG_FILE" 2>&1 || err "Tema Dracula falhou (ver $LOG_FILE)"
  ok "Tema Dracula no LXDE"
}

# ── Pacotes que nao existem no Ubuntu 24.04 ───────────────────
# Baixados antes do debootstrap, como o Limine: rede ruim aparece em
# segundos, nao depois de uma hora de build.
fetch_debs() {
  step "Gum, AntiMicroX e Heroic"
  DEBS_DIR="$WORK_DIR/debs"
  mkdir -p "$DEBS_DIR"
  fetch_deb "https://github.com/charmbracelet/gum/releases/download/v${GUM_VERSION}/gum_${GUM_VERSION}_amd64.deb" \
    "$GUM_SHA256" gum.deb
  fetch_deb "https://github.com/AntiMicroX/antimicrox/releases/download/${ANTIMICROX_VERSION}/antimicrox-${ANTIMICROX_VERSION}-ubuntu-24.04-x86_64.deb" \
    "$ANTIMICROX_SHA256" antimicrox.deb
  if ! $SKIP_HEROIC; then
    fetch_deb "https://github.com/Heroic-Games-Launcher/HeroicGamesLauncher/releases/download/v${HEROIC_VERSION}/Heroic-${HEROIC_VERSION}-linux-amd64.deb" \
      "$HEROIC_SHA256" heroic.deb
  fi
}

fetch_deb() {
  local url=$1 sha=$2 name=$3
  curl -sSfL --retry 3 --max-time 600 -o "$DEBS_DIR/$name" "$url" >> "$LOG_FILE" 2>&1 \
    || err "Download falhou: $url"
  echo "$sha  $DEBS_DIR/$name" | sha256sum -c --quiet - >> "$LOG_FILE" 2>&1 \
    || err "Hash diferente do fixado: $url"
  ok "$name ($(du -h "$DEBS_DIR/$name" | cut -f1))"
}

install_debs_chroot() {
  step "Instalando Gum e AntiMicroX no chroot"
  cp "$DEBS_DIR"/*.deb "$CHROOT_DIR/tmp/"
  chroot "$CHROOT_DIR" bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends /tmp/gum.deb /tmp/antimicrox.deb' >> "$LOG_FILE" 2>&1 \
    || err "Instalacao do gum/antimicrox falhou (ver $LOG_FILE)"
  rm -f "$CHROOT_DIR"/tmp/*.deb
  ok "gum $(chroot "$CHROOT_DIR" gum --version | awk '{print $3}'), antimicrox $ANTIMICROX_VERSION"
}

# ── Repositorio local do FliperOS (frontends) ─────────────────
# Os .deb do packaging/ (build-deb.sh + make-repo.sh) vao para
# /opt/fliperos/repo, uma fonte do apt dentro da propria imagem: o Setup >
# Frontend instala dali sem rede. O Attract-Mode Plus ja vem instalado (as
# dependencias dele vem do Ubuntu, e o gabinete pode nao ter rede).
install_local_repo_chroot() {
  if [[ -z $FLIPEROS_REPO ]] || ! compgen -G "$FLIPEROS_REPO/*.deb" > /dev/null; then
    warn "Sem repositorio de frontends: gere com packaging/build-deb.sh e packaging/make-repo.sh"
    return
  fi
  step "Repositorio local do FliperOS (frontends)"
  local repo="$CHROOT_DIR/opt/fliperos/repo"
  rm -rf "$repo"
  mkdir -p "$repo"
  cp "$FLIPEROS_REPO"/*.deb "$FLIPEROS_REPO"/Packages "$FLIPEROS_REPO"/Packages.gz "$FLIPEROS_REPO"/Release "$repo/" \
    || err "Repositorio incompleto em $FLIPEROS_REPO (falta o Packages ou o Release do make-repo.sh)"
  chmod -R a+rX "$repo"
  echo "deb [trusted=yes] file:/opt/fliperos/repo ./" > "$CHROOT_DIR/etc/apt/sources.list.d/fliperos.list"
  chroot "$CHROOT_DIR" bash -c 'apt-get update -qq && DEBIAN_FRONTEND=noninteractive \
    apt-get install -y --no-install-recommends fliperos-attractplus' >> "$LOG_FILE" 2>&1 \
    || err "Instalacao do Attract-Mode Plus do repositorio local falhou (ver $LOG_FILE)"
  ok "Repositorio local com $(ls "$repo"/*.deb | wc -l) pacote(s); Attract-Mode Plus instalado"
}

# ── Kernel 15 kHz ─────────────────────────────────────────────
# Kernel.org LTS com os patches D0023R (fliperos-kernel.sh), o equivalente do
# linux-15khz do GroovyArcade. E ele que entende o video=640x480iS do menu de
# boot. Compilado no container (nao no chroot) e guardado no cache.
install_15khz_kernel() {
  step "Kernel 15 kHz"
  local src key dir
  src="$(dirname "$(realpath "$0")")"
  key=$(bash "$src/fliperos-kernel.sh" key)
  if [[ -n $KERNEL_CACHE ]]; then
    dir="$KERNEL_CACHE/$key"
  else
    dir="$WORK_DIR/kernel"
  fi
  if compgen -G "$dir/linux-image-*.deb" > /dev/null && compgen -G "$dir/linux-headers-*.deb" > /dev/null; then
    ok "Kernel $key do cache ($dir)"
  else
    info "Compilando o kernel $key (demora; fica no cache para os proximos builds)"
    mkdir -p "$dir"
    bash "$src/fliperos-kernel.sh" build "$dir" >> "$LOG_FILE" 2>&1 \
      || { rm -f "$dir"/*.deb; err "Compilacao do kernel falhou (ver $LOG_FILE)"; }
    ok "Kernel $key compilado"
  fi
  cp "$dir"/linux-image-*.deb "$dir"/linux-headers-*.deb "$CHROOT_DIR/tmp/"
  # O postinst do linux-image gera o initrd e chama os hooks (Limine, DKMS).
  chroot "$CHROOT_DIR" bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y /tmp/linux-image-*.deb /tmp/linux-headers-*.deb' \
    >> "$LOG_FILE" 2>&1 || err "Instalacao do kernel falhou (ver $LOG_FILE)"
  rm -f "$CHROOT_DIR"/tmp/linux-*.deb
  KERNEL_RELEASE=$(ls "$CHROOT_DIR/lib/modules")
  ok "Kernel instalado: $KERNEL_RELEASE"
}

# ── Compilar SwitchRes2 no chroot ─────────────────────────────
build_switchres_chroot() {
  if $SKIP_SWITCHRES; then
    warn "SwitchRes pulado — sem ele nao ha EDIDs por monitor, geometria nem as entradas EDID do boot"
    return
  fi
  step "Compilando SwitchRes ($SWITCHRES_TAG) no chroot"
  cat > "$CHROOT_DIR/tmp/build-switchres.sh" << 'SRSCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends \
  libdrm-dev libgbm-dev libxrandr-dev libxi-dev libxext-dev pkg-config git build-essential \
  libsdl2-dev libsdl2-ttf-dev
git clone --depth=1 --branch __SWITCHRES_TAG__ https://github.com/antonioginer/switchres /tmp/srs
# Projeto usa makefile proprio (sem CMakeLists.txt) — build via make direto.
make -C /tmp/srs -j$(nproc) all
# "grid" e um target separado que "all" nao cobre e "install" nao instala:
# e a carta de teste do geometry e da resolucao personalizada do
# fliperos-setup. Precisa de SDL2_ttf.
make -C /tmp/srs grid
make -C /tmp/srs install PREFIX=/usr/local
install -m755 /tmp/srs/switchres /usr/local/bin/switchres
install -m755 /tmp/srs/grid /usr/local/bin/grid
# O "geometry" que o gasetup chama e o geometry.py do proprio Switchres
# (o PKGBUILD do GroovyArcade o instala assim, com o shebang acrescentado).
{ echo '#!/usr/bin/env python3'; cat /tmp/srs/geometry.py; } > /usr/local/bin/geometry
chmod 755 /usr/local/bin/geometry
# switchres.ini do upstream, como o pacote do GroovyArcade; o fliperos-setup
# grava nele o monitor escolhido.
[ -f /etc/switchres.ini ] || sed 's/\r$//' /tmp/srs/switchres.ini > /etc/switchres.ini
ldconfig
rm -rf /tmp/srs
# Um EDID por preset de monitor, mais os de super resolucao das entradas
# "EDID" do menu de boot.
/usr/local/sbin/fliperos-rebuild-edids /lib/firmware/edid
echo "SwitchRes OK"
SRSCRIPT
  sed -i "s|__SWITCHRES_TAG__|${SWITCHRES_TAG}|g" "$CHROOT_DIR/tmp/build-switchres.sh"
  chmod +x "$CHROOT_DIR/tmp/build-switchres.sh"
  chroot "$CHROOT_DIR" /tmp/build-switchres.sh >> "$LOG_FILE" 2>&1 \
    && ok "SwitchRes, grid, geometry e $(ls "$CHROOT_DIR/lib/firmware/edid" | wc -l) EDIDs" \
    || err "SwitchRes falhou; ISO nao sera publicada como completa"
  for edid in generic_15_super_resp generic_15_super_resi generic_15 arcade_15; do
    [[ -s "$CHROOT_DIR/lib/firmware/edid/$edid.bin" ]] || err "EDID ausente: $edid.bin"
  done
}

# ── Skyscraper (Setup > Scraper) ──────────────────────────────
# Qt6, a mesma do AntiMicroX. As bibliotecas que o binario usa ficam marcadas
# como instaladas a mao, senao o autoremove as levaria junto com os -dev. O
# ldd mostra os caminhos por /lib, que com o /usr unificado nao estao no
# banco do dpkg: o readlink -f leva ao arquivo real em /usr/lib.
build_skyscraper_chroot() {
  if $SKIP_SKYSCRAPER; then
    warn "Skyscraper pulado — o Scraper do Setup nao vai funcionar"
    return
  fi
  step "Compilando Skyscraper ($SKYSCRAPER_TAG) no chroot"
  cat > "$CHROOT_DIR/tmp/build-skyscraper.sh" << 'SKYSCRIPT'
#!/bin/bash
set -eo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
BUILD_DEPS="qt6-base-dev qt6-base-dev-tools qmake6"
apt-get install -y --no-install-recommends $BUILD_DEPS libqt6sql6-sqlite p7zip-full
git clone --depth=1 --branch __SKYSCRAPER_TAG__ https://github.com/Gemba/skyscraper /tmp/skyscraper
[ "$(git -C /tmp/skyscraper rev-parse HEAD)" = __SKYSCRAPER_COMMIT__ ] || { echo "Skyscraper: commit inesperado"; exit 1; }
cd /tmp/skyscraper
qmake6 PREFIX=/usr/local
make -j"$(nproc)"
make install
cd /
libs=$(ldd /usr/local/bin/Skyscraper | awk '/=> \// { print $3 }' | xargs -r readlink -f)
pkgs=$(dpkg -S $libs | cut -d: -f1 | sort -u)
apt-mark manual $pkgs libqt6sql6-sqlite p7zip-full > /dev/null
apt-get remove -y $BUILD_DEPS
apt-get autoremove -y -qq
rm -rf /tmp/skyscraper
# Sem pipe: e aqui que uma biblioteca levada pelo autoremove aparece.
/usr/local/bin/Skyscraper --version > /tmp/skyscraper-version
head -1 /tmp/skyscraper-version
echo "SKYSCRAPER_OK"
SKYSCRIPT
  sed -i -e "s|__SKYSCRAPER_TAG__|${SKYSCRAPER_TAG}|g" \
         -e "s|__SKYSCRAPER_COMMIT__|${SKYSCRAPER_COMMIT}|g" "$CHROOT_DIR/tmp/build-skyscraper.sh"
  chmod +x "$CHROOT_DIR/tmp/build-skyscraper.sh"
  chroot "$CHROOT_DIR" /tmp/build-skyscraper.sh >> "$LOG_FILE" 2>&1 \
    && ok "Skyscraper compilado" \
    || err "Skyscraper falhou; use --skip-skyscraper para uma ISO sem o Scraper"
}

# ── Wi-Fi gravado na imagem (opcional) ────────────────────────
# Escrito direto no filesystem do chroot, nao pelo sed do script de setup:
# uma senha com | ou & quebraria a substituicao.
install_wifi_profile() {
  [[ -n "$WIFI_SSID" ]] || return 0
  step "Gravando perfil de Wi-Fi na imagem"
  warn "A ISO passa a CONTER a senha do Wi-Fi em texto. Nao a distribua."
  local dir="$CHROOT_DIR/etc/NetworkManager/system-connections"
  mkdir -p "$dir"
  local file="$dir/fliperos-wifi.nmconnection"
  {
    echo "[connection]"
    echo "id=fliperos-wifi"
    echo "type=wifi"
    echo "autoconnect=true"
    echo "autoconnect-priority=10"
    echo
    echo "[wifi]"
    echo "mode=infrastructure"
    echo "ssid=$WIFI_SSID"
    echo
    if [[ -n "$WIFI_PSK" ]]; then
      echo "[wifi-security]"
      echo "key-mgmt=wpa-psk"
      echo "psk=$WIFI_PSK"
      echo
    fi
    echo "[ipv4]"
    echo "method=auto"
    echo
    echo "[ipv6]"
    echo "method=auto"
  } > "$file"
  # O NetworkManager IGNORA o arquivo em silencio se ele nao for 0600 do root.
  chmod 600 "$file"
  chown 0:0 "$file"
  ok "Wi-Fi \"$WIFI_SSID\" gravado; conecta sozinho no boot"
}

# ── Drivers de input out-of-tree ──────────────────────────────
# O kernel do Ubuntu JA cobre boa parte: hid-logitech traz o lg4ff (force
# feedback de G25/G27/G29/DFGT), hid-logitech-hidpp cobre G920, e hid-tmff
# cobre Thrustmaster antigo. O que falta e:
#   - GunCon 2: nao existe no mainline, so como modulo externo (o gap real);
#   - Thrustmaster moderno (T300/T248/TX): hid-tmff2;
#   - refinamento de FFB Logitech: new-lg4ff, que SUBSTITUI o hid-logitech.
# Por isso o GunCon 2 entra por padrao e os dois de volante ficam opcionais:
# trocar um driver mainline que funciona por um out-of-tree nao testado aqui
# nao e troca que se faz calada.
build_input_drivers_chroot() {
  if $SKIP_INPUT_DRIVERS; then
    warn "Drivers de input pulados — GunCon 2 nao vai funcionar"
    return
  fi
  step "Compilando drivers de input (DKMS)"
  cat > "$CHROOT_DIR/tmp/build-input.sh" << 'INPUTSCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends dkms git build-essential
KVER=$(ls /lib/modules | sort -V | tail -1)
echo "Compilando para o kernel $KVER"

# GunCon 2 (0b9a:016a). O repo nao traz dkms.conf, entao escrevemos um; o
# Makefile dele aceita KVERSION, que e o nome que o dkms expande em $kernelver.
git clone --depth 1 https://github.com/beardypig/guncon2 /usr/src/guncon2-1.0
cat > /usr/src/guncon2-1.0/dkms.conf << 'DKMSCONF'
PACKAGE_NAME="guncon2"
PACKAGE_VERSION="1.0"
# O 'make' entre aspas NAO e enfeite: sem isso o dkms acrescenta
# KERNELRELEASE= na linha de comando, e o Makefile do guncon2 usa
# justamente "ifeq ($(KERNELRELEASE),)" pra decidir se foi chamado pelo
# Kbuild — com a variavel definida ele cai no ramo que so declara obj-m, onde
# o alvo "modules" nao existe, e o build morre com exit 2. Aspas suprimem
# esse acrescimo (documentado no dkms(8) e no dkms.conf do hid-tmff2).
MAKE[0]="'make' KVERSION=$kernelver modules"
CLEAN="'make' clean"
BUILT_MODULE_NAME[0]="guncon2"
DEST_MODULE_LOCATION[0]="/kernel/drivers/input/joystick"
AUTOINSTALL="yes"
DKMSCONF
dkms add -m guncon2 -v 1.0
# O dkms diz "consulte o make.log" e o make.log fica dentro do chroot, que
# desaparece com o container: sem despejar aqui, o erro do compilador se perde.
if ! dkms build -m guncon2 -v 1.0 -k "$KVER"; then
  echo "--- make.log do guncon2 ---"
  cat /var/lib/dkms/guncon2/1.0/build/make.log 2>/dev/null || echo "(sem make.log)"
  exit 1
fi
dkms install -m guncon2 -v 1.0 -k "$KVER"
# Carrega no boot: sem isso o modulo so existe em disco.
echo guncon2 > /etc/modules-load.d/fliperos-guncon2.conf
echo "GUNCON2_OK"
INPUTSCRIPT

  if $WITH_WHEEL_DRIVERS; then
    cat >> "$CHROOT_DIR/tmp/build-input.sh" << 'WHEELSCRIPT'

# Thrustmaster moderno. Precisa dos submodulos: deps/hid-tminit chaveia o
# volante do modo inicial pro modo real. A versao vem do dkms.conf do projeto,
# nao do dkms-install.sh dele — os dois divergem no upstream (0.82 vs 0.83) e
# o dkms recusa quando o diretorio e a PACKAGE_VERSION nao batem.
git clone --depth 1 --recurse-submodules \
  https://github.com/Kimplul/hid-tmff2 /tmp/hid-tmff2
TM_VER=$(sed -n 's/^PACKAGE_VERSION="\(.*\)"/\1/p' /tmp/hid-tmff2/dkms/dkms.conf)
[ -n "$TM_VER" ] || { echo "nao deu pra ler a versao do hid-tmff2"; exit 1; }
cp -r /tmp/hid-tmff2 "/usr/src/hid-tmff2-$TM_VER"
cp /tmp/hid-tmff2/dkms/dkms.conf "/usr/src/hid-tmff2-$TM_VER/dkms.conf"
dkms add -m hid-tmff2 -v "$TM_VER"
dkms build -m hid-tmff2 -v "$TM_VER" -k "$KVER"
dkms install -m hid-tmff2 -v "$TM_VER" -k "$KVER"

# new-lg4ff substitui o hid-logitech do kernel (DEST_MODULE_NAME=hid-logitech).
git clone --depth 1 https://github.com/berarma/new-lg4ff /tmp/new-lg4ff
LG_VER=$(sed -n 's/^PACKAGE_VERSION="\(.*\)"/\1/p' /tmp/new-lg4ff/dkms.conf)
[ -n "$LG_VER" ] || { echo "nao deu pra ler a versao do new-lg4ff"; exit 1; }
cp -r /tmp/new-lg4ff "/usr/src/new-lg4ff-$LG_VER"
dkms add -m new-lg4ff -v "$LG_VER"
dkms build -m new-lg4ff -v "$LG_VER" -k "$KVER"
dkms install -m new-lg4ff -v "$LG_VER" -k "$KVER"
rm -rf /tmp/hid-tmff2 /tmp/new-lg4ff
echo "WHEELS_OK"
WHEELSCRIPT
  fi

  chmod +x "$CHROOT_DIR/tmp/build-input.sh"
  if chroot "$CHROOT_DIR" /tmp/build-input.sh >> "$LOG_FILE" 2>&1; then
    ok "GunCon 2 compilado via DKMS"
    if $WITH_WHEEL_DRIVERS; then
      ok "hid-tmff2 e new-lg4ff compilados via DKMS"
    fi
  else
    echo -e "${DIM}--- fim do log do chroot ---${RST}" >&2
    tail -25 "$LOG_FILE" >&2 || true
    err "Compilacao dos drivers de input falhou"
  fi
  # O return 0 e necessario: o status do ultimo comando vira o status da
  # funcao, e a funcao e chamada nua no fluxo principal, onde o set -e aborta
  # com status 1. Foi assim que "$WITH_WHEEL_DRIVERS && ok ..." — que sozinho
  # nao aborta nada — derrubou um build inteiro depois do driver ja compilado.
  return 0
}

# ── Splash grafico (Plymouth) ─────────────────────────────────
# Resolucao do modo de boot padrao (640x480i, 15 kHz): o splash tem de ser
# gerado nela, nao na resolucao de um monitor moderno.
splash_mode_geometry() {
  echo "640x480"
}

# O Ubuntu 24.04 NAO traz plymouth-set-default-theme: o pacote plymouth
# fornece apenas /usr/bin/plymouth e /usr/sbin/plymouthd. O tema padrao e um
# alternative — mesmo mecanismo que o install.sh do tema Evangelion usa.
set_default_plymouth_theme() {
  local theme="$1"
  local file="/usr/share/plymouth/themes/${theme}/${theme}.plymouth"
  chroot "$CHROOT_DIR" test -f "$file" \
    || err "Tema de splash ausente no chroot: $file"
  chroot "$CHROOT_DIR" update-alternatives --install \
      /usr/share/plymouth/themes/default.plymouth default.plymouth "$file" 100 \
    && chroot "$CHROOT_DIR" update-alternatives --set default.plymouth "$file" \
    || err "Nao foi possivel definir $theme como tema padrao do Plymouth"
}

install_splash_theme() {
  if [[ "$SPLASH_THEME" == none ]]; then
    warn "Splash desabilitado (--splash none); boot em modo texto"
    return
  fi
  if [[ "$SPLASH_THEME" == fliperos ]]; then
    set_default_plymouth_theme fliperos
    ok "Splash: tema fliperos (texto renderizado, sem asset binario)"
    return
  fi

  step "Instalando o splash Evangelion UI (Pling ${EVANGELION_PLING_ID})"
  warn "O autor do tema declara RISCO DE CONVULSAO (luzes piscando)."
  warn "Tema fan-made, sem arquivo de licenca no pacote — revise antes de redistribuir a ISO."
  local geom url tarball vendored
  geom=$(splash_mode_geometry)
  tarball="$CHROOT_DIR/tmp/evangelion-ui.tar.gz"
  vendored="$(dirname "$(realpath "$0")")/themes/evangelion-ui.tar.gz"
  if [[ -f "$vendored" ]]; then
    cp "$vendored" "$tarball"
    ok "Tema obtido de themes/evangelion-ui.tar.gz (copia local)"
  else
    url=$(curl -sL --max-time 60 \
      "https://api.pling.com/ocs/v1/content/data/${EVANGELION_PLING_ID}?format=json" \
      | tr ',' '\n' | grep '"downloadlink1"' | cut -d'"' -f4)
    [[ -n "$url" ]] || err "Nao foi possivel resolver o link do tema no Pling"
    curl -sL --max-time 900 -o "$tarball" "$url" || err "Download do tema Evangelion falhou"
    ok "Tema baixado ($(du -h "$tarball" | cut -f1))"
  fi

  cat > "$CHROOT_DIR/tmp/install-splash.sh" << SPLASHSCRIPT
#!/bin/bash
set -e
# O configure_chroot limpa /var/lib/apt/lists, entao sem este update o
# apt nao acha o imagemagick.
apt-get update -qq
apt-get install -y --no-install-recommends imagemagick
dest=/usr/share/plymouth/themes/evangelion-ui
mkdir -p "\$dest"
cd /tmp && rm -rf eva && mkdir eva && tar xzf evangelion-ui.tar.gz -C eva
cp eva/evangelion-ui.plymouth eva/evangelion-ui.script "\$dest/"
tar xzf eva/images.tar.gz -C "\$dest/"
# O script do tema centraliza os frames sem escalar, entao 720x480 apareceria
# recortado no modo do CRT. O "!" forca as dimensoes exatas: achatar para
# ${geom} e o que corrige a proporcao num tubo de pixel nao-quadrado.
mogrify -resize '${geom}!' "\$dest"/*.png
sed -i 's|EVANGELION_UI_PATH|/usr|g' "\$dest/evangelion-ui.plymouth"
apt-get remove -y --purge imagemagick
apt-get autoremove -y -qq
rm -rf /tmp/eva /tmp/evangelion-ui.tar.gz
du -sh "\$dest"
SPLASHSCRIPT
  chmod +x "$CHROOT_DIR/tmp/install-splash.sh"
  if chroot "$CHROOT_DIR" /tmp/install-splash.sh >> "$LOG_FILE" 2>&1; then
    set_default_plymouth_theme evangelion-ui
    ok "Splash: Evangelion UI, 202 frames reescalados para $geom"
  else
    # O $LOG_FILE fica DENTRO do container e desaparece com --rm, entao o
    # motivo da falha tem de ir pra saida padrao ou nao ha como diagnosticar.
    echo -e "${DIM}--- fim do log do chroot ---${RST}" >&2
    tail -25 "$LOG_FILE" >&2 || true
    err "Instalacao do splash Evangelion falhou"
  fi
}

# ── Compilar GroovyMAME no chroot ─────────────────────────────
build_groovymame_chroot() {
  if $SKIP_GROOVYMAME; then
    warn "GroovyMAME pulado (--skip-groovymame)"
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
# aqui: --enable-kms --enable-egl --disable-x11 --disable-wayland builda
# limpo (config.h confirma HAVE_KMS/HAVE_EGL/HAVE_GBM=1, sem
# HAVE_X11/HAVE_WAYLAND) e o binario resultante reporta "KMS: yes",
# "EGL: yes", "udev: yes" em --features.
# Por isso RetroArch/Flycast usam fliperos-kms-run (sem Xorg), diferente
# de PCSX2/Supermodel que continuam em fliperos-x11-run.
# Com SDL2 para o driver de controle "sdl2" existir em Drivers > Controle
# (mapeamentos do fliperos-controllers, como os outros emuladores; sem
# perfil, o "Standard Gamepad" embutido). O padrao segue udev; video e audio
# continuam fixos no retroarch.cfg (gl/KMS e alsa). SDL 1.x fica fora.
build_retroarch_chroot() {
  if $SKIP_RETROARCH; then
    warn "RetroArch pulado (--skip-retroarch)"
    return
  fi
  step "Compilando RetroArch (KMS/DRM, sem X11) no chroot"
  cat > "$CHROOT_DIR/tmp/build-retroarch.sh" << 'RASCRIPT'
#!/bin/bash
set -e
apt-get update -qq
apt-get install -y --no-install-recommends \
  libegl1-mesa-dev libgles2-mesa-dev libudev-dev libsdl2-dev

git clone --depth=1 https://github.com/libretro/RetroArch /tmp/retroarch
cd /tmp/retroarch
./configure --enable-kms --enable-egl --disable-x11 --disable-wayland \
  --disable-sdl --enable-sdl2
make -j"$(nproc)"
make install
# O atalho do proprio RetroArch abriria o binario dentro do X do desktop,
# onde este build (so KMS) nao roda; o do FliperOS passa pelo
# fliperos-launch. O icone (share/pixmaps) fica.
rm -f /usr/local/share/applications/com.libretro.RetroArch.desktop
cd /
rm -rf /tmp/retroarch

# Cores, informacoes dos cores e perfis de controle ficam em /opt/fliperos,
# do usuario fliperos: o Online Updater do RetroArch baixa outros cores do
# buildbot da libretro e atualiza os .info e os perfis sem precisar de root.
RA_DIR=/opt/fliperos/retroarch
mkdir -p "$RA_DIR/cores" "$RA_DIR/info" "$RA_DIR/autoconfig"

# fetch_pinned REPO COMMIT DESTINO: so os arquivos daquele commit.
fetch_pinned() {
  rm -rf /tmp/pinned && git init -q /tmp/pinned
  git -C /tmp/pinned fetch -q --depth 1 "https://github.com/$1" "$2"
  mkdir -p "$3"
  git -C /tmp/pinned archive FETCH_HEAD | tar -x -C "$3"
  rm -rf /tmp/pinned
}
# Perfis de autoconfig de joypad (deteccao automatica por vendor/product ID).
fetch_pinned libretro/retroarch-joypad-autoconfig __RA_AUTOCONFIG_COMMIT__ /tmp/ra-autoconfig
cp -a /tmp/ra-autoconfig/udev "$RA_DIR/autoconfig/"
rm -rf /tmp/ra-autoconfig
# Informacoes dos cores (nome, sistemas, BIOS, savestate): sem elas o menu
# so mostra o nome do arquivo e nao sabe o que cada core roda.
fetch_pinned libretro/libretro-core-info __RA_CORE_INFO_COMMIT__ /tmp/ra-info
cp /tmp/ra-info/*.info "$RA_DIR/info/"
rm -rf /tmp/ra-info

# Cores de fabrica, para funcionar sem rede: NES/SNES/Mega Drive/GBA
# (essenciais 8/16-bit), PS1 e um core de arcade leve (mame2010,
# complementar ao GroovyMAME standalone, o caminho principal de arcade).
# Compilados aqui: no buildbot os cores avulsos sao "nightly" e nao dao
# para fixar por hash.
build_core() {
  local repo="$1" name dir mk=""
  name="$(basename "$repo")"
  dir="/tmp/core-${name}"
  git clone --depth=1 --recursive "https://github.com/${repo}" "$dir"
  if [[ -f "$dir/libretro/Makefile" ]]; then
    dir="$dir/libretro"; mk="Makefile"
  elif [[ -f "$dir/Makefile.libretro" ]]; then
    mk="Makefile.libretro"
  elif [[ -f "$dir/Makefile" ]]; then
    mk="Makefile"
  else
    # So CMake (o mGBA desde 2025): o core sai com BUILD_LIBRETRO, sem o
    # frontend proprio (Qt/SDL) nem as bibliotecas opcionais.
    cmake -S "$dir" -B "$dir/build" -DCMAKE_BUILD_TYPE=Release -DBUILD_LIBRETRO=ON \
      -DBUILD_QT=OFF -DBUILD_SDL=OFF -DBUILD_GL=OFF -DBUILD_GLES2=OFF -DBUILD_GLES3=OFF \
      -DUSE_FFMPEG=OFF -DUSE_DISCORD_RPC=OFF -DUSE_LUA=OFF -DUSE_SQLITE3=OFF -DUSE_ELF=OFF \
      -DUSE_EDITLINE=OFF -DUSE_MINIZIP=OFF -DUSE_LIBZIP=OFF -DUSE_EPOXY=OFF -DENABLE_SCRIPTING=OFF
    cmake --build "$dir/build" -j"$(nproc)"
  fi
  [[ -z $mk ]] || make -C "$dir" -f "$mk" -j"$(nproc)"
  # Um core que nao gerou o .so falha aqui, e nao calado.
  compgen -G "$dir/*_libretro.so" > /dev/null || compgen -G "$dir/build/*_libretro.so" > /dev/null \
    || { echo "core ${name}: nenhum *_libretro.so gerado"; exit 1; }
  find "$dir" -maxdepth 2 -name '*_libretro.so' -exec cp {} "$RA_DIR/cores/" \;
  rm -rf "/tmp/core-${name}"
}
build_core libretro/libretro-fceumm
build_core libretro/snes9x
build_core libretro/Genesis-Plus-GX
build_core libretro/mgba
build_core libretro/pcsx_rearmed
build_core libretro/mame2010-libretro
chown -R fliperos:fliperos "$RA_DIR"

echo "RetroArch OK"
RASCRIPT
  sed -i -e "s|__RA_AUTOCONFIG_COMMIT__|${RA_AUTOCONFIG_COMMIT}|g" \
         -e "s|__RA_CORE_INFO_COMMIT__|${RA_CORE_INFO_COMMIT}|g" "$CHROOT_DIR/tmp/build-retroarch.sh"
  chmod +x "$CHROOT_DIR/tmp/build-retroarch.sh"
  chroot "$CHROOT_DIR" /tmp/build-retroarch.sh >> "$LOG_FILE" 2>&1 \
    && ok "RetroArch compilado (KMS/DRM) com cores e autoconfig de joypad" \
    || err "RetroArch falhou; use --skip-retroarch explicitamente para ISO sem ele"
}

# ── Compilar Flycast (Dreamcast/Naomi), X11 ──────────────────
# Recipe identica a testada no container de validacao: precisa de
# 'git submodule update --init --recursive' (nao vem no clone raso) e das
# deps de build abaixo. Roda pelo fliperos-x11-run, onde o Switchres cria o
# modo da tabela emulator-modes.conf (640x240 no 15 kHz). O SDL2 do Ubuntu
# tambem tem o kmsdrm, se um dia voltar para o KMS. USE_VULKAN=OFF porque
# adiciona deps novas (glslang/SPIRV) sem necessidade pro caminho OpenGL.
build_flycast_chroot() {
  if $SKIP_FLYCAST; then
    warn "Flycast pulado (--skip-flycast)"
    return
  fi
  step "Compilando Flycast (Dreamcast/Naomi, X11) no chroot"
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
# Icone do menu do LXDE (config/applications/fliperos-flycast.desktop).
install -Dm644 shell/linux/flycast.png /usr/local/share/pixmaps/flycast.png
cd /
rm -rf /tmp/flycast
echo "Flycast OK"
FCSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-flycast.sh"
  chroot "$CHROOT_DIR" /tmp/build-flycast.sh >> "$LOG_FILE" 2>&1 \
    && ok "Flycast compilado" \
    || err "Flycast falhou; use --skip-flycast explicitamente para ISO sem ele"
}

# ── PCSX2 (PS2), X11 ──────────────────────────────────────────
# O AppImage oficial, fixado por versao e hash: o PCSX2 atual exige SDL3,
# Qt 6.10, plutosvg, ryml e Shaderc, que o Ubuntu 24.04 nao tem (o Qt dele
# e o 6.4). O AppImage traz as bibliotecas dele e e extraido em /opt/pcsx2,
# sem precisar de FUSE. Qt nao tem backend KMS suportado: fica em X11 via
# fliperos-x11-run.
build_pcsx2_chroot() {
  if $SKIP_PCSX2; then
    warn "PCSX2 pulado (--skip-pcsx2)"
    return
  fi
  step "PCSX2 ${PCSX2_VERSION} (AppImage oficial, X11)"
  local image="$WORK_DIR/pcsx2.AppImage"
  curl -sSfL --retry 3 --max-time 900 -o "$image" \
    "https://github.com/PCSX2/pcsx2/releases/download/v${PCSX2_VERSION}/pcsx2-v${PCSX2_VERSION}-linux-appimage-x64-Qt.AppImage" \
    >> "$LOG_FILE" 2>&1 || err "Download do PCSX2 falhou"
  echo "$PCSX2_SHA256  $image" | sha256sum -c --quiet - >> "$LOG_FILE" 2>&1 \
    || err "PCSX2: hash diferente do fixado"
  chmod +x "$image"
  (cd "$WORK_DIR" && rm -rf squashfs-root && "$image" --appimage-extract > /dev/null) \
    || err "PCSX2: o AppImage nao extraiu"
  rm -rf "$CHROOT_DIR/opt/pcsx2"
  mv "$WORK_DIR/squashfs-root" "$CHROOT_DIR/opt/pcsx2"
  chmod -R a+rX "$CHROOT_DIR/opt/pcsx2"
  printf '#!/bin/sh\nexec /opt/pcsx2/AppRun "$@"\n' > "$CHROOT_DIR/usr/local/bin/pcsx2"
  chmod 755 "$CHROOT_DIR/usr/local/bin/pcsx2"
  # Icone do menu do LXDE (config/applications/fliperos-pcsx2.desktop).
  install -Dm644 "$CHROOT_DIR/opt/pcsx2/PCSX2.png" "$CHROOT_DIR/usr/local/share/pixmaps/pcsx2.png"
  rm -f "$image"
  ok "PCSX2 ${PCSX2_VERSION} em /opt/pcsx2"
}

# ── Compilar Supermodel (Sega Model 3), X11 ───────────────────
# SDL2+OpenGL, sem caminho KMS/DRM documentado pelo projeto — fica em
# X11 via fliperos-x11-run.
build_supermodel_chroot() {
  if $SKIP_SUPERMODEL; then
    warn "Supermodel pulado (--skip-supermodel)"
    return
  fi
  step "Compilando Supermodel (Model 3, X11) no chroot"
  cat > "$CHROOT_DIR/tmp/build-supermodel.sh" << 'SMSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends libsdl2-dev libsdl2-net-dev libglu1-mesa-dev zlib1g-dev
git clone --depth=1 https://github.com/trzy/Supermodel /tmp/supermodel
cd /tmp/supermodel
# Makefile proprio (sem CMake), como o README do projeto manda no Linux.
make -f Makefiles/Makefile.UNIX -j"$(nproc)"
install -m755 bin/supermodel /usr/local/bin/supermodel
# Games.xml (a lista de jogos que ele reconhece) e a configuracao padrao.
mkdir -p /usr/local/share/supermodel
cp -r Config Assets /usr/local/share/supermodel/
cd /
rm -rf /tmp/supermodel
echo "Supermodel OK"
SMSCRIPT
  chmod +x "$CHROOT_DIR/tmp/build-supermodel.sh"
  chroot "$CHROOT_DIR" /tmp/build-supermodel.sh >> "$LOG_FILE" 2>&1 \
    && ok "Supermodel compilado" \
    || err "Supermodel falhou; use --skip-supermodel explicitamente para ISO sem ele"
}

# ── Hypseus Singe (laserdisc: Dragon's Lair, Space Ace...), X11 ──
# Instalado como o README do projeto manda: o binario como hypseus.bin e os
# scripts run.sh/singe.sh como os comandos hypseus e singe, que usam o
# ~/.hypseus. O ~/.hypseus e o /opt/fliperos/roms/hypseus (o acervo do
# Samba): ROMs em roms/, videos de laserdisc em vldp/, jogos Singe em singe/.
build_hypseus_chroot() {
  if $SKIP_HYPSEUS; then
    warn "Hypseus Singe pulado (--skip-hypseus)"
    return
  fi
  step "Compilando Hypseus Singe ($HYPSEUS_TAG) no chroot"
  cat > "$CHROOT_DIR/tmp/build-hypseus.sh" << 'HSSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends autoconf automake libtool pkg-config \
  libsdl2-dev libsdl2-image-dev libsdl2-ttf-dev libsdl2-mixer-dev zlib1g-dev libzip-dev libogg-dev libvorbis-dev
git clone --depth=1 --branch __HYPSEUS_TAG__ https://github.com/DirtBagXon/hypseus-singe /tmp/hypseus
cd /tmp/hypseus
mkdir build
(cd build && cmake ../src -DCMAKE_BUILD_TYPE=Release && make -j"$(nproc)")
install -m755 build/hypseus /usr/local/bin/hypseus.bin
install -m755 scripts/run.sh /usr/local/bin/hypseus
install -m755 scripts/singe.sh /usr/local/bin/singe
home=/opt/fliperos/roms/hypseus
mkdir -p "$home/roms" "$home/vldp" "$home/singe"
cp -R pics sound fonts midi "$home/"
chown -R fliperos:fliperos "$home"
ln -sfn "$home" /home/fliperos/.hypseus
chown -h fliperos:fliperos /home/fliperos/.hypseus
cd /
rm -rf /tmp/hypseus
echo "Hypseus OK"
HSSCRIPT
  sed -i "s|__HYPSEUS_TAG__|${HYPSEUS_TAG}|g" "$CHROOT_DIR/tmp/build-hypseus.sh"
  chmod +x "$CHROOT_DIR/tmp/build-hypseus.sh"
  chroot "$CHROOT_DIR" /tmp/build-hypseus.sh >> "$LOG_FILE" 2>&1 \
    && ok "Hypseus Singe compilado" \
    || err "Hypseus Singe falhou; use --skip-hypseus para ISO sem ele"
}

# ── OpenBOR (beat 'em ups), X11 ───────────────────────────────
# O OpenBOR procura Paks/, Saves/ e Logs/ na pasta em que roda: o comando
# openbor entra em /opt/fliperos/roms/openbor (o acervo do Samba) antes.
build_openbor_chroot() {
  if $SKIP_OPENBOR; then
    warn "OpenBOR pulado (--skip-openbor)"
    return
  fi
  step "Compilando OpenBOR (${OPENBOR_COMMIT:0:7}) no chroot"
  cat > "$CHROOT_DIR/tmp/build-openbor.sh" << 'OBSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends ninja-build libsdl2-dev libvorbis-dev libpng-dev libvpx-dev
git init -q /tmp/openbor
git -C /tmp/openbor fetch -q --depth 1 https://github.com/DCurrent/openbor __OPENBOR_COMMIT__
git -C /tmp/openbor -c advice.detachedHead=false checkout -q FETCH_HEAD
cd /tmp/openbor
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_LINUX=ON -DTARGET_ARCH=AMD64
cmake --build build --parallel
install -Dm755 engine/releases/LINUX/OpenBOR /usr/local/lib/openbor/OpenBOR
install -Dm644 engine/resources/OpenBOR_Icon_128x128.png /usr/local/share/pixmaps/openbor.png
games=/opt/fliperos/roms/openbor
mkdir -p "$games/Paks" "$games/Saves" "$games/Logs" "$games/ScreenShots"
chown -R fliperos:fliperos "$games"
cat > /usr/local/bin/openbor << 'EOF'
#!/bin/sh
# Os jogos (.pak) vao em /opt/fliperos/roms/openbor/Paks.
cd /opt/fliperos/roms/openbor && exec /usr/local/lib/openbor/OpenBOR "$@"
EOF
chmod 755 /usr/local/bin/openbor
cd /
rm -rf /tmp/openbor
echo "OpenBOR OK"
OBSCRIPT
  sed -i "s|__OPENBOR_COMMIT__|${OPENBOR_COMMIT}|g" "$CHROOT_DIR/tmp/build-openbor.sh"
  chmod +x "$CHROOT_DIR/tmp/build-openbor.sh"
  chroot "$CHROOT_DIR" /tmp/build-openbor.sh >> "$LOG_FILE" 2>&1 \
    && ok "OpenBOR compilado" \
    || err "OpenBOR falhou; use --skip-openbor para ISO sem ele"
}

# ── Dolphin (GameCube/Wii), X11 ───────────────────────────────
# Compilado da versao estavel: a distribuicao oficial para Linux e o
# Flatpak, que traria o runtime do KDE (~1 GB). Sem atualizacao automatica
# nem estatisticas. O atalho do proprio Dolphin sai (ele abriria o emulador
# dentro do X do desktop); o do FliperOS passa pelo fliperos-launch.
build_dolphin_chroot() {
  if $SKIP_DOLPHIN; then
    warn "Dolphin pulado (--skip-dolphin)"
    return
  fi
  step "Compilando Dolphin ($DOLPHIN_TAG) no chroot"
  cat > "$CHROOT_DIR/tmp/build-dolphin.sh" << 'DOLSCRIPT'
#!/bin/bash
set -e
apt-get install -y --no-install-recommends \
  qt6-base-dev qt6-base-private-dev libqt6svg6-dev pkg-config \
  libavcodec-dev libavformat-dev libavutil-dev libswscale-dev \
  libxi-dev libxrandr-dev libudev-dev libevdev-dev libsfml-dev libminiupnpc-dev \
  libmbedtls-dev libcurl4-openssl-dev libhidapi-dev libsystemd-dev libbluetooth-dev \
  libasound2-dev libpulse-dev libpugixml-dev libbz2-dev libzstd-dev liblzo2-dev \
  libpng-dev libusb-1.0-0-dev gettext
git clone --depth=1 --branch __DOLPHIN_TAG__ https://github.com/dolphin-emu/dolphin /tmp/dolphin
cd /tmp/dolphin
git submodule update --init --recursive --depth 1
cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/usr/local \
  -DENABLE_AUTOUPDATE=OFF -DENABLE_ANALYTICS=OFF -DENABLE_TESTS=OFF
cmake --build build -j"$(nproc)"
cmake --install build
rm -f /usr/local/share/applications/dolphin-emu.desktop
install -Dm644 Data/dolphin-emu.png /usr/local/share/pixmaps/dolphin-emu.png
cd /
rm -rf /tmp/dolphin
echo "Dolphin OK"
DOLSCRIPT
  sed -i "s|__DOLPHIN_TAG__|${DOLPHIN_TAG}|g" "$CHROOT_DIR/tmp/build-dolphin.sh"
  chmod +x "$CHROOT_DIR/tmp/build-dolphin.sh"
  chroot "$CHROOT_DIR" /tmp/build-dolphin.sh >> "$LOG_FILE" 2>&1 \
    && ok "Dolphin compilado" \
    || err "Dolphin falhou; use --skip-dolphin para ISO sem ele"
}

# ── Arquitetura i386 (Wine de 32 bits e Steam) ────────────────
enable_i386_chroot() {
  chroot "$CHROOT_DIR" dpkg --print-foreign-architectures | grep -qx i386 && return 0
  chroot "$CHROOT_DIR" dpkg --add-architecture i386
  chroot "$CHROOT_DIR" apt-get update -qq >> "$LOG_FILE" 2>&1 || err "apt-get update (i386) falhou"
}

# ── Wine (Model 2 Emulator e jogos do Windows) ────────────────
# O Model 2 Emulator nao vem na imagem (freeware de codigo fechado, sem
# permissao clara de redistribuicao): o fliperos-model2 o procura em
# /opt/fliperos/model2, onde o usuario o copia.
install_wine_chroot() {
  if $SKIP_WINE; then
    warn "Wine pulado (--skip-wine) — sem Model 2"
    return
  fi
  step "Wine (Model 2 Emulator e jogos do Windows)"
  enable_i386_chroot
  chroot "$CHROOT_DIR" bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    wine wine64 wine32:i386' >> "$LOG_FILE" 2>&1 || err "Instalacao do Wine falhou"
  mkdir -p "$CHROOT_DIR/opt/fliperos/model2/roms"
  chroot "$CHROOT_DIR" chown -R fliperos:fliperos /opt/fliperos/model2
  ok "Wine $(chroot "$CHROOT_DIR" wine --version 2> /dev/null | head -1)"
}

# ── Steam ─────────────────────────────────────────────────────
# O steam-installer do Ubuntu (multiverse): o cliente de verdade e baixado
# pela Valve na primeira abertura, com rede. Roda dentro do desktop (X).
install_steam_chroot() {
  if $SKIP_STEAM; then
    warn "Steam pulado (--skip-steam)"
    return
  fi
  step "Steam"
  enable_i386_chroot
  # O pacote do noble so tem avisos no debconf (need-nvidia-i386, purge),
  # que o modo noninteractive pula; a licenca da Valve aparece no proprio
  # cliente, na primeira abertura.
  chroot "$CHROOT_DIR" bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y steam-installer' \
    >> "$LOG_FILE" 2>&1 || err "Instalacao do Steam falhou"
  ok "Steam (o cliente baixa o resto na primeira abertura)"
}

# ── Heroic Games Launcher (GOG, Epic e Amazon) ────────────────
# Nao existe cliente do GOG para Linux; o Heroic e o que se usa (tambem no
# Steam Deck). O .deb oficial, fixado por hash, baixado no fetch_debs.
install_heroic_chroot() {
  if $SKIP_HEROIC; then
    warn "Heroic pulado (--skip-heroic) — sem GOG"
    return
  fi
  step "Heroic Games Launcher $HEROIC_VERSION (GOG)"
  cp "$DEBS_DIR/heroic.deb" "$CHROOT_DIR/tmp/heroic.deb"
  chroot "$CHROOT_DIR" bash -c 'DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /tmp/heroic.deb' \
    >> "$LOG_FILE" 2>&1 || err "Instalacao do Heroic falhou"
  rm -f "$CHROOT_DIR/tmp/heroic.deb"
  ok "Heroic $HEROIC_VERSION"
}

# ── squashfs ──────────────────────────────────────────────────
create_squashfs() {
  step "Criando squashfs"
  # O resolv.conf do container do build (o DNS interno do Docker) servia so
  # ao apt do chroot; na imagem o NetworkManager o escreve com o DNS do DHCP
  # (fliperos-rootfs.sh).
  printf '# Escrito pelo NetworkManager com o DNS da rede.\n' > "$CHROOT_DIR/etc/resolv.conf"
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
  mkdir -p "$ISO_DIR/boot/limine"
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

# ── Limine ────────────────────────────────────────────────────
# Baixado ANTES do debootstrap: um problema de rede aqui aparece em segundos,
# nao depois de uma hora de compilacao.
fetch_limine() {
  step "Limine"
  LIMINE_DIR="$WORK_DIR/limine"
  bash "$(dirname "$(realpath "$0")")/fliperos-limine.sh" fetch "$LIMINE_DIR" >> "$LOG_FILE" 2>&1 \
    || err "Falha ao obter o Limine (ver $LOG_FILE)"
  ok "Limine $("$LIMINE_DIR/limine" version --version-only)"
}

install_limine_rootfs() {
  bash "$(dirname "$(realpath "$0")")/fliperos-limine.sh" rootfs "$CHROOT_DIR" "$LIMINE_DIR"
  ok "Limine e fliperos-limine-update no rootfs"
}

# Parametros comuns a todas as entradas do menu de boot da midia: splash,
# console sem apagar (consoleblank=0, como no GroovyArcade), o radeon nas
# placas SI/CIK, onde o 15 kHz foi validado no gabinete, e os do modo de
# latencia padrao (LATENCY_BASE_PARAMS em fliperos-setup/lib/latency.sh) e
# do boot calado (BOOT_SILENT em fliperos-setup/lib/bootloader.sh).
BOOT_COMMON="quiet splash loglevel=3 rd.udev.log_level=3 udev.log_level=3 vt.global_cursor_default=0 consoleblank=0 radeon.si_support=1 radeon.cik_support=1 amdgpu.si_support=0 amdgpu.cik_support=0 mitigations=off audit=0 usbhid.jspoll=1 usbhid.kbpoll=1 usbhid.mousepoll=1"

create_boot_config() {
  install -Dm644 "$(dirname "$(realpath "$0")")/config/limine.conf" "$ISO_DIR/boot/limine/limine.conf"
  sed -i -e "s|__VERSION__|${FLIPEROS_VERSION}|g" -e "s|__COMMON__|${BOOT_COMMON}|g" \
    "$ISO_DIR/boot/limine/limine.conf"
}

# ── Gerar ISO (BIOS + EFI via Limine) ─────────────────────────
create_iso() {
  step "Gerando ISO: $OUTPUT_ISO"
  mkdir -p "$(dirname "$OUTPUT_ISO")"
  bash "$(dirname "$(realpath "$0")")/fliperos-limine.sh" iso "$LIMINE_DIR" "$ISO_DIR" \
    "$OUTPUT_ISO" "FLIPEROS_${FLIPEROS_VERSION//./_}" >> "$LOG_FILE" 2>&1 \
    || err "ISO nao gerada (ver $LOG_FILE)"
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
  echo -e "  Kernel  : ${CYN}${KERNEL_RELEASE:-?} (patches 15 kHz D0023R)${RST}"
  echo -e "\n  Gravar em USB:"
  echo -e "  ${CYN}sudo dd if=$OUTPUT_ISO of=/dev/sdX bs=4M status=progress oflag=sync${RST}"
  echo -e "\n  Login: fliperos / fliperos"
  echo -e "  ${YLW}Kernel proprio nao assinado — desabilite o Secure Boot na UEFI${RST}"
  $SKIP_SWITCHRES  && echo -e "  ${YLW}Sem SwitchRes: sem EDIDs por monitor, geometria nem as entradas EDID do boot${RST}"
  $SKIP_GROOVYMAME && echo -e "  ${YLW}GroovyMAME nao incluido${RST}"
  $SKIP_RETROARCH  && echo -e "  ${YLW}RetroArch nao incluido${RST}"
  $SKIP_FLYCAST    && echo -e "  ${YLW}Flycast nao incluido${RST}"
  $SKIP_PCSX2      && echo -e "  ${YLW}PCSX2 nao incluido${RST}"
  $SKIP_SUPERMODEL && echo -e "  ${YLW}Supermodel nao incluido${RST}"
  $SKIP_DOLPHIN    && echo -e "  ${YLW}Dolphin nao incluido${RST}"
  $SKIP_HYPSEUS    && echo -e "  ${YLW}Hypseus Singe nao incluido${RST}"
  $SKIP_OPENBOR    && echo -e "  ${YLW}OpenBOR nao incluido${RST}"
  $SKIP_WINE       && echo -e "  ${YLW}Wine nao incluido (sem Model 2)${RST}"
  $SKIP_STEAM      && echo -e "  ${YLW}Steam nao incluido${RST}"
  $SKIP_HEROIC     && echo -e "  ${YLW}Heroic nao incluido (sem GOG)${RST}"
  $SKIP_SKYSCRAPER && echo -e "  ${YLW}Skyscraper nao incluido (Setup > Scraper indisponivel)${RST}"
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
echo -e "${DIM}Ubuntu $UBUNTU_CODENAME — kernel 15 kHz — saida: $OUTPUT_ISO${RST}\n"

mkdir -p "$ISO_DIR"

[[ -c /dev/null ]] || err "/dev/null invalido; build recusado"
check_host_deps
fetch_limine
fetch_debs
build_rootfs
configure_chroot
install_limine_rootfs
install_fliperos_files
install_debs_chroot
install_local_repo_chroot
# O kernel antes dos drivers DKMS (compilados para ele) e antes do
# update-initramfs final.
install_15khz_kernel
install_wifi_profile
install_splash_theme
build_input_drivers_chroot
build_switchres_chroot
# Depois dos EDIDs (switchres) e do tema do splash: o hook do Plymouth so
# embarca o tema marcado como padrao, e o initramfs e o unico lugar onde os
# EDIDs das entradas "EDID" do boot existem na hora do KMS.
chroot "$CHROOT_DIR" update-initramfs -u -k all >> "$LOG_FILE" 2>&1 || err "update-initramfs falhou"
build_skyscraper_chroot
build_groovymame_chroot
build_retroarch_chroot
build_flycast_chroot
build_pcsx2_chroot
build_supermodel_chroot
build_hypseus_chroot
build_openbor_chroot
build_dolphin_chroot
install_wine_chroot
install_steam_chroot
install_heroic_chroot
# Pastas do acervo (~/roms): uma por emulador e por core do RetroArch, das
# informacoes dos cores que o build do RetroArch deixou.
chroot "$CHROOT_DIR" env HOME=/home/fliperos /opt/fliperos/bin/fliperos-roms >> "$LOG_FILE" 2>&1
chroot "$CHROOT_DIR" chown -R fliperos:fliperos /home/fliperos/roms
rm -f "$CHROOT_DIR/usr/sbin/policy-rc.d"
unmount_chroot
create_squashfs
copy_kernel
create_boot_config
create_iso
cleanup
summary
