# FliperOS 0.7 — instalador para gabinetes CRT, no estilo do GroovyArcade

Ubuntu 24.04 amd64 com o **kernel 15 kHz** (kernel.org 6.18 LTS + patches D0023R, os mesmos do `linux-15khz` do GroovyArcade). A mídia é **só de instalação** e segue o fluxo do GroovyArcade: menu de boot com a faixa de frequência, teste das saídas de vídeo com voz, *Testing Results*, menu **FliperOS Setup** e instalação no HD/SSD com barra de progresso. No sistema instalado, o mesmo programa vira o menu de configuração que aparece quando o frontend fecha.

As telas são do **`fliperos-setup`**, em Bash com [Gum](https://github.com/charmbracelet/gum) (Charmbracelet, feito sobre Bubble Tea), tema **Dracula** e textos em inglês, como no GroovyArcade. Pensadas para **640x480i**: 80x30 caracteres, nada animado nem piscando.

> 15 kHz foi validado no gabinete com a versão anterior (kernel padrão + EDID, 640x240). O kernel 15 kHz, o 640x480i, o teste de saídas e o instalador desta versão foram validados em VM (QEMU); o gabinete real ainda precisa confirmar.

## 1. Gravar a mídia

Grave a ISO **byte a byte** num pendrive e desative o Secure Boot (o kernel 15 kHz é próprio, não assinado).

A ISO usa o bootloader **Limine** e é **híbrida** (`xorriso` + `limine bios-install`): a mesma imagem boota como CD e como pendrive, em BIOS e em UEFI. Gravadores que reconstroem a estrutura de boot a quebram — **Rufus no modo padrão ("ISO image"), Ventoy e UNetbootin não servem**. Use o **balenaEtcher**, ou o Rufus em "DD Image mode", ou `dd`:

```bash
sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Confirme o `/dev/sdX` com `lsblk` antes: o dispositivo errado apaga o disco errado.

## 2. Menu de boot

As mesmas opções do GroovyArcade (`os/groovyarcade/syslinux/syslinux.cfg`). Aqui só se escolhe em que faixa o Linux sobe; a saída e o monitor são decididos depois, pelo teste de saídas.

| Entrada | Parâmetros | Para |
| --- | --- | --- |
| **15 kHz** (padrão) | `video=640x480iS` | Monitor arcade ou TV, 640x480 entrelaçado |
| 25 kHz | `video=512x384S` | Monitor de média resolução |
| 31 kHz | `video=640x480S` | Monitor de alta resolução |
| SVGA / LCD monitor | — | Monitor de PC ou LCD (vale o EDID dele) |
| Intel 15 kHz | `video=1280x480iS i915.no_ytiled_scanout=1` | Intel: super resolução; o parâmetro é do patch 09 e liga o entrelaçado na Gen9 |
| NVIDIA 15 kHz | `video=1280x480iS` | NVIDIA: super resolução |
| NTSC | `video=720x480iS` | TV NTSC |
| PAL | `video=768x576iS` | TV PAL |
| EDID progressive | `drm.edid_firmware=edid/generic_15_super_resp.bin video=e` | EDID do Switchres, todas as saídas forçadas |
| EDID interlaced | `drm.edid_firmware=edid/generic_15_super_resi.bin video=e` | Idem, entrelaçado |

O `S` no fim do modo é do patch 15 kHz: usa a tabela fixa de modos de baixo dotclock do kernel (`drm_modes_low_dotclock.c`), e o `i` é entrelaçado. Todas as entradas levam `quiet splash consoleblank=0` e o `radeon` nas placas SI/CIK.

**Timer de 30 segundos.** Sem tecla, sobe a entrada **15 kHz**, que é a segura para um gabinete: um LCD recebendo 15 kHz só mostra "fora de faixa", mas 31 kHz num tubo só de 15 kHz pode danificá-lo.

O menu em si **não aparece num CRT de 15 kHz** — ele sai no modo texto do firmware (~31 kHz), antes do kernel. É o mesmo no GroovyArcade. Para escolher outra entrada num gabinete só de 15 kHz, ligue um LCD temporariamente; com o CRT, espere os 30 s. A primeira coisa legível no tubo é o splash, já no modo de boot.

## 3. Teste de saídas e *Testing Results*

Portado do `gatools` (`video/video.sh`): assim que a mídia sobe, o `fliperos-setup`:

1. força ligadas as saídas analógicas ("Lights on") e explica o teste, falando pelo `espeak-ng`;
2. apaga todas as saídas e liga **uma de cada vez**, escrevendo `on`/`off`/`detect` em `/sys/class/drm/cardN-CONECTOR/status` (analógica sem monitor detectado é forçada; digital sem nada ligado é pulada);
3. em cada uma, diz em voz "Testing output V G A 1. If you can see this screen, press Enter." e mostra *"If you can see this screen clearly, press ENTER."* por 10 s;
4. **no primeiro ENTER para** e vai para a tela *Testing Results* (o gatools testa todas e escolhe a melhor; aqui quem está olhando para a tela já decidiu). Sem ENTER, repete a volta até três vezes.

Com duas placas, o console é levado para o framebuffer da placa testada (`con2fbmap`), como no gatools.

A tela **Testing Results** mostra GPU, driver, conector, modo atual e frequência horizontal (lidos do CRTC ativo pelo `fliperos-video-check`), se a placa gera dotclock baixo, se há modo entrelaçado, EDID, se o monitor foi identificado e se a saída será forçada no boot — com as mesmas frases do `inform_user` do gatools — e oferece **Validate settings** ou **Repeat test**.

Validado, vale o `configure_from_connector` do gatools:

- EDID do Switchres (dongle) → o monitor vem do próprio EDID;
- sem isso, o tipo de monitor é **obrigatório** (a lista abre na sugestão da entrada de boot);
- a linha do kernel sai do monitor: `video=VGA-1:640x480iSe` (o `e` quando foi preciso forçar a saída); placa sem dotclock baixo (Intel, NVIDIA) → super resolução `1280x480iS` e `dotclock_min 25.0` no Switchres; APU → `interlace_force_even 1`; boot por EDID → `drm.edid_firmware=CONECTOR:edid/<monitor>.bin`; LCD → nada (vale o EDID dele).

Tudo é gravado em **`/etc/fliperos/fliperos.conf`** (GPU, driver, conector, detecção, monitor, faixa, modo de boot, parâmetros do kernel, orientação, launcher), o equivalente do `ga.conf`, e no `switchres.ini`/`mame.ini`.

## 4. FliperOS Setup

Menu da mídia (o `isomainmenu` do gasetup): **Install to HD/SSD**, **Recovery Mode**, **Terminal** e **Shutdown**. O título mostra o host e o IP.

### Install to HD/SSD

1. **Do you want to configure video?** — *Yes* abre o **Video Setup**:
   - **Monitor Type**: os 29 presets do Switchres, na lista do gatools;
   - **Monitor Orientation**: horizontal, vertical horário, vertical anti-horário (console girado com `fbcon=rotate`, `panel_orientation` no `video=`, `ror`/`rol` do MAME e o desktop pelo `xrandr`);
   - **Resolution**: só os modos da tabela do kernel que a faixa do monitor e a placa aceitam (sem dotclock baixo, só as super resoluções), mais **resolução personalizada**: testa no `grid` do Switchres e gera um EDID (`switchres -e`), como o `worker_custom_video_mode`;
   - **Geometry**: o mesmo **`geometry`** do GroovyArcade — o `geometry.py` do Switchres, que desenha o grid e devolve o `crt_range`, gravado como `monitor custom` no `/etc/switchres.ini`. O grid sai na resolução escolhida acima, com o refresh dela (50 Hz nos modos PAL; sem escolha, 640x480). Para baixo a imagem só anda enquanto houver linhas em branco abaixo dela (o Switchres não passa do *front porch*); quando parar, o ajuste é o **V-POS** do monitor.
2. **Automatically Partition** — lista os discos pelo **modelo, tamanho, caminho e barramento** (USB/NVMe/SATA). Não aparecem: a própria mídia de instalação, discos com menos de 16 GiB, montados ou em swap, com RAID/LVM/criptografia ou dependentes ativos — cada um com o motivo, acima da lista. **My drive is not listed (details)** mostra tudo o que o Linux enxerga (o `lsblk`, as controladoras e as mensagens do kernel): um HD/SSD que nem ali aparece está escondido antes do Linux, quase sempre pelo modo SATA da BIOS em RAID/Intel RST (troque para AHCI) ou pelo Intel VMD.
3. **WARNING** — modelo, caminho e tamanho do disco que será apagado; *No* volta para a escolha do disco. Se o disco já tem FliperOS, o aviso sugere o Recovery Mode.
4. **Installing FliperOS** — uma tela só, com o disco de destino, barra de progresso **real** (a cópia do sistema vem do percentual do `unsquashfs`, como o `dialog --gauge` do gasetup), a etapa e mensagens curtas. A saída dos comandos vai para `/var/log/fliperos-setup.log`. Em erro: etapa, erro, **View log / Retry / Return**.
5. **Installation completed successfully. Remove the installation CD/DVD/USB.** — e **Reboot now?**

Particionamento: GPT, BIOS boot de 1 MiB, ESP FAT32 de 1 GiB, o resto em ext4. As partições novas têm as assinaturas antigas apagadas e a de BIOS boot é zerada (um resto de sistema de arquivos do disco anterior ali fazia o `limine bios-install` recusar; ele também roda com `--force`). O Limine é instalado para BIOS (estágio 2 na partição BIOS boot) e para UEFI (`EFI/BOOT/BOOTX64.EFI`, o caminho removível), sem mexer na NVRAM. O Limine só lê FAT, então kernel e initrd ficam **na ESP** (`/boot/efi/fliperos/`), mantidos pelo `fliperos-limine-update` — o equivalente do `update-grub`, chamado pelos hooks de kernel e de initramfs. Os parâmetros do kernel ficam em `/etc/default/fliperos-boot`.

O disco novo leva o que foi decidido na mídia: `fliperos.conf`, Switchres, MAME, Xorg, a linha do kernel, as redes Wi-Fi configuradas e a placa de som.

### Recovery Mode

Procura discos com FliperOS (partição `FliperOS` com o marcador `/etc/fliperos/installed`) e oferece: terminal dentro do sistema instalado (`chroot`, o `rescue_mode` do gasetup), **reinstalar o bootloader** (o "Fix UEFI boot", para BIOS e UEFI), **aplicar o vídeo desta sessão** (placa de vídeo trocada) e **restaurar os arquivos do sistema** a partir da mídia, preservando ROMs, saves, home, rede, áudio e vídeo.

## 5. Sistema instalado

**Boot sem texto:** do Limine direto ao Plymouth. O menu do Limine fica escondido (`quiet: yes`; uma tecla nos 3 segundos dele o mostra, com a entrada de diagnóstico), o kernel e o udev ficam calados (`quiet loglevel=3 rd.udev.log_level=3 udev.log_level=3`), o cursor do console some (`vt.global_cursor_default=0`, e volta no shell) e o login automático não escreve nada (`agetty --skip-login --noissue`, `~/.hushlogin`) e o console continua calado depois do boot (`kernel.printk = 3 4 1 3` em `/etc/sysctl.d/99-fliperos-console.conf`: o `10-console-messages.conf` do Ubuntu voltava o nível para 4 e um erro do kernel depois do Plymouth, como o do codec HDMI da Intel sem uso, aparecia na tela).

O tty1 faz o login sozinho e segue o fluxo do `.bash_profile` do GroovyArcade (`config/fliperos-tty1`, chamado pelo `~/.zprofile`): abre o **launcher padrão** e, quando ele fecha, o **menu do FliperOS**. O menu é um laço: **Start frontend** e **Start desktop** fazem o setup sair e o `fliperos-tty1` abre o launcher no próprio tty1, como no boot, e volta ao menu quando ele fecha. O setup roda como root dentro do pseudo-terminal do `sudo`; aberto de lá, o X não tem o tty1 como terminal e não consegue trocar de VT (`xf86OpenConsole: VT_ACTIVATE failed`) — era o "desktop não inicia" do gabinete. Se o X cair ao abrir, os erros do log dele ficam na tela até o Enter (cópia em `/opt/fliperos/logs/Xorg-failed.log`). O shell do usuário é o **zsh com Oh My Zsh** e o tema Dracula (seção 6); o `~/.bash_profile` chama o mesmo fluxo, para quem voltar ao bash.

**Controle nos menus:** com o menu do setup na tela, o controle faz as vezes do teclado — direcional, hat ou analógico = setas (repetem segurando), botão 1 / A / Start = Enter, botão 2 / B / Select = Esc, botão 3 / X / Y = Espaço (marca nas listas de marcar), L / R = Page Up / Page Down. Vale para encoders de fliperama (eixo digital 0–255), gamepads e joysticks USB; pistolas de luz ficam de fora (mirar andaria pelo menu). O serviço `fliperos-padkeys` (Python puro, `uinput` do kernel) só traduz enquanto existe `/run/fliperos/padkeys`, que o setup cria ao abrir e apaga ao sair: frontends, emuladores e o desktop leem o controle sozinhos, sem botão valendo duas vezes.

**Primeiro boot:** *Choose default launcher*, com a lista gerada dos launchers instalados de fato (Attract-Mode Plus, RetroArch, EmulationStation..., LXDE) e o próprio *FliperOS Setup*. Muda depois em Setup > Frontend.

**Menu principal** (o `mainmenu` do gasetup; o título mostra `host (IP) - N% used on /`):

- **Start frontend**
- **Setup (video, audio, network...)**
  - **Video Setup** — o mesmo da instalação; grava a linha do kernel e oferece reiniciar;
  - **Audio Setup** — placa padrão (`/etc/asound.conf`), volume, AlsaMixer, **MAME audio latency** (`audio_latency` do `mame.ini`, 0.0 a 50.0, 0 = padrão; o "Audio Latency MAME" do GA) e teste de som. Como no GA, o volume move `Master`/`Front`/`Speaker`/`Headphone` e deixa o `PCM` no máximo (placa só com `PCM` usa o `PCM`). O codec HDA fica sempre ligado (`options snd_hda_intel power_save=0 power_save_controller=N`): com o `power_save` de 1 s do kernel do Ubuntu ele desligava em silêncio e religava no próximo som, e cada liga-desliga estalava nas caixas ("puffs" com o menu parado). Não há servidor de som: RetroArch (`audio_driver = alsa`), GroovyMAME (`sound sdl`) e os emuladores SDL (`SDL_AUDIODRIVER=alsa`) tocam direto no ALSA, então esse volume vale para todos, em KMS ou X. **Menu sounds**: o gum do FliperOS (`patches/gum/0002-sons-do-menu.patch`) toca um WAV quando o cursor anda e outro no Enter, como na tela de seleção de um jogo (o Street Fighter Alpha 2, por exemplo), nos menus e nas perguntas sim/não do Setup (`aplay`; um som novo corta o que ainda toca, e o do Enter continua depois que o menu fecha). Os sons são da pessoa — o FliperOS não traz sons de jogo: `move.wav` e `select.wav` em `/opt/fliperos/sounds/menu` (na rede, o compartilhamento FliperOS, pasta `sounds/menu`). Com um deles lá, liga sozinho; o item do Audio Setup desliga e liga (`menu_sounds` no `fliperos.conf`);
  - **Network Setup** — Wi-Fi pela lista de redes (com sinal) ou **rede oculta digitando o SSID**; ao conectar, o IP aparece no título, ao lado do uso do disco;
  - **Frontend** — o launcher padrão; um que não está instalado pode ser instalado do repositório do FliperOS, que vem dentro da imagem (`/opt/fliperos/repo`, seção 13). O que ainda não tem pacote aparece como *not available yet*. O **Fightcade 2** não vem de pacote: é baixado na hora do site dele (seção 12, "Fightcade 2"). **Em 240p**: num monitor de 15 kHz os frontends rodam em 320x240, e o padrão de cada um é desenhado para 720 linhas ou mais — o texto fica com 4 a 8 pixels. Por isso o Setup já deixa gravado, uma vez só (o que for mudado depois no próprio frontend fica; com o frontend aberto, fica para a vez seguinte): os dois ganham um tema **FliperOS 240p**, feito para 240 linhas e nas cores do Dracula: o sistema em cima, a lista dos jogos em letra de 12 pixels, a imagem do jogo com ano, produtora e descrição. No **EmulationStation** (ES-DE) é o `config/esde-theme-fliperos`, instalado em `/usr/share/es-de/themes/fliperos-240p-es-de` (`Theme` no `es_settings.xml`), sem o desfoque do fundo do menu e sem o aviso de versão nova: os sistemas numa lista de nomes, o vídeo do jogo (se houver) no lugar da imagem, e no rodapé só os botões que cabem em 320 pixels. Nos temas que o ES-DE traz, mesmo com a fonte grande, a letra da lista é fina e de pouco contraste e a ajuda do rodapé fica com uns 6 pixels. No **Pegasus** é o `config/pegasus-theme-fliperos`, instalado em `/usr/share/pegasus-frontend/themes` — esquerda/direita trocam de sistema, L2/R2 pulam dez jogos. O Grid, o tema padrão do Pegasus, em 320x240 mostra as capas mas deixa a descrição com 4 pixels;
  - **Latency** — modo **Standard** (qualquer máquina) ou **Low latency** (CPUs modernas), com a conferência desta máquina contra a recomendação e a lista do hardware ideal (seção 9, Latência);
  - **Scraper** — capas, screenshots, logos, vídeos e informações de cada ROM, com o **Skyscraper** (o mesmo que o GroovyArcade empacota), de ScreenScraper, ArcadeDB ou TheGamesDB. **O que buscar** é de marcar: capturas (`snap`), logos, capas (`box`), marquees, descrições (`texto`) e vídeos (`preview`, desmarcados de início: ocupam muito mais). O Skyscraper só baixa os tipos marcados (`--flags noscreenshots,nocovers,nowheels,nomarquees` e `videos`) e só exporta esses; a escolha fica guardada. Um tipo de arte que a pasta ainda não tinha faz buscar de novo os jogos que já estão no cache (`--refresh`): sem isso o Skyscraper não volta a eles. Entram as pastas com jogos (o `_info.txt` de cada uma não conta) que o FliperOS sabe abrir: `~/roms/mame`, `dreamcast`, `ps2`, `dolphin` e as dos cores do RetroArch (`~/roms/retroarch/<core>`, pela plataforma do `systemid` do `.info` do core). A arte e os textos vão para **`~/media/<tipo>/<sistema>`** (seção 12, "BIOS, arte e configurações em `~`"): o Skyscraper grava cada tipo numa subpasta de nome fixo (`screenshots`, `covers`, `wheels`, `marquees`, `videos`), e para ele `~/media/.skyscraper/<sistema>` tem links com esses nomes para `snap`, `box`, `logo`, `marquee` e `preview`; as descrições saem da lista gerada para `~/media/texto`. A lista vai para o frontend. Com o **GroovyMAME** de launcher padrão, a pasta do MAME só ganha a arte: o `mame.ini` e o `ui.ini` já procuram em `~/media/<tipo>/arcade` (a primeira `snapshot_directory` continua sendo a do F12). No **ES-DE** (o EmulationStation do FliperOS) a lista vai para `~/ES-DE/gamelists/<sistema>` (formato `esde` do Skyscraper, caminhos relativos) e a `MediaDirectory` é `~/media/.es-de`, com um link por tipo do ES-DE (`screenshots`, `covers`, `marquees` = logo, `videos`) para `~/media`. A arte de antes (`~/.mame/scraped/mame`, `~/.attract/scraped/<pasta>`, `<pasta das ROMs>/media`) vai para `~/media` no `tools/cabinet-update.sh` e ao raspar a pasta. As imagens saem cada uma como veio (captura, capa, logo, marquee; o `artwork.xml` do Setup), e não montadas umas sobre as outras como no padrão do Skyscraper. **Clones**: na pasta do MAME o Setup pergunta se busca também os clones dos jogos que existem (`groovymame -listclones`: mvscu, mvscj...), que num romset merged estão dentro do zip do pai e não têm arquivo — a pasta raspada passa a ser uma de referências em `~/.cache/fliperos-scraper` (links para as ROMs e um arquivo pequeno por clone). **Retomada**: o Skyscraper só grava o cache no fim de cada execução, então os jogos vão em lotes de 20 (`--includefrom`) e o trabalho fica anotado em `/var/lib/fliperos/scraper` (pastas que faltam, os arquivos de cada uma já gravados, a fonte e a conta, só para o root); desligou ou fechou no meio, o Setup > Scraper oferece retomar do lote em que parou. No **Attract-Mode Plus** (o do launcher padrão, ou sem frontend escolhido, se estiver instalado) o Setup cria, como o `efc.sh` do GroovyArcade, o emulador que faltar em `~/.attract/emulators` — com o comando que abre o jogo (`fliperos-x11-run groovymame [name]`, `fliperos-kms-run retroarch -L <core>`, `fliperos-x11-run flycast/pcsx2/dolphin-emu`) e a arte em `~/media/<tipo>/<sistema>` — e a tela dele no `attract.cfg` (tema AdvanceMenu); o Skyscraper grava a romlist em `~/.attract/romlists` e as descrições em `~/.attract/scraper/<emulador>/overview`, um link para `~/media/texto/<sistema>`. No Pegasus, o `metadata.pegasus.txt` fica na própria pasta das ROMs, apontando para a arte em `~/media`. O que já existe (tela, emulador mudado no Attract-Mode) não é regravado — o emulador criado pelo Setup é refeito, para a arte passar a `~/media` —, e um sistema que falha não para os outros;
  - **MAME ROM Cleaner** — de uma pasta com um romset do MAME, **copia** (ou move) para a pasta do emulador os jogos que passam nos filtros, com o pai, a BIOS e os dispositivos de que eles precisam. Funciona como o [ROMLister](https://www.waste.org/~winkles/ROMLister/): junta o XML da versão do MAME do romset com o `catver.ini` (categorias e jogos adultos), o `nplayers.ini` (como se joga a dois) e o `controls.xml` do Controls.dat (os botões que o jogo usa de verdade), e filtra pelo que o gabinete tem. **Onde está o romset**: numa pasta desta máquina (disco, pendrive; o navegador de pastas do próprio menu: Enter abre, `..` volta, **Use this folder** escolhe) ou numa **pasta compartilhada da rede** (Windows, NAS: o Setup pergunta o computador, o usuário, a senha e lista as pastas compartilhadas dele; ela é montada só para leitura em `/mnt/network` com o `cifs-utils`, a senha vai num arquivo que só o root lê, nunca na linha de comando, e só fica guardada, em `/etc/fliperos/netshare.cred`, se a pessoa pedir — `lib/netshare.sh`). Assim o romset inteiro fica no computador da casa e o gabinete pega só o que usa. **Para que emulador**: **GroovyMAME** (o XML é o `groovymame -listxml`; os jogos vão para `~/roms/mame` e as BIOS e os dispositivos para `~/bios/mame`, que também está no `rompath`: fora da pasta dos jogos eles não aparecem como jogo nos frontends), **Flycast** (o mesmo romset e o mesmo XML, só os sistemas dele: **Naomi**, **Naomi 2** e **Atomiswave**, cada um na sua pasta, `~/roms/naomi`, `~/roms/naomi2` e `~/roms/atomiswave`, com as BIOS — `naomi.zip`, `naomi2.zip`, `awbios.zip` e as especiais — em `~/bios/dc` e sem os dispositivos do MAME, que o Flycast não usa; o sistema de um set é o da primeira BIOS na cadeia de `romof`), **MAME 2010** (0.139, o do core `mame2010` do RetroArch; o XML vem na imagem em `/usr/local/share/fliperos/mame2010.xml.xz`, fixado por commit e sha256; jogos e BIOS em `~/roms/retroarch/mame2010`, onde o core os procura) ou outra versão (um XML do `mame -listxml`). O que foi lido do XML fica em `/var/cache/fliperos` (um minuto com o do GroovyMAME; a leitura seguinte leva um segundo). **A tela dos parâmetros** mostra cada parâmetro com a escolha atual; **Enter abre as opções dele** — de escolher uma (radio, `(*)`) ou de marcar várias (checkbox, `[x]`: Espaço ou o botão 3 marca, `a` marca todas, Enter confirma) — e volta para a tela com a escolha feita. Os parâmetros: jogos (só máquinas de ficha, ou tudo), emulação (funcionando, com imperfeitos, ou tudo), **categorias** (os gêneros do `catver.ini`, com quantos sets cada um; caça-níqueis, pinball, computadores e consoles começam desmarcados), **jogos adultos** (`* Mature *` no `catver.ini`), jogadores, **modo de jogo** (do `nplayers.ini`: um jogador, dois ou mais alternando, dois ou mais ao mesmo tempo, não informado), botões (os do `controls.xml` quando ele conhece o jogo — o Metal Slug tem 4 no MAME e usa 3 —, senão os do MAME), **controles do painel** (joystick de 8, 4 e 2 direções, dois joysticks por jogador, trackball, spinner, paddle, rotativo, analógico, pedais, pistola, teclado, mahjong; jogo só de botões sempre passa; os tipos do 0.139, `joy8way`, `vjoy2way`, `doublejoy8way`, e os do atual, `joy` e `doublejoy` com `ways`), tela (horizontal, vertical), **resolução** (baixa, até 288 linhas, a única progressiva num tubo de 15 kHz; média; alta — pelo `pixclock`/`htotal` do XML ou, sem eles, pelas linhas), clones (a melhor versão de cada jogo, só os pais, ou todas) e a **região** preferida, bootlegs, protótipos, **décadas**, vetoriais, jogos com CHD (ficam, saem, ou só eles), **placa** (Neo-Geo, CPS-1, CPS-2, CPS-3, as do PlayStation — ZN-1/ZN-2, Namco System 10/11/12, Konami GV/GQ/573/Twinkle, Taito G-NET, pela CPU da Sony no XML — e as Midway do Mortal Kombat) e, no GroovyMAME, se os jogos de Naomi e Atomiswave vão também para ele (o padrão é deixá-los para o Flycast). Sem um dos três arquivos de dados, os parâmetros dele não aparecem; a tela diz quais foram achados e de que versão. Eles **vêm com o romset**: o Setup os procura na pasta dele, na de cima, na subpasta `folders` (a da interface do MAME) e em `/usr/local/share/fliperos/romclean` (a imagem não os traz: o `catver.ini` é da [progetto-SNAPS](https://www.progettosnaps.net/catver/), o `nplayers.ini` do [NPlayers](http://nplayers.arcadebelgium.be) e o `controls.xml` do Controls.dat). Presets: **Joystick cabinet** (só arcade, até 2 jogadores e 6 botões, joysticks, uma versão de cada jogo, sem bootleg, protótipo e adulto), **Everything that works**, **PlayStation-based hardware** e **Everything**. O que os jogos escolhidos usam vai junto: o pai (num romset merged o clone está no zip dele), a BIOS e os dispositivos com ROM (`romof`, `cloneof`, `device_ref`), também os dos jogos que já estão no destino. Antes de mexer, o resumo (quantos vão e o tamanho, o espaço livre, quantos não estão no XML, que não são tocados) e a lista; a cópia mostra o progresso, cada arquivo chega como `.part` e só então ganha o nome (uma cópia cortada não passa por inteira), o que já está no destino com o mesmo tamanho fica — repetir continua de onde parou — e o que chega fica do dono da pasta do emulador. **Mover** (só de uma pasta em que dá para gravar) tira os arquivos do romset e depois pergunta se apaga o que sobrou; os sets do Flycast nunca entram nessa lista (`config/fliperos-romclean`, `lib/romclean.sh`);
  - **MAME CHD Cleaner** — os CHDs costumam vir numa coleção à parte, enorme. Este item olha os jogos que **já estão na pasta de ROMs** do emulador (`~/roms/mame`; no Flycast, `~/roms/naomi` e `~/roms/naomi2`; no MAME 2010, a pasta do core), vê no XML do MAME quais usam disco e copia, da pasta dos CHDs (uma subpasta por jogo, desta máquina ou de uma pasta da rede), só os deles, para dentro da pasta de ROMs (`<pasta>/<jogo>/<disco>.chd`, onde o MAME e o Flycast os procuram). O disco de um clone que é o mesmo do pai vem da pasta do pai; disco sem dump não conta. A tela mostra quantos jogos usam CHD, quantas pastas foram achadas e o tamanho, o espaço livre e a lista do que **não foi achado**; dá para incluir os clones que estão dentro dos zips (romset merged) e trocar a pasta de ROMs. A cópia mostra o progresso e continua de onde parou; de uma pasta em que dá para gravar também dá para mover (`fliperos-romclean chds`);
  - **Free games** — baixa homebrew de código aberto para as pastas dos cores do RetroArch (`~/roms/retroarch/<core>`), para os frontends não começarem vazios e para testar vídeo, som e controle sem ROM de ninguém: as Test Suites de 240p do NES, do Game Boy e do GBA, Thwaite, Nova the Squirrel, Libbet and the Magic Floor e µCity. Cada arquivo vem da página de versões do próprio projeto, com o sha256 fixado e a licença na lista (GPL e zlib, conferidas no repositório de cada um); só os dos cores instalados, e o que já está lá fica. A imagem não traz ROM nem BIOS de ninguém (`config/fliperos-freeroms`, `lib/freeroms.sh`);
  - **Quirks** — correções do kernel para controles USB que chegam errados (o parâmetro `usbhid.quirks`). Cada quirk tem um **nome** dado pela pessoa e um **código** `0xVENDOR:0xPRODUTO:0xFLAGS`, por exemplo `0x16c0:0x05e1:0x40` para um encoder Xin-Mo duplo aparecer como dois jogadores. Escolher um da lista o apaga; **USB devices connected now** mostra o vendor:produto de cada dispositivo ligado. Flags úteis: `0x40` um dispositivo por jogador (MULTI_INPUT, encoders duplos), `0x8` sem pedidos GET (NOGET, encoder que trava), `0x400` sempre consultar (ALWAYS_POLL). O kernel lê no máximo 4 quirks e só no boot: a lista fica em `/etc/fliperos/quirks.conf`, vai para a linha do kernel (`/etc/default/fliperos-boot`) e vale depois de reiniciar. Feito na mídia de instalação, vai junto para o disco;
  - **Joysticks** — calibradores e a porta paralela (`config/fliperos-calibrate`, `screens/joysticks.sh`):
    - **Button mapping (RetroArch and GroovyMAME)** — o painel de cada jogador, comando por comando: cima, baixo, esquerda, direita, os botões 1 a 6 na ordem do painel (1 2 3 em cima, 4 5 6 embaixo), Start e Coin. O primeiro comando apertado diz qual controle é o do jogador (num painel V-USB de dois aparelhos iguais, um por jogador); sem apertar nada por 8 segundos o comando fica de fora; o controle como teclado do menu fica desligado enquanto isso. A leitura é a do SDL (`config/fliperos-buttons`), e o resultado vai para os dois: no **RetroArch**, os binds de cada jogador em `/etc/fliperos/retroarch/buttons.cfg`, que o `fliperos-kms-run` soma à config (`--appendconfig`) por cima do perfil automático do controle, com os botões no layout dos cores de arcade (Y X L / B A R, Start e Select na ficha); no **GroovyMAME**, o ctrlr `~/.mame/ctrlr/fliperos.cfg` (os `JOYCODE` de cada jogador, com as teclas padrão do MAME junto) e no `mame.ini` `ctrlr fliperos` e `joystickprovider sdljoy` — no `sdlgame`, o padrão, o MAME vê o painel pelo mapeamento de game controller do SDL (A, B, X, Y...), que não segue a ordem dos botões. Vale também nos outros emuladores: o mapeamento de **game controller do SDL** do aparelho (GUID), no layout de fight stick (X Y RB em cima, A B RT embaixo, a ficha no Back), em `/var/lib/fliperos/gamecontrollerdb-user.txt`, que o `fliperos-controllers` põe por último no `gamecontrollerdb.txt` (PCSX2, com Pad1/Pad2 no SDL pelo `fliperos-x11-run` enquanto o PCSX2 não tiver bind de SDL; Dolphin; AntiMicroX); o **Flycast** por nome de aparelho (Dreamcast pelo SDL; arcade, Naomi e Atomiswave, com o botão N do painel no botão N do jogo e a ficha no D); e o **OpenBOR**, nas teclas de cada jogador do `Saves/default.cfg` e do `.cfg` de cada pak (o struct `s_savedata`: 1 ataque, 2 pulo, 3 especial, 4 a 6 os outros ataques, a ficha no Esc). O mapa fica em `/etc/fliperos/buttons.map`, e a atualização do sistema grava tudo de novo;
    - **Calibrate GunCon 2** — a tela fica branca (a pistola precisa de luz onde mira) com um alvo em cada canto; três tiros em cada um (vale a mediana; tiro fora da tela é recusado), e o calibrador calcula a faixa real da pistola no tubo — o GunCon 2 é linear, então dois pontos conhecidos dão as bordas. Um tiro no centro confere o resultado antes de gravar `/etc/fliperos/guncon2.conf`, que a regra do udev reaplica a cada conexão (o evdev esquece a calibração);
    - **Calibrate wheel, pedals or analog stick** — os eixos aparecem ao vivo; vira-se o volante de ponta a ponta e pisa-se cada pedal até o fim, depois tudo em repouso. Eixo com repouso no meio (volante, analógico) ganha faixa simétrica em volta do repouso — o centro dá 0 e os dois lados chegam ao fim — e 1% de zona morta; pedal fica com a faixa vista. Vai para `/etc/fliperos/calibration.conf` (uma linha por eixo) e o udev reaplica a cada conexão;
    - **LPT joysticks** — joysticks e pads na **porta paralela**, pelos drivers do próprio kernel: **adaptador de gamepad** (`gamecon`: NES, SNES, N64, PlayStation, tapete DDR, Multisystem; até 5 por porta, nos pinos 10, 11, 12, 13 e 15), **adaptador DB9** (`db9`: Atari/Amiga/Master System, Genesis de 3/5/6 botões, Saturn, CD32; precisa da porta em EPP ou ECP na BIOS) e **interface TurboGraFX** (`turbografx`: até 7 joysticks Multisystem). O adaptador não tem como ser detectado: a pessoa diz qual é e o que está ligado em cada entrada, e o setup grava `/etc/modprobe.d/fliperos-lpt.conf` (as opções do módulo, mais `blacklist lp`: o driver de impressora registraria a porta, e os de joystick a querem só para eles) e `/etc/modules-load.d/fliperos-lpt.conf` (carrega no boot), carrega o driver na hora e mostra os joysticks criados. A porta em si o kernel acha sozinho (`parport_pc`) quando ela existe — na placa-mãe costuma vir **desligada na BIOS** (Super I/O > Parallel Port); sem ela, uma placa paralela PCI/PCIe. Os joysticks da paralela também movem os menus;
  - **Debug mode** — desligado (o padrão), o boot vai direto ao Plymouth e a saída dos frontends e emuladores (X, Switchres, o próprio programa) vai para `/opt/fliperos/logs/<programa>.log`, refeito a cada abertura: na tela só a imagem. Ligado, aparece tudo: o menu do Limine (`FLIPEROS_QUIET="no"` em `/etc/default/fliperos-boot`), as mensagens do kernel e do systemd no boot (sem `quiet splash` nem os parâmetros que calam) e a saída dos programas no console. Os programas seguem na hora; o boot, depois de reiniciar;
  - **System Update** — `apt-get update` e `upgrade`, com o progresso real do apt;
- **Start desktop** — o LXDE. O **Desconectar** (o item do menu, o botão do painel e o fim da sessão do lxsession) abre um terminal em tela cheia com o menu no gum, no visual do Setup: voltar ao menu do FliperOS, reiniciar, desligar ou cancelar (`config/fliperos-logout`; a janela de ícones do `lxsession-logout` ficava ilegível numa tela de baixa resolução);
- **Exit to shell** — `fliperos-menu` volta ao menu;
- **Shutdown / Reboot**.

**Teclas de volume:** as teclas de volume do teclado (ou de um encoder de painel programado para mandá-las) funcionam em qualquer tela — emulador em KMS, desktop, console. O `triggerhappy` lê o `/dev/input` e chama `fliperos-setup --volume up|down|mute` (passos de 5% na placa do Audio Setup, gravados a cada toque porque gabinete costuma ser desligado na tomada); `config/fliperos-volume.triggers` diz quais teclas. O painel do LXDE fica só com o mouse, para não mudar o volume duas vezes. Durante o jogo não aparece barra de volume (nada desenha por cima de um emulador em KMS).

### Desktop LXDE

O LXDE do GroovyArcade: `lxde` completo com o openbox-lxde, painel embaixo (menu, gerenciador de arquivos, terminal, tarefas, CPU, volume, bandeja, rede, relógio), sem compositor, sem DPMS nem descanso de tela, fonte Sans 10 e a orientação do Video Setup. Tudo no tema Dracula (seção 6).

**Terminal: Alacritty.** O `lxterminal` e o `xterm` (o terminal padrão do sistema, com fontes bitmap que a imagem nem tem) não desenhavam as bordas do Gum; saíram, e o terminal do painel, do menu e do *FliperOS Setup* é o **Alacritty**, que sempre trabalha em UTF-8 e desenha bordas e blocos sozinho, sem depender da fonte. Tema Dracula com a paleta do console (`config/lxde/alacritty/alacritty.toml`), DejaVu Sans Mono, cursor sem piscar (piscar redesenha a tela, o que tremula no entrelaçado). O tamanho da letra não segue o DPI do EDID do CRT (daria 50 DPI ou menos): o `fliperos-lxde` exporta `WINIT_X11_SCALE_FACTOR=1`. Como o metapacote `lxde` depende do `lxterminal`, a imagem instala os componentes dele um a um.

**App Store:** o **GNOME Software** com o plugin de **Flatpak** e o **Flathub** como fonte, no menu (Ferramentas do sistema) e no painel como *App Store*: pacotes do Ubuntu e apps Flatpak (emuladores, jogos, programas). O App Center do Ubuntu 24.04 depende do snap, que não vai na imagem. Sem baixar atualizações sozinha nem tela de boas-vindas (`config/fliperos-software.gschema.override`): disco e rede no meio de uma partida pesam na latência, pelo mesmo motivo dos timers do apt mascarados. Instalar pede a senha do usuário (`fliperos`), pelo lxpolkit.

**Navegador e torrents:** o **Falkon** e o **Transmission** vêm na imagem e aparecem no menu (Internet) como *Falkon (browser)* e *Transmission (torrent)*: o `fliperos-rootfs.sh` copia a entrada de cada pacote para `/usr/local/share/applications`, que vem antes, com o nome trocado em todos os idiomas.

**Emuladores no menu (Jogos):** RetroArch, GroovyMAME, Flycast, PCSX2, Supermodel, Dolphin, OpenBOR, Model 2 e, depois de baixado pelo Setup, o Fightcade 2, com os ícones dos próprios projetos (GroovyMAME, Supermodel, Model 2 e Fightcade não têm ícone para Linux na imagem; os deles são do FliperOS, em `config/icons`). Nenhum deles roda dentro do X do desktop — RetroArch e GroovyMAME usam o KMS, os outros sobem um Xorg próprio no modo da tabela de modos (seção 12) —, então o atalho (`fliperos-launch`) grava o pedido e fecha o desktop (com uma confirmação se houver janelas abertas), o `fliperos-session` abre o emulador no CRT e, quando ele fecha, **o desktop volta**. Emulador que não foi compilado (`--skip-*`) não aparece no menu. Steam e Heroic (GOG) também estão em Jogos, mas abrem dentro do próprio desktop. Vêm também as ferramentas do GroovyArcade: **AntiMicroX** e **QJoyPad** (controle como teclado/mouse), `xterm`, `htop`, `evtest`, `joy2key`, `hwinfo`, `lshw`, `read-edid`, `i2c-tools`. O **FliperOS Setup** fica em **System Tools** (e no painel), como o `gasetup.desktop`. O terminal usa as cores do Dracula. Sair do desktop volta ao menu.

**Screen Resolution (Preferências):** troca a resolução do desktop **na hora**. A lista é a das resoluções do monitor escolhido no Video Setup, mais *Other resolution...* (qualquer `LARGURAxALTURA@HZ`). O Switchres calcula o modo nas faixas do `/etc/switchres.ini` (`switchres --calc`, o mesmo cálculo dos emuladores) e o `xrandr` o aplica, ajustando o tamanho da tela; a janela abre maximizada e acompanha a troca. Sem confirmar em 15 segundos, volta a resolução anterior. *Use every time the desktop starts* guarda o modo em `~/.config/fliperos/desktop-mode`, que o `fliperos-lxde` aplica ao abrir o desktop; escolher a resolução do boot esquece o guardado. Só o desktop muda: o console, o setup e os frontends seguem a resolução do Video Setup. Com monitor LCD, a lista é a dos modos do EDID dele.

## 6. Tema Dracula

O [Dracula](https://draculatheme.com) é o tema de tudo o que o FliperOS desenha:

| Onde | Como |
| --- | --- |
| Console e `fliperos-setup` | paleta do VT (abaixo) e o Gum com os índices dela |
| LXDE — janelas e programas GTK 2/3 | tema oficial `dracula/gtk`, fixado por commit (`fliperos-dracula.sh`), com as engines `murrine`/`pixbuf` do GTK 2 |
| LXDE — bordas e menus do Openbox | `config/openbox-3/themerc` (o `dracula/gtk` não tem Openbox), escolhido no `lxde-rc.xml` |
| LXDE — painel, fundo, terminal | cores em `config/lxde` (lxpanel, pcmanfm, lxterminal) |
| Terminal (zsh) | **Oh My Zsh** com o tema oficial `dracula/zsh`, os dois fixados por commit em `/usr/local/share/oh-my-zsh` (`fliperos-dracula.sh`), sem atualização automática; `~/.zshrc` é o `config/zshrc`. No console do Linux a seta e o ✓/✗ do git viram `>`, `ok` e `*` (a fonte do console não tem esses símbolos) |
| RetroArch | o tema **Dracula embutido no RGUI** (`rgui_menu_color_theme = 17`) |
| GroovyMAME | cores da interface (menus, lista de jogos, sliders) em `/etc/fliperos/mame/ui.ini` (`config/mame-ui.ini`, ARGB) |

### No console

No console do Linux só existem 16 cores, e o fundo só aceita as 8 primeiras. A paleta do VT é reprogramada com os tons do Dracula no boot (`/etc/vtrgb`, aplicada pelo `setvtrgb.service` do Ubuntu, com `config/vtrgb-dracula` como alternativa de maior prioridade) e de novo pelo `fliperos-setup`; os estilos do Gum usam os **índices** da paleta, não cores hexadecimais. Assim o tubo e um terminal gráfico mostram o mesmo. A fonte do console (Lat15/Uni2) tem as bordas arredondadas, os blocos da barra e as setas que as telas usam.

## 7. Arquitetura do `fliperos-setup`

```
fliperos-setup/
├── fliperos-setup        ponto de entrada (mídia ou sistema instalado)
├── lib/                  lógica — nenhum arquivo daqui chama o gum, exceto ui.sh
│   ├── common.sh config.sh progress.sh speech.sh
│   ├── drm.sh video.sh monitor.sh xorg.sh bootloader.sh
│   ├── disk.sh install.sh recovery.sh
│   ├── launcher.sh audio.sh network.sh status.sh scraper.sh update.sh
│   ├── romclean.sh netshare.sh  MAME ROM Cleaner; pasta compartilhada da rede (SMB)
│   ├── hardware.sh latency.sh   CPU/memória/GPU e os modos de latência
│   ├── quirks.sh padkeys.sh     quirks do usbhid; controle nos menus
│   ├── lpt.sh            joysticks na porta paralela (db9, gamecon, turbografx)
│   └── ui.sh             Gum, tema, quadro da tela
└── screens/              telas — só combinam ui.sh com a lógica
    ├── output-test.sh (teste + Testing Results)  main-menu.sh  setup-menu.sh
    ├── video-setup.sh  disk-selection.sh  install-progress.sh  progress.sh
    └── recovery.sh  first-boot.sh  latency.sh  lpt.sh  rom-cleaner.sh
```

As operações longas (instalar, reparar, atualizar, scraper) não conhecem a tela: escrevem eventos (`@step`, `@pct`, `@msg`, `@fail`) que `screens/progress.sh` desenha. Tudo vai para `/var/log/fliperos-setup.log`.

## 8. Kernel 15 kHz

`fliperos-kernel.sh` baixa o kernel.org **6.18.54**, aplica `patches/kernel-15khz/6.18/` (D0023R, 01 a 09) sobre o `.config` do kernel do próprio Ubuntu 24.04 e gera os `.deb`. Sem assinatura de módulo e sem informação de depuração. Compilar leva horas, então os `.deb` ficam num cache chaveado por versão e hash dos patches (`/output/kernel-cache/<chave>/`): o próximo build reaproveita.

O Switchres (`v2.2.1`, a mesma versão do pacote do GroovyArcade) é compilado com o `grid` e o `geometry`, e gera no build um EDID por preset de monitor mais os dois de super resolução das entradas EDID do boot (`fliperos-rebuild-edids`, o `rebuild_edids` do GroovyArcade). O hook do initramfs leva todos para o initramfs.

## 9. Latência

O que mais pesa no atraso entre apertar o botão e a imagem mudar é igual no FliperOS e no GroovyArcade: os mesmos patches de kernel (a mesma saída de vídeo no radeon/amdgpu), o mesmo Switchres e GroovyMAME, e o CRT, que não processa a imagem. O FliperOS aplica os ajustes que o GA já faz e acrescenta outros, em dois modos escolhidos em **Setup > Latency** (`fliperos-setup/lib/latency.sh`).

| Ajuste | GroovyArcade | FliperOS Standard | FliperOS Low latency |
| --- | --- | --- | --- |
| `mitigations=off audit=0` no kernel | sim | sim | sim |
| USB lido a 1000 Hz (`usbhid.jspoll=1 kbpoll=1 mousepoll=1`) | não | sim | sim |
| CPU no governador `performance` | enquanto o frontend roda | enquanto o frontend roda | sempre, desde o boot |
| Preempção do kernel | `linux-15khz` (há também um `linux-rt`) | 6.18 `PREEMPT_DYNAMIC`, modo voluntary | `preempt=full` |
| GroovyMAME `lowlatency 1`, `autoframedelay 1`, `framedelay 0` | `lowlatency` (o resto é padrão) | sim | sim |
| RetroArch `video_max_swapchain_images = 2` | sim | sim | sim |
| RetroArch `video_threaded` desligado, `input_poll_type_behavior = 2` | padrão | sim | sim |
| RetroArch frame delay automático | não | não | sim |
| RetroArch preemptive frames (1 quadro) | não | não | sim |
| apt e man-db rodando sozinhos | não existem (Arch) | mascarados | mascarados |

**O que cada ajuste faz:**

- **`mitigations=off audit=0`** — a linha padrão do GA. Desliga as proteções do kernel contra Spectre/Meltdown, que custam mais nas CPUs antigas (sem correção no hardware) típicas de gabinete. É troca de segurança por desempenho, aceitável numa máquina que só roda jogos.
- **USB a 1000 Hz** — um controle full-speed é lido a cada 8 ms (125 Hz); a espera média cai de ~4 ms para ~0,5 ms. Vale para o que usa o driver `usbhid` (encoders tipo Zero Delay/Xin-Mo, I-PAC como teclado, trackball); controles de Xbox usam o `xpad` e não mudam. Se algum controle se comportar mal, `usb_poll=default` no `/etc/fliperos/fliperos.conf` e aplicar o modo de novo volta ao polling original.
- **Governador `performance`** — o frame delay conta com um tempo fixo de emulação por quadro; com a CPU subindo o clock só depois que a carga aparece, esse tempo varia. No modo padrão vale só durante a sessão (o `fliperos-session` chama `fliperos-setup --session-start/--session-end`, como o `cpu_governor.sh` do galauncher); no de baixa latência, desde o boot (`fliperos-latency.service`).
- **`preempt=full`** — o kernel 6.18 do FliperOS é `PREEMPT_DYNAMIC`; com este parâmetro ele passa a interromper qualquer trabalho do kernel para rodar o emulador, o que o antigo kernel `lowlatency` do Ubuntu fazia. Reduz mais a variação (jitter) do que a média.
- **Frame delay** (`autoframedelay` do GroovyMAME, `video_frame_delay_auto` do RetroArch) — o emulador espera parte do quadro antes de emular, e lê os controles mais perto da hora em que a imagem sai: até quase um quadro (16,7 ms) a menos. O automático recua sozinho quando a CPU não dá conta.
- **Preemptive frames** — tira o atraso interno do próprio jogo (1 quadro), refazendo o último quadro só quando a entrada muda (mais leve que o run-ahead, que refaz todo quadro). Precisa de core com savestate; os que não têm desligam o recurso com aviso.
- **apt e man-db** — os timers do Ubuntu rodariam `apt update` e a reindexação do `man` no meio de uma partida. Atualizar fica no Setup > System Update, como no GA.

**O que ficou de fora, e por quê:** kernel `PREEMPT_RT` (o GA tem um `linux-rt`), porque o `preempt=full` cobre o uso de gabinete e o RT troca vazão por previsibilidade, que só vale com medição mostrando ganho; limitar os C-states da CPU, porque o ganho seria de microssegundos ao acordar a CPU, contra mais consumo e calor; e o `video_hard_sync` do RetroArch, porque no KMS a swapchain de 2 imagens já espera cada flip.

**Comparado com o GA:** no mesmo hardware, espere empate no modo Standard (com uma vantagem de poucos ms do USB a 1000 Hz) e até 1 a 2 quadros a menos nos jogos do RetroArch no modo Low latency. Um GA configurado à mão chega ao mesmo; a diferença é o FliperOS vir assim de fábrica.

### Hardware recomendado

| Uso | CPU | Memória e disco | GPU |
| --- | --- | --- | --- |
| **Standard** (até PS1 e a maior parte do arcade) | x86-64 com 2 núcleos | 4 GB, 16 GB de disco | AMD com saída VGA ou DVI-I, da faixa do CRT_EmuDriver (HD 2000 a R7/R9 GCN 1.0) |
| **Low latency** | AVX2 (x86-64-v3: Intel Core de 4ª geração, AMD Ryzen ou mais novos), 4 threads, 3,0 GHz ou mais | 4 GB (8 GB melhor) | idem |
| **Tudo** (PS2, Model 3, Dreamcast) | 4 núcleos físicos com AVX2 e single-thread PassMark ≥ 2000 (Core i7-7700, Ryzen 5 3600 ou mais novos) | 16 GB, SSD | idem: em resolução de CRT até a R7 240 passa do mínimo do PCSX2 (G3D ≥ 600) |

A faixa "Tudo" segue o nível *Moderate* dos [requisitos do PCSX2](https://pcsx2.net/docs/setup/requirements), o emulador mais pesado da ISO; a GPU mais forte que o PCSX2 pede nesse nível é para resolução aumentada, que não existe num CRT. Placas sem saída analógica (as AMD depois da GCN 1.0, as NVIDIA recentes) precisam de conversor DisplayPort/HDMI para VGA.

**Conferir a máquina:** Setup > Latency mostra CPU, núcleos, clock, nível de instruções, memória, GPU e as saídas analógicas, e **Check this computer** compara com o mínimo do modo Low latency (`lib/hardware.sh`: x86-64-v3, 4 threads, 3,0 GHz, 4 GB). Escolher Low latency numa máquina abaixo disso pede confirmação.

### Medir

A única comparação confiável é medir, no mesmo gabinete, o mesmo jogo e a mesma versão do emulador. Filme o botão e a tela juntos com um celular em câmera lenta de 240 fps (~4 ms por quadro de vídeo), 20 a 30 apertos por configuração, e conte os quadros do vídeo entre o botão descer e a imagem reagir.

## 10. Build

Sempre em Docker (`CLAUDE.md` proíbe chroot com `/dev` do host no WSL).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso
```

| Opção | Efeito |
| --- | --- |
| `--skip-groovymame`, `--skip-retroarch`, `--skip-flycast`, `--skip-pcsx2`, `--skip-supermodel` | Não põe o emulador na imagem (os compilados levam de minutos a horas; GroovyMAME e PCSX2 são os releases oficiais) |
| `--skip-skyscraper` | Sem o Scraper do Setup |
| `--skip-switchres` | Sem Switchres: sem EDIDs por monitor, geometria e entradas EDID do boot |
| `--skip-input-drivers`, `--skip-wheel-drivers` | Sem os drivers de entrada (GunCon 2 e volantes), ou só sem os de volante. Por padrão vêm o `guncon2`, o `hid-tmff2` (Thrustmaster T150/T300/TX/T248...) e o `new-lg4ff` (Logitech com force feedback completo, no lugar do `hid-logitech`), via DKMS — validados no 6.18 do gabinete |
| `--kernel-cache DIR` | Onde guardar/reaproveitar os `.deb` do kernel (padrão `/output/kernel-cache`) |
| `--splash fliperos\|evangelion\|none` | Tema do Plymouth |
| `--wifi-ssid NOME --wifi-psk SENHA` | Grava uma rede Wi-Fi na imagem (**a senha fica em texto na ISO**; não a distribua) |
| `--repo DIR` | Repositório APT dos frontends levado para a imagem (padrão `/output/repo`, se existir) |

O que não existe no Ubuntu 24.04 é baixado com versão e hash fixados: Limine 11.4.1, Gum 2.0.2 (o `.deb` fica pelas páginas de manual; o binário é o do código da mesma versão com `patches/gum`, compilado com o Go 1.26.7: setas ▲/▼ em vez dos pontos na paginação dos menus, os sons do menu e o Espaço marcando nas listas de marcar — o gum 2.0.2 só conhece a tecla como `" "`, e a biblioteca dele a chama de `space` —, posto no lugar do `/usr/bin/gum` com `dpkg-divert`), AntiMicroX 3.6.1 (`.deb` oficial para 24.04), Skyscraper 3.21.0 (fork Gemba, compilado com Qt6).

Auditoria da ISO gerada (só leitura): confere menu de boot, kernel, arquivos do setup, bibliotecas dos programas compilados, EDIDs e boot BIOS/UEFI.

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-vmtest bash tools/verify-iso.sh /w/output/fliperos-0.7.iso
```

## 11. Testes

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

- `tests/test_setup.py` — a lógica do `fliperos-setup` com sysfs do DRM, EDIDs, `lsblk`, `nmcli` e `aplay` falsos, no mesmo Ubuntu (e mesmo `mawk`/`jq`) da ISO.
- `tests/test_build.py` — menu de boot, kernel e patches, pins, arquivos da imagem, Limine do disco instalado, `fliperos-video-check`.
- `tools/ui-snapshot.sh TELA [LARG ALT]` — fotografa uma tela em texto num tmux 80x30 (ou 64x24, o 512x384 de 25 kHz), com um sistema falso (`tools/ui-demo.sh`).
- `tools/vm-test.py install ISO` — em QEMU: instala pela lib do setup num disco descartável e boota o disco em BIOS e UEFI. `tools/vm-test.py screens ISO` e `tools/vm-monitor.py` fotografam o tty1 de verdade (Gum no console do Linux) tela a tela. `tools/vm-test.py desktop ISO` abre o LXDE no disco instalado (pelo boot e pelo menu, com o `xorg.conf` de 15 kHz). `tools/vm-test.py dev ISO` leva os arquivos do repositório de agora para o disco instalado, sem ISO nova, e usa o menu com um gamepad falso (`tools/vm-fakepad.py`, uinput) até o desktop, a troca de resolução e os quirks.
- **Atualizar o gabinete sem ISO nova** (pela rede, com o login padrão):

  ```powershell
  docker build -t fliperos-ssh -f tools/Dockerfile.ssh tools
  docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-ssh sh tools/cabinet-push.sh 192.168.1.111
  ```

  O `tools/cabinet-push.sh` envia o setup, o `config/`, o `fliperos-rootfs.sh` e o repositório de frontends; lá o `tools/cabinet-update.sh` guarda uma cópia do que muda em `/root/fliperos-backup-DATA.tgz`, roda o mesmo `fliperos-rootfs.sh` do build e aplica o que vem de fora dele: `fliperos-limine-update`, login automático, DNS, relógio, pacotes novos (pelo apt), linha do kernel e serviços. No fim reinicia o tty1.

## 12. Emuladores

| Emulador | Sistemas | Como abre | Modo de vídeo |
| --- | --- | --- | --- |
| GroovyMAME | arcade | KMS | troca sozinho por jogo (Switchres) |
| RetroArch | vários (cores) | KMS | troca sozinho por jogo (CRT SwitchRes) |
| Flycast | Dreamcast, Naomi, Atomiswave | Xorg próprio (`fliperos-x11-run`) | 640x240 no 15 kHz, 640x480 nos outros |
| PCSX2 (AppImage oficial) | PS2 | Xorg próprio | idem |
| Dolphin | GameCube, Wii | Xorg próprio | idem |
| Hypseus Singe | laserdisc (Dragon's Lair, Space Ace...) | Xorg próprio | idem |
| OpenBOR | beat 'em ups | Xorg próprio | 320x240 |
| Supermodel | Sega Model 3 | Xorg próprio | 640x240@57.524 no 15 kHz, 496x384 nos outros |
| Model 2 Emulator (Wine) | Sega Model 2 | Xorg próprio | idem |
| Fightcade 2 (baixado pelo Setup) | partidas online: FBNeo, SNES9x e FBA (Wine), Flycast | Xorg próprio | 640x480 (entrelaçado no 15 kHz) |
| Steam, Heroic (GOG, Epic, Amazon) | jogos de PC | dentro do desktop LXDE | o do desktop |

Todos aparecem no menu **Jogos** do LXDE (seção 5). O RetroArch usa `crt_switch_resolution 4` (o `/etc/switchres.ini` do Setup) na **largura nativa** de cada jogo quando a placa gera dotclock baixo (o "s" no resultado do teste de saídas: radeon/amdgpu), como o GroovyArcade; a super resolução 2560 fica só para as placas que não geram (Intel, NVIDIA). Em 2560 o RetroArch desenha as notificações nessa largura, e no tubo elas saíam espremidas (`video_retroarch_super`, gravado com o teste de saídas e na instalação).

**GroovyMAME na resolução nativa.** O GroovyMAME roda no X, como no modo X do GroovyArcade: chamado no console (pelo `fliperos-launch`, pela sessão do boot, por um frontend ou no terminal), o comando `groovymame` se abre num Xorg só para ele (`fliperos-x11-run`) e, com `modesetting 1` no `mame.ini`, o Switchres do GroovyMAME cria e troca o modo de cada jogo pelo XRandR — no gabinete, o MvC em `SR-1_384x224@59.64`, na tela inteira. Comandos sem tela (`-listxml`, `-listclones`, `-verifyroms`, `-showconfig`, `-createconfig`, `-version`...) rodam direto, sem subir o X. Como no `galauncher.xinitrc` do GroovyArcade, o `fliperos-x11-client` sobe o **openbox** antes do programa (`config/openbox-x11-run.xml`: sem bordas, sem atalhos): é ele que encaixa a janela de tela cheia na tela nova a cada troca de modo pelo XRandR; sem ele a janela ficava no tamanho do modo em que abriu (a interface num quarto da tela de 640x480, o jogo fora do lugar). Aberto sem jogo (a interface), o `groovymame` passa `-noautosync -waitvsync`: o jogo escolhido na interface roda no mesmo processo, e o emusync do GroovyMAME no X (`emusync_linux.cpp` do gm0289sr222f) usa o `/dev/dri/card0` que fechou ao sair da interface (o `osd_deinit` fecha o fd e não o zera; "drmCrtcGetSequence(-1)") — com o `autosync`, o `syncrefresh` tirava o throttle e o jogo corria acelerado. Aberto já com o jogo (frontends, linha de comando), o vblank funciona e o `autosync` fica. No KMS isso não funcionava nesta instalação: com `modesetting 0` e `SDL_KMSDRM_REQUIRE_DRM_MASTER=0` o Switchres aplicava o modo do jogo, mas o SDL continuava desenhando no tamanho do modo do boot (no `framebuffer` do debugfs do radeon, os quadros do GroovyMAME em 320x240 com a tela em 384x224) — o jogo saía esticado, espremido ou no meio com faixas pretas, conforme a resolução escolhida no Setup; com `modesetting 1` o modo nem era aplicado ("No way to get master rights") ou a tela ficava preta ("Could not queue pageflip: -13"). O RetroArch, no KMS, cria os quadros já no tamanho do jogo (384x224) e troca certo. Numa instalação anterior, o `fliperos-rootfs.sh` troca o `modesetting 0` de antes pelo 1. O outro motivo da largura dobrada é o formato da tela: com `aspect auto` o GroovyMAME tira o formato do modo atual, e o boot em 640x240 dá 8:3 — o dobro de 4:3, então o Switchres dobrava a largura de todo jogo ("SR(0): 768x224"). O `mame.ini` vem com `aspect 4:3`, como o GroovyArcade (`-aspect "4:3"`); o Setup só volta para `auto` quando o monitor escolhido é LCD.

**GroovyMAME: o release e o comando `groovymame`.** O build não compila mais o GroovyMAME (levava mais de uma hora): usa o release oficial para Linux (`gm0289sr222f`, MAME 0.289 com Switchres 2.22f, conferido por sha256), em `/usr/local/libexec/groovymame`, com as bibliotecas que ele pede (Qt6 é a do depurador). O comando `groovymame` — o que o `fliperos-launch`, os frontends e o terminal chamam — é o `config/fliperos-groovymame`, que passa `-inipath /etc/fliperos/mame`: o padrão do release é `.;ini`, relativo à pasta de onde se abre, então um `~/.mame/mame.ini` não vale; o que vale é o `/etc/fliperos/mame/mame.ini` (do usuário `fliperos`), que o Setup grava. O release só traz o binário; como o pacote do GroovyArcade, o build põe em `/usr/local/share/groovymame` os arquivos do código da mesma tag (commit `953db38`): `plugins` (o `hiscore`), a fonte `uismall.bdf`, `bgfx`, `artwork`, `language`, `ctrlr`, `keymaps` e `hash`. O `mame.ini` é feito como o do GroovyArcade: o `-createconfig` do próprio GroovyMAME (todas as opções da versão, no padrão dela), com as do `config/mame.ini` por cima, na linha de cada uma (`config/fliperos-mame-ini`, no build). As opções do GroovyArcade (o `-createconfig` do gasetup): `plugin hiscore`, `skip_gameinfo 1`, `video opengl`, `switchres_ini 1`, `sound sdl`, `aspect 4:3` — e a latência do Setup; a fonte da interface fica a do próprio MAME (`uifont default`), porque a de pixel do GroovyArcade (`uismall.bdf`) ficava pequena demais no gabinete (`lowlatency`, `autoframedelay`, `framedelay`). O `modesetting 1` também é o do GroovyArcade, com o GroovyMAME no X (o parágrafo "GroovyMAME na resolução nativa"). O que o GroovyMAME grava (cfg, nvram, recordes do hiscore, savestates) vai para `~/.mame`; o `ui.ini` ganha o `infos_text_size 1.00` do GroovyArcade e `font_rows 20`, junto das cores Dracula — o GroovyArcade usa 19, mas o MAME só aceita de 20 a 40 e troca o 19 pelo padrão 30, que em 224 linhas deixa a fonte com 7 pixels de altura e ilegível; com 20 ela fica com 11. Numa instalação anterior, o `fliperos-rootfs.sh` só acrescenta ao `mame.ini` e ao `ui.ini` as chaves que eles ainda não têm (o que já estava gravado fica, tema incluído); nas pastas, as relativas (o `.`, `cfg`, `snap` de um `-createconfig` puro: relativas à pasta de onde o GroovyMAME é aberto, enchiam a home de `cfg` e `nvram`) saem, e sem nenhuma absoluta vale a do `config/`. O `cfg`/`nvram` que ficou na home vai para `~/.mame`; com os dois, fica cada arquivo na versão mais nova. Num sistema instalado antes, o `fliperos-rootfs.sh` move o binário compilado para `/usr/local/libexec` e põe o atalho no lugar.

**Reset Geometry.** O Setup > Video Setup > Geometry grava a geometria medida no grid (`crt_range0` com monitor `custom` no `/etc/switchres.ini`, e `switchres_ini 1` no `mame.ini`). **Reset Geometry** desfaz: o Switchres volta ao preset do monitor escolhido, o que vale para o GroovyMAME (`switchres_ini 1`, como no GroovyArcade) e para o modo 4 do RetroArch, que leem o mesmo arquivo.

**Nada entrelaçado no 15 kHz.** No tubo de 15 kHz nenhum emulador do `fliperos-x11-run` abre em 480i (a exceção é o Fightcade 2, cuja sala de jogos não cabe em 240 linhas): os de 480 linhas e os de 384 (Model 2 e 3) rodam em **640x240 progressivo** e **esticados a 200%** na horizontal — 640x240 tem pixels 8:3, e a imagem 4:3 só enche o tubo esticada: Flycast `rend.ScreenStretching=200` (300·L/4A), PCSX2 `AspectRatio = Stretch`, Dolphin `AspectRatio=3`, Supermodel `-fullscreen -res=640,240 -stretch`, Hypseus `-x 640 -y 240 -ignore_aspect_ratio` (opções no fim da linha: o Hypseus lê o jogo e o player primeiro) e o Model 2 com a tela cheia do `EMULATOR.INI` no modo da tabela. No gabinete o Flycast abria em 640x480i: o setup grava `frequency=15k`, e o script só reconhecia `15`, então todo emulador caía na coluna de 31 kHz.

**Sem texto ao abrir.** A saída do X, do Switchres e do emulador vai para `/opt/fliperos/logs/<programa>.log` (o último uso de cada um), e entre o desktop e o emulador a tela fica limpa; o Debug mode do Setup mostra tudo. O cursor do mouse só aparece nos emuladores com interface de mouse — PCSX2 (lista de jogos, assistente da BIOS), Dolphin, Flycast, o Model 2 no Wine e o Fightcade —, que o escondem sozinhos durante o jogo em tela cheia; os outros abrem com o Xorg `-nocursor`.

**ROMs em `~/roms`.** O acervo fica em `/home/fliperos/roms` (`\\fliperos\roms` pela rede), com uma pasta por emulador — `mame`, `ps2`, `dreamcast` (os discos do Flycast), `naomi`, `naomi2` e `atomiswave` (os arcades do Flycast, um sistema por pasta: nos frontends cada um é um sistema, com a plataforma dele no Scraper), `model3`, `dolphin`, `openbor/Paks`, `hypseus`, `model2` (link para a pasta do emulador no Wine) — e uma por **core do RetroArch** em `~/roms/retroarch/<core>` (todos os que o RetroArch conhece: os das informações dos cores, ~330), cada uma com um `_info.txt` do sistema e das extensões. O `fliperos-roms` cria o que faltar a cada login, então um core novo do Online Updater ganha pasta. O RetroArch abre o navegador em `~/roms`, o GroovyMAME procura em `~/roms/mame`, o Flycast em `~/roms/dreamcast`, `naomi`, `naomi2` e `atomiswave` (`Dreamcast.ContentPath`) e o PCSX2 lista `~/roms/ps2` (se ainda não houver pasta escolhida). `/opt/fliperos/roms` virou um link para `~/roms`: os caminhos antigos continuam valendo, e uma instalação anterior teve as ROMs movidas para lá (só renomeadas, sem sobrescrever nada).

**BIOS, arte e configurações em `~`.** Ao lado de `~/roms`, o `fliperos-roms` cria (a cada login, só o que falta, cada pasta com o seu `_info.txt`):

- **`~/bios`** (`\\fliperos\bios`) — é a pasta *system* do RetroArch (`system_directory`): os arquivos soltos nela e as subpastas que os cores procuram. `~/bios/dc` é a do **Flycast** e do core Flycast (`dc_boot.bin`, `dc_flash.bin`, `naomi.zip`, `awbios.zip`...; `Dreamcast.BiosPath` no `emu.cfg` e `FLYCAST_BIOS_PATH` no `fliperos-x11-run`), `~/bios/ps2` a do **PCSX2** (a pasta `bios` dele, `~/.config/PCSX2/bios`, vira um link para lá, com o que já tinha) e `~/bios/mame` entra no `rompath` do **GroovyMAME** (BIOS e dispositivos como `neogeo.zip` e `qsound.zip`; continuam valendo em `~/roms/mame`). `/opt/fliperos/bios` virou um link para `~/bios`. O FliperOS não traz BIOS: cada um põe as suas.
- **`~/media`** (`\\fliperos\media`) — a arte e os textos dos frontends, uma pasta por tipo e, dentro, uma por sistema (a plataforma do Skyscraper: `arcade`, `snes`, `dreamcast`, `ps2`, `gc`...): `snap` (capturas), `preview` (vídeos), `logo` (wheel), `box` (capas e flyers), `marquee` e `texto` (a descrição de cada jogo, `.txt`). O Setup > Scraper grava lá, e os frontends leem de lá: o Attract-Mode pelas linhas `artwork` do emulador, o ES-DE pela `MediaDirectory`, o Pegasus pelo `metadata.pegasus.txt` e a lista de jogos do GroovyMAME pelo `mame.ini` (`snapshot_directory`) e o `ui.ini` (`covers_directory`, `flyers_directory`, `marquees_directory`, `logos_directory`). Arte posta à mão com o nome da ROM (`snap/arcade/sf2.png`) também aparece no Attract-Mode, no ES-DE e no GroovyMAME.
- **`~/config`** (`\\fliperos\config`) — links para a configuração de cada emulador e frontend instalado: `retroarch`, `groovymame` (`/etc/fliperos/mame`, com o `mame.ini` e o `ui.ini`), `flycast`, `pcsx2`, `dolphin`, `supermodel`, `openbor` (os `.cfg` de `~/roms/openbor/Saves`), `hypseus`, `model2`, `attractmode`, `es-de`, `pegasus` e `skyscraper`. Cada link aparece quando o programa já criou a sua configuração (em geral, depois de aberto uma vez); um apagado volta no login seguinte, e um que ficou sem destino (o programa saiu) vai embora.

**Controles no SDL.** AntiMicroX, PCSX2, Dolphin, Flycast e RetroArch usam o SDL2, que mapeia um controle fora do banco dele de forma automática e incompleta: deixa de fora os botões sem par num controle moderno (`BTN_C`, `BTN_Z`, botões extras — no modo de controle o AntiMicroX nem os mostra) e põe no **analógico** um direcional digital que o aparelho manda como eixos de −1 a +1 (comum em encoders de fliperama e projetos V-USB), e aí jogo que anda pelo direcional não se mexe. O `fliperos-controllers` (no boot e a cada controle ligado, pelo udev) pergunta ao próprio SDL como ele vê cada controle e, só nos de mapeamento automático ou sem mapeamento com direcional digital, completa: botões que sobraram vão para gatilhos, `misc1` e paddles, e os eixos digitais viram **direcional**. Controles do banco do SDL (Xbox, DualShock...) ficam como estão; analógico de verdade (volante, manche) também. O resultado vai para `/var/lib/fliperos/gamecontrollerdb.txt` (acumulado), apontado por `SDL_GAMECONTROLLERCONFIG_FILE` no `/etc/environment` e nos lançadores. O **Flycast** monta o mapeamento padrão a partir do SDL mas não entende direcional ligado a meio eixo; para esses controles ele ganha também os arquivos de mapeamento (Dreamcast e arcade, na convenção do próprio Flycast), só se ainda não houver um. Ele vem ainda com o jogador 2 (porta B) com controle — o padrão dele deixa só o jogador 1 — e com a **interpolação linear desligada** (`rend.LinearInterpolation = no` no `emu.cfg`; a opção *Linear Interpolation* das configurações dele): o padrão do Flycast borra a imagem ao levá-la para o modo do tubo, e sem o filtro os pixels saem nítidos. Num `emu.cfg` de antes, a opção só é desligada se ainda não estiver gravada; gravada, a escolha é da pessoa. O **RetroArch** vem compilado com SDL2, então o driver de controle `sdl2` aparece em **Drivers > Controle** ao lado do `udev`, e a escolha fica (o `retroarch.cfg` do sistema não fixa o driver de controle). O padrão continua `udev`, que mostra no menu o número de verdade de cada botão do controle; no `sdl2` valem os mesmos mapeamentos dos outros emuladores, um controle sem perfil cai no "Standard Gamepad" embutido, e os números passam a ser os do SDL (A = 0, B = 1...). O SDL lê os mapeamentos ao abrir: um controle ligado pela primeira vez com o RetroArch aberto só fica certo ao reabrir. No `udev`, painel e encoder de fliperama ficavam "not configured" (não há perfil de fábrica para eles); o `fliperos-controllers` grava um em `/opt/fliperos/retroarch/autoconfig/udev` para todo controle com direcional digital e sem analógico que nenhum perfil cubra, com os botões na ordem do painel no layout dos cores de arcade (FBNeo): **1 2 3 = Y X L** (fileira de cima), **4 5 6 = B A R** (de baixo) — os cores de MAME leem Button 1-6 do RetroPad em outra ordem (o MAME, B A Y X L R; o MAME 2010, A B X Y L R), e um remap de core (`config/retroarch-remaps`, em `~/.config/retroarch/config/remaps/<core>`; um salvo pelo menu do RetroArch fica) leva o botão N do painel ao Button N do jogo, como no GroovyMAME; num painel de até 9 botões o 7º é Start e o 8º Select (ficha); com 10 ou mais, 7 e 8 são L2/R2 e Select/Start ficam no 9 e 10, como nos encoders USB. O perfil leva nome e VID+PID (o VID+PID do V-USB é o mesmo em projetos diferentes) e não é regravado: um salvo pelo menu (**Save Controller Profile**) fica. O menu do RetroArch sempre chama os botões pelos do RetroPad (A, B, X, Y...); com um core de arcade aberto, **Menu Rápido > Controles** mostra os nomes do jogo. Um encoder cujo direcional seja só eixos e que o kernel junte num controle só pode precisar de um quirk (Setup > Quirks).

**GroovyMAME: o que falta.** Quando um jogo para no "System media audit failed", o motivo fica em `/opt/fliperos/logs/groovymame.log`, e `groovymame -verifyroms JOGO` lista os arquivos que faltam — BIOS e ROMs de dispositivo vêm em zips à parte do jogo. Tudo vai em `~/roms/mame` (as BIOS também podem ficar em `~/bios/mame`), da mesma versão do MAME (0.289).

O PCSX2 é o AppImage oficial (fixado por versão e sha256, extraído em `/opt/pcsx2`): o código atual dele exige SDL3 e Qt 6.10, que o Ubuntu 24.04 não tem. O Dolphin é compilado da versão estável (a distribuição oficial para Linux é o Flatpak, que traria ~1 GB de runtime).

**Cores do RetroArch.** Vêm 6 compilados, para funcionar sem rede: FCEUmm (NES), Snes9x, Genesis Plus GX (Mega Drive/Master System), mGBA, PCSX ReARMed (PS1) e MAME 2010. Qualquer outro se baixa no próprio RetroArch, em **Online Updater > Core Downloader** (do buildbot da libretro): cores, `.info` e perfis de controle ficam em `/opt/fliperos/retroarch`, do usuário `fliperos`, então o menu grava sem root. Os `.info` e os perfis de fábrica vêm fixados por commit (`libretro-core-info`, `retroarch-joypad-autoconfig`).

### Rodar um programa em 640x240

Num monitor de 15 kHz, 480 linhas só existem entrelaçadas (480i), e o entrelaçado cintila. Em **640x240 progressivo** o programa desenha as 480 linhas dele em 240: perde metade da resolução vertical, mas a imagem fica estável — é como o FliperOS roda Dreamcast, PS2, GameCube/Wii e laserdisc no 15 kHz. Quem faz isso é o `fliperos-x11-run`: ele abre o programa num Xorg só para ele, e o Switchres cria o modo pedido nas faixas do monitor escolhido no Video Setup.

Três jeitos, do mais pontual ao permanente:

1. **Na hora, no console** (Setup > Exit to shell, no gabinete):

   ```sh
   /opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 programa [argumentos]
   ```

   Qualquer modo serve (`LARGURAxALTURA@HZ`, ex. `320x240@60`, `640x240@59.94`, `384x224@59.64`).

2. **No menu do desktop**: um atalho em `~/.local/share/applications/meu-programa.desktop`. O `fliperos-launch --mode` sai do desktop, abre o programa no modo pedido e volta ao desktop quando ele fecha (com a mesma confirmação dos emuladores do menu):

   ```ini
   [Desktop Entry]
   Type=Application
   Name=Meu programa
   Exec=/opt/fliperos/bin/fliperos-launch --mode 640x240@60 /caminho/do/programa
   Categories=Game;
   ```

3. **Sempre para aquele programa**: uma linha em `/etc/fliperos/emulator-modes.conf` (nome do comando, modo no 15 kHz, modo nos outros monitores). Daí em diante qualquer caminho que passe pelo `fliperos-x11-run` — o menu, um frontend, o console sem `--mode` — usa esse modo:

   ```
   meuemulador         640x240@60      640x480@60
   ```

   A imagem nova não sobrescreve esse arquivo depois de editado.

Num frontend (Attract-Mode e outros), o comando do emulador fica `/opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 emulador "[romfilename]"` (ou sem `--mode`, com a linha na tabela).

**A imagem tem de ser esticada.** 640x240 é uma tela 8:3 em pixels, que o tubo mostra em 4:3. Um programa que "mantém a proporção 4:3" usaria só metade da largura (320 colunas) e sairia espremido no meio. Configure o programa para **esticar/preencher a tela** — para Flycast (`rend.ScreenStretching = 200`, via `-config`), Dolphin (`AspectRatio = 3`, via `-C`) e PCSX2 (`AspectRatio = Stretch`, no `PCSX2.ini` a partir da segunda abertura) o `fliperos-x11-run` já faz isso sozinho. A conta, para outro modo: esticar `300 × largura ÷ (4 × altura)` por cento.

**GroovyMAME e RetroArch** não passam por aqui: eles trocam de modo sozinhos a cada jogo. No GroovyMAME, `interlace 0` no `/etc/fliperos/mame/mame.ini` faz o Switchres nunca escolher um modo entrelaçado (os jogos de 480 linhas saem em 240p).

### Laserdisc (Hypseus Singe)

Os jogos de laserdisc ficam em `/opt/fliperos/roms/hypseus`, que é o `~/.hypseus` (pela rede: `\\fliperos\FliperOS\roms\hypseus`): a ROM em `roms/<jogo>.zip`, o vídeo do laserdisc em `vldp/<jogo>/` com o framefile `<jogo>.txt`, e os jogos Singe em `singe/<jogo>/`. Para abrir no CRT (640x240 no 15 kHz, tela cheia):

```sh
/opt/fliperos/bin/fliperos-x11-run hypseus lair     # Dragon's Lair
/opt/fliperos/bin/fliperos-x11-run singe timegal    # um jogo Singe
```

no console ou como comando de um frontend. O Hypseus não tem menu próprio (precisa do nome do jogo), por isso não tem atalho em Jogos. É o Hypseus Singe v2.12.1 (a série 3 exige SDL3, que o Ubuntu 24.04 não tem), instalado como o README do projeto manda (`hypseus`/`singe` são os scripts dele, `hypseus.bin` o programa).

### OpenBOR

Os jogos (`.pak`) vão em `/opt/fliperos/roms/openbor/Paks` (pela rede: `\\fliperos\FliperOS\roms\openbor\Paks`). Menu **Jogos > OpenBOR** abre o menu do próprio OpenBOR, que lista os paks.

### Model 2 (Wine)

O Model 2 Emulator (ElSemi) é freeware de código fechado, só para Windows, sem permissão clara de redistribuição — por isso **não vem na imagem**. Copie os arquivos do `m2emulator` 1.1a (o `emulator_multicpu.exe` e o resto) para `/opt/fliperos/model2` e as ROMs para `/opt/fliperos/model2/roms` (pela rede: `\\fliperos\FliperOS\model2`). O menu **Jogos > Model 2** abre o emulador no Wine (`fliperos-model2`, com um prefixo do Wine só dele em `~/.local/share/fliperos/wine-model2`); sem o emulador copiado, ele mostra essas instruções. Tela cheia e resolução se ajustam no `EMULATOR.INI` do próprio emulador.

### Fightcade 2

O Fightcade 2 (partidas online de arcade e console, com rollback) é freeware de código fechado, sem permissão clara de redistribuição — **não vem na imagem nem no repositório**. Em **Setup > Frontend** ele aparece como *Fightcade 2 (not installed)*: escolhido, o Setup **baixa o pacote oficial para Linux do site dele** (uns 160 MB, `https://www.fightcade.com/download/linux`), com a barra de progresso, para `/opt/fliperos/fightcade` — pasta do usuário, porque o Fightcade se atualiza sozinho gravando nela. Na tabela de sessões a coluna do pacote é `fetch:fliperos-fightcade` (um programa baixado do site dele, não um `.deb`), e o "binário" da linha, `/opt/fliperos/fightcade/fightcade`, só existe depois do download. Depois de instalado ele pode ser o launcher do boot e aparece em **Jogos > Fightcade 2** no LXDE. `/opt/fliperos/bin/fliperos-fightcade fetch` baixa de novo por cima (reparo): as ROMs e as configurações ficam.

- **ROMs em `~/roms/fightcade`**, uma pasta por emulador dele: `fbneo` (os `.zip` do FBNeo 0.2.97.44, com o `neogeo.zip`; os de console em subpastas `megadrive`, `nes`, `sms`...), `flycast` (Naomi, Atomiswave, Dreamcast), `snes9x` e `fc1` (os jogos do Fightcade 1, romset do FB Alpha 0.2.96.74). As pastas `ROMs` de dentro do Fightcade viram links para elas (`config/fliperos-roms`); as pastas existem mesmo antes de instalar. Os romsets são os que cada emulador pede, não os do MAME atual.
- **Tela**: a sala de jogos é uma página de desktop (janela de 1280x800) e não cabe em 240 linhas, então é o único programa da tabela de modos que abre em **640x480, entrelaçado no 15 kHz** (`fightcade 640x480@60` em `/etc/fliperos/emulator-modes.conf`), com a página encolhida na proporção da altura (`--force-device-scale-factor`, 0,67 em 480 linhas; `FIGHTCADE_SCALE` fixa outro valor, e *Text > Zoom In/Out*, Ctrl+= e Ctrl+-, ajusta na hora). **Os jogos abrem dentro desse mesmo modo**, redimensionados — não na resolução nativa de cada um, como no GroovyMAME.
- **Teclas**: precisa de teclado e mouse (o login, a sala). **Ctrl+W** (*Window > Close*) fecha o Fightcade e volta ao menu; **Alt+Tab** troca entre a sala e o emulador da partida e **Alt+F4** fecha a janela da frente (`config/openbox-fightcade.xml`).
- **Wine**: os emuladores FBNeo, SNES9x e FBA são programas de Windows de 32 bits; rodam no Wine da imagem com um prefixo só deles (`~/.local/share/fliperos/wine-fightcade`), sem a janela do Mono/Gecko. O Direct3D do Wine de 32 bits desenha pelo **OpenGL de 32 bits** (`libgl1:i386`, `libgl1-mesa-dri:i386`, `libglx-mesa0:i386`, que a imagem instala junto do Wine): sem ele o FBNeo para em *"Couldn't initialise DirectX9 Alternate video output"*. O Flycast do Fightcade é nativo.

Conferido numa tela virtual de 640x480 com o pacote 2.1.45: download, reparo, a sala aberta, o FBNeo abrindo no Wine, Alt+Tab e Ctrl+W. **Não conferido**: uma partida online (precisa de conta) e a imagem no tubo.

### Steam e GOG

**Steam**: o `steam-installer` do Ubuntu; na primeira abertura a Valve baixa o cliente (centenas de MB, precisa de rede). **GOG**: não existe cliente oficial para Linux; vem o **Heroic Games Launcher** (GOG, Epic e Amazon; o mesmo do Steam Deck), que roda os jogos de Windows com o Wine/Proton que ele mesmo baixa. Os dois abrem **dentro do desktop LXDE** (são programas do X), pelo menu **Jogos**. A interface deles foi feita para telas maiores: num CRT de 15 kHz a 640x480 ela fica apertada — num monitor de 31 kHz ou LCD o uso é bem melhor.

## 13. Outros componentes

**Repositório APT e frontends.** Os frontends (Attract-Mode Plus, EmulationStation, RetroFE, Pegasus) vêm de um repositório APT próprio de `.deb` pré-compilados, como o `groovy-ux-repo` do GroovyArcade (`packaging/build-deb.sh`, `packaging/make-repo.sh`, `Dockerfile.packages`, receitas em `packaging/packages/`). A tabela `config/fliperos-sessions.conf` diz, para cada launcher, se roda em KMS ou X (da tabela `videodata.conf` do galauncher) e de que pacote vem. O build leva o repositório para dentro da imagem (`/opt/fliperos/repo`, `deb [trusted=yes] file:/opt/fliperos/repo ./`, opção `--repo`) e já instala o Attract-Mode Plus; sem isso o apt do gabinete dizia "Impossível encontrar o pacote". Hoje só o Attract-Mode Plus tem receita: os outros aparecem em Setup > Frontend como *not available yet*.

**Splash.** Plymouth com o tema próprio `fliperos` (texto, sem imagem), `evangelion` (202 quadros, com **risco de convulsão** declarado pelo autor e sem licença no pacote) ou nenhum.

**Rede.** Samba (`\\<ip>\FliperOS` → `/opt/fliperos`, e `\\<ip>\roms`, `bios`, `media` e `config` → as pastas de mesmo nome em `~`, escrita só com o usuário `fliperos`; `config/smb.conf`), SSH/SFTP e Avahi (`fliperos.local`). Login padrão `fliperos`/`fliperos`, como o `arcade`/`arcade` do GroovyArcade. O NetworkManager cuida do Wi-Fi **e do cabo** (o `10-globally-managed-devices.conf` vazio anula o do Ubuntu, que só gerenciava Wi-Fi) e escreve ele mesmo o `/etc/resolv.conf` com o DNS do DHCP (`90-fliperos-dns.conf`: o Ubuntu entregaria o DNS ao `systemd-resolved`, que não está na imagem). O relógio vem da rede (`systemd-timesyncd`). No primeiro teste no gabinete faltavam os três: o `resolv.conf` era o do container do build, o relógio da BIOS estava dois meses atrasado, e o apt não funcionava (nem System Update, nem frontends).

**Diagnóstico.** `sudo fliperos-video-check --json` lê o modo ativo de cada saída (CRTC atual via libdrm, só leitura): conector, resolução, kHz, Hz, entrelaçado.

## 14. Arquivos

| Arquivo | Função |
| --- | --- |
| `fliperos-setup/` | O setup (mídia e sistema instalado) |
| `fliperos-mkiso.sh` | Build da ISO |
| `fliperos-kernel.sh` | Kernel 15 kHz em `.deb`, com cache |
| `fliperos-rootfs.sh` | Instala na imagem o setup, a sessão, o LXDE, a paleta e a configuração de partida |
| `fliperos-limine.sh` | Limine fixado: baixa, instala no rootfs, gera a ISO híbrida |
| `fliperos-limine-update.py` | O `update-grub` do Limine no disco instalado |
| `fliperos-video-check.py` | Modo ativo das saídas (DRM, só leitura) |
| `fliperos-detect.sh` | Relatório de sistema e vídeo |
| `config/limine.conf` | Menu de boot da mídia |
| `config/fliperos-rebuild-edids`, `config/fliperos-edid-hook` | EDIDs do Switchres e o hook do initramfs |
| `config/fliperos-session`, `config/fliperos-sessions.conf` | Abre o launcher padrão; tabela de launchers |
| `config/fliperos-lxde`, `config/lxde/` | Sessão e configuração do LXDE |
| `config/vtrgb-dracula` | Paleta Dracula do console |
| `config/fliperos-latency.service` | Aplica o modo de latência no boot |
| `config/fliperos-volume.triggers` | Teclas de volume (triggerhappy) |
| `fliperos-dracula.sh`, `config/openbox-3/themerc` | Tema Dracula do LXDE (GTK fixado por commit + Openbox) e do terminal (Oh My Zsh + dracula/zsh) |
| `config/zshrc`, `config/fliperos-tty1`, `config/fliperos-menu` | zsh do usuário; fluxo do tty1 (primeiro boot, launcher, o laço do menu); do shell de volta ao menu |
| `config/fliperos-padkeys`, `config/fliperos-padkeys.service` | Controle como teclado nos menus do setup |
| `config/fliperos-calibrate` | Calibração do GunCon 2 e de volante/pedais/analógico (Setup > Joysticks) e a reaplicação pelo udev |
| `config/fliperos-roms`, `config/smb.conf`, `config/flycast-emu.cfg` | Pastas em `~` (`roms`, `bios`, `media`, `config`); Samba (FliperOS, roms, bios, media, config); Flycast de partida |
| `config/fliperos-controllers`, `config/fliperos-controllers.service` | Completa o mapeamento automático do SDL2 (e o do Flycast) dos controles ligados |
| `config/lxde/alacritty/alacritty.toml`, `config/fliperos-software.gschema.override`, `config/applications/org.gnome.Software.desktop` | Terminal (Alacritty) e App Store do desktop |
| `fliperos-setup/lib/debug.sh` | Debug mode: boot e programas com ou sem texto |
| `config/fliperos-resolution`, `config/applications/fliperos-resolution.desktop` | Screen Resolution: a resolução do desktop na hora |
| `config/mame-ui.ini` | Cores Dracula da interface do GroovyMAME |
| `config/applications/`, `config/icons/`, `config/fliperos-launch` | Emuladores no menu do LXDE e a saída do desktop para abri-los |
| `config/fliperos-x11-run`, `config/fliperos-emulator-modes.conf` | Abre um programa num Xorg próprio no modo pedido (`--mode 640x240@60`) ou no da tabela por emulador |
| `config/fliperos-model2`, `config/fliperos-ini-set` | Model 2 Emulator no Wine; ajuste de ini por seção (PCSX2) |
| `config/fliperos-fightcade`, `config/openbox-fightcade.xml` | Fightcade 2: baixa do site dele (`fetch`) e abre num Xorg próprio; os atalhos de janela dele |
| `config/fliperos-groovymame` | O comando `groovymame`: o release em `/usr/local/libexec` com o `mame.ini` do sistema |
| `config/retroarch.cfg`, `config/mame.ini` | Configuração de sistema do RetroArch e do GroovyMAME (valores do modo Standard) |
| `patches/kernel-15khz/6.18/` | Patches D0023R |
| `packaging/` | `.deb` dos frontends e o repositório APT |
| `tests/`, `tools/` | Testes e ferramentas de verificação |

## Fontes consultadas

Código atual do GroovyArcade, no GitLab do grupo `groovyarcade`:

- `gasetup` `2dbaa5297c716b4f32b0b55d5439c1f08f8cedda` — `core/procedures/interactive` (isomainmenu, mainmenu, setup; áudio: `worker_audio_menu`, `worker_set_volume`, `worker_audio_latency`), `core/libs/lib-video.sh`, `lib-install.sh`, `lib-network.sh`, `lib-troubleshoot.sh`; latência: `core/libs/lib-bootloaders.sh` (linha padrão do kernel), `core/configs/groovymame/groovymame.sh` e `core/configs/retroarch/retroarch.sh`
- `tools/gatools` `28cef9faeec9d85d001ea5259af2d7e2fa343430` — `video/video.sh` (teste de saídas, Testing results), `video/monitor.sh`, `video/inform.sh`
- `tools/galauncher` `7e4950e3a4b92faf5eeebcae7c3a29a9e73689be` — `startfe.sh`, `videodata.conf`, `modules/cpu_governor.sh`
- `os` `59670f3d476331e7c18bc3a03fea6e7860fa1b7a` — menu de boot, `.bash_profile`, LXDE, AntiMicroX, QJoyPad
- `packages` `608bd30c3799c6a14c0b21823c53919c40ab8e9a` — kernel `linux-15khz`, `switchres` (`rebuild_edids`, `geometry`), `skyscraper`

Nomes das opções de latência conferidos no código atual: [GroovyMAME](https://github.com/antonioginer/GroovyMAME) `953db38` (`src/emu/emuopts.h`: `lowlatency`, `autoframedelay`, `framedelay`) e [RetroArch](https://github.com/libretro/RetroArch) `6fe0b87` (`settings/settings_def_frame_delay.h`, `settings_def_video_sync.h`, `configuration.c`).

E também: [Switchres](https://github.com/antonioginer/switchres) (`geometry.py`, `edid.cpp`, `switchres.ini`), [D0023R/linux_kernel_15khz](https://github.com/D0023R/linux_kernel_15khz) `ece6ef15eca9480eaf75870a44764f47118e9cfe`, [Gum](https://github.com/charmbracelet/gum) v2.0.2 e o [Dracula](https://draculatheme.com) ([dracula/gtk](https://github.com/dracula/gtk) `71640b9456110f3bac2130d0b387a3154a9fb4d2`, [dracula/zsh](https://github.com/dracula/zsh) `a3e27d47ea2ed1e3b435f44aa71caf71d3219af6`, [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh) `4d4cfc287e9d887b81242c0e431b5f49f9cec5c1`; o tema do RGUI é `RGUI_THEME_DRACULA` em `menu/menu_defines.h` do RetroArch; as opções de cor da UI do GroovyMAME estão em `src/frontend/mame/ui/moptions.cpp`).
