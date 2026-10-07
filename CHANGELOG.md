# Changelog

What changed in each ISO published in [Releases](https://github.com/juniorterin/fliperOS/releases), in the format of GroovyArcade's releases. Each version's section is the text of its release: `tools/release-publish.sh` doesn't publish an ISO without its section.

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
