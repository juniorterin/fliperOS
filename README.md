# FliperOS 0.7 — instalador para gabinetes CRT, no estilo do GroovyArcade

Ubuntu 24.04 amd64 com o **kernel 15 kHz** (kernel.org 6.18 LTS + patches D0023R, os mesmos do `linux-15khz` do GroovyArcade). A mídia é **só de instalação** e segue o fluxo do GroovyArcade: menu de boot com a faixa de frequência, teste das saídas de vídeo com voz, *Testing Results*, menu **FliperOS Setup** e instalação no HD com barra de progresso. No sistema instalado, o mesmo programa vira o menu de configuração que aparece quando o frontend fecha.

As telas são do **`fliperos-setup`**, em Bash com [Gum](https://github.com/charmbracelet/gum) (Charmbracelet, feito sobre Bubble Tea), tema **Dracula** e textos em inglês, como no GroovyArcade. Pensadas para **640x480i**: 80x30 caracteres, nada animado nem piscando.

> 15 kHz foi validado no gabinete com a versão anterior (kernel padrão + EDID, 640x240). O kernel 15 kHz, o 640x480i, o teste de saídas e o instalador desta versão foram validados em VM (QEMU); o gabinete real ainda precisa confirmar.

## 1. Gravar a mídia

Grave a ISO **byte a byte** num pendrive e desative o Secure Boot (o kernel 15 kHz é próprio, não assinado).

A ISO usa o bootloader **Limine** e é **híbrida** (`xorriso` + `limine bios-install`): a mesma imagem boota como CD e como pendrive, em BIOS e em UEFI. Gravadores que reconstroem a estrutura de boot a quebram — **Rufus no modo padrão ("ISO image"), Ventoy e UNetbootin não servem**. Use o **balenaEtcher**, ou o Rufus em "DD Image mode", ou `dd`:

```bash
sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Confirme o `/dev/sdX` com `lsblk` antes: o dispositivo errado apaga o disco errado.

## 2. Menu de boot

As mesmas opções do GroovyArcade (`os/groovyarcade/syslinux/syslinux.cfg`). Aqui só se escolhe em que faixa o Linux sobe; a saída e o monitor são decididos depois, pelo teste de saídas.

| Entrada | Parâmetros | Para |
| --- | --- | --- |
| **15 kHz** (padrão) | `video=640x480iS` | Monitor arcade ou TV, 640x480 entrelaçado |
| 25 kHz | `video=512x384S` | Monitor de média resolução |
| 31 kHz | `video=640x480S` | Monitor de alta resolução |
| SVGA / LCD monitor | — | Monitor de PC ou LCD (vale o EDID dele) |
| Intel 15 kHz | `video=1280x480iS i915.no_ytiled_scanout=1` | Intel: super resolução; o parâmetro é do patch 09 e liga o entrelaçado na Gen9 |
| NVIDIA 15 kHz | `video=1280x480iS` | NVIDIA: super resolução |
| NTSC | `video=720x480iS` | TV NTSC |
| PAL | `video=768x576iS` | TV PAL |
| EDID progressive | `drm.edid_firmware=edid/generic_15_super_resp.bin video=e` | EDID do Switchres, todas as saídas forçadas |
| EDID interlaced | `drm.edid_firmware=edid/generic_15_super_resi.bin video=e` | Idem, entrelaçado |

O `S` no fim do modo é do patch 15 kHz: usa a tabela fixa de modos de baixo dotclock do kernel (`drm_modes_low_dotclock.c`), e o `i` é entrelaçado. Todas as entradas levam `quiet splash consoleblank=0` e o `radeon` nas placas SI/CIK.

**Timer de 30 segundos.** Sem tecla, sobe a entrada **15 kHz**, que é a segura para um gabinete: um LCD recebendo 15 kHz só mostra "fora de faixa", mas 31 kHz num tubo só de 15 kHz pode danificá-lo.

O menu em si **não aparece num CRT de 15 kHz** — ele sai no modo texto do firmware (~31 kHz), antes do kernel. É o mesmo no GroovyArcade. Para escolher outra entrada num gabinete só de 15 kHz, ligue um LCD temporariamente; com o CRT, espere os 30 s. A primeira coisa legível no tubo é o splash, já no modo de boot.

## 3. Teste de saídas e *Testing Results*

Portado do `gatools` (`video/video.sh`): assim que a mídia sobe, o `fliperos-setup`:

1. força ligadas as saídas analógicas ("Lights on") e explica o teste, falando pelo `espeak-ng`;
2. apaga todas as saídas e liga **uma de cada vez**, escrevendo `on`/`off`/`detect` em `/sys/class/drm/cardN-CONECTOR/status` (analógica sem monitor detectado é forçada; digital sem nada ligado é pulada);
3. em cada uma, diz em voz "Testing output V G A 1. If you can see this screen, press Enter." e mostra *"If you can see this screen clearly, press ENTER."* por 10 s;
4. **no primeiro ENTER para** e vai para a tela *Testing Results* (o gatools testa todas e escolhe a melhor; aqui quem está olhando para a tela já decidiu). Sem ENTER, repete a volta até três vezes.

Com duas placas, o console é levado para o framebuffer da placa testada (`con2fbmap`), como no gatools.

A tela **Testing Results** mostra GPU, driver, conector, modo atual e frequência horizontal (lidos do CRTC ativo pelo `fliperos-video-check`), se a placa gera dotclock baixo, se há modo entrelaçado, EDID, se o monitor foi identificado e se a saída será forçada no boot — com as mesmas frases do `inform_user` do gatools — e oferece **Validate settings** ou **Repeat test**.

Validado, vale o `configure_from_connector` do gatools:

- EDID do Switchres (dongle) → o monitor vem do próprio EDID;
- sem isso, o tipo de monitor é **obrigatório** (a lista abre na sugestão da entrada de boot);
- a linha do kernel sai do monitor: `video=VGA-1:640x480iSe` (o `e` quando foi preciso forçar a saída); placa sem dotclock baixo (Intel, NVIDIA) → super resolução `1280x480iS` e `dotclock_min 25.0` no Switchres; APU → `interlace_force_even 1`; boot por EDID → `drm.edid_firmware=CONECTOR:edid/<monitor>.bin`; LCD → nada (vale o EDID dele).

Tudo é gravado em **`/etc/fliperos/fliperos.conf`** (GPU, driver, conector, detecção, monitor, faixa, modo de boot, parâmetros do kernel, orientação, launcher), o equivalente do `ga.conf`, e no `switchres.ini`/`mame.ini`.

## 4. FliperOS Setup

Menu da mídia (o `isomainmenu` do gasetup): **Install to HD**, **Recovery Mode**, **Terminal** e **Shutdown**. O título mostra o host e o IP.

### Install to HD

1. **Do you want to configure video?** — *Yes* abre o **Video Setup**:
   - **Monitor Type**: os 29 presets do Switchres, na lista do gatools;
   - **Monitor Orientation**: horizontal, vertical horário, vertical anti-horário (console girado com `fbcon=rotate`, `panel_orientation` no `video=`, `ror`/`rol` do MAME e o desktop pelo `xrandr`);
   - **Resolution**: só os modos da tabela do kernel que a faixa do monitor e a placa aceitam (sem dotclock baixo, só as super resoluções), mais **resolução personalizada**: testa no `grid` do Switchres e gera um EDID (`switchres -e`), como o `worker_custom_video_mode`;
   - **Geometry**: o mesmo **`geometry`** do GroovyArcade — o `geometry.py` do Switchres, que desenha o grid e devolve o `crt_range`, gravado como `monitor custom` no `/etc/switchres.ini`.
2. **Automatically Partition** — lista os discos pelo **modelo, tamanho, caminho e barramento** (USB/NVMe/SATA). Não aparecem: a própria mídia de instalação, discos com menos de 16 GiB, montados ou em swap, com RAID/LVM/criptografia ou dependentes ativos — cada um com o motivo, acima da lista.
3. **WARNING** — modelo, caminho e tamanho do disco que será apagado; *No* volta para a escolha do disco. Se o disco já tem FliperOS, o aviso sugere o Recovery Mode.
4. **Installing FliperOS** — uma tela só, com o disco de destino, barra de progresso **real** (a cópia do sistema vem do percentual do `unsquashfs`, como o `dialog --gauge` do gasetup), a etapa e mensagens curtas. A saída dos comandos vai para `/var/log/fliperos-setup.log`. Em erro: etapa, erro, **View log / Retry / Return**.
5. **Installation completed successfully. Remove the installation CD/DVD/USB.** — e **Reboot now?**

Particionamento: GPT, BIOS boot de 1 MiB, ESP FAT32 de 1 GiB, o resto em ext4. O Limine é instalado para BIOS (estágio 2 na partição BIOS boot) e para UEFI (`EFI/BOOT/BOOTX64.EFI`, o caminho removível), sem mexer na NVRAM. O Limine só lê FAT, então kernel e initrd ficam **na ESP** (`/boot/efi/fliperos/`), mantidos pelo `fliperos-limine-update` — o equivalente do `update-grub`, chamado pelos hooks de kernel e de initramfs. Os parâmetros do kernel ficam em `/etc/default/fliperos-boot`.

O disco novo leva o que foi decidido na mídia: `fliperos.conf`, Switchres, MAME, Xorg, a linha do kernel, as redes Wi-Fi configuradas e a placa de som.

### Recovery Mode

Procura discos com FliperOS (partição `FliperOS` com o marcador `/etc/fliperos/installed`) e oferece: terminal dentro do sistema instalado (`chroot`, o `rescue_mode` do gasetup), **reinstalar o bootloader** (o "Fix UEFI boot", para BIOS e UEFI), **aplicar o vídeo desta sessão** (placa de vídeo trocada) e **restaurar os arquivos do sistema** a partir da mídia, preservando ROMs, saves, home, rede, áudio e vídeo.

## 5. Sistema instalado

O tty1 faz o login sozinho e segue o `.bash_profile` do GroovyArcade: abre o **launcher padrão** e, quando ele fecha, o **menu do FliperOS**.

**Primeiro boot:** *Choose default launcher*, com a lista gerada dos launchers instalados de fato (Attract-Mode Plus, RetroArch, EmulationStation..., LXDE) e o próprio *FliperOS Setup*. Muda depois em Setup > Frontend.

**Menu principal** (o `mainmenu` do gasetup; o título mostra `host (IP) - N% used on /`):

- **Start frontend**
- **Setup (video, audio, network...)**
  - **Video Setup** — o mesmo da instalação; grava a linha do kernel e oferece reiniciar;
  - **Audio Setup** — placa padrão (`/etc/asound.conf`), volume, AlsaMixer, teste de som;
  - **Network Setup** — Wi-Fi pela lista de redes (com sinal) ou **rede oculta digitando o SSID**; ao conectar, o IP aparece no título, ao lado do uso do disco;
  - **Frontend** — o launcher padrão; um que não está instalado pode ser instalado do repositório do FliperOS;
  - **Scraper** — capas, screenshots, logos, vídeos e informações de cada ROM encontrada em `/opt/fliperos/roms/<sistema>`, com o **Skyscraper** (o mesmo que o GroovyArcade empacota), de ScreenScraper, ArcadeDB ou TheGamesDB, no formato do launcher padrão;
  - **System Update** — `apt-get update` e `upgrade`, com o progresso real do apt;
- **Start desktop** — o LXDE;
- **Exit to shell** — `sudo fliperos-setup` volta ao menu;
- **Shutdown / Reboot**.

### Desktop LXDE

O LXDE do GroovyArcade: `lxde` completo com o openbox-lxde, painel embaixo (menu, gerenciador de arquivos, terminal, tarefas, CPU, volume, bandeja, rede, relógio), sem compositor, sem DPMS nem descanso de tela, fonte Sans 10 e a orientação do Video Setup. Vêm também as ferramentas do GroovyArcade: **AntiMicroX** e **QJoyPad** (controle como teclado/mouse), `xterm`, `htop`, `evtest`, `joy2key`, `hwinfo`, `lshw`, `read-edid`, `i2c-tools`. O **FliperOS Setup** fica em **System Tools** (e no painel), como o `gasetup.desktop`. O terminal usa as cores do Dracula. Sair do desktop volta ao menu.

## 6. Tema Dracula no console

No console do Linux só existem 16 cores, e o fundo só aceita as 8 primeiras. A paleta do VT é reprogramada com os tons do Dracula no boot (`/etc/vtrgb`, aplicada pelo `setvtrgb.service` do Ubuntu, com `config/vtrgb-dracula` como alternativa de maior prioridade) e de novo pelo `fliperos-setup`; os estilos do Gum usam os **índices** da paleta, não cores hexadecimais. Assim o tubo e um terminal gráfico mostram o mesmo. A fonte do console (Lat15/Uni2) tem as bordas arredondadas, os blocos da barra e as setas que as telas usam.

## 7. Arquitetura do `fliperos-setup`

```
fliperos-setup/
├── fliperos-setup        ponto de entrada (mídia ou sistema instalado)
├── lib/                  lógica — nenhum arquivo daqui chama o gum, exceto ui.sh
│   ├── common.sh config.sh progress.sh speech.sh
│   ├── drm.sh video.sh monitor.sh xorg.sh bootloader.sh
│   ├── disk.sh install.sh recovery.sh
│   ├── launcher.sh audio.sh network.sh status.sh scraper.sh update.sh
│   └── ui.sh             Gum, tema, quadro da tela
└── screens/              telas — só combinam ui.sh com a lógica
    ├── output-test.sh (teste + Testing Results)  main-menu.sh  setup-menu.sh
    ├── video-setup.sh  disk-selection.sh  install-progress.sh  progress.sh
    └── recovery.sh  first-boot.sh
```

As operações longas (instalar, reparar, atualizar, scraper) não conhecem a tela: escrevem eventos (`@step`, `@pct`, `@msg`, `@fail`) que `screens/progress.sh` desenha. Tudo vai para `/var/log/fliperos-setup.log`.

## 8. Kernel 15 kHz

`fliperos-kernel.sh` baixa o kernel.org **6.18.54**, aplica `patches/kernel-15khz/6.18/` (D0023R, 01 a 09) sobre o `.config` do kernel do próprio Ubuntu 24.04 e gera os `.deb`. Sem assinatura de módulo e sem informação de depuração. Compilar leva horas, então os `.deb` ficam num cache chaveado por versão e hash dos patches (`/output/kernel-cache/<chave>/`): o próximo build reaproveita.

O Switchres (`v2.2.1`, a mesma versão do pacote do GroovyArcade) é compilado com o `grid` e o `geometry`, e gera no build um EDID por preset de monitor mais os dois de super resolução das entradas EDID do boot (`fliperos-rebuild-edids`, o `rebuild_edids` do GroovyArcade). O hook do initramfs leva todos para o initramfs.

## 9. Build

Sempre em Docker (`CLAUDE.md` proíbe chroot com `/dev` do host no WSL).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso
```

| Opção | Efeito |
| --- | --- |
| `--skip-groovymame`, `--skip-retroarch`, `--skip-flycast`, `--skip-pcsx2`, `--skip-supermodel` | Não compila o emulador (cada um leva de minutos a horas) |
| `--skip-skyscraper` | Sem o Scraper do Setup |
| `--skip-switchres` | Sem Switchres: sem EDIDs por monitor, geometria e entradas EDID do boot |
| `--skip-input-drivers`, `--with-wheel-drivers` | GunCon 2 (padrão) e drivers de volante out-of-tree |
| `--kernel-cache DIR` | Onde guardar/reaproveitar os `.deb` do kernel (padrão `/output/kernel-cache`) |
| `--splash fliperos\|evangelion\|none` | Tema do Plymouth |
| `--wifi-ssid NOME --wifi-psk SENHA` | Grava uma rede Wi-Fi na imagem (**a senha fica em texto na ISO**; não a distribua) |

O que não existe no Ubuntu 24.04 é baixado com versão e hash fixados: Limine 11.4.1, Gum 2.0.2, AntiMicroX 3.6.1 (`.deb` oficial para 24.04), Skyscraper 3.21.0 (fork Gemba, compilado com Qt6).

Auditoria da ISO gerada (só leitura): confere menu de boot, kernel, arquivos do setup, bibliotecas dos programas compilados, EDIDs e boot BIOS/UEFI.

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-vmtest bash tools/verify-iso.sh /w/output/fliperos-0.7.iso
```

## 10. Testes

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

- `tests/test_setup.py` — a lógica do `fliperos-setup` com sysfs do DRM, EDIDs, `lsblk`, `nmcli` e `aplay` falsos, no mesmo Ubuntu (e mesmo `mawk`/`jq`) da ISO.
- `tests/test_build.py` — menu de boot, kernel e patches, pins, arquivos da imagem, Limine do disco instalado, `fliperos-video-check`.
- `tools/ui-snapshot.sh TELA [LARG ALT]` — fotografa uma tela em texto num tmux 80x30 (ou 64x24, o 512x384 de 25 kHz), com um sistema falso (`tools/ui-demo.sh`).
- `tools/vm-test.py install ISO` — em QEMU: instala pela lib do setup num disco descartável e boota o disco em BIOS e UEFI. `tools/vm-test.py screens ISO` e `tools/vm-monitor.py` fotografam o tty1 de verdade (Gum no console do Linux) tela a tela.

## 11. Outros componentes

**Repositório APT e frontends.** Os frontends (Attract-Mode Plus, EmulationStation, RetroFE, Pegasus) vêm de um repositório APT próprio de `.deb` pré-compilados, como o `groovy-ux-repo` do GroovyArcade (`packaging/build-deb.sh`, `packaging/make-repo.sh`, `Dockerfile.packages`, receitas em `packaging/packages/`). A tabela `config/fliperos-sessions.conf` diz, para cada launcher, se roda em KMS ou X (da tabela `videodata.conf` do galauncher) e de que pacote vem.

**Splash.** Plymouth com o tema próprio `fliperos` (texto, sem imagem), `evangelion` (202 quadros, com **risco de convulsão** declarado pelo autor e sem licença no pacote) ou nenhum.

**Rede.** Samba (`\\<ip>\FliperOS` → `/opt/fliperos`, escrita só com o usuário `fliperos`), SSH/SFTP e Avahi (`fliperos.local`). Login padrão `fliperos`/`fliperos`, como o `arcade`/`arcade` do GroovyArcade.

**Emuladores.** GroovyMAME, RetroArch (KMS, com cores libretro), Flycast (KMS), PCSX2 e Supermodel (X, via `fliperos-x11-run` e Switchres). O RetroArch usa `crt_switch_resolution 4` (o `/etc/switchres.ini` do Setup).

**Diagnóstico.** `sudo fliperos-video-check --json` lê o modo ativo de cada saída (CRTC atual via libdrm, só leitura): conector, resolução, kHz, Hz, entrelaçado.

## 12. Arquivos

| Arquivo | Função |
| --- | --- |
| `fliperos-setup/` | O setup (mídia e sistema instalado) |
| `fliperos-mkiso.sh` | Build da ISO |
| `fliperos-kernel.sh` | Kernel 15 kHz em `.deb`, com cache |
| `fliperos-rootfs.sh` | Instala na imagem o setup, a sessão, o LXDE, a paleta e a configuração de partida |
| `fliperos-limine.sh` | Limine fixado: baixa, instala no rootfs, gera a ISO híbrida |
| `fliperos-limine-update.py` | O `update-grub` do Limine no disco instalado |
| `fliperos-video-check.py` | Modo ativo das saídas (DRM, só leitura) |
| `fliperos-detect.sh` | Relatório de sistema e vídeo |
| `config/limine.conf` | Menu de boot da mídia |
| `config/fliperos-rebuild-edids`, `config/fliperos-edid-hook` | EDIDs do Switchres e o hook do initramfs |
| `config/fliperos-session`, `config/fliperos-sessions.conf` | Abre o launcher padrão; tabela de launchers |
| `config/fliperos-lxde`, `config/lxde/` | Sessão e configuração do LXDE |
| `config/vtrgb-dracula` | Paleta Dracula do console |
| `patches/kernel-15khz/6.18/` | Patches D0023R |
| `packaging/` | `.deb` dos frontends e o repositório APT |
| `tests/`, `tools/` | Testes e ferramentas de verificação |

## Fontes consultadas

Código atual do GroovyArcade, no GitLab do grupo `groovyarcade`:

- `gasetup` `2dbaa5297c716b4f32b0b55d5439c1f08f8cedda` — `core/procedures/interactive` (isomainmenu, mainmenu, setup), `core/libs/lib-video.sh`, `lib-install.sh`, `lib-network.sh`, `lib-troubleshoot.sh`
- `tools/gatools` `28cef9faeec9d85d001ea5259af2d7e2fa343430` — `video/video.sh` (teste de saídas, Testing results), `video/monitor.sh`, `video/inform.sh`
- `tools/galauncher` `7e4950e3a4b92faf5eeebcae7c3a29a9e73689be` — `startfe.sh`, `videodata.conf`
- `os` `59670f3d476331e7c18bc3a03fea6e7860fa1b7a` — menu de boot, `.bash_profile`, LXDE, AntiMicroX, QJoyPad
- `packages` `608bd30c3799c6a14c0b21823c53919c40ab8e9a` — kernel `linux-15khz`, `switchres` (`rebuild_edids`, `geometry`), `skyscraper`

E também: [Switchres](https://github.com/antonioginer/switchres) (`geometry.py`, `edid.cpp`, `switchres.ini`), [D0023R/linux_kernel_15khz](https://github.com/D0023R/linux_kernel_15khz) `ece6ef15eca9480eaf75870a44764f47118e9cfe`, [Gum](https://github.com/charmbracelet/gum) v2.0.2 e o [Dracula](https://draculatheme.com).
