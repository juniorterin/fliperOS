#!/usr/bin/env bash
# Atualiza um FliperOS ja instalado com os arquivos deste repositorio, sem
# ISO nova: o mesmo fliperos-rootfs.sh do build, mais o que no build vem de
# fora dele (fliperos-limine-update, login automatico, repositorio local,
# pacotes novos e a linha do kernel). Roda NO gabinete, como root, de dentro
# do pacote que o tools/cabinet-push.sh monta e envia:
#
#   sudo bash /tmp/fliperos-update/tools/cabinet-update.sh
#
# Antes de mexer, guarda o que muda em /root/fliperos-backup-DATA.tgz. No
# fim reinicia o tty1, que volta pelo fluxo novo (launcher padrao e menu).
set -euo pipefail
src=$(cd "$(dirname "$0")/.." && pwd)
lib=/usr/local/lib/fliperos-setup/lib
[[ $EUID -eq 0 ]] || { echo "Run as root (sudo)." >&2; exit 1; }
[[ -f /etc/fliperos/installed ]] || { echo "This is not an installed FliperOS." >&2; exit 1; }

backup=/root/fliperos-backup-$(date +%Y%m%d-%H%M%S).tgz
tar czf "$backup" --ignore-failed-read \
  /usr/local/lib/fliperos-setup /opt/fliperos/bin /usr/local/sbin/fliperos-limine-update \
  /etc/default/fliperos-boot /etc/systemd/system/getty@tty1.service.d /etc/NetworkManager/conf.d \
  /etc/resolv.conf /home/fliperos/.config /home/fliperos/.zshrc /boot/efi/limine/limine.conf 2> /dev/null || true
echo "== Backup: $backup"

# Os arquivos do tema do boot antes e depois: o Plymouth do boot le o tema
# do initramfs, entao um tema mudado so aparece com o initramfs refeito.
splash_sum() {
  local theme
  theme=$(readlink -f /usr/share/plymouth/themes/default.plymouth) || return 0
  { find "$(dirname "$theme")" /usr/share/fonts/truetype/fliperos /etc/initramfs-tools/hooks/fliperos-fonts \
      -type f -exec cksum {} + 2> /dev/null || true; } | sort | cksum
}
splash_before=$(splash_sum)

echo "== FliperOS files (fliperos-rootfs.sh)"
bash "$src/fliperos-rootfs.sh" /
install -Dm755 "$src/fliperos-limine-update.py" /usr/local/sbin/fliperos-limine-update
# As bibliotecas que o Switchres abre por dlopen (libX11.so, libXrandr.so,
# libdrm.so): a imagem sem os -dev vinha sem esses links, e o GroovyMAME
# fechava na interface.
echo "== Libraries opened by name (fliperos-dlopen-links)"
/opt/fliperos/bin/fliperos-dlopen-links || echo "warning: fliperos-dlopen-links failed"
if [[ $(splash_sum) != "$splash_before" ]]; then
  echo "== Boot splash changed: rebuilding the initramfs"
  update-initramfs -u > /dev/null || echo "warning: update-initramfs failed; the old splash stays until it runs"
fi

# O firmware da NVIDIA: as imagens 0.9 e 0.9.1 vinham sem ele (path-exclude
# do dpkg), e o nouveau nao acelera as placas mais novas. A exclusao sai, e
# numa maquina com placa NVIDIA o linux-firmware e reinstalado ja (um
# download grande); nas outras ele volta na proxima atualizacao do pacote.
fwcfg=/etc/dpkg/dpkg.cfg.d/fliperos-firmware
if grep -q 'firmware/nvidia/' "$fwcfg" 2> /dev/null; then
  echo "== NVIDIA firmware back (dpkg path-exclude removed)"
  sed -i -e '/firmware\/nvidia\//d' -e 's/^# NVIDIA, redes de datacenter/# Redes de datacenter/' "$fwcfg"
fi
if [[ ! -d /usr/lib/firmware/nvidia ]] && grep -qsx 0x10de /sys/bus/pci/devices/*/vendor; then
  echo "== NVIDIA card here: reinstalling linux-firmware"
  apt-get update -qq || true
  DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 install -y -q --reinstall linux-firmware ||
    echo "warning: linux-firmware was not reinstalled (no network?); the next update tries again"
fi

echo "== Automatic login without text"
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'UNIT'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin fliperos --skip-login --noissue %I $TERM
UNIT

echo "== Language: English (the keyboard stays as it is)"
# Como a ISO (fliperos-mkiso.sh): o desktop, o Falkon e o sistema em ingles,
# como o Setup. Vale a partir do proximo login (o tty1 reiniciado abaixo).
if [[ $(sed -n 's/^LANG=//p' /etc/default/locale 2> /dev/null) != en_US.UTF-8 ]]; then
  locale -a 2> /dev/null | grep -qix 'en_US.utf8' || locale-gen en_US.UTF-8 > /dev/null
  update-locale LANG=en_US.UTF-8
fi

echo "== DNS through NetworkManager"
nmcli general reload conf > /dev/null && nmcli general reload dns-full > /dev/null || true
sleep 2
grep nameserver /etc/resolv.conf || true

# O indice do repositorio local antes e depois: mudou, o apt tem de reler.
repo_index() { cat /opt/fliperos/repo/Packages* 2> /dev/null | cksum; }
repo_before=$(repo_index)
if compgen -G "$src/repo/*.deb" > /dev/null; then
  echo "== Local repository (/opt/fliperos/repo)"
  rm -rf /opt/fliperos/repo
  mkdir -p /opt/fliperos/repo
  cp "$src"/repo/* /opt/fliperos/repo/
  chmod -R a+rX /opt/fliperos/repo
  echo "deb [trusted=yes] file:/opt/fliperos/repo ./" > /etc/apt/sources.list.d/fliperos.list
fi
repo_after=$(repo_index)

echo "== Clock"
# Sem servico de hora (imagens ate o commit 11f715a), vale o relogio da BIOS,
# que pode estar meses errado: o apt recusa os repositorios ("not valid
# yet"). Acerta pela hora do servidor do Ubuntu antes do apt.
if ! systemctl is-active --quiet systemd-timesyncd; then
  now=$(curl -sI -m 10 http://archive.ubuntu.com/ubuntu/ | sed -n 's/^[Dd]ate: //p' | tr -d '\r')
  [[ -n $now ]] && date -s "$now" > /dev/null && echo "set from the network"
fi
date

echo "== New packages"
# Os que a imagem ganhou depois da instalacao (fliperos-mkiso.sh).
packages=(usbutils systemd-timesyncd p7zip-full gnome-software gnome-software-plugin-flatpak flatpak xdg-desktop-portal-gtk
  alacritty libsdl2-ttf-2.0-0 libsdl2-gfx-1.0-0 libqt6core6t64 libqt6gui6t64 libqt6widgets6t64 cifs-utils smbclient
  falkon transmission-gtk transmission-daemon gvfs
  libnss3 libxss1 libxtst6 libcups2t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libgtk-3-0t64 libasound2t64 xdg-utils)
# A interface grafica do Setup (fliperos-setup/gui) e a area de transferencia
# do navegador do Downloader (config/fliperos-browser).
packages+=(python3-pygame xclip)
# O compressor do Volume leveler (Setup > Audio Setup, lib/audio.sh).
packages+=(swh-plugins)
# Para compilar o filtro de flicker do 480i e a calibracao de cor
# (config/fliperos-deflicker-build).
packages+=(gcc libc6-dev pkg-config libdrm-dev libgl-dev libegl-dev libx11-dev libxrandr-dev)
# E o compositor que leva o filtro ao desktop LXDE (config/fliperos-desktop-deflicker).
packages+=(picom)
[[ -f /etc/apt/sources.list.d/fliperos.list ]] && packages+=(fliperos-attractplus)
# O OpenGL de 32 bits do Wine (os emuladores do Fightcade), onde ha Wine. O
# Wine em si nao vem mais na imagem (Setup > Games > Extras, config/fliperos-extras).
dpkg -s wine32:i386 > /dev/null 2>&1 && packages+=(libgl1:i386 libgl1-mesa-dri:i386 libglx-mesa0:i386)
# So mexe no apt se falta algum pacote ou se o repositorio local mudou: o
# apt-get segura a trava dos pacotes, e quem estivesse instalando um
# frontend pelo Setup naquela hora recebia "Impossivel criar acesso
# exclusivo". Quando mexe, espera a trava de quem estiver com ela.
missing=()
for p in "${packages[@]}"; do
  dpkg -s "$p" > /dev/null 2>&1 || missing+=("$p")
done
if ((${#missing[@]})) || [[ $repo_before != "$repo_after" ]]; then
  apt-get update -qq || echo "warning: apt-get update had errors (no network, or another program holding the lock?)"
  DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 install -y -q --no-install-recommends \
    "${packages[@]}" || echo "warning: did not install ${packages[*]}"
  # Os frontends do repositorio local que ja estao instalados sobem para a
  # versao nova dele (um pacote refeito, como o ES-DE com patch).
  if [[ $repo_before != "$repo_after" ]]; then
    ours=()
    while read -r p; do
      dpkg -s "$p" > /dev/null 2>&1 && ours+=("$p")
    done < <(sed -n 's/^Package: //p' /opt/fliperos/repo/Packages 2> /dev/null)
    if ((${#ours[@]})); then
      echo "== Local repository packages: ${ours[*]}"
      DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 install -y -q --only-upgrade \
        "${ours[@]}" || echo "warning: did not upgrade ${ours[*]}"
    fi
  fi
else
  echo "all installed and the local repository did not change: apt was not used"
fi
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo ||
  echo "warning: Flathub was not added"
# O filtro de flicker do 480i e a calibracao de cor: compilados aqui, como no
# build da imagem, quando o fonte mudou. Pelo sha256 do fonte (gravado ao
# lado do que saiu), nao pela data: o pacote traz a data do arquivo no PC
# de quem enviou, e uma biblioteca compilada depois, de um fonte mais velho,
# parecia em dia (o FPS do painel web nao chegava ao gabinete).
build_native() {
  local name=$1 source=$2 out=$3 sum
  sum=$(sha256sum "$source" | cut -d' ' -f1)
  [[ -f $out && $(cat "$out.source-sha256" 2> /dev/null) == "$sum" ]] && return 0
  echo "== $name"
  if bash "$src/config/fliperos-deflicker-build" "$source" "$out"; then
    printf '%s\n' "$sum" > "$out.source-sha256"
  else
    echo "warning: $name did not compile"
  fi
}
build_native "480i flicker filter (fliperos-deflicker)" "$src/config/fliperos-deflicker.c" \
  /usr/local/lib/fliperos/libfliperos-deflicker.so
build_native "Colour calibration (fliperos-color)" "$src/config/fliperos-color.c" /usr/local/bin/fliperos-color
build_native "Live screen DRM guard (fliperos-dropmaster)" "$src/config/fliperos-dropmaster.c" \
  /usr/local/lib/fliperos/libfliperos-dropmaster.so
build_native "GroovyMAME sound on the ALSA default (fliperos-sdl-audio)" "$src/config/fliperos-sdl-audio.c" \
  /usr/local/lib/fliperos/libfliperos-sdl-audio.so
# O painel web roda o codigo que leu ao subir: o novo vale ja (so se ele
# estava no ar).
systemctl try-restart fliperos-web.service 2> /dev/null || true
# A tela ao vivo tambem (o go2rtc.yaml e refeito ao subir).
systemctl daemon-reload 2> /dev/null
systemctl try-restart fliperos-stream.service 2> /dev/null || true
# O override da App Store (fliperos-rootfs.sh) pode ter chegado depois do
# pacote.
glib-compile-schemas /usr/share/glib-2.0/schemas 2> /dev/null || true

echo "== Terminals: Alacritty only"
# O metapacote lxde depende do lxterminal: os componentes dele (a mesma lista
# do fliperos-mkiso.sh) passam a "instalados a mao" antes, senao um
# autoremove levaria o desktop junto com o metapacote.
lxde_parts=(lxde-core lxsession openbox-lxde-session lxpolkit lxappearance lxappearance-obconf lxde-icon-theme
  lxhotkey-gtk lxinput lxrandr lxsession-edit galculator gpicview mousepad xarchiver)
keep=()
for p in "${lxde_parts[@]}"; do
  dpkg -s "$p" > /dev/null 2>&1 && keep+=("$p")
done
((${#keep[@]})) && apt-mark manual "${keep[@]}" > /dev/null
if command -v alacritty > /dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get purge -y -q lxterminal xterm > /dev/null 2>&1 || true
  echo "lxterminal/xterm: $(dpkg -l lxterminal xterm 2> /dev/null | grep -c '^ii') installed"
  echo "x-terminal-emulator: $(readlink -f /usr/bin/x-terminal-emulator)"
  # O que a imagem sem os -dev deixou sem pacote que dependa dele (bibliotecas
  # que os emuladores abrem por dlopen: o SVG do Qt, sndio, hidapi, OpenAL)
  # passa a instalado a mao, senao um "apt autoremove" as levaria.
  orphans=$(apt-get autoremove -s 2> /dev/null | awk '/^Remv / { print $2 }')
  # shellcheck disable=SC2086 # um pacote por palavra
  [[ -z $orphans ]] || apt-mark manual $orphans > /dev/null
  echo "autoremove would take: $(apt-get autoremove -s 2> /dev/null | grep -c '^Remv') packages"
else
  echo "warning: Alacritty did not install; the old terminals stay"
fi

echo "== Kernel line (boot straight to Plymouth)"
(
  set +eu
  for f in "$lib"/*.sh; do
    # shellcheck source=/dev/null
    . "$f"
  done
  line=$(boot_read_cmdline) || line=$BOOT_BASE_CMDLINE
  new=()
  for word in $line; do
    [[ " $BOOT_SILENT " == *" $word "* ]] && continue
    new+=("$word")
    # shellcheck disable=SC2206 # um parametro por palavra
    [[ $word == splash ]] && new+=($BOOT_SILENT)
  done
  boot_write_cmdline "${new[*]}"
  boot_apply || { echo "boot_apply failed (see /var/log/fliperos-setup.log)"; exit 1; }
  # O fliperos-rootfs.sh reinstalou o retroarch.cfg da imagem: o que o setup
  # decide por maquina volta (largura do CRT SwitchRes, modo de latencia).
  video_retroarch_super
  video_mame_aspect
  video_mame_monitor
  latency_emulators "$(latency_mode)"
  grep -E '^(aspect|monitor) ' "$MAME_INI"
  grep -E '^crt_switch_resolution_super' "$RETROARCH_CFG"
)

echo "== Quiet console (kernel.printk from fliperos-rootfs.sh) already on this boot"
sysctl -q -p /etc/sysctl.d/99-fliperos-console.conf && cat /proc/sys/kernel/printk

echo "== HDA sound always on (power_save from fliperos-rootfs.sh) already on this boot"
if [[ -d /sys/module/snd_hda_intel/parameters ]]; then
  echo 0 > /sys/module/snd_hda_intel/parameters/power_save
  echo N > /sys/module/snd_hda_intel/parameters/power_save_controller
  echo "power_save=$(cat /sys/module/snd_hda_intel/parameters/power_save)"
fi

echo "== Setup > Joysticks > Button mapping buttons in every emulator"
if [[ -f /etc/fliperos/buttons.map ]]; then
  /opt/fliperos/bin/fliperos-buttons save /etc/fliperos/buttons.map | sed 's/^/saved: /'
else
  echo "no map (Setup > Joysticks > Button mapping)"
fi

# O SM2-Emu e compilado na maquina (Setup > Games > Emulators & Games): os
# patches do FliperOS que o update trouxe so entravam numa abertura pelo menu
# do desktop, que pergunta. Pelos frontends nunca. Ja compilado e com outros
# patches, compila de novo aqui; se falhar, o de antes fica (e o menu do
# desktop pergunta de novo).
echo "== Model 2 (SM2-Emu) with the patches of this version"
sm2=/usr/local/bin/fliperos-sm2emu
if [[ -x $sm2 ]] && runuser -u fliperos -- env HOME=/home/fliperos "$sm2" --outdated; then
  mkdir -p /opt/fliperos/logs
  if "$sm2" --deps > /opt/fliperos/logs/sm2-emu-build.log 2>&1 &&
    runuser -u fliperos -- env HOME=/home/fliperos "$sm2" --build >> /opt/fliperos/logs/sm2-emu-build.log 2>&1; then
    echo "rebuilt"
  else
    echo "warning: did not rebuild (the previous build stays; /opt/fliperos/logs/sm2-emu-build.log)"
  fi
else
  echo "not built here, or already with these patches"
fi

echo "== MAME 2010 XML (ROM cleaner)"
/opt/fliperos/bin/fliperos-romclean fetch-mame2010 /usr/local/share/fliperos/mame2010.xml.xz || echo "failed (no network?)"

echo "== Setup > Joysticks > Buttons layout: the buttons table of each MAME"
if [[ -s /etc/fliperos/buttons.layout ]]; then
  (
    set +eu
    for f in "$lib"/*.sh; do
      # shellcheck source=/dev/null
      . "$f"
    done
    buttons_layout_apply
    wc -l "$GAME_BUTTONS" "$GAME_BUTTONS_MAME2010" 2> /dev/null | sed '$d'
  )
else
  echo "no layout (Setup > Joysticks > Buttons layout)"
fi

echo "== FBNeo sets (the system of each one, for the RetroArch core)"
/opt/fliperos/bin/fliperos-fbneo fetch /usr/local/share/fliperos/fbneo-sets.tsv.xz || echo "failed (no network?)"

echo "== Folders in ~ (roms, bios, media, config)"
runuser -u fliperos -- /opt/fliperos/bin/fliperos-roms
ls -ld /opt/fliperos/roms /opt/fliperos/bios
echo "core folders: $(find /home/fliperos/roms/retroarch -mindepth 1 -maxdepth 1 -type d | wc -l)"
echo "config: $(find /home/fliperos/config -mindepth 1 -maxdepth 1 -type l -printf '%f ')"

echo "== Scraper artwork in ~/media"
(
  set +eu
  for f in "$lib"/*.sh; do
    # shellcheck source=/dev/null
    . "$f"
  done
  # A de antes (~/.mame/scraped, ~/.attract/scraped, <pasta>/media) vai para
  # ~/media, e o frontend padrao passa a ler de la.
  scraper_media_migrate
  # O tema padrao do Attract-Mode Plus, baixado do GitHub dele se faltar
  # (config/fliperos-arcadeflow); as telas que estao no Basic passam para ele.
  if launcher_installed attractplus && [[ $(scraper_attract_layout) != Arcadeflow ]]; then
    /opt/fliperos/bin/fliperos-arcadeflow fetch || echo "Arcadeflow: not downloaded (no network?); the displays stay on Basic"
  fi
  # O Pillow da arte das telas do Arcadeflow, onde o tema ja esta instalado.
  [[ $(scraper_attract_layout) != Arcadeflow ]] || /opt/fliperos/bin/fliperos-arcadeflow pillow
  frontends_configure "$(launcher_current)"
  # A configuracao de 240p do ES-DE e do Pegasus instalados (lib/frontends.sh).
  frontends_240p
  frontends_attract_defaults
  frontends_arcadeflow_screen
  frontends_arcadeflow_systems
  for t in $MEDIA_TYPES; do
    echo "$t: $(find "$MEDIA_DIR/$t" -mindepth 2 -type f | wc -l) file(s)"
  done
)
# So se estiver no ar: em "After boot" (Setup > System > Services) ele sobe
# depois da primeira tela.
systemctl try-restart smbd 2> /dev/null || true
udevadm control --reload 2> /dev/null || true
sed -n 's/^FLIPEROS_CMDLINE=//p' /etc/default/fliperos-boot

echo "== Services"
systemctl daemon-reload
systemctl enable --now systemd-timesyncd.service > /dev/null 2>&1 || true
# Mapeamentos de controle do SDL dos controles ligados agora (o servico tambem
# roda no boot e a cada controle ligado).
systemctl start fliperos-controllers.service 2> /dev/null || true
echo "SDL mappings: $(grep -vc '^#' /var/lib/fliperos/gamecontrollerdb.txt 2> /dev/null || echo 0)"
systemctl enable fliperos-padkeys.service > /dev/null 2>&1 || true
systemctl restart fliperos-padkeys.service
# O botao de desligar (config/fliperos-powerkey): o triggerhappy rele as
# teclas dele, e o logind a configuracao (pelo HUP, sem reiniciar: o X e as
# sessoes abertas dependem dele).
systemctl restart triggerhappy.service 2> /dev/null || true
systemctl kill -s HUP systemd-logind.service 2> /dev/null || true
echo "fliperos-padkeys: $(systemctl is-active fliperos-padkeys.service)"
# Pixelcade: so sobe com o pixelweb baixado (Setup > Games > Extras).
systemctl restart fliperos-pixelcade.service 2> /dev/null || true
echo "fliperos-pixelcade: $(systemctl is-active fliperos-pixelcade.service 2> /dev/null)"
# ZeDMD: so sobe com o dmdserver baixado (Setup > Games > Extras).
systemctl restart fliperos-zedmd.service 2> /dev/null || true
echo "fliperos-zedmd: $(systemctl is-active fliperos-zedmd.service 2> /dev/null)"
# DOFLinx: so sobe com ele baixado (Setup > Games > Extras).
systemctl restart fliperos-doflinx.service 2> /dev/null || true
echo "fliperos-doflinx: $(systemctl is-active fliperos-doflinx.service 2> /dev/null)"
# Os discos que ja estavam ligados (os que aparecerem depois, pela udev).
lsblk -rnpo NAME,FSTYPE | awk '$2 != "" { print $1 }' | while read -r dev; do
  /opt/fliperos/bin/fliperos-automount "$dev" 2> /dev/null || true
done
echo "Disks: $(findmnt -rno TARGET | grep -c '^/media/fliperos/')"
# O transmission-daemon do pacote nao: o do Setup > Games > Downloader e o
# fliperos-transmission, que o Setup sobe quando um download e pedido (nunca
# no boot: o fliperos-rootfs.sh tirou o "enabled" de versoes anteriores).
systemctl disable --now transmission-daemon.service > /dev/null 2>&1 || true
systemctl mask transmission-daemon.service > /dev/null 2>&1 || true
systemctl try-restart fliperos-transmission.service
echo "fliperos-transmission: $(systemctl is-active fliperos-transmission.service 2> /dev/null)"

# Pelo fliperos-update (FLIPEROS_UPDATE=1) ele mesmo grava o manifesto e o
# nivel, e o tty1 e quem pediu o update: nao reinicia.
if [[ -n ${FLIPEROS_UPDATE:-} ]]; then
  echo "== Done (fliperos-update)"
  exit 0
fi
echo "== Update manifest and level (fliperos-update)"
python3 "$src/config/fliperos-update" record "$src" || echo "warning: the update manifest was not written"

# So reinicia o tty1 se nele estiver o menu (login, shell, sudo): um jogo,
# frontend ou o desktop aberto agora seria fechado no meio.
# Sem nada alem do menu, o grep -v nao acha nada e sai com 1: com pipefail
# isso parava o script aqui.
busy=$(pgrep -l -t tty1 | awk '{ print $2 }' | { grep -vxE 'login|zsh|bash|sudo|fliperos-tty1' || true; } |
  sort -u | tr '\n' ' ')
if [[ -z $busy ]]; then
  echo "== Restarting tty1 with the new flow"
  # O menu aberto (o Setup roda no pty do sudo, fora do tty1) e a interface
  # grafica dele: sem isto o Setup antigo ficava orfao e a interface podia
  # segurar o video, e o menu novo abria em texto.
  pkill -TERM -f '^bash /usr/local/(bin|lib/fliperos-setup)/fliperos-setup --menu' 2> /dev/null || true
  pkill -TERM -f 'fliperos-setup/gui/fliperos-gui --serve' 2> /dev/null || true
  # A interface ainda com o video na mao: o X do jogo do boot (modo jogo)
  # nao pegava a placa ("drmSetMaster failed") e o jogo nao abria.
  for ((i = 0; i < 50; i++)); do
    pgrep -f 'fliperos-setup/gui/fliperos-gui --serve' > /dev/null || break
    sleep 0.1
  done
  pkill -KILL -f 'fliperos-setup/gui/fliperos-gui --serve' 2> /dev/null || true
  systemctl restart getty@tty1.service
  echo "Done. To see the boot without text, reboot the cabinet."
else
  echo "== tty1 in use ($busy): not restarted. The new menu appears when it comes back."
fi
