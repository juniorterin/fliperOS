# FliperOS 0.6 — Ubuntu para CRT 15 kHz

Base Ubuntu 22.04 amd64. Configuração de vídeo e instalador revisados usando as fontes oficiais do Switchres, kernel DRM e GroovyArcade/gasetup. A ISO é live e oferece instalação em disco. A saída física ainda precisa ser validada na GPU e no CRT reais.

## Instalação no estilo GroovyArcade

O fluxo segue a instalação pela ISO do gasetup: iniciar live, identificar a saída do CRT, confirmar a imagem, escolher live ou disco, revisar o destino, extrair o sistema e configurar o boot.

1. Grave `output/fliperos-0.6.iso` em um pendrive e inicie o computador por ele. Desative Secure Boot; esta ISO não oferece uma cadeia de boot assinada validada.
2. A entrada CRT usa **VGA-1**. Se o conector for outro, edite os nomes em `video=` e `drm.edid_firmware=` no GRUB. Nomes repetidos em múltiplas GPUs exigem configuração manual.
3. Login live: `fliperos`, senha `fliperos`. O assistente abre no TTY1. Para reabrir: `sudo fliperos-install`.
4. Escolha live ou instalação. Selecione a saída ativa do CRT e confirme que a imagem está visível e estável. O assistente não testa novos modos automaticamente.
5. Na instalação, selecione o disco por caminho, modelo, capacidade e serial. Discos montados, mídia live, swap ativa e dispositivos com dependentes ativos são recusados.
6. Revise o plano e digite `APAGAR /dev/…` com o dispositivo exato. **O disco inteiro será apagado; não há dual boot.**
7. O instalador extrai o squashfs, grava fstab com UUIDs, reconstrói o initramfs e instala GRUB. Defina uma senha nova e reinicie sem o pendrive.

Particionamento: GPT, BIOS boot de 1 MiB, ESP FAT32 de 512 MiB, restante ext4. Instala GRUB BIOS e UEFI pelo caminho removível, sem alterar NVRAM. Mínimo: 16 GiB.

É uma implementação própria do fluxo, adaptada ao Ubuntu. Não copia `pacstrap`, `pacman`, `mkinitcpio`, o kernel Arch ou todos os menus do gasetup. Não inclui net-install nem perfis de 25/31 kHz. O gasetup oferece outros bootloaders; aqui é usado GRUB.

Plano sem nenhuma escrita:

```bash
sudo fliperos-install --plan /dev/sdX --connector VGA-1
```

A instalação real é bloqueada em Docker/WSL. Não execute instalação contra discos de trabalho durante testes.

## Timing de vídeo

15 kHz é a frequência horizontal. Resolução e refresh vertical isoladamente não a determinam. No modo DRM comum, **HSync em kHz = clock em kHz / total horizontal**, incluindo apagamento.

O `crt15-edid.bin` anuncia somente um timing detalhado:

```text
640x240 progressivo, 13,020 MHz
Horizontal: 640 666 728 832
Vertical:   240 242 245 261
Polaridade: -HSync -VSync
HSync: 15,649038 kHz; refresh: 59,958 Hz
```

640 pixels de largura não transformam esse modo em 480p. São 240 linhas progressivas. O timing é genérico, não uma calibração específica do monitor. O antigo `320x240-edid.bin` foi preservado apenas como referência e não é usado: também anunciava um modo GTF de 14,940 kHz e seu clock baixo falhava na validação EDID utilizada.

O boot usa `video=VGA-1:e drm.edid_firmware=VGA-1:edid/crt15.bin`. O EDID está no initramfs para o driver encontrá-lo no início do KMS.

**BIOS/UEFI e GRUB vêm antes desse mecanismo e podem emitir frequências acima de 15 kHz.** O override não garante toda a sequência desde ligar o computador. GPU, adaptadores e circuito RGBHV/RGBS precisam de teste. Não conecte um CRT de frequência fixa a sinal desconhecido para testar por tentativa.

Os parâmetros SI/CIK selecionam `radeon` apenas nas famílias compartilhadas com `amdgpu`, sem blacklist geral. Identifique o chip por PCI ID e driver real. A R7 240 normalmente é Oland, não Cape Verde.

## Diagnóstico do modo ativo

```bash
sudo fliperos-video-check --connector VGA-1
sudo fliperos-video-check --json
sudo bash /opt/fliperos/fliperos-detect.sh
journalctl -b -u fliperos-video-check.service --no-pager
```

O verificador abre DRM somente para leitura e consulta conector, encoder e CRTC atual via libdrm. Não toma DRM master, não troca modos e não usa a lista de modos anunciados como comprovação de atividade. DPMS desligado é tratado como inativo quando esse estado está disponível.

| Resultado | Código | Significado |
| --- | --- | --- |
| `MODO_ATIVO_15KHZ` | 0 | Saídas selecionadas ativas dentro de 15–16 kHz |
| `FORA_DA_FAIXA` | 1 | Existe saída ativa fora da faixa |
| `INCONCLUSIVO` | 2 | Sem saída ativa, acesso, GPU ou dados completos |

Sem filtro, considera todas as saídas ativas. Um LCD a 31 kHz junto do CRT faz o resultado global indicar fora da faixa. Use `--connector` para examinar só o CRT e `--min-khz`/`--max-khz` para os limites específicos do monitor.

Essa leitura é o estado informado pelo kernel naquele momento. Não mede eletricamente HSync, não confirma a saída após um conversor e não garante modos escolhidos posteriormente pelos jogos. A medição física exige instrumento ou indicação confiável do monitor/analisador.

## Switchres e emuladores

O console inicia pelo EDID. O serviço de boot apenas verifica. Os emuladores abrem Xorg inicialmente em 640x240 e usam Switchres/XRandR durante a execução.

O backend KMS do Switchres chama-se `drmkms`, não `kms`, e upstream o identifica como trabalho em andamento. Troca dinâmica sem X pode exigir patches adicionais; não é prometida nesse kernel Ubuntu padrão.

O INI usa `chave valor`, sem seções nem `=`. O caminho é passado com `--ini`. O cálculo usa `--calc`, não `--dryrun`. Gerar uma modeline não comprova saída física.

```bash
switchres 640 240 60 --calc --ini /etc/fliperos/switchres.ini
fliperos-launcher
```

O wrapper usa `--launch` para manter Switchres acompanhando o emulador e restaurar o modo ao sair. Recusa perfis acima de 15 kHz. A solicitação 640x480 dos emuladores 3D usa arcade_15 com interlace habilitado; ainda exige teste da GPU e do emulador. Jogos que trocam o modo por conta própria também precisam de validação.

A ISO de diagnóstico reaproveita o Switchres compilado da imagem anterior. GroovyMAME e demais emuladores só estão disponíveis se seus binários tiverem sido instalados. O launcher informa componentes ausentes. Não certificamos desempenho ou troca dinâmica sem testes no hardware.

## Build

Use Docker para isolar o build. `CLAUDE.md` proíbe bind de `/dev` do host em chroots de build no WSL. O gerador recusa execução direta em WSL e não remove recursivamente um workspace com mounts restantes.

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-novo.iso --skip-groovymame
```

O privilégio acima pertence ao container de build; não monte `/dev` do host nele. Build não testa sinal de vídeo. Compilações solicitadas devem falhar explicitamente se não concluírem; omissões usam `--skip-*`.

| Arquivo | Função |
| --- | --- |
| `fliperos-mkiso.sh` | Build de uma ISO Ubuntu nova |
| `fliperos-setup.sh` | Setup em Ubuntu existente; `--dry-run` não escreve |
| `fliperos-install.py` | Assistente live/instalação em disco |
| `fliperos-install-video.sh` | Assets compartilhados entre setup e ISO |
| `fliperos-video-check.py` | Consulta de modo ativo DRM |
| `fliperos-detect.sh` | Relatório de sistema e vídeo |
| `config/` | Xorg, Switchres, GRUB, serviço, hook EDID e launchers |
| `tools/repack-iso.sh` | Revisão da ISO 0.5 em container de auditoria |
| `tests/test_video.py` | Testes de frequência, EDID e discos |

## Fontes consultadas

- [GroovyArcade e fluxo de instalação](https://github.com/substring/os)
- [gasetup: instalação](https://gitlab.com/groovyarcade/gasetup/-/blob/master/core/libs/lib-install.sh)
- [gasetup: fluxo interativo](https://gitlab.com/groovyarcade/gasetup/-/blob/master/core/procedures/interactive)
- [gasetup: bootloaders](https://gitlab.com/groovyarcade/gasetup/-/blob/master/core/libs/lib-bootloaders.sh)
- [Switchres: CLI e uso](https://github.com/antonioginer/switchres)
- [Switchres: opções e sintaxe](https://github.com/antonioginer/switchres/blob/master/switchres.ini)
- [Kernel 15 kHz: EDID e patches KMS](https://github.com/D0023R/linux_kernel_15khz)
- [DRM: estruturas e unidades dos modos](https://kernel.org/doc/html/v6.16/gpu/drm-uapi.html)

Revisões consultadas: gasetup `f190da5f7b5157f1122e37c49a6b73dc62970269`; Switchres `da27cc69b59c9c274bffae51ab148dedcf2b0a75`. O antigo link para `switchres/doc/switchres_kms.md` não existe nessa revisão. `get-docker.sh` é um instalador externo de Docker preservado no repositório; não integra o instalador FliperOS.
