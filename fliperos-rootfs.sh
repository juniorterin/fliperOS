#!/usr/bin/env bash
# Instala os arquivos do FliperOS num rootfs: o fliperos-setup, a sessao de
# boot, o LXDE, a paleta do console e a configuracao de video de partida.
# Usado pelo fliperos-mkiso.sh e pelas ferramentas de auditoria em tools/.
#
#   fliperos-rootfs.sh RAIZ
#
# O que depende do monitor (modo de boot, Switchres, Xorg) NAO sai daqui:
# e decidido na midia pelo teste de saidas e gravado pelo fliperos-setup.
set -euo pipefail
src=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
root=${1:?Uso: fliperos-rootfs.sh RAIZ}
[[ -d "$root/etc" ]] || { echo "Invalid rootfs: $root" >&2; exit 2; }
home="$root/home/fliperos"

# ── fliperos-setup (o gasetup do FliperOS) ────────────────────────
rm -rf "$root/usr/local/lib/fliperos-setup"
mkdir -p "$root/usr/local/lib"
cp -r "$src/fliperos-setup" "$root/usr/local/lib/fliperos-setup"
find "$root/usr/local/lib/fliperos-setup" -type d -exec chmod 755 {} +
find "$root/usr/local/lib/fliperos-setup" -type f -exec chmod 644 {} +
chmod 755 "$root/usr/local/lib/fliperos-setup/fliperos-setup"
mkdir -p "$root/usr/local/bin" "$root/usr/local/sbin"
ln -sfn /usr/local/lib/fliperos-setup/fliperos-setup "$root/usr/local/bin/fliperos-setup"
install -Dm644 "$src/config/fliperos-setup.desktop" "$root/usr/share/applications/fliperos-setup.desktop"

# Diagnostico do modo ativo (alimenta o "Testing Results") e EDIDs por preset.
install -Dm755 "$src/fliperos-video-check.py" "$root/usr/local/bin/fliperos-video-check"
install -Dm755 "$src/config/fliperos-rebuild-edids" "$root/usr/local/sbin/fliperos-rebuild-edids"
install -Dm755 "$src/config/fliperos-edid-hook" "$root/etc/initramfs-tools/hooks/fliperos-edid"

# ── Estado e sessao de boot ───────────────────────────────────────
mkdir -p "$root/etc/fliperos" "$root/etc/fliperos/mame" "$root/etc/fliperos/retroarch"
install -Dm644 "$src/config/fliperos-sessions.conf" "$root/etc/fliperos/sessions.conf"
[[ -f "$root/etc/fliperos/session" ]] || printf 'setup\n' > "$root/etc/fliperos/session"
for name in fliperos-session fliperos-kms-run fliperos-x11-run fliperos-x11-client fliperos-lxde fliperos-launch \
  fliperos-tty1 fliperos-ini-set fliperos-resolution fliperos-logout fliperos-escquit fliperos-panning \
  fliperos-automount; do
  install -Dm755 "$src/config/$name" "$root/opt/fliperos/bin/$name"
done
# Pastas do acervo em ~/roms (uma por emulador e por core do RetroArch) e os
# temas do splash em ~/splashscreen.
install -Dm755 "$src/config/fliperos-roms" "$root/opt/fliperos/bin/fliperos-roms"
# Console calado depois do boot tambem: o 10-console-messages.conf do Ubuntu
# volta o nivel do console para 4 (kernel.printk = 4 4 1 7) no meio do boot,
# por cima do loglevel=3 da linha do kernel, e um erro do kernel depois que o
# Plymouth sai aparecia na tela (no gabinete, "hdaudio hdaudioC0D3: Unable
# to configure", o codec HDMI da Intel sem uso). 3: so os criticos.
mkdir -p "$root/etc/sysctl.d"
printf 'kernel.printk = 3 4 1 3\n' > "$root/etc/sysctl.d/99-fliperos-console.conf"
# Samba: \\fliperos\FliperOS (/opt/fliperos) e \\fliperos\roms.
install -Dm644 "$src/config/smb.conf" "$root/etc/samba/smb.conf"
# Sons do menu do Setup (Audio Setup > Menu sounds): os WAV da pessoa, que
# ela grava pela rede (\\fliperos\FliperOS\sounds\menu).
install -d -m 775 "$root/opt/fliperos/sounds/menu"
[[ -f "$root/opt/fliperos/sounds/menu/_info.txt" ]] || cat > "$root/opt/fliperos/sounds/menu/_info.txt" << 'EOF'
Menu sounds of the FliperOS Setup (WAV):
  move.wav    when the cursor moves
  select.wav  on Enter
They play once they are here; Setup > Audio Setup > Menu sounds turns them
on and off. FliperOS doesn't come with game sounds: use your own.
EOF
chown -R 1000:1000 "$root/opt/fliperos/sounds" 2> /dev/null || true
# fliperos-menu: do shell de volta ao menu (o laco do fliperos-tty1).
install -Dm755 "$src/config/fliperos-menu" "$root/usr/local/bin/fliperos-menu"
# Controle como teclado nos menus do setup (o servico so age com o menu na
# tela; ver config/fliperos-padkeys).
install -Dm755 "$src/config/fliperos-padkeys" "$root/opt/fliperos/bin/fliperos-padkeys"
install -Dm644 "$src/config/fliperos-padkeys.service" "$root/etc/systemd/system/fliperos-padkeys.service"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -sfn /etc/systemd/system/fliperos-padkeys.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-padkeys.service"
# O openbox do fliperos-x11-run (encaixa a janela na tela a cada troca de
# modo; config/fliperos-x11-client).
install -Dm644 "$src/config/openbox-x11-run.xml" "$root/etc/fliperos/openbox-x11-run.xml"
install -Dm644 "$src/config/openbox-black-themerc" "$root/usr/share/themes/FliperOS-Black/openbox-3/themerc"
# Modo de video de cada emulador do fliperos-x11-run (640x240 nos de 480i
# num monitor de 15 kHz). O usuario pode editar: a imagem nao sobrescreve.
[[ -f "$root/etc/fliperos/emulator-modes.conf" ]] \
  || install -Dm644 "$src/config/fliperos-emulator-modes.conf" "$root/etc/fliperos/emulator-modes.conf"
# Tabelas de versoes anteriores: Model 2 e 3 em 496x384 no 15 kHz, que so
# existe entrelacado. So muda a linha que ainda e a de fabrica.
sed -i -E 's/^(supermodel|fliperos-model2)( +)496x384@57\.524  496x384@57\.524$/\1\2640x240@57.524  496x384@57.524/' \
  "$root/etc/fliperos/emulator-modes.conf"
# O SNES9x do Fightcade era 320x240 no 15 kHz; agora o do console. A sala
# era 640x480; agora 512x448 (o texto maior).
sed -i -E -e 's/^fightcade-snes9x    320x240@60      640x480@60$/fightcade-snes9x    256x224@60.0988 640x480@60/' \
  -e 's/^fightcade           640x480@60      640x480@60$/fightcade           512x448@60      640x480@60/' \
  "$root/etc/fliperos/emulator-modes.conf"
# Tabelas de antes do Fightcade ganham as linhas dele, as do config/: a da
# sala de jogos (640x480: nao cabe em 240 linhas; sem ela o fliperos-x11-run
# o abriria em 320x240) e a de cada emulador das partidas.
while IFS= read -r line; do
  grep -q "^${line%%[[:space:]]*}[[:space:]]" "$root/etc/fliperos/emulator-modes.conf" ||
    printf '%s\n' "$line" >> "$root/etc/fliperos/emulator-modes.conf"
done < <(grep '^fightcade' "$src/config/fliperos-emulator-modes.conf")
# SM2-Emu: o modo, numa tabela de antes dele. A linha mudada pela pessoa fica.
line=$(grep '^sm2-emu[[:space:]]' "$src/config/fliperos-emulator-modes.conf" || true)
[[ -z $line ]] || grep -q '^sm2-emu[[:space:]]' "$root/etc/fliperos/emulator-modes.conf" ||
  printf '%s\n' "$line" >> "$root/etc/fliperos/emulator-modes.conf"
# Model 2 no Wine: no PATH, para os frontends tambem chamarem.
install -Dm755 "$src/config/fliperos-model2" "$root/usr/local/bin/fliperos-model2"
# SM2-Emu: so o lancador. O fonte e o binario nascem em ~/.local/src na
# primeira abertura (config/fliperos-sm2emu), fora da imagem.
install -Dm755 "$src/config/fliperos-sm2emu" "$root/usr/local/bin/fliperos-sm2emu"
# Os patches que ele aplica no fonte antes de compilar.
rm -rf "$root/usr/local/share/fliperos/sm2-emu-patches"
install -d "$root/usr/local/share/fliperos/sm2-emu-patches"
install -m644 "$src"/config/sm2-emu-patches/*.patch "$root/usr/local/share/fliperos/sm2-emu-patches/"
# Fightcade 2 (Setup > Frontend): o que o baixa do site dele e o abre, e o
# openbox dele (Alt+Tab entre a sala de jogos e o emulador). O programa em si
# nao vem na imagem (codigo fechado).
install -Dm755 "$src/config/fliperos-fightcade" "$root/opt/fliperos/bin/fliperos-fightcade"
install -Dm644 "$src/config/openbox-fightcade.xml" "$root/etc/fliperos/openbox-fightcade.xml"
# Wine, Steam e Heroic nao vem na imagem: o Setup > Extras os instala.
install -Dm755 "$src/config/fliperos-extras" "$root/opt/fliperos/bin/fliperos-extras"
# groovymame: o atalho (config/fliperos-groovymame) na frente do binario do
# release, em /usr/local/libexec. Num sistema de antes, o binario compilado
# estava no lugar do atalho: muda de pasta.
gm="$root/usr/local/bin/groovymame"
if [[ -f $gm ]] && [[ $(head -c 4 "$gm" | od -An -c | tr -d ' ') == '177ELF' ]]; then
  mkdir -p "$root/usr/local/libexec"
  mv -f "$gm" "$root/usr/local/libexec/groovymame"
fi
install -Dm755 "$src/config/fliperos-groovymame" "$gm"
# A opcao GroovyMAME 4:3 saiu do Video Setup: o gerador, os .ini por jogo e
# a chave de uma instalacao anterior vao embora.
rm -rf "$root/opt/fliperos/bin/fliperos-mame-aspect" "$root/etc/fliperos/mame/aspect"
[[ -f "$root/etc/fliperos/fliperos.conf" ]] && sed -i '/^mame_crt_aspect=/d' "$root/etc/fliperos/fliperos.conf"
# O mame.ini completo, como o GroovyArcade (o -createconfig do GroovyMAME com
# as opcoes do config/mame.ini por cima): o build o roda.
install -Dm755 "$src/config/fliperos-mame-ini" "$root/opt/fliperos/bin/fliperos-mame-ini"
# Setup > Joysticks > Button mapping: os botoes de cada jogador no RetroArch
# e no GroovyMAME.
install -Dm755 "$src/config/fliperos-buttons" "$root/opt/fliperos/bin/fliperos-buttons"
# Setup > MAME ROM Cleaner: o que sai de uma pasta de ROMs, pelo XML do MAME.
install -Dm755 "$src/config/fliperos-romclean" "$root/opt/fliperos/bin/fliperos-romclean"
# Setup > Free games: homebrew de codigo aberto para as pastas de ~/roms.
install -Dm755 "$src/config/fliperos-freeroms" "$root/opt/fliperos/bin/fliperos-freeroms"
# Setup > Scraper > progetto-SNAPS: as capturas dos jogos de arcade.
install -Dm755 "$src/config/fliperos-snaps" "$root/opt/fliperos/bin/fliperos-snaps"
# Setup > Downloader: o romset e os CHDs por link magnetico, so o que o filtro
# do ROM cleaner escolhe. O servico so e ligado pelo Setup, com um link.
install -Dm755 "$src/config/fliperos-downloader" "$root/opt/fliperos/bin/fliperos-downloader"
install -Dm644 "$src/config/fliperos-transmission.service" "$root/etc/systemd/system/fliperos-transmission.service"
install -Dm644 "$src/config/fliperos-downloader-magnets" "$root/usr/local/share/fliperos/downloader-magnets"
# Updates sem ISO nova (patches do updates/index, em ordem), perguntados no
# boot pelo fliperos-tty1.
install -Dm755 "$src/config/fliperos-update" "$root/opt/fliperos/bin/fliperos-update"
# catver.ini, nplayers.ini e controls.xml do ROM cleaner: junto do romset ou
# nesta pasta (lib/romclean.sh); e onde ele guarda o que leu do XML do MAME.
mkdir -p "$root/usr/local/share/fliperos/romclean" "$root/var/cache/fliperos"
[[ -f "$root/etc/fliperos/mame/mame.ini" ]] || install -Dm644 "$src/config/mame.ini" "$root/etc/fliperos/mame/mame.ini"
# Cores Dracula da interface do GroovyMAME; o ui.ini e do usuario porque o
# MAME o regrava quando a interface e personalizada pelo proprio menu.
[[ -f "$root/etc/fliperos/mame/ui.ini" ]] || install -Dm644 "$src/config/mame-ui.ini" "$root/etc/fliperos/mame/ui.ini"
# Numa instalacao anterior, o mame.ini e o ui.ini ganham as chaves de
# config/ que ainda nao tem; as que o Setup, o MAME ou o usuario ja
# gravaram ficam como estao.
for ini in mame.ini:mame.ini ui.ini:mame-ui.ini; do
  target="$root/etc/fliperos/mame/${ini%%:*}"
  while read -r key value; do
    grep -qE "^${key}[[:space:]]" "$target" || printf '%-25s %s\n' "$key" "$value" >> "$target"
  done < <(grep -vE '^[[:space:]]*(#|$)' "$src/config/${ini#*:}")
  # As pastas: uma relativa (o "cfg", "snap", "." do -createconfig puro)
  # depende da pasta de onde o GroovyMAME e aberto, e ele enchia a home de
  # cfg/nvram; sai, e sem nenhuma absoluta vale a do config/. As de procura
  # do config/ (a BIOS em ~/bios/mame, a arte em ~/media/<tipo>/arcade)
  # entram tambem na lista que ja existe, sem tirar as que estao la; as de
  # ~/.mame/scraped (o Scraper de antes do ~/media) saem.
  while read -r key value; do
    case $key in *path | *_directory) ;; *) continue ;; esac
    add=0
    case $key in
      rompath | snapshot_directory | covers_directory | flyers_directory | marquees_directory | logos_directory) add=1 ;;
    esac
    awk -v k="$key" -v want="$value" -v add="$add" '
      $1 == k && !done {
        cur = $0
        sub(/^[[:space:]]*[^[:space:]]+[[:space:]]*/, "", cur)
        n = split(cur, have, ";")
        out = ""
        for (i = 1; i <= n; i++) {
          if (have[i] !~ /^[\/$~]/ || have[i] ~ /\/\.mame\/scraped\//) continue
          out = out (out == "" ? "" : ";") have[i]
          seen[have[i]] = 1
        }
        m = split(want, extra, ";")
        if (add || out == "")
          for (i = 1; i <= m; i++) if (!(extra[i] in seen)) out = out (out == "" ? "" : ";") extra[i]
        printf "%-25s %s\n", k, out
        done = 1
        next
      }
      { print }' "$target" > "$target.new" && mv -f "$target.new" "$target"
  done < <(grep -vE '^[[:space:]]*(#|$)' "$src/config/${ini#*:}")
done
# O modesetting 0 de antes (o GroovyMAME no KMS) no X nao troca o modo do
# jogo: passa para o 1 do config/mame.ini.
sed -i -E 's/^(modesetting[[:space:]]+)0[[:space:]]*$/\11/' "$root/etc/fliperos/mame/mame.ini"
chown -R 1000:1000 "$root/etc/fliperos/mame" 2> /dev/null || true
install -Dm644 "$src/config/retroarch.cfg" "$root/etc/fliperos/retroarch/retroarch.cfg"
install -Dm644 "$src/config/retroarch-gl.cfg" "$root/etc/fliperos/retroarch/retroarch-gl.cfg"
# PCSX2.ini de partida: o fliperos-x11-run o copia para o usuario na
# primeira abertura (sem o assistente, Big Picture, BIOS e jogos em ~).
install -Dm644 "$src/config/pcsx2.ini" "$root/etc/fliperos/pcsx2.ini"

# Emuladores no menu do LXDE (Jogos). O TryExec esconde o que nao foi
# compilado; os icones dos projetos vem do build de cada um. Os que nao
# entram na imagem com icone (o GroovyMAME do release, o SM2-Emu e o
# Fightcade, baixados depois) levam o oficial de config/icons; o Supermodel,
# sem icone proprio, o monograma do FliperOS.
for file in "$src"/config/applications/*.desktop; do
  install -Dm644 "$file" "$root/usr/local/share/applications/${file##*/}"
done
for file in "$src"/config/icons/*.svg "$src"/config/icons/*.png; do
  install -Dm644 "$file" "$root/usr/local/share/pixmaps/${file##*/}"
done
# Os monogramas que os oficiais substituiram.
rm -f "$root"/usr/local/share/pixmaps/fliperos-{groovymame,model2,fightcade}.svg
# Os temas do FliperOS para 240p (lib/frontends.sh os deixa escolhidos num
# monitor de 15 kHz). O do Pegasus: na pasta de temas do sistema, onde o
# Pegasus os procura.
for file in "$src"/config/pegasus-theme-fliperos/*; do
  install -Dm644 "$file" "$root/usr/share/pegasus-frontend/themes/fliperos-240p/${file##*/}"
done
# E o do ES-DE, na pasta de temas dele (o nome da pasta e o que vai na opcao
# Theme do es_settings.xml).
for file in "$src"/config/esde-theme-fliperos/*; do
  install -Dm644 "$file" "$root/usr/share/es-de/themes/fliperos-240p-es-de/${file##*/}"
done
# Falkon e Transmission (vem na imagem): no menu do LXDE o nome diz para que
# servem, "Falkon (browser)" e "Transmission (torrent)". A entrada do pacote
# e copiada para /usr/local/share/applications (que vem antes) com o nome
# trocado em todos os idiomas, so no grupo principal: as acoes ficam.
for pair in org.kde.falkon.desktop:browser transmission-gtk.desktop:torrent; do
  entry="$root/usr/share/applications/${pair%%:*}"
  [[ -f $entry ]] || continue
  awk -v suffix=" (${pair#*:})" '
    /^\[/ { main = ($0 == "[Desktop Entry]") }
    main && /^Name(\[[^]]*\])?=/ && index($0, suffix) == 0 { $0 = $0 suffix }
    { print }' "$entry" > "$root/usr/local/share/applications/${pair%%:*}"
done

# App Store (GNOME Software + Flathub): sem atualizacao sozinha nem tela de
# boas-vindas. O org.gnome.Software.desktop de config/applications, com o
# mesmo ID do pacote, vem antes dele (/usr/local/share) e a chama de "App
# Store" no menu; o painel tem um botao para ela.
install -Dm644 "$src/config/fliperos-software.gschema.override" \
  "$root/usr/share/glib-2.0/schemas/90_fliperos-software.gschema.override"
if [[ -x "$root/usr/bin/glib-compile-schemas" ]] && [[ -d "$root/proc/1" || -n ${FLIPEROS_ROOTFS_CHROOT:-} ]]; then
  chroot "$root" glib-compile-schemas /usr/share/glib-2.0/schemas || true
fi

# Xorg sem descanso de tela ate o fliperos-setup gerar a configuracao do
# monitor (ele reescreve este arquivo).
mkdir -p "$root/etc/X11/xorg.conf.d"
[[ -f "$root/etc/X11/xorg.conf.d/10-fliperos.conf" ]] || cat > "$root/etc/X11/xorg.conf.d/10-fliperos.conf" << 'EOF'
# Gerado pelo fliperos-setup; o Video Setup reescreve este arquivo.
Section "ServerFlags"
    Option "BlankTime" "0"
    Option "StandbyTime" "0"
    Option "SuspendTime" "0"
    Option "OffTime" "0"
EndSection
EOF

# ── Perifericos (light gun, volantes) ─────────────────────────────
install -Dm755 "$src/config/fliperos-guncon2-calibrate" "$root/usr/local/bin/fliperos-guncon2-calibrate"
# Calibrador do Setup > Joysticks (GunCon 2, volante, pedais, analogico).
install -Dm755 "$src/config/fliperos-calibrate" "$root/opt/fliperos/bin/fliperos-calibrate"
install -Dm644 "$src/config/99-fliperos-input.rules" "$root/etc/udev/rules.d/99-fliperos-input.rules"
# Discos montados sozinhos em /media/fliperos, com um icone no desktop para
# cada um (config/fliperos-automount); sem senha pelo polkit.
install -Dm644 "$src/config/99-fliperos-disks.rules" "$root/etc/udev/rules.d/99-fliperos-disks.rules"
install -Dm644 "$src/config/fliperos-automount@.service" "$root/etc/systemd/system/fliperos-automount@.service"
install -Dm644 "$src/config/50-fliperos-udisks.rules" "$root/etc/polkit-1/rules.d/50-fliperos-udisks.rules"
if [[ ! -f "$root/etc/fliperos/guncon2.conf" ]]; then
  cat > "$root/etc/fliperos/guncon2.conf" << 'EOF'
# Faixa util do GunCon 2 neste monitor. Os valores abaixo sao o exemplo do
# upstream e NAO servem pra todo tubo — calibre no seu e ajuste aqui.
X_MIN=175
X_MAX=720
Y_MIN=20
Y_MAX=240
EOF
fi

# Mapeamentos de controle do SDL2 (AntiMicroX, emuladores SDL): o
# fliperos-controllers completa o mapeamento automatico do SDL (botoes que ele
# deixa de fora, direcional digital mandado como eixos) no boot e a cada
# controle ligado, em /var/lib/fliperos/gamecontrollerdb.txt. Todo login le o
# /etc/environment; o fliperos-lxde e os lancadores tambem exportam.
install -Dm755 "$src/config/fliperos-controllers" "$root/opt/fliperos/bin/fliperos-controllers"
install -Dm644 "$src/config/fliperos-controllers.service" "$root/etc/systemd/system/fliperos-controllers.service"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants" "$root/var/lib/fliperos"
ln -sfn /etc/systemd/system/fliperos-controllers.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-controllers.service"
rm -f "$root/etc/fliperos/gamecontrollerdb.txt"
sed -i '/^SDL_GAMECONTROLLERCONFIG_FILE=/d' "$root/etc/environment" 2> /dev/null || true
echo 'SDL_GAMECONTROLLERCONFIG_FILE=/var/lib/fliperos/gamecontrollerdb.txt' >> "$root/etc/environment"

# ── Teclas de volume ──────────────────────────────────────────────
# O triggerhappy le o /dev/input e roda o fliperos-setup --volume: vale em
# qualquer tela (KMS, X, console). O servico do pacote roda os comandos como
# "nobody", sem acesso ao /dev/snd; aqui ele roda como root, e so executa o
# que esta em /etc/triggerhappy/triggers.d (de root).
install -Dm644 "$src/config/fliperos-volume.triggers" "$root/etc/triggerhappy/triggers.d/fliperos-volume.conf"
mkdir -p "$root/etc/systemd/system/triggerhappy.service.d"
cat > "$root/etc/systemd/system/triggerhappy.service.d/fliperos.conf" << 'EOF'
[Service]
ExecStart=
ExecStart=/usr/sbin/thd --triggers /etc/triggerhappy/triggers.d/ --socket /run/thd.socket --deviceglob /dev/input/event*
EOF

# ── Rede ──────────────────────────────────────────────────────────
# O Ubuntu manda o NetworkManager entregar o DNS ao systemd-resolved, que nao
# esta na imagem: o /etc/resolv.conf nunca era atualizado (ficava o DNS do
# container do build) e o gabinete nao resolvia nome nenhum — sem System
# Update nem frontends pelo apt. Aqui o proprio NM escreve o resolv.conf com
# o DNS do DHCP. O 10-globally-managed-devices.conf vazio anula o do Ubuntu
# (que so deixa o NM cuidar do Wi-Fi): o cabo de rede tambem pega IP.
mkdir -p "$root/etc/NetworkManager/conf.d"
cat > "$root/etc/NetworkManager/conf.d/90-fliperos-dns.conf" << 'EOF'
[main]
dns=default
rc-manager=file
EOF
: > "$root/etc/NetworkManager/conf.d/10-globally-managed-devices.conf"

# ── Splash e console ──────────────────────────────────────────────
# Os temas que vem na imagem (config/splashscreen): no Plymouth e em
# /usr/share/fliperos/splashscreen, de onde o fliperos-roms os copia para
# ~/splashscreen. Setup > Splash screen escolhe o do boot entre os de la.
rm -rf "$root/usr/share/fliperos/splashscreen"
mkdir -p "$root/usr/share/fliperos"
cp -r "$src/config/splashscreen" "$root/usr/share/fliperos/splashscreen"
for theme in "$src"/config/splashscreen/*/; do
  theme=$(basename "$theme")
  rm -rf "$root/usr/share/plymouth/themes/$theme"
  mkdir -p "$root/usr/share/plymouth/themes"
  cp -r "$src/config/splashscreen/$theme" "$root/usr/share/plymouth/themes/$theme"
done
chmod -R a+rX "$root/usr/share/fliperos/splashscreen" "$root/usr/share/plymouth/themes"
# JetBrains Mono, a fonte do tema de texto, tambem no initramfs (o hook).
rm -rf "$root/usr/share/fonts/truetype/fliperos"
install -Dm644 -t "$root/usr/share/fonts/truetype/fliperos" \
  "$src"/config/fonts/jetbrains-mono/*.ttf "$src/config/fonts/jetbrains-mono/OFL.txt"
install -Dm755 "$src/config/fliperos-initramfs-fonts" "$root/etc/initramfs-tools/hooks/fliperos-fonts"

# ── OpenBOR ───────────────────────────────────────────────────────
# Onde ha o OpenBOR 4 (compilado no fliperos-mkiso.sh): o comando openbor e
# o 3.0 build 6391 dos paks que o 4 recusa (config/fliperos-openbor).
if [[ -x $root/usr/local/lib/openbor/OpenBOR ]]; then
  install -Dm755 "$src/config/fliperos-openbor" "$root/usr/local/bin/openbor"
  install -Dm755 "$src/config/openbor-legacy/OpenBOR-3.0" "$root/usr/local/lib/openbor/OpenBOR-3.0"
  install -Dm644 "$src/config/openbor-legacy/LICENSE" "$root/usr/local/share/doc/openbor-3.0/LICENSE"
fi
# Paleta Dracula no console: o setvtrgb.service do Ubuntu aplica /etc/vtrgb
# no boot, e /etc/vtrgb e uma alternativa (a de maior prioridade vence).
install -Dm644 "$src/config/vtrgb-dracula" "$root/etc/fliperos/vtrgb-dracula"
if [[ -x "$root/usr/bin/update-alternatives" ]] && [[ -d "$root/proc/1" || -n ${FLIPEROS_ROOTFS_CHROOT:-} ]]; then
  chroot "$root" update-alternatives --install /etc/vtrgb vtrgb /etc/fliperos/vtrgb-dracula 100 > /dev/null
else
  ln -sfn /etc/fliperos/vtrgb-dracula "$root/etc/vtrgb"
fi

# ── Drivers ───────────────────────────────────────────────────────
# radeon nas placas SI/CIK (onde o 15 kHz foi validado no gabinete) sem
# desligar o amdgpu das demais.
# Som HDA sempre ligado: com o power_save do kernel do Ubuntu (1 s) o codec
# desliga em silencio e religa no proximo som, e cada liga-desliga estala
# nas caixas (no gabinete, "puffs" com o menu parado).
cat > "$root/etc/modprobe.d/fliperos.conf" << 'EOF'
options radeon si_support=1 cik_support=1 dpm=1
options amdgpu si_support=0 cik_support=0
options snd_hda_intel power_save=0 power_save_controller=N
EOF
# O live-config do Debian criaria um usuario padrao no mesmo UID 1000.
ln -sf /dev/null "$root/etc/systemd/system/live-config.service"

# ── Latencia (docs/wiki/Latency.md) ───────────────────────────────
# O modo escolhido em Setup > Latency vale desde o boot.
install -Dm644 "$src/config/fliperos-latency.service" "$root/etc/systemd/system/fliperos-latency.service"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -sfn /etc/systemd/system/fliperos-latency.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-latency.service"
# Nada de apt nem man-db rodando sozinho no meio de uma partida (picos de
# CPU e disco). Atualizar fica no Setup > System Update, como no GA.
for timer in apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
  ln -sfn /dev/null "$root/etc/systemd/system/$timer"
done
# Servicos de versoes anteriores (conferencia fixa de VGA-1 a 15 kHz).
rm -f "$root/etc/systemd/system/multi-user.target.wants/fliperos-video-check.service" \
  "$root/etc/systemd/system/fliperos-video-check.service"

# ── Usuario: login no tty1, frontend e setup ──────────────────────
if [[ -d "$home" ]]; then
  # O fluxo do .bash_profile do GroovyArcade (config/fliperos-tty1): no
  # disco instalado abre o launcher padrao e, quando ele fecha, o setup; na
  # midia de instalacao abre direto o setup. O shell do usuario e o zsh
  # (Oh My Zsh + Dracula); o .bash_profile fica para quem voltar ao bash.
  cat > "$home/.zprofile" << 'EOF'
if [[ -z "${DISPLAY:-}" && "$(tty)" == /dev/tty1 ]]; then
    /opt/fliperos/bin/fliperos-tty1
fi
EOF
  cat > "$home/.bash_profile" << 'EOF'
[[ -f ~/.bashrc ]] && . ~/.bashrc
if [[ -z "${DISPLAY:-}" && "$(tty)" == /dev/tty1 ]]; then
    /opt/fliperos/bin/fliperos-tty1
fi
command -v fliperos-motd > /dev/null && fliperos-motd
EOF
  install -m644 "$src/config/zshrc" "$home/.zshrc"
  # Remaps dos cores de MAME do RetroArch: o botao N do painel e o Button N
  # (config/retroarch-remaps). Um remap salvo pelo menu do RetroArch (sem o
  # cabecalho "# FliperOS") fica.
  for rmp in "$src"/config/retroarch-remaps/*.rmp; do
    name=$(basename "$rmp" .rmp)
    target="$home/.config/retroarch/config/remaps/$name/$name.rmp"
    if [[ ! -f $target ]] || head -1 "$target" | grep -q '^# FliperOS'; then
      install -Dm644 "$rmp" "$target"
    fi
  done
  # switchres.ini de um core so (config/retroarch-switchres): o CRT SwitchRes
  # do RetroArch o le por cima do /etc/switchres.ini ao abrir um jogo naquele
  # core. Como nos remaps, um arquivo sem o cabecalho "# FliperOS" fica.
  for ini in "$src"/config/retroarch-switchres/*.switchres.ini; do
    name=$(basename "$ini" .switchres.ini)
    target="$home/.config/retroarch/config/$name/$name.switchres.ini"
    if [[ ! -f $target ]] || head -1 "$target" | grep -q '^# FliperOS'; then
      install -Dm644 "$ini" "$target"
    fi
  done
  chown -R 1000:1000 "$home/.config/retroarch" 2> /dev/null || true
  # Acervo em ~/roms; /opt/fliperos/roms vira um link para la, e os caminhos
  # antigos (mame.ini, frontends, Hypseus, OpenBOR) continuam valendo. Uma
  # instalacao com ROMs em /opt/fliperos/roms as leva junto: so renomeia
  # (mesmo disco), sem sobrescrever nada; se sobrar algo, fica onde esta.
  roms_merge() {
    local from=$1 to=$2 item
    mkdir -p "$to"
    for item in "$from"/* "$from"/.[!.]*; do
      [[ -e $item || -L $item ]] || continue
      if [[ ! -e $to/${item##*/} && ! -L $to/${item##*/} ]]; then
        mv "$item" "$to/"
      elif [[ -d $item && ! -L $item && -d $to/${item##*/} ]]; then
        roms_merge "$item" "$to/${item##*/}"
      fi
    done
    rmdir "$from" 2> /dev/null || true
  }
  # O mesmo com a BIOS: ~/bios e o system_directory do RetroArch.
  for dir in roms bios; do
    old="$root/opt/fliperos/$dir"
    mkdir -p "$home/$dir"
    if [[ -d $old && ! -L $old ]]; then
      roms_merge "$old" "$home/$dir"
    fi
    if [[ ! -e $old && ! -L $old ]]; then
      mkdir -p "$(dirname "$old")"
      ln -s "/home/fliperos/$dir" "$old"
    elif [[ ! -L $old ]]; then
      echo "warning: $old has files that also exist in ~/$dir; nothing was deleted" >&2
    fi
    chown 1000:1000 "$home/$dir" 2> /dev/null || true
  done
  # Flycast: o jogador 2 (porta B) com controle, que o padrao deixa sem, as
  # ROMs em ~/roms/dreamcast, a interpolacao linear desligada (o padrao dele
  # borra a imagem ao leva-la para o modo do tubo) e a classificacao de
  # transparencia por pixel (pvr.rend 3, OpenGL com OIT; o padrao e por
  # tira). So na primeira vez: depois o arquivo e dele.
  if [[ ! -f $home/.config/flycast/emu.cfg ]]; then
    install -Dm644 "$src/config/flycast-emu.cfg" "$home/.config/flycast/emu.cfg"
  fi
  # Num emu.cfg de antes, cada uma so muda se a opcao ainda nao esta gravada:
  # gravada (o Flycast grava todas ao fechar), a escolha e dele.
  if ! grep -q '^rend\.LinearInterpolation' "$home/.config/flycast/emu.cfg"; then
    bash "$src/config/fliperos-ini-set" "$home/.config/flycast/emu.cfg" config rend.LinearInterpolation no
  fi
  if ! grep -q '^pvr\.rend' "$home/.config/flycast/emu.cfg"; then
    bash "$src/config/fliperos-ini-set" "$home/.config/flycast/emu.cfg" config pvr.rend 3
  fi
  # A BIOS em ~/bios/dc (fliperos-roms), tambem num emu.cfg de antes dela.
  if ! grep -q '^Dreamcast.BiosPath' "$home/.config/flycast/emu.cfg"; then
    bash "$src/config/fliperos-ini-set" "$home/.config/flycast/emu.cfg" config Dreamcast.BiosPath /home/fliperos/bios/dc
  fi
  # As pastas dos arcades do Flycast (~/roms/naomi, naomi2, atomiswave, do
  # MAME ROM Cleaner) na lista de jogos dele, junto das que ja estao la.
  for dir in naomi naomi2 atomiswave; do
    grep -qE "^Dreamcast\.ContentPath = .*/home/fliperos/roms/$dir(;|\$)" "$home/.config/flycast/emu.cfg" ||
      sed -i -E "s|^(Dreamcast\.ContentPath = .*[^;[:space:]]);?[[:space:]]*\$|\1;/home/fliperos/roms/$dir|" \
        "$home/.config/flycast/emu.cfg"
  done
  chown -R 1000:1000 "$home/.config/flycast" 2> /dev/null || true
  # GroovyMAME: o que ele grava vai para ~/.mame (config/mame.ini). Antes ia
  # para a pasta de onde ele era aberto (a home, pelo menu): cfg, nvram e
  # companhia mudam para la, sem sobrescrever. O ~/snap fica: no Ubuntu e do
  # snapd.
  mkdir -p "$home/.mame"
  # Com as duas (um mame.ini de pastas relativas gravou na home depois),
  # cada arquivo fica na versao mais nova: e o mesmo arquivo do MAME, e o da
  # home costuma ser o do ultimo jogo.
  mame_merge() {
    local from=$1 to=$2 item
    for item in "$from"/* "$from"/.[!.]*; do
      [[ -e $item || -L $item ]] || continue
      if [[ ! -e $to/${item##*/} && ! -L $to/${item##*/} ]]; then
        mv "$item" "$to/"
      elif [[ -d $item && ! -L $item && -d $to/${item##*/} ]]; then
        mame_merge "$item" "$to/${item##*/}"
      elif [[ -f $item && -f $to/${item##*/} ]]; then
        if [[ $item -nt $to/${item##*/} ]]; then
          mv -f "$item" "$to/${item##*/}"
        else
          rm -f "$item"
        fi
      fi
    done
    rmdir "$from" 2> /dev/null || true
  }
  for dir in cfg nvram sta inp diff comments hiscore; do
    if [[ -d $home/$dir && ! -L $home/$dir && ! -e $home/.mame/$dir ]]; then
      mv "$home/$dir" "$home/.mame/$dir"
    elif [[ -d $home/$dir && ! -L $home/$dir && -d $home/.mame/$dir ]]; then
      mame_merge "$home/$dir" "$home/.mame/$dir"
    fi
  done
  chown -R 1000:1000 "$home/.mame" 2> /dev/null || true
  # Sem MOTD nem "Last login" entre o Plymouth e o setup/frontend.
  : > "$home/.hushlogin"
  # LXDE como o do GroovyArcade (ver config/lxde), com o papel de parede da
  # imagem esticado na tela (o CRT e 4:3 em qualquer modo).
  install -Dm644 "$src/config/wallpaper.jpg" "$root/usr/share/fliperos/wallpaper.jpg"
  mkdir -p "$home/.config"
  cp -r "$src/config/lxde/." "$home/.config/"
  # Layouts do Attract-Mode Plus (config/attractplus-layouts): os de
  # ~/.attract/layouts valem antes dos de /usr/share/attractplus de mesmo nome.
  mkdir -p "$home/.attract/layouts"
  for layout in "$src"/config/attractplus-layouts/*/; do
    layout=$(basename "$layout")
    rm -rf "$home/.attract/layouts/$layout"
    cp -r "$src/config/attractplus-layouts/$layout" "$home/.attract/layouts/$layout"
    chown -R 1000:1000 "$home/.attract/layouts/$layout" 2> /dev/null || true
  done
  chown 1000:1000 "$home/.attract" "$home/.attract/layouts" 2> /dev/null || true
  # Janelas e menus do Openbox no tema Dracula (fliperos-dracula.sh): o
  # openbox-lxde le ~/.config/openbox/lxde-rc.xml, que nasce da copia do
  # padrao do sistema; so o nome do tema muda, e a janela do Screen
  # Resolution abre maximizada (o Openbox a reajusta a cada troca de modo).
  # O do LXDE e do openbox-lxde-session; o do openbox puro fica de reserva.
  for rc in etc/xdg/openbox/LXDE/rc.xml etc/xdg/openbox/rc.xml; do
    [[ -f "$root/$rc" ]] || continue
    mkdir -p "$home/.config/openbox"
    sed -e '/<theme>/,/<\/theme>/ s|<name>[^<]*</name>|<name>Dracula</name>|' \
      -e 's|</applications>|  <application title="Screen Resolution"><maximized>yes</maximized></application>\n</applications>|' \
      "$root/$rc" > "$home/.config/openbox/lxde-rc.xml"
    break
  done
  chown -R 1000:1000 "$home/.zprofile" "$home/.bash_profile" "$home/.zshrc" "$home/.hushlogin" "$home/.config" 2> /dev/null || true
fi
# zsh como shell do usuario, se estiver na imagem (o root continua no bash).
if [[ -x "$root/usr/bin/zsh" ]]; then
  sed -i 's|^\(fliperos:.*:\)/bin/bash$|\1/usr/bin/zsh|' "$root/etc/passwd"
fi
# fliperos-setup sem senha tambem cobre o --session-start/--session-end que
# o fliperos-session chama em volta do launcher (governador da CPU).
cat > "$root/etc/sudoers.d/fliperos-setup" << 'EOF'
fliperos ALL=(root) NOPASSWD: /usr/local/bin/fliperos-setup, /usr/bin/setterm, /usr/bin/plymouth quit
EOF
chmod 440 "$root/etc/sudoers.d/fliperos-setup"

# Splash ate o FliperOS ter o que mostrar: quem tira o Plymouth e o
# fliperos-tty1, logo antes do launcher, do menu ou do aviso de update. O
# plymouth-quit do Ubuntu o tirava ao liberar os logins, e o login e a
# espera da rede do update ficavam ~16 s com a tela preta. Ele passa a ser
# a rede de seguranca (tira o splash 90 s depois, se nada o tirou), e o
# plymouth-quit-wait nao espera mais: o getty do tty1 e ordenado depois dele.
mkdir -p "$root/etc/systemd/system/plymouth-quit.service.d" \
  "$root/etc/systemd/system/plymouth-quit-wait.service.d"
cat > "$root/etc/systemd/system/plymouth-quit.service.d/fliperos.conf" << 'EOF'
[Service]
Type=exec
ExecStart=
ExecStart=-/bin/sh -c 'sleep 90; exec /usr/bin/plymouth quit'
EOF
cat > "$root/etc/systemd/system/plymouth-quit-wait.service.d/fliperos.conf" << 'EOF'
[Service]
ExecStart=
ExecStart=/bin/true
EOF
rm -f "$root/etc/sudoers.d/fliperos-installer"

# MOTD: ao entrar no shell, como abrir o menu (config/fliperos-motd, chamado
# pelo ~/.zshrc, pelo ~/.bash_profile e pelo fliperos-menu). O aviso de uma
# linha de antes, no /etc/profile.d, saia no boot, antes do launcher.
install -Dm755 "$src/config/fliperos-motd" "$root/usr/local/bin/fliperos-motd"
rm -f "$root/etc/profile.d/fliperos.sh"
