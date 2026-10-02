#!/usr/bin/env bash
# Auditoria so de leitura de uma ISO gerada: confere que o que foi para a
# imagem e o que esta no repositorio, sem montar nada nem tocar em hardware.
#
#   tools/verify-iso.sh caminho.iso      (no container do build)
set -euo pipefail
iso=${1:?Uso: verify-iso.sh caminho.iso}
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
work=$(mktemp -d /tmp/fliperos-verify.XXXXXX)
fail() { echo "FALHOU: $*" >&2; exit 1; }
echo "Auditoria extraida em $work"

xorriso -osirrox on -indev "$iso" \
  -extract /boot/limine/limine.conf "$work/limine.conf" \
  -extract /live/filesystem.squashfs "$work/filesystem.squashfs" \
  -extract /boot/vmlinuz "$work/vmlinuz" \
  -extract /boot/initrd.img "$work/initrd.img" > "$work/extract.log" 2>&1

# ── Menu de boot ──────────────────────────────────────────────
version=$(sed -n 's/^FLIPEROS_VERSION="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
common=$(sed -n 's/^BOOT_COMMON="\(.*\)"$/\1/p' "$src/fliperos-mkiso.sh")
sed -e "s|__VERSION__|$version|g" -e "s|__COMMON__|$common|g" "$src/config/limine.conf" > "$work/limine.expected"
cmp "$work/limine.expected" "$work/limine.conf" || fail "limine.conf difere do template"
entries=$(grep -c '^/' "$work/limine.conf")
[[ $entries == 10 ]] || fail "menu de boot com $entries entradas (esperado 10)"
grep -q '^timeout: 30$' "$work/limine.conf" || fail "timer do menu de boot nao e 30 s"
echo "menu de boot: 10 entradas, 30 s, 15 kHz padrao"

# ── Kernel 15 kHz ─────────────────────────────────────────────
kernel=$(sed -n 's/^KERNEL_VERSION="\(.*\)"$/\1/p' "$src/fliperos-kernel.sh")
strings "$work/vmlinuz" | grep -q "^$kernel-15khz " || grep -aq "$kernel-15khz" "$work/vmlinuz" \
  || fail "o kernel da ISO nao e o $kernel-15khz"
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
    || fail "fliperos-setup: falta $file"
  cmp -s "$src/fliperos-setup/$file" "$work/f" || fail "fliperos-setup: $file difere do repositorio"
done
grep -E 'usr/local/bin/fliperos-setup ->' "$work/links.txt" | grep -q '/usr/local/lib/fliperos-setup/fliperos-setup' \
  || fail "/usr/local/bin/fliperos-setup nao aponta para o setup"
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
  cmp -s "$src/${pair%%:*}" "$work/f" || fail "${pair#*:} difere de ${pair%%:*}"
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
    $found || fail "/$bin precisa de $lib, que nao esta na imagem"
  done
done
echo "bibliotecas dos programas compilados presentes"

# ── EDIDs: um por preset e os de super resolucao, no rootfs e no initramfs ─
for edid in generic_15 arcade_15 arcade_25 arcade_31 ntsc pal vesa_480 generic_15_super_resp generic_15_super_resi; do
  has "usr/lib/firmware/edid/$edid.bin"
  grep -q "firmware/edid/$edid.bin\$" "$work/initrd.txt" || fail "EDID fora do initramfs: $edid.bin"
done
unsquashfs -cat "$work/filesystem.squashfs" usr/lib/firmware/edid/generic_15_super_resi.bin > "$work/edid.bin"
edid-decode "$work/edid.bin" > "$work/edid.txt" 2>&1 || true
grep -q 'Switchres' "$work/edid.txt" || fail "o EDID super res nao e do Switchres"
echo "EDIDs do Switchres no rootfs e no initramfs"

# ── Splash, servicos, Limine do disco instalado ───────────────
grep -q 'themes/default.plymouth' "$work/files.txt" || fail "sem tema de splash padrao"
grep -q 'plymouth/themes' "$work/initrd.txt" || fail "tema de splash fora do initramfs"
grep -q 'multi-user.target.wants/ssh.service' "$work/files.txt" || fail "ssh.service nao habilitado"
grep -E 'etc/systemd/system/default.target ->' "$work/links.txt" | grep -q 'multi-user.target' \
  || fail "default.target nao aponta para multi-user"
for unit in lightdm.service display-manager.service; do
  grep -E "etc/systemd/system/$unit ->" "$work/links.txt" | grep -q '/dev/null' || fail "$unit nao mascarado"
done
grep -E 'etc/vtrgb ->' "$work/links.txt" | grep -q 'alternatives/vtrgb' || fail "/etc/vtrgb nao e a alternativa"
for hook in etc/kernel/postinst.d etc/kernel/postrm.d etc/initramfs/post-update.d; do
  grep -E "$hook/zz-fliperos-limine ->" "$work/links.txt" | grep -q '/usr/local/sbin/fliperos-limine-update' \
    || fail "hook do Limine ausente: $hook"
done
echo "splash no initramfs, ssh, sem display manager, paleta Dracula, hooks do Limine"

# ── Latencia ──────────────────────────────────────────────────
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/fliperos-latency.service > "$work/f" \
  || fail "ausente: fliperos-latency.service"
cmp -s "$src/config/fliperos-latency.service" "$work/f" || fail "fliperos-latency.service difere do repositorio"
grep -E 'multi-user.target.wants/fliperos-latency.service ->' "$work/links.txt" | grep -q 'fliperos-latency.service' \
  || fail "fliperos-latency.service nao habilitado"
for unit in apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
  grep -E "etc/systemd/system/$unit ->" "$work/links.txt" | grep -q '/dev/null' || fail "$unit nao mascarado"
done
base=$(sed -n 's/^LATENCY_BASE_PARAMS="\(.*\)"$/\1/p' "$src/fliperos-setup/lib/latency.sh")
for param in $base; do
  grep -q -- " $param " <<< " $(grep -m1 'cmdline:' "$work/limine.conf") " || fail "boot da midia sem $param"
done
echo "latencia: servico no boot, timers do apt mascarados, $base"

# ── Teclas de volume ──────────────────────────────────────────
unsquashfs -cat "$work/filesystem.squashfs" etc/triggerhappy/triggers.d/fliperos-volume.conf > "$work/f" \
  || fail "ausente: teclas de volume do triggerhappy"
cmp -s "$src/config/fliperos-volume.triggers" "$work/f" || fail "teclas de volume diferem do repositorio"
unsquashfs -cat "$work/filesystem.squashfs" etc/systemd/system/triggerhappy.service.d/fliperos.conf > "$work/f" \
  || fail "ausente: drop-in do triggerhappy"
grep -q -- '--user' "$work/f" && fail "triggerhappy ainda roda como outro usuario (sem acesso ao audio)"
grep -q 'multi-user.target.wants/triggerhappy.service' "$work/files.txt" || fail "triggerhappy nao habilitado"
echo "teclas de volume: triggerhappy habilitado, como root, com as teclas do FliperOS"

# ── Tema Dracula e emuladores no menu do LXDE ─────────────────
for path in usr/share/themes/Dracula/gtk-2.0/gtkrc usr/share/themes/Dracula/gtk-3.20/gtk.css \
  usr/share/themes/Dracula/openbox-3/themerc home/fliperos/.config/openbox/lxde-rc.xml \
  etc/fliperos/mame/ui.ini; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" home/fliperos/.config/openbox/lxde-rc.xml > "$work/f"
grep -q '<name>Dracula</name>' "$work/f" || fail "o Openbox do LXDE nao usa o tema Dracula"
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
echo "tema Dracula (GTK, Openbox, GroovyMAME) e emuladores no menu do LXDE"

# ── Modo de video dos emuladores (640x240 nos de 480i) ────────
for path in etc/fliperos/emulator-modes.conf opt/fliperos/bin/fliperos-ini-set opt/fliperos/bin/fliperos-x11-run; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/emulator-modes.conf > "$work/f"
cmp -s "$src/config/fliperos-emulator-modes.conf" "$work/f" || fail "emulator-modes.conf difere do repositorio"
echo "modos: tabela por emulador e fliperos-x11-run --mode"

# ── Emuladores e lojas novos (so o que foi incluido no build) ─
present() { grep -q "squashfs-root/$1\$" "$work/files.txt"; }
if present usr/local/bin/hypseus.bin; then
  has usr/local/bin/hypseus
  has home/fliperos/roms/hypseus/fonts
  grep -E 'home/fliperos/.hypseus ->' "$work/links.txt" | grep -q '/opt/fliperos/roms/hypseus' \
    || fail "/home/fliperos/.hypseus nao aponta para /opt/fliperos/roms/hypseus"
  echo "Hypseus Singe: binario, scripts e home no acervo"
fi
if present usr/local/lib/openbor/OpenBOR; then
  has usr/local/bin/openbor
  has home/fliperos/roms/openbor/Paks
  echo "OpenBOR: wrapper e Paks no acervo"
fi
if present usr/local/bin/dolphin-emu; then
  has usr/local/share/pixmaps/dolphin-emu.png
  present usr/local/share/applications/dolphin-emu.desktop && fail "o atalho do proprio Dolphin nao saiu"
  echo "Dolphin: sem o atalho proprio (abre pelo fliperos-launch)"
fi
if present usr/bin/wine; then
  has usr/local/bin/fliperos-model2
  has opt/fliperos/model2/roms
  echo "Wine e o lancador do Model 2 (o emulador o usuario copia)"
fi
present usr/games/steam && echo "Steam: steam-installer"
present opt/Heroic/heroic && echo "Heroic (GOG)"

# ── RetroArch: cores de fabrica e pasta do Online Updater ─────
if grep -q 'squashfs-root/usr/local/bin/retroarch$' "$work/files.txt"; then
  for core in fceumm snes9x genesis_plus_gx mgba pcsx_rearmed mame2010; do
    has "opt/fliperos/retroarch/cores/${core}_libretro.so"
  done
  grep -q 'squashfs-root/opt/fliperos/retroarch/info/snes9x_libretro.info$' "$work/files.txt" \
    || fail "RetroArch sem os .info dos cores"
  unsquashfs -lln "$work/filesystem.squashfs" > "$work/numeric.txt" 2> /dev/null
  grep -E ' 1000/1000 .* squashfs-root/opt/fliperos/retroarch/cores$' "$work/numeric.txt" > /dev/null \
    || fail "a pasta de cores do RetroArch nao e do usuario (o Core Downloader nao grava)"
  echo "RetroArch: 6 cores de fabrica, .info e pasta do usuario para o Core Downloader"
fi

# ── GroovyMAME: release, atalho e arquivos da tag ─────────────
if present usr/local/libexec/groovymame; then
  unsquashfs -cat "$work/filesystem.squashfs" usr/local/bin/groovymame > "$work/f" \
    || fail "ausente: /usr/local/bin/groovymame (o atalho)"
  cmp -s "$src/config/fliperos-groovymame" "$work/f" || fail "/usr/local/bin/groovymame difere de config/fliperos-groovymame"
  for path in usr/local/share/groovymame/fonts/uismall.bdf usr/local/share/groovymame/plugins/hiscore/init.lua \
    usr/local/share/groovymame/bgfx/chains/default.json usr/local/share/groovymame/hash/nes.xml; do
    has "$path"
  done
  unsquashfs -cat "$work/filesystem.squashfs" etc/fliperos/mame/mame.ini > "$work/f"
  cmp -s "$src/config/mame.ini" "$work/f" || fail "/etc/fliperos/mame/mame.ini difere de config/mame.ini"
  echo "GroovyMAME: release em /usr/local/libexec, atalho groovymame, plugins/fonte/bgfx/hash e mame.ini do GroovyArcade"
fi

# ── Terminal: zsh com Oh My Zsh e o tema Dracula ──────────────
for path in usr/bin/zsh usr/local/share/oh-my-zsh/oh-my-zsh.sh \
  usr/local/share/oh-my-zsh/custom/themes/dracula.zsh-theme \
  usr/local/share/oh-my-zsh/custom/themes/lib/async.zsh opt/fliperos/bin/fliperos-tty1; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" home/fliperos/.zshrc > "$work/f" || fail "ausente: /home/fliperos/.zshrc"
cmp -s "$src/config/zshrc" "$work/f" || fail "/home/fliperos/.zshrc difere de config/zshrc"
unsquashfs -cat "$work/filesystem.squashfs" etc/passwd > "$work/f"
grep -q '^fliperos:.*:/usr/bin/zsh$' "$work/f" || fail "o shell do usuario fliperos nao e o zsh"
echo "terminal: zsh do usuario com Oh My Zsh e o tema Dracula"

# ── Acervo em ~/roms ───────────────────────────────────────────
grep -E 'opt/fliperos/roms ->' "$work/links.txt" | grep -q '/home/fliperos/roms' \
  || fail "/opt/fliperos/roms nao aponta para /home/fliperos/roms"
for path in home/fliperos/roms/mame home/fliperos/roms/ps2/_info.txt etc/samba/smb.conf \
  opt/fliperos/bin/fliperos-roms opt/fliperos/bin/fliperos-calibrate; do
  has "$path"
done
if present opt/fliperos/retroarch/info/snes9x_libretro.info; then
  has home/fliperos/roms/retroarch/snes9x/_info.txt
fi
echo "acervo: ~/roms com uma pasta por emulador e por core do RetroArch"

# ── Terminal do desktop: so o Alacritty ───────────────────────
# O lxterminal e o xterm nao desenhavam as bordas do Gum; uma dependencia
# nova nao pode traze-los de volta.
has usr/bin/alacritty
has home/fliperos/.config/alacritty/alacritty.toml
for bin in usr/bin/lxterminal usr/bin/xterm usr/bin/lxterm usr/bin/uxterm; do
  present "$bin" && fail "terminal que devia ter saido: /$bin"
done
echo "terminal do desktop: Alacritty (sem lxterminal nem xterm)"

# ── App Store: GNOME Software + Flathub ───────────────────────
for path in usr/bin/gnome-software usr/bin/flatpak usr/share/glib-2.0/schemas/90_fliperos-software.gschema.override \
  usr/local/share/applications/org.gnome.Software.desktop; do
  has "$path"
done
unsquashfs -cat "$work/filesystem.squashfs" var/lib/flatpak/repo/config > "$work/f" 2> /dev/null || true
grep -q '^\[remote "flathub"\]' "$work/f" || fail "Flathub nao esta nas fontes de Flatpak"
present 'usr/lib/x86_64-linux-gnu/gnome-software/plugins-.*/libgs_plugin_snap.so' && fail "App Store com o plugin de snap"
echo "App Store: GNOME Software com Flatpak e Flathub, sem atualizacao automatica"

xorriso -indev "$iso" -report_el_torito plain > "$work/boot.txt" 2>&1
grep -q 'BIOS' "$work/boot.txt" || fail "sem boot BIOS"
grep -q 'UEFI' "$work/boot.txt" || fail "sem boot UEFI"
echo "ISO conferida: boot BIOS e UEFI."
sha256sum "$iso"
