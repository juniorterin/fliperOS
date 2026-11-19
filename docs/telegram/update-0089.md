🇧🇷 **Atualização 89 do FliperOS: Games > Folders refeito, HD com pastas do Batocera usado do jeito que está, formatar disco e animações** 📀

Setup > Games > Folders agora são duas coisas:

- **Folder shortcuts** é o antigo Link: mandar uma pasta do FliperOS para outro disco, como um atalho. A lista diz o que cada pasta guarda e para onde o atalho aponta, e "How shortcuts work" explica com um exemplo. Apontar a pasta de um sistema para uma pasta que tem vários consoles agora pergunta antes.
- **External storage** é para um disco inteiro, e leva o Storage que ficava em System: **FliperOS folders** (as pastas do FliperOS num segundo disco) e **Batocera filesystem**.

**Batocera filesystem:** um HD que guarda os jogos do jeito do Batocera (`batocera/roms/snes`, `megadrive`, `psx`...) é usado onde está. Cada pasta de console vira um sistema nos frontends, com o core que o FliperOS prefere, e em "Cores of the consoles" você troca o core de cada console. Nada é copiado nem escrito nas pastas de console. As pastas ao lado (`bios`, `saves`, `nvram`, `snap`) viram as do FliperOS, e as pastas que só o FliperOS tem (`namco2x6`, `fightcade`, `custom-packages`) são criadas no disco. Ainda não foi testado num disco Batocera de verdade.

🇺🇸 **FliperOS update 89: Games > Folders redone, a disk with Batocera folders used as it is, disk formatting and animations** 📀

Setup > Games > Folders is now two things:

- **Folder shortcuts** is the old Link: send a FliperOS folder to another disk, like a shortcut. The list says what each folder keeps and where the shortcut points, and "How shortcuts work" explains it with an example. Pointing a one-system folder at a folder that holds many consoles now asks first.
- **External storage** is for a whole disk, and takes the Storage that used to be in System: **FliperOS folders** (the FliperOS folders on a second disk) and **Batocera filesystem**.

**Batocera filesystem:** a hard disk that keeps the games the way Batocera does (`batocera/roms/snes`, `megadrive`, `psx`...) is used where it is. Each console folder becomes a system in the frontends, with the core FliperOS prefers, and in "Cores of the consoles" you change the core of each console. Nothing is copied or written inside the console folders. The folders beside them (`bios`, `saves`, `nvram`, `snap`) become the FliperOS ones, and the folders only FliperOS has (`namco2x6`, `fightcade`, `custom-packages`) are made on the disk. Not tried yet on a real Batocera disk.

![](docs/telegram/img/update-0089-external-storage.png)
![](docs/telegram/img/update-0089-cores.png)

---

🇧🇷 **A pergunta única do disco, e formatar**

- Quando um HD com pastas do Batocera é ligado, ou o gabinete liga com ele conectado, o frontend pergunta **uma vez** se quer usá-lo (o NÃO vem escolhido). Um disco assim não ganha mais a pasta `fliperos`. Um disco novo e comum ganha o mesmo tipo de pergunta, e um disco sem rótulo não aparece mais duas vezes na lista.
- **Format this disk** apaga a partição e a refaz em ext4 (o melhor para o FliperOS) ou exFAT (o Windows e o Mac abrem). Pergunta duas vezes, e recusa o disco do sistema, um disco em uso e um com RAID, LVM ou criptografia. Ainda não foi testado num disco de verdade.
- As telas e o painel web dizem onde uma pasta está de verdade quando ela está em outro disco, como o `~/roms/custom-packages (on HD: ...)` dos pacotes dos jogos custom.
- Raspar com o site funciona com o `~/media` num HD exFAT, FAT ou NTFS.

🇺🇸 **The one-time disk question, and formatting**

- When a hard disk with Batocera folders is plugged in, or the cabinet turns on with it connected, the frontend asks **once** whether to use it (NO is selected). Such a disk no longer gets a `fliperos` folder. A new, plain disk gets the same kind of question, and a disk without a label is no longer listed twice.
- **Format this disk** erases the partition and makes it new as ext4 (the best for FliperOS) or exFAT (Windows and Mac open it). It asks twice, and refuses the system disk, a disk in use and one with RAID, LVM or encryption. Not tried yet on a real disk.
- The screens and the web panel say where a folder really is when it is on another disk, like the `~/roms/custom-packages (on HD: ...)` of the custom game packages.
- Scraping with the site works with `~/media` on an exFAT, FAT or NTFS hard disk.

![](docs/telegram/img/update-0089-dialog.png)
![](docs/telegram/img/update-0089-format.png)

---

🇧🇷 **Animações no Setup e no menu do jogo**

- **Setup:** entrar num item aproxima a tela, e voltar afasta, em 0,3 segundo. O Setup e o frontend agora pedem vsync, para o quadro não trocar no meio da imagem (tearing).
- **Menu de um jogo:** abre animado, o azulejo escolhido se mexe e apertar toca o efeito antes de agir. O PLAY acende em verde e a imagem se desliga como numa TV de tubo, justo quando o jogo abre; a estrela solta faíscas; o + mergulha na página dele.

Ainda não visto num tubo.

🇺🇸 **Animations in the Setup and the game menu**

- **Setup:** entering an item zooms the screen in, and going back zooms out, in 0.3 seconds. The Setup and the frontend now ask for vsync, so a frame does not change in the middle of the picture (tearing).
- **A game's menu:** it opens animated, the tile you pick moves and pressing plays the effect before it acts. PLAY lights up green and the picture switches off like a tube TV, just as the game opens; the star sparkles; the + dives into its page.

Not seen yet on a CRT.
