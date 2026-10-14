# Changelog

What changed in each ISO published in [Releases](https://github.com/juniorterin/fliperOS/releases), in the format of GroovyArcade's releases. Each version's section is the text of its release: `tools/release-publish.sh` doesn't publish an ISO without its section.

## 0.9.1

The MAME ROM Cleaner works out of the box: `catver.ini`, `nplayers.ini` and `controls.xml` now ship in the image, so the categories, adult games, play mode and real button count filters show without copying anything. The 0.9 ISO left their folder empty. Also new are the versus scoreboard on the LED display for fighting games, the game outputs for light guns and button lights, and Arcadeflow as the Attract-Mode Plus theme. None of the scoreboard and outputs work has been tried with a real gun, LED board or two-player match on the tube. The ISO comes with updates 16 and 17 already applied; an installed 0.8.x or 0.9 gets the same changes through the updates at boot.

**System changes:**

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

- **The Setup is grouped, in the order of setting up a cabinet**: Video Setup, Audio Setup, Network Setup, Joysticks, **Games** (Frontend, Emulators & Games, Folders, Downloader, Cleaner, Scraper, AttractPlus ROM List) and **System** (Extras, Latency, System Update, Debug mode, Splash screen). Quirks is inside Joysticks. It was one list of 17 items
- **Info balloons**: under the list, a balloon says what the item under the cursor is for, in the FliperOS menu, the Setup and its groups, Video, Audio and Network Setup, Joysticks and the Downloader. It needs the gum of this ISO: a system that came from an older ISO shows the same menus without the balloons
- MAME ROM Cleaner on a MAME 2010 romset: the Naomi and Atomiswave games the filter leaves out go with the rest. They were always kept (for Flycast, which can't read that romset) and showed up in the MAME 2010 list
- MAME ROM Cleaner and Downloader filter: *Data files* shows the three files that ship with FliperOS and their version
- AttractPlus ROM List: every folder with games gets its display, also one removed before; a folder left without games loses its display, and Arcadeflow reads a rebuilt list
- Extras: **Hook Of The Reaper** (through Wine), **QMamehook** (native, for serial-port guns) and **LEDSpicer** (button lights), the readers of the game outputs. None of them is in the image
- Extras > Pixelcade, with Pixelcade installed: update it, or install the paid art pack with the license code of the purchase
- The frontends no longer list Fightcade's whole ROM collection as FBNeo games

**Tool changes:**

- New `fliperos-versus` (the scoreboard), `fliperos-outputs` (the outputs readers), `fliperos-arcadeflow`, `fliperos-fbneo` (the system of each FBNeo set) and `fliperos-powerkey`
- `tools/verify-iso.sh` checks that the three ROM Cleaner data files in the image are the repository's

**Documentation:**

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
