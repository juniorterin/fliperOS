**FliperOS** is Ubuntu 24.04 (amd64) for arcade cabinets with a CRT monitor, in the style of GroovyArcade: a **15 kHz kernel** (kernel.org 6.18 LTS + the D0023R patches, the same as GroovyArcade's `linux-15khz`), Switchres, emulators and frontends ready to play, the **GunCon 2 light gun** working out of the box (driver and calibration for the tube, see [Controls](Controls.md)), and a setup menu made for the tube's screen.

The media is **installation-only** and follows the GroovyArcade flow: a boot menu with the frequency range, a spoken test of the video outputs, *Testing Results*, the **FliperOS Setup** menu and installation to the HD/SSD. On the installed system the same program becomes the setup menu that appears when the frontend closes. The screens belong to **`fliperos-setup`**, written in Bash with [Gum](https://github.com/charmbracelet/gum), with the **Dracula** theme and English text, designed for **640x480i**: 80x30 characters, nothing animated or blinking.

> In development: 0.8.3 is tested in a VM (QEMU) and on a cabinet with a 15 kHz CRT.

## Using it

| Page | What it covers |
| --- | --- |
| [Install](Install.md) | Writing the media, the boot menu, the video output test, installing to the HD/SSD, Recovery Mode |
| [Installed system](Installed-system.md) | The boot, the default launcher, the Setup menu item by item (video, audio, network, debug, update) |
| [Frontends](Frontends.md) | Choosing the boot frontend, the 240p themes for EmulationStation and Pegasus, the APT repository |
| [Emulators](Emulators.md) | Each emulator and the video mode it opens in, GroovyMAME, RetroArch, running a program at 640x240, laserdisc, Model 2, Steam and GOG |
| [Fightcade 2](Fightcade-2.md) | Online matches: download through the Setup, ROMs, the lobby, matches in each game's native resolution, keys |
| [ROMs, BIOS and artwork](ROMs.md) | The folders in `~` (`roms`, `bios`, `media`, `config`), the MAME ROM Cleaner, the CHD Cleaner, the free games |
| [Scraper](Scraper.md) | Covers, screenshots, logos, videos and descriptions of the games, for every frontend |
| [Adding games](Adding-games.md) | Step by step: games, real names and artwork in Attract-Mode Plus and ES-DE, emulator command lines in KMS or X11, adding a new emulator |
| [Controls](Controls.md) | Each player's buttons, the GunCon 2 light gun (driver and calibration), wheel and pedals, parallel port, USB quirks, how SDL sees each controller |
| [Desktop and theme](Desktop.md) | LXDE, the programs in the menu, changing the resolution, the Dracula theme |
| [Multiple monitors](Multiple-Monitors.md) | Two or three arcade monitors on one card: the Setup, the multi-screen games in GroovyMAME (Darius, Punch-Out!!) and Flycast (F355 Challenge), how it works |
| [Latency](Latency.md) | The Standard and Low latency modes, what each tweak does, recommended hardware, how to measure |

## Hacking on it

| Page | What it covers |
| --- | --- |
| [15 kHz kernel](Kernel-15-kHz.md) | The kernel and the patches |
| [Build and tests](Build-and-tests.md) | Building the ISO in Docker, the build options, the ISO audit, publishing the release, the tests, updating a cabinet over the network |
| [Architecture](Architecture.md) | How `fliperos-setup` is organized, the other components (splash, network, diagnostics) and what each file in the repository is |
| [Sources](Sources.md) | Where each part came from: GroovyArcade, Switchres and the other projects consulted |

The pages of this wiki are kept in the repository, in [`docs/wiki`](https://github.com/juniorterin/fliperOS/tree/main/docs/wiki), and published here by `tools/wiki-publish.sh`: to fix a page, change the file there.
