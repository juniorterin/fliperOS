#!/usr/bin/env bash
# Auditoria so de leitura de uma ISO gerada: confere que o que foi para a
# imagem e o que esta no repositorio, sem montar nada nem tocar em hardware.
#
#   docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-vmtest bash tools/verify-iso.sh /w/output/fliperos-0.8.1.iso
#
# No container fliperos-vmtest (tools/Dockerfile.vmtest): o do build nao tem
# o lsinitramfs.
set -euo pipefail
iso=${1:?Uso: verify-iso.sh caminho.iso}
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
# FLIPEROS_VERIFY_DIR: onde extrair, para quem usa o resultado depois (o
# tools/release-publish.sh le de la a lista de arquivos e o squashfs).
work=${FLIPEROS_VERIFY_DIR:-$(mktemp -d /tmp/fliperos-verify.XXXXXX)}
mkdir -p "$work"
fail() { echo "FALHOU: $*" >&2; exit 1; }
echo "Audit extracted to $work"

xorriso -osirrox on -indev "$iso" \
  -extract /boot/limine/limine.conf "$work/limine.conf" \
  -extract /live/filesystem.squashfs "$work/filesystem.squashfs" \
  -extract /boot/vmlinuz "$work/vmlinuz" \
  -extract /boot/initrd.img "$work/initrd.img" > "$work/extract.log" 2>&1

# ── Menu de boot ──────────────────────────────────────────────
version=$(sed -n 's/^FLIPEROS_VERSION="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
common=$(sed -n 's/^BOOT_COMMON="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
sed -e "s|__VERSION__|$version|g" -e "s|__COMMON__|$common|g" "$src/config/limine.conf" > "$work/limine.expected"
cmp "$work/limine.expected" "$work/limine.conf" || fail "limine.conf differs from the template"
entries=$(grep -c '^/' "$work/limine.conf")
[[ $entries == 10 ]] || fail "boot menu with $entries entries (expected 10)"
grep -q '^timeout: 30$' "$work/limine.conf" || fail "boot menu timer is not 30 s"
echo "boot menu: 10 entries, 30 s, 15 kHz default"

# ── Kernel 15 kHz ─────────────────────────────────────────────
kernel=$(sed -n 's/^KERNEL_VERSION="\(.*\)"$/\1/p' "$src/fliperos-kernel.sh")
strings "$work/vmlinuz" | grep -q "^$kernel-15khz " || grep -aq "$kernel-15khz" "$work/vmlinuz" \
  || fail "the ISO kernel is not $kernel-15khz"
echo "kernel: $kernel-15khz"

# A listagem sai uma vez para arquivo: com "set -o pipefail", um "grep -q"
# num pipe fecha a entrada, o unsquashfs leva SIGPIPE e o pipeline falha.
unsquashfs -l "$work/filesystem.squashfs" > "$work/files.txt"
unsquashfs -lls "$work/filesystem.squashfs" > "$work/links.txt" 2> /dev/null
lsinitramfs "$work/initrd.img" > "$work/initrd.txt"
has() { grep -q "squashfs-root/$1\$" "$work/files.txt" || fail "ausente na ISO: $1"; }

# ── fliperos-setup igual ao do repositorio ────────────────────
( cd "$src/fliperos-setup" && find . -type f ) | while read -r file; do
  unsquashfs -cat "$work/filesystem.squashfs" "usr/local/lib/fliperos-setup/${file#./}" > "$work/f" \
    || fail "fliperos-setup: missing $file"
  cmp -s "$src/fliperos-setup/$file" "$work/f" || fail "fliperos-setup: $file differs from the repository"
done
grep -E 'usr/local/bin/fliperos-setup ->' "$work/links.txt" | grep -q '/usr/local/lib/fliperos-setup/fliperos-setup' \
  || fail "/usr/local/bin/fliperos-setup does not point to the setup"
echo "fliperos-setup: todos os arquivos conferem"

for pair in fliperos-video-check.py:usr/local/bin/fliperos-video-check \
  fliperos-limine-update.py:usr/local/sbin/fliperos-limine-update \
  config/fliperos-rebuild-edids:usr/local/sbin/fliperos-rebuild-edids \
  config/fliperos-session:opt/fliperos/bin/fliperos-session \
  config/fliperos-lxde:opt/fliperos/bin/fliperos-lxde \
  config/fliperos-sessions.conf:etc/fliperos/sessions.conf \
  config/fliperos-setup.desktop:usr/share/applications/fliperos-setup.desktop \
  config/vtrgb-dracula:etc/fliperos/vtrgb-dracula; do
  unsquashfs -cat "$work/filesystem.squashfs" "${pair#*:}" > "$work/f" || fail "ausente: ${pair#*:}"
  cmp -s "$src/${pair%%:*}" "$work/f" || fail "${pair#*:} differs from ${pair%%:*}"
done
echo "ferramentas, sessao, LXDE e paleta conferem"

# ── Programas que o setup usa ─────────────────────────────────
for path in usr/bin/gum usr/bin/antimicrox usr/bin/qjoypad usr/bin/jq usr/bin/espeak-ng usr/bin/con2fbmap \
  usr/local/bin/switchres usr/local/bin/grid usr/local/bin/geometry usr/local/bin/Skyscraper \
  usr/local/bin/limine usr/local/share/limine/limine-bios.sys usr/local/share/limine/BOOTX64.EFI \
  usr/bin/startlxde etc/switchres.ini; do
  has "$path"
done
echo "gum, antimicrox, qjoypad, switchres/grid/geometry, Skyscraper, Limine, LXDE presentes"

# O autoremove do fim de cada compilacao pode levar uma biblioteca que o
# binario usa (o Skyscraper ja perdeu a libQt6Xml assim): toda NEEDED dos
# programas compilados no build tem de existir na imagem.
for bin in usr/local/bin/switchres usr/local/bin/grid usr/local/bin/Skyscraper usr/bin/antimicrox; do
  unsquashfs -cat "$work/filesystem.squashfs" "$bin" > "$work/bin"
  for lib in $(readelf -d "$work/bin" | sed -n 's/.*(NEEDED).*\[\(.*\)\]$/\1/p'); do
    found=false
    for dir in usr/lib/x86_64-linux-gnu usr/lib usr/local/lib; do
      grep -qxF "squashfs-root/$dir/$lib" "$work/files.txt" && { found=true; break; }
    done
    $found || fail "/$bin needs $lib, which is not in the image"
  done
done
echo "libraries of the compiled programs present"

# ── EDIDs: um por preset e os de super resolucao, no rootfs e no initramfs ─
for edid in generic_15 arcade_15 arcade_25 arcade_31 ntsc pal vesa_480 generic_15_super_resp generic_15_super_resi; do
  has "usr/lib/firmware/edid/$edid.bin"
  grep -q "firmware/edid/$edid.bin\$" "$work/initrd.txt" || fail "EDID missing from the initramfs: $edid.bin"
done
unsquashfs -cat "$work/filesystem.squashfs" usr/lib/firmware/edid/generic_15_super_resi.bin > "$work/edid.bin"
edid-decode "$work/edid.bin" > "$work/edid.txt" 2>&1 || true
grep -q 'Switchres' "$work/edid.txt" || fail "the super res EDID is not from Switchres"
echo "Switchres EDIDs in the rootfs and in the initramfs"

# ── Splash, servicos, Limine do disco instalado ───────────────
grep -q 'themes/default.plymouth' "$work/files.txt" || fail "no default splash theme"
grep -q 'plymouth/themes' "$work/initrd.txt" || fail "splash theme missing from the initramfs"
grep -q 'multi-user.target.wants/ssh.service' "$work/files.txt" || fail "ssh.service not enabled"
grep -E 'etc/systemd/system/default.target ->' "$work/links.txt" | grep -q 'multi-user.target' \
  || fail "default.target does not point to multi-user"
for unit in lightdm.service display-manager.service; do
  grep -E "etc/systemd/system/$unit ->" "$work/links.txt" | grep -q '/dev/null' || fail "$unit not masked"
done
grep -E 'etc/vtrgb ->' "$work/links.txt" | grep -q 'alternatives/vtrgb' || fail "/etc/vtrgb is not the alternative"
for hook in etc/kernel/postinst.d etc/kernel/postrm.d etc/initramfs/post-update.d; do
  grep -E "$hook/zz-fliperos-limine ->" "$work/links.txt" | grep -q '/usr/local/sbin/fliperos-limine-update' \
    || fail "Limine hook missing: $hook"
done
echo "splash in the initramfs, ssh, no display manager, Dracula palette, Limine hooks"

# ── Latencia ──────────────────────────────────────────────────
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/fliperos-latency.service > "$work/f" \
  || fail "ausente: fliperos-latency.service"
cmp -s "$src/config/fliperos-latency.service" "$work/f" || fail "fliperos-latency.service differs from the repository"
grep -E 'multi-user.target.wants/fliperos-latency.service ->' "$work/links.txt" | grep -q 'fliperos-latency.service' \
  || fail "fliperos-latency.service not enabled"
for unit in apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
  grep -E "etc/systemd/system/$unit ->" "$work/links.txt" | grep -q '/dev/null' || fail "$unit not masked"
done
base=$(sed -n 's/^LATENCY_BASE_PARAMS="\(.*\)"$/\1/p' "$src/fliperos-setup/lib/latency.sh")
for param in $base; do
  grep -q -- " $param " <<< " $(grep -m1 'cmdline:' "$work/limine.conf") " || fail "media boot without $param"
done
echo "latency: service at boot, apt timers masked, $base"

# ── Teclas de volume ──────────────────────────────────────────
unsquashfs -cat "$work/filesystem.squashfs" etc/triggerhappy/triggers.d/fliperos-volume.conf > "$work/f" \
  || fail "missing: triggerhappy volume keys"
cmp -s "$src/config/fliperos-volume.triggers" "$work/f" || fail "volume keys differ from the repository"
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/triggerhappy.service.d/fliperos.conf > "$work/f" \
  || fail "missing: triggerhappy drop-in"
grep -q -- '--user' "$work/f" && fail "triggerhappy still runs as another user (no audio access)"
grep -q 'multi-user.target.wants/triggerhappy.service' "$work/files.txt" || fail "triggerhappy not enabled"
echo "volume keys: triggerhappy enabled, as root, with the FliperOS keys"

# ── Tema Dracula e emuladores no menu do LXDE ─────────────────
for path in usr/share/themes/Dracula/gtk-2.0/gtkrc usr/share/themes/Dracula/gtk-3.20/gtk.css \
  usr/share/themes/Dracula/openbox-3/themerc home/fliperos/.config/openbox/lxde-rc.xml \
  etc/fliperos/mame/ui.ini; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" home/fliperos/.config/openbox/lxde-rc.xml > "$work/f"
grep -q '<name>Dracula</name>' "$work/f" || fail "the LXDE Openbox does not use the Dracula theme"
for file in "$src"/config/applications/*.desktop; do
  has "usr/local/share/applications/${file##*/}"
  # Com o emulador na imagem, o icone tem de estar la tambem. Um nome sem
  # caminho (preferences-desktop-display) e do tema de icones.
  exe=$(sed -n 's/^TryExec=//p' "$file")
  icon=$(sed -n 's/^Icon=//p' "$file")
  if [[ $icon == /* ]] && grep -q "squashfs-root$exe\$" "$work/files.txt"; then
    has "${icon#/}"
  fi
done
echo "Dracula theme (GTK, Openbox, GroovyMAME) and emulators in the LXDE menu"

# ── Modo de video dos emuladores (640x240 nos de 480i) ────────
for path in etc/fliperos/emulator-modes.conf opt/fliperos/bin/fliperos-ini-set opt/fliperos/bin/fliperos-x11-run; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/emulator-modes.conf > "$work/f"
cmp -s "$src/config/fliperos-emulator-modes.conf" "$work/f" || fail "emulator-modes.conf differs from the repository"
echo "modos: tabela por emulador e fliperos-x11-run --mode"

# ── Emuladores e lojas novos (so o que foi incluido no build) ─
present() { grep -q "squashfs-root/$1\$" "$work/files.txt"; }
if present usr/local/bin/hypseus.bin; then
  has usr/local/bin/hypseus
  has home/fliperos/roms/hypseus/fonts
  grep -E 'home/fliperos/.hypseus ->' "$work/links.txt" | grep -q '/opt/fliperos/roms/hypseus' \
    || fail "/home/fliperos/.hypseus does not point to /opt/fliperos/roms/hypseus"
  echo "Hypseus Singe: binary, scripts and home in the collection"
fi
if present usr/local/lib/openbor/OpenBOR; then
  has usr/local/bin/openbor
  has home/fliperos/roms/openbor/Paks
  echo "OpenBOR: wrapper and Paks in the collection"
fi
if present usr/local/bin/dolphin-emu; then
  has usr/local/share/pixmaps/dolphin-emu.png
  present usr/local/share/applications/dolphin-emu.desktop && fail "Dolphin's own shortcut was not removed"
  echo "Dolphin: without its own shortcut (opens through fliperos-launch)"
fi
# Wine, Steam e Heroic: pelo Setup > Extras (config/fliperos-extras), fora
# da imagem para a ISO caber num arquivo do GitHub.
for path in usr/local/bin/fliperos-model2 opt/fliperos/model2/roms opt/fliperos/bin/fliperos-extras; do
  has "$path"
done
for path in usr/bin/wine usr/games/steam opt/Heroic/heroic; do
  present "$path" && fail "/$path came in the image (it should come through Setup > Extras)"
done
unsquashfs -cat "$work/filesystem.squashfs" var/lib/dpkg/arch > "$work/f" 2> /dev/null
grep -qx i386 "$work/f" || fail "the i386 architecture is not enabled (32-bit Wine would not install)"
echo "Wine, Steam and Heroic: out of the image, with fliperos-extras and the i386 architecture"
# Imagem enxuta (slim_rootfs_chroot): sem cache do apt, sem -dev e sem o
# firmware fora do escopo.
grep -qE 'squashfs-root/var/cache/apt/archives/[^/]+\.deb$' "$work/files.txt" && fail "the image carries .deb files in the apt cache"
grep -qE 'squashfs-root/usr/lib/firmware/(nvidia|mellanox|qcom)/' "$work/files.txt" && fail "the image carries out-of-scope firmware"
grep -q 'squashfs-root/usr/lib/firmware/amdgpu/' "$work/files.txt" || fail "the image lost the amdgpu firmware"
unsquashfs -cat "$work/filesystem.squashfs" var/lib/dpkg/status > "$work/f"
awk '/^Package: / { p = $2 } /^Status: install ok installed/ { print p }' "$work/f" \
  | grep -xE 'qt6-base-dev|libsdl2-dev|libavcodec-dev|libdrm-dev|libcurl4-openssl-dev|cmake|ninja-build' \
  > "$work/dev.txt" || true
[[ -s $work/dev.txt ]] && fail "build packages in the image: $(paste -sd' ' "$work/dev.txt")"
echo "slim image: no cached .deb, no build -dev packages and no out-of-scope firmware"
# Fightcade 2: o que o baixa e abre vem na imagem; o programa, nao.
for path in opt/fliperos/bin/fliperos-fightcade etc/fliperos/openbox-fightcade.xml; do
  has "$path"
done
grep -q '^fightcade|kms|/opt/fliperos/fightcade/fightcade|fetch:fliperos-fightcade|' "$src/config/fliperos-sessions.conf" ||
  fail "the sessions table does not have Fightcade"
present opt/fliperos/fightcade/Fightcade2.sh && fail "Fightcade came inside the image (it is closed source: download only)"
echo "Fightcade 2: launcher in the image, program by download (Setup > Frontend)"
# ── RetroArch: cores de fabrica e pasta do Online Updater ─────
if grep -q 'squashfs-root/usr/local/bin/retroarch$' "$work/files.txt"; then
  for core in fceumm snes9x genesis_plus_gx mgba pcsx_rearmed mame2010; do
    has "opt/fliperos/retroarch/cores/${core}_libretro.so"
  done
  grep -q 'squashfs-root/opt/fliperos/retroarch/info/snes9x_libretro.info$' "$work/files.txt" \
    || fail "RetroArch without the cores' .info files"
  unsquashfs -lln "$work/filesystem.squashfs" > "$work/numeric.txt" 2> /dev/null
  grep -E ' 1000/1000 .* squashfs-root/opt/fliperos/retroarch/cores$' "$work/numeric.txt" > /dev/null \
    || fail "the RetroArch cores folder is not the user's (the Core Downloader cannot write)"
  # Com o _FORTIFY_SOURCE do gcc do Ubuntu o mame2010 aborta ao abrir os jogos
  # de Namco System 12 (build_core em fliperos-mkiso.sh).
  unsquashfs -cat "$work/filesystem.squashfs" opt/fliperos/retroarch/cores/mame2010_libretro.so > "$work/f" \
    || fail "could not read the mame2010 core"
  symbols=$(readelf -Ws --dyn-syms "$work/f")
  [[ $symbols != *__strcat_chk* ]] || fail "the mame2010 core was compiled with _FORTIFY_SOURCE"
  echo "RetroArch: 6 factory cores, .info files and a user folder for the Core Downloader"
fi

# ── GroovyMAME: release, atalho e arquivos da tag ─────────────
if present usr/local/libexec/groovymame; then
  unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/groovymame > "$work/f" \
    || fail "missing: /usr/local/bin/groovymame (the shortcut)"
  cmp -s "$src/config/fliperos-groovymame" "$work/f" || fail "/usr/local/bin/groovymame differs from config/fliperos-groovymame"
  for path in usr/local/share/groovymame/fonts/uismall.bdf usr/local/share/groovymame/plugins/hiscore/init.lua \
    usr/local/share/groovymame/bgfx/chains/default.json usr/local/share/groovymame/hash/nes.xml; do
    has "$path"
  done
  # O mame.ini da imagem e o do -createconfig (fliperos-mame-ini): cada
  # opcao do config/mame.ini tem de estar nele com o mesmo valor.
  unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/mame/mame.ini > "$work/f"
  (($(wc -l < "$work/f") > 100)) || fail "/etc/fliperos/mame/mame.ini is not the full -createconfig one"
  while read -r key value; do
    got=$(awk -v k="$key" '$1 == k { sub("^[ \t]*" k "[ \t]+", ""); print; exit }' "$work/f")
    [[ $got == "$value" ]] || fail "image mame.ini: $key is '$got', config/mame.ini says '$value'"
  done < <(grep -vE '^[[:space:]]*(#|$)' "$src/config/mame.ini")
  echo "GroovyMAME: release in /usr/local/libexec, groovymame shortcut, plugins/font/bgfx/hash and GroovyArcade's mame.ini"
fi

# ── MAME ROM Cleaner: o programa e o XML do MAME 2010 ─────────
unsquashfs -cat "$work/filesystem.squashfs" opt/fliperos/bin/fliperos-romclean > "$work/f" \
  || fail "ausente: /opt/fliperos/bin/fliperos-romclean"
cmp -s "$src/config/fliperos-romclean" "$work/f" || fail "fliperos-romclean differs from config/fliperos-romclean"
unsquashfs -cat "$work/filesystem.squashfs" usr/local/share/fliperos/mame2010.xml.xz > "$work/f" \
  || fail "ausente: /usr/local/share/fliperos/mame2010.xml.xz"
got=$(python3 -c 'import hashlib, lzma, sys; print(hashlib.sha256(lzma.open(sys.argv[1]).read()).hexdigest())' \
  "$work/f")
[[ $got == "$(sed -n "s/^MAME2010_SHA256 = '\(.*\)'$/\1/p" "$src/config/fliperos-romclean")" ]] \
  || fail "the image's mame2010.xml.xz is not the pinned XML"
# A pasta da rede (cifs-utils, smbclient) e as pastas de dados e de cache.
for path in usr/sbin/mount.cifs usr/bin/smbclient usr/local/lib/fliperos-setup/lib/netshare.sh \
  usr/local/share/fliperos/romclean var/cache/fliperos opt/fliperos/bin/fliperos-freeroms; do
  has "$path"
done
# O gum e o compilado com patches/gum (o Espaco marcando nas listas de
# marcar e o 0003; o build falha se um patch nao aplica), nao o do .deb.
unsquashfs -cat "$work/filesystem.squashfs" usr/bin/gum > "$work/f" || fail "ausente: /usr/bin/gum"
grep -qa -- '-fliperos' "$work/f" || fail "/usr/bin/gum is the .deb one, without the FliperOS patches"
echo "ROM cleaner: fliperos-romclean, the MAME 2010 XML (0.139) and the network folder (mount.cifs, smbclient)"

# ── Downloader: o programa, o servico e o transmission-daemon ─
for name in fliperos-downloader:opt/fliperos/bin/fliperos-downloader \
  fliperos-transmission.service:etc/systemd/system/fliperos-transmission.service \
  fliperos-downloader-magnets:usr/local/share/fliperos/downloader-magnets; do
  unsquashfs -cat "$work/filesystem.squashfs" "${name#*:}" > "$work/f" || fail "ausente: /${name#*:}"
  cmp -s "$src/config/${name%%:*}" "$work/f" || fail "${name%%:*} differs from the repository"
done
for path in usr/bin/transmission-daemon usr/local/lib/fliperos-setup/lib/downloader.sh \
  usr/local/lib/fliperos-setup/screens/downloader.sh; do
  has "$path"
done
grep -E 'etc/systemd/system/transmission-daemon.service ->' "$work/links.txt" | grep -q '/dev/null' \
  || fail "the stock transmission-daemon.service is not masked"
echo "Downloader: fliperos-downloader, the default magnet links, fliperos-transmission.service and transmission-daemon (stock unit masked)"

# ── Updates sem ISO nova: o programa, o manifesto e o nivel ───
unsquashfs -cat "$work/filesystem.squashfs" opt/fliperos/bin/fliperos-update > "$work/f" \
  || fail "ausente: /opt/fliperos/bin/fliperos-update"
cmp -s "$src/config/fliperos-update" "$work/f" || fail "fliperos-update differs from the repository"
unsquashfs -cat "$work/filesystem.squashfs" var/lib/fliperos/update/manifest > "$work/manifest" \
  || fail "ausente: /var/lib/fliperos/update/manifest"
grep -q $'^usr/local/lib/fliperos-setup/fliperos-setup\t' "$work/manifest" \
  || fail "the update manifest does not have the setup"
level=$(unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/patch-level) || fail "ausente: /etc/fliperos/patch-level"
expected=$(awk -F'\t' '/^[0-9]/ { n = $1 } END { print n + 0 }' "$src/updates/index")
[[ $level == "$expected" ]] || fail "patch-level $level (the updates/index has $expected)"
grep -q 'update_pending' "$src/config/fliperos-tty1" || fail "fliperos-tty1 does not check for updates"
echo "Updates: fliperos-update, manifest ($(wc -l < "$work/manifest") files) and level $level"

# ── Terminal: zsh com Oh My Zsh e o tema Dracula ──────────────
for path in usr/bin/zsh usr/local/share/oh-my-zsh/oh-my-zsh.sh \
  usr/local/share/oh-my-zsh/custom/themes/dracula.zsh-theme \
  usr/local/share/oh-my-zsh/custom/themes/lib/async.zsh opt/fliperos/bin/fliperos-tty1; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" home/fliperos/.zshrc > "$work/f" || fail "ausente: /home/fliperos/.zshrc"
cmp -s "$src/config/zshrc" "$work/f" || fail "/home/fliperos/.zshrc differs from config/zshrc"
unsquashfs -cat "$work/filesystem.squashfs" etc/passwd > "$work/f"
grep -q '^fliperos:.*:/usr/bin/zsh$' "$work/f" || fail "the fliperos user's shell is not zsh"
echo "terminal: user zsh with Oh My Zsh and the Dracula theme"

# ── Acervo em ~/roms ───────────────────────────────────────────
grep -E 'opt/fliperos/roms ->' "$work/links.txt" | grep -q '/home/fliperos/roms' \
  || fail "/opt/fliperos/roms does not point to /home/fliperos/roms"
for path in home/fliperos/roms/mame home/fliperos/roms/ps2/_info.txt etc/samba/smb.conf \
  opt/fliperos/bin/fliperos-roms opt/fliperos/bin/fliperos-calibrate; do
  has "$path"
done
if present opt/fliperos/retroarch/info/snes9x_libretro.info; then
  has home/fliperos/roms/retroarch/snes9x/_info.txt
fi
echo "collection: ~/roms with one folder per emulator and per RetroArch core"

# ── Terminal do desktop: so o Alacritty ───────────────────────
# O lxterminal e o xterm nao desenhavam as bordas do Gum; uma dependencia
# nova nao pode traze-los de volta (o Steam trazia: STEAM_PACKAGES em
# config/fliperos-extras).
has usr/bin/alacritty
has home/fliperos/.config/alacritty/alacritty.toml
for bin in usr/bin/lxterminal usr/bin/xterm usr/bin/lxterm usr/bin/uxterm; do
  present "$bin" && fail "terminal que devia ter saido: /$bin"
done
echo "desktop terminal: Alacritty (no lxterminal or xterm)"

# ── App Store: GNOME Software + Flathub ───────────────────────
for path in usr/bin/gnome-software usr/bin/flatpak usr/share/glib-2.0/schemas/90_fliperos-software.gschema.override \
  usr/local/share/applications/org.gnome.Software.desktop; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" var/lib/flatpak/repo/config > "$work/f" 2> /dev/null || true
grep -q '^\[remote "flathub"\]' "$work/f" || fail "Flathub is not among the Flatpak sources"
present 'usr/lib/x86_64-linux-gnu/gnome-software/plugins-.*/libgs_plugin_snap.so' && fail "App Store with the snap plugin"
echo "App Store: GNOME Software with Flatpak and Flathub, no automatic updates"

xorriso -indev "$iso" -report_el_torito plain > "$work/boot.txt" 2>&1
grep -q 'BIOS' "$work/boot.txt" || fail "no BIOS boot"
grep -q 'UEFI' "$work/boot.txt" || fail "no UEFI boot"
echo "ISO conferida: boot BIOS e UEFI."
sha256sum "$iso"
