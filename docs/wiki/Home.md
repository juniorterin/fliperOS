**FliperOS** é um Ubuntu 24.04 (amd64) para gabinetes de fliperama com monitor CRT, no estilo do GroovyArcade: **kernel 15 kHz** (kernel.org 6.18 LTS + patches D0023R, os mesmos do `linux-15khz` do GroovyArcade), Switchres, emuladores e frontends prontos, e um menu de configuração feito para a tela do tubo.

A mídia é **só de instalação** e segue o fluxo do GroovyArcade: menu de boot com a faixa de frequência, teste das saídas de vídeo com voz, *Testing Results*, menu **FliperOS Setup** e instalação no HD/SSD. No sistema instalado, o mesmo programa vira o menu de configuração que aparece quando o frontend fecha. As telas são do **`fliperos-setup`**, em Bash com [Gum](https://github.com/charmbracelet/gum), tema **Dracula** e textos em inglês, pensadas para **640x480i**: 80x30 caracteres, nada animado nem piscando.

> Em desenvolvimento: a 0.7 é testada em VM (QEMU) e num gabinete com CRT de 15 kHz.

## Para usar

| Página | O que tem |
| --- | --- |
| [Instalar](Instalar.md) | Gravar a mídia, o menu de boot, o teste das saídas de vídeo, instalar no HD/SSD, o Recovery Mode |
| [Sistema instalado](Sistema-instalado.md) | O boot, o launcher padrão, o menu do Setup item por item (vídeo, áudio, rede, debug, atualização) |
| [Frontends](Frontends.md) | Escolher o frontend do boot, os temas de 240p do EmulationStation e do Pegasus, o repositório APT |
| [Emuladores](Emuladores.md) | Cada emulador, em que modo de vídeo abre, GroovyMAME, RetroArch, rodar um programa em 640x240, laserdisc, Model 2, Steam e GOG |
| [Fightcade 2](Fightcade-2.md) | Partidas online: download pelo Setup, ROMs, os modos da sala e das partidas, teclas |
| [ROMs, BIOS e arte](ROMs.md) | As pastas de `~` (`roms`, `bios`, `media`, `config`), o MAME ROM Cleaner, o CHD Cleaner, os jogos livres |
| [Scraper](Scraper.md) | Capas, screenshots, logos, vídeos e textos dos jogos, para todos os frontends |
| [Controles](Controles.md) | Botões de cada jogador, pistola e volante, porta paralela, quirks USB, como o SDL vê cada controle |
| [Desktop e tema](Desktop.md) | O LXDE, os programas do menu, a troca de resolução, o tema Dracula |
| [Latência](Latency.md) | Os modos Standard e Low latency, o que cada ajuste faz, hardware recomendado, como medir |

## Para mexer

| Página | O que tem |
| --- | --- |
| [Kernel 15 kHz](Kernel-15-kHz.md) | O kernel e os patches |
| [Build e testes](Build-e-testes.md) | Gerar a ISO em Docker, as opções do build, a auditoria da ISO, publicar o release, os testes, atualizar um gabinete pela rede |
| [Arquitetura](Arquitetura.md) | Como o `fliperos-setup` é organizado, os outros componentes (splash, rede, diagnóstico) e o que é cada arquivo do repositório |
| [Fontes](Fontes.md) | De onde veio cada parte: GroovyArcade, Switchres e os demais projetos consultados |

As páginas desta wiki são mantidas no repositório, em [`docs/wiki`](https://github.com/juniorterin/fliperOS/tree/main/docs/wiki), e publicadas aqui pelo `tools/wiki-publish.sh`: para corrigir uma página, mude o arquivo de lá.
