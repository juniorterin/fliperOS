# Pendências do FliperOS

O que já foi pedido e ainda não foi feito. Quando um item fica pronto, ele sai daqui e o que mudou vai para o [CHANGELOG](CHANGELOG.md).

## Vídeo

### Calibração de cor do monitor

Um calibrador no Setup para a cor da imagem: "algo com as cores, contraste". Posição e tamanho ficam de fora, porque o Video Setup > Geometry já faz isso.
- **Parâmetros:** a lista ainda não foi definida; perguntar antes de começar. Sugestão (não confirmada): brilho, contraste, gama, saturação e ganho de R/G/B, com padrões de teste (barras de cor, rampa de cinza, nível de preto e de branco).
- **Hardware:** só mostrar o que a placa suporta. Conferir no DRM o `GAMMA_LUT` e o `CTM` de cada CRTC.
- **O que os outros têm:**
  - **RePlayOS** (`replay.cfg`): `video_gamma` de 0.5 a 1.5, `video_red/green/blue_scale` de 0.0 a 1.0, `video_crt_rgb_range` (auto/full/limited) e uma tela de teste (SCREEN_TEST).
  - **MiSTer** (`MiSTer.ini`):
    - brilho, contraste e saturação de 0 a 100;
    - matiz de 0 a 360;
    - `video_gain_offset` (ganho e offset por canal, de -2 a 2);
    - `hdmi_limited`;
    - gama por core no OSD.
  - **Batocera:** só posição/tamanho e a grade do Switchres.

## Modo Tour/Welcome (fase 4)

**Adiado em 2026-10-16; talvez nem seja feito.** Seria uma tela animada na interface gráfica que apresentaria o menu, os botões e as seções, oferecida no primeiro boot e no Setup.

## Painel web e API REST (fase 5)

- **5a:**
  - um servidor na rede local, com login pelo usuário e senha do sistema, que entra na tabela de serviços;
  - API de leitura:
    - CPU/GPU;
    - vídeo: modo pedido e aplicado, refresh real, modeline, kHz, conector, driver;
    - discos, rede, processos, logs;
    - volume, que pode ser mudado;
  - FPS com histórico de 1 minuto guardado no navegador.
- **5b:**
  - abrir e fechar jogos;
  - configurações;
  - arquivos (upload e pastas);
  - tarefas;
  - screenshot;
  - torrent com o filtro do MAME;
  - terminal web;
  - trackball de toque pelo celular.
- **5c (experimental):**
  - transmissão por WebRTC em H.264 por hardware;
  - marquee do Pixelcade/ZeDMD como overlay para o OBS.

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
