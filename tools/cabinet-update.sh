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

if compgen -G "$src/repo/*.deb" > /dev/null; then
  echo "== Repositorio local (/opt/fliperos/repo)"
  rm -rf /opt/fliperos/repo
  mkdir -p /opt/fliperos/repo
  cp "$src"/repo/* /opt/fliperos/repo/
  chmod -R a+rX /opt/fliperos/repo
  echo "deb [trusted=yes] file:/opt/fliperos/repo ./" > /etc/apt/sources.list.d/fliperos.list
fi

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
packages=(usbutils systemd-timesyncd)
[[ -f /etc/apt/sources.list.d/fliperos.list ]] && packages+=(fliperos-attractplus)
apt-get update -qq || echo "aviso: apt-get update com erros (sem rede?)"
DEBIAN_FRONTEND=noninteractive apt-get install -y -q --no-install-recommends "${packages[@]}" ||
  echo "aviso: nao instalou ${packages[*]}"

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
)
sed -n 's/^FLIPEROS_CMDLINE=//p' /etc/default/fliperos-boot

echo "== Servicos"
systemctl daemon-reload
systemctl enable --now systemd-timesyncd.service > /dev/null 2>&1 || true
systemctl enable fliperos-padkeys.service > /dev/null 2>&1 || true
systemctl restart fliperos-padkeys.service
echo "fliperos-padkeys: $(systemctl is-active fliperos-padkeys.service)"

echo "== Reiniciando o tty1 no fluxo novo"
systemctl restart getty@tty1.service
echo "Pronto. Para ver o boot sem texto, reinicie o gabinete."
