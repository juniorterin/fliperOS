#!/usr/bin/env bash
# Update 6: o splash padrao passa a ser o fliperos-text (o tema de terminal
# animado). So troca quem ainda esta no padrao antigo (fliperos) sem ter
# escolhido um tema no Setup > Splash screen.
set -euo pipefail
themes=/usr/share/plymouth/themes
bundled=/usr/share/fliperos/splashscreen
home_splash=/home/fliperos/splashscreen
file=$themes/fliperos-text/fliperos-text.plymouth
[[ -f $file ]] || exit 0

# As copias em ~/splashscreen de antes do .bundled (config/fliperos-roms):
# as iguais as da imagem ganham o .bundled e passam a acompanhar a imagem;
# o fliperos-text antigo (sem a JetBrains Mono) da lugar ao novo.
splash_sum() { (cd "$1" && find . -type f ! -name .bundled -exec cksum {} + | sort | cksum); }
for theme in "$bundled"/*/; do
  name=$(basename "$theme")
  dest=$home_splash/$name
  [[ -d $dest && ! -e $dest/.bundled ]] || continue
  if [[ $name == fliperos-text ]] && ! grep -q 'JetBrains Mono' "$dest/fliperos-text.script" 2> /dev/null; then
    rm -rf "$dest"
    cp -r "${theme%/}" "$home_splash/"
  fi
  [[ $(splash_sum "$dest") == "$(splash_sum "$theme")" ]] || continue
  splash_sum "$dest" > "$dest/.bundled"
  chown -R fliperos:fliperos "$dest"
done

[[ $(readlink -f "$themes/default.plymouth" 2> /dev/null) == "$themes/fliperos/fliperos.plymouth" ]] || exit 0
grep -q '^splash=' /etc/fliperos/fliperos.conf 2> /dev/null && exit 0
echo "== Boot splash: fliperos-text"
update-alternatives --install "$themes/default.plymouth" default.plymouth "$file" 100 > /dev/null
update-alternatives --set default.plymouth "$file" > /dev/null
update-initramfs -u > /dev/null || echo "warning: update-initramfs failed; the old splash stays until it runs"
