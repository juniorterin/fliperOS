## The FliperOS frontend

The default since 2026-10-23: the game list in the look of the Setup menu (Press Start 2P, Dracula colours, the animated background), drawn at 320x240 and stretched to the screen mode. It ships in the image (`fliperos-setup/gui/fliperos-frontend`, Python and pygame) and is the `fliperos` row of the session table.

It shows the same thing as the [Web panel](Web-panel.md), from the same code:
- the games of each folder, from FliperOS's own lists (`~/.local/share/fliperos/lists`, in the format of Attract-Mode's romlists; Attract-Mode Plus is optional). The arcade ones carry the name, year, manufacturer, clones and category from MAME's XML (the AttractPlus ROM List, `fliperos-romclean romlist`);
- the game filters the Setup writes into every Attract-Mode display (`fliperos-setup --filters`), plus Favourites;
- FliperOS's own favourites (`~/.config/fliperos/favourites`) and the game information saved in `~/media/info`.

**The lists follow the folders.** When the frontend opens, and whenever a games folder changes (games copied over the network or from a USB disk), it asks the Setup to redo the lists in the background (`fliperos-setup --romlists`). New arcade sets get their MAME names right away: when MAME's list is not cached yet, GroovyMAME's `-listxml` is read once (about a minute).

**Vertical monitor.** With Video Setup > Monitor orientation on a vertical setting, the frontend is laid out standing up (240x320) and turned to the monitor's side when shown, the same side GroovyMAME turns the games to (`ror` for clockwise, `rol` for counter-clockwise). In the list the picture goes on top and the games below; the grid has three rows of 3:4 thumbnails; the controls guide stacks the stick above the buttons.

**Three views** (Start switches them):
- **List**: the games on the left, the picture, logo and information on the right. A game with clones has a "+" on its left: button 1 unfolds the clones under it, each with what differs in its name (the region, the set, bootleg).
- **Full screen**: the game's video or picture behind (it slides to the next game with the cursor; the videos of the 3 games before and after are opened ahead, held on their first frame), the name and information in front, and on the right the list as four stacked thumbnails, with arrows above and below while there are more games that way; the column slides to its new place. The pictures of the games around the cursor are read ahead, so changing game is instant. The clones come right after their parent: each clone thumbnail carries a **CLONE** badge with an up arrow in its top-right corner, the title shows what differs in its name after the title, and button 2 goes back to the parent.
- **Grid**: three thumbnails a row, two rows, all the same size: 4:3 with the game's screenshot (or its cover), 3:4 when Video Setup has the monitor vertical. The chosen one has a pink frame that slides to it, and the rows slide too. Every visible game plays its video at once, silent except the chosen one; the videos of the 3 rows above and below are opened and held on their first frame, so a new row starts playing at once. A scrollbar in the corner, with a small arrow above and below it while there are more rows that way. The clones come right after their parent, with the same **CLONE** badge as in full screen; button 2 on a clone goes back to the parent.

**The game's video.** In the three views, the game's video (`~/media/preview/<folder>/<set>.mp4`) plays with its sound, half a second after the cursor stops on it; without a video, its picture shows. In any view, a game missing some of its art (screenshot, cover, marquee, logo or video) gets the missing pieces scraped by itself when the cursor stays on it for 2 seconds, once per game; they land in the same `~/media` folders the scraper uses. The logo comes from the Arcade Database too (its "decals"); what it lacks comes one file at a time from the archive.org packs of Setup > Games > Scraper > Art packs by torrent, without downloading the pack.

**Automatic scrape.** While the frontend is open, it fetches in the background, one game at a time, what each game in the folders still lacks:
- arcade: the information, screenshot, flyer, marquee and logo from the Arcade Database;
- consoles: the cover and screenshot from libretro-thumbnails;
- videos and the logos still missing: the torrent packs of Setup > Games > Scraper > Art packs by torrent, only the files of the games you have (`fliperos-setup --mediapacks auto`, checked every 6 hours). A pack that keeps its files in one .zip per letter (the MAME videos) would download whole letters, gigabytes for a few videos: it stays out of the torrent, and the frontend fetches each file from inside the zip over HTTP instead.

It pauses while a game is open. A game is tried once every 30 days (what a source does not have stays missing): `~/.local/share/fliperos/scrape-state.json`. Tab > Frontend options shows a progress bar, how many games are left and the torrents' progress.

Genre, controls and buttons show with Arcadeflow's icons when Arcadeflow has been downloaded (it can't ship in the image). In the list they come without text, in two rows: the genre with the number of players beside it, then the control (a pistol for light-gun games, which Arcadeflow has no icon for) with the buttons.

**Controls.** A guide shows them each time the frontend opens; any button closes it. The guide draws the controls as **Frontend controls** (below) left them: each panel button where Setup > Joysticks > Buttons layout puts it, in its function's colour. A button with no function is left out of the drawing, and so is the joystick when no direction has one. Under the buttons come Start and the functions that only have a key.

These are the defaults:
- Up and down move through the games; past the last one comes the first again, and before the first the last (holding stops at the end, the next press goes around). Holding speeds up, and after 3 seconds the letter mode starts: the letter big in the middle of the screen, the cursor jumping from letter to letter (slowly at first, faster after a short hold).
  - The letter mode stays after letting go: each tap of up or down moves one letter.
  - Two seconds without touching anything (or any other button) end it, on the first game of that letter.
- Left and right change the game list (each games folder, and Arcade with all the arcade folders together); the screen slides to the new one. A strip of tiles shows the lists around the chosen one: each tile has the system's written logo (the same as the marquee's, from the Arcadeflow theme, made once and kept in `~/.cache/fliperos/syslogo`), filling 80% of a tile as wide as the logo needs, with the emulator's icon sitting on the bottom right corner; under it, the number of games. Without Arcadeflow, or a system it doesn't know, the tile is square with only the emulator's icon, and the list's name is written under it. The same logo also replaces the list's name at the top of the screen. Each game list remembers where the cursor was, also after the frontend is closed or the cabinet turned off. In the grid they move through it, and change the game list only when the chosen game already touches that side; a tab below the thumbnails names the next one.
- Button 1 opens the game's menu: Play, Favourite and "+". The "+" page has the game's information from the Arcade Database, saved on the cabinet, in two pages. The first has the cover, year, genre, players and control, the player 1 buttons drawn on the panel where **Buttons layout** puts them (with their colour and what they do, the same drawing as the controls guide; the joystick directions are left out) and the game's description. A blinking arrow on the right leads to the second: the game's pictures, maker, series, screen, status, language, set and rating, and the rest of the arcade-history.com text (Technical, Trivia...). A value too long for its line shows with "..." and then scrolls inside it, like a marquee.
- Button 2 goes back; from the list, it asks whether to return to the FliperOS menu.
- Buttons 3 and 6 move a page up and down. Button 4 marks or unmarks the favourite. Button 5 opens the filters; the filter belongs to the romlist (each one keeps its own, and changing romlist brings back its filter).
- Tab (keyboard) opens the game options:
  - Classify: genre, players, buttons, control, year, maker, rotation and series, saved in `~/media/info/<folder>/<set>.user.json`; the filters use them;
  - Rename, with an on-screen keyboard;
  - Scrape this game: its information, pictures, logo and video, right away;
  - Delete this game: after a YES/NO question, its file goes away from the folder (for MAME, also the CHD folder of the same name); its art in `~/media` stays. A clone kept inside its parent's zip has no file of its own to delete.

  Under them come the **frontend options**. The game options and the frontend options are one list that scrolls with the chosen line (always whole lines, never cut in half), with the Auto scrape box fixed at the bottom; the card is 200 pixels tall, so it fits on the tube. Each option is saved at once in `~/.config/fliperos/frontend.json`:
  - **View**: list, full screen or grid, with left and right (Start also switches it).
  - **Show clones** and **Hidden games** (the list of hidden games; button 1 brings one back).
  - **Frontend controls**: a screen with the frontend's functions (games up and down, list left and right, select, back, page up and down, favourite, filter, view mode and game options). Each one has a **Panel** column and a **Keyboard** column; left and right switch between them.

    Select asks for the new one: press the panel control (a button, a direction or Start) or the key. A button or key that another function already had swaps: that function gets the old one. The same one again, or Delete, leaves the function with none; any function can have none.

    Nothing pressed for 8 seconds keeps it as it was (Esc, or the panel's back button when choosing a key, cancels). **Reset** brings back the defaults. Each change works at once and is saved in `frontend.json` (`controls`).

    **Panel layout** (left and right) is the shape of the panel that the guide draws: **6 buttons** in two rows (where Buttons layout puts them), **4 in line** like a Neo Geo MVS, **3 in line**, **2 in line** or **2 stacked**. The guide draws only the buttons that shape has, and in this screen a button it doesn't have shows dimmed (its function then works only from the keyboard).

    The coin stays the coin (commercial mode). A key that the panel itself sends (a keyboard encoder: the `k:` entries of the Button mapping, or MAME's keys without them) can't be a keyboard key. Leaving the screen with select or back off the panel shows a warning: without them the menus only open from the keyboard.
  - **Exit key**: the keyboard key that closes the game. Button 1 asks for it: press it within 8 seconds; button 2 on a controller cancels. A key the panel itself sends (a keyboard encoder) is refused, since each button does one thing. Left, right or the Delete key turns it off.
  - **Exit buttons**: panel buttons that close the game when held together for a second. Button 1 asks for them: hold two or more together for a second. Left, right or the Delete key turns it off. In commercial mode the coin can't be one of them.
  - **Power closes game**: on (the default), the cabinet's power button closes the open game; off, it does nothing while a game is open. With no game open it always powers off.
  - **Commercial mode** and, with it on, **Minutes per coin** (1 to 60, left and right).

  The exit key and buttons are read alongside the game by `fliperos-buttons hotkey`, without taking anything from it. The frontend closes the game and what runs under it (the X server, the emulator) with SIGTERM, and SIGKILL after 4 seconds.

**Commercial mode** (Tab > Frontend options), for a cabinet that charges by the time played:
- Without time, the customer can browse the games but not choose one: button 1 shows INSERT COIN.
- Each coin (the panel's COIN, also during a game) adds the minutes chosen in Minutes per coin to the time left. The time runs by the clock, also on the menu and with the cabinet off. Turning commercial mode off clears the time left: turned on again, it starts with no coin.
- When the time runs out during a game, the game closes and the frontend says TIME IS UP.
- The indicator: without time, a coin going into a slot and INSERT COIN blinking, in a frame. With time, a clock with the minutes left (the seconds, in red, in the last minute). In the list it sits under the game's control icons; in full screen in the top left corner; in the grid in the bottom right corner (the logo, the texts and the icons move up a little, the icons in two lines).
- It is a kiosk: the controller's button 2 never closes the frontend. The Esc key of a real keyboard (the operator's) still asks whether to go back to the FliperOS menu.

**The power button.** With no game open, the cabinet's power button powers off; with a game open it closes the game (Tab > Frontend options > Power closes game). The frontend tells `fliperos-powerkey` which process is the game through the file named in `FLIPEROS_POWERKEY=games:FILE` (`$XDG_RUNTIME_DIR/fliperos-frontend.game`): its other children, the video player and the scraper, are not a game. Before this, the button killed the video and never powered off.

The buttons are the panel's own, from Setup > Joysticks > Button mapping (`/etc/fliperos/buttons.map`). Without a mapping, a common pad works, and so does a keyboard encoder in MAME's layout.

A game opened from the frontend gets the screen, the sound and the controls, and counts in Attract-Mode's play statistics (the Most Played filter).

## Setup > Games > Frontend

The default launcher, the one that opens when the computer starts; one that isn't installed can be installed from the FliperOS repository, which ships inside the image (`/opt/fliperos/repo`, below). Whatever doesn't have a package yet shows as *not available yet*.

**Fightcade 2** doesn't come from a package: it is downloaded on the spot from its website ([Fightcade 2](Fightcade-2.md)). **At 240p**: on a 15 kHz monitor the frontends run at 320x240, and each one's default is designed for 720 lines or more — the text ends up 4 to 8 pixels tall.

That's why the Setup writes a configuration once (whatever is changed later in the frontend itself stays; with the frontend open, it applies next time): both get a **FliperOS 240p** theme, made for 240 lines and in Dracula colors: the system at the top, the game list in a 12-pixel font, the game image with year, publisher and description.

In **EmulationStation** (ES-DE) it is `config/esde-theme-fliperos`, installed in `/usr/share/es-de/themes/fliperos-240p-es-de` (`Theme` in `es_settings.xml`), without the menu background blur and without the new-version notice: the systems as a list of names, the game video (if any) in place of the image, and in the footer only the buttons that fit in 320 pixels.

In a wide-pixel mode (640x240 on a 4:3 tube) the FliperOS ES-DE package draws the interface at 320x240 and stretches it twice horizontally (`packaging/patches/emulationstation`; `fliperos-kms-run` sets `ESDE_STRETCH_X` from the mode), so text and images keep their proportions on the tube, as Arcadeflow does.

In the themes that ES-DE ships, even with the large font, the list text is thin and low-contrast and the footer help ends up about 6 pixels tall. In **Pegasus** it is `config/pegasus-theme-fliperos`, installed in `/usr/share/pegasus-frontend/themes` — left/right switch systems, L2/R2 skip ten games.

Grid, Pegasus's default theme, shows the covers at 320x240 but leaves the description 4 pixels tall.

## Pixelcade marquee

A [Pixelcade](https://pixelcade.org) LED or LCD marquee shows the game you have selected in the frontend and the game you open. **Setup > Games > Extras > Pixelcade** installs it.

Pixelcade's software (`pixelweb`) is closed source, so it isn't in the image: the Setup downloads it from Pixelcade's GitHub ([alinke/pixelcade-linux-builds](https://github.com/alinke/pixelcade-linux-builds)), along with the artwork (a few hundred MB), into `~/pixelcade`.

Choosing Extras > Pixelcade again, once it is installed, offers to update the program and the artwork, or to install the **paid art pack**: type the license code you got from Pixelcade and the Setup downloads the pack.

`~/pixelcade` is the folder Pixelcade's own guides use, so the same can be done by hand: `cd ~/pixelcade && ./pixelweb -install-artpack <code>`.

The events below are the ones of Pixelcade's own EmulationStation scripts ([alinke/pixelcade-linux](https://github.com/alinke/pixelcade-linux/tree/main/batocera/scripts)), with the same calls to `pixelweb`.

- **Service**: `fliperos-pixelcade.service` keeps `pixelweb` running as the `fliperos` user and starts it when the marquee is plugged in (`99-fliperos-pixelcade.rules`, USB IDs `1b4f:0008` for V1 and `2e8a:1050` for V2). The serial port belongs to the `dialout` group. Pixelcade's settings page is at `http://<cabinet IP>:8080`.

  If no marquee is connected, `pixelweb` searches for about 30 seconds and then exits. The service tries 3 times and then stops until the marquee is plugged in. When it starts, the marquee shows the FliperOS logo; when the computer shuts down or restarts, it shows "Bye".
- **Game opened**: every game from every frontend and emulator goes through `fliperos-kms-run` or `fliperos-x11-run`. These call `fliperos-pixelcade launch` in the background, so a game never waits for the marquee. The game is the last argument: a file in `~/roms`, or the set name for GroovyMAME and Model 2.

  When there is no game (a frontend, an emulator's menu) nothing happens. First a text scrolls once: the game's high scores, or "Now Playing" and the game's name. Then the game's marquee stays.
- **High scores**: for arcade games, the text is the top three scores (`#1 19,130 DAA #2 ...`). They come from the game's `.hi` file, the newest one among `~/.mame/hiscore` (GroovyMAME's `hiscore` plugin) and the RetroArch saves folder (`/opt/fliperos/saves/retroarch`, where the MAME and FBNeo cores write theirs).

  The hi2txt program reads the file, as in Pixelcade's installer. Extras > Pixelcade downloads it (pinned by hash) into `~/pixelcade/hi2txt` and installs Java from apt (`default-jre-headless`), which it needs. A game that hi2txt doesn't know shows its name instead.
- **Game closed**: the helper waits for the game to end and then shows the game's marquee the way the frontend selection does. That matters in Pegasus, which doesn't report what is selected.
- **Game selected**: in **ES-DE**, through its custom event scripts (`~/ES-DE/scripts/game-select` and `system-select`, with *Custom event scripts* and *Browsing custom events* turned on; browsing doesn't wait for them).

  In **Attract-Mode Plus**, through FliperOS's *Pixelcade* plugin, which is copied to `~/.attract/plugins` and turned on in `plugins.cfg`. Pegasus has no event hooks, so it only shows the game that was opened.

  The service writes these frontend settings at every boot; if the frontend is open at that moment, they wait for the next boot.
- **Screensaver**: when the FliperOS frontend is idle for 30 seconds, or the screensaver of ES-DE (`screensaver-start` and `screensaver-end` scripts) or Attract-Mode Plus starts, the marquee plays the FliperOS logo animation (the same as the ZeDMD's, copied to `~/pixelcade/console/fliperos-idle.gif`). Without it, the marquee goes into Pixelcade's attract mode, a playlist you set up on the settings page. When it ends, the marquee shows the selected game or system again.
- **FliperOS menu**: in the menu that opens when the frontend closes, the marquee follows the cursor. Each of the five items has its own animation in the style of the default logo: a synthwave sun with an animated icon and the item's name in neon chrome, with glitches. The items are **FRONTEND** (a joystick), **SETUP** (two gears), **DESKTOP** (a monitor with windows and a mouse), **SHELL** (a terminal typing) and **POWER** (the power symbol pulsing). Entering an item keeps its animation through the submenus. The graphic Setup sends each move of the cursor (`fliperos-pixelcade menu ITEM`); the text Setup sends the item when you enter it. The ZeDMD, the Pixelcade, the web panel's preview and the OBS page all play it (`tools/marquee-logo-anim.py`, `marquee-menu-ITEM.gif` among the web panel's files).
- **Achievements**: with RetroAchievements turned on in RetroArch (`cheevos_enable = "true"`), each unlocked achievement shows on the marquee, and then the game's marquee comes back.

  RetroArch has no event for this, so `fliperos-kms-run` opens it with `--verbose` and the helper reads the `[RCHEEVOS] Awarding achievement` lines from `/opt/fliperos/logs/retroarch.log`. In debug mode the log goes to the screen and no achievement is shown.
- **Pixelcade LCD over USB**: the LCD marquee (USB ID `1d6b:3232`, firmware 6.3 or newer) appears as a network card.

  The udev rule keeps it out of NetworkManager and starts `fliperos-pixelcade-lcd@<interface>.service`, which gives the card the address `169.254.100.2` (the LCD is `169.254.100.1`), sets `lcdMarquee` and `lcdUsbConnected` in `~/pixelcade/pixelcade.ini`, writes the LCD's name there and restarts the service. This is what Pixelcade's installer does; it has not been tested with an LCD marquee yet.
- **Visual Pinball**: a program whose name starts with `vpinball` draws the display itself, over the same serial port. When it opens, `pixelweb` (and `dmdserver`) close and let go of the port; when it ends, the services open them again. FliperOS doesn't ship Visual Pinball.
- **Changing the system in the FliperOS frontend**: when you switch the game list (left and right), the system's written logo (NAOMI, ATOMISWAVE, SEGA MODEL 3...) slides in on the marquee from the side the list moved to, with the previous one leaving, and blinks twice. It is the same slide as the frontend's screen.

  The logos are the ones of the Arcadeflow's displays menu: each is a character of the theme's font, drawn when needed by `fliperos-syslogo` from `~/.attract/layouts/Arcadeflow` (the Setup downloads the theme; Arcadeflow has no license, so none of it is in the image). Without the theme, or for a system that isn't in it, the marquee shows the system's art as before.

  The ZeDMD gets the frames straight from `fliperos-dmd slide`. The Pixelcade only shows files, so the logo goes in a GIF in `~/pixelcade/console` (`fliperos-logo-*`, replaced at each switch). `fliperos-syslogo export DIR` writes every logo as a PNG.

  The marquee preview of the [web panel](Web-panel.md) and the marquee page for OBS draw the same logo with the same slide and blinks (the panel serves it as a PNG, `/api/marquee/logo?name=`), as long as **marquee_overlay** is on; the preview turns it on by itself.
- **Systems**: the arcade folders (`mame`, `naomi`, `naomi2`, `atomiswave`, `model2`, `model3`, and the MAME and FBNeo cores) use Pixelcade's `mame` artwork. The RetroArch cores go by their system (`snes`, `genesis`, `psx`...). Other folders go by their name.

### DOFLinx (effects during the game)

[DOFLinx](https://doflinx.github.io/docs/) shows the score and effects on the Pixelcade marquee while a game runs. It is closed source and large (about 230 MB to download), so it is a separate extra: **Setup > Games > Extras > DOFLinx**, after Pixelcade. It follows Pixelcade's own setup, which covers the **FBNeo** arcade games in RetroArch.

- **What is installed**: the Linux program from DOFLinx's GitHub ([DOFLinx/CurrentExecutable](https://github.com/DOFLinx/CurrentExecutable)) into `~/doflinx`, the `DOFLinx.ini` and `colours.ini` that Pixelcade publishes, with FliperOS's folders, in `~/doflinx/config`, and the per-game files, which `pixelweb -update-doflinx` downloads into `~/pixelcade/DOFLinx`.

  If you change `DOFLinx.ini`, a later install keeps your file and saves the new one as `DOFLinx.ini.latest`.
- **RetroArch**: DOFLinx finds the running game and reads its memory through RetroArch's Network Command Interface. The install writes `/etc/fliperos/retroarch/doflinx.cfg` (`network_cmd_enable`, port 55355), which `fliperos-kms-run` adds to RetroArch. Without DOFLinx the interface stays off.
- **Service**: `fliperos-doflinx.service` runs it as the `fliperos` user after `pixelweb` answers.
- It has not been tested with a marquee yet.

## ZeDMD (open-source LED display)

[ZeDMD](https://github.com/PPUC/ZeDMD) is an open-source LED display you can build yourself: an ESP32 board driving HUB75 LED panels, 128x32 (two 64x32 panels) or 256x64. **Setup > Games > Extras > ZeDMD** installs support for it.

**It needs ZeDMD firmware 5.1.0 or newer.** Older firmware, like the one that works on Batocera 41, doesn't connect to FliperOS. [ZeDMD firmware version](#zedmd-firmware-version) says how to check yours and how to update it.

The display gets the same events as the Pixelcade marquee: the game selected in ES-DE or Attract-Mode Plus, the system selected in ES-DE, the game opened from any frontend or emulator (with the high scores or "Now Playing" scrolling first), the game closed, the screensaver, the RetroAchievements and "Bye" at shutdown.

Pixelcade and ZeDMD can be installed together. The high scores need hi2txt and Java, which come with Extras > Pixelcade.

- **What is installed**: `dmdserver` from [libdmdutil](https://github.com/vpinball/libdmdutil) (the Visual Pinball DMD library, pinned version and hash) into `~/zedmd`, and the `python3-pil` package. Neither is in the image.
- **Service**: `fliperos-zedmd.service` runs `dmdserver` as the `fliperos` user, listening on `127.0.0.1:6789`.

  The udev rule (`99-fliperos-zedmd.rules`) names the ESP32's USB serial adapter `/dev/zedmd` and starts the service when it is plugged in (CP210x `10c4:ea60`, CH340 `1a86:7523`, CH9102 `1a86:55d4`, ESP32-S3 native USB `303a:1001`). With another adapter, `dmdserver` searches every USB serial port. If no ZeDMD is found, the service tries 3 times and then stops until one is plugged in.
- **What it shows**: `fliperos-dmd` sends a 128x32 picture (`dmdserver` scales it up for a 256x64 panel).

  It looks in `~/media` in this order: `dmd/<games folder>/<rom>.png` or `.gif` (`dmd/mame/sf2.gif`; the same folders as `~/roms`) (art made for the display; GIFs play animated), then the scraped `marquee` and `logo` images (**Setup > Games > Scraper**).

  Without any picture it shows the game's name, taken from the Attract-Mode or ES-DE game list. A name that doesn't fit in one line keeps scrolling in big letters until the next event, like an LED sign; the web panel's marquee preview and the OBS page do the same. A system picture goes in `~/media/dmd/<system>.png`.
- **Screensaver and startup**: when the service starts, and whenever the frontend is idle, the display plays a looping 3D vector animation in two flat colors (cyan and magenta) on black, with 1-pixel lines: the screen opens like a CRT, the camera dives through a wireframe tunnel with spinning wireframe cubes, and out of a flash of light the FliperOS letters appear as extruded line art, each one spinning like a coin while it is drawn, over a scrolling floor. The word sways, a scan line swaps the two colors, it makes a full turn to show its depth, and it flies back into the distance as the screen closes. It goes on until the next game or system event. `tools/zedmd-vector-anim.py` renders it (`config/zedmd-fliperos.gif`, 128x32, 8 seconds).

  **Idle** means 30 seconds without pressing a button in the FliperOS frontend (`FLIPEROS_IDLE_SECONDS`, 0 turns it off). The first press brings back the logo of the selected system. ES-DE and Attract-Mode Plus start the same animation with their own screensaver timers. The pictures in `~/media/dmd` and `~/media/marquee` are no longer cycled; `fliperos-dmd attract art` still does it.
- **Artwork**: Pixelcade's artwork is licensed only for Pixelcade hardware, so FliperOS doesn't use it on the ZeDMD.

### ZeDMD firmware version

FliperOS talks to the display through `dmdserver` from libdmdutil 0.11.0, which brings libzedmd 0.10. That library only understands **ZeDMD firmware 5.1.0 or newer**. The newest release is [5.1.8](https://github.com/PPUC/ZeDMD/releases/latest).

The firmware changed its USB handshake twice, and each time the new library stopped talking to the older firmware:

| Firmware | Works with FliperOS |
| --- | --- |
| 3.x and 4.x | **No.** 3.6.0 was tried on a user's cabinet: it never answers |
| 5.0.x | **No.** Its handshake reply is shorter than libzedmd 0.10 expects (read from the code, not tried) |
| 5.1.0 and newer | **Yes.** 5.1.8 was tried on the same cabinet: a 128x32 ESP32 board with a CH340 USB adapter |

**Coming from Batocera.** Batocera 41 has an older libzedmd, which still talks to firmware before 5.1. Batocera 42 and 43 have the new one, like FliperOS: the ZeDMD 5.1.0 release notes told Batocera users to wait for Batocera 42.

So a ZeDMD that works on Batocera 41 but not on 42 or 43 has old firmware, and FliperOS won't see it either until it is updated. After the update it no longer works on Batocera 41.

**Seeing the version.** The display shows it at the bottom right of its logo when it powers on (every version does). Once it connects, the service log has it too: `journalctl -u fliperos-zedmd` shows `ZeDMD 5.1.8 found: device=/dev/zedmd, width=128, height=32`.

**What old firmware looks like.** The display stays on its logo. The log shows `ZeDMD handshake response error, result: 0`, then `Unable to connect to ZeDMD on /dev/zedmd` and `No DMD displays found`, three times, and the service stops.

A ZeDMD 5.x gives the same messages while its settings menu is open: it only talks over USB after **Exit** in that menu.

### Updating the ZeDMD firmware

FliperOS doesn't update the display by itself. It is done once, from FliperOS or from a PC.

1. From the [latest ZeDMD release](https://github.com/PPUC/ZeDMD/releases/latest), download the zip for your board and panels. `ZeDMD-128x32.zip` is for an ESP32 with two 64x32 panels, `ZeDMD-256x64.zip` for HD, `ZeDMD-128x64.zip` for a single 128x64 panel, and the `ZeDMD-S3-N16R8_…` ones for an ESP32-S3 N16R8. The [ZeDMD README](https://github.com/PPUC/ZeDMD#flashing-the-firmware) describes each one.

   The zip has `ZeDMD.bin`: the firmware and its files in one image, written at address 0.
2. On FliperOS, in a terminal (SSH, or the web panel's Terminal), with the display plugged in:

   ```
   sudo systemctl stop fliperos-zedmd
   sudo apt install esptool
   esptool --chip esp32 --port /dev/zedmd -b 460800 --no-stub write_flash 0x0 ZeDMD.bin
   ```

   Ubuntu's esptool comes without esptool's helper program (the "stub"), hence `--no-stub`: the ESP32's own ROM writes the flash. It takes about 2 minutes and ends with `Hash of data verified`. For an ESP32-S3 the chip is `esp32s3`.

   From a Windows PC, the ZeDMD project's [ZeDMD_Updater2](https://github.com/zesinger/ZeDMD_Updater2) does the same.
3. On the first start after the update the display opens its settings menu, and it doesn't talk over USB while the menu is open. Set **RGB Order** until the top left shows red as red, green as green and blue as blue, then pick **Exit**. Without buttons, unplugging the display and plugging it back also leaves the menu.

   The update doesn't keep the old RGB order and brightness.
4. Start the service again, since it gave up after its 3 tries: `sudo systemctl reset-failed fliperos-zedmd`, then `sudo systemctl start fliperos-zedmd`. The log should show `ZeDMD 5.1.8 found`.

**Two warnings in the log are normal.** With 5.1.8 on the original ESP32 the log says `The ZeDMD USB package size of 32 is a very low value` and `The ZeDMD panel minimal refresh rate of 30 is a very low value`. Those are the firmware's defaults, and pictures and scrolling text are fine with them.

If animations stutter, the ZeDMD README suggests a USB package size of 512 for the original ESP32 (`USB packet size` in the display's menu).

**Keeping the old firmware.** To go back to it later (to use the display on Batocera 41 again), save the flash before updating. Ubuntu's esptool can't do it: with `--no-stub`, `read_flash` stops at 2 MB with `CRC or checksum was invalid`, because in that mode it doesn't tell the ROM the flash size.

Espressif's own esptool, which has the stub (`pipx install esptool`, or its [releases](https://github.com/espressif/esptool/releases)), reads the whole flash with `esptool --chip esp32 --port /dev/zedmd read_flash 0 ALL zedmd-backup.bin` (not tried here). It goes back the same way as the update: `write_flash 0x0 zedmd-backup.bin`.

## Versus score on the LED display

During a two-player match the display shows the score: the matches each side has won since the game opened. On a ZeDMD the score stays on the display (`GUILE 3 x 1 KEN`, with each side's character when the game tells it, or `P1` and `P2`).

On a Pixelcade a text scrolls each time someone wins a match, and then the game's marquee comes back. The score appears with the first win: until then (the game's demo, the character select, the first match) the display keeps the game's picture.

It works in **GroovyMAME**, for about 200 arcade ROM sets, and in **RetroArch with the FBNeo core**, for about 100: the ones [Fightcade](https://www.fightcade.com) has a detector for. The full list is in [Scoreboard games](Scoreboard-games.md).

What was checked on a FliperOS cabinet, with Fightcade's own detectors and no picture on the tube:

- **GroovyMAME**: Street Fighter II' Champion Edition, The King of Fighters '98, Mortal Kombat II and Street Fighter III 3rd Strike, one of each kind of detector, played by a script. The wins of both players and the characters came out right, and so did the 128x32 picture sent to the display.
- **RetroArch (FBNeo)**: Street Fighter II' CE, KOF '98 and 3rd Strike left in their demo. The memory the detectors describe was read right (the match start and the characters). No match was played there, because nothing can press the buttons of a RetroArch without picture, so a win has not been seen counted in RetroArch.
- A real LED display (ZeDMD or Pixelcade) showing the score has not been seen yet.

- **Where the score comes from**: the game only draws it on the screen, so it is read from the game's memory. The map is [Fightcade's detectors](https://github.com/fightcadeorg/fightcade-detectors), one file per game saying where a match starts, where each side wins and which character each side chose.

  It is the map Fightcade uses to know who won each online match. Its repository has no license, so the files aren't in the image: Extras > Pixelcade and Extras > ZeDMD download them (a pinned version) into `~/.local/share/fliperos/versus-detectors`. `fliperos-versus fetch` downloads them again. The repository keeps a reference copy of the same version in [`third-party/fightcade-detectors`](https://github.com/juniorterin/fliperOS/tree/main/third-party/fightcade-detectors) (not installed by anything).
- **Which games**: the CPS1 and CPS2 games (Street Fighter II, Alpha 3, Marvel vs. Capcom...), the Neo Geo ones (The King of Fighters, Garou, Samurai Shodown...) the CPS3 ones (Street Fighter III, JoJo, Red Earth) and the ones whose detector uses the CPU's own addresses (Mortal Kombat II and many others; these only in GroovyMAME). A clone uses its parent's detector.
- **How it is read**: for a game with a detector, the `groovymame` command turns on the `fliperos-versus` plugin.

  The plugin evaluates the detector every frame, the way Fightcade's emulator does (a condition counts after 30 frames in a row), and writes the result (`fliperos_wins1`, `fliperos_wins2`, `fliperos_char1`, `fliperos_char2`) to a file in the session's runtime folder, which `fliperos-versus` follows.

  These are not MAME outputs and don't go through port 8000: in today's MAME a script can't create new outputs, only use the ones the game declares.
- **Points**: the detectors don't have each player's points. For those there is `/etc/fliperos/versus-games.conf`, a table of addresses read directly (the format is explained at its top; your own lines go in `~/config/versus-games.conf`). It is empty for now, so the display shows the wins only. When a game has its points there, they appear below the wins.
- **RetroArch**: with the **FBNeo** core, the emulator the detectors were written for.

  `fliperos-kms-run` turns on RetroArch's Network Command Interface for a game with a detector (`/etc/fliperos/retroarch/versus.cfg`), and `fliperos-versus` reads the game's memory ten times a second (`READ_CORE_RAM`) and evaluates the detector itself.

  It covers the CPS1, CPS2, Neo Geo and CPS3 games; a detector that uses the CPU's own addresses can't be read there. The MAME cores (`mame2010`, `mame`) don't let the memory be read, so there is no score in them: use GroovyMAME or FBNeo for those games.
- **The FBNeo core** comes in the image from 0.9.1. On an installed system, get it in RetroArch: *Online Updater > Core Downloader > Arcade (FinalBurn Neo)*. Its games go in `~/roms/retroarch/fbneo`, in FBNeo's own ROM sets.

  The Fightcade ROMs (`~/roms/fightcade`) are Fightcade's alone: the frontends don't list them, and the core's folder is not linked to them (an earlier FliperOS made that link by itself; it is removed at the next boot, and the folder is empty again).

  To play a set in the core, copy it to `~/roms/retroarch/fbneo`; a set that changed between Fightcade's FBNeo 0.2.97.44 and the current core may not open in the core.
- **Console sets in the FBNeo folder.** The core only looks for a `.zip` among the arcade sets, unless the folder it is in has the name of a system (`megadrive`, `sms`, `nes`, `pce`, `tg16`, `sgx`, `msx`, `coleco`, `sg1000`, `gamegear`, `spectrum`, `fds`, `snes`, `ngp`, `channelf`); a Mega Drive game loose among the arcade sets closed with *romset is unknown*.

  Fightcade ROM packs often come like that, with every system in one folder.

  FliperOS finds the system of each set in FBNeo's own lists (`/opt/fliperos/bin/fliperos-fbneo`; a name that exists in more than one system is settled by the CRCs inside the `.zip`) and opens the game through a link in `~/.cache/fliperos-fbneo/<system>/`, with its parent set and the system BIOS (`spectrum.zip`, `msx.zip`, `coleco.zip`...) linked next to it, so nothing has to be moved.

  This happens when a frontend or the Games menu opens the game; a set loaded by hand in RetroArch's own menu still has to be in a system folder. A set that is in none of FBNeo's current lists still shows *romset is unknown*.
- **Model 2 (SM2-Emu)**: for Virtua Fighter 2, Fighting Vipers, Sonic the Fighters, Last Bronx and Dead or Alive, the emulator itself reads the memory, with FliperOS's patch, and publishes the rounds each side has taken among the game's outputs (`P1_Wins`, `P2_Wins` on TCP port 8000, see [DIY hardware](DIY-hardware.md#model-2-game-outputs)).

  With a display installed, `fliperos-x11-run` turns that port on for these games and `fliperos-versus` follows it. A match is counted for the side with more rounds when they go back to zero, which the game does when the next match starts, so the win appears then; there are no characters.

  Checked with the real emulator up to the rounds arriving and with a scripted feed for the count; not seen in a match on a cabinet. `fliperos-versus watch model2 <game>` shows the values.
- **Sides**: `versus_side=2` in `/etc/fliperos/fliperos.conf` puts player 2 first, for the cabinet on that side.
- **Checking a game**: open it and run `fliperos-versus watch mame <game>` over SSH: it prints the wins and the characters as they change, to compare with the screen.
- The count starts again when the game closes. Only with a Pixelcade or a ZeDMD installed; without one, nothing is turned on.

## APT repository

Attract-Mode Plus comes from a dedicated APT repository of prebuilt `.deb`s, like GroovyArcade's `groovy-ux-repo` (`packaging/build-deb.sh`, `packaging/make-repo.sh`, `Dockerfile.packages`, recipes in `packaging/packages/`). The build carries the repository into the image (`/opt/fliperos/repo`, `deb [trusted=yes] file:/opt/fliperos/repo ./`, option `--repo`) and already installs Attract-Mode Plus; without it, the cabinet's apt said "Unable to locate package".

The `config/fliperos-sessions.conf` table says, for each launcher, whether it runs in KMS or X (from galauncher's `videodata.conf` table) and which package it comes from.

## EmulationStation and Pegasus: built on the cabinet

ES-DE and Pegasus are **not** in the image or in its repository. The first time you choose one in Setup > Games > Frontend, the Setup says it will be built on that machine and asks for confirmation. It needs the internet.

What happens (`config/fliperos-frontend-build`, installed as `/opt/fliperos/bin/fliperos-emulationstation` and `fliperos-pegasus`; the name picks the recipe):

1. It installs the build tools of the recipe (`packaging/packages/<package>.sh`, the same recipe the CI uses, kept in `/usr/local/share/fliperos/packaging`).
2. `build-deb.sh` downloads the official source at the pinned version, **applies FliperOS's patches** (ES-DE: the 2x horizontal stretch in `packaging/patches/emulationstation`; Pegasus: its own KMS patch) and compiles.
3. The `.deb` is installed with apt, which brings the runtime libraries from Ubuntu.
4. The build tools that were not on the system before are removed.

**ES-DE needs OpenGL 3.3 or OpenGL ES 3.0.** A card that gives less (an Intel HD of the first generation has OpenGL 2.1 and ES 2.0) can't open it: the Frontend screen marks it with a red X and the reason, asks before choosing it, and the installer refuses to build it (`fliperos-emulationstation unsupported` prints the reason). See [Video cards](Video-cards.md#limits-of-the-intel-hd).

Everything the build prints goes to `/var/log/<package>-build.log`. It needs about 4 GB free in `/var/tmp`. Choosing the frontend again rebuilds it. A recipe marked `PKG_ON_DEMAND=1` is left out of `build-deb.sh --list-iso`, which is the list the CI builds for the image.
