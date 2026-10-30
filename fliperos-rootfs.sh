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
# A interface grafica do Setup (lib/ui.sh a abre no menu do gabinete).
chmod 755 "$root/usr/local/lib/fliperos-setup/gui/fliperos-gui"
mkdir -p "$root/usr/local/bin" "$root/usr/local/sbin"
ln -sfn /usr/local/lib/fliperos-setup/fliperos-setup "$root/usr/local/bin/fliperos-setup"
install -Dm644 "$src/config/fliperos-setup.desktop" "$root/usr/share/applications/fliperos-setup.desktop"
# O changelog, para a tela What's new do Setup (lib/whatsnew.sh). Uma arvore
# sem ele deixa o que ja estava.
[[ ! -f $src/CHANGELOG.md ]] || install -Dm644 "$src/CHANGELOG.md" "$root/usr/local/share/fliperos/CHANGELOG.md"
# E as notas de cada update (updates/notes), que a mesma tela mostra debaixo
# do titulo dele.
if [[ -d $src/updates/notes ]]; then
  mkdir -p "$root/usr/local/share/fliperos/update-notes"
  cp "$src"/updates/notes/*.md "$root/usr/local/share/fliperos/update-notes/" 2> /dev/null || true
fi

# Diagnostico do modo ativo (alimenta o "Testing Results") e EDIDs por preset.
install -Dm755 "$src/fliperos-video-check.py" "$root/usr/local/bin/fliperos-video-check"
install -Dm755 "$src/config/fliperos-rebuild-edids" "$root/usr/local/sbin/fliperos-rebuild-edids"
# O EDID com os dois modos do console em pe (lib/video.sh vertical_edid).
install -Dm755 "$src/config/fliperos-edid-modes" "$root/opt/fliperos/bin/fliperos-edid-modes"
install -Dm755 "$src/config/fliperos-edid-hook" "$root/etc/initramfs-tools/hooks/fliperos-edid"

# ── Estado e sessao de boot ───────────────────────────────────────
mkdir -p "$root/etc/fliperos" "$root/etc/fliperos/mame" "$root/etc/fliperos/retroarch"
install -Dm644 "$src/config/fliperos-sessions.conf" "$root/etc/fliperos/sessions.conf"
# O frontend do FliperOS abre ao ligar (Setup > Games > Frontend troca).
[[ -f "$root/etc/fliperos/session" ]] || printf 'fliperos\n' > "$root/etc/fliperos/session"
chmod 755 "$root/usr/local/lib/fliperos-setup/gui/fliperos-frontend" "$root/usr/local/lib/fliperos-setup/gui/fliperos-scrape"
for name in fliperos-session fliperos-bootgame fliperos-kms-run fliperos-x11-run fliperos-x11-client fliperos-lxde fliperos-launch \
  fliperos-tty1 fliperos-ini-set fliperos-resolution fliperos-logout fliperos-escquit fliperos-powerkey fliperos-desktop-deflicker \
  fliperos-panning fliperos-automount fliperos-multiscreen fliperos-dlopen-links fliperos-browser fliperos-magnet; do
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
# O picom do autostart do pacote fica de fora do desktop: o fliperos-lxde
# poe /etc/fliperos/xdg antes no XDG_CONFIG_DIRS, e o do filtro de flicker
# (fliperos-desktop-deflicker) e o unico compositor.
install -Dm644 "$src/config/picom-autostart-hidden.desktop" "$root/etc/fliperos/xdg/autostart/picom.desktop"
# O FPS dos emuladores em Vulkan para o painel web: a camada implicita
# (config/fliperos-vkfps.c, compilada com o filtro de flicker; tambem o filtro), que so entra
# com FLIPEROS_VK_FPS=1 (o fliperos-kms-run e o fliperos-x11-client).
install -Dm644 "$src/config/fliperos-vkfps.json" "$root/usr/share/vulkan/implicit_layer.d/fliperos-vkfps.json"
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
# Uma tabela de antes de um programa (o Fightcade, o SM2-Emu, o DuckStation)
# ganha a linha dele, a do config/: sem ela o fliperos-x11-run o abriria em
# 320x240. A linha que ja existe, mudada pela pessoa ou nao, fica.
while IFS= read -r line; do
  grep -q "^${line%%[[:space:]]*}[[:space:]]" "$root/etc/fliperos/emulator-modes.conf" ||
    printf '%s\n' "$line" >> "$root/etc/fliperos/emulator-modes.conf"
done < <(grep -E '^[^#[:space:]]+[[:space:]]' "$src/config/fliperos-emulator-modes.conf")
# Model 2 no Wine: no PATH, para os frontends tambem chamarem.
install -Dm755 "$src/config/fliperos-model2" "$root/usr/local/bin/fliperos-model2"
# SM2-Emu: so o lancador. O fonte e o binario nascem em ~/.local/src na
# primeira abertura (config/fliperos-sm2emu), fora da imagem.
install -Dm755 "$src/config/fliperos-sm2emu" "$root/usr/local/bin/fliperos-sm2emu"
# Os patches que ele aplica no fonte antes de compilar. O que o upstream
# aceitou sai de config/sm2-emu-patches, e a pasta pode estar vazia.
rm -rf "$root/usr/local/share/fliperos/sm2-emu-patches"
install -d "$root/usr/local/share/fliperos/sm2-emu-patches"
for patch in "$src"/config/sm2-emu-patches/*.patch; do
  [[ ! -f $patch ]] || install -m644 "$patch" "$root/usr/local/share/fliperos/sm2-emu-patches/"
done
# Fightcade 2 (Setup > Games > Frontend): o que o baixa do site dele e o abre, e o
# openbox dele (Alt+Tab entre a sala de jogos e o emulador). O programa em si
# nao vem na imagem (codigo fechado).
install -Dm755 "$src/config/fliperos-fightcade" "$root/opt/fliperos/bin/fliperos-fightcade"
install -Dm644 "$src/config/openbox-fightcade.xml" "$root/etc/fliperos/openbox-fightcade.xml"
# EmulationStation-DE e Pegasus (Setup > Games > Frontend): nao vem na imagem. O
# Setup os compila no gabinete na primeira escolha, com a receita e os patches
# abaixo (a mesma receita da CI). O programa tem o nome do pacote: e o nome que
# escolhe a receita.
install -Dm755 "$src/config/fliperos-frontend-build" "$root/opt/fliperos/bin/fliperos-emulationstation"
install -Dm755 "$src/config/fliperos-frontend-build" "$root/opt/fliperos/bin/fliperos-pegasus"
install -Dm755 "$src/packaging/build-deb.sh" "$root/usr/local/share/fliperos/packaging/build-deb.sh"
for recipe in fliperos-emulationstation fliperos-pegasus; do
  install -Dm644 "$src/packaging/packages/$recipe.sh" "$root/usr/local/share/fliperos/packaging/packages/$recipe.sh"
done
rm -rf "$root/usr/local/share/fliperos/packaging/patches"
for patch in "$src"/packaging/patches/emulationstation/*.patch; do
  install -Dm644 "$patch" "$root/usr/local/share/fliperos/packaging/patches/emulationstation/${patch##*/}"
done
# Arcadeflow, o tema padrao do Attract-Mode Plus (Setup > Games > Frontend): o que o
# baixa do GitHub dele. O tema em si nao vem na imagem (sem licenca).
install -Dm755 "$src/config/fliperos-arcadeflow" "$root/opt/fliperos/bin/fliperos-arcadeflow"
# A arte das telas com nome proprio no menu dele (MAME 2010: a do MAME do tema
# com "2010" por cima), feita na maquina a partir da arte do tema.
install -Dm755 "$src/config/fliperos-arcadeflow-art" "$root/opt/fliperos/bin/fliperos-arcadeflow-art"
# As saidas dos jogos (porta 8000, o protocolo do MAMEHooker) para placas e
# LEDs: o helper que os lancadores chamam e a chave do PPA do LEDSpicer. O
# Hook Of The Reaper e o LEDSpicer em si vem pelo Setup > Games > Extras.
install -Dm755 "$src/config/fliperos-outputs" "$root/opt/fliperos/bin/fliperos-outputs"
install -Dm644 "$src/config/ledspicer-ppa.asc" "$root/usr/local/share/fliperos/ledspicer-ppa.asc"
# Wine, Steam, Heroic e o Pixelcade nao vem na imagem: o Setup > Games > Extras os
# instala.
install -Dm755 "$src/config/fliperos-extras" "$root/opt/fliperos/bin/fliperos-extras"
# Setup > Games > Emulators & Games: o estado de cada emulador e a instalacao dos que
# nao vem na imagem; o KOF Final Attack no Ikemen GO (config/fliperos-kof).
install -Dm755 "$src/config/fliperos-emulators" "$root/opt/fliperos/bin/fliperos-emulators"
install -Dm755 "$src/config/fliperos-kof" "$root/usr/local/bin/fliperos-kof"
# O DuckStation (PlayStation) tambem e de la: a licenca dele nao deixa
# redistribuir, e o config/fliperos-duckstation baixa o AppImage oficial.
install -Dm755 "$src/config/fliperos-duckstation" "$root/opt/fliperos/bin/fliperos-duckstation"
# Pixelcade (marquee de LED/LCD): o pixelweb e a arte sao baixados pelo
# Setup > Games > Extras para ~/pixelcade (codigo fechado). Daqui vem o que liga os
# frontends e os lancadores a ele, o servico (so sobe com o pixelweb
# baixado) e a regra da udev que o abre quando o marquee e conectado.
install -Dm755 "$src/config/fliperos-pixelcade" "$root/opt/fliperos/bin/fliperos-pixelcade"
install -Dm644 "$src/config/attractplus-plugins/Pixelcade/plugin.nut" \
  "$root/usr/local/share/fliperos/attractplus-plugins/Pixelcade/plugin.nut"
install -Dm644 "$src/config/fliperos-pixelcade.service" "$root/etc/systemd/system/fliperos-pixelcade.service"
install -Dm644 "$src/config/99-fliperos-pixelcade.rules" "$root/etc/udev/rules.d/99-fliperos-pixelcade.rules"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -sfn /etc/systemd/system/fliperos-pixelcade.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-pixelcade.service"
# O logo do FliperOS que o marquee (e o ZeDMD) mostra ao ligar, o servico do
# Pixelcade LCD ligado pela USB (aberto pela udev) e o do DOFLinx, os efeitos
# durante o jogo (so sobe com o Setup > Games > Extras > DOFLinx instalado).
install -Dm644 "$src/config/pixelcade-fliperos.png" "$root/usr/local/share/fliperos/pixelcade/fliperos.png"
install -Dm644 "$src/config/fliperos-pixelcade-lcd@.service" \
  "$root/etc/systemd/system/fliperos-pixelcade-lcd@.service"
install -Dm644 "$src/config/fliperos-doflinx.service" "$root/etc/systemd/system/fliperos-doflinx.service"
ln -sfn /etc/systemd/system/fliperos-doflinx.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-doflinx.service"
# ZeDMD (DMD de LED open source): os mesmos eventos, desenhados pelo
# fliperos-dmd. O dmdserver (libdmdutil) e o Pillow vem pelo Setup > Games > Extras.
install -Dm755 "$src/config/fliperos-dmd" "$root/opt/fliperos/bin/fliperos-dmd"
# O logotipo escrito de cada sistema no marquee, da fonte do tema Arcadeflow
# (que o Setup baixa: nada dele vem na imagem).
install -Dm755 "$src/config/fliperos-syslogo" "$root/opt/fliperos/bin/fliperos-syslogo"
# A abertura do ZeDMD: a animacao vetorial 3D do logo (tools/zedmd-vector-anim.py).
install -Dm644 "$src/config/zedmd-fliperos.gif" "$root/usr/local/share/fliperos/pixelcade/zedmd-fliperos.gif"
install -Dm644 "$src/config/fliperos-zedmd.service" "$root/etc/systemd/system/fliperos-zedmd.service"
install -Dm644 "$src/config/99-fliperos-zedmd.rules" "$root/etc/udev/rules.d/99-fliperos-zedmd.rules"
ln -sfn /etc/systemd/system/fliperos-zedmd.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-zedmd.service"
# O placar de uma partida versus no LED do gabinete: o programa que o le e
# conta as vitorias, a tabela de enderecos por jogo, o plugin do GroovyMAME
# que publica o placar como saidas e o Network Command Interface do RetroArch
# (junto so num jogo da tabela).
install -Dm755 "$src/config/fliperos-versus" "$root/opt/fliperos/bin/fliperos-versus"
install -Dm644 "$src/config/versus-games.conf" "$root/etc/fliperos/versus-games.conf"
install -Dm644 "$src/config/retroarch-versus.cfg" "$root/etc/fliperos/retroarch/versus.cfg"
for file in plugin.json init.lua; do
  install -Dm644 "$src/config/mame-plugins/fliperos-versus/$file" \
    "$root/usr/local/share/fliperos/mame-plugins/fliperos-versus/$file"
done
# groovymame: o atalho (config/fliperos-groovymame) na frente do binario do
# release, em /usr/local/libexec. Num sistema de antes, o binario compilado
# estava no lugar do atalho: muda de pasta.
gm="$root/usr/local/bin/groovymame"
if [[ -f $gm ]] && [[ $(head -c 4 "$gm" | od -An -c | tr -d ' ') == '177ELF' ]]; then
  mkdir -p "$root/usr/local/libexec"
  mv -f "$gm" "$root/usr/local/libexec/groovymame"
fi
install -Dm755 "$src/config/fliperos-groovymame" "$gm"
# Sem o "Initializing..." ao abrir o jogo: o texto vira vazio no binario do
# release (config/fliperos-groovymame-quiet; o build da imagem faz o mesmo
# ao instalar o GroovyMAME).
install -Dm755 "$src/config/fliperos-groovymame-quiet" "$root/opt/fliperos/bin/fliperos-groovymame-quiet"
[[ -f $root/usr/local/libexec/groovymame ]] &&
  python3 "$src/config/fliperos-groovymame-quiet" "$root/usr/local/libexec/groovymame" > /dev/null
# Jogos de 2 ou 3 telas com mais de um monitor: o numscreens de cada um, do
# XML do GroovyMAME (Setup > Video Setup > Multiple Monitors).
install -Dm755 "$src/config/fliperos-mame-screens" "$root/opt/fliperos/bin/fliperos-mame-screens"
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
# Setup > Games > Cleaner > MAME ROM Cleaner: o que sai de uma pasta de ROMs, pelo XML do MAME.
install -Dm755 "$src/config/fliperos-romclean" "$root/opt/fliperos/bin/fliperos-romclean"
# O sistema de cada set do FBNeo: o fliperos-kms-run abre os de console que
# estao soltos na pasta dos arcades.
install -Dm755 "$src/config/fliperos-fbneo" "$root/opt/fliperos/bin/fliperos-fbneo"
# Setup > Games > Downloader > Free games: homebrew de codigo aberto para as pastas de ~/roms.
install -Dm755 "$src/config/fliperos-freeroms" "$root/opt/fliperos/bin/fliperos-freeroms"
# Setup > Games > Scraper > progetto-SNAPS: as capturas dos jogos de arcade.
install -Dm755 "$src/config/fliperos-snaps" "$root/opt/fliperos/bin/fliperos-snaps"
# Setup > Games > Downloader: o romset e os CHDs por link magnetico, so o que o filtro
# do ROM cleaner escolhe. O servico so sobe quando um download e pedido, nunca
# no boot: o "enabled" de versoes anteriores sai.
install -Dm755 "$src/config/fliperos-downloader" "$root/opt/fliperos/bin/fliperos-downloader"
install -Dm644 "$src/config/fliperos-transmission.service" "$root/etc/systemd/system/fliperos-transmission.service"
rm -f "$root/etc/systemd/system/multi-user.target.wants/fliperos-transmission.service"
# O painel web (config/fliperos-web, Setup > System > Services > Web panel):
# sobe depois do boot (web=after no services.conf) ate a pessoa mudar.
install -Dm755 "$src/config/fliperos-web" "$root/opt/fliperos/bin/fliperos-web"
install -Dm644 "$src/config/fliperos-web.service" "$root/etc/systemd/system/fliperos-web.service"
rm -rf "$root/usr/local/share/fliperos/web"
install -Dm644 -t "$root/usr/local/share/fliperos/web" "$src"/config/web/*
grep -q '^web=' "$root/etc/fliperos/services.conf" 2> /dev/null ||
  echo 'web=after' >> "$root/etc/fliperos/services.conf"
# Desligar sem esperar 90 s pelo que ficou preso na sessao do tty1.
install -Dm644 "$src/config/fliperos-session-stop.conf" \
  "$root/etc/systemd/system/session-.scope.d/fliperos-stop.conf"
# Nem por um servico (do sistema ou do usuario) que nao sai no SIGTERM.
install -Dm644 "$src/config/fliperos-stop-timeout.conf" "$root/etc/systemd/system.conf.d/fliperos-stop.conf"
install -Dm644 "$src/config/fliperos-stop-timeout.conf" "$root/etc/systemd/user.conf.d/fliperos-stop.conf"
# Ligar mais rapido: o login automatico do tty1 nao espera a rede subir.
install -Dm644 "$src/config/fliperos-user-sessions.service" "$root/etc/systemd/system/systemd-user-sessions.service"
# O pam_lastlog saiu do Ubuntu 24.04, mas a linha dele ficou no login: um
# erro a cada login, nada mais.
if [[ -f "$root/etc/pam.d/login" && ! -e "$root/usr/lib/security/pam_lastlog.so" ]]; then
  sed -i '/^[^#]*pam_lastlog\.so/d' "$root/etc/pam.d/login"
fi
# O scrape automatico (config/fliperos-scrape.service, Setup > System >
# Services > Auto scrape): sobe depois do boot (scrape=after) ate a pessoa
# mudar, e segue com um jogo aberto.
install -Dm644 "$src/config/fliperos-scrape.service" "$root/etc/systemd/system/fliperos-scrape.service"
grep -q '^scrape=' "$root/etc/fliperos/services.conf" 2> /dev/null ||
  echo 'scrape=after' >> "$root/etc/fliperos/services.conf"
# A tela ao vivo no painel web (config/fliperos-stream): o go2rtc e o ffmpeg
# vem pelo Setup > Games > Extras > Live screen, que liga o servico.
install -Dm755 "$src/config/fliperos-stream" "$root/opt/fliperos/bin/fliperos-stream"
install -Dm644 "$src/config/fliperos-stream.service" "$root/etc/systemd/system/fliperos-stream.service"
# Setup > System > Lab mode: o painel web num endereco temporario da internet
# (o cloudflared vem da rede na primeira vez; config/fliperos-lab).
install -Dm755 "$src/config/fliperos-lab" "$root/opt/fliperos/bin/fliperos-lab"
# Setup > Video Setup > Video driver numa NVIDIA: o driver dela, do apt do
# Ubuntu, compilado pelo DKMS para o kernel 15 kHz (config/fliperos-nvidia).
install -Dm755 "$src/config/fliperos-nvidia" "$root/opt/fliperos/bin/fliperos-nvidia"
install -Dm644 "$src/config/fliperos-lab.service" "$root/etc/systemd/system/fliperos-lab.service"
install -Dm644 "$src/config/fliperos-downloader-magnets" "$root/usr/local/share/fliperos/downloader-magnets"
# Setup > Games > Scraper > Art packs by torrent: logos e videos de pacotes em
# torrent, so os dos jogos das pastas, pelo mesmo Transmission.
install -Dm755 "$src/config/fliperos-mediapacks" "$root/opt/fliperos/bin/fliperos-mediapacks"
install -Dm644 "$src/config/fliperos-media-torrents" "$root/usr/local/share/fliperos/media-torrents"
# Setup > Games > Downloader > Download BIOS: as BIOS que faltam aos jogos das
# pastas, uma a uma, do pacote de referencia (um torrent do archive.org).
install -Dm755 "$src/config/fliperos-bios" "$root/opt/fliperos/bin/fliperos-bios"
install -Dm644 "$src/config/fliperos-bios-pack" "$root/usr/local/share/fliperos/bios-pack"
# Updates sem ISO nova (patches do updates/index, em ordem), perguntados no
# boot pelo fliperos-tty1.
install -Dm755 "$src/config/fliperos-update" "$root/opt/fliperos/bin/fliperos-update"
# catver.ini, nplayers.ini e controls.xml do ROM cleaner (config/romclean):
# os desta pasta valem quando o romset nao traz os dele (lib/romclean.sh); e
# onde ele guarda o que leu do XML do MAME.
mkdir -p "$root/var/cache/fliperos"
for file in catver.ini nplayers.ini controls.xml flycast-controls.tsv; do
  install -Dm644 "$src/config/romclean/$file" "$root/usr/local/share/fliperos/romclean/$file"
done
[[ -f "$root/etc/fliperos/mame/mame.ini" ]] || install -Dm644 "$src/config/mame.ini" "$root/etc/fliperos/mame/mame.ini"
# Cores Dracula da interface do GroovyMAME; o ui.ini e do usuario porque o
# MAME o regrava quando a interface e personalizada pelo proprio menu.
[[ -f "$root/etc/fliperos/mame/ui.ini" ]] || install -Dm644 "$src/config/mame-ui.ini" "$root/etc/fliperos/mame/ui.ini"
# A tela de avisos ao abrir o jogo sai tambem num ui.ini de antes, que ja
# tem o skip_warnings 0 do -createconfig.
sed -i 's/^skip_warnings[[:space:]].*/skip_warnings             1/' "$root/etc/fliperos/mame/ui.ini"
# A nvram do MAME agora fica em ~/nvram/mame (config/fliperos-roms): os
# caminhos padrao de antes mudam junto; uma pasta escolhida pela pessoa fica.
[[ ! -f $root/etc/fliperos/mame/mame.ini ]] ||
  sed -i -E 's#^(nvram_directory[[:space:]]+)(\$HOME|/home/fliperos)(/\.mame)?/nvram/?[[:space:]]*$#\1$HOME/nvram/mame#' \
    "$root/etc/fliperos/mame/mame.ini"
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
  # do config/ (a BIOS em ~/bios/mame, a arte em ~/media/<tipo>/mame)
  # entram tambem na lista que ja existe, sem tirar as que estao la; as de
  # ~/.mame/scraped (o Scraper de antes do ~/media) e as de
  # ~/media/<tipo>/arcade (de quando a arte ficava por plataforma) saem.
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
          if (have[i] !~ /^[\/$~]/ || have[i] ~ /\/\.mame\/scraped\// || have[i] ~ /\/media\/[a-z]+\/arcade\/?$/) continue
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
# O sound portaudio de uma atualizacao de 2026-10-23 deixava o jogo mudo (o
# portaudio do MAME abre o hw: da placa): volta ao sdl do config/mame.ini.
sed -i -E 's/^(sound[[:space:]]+)portaudio[[:space:]]*$/\1sdl/' "$root/etc/fliperos/mame/mame.ini"
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

# ── Botao de desligar ─────────────────────────────────────────────
# Com um jogo aberto o botao fecha o jogo e volta ao frontend; sem jogo,
# desliga (config/fliperos-powerkey, pelo triggerhappy). O logind desligaria
# a maquina a cada aperto, com jogo aberto e tudo: aqui ele ignora o botao.
# Segurar o botao por 4 s segue cortando a energia (quem faz e a placa-mae).
install -Dm644 "$src/config/fliperos-power.triggers" "$root/etc/triggerhappy/triggers.d/fliperos-power.conf"
mkdir -p "$root/etc/systemd/logind.conf.d"
printf '[Login]\nHandlePowerKey=ignore\n' > "$root/etc/systemd/logind.conf.d/fliperos.conf"

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
# ~/splashscreen. Setup > System > Splash screen escolhe o do boot entre os de la.
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
# O tema do FliperOS segue o monitor em pe (lib/splash.sh splash_orientation):
# a copia nova volta a orientacao gravada (a imagem nova ainda nao tem o
# fliperos.conf).
orientation=$(sed -n 's/^orientation=//p' "$root/etc/fliperos/fliperos.conf" 2> /dev/null | tail -1) || orientation=""
if [[ $orientation == vertical-cw || $orientation == vertical-ccw ]]; then
  sed -i "s/^orientation = \"[^\"]*\";/orientation = \"$orientation\";/" "$root"/usr/share/plymouth/themes/*/*.script
fi
# JetBrains Mono, a fonte do tema de texto, tambem no initramfs (o hook).
rm -rf "$root/usr/share/fonts/truetype/fliperos"
install -Dm644 -t "$root/usr/share/fonts/truetype/fliperos" \
  "$src"/config/fonts/jetbrains-mono/*.ttf "$src/config/fonts/jetbrains-mono/OFL.txt"
install -Dm755 "$src/config/fliperos-initramfs-fonts" "$root/etc/initramfs-tools/hooks/fliperos-fonts"
# O nouveau e o firmware da NVIDIA fora do initramfs (105 MB a menos nele):
# o udev carrega o nouveau do disco, com o firmware de la.
install -Dm755 "$src/config/fliperos-initramfs-nvidia" "$root/etc/initramfs-tools/hooks/fliperos-nvidia"

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
# radeon ou amdgpu nas placas SI/CIK: so a linha do kernel escolhe
# (AMD_DRIVER_KEYS em fliperos-setup/lib/bootloader.sh); aqui so o dpm.
# Som HDA sempre ligado: com o power_save do kernel do Ubuntu (1 s) o codec
# desliga em silencio e religa no proximo som, e cada liga-desliga estala
# nas caixas (no gabinete, "puffs" com o menu parado).
cat > "$root/etc/modprobe.d/fliperos.conf" << 'EOF'
options radeon dpm=1
options snd_hda_intel power_save=0 power_save_controller=N
EOF
# O live-config do Debian criaria um usuario padrao no mesmo UID 1000.
ln -sf /dev/null "$root/etc/systemd/system/live-config.service"

# ── Latencia (docs/wiki/Latency.md) ───────────────────────────────
# O modo escolhido em Setup > System > Latency vale desde o boot.
install -Dm644 "$src/config/fliperos-latency.service" "$root/etc/systemd/system/fliperos-latency.service"
mkdir -p "$root/etc/systemd/system/multi-user.target.wants"
ln -sfn /etc/systemd/system/fliperos-latency.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-latency.service"

# ── Teste da troca de driver de video (Setup > Video Setup > Video driver) ─
# Sem confirmar a imagem no boot seguinte, volta ao driver anterior.
install -Dm644 "$src/config/fliperos-driver-trial.service" "$root/etc/systemd/system/fliperos-driver-trial.service"
ln -sfn /etc/systemd/system/fliperos-driver-trial.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-driver-trial.service"

# ── Servicos (Setup > System > Services, lib/services.sh) ─────────
# O Wi-Fi em "After boot"/"Off" desligado antes do NetworkManager; os "After
# boot" sobem depois da primeira tela (fliperos-services-screen.timer, ligado
# pelo fliperos-tty1) ou, sem tela, pelo timer de reserva.
for unit in fliperos-services.service fliperos-services-late.service fliperos-services-late.timer \
  fliperos-services-screen.timer; do
  install -Dm644 "$src/config/$unit" "$root/etc/systemd/system/$unit"
done
ln -sfn /etc/systemd/system/fliperos-services.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-services.service"
mkdir -p "$root/etc/systemd/system/timers.target.wants"
ln -sfn /etc/systemd/system/fliperos-services-late.timer \
  "$root/etc/systemd/system/timers.target.wants/fliperos-services-late.timer"
# O update do FliperOS: procurado em segundo plano depois da primeira tela
# (o --services-late liga o check) e aplicado ao desligar.
for unit in fliperos-update-check.service fliperos-update-shutdown.service; do
  install -Dm644 "$src/config/$unit" "$root/etc/systemd/system/$unit"
done
ln -sfn /etc/systemd/system/fliperos-update-shutdown.service \
  "$root/etc/systemd/system/multi-user.target.wants/fliperos-update-shutdown.service"
# O compartilhamento (o smbd e o nmbd, que sozinho levava uns 13 s no boot)
# sobe depois da primeira tela ate a pessoa mudar.
if ! grep -q '^samba=' "$root/etc/fliperos/services.conf" 2> /dev/null; then
  echo 'samba=after' >> "$root/etc/fliperos/services.conf"
  rm -f "$root/etc/systemd/system/multi-user.target.wants/smbd.service" \
    "$root/etc/systemd/system/multi-user.target.wants/nmbd.service"
fi
# Nada de apt nem man-db rodando sozinho no meio de uma partida (picos de
# CPU e disco). Atualizar fica no Setup > System > System Update, como no GA.
for timer in apt-daily.timer apt-daily-upgrade.timer man-db.timer; do
  ln -sfn /dev/null "$root/etc/systemd/system/$timer"
done
# O que o Ubuntu sobe no boot e um fliperama nao usa: o Samba como
# controlador de dominio (o compartilhamento e o smbd), o gpu-manager (placas
# hibridas de notebook; mexeria no Xorg que o Setup grava), o Ubuntu Pro e as
# noticias do MOTD pela rede.
for unit in samba-ad-dc.service gpu-manager.service ubuntu-advantage.service ua-reboot-cmds.service \
  ua-timer.timer motd-news.timer motd-news.service; do
  ln -sfn /dev/null "$root/etc/systemd/system/$unit"
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
  # O MAME 2010 le o teclado direto, e as teclas do painel sao as padrao do
  # MAME: cada botao chegava duas vezes (teclado e RetroPad), e o Buttons
  # layout so trocava uma delas. O default.cfg do core deixa os botoes so no
  # RetroPad (config/mame2010-default.cfg). Um sem o P4 Button 6 nosso (o
  # de antes, ou o que o menu do MAME gravou) e trocado.
  mame2010_cfg="$root/opt/fliperos/saves/retroarch/MAME 2010/mame2010/cfg"
  if [[ ! -f $mame2010_cfg/default.cfg ]] || ! grep -q JOYCODE_4_BUTTON6 "$mame2010_cfg/default.cfg"; then
    for dir in "$root/opt/fliperos/saves" "$root/opt/fliperos/saves/retroarch" \
      "$root/opt/fliperos/saves/retroarch/MAME 2010" "${mame2010_cfg%/cfg}" "$mame2010_cfg"; do
      [[ -d $dir ]] || install -d -o 1000 -g 1000 "$dir"
    done
    install -m644 -o 1000 -g 1000 "$src/config/mame2010-default.cfg" "$mame2010_cfg/default.cfg"
  fi
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
  # Texture Filtering em Force Nearest (1): o padrao (0) deixa o jogo filtrar
  # as texturas, que no tubo saem borradas. O Flycast grava o 0 ao fechar,
  # entao num emu.cfg de antes vale uma vez so (a marca em /var/lib); depois
  # a escolha e dele.
  if [[ ! -e $root/var/lib/fliperos/flycast-texture-nearest ]]; then
    if ! grep -qE '^rend\.TextureFiltering = [12]' "$home/.config/flycast/emu.cfg"; then
      bash "$src/config/fliperos-ini-set" "$home/.config/flycast/emu.cfg" config rend.TextureFiltering 1
    fi
    mkdir -p "$root/var/lib/fliperos" && : > "$root/var/lib/fliperos/flycast-texture-nearest"
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
  # A nvram nao entra: ~/nvram e a pasta dela (config/fliperos-roms), e o
  # ~/.mame/nvram e um link para dentro dela. Juntar as duas apagava tudo.
  for dir in cfg sta inp diff comments hiscore; do
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
  # No desktop, o atalho da pasta pessoal (roms, bios, media, config).
  [[ -d $home/Desktop ]] || install -d -o 1000 -g 1000 "$home/Desktop"
  install -m755 -o 1000 -g 1000 "$src/config/fliperos-home.desktop" "$home/Desktop/home.desktop"
  # E o da App Store (o mesmo do menu e do painel).
  install -m755 -o 1000 -g 1000 "$src/config/applications/org.gnome.Software.desktop" \
    "$home/Desktop/app-store.desktop"
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
