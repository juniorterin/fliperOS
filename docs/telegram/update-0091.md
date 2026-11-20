🇧🇷 **Atualização 91 do FliperOS: sons no menu e no frontend, e uma trilha com o nome de cada música** 🎶

**Setup > Audio Setup > Menu sounds** (com ícone novo): seis sons, cada um com o seu **arquivo** (um seletor de arquivos, em `~/media/fliperos-sounds`) e o seu **volume**: cursor andando, Enter, Voltar, abrir jogo, fechar jogo e alerta.

Já vem com sons retrowave: senoides suaves com um eco quente. Abrir o frontend, o desktop ou o shell toca só o som de abrir jogo.

🇺🇸 **FliperOS update 91: menu and frontend sounds, and a soundtrack that shows each song's name** 🎶

**Setup > Audio Setup > Menu sounds** (with a new icon): six sounds, each with its own **file** (a file picker, in `~/media/fliperos-sounds`) and its own **volume**: cursor moving, Enter, Back, game open, game close and alert.

It comes with retrowave sounds: soft sine waves with a warm echo. Opening the frontend, the desktop or the shell plays only the game-open sound.

![](docs/telegram/img/update-0091-setup-sounds.webp)

---

🇧🇷 **Tab > FRONTEND SOUNDS**

Os mesmos seis sons do Setup, um conjunto só: mudar num lugar muda no outro. E a **música**: um arquivo, ou uma pasta dentro de `music/` tocada ao acaso, com o seu volume.

**PAUSE MUSIC**, se ligado, faz a música esperar o som do vídeo de preview; desligado (o padrão), as duas tocam juntas. O volume do vídeo de preview também é ajustável.

O som do preview chegava uns 0,3 s depois da imagem: agora o frontend mede o atraso e segura a imagem, e os dois saem juntos.

🇺🇸 **Tab > FRONTEND SOUNDS**

The same six sounds as the Setup, one set: change one place and the other follows. And the **music**: a file, or a folder inside `music/` played at random, with its own volume.

**PAUSE MUSIC**, when on, makes the music wait for the preview video's sound; off (the default), both play together. The preview video's volume is adjustable too.

The preview's sound used to reach the speakers about 0.3 s after the picture: the frontend now measures that delay and holds the picture, so both come out together.

![](docs/telegram/img/update-0091-frontend-sounds.webp)

---

🇧🇷 **A música que começou**

Quando uma música começa, entra uma barra com o nome dela, como uma conquista desbloqueada: o círculo com a nota e um cometa girando. A barra tem só a largura do nome e fica longe da borda; um nome comprido corre, e ela espera ele chegar ao fim.

As músicas não vêm no FliperOS (a licença do Pixabay não deixa distribuir o arquivo sozinho): ponha em `~/media/fliperos-sounds/music`. Créditos no README: BurtySounds, Musinova e kaazoom.

🇺🇸 **The song that just started**

When a song starts, a bar with its name slides in, like an unlocked achievement: the circle with a note and a comet running around it. The bar is only as wide as the name and stays clear of the edge; a long name runs, and the bar waits for it to get to the end.

The songs do not ship with FliperOS (the Pixabay licence does not allow handing the file out on its own): put them in `~/media/fliperos-sounds/music`. Credits are in the README: BurtySounds, Musinova and kaazoom.

![](docs/telegram/img/update-0091-frontend-music.webp)
