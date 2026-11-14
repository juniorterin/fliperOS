# Pendências do FliperOS

O que já foi pedido e ainda não foi feito. Quando um item fica pronto, ele sai daqui e o que mudou vai para o [CHANGELOG](CHANGELOG.md).

## Frontend do FliperOS

É o padrão desde 2026-10-23 (c5bc185), e o que foi decidido no desenho está na wiki ([Frontends](docs/wiki/Frontends.md)). Falta conferir com o painel de verdade, segurando o direcional, a rolagem que acelera aos poucos e o modo letra.

## Mídia física: CD, DVD e o leitor de cartuchos

Pedido de 2026-11-07. Os discos (a fileira PHYSICAL MEDIA, o cartão com PLAY / EMULATOR / RIP TO FOLDER e o Boot from media) estão feitos e testados só com imagens de disco e drives de mentira; nunca rodou um drive de verdade. Falta num gabinete com um drive:
- **Jogar do drive:** o DuckStation com `/dev/srN`, o PCSX2 com `-disc` e um core do RetroArch com `cdrom://driveN.cue` (o RetroArch do pacote tem de ter vindo com o `HAVE_CDROM`; o usuário precisa do grupo `cdrom`, que vale depois de reiniciar).
- **O rip:** um CD de PlayStation com o `cdrdao` e o `chdman`, um com faixas de áudio (PC Engine CD ou Sega CD), e um DVD de PS2.
- **O reconhecimento** em discos de verdade de cada console (Saturn, Sega CD, PC Engine CD, 3DO, Neo Geo CD, PC-FX).
- **OSCR (Open Source Cartridge Reader):** o patch do firmware (`patches/oscr`, compila nas duas variantes do HW5 com `tools/oscr-firmware.sh`) e a parte do frontend estão feitos, testados só com um OSCR de mentira num pseudo-terminal. Falta num OSCR de verdade: gravar o firmware, o `SCAN` a 3,3 V de cada slot (quais cartuchos de 5 V respondem assim), o `DUMP` de cada sistema sem o botão (algum menu do firmware pode ainda esperar), o `GET` a 1 Mbaud pelo CH340, e o save ao lado da ROM no RetroArch. A gravação pelo Setup > System > Cartridge reader (backup, `avrdude` pelo bootloader do Mega, a conferência e o Restore) só rodou com um `avrdude` de mentira.

## Vídeo: conferir no tubo

Os hacks de entrelaçado, a calibração de cor, as scanlines de 31 kHz e o monitor vertical foram vistos no CRT em 2026-11-13. Falta:
- **OSD:** o atalho do painel abriu a OSD no gabinete em 2026-11-13 (Direita + Start, escolhido em Frontend controls > OSD MENU; antes do 216ee7a o vigia recomeçava a cada meio segundo e segurar 1 s nunca completava). Falta a geometria num jogo do RetroArch (em KMS, só foi testada no frontend).
- **Atalhos do jogo (Frontend controls):** EXIT GAME e EMULATOR MENU segurados no painel de verdade, e o Esc do menu do PCSX2, do PCSX2x6 e do DuckStation (sem jogo nem BIOS no gabinete, não testados). Os outros menus foram abertos por teclado virtual (RetroArch, GroovyMAME, Flycast, SM2-Emu).

## GroovyMAME no KMS

É o padrão desde 2026-11-05 (144835f), com o SDL2 do pacote `fliperos-sdl2-kms`; no gabinete, sf2 e kof98 abriram no modo de cada jogo. Falta:
- **Vários monitores com os jogos de várias telas:** hoje esse caso fica no X (`config/fliperos-groovymame`, `use_kms`). Para ir ao KMS: o `fliperos-kms-run` não desligar os monitores extras para o GroovyMAME (ele chama `fliperos-setup --outputs main`), o `-screenN` de cada tela vir dos conectores do DRM em vez da ordem do `xrandr`, e conferir se o Switchres troca o modo no conector certo de cada tela (o comentário do `custom_video_drmkms.cpp` diz que ele pode voltar ao primeiro conector). Precisa de um gabinete com dois monitores ligados.
- **Conferir no KMS:** um jogo escolhido na interface do MAME (no X era aí o bug da velocidade, do emusync), um jogo de 480i, um jogo que troca de resolução no meio, a pistola de luz e as placas Intel e NVIDIA. Se algum falhar, `groovymame_video=x11` no `fliperos.conf` volta ao X.
- **Instalações só atualizadas pela rede** ficam no X: o pacote vem no repositório da ISO, que a atualização não traz.

## Todos os emuladores atualizáveis

Pedido de 2026-11-06: cada emulador que vem na imagem chega pelos updates (um pacote do FliperOS, release `packages` + `updates/packages.list`) e tem, no Setup > Emulators & Games, a opção do mais novo do projeto com os nossos patches e a volta ao pacote (`fliperos-emulators edge`, 9b3bdeb).
- **Flycast, RetroArch, Dolphin:** pacotes (updates 43, 47 e o 0.21) com a opção do mais novo (9b3bdeb, 04aacb0; o Dolphin pela tag estável). Falta rodar a opção num gabinete.
- **GroovyMAME, Supermodel, OpenBOR, PCSX2 e Gum:** pacotes feitos e publicados (b926e6e, 97519cf), os quatro emuladores com a opção do mais novo. Estão como `installed` na `updates/packages.list` (um pacote novo entra assim: nenhum gabinete o ganha). Falta testar cada um num gabinete; depois, `always` e um update.
- **PCSX2x6:** virar pacote depois que o trabalho dele assentar.
- **Kernel:** `KERNEL_BUILD=2` (97519cf): vira `6.18.54-15khz.2`, um pacote novo ao lado do antigo (o Limine guarda o anterior). Falta compilar, publicar (`tools/publish-packages.sh` pega o `output/kernel`) e testar o boot num gabinete antes de `always`.

## Placas de vídeo

- **Driver da NVIDIA:** o que se mediu numa GTX 980 Ti com o driver 580 (2026-10-26) ainda não entrou no Setup:
  - o KMS dele (`nvidia-drm`) só aceita os modos progressivos do EDID, e um EDID só com 1280x480i deixa o boot preto. Com esse driver, o boot precisa de um EDID com modos progressivos (1280x240 e 640x240 funcionaram);
  - o `xorg.conf` só ganha a seção `Driver "nvidia"` com o `ModeValidation` quando há um modeline ou outra tela (`fliperos-setup/lib/xorg.sh`). Subindo pelo EDID, o X fica sem ela, e é ela que deixa passar os modos de 15 kHz.
- **Card firmware (ATOM-15):** a gravação de verdade nunca rodou numa placa, só com um `amdvbflash` falso nos testes. Precisa de uma placa AMD de reserva, sem ATOM-15, e do `amdvbflash` em `~/vbios`. Também nunca foram comparadas com o `atom-15.exe` as opções Avivo/DCE8, 25 e 31 kHz, o sync composto e a mudança do GOP.

## Jogos em rede: link e net play

O link e o net play pelo frontend entraram na 0.19; depois, o net play ganhou todo core do RetroArch marcado "deterministic", o GGPO do Flycast e o Dolphin (com o patch próprio). Falta:
- **Duas pessoas jogando de verdade:** uma corrida inteira em link e um crédito inteiro em net play. Até aqui, as telas e as entradas de cada lado foram conferidas com teclas por script e controles virtuais.
- **Net play com outro core além do FBNeo:** os outros aparecem no frontend, mas nenhum foi jogado entre duas máquinas.
- **Party do RetroArch sem espera:** quem abre já entra no jogo e os outros entram com ele rodando (o aviso "NOME IS PLAYING", com o sininho). Testado só no loopback e nas telas desenhadas; falta entre dois gabinetes, vendo o RetroArch do anfitrião aceitar quem chega com o jogo andando.
- **GGPO de até quatro (patch 0002 do Flycast):** provado com três Flycast num PC (Isuka 2+1+1, cada ficha na porta certa) e entre o gabinete e o PC (2026-11-06: a party do frontend, as portas de cada plano certas; travadas curtas e leves, provavelmente do lado do PC, Flycast em Docker com vídeo por software atrás de uma ponte UDP). Falta entre dois gabinetes no cabo, para ver se as travadas somem. Patches 0003 a 0005 testados em 2026-11-07 entre o gabinete e o PC com jogadores por script (seis sessões, wiki Linked-cabinets): a party travada (atraso 1, previsão ≤ 2) ficou a 1 quadro, sem esperas e com menos engasgos. Sobra um quadro de ≥34 ms na maioria dos segundos em todas as configurações (o laço de emulação do Flycast, não a rede); falta ver no CRT se ele aparece, e testar entre dois gabinetes. No gabinete do dono o binário foi posto à mão (o original em `/usr/local/bin/flycast.orig`); o pacote `fliperos-flycast` ainda não foi publicado com o patch: depois do teste, subir `PKG_REVISION` para 1fliperos2, publicar o .deb (`tools/publish-packages.sh`) e um update. Até lá os outros gabinetes ficam no GGPO de dois.
- **GGPO do Flycast:** nenhuma partida foi aberta pelo frontend ainda. Entre o gabinete e um PC com Windows, o lado do cliente não foi provado (dois Flycast do gabinete ligaram, numa rede de teste dentro da mesma máquina).
- **Initial D Ver. 3 e F355 Challenge:** o link entre dois Flycast começou numa máquina só, mas as telas não foram vistas, e os dois não estão na lista do frontend.
- **Dirt Devils em quatro** não ligou nos testes; o perfil dele diz dois.
- **Mais jogos em link**, cada um depois de testado em pares: os outros do Model 2 (o papel de cada máquina fica no menu de teste de cada jogo), Gunbuster, Model 1 e System 32.
- **Perguntas em aberto** do plano ([link-frontend-plan](docs/research/link-frontend-plan.md)): começar com menos máquinas que o máximo, duas festas do mesmo jogo, mandar as ROMs sem perguntar ao dono do outro gabinete, recusar sets de regiões diferentes.

## Wine e jogos custom: conferir no gabinete

Feito em 2026-11-07 e testado só no Docker:
- **Filtro de flicker e OSD nos jogos do Wine:** a camada de 32 bits (compilada pelo Extras junto com o Wine) e o nome próprio de cada jogo custom (`--app custom_<grupo>_<nome>`, com linha em Interlaced hacks). A camada compila em 32 bits, e o carregador pula a da outra arquitetura (Docker noble), mas nenhum jogo do Wine rodou com ela. A camada do Vulkan de 32 bits (DXVK) passou no teste com o lavapipe de 32 bits (`ARCH=i386 tools/vkfps-test.sh`). Falta abrir no gabinete um jogo de 32 bits do Wine em 640x480i, um em OpenGL e um em DXVK, e ver a OSD com a linha do filtro.
- **Pastas de jogo em squashfs** (Custom games > Pack a game folder): empacotar, montar, gravar por cima, desmontar e desempacotar foram testados num container com a home em tmpfs, com lz4 (o kernel do WSL não tem o zstd do squashfs; o do FliperOS tem). Falta num gabinete: um jogo do Wine empacotado abrindo, o serviço montando no boot e o compartilhamento de rede com a pasta montada.
- **Pacotes de jogo custom** (`JOGO.fliperos-customgame.zip`, 2026-11-14): criar, instalar, os azulejos e o executor foram testados no Docker. Falta num gabinete:
  - um pacote feito no assistente e instalado em outro gabinete;
  - o jogo aberto pelo frontend (antes os custom davam "CANNOT OPEN THIS GAME") e pelo painel web.
- **Controller configuration** (OSD dos jogos custom): o teclado foi conferido em imagem (320x240, 256x224, vertical) e o `gamekeys` pelo socket, sem controle de verdade. Falta:
  - no tubo, ler as teclas;
  - com o painel, capturar um botão e o jogo receber a tecla;
  - um controle lido pelo HIDAPI calado com a OSD aberta;
  - um painel que se diz teclado (I-PAC): o jogo recebe a tecla nova e também a original.
- **PortProton**: a instalação sem janelas (scripts fixos, primeiro download num Xvfb, o curl por https) e o `.ppdb` deram certo num container Ubuntu 24.04 (~3 GB). Nenhum jogo abriu ainda. Falta:
  - instalar pelo Setup num gabinete;
  - abrir um `.exe` de verdade em 640x240 e 480i;
  - ver se o filtro e a OSD entram no runtime dele (`PW_USE_RUNTIME=1`, bubblewrap). Se não entrarem, gravar `PW_USE_RUNTIME=0` no `.ppdb` gerado;
  - ver se alguma janela do yad aparece no meio do jogo.
- **Wine Staging** (Extras): o repositório e os pacotes foram conferidos (`winehq-staging` 11.21 para o noble, chave D43F...672F), mas a instalação nunca rodou. Falta instalar num gabinete que já tem o Wine do Ubuntu (a troca pelo apt) e abrir o Fightcade (FBNeo, SNES9x, FBA) com ele.

## Painel web e API REST (fase 5)

As fases 5a (leitura), 5b (controle) e 5c (a tela ao vivo e o marquee para o OBS, com som desde o update 27) estão feitas e rodam no gabinete, em http://fliperos.local:8081. Falta:
- **Trackball pelo celular:** pronto, mas desligado desde 2026-10-17, a pedido. O cartão está escondido e `FLIPEROS_WEB_TRACKBALL=1` no serviço liga de novo.
- **A carga da tela ao vivo com um jogo pesado aberto** (o serviço roda com Nice=10).
- **Remote play:** ficou para depois, a pedido. Seria um controle virtual alimentado pelo navegador.

## Bugs

- **Atalhos de teclado do RetroArch não funcionam no master de 2026-10-12.** Num jogo o teclado chega ao core (as setas movem), mas nenhum atalho funciona (Esc, F1, F2). Isso acontece com linuxraw e com udev, mesmo com um `retroarch.cfg` vazio. O master está no meio da reescrita da entrada (teclado por jogador, `input_hotkey_follows_player1`, `input_hotkey_port_seen`). Não foi conferido de novo: o build da ISO ainda pega o master do dia (`git clone --depth=1`). Opções:
  - **(a)** achar por bisect o commit que quebrou e fixar um commit do master anterior a ele (mantém o motor de modelines do CRT dentro do RetroArch);
  - **(b)** a versão estável v1.22.2, que usa a libswitchres no lugar desse motor (validar o 15 kHz de novo);
  - **(c)** esperar.

  Enquanto isso: Start+Select no painel abre o menu (fora do frontend do FliperOS; aberto por ele, o menu é o atalho EMULATOR MENU e o Start+Select fica desligado), e de lá dá para usar Quit. Em 2026-11-13, no commit fixado hoje (7d2e953), o F1 injetado por uinput abriu e fechou o Quick Menu no gabinete (é por ele que sai o EMULATOR MENU do frontend); Esc e F2 ainda não foram conferidos.
- **RetroArch não fecha com Esc quando aberto pelo "jogo direto do boot"** (PS1, MAME 2010). SM2-Emu, GroovyMAME e Supermodel fecham. Provavelmente é o mesmo bug dos atalhos.
- **Menu embaralhado uma vez** depois de sair de um jogo pelo botão de desligar. Não reproduzido; o log mostra a interface gráfica aberta normalmente.

## Downloader

- **Um filtro de torrent por vez.** Aplicar o filtro de outro emulador enquanto um download ainda corre desmarca os arquivos pendentes do anterior, e salvar um filtro novo substitui o que estava salvo. Falta um filtro por emulador. Desde a2d67bb, a limpeza só mexe nas pastas do filtro atual, então trocar de emulador não apaga mais os jogos do outro.

## Placar versus entre dois gabinetes

A fase 1 (as saídas dos jogos) está feita. O placar já lê vitórias e personagens pelos detectores do Fightcade, mas ainda não foi visto num display de LED de verdade.
- **Fase 2:** os pontos ao vivo dependem de `config/versus-games.conf`, que está vazio. É preciso descobrir os endereços de memória de cada jogo.
- **Fase 3:** o netplay na rede local já está no frontend (ver "Jogos em rede" acima), só pelo cabo de rede, com a presença por broadcast UDP em vez de mDNS. Falta ligar o placar versus a ele.
- **Fase 4:** um PC com dois monitores (GroovyMAME `-numscreens 2` para jogos de uma tela).

## HUD do ZeDMD por estilo de jogo

Hoje o ZeDMD mostra arte, texto e o placar de luta (`versus_frame` em `config/fliperos-dmd`). Vidas, munição e recoil do Model 2 já saem pela porta 8000, mas ninguém os desenha. Falta um layout por estilo e um estado de entrada normalizado. Decidido: layouts e contrato primeiro, leitores depois.
- **Estilos (128x32):** `fighter` (nomes e personagens, barra de vida, vitórias, pontos), `lightgun` (vidas, pente em barras, créditos), `racing` (posição, volta, tempo, velocidade), `shmup` (pontos, vidas, bombas, power, stage), `platform`, `puzzle`, `sports` e `generic` (placar e créditos, o padrão). O estilo vem do gênero do `catver.ini` e da família `lightgun` (`annotate()` em `config/fliperos-romclean`).
- **Telas de evento por cima do HUD:** INSERT COIN piscando, ficha entrou (CREDIT +1), contador de CONTINUE (9 a 0 com barra), ganhou, perdeu, game over e hi-score.
- **Entrada:** o arquivo `$XDG_RUNTIME_DIR/fliperos-hud`, em `chave=valor` como o `fliperos-marquee`. Os nomes seguem o vocabulário do SM2-Emu em minúsculas: `style`, `state` (attract/play/continue/over), `credits`, `stage`, `time`, `hi`, `p1_`/`p2_` + `score life life_max lives ammo ammo_max bombs power combo wins rounds char name`, e os de cada estilo (`speed lap laps pos pos_of round level lines next`). Eventos: `event` (coin/start/win/lose/continue/gameover/hiscore), `event_side`, `event_seq` (repete o mesmo evento) e `continue` (segundos restantes). Ausente = omitido; inválido ou desconhecido = ignorado; `style` desconhecido = `generic`.
- **Eventos que o próprio `hud` deduz:** `credits` subiu → ficha; `wins` subiu → ganhou ou perdeu (em rede, "YOU" ou "RIVAL" pelo `versus_side`); `life` zerou → perdeu; `lives` zerou → game over. Um `event` explícito vence o deduzido.
- **Código:** em `config/fliperos-dmd` (Pillow, DMDStream RGB24 128x32): fonte bitmap 5x7 própria (referência: `GLYPHS` em `website/src/components/LedMatrix.tsx`), leitura tolerante do arquivo, uma função de layout por estilo, subcomando `hud` (relê o arquivo só quando muda, ~10 fps), `hud --demo ESTILO`, `hud --demo-events` e `hud --sheet SAIDA.png` (folha de prévia em 4x). Testes em `ZeDMDTests` (imagem `fliperos-tests-pil`).
- **Fontes que já existem:** o `config/fliperos-versus` já reúne Fightcade (detectores `.inf`), GroovyMAME (plugin, `fliperos-versus.feed`), RetroArch/FBNeo (UDP 55355) e Model 2 (`P1_Wins`) em `wins1/wins2/score1/score2/char1/char2`. Falta só gravar também o arquivo do HUD (`style=fighter`): a luta fica pronta de ponta a ponta sem leitor novo.
- **Sem fonte hoje:** vidas, munição, recoil e créditos fora do Model 2 (precisa de um leitor genérico da porta 8000, que só abre com HOTR, QMamehook ou LEDSpicer, ver `fliperos-x11-run`) e o **contador de continue** (precisa do endereço de memória de cada jogo na `versus-games.conf` ou de uma saída do jogo). Corrida, shmup, plataforma, puzzle e esportes também dependem dos endereços de cada jogo (fase 2 do versus).
- Nunca visto num LED de verdade.

## Site

- **Prints a refazer:** os de `gui/` são de 2026-10-15 e os de `frontend/` de 2026-10-24, antes das mudanças das últimas versões. Faltam `gui/video-driver`, `gui/unsupported`, `gui/lab` e `frontend/options`, que hoje aparecem como cartões só de texto.
- **Vídeo de apresentação:** a cena do primeiro boot ainda é a pergunta antiga (o que abrir ao ligar), não o assistente de primeiro boot da 0.15.

## Modo Tour/Welcome (fase 4)

**Adiado em 2026-10-16; talvez nem seja feito.** Seria uma tela animada na interface gráfica que apresentaria o menu, os botões e as seções, oferecida no primeiro boot e no Setup.
