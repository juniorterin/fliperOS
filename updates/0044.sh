#!/usr/bin/env bash
# Update 44: o PCSX2x6 (Namco System 246/256) nos gabinetes que ja estao
# instalados. Na ISO ele vem do build_pcsx2x6_chroot; aqui o mesmo AppImage
# (versao e sha256 fixados no fliperos-mkiso.sh) e extraido em /opt/pcsx2x6,
# com o comando pcsx2x6 e o icone. Quem ja tem essa versao nao baixa de novo.
set -euo pipefail
src=${FLIPEROS_UPDATE_SRC:-${SRC:-$(cd "$(dirname "$0")/.." && pwd)}}
mkiso=$src/fliperos-mkiso.sh
version=$(sed -n 's/^PCSX2X6_VERSION="\([^"]*\)".*/\1/p' "$mkiso" | head -n 1)
sha=$(sed -n 's/^PCSX2X6_SHA256="\([0-9a-f]\{64\}\)".*/\1/p' "$mkiso" | head -n 1)
[[ -n $version && -n $sha ]] || {
  echo "PCSX2x6: version/sha256 not found in $mkiso"
  exit 1
}
versions=/usr/local/share/fliperos/emulator-versions.d
[[ -x /opt/pcsx2x6/AppRun && -x /usr/local/bin/pcsx2x6 && $(cat "$versions/pcsx2x6" 2> /dev/null) == "$version" ]] && exit 0

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
image=$work/pcsx2x6.AppImage
curl -sSfL --retry 3 --max-time 900 -o "$image" \
  "https://github.com/PS2Homebrew-arcade/pcsx2x6/releases/download/v$version/pcsx2x6-v$version-linux-appimage-x64-Qt.AppImage" || {
  echo "PCSX2x6: download failed"
  exit 1
}
echo "$sha  $image" | sha256sum -c --quiet - || {
  echo "PCSX2x6: the download does not match the pinned sha256"
  exit 1
}
chmod +x "$image"
(cd "$work" && "$image" --appimage-extract > /dev/null) || {
  echo "PCSX2x6: the AppImage did not extract"
  exit 1
}
rm -rf /opt/pcsx2x6.new
mv "$work/squashfs-root" /opt/pcsx2x6.new
chmod -R a+rX /opt/pcsx2x6.new
rm -rf /opt/pcsx2x6
mv /opt/pcsx2x6.new /opt/pcsx2x6
printf '#!/bin/sh\nexec /opt/pcsx2x6/AppRun "$@"\n' > /usr/local/bin/pcsx2x6
chmod 755 /usr/local/bin/pcsx2x6
install -Dm644 /opt/pcsx2x6/PCSX2x6.png /usr/local/share/pixmaps/pcsx2x6.png
mkdir -p "$versions"
echo "$version" > "$versions/pcsx2x6"
echo "PCSX2x6 $version installed in /opt/pcsx2x6"
