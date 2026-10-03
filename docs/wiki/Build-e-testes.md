## Build

Sempre em Docker (`CLAUDE.md` proíbe chroot com `/dev` do host no WSL).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso
```

| Opção | Efeito |
| --- | --- |
| `--skip-groovymame`, `--skip-retroarch`, `--skip-flycast`, `--skip-pcsx2`, `--skip-supermodel` | Não põe o emulador na imagem (os compilados levam de minutos a horas; GroovyMAME e PCSX2 são os releases oficiais) |
| `--skip-skyscraper` | Sem o Scraper do Setup |
| `--skip-switchres` | Sem Switchres: sem EDIDs por monitor, geometria e entradas EDID do boot |
| `--skip-input-drivers`, `--skip-wheel-drivers` | Sem os drivers de entrada (GunCon 2 e volantes), ou só sem os de volante. Por padrão vêm o `guncon2`, o `hid-tmff2` (Thrustmaster T150/T300/TX/T248...) e o `new-lg4ff` (Logitech com force feedback completo, no lugar do `hid-logitech`), via DKMS — validados no 6.18 do gabinete |
| `--kernel-cache DIR` | Onde guardar/reaproveitar os `.deb` do kernel (padrão `/output/kernel-cache`) |
| `--splash fliperos\|evangelion\|none` | Tema do Plymouth |
| `--wifi-ssid NOME --wifi-psk SENHA` | Grava uma rede Wi-Fi na imagem (**a senha fica em texto na ISO**; não a distribua) |
| `--repo DIR` | Repositório APT dos frontends levado para a imagem (padrão `/output/repo`, se existir) |

O que não existe no Ubuntu 24.04 é baixado com versão e hash fixados: Limine 11.4.1, Gum 2.0.2 (o `.deb` fica pelas páginas de manual; o binário é o do código da mesma versão com `patches/gum`, compilado com o Go 1.26.7: setas ▲/▼ em vez dos pontos na paginação dos menus, os sons do menu e o Espaço marcando nas listas de marcar — o gum 2.0.2 só conhece a tecla como `" "`, e a biblioteca dele a chama de `space` —, posto no lugar do `/usr/bin/gum` com `dpkg-divert`), AntiMicroX 3.6.1 (`.deb` oficial para 24.04), Skyscraper 3.21.0 (fork Gemba, compilado com Qt6).

Auditoria da ISO gerada (só leitura): confere menu de boot, kernel, arquivos do setup, bibliotecas dos programas compilados, EDIDs e boot BIOS/UEFI.

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-vmtest bash tools/verify-iso.sh /w/output/fliperos-0.7.iso
```

## Testes

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

- `tests/test_setup.py` — a lógica do `fliperos-setup` com sysfs do DRM, EDIDs, `lsblk`, `nmcli` e `aplay` falsos, no mesmo Ubuntu (e mesmo `mawk`/`jq`) da ISO.
- `tests/test_build.py` — menu de boot, kernel e patches, pins, arquivos da imagem, Limine do disco instalado, `fliperos-video-check`.
- `tools/ui-snapshot.sh TELA [LARG ALT]` — fotografa uma tela em texto num tmux 80x30 (ou 64x24, o 512x384 de 25 kHz), com um sistema falso (`tools/ui-demo.sh`).
- `tools/vm-test.py install ISO` — em QEMU: instala pela lib do setup num disco descartável e boota o disco em BIOS e UEFI. `tools/vm-test.py screens ISO` e `tools/vm-monitor.py` fotografam o tty1 de verdade (Gum no console do Linux) tela a tela. `tools/vm-test.py desktop ISO` abre o LXDE no disco instalado (pelo boot e pelo menu, com o `xorg.conf` de 15 kHz). `tools/vm-test.py dev ISO` leva os arquivos do repositório de agora para o disco instalado, sem ISO nova, e usa o menu com um gamepad falso (`tools/vm-fakepad.py`, uinput) até o desktop, a troca de resolução e os quirks.
- **Atualizar o gabinete sem ISO nova** (pela rede, com o login padrão):

  ```powershell
  docker build -t fliperos-ssh -f tools/Dockerfile.ssh tools
  docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-ssh sh tools/cabinet-push.sh 192.168.1.111
  ```

  O `tools/cabinet-push.sh` envia o setup, o `config/`, o `fliperos-rootfs.sh` e o repositório de frontends; lá o `tools/cabinet-update.sh` guarda uma cópia do que muda em `/root/fliperos-backup-DATA.tgz`, roda o mesmo `fliperos-rootfs.sh` do build e aplica o que vem de fora dele: `fliperos-limine-update`, login automático, DNS, relógio, pacotes novos (pelo apt), linha do kernel e serviços. No fim reinicia o tty1.
