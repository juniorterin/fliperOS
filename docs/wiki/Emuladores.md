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
| Fightcade 2 (baixado pelo Setup) | partidas online: FBNeo, SNES9x e FBA (Wine), Flycast | Xorg próprio | a sala em 640x480 (entrelaçado no 15 kHz); as partidas em 320x240 (Wine) e 640x240 (Flycast) |
| Steam, Heroic (GOG, Epic, Amazon) | jogos de PC | dentro do desktop LXDE | o do desktop |

Páginas próprias: [Fightcade 2](Fightcade-2.md), [ROMs, BIOS e arte](ROMs.md) (as pastas de `~`) e [Controles](Controles.md) (botões, SDL, calibração).

Todos aparecem no menu **Jogos** do LXDE ([Desktop e tema](Desktop.md)). O RetroArch usa `crt_switch_resolution 4` (o `/etc/switchres.ini` do Setup) na **largura nativa** de cada jogo quando a placa gera dotclock baixo (o "s" no resultado do teste de saídas: radeon/amdgpu), como o GroovyArcade; a super resolução 2560 fica só para as placas que não geram (Intel, NVIDIA). Em 2560 o RetroArch desenha as notificações nessa largura, e no tubo elas saíam espremidas (`video_retroarch_super`, gravado com o teste de saídas e na instalação). O vídeo do RetroArch é o driver `glcore` (OpenGL 3.2 core) e o áudio o `sdl2`, que sai direto no ALSA; os dois vêm do `retroarch.cfg` do sistema (`/etc/fliperos/retroarch`), que entra por cima do do usuário a cada abertura. Em placa que só tem OpenGL 2.x (Radeon X300 a X1950, Intel até o Core de 1ª geração, GeForce FX/6/7) o `glcore` não abre: o `fliperos-kms-run` pergunta ao Mesa (`eglinfo`) e, nelas, passa o `gl` no lugar.

**GroovyMAME na resolução nativa.** O GroovyMAME roda no X, como no modo X do GroovyArcade: chamado no console (pelo `fliperos-launch`, pela sessão do boot, por um frontend ou no terminal), o comando `groovymame` se abre num Xorg só para ele (`fliperos-x11-run`) e, com `modesetting 1` no `mame.ini`, o Switchres do GroovyMAME cria e troca o modo de cada jogo pelo XRandR — no gabinete, o MvC em `SR-1_384x224@59.64`, na tela inteira. Comandos sem tela (`-listxml`, `-listclones`, `-verifyroms`, `-showconfig`, `-createconfig`, `-version`...) rodam direto, sem subir o X. Como no `galauncher.xinitrc` do GroovyArcade, o `fliperos-x11-client` sobe o **openbox** antes do programa (`config/openbox-x11-run.xml`: sem bordas, sem atalhos): é ele que encaixa a janela de tela cheia na tela nova a cada troca de modo pelo XRandR; sem ele a janela ficava no tamanho do modo em que abriu (a interface num quarto da tela de 640x480, o jogo fora do lugar). Aberto sem jogo (a interface), o `groovymame` passa `-noautosync -waitvsync`: o jogo escolhido na interface roda no mesmo processo, e o emusync do GroovyMAME no X (`emusync_linux.cpp` do gm0289sr222f) usa o `/dev/dri/card0` que fechou ao sair da interface (o `osd_deinit` fecha o fd e não o zera; "drmCrtcGetSequence(-1)") — com o `autosync`, o `syncrefresh` tirava o throttle e o jogo corria acelerado. Aberto já com o jogo (frontends, linha de comando), o vblank funciona e o `autosync` fica. No KMS isso não funcionava nesta instalação: com `modesetting 0` e `SDL_KMSDRM_REQUIRE_DRM_MASTER=0` o Switchres aplicava o modo do jogo, mas o SDL continuava desenhando no tamanho do modo do boot (no `framebuffer` do debugfs do radeon, os quadros do GroovyMAME em 320x240 com a tela em 384x224) — o jogo saía esticado, espremido ou no meio com faixas pretas, conforme a resolução escolhida no Setup; com `modesetting 1` o modo nem era aplicado ("No way to get master rights") ou a tela ficava preta ("Could not queue pageflip: -13"). O RetroArch, no KMS, cria os quadros já no tamanho do jogo (384x224) e troca certo. Numa instalação anterior, o `fliperos-rootfs.sh` troca o `modesetting 0` de antes pelo 1. O outro motivo da largura dobrada é o formato da tela: com `aspect auto` o GroovyMAME tira o formato do modo atual, e o boot em 640x240 dá 8:3 — o dobro de 4:3, então o Switchres dobrava a largura de todo jogo ("SR(0): 768x224"). O `mame.ini` vem com `aspect 4:3`, como o GroovyArcade (`-aspect "4:3"`); o Setup só volta para `auto` quando o monitor escolhido é LCD.

**GroovyMAME: o release e o comando `groovymame`.** O build não compila mais o GroovyMAME (levava mais de uma hora): usa o release oficial para Linux (`gm0289sr222f`, MAME 0.289 com Switchres 2.22f, conferido por sha256), em `/usr/local/libexec/groovymame`, com as bibliotecas que ele pede (Qt6 é a do depurador). O comando `groovymame` — o que o `fliperos-launch`, os frontends e o terminal chamam — é o `config/fliperos-groovymame`, que passa `-inipath /etc/fliperos/mame`: o padrão do release é `.;ini`, relativo à pasta de onde se abre, então um `~/.mame/mame.ini` não vale; o que vale é o `/etc/fliperos/mame/mame.ini` (do usuário `fliperos`), que o Setup grava. O release só traz o binário; como o pacote do GroovyArcade, o build põe em `/usr/local/share/groovymame` os arquivos do código da mesma tag (commit `953db38`): `plugins` (o `hiscore`), a fonte `uismall.bdf`, `bgfx`, `artwork`, `language`, `ctrlr`, `keymaps` e `hash`. O `mame.ini` é feito como o do GroovyArcade: o `-createconfig` do próprio GroovyMAME (todas as opções da versão, no padrão dela), com as do `config/mame.ini` por cima, na linha de cada uma (`config/fliperos-mame-ini`, no build). As opções do GroovyArcade (o `-createconfig` do gasetup): `plugin hiscore`, `skip_gameinfo 1`, `video opengl`, `switchres_ini 1`, `sound sdl`, `aspect 4:3` — e a latência do Setup; a fonte da interface fica a do próprio MAME (`uifont default`), porque a de pixel do GroovyArcade (`uismall.bdf`) ficava pequena demais no gabinete (`lowlatency`, `autoframedelay`, `framedelay`). O `modesetting 1` também é o do GroovyArcade, com o GroovyMAME no X (o parágrafo "GroovyMAME na resolução nativa"). O que o GroovyMAME grava (cfg, nvram, recordes do hiscore, savestates) vai para `~/.mame`; o `ui.ini` ganha o `infos_text_size 1.00` do GroovyArcade e `font_rows 20`, junto das cores Dracula — o GroovyArcade usa 19, mas o MAME só aceita de 20 a 40 e troca o 19 pelo padrão 30, que em 224 linhas deixa a fonte com 7 pixels de altura e ilegível; com 20 ela fica com 11. Numa instalação anterior, o `fliperos-rootfs.sh` só acrescenta ao `mame.ini` e ao `ui.ini` as chaves que eles ainda não têm (o que já estava gravado fica, tema incluído); nas pastas, as relativas (o `.`, `cfg`, `snap` de um `-createconfig` puro: relativas à pasta de onde o GroovyMAME é aberto, enchiam a home de `cfg` e `nvram`) saem, e sem nenhuma absoluta vale a do `config/`. O `cfg`/`nvram` que ficou na home vai para `~/.mame`; com os dois, fica cada arquivo na versão mais nova. Num sistema instalado antes, o `fliperos-rootfs.sh` move o binário compilado para `/usr/local/libexec` e põe o atalho no lugar.

**Reset Geometry.** O Setup > Video Setup > Geometry grava a geometria medida no grid (`crt_range0` com monitor `custom` no `/etc/switchres.ini`, e `switchres_ini 1` no `mame.ini`). **Reset Geometry** desfaz: o Switchres volta ao preset do monitor escolhido, o que vale para o GroovyMAME (`switchres_ini 1`, como no GroovyArcade) e para o modo 4 do RetroArch, que leem o mesmo arquivo.

**Nada entrelaçado no 15 kHz.** No tubo de 15 kHz nenhum emulador do `fliperos-x11-run` abre em 480i (a exceção é a sala de jogos do Fightcade 2, que não cabe em 240 linhas; as partidas dele não): os de 480 linhas e os de 384 (Model 2 e 3) rodam em **640x240 progressivo** e **esticados a 200%** na horizontal — 640x240 tem pixels 8:3, e a imagem 4:3 só enche o tubo esticada: Flycast `rend.ScreenStretching=200` (300·L/4A), PCSX2 `AspectRatio = Stretch`, Dolphin `AspectRatio=3`, Supermodel `-fullscreen -res=640,240 -stretch`, Hypseus `-x 640 -y 240 -ignore_aspect_ratio` (opções no fim da linha: o Hypseus lê o jogo e o player primeiro) e o Model 2 com a tela cheia do `EMULATOR.INI` no modo da tabela. No gabinete o Flycast abria em 640x480i: o setup grava `frequency=15k`, e o script só reconhecia `15`, então todo emulador caía na coluna de 31 kHz.

**Sem texto ao abrir.** A saída do X, do Switchres e do emulador vai para `/opt/fliperos/logs/<programa>.log` (o último uso de cada um), e entre o desktop e o emulador a tela fica limpa; o Debug mode do Setup mostra tudo. O cursor do mouse só aparece nos emuladores com interface de mouse — PCSX2 (lista de jogos, assistente da BIOS), Dolphin, Flycast, o Model 2 no Wine e o Fightcade —, que o escondem sozinhos durante o jogo em tela cheia; os outros abrem com o Xorg `-nocursor`.

**GroovyMAME: o que falta.** Quando um jogo para no "System media audit failed", o motivo fica em `/opt/fliperos/logs/groovymame.log`, e `groovymame -verifyroms JOGO` lista os arquivos que faltam — BIOS e ROMs de dispositivo vêm em zips à parte do jogo. Tudo vai em `~/roms/mame` (as BIOS também podem ficar em `~/bios/mame`), da mesma versão do MAME (0.289).

O PCSX2 é o AppImage oficial (fixado por versão e sha256, extraído em `/opt/pcsx2`): o código atual dele exige SDL3 e Qt 6.10, que o Ubuntu 24.04 não tem. O Dolphin é compilado da versão estável (a distribuição oficial para Linux é o Flatpak, que traria ~1 GB de runtime).

**Cores do RetroArch.** Vêm 6 compilados, para funcionar sem rede: FCEUmm (NES), Snes9x, Genesis Plus GX (Mega Drive/Master System), mGBA, PCSX ReARMed (PS1) e MAME 2010. Qualquer outro se baixa no próprio RetroArch, em **Online Updater > Core Downloader** (do buildbot da libretro): cores, `.info` e perfis de controle ficam em `/opt/fliperos/retroarch`, do usuário `fliperos`, então o menu grava sem root. Os `.info` e os perfis de fábrica vêm fixados por commit (`libretro-core-info`, `retroarch-joypad-autoconfig`). O MAME 2010 é compilado sem o `_FORTIFY_SOURCE` que o gcc do Ubuntu liga sozinho (`ARCHOPTS=-U_FORTIFY_SOURCE`): o MAME 0.139 escreve 9 bytes num `char[8]` ao iniciar a CPU H8/3002, e com a checagem a glibc fechava o RetroArch (`buffer overflow detected`) em todo jogo de Namco System 12 (Tekken 3, Tekken Tag, Soul Calibur), System 23 e ND-1.

## Rodar um programa em 640x240

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

**GroovyMAME e RetroArch** não passam por aqui: eles trocam de modo sozinhos a cada jogo. No GroovyMAME, `interlace 0` no `/etc/fliperos/mame/mame.ini` faz o Switchres nunca escolher um modo entrelaçado (os jogos de 480 linhas saem em 240p). No RetroArch, o core **MAME 2010** já vem assim: o CRT SwitchRes lê um `switchres.ini` só do core, por cima do `/etc/switchres.ini`, em `~/.config/retroarch/config/MAME 2010/MAME 2010.switchres.ini` (de `config/retroarch-switchres`), com `interlace 0` — um jogo de 640x480 (Namco System 12) abre em 640x240 progressivo, com a imagem encolhida na vertical, em vez de 480i. O mesmo arquivo com o nome de outro core (`config/<Core>/<Core>.switchres.ini`) faz o mesmo nele; para voltar ao 480i, `interlace 1` e sem a linha `# FliperOS` do começo (as atualizações só regravam o arquivo que a tem).

## Laserdisc (Hypseus Singe)

Os jogos de laserdisc ficam em `/opt/fliperos/roms/hypseus`, que é o `~/.hypseus` (pela rede: `\\fliperos\FliperOS\roms\hypseus`): a ROM em `roms/<jogo>.zip`, o vídeo do laserdisc em `vldp/<jogo>/` com o framefile `<jogo>.txt`, e os jogos Singe em `singe/<jogo>/`. Para abrir no CRT (640x240 no 15 kHz, tela cheia):

```sh
/opt/fliperos/bin/fliperos-x11-run hypseus lair     # Dragon's Lair
/opt/fliperos/bin/fliperos-x11-run singe timegal    # um jogo Singe
```

no console ou como comando de um frontend. O Hypseus não tem menu próprio (precisa do nome do jogo), por isso não tem atalho em Jogos. É o Hypseus Singe v2.12.1 (a série 3 exige SDL3, que o Ubuntu 24.04 não tem), instalado como o README do projeto manda (`hypseus`/`singe` são os scripts dele, `hypseus.bin` o programa).

## OpenBOR

Os jogos (`.pak`) vão em `/opt/fliperos/roms/openbor/Paks` (pela rede: `\\fliperos\FliperOS\roms\openbor\Paks`). Menu **Jogos > OpenBOR** abre o menu do próprio OpenBOR, que lista os paks.

## Model 2 (Wine)

O Model 2 Emulator (ElSemi) é freeware de código fechado, só para Windows, sem permissão clara de redistribuição — por isso **não vem na imagem**. Copie os arquivos do `m2emulator` 1.1a (o `emulator_multicpu.exe` e o resto) para `/opt/fliperos/model2` e as ROMs para `/opt/fliperos/model2/roms` (pela rede: `\\fliperos\FliperOS\model2`). O menu **Jogos > Model 2** abre o emulador no Wine (`fliperos-model2`, com um prefixo do Wine só dele em `~/.local/share/fliperos/wine-model2`); sem o emulador copiado, ele mostra essas instruções. Tela cheia e resolução se ajustam no `EMULATOR.INI` do próprio emulador.

## Steam e GOG

**Steam**: o `steam-installer` do Ubuntu; na primeira abertura a Valve baixa o cliente (centenas de MB, precisa de rede). **GOG**: não existe cliente oficial para Linux; vem o **Heroic Games Launcher** (GOG, Epic e Amazon; o mesmo do Steam Deck), que roda os jogos de Windows com o Wine/Proton que ele mesmo baixa. Os dois abrem **dentro do desktop LXDE** (são programas do X), pelo menu **Jogos**. A interface deles foi feita para telas maiores: num CRT de 15 kHz a 640x480 ela fica apertada — num monitor de 31 kHz ou LCD o uso é bem melhor.
