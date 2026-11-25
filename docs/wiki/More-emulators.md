The other emulators: Dolphin, DuckStation, Hypseus Singe (laserdisc), KOF Final Attack on Ikemen GO, Odin (Sega Hikaru, Gaelco 3D) and xemu (Sega Chihiro).

## Dolphin (GameCube, Wii, Triforce)

Its games go in `~/roms/dolphin` (`.iso`, `.rvz`, `.wbfs`). It is compiled from Dolphin's stable version, as a FliperOS package updated with FliperOS (the official Linux build is a Flatpak, which would bring about 1 GB of runtime); **Build the newest** in **Setup > Games > Emulators & Games** compiles the newest ([Games Setup](Setup-Games.md#the-newest-version-of-a-packaged-emulator)).

- It opens in its own Xorg at **640x240** on a 15 kHz tube, stretched to fill it (`AspectRatio=3`), or interlaced with **Interlaced hacks**.
- On amdgpu it runs in **Vulkan**.
- **Wii games are 4:3.** Dolphin starts the Wii with a 16:9 TV (`IPL.AR` in the Wii's `SYSCONF`), and the picture, stretched to the whole 640x240 window of the tube, would come out squeezed. FliperOS opens Dolphin with `-C SYSCONF.IPL.AR=False`, which sets the Wii's TV to 4:3 for that game (even the first one on a new cabinet). `wii_aspect=16:9` in `fliperos.conf` puts the Wii back in 16:9 for a widescreen monitor.
- An **NKit** image (`.nkit.iso`) opens without Dolphin's "NKit Warning" window (it would wait for a click the panel can't give): FliperOS sets `SkipNKitWarning` each time. Savestates and input recordings are still not shared between an NKit image and a normal one.
- It has no menu of its own for the panel, so **coin + button 1** opens the FliperOS [on-screen menu](On-screen-menu.md).
- **Net play** between cabinets, with FliperOS's patch ([Linked cabinets](Net-play.md#dolphin-net-play)), and [RetroAchievements](RetroAchievements.md).

## DuckStation (PlayStation)

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/docs/img/wiki/game-duckstation.webp" width="480" alt="A PlayStation game in DuckStation">

Its license (CC BY-NC-ND 4.0) doesn't allow it in the image: **Setup > Games > Emulators & Games > DuckStation** downloads the official AppImage from its GitHub, and choosing it again updates it. A PlayStation game opened before it is installed installs it first.

- Its games go in `~/roms/ps1` (it is there from the install, so games can be copied before it), and it also lists the ones in `~/roms/retroarch/pcsx_rearmed`. The BIOS is the one in `~/bios`, the same as RetroArch's.
- Each launch sets full screen, *Stretch To Fill* and the BIOS folder; the first one also skips its setup wizard and puts both panels on SDL (Cross/Circle/Square/Triangle on A/B/X/Y, as in PCSX2).
- **PAL games** run at 50 Hz on the tube, 240p games without field flicker, and the picture is cropped so one game line is one tube line.
- The renderer stays on Automatic: **Vulkan** where there is one (amdgpu, Intel), OpenGL on radeon. A renderer you choose in DuckStation stays.
- **Esc** or **Select + Start** opens its menu, and **coin + button 1** too. Opened from a frontend it closes with the game; from the desktop menu it opens in Big Picture.
- Its log is in the web panel's **System > Processes and logs**. Not seen on the CRT yet.

## Hypseus Singe (laserdisc)

Dragon's Lair, Space Ace and the other laserdisc games, plus Singe games. They live in `/opt/fliperos/roms/hypseus`, which is `~/.hypseus` (over the network: `\\fliperos\FliperOS\roms\hypseus`):

| What | Where |
| --- | --- |
| The game's ROM | `roms/<game>.zip` |
| The laserdisc video | `vldp/<game>/`, with the framefile `<game>.txt` |
| Singe games | `singe/<game>/` |

To open one on the tube (640x240 at 15 kHz, full screen), in the console or as a frontend command:

```sh
/opt/fliperos/bin/fliperos-x11-run hypseus lair     # Dragon's Lair
/opt/fliperos/bin/fliperos-x11-run singe timegal    # a Singe game
```

Hypseus has no menu of its own (it needs the game's name), so it has no shortcut in the desktop's Games menu. It is Hypseus Singe v2.12.1: the 3.x series needs SDL3, which Ubuntu 24.04 doesn't have.

## KOF Final Attack (Ikemen GO, 4:3)

*The King of Fighters: Final Attack* is a MUGEN game in 16:9. The [4:3 patch](https://github.com/juniorterin/KOF-Final-Attack-4-3-patch) converts it to [Ikemen GO](https://github.com/ikemen-engine/Ikemen-GO) in 4:3 at 320x240, with one sprite pixel per screen pixel, for the CRT.

**Setup > Games > Emulators & Games > KOF Final Attack** offers two ways to get the game:

- **Download from itch.io:** the free game from [its page](https://united-by-games.itch.io/the-king-of-fighters-final-attack) (United By Games, a 1.4 GB zip) is downloaded, unpacked, patched and deleted by itself. It needs 7 GB free.
- **Use a folder I have:** the folder of the original game (the one with `Final Attack.exe`) on a USB disk, the network share or the home folder.

The converted copy goes to `~/roms/ikemen/kof-final-attack` (about 2 GB). The original folder is not changed. **Update** downloads the newest game, patch and Ikemen GO and converts again.

It opens from the desktop menu (**Games > KOF Final Attack**) or with `fliperos-kof`, in its own Xorg at 320x240@60. It is not in the frontends' game lists.

## Odin (Sega Hikaru and Gaelco 3D)

Odin is a low level emulator of the **Sega Hikaru** (Air Trix, Brave Firefighters, Planet Harriers, NASCAR Arcade, Star Wars Racer Arcade, Cyber Troopers Virtual-On Force) and of the **Gaelco 3D** boards (ATV Track, Smashing Drive, Football Power, Radikal Bikers, Speed Up, Surf Planet). Its games go in **`~/roms/odin`**, one MAME set (`.zip` or `.7z`) per game: `airtrix`, `braveff`, `pharrier`, `sgnascar`, `swracer`, `von4`, `atvtrack`, `smashdrv`, `gfootbal`, `radikalb`, `footbpow`, `speedup`, `surfplnt`.

- **It installs itself.** Odin does not come in the image. The `odin` folder exists from the installation; when the first game is in it and you open it in the frontend, a bar installs Odin (a package already built, so it takes the time of a download) and the game opens. By hand: **Setup > Games > Emulators & Games > Odin**. It is a system of its own in every frontend (Odin), with the game names from the GroovyMAME list.
- **The shared sets** the Hikaru games need, `hikaru.zip` and `mie.zip` (and `tms320c31.zip` for Radikal Bikers, Football Power, Speed Up and Surf Planet), go in `~/bios/odin`; `~/bios/mame` and `~/roms/odin` work too. The other sets (`jvs13551`, `18wheelr`, `srally2`) are optional: without them Odin imitates those boards.
- **Video.** It needs an OpenGL 4.3 driver (or Vulkan 1.3): an AMD card with the Mesa driver, like the R7 240 or the R9 380, has it; a GPU with only OpenGL 2.1 (Intel Ironlake) does not. On **amdgpu** it draws in **Vulkan**, on the other drivers (radeon, Intel) in OpenGL, chosen the first time it opens and each time the driver changes (Setup > Video Setup); in between, the Renderer you pick in its menu stays. It opens in its own Xorg at **640x480** (interlaced on a 15 kHz tube, which Switchres sets up): Odin opens a window of at least 640x480 that it cannot shrink, so any smaller mode (320x240) shows only a corner of the picture, and it has no stretch option, so 640x240 would be cut in half too. On 25/31 kHz monitors and LCDs it is 640x480 progressive. Note that the flicker filter (Video Setup) works in OpenGL, not in the Vulkan renderer that amdgpu uses by default. It starts in full screen, with the bezel off and VSync on; the first time only, so what you change in its menu stays.
- **Files.** What the board keeps without power (EEPROM, NVRAM, clock, the Virtual-On card) is in `~/nvram/odin/<game>`, the save states (F2 saves, F4 loads) in `~/save/odin`, and `odin.ini` and `odin.log` in `~/.local/share/odin` (also reachable from the `config` folder).
- **Controls.** Odin has its own menu (Escape, F10 or Guide) and its own pages for the controls, wheels and light guns; **coin + button 1** opens it. Calibrate the controls of each game the first time, in its test menu (key `0`, or Guide held with R3).
- **Updates.** A cabinet that has it gets the new version with the system updates. The version is the project's commit of 2026-11-18 (0.1.1 and the Gaelco 3D games).

Odin has not been seen on a CRT yet.

## xemu (Sega Chihiro)

The Sega Chihiro is an arcade board built on the original Xbox hardware. FliperOS runs it in **xemu**, the Tovarichtch fork of the Xbox emulator (GPL-2.0), which has the Chihiro board: OutRun 2 and OutRun 2 SP, The House of the Dead III, Virtua Cop 3, Ghost Squad, Crazy Taxi High Roller, Wangan Midnight Maximum Tune 1 and 2, Ollie King and Gundam Battle Operating Simulator. The ALL.net games (the Satellite Terminal ones, with a touchpad) do not work. Its games go in **`~/roms/chihiro`**, one `.bin` per game.

- **It installs itself.** xemu does not come in the image. The `chihiro` folder exists from the installation; when the first game is in it and you open it in the frontend, a bar installs xemu (a package already built) and the game opens. By hand: **Setup > Games > Emulators & Games > xemu**. It is a system of its own in every frontend (Sega Chihiro).
- **The games.** xemu only opens a Chihiro *netboot* image, a `.bin`, but you do not have to make it: put the **disc** of the game in `~/roms/chihiro` (the `.7z` of a TOSEC dump with its `.gdi`, or a Redump `.cue` with its tracks, or a `.chd`) and it shows in the frontend as it is. The first time you open it, a bar (**PREPARING THE GAME**, B cancels) unpacks the disc, finds out which game it is from the product number in its header (`GDX-0003B` is Virtua Cop 3, set `vcop3`), looks for that game's key, converts it with the [chihiro-netboot](https://github.com/Tovarichtch/chihiro-netboot) tool (MIT, it comes with FliperOS) and keeps the image in `~/roms/chihiro/.netboot/`. The next openings go straight to the game. A `.bin` netboot image you already have works as it is. A normal Xbox disc image or a MAME `.zip` does not.
- **The game key** is a small file (`317-0354-com.data` for Virtua Cop 3) inside the game's MAME set (`vcop3.zip`; `vcop3a.zip` and the clones work too, and in a merged romset it is in the parent's zip). It is looked for in `~/roms/mame`, `~/bios/mame`, `~/bios/chihiro` and next to the game. When no folder has it, FliperOS asks the Downloader to fetch **only that file** (`fliperos-downloader fetch-sets`), from the ROM set link you saved in Setup > Games > Downloader and, if you saved none, from the one that comes with the image (the one that screen suggests); it uses a Transmission of its own for that, so the filter, the plan, the saved links and the downloads in progress are not touched. With no link at all, or with no network, the game does not open and says so (GAME KEY (MAME SET) NOT FOUND, NO NETWORK FOR THE GAME KEY). You can also put the `.zip` in `~/roms/mame` yourself.
- **Memory and space.** The conversion reads the whole data track (about 1.2 GB) into memory: it needs about 3 GB free (it says NOT ENOUGH MEMORY before starting if there is less) and about 2 GB of space on the disk of the game. It takes a minute or two, once per game. The temporary files go away when it ends, even when it fails.
- **The board files** go in `~/bios/chihiro`, loose (not inside the zip): `chihiro_xbox_bios.bin` and, beside it, `ic10_g24lc64.bin`, `ic11_24lc024.bin`, `pc20_g24lc64.bin` and `fpr21042_m29w160et.bin` (what is inside MAME's `chihiro.zip`). `ver1305.bin` (the network board firmware, from `seganetw.zip`) is only needed by the games played over a link (OutRun 2 SP, Gundam). **Setup > Games > Downloader > Download BIOS** brings all of them when there is a game in the folder. No Xbox BIOS or MCPX ROM is needed: the Chihiro BIOS carries its own boot ROM.
- **Video.** It needs OpenGL 4.0 or more, or Vulkan: an AMD card with the Mesa driver has it, a GPU with only OpenGL 2.1 (Intel Ironlake) does not. The renderer follows the card's driver, as in Odin: **Vulkan on amdgpu**, OpenGL on the others, chosen the first time and each time the driver changes (what you pick in its menu stays in between). On the cabinet's R7 240 (Oland) the OpenGL renderer **hangs the GPU** in the first frames of the game (`ring gfx timeout` in the kernel log, then Xorg falls and the screen goes back to the frontend); Vulkan (RADV) runs it. The game is 640x480, so it opens in its own Xorg at **640x480** (interlaced on a 15 kHz tube, where the flicker filter applies; progressive on 25/31 kHz monitors and LCDs), in full screen, 4:3, with no menu bar and VSync on; the first time only, so what you change in its menu stays. The package is built from the fork's **perf-experimental** branch, with its optimizations on by default (CPU boost: native SSE and a wider jump cache; GPU boost: the tuned NV2A; smooth first play: the game's known shaders compile while it boots, so the first minutes do not stutter). The stock `main` branch of the fork has none of them: on the cabinet's i7-870 Virtua Cop 3 ran badly choppy with it, with one CPU thread of the emulated Xbox at ~93% of a core. The emulator has **sound** through ALSA (the SDL it carries only had PipeWire, which the cabinet does not run: it opened silent).
- **Files.** The configuration (`xemu.toml`), the board EEPROM and the cards are in `~/.local/share/xemu-chihiro` (also reachable from the `config` folder); the save states in `~/save/chihiro`.
- **Controls.** xemu keeps each function of a game as a number (a key, a mouse or gun button, a joystick button or axis) and does not read the Setup's button map. FliperOS closes the gap with the keyboard, the way it does for custom games: each time the game opens, `fliperos-chihiro-input` writes into `xemu.toml` the key of each function, and `fliperos-buttons gamekeys` reads your panel or pad from **Setup > Joysticks > Button mapping** and presses those keys through a virtual keyboard while the game runs (it quits with it). The same buttons do the same job in every game: **coin** and **start** of player 1 and 2 (keys `5`/`Enter` and `6`/`2`), the stick = the arrows (the wheel of OutRun 2 and Maximum Tune, Ollie King's swing and board), **b1** = the gas, the gun's pedal, Crazy Taxi's jump, **b2** = the brake, reload, **b3/b4** = the gears, **b5** = the camera, **b6** = Maximum Tune's intruder, **b7** = the card. Player 2 has `b1`/`b2` for the pedal and reload of the two-gun games. The gun's trigger and body button stay on the mouse (the GunCon 2), since a function takes one key. xemu opens its own menu on a right click of the mouse, and the GunCon 2 sends its A/C buttons and the shot off the screen (the "off-screen reload" of the OSD) as a right click, so the system keeps xemu's **Light Gun Mode** on at every opening: in the gun games (Virtua Cop 3, House of the Dead 3, Ghost Squad) the cursor is hidden and the mouse buttons belong to the game, and no shot opens the menu; in the other games the right click still opens it. The map from panel button to key is `~/.local/share/xemu-chihiro/chihiro.key` (reachable from the `config` folder): it is made once and is yours to edit, but the key each function listens to is the system's and is set again at every opening. `FLIPEROS_CHIHIRO_KEYS=off` turns the virtual keyboard off. xemu's own menu opens with F1. The test menu is the key `0` and the service key `9` (there is no panel button for them); guns and wheels are calibrated in the game's test menu. Gundam (twin sticks) keeps xemu's own keys.
- **Updates.** A cabinet that has it gets the new version with the system updates. The version is the fork's `perf-experimental` commit `98fbd75` (2026-10-03).

**Check a disc without converting it:** `fliperos-chihiro-prepare inspect DISC` prints the product number, the MAME set it maps to and which key files are missing. Virtua Cop 3 has been seen running on the cabinet (the INSERT COIN screen, in Vulkan), not yet on a CRT and not at full speed: the i7-870 is near the least xemu asks for.

## How it works

- **DuckStation** is unpacked in `/opt/duckstation` (`config/fliperos-duckstation`); a `~/roms/duckstation` or `~/roms/psx` from before moves to `~/roms/ps1`, with its art. Its settings are `[Cheevos]`, `AspectRatio` and the BIOS path in its `settings.ini`, written at each launch by `fliperos-x11-run`; `-batch` closes it with the game.
- **Hypseus** is installed as the project's README says: `hypseus` and `singe` are its scripts, `hypseus.bin` the program. `fliperos-x11-run` passes `-x 640 -y 240 -ignore_aspect_ratio` at the end of the line (Hypseus reads the game and the player first). Its memory is in `~/nvram/hypseus`.
- **KOF:** the installer (`config/fliperos-kof`) downloads the patch, which downloads Ikemen GO and a portable PowerShell (the conversion scripts are PowerShell). The patch works from a `Patch 4x3` folder inside the original, removed at the end; a folder that can't be written to is copied to the disk first. Installing again replaces the copy only after the new one is ready. `fliperos-kof` is in `emulator-modes.conf` at 320x240@60.

See also: [Emulators](Emulators.md), [KMS and X11](KMS-and-X11.md).
