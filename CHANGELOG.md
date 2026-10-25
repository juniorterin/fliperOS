# Changelog

What changed in each ISO published in [Releases](https://github.com/juniorterin/fliperOS/releases), in the format of GroovyArcade's releases. Each version's section is the text of its release: `tools/release-publish.sh` doesn't publish an ISO without its section.

## 0.12

NVIDIA cards with VGA or DVI-I can now show native 15 kHz resolutions: FliperOS's own kernel patch lets the open driver (nouveau) take the low clocks, and the output test checks each card with a 320x240 grid before using them. Cards that don't pass keep the super resolutions. The new Video cards page of the wiki lists which AMD, NVIDIA and Intel cards work and what each one gives. The first boot of an installed system already installs and turns on the web panel's Live screen. Art packs that stopped when the cabinet was turned off now continue where they were, and the Auto scrape panel says which system each pack is for (MAME logos, MAME videos). The NVIDIA path has not been seen on a real NVIDIA card yet.

**System changes:**

- **15 kHz kernel**: patch 10 (FliperOS's own) removes nouveau's 25 MHz floor on analog outputs (VGA, DVI-I), so NVIDIA cards from the GeForce 8 to the GTX 900 can boot at `640x480iS` and run each game at its native resolution
- The frontend: switching between list, grid and full screen stays on the same game, clones too; clones with a name of their own (hacks, bootlegs) show the whole title in the list, and the selected title scrolls in a loop instead of wrapping
- Art packs: a torrent stuck with no peers comes by HTTP straight from archive.org; a pack interrupted by a reboot continues from the file it was on instead of starting over

**Package changes:**

- go2rtc (the Live screen) is downloaded by the first boot of the installed system, a pinned version checked by sha256; it still isn't in the image

**fliperos-setup changes:**

- The video output test shows a 320x240 grid on NVIDIA cards with an analog output: seen, native resolutions; not seen, super resolutions. Video Setup > Low resolutions repeats it
- The installer lists the HD/SSDs as a vertical text list (device, size, type and model)
- The first boot installs and turns on the Live screen of the web panel (it offers Wi-Fi when there is no internet)
- The Auto scrape panel names the system of each art pack: MAME LOGOS, MAME VIDEOS, NAOMI LOGOS...

**Tool changes:**

- `fliperos-mediapacks resume` and `fliperos-setup --mediapacks resume` continue the art packs in progress; the automatic scrape calls them when a pack is stopped

**Documentation:**

- New wiki page: Video cards, the list of supported AMD, NVIDIA and Intel cards

## 0.11

FliperOS has a frontend of its own, and it is the default: game lists made by FliperOS itself (Attract-Mode and ES-DE are optional), a grid and a full-screen view with each game's video, and a scraper that fetches the missing art, logos, videos and info of every game by itself. The cabinet also has a web panel at http://fliperos.local: open and close games, see the screen live with sound, change settings mid-game, manage files, the ROM filter and the downloads from a phone. On a vertical monitor the frontend, the Setup menu, the boot screen and the terminal now stand upright. Updates show what they change before asking to apply, and after a new version or update the menu shows what's new once. The frontend and the web panel run on the cabinet; the vertical mode has not been seen on a CRT yet. An installed 0.10 gets all of this through updates 18 to 22. This ISO was rebuilt on 2026-10-25 with updates 19 to 22: a faster boot, a reboot without the 90 s wait, updates applied at power off, the installer in the graphical menu, an on-screen keyboard for the Wi-Fi password, MAME 2010 buttons pressed once (also on panels that show up as Xbox 360 pads), the automatic scrape running during games, the arcade videos by torrent one letter at a time, and hiding games and clones in the frontend.

**System changes:**

- **FliperOS frontend** (`fliperos-frontend`, the default session): the look of the Setup menu, a list, a grid of three per row (3:4 tiles on a vertical monitor) and a full-screen view with four thumbnails on the right. Every visible game plays its video, the videos around the cursor are loaded ahead, moves and list changes slide, the list wraps from the last game to the first, and each game list remembers where the cursor stopped. A button guide, clones grouped under their parent, and a Tab menu with Frontend options, favourites, filters and deleting a game. A loading screen replaces the black screen when it opens from the menu
- **Automatic scrape** in the frontend: what each game lacks (art, logo, video, description, players, buttons) comes from the Arcade Database, libretro-thumbnails and the Internet Archive art packs, torrents first and zip packs one file at a time. Tab > Frontend options shows the progress and how many games are left. A game left under the cursor for 2 s is scraped only when something is missing, once every 30 days
- **Game lists of FliperOS's own** (`~/.local/share/fliperos/lists`), with the real names from MAME, the real buttons of each arcade game (Controls.dat and Flycast's table) and Naomi, Naomi 2 and Atomiswave split by BIOS. Attract-Mode and ES-DE get copies; favourites, filters and play statistics stay in FliperOS
- **Vertical monitor**: the frontend and the Setup menu lay out for a 3:4 screen, the boot screen (Plymouth) has upright art, and the terminal boots in 640x480i with an EDID of FliperOS's own (640x240 and 640x480i), so the console has room on its side
- **GroovyMAME** opens the game straight away: no warnings screen and no "Initializing" (a patch to the binary). Its sound goes through ALSA's default again
- **Web panel** at http://fliperos.local (port 8081): Status, Games (FliperOS's names, filters, info and favourites), Files, ROM filter, Downloads, Settings that save at once, Terminal, Screenshot, and **Live**: the screen in the browser through WebRTC with the game's sound, plus `/overlay/live` and `/overlay/marquee` pages for OBS
- The power button closes a game opened from the web panel instead of turning the cabinet off
- Disks without a label mount in `/media/fliperos` with the disk model's name
- The initramfs no longer carries nouveau and the NVIDIA firmware (104 MB less); the firmware stays in the system
- **What's new**: after a new version or update the FliperOS menu shows, once, the changelog of what came in. Setup > System > What's new shows it again
- **Updates show their changelog** (`updates/notes/NNNN.md`) before asking to apply, with scrolling, and *Read what changes* shows it again

**Package changes:**

- `ffmpeg` is in the image (the frontend's videos and the live screen)
- **DuckStation** (PlayStation) installs from Setup > Emulators & Games; its license does not allow it in the image
- RetroFE is no longer offered as a frontend, and the Model 2 Emulator (Wine) is gone: Model 2 is SM2-Emu only

**fliperos-setup changes:**

- Setup > Games > Scraper scrapes the same way as the frontend, with no account needed; the sites with login stay as an option
- Extras moved into Games, and each emulator has its own Update
- The graphical menu: a conventional scroll bar in lists, Video Setup > Resolution as a vertical list, one tap on the joystick moves one item, and the menu closes when the Setup dies with a menu on screen
- The Downloader takes a magnet link or a `.torrent` file
- Colour calibration changes live with a game open, and going back to the default resets everything
- The install media opens the graphical menu after the video output test, so installing is graphical too
- Everything that downloads checks the internet first and offers to connect to Wi-Fi; passwords have an on-screen keyboard for the joystick
- Scraper > Scrape the games and the automatic scrape go on in the background (a service, Setup > System > Services > Auto scrape), also during a game
- MAME 2010 reads each panel button once (only through the RetroPad), so Buttons layout works in it
- Video Setup > 480i games is now 480i hacks; the menu shows the network use, and its tiles stop at the ends

**Tool changes:**

- `fliperos-update notes` prints the changelog of the pending updates; `tools/make-update.sh` refuses to publish an update without `updates/notes/NNNN.md`
- New `fliperos-scrape` (the scraper of the frontend and the Setup) and `fliperos-web` (the web panel)
- `tools/cabinet-update.sh` rebuilds the flicker filter and `fliperos-color` when their source changes, and updates the frontends of the local repository

**Documentation:**

- New wiki page: Web panel. The paragraphs are shorter, and the BIOS come through Download BIOS
- The README presents FliperOS as an alternative to GroovyArcade, Batocera, Recalbox, ReplayOS and RGB-Pi

## 0.10

The Setup has a graphical interface: on the cabinet every menu is a carousel of big icons over an animated background (snow, water, fire, smoke, stars), and over SSH the same menus stay in text. Also new are a flicker filter for 480i, the choice of 640x240 or 480i for each program, colour calibration, a custom monitor range made on the geometry grid, and the choice between the radeon and amdgpu drivers on the AMD cards that work with both. The 0.9.1 ISO never got out (its build stopped on GitHub), so everything written for it below comes in this one. The amdgpu driver was seen working at 15 kHz on the cabinet's R7 240; the 480i filter and the colour calibration have not been seen on a CRT yet. An installed 0.9 already has updates 16 and 17; the rest of this list comes with this ISO.

The MAME ROM Cleaner works out of the box: `catver.ini`, `nplayers.ini` and `controls.xml` now ship in the image, so the categories, adult games, play mode and real button count filters show without copying anything. The 0.9 ISO left their folder empty. Also new are the versus scoreboard on the LED display for fighting games, the game outputs for light guns and button lights, and Arcadeflow as the Attract-Mode Plus theme. None of the scoreboard and outputs work has been tried with a real gun, LED board or two-player match on the tube. The ISO comes with updates 16 and 17 already applied; an installed 0.8.x or 0.9 gets the same changes through the updates at boot.

**System changes:**

- **Graphical Setup.** On the cabinet the FliperOS menu and the whole Setup open in a graphical interface (pygame, 320x240 stretched to the tube): menus as carousels of icons, the official icon of each program, the ROM filter as a board of tiles with the GAMES / SIZE count of what passes, the Button mapping panel and the Buttons layout drawn, the GunCon 2 calibration drawn with a target and the shots, and a new animated background each time the menu opens. On a vertical monitor the menu stands up with the tube. Over SSH, on the installation media or without KMS video the Setup is the text one, as before; `ui=text` in `fliperos.conf` keeps it in text
- **480i flicker filter**, like RePlayOS's: an OpenGL layer over every emulator and frontend (picom on the desktop) that softens the line flicker of 480i, in light, medium or strong
- **Video driver: radeon or amdgpu** on the AMD cards that work with both (GCN 1.0 and 1.1: HD 7000, R7/R9 200 and 300, like the R7 240), in Video Setup and in the installation. The Setup finds out from the kernel modules themselves whether the card has the choice. radeon is the recommended one and the default: 15 kHz was validated on it. amdgpu brings Vulkan, was seen working at 15 kHz on an R7 240, and goes in with `amdgpu.dc=0`, because the 6.18 kernel has no VGA/DVI-I output in amdgpu's new display code for these cards. Every switch is on trial: the next boot asks to confirm the picture with Enter within 15 s, and with no answer (no picture) it goes back to the previous driver and restarts by itself; a trial boot that hangs goes back at the next boot. With amdgpu set, the boot menu (a key during boot) also has a **FliperOS - radeon driver** entry. The first time the menu opens, a card running on the driver that is not the recommended one gets a popup offering the switch, once
- **Game mode**: with a game set to open at boot, it opens before everything else. The update check, the `~/roms` folders and the frontends' lists wait until the game closes, and the network is not waited for (on the cabinet the game took 56 s to open, 36 of them waiting for the network)
- **Volume leveler** (Audio Setup), off by default: a compressor in ALSA's `default`, where every emulator goes through, so loud and quiet systems come closer to the same volume, with no added delay
- **Flycast**: no loading screen (the screen stays black while the game loads; a loading error still shows), and Texture Filtering in Force Nearest, sharp pixels as on the board
- The NVIDIA firmware is back in the image: without it nouveau does not accelerate the newer cards
- Attract-Mode Plus: the joysticks come in the kernel's order. With two joysticks whose input numbers cross 9/10 (a split double encoder does), the frontend's Joy0 was the second player
- Attract-Mode Plus opens about 5 s sooner after the menu, and an arcade list is rebuilt only when its folder changes (it was redone at every opening)
- Arcadeflow in 640x240 is drawn for a 4:3 screen and stretched to the width: everything came out twice as wide. The context menu and the grouped clones work, opening a clone, and the clones of a merged romset are no longer marked unavailable
- A Wi-Fi network connected in the Setup looks for FliperOS updates right away; on a new install the update only showed at the next boot
- **GroovyMAME no longer closes at its game list.** The slimmed image came without `libX11.so`, `libXrandr.so` and `libdrm.so`, which Switchres opens by name, so no video mode was created. The build and the update put those names back
- **Scraper: art packs by torrent.** Setup > Games > Scraper > Art packs by torrent brings logos and videos from torrents, already filled with Internet Archive packs for MAME, Naomi, Atomiswave, Model 2 and Model 3. A pack only downloads when its folders have ROMs, and only the files of the games you have. Your own torrents can be added. On the cabinet only a test download was tried, not the screens on the tube
- **Scraper: choose the provider and log in.** Scraper provider picks ScreenScraper, TheGamesDB, ArcadeDB, progetto-SNAPS, MobyGames, IGDB or OpenRetro, and saves the account of the ones that ask (user and password, or API key). The ScreenScraper password used to be asked on every scrape
- **ROM Cleaner: the Naomi, Naomi 2 and Atomiswave games are filtered by the controls they really use.** MAME's XML gives nearly all of them the board's generic panel (an 8-way joystick and 6 buttons), so steering wheel, flight stick and light gun games passed as joystick games (Ferrari F355, Initial D, Club Kart, Ninja Assault...). Their controls and buttons now come from Flycast's own game table
- **The ROM Cleaner's data files are in the image**, in `/usr/local/share/fliperos/romclean`: `catver.ini` 0.289 (progetto-SNAPS), `nplayers.ini` 0.278 (NPlayers, CC BY-SA 3.0) and `controls.xml` 0.141.1 (Controls.dat). Files of your own in the romset folder, or in the one above it, are used instead. The AttractPlus ROM List gets its categories from the same `catver.ini`
- Downloader and MAME CHD Cleaner: from a game's CHD folder only the disks of the chosen versions are taken. In a merged CHD collection the parent's folder holds the disks of every version, and all of them were downloaded or copied
- **Versus scoreboard on the LED display.** In a fighting game, the Pixelcade or ZeDMD shows each side's character and the wins of the session. It works in about 200 games in GroovyMAME and 100 in RetroArch's FBNeo core, through Fightcade's detectors (downloaded by Extras > Pixelcade or ZeDMD, not in the image), and in the Sega Model 2 fighters. The list is in [Scoreboard games](https://github.com/juniorterin/fliperOS/wiki/Scoreboard-games)
- **Game outputs** (recoil, lamps, motors). GroovyMAME, Flycast, Supermodel and SM2-Emu publish them on port 8000, the MAMEHooker protocol, only while an outputs reader from Extras is installed
- **Setup > Joysticks > Buttons layout**: where the buttons of a game go on the panel, by how many buttons the game uses (1 to 5). A 4-button game can be 1 2 on top and 3 4 below, or 1 3 on top and 2 4 below. For GroovyMAME, RetroArch's MAME and MAME 2010 cores, Model 2 (SM2-Emu) and Model 3 (Supermodel). In Model 2 the panel's button N is now the game's button N; button 1 used to be on the bottom row Joysticks now comes right after Network Setup in the Setup
- Buttons layout in RetroArch's MAME 2010 core: Tekken 3 and the other games that MAME 0.139 numbers by the board's button block (1 2 4 5 of 6) keep their buttons in place. The layout of the 4-button games moved them, and one kick button did nothing
- **Setup > Emulators & Games**, after Frontend: the emulators of the desktop menu, each marked installed or not installed, and the installation of the ones that don't come in the image. Model 2 is downloaded and built from there, Fightcade 2 is downloaded, and **KOF Final Attack** is converted to Ikemen GO in 4:3 at 320x240 from the folder of the original game you bring, with the 4:3 patch. Splash screen is now the last item of the Setup
- **The cabinet's power button** closes the open game and returns to the frontend. In the frontend, the menu or the desktop it shuts down, as before
- When the session drops, the frontend closes with it. A frontend left running with no screen kept the sound card open, and GroovyMAME was silent in every game
- Fightcade at 15 kHz: the screen runs at the game's own refresh rate also for the games that stay in a table mode (vertical games, widths the modeline cannot make exact)

**Package changes:**

- RetroArch, Flycast and Dolphin are built with **Vulkan**, for the amdgpu driver. RetroArch's default stays glcore, and Flycast goes back to OpenGL while the 480i flicker filter is on. PCSX2 was seen running in Vulkan on the CRT with amdgpu (R7 240)
- An emulator no longer fails to open, with no message, when the colour calibration cannot be applied (another program holds the screen): the launchers go on without it
- ES-DE in 640x240 draws its interface in 4:3 (320x240) and stretches it 2x horizontally, so text and pictures keep their proportions on the tube (not yet seen on the CRT)
- RetroArch: the **FinalBurn Neo** core comes in the image
- RetroArch: one press of Esc closes the game. It asked for a second press with a notice that FliperOS keeps hidden
- RetroArch's FBNeo core opens the console sets (Mega Drive, Master System, ZX Spectrum and the like) that sit loose in the arcade folder
- ES-DE: RetroArch games open again; they closed in the same second with no error
- ES-DE: returning from a game no longer leaves the screen black, and the preview video no longer plays under the game
- ES-DE: Model 2, Model 3 and the MAME cores show their own logo in place of the arcade one
- Attract-Mode Plus: **Arcadeflow** is the default theme. Setup > Frontend downloads it (it has no license, so it is not in the image); without network the displays stay on Basic. The select button opens the game on the first press
- Attract-Mode Plus: Arcadeflow starts the video of the game under the selector sooner (the theme's "Video delay multiplier" at 0.25x: a quarter of a second in place of one before it loads the video)
- Attract-Mode Plus: in Arcadeflow's displays menu, the Supermodel display has the Sega Model 3 logo, and the MAME 2010 one is **MAME 2010**, with the MAME logo and picture and a tilted "2010" on them, apart from GroovyMAME's *MAME*. Every FliperOS display gets the logo of its system (GameCube for Dolphin, PlayStation for its RetroArch cores...); only the ones named like the system had it
- `~/media`: every type of art (`snap`, `preview`, `logo`, `box`, `marquee`, `dmd`, `texto`) has the same folders as `~/roms` (`mame`, `model2`, `naomi`, `retroarch/mame2010`...) in place of one per scraper platform (`arcade`, `snes`). Each games folder has its own art, and its own custom folder in Setup > Folders (`~/media/preview/model2` on another disk). What was in the platform folders is moved the next time the launcher opens; the other arcade folders still look in the `mame` one after their own
- Attract-Mode Plus: selecting games no longer leaves a zombie process behind each one
- Attract-Mode Plus: a game copied to a folder that already had its list shows up the next time the frontend opens, and a deleted one leaves. The list was made once and never looked at the folder again. An arcade list made by AttractPlus ROM List is still redone there
- SM2-Emu: FliperOS's patch adds recoil, ammo, life and credits to the outputs of the gun games (Virtua Cop, Virtua Cop 2, House of the Dead, Gunblade NY, Behind Enemy Lines, Rail Chase 2), credits to 21 games and each side's rounds to the fighters

**fliperos-setup changes:**

- **Video Setup > 480i games**: a table of every program (emulators, RetroArch cores, Fightcade, the desktop) where each one gets 640x240, 480i with the flicker filter at its own level, with a preview on the tube, or pure 480i. Saved as it changes
- **Video Setup > Colour calibration**: brightness, contrast, gamma, colour temperature, gain, black level and gamma for each gun, saturation and hue (by software on cards without a colour matrix, like the R7 240 on radeon) and the RGB range. Test patterns on the tube (colour bars, grey steps, black and white level, ColorChecker) or the numbers over SSH
- **Video Setup > Monitor Type > Custom**, right after Generic 15.7 kHz: the monitor's own range (`crt_range0`), made on the Geometry grid or typed, on top of the preset in use; choosing a preset undoes it. The Geometry grid no longer closes at the first arrow (it opens 8 pixels wider than the boot mode, like GroovyArcade's 648), and an error of the tool shows as an error, not as cancelled
- **Setup > System > Services**: SSH, the network share, `fliperos.local`, the Wi-Fi radio, the Downloader and *Wait for network*, each at boot, after boot (about 40 s later) or off. **Setup > System > Password** changes the `fliperos` password for login, SSH and the share
- **Setup > Games > Downloader > Download BIOS**: only the BIOS the games in each `~/roms` folder lack (from each RetroArch core's `.info`, MAME's XML for the arcade sets, and PCSX2's and Flycast's), file by file, from the Batocera 36 BIOS pack on the Internet Archive. It also checks by itself, in the background, each time the menu opens. Tried on the cabinet (the four PS1 BIOS, the PS2 one, Naomi and Neo-Geo); the screens were not seen on the CRT
- **Setup > Games > Custom games**: games and programs that are not a ROM (a PC game, your own emulator, a script), in groups the frontends show as systems, each with its video mode (240p, 480i or WIDTHxHEIGHT@HZ)
- **Setup > Games > Folders**: a custom folder for `~/roms`, `~/bios`, `~/media`, `~/splashscreen` or any folder inside them (an emulator, a RetroArch core, a type of art). It becomes a link to the folder chosen on a disk, and the one before stays beside it as `old-<name>`; nothing is copied or deleted
- **Button mapping**: *Keyboard encoder (MAME default keys)* writes MAME's keys of each player to RetroArch, GroovyMAME, Supermodel, Hypseus, Flycast and OpenBOR. The mapping also reaches Attract-Mode Plus, Flycast gets the hat D-pad (an Xbox 360 style controller had none) and the triggers, and a trigger saved inverted, which held a button down at rest in every emulator, is fixed, also in an old `buttons.map`. Fightcade's Dojo gets Flycast's video and control options
- Buttons layout in MAME with a keyboard: one key no longer presses two buttons when the layout moves them
- Downloader: switching the filter to another emulator no longer deletes the games the previous one brought (the Naomi and Atomiswave games left when the filter went to GroovyMAME)
- The ROM filter starts from the monitor's orientation: only horizontal games on a horizontal monitor, only vertical ones on a vertical monitor
- `fliperos-menu` typed over SSH opens the Setup in text there; frontends, games and the desktop open only from the cabinet
- Every Setup menu opens on its first item, and Games comes before Joysticks
- The progress screen fits the 15-line console of 640x240 (the Downloader scrolled the screen)
- **The Setup is grouped, in the order of setting up a cabinet**: Video Setup, Audio Setup, Network Setup, Joysticks, **Games** (Frontend, Emulators & Games, Folders, Downloader, Cleaner, Scraper, AttractPlus ROM List) and **System** (Extras, Latency, System Update, Debug mode, Splash screen). Quirks is inside Joysticks. It was one list of 17 items
- **Info balloons**: under the list, a balloon says what the item under the cursor is for, in the FliperOS menu, the Setup and its groups, Video, Audio and Network Setup, Joysticks and the Downloader. It needs the gum of this ISO: a system that came from an older ISO shows the same menus without the balloons
- MAME ROM Cleaner on a MAME 2010 romset: the Naomi and Atomiswave games the filter leaves out go with the rest. They were always kept (for Flycast, which can't read that romset) and showed up in the MAME 2010 list
- MAME ROM Cleaner and Downloader filter: *Data files* shows the three files that ship with FliperOS and their version
- AttractPlus ROM List: every folder with games gets its display, also one removed before; a folder left without games loses its display, and Arcadeflow reads a rebuilt list
- Extras: **Hook Of The Reaper** (through Wine), **QMamehook** (native, for serial-port guns) and **LEDSpicer** (button lights), the readers of the game outputs. None of them is in the image
- Extras > Pixelcade, with Pixelcade installed: update it, or install the paid art pack with the license code of the purchase
- The frontends no longer list Fightcade's whole ROM collection as FBNeo games

**Tool changes:**

- New `fliperos-color` (applies the colour calibration through DRM and in X) and `fliperos-gui` (the graphical Setup)
- New `fliperos-versus` (the scoreboard), `fliperos-outputs` (the outputs readers), `fliperos-arcadeflow`, `fliperos-fbneo` (the system of each FBNeo set) and `fliperos-powerkey`
- `tools/verify-iso.sh` checks that the three ROM Cleaner data files in the image are the repository's

**Documentation:**

- The wiki spells out the address, user and password for SSH, SFTP and the network share
- New page: [Scoreboard games](https://github.com/juniorterin/fliperOS/wiki/Scoreboard-games)
- ROMs page: where the ROM Cleaner's data files come from and how to use newer ones
- Website: the displays section (ZeDMD and the scoreboard) and a section on open hardware

## 0.9

Two or three arcade monitors: games made for several screens, such as Darius, Punch-Out!! and F355 Challenge, open each screen on its own tube. Also new is support for LED marquees, the Pixelcade and the open-source ZeDMD, which show the game you select and the game you open. The marquee support has not been tried on a real marquee yet. The ISO comes with updates 12 to 15 already applied; an installed 0.8.x gets those through the updates at boot, and the changes made after update 15 (the marquees, SM2-Emu 0.9.44, the Downloader fix) in a later update.

**System changes:**

- **Two or three CRTs.** A second and a third arcade monitor on the other analog outputs of the video card get the boot mode of the main one. Games with 2 or 3 screens open one screen per monitor, each in its own 15 kHz mode; everything else stays on monitor 1. Monitors on digital outputs (with an active converter) or on a second video card are also offered, as experimental
- **LED marquee (Pixelcade and ZeDMD).** The marquee shows the game selected in ES-DE or Attract-Mode Plus and the game opened from any frontend or emulator. When a game opens, its top three high scores (arcade games) or its name scroll once; when it closes, the marquee goes back to the selection. The frontend's screensaver puts the marquee in attract mode, RetroAchievements unlocked in RetroArch show on it, and it says "Bye" at shutdown
- Emulators fill the screen on Intel and NVIDIA cards. On a card without a low dot clock, Flycast came out narrow in the middle of the screen and Supermodel and Hypseus in a corner of it
- Downloader: changing the filter no longer deletes the BIOS (`neogeo.zip`, `qsound.zip` and the like) that games still in the folders need

**Package changes:**

- GroovyMAME: games with 2 or 3 screens (Darius, The Ninja Warriors, Punch-Out!!) get one window per monitor, also when the game is chosen in GroovyMAME's own list
- Flycast: the NAOMI multiboard games (F355 Challenge, Airline Pilots, Sega Strike Fighter) on three monitors
- SM2-Emu 0.9.44. Its project accepted FliperOS's five patches, so they are no longer applied here; Games > Model 2 updates the source before rebuilding
- RetroArch opens with `--verbose` when RetroAchievements are on and a marquee is installed, which is how an achievement reaches the marquee
- The Games menu shows the official icons of GroovyMAME, SM2-Emu and Fightcade

**fliperos-setup changes:**

- Video Setup > Multiple Monitors: *Monitor 2* and *Monitor 3* (which output each one uses), *Multi-Screen Games* (one screen per monitor, or everything on monitor 1), *Game Screen Order* and *Identify Monitors* (turns each monitor off for 3 seconds, in order)
- Extras: **Pixelcade** (downloads Pixelcade's closed-source software and artwork, hi2txt for the high scores and Java from apt), **ZeDMD** (the open-source `dmdserver` from libdmdutil) and **DOFLinx** (effects on the Pixelcade marquee during FBNeo arcade games). None of them is in the image
- Extras: choosing one that is already installed offers to download it again, which updates it
- The version shows next to "FliperOS" at the top of the Setup

**Tool changes:**

- New `fliperos-pixelcade` (the marquee events, the installs and the services) and `fliperos-dmd` (draws the 128x32 picture for the ZeDMD)
- New `fliperos-mame-screens` and `fliperos-multiscreen` (the multi-screen games in GroovyMAME and Flycast)
- udev rules that start the marquee service when a Pixelcade (LED, or LCD over USB) or a ZeDMD is plugged in

**Documentation:**

- New pages: [Multiple monitors](https://github.com/juniorterin/fliperOS/wiki/Multiple-Monitors) and [DIY hardware](https://github.com/juniorterin/fliperOS/wiki/DIY-hardware) (open-source projects to build with an Arduino, a Raspberry Pi Pico or an ESP32)
- Frontends page: the Pixelcade marquee, the ZeDMD and DOFLinx
- README: the menus explained item by item, and the LXDE desktop as the main way to copy games

## 0.8.3

Sega Model 2 on the tube: SM2-Emu replaces the Wine Model 2 Emulator, and the 2B and 2C games run at full speed even on older CPUs, stretched to fill the screen and with VSync. Every disk is also mounted by itself, with an icon on the desktop. The ISO comes with updates 10 and 11 already applied; an installed 0.8, 0.8.1 or 0.8.2 gets the same changes through the updates at boot.

**System changes:**

- **Every disk is mounted by itself**, at boot and when plugged in (a USB stick, an external HD), in `/media/fliperos/<label>`, with an icon on the LXDE desktop. Mounting, unmounting and ejecting need no password; system partitions (EFI, recovery, Windows reserved), swap, LUKS, LVM and RAID are left alone
- Downloader: Start no longer leaves the download paused. Transmission saw the torrent with no files chosen yet as finished and paused it at the seed ratio limit

**Package changes:**

- Model 2 is SM2-Emu, from the Games menu. It is not compiled into the image; the first launch clones and builds it, then lists the games in `~/roms/model2`. A set that cannot be loaded stays on that list and names the missing chip. The Wine Model 2 Emulator is no longer in the menu
- Model 2: the 2B and 2C games run at full speed on older CPUs. FliperOS patches SM2-Emu so the geometry coprocessor no longer spins while it waits for data, and builds it with link-time optimization. The emulated machine is unchanged. On an i3-540, House of the Dead went from 0.93× to 2.34× and Last Bronx from 0.71× to 1.65×
- Model 2 at 15 kHz stretches the frame to fill 640x240. The emulator's settings file starts at 4:3, which left the picture in the middle of the tube
- Model 2: VSync is on by default, so the picture no longer tears on the tube. Turning it off in the F10 menu sticks
- Model 2: the F10 settings menu can be read at 640x240. Its text was shrunk to about 6 pixels high and the window covered the menu and status bars; now the text stays at its normal size and the window scrolls
- Model 2: opening a game no longer overwrites its saved NVRAM

**fliperos-setup changes:**

- ROM Cleaner for Model 2 (now SM2-Emu): the I/O board sets `model1io.zip` and `model1io2.zip` go along with Daytona USA, Desert Tank and Virtua Cop, which do not start without them. The Model 2 game list hides them

**Tool changes:**

- New `fliperos-automount` (mounts each disk that appears) and `fliperos-sm2emu` (builds SM2-Emu with FliperOS's patches and lists the Model 2 games)

**Documentation:**

- Emulators page: SM2-Emu, built from the menu instead of into the image, its speed patches and settings
- Desktop page: disks mounted by themselves, with an icon on the desktop

## 0.8.2

Fightcade 2 on the tube as it should be: every online match in the game's native resolution, with the Setup's buttons and a pure picture. The ISO comes with updates 8 and 9 already applied; an installed 0.8 or 0.8.1 gets the same changes through the updates at boot.

**System changes:**

- The boot splash stays on screen until the menu or the frontend opens: before, it left halfway through the boot, and the login and the wait for the network (for the update check) were about 15 seconds of black screen
- **Esc closes the frontend** and returns to the FliperOS menu, in Attract-Mode Plus, ES-DE, RetroFE, Pegasus and the Fightcade lobby (only when no game is open; inside a game, Esc stays with the game)
- LXDE desktop: a window that doesn't fit the 640x480 screen, even maximized, makes the desktop scroll (move the mouse to the edge), so its buttons can be reached
- Boot splash: the title of the default theme no longer gets stuck on "AliperOS"

**Package changes:**

- Fightcade 2: **each FBNeo and FBA game plays in its own native resolution** at 15 kHz, like GroovyMAME in GroovyArcade (384x224 for CPS, with a Switchres modeline from GroovyMAME's game data), with no scaling to 320x240; SNES9x plays at the console's 256x224
- Fightcade 2: pure picture in the emulators (no scanlines, bilinear filtering, shaders or effects) with VSync on
- Fightcade 2: FBNeo and FBA get the buttons mapped in Setup > Joysticks, for each player
- Fightcade 2: the lobby opens at 512x448, with bigger text on the tube
- Fightcade 2: an FBNeo left open with no game after an error (missing ROM) closes by itself, instead of leaving a black square over the lobby

**fliperos-setup changes:**

- New: Setup > Frontend > *Add a custom frontend*, to open any program you choose (label and command) as the frontend, including at boot; *Edit or delete a custom frontend* changes or removes it

**Tool changes:**

- `fliperos-buttons fbneo MAP VERSION`: writes FBNeo's input preset from the Setup's button mapping
- New `fliperos-escquit` (Esc closes the frontend) and `fliperos-panning` (desktop scrolling)

**Documentation:**

- Fightcade 2 page: native resolution, pure picture and the lobby mode
- Website: support section and the new desktop screenshot

## 0.8.1

The first ISO with the update system: 0.8's build stopped at the audit before publishing, so 0.8.1 brings everything in 0.8 (in [CHANGELOG.md](https://github.com/juniorterin/fliperOS/blob/main/CHANGELOG.md)) and comes with updates 1 to 7 already applied. An installed 0.8 gets the same changes through the updates at boot.

**System changes:**

- New boot splash: an animated text theme in the style of modern terminals is the default
- More splash themes come in the image (Cogwheel, Into It and Windoze 95), and `~/splashscreen` is the folder for your own themes
- New default LXDE wallpaper
- The update check at boot waits for Wi-Fi to connect (on Wi-Fi it gave up before the network was up)

**Package changes:**

- OpenBOR: paks made for OpenBOR 3.0, which OpenBOR 4 refuses, open again. OpenBOR 3.0 (build 6391) comes in the image, and when OpenBOR 4 fails on a pak the launcher remembers it and opens that pak with 3.0, with the same button mapping
- Attract-Mode Plus: the Basic layout is the default, sharp on the CRT, and every display without filters gets GroovyArcade's: All Games, Most Played, and by genre, manufacturer and year

**fliperos-setup changes:**

- New: Setup > Splash screen, to choose the boot theme, with a preview
- The menu no longer freezes after a splash preview

**Tool changes:**

- ISO build: `updates/` goes into the build's Docker image, so the ISO records the level of the last update (0.8's ISO came out with level 0 and failed the audit)
- `tools/build-openbor-legacy.sh`: builds the OpenBOR 3.0 that comes in the image
- `tools/vm-test.py`: the dev and site runs record the update level after the rootfs

**Documentation:**

- Step-by-step guide from writing the USB stick to playing a game, in the README in English and in Portuguese (`README.pt-BR.md`); the Portuguese website links to the Portuguese README

## 0.8

Updates without a new ISO: from this version on, small fixes reach the installed cabinet at boot. The ISO comes with update 1, which brings everything below to an installed 0.7 (`updates/bootstrap.sh` installs the update system there).

**System changes:**

- FliperOS updates without a new ISO: at every boot with internet, before the launcher, the cabinet asks GitHub whether there are updates and asks before applying them
- Updates are numbered and always applied in order: one only goes in after all the previous ones, and a failure stops the ones after it
- Before asking, the update lists the files changed on this machine that it replaces, and keeps a copy of each in `/var/lib/fliperos/update/backup` (`fliperos-update restore N` puts them back)
- Each update is checked against the sha256 in the update list before anything is written
- Terminal: Ctrl+V pastes in Alacritty, as in the browser

**Package changes:**

- MAME 2010 as the "MAME 3D": the PlayStation-based arcade games, with their own preset in the filter
- Attract-Mode Plus: a new system's display goes to `config/displays.cfg`, which Attract-Mode Plus 3.x reads (the system didn't show up in the frontend)
- Scraper: progetto-SNAPS as the source of arcade screenshots
- The links of the MAME 0.289 romset and of the 0.288 CHDs come in the image, already filled in the Downloader

**fliperos-setup changes:**

- New: FliperOS update screen at boot (`fliperos-setup --update-check`): *Apply now* or *Not now*, with the list of replaced files
- New: Downloader — ROM/CHD MAME torrent from magnet links, downloading only what the filter chooses, through Transmission, with the final folder and Start/Pause; and Free games
- New: AttractPlus ROM List — Attract-Mode Plus game lists of the arcade folders with each game's real name, clones and bootlegs included
- Cleaner: the MAME ROM Cleaner and the MAME CHD Cleaner in one area
- Cleaner and Downloader filter: Model 2 Emulator and Supermodel (Model 3) targets, besides GroovyMAME, Flycast and MAME 2010
- Filter: Mahjong is a genre of its own, off by default
- Scraper: a single system reached Skyscraper without its folder or platform

**Tool changes:**

- `tools/make-update.sh`: publishes the current commit as the next update (`updates/index`, with the sha256 of the files)
- `updates/bootstrap.sh`: brings the update system to installs from 0.7
- `tools/cabinet-update.sh` records the update manifest and level; `tools/verify-iso.sh` checks them in the ISO

## 0.7

First published ISO. The changes are relative to 0.6, which never left the workbench.

**System changes:**

- 15 kHz kernel: kernel.org 6.18.54 LTS with the D0023R patches, the ones in GroovyArcade's `linux-15khz`
- Limine instead of GRUB, on the ISO (hybrid, BIOS and UEFI) and on the installed disk
- Boot menu with GroovyArcade's entries: 15, 25 and 31 kHz, LCD, Intel and NVIDIA in super resolution, NTSC, PAL and EDID
- Boot without text, straight to the splash, and a quiet console after it
- Network on the installed system: DNS from DHCP, wired through NetworkManager and the clock from the network
- Folders in `~`: `roms`, `bios`, `media` and `config`, also over the network (Samba)
- Sound: HDA codec always on (no pops with the menu idle) and volume keys on any screen
- LXDE desktop with the Dracula theme, Alacritty as the terminal, App Store (GNOME Software with Flathub), Falkon and Transmission
- Logging out of LXDE opens the FliperOS menu
- zsh terminal with Oh My Zsh and the Dracula theme
- Input drivers through DKMS: GunCon 2, Thrustmaster (`hid-tmff2`) and Logitech (`new-lg4ff`) wheels
- SDL mapping completed for any connected controller
- Slim ISO, below GitHub's 2 GiB per-file limit: no build packages, no apt cache, no out-of-scope firmware (NVIDIA, datacenter networking, Qualcomm SoCs) and the system in xz

**Package changes:**

- GroovyMAME: official release `gm0289sr222f` (MAME 0.289, Switchres 2.22f) instead of compiling
- GroovyMAME: `mame.ini` like GroovyArcade's, in its own Xorg with `modesetting 1`, at each game's native resolution
- RetroArch: CRT SwitchRes on, 6 cores in the image and the Core Downloader enabled
- RetroArch: automatic profile for panels and encoders, remaps for the MAME cores, input and joypad in linuxraw
- RetroArch: glcore video and sdl2 audio by default, no on-screen notifications
- MAME 2010: compiled without `_FORTIFY_SOURCE` (Tekken Tag didn't open)
- Flycast, PCSX2, Dolphin, Supermodel, Hypseus Singe and Model 2: at 15 kHz they open at 640x240 progressive, stretched to 200%, never at 480i
- PCSX2 from the official AppImage; Supermodel through the project's Makefile; Model 2 in Wine
- Flycast: the panel's directions on the D-pad, linear interpolation off, per-pixel transparency
- PCSX2: no setup wizard, in Big Picture, vsync, no mouse pointer, BIOS in `~/bios/ps2` and games in `~/roms/ps2`
- PCSX2: Mesa's OpenGL thread on; the panel's directions also on the left analog stick
- Supermodel: opens from the menu (game list in a terminal), finds the game list, Button mapping buttons; `model3` folder in the frontends
- Supermodel: CPU emulated at 75 MHz in Step 1.5 and 2.x games, which were slow (Virtua Fighter 3tb from 35 to 59 fps)
- OpenBOR in full screen out of the box
- Wine (Model 2, the Fightcade emulators), Steam and Heroic (GOG, Epic, Amazon) out of the ISO: Setup > Extras installs them over the network
- Frontends: Attract-Mode Plus, EmulationStation (ES-DE) and Pegasus as `.deb`s, in an APT repository inside the image, with the games already configured
- FliperOS 240p theme for EmulationStation and Pegasus
- Fightcade 2 as a frontend option, downloaded from its website; each match in its emulator's mode
- Fightcade's Flycast Dojo with the system Flycast's options (interpolation, transparency and both controllers)
- Attract-Mode: a new display starts with the folder's game list
- Skyscraper 3.21.0, Gum 2.0.2 (arrows in the pagination and menu sounds), AntiMicroX 3.6.1, Switchres 2.2.1

**fliperos-setup changes:**

- New: the equivalent of gasetup, in Bash and Gum, with the Dracula theme, made for 640x480i (80x30)
- Video output test with voice and *Testing Results*, ported from gatools
- Installation to HD/SSD and Recovery Mode
- Video Setup: monitor, orientation, resolution, geometry and Reset Geometry
- Audio Setup like GroovyArcade's, and menu sounds with your own WAV files
- Network Setup: Wi-Fi from the list of networks or a hidden network
- Frontend: chooses the boot launcher and installs what didn't come in the image
- Extras: installs Wine, Steam and Heroic over the network
- Latency: Standard and Low latency modes, with a hardware check
- Scraper: covers, videos and text for every frontend, with the choice of media types
- MAME ROM Cleaner (checklist parameters, like ROMLister; Flycast; network folder) and MAME CHD Cleaner
- Free games: open-source homebrew to fill the frontends
- Joysticks: Button mapping for every emulator (RetroArch, GroovyMAME, Flycast and Flycast Dojo, PCSX2, Dolphin, Supermodel, Hypseus Singe, OpenBOR), light gun and wheel calibration, parallel port joysticks
- `usbhid` quirks for USB controllers
- The cabinet's controller in the menus
- Debug mode and System Update; the Setup waits for the package lock instead of failing
- Start frontend and Start desktop through tty1 (the desktop didn't open from the menu)

**Tool changes:**

- `tools/vm-test.py`: installs in QEMU and boots the disk on BIOS and UEFI; captures the screens; `dev` mode with a fake gamepad
- `tools/verify-iso.sh`: read-only audit of the generated ISO
- `tools/cabinet-push.sh`: updates a cabinet over the network, without a new ISO
- Documentation in the wiki (`docs/wiki`, `tools/wiki-publish.sh`) and in a single HTML file (`tools/render-docs.py`)
- `tools/release-publish.sh`: publishes the ISO to Releases with this changelog
- Automatic release: pushing a version tag builds the ISO on GitHub Actions and publishes it (`.github/workflows/release.yml`)
