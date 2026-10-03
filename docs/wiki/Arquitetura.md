## O `fliperos-setup`

```
fliperos-setup/
├── fliperos-setup        ponto de entrada (mídia ou sistema instalado)
├── lib/                  lógica — nenhum arquivo daqui chama o gum, exceto ui.sh
│   ├── common.sh config.sh progress.sh speech.sh
│   ├── drm.sh video.sh monitor.sh xorg.sh bootloader.sh
│   ├── disk.sh install.sh recovery.sh
│   ├── launcher.sh audio.sh network.sh status.sh scraper.sh update.sh
│   ├── romclean.sh netshare.sh  MAME ROM Cleaner; pasta compartilhada da rede (SMB)
│   ├── hardware.sh latency.sh   CPU/memória/GPU e os modos de latência
│   ├── quirks.sh padkeys.sh     quirks do usbhid; controle nos menus
│   ├── lpt.sh            joysticks na porta paralela (db9, gamecon, turbografx)
│   └── ui.sh             Gum, tema, quadro da tela
└── screens/              telas — só combinam ui.sh com a lógica
    ├── output-test.sh (teste + Testing Results)  main-menu.sh  setup-menu.sh
    ├── video-setup.sh  disk-selection.sh  install-progress.sh  progress.sh
    └── recovery.sh  first-boot.sh  latency.sh  lpt.sh  rom-cleaner.sh
```

As operações longas (instalar, reparar, atualizar, scraper) não conhecem a tela: escrevem eventos (`@step`, `@pct`, `@msg`, `@fail`) que `screens/progress.sh` desenha. Tudo vai para `/var/log/fliperos-setup.log`.

## Outros componentes

**Splash.** Plymouth com o tema próprio `fliperos` (texto, sem imagem), `evangelion` (202 quadros, com **risco de convulsão** declarado pelo autor e sem licença no pacote) ou nenhum.

**Rede.** Samba (`\\<ip>\FliperOS` → `/opt/fliperos`, e `\\<ip>\roms`, `bios`, `media` e `config` → as pastas de mesmo nome em `~`, escrita só com o usuário `fliperos`; `config/smb.conf`), SSH/SFTP e Avahi (`fliperos.local`). Login padrão `fliperos`/`fliperos`, como o `arcade`/`arcade` do GroovyArcade. O NetworkManager cuida do Wi-Fi **e do cabo** (o `10-globally-managed-devices.conf` vazio anula o do Ubuntu, que só gerenciava Wi-Fi) e escreve ele mesmo o `/etc/resolv.conf` com o DNS do DHCP (`90-fliperos-dns.conf`: o Ubuntu entregaria o DNS ao `systemd-resolved`, que não está na imagem). O relógio vem da rede (`systemd-timesyncd`). No primeiro teste no gabinete faltavam os três: o `resolv.conf` era o do container do build, o relógio da BIOS estava dois meses atrasado, e o apt não funcionava (nem System Update, nem frontends).

**Diagnóstico.** `sudo fliperos-video-check --json` lê o modo ativo de cada saída (CRTC atual via libdrm, só leitura): conector, resolução, kHz, Hz, entrelaçado.

## Arquivos

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
| `config/fliperos-latency.service` | Aplica o modo de latência no boot |
| `config/fliperos-volume.triggers` | Teclas de volume (triggerhappy) |
| `fliperos-dracula.sh`, `config/openbox-3/themerc` | Tema Dracula do LXDE (GTK fixado por commit + Openbox) e do terminal (Oh My Zsh + dracula/zsh) |
| `config/zshrc`, `config/fliperos-tty1`, `config/fliperos-menu` | zsh do usuário; fluxo do tty1 (primeiro boot, launcher, o laço do menu); do shell de volta ao menu |
| `config/fliperos-padkeys`, `config/fliperos-padkeys.service` | Controle como teclado nos menus do setup |
| `config/fliperos-calibrate` | Calibração do GunCon 2 e de volante/pedais/analógico (Setup > Joysticks) e a reaplicação pelo udev |
| `config/fliperos-roms`, `config/smb.conf`, `config/flycast-emu.cfg` | Pastas em `~` (`roms`, `bios`, `media`, `config`); Samba (FliperOS, roms, bios, media, config); Flycast de partida |
| `config/fliperos-controllers`, `config/fliperos-controllers.service` | Completa o mapeamento automático do SDL2 (e o do Flycast) dos controles ligados |
| `config/lxde/alacritty/alacritty.toml`, `config/fliperos-software.gschema.override`, `config/applications/org.gnome.Software.desktop` | Terminal (Alacritty) e App Store do desktop |
| `fliperos-setup/lib/debug.sh` | Debug mode: boot e programas com ou sem texto |
| `config/fliperos-resolution`, `config/applications/fliperos-resolution.desktop` | Screen Resolution: a resolução do desktop na hora |
| `config/mame-ui.ini` | Cores Dracula da interface do GroovyMAME |
| `config/applications/`, `config/icons/`, `config/fliperos-launch` | Emuladores no menu do LXDE e a saída do desktop para abri-los |
| `config/fliperos-x11-run`, `config/fliperos-emulator-modes.conf` | Abre um programa num Xorg próprio no modo pedido (`--mode 640x240@60`) ou no da tabela por emulador |
| `config/fliperos-model2`, `config/fliperos-ini-set` | Model 2 Emulator no Wine; ajuste de ini por seção (PCSX2) |
| `config/fliperos-fightcade`, `config/openbox-fightcade.xml` | Fightcade 2: baixa do site dele (`fetch`) e abre num Xorg próprio; os atalhos de janela dele |
| `config/fliperos-groovymame` | O comando `groovymame`: o release em `/usr/local/libexec` com o `mame.ini` do sistema |
| `config/retroarch.cfg`, `config/mame.ini` | Configuração de sistema do RetroArch e do GroovyMAME (valores do modo Standard) |
| `patches/kernel-15khz/6.18/` | Patches D0023R |
| `packaging/` | `.deb` dos frontends e o repositório APT |
| `tests/`, `tools/` | Testes e ferramentas de verificação |
| `README.md`, `docs/wiki/` | O resumo e a documentação completa: as páginas desta wiki, mantidas junto do código |
| `tools/wiki-publish.sh`, `tools/render-docs.py` | Publica `docs/wiki` na wiki do GitHub; gera o `fliperos-doc.html` (tudo num arquivo só, para ler sem rede) |
