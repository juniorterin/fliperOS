# FliperOS 0.7

Ubuntu 24.04 (amd64) para gabinetes de fliperama com monitor CRT, no estilo do GroovyArcade: **kernel 15 kHz**, Switchres, emuladores e frontends prontos, e um menu de configuração (`fliperos-setup`) feito para a tela do tubo.

Em desenvolvimento: a 0.7 é testada em VM (QEMU) e num gabinete com CRT de 15 kHz. A documentação completa está na **[wiki](https://github.com/juniorterin/fliperOS/wiki)**.

## O que vem

- **Vídeo**: kernel 6.18 LTS com os patches de 15 kHz, boot em 15, 25 ou 31 kHz ou LCD, Switchres.
- **Emuladores**: GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Model 2, Hypseus Singe e OpenBOR; Steam e Heroic no desktop.
- **Frontends**: Attract-Mode Plus, EmulationStation (ES-DE), Pegasus e Fightcade 2.
- **Setup**: vídeo e geometria, áudio, rede, scraper, limpeza de romsets do MAME, controles (botões, pistola, volante) e latência.
- **Pastas** `roms`, `bios`, `media` e `config` em `~` e pela rede (Samba); desktop LXDE com loja de aplicativos.

## Instalar

A ISO de cada versão sai em [Releases](https://github.com/juniorterin/fliperOS/releases), com o que mudou ([CHANGELOG.md](CHANGELOG.md)).

1. Grave a ISO **byte a byte** (balenaEtcher, Rufus em "DD Image mode" ou `dd`; Rufus no modo padrão e Ventoy não servem) e desative o Secure Boot.

   ```bash
   sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
   ```

2. Ligue o gabinete pela mídia e espere 30 segundos: ela sobe em **15 kHz** (o menu de boot não aparece num tubo de 15 kHz).
3. Aperte **Enter** quando enxergar a tela, escolha o monitor e **Install to HD/SSD**, que apaga o disco escolhido.
4. Reinicie, escolha o launcher padrão e ponha as ROMs em `~/roms` (pela rede, `\\fliperos\roms`).

## Build e testes

Sempre em Docker ([`CLAUDE.md`](CLAUDE.md) diz por quê).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso

docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

## Documentação

**Para usar:** [Instalar](https://github.com/juniorterin/fliperOS/wiki/Instalar) · [Sistema instalado](https://github.com/juniorterin/fliperOS/wiki/Sistema-instalado) · [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) · [Emuladores](https://github.com/juniorterin/fliperOS/wiki/Emuladores) · [Fightcade 2](https://github.com/juniorterin/fliperOS/wiki/Fightcade-2) · [ROMs, BIOS e arte](https://github.com/juniorterin/fliperOS/wiki/ROMs) · [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper) · [Controles](https://github.com/juniorterin/fliperOS/wiki/Controles) · [Desktop e tema](https://github.com/juniorterin/fliperOS/wiki/Desktop) · [Latência](https://github.com/juniorterin/fliperOS/wiki/Latency)

**Para mexer:** [Kernel 15 kHz](https://github.com/juniorterin/fliperOS/wiki/Kernel-15-kHz) · [Build e testes](https://github.com/juniorterin/fliperOS/wiki/Build-e-testes) · [Arquitetura](https://github.com/juniorterin/fliperOS/wiki/Arquitetura) · [Fontes](https://github.com/juniorterin/fliperOS/wiki/Fontes)

As páginas ficam em [`docs/wiki`](docs/wiki) e vão para a wiki com `bash tools/wiki-publish.sh`. O [`fliperos-doc.html`](fliperos-doc.html) é tudo num arquivo só, para ler sem rede (`tools/render-docs.py`), e [`docs/wikipedia`](docs/wikipedia) guarda o rascunho de um artigo para a Wikipédia.
