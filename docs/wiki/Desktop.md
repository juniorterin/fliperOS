## Desktop LXDE

O LXDE do GroovyArcade: `lxde` completo com o openbox-lxde, painel embaixo (menu, gerenciador de arquivos, terminal, tarefas, CPU, volume, bandeja, rede, relógio), sem compositor, sem DPMS nem descanso de tela, fonte Sans 10 e a orientação do Video Setup. Tudo no tema Dracula (Desktop e tema).

**Terminal: Alacritty.** O `lxterminal` e o `xterm` (o terminal padrão do sistema, com fontes bitmap que a imagem nem tem) não desenhavam as bordas do Gum; saíram, e o terminal do painel, do menu e do *FliperOS Setup* é o **Alacritty**, que sempre trabalha em UTF-8 e desenha bordas e blocos sozinho, sem depender da fonte. Tema Dracula com a paleta do console (`config/lxde/alacritty/alacritty.toml`), DejaVu Sans Mono, cursor sem piscar (piscar redesenha a tela, o que tremula no entrelaçado). O tamanho da letra não segue o DPI do EDID do CRT (daria 50 DPI ou menos): o `fliperos-lxde` exporta `WINIT_X11_SCALE_FACTOR=1`. Como o metapacote `lxde` depende do `lxterminal`, a imagem instala os componentes dele um a um.

**App Store:** o **GNOME Software** com o plugin de **Flatpak** e o **Flathub** como fonte, no menu (Ferramentas do sistema) e no painel como *App Store*: pacotes do Ubuntu e apps Flatpak (emuladores, jogos, programas). O App Center do Ubuntu 24.04 depende do snap, que não vai na imagem. Sem baixar atualizações sozinha nem tela de boas-vindas (`config/fliperos-software.gschema.override`): disco e rede no meio de uma partida pesam na latência, pelo mesmo motivo dos timers do apt mascarados. Instalar pede a senha do usuário (`fliperos`), pelo lxpolkit.

**Navegador e torrents:** o **Falkon** e o **Transmission** vêm na imagem e aparecem no menu (Internet) como *Falkon (browser)* e *Transmission (torrent)*: o `fliperos-rootfs.sh` copia a entrada de cada pacote para `/usr/local/share/applications`, que vem antes, com o nome trocado em todos os idiomas.

**Emuladores no menu (Jogos):** RetroArch, GroovyMAME, Flycast, PCSX2, Supermodel, Dolphin, OpenBOR, Model 2 e, depois de baixado pelo Setup, o Fightcade 2, com os ícones dos próprios projetos (GroovyMAME, Supermodel, Model 2 e Fightcade não têm ícone para Linux na imagem; os deles são do FliperOS, em `config/icons`). Nenhum deles roda dentro do X do desktop — RetroArch e GroovyMAME usam o KMS, os outros sobem um Xorg próprio no modo da tabela de modos ([Emuladores](Emuladores.md)) —, então o atalho (`fliperos-launch`) grava o pedido e fecha o desktop (com uma confirmação se houver janelas abertas), o `fliperos-session` abre o emulador no CRT e, quando ele fecha, **o desktop volta**. Emulador que não foi compilado (`--skip-*`) não aparece no menu. Steam e Heroic (GOG) também estão em Jogos, mas abrem dentro do próprio desktop. Vêm também as ferramentas do GroovyArcade: **AntiMicroX** e **QJoyPad** (controle como teclado/mouse), `xterm`, `htop`, `evtest`, `joy2key`, `hwinfo`, `lshw`, `read-edid`, `i2c-tools`. O **FliperOS Setup** fica em **System Tools** (e no painel), como o `gasetup.desktop`. O terminal usa as cores do Dracula. Sair do desktop volta ao menu.

**Screen Resolution (Preferências):** troca a resolução do desktop **na hora**. A lista é a das resoluções do monitor escolhido no Video Setup, mais *Other resolution...* (qualquer `LARGURAxALTURA@HZ`). O Switchres calcula o modo nas faixas do `/etc/switchres.ini` (`switchres --calc`, o mesmo cálculo dos emuladores) e o `xrandr` o aplica, ajustando o tamanho da tela; a janela abre maximizada e acompanha a troca. Sem confirmar em 15 segundos, volta a resolução anterior. *Use every time the desktop starts* guarda o modo em `~/.config/fliperos/desktop-mode`, que o `fliperos-lxde` aplica ao abrir o desktop; escolher a resolução do boot esquece o guardado. Só o desktop muda: o console, o setup e os frontends seguem a resolução do Video Setup. Com monitor LCD, a lista é a dos modos do EDID dele.

## Tema Dracula

O [Dracula](https://draculatheme.com) é o tema de tudo o que o FliperOS desenha:

| Onde | Como |
| --- | --- |
| Console e `fliperos-setup` | paleta do VT (abaixo) e o Gum com os índices dela |
| LXDE — janelas e programas GTK 2/3 | tema oficial `dracula/gtk`, fixado por commit (`fliperos-dracula.sh`), com as engines `murrine`/`pixbuf` do GTK 2 |
| LXDE — bordas e menus do Openbox | `config/openbox-3/themerc` (o `dracula/gtk` não tem Openbox), escolhido no `lxde-rc.xml` |
| LXDE — painel, fundo, terminal | cores em `config/lxde` (lxpanel, pcmanfm, lxterminal) |
| Terminal (zsh) | **Oh My Zsh** com o tema oficial `dracula/zsh`, os dois fixados por commit em `/usr/local/share/oh-my-zsh` (`fliperos-dracula.sh`), sem atualização automática; `~/.zshrc` é o `config/zshrc`. No console do Linux a seta e o ✓/✗ do git viram `>`, `ok` e `*` (a fonte do console não tem esses símbolos) |
| RetroArch | o tema **Dracula embutido no RGUI** (`rgui_menu_color_theme = 17`) |
| GroovyMAME | cores da interface (menus, lista de jogos, sliders) em `/etc/fliperos/mame/ui.ini` (`config/mame-ui.ini`, ARGB) |

### No console

No console do Linux só existem 16 cores, e o fundo só aceita as 8 primeiras. A paleta do VT é reprogramada com os tons do Dracula no boot (`/etc/vtrgb`, aplicada pelo `setvtrgb.service` do Ubuntu, com `config/vtrgb-dracula` como alternativa de maior prioridade) e de novo pelo `fliperos-setup`; os estilos do Gum usam os **índices** da paleta, não cores hexadecimais. Assim o tubo e um terminal gráfico mostram o mesmo. A fonte do console (Lat15/Uni2) tem as bordas arredondadas, os blocos da barra e as setas que as telas usam.
