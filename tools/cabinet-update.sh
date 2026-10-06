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
[[ $EUID -eq 0 ]] || { echo "Rode como root (sudo)." >&2; exit 1; }
[[ -f /etc/fliperos/installed ]] || { echo "Isto nao e um FliperOS instalado." >&2; exit 1; }

backup=/root/fliperos-backup-$(date +%Y%m%d-%H%M%S).tgz
tar czf "$backup" --ignore-failed-read \
  /usr/local/lib/fliperos-setup /opt/fliperos/bin /usr/local/sbin/fliperos-limine-update \
  /etc/default/fliperos-boot /etc/systemd/system/getty@tty1.service.d /etc/NetworkManager/conf.d \
  /etc/resolv.conf /home/fliperos/.config /home/fliperos/.zshrc /boot/efi/limine/limine.conf 2> /dev/null || true
echo "== Copia de seguranca: $backup"

echo "== Arquivos do FliperOS (fliperos-rootfs.sh)"
bash "$src/fliperos-rootfs.sh" /
install -Dm755 "$src/fliperos-limine-update.py" /usr/local/sbin/fliperos-limine-update

echo "== Login automatico sem texto"
cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << 'UNIT'
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin fliperos --skip-login --noissue %I $TERM
UNIT

echo "== DNS pelo NetworkManager"
nmcli general reload conf > /dev/null && nmcli general reload dns-full > /dev/null || true
sleep 2
grep nameserver /etc/resolv.conf || true

# O indice do repositorio local antes e depois: mudou, o apt tem de reler.
repo_index() { cat /opt/fliperos/repo/Packages* 2> /dev/null | cksum; }
repo_before=$(repo_index)
if compgen -G "$src/repo/*.deb" > /dev/null; then
  echo "== Repositorio local (/opt/fliperos/repo)"
  rm -rf /opt/fliperos/repo
  mkdir -p /opt/fliperos/repo
  cp "$src"/repo/* /opt/fliperos/repo/
  chmod -R a+rX /opt/fliperos/repo
  echo "deb [trusted=yes] file:/opt/fliperos/repo ./" > /etc/apt/sources.list.d/fliperos.list
fi
repo_after=$(repo_index)

echo "== Relogio"
# Sem servico de hora (imagens ate o commit 11f715a), vale o relogio da BIOS,
# que pode estar meses errado: o apt recusa os repositorios ("not valid
# yet"). Acerta pela hora do servidor do Ubuntu antes do apt.
if ! systemctl is-active --quiet systemd-timesyncd; then
  now=$(curl -sI -m 10 http://archive.ubuntu.com/ubuntu/ | sed -n 's/^[Dd]ate: //p' | tr -d '\r')
  [[ -n $now ]] && date -s "$now" > /dev/null && echo "acertado pela rede"
fi
date

echo "== Pacotes novos"
# Os que a imagem ganhou depois da instalacao (fliperos-mkiso.sh).
packages=(usbutils systemd-timesyncd gnome-software gnome-software-plugin-flatpak flatpak xdg-desktop-portal-gtk
  alacritty libsdl2-ttf-2.0-0 libqt6core6t64 libqt6gui6t64 libqt6widgets6t64 cifs-utils smbclient
  falkon transmission-gtk zenity
  libnss3 libxss1 libxtst6 libcups2t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 libgtk-3-0t64 libasound2t64 xdg-utils)
[[ -f /etc/apt/sources.list.d/fliperos.list ]] && packages+=(fliperos-attractplus)
# O OpenGL de 32 bits do Wine (os emuladores do Fightcade), onde ha Wine.
dpkg --print-foreign-architectures | grep -qx i386 && packages+=(libgl1:i386 libgl1-mesa-dri:i386 libglx-mesa0:i386)
# So mexe no apt se falta algum pacote ou se o repositorio local mudou: o
# apt-get segura a trava dos pacotes, e quem estivesse instalando um
# frontend pelo Setup naquela hora recebia "Impossivel criar acesso
# exclusivo". Quando mexe, espera a trava de quem estiver com ela.
missing=()
for p in "${packages[@]}"; do
  dpkg -s "$p" > /dev/null 2>&1 || missing+=("$p")
done
if ((${#missing[@]})) || [[ $repo_before != "$repo_after" ]]; then
  apt-get update -qq || echo "aviso: apt-get update com erros (sem rede, ou outro programa com a trava?)"
  DEBIAN_FRONTEND=noninteractive apt-get -o DPkg::Lock::Timeout=120 install -y -q --no-install-recommends \
    "${packages[@]}" || echo "aviso: nao instalou ${packages[*]}"
else
  echo "todos instalados e o repositorio local nao mudou: o apt nao foi usado"
fi
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo ||
  echo "aviso: Flathub nao foi adicionado"
# O override da App Store (fliperos-rootfs.sh) pode ter chegado depois do
# pacote.
glib-compile-schemas /usr/share/glib-2.0/schemas 2> /dev/null || true

echo "== Terminais: so o Alacritty"
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
  echo "lxterminal/xterm: $(dpkg -l lxterminal xterm 2> /dev/null | grep -c '^ii') instalados"
  echo "x-terminal-emulator: $(readlink -f /usr/bin/x-terminal-emulator)"
  echo "autoremove levaria: $(apt-get autoremove -s 2> /dev/null | grep -c '^Remv') pacotes"
else
  echo "aviso: Alacritty nao instalou; os terminais antigos ficam"
fi

echo "== Linha do kernel (boot direto no Plymouth)"
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
  boot_apply || { echo "boot_apply falhou (ver /var/log/fliperos-setup.log)"; exit 1; }
  # O fliperos-rootfs.sh reinstalou o retroarch.cfg da imagem: o que o setup
  # decide por maquina volta (largura do CRT SwitchRes, modo de latencia).
  video_retroarch_super
  video_mame_aspect
  video_mame_monitor
  latency_emulators "$(latency_mode)"
  grep -E '^(aspect|monitor) ' "$MAME_INI"
  grep -E '^crt_switch_resolution_super' "$RETROARCH_CFG"
)

echo "== Console calado (kernel.printk do fliperos-rootfs.sh) ja neste boot"
sysctl -q -p /etc/sysctl.d/99-fliperos-console.conf && cat /proc/sys/kernel/printk

echo "== Som HDA sempre ligado (power_save do fliperos-rootfs.sh) ja neste boot"
if [[ -d /sys/module/snd_hda_intel/parameters ]]; then
  echo 0 > /sys/module/snd_hda_intel/parameters/power_save
  echo N > /sys/module/snd_hda_intel/parameters/power_save_controller
  echo "power_save=$(cat /sys/module/snd_hda_intel/parameters/power_save)"
fi

echo "== Botoes do Setup > Joysticks > Button mapping em todos os emuladores"
if [[ -f /etc/fliperos/buttons.map ]]; then
  /opt/fliperos/bin/fliperos-buttons save /etc/fliperos/buttons.map | sed 's/^/gravado: /'
else
  echo "sem mapa (Setup > Joysticks > Button mapping)"
fi

echo "== XML do MAME 2010 (ROM cleaner)"
/opt/fliperos/bin/fliperos-romclean fetch-mame2010 /usr/local/share/fliperos/mame2010.xml.xz || echo "falhou (sem rede?)"

echo "== Pastas em ~ (roms, bios, media, config)"
runuser -u fliperos -- /opt/fliperos/bin/fliperos-roms
ls -ld /opt/fliperos/roms /opt/fliperos/bios
echo "pastas de core: $(find /home/fliperos/roms/retroarch -mindepth 1 -maxdepth 1 -type d | wc -l)"
echo "config: $(find /home/fliperos/config -mindepth 1 -maxdepth 1 -type l -printf '%f ')"

echo "== Arte do Scraper em ~/media"
(
  set +eu
  for f in "$lib"/*.sh; do
    # shellcheck source=/dev/null
    . "$f"
  done
  # A de antes (~/.mame/scraped, ~/.attract/scraped, <pasta>/media) vai para
  # ~/media, e o frontend padrao passa a ler de la.
  scraper_media_migrate
  frontends_configure "$(launcher_current)"
  # A configuracao de 240p do ES-DE e do Pegasus instalados (lib/frontends.sh).
  frontends_240p
  for t in $MEDIA_TYPES; do
    echo "$t: $(find "$MEDIA_DIR/$t" -mindepth 2 -type f | wc -l) arquivo(s)"
  done
)
systemctl restart smbd 2> /dev/null || true
udevadm control --reload 2> /dev/null || true
sed -n 's/^FLIPEROS_CMDLINE=//p' /etc/default/fliperos-boot

echo "== Servicos"
systemctl daemon-reload
systemctl enable --now systemd-timesyncd.service > /dev/null 2>&1 || true
# Mapeamentos de controle do SDL dos controles ligados agora (o servico tambem
# roda no boot e a cada controle ligado).
systemctl start fliperos-controllers.service 2> /dev/null || true
echo "mapeamentos do SDL: $(grep -vc '^#' /var/lib/fliperos/gamecontrollerdb.txt 2> /dev/null || echo 0)"
systemctl enable fliperos-padkeys.service > /dev/null 2>&1 || true
systemctl restart fliperos-padkeys.service
echo "fliperos-padkeys: $(systemctl is-active fliperos-padkeys.service)"

# So reinicia o tty1 se nele estiver o menu (login, shell, sudo): um jogo,
# frontend ou o desktop aberto agora seria fechado no meio.
# Sem nada alem do menu, o grep -v nao acha nada e sai com 1: com pipefail
# isso parava o script aqui.
busy=$(pgrep -l -t tty1 | awk '{ print $2 }' | { grep -vxE 'login|zsh|bash|sudo|fliperos-tty1' || true; } |
  sort -u | tr '\n' ' ')
if [[ -z $busy ]]; then
  echo "== Reiniciando o tty1 no fluxo novo"
  systemctl restart getty@tty1.service
  echo "Pronto. Para ver o boot sem texto, reinicie o gabinete."
else
  echo "== tty1 em uso ($busy): nao reiniciado. O menu novo aparece quando ele voltar."
fi
