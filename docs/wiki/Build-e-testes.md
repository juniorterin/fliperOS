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

## Release

Toda ISO nova vai para os [Releases](https://github.com/juniorterin/fliperOS/releases) do GitHub, com o changelog da versão, como os releases do GroovyArcade ([substring/os](https://github.com/substring/os/releases)): o texto por área (sistema, pacotes, `fliperos-setup`, ferramentas) e, junto da ISO, a lista de pacotes.

1. Escreva em `CHANGELOG.md` a seção `## VERSÃO` com o que mudou desde o release anterior (`git log VERSÃO_ANTERIOR..HEAD` lista os commits). Uma ISO nova depois de um release pede versão nova (`FLIPEROS_VERSION` no `fliperos-mkiso.sh`).
2. Faça o commit e o push.
3. Marque a versão e envie a tag (o nome é a versão, sem "v"):

   ```powershell
   git tag 0.7
   git push origin 0.7
   ```

O push da tag dispara o workflow **Release** do GitHub Actions (`.github/workflows/release.yml`). Ele confere se a tag é o `FLIPEROS_VERSION` e se o `CHANGELOG.md` tem a seção dela, monta o repositório dos frontends (`Dockerfile.packages`) e gera a ISO no mesmo `Dockerfile.fliperos` do build local. Depois publica pelo `tools/release-publish.sh`, com o token do próprio workflow. Os `.deb` do kernel e dos frontends ficam no cache do Actions, então só recompilam quando muda a versão, um patch ou uma receita. Sem cache, o build leva umas 3 horas num runner de 4 núcleos (o limite é 6 h). Se ele falhar, o `fliperos-mkiso.log` fica como artifact do workflow. Rodado à mão (*Actions > Release > Run workflow*), ele gera a ISO da versão atual e a deixa como artifact por 3 dias, sem publicar.

Para publicar uma ISO gerada aqui, no container da auditoria:

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run -it --rm -v fliperos-gh:/root/.config/gh fliperos-vmtest gh auth login
docker run --rm -v "${PWD}:/w:ro" -v fliperos-gh:/root/.config/gh -w /w fliperos-vmtest bash tools/release-publish.sh /w/output/fliperos-0.7.iso
```

O `gh auth login` é uma vez só: o login fica no volume `fliperos-gh`.

O `tools/release-publish.sh` só publica o que pode ir a público:

- a ISO passa pela auditoria (`tools/verify-iso.sh`), então é a do repositorio de agora — uma ISO antiga, gerada antes dos últimos commits, é recusada;
- uma ISO com rede gravada (`--wifi-ssid`, `--wifi-psk`) é recusada: a senha iria junto;
- sem a seção da versão no `CHANGELOG.md`, nada é publicado;
- um release que já existe não é trocado sem `--replace` (apaga e publica de novo).

O GitHub aceita até 2 GiB por arquivo, e a ISO fica abaixo disso. O `slim_rootfs_chroot` do build tira os pacotes `-dev` e as ferramentas de compilação, mas ficam o `build-essential`, o `dkms` e os headers do kernel, que os drivers DKMS usam. Sem `autoremove`, porque os plugins do Qt e o Vulkan entram por `dlopen` e não aparecem no `ldd`; as bibliotecas que o `ldd` mostra são marcadas como instaladas à mão, e um `ldd` antes e depois derruba o build se faltar alguma. Também saem o cache e as listas do apt, e o firmware fora do escopo (NVIDIA, Mellanox, Marvell Prestera, Qualcomm, QLogic), por `path-exclude` do dpkg para uma atualização não o trazer de volta. O squashfs é em xz. Wine, Steam e Heroic não vêm na imagem: o Setup > Extras os instala (`config/fliperos-extras`). Se a ISO passar de 2 GiB, ela vai em partes de 1900 MiB (`fliperos-0.7.iso.001`, `.002`...), e o texto do release ganha a instrução de juntar (`copy /b` no Windows, `cat` no Linux). Vão também o `fliperos-0.7.sha256` (a ISO inteira e cada parte) e o `fliperos-0.7-pkglist.txt` (pacote, versão e arquitetura do que está na imagem). `--prerelease` marca como pré-release; `--to PASTA` só prepara os arquivos e o texto (`notes.md`), sem tocar no GitHub; `--notes VERSÃO` mostra o texto da versão.

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
