## The FliperOS frontend

The default since 2026-10-23: the game list in the look of the Setup menu (Press Start 2P, Dracula colours, the animated background), drawn at 320x240 and stretched to the screen mode. It ships in the image (`fliperos-setup/gui/fliperos-frontend`, Python and pygame) and is the `fliperos` row of the session table.

It shows the same thing as the [Web panel](Web-panel.md), from the same code:
- the games of each folder, from the Attract-Mode Plus romlists. The arcade ones carry the name, year, manufacturer, clones and category from MAME's XML (the AttractPlus ROM List, `fliperos-romclean romlist`);
- the game filters the Setup writes into every Attract-Mode display (`fliperos-setup --filters`), plus Favourites;
- FliperOS's own favourites (`~/.config/fliperos/favourites`) and the game information saved in `~/media/info`.

**The lists follow the folders.** When the frontend opens, and whenever a games folder changes (games copied over the network or from a USB disk), it asks the Setup to redo the lists in the background (`fliperos-setup --romlists`). New arcade sets get their MAME names right away: when MAME's list is not cached yet, GroovyMAME's `-listxml` is read once (about a minute).

**Three views** (Start switches them):
- **List**: the games on the left, the picture, logo and information on the right. A game with clones has a "+" on its left: button 1 unfolds the clones under it, each with what differs in its name (the region, the set, bootleg).
- **Full screen**: the game's video or picture behind, the name and information in front, and on the right the list as four stacked thumbnails, with arrows above and below while there are more games that way; the column slides to its new place. The pictures of the games around the cursor are read ahead, so changing game is instant.
- **Grid**: three thumbnails a row, two rows, the chosen one bigger: 4:3 with the game's screenshot (or its cover), 3:4 when Video Setup has the monitor vertical. A scrollbar in the corner, with a small arrow above and below it while there are more rows that way.

**The game's video.** In the list and in full screen, the game's video (`~/media/preview/<folder>/<set>.mp4`) plays with its sound, half a second after the cursor stops on it; without a video, its picture shows. In any view, a game missing some of its art (screenshot, cover, marquee, logo or video) gets the missing pieces scraped by itself when the cursor stays on it for 2 seconds, once per game; they land in the same `~/media` folders the scraper uses. The logo comes from the Arcade Database too (its "decals"); what it lacks comes one file at a time from the archive.org packs of Setup > Games > Scraper > Art packs by torrent, without downloading the pack.

**Automatic scrape.** While the frontend is open, it fetches in the background, one game at a time, what each game in the folders still lacks:
- arcade: the information, screenshot, flyer, marquee and logo from the Arcade Database;
- consoles: the cover and screenshot from libretro-thumbnails;
- videos and the logos still missing: the torrent packs of Setup > Games > Scraper > Art packs by torrent, only the files of the games you have (`fliperos-setup --mediapacks auto`, checked every 6 hours). A pack that keeps its files in one .zip per letter (the MAME videos) would download whole letters, gigabytes for a few videos: it stays out of the torrent, and the frontend fetches each file from inside the zip over HTTP instead.

It pauses while a game is open. A game is tried once every 30 days (what a source does not have stays missing): `~/.local/share/fliperos/scrape-state.json`. Tab > Frontend options shows a progress bar, how many games are left and the torrents' progress.

Genre, controls and buttons show with Arcadeflow's icons when Arcadeflow has been downloaded (it can't ship in the image). In the list they come without text, in two rows: the genre with the number of players beside it, then the control (a pistol for light-gun games, which Arcadeflow has no icon for) with the buttons.

**Controls.** A guide shows them each time the frontend opens; any button closes it.
- Up and down move through the games; past the last one comes the first again, and before the first the last (holding stops at the end, the next press goes around). Holding speeds up, and after 3 seconds the letter mode starts: the letter big in the middle of the screen, the cursor jumping from letter to letter (slowly at first, faster after a short hold).
  - The letter mode stays after letting go: each tap of up or down moves one letter.
  - Two seconds without touching anything (or any other button) end it, on the first game of that letter.
- Left and right change the romlist (each games folder, and Arcade with all the arcade folders together); the screen slides to the new one. In the grid they move through it, and change the romlist only when the chosen game already touches that side; a tab on the edge names the next one.
- Button 1 opens the game's menu: Play, Favourite and "+". The "+" page has the game's information from the Arcade Database, saved on the cabinet.
- Button 2 goes back; from the list, it asks whether to return to the FliperOS menu.
- Buttons 3 and 6 move a page up and down. Button 4 marks or unmarks the favourite. Button 5 opens the filters.
- Tab (keyboard) opens the game options:
  - Classify: genre, players, buttons, control, year, maker, rotation and series, saved in `~/media/info/<folder>/<set>.user.json`; the filters use them;
  - Rename, with an on-screen keyboard;
  - Scrape this game: its information, pictures, logo and video, right away;
  - Delete this game: after a YES/NO question, its file goes away from the folder (for MAME, also the CHD folder of the same name); its art in `~/media` stays. A clone kept inside its parent's zip has no file of its own to delete.

  Under a line come the **frontend options**: the view mode (list, full screen or grid), changed with left and right and saved at once. Start also switches it.

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
- **Game closed**: the helper waits for the game to end and then shows the game's marquee the way the frontend selection does. That matters in Pegasus and RetroFE, which don't report what is selected.
- **Game selected**: in **ES-DE**, through its custom event scripts (`~/ES-DE/scripts/game-select` and `system-select`, with *Custom event scripts* and *Browsing custom events* turned on; browsing doesn't wait for them).

  In **Attract-Mode Plus**, through FliperOS's *Pixelcade* plugin, which is copied to `~/.attract/plugins` and turned on in `plugins.cfg`. Pegasus and RetroFE have no event hooks, so they only show the game that was opened.

  The service writes these frontend settings at every boot; if the frontend is open at that moment, they wait for the next boot.
- **Screensaver**: when the screensaver of ES-DE (`screensaver-start` and `screensaver-end` scripts) or Attract-Mode Plus starts, the marquee goes into Pixelcade's attract mode, a playlist you set up on the settings page. When it ends, the marquee shows the selected game or system again.
- **Achievements**: with RetroAchievements turned on in RetroArch (`cheevos_enable = "true"`), each unlocked achievement shows on the marquee, and then the game's marquee comes back.

  RetroArch has no event for this, so `fliperos-kms-run` opens it with `--verbose` and the helper reads the `[RCHEEVOS] Awarding achievement` lines from `/opt/fliperos/logs/retroarch.log`. In debug mode the log goes to the screen and no achievement is shown.
- **Pixelcade LCD over USB**: the LCD marquee (USB ID `1d6b:3232`, firmware 6.3 or newer) appears as a network card.

  The udev rule keeps it out of NetworkManager and starts `fliperos-pixelcade-lcd@<interface>.service`, which gives the card the address `169.254.100.2` (the LCD is `169.254.100.1`), sets `lcdMarquee` and `lcdUsbConnected` in `~/pixelcade/pixelcade.ini`, writes the LCD's name there and restarts the service. This is what Pixelcade's installer does; it has not been tested with an LCD marquee yet.
- **Visual Pinball**: a program whose name starts with `vpinball` draws the display itself, over the same serial port. When it opens, `pixelweb` (and `dmdserver`) close and let go of the port; when it ends, the services open them again. FliperOS doesn't ship Visual Pinball.
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

The display gets the same events as the Pixelcade marquee: the game selected in ES-DE or Attract-Mode Plus, the system selected in ES-DE, the game opened from any frontend or emulator (with the high scores or "Now Playing" scrolling first), the game closed, the screensaver, the RetroAchievements and "Bye" at shutdown.

Pixelcade and ZeDMD can be installed together. The high scores need hi2txt and Java, which come with Extras > Pixelcade.

- **What is installed**: `dmdserver` from [libdmdutil](https://github.com/vpinball/libdmdutil) (the Visual Pinball DMD library, pinned version and hash) into `~/zedmd`, and the `python3-pil` package. Neither is in the image.
- **Service**: `fliperos-zedmd.service` runs `dmdserver` as the `fliperos` user, listening on `127.0.0.1:6789`.

  The udev rule (`99-fliperos-zedmd.rules`) names the ESP32's USB serial adapter `/dev/zedmd` and starts the service when it is plugged in (CP210x `10c4:ea60`, CH340 `1a86:7523`, CH9102 `1a86:55d4`, ESP32-S3 native USB `303a:1001`). With another adapter, `dmdserver` searches every USB serial port. If no ZeDMD is found, the service tries 3 times and then stops until one is plugged in.
- **What it shows**: `fliperos-dmd` sends a 128x32 picture (`dmdserver` scales it up for a 256x64 panel).

  It looks in `~/media` in this order: `dmd/<games folder>/<rom>.png` or `.gif` (`dmd/mame/sf2.gif`; the same folders as `~/roms`) (art made for the display; GIFs play animated), then the scraped `marquee` and `logo` images (**Setup > Games > Scraper**).

  Without any picture it shows the game's name, taken from the Attract-Mode or ES-DE game list, scrolling when it doesn't fit. A system picture goes in `~/media/dmd/<system>.png`.
- **Screensaver and startup**: during the frontend's screensaver the display cycles through the pictures in `~/media/dmd` and `~/media/marquee`, in random order, 8 seconds each. When the service starts it shows the FliperOS logo.
- **Artwork**: Pixelcade's artwork is licensed only for Pixelcade hardware, so FliperOS doesn't use it on the ZeDMD.

## Versus score on the LED display

During a two-player match the display shows the score: the matches each side has won since the game opened. On a ZeDMD the score stays on the display (`GUILE 3 x 1 KEN`, with each side's character when the game tells it, or `P1` and `P2`).

On a Pixelcade a text scrolls each time someone wins a match, and then the game's marquee comes back. The score appears with the first win: until then (the game's demo, the character select, the first match) the display keeps the game's picture.

It works in **GroovyMAME**, for about 200 arcade ROM sets, and in **RetroArch with the FBNeo core**, for about 100: the ones [Fightcade](https://www.fightcade.com) has a detector for. The full list is in [Scoreboard games](Scoreboard-games.md).

What was checked on a FliperOS cabinet, with Fightcade's own detectors and no picture on the tube:

- **GroovyMAME**: Street Fighter II' Champion Edition, The King of Fighters '98, Mortal Kombat II and Street Fighter III 3rd Strike, one of each kind of detector, played by a script. The wins of both players and the characters came out right, and so did the 128x32 picture sent to the display.
- **RetroArch (FBNeo)**: Street Fighter II' CE, KOF '98 and 3rd Strike left in their demo. The memory the detectors describe was read right (the match start and the characters). No match was played there, because nothing can press the buttons of a RetroArch without picture, so a win has not been seen counted in RetroArch.
- A real LED display (ZeDMD or Pixelcade) showing the score has not been seen yet.

- **Where the score comes from**: the game only draws it on the screen, so it is read from the game's memory. The map is [Fightcade's detectors](https://github.com/fightcadeorg/fightcade-detectors), one file per game saying where a match starts, where each side wins and which character each side chose.

  It is the map Fightcade uses to know who won each online match. Its repository has no license, so the files aren't in the image: Extras > Pixelcade and Extras > ZeDMD download them (a pinned version) into `~/.local/share/fliperos/versus-detectors`. `fliperos-versus fetch` downloads them again.
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

The frontends (Attract-Mode Plus, EmulationStation, RetroFE, Pegasus) come from a dedicated APT repository of prebuilt `.deb`s, like GroovyArcade's `groovy-ux-repo` (`packaging/build-deb.sh`, `packaging/make-repo.sh`, `Dockerfile.packages`, recipes in `packaging/packages/`).

The `config/fliperos-sessions.conf` table says, for each launcher, whether it runs in KMS or X (from galauncher's `videodata.conf` table) and which package it comes from.

The build carries the repository into the image (`/opt/fliperos/repo`, `deb [trusted=yes] file:/opt/fliperos/repo ./`, option `--repo`) and already installs Attract-Mode Plus; without it, the cabinet's apt said "Unable to locate package".

Attract-Mode Plus, EmulationStation (ES-DE) and Pegasus have recipes; RetroFE doesn't yet, and shows in Setup > Games > Frontend as *not available yet*.
