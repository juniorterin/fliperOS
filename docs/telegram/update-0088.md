🇧🇷 **Atualização 88 do FliperOS: Wi-Fi USB que começa como CD-ROM, FliperOS escrito certo e um aro de carregamento no menu na tela** 📶

- Adaptadores Wi-Fi USB que começam como um CD-ROM com os próprios drivers (o Realtek RTL8188GU, `0bda:1a2b`, e parecidos) agora viram Wi-Fi sozinhos ao serem ligados: o sistema ganha o `usb-modeswitch` e as regras dele, e o update os instala. O adaptador que já está ligado precisa ser tirado e posto de novo uma vez. No Setup > Wi-Fi, quando nenhum adaptador é encontrado, a lista do hardware de rede avisa se algum ainda aparece como CD-ROM de drivers. Ainda não foi testado com um adaptador de verdade.
- FliperOS se escreve FliperOS em todo lugar, nunca em caixa alta, e o "OS" tem outra cor onde o nome é desenhado: o Setup, o frontend, o painel web, o menu na tela e as animações do ZeDMD e do letreiro. Os nomes da máquina, das pastas e do usuário (`fliperos.local`) continuam iguais.
- Menu na tela: abrir uma página que demora um pouco (Colour, Scanlines, Geometry e GunCon 2) não deixa mais o menu parado sem desenhar nada. As teclas esperam a página abrir e, passado um quarto de segundo, um aro pequeno com um cometa girando aparece no canto do título.

🇺🇸 **FliperOS update 88: USB Wi-Fi adapters that start as a CD-ROM, FliperOS spelled right and a loading ring in the on-screen menu** 📶

- USB Wi-Fi adapters that start as a CD-ROM with their own drivers (the Realtek RTL8188GU, `0bda:1a2b`, and similar ones) now switch to Wi-Fi by themselves when plugged in: the system gets `usb-modeswitch` and its rules, and the update installs them. An adapter that is already plugged in has to be unplugged and plugged in again once. In Setup > Wi-Fi, when no adapter is found, the list of network hardware now says so if one is still showing as a driver CD-ROM. Not tried yet with a real adapter.
- FliperOS is written FliperOS everywhere, never in capital letters, and the "OS" has another colour where the name is drawn: the Setup, the frontend, the web panel, the on-screen menu and the ZeDMD and marquee animations. The machine, folder and user names (`fliperos.local`) stay the same.
- On-screen menu: opening a page that takes a moment (Colour, Scanlines, Geometry and GunCon 2) no longer leaves the menu still with nothing drawn. The keys wait for the page to open and, after a quarter of a second, a small ring with a spinning comet shows in the title corner.

---

🇧🇷 **Painel web, jogos custom: uma página de Jogos, edição e pacotes**

- Uma página só de Jogos: enviar um zip o instala no grupo escolhido, há um filtro no alto, os pacotes por instalar ficam acima dos grupos e cada jogo é um cartão completo (Abrir, editar, baixar, menu).
- Um jogo instalado se edita numa ficha só: modo, informações, executável e runner (Windows), comando (Linux), mapa do controle e arte. A arte tem a bandeja de captura (uma foto e 30 segundos de vídeo da tela do gabinete), a prévia e o Testar no gabinete. O seletor de controle mostra um ícone por tipo.
- Baixar um jogo instalado refaz o pacote com as configurações e o `.key` que mudaram depois da instalação; se o zip já leva o mesmo, nada é refeito.
- O Criar pacote faz um pacote, ou vários de uma vez numa tabela, e no fim pergunta se instala e em que grupo.
- O nome e o logotipo de um grupo se editam numa ficha só, e o grupo novo já deixa escolher o logotipo ao dar o nome: enviar uma imagem ou escolher um dos logotipos que o FliperOS já tem.

🇺🇸 **Web panel, custom games: a Games page, editing and packages**

- One Games page: sending a zip installs it into the group you choose, there is a filter at the top, the packages waiting to be installed sit above the groups and every game is a full card (Open, edit, download, menu).
- An installed game is edited in one form: mode, information, executable and runner (Windows), command (Linux), controller map and art. The art has the capture tray (a photo and 30 seconds of video of the cabinet's screen), the preview and Test on the cabinet. The controller picker shows an icon per type.
- Download on an installed game rebuilds the package with the settings and the `.key` file that changed after the install; if the zip already carries the same, nothing is redone.
- Create package makes one package, or many at once in a table, and when it is done it asks whether to install it and in which group.
- A group's name and logo are edited in one form, and a new group already lets you choose the logo while you name it: upload an image or pick one of the logos FliperOS already has.

---

🇧🇷 **Painel web: o Jogar abre jogo custom e o Jogando agora ganhou uma grade só**

- O Jogar agora abre um jogo custom, nas duas páginas. Antes, o gabinete ignorava o pedido, então o Jogar nunca os abria. O Fechar também enxerga um jogo custom aberto: um jogo de Windows (Wine, PortProton) não tem nome de emulador, e o Fechar respondia "closed 0".
- O Jogando agora, a prévia do marquee e o volume ficam numa grade só, alinhada. Na página de Jogos, a barra da vitrine fica toda na mesma altura, os filtros que não cabem esmaecem na ponta com uma seta que rola, e os clones viram uma chave com caixinha. Na ficha do jogo, "Abrir ao ligar o gabinete" vira uma linha da grade de fatos, e "1 vezes" passa a "uma vez".

🇺🇸 **Web panel: Play opens custom games and Playing now is one grid**

- Play opens a custom game now, on both pages. Before, the cabinet ignored the request, so Play never opened them. Close also sees a custom game that is open: a Windows game (Wine, PortProton) has no emulator name, and Close answered "closed 0".
- Playing now, the marquee preview and the volume sit in one aligned grid. On the Games page the showcase bar has one height, the filters that do not fit fade at the edge with an arrow that scrolls, and clones are a switch with a box. On a game's sheet, "Open when the cabinet turns on" is a row of the facts grid, and "1 times" now reads "once".
