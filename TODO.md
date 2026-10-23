# Pendências do FliperOS

O que já foi pedido e ainda não foi feito. Quando um item fica pronto, ele sai daqui e o que mudou vai para o [CHANGELOG](CHANGELOG.md).

## Pedidos de 2026-10-23

Menu e Setup:
- **Fundo animado no azulejo selecionado** do menu.
- **Extras dentro de Games** no menu.
- **Update de cada emulador** no menu (Setup > Games > Emulators & Games).
- **Downloader:** escolher um arquivo .torrent (além do link magnético) para o romset e para os CHDs.
- **Rótulo do HD em /media/fliperos/** (o nome do volume no lugar do dispositivo).
- **Boot lento:** subir só sob demanda o que não precisa estar no boot. Em andamento: há mudanças ainda não commitadas (os serviços depois da primeira tela, o Transmission só quando um download é pedido).

Frontend próprio (o padrão no futuro), **primeiro mostrar o design:**
- três modos: lista com mídia e informações (ícones à direita); tela cheia com a mídia ao fundo e o nome e as informações na frente; flow (como o Arcadeflow hoje);
- o mesmo desenho do menu de hoje, que ele vai integrar;
- ícones e logotipos do Arcadeflow.

Painel web:
- **Filtro 480i** mais intuitivo.
- **Frontend:** um ícone animado no centro enquanto busca os dados na internet. O rodapé do jogo está apertado (Arcade Database, (C) arcade-history.com, Jogar, Favoritar): dar espaço.
- **Marquee na live:** ligado no meio da transmissão, a imagem não se atualiza.
- **FPS e jogo do PCSX2** não aparecem; testar todos os emuladores.

Documentação e site:
- **Respiro nos textos:** os MD e a wiki estão abarrotados.
- **BIOS:** revisar o que fala de baixar e onde pôr as BIOS (o Download BIOS agora faz isso sozinho).
- **Painel web em destaque** no site e na documentação.
- **SEO** no site (Google e ChatGPT) e no GitHub: linux arcade 15khz groovyarcade replayos batocera recalbox rgbpi.

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

  No gabinete, em 2026-10-22, a imagem funcionou: o Attract-Mode ao vivo no navegador do PC, 640x240 a 59 fps, com 13 ms no buffer, e a página do OBS também. O x264 roda a 62 fps no i7 870. O `hwdownload` direto falha no AMD (EPERM ao mapear o buffer); o quadro passa pelo VA-API e funciona. Falta conferir:
  - **Live screen sound ainda não funciona no gabinete** (HDA Intel, 2026-10-22). Ao ligar, o Setup testa o `default` e, como ele não abriu, voltou sozinho para desligado; o som dos jogos não foi afetado. Testes com um asound.conf à parte:
    - o `dmix` padrão do loopback não abre ("Sample format non available");
    - o `timer_source` na placa deixa o loopback ocupado, e o `hrtimer` não abre;
    - um `dmix` próprio na placa dá "busy" quando o `dmix` do sistema (chave 5678293, S32_LE, 48000, 1024/16384) já está aberto por quem toca;
    - entrando no mesmo `dmix` do sistema (a mesma chave), cada parte abre sozinha, mas o `multi` dos dois recusa ("Slave PCM not usable");
    - só funcionou com o cartão livre e os dois em S16/4096: 31 s sem xrun.

    Opções:
    - **(a)** continuar no ALSA (o `multi` com outros tamanhos, ou o plugin `file` num FIFO com um leitor sempre aberto);
    - **(b)** PipeWire só para a transmissão (o monitor da saída), mexendo na pilha de áudio dos jogos;
    - **(c)** ficar sem som na transmissão.
  - **A carga com um jogo pesado aberto** (o serviço roda com Nice=10).
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
