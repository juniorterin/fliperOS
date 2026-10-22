# Pendências do FliperOS

O que já foi pedido e ainda não foi feito. Quando um item fica pronto, ele sai daqui e o que mudou vai para o [CHANGELOG](CHANGELOG.md).

## Vídeo: conferir no tubo

Feito em 2026-10-16 e testado só no Docker; falta ver no CRT do gabinete:
- **Video Setup > 480i games:** um emulador marcado em "480i filter" ou "480i pure", e o preview do filtro (o Setup abre um Xorg só dele: se a tela ficar preta ou não voltar ao menu, é aí).
- **Video Setup > Colour calibration:** os padrões de teste e as mudanças ao vivo; se a cor fica depois de sair do calibrador, ao abrir um jogo e ao voltar ao menu.

## Modo Tour/Welcome (fase 4)

**Adiado em 2026-10-16; talvez nem seja feito.** Seria uma tela animada na interface gráfica que apresentaria o menu, os botões e as seções, oferecida no primeiro boot e no Setup.

## Painel web e API REST (fase 5)

- **5a (leitura) e 5b (controle) feitas em 2026-10-17:** http://fliperos.local:8081 (era a 8080 até 2026-10-22). Cada parte foi testada no gabinete pela API (abrir e fechar jogos, FPS, screenshot, arquivos, terminal, trackball, Downloader, configurações). Falta conferir num navegador de verdade, no PC e no celular: o layout, o terminal no Chrome e o trackball no toque.
- **Trackball pelo celular:** pronto, mas desligado por enquanto (2026-10-17, a pedido). O cartão está escondido e `FLIPEROS_WEB_TRACKBALL=1` no serviço liga de novo.
- **5c feita em 2026-10-22, falta ver no gabinete** (ele estava desligado). Testada no Docker de ponta a ponta: go2rtc, WebRTC e o Chromium, com um padrão de teste no lugar da tela. Chegaram H.264 e Opus, 640x240 a 61 fps, com 10 a 40 ms no buffer. Partes:
  - a tela ao vivo no painel e o endereço dela para o OBS;
  - o marquee para o OBS.

  No gabinete, falta conferir:
  - **kmsgrab no radeon:** se o framebuffer sai certo pelo `hwdownload` (um framebuffer com tiling sairia embaralhado). Plano B: a camada OpenGL do filtro de flicker, que já lê os quadros para o screenshot.
  - **Live screen sound:** o loopback no relógio da placa (`timer_source`) e se os jogos continuam com som pelo `fliperos_tee`.
  - **A carga do x264** com um jogo pesado aberto (o serviço roda com Nice=10).
  - **Remote play:** ficou para depois, a pedido. Seria um controle virtual alimentado pelo navegador.

## Bugs

- **Atalhos de teclado do RetroArch não funcionam no master de 2026-10-12.** Num jogo o teclado chega ao core (as setas movem), mas nenhum atalho funciona (Esc, F1, F2). Isso acontece com linuxraw e com udev, mesmo com um `retroarch.cfg` vazio. O master está no meio da reescrita da entrada (teclado por jogador, `input_hotkey_follows_player1`, `input_hotkey_port_seen`). Opções:
  - **(a)** achar por bisect o commit que quebrou e fixar um commit do master anterior a ele (mantém o motor de modelines do CRT dentro do RetroArch);
  - **(b)** a versão estável v1.22.2, que usa a libswitchres no lugar desse motor (validar o 15 kHz de novo);
  - **(c)** esperar.

  Enquanto isso: Start+Select no painel abre o menu, e de lá dá para usar Quit. Só um teclado de verdade serve para testar; teclas injetadas por uinput não chegam ao RetroArch.
- **RetroArch não fecha com Esc quando aberto pelo "jogo direto do boot"** (PS1, MAME 2010). SM2-Emu, GroovyMAME e Supermodel fecham. Provavelmente é o mesmo bug dos atalhos.
- **Reiniciar pelo menu trava uns 90 s na tela de reboot do Plymouth.** O SIGTERM do systemd não encerra o Setup (sudo, sudo, bash), que só morre no SIGKILL, após o timeout. Suspeita: o trap de EXIT (`restore_terminal` → `ui_done` esperando o FIFO da interface gráfica, ou um acesso a `/dev/tty`) enquanto o sistema desliga.
- **Menu embaralhado uma vez** depois de sair de um jogo pelo botão de desligar. Não reproduzido; o log mostra a interface gráfica aberta normalmente.

## Downloader

- **Um filtro de torrent por vez.** Aplicar o filtro de outro emulador enquanto um download ainda corre desmarca os arquivos pendentes do anterior. Falta um filtro por emulador. Desde a2d67bb, a limpeza só mexe nas pastas do filtro atual, então trocar de emulador não apaga mais os jogos do outro.

## Placar versus entre dois gabinetes

A fase 1 (as saídas dos jogos) está feita. O placar já lê vitórias e personagens pelos detectores do Fightcade, mas ainda não foi visto num display de LED de verdade.
- **Fase 2:** os pontos ao vivo dependem de `config/versus-games.conf`, que está vazio. É preciso descobrir os endereços de memória de cada jogo.
- **Fase 3:** netplay na rede local (Setup > Network > Versus link, mDNS, `--host`/`--connect`).
- **Fase 4:** um PC com dois monitores (GroovyMAME `-numscreens 2` para jogos de uma tela).
