🇧🇷 **Atualização 65 do FliperOS: controles Bluetooth, mapeamento de arcade ou joypad e o guia do joypad** 🎮

O Setup ganha um gerenciador de Bluetooth, e o Button mapping pergunta primeiro qual controle você vai mapear e se ele é um painel de arcade ou um joypad. O frontend passa a ter a coluna JOYPAD e um guia desenhado com os botões do videogame que você escolher. Abaixo, todas as telas novas.

🇺🇸 **FliperOS update 65: Bluetooth controllers, arcade or joypad mapping and the joypad guide** 🎮

The Setup gets a Bluetooth manager, and Button mapping first asks which controller you are mapping and whether it is an arcade panel or a joypad. The frontend now has a JOYPAD column and a guide drawn with the buttons of the console you pick. Every new screen is below.

---

![](docs/telegram/img/0065-setup-joysticks.png)
![](docs/telegram/img/0065-setup-bluetooth.png)

🇧🇷 **Bluetooth**

Setup > Joysticks > Bluetooth: pareie um controle (coloque-o em modo de pareamento e escolha na lista), deixe o gabinete parear sozinho por 30 s, conecte, desconecte, esqueça um controle e ligue ou desligue o adaptador.

🇺🇸 **Bluetooth**

Setup > Joysticks > Bluetooth: pair a controller (put it in pairing mode and pick it from the list), let the cabinet pair on its own for 30 s, connect, disconnect, forget a controller and turn the adapter on or off.

---

![](docs/telegram/img/0065-setup-controllers.png)
![](docs/telegram/img/0065-setup-player.png)

🇧🇷 **Primeiro o controle, depois o jogador**

O Button mapping começa com a lista dos controles ligados, com o ícone de fio ou sem fio, e a lista se atualiza sozinha quando você liga um controle. Escolha o controle e diga se ele é o P1, P2, P3... Os controles com fio vêm sempre primeiro; os Bluetooth pegam os jogadores que sobram, na ordem em que conectam.

🇺🇸 **The controller first, then the player**

Button mapping starts with the list of connected controllers, with a wired or wireless icon, and the list refreshes by itself when you turn a controller on. Pick the controller and say whether it is P1, P2, P3... Wired controllers always come first; Bluetooth ones take the players left, in the order they connect.

---

![](docs/telegram/img/0065-setup-kind.png)
![](docs/telegram/img/0065-setup-panelbuttons.png)
![](docs/telegram/img/0065-setup-capture8.png)

🇧🇷 **Painel de arcade ou JAMMA**

Escolha arcade e diga quantos botões cada jogador tem, de 1 a 8. O painel desenhado mostra só esses botões, e cada um acende na hora de apertar. Esc cancela o mapeamento.

🇺🇸 **Arcade panel or JAMMA**

Pick arcade and say how many buttons each player has, from 1 to 8. The panel drawing shows only those buttons, and each one lights up when it is its turn. Esc cancels the mapping.

---

![](docs/telegram/img/0065-setup-padcapture.png)
![](docs/telegram/img/0065-setup-padcapture2.png)

🇧🇷 **Joypad, como no Batocera**

Escolha joypad e o Setup reconhece o controle (Xbox, PlayStation, Nintendo...) e já mostra os botões com os nomes dele. Aperte cada um na ordem; segure qualquer botão para pular um que o controle não tem.

🇺🇸 **Joypad, like in Batocera**

Pick joypad and the Setup recognises the controller (Xbox, PlayStation, Nintendo...) and shows the buttons with its own names. Press each one in turn; hold any button to skip one the controller does not have.

---

![](docs/telegram/img/0065-setup-confirm.png)
![](docs/telegram/img/0065-setup-confirm2.png)

🇧🇷 **Os botões dos menus**

No fim, aperte o botão que aceita nos menus (o verde) e o que volta (o vermelho). O Setup e o frontend passam a usar esses dois, seja o controle de Xbox, de PlayStation ou de GameCube.

🇺🇸 **The menu buttons**

At the end, press the button that accepts in the menus (the green one) and the one that goes back (the red one). The Setup and the frontend use those two from then on, whether it is an Xbox, a PlayStation or a GameCube controller.

---

![](docs/telegram/img/0065-fe-controls.png)
![](docs/telegram/img/0065-fe-controls-layout.png)
![](docs/telegram/img/0065-fe-controls-joypad.png)

🇧🇷 **Frontend controls com a coluna JOYPAD**

No frontend, Tab > Frontend options > Frontend controls agora tem três colunas: o comando do painel, o botão do joypad e a tecla de cada função. No alto, GUIDE escolhe se o guia mostra o painel de arcade ou um joypad, e JOYPAD LAYOUT escolhe o videogame.

🇺🇸 **Frontend controls with the JOYPAD column**

In the frontend, Tab > Frontend options > Frontend controls now has three columns: the panel control, the joypad button and the key of each function. At the top, GUIDE chooses whether the guide shows the arcade panel or a joypad, and JOYPAD LAYOUT picks the console.

---

![](docs/telegram/img/0065-guide-playstation.png)
![](docs/telegram/img/0065-guide-xbox.png)
![](docs/telegram/img/0065-guide-gamecube.png)
![](docs/telegram/img/0065-guide-snes.png)
![](docs/telegram/img/0065-guide-nes.png)
![](docs/telegram/img/0065-guide-dreamcast.png)
![](docs/telegram/img/0065-guide-saturn.png)
![](docs/telegram/img/0065-guide-megadrive.png)
![](docs/telegram/img/0065-guide-neogeo.png)
![](docs/telegram/img/0065-guide-n64.png)
![](docs/telegram/img/0065-guide-arcade.png)

🇧🇷 **O guia com os botões de cada videogame**

PlayStation, Xbox, GameCube, Super Nintendo, NES, Dreamcast, Saturn, Mega Drive, Neo Geo CD e Nintendo 64, com os botões nas posições e proporções dos controles originais, e cada função no botão dela. O último é o guia do painel de arcade.

🇺🇸 **The guide with the buttons of each console**

PlayStation, Xbox, GameCube, Super Nintendo, NES, Dreamcast, Saturn, Mega Drive, Neo Geo CD and Nintendo 64, with the buttons in the places and sizes of the original controllers, and each function on its button. The last one is the arcade panel guide.

---

🇧🇷 **Também na atualização 65 do FliperOS**

- Escolha a versão do FliperOS: Setup > System > FliperOS version (e o painel web) lista os updates; volte a um mais velho se um update estragou algo, ou avance para um mais novo.
- O botão de desligar fecha um jogo do GroovyMAME na hora, gravando recordes, NVRAM e ajustes.
- Teclado, painel ou controle ligado depois do boot agora funciona com as teclas de desligar e de volume.
- Os jogos 2D da Midway (Mortal Kombat 1 a 3, NBA Jam, Smash TV, NARC...) não ficam mais esticados no tubo: 320x240p a 59 Hz.

🇺🇸 **Also in FliperOS update 65:**

- Choose the FliperOS version: Setup > System > FliperOS version (and the web panel) lists the updates; go back to an earlier one if an update broke something, or forward to a newer one.
- The power button closes a GroovyMAME game at once, saving high scores, NVRAM and settings.
- A keyboard, panel or controller plugged in after boot now works with the power and volume keys.
- Midway 2D games (Mortal Kombat 1 to 3, NBA Jam, Smash TV, NARC...) no longer look stretched on the tube: 320x240p at 59 Hz.
