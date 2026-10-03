Da mídia gravada ao sistema no disco: gravar a ISO, o menu de boot, o teste das saídas de vídeo e a instalação pelo **FliperOS Setup**.

## Gravar a mídia

Grave a ISO **byte a byte** num pendrive e desative o Secure Boot (o kernel 15 kHz é próprio, não assinado).

A ISO usa o bootloader **Limine** e é **híbrida** (`xorriso` + `limine bios-install`): a mesma imagem boota como CD e como pendrive, em BIOS e em UEFI. Gravadores que reconstroem a estrutura de boot a quebram — **Rufus no modo padrão ("ISO image"), Ventoy e UNetbootin não servem**. Use o **balenaEtcher**, ou o Rufus em "DD Image mode", ou `dd`:

```bash
sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Confirme o `/dev/sdX` com `lsblk` antes: o dispositivo errado apaga o disco errado.

## Menu de boot

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

## Teste de saídas e *Testing Results*

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

## FliperOS Setup

Menu da mídia (o `isomainmenu` do gasetup): **Install to HD/SSD**, **Recovery Mode**, **Terminal** e **Shutdown**. O título mostra o host e o IP.

### Install to HD/SSD

1. **Do you want to configure video?** — *Yes* abre o **Video Setup**:
   - **Monitor Type**: os 29 presets do Switchres, na lista do gatools;
   - **Monitor Orientation**: horizontal, vertical horário, vertical anti-horário (console girado com `fbcon=rotate`, `panel_orientation` no `video=`, `ror`/`rol` do MAME e o desktop pelo `xrandr`);
   - **Resolution**: só os modos da tabela do kernel que a faixa do monitor e a placa aceitam (sem dotclock baixo, só as super resoluções), mais **resolução personalizada**: testa no `grid` do Switchres e gera um EDID (`switchres -e`), como o `worker_custom_video_mode`;
   - **Geometry**: o mesmo **`geometry`** do GroovyArcade — o `geometry.py` do Switchres, que desenha o grid e devolve o `crt_range`, gravado como `monitor custom` no `/etc/switchres.ini`. O grid sai na resolução escolhida acima, com o refresh dela (50 Hz nos modos PAL; sem escolha, 640x480). Para baixo a imagem só anda enquanto houver linhas em branco abaixo dela (o Switchres não passa do *front porch*); quando parar, o ajuste é o **V-POS** do monitor.
2. **Automatically Partition** — lista os discos pelo **modelo, tamanho, caminho e barramento** (USB/NVMe/SATA). Não aparecem: a própria mídia de instalação, discos com menos de 16 GiB, montados ou em swap, com RAID/LVM/criptografia ou dependentes ativos — cada um com o motivo, acima da lista. **My drive is not listed (details)** mostra tudo o que o Linux enxerga (o `lsblk`, as controladoras e as mensagens do kernel): um HD/SSD que nem ali aparece está escondido antes do Linux, quase sempre pelo modo SATA da BIOS em RAID/Intel RST (troque para AHCI) ou pelo Intel VMD.
3. **WARNING** — modelo, caminho e tamanho do disco que será apagado; *No* volta para a escolha do disco. Se o disco já tem FliperOS, o aviso sugere o Recovery Mode.
4. **Installing FliperOS** — uma tela só, com o disco de destino, barra de progresso **real** (a cópia do sistema vem do percentual do `unsquashfs`, como o `dialog --gauge` do gasetup), a etapa e mensagens curtas. A saída dos comandos vai para `/var/log/fliperos-setup.log`. Em erro: etapa, erro, **View log / Retry / Return**.
5. **Installation completed successfully. Remove the installation CD/DVD/USB.** — e **Reboot now?**

Particionamento: GPT, BIOS boot de 1 MiB, ESP FAT32 de 1 GiB, o resto em ext4. As partições novas têm as assinaturas antigas apagadas e a de BIOS boot é zerada (um resto de sistema de arquivos do disco anterior ali fazia o `limine bios-install` recusar; ele também roda com `--force`). O Limine é instalado para BIOS (estágio 2 na partição BIOS boot) e para UEFI (`EFI/BOOT/BOOTX64.EFI`, o caminho removível), sem mexer na NVRAM. O Limine só lê FAT, então kernel e initrd ficam **na ESP** (`/boot/efi/fliperos/`), mantidos pelo `fliperos-limine-update` — o equivalente do `update-grub`, chamado pelos hooks de kernel e de initramfs. Os parâmetros do kernel ficam em `/etc/default/fliperos-boot`.

O disco novo leva o que foi decidido na mídia: `fliperos.conf`, Switchres, MAME, Xorg, a linha do kernel, as redes Wi-Fi configuradas e a placa de som.

### Recovery Mode

Procura discos com FliperOS (partição `FliperOS` com o marcador `/etc/fliperos/installed`) e oferece: terminal dentro do sistema instalado (`chroot`, o `rescue_mode` do gasetup), **reinstalar o bootloader** (o "Fix UEFI boot", para BIOS e UEFI), **aplicar o vídeo desta sessão** (placa de vídeo trocada) e **restaurar os arquivos do sistema** a partir da mídia, preservando ROMs, saves, home, rede, áudio e vídeo.
