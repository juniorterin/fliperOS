🇧🇷 **Atualização 86 do FliperOS: o filtro de flicker nos jogos do PortProton e o menu na tela que não fica preto** 🖥️

Dois defeitos do filtro do entrelaçado nos jogos custom do Windows:

- Os jogos custom que abrem pelo PortProton (o runner padrão) ficavam sem o filtro de flicker em 480i: o contêiner do PortProton troca a variável pela qual a camada do filtro é carregada, então a camada nunca chegava neles (visto no MARVEL Cosmic Invasion). Agora eles recebem o filtro pelo compositor que o Fightcade e o desktop já usam, no nível do próprio jogo (Video Setup > Interlaced hacks). O Wine do sistema e o Wine Staging continuam com a camada, e o log deles não se enche mais de linhas "wrong ELF class".
- O menu na tela não fica mais preto quando você troca o nível do filtro. Trocar o nível reinicia o compositor, que limpava a janela do menu, e nada a pintava de novo até o menu mudar. Agora ela se repinta (PortProton, Wine, MUGEN, Fightcade).

🇺🇸 **FliperOS update 86: the flicker filter in PortProton games and an on-screen menu that stays visible** 🖥️

Two flaws of the interlaced filter in custom Windows games:

- Custom games that open through PortProton (the default runner) had no flicker filter in 480i: PortProton's container replaces the variable the filter's layer loads through, so the layer never reached them (seen in MARVEL Cosmic Invasion). They now get the filter through the compositor that Fightcade and the desktop already use, at the game's own level (Video Setup > Interlaced hacks). The system Wine and Wine Staging keep the layer, and their logs no longer fill with "wrong ELF class" lines.
- The on-screen menu no longer goes black when you change the filter level. Changing the level restarts the compositor, which cleared the menu's window, and nothing painted it again until the menu changed. It now repaints (PortProton, Wine, MUGEN, Fightcade).

---

🇧🇷 **Fightcade, Wine e o painel web**

- Fightcade: os jogos de Naomi e Atomiswave (Marvel vs. Capcom 2 e os outros) abrem. O Flycast do Fightcade recebe as BIOS de arcade (`naomi.zip`, `naomi2.zip`, `awbios.zip`, `dc_boot.bin`) de `~/bios/dc` toda vez que o Fightcade abre, só as que ainda não tem.
- Jogos de Windows no Wine, o FBNeo do Fightcade incluído, trocam de modo de tela agora: a biblioteca XRandR de 32 bits (`libxrandr2:i386`) vem com o Wine, e o update a instala onde o Wine já está.
- Jogos custom de 32 bits (o Darkula e a maioria dos .exe) não abrem e fecham sozinhos numa placa com o driver Vulkan do Mesa (AMD amdgpu, Intel mais nova): o driver de 32 bits (`mesa-vulkan-drivers:i386`) vem com o Wine e o PortProton, e o update o instala. Enquanto ele não está lá, o jogo desenha com OpenGL.
- Painel web: o Fightcade não quebra mais o painel (o status falhava com a sala, ou um jogo sem a camada de FPS, aberto) e mostra o FPS do FBNeo, do FBA e do SNES9x.

🇺🇸 **Fightcade, Wine and the web panel**

- Fightcade: Naomi and Atomiswave games (Marvel vs. Capcom 2 and the rest) open. Fightcade's Flycast gets the arcade BIOS (`naomi.zip`, `naomi2.zip`, `awbios.zip`, `dc_boot.bin`) from `~/bios/dc` every time Fightcade starts, only the ones it doesn't have yet.
- Windows games on Wine, Fightcade's FBNeo included, can change the screen mode now: the 32-bit XRandR library (`libxrandr2:i386`) comes with Wine, and the update installs it where Wine already is.
- 32-bit custom games (Darkula and most .exe files) no longer open and close by themselves on a card that uses the Mesa Vulkan driver (AMD amdgpu, newer Intel): the 32-bit driver (`mesa-vulkan-drivers:i386`) comes with Wine and PortProton, and the update installs it. Until it is there, the game draws with OpenGL.
- Web panel: Fightcade no longer breaks the panel (the status failed while its lobby, or a game without the FPS layer, was open) and it shows the frame rate of FBNeo, FBA and SNES9x.

---

🇧🇷 **Também na Atualização 86 do FliperOS: controles, jogos custom e frontend**

- Button mapping: o GroovyMAME abre com os seis botões do painel não importa como o mapeamento foi salvo (painel web, menu gráfico, ao ligar um controle, na atualização).
- Jogos custom: Criar pacote > Testar grava 30 segundos a 60 quadros por segundo, com o som do jogo, e as fotos e os vídeos saem em 4:3 exato. A opção "Does the game already work with the joystick?" faz o pacote levar um mapa de teclas vazio. O Testar no gabinete tem o botão Fechar e mostra o fim do log se o jogo fechar sozinho.
- Jogos custom: cada grupo pode ter um logotipo de uma cor só (enviado ou escolhido entre os 322 dos sistemas), mostrado no letreiro do Pixelcade/ZeDMD, na tira do frontend e no topo da lista, e pode ser renomeado (Setup: Rename group, ou o lápis no painel web) com tudo o que vai junto. O botão do ícone do grupo saiu do painel web.
- Frontend: um vídeo sem faixa de som toca mesmo assim.

Quem já tem o FliperOS instalado recebe pela atualização do próprio Setup, sem ISO nova.

🇺🇸 **Also in FliperOS update 86:** controls, custom games and the frontend

- Button mapping: GroovyMAME opens with the panel's six buttons however the mapping was saved (web panel, graphical menu, plugging a controller, the update).
- Custom games: Create package > Test records 30 seconds at 60 frames per second, with the game's sound, and photos and videos are exact 4:3. "Does the game already work with the joystick?" makes the package carry an empty key map. Test on the cabinet has a Close button and shows the end of the log if the game closes by itself.
- Custom games: each group can have a one-colour logo (uploaded or picked from the 322 system logos), shown on the Pixelcade/ZeDMD marquee, the frontend ribbon and the top of the list, and can be renamed (Setup: Rename group, or the pencil in the web panel) with everything that goes with it. The group icon button is gone from the web panel.
- Frontend: a video with no sound track plays anyway.

Installed cabinets get it from the Setup's own update, no new ISO.
