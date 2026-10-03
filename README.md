# FliperOS 0.7

Ubuntu 24.04 (amd64) para gabinetes de fliperama com monitor CRT, no estilo do GroovyArcade: **kernel 15 kHz**, Switchres, emuladores e frontends prontos, e um menu de configuração feito para a tela do tubo (Bash + [Gum](https://github.com/charmbracelet/gum), tema Dracula, textos em inglês).

A mídia é só de instalação: menu de boot com a faixa de frequência, teste das saídas de vídeo com voz, instalação no HD/SSD. No sistema instalado, o mesmo programa (`fliperos-setup`) é o menu que aparece quando o frontend fecha.

> 15 kHz foi validado no gabinete com a versão anterior (kernel padrão + EDID, 640x240). O kernel 15 kHz, o 640x480i, o teste de saídas e o instalador desta versão foram validados em VM (QEMU); o gabinete real ainda precisa confirmar.

A documentação completa está na **[wiki](https://github.com/juniorterin/fliperOS/wiki)**.

## O que vem

- **Vídeo**: kernel.org 6.18 LTS com os patches de 15 kHz do GroovyArcade, entradas de boot para 15, 25 e 31 kHz e LCD, Switchres, e o Video Setup (monitor, orientação, resolução, geometria).
- **Emuladores**: GroovyMAME, RetroArch (6 cores e o Online Updater), Flycast, PCSX2, Dolphin, Supermodel, Hypseus Singe e OpenBOR; Model 2 no Wine; Steam e Heroic no desktop. Cada um abre no modo de vídeo certo para o tubo.
- **Frontends**: Attract-Mode Plus, EmulationStation (ES-DE) e Pegasus, com temas de 240p; **Fightcade 2**, baixado do site dele pelo Setup.
- **Ferramentas do Setup**: Scraper (capas, vídeos e textos dos jogos), MAME ROM Cleaner e CHD Cleaner, jogos livres, mapa de botões por jogador, calibração de pistola e volante, quirks de controles USB, modos de latência.
- **Pastas em `~`**, também pela rede (Samba): `roms`, `bios`, `media` e `config`.
- **Desktop LXDE** com tema Dracula, loja de aplicativos (Flatpak), navegador e cliente de torrent.

## Instalar

1. Grave a ISO **byte a byte** num pendrive (balenaEtcher, Rufus em "DD Image mode" ou `dd`) e desative o Secure Boot. Rufus no modo padrão, Ventoy e UNetbootin não servem.

   ```bash
   sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
   ```

2. Ligue o gabinete pela mídia. Sem tecla, em 30 segundos sobe a entrada **15 kHz** (o menu de boot não aparece num tubo de 15 kHz; a primeira coisa legível é o splash).
3. No teste de saídas, aperte **Enter** quando enxergar a tela, confira o *Testing Results* e escolha o tipo de monitor.
4. **Install to HD/SSD** apaga o disco escolhido e instala; depois, **Reboot**.
5. No primeiro boot, escolha o launcher padrão. As ROMs vão em `~/roms` (pela rede, `\\fliperos\roms`).

Detalhes: [Instalar](https://github.com/juniorterin/fliperOS/wiki/Instalar).

## Build

Sempre em Docker ([`CLAUDE.md`](CLAUDE.md) proíbe chroot com o `/dev` do host no WSL).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso
```

Opções do build, auditoria da ISO e como atualizar um gabinete pela rede sem ISO nova: [Build e testes](https://github.com/juniorterin/fliperOS/wiki/Build-e-testes).

## Testes

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

## Documentação

| Para usar | |
| --- | --- |
| [Instalar](https://github.com/juniorterin/fliperOS/wiki/Instalar) | Gravar a mídia, menu de boot, teste das saídas, instalação, Recovery Mode |
| [Sistema instalado](https://github.com/juniorterin/fliperOS/wiki/Sistema-instalado) | O boot, o launcher padrão e o menu do Setup, item por item |
| [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) | O frontend do boot, os temas de 240p, o repositório APT |
| [Emuladores](https://github.com/juniorterin/fliperOS/wiki/Emuladores) | Cada emulador e o modo de vídeo em que abre |
| [Fightcade 2](https://github.com/juniorterin/fliperOS/wiki/Fightcade-2) | Partidas online: download, ROMs, modos de vídeo, teclas |
| [ROMs, BIOS e arte](https://github.com/juniorterin/fliperOS/wiki/ROMs) | As pastas de `~`, o ROM Cleaner, o CHD Cleaner, os jogos livres |
| [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper) | Arte e textos dos jogos para os frontends |
| [Controles](https://github.com/juniorterin/fliperOS/wiki/Controles) | Botões, pistola, volante, porta paralela, quirks USB |
| [Desktop e tema](https://github.com/juniorterin/fliperOS/wiki/Desktop) | O LXDE, a troca de resolução, o tema Dracula |
| [Latência](https://github.com/juniorterin/fliperOS/wiki/Latency) | Os modos de latência, hardware recomendado, como medir |

| Para mexer | |
| --- | --- |
| [Kernel 15 kHz](https://github.com/juniorterin/fliperOS/wiki/Kernel-15-kHz) | O kernel e os patches |
| [Build e testes](https://github.com/juniorterin/fliperOS/wiki/Build-e-testes) | A ISO, as opções do build, os testes, o gabinete pela rede |
| [Arquitetura](https://github.com/juniorterin/fliperOS/wiki/Arquitetura) | O `fliperos-setup`, os outros componentes, o que é cada arquivo |
| [Fontes](https://github.com/juniorterin/fliperOS/wiki/Fontes) | GroovyArcade, Switchres e os demais projetos consultados |

As páginas da wiki são mantidas neste repositório, em [`docs/wiki`](docs/wiki), junto com o código: muda-se o arquivo de lá, e `bash tools/wiki-publish.sh` publica. O [`fliperos-doc.html`](fliperos-doc.html) é a mesma documentação num arquivo só, para ler sem rede (`tools/render-docs.py`).
