# FliperOS 0.8

[English](README.md) | **Português**

Ubuntu 24.04 (amd64) para gabinetes de fliperama com monitor CRT, no estilo do GroovyArcade: **kernel de 15 kHz**, Switchres, emuladores e frontends prontos para jogar e um menu de configuração (`fliperos-setup`) feito para a tela do tubo.

Em desenvolvimento: a 0.8 é testada no QEMU e num gabinete com CRT de 15 kHz. Documentação completa na **[wiki](https://github.com/juniorterin/fliperOS/wiki)** (em inglês). Site: **[fliperos.juniorter.in](https://fliperos.juniorter.in)** (código em [`website/`](website)).

## O que vem nele

- **Vídeo**: kernel 6.18 LTS com os patches de 15 kHz, boot em 15, 25 ou 31 kHz ou LCD, Switchres.
- **Emuladores**: GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Model 2, Hypseus Singe e OpenBOR; Wine, Steam e Heroic pelo Setup > Extras.
- **Frontends**: Attract-Mode Plus, EmulationStation (ES-DE), Pegasus e Fightcade 2.
- **Pistola de luz**: GunCon 2 pronta para usar (driver por DKMS), calibrada para o tubo no Setup > Joysticks. Volantes também.
- **Setup**: vídeo, geometria, áudio, rede, scraper, listas de ROMs, limpeza de romset do MAME, controles e latência.
- **Pastas** `roms`, `bios`, `media` e `config` em `~` e pela rede (Samba); desktop LXDE com loja de aplicativos.
- **SSH** ligado desde o primeiro boot (`ssh fliperos@fliperos.local`, senha `fliperos`). Por baixo dos menus é um Ubuntu comum, então um assistente de IA consegue configurá-lo pelo SSH.

## Do zero ao jogo: passo a passo

Este guia vai do gabinete vazio até um jogo na tela. Cada passo diz o que vai aparecer e o que apertar. Os detalhes de cada tela estão nas páginas da wiki citadas pelo caminho (em inglês).

### 1. O que você precisa

- **Um PC (amd64)** para o gabinete. Para fliperama até os anos 90 e consoles até o PlayStation, bastam um processador de 2 núcleos, 4 GB de RAM e um disco de 16 GB. Para PS2, Model 3 e Dreamcast, um processador de 4 núcleos com AVX2 (Core i7-7700, Ryzen 5 3600 ou mais novo), 16 GB e SSD. O disco onde você instalar é **apagado por inteiro**.
- **Uma placa de vídeo com saída analógica.** A melhor opção é uma **AMD Radeon com VGA ou DVI-I**, da série HD 2000 até as R7/R9 (GCN 1.0), que gera 15 kHz nativamente. Intel e NVIDIA funcionam em 15 kHz com os modos de "super resolução". Placas sem saída analógica precisam de um conversor DisplayPort/HDMI para VGA.
- **O monitor**: um CRT de fliperama (15 kHz), uma TV por um adaptador VGA para SCART/componente ou um monitor de 25/31 kHz. LCD também funciona.
- **Um pendrive de 4 GB ou mais** (ele será apagado).
- **Um teclado USB** para a instalação. Depois disso, o painel ou um controle mexe em todos os menus.
- **Conexão de rede** (cabo ou Wi-Fi), para copiar os jogos de outro computador e receber as atualizações. É opcional, mas facilita tudo.
- **Outro computador** (Windows, Linux ou macOS) para gravar o pendrive e, depois, copiar os jogos pela rede.

### 2. Baixe a ISO

1. Abra os [Releases](https://github.com/juniorterin/fliperOS/releases) e baixe o `fliperos-0.8.iso` da versão mais recente (o que mudou está no [CHANGELOG.md](CHANGELOG.md), em inglês).
2. Se o release trouxer um SHA-256, confira: `sha256sum fliperos-0.8.iso` no Linux, `Get-FileHash fliperos-0.8.iso` no PowerShell do Windows.

### 3. Grave o pendrive

A ISO tem de ser gravada **byte a byte**. Programas que refazem a estrutura de boot do pendrive estragam a gravação: **o Rufus no modo padrão ("imagem ISO"), o Ventoy e o UNetbootin não funcionam.**

- **Windows, macOS ou Linux, o mais fácil**: [balenaEtcher](https://etcher.balena.io). *Flash from file* > escolha a ISO > *Select target* > o pendrive > *Flash!*.
- **Windows com o Rufus**: escolha o pendrive e a ISO, clique em *INICIAR* e, quando ele perguntar, escolha **"Gravar no modo Imagem DD"**.
- **Linux**: descubra o pendrive com `lsblk` (aqui `/dev/sdX`; o dispositivo errado apaga o disco errado) e rode:

  ```bash
  sudo dd if=fliperos-0.8.iso of=/dev/sdX bs=4M status=progress conv=fsync
  ```

### 4. Prepare a BIOS do gabinete

Entre na configuração da BIOS/UEFI (em geral **Del**, **F2** ou **F10** logo ao ligar) e:

1. **Desligue o Secure Boot**: o kernel de 15 kHz é próprio e não é assinado, e com o Secure Boot ligado ele não inicia.
2. **Modo SATA em AHCI** (não RAID nem Intel RST); senão o instalador não enxerga o disco.
3. **Boot pelo pendrive**: coloque-o em primeiro na ordem de boot, ou use o menu de boot de uma vez só (muitas vezes **F8**, **F11** ou **F12**). Funciona em BIOS (legado) e em UEFI.

Salve e saia com o pendrive conectado.

### 5. Dê boot pelo pendrive

1. **Espere uns 30 segundos sem apertar nada.** O menu de boot (15 kHz, 25 kHz, 31 kHz, LCD...) é desenhado em 31 kHz, então **ele não aparece num tubo de 15 kHz**. Sem nenhuma tecla, a opção **15 kHz** entra sozinha, que é a segura para gabinete. Num monitor de PC ou LCD, você pode escolher *SVGA / LCD monitor* no menu.
2. O splash do FliperOS aparece, já em 15 kHz.
3. **Teste das saídas.** O FliperOS liga uma saída de vídeo por vez e uma voz diz *"Testing output VGA 1. If you can see this screen, press Enter."* Quando o texto *"If you can see this screen clearly, press ENTER"* estiver legível no **seu** monitor, aperte **Enter**. Sem Enter ele passa para a próxima saída e repete a rodada até três vezes.
4. **Testing Results** mostra a placa, a saída, o modo e a frequência. Escolha **Validate settings** (ou **Repeat test** para testar de novo).
5. **Tipo de monitor**: escolha o seu na lista (por exemplo *generic_15* para um monitor de fliperama comum ou TV, *arcade_15*, *ntsc*, *pal* ou um modelo específico). A lista abre na sugestão da opção de boot. A tabela completa das opções de boot está em [Install](https://github.com/juniorterin/fliperOS/wiki/Install).

### 6. Instale no disco

Abre o menu **FliperOS Setup** (Install to HD/SSD, Recovery Mode, Terminal, Shutdown). As setas mexem, o **Enter** confirma e o **Esc** volta.

1. Escolha **Install to HD/SSD**.
2. **Do you want to configure video?** Escolha *Yes* para ajustar agora (dá para fazer depois em Setup > Video Setup):
   - **Monitor Type**: o mesmo monitor do teste;
   - **Monitor Orientation**: horizontal, ou vertical para um monitor girado (jogos verticais);
   - **Resolution**: os modos que o seu monitor e a sua placa aceitam (a sugestão serve);
   - **Geometry**: uma grade para centralizar a imagem e acertar o tamanho dela no tubo. Ajuste com as setas e salve com o Enter.
3. **Automatically Partition**: escolha o disco pelo modelo, tamanho e tipo (USB/NVMe/SATA). Se o seu não aparecer, **My drive is not listed (details)** explica o porquê (quase sempre o modo SATA do passo 4).
4. **WARNING**: mostra o disco que será **apagado por inteiro**. Confira e confirme (*No* volta para a lista).
5. **Installing FliperOS**: uma barra de progresso com a etapa atual. Leva alguns minutos.
6. **Installation completed successfully**: tire o pendrive e escolha **Reboot now**.

### 7. Primeiro boot do sistema instalado

1. O gabinete vai direto para o splash, sem texto.
2. **Choose default launcher**: o que abre toda vez que o gabinete liga. Para um gabinete, escolha o **Attract-Mode Plus** (lista de jogos com imagens, feita para fliperama). As outras opções são EmulationStation (ES-DE), Pegasus, RetroArch, o desktop LXDE ou o próprio FliperOS Setup. Dá para trocar depois em Setup > Frontend.
3. Quando você sai do launcher (Esc), aparece o **menu do FliperOS**: *Start frontend*, *Setup (video, audio, network...)*, *Start desktop*, *Exit to shell*, *Shutdown / Reboot*. O título mostra o IP do gabinete.
4. **Rede**: o cabo de rede funciona sozinho. Para Wi-Fi: *Setup > Network Setup*, escolha a rede e digite a senha. Conectado, o IP aparece no título do menu.
5. **Atualizações**: a cada boot com internet, se houver uma atualização do FliperOS, uma tela diz o que ela traz e pergunta **Apply now** (aplicar agora) ou **Not now** (agora não).

### 8. Configure os controles

Nos menus, o painel ou um controle já funciona como teclado: direcional = setas, botão 1 = Enter, botão 2 = Esc.

1. *Setup > Joysticks > Button mapping*.
2. Para cada jogador, aperte o que ele pede, nesta ordem: cima, baixo, esquerda, direita, **botões 1 a 6** na ordem do painel (1 2 3 na fileira de cima, 4 5 6 na de baixo), **Start** e **Ficha** (Coin). O primeiro comando apertado diz qual controle é daquele jogador. Sem nada apertado por 8 segundos, aquele comando fica de fora.
3. O mapeamento vai para todos os emuladores de uma vez (GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Hypseus e OpenBOR).
4. Pistola de luz (GunCon 2), volante e pedais têm calibradores no mesmo menu, e o *Setup > Quirks* corrige encoders USB que chegam errados (por exemplo, um encoder duplo que aparece como um jogador só). Veja [Controls](https://github.com/juniorterin/fliperOS/wiki/Controls).

### 9. Copie os seus jogos

Use só jogos que você tem direito de usar (cópias dos seus originais, ou os jogos homebrew livres do *Setup > Downloader > Free games*).

**Pela rede (o mais fácil)**, de outro computador na mesma rede:

- **Windows**: na barra de endereço do Explorador de Arquivos digite `\\fliperos\roms` (ou `\\IP-do-gabinete\roms`) e aperte Enter. Se pedir login, use `fliperos` / `fliperos`.
- **macOS**: Finder > Ir > Conectar ao Servidor > `smb://fliperos.local/roms`.
- **Linux**: `smb://fliperos.local/roms` no gerenciador de arquivos.
- Também há: `\\fliperos\bios` (arquivos de BIOS), `\\fliperos\media` (imagens e vídeos) e `\\fliperos\config` (configurações dos emuladores).

**Sem rede**: copie os arquivos para um pendrive, abra o *Start desktop* (LXDE) e arraste-os para a pasta `roms` no gerenciador de arquivos. Ou use SFTP (`fliperos@fliperos.local`, senha `fliperos`).

**Cada emulador tem a sua pasta** em `roms`. Copie os arquivos como vieram: os sets do MAME ficam zipados e **nunca são renomeados** (`sf2ce.zip`, não `Street Fighter II.zip`).

| Pasta | Jogos | Emulador |
| --- | --- | --- |
| `mame` | Fliperama: sets do MAME (`.zip`, `.7z`) e as pastas de CHD | GroovyMAME |
| `naomi`, `naomi2`, `atomiswave` | Sets de Sega Naomi e Sammy Atomiswave | Flycast |
| `model3` | Sets de Sega Model 3 | Supermodel |
| `model2` | Sets de Sega Model 2 | Model 2 Emulator (precisa do Setup > Extras > Wine) |
| `dreamcast` | `.gdi`, `.cdi`, `.chd` | Flycast |
| `ps2` | `.iso`, `.chd`, `.cso` | PCSX2 |
| `dolphin` | GameCube e Wii (`.iso`, `.rvz`, `.wbfs`) | Dolphin |
| `retroarch/<core>` | Consoles e computadores; o `_info.txt` de cada pasta lista as extensões | RetroArch |
| `openbor/Paks` | Jogos do OpenBOR (`.pak`) | OpenBOR |

**BIOS** vão em `bios`, nunca numa pasta de jogos: `bios/mame` para o MAME (`neogeo.zip`, `qsound.zip`...), `bios/dc` para o Flycast (`naomi.zip`, `awbios.zip`, `dc_boot.bin`), `bios/ps2` para o PCSX2 e a própria pasta `bios` para os cores do RetroArch.

Tem um romset completo do MAME? *Setup > Cleaner > MAME ROM Cleaner* deixa só os jogos que funcionam e combinam com o seu gabinete (horizontal ou vertical, os controles que você tem) e os põe na pasta do emulador certo. Mais em [ROMs, BIOS and artwork](https://github.com/juniorterin/fliperOS/wiki/ROMs).

### 10. Faça o frontend mostrar os jogos

1. *Setup > Frontend* > escolha o **Attract-Mode Plus** de novo (mesmo que ele já seja o padrão). O Setup cria um sistema para cada pasta que tem jogos. Faça isso de novo sempre que uma pasta receber os primeiros jogos.
2. **Nomes de verdade** (*Street Fighter II* em vez de `sf2`): *Setup > AttractPlus ROM List*, para as pastas de fliperama. Funciona sem internet e também traz ano, fabricante e os clones.
3. **Imagens** (telas, logos, vídeos, descrições): *Setup > Scraper*, que precisa de internet. Veja [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper).
4. Jogos novos colocados depois numa pasta que já aparece no Attract-Mode: rode de novo o *Setup > AttractPlus ROM List* ou o *Setup > Scraper*. Detalhes em [Adding games](https://github.com/juniorterin/fliperOS/wiki/Adding-games).

### 11. Jogue

1. No menu do FliperOS escolha **Start frontend** (ou só ligue o gabinete: o launcher padrão abre sozinho).
2. No **Attract-Mode Plus**: **esquerda/direita** trocam o sistema (MAME, Naomi, PCSX2...) e **cima/baixo** andam pelos jogos. Cada sistema vem com filtros (All Games, Most Played, gêneros, fabricantes, anos); o **Tab** abre a configuração do Attract-Mode, onde *Controls* liga botões para trocar de filtro e o que mais você quiser.
3. Aperte o **botão 1** (ou Enter) num jogo. A tela fica preta por um instante enquanto o Switchres acerta o modo de vídeo daquele jogo, e o jogo começa.
4. Ponha crédito com a **Ficha** e comece com o **Start**.
5. **Sair do jogo**: no GroovyMAME, **Esc** no teclado. No RetroArch, **Start + Ficha** juntos abrem o menu dele, e então *Quick Menu > Close Content*. Os outros emuladores usam a tecla ou o menu de saída de cada um ([Emulators](https://github.com/juniorterin/fliperOS/wiki/Emulators)). Você volta para a lista de jogos.
6. **Esc** no Attract-Mode (e confirmar) sai do frontend e volta para o menu do FliperOS, onde *Shutdown / Reboot* desliga o gabinete com segurança.

### 12. Se algo der errado

- **Sem imagem no boot**: espere os 30 segundos (o menu não aparece em 15 kHz). Num tubo só de 15 kHz, ligue um LCD temporariamente para escolher outra opção de boot.
- **O instalador não lista o disco**: modo SATA em AHCI na BIOS. *My drive is not listed (details)* mostra o que o Linux enxerga.
- **A imagem está fora do centro ou grande demais**: *Setup > Video Setup > Geometry*.
- **Um sistema não aparece no frontend**: a pasta precisa de pelo menos um arquivo de jogo (o `_info.txt` não conta); depois escolha o frontend de novo em *Setup > Frontend*.
- **Um jogo não abre**: ligue o *Setup > Debug mode* para ver as mensagens do emulador na tela; sem ele, elas ficam em `/opt/fliperos/logs`. Confira as BIOS em `bios`.
- **Sem som**: *Setup > Audio Setup* escolhe a placa e o volume e toca um teste.
- **Algo que os menus não cobrem**: pelo SSH (`ssh fliperos@fliperos.local`, senha `fliperos`) é um Ubuntu 24.04 comum, e um assistente de IA com acesso ao terminal consegue configurar para você. Numa rede que você não controla, troque a senha com `passwd`.

Mais em [Installed system](https://github.com/juniorterin/fliperOS/wiki/Installed-system), [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) e [Latency](https://github.com/juniorterin/fliperOS/wiki/Latency).

## Build e testes

Sempre no Docker (o [`CLAUDE.md`](CLAUDE.md) explica por quê).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.8.iso

docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

## Documentação

As páginas da wiki estão em inglês.

**Para usar:** [Install](https://github.com/juniorterin/fliperOS/wiki/Install) · [Installed system](https://github.com/juniorterin/fliperOS/wiki/Installed-system) · [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) · [Emulators](https://github.com/juniorterin/fliperOS/wiki/Emulators) · [Fightcade 2](https://github.com/juniorterin/fliperOS/wiki/Fightcade-2) · [ROMs, BIOS and artwork](https://github.com/juniorterin/fliperOS/wiki/ROMs) · [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper) · [Adding games](https://github.com/juniorterin/fliperOS/wiki/Adding-games) · [Controls](https://github.com/juniorterin/fliperOS/wiki/Controls) · [Desktop and theme](https://github.com/juniorterin/fliperOS/wiki/Desktop) · [Latency](https://github.com/juniorterin/fliperOS/wiki/Latency)

**Para mexer nele:** [15 kHz kernel](https://github.com/juniorterin/fliperOS/wiki/Kernel-15-kHz) · [Build and tests](https://github.com/juniorterin/fliperOS/wiki/Build-and-tests) · [Architecture](https://github.com/juniorterin/fliperOS/wiki/Architecture) · [Sources](https://github.com/juniorterin/fliperOS/wiki/Sources)

As páginas ficam em [`docs/wiki`](docs/wiki) e vão para a wiki com `bash tools/wiki-publish.sh`. O [`fliperos-doc.html`](fliperos-doc.html) junta tudo num arquivo só (`tools/render-docs.py`).
