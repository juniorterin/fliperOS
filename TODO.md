# Pendências do FliperOS

O que já foi pedido e ainda não foi feito. Quando um item fica pronto, ele sai daqui e o que mudou vai para o [CHANGELOG](CHANGELOG.md).

## Vídeo

### 480i puro por sistema (fase 3c)

Hoje, num monitor de 15 kHz, nada que tenha 480 linhas abre em 480i por padrão. A ideia é poder escolher, sistema por sistema, entre o hack de 640x240 e o 480i de verdade com o filtro de flicker. A escolha ficaria numa tela do Video Setup e seria aplicada pelo `fliperos-x11-run` e pelo `fliperos-kms-run`.

**Decisão em aberto:** todo sistema continua em 640x240 por padrão e o 480i só entra quando a pessoa escolhe? Ou algum sistema já vem em 480i, por exemplo Dreamcast/Naomi com texto pequeno?

Como está hoje, em 15 kHz:

| Modo | Quem usa |
| --- | --- |
| 640x240 esticado a 200% (`config/fliperos-emulator-modes.conf`) | Flycast (também o do Fightcade), PCSX2, Dolphin, Hypseus e Singe; Supermodel, Model 2 e SM2-Emu em 640x240@57.524 |
| Modo de boot do Video Setup (640x240), sem troca | console e Setup (texto e gráfico), Attract-Mode Plus, ES-DE, RetroFE, Pegasus, menu do RetroArch, interface do GroovyMAME |
| Modo nativo de cada jogo | RetroArch e GroovyMAME. Jogos de 480 linhas: o GroovyMAME (`interlace 0`) e o core MAME 2010 descem para 240p, com a imagem achatada; os outros cores do RetroArch ainda podem abrir em 480i |
| 320x240 | OpenBOR, KOF Final Attack |
| Fightcade | lobby em 512x448 entrelaçado; FBNeo/FBA no modo de cada jogo; SNES9x em 256x224 |
| Resolução do Screen Resolution | desktop LXDE (640x480 em 15 kHz já é 480i) |

O filtro de flicker do 480i (Setup > Video Setup > Interlace flicker filter) está pronto, mas ainda não foi visto no tubo. Hoje ele só age onde já existe 480i: no desktop em 640x480, no lobby do Fightcade e nos cores do RetroArch que abrem em 480i.

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

Uma tela animada na interface gráfica que apresenta o menu, os botões e as seções. Oferecida no primeiro boot e no Setup. No modo texto, vira páginas.

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
