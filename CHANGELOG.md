# Changelog

What changed in each ISO published in [Releases](https://github.com/juniorterin/fliperOS/releases), in the format of GroovyArcade's releases. Each version's section is the text of its release: `tools/release-publish.sh` doesn't publish an ISO without its section.

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
- SM2-Emu, a native Sega Model 2 emulator: a Games menu entry. It is not compiled into the image; the first launch clones and builds it, then lists the games in `~/roms/model2`

**fliperos-setup changes:**

- New: Setup > Frontend > *Add a custom frontend*, to open any program you choose (label and command) as the frontend, including at boot; *Edit or delete a custom frontend* changes or removes it

**Tool changes:**

- `fliperos-buttons fbneo MAP VERSION`: writes FBNeo's input preset from the Setup's button mapping
- New `fliperos-escquit` (Esc closes the frontend) and `fliperos-panning` (desktop scrolling)

**Documentation:**

- Fightcade 2 page: native resolution, pure picture and the lobby mode
- Emulators page: SM2-Emu, built from the menu instead of into the image
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
