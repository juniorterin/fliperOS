# Changelog

O que mudou em cada ISO publicada em [Releases](https://github.com/juniorterin/fliperOS/releases), no formato dos releases do GroovyArcade. A seção de cada versão é o texto do release dela: o `tools/release-publish.sh` não publica uma ISO sem a seção.

## 0.7

Primeira ISO publicada. As mudanças são em relação à 0.6, que não saiu daqui.

**Mudanças no sistema:**

- Kernel 15 kHz: kernel.org 6.18.54 LTS com os patches D0023R, os do `linux-15khz` do GroovyArcade
- Limine no lugar do GRUB, na ISO (híbrida, BIOS e UEFI) e no disco instalado
- Menu de boot com as entradas do GroovyArcade: 15, 25 e 31 kHz, LCD, Intel e NVIDIA em super resolução, NTSC, PAL e EDID
- Boot sem texto, direto ao splash, e console calado depois dele
- Rede no sistema instalado: DNS do DHCP, cabo pelo NetworkManager e relógio pela rede
- Pastas em `~`: `roms`, `bios`, `media` e `config`, também pela rede (Samba)
- Som: codec HDA sempre ligado (sem estalos com o menu parado) e teclas de volume em qualquer tela
- Desktop LXDE com tema Dracula, Alacritty como terminal, App Store (GNOME Software com Flathub), Falkon e Transmission
- Desconectar do LXDE abre o menu do FliperOS
- Terminal zsh com Oh My Zsh e tema Dracula
- Drivers de entrada por DKMS: GunCon 2, volantes Thrustmaster (`hid-tmff2`) e Logitech (`new-lg4ff`)
- Mapeamento do SDL completado para qualquer controle ligado

**Mudanças nos pacotes:**

- GroovyMAME: release oficial `gm0289sr222f` (MAME 0.289, Switchres 2.22f) em vez de compilar
- GroovyMAME: `mame.ini` como o do GroovyArcade, num Xorg próprio com `modesetting 1`, na resolução nativa de cada jogo
- RetroArch: CRT SwitchRes ligado, 6 cores na imagem e o Core Downloader liberado
- RetroArch: perfil automático para painel e encoder, remap dos cores de MAME, entrada e controle em linuxraw
- RetroArch: vídeo glcore e áudio sdl2 por padrão, sem notificações na tela
- MAME 2010: compilado sem `_FORTIFY_SOURCE` (Tekken Tag não abria)
- Flycast, PCSX2, Dolphin, Supermodel, Hypseus Singe e Model 2: no 15 kHz abrem em 640x240 progressivo, esticado a 200%, nunca em 480i
- PCSX2 pelo AppImage oficial; Supermodel pelo Makefile do projeto; Model 2 no Wine
- Flycast: direcional do painel no D-pad, interpolação linear desligada, transparência por pixel
- PCSX2: sem o assistente, em Big Picture, vsync, sem o ponteiro do mouse, BIOS em `~/bios/ps2` e jogos em `~/roms/ps2`
- Supermodel: abre pelo menu (escolha do jogo), acha a lista de jogos, botões do Button mapping; pasta `model3` nos frontends
- OpenBOR em tela cheia de fábrica
- Steam e Heroic (GOG, Epic, Amazon) no desktop
- Frontends: Attract-Mode Plus, EmulationStation (ES-DE) e Pegasus em `.deb`, num repositório APT dentro da imagem, com os jogos já configurados
- Tema FliperOS 240p para o EmulationStation e o Pegasus
- Fightcade 2 como opção de frontend, baixado do site dele; cada partida no modo do emulador dela
- Attract-Mode: tela nova já nasce com a lista de jogos da pasta
- Skyscraper 3.21.0, Gum 2.0.2 (setas na paginação e sons do menu), AntiMicroX 3.6.1, Switchres 2.2.1

**Mudanças no fliperos-setup:**

- Novo: o equivalente do gasetup, em Bash e Gum, com tema Dracula, feito para 640x480i (80x30)
- Teste das saídas de vídeo com voz e *Testing Results*, portados do gatools
- Instalação no HD/SSD e Recovery Mode
- Video Setup: monitor, orientação, resolução, geometria e Reset Geometry
- Audio Setup como o do GroovyArcade, e sons do menu com os WAV da pessoa
- Network Setup: Wi-Fi pela lista de redes ou rede oculta
- Frontend: escolhe o launcher do boot e instala o que não veio na imagem
- Latency: modos Standard e Low latency, com a conferência do hardware
- Scraper: capas, vídeos e textos para todos os frontends, com a escolha dos tipos de mídia
- MAME ROM Cleaner (parâmetros de marcar, como o ROMLister; Flycast; pasta da rede) e MAME CHD Cleaner
- Free games: homebrew de código aberto para preencher os frontends
- Joysticks: Button mapping para todos os emuladores (RetroArch, GroovyMAME, Flycast e Flycast Dojo, PCSX2, Dolphin, Supermodel, Hypseus Singe, OpenBOR), calibração de pistola e volante, joysticks na porta paralela
- Quirks do `usbhid` para controles USB
- Controle do gabinete nos menus
- Debug mode e System Update; o Setup espera a trava dos pacotes em vez de falhar
- Start frontend e Start desktop pelo tty1 (o desktop não abria pelo menu)

**Mudanças nas ferramentas:**

- `tools/vm-test.py`: instala em QEMU e boota o disco em BIOS e UEFI; fotografa as telas; modo `dev` com gamepad falso
- `tools/verify-iso.sh`: auditoria só de leitura da ISO gerada
- `tools/cabinet-push.sh`: atualiza um gabinete pela rede, sem ISO nova
- Documentação na wiki (`docs/wiki`, `tools/wiki-publish.sh`) e num HTML só (`tools/render-docs.py`)
- `tools/release-publish.sh`: publica a ISO em Releases com este changelog
