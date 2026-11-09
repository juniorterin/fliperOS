| Emulator | Systems | How it opens | Video mode |
| --- | --- | --- | --- |
| GroovyMAME | arcade | KMS | switches per game by itself (Switchres) |
| RetroArch | many (cores) | KMS | switches per game by itself (CRT SwitchRes) |
| Flycast | Dreamcast, Naomi, Atomiswave | its own Xorg (`fliperos-x11-run`) | 640x240 at 15 kHz, 640x480 on the others |
| PCSX2 (official AppImage) | PS2 | its own Xorg | same |
| DuckStation (downloaded through the Setup) | PlayStation | its own Xorg | same |
| PCSX2x6 (PCSX2 fork) | Namco System 246 and 256 arcade games | its own Xorg | same |
| Dolphin | GameCube, Wii, Triforce | its own Xorg | same |
| Hypseus Singe | laserdisc (Dragon's Lair, Space Ace...) | its own Xorg | same |
| OpenBOR | beat 'em ups | its own Xorg | 320x240 |
| Supermodel | Sega Model 3 | its own Xorg | 640x240@57.524 at 15 kHz, 496x384 on the others |
| Model 2 (SM2-Emu) | Sega Model 2 | its own Xorg | same |
| Fightcade 2 (downloaded through the Setup) | online matches: FBNeo, SNES9x and FBA (Wine), Flycast | its own Xorg | the lobby at 512x448 (interlaced at 15 kHz); the matches in the **game's native resolution**: each FBNeo/FBA game in its own mode (384x224 for CPS, via GroovyMAME and Switchres), SNES9x at 256x224, Flycast at 640x240 |
| Steam, Heroic (GOG, Epic, Amazon), through Setup > Games > Extras | PC games | inside the LXDE desktop | the desktop's |

Dedicated pages: [Fightcade 2](Fightcade-2.md), [ROMs, BIOS and artwork](ROMs.md) (the folders in `~`) and [Controls](Controls.md) (buttons, SDL, calibration).

All of them appear in LXDE's **Games** menu ([Desktop and theme](Desktop.md)).

RetroArch uses `crt_switch_resolution 4` (the Setup's `/etc/switchres.ini`) at each game's **native width** when the card generates low dotclocks (the "s" in the output test result: radeon/amdgpu, and an NVIDIA that passed the low resolution grid), like GroovyArcade; the 2560 super resolution is only for cards that don't (Intel, the other NVIDIA).

At 2560 RetroArch draws its notifications at that width, and on the tube they came out squashed (`video_retroarch_super`, saved by the output test and at installation).

RetroArch's video is the `glcore` driver (OpenGL 3.2 core) and its audio is `sdl2`, which goes straight into ALSA; both come from the system `retroarch.cfg` (`/etc/fliperos/retroarch`), which is applied on top of the user's on each launch.

From there also come input and joypad in `linuxraw` (the kernel's `/dev/input/js*`; `fliperos-controllers` generates the automatic controller profiles for `udev` and `linuxraw`), RetroArch without on-screen notifications and a single Esc to close the game (`confirm_quit` off; the default asks for a second Esc, with a notice that would not show).

On cards with only OpenGL 2.x (Radeon X300 to X1950, Intel up to 1st-generation Core, GeForce FX/6/7) `glcore` doesn't open: `fliperos-kms-run` asks Mesa (`eglinfo`) and, on those, passes `gl` instead.

**GroovyMAME at native resolution.** GroovyMAME runs in KMS, without Xorg, like GroovyArcade. Called from the console (by `fliperos-launch`, by the boot session, by a frontend or in the terminal), the `groovymame` command opens through `fliperos-kms-run`.

Switchres attaches each game's mode to the connector (the `ATTACHMODE` of kernel patch 06), and SDL switches to it. On the cabinet: Street Fighter II at `SR-1_384x224@59.64` (99.9% speed), The King of Fighters '98 at `SR-1_320x224@59.19`.

This needs the SDL2 of the `fliperos-sdl2-kms` package (`packaging/packages`), installed in `/usr/local/lib/fliperos/sdl2-kms` and loaded only by GroovyMAME. It is Ubuntu's SDL2 with GroovyArcade's two KMS patches (`packaging/patches/sdl2`): SDL re-reads the connector's modes on every query, and puts the original mode back when the window closes.

Ubuntu's SDL2 reads the mode list once, when it opens, and picked the closest of the old modes: the game stayed in the boot mode.

`SDL_KMSDRM_REQUIRE_DRM_MASTER=0` must not be set: with it, Switchres's SDL2 backend switches the mode by itself (`kms_modesetting`), and SDL undoes the switch on its next frame.

Commands without a screen (`-listxml`, `-listclones`, `-verifyroms`, `-showconfig`, `-createconfig`, `-version`...) run directly.

**GroovyMAME in X.** The `groovymame` command opens in an Xorg of its own (`fliperos-x11-run`) when the package's SDL is missing (an installation updated only over the network, before an ISO that brings it), when multi-screen games are on with more than one monitor (in KMS only the main monitor stays on), or with `groovymame_video=x11` in `/etc/fliperos/fliperos.conf`.

There Switchres switches each game's mode through XRandR. Frontend lines saved as `fliperos-x11-run groovymame` follow the same choice: `fliperos-x11-run` hands `groovymame` back to the command.

As in GroovyArcade's `galauncher.xinitrc`, `fliperos-x11-client` starts **openbox** before the program (`config/openbox-x11-run.xml`: no borders, no shortcuts): it is what fits the full-screen window to the new screen on each mode switch through XRandR; without it the window kept the size of the mode it opened in (the UI in a quarter of the 640x480 screen, the game out of place).

Opened without a game (the UI), `groovymame` passes `-noautosync -waitvsync`: the game chosen in the UI runs in the same process, and GroovyMAME's emusync in X (`emusync_linux.cpp` from gm0289sr222f) uses the `/dev/dri/card0` that it closed when leaving the UI (`osd_deinit` closes the fd and doesn't reset it; "drmCrtcGetSequence(-1)") — with `autosync`, `syncrefresh` removed the throttle and the game ran too fast. The same options stay in KMS.

Opened directly with the game (frontends, command line), vblank works and `autosync` stays. On an earlier installation, `fliperos-rootfs.sh` replaces the old `modesetting 0` with 1.

The other reason for the doubled width is the screen's aspect: with `aspect auto` GroovyMAME takes the aspect from the current mode, and booting at 640x240 gives 8:3 — twice 4:3, so Switchres doubled the width of every game ("SR(0): 768x224").

`mame.ini` ships with `aspect 4:3`, like GroovyArcade (`-aspect "4:3"`); the Setup only goes back to `auto` when the chosen monitor is an LCD.

**GroovyMAME: the package and the `groovymame` command.** The `fliperos-groovymame` package compiles GroovyMAME from the source of the release's tag (`gm0289sr222f`, MAME 0.289 with Switchres 2.22f, commit `953db38`) with FliperOS's lockstep patch, the party of MAME games between cabinets (see [Linked cabinets](Linked-cabinets.md)). The build takes hours, so it happens once, when the package is made: the image and the updates install the same `.deb`. The binary goes to `/usr/local/libexec/groovymame`, without the Qt debugger and without the tools. Setup > Emulators & Games can also build the newest GroovyMAME right on the cabinet, from the newest tag with the same patches (the party keeps working). That compiles the whole MAME: hours, with 20 GB free on the disk (one compiler process per 1.5 GB of free memory). If a patch no longer fits the new code, the package stays.

The `groovymame` command — the one `fliperos-launch`, the frontends and the terminal call — is `config/fliperos-groovymame`, which passes `-inipath /etc/fliperos/mame`: the release's default is `.;ini`, relative to the folder it is opened from, so a `~/.mame/mame.ini` doesn't apply; what applies is `/etc/fliperos/mame/mame.ini` (owned by the `fliperos` user), which the Setup writes.

It also preloads `libfliperos-sdl-audio.so` (`config/fliperos-sdl-audio.c`). MAME 0.289 routes each game's speaker to the output SDL calls the default and saves that choice in the game's cfg (`sound_map`).

SDL 2.30's ALSA backend cannot name a default and lists only the `hw:` devices, so MAME took the card's raw `hw:` device: no dmix shared with other programs, not the card picked in the Setup, and no sound on the live screen. The library reports ALSA's `default` as SDL's default.

On the first game with it, the command also removes the old `sound_map` entries from `~/.mame/cfg` once (marker `.fliperos-sound-default`). MAME's `portaudio` module is no fix: it never lists `default` either, and opens the card's `hw:` device, silent while another program holds the card.

Like GroovyArcade's package, the package also puts in `/usr/local/share/groovymame` the source files of the same tag (commit `953db38`): `plugins` (`hiscore`), the `uismall.bdf` font, `bgfx`, `artwork`, `language`, `ctrlr`, `keymaps` and `hash`.

`mame.ini` is made like GroovyArcade's: GroovyMAME's own `-createconfig` (every option of the version, at its default), with those of `config/mame.ini` on top, each on its own line (`config/fliperos-mame-ini`, at build time).

The GroovyArcade options (gasetup's `-createconfig`): `plugin hiscore`, `skip_gameinfo 1`, `video opengl`, `switchres_ini 1`, `sound sdl`, `aspect 4:3` — plus the Setup's latency (`lowlatency`, `autoframedelay`, `framedelay`); the UI font stays MAME's own (`uifont default`), because GroovyArcade's pixel font (`uismall.bdf`) was too small on the cabinet.

`modesetting 1` is also GroovyArcade's, and serves both KMS and X (the "GroovyMAME at native resolution" paragraph).

What GroovyMAME writes goes to `~/.mame` (cfg, hiscore records), `~/nvram/mame` (nvram) and `~/save/mame` (savestates); `ui.ini` gets GroovyArcade's `infos_text_size 1.00` and `font_rows 20`, together with the Dracula colors — GroovyArcade uses 19, but MAME only accepts 20 to 40 and replaces 19 with the default 30, which at 224 lines leaves the font 7 pixels tall and unreadable; with 20 it is 11.

On an earlier installation, `fliperos-rootfs.sh` only adds to `mame.ini` and `ui.ini` the keys they don't have yet (what was already saved stays, theme included); among the paths, the relative ones (the `.`, `cfg`, `snap` of a plain `-createconfig`: relative to the folder GroovyMAME is opened from, they filled the home folder with `cfg` and `nvram`) are removed, and with no absolute one left, the one from `config/` applies.

The `cfg`/`nvram` left in the home folder moves to `~/.mame`; when both exist, each file keeps its newest version. On a system installed earlier, `fliperos-rootfs.sh` moves the compiled binary to `/usr/local/libexec` and puts the shortcut in its place.

**Reset Geometry.** Setup > Video Setup > Geometry saves the geometry measured on the grid (`crt_range0` with monitor `custom` in `/etc/switchres.ini`, and `switchres_ini 1` in `mame.ini`). The Monitor Type then shows **Custom**, where a `crt_range0` can also be typed in.

**Reset Geometry**, or choosing a preset in Monitor Type, undoes it: Switchres goes back to the chosen monitor's preset, which applies to GroovyMAME (`switchres_ini 1`, as in GroovyArcade) and to RetroArch's mode 4, which read the same file.

**Multiple monitors (2 or 3 screens).** Setup > Video Setup > **Multiple Monitors** adds a second and a third arcade monitor on the other outputs of the same card (analog; digital through an active converter is experimental).

With **Multi-Screen Games** on, GroovyMAME opens each screen of Darius, The Ninja Warriors or Punch-Out!! on its own monitor, and Flycast does the same with the NAOMI multi-board games (F355 Challenge, Airline Pilots, Sega Strike Fighter) on 3 monitors. The other emulators and the frontends stay on monitor 1. Details in [Multiple monitors](Multiple-Monitors.md).

**Nothing interlaced at 15 kHz, by default.** On a 15 kHz tube no `fliperos-x11-run` emulator opens interlaced unless it is chosen for it in [Interlaced hacks](#interlaced-hacks-640x240-filter-or-pure-interlaced) (the exception is the Fightcade 2 lobby, which doesn't fit in 240 lines; its matches do): the 480-line ones and the 384-line ones (Model 2 and 3) run at **640x240 progressive**, **stretched to 200%** horizontally — 640x240 has 8:3 pixels, and the 4:3 image only fills the tube when stretched: Flycast `rend.ScreenStretching=200` (300·W/4H), PCSX2 `AspectRatio = Stretch`, Dolphin `AspectRatio=3`, Supermodel `-fullscreen -res=640,240 -stretch`, Hypseus `-x 640 -y 240 -ignore_aspect_ratio` (options at the end of the line: Hypseus reads the game and the player first), and Model 2 (SM2-Emu) with `aspect_mode = stretch` set on every launch when the mode is wider than 4:3 (its settings file starts at 4:3).

On the cabinet Flycast opened at 640x480i: the setup saves `frequency=15k`, and the script only recognized `15`, so every emulator fell into the 31 kHz column.

**Cards without low dotclocks (Intel, NVIDIA that didn't pass the grid; see [Video cards](Video-cards.md)).** They cannot generate the ~12 MHz pixel clock of a 640x240 mode at 15 kHz, so the Setup writes `dotclock_min 25.0` to `/etc/switchres.ini`.

With it, `fliperos-x11-run` asks for the super resolution width (`super_width`, 2560) instead of the table's, as RetroArch does: the lines and the frequencies are the same, only the pixels are thinner.

The stretch and the sizes given to the emulators follow that width (Flycast `rend.ScreenStretching=800`, Supermodel `-res=2560,240`, Hypseus `-x 2560`). Otherwise Switchres would double the width by itself until it passed the minimum, and the emulators that are given the table's size would draw in part of the screen. Fightcade's per-game modes don't go through this yet.

**No loading screen in Flycast.** While a game loads, Flycast shows the box art and a "Loading..." window with a progress bar. FliperOS builds it with a patch (`config/flycast-patches`) that keeps the screen black until the game starts, as on the arcade board; a load error still shows. If a newer Flycast no longer takes the patch, the image build warns and leaves it out, and the loading screen comes back.

**No text on launch.** The output of X, Switchres and the emulator goes to `/opt/fliperos/logs/<program>.log` (the last run of each), and between the desktop and the emulator the screen stays clean; the Setup's Debug mode shows everything.

The mouse cursor only appears in emulators with a mouse UI — PCSX2 (game list, BIOS wizard), Dolphin, Flycast and Fightcade —, which hide it themselves during full-screen play; the others open with Xorg `-nocursor`.

**GroovyMAME: what's missing.** When a game stops at "System media audit failed", the reason is in `/opt/fliperos/logs/groovymame.log`, and `groovymame -verifyroms GAME` lists the missing files — BIOS and device ROMs come in zips separate from the game. A missing BIOS is brought by Setup > Games > Downloader > **Download BIOS** ([ROMs, BIOS and artwork](ROMs.md#download-bios)). By hand, everything goes in `~/roms/mame` (BIOS can also go in `~/bios/mame`), from the same MAME version (0.289).

PCSX2 is the official AppImage (pinned by version and sha256, extracted to `/opt/pcsx2`): its current code requires SDL3 and Qt 6.10, which Ubuntu 24.04 doesn't have. Dolphin is compiled from the stable version (the official Linux distribution is the Flatpak, which would bring ~1 GB of runtime).

**PCSX2: performance and controls.** `fliperos-x11-run` opens PCSX2 with `mesa_glthread=true` (Mesa's OpenGL thread, which takes the sending of commands to the card off the main CPU thread; to run without it, export `mesa_glthread=false`). Per-game tweaks go in that game's ini, `~/.config/PCSX2/gamesettings/<serial>_<crc>.ini`.

**PCSX2: default video.** The first `PCSX2.ini` (`config/pcsx2.ini`) comes with the settings chosen on the cabinet's CRT: texture filtering **Nearest** (`filter = 0`), no bilinear smoothing on the output (`linear_present_mode = 0`), VSync on and used for timing, 3 software-renderer threads, and the renderer left on **Automatic** (Vulkan on a card that has it, OpenGL otherwise). PCSX2 warns that Nearest is an "unsafe setting"; set Bilinear (PS2) back in a game that draws wrong.

Turning on `UserHacks = true` there disables the fixes PCSX2's GameDB applies to that game. The panel's D-pad also works as the **left analog stick** (`LUp`/`LDown`/`LLeft`/`LRight` in `PCSX2.ini` point to the controller's D-pad when they are empty or on the keyboard): many PS2 games only move with the analog stick.

**Supermodel: game choice and speed.** Opened without a game (from the desktop menu), `fliperos-launch` opens a terminal (Alacritty) with the list of games in `~/roms/model3`, by the names in Supermodel's `Games.xml`; Enter opens the chosen one, Esc exits.

Supermodel's bottleneck is the emulated PowerPC CPU, not the video: games on the Step 1.5 (100 MHz) and Step 2.x (166 MHz) boards were slow on an i3 (Virtua Fighter 3tb at 35 fps).

For them `fliperos-x11-run` passes `-ppc-frequency=75`, which emulates the CPU at 75 MHz (Virtua Fighter 3tb at 59 fps); Step 1.0 games (66 MHz) stay as they are. `FLIPEROS_SUPERMODEL_PPC=100` changes the value, and `FLIPEROS_SUPERMODEL_PPC=0` turns it off. If a game shows internal slowdown or wrong parts, raise the value for it.

**RetroArch cores.** Seven come compiled, to work without network: FCEUmm (NES), Snes9x, Genesis Plus GX (Mega Drive/Master System), mGBA, PCSX ReARMed (PS1), MAME 2010 and, from 0.9.1, **FinalBurn Neo** (the arcade core in which the versus score reaches the LED display through RetroArch, see [Frontends](Frontends.md); its games go in `~/roms/retroarch/fbneo`, in FBNeo's own ROM sets).

MAME 2010 is the **MAME 3D**: MAME 0.139, which runs the **PlayStation-based (PSX) arcade games** well (ZN-1/ZN-2 — Street Fighter EX, Rival Schools —, Namco System 11/12 — Tekken, Tekken 3, Soul Calibur —, Konami GV/GQ, Taito G-NET...).

Any other can be downloaded in RetroArch itself, in **Online Updater > Core Downloader** (from the libretro buildbot): cores, `.info` files and controller profiles live in `/opt/fliperos/retroarch`, owned by the `fliperos` user, so the menu saves without root.

The factory `.info` files and profiles are pinned by commit (`libretro-core-info`, `retroarch-joypad-autoconfig`).

MAME 2010 is compiled without the `_FORTIFY_SOURCE` that Ubuntu's gcc turns on by itself (`ARCHOPTS=-U_FORTIFY_SOURCE`): MAME 0.139 writes 9 bytes into a `char[8]` when starting the H8/3002 CPU, and with the check glibc closed RetroArch (`buffer overflow detected`) on every Namco System 12 game (Tekken 3, Tekken Tag, Soul Calibur), System 23 and ND-1.

## Running a program at 640x240

On a 15 kHz monitor, 480 lines only exist interlaced (480i), and interlacing flickers. At **640x240 progressive** the program draws its 480 lines in 240: it loses half the vertical resolution, but the image is stable — that's how FliperOS runs Dreamcast, PS2, GameCube/Wii and laserdisc at 15 kHz.

The one doing this is `fliperos-x11-run`: it opens the program in an Xorg of its own, and Switchres creates the requested mode within the ranges of the monitor chosen in Video Setup.

Three ways, from the one-off to the permanent:

1. **On the spot, in the console** (Setup > Exit to shell, on the cabinet):

   ```sh
   /opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 program [arguments]
   ```

   Any mode works (`WIDTHxHEIGHT@HZ`, e.g. `320x240@60`, `640x240@59.94`, `384x224@59.64`).

2. **In the desktop menu**: a shortcut in `~/.local/share/applications/my-program.desktop`. `fliperos-launch --mode` leaves the desktop, opens the program in the requested mode and returns to the desktop when it closes (with the same confirmation as the menu's emulators):

   ```ini
   [Desktop Entry]
   Type=Application
   Name=My program
   Exec=/opt/fliperos/bin/fliperos-launch --mode 640x240@60 /path/to/the/program
   Categories=Game;
   ```

3. **Always for that program**: a line in `/etc/fliperos/emulator-modes.conf` (command name, mode at 15 kHz, mode on the other monitors). From then on any path that goes through `fliperos-x11-run` — the menu, a frontend, the console without `--mode` — uses that mode:

   ```
   myemulator          640x240@60      640x480@60
   ```

   A new image doesn't overwrite this file once it has been edited.

In a frontend (Attract-Mode and others), the emulator command becomes `/opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 emulator "[romfilename]"` (or without `--mode`, with the line in the table).

**The image has to be stretched.** 640x240 is an 8:3 screen in pixels, which the tube shows as 4:3. A program that "keeps the 4:3 aspect ratio" would use only half the width (320 columns) and come out squashed in the middle.

Set the program to **stretch/fill the screen** — for Flycast (`rend.ScreenStretching = 200`, via `-config`), Dolphin (`AspectRatio = 3`, via `-C`), PCSX2 (`AspectRatio = Stretch`, in `PCSX2.ini` from the second launch on) and Model 2 (`aspect_mode = stretch`) `fliperos-x11-run` already does it by itself. The math, for another mode: stretch by `300 × width ÷ (4 × height)` percent.

**GroovyMAME and RetroArch** don't go through here: they switch modes by themselves on every game. In GroovyMAME, `interlace 0` in `/etc/fliperos/mame/mame.ini` makes Switchres never choose an interlaced mode (480-line games come out at 240p).

In RetroArch, the **MAME 2010** core already ships that way: CRT SwitchRes reads a `switchres.ini` of the core only, on top of `/etc/switchres.ini`, in `~/.config/retroarch/config/MAME 2010/MAME 2010.switchres.ini` (from `config/retroarch-switchres`), with `interlace 0` — a 640x480 game (Namco System 12) opens at 640x240 progressive, with the image shrunk vertically, instead of 480i.

The same file named after another core (`config/<Core>/<Core>.switchres.ini`) does the same for it; to go back to interlaced, `interlace 1` and without the `# FliperOS` line at the top (updates only rewrite the file that has it).

## Interlaced hacks: 640x240, filter or pure interlaced

**Setup > Video Setup > Interlaced hacks** is a table with one row per program and three columns, one mark per row, like the Services table. It sets how each program shows games with more than 240 lines on a 15 kHz tube:

- **640x240**: the 640x240 progressive mode described above. No flicker, half the lines.
- **Interlaced filter**: all the lines, interlaced (the program's 25/31 kHz line in `emulator-modes.conf`, 640x480 or 496x384, which Switchres makes interlaced on the tube; GroovyMAME and RetroArch pick each game's own interlaced mode, such as 448i, 480i or 576i) with the flicker filter at that program's level.
- **Interlaced pure**: the same interlaced mode without the filter. Sharpest, with the flicker.

Marking **Interlaced filter** on a row opens that program's level (light, medium, strong) and **Preview on the screen**. The preview opens a test screen at 640x480i through the same path as the emulators.

It is made to flicker: one-pixel stripes and a checkerboard, small text, thin frames and a grid, a moving line and a scrolling marquee. The arrows change the level while it is on the tube, and Enter keeps it (off makes the row pure). To choose another level for a row already on the filter, mark pure and then the filter again.

| Row | 640x240 means | Interlaced means | Default |
| --- | --- | --- | --- |
| Flycast, PCSX2, DuckStation, Dolphin, Hypseus Singe | `fliperos-x11-run` opens the 640x240 line of the table | the 640x480 line | 640x240 |
| Supermodel, SM2-Emu (384 lines) | 640x240 at 57.524 Hz | 496x384 at 57.524 Hz, interlaced | 640x240 |
| GroovyMAME | `interlace 0` in `mame.ini`: Switchres never picks an interlaced mode | `interlace 1` | Interlaced filter |
| RetroArch PS1, SNES, Mega Drive, FBNeo | `interlace 0` in the core's own `switchres.ini` | `interlace 1` | Interlaced filter |
| RetroArch MAME 2010 | the same, `interlace 0` (the shipped file) | `interlace 1` | 640x240 |
| Fightcade Flycast | its Flycast matches at 640x240 | 640x480, with or without the filter (picom, see below) | 640x240 |
| Desktop | none (the resolution comes from Desktop Resolution) | picom with or without the filter | Interlaced filter |
| Other programs | none | custom games and anything else in an interlaced mode | Interlaced filter |

The default of each row is what that program already did. The choices are saved in `fliperos.conf`:
- `mode480_PROGRAM=240p|filter|pure`, which `fliperos-x11-run` and `fliperos-fightcade` read;
- `deflicker_PROGRAM=light|medium|strong|off`, which the filter reads;
- `deflicker=` for the Other programs row.

PROGRAM is the command name in `emulator-modes.conf`, or the RetroArch core without `_libretro.so`. The core files are written as `~/.config/retroarch/config/<Core>/<Core>.switchres.ini` without the `# FliperOS` header, so updates leave them alone. Everything counts from the next game.

## Interlaced flicker filter

When a game does run interlaced (any interlaced mode, whatever its size: 480i, 448i, 576i, the 496-line one Switchres makes for Model 3), a line one pixel tall exists in only one of the two fields, so it is drawn 30 times a second and flickers. The filter blends each line with its neighbour before the frame goes out. Then every detail is in both fields: the flicker goes away and the image is a little softer.
- **Medium**, the default, averages each line with the next one. That is RePlayOS's "Interlaced Flicker Reduction", which samples between two lines.
- **Light** (15/70/15) keeps more detail.
- **Strong** (a third each from the line above, the line and the line below) hides the most.
- **Off** leaves the picture sharp, with the flicker.

The level is per program, in the Interlaced hacks table above.

The filter finds the level from the first of these that is set:
1. a file named by `FLIPEROS_DEFLICKER_FILE`, re-read every 30 frames (the preview);
2. `FLIPEROS_DEFLICKER`;
3. the open RetroArch core: `deflicker_pcsx_rearmed=`. The filter lists the loaded libraries every 30 frames to see which `*_libretro.so` is open. It does not wrap `dlopen`, which would change where each program looks for its own libraries;
4. the program: `deflicker_flycast=`. The name comes from `FLIPEROS_DEFLICKER_APP`, which `fliperos-x11-run` sets to the table name, or else from the process;
5. `deflicker=`.

It works below the emulators, so no emulator needs a shader of its own.

`libfliperos-deflicker.so` (`config/fliperos-deflicker.c`, built with the image and on each update into `/usr/local/lib/fliperos`) is loaded through `LD_PRELOAD` by `fliperos-kms-run` (RetroArch and the other KMS emulators) and by `fliperos-x11-client` (the emulators in their own Xorg).

It is not loaded into Xorg or into Switchres: `fliperos-x11-run` takes it out of an `LD_PRELOAD` inherited from a frontend, and `fliperos-x11-client` puts it back on the emulator alone. The library catches the frame swap (`glXSwapBuffers`, `eglSwapBuffers`, including lookups through `dlsym` and `GetProcAddress`, as SDL does).

It copies the frame, draws it back through a three-tap vertical filter and restores the GL state the emulator had. It checks the CRTC mode of every card (`/dev/dri/card0` to `card7`, since the monitor's card is not always `card0`) through DRM every 30 frames: in a progressive mode (240p, 31 kHz, LCD) it does nothing.

Programs in **Vulkan** (PCSX2, Dolphin, DuckStation and Flycast on `amdgpu`) get the same filter from the implicit Vulkan layer `config/fliperos-vkfps.c`, on with `FLIPEROS_VK_FPS=1`. Before each present, in an interlaced mode, it copies the image and draws it back with the same weights and the same level. They stay on Vulkan: the layer asks the swapchain for what it needs and allocates nothing until the first filtered frame.

The layer was tested on Mesa's software driver (lavapipe) with the Khronos validation layers on (`tools/vkfps-test.sh`), and on the cabinet's R7 240 (RADV on `amdgpu`) in a real interlaced Xorg. There, one-line stripes gave the expected values at each level, and Flycast and PCSX2 ran in Vulkan with it, at the same speed with and without the filter and with no GPU errors. The level changes from the web panel with the game open. Dolphin and DuckStation have not run with it yet. The software saturation and hue of the colour calibration go through it too, for cards without a colour matrix.

The LXDE desktop draws without OpenGL, so it gets the same filter through **picom** with a window shader (`config/fliperos-desktop-deflicker --watch`, started by `fliperos-lxde`, at the Desktop row's level `deflicker_desktop=`). It checks the screen mode every 2 seconds and runs picom only while it is interlaced, so a change in Desktop Resolution counts at once. Ubuntu's own picom autostart (`/etc/xdg/autostart/picom.desktop`, without the shader) would take the screen first, since only one compositor runs at a time: `fliperos-lxde` puts `/etc/fliperos/xdg` first in `XDG_CONFIG_DIRS`, where a `picom.desktop` with `Hidden=true` hides it.

Programs in **Wine** are mostly 32-bit, and a 32-bit process can't load the 64-bit library. When Wine is installed from the Extras (the Ubuntu Wine or Wine Staging), the Setup also builds the library for 32 bits (`/usr/local/lib/fliperos/i386/libfliperos-deflicker.so`, with `gcc-multilib` and `libdrm-dev:i386`), and the update rebuilds it when the source changes. When the command runs `wine` or a `.exe`, including a custom game's `bash -c "wine ..."`, `fliperos-x11-client` puts both in `LD_PRELOAD`. The Linux loader skips the one that isn't of the process's kind, and the Wine game gets the filter and the on-screen menu. Games that draw in **Vulkan through DXVK** get the Vulkan layer built for 32 bits as well (`/usr/local/lib/fliperos/i386/libfliperos-vkfps.so`). Its manifest (`config/fliperos-vkfps-i386.json`, a layer of its own name with `library_arch` 32) is only taken by the 32-bit Vulkan loader. `tools/vkfps-test.sh` runs the whole layer test in 32 bits with `ARCH=i386` (lavapipe; Ubuntu has no 32-bit validation layers): the three levels, the on-screen menu, the FPS, the scanlines and the gun flash gave the same values as in 64 bits.

The programs that still cannot take the library get the same picom over their whole Xorg, without the on-screen menu: `fliperos-x11-client` starts it for Fightcade (its lobby is Electron) and for a `wine` or `.exe` command when the 32-bit library is missing. The Fightcade lobby (512x448, interlaced on a 15 kHz tube) uses the Other programs level; while a Flycast match is open, `fliperos-fightcade` switches it to the Fightcade Flycast row's level (`deflicker_fightcade-flycast=`). The Wine matches run at 240 lines, so there picom has nothing to filter and stays off.

For testing:
- `FLIPEROS_DEFLICKER=off|light|medium|strong` overrides the level.
- `FLIPEROS_DEFLICKER_FORCE=1` filters in any mode.
- `FLIPEROS_DEFLICKER_DEBUG=1` prints the level it picked (with the program and the core) and the size and GL profile it filters.
- `tools/deflicker-test.sh` builds the library and checks the result on a software-rendered Xvfb. It covers the per-program and per-core levels, the desktop shader and the preview with its arrows.

## Emulators & Games

**Setup > Games > Emulators & Games** lists the emulators of the desktop menu (RetroArch, GroovyMAME, Flycast, PCSX2, Dolphin, Supermodel, OpenBOR, Model 2, Fightcade 2, DuckStation) and KOF Final Attack, each marked **installed** or **not installed** — the same file the desktop menu looks at (`TryExec`) to show the shortcut.

Next to each installed one is its **version**, read from files without opening the emulator (`fliperos-emulators versions`): the `/usr/local/share/fliperos/emulator-versions` the image build writes (the pinned version, or the date and commit of the master branch built that day), the AppImages' metainfo (PCSX2, DuckStation), Fightcade's `VERSION.txt`, the commit of the SM2-Emu source and, on an older image without the file, GroovyMAME's version text. Choosing an installed one asks GitHub what the update brings (`fliperos-emulators latest NAME`, a few seconds; without network it only shows the installed one): **Up to date**, or **Update: X**. For the image's emulators that is the version the next FliperOS image pins (from the repository's `fliperos-mkiso.sh`) or the newest master commit; Fightcade doesn't publish its version before the download.

Choosing one that is not installed installs it (`config/fliperos-emulators`):

- **Model 2**: installs what is missing from the compiler and clones and builds SM2-Emu as the user, the same build the desktop menu does on the first click (`fliperos-sm2emu --deps` and `--build`). Chosen again when installed, it updates and rebuilds.

  When a system update brings other FliperOS patches for it (`config/sm2-emu-patches`), the update rebuilds it by itself (`fliperos-sm2emu --outdated`, log in `/opt/fliperos/logs/sm2-emu-build.log`; if the build fails the previous one stays), so it also reaches whoever only plays from a frontend.
- **Fightcade 2**: downloaded from its site, with Wine ([Fightcade 2](Fightcade-2.md)).
- **DuckStation** (PlayStation): its license (CC BY-NC-ND 4.0) doesn't allow it in the image, so the official AppImage is downloaded from its GitHub (the `latest` release) and unpacked in `/opt/duckstation` (`config/fliperos-duckstation`). Chosen again when installed, it updates.

  Its games go in `~/roms/ps1` (created once it is installed; a `~/roms/duckstation` or `~/roms/psx` from before is moved there, with its art in `~/media`), and it also lists the ones in `~/roms/retroarch/pcsx_rearmed`; the BIOS is the one in `~/bios`, the same as RetroArch's.

  Each launch (`fliperos-x11-run`) sets full screen, `AspectRatio = Stretch To Fill` and the BIOS folder; the first one also skips its setup wizard and puts both panels on SDL (Cross/Circle/Square/Triangle on A/B/X/Y, as in PCSX2).

  Its renderer stays on Automatic, which picks **Vulkan** where there is one (amdgpu, Intel; radeon has none, and it uses OpenGL); the [interlaced flicker filter](#interlaced-flicker-filter) works on either.

  A renderer chosen in DuckStation itself stays. Esc or Select+Start opens its menu. Opened from a frontend it closes with the game (`-batch`); from the desktop menu it opens in Big Picture. Not seen on the CRT yet.
- **KOF Final Attack (Ikemen GO, 4:3)**: below.
- The others come compiled in the image; one that is missing (an image built without it) can't be installed from here.

### KOF Final Attack

*The King of Fighters: Final Attack* is a MUGEN game in 16:9. The [4:3 patch](https://github.com/juniorterin/KOF-Final-Attack-4-3-patch) converts it to [Ikemen GO](https://github.com/ikemen-engine/Ikemen-GO) in 4:3 at 320x240 with one sprite pixel per screen pixel, for the CRT.

The installer offers two ways to get the game:

- **Download from itch.io**: the free game from [its page](https://united-by-games.itch.io/the-king-of-fighters-final-attack) (United By Games, a 1.4 GB zip) is downloaded, unpacked, patched and deleted by itself. It asks for 7 GB free (the zip, the unpacked game and the converted copy).
- **Use a folder I have**: the folder of the original game (the one with `Final Attack.exe`) on a USB disk, over the network share or in the home folder (the folder above it also works).

The installer (`config/fliperos-kof`) downloads the patch, which downloads Ikemen GO and a portable PowerShell (the conversion scripts are PowerShell), and makes the converted copy in `~/roms/ikemen/kof-final-attack` (about 2 GB; 3 GB free are asked for).

The original folder is not changed: the patch works from a `Patch 4x3` folder inside it, removed at the end, and a folder that can't be written to (a read-only disk) is copied to the disk first. Installing again replaces the copy only after the new one is ready.

It opens from the desktop menu (**Games > KOF Final Attack**) or with `fliperos-kof` on a terminal, in its own Xorg at 320x240@60 (`fliperos-kof` in `emulator-modes.conf`). It is not in the frontends' game lists.

## RetroAchievements

**RetroAchievements** in the main menu, right after Start desktop (and the RetroAchievements box in the web panel's Settings) signs in to a free [retroachievements.org](https://retroachievements.org) account once, for every emulator that has achievements: RetroArch, DuckStation, PCSX2, Dolphin and Flycast. It also turns the achievements on or off and switches **hardcore mode** (no save states, rewind or cheats).

The login trades the user and password for the account's token through the site's API (`dorequest.php?r=login2`, the same call the emulators make). The password goes to `curl` on standard input, never on a command line or in a log, and is not saved; only the token is, in `/etc/fliperos/cheevos` (mode 640, the user's group can read it).

- **RetroArch** reads `/etc/fliperos/retroarch/cheevos.cfg`, which `fliperos-kms-run` adds to `--appendconfig`, above `retroarch.cfg` (an update rewrites that one).
- **DuckStation, PCSX2, Dolphin and Flycast** keep the account in their own ini. `config/fliperos-cheevos` writes it at each launch from `fliperos-x11-run` (`[Cheevos]` in DuckStation's `settings.ini`, `[Achievements]` in `PCSX2.ini` and Dolphin's `RetroAchievements.ini`, `[achievements]` in Flycast's `emu.cfg`), and the Setup writes it right away into the ones that already exist.
- Without `/etc/fliperos/cheevos` nothing changes: an account made inside an emulator's own menu keeps working. Signing out clears the user and token everywhere.

The Pixelcade/ZeDMD marquee shows each unlocked achievement in RetroArch ([Frontends](Frontends.md)).

## Laserdisc (Hypseus Singe)

Laserdisc games live in `/opt/fliperos/roms/hypseus`, which is `~/.hypseus` (over the network: `\\fliperos\FliperOS\roms\hypseus`): the ROM in `roms/<game>.zip`, the laserdisc video in `vldp/<game>/` with the framefile `<game>.txt`, and Singe games in `singe/<game>/`. To open on the CRT (640x240 at 15 kHz, full screen):

```sh
/opt/fliperos/bin/fliperos-x11-run hypseus lair     # Dragon's Lair
/opt/fliperos/bin/fliperos-x11-run singe timegal    # a Singe game
```

in the console or as a frontend command. Hypseus has no menu of its own (it needs the game name), which is why it has no shortcut in Games. It is Hypseus Singe v2.12.1 (the 3.x series requires SDL3, which Ubuntu 24.04 doesn't have), installed as the project's README says (`hypseus`/`singe` are its scripts, `hypseus.bin` the program).

## OpenBOR

The games (`.pak`) go in `/opt/fliperos/roms/openbor/Paks` (over the network: `\\fliperos\FliperOS\roms\openbor\Paks`). The **Games > OpenBOR** menu opens OpenBOR's own menu, which lists the paks.

**In the frontends.** The paks are also a system of their own, **OpenBOR**, in the FliperOS frontend (and in the web panel, Attract-Mode Plus, ES-DE and Pegasus), one game per `.pak` (any case: `HFFgp32.PAK` counts). Picking one opens that pak straight away, without OpenBOR's menu, in the pak's own video mode (below). The system shows up once `Paks` has a pak; `Saves`, `Logs` and `v3` next to it are not games and stay out.

**Game information.** A pak has no record of its name, author or year: it is a package of the game's files. `fliperos-openbor-meta` (`config/fliperos-openbor-meta`) reads what is inside each pak (the file table at the end, PAK32 or PAK64) and the frontend shows it:

| From the pak | Where it goes |
|---|---|
| The title screen (`data/bgs/title.*`, then `titleb`, `logo`, `select`) | The game's picture, `~/media/snap/openbor/<pak>.png` or `.gif` |
| Players: the highest `maxplayers` of the modes in `levels.txt` (OpenBOR assumes 2; `single` is 1) | **Players** (the frontend's player filter) |
| The modes (`set` lines of `levels.txt`: Story, Arcade, Boss Rush...) | **Series** |
| The resolution (`data/videopc.txt` or `data/video.txt`: `video 400x300`, or modes 0 to 6, 320x240 to 960x540) | **Extra**, and the video mode the game opens in |

Until ScreenScraper brings one, the description is made from the pak: *An OpenBOR game for 1 player. Mode: Story. Resolution 400x300.* ScreenScraper's description replaces it; a description from anywhere else (written by hand, or by the Scraper's own lists) is left alone. An image with almost no colours (the flat backgrounds many paks leave in place of a title) is skipped. The select screen is only a background with "Player Select", so it is not used as a cover. Art already in `~/media` (from the Scraper, or put there by hand) is never replaced.

The rest (the real title, year, developer, genre, description, cover and logo) comes from **ScreenScraper** through the Scraper: **Setup > Games > Scraper** (or the web panel's Scraper page) lists OpenBOR with the other folders (Skyscraper's `openbor` platform, ScreenScraper system 214). After the Scraper runs for OpenBOR, `fliperos-openbor-meta` takes the title, year, developer, genre, players and description from Skyscraper's cache (`~/.skyscraper/cache/openbor`) and puts them over what came from the pak. Everything goes in the FliperOS list `~/.local/share/fliperos/lists/OpenBOR.txt` (the frontend and the web panel read it; Attract-Mode Plus gets a copy) and the description in `~/media/texto/openbor/<pak>.txt`. The list is rewritten when the frontend opens and when the `Paks` folder changes (`fliperos-setup --romlists`). The FliperOS frontend's automatic scrape (Arcade Database, libretro-thumbnails) has no OpenBOR games; ScreenScraper only comes through the Scraper. To see what a pak has: `fliperos-openbor-meta info "My Game.pak"`.

**Video mode.** Each pak opens in its own resolution, adjusted to the monitor (`fliperos-openbor-meta mode`, called by `fliperos-x11-run`):

| Pak | 15 kHz monitor | 25/31 kHz and LCD |
|---|---|---|
| Up to 240 lines (320x240) | as is, 60 Hz | as is, 60 Hz |
| 241 to 288 lines (480x272) | as is, 50 Hz (like PAL) | as is, 60 Hz |
| 289 to 447 lines (400x300) | 240 lines, 60 Hz (OpenBOR scales the game down) | as is, 60 Hz |
| 448 lines or more (640x480, 800x600, 960x540) | half the lines, like FliperOS runs 480-line consoles: 640x240 at 60 Hz, 960x270 at 50 Hz; 800x600 (300 lines halved) goes to 800x240 | as is, 60 Hz |

With **Setup > Video Setup > Interlaced hacks** on for OpenBOR, a 15 kHz monitor gets the other column (480 lines, interlaced). Without a pak (the menu, **Games > OpenBOR**), the mode stays the one in `emulator-modes.conf` (320x240).

**Running a pak from the command line.** The `openbor` command takes the pak as its only argument: the full path, or only the file name of a pak that is in `Paks`. In the console (Setup > Exit to shell, on the cabinet), the same line the frontends run:

```sh
/opt/fliperos/bin/fliperos-x11-run openbor "/home/fliperos/roms/openbor/Paks/My Game.pak"
```

`fliperos-x11-run` opens an Xorg in the pak's video mode (above); the short form `fliperos-x11-run openbor "My Game.pak"` finds the pak in `Paks`. Without an argument, `openbor` opens the menu, as before. OpenBOR 4 reads the pak from its first argument (`OpenBOR /path/game.pak`); 3.0 doesn't take arguments, so for a pak listed in `v3/paks.txt` the command links `v3/Paks` to `v3/OnePak`, a folder with only that pak, and 3.0 opens it without the menu (it skips the menu when there is one pak).

**Old paks.** OpenBOR is version 4. Many mods were made for 3.0 (build 6391) and stop as soon as they load in 4 (the log in `Logs/OpenBorLog.txt` says *An Error Occurred*, e.g. *Unable to load image file '...gif'*: 4 no longer takes GIF sprites).

FliperOS also ships 3.0 build 6391: when 4 refuses a pak, the `openbor` command (`config/fliperos-openbor`) opens 3.0 right away and writes the pak in `openbor/v3/paks.txt`; when every pak is on that list, 3.0 opens directly. 3.0 runs in `openbor/v3`, with its own `Saves` and `Logs` (the `.cfg` files of one version don't work in the other) and the same `Paks` and `ScreenShots`; the controls of the Setup go to both.

To try a pak in 4 again, remove its line from `paks.txt`. The 3.0 binary is in the repository (`config/openbor-legacy`, rebuilt by `tools/build-openbor-legacy.sh`), so updates bring it too.

## Model 2

[SM2-Emu](https://github.com/dmanlfc/sm2-emu) is the Sega Model 2 emulator (native, BSD). It is **not compiled into the image**. **Games > Model 2** is always in the menu. The first click opens a terminal and asks to clone and build it (the network, once; a few minutes).

What is missing from the compiler (`glslc`, ninja, the X and ALSA headers the vendored SDL3 needs) is installed then, with sudo. The tree stays in `~/.local/src/sm2-emu`, owned by the user.

After that, the same screen lists the `.zip` files in `~/roms/model2` by the names in `games.xml`, and *Update Model 2* at the bottom pulls and rebuilds. Esc cancels and the desktop stays. A set that cannot be loaded stays on that screen, with the missing chip named in the header, instead of closing back to the desktop.

It opens in its own Xorg, full screen, in the same mode as Supermodel. At 15 kHz that is 640x240, and each launch sets `aspect_mode = stretch` so the frame fills the tube. VSync is on by default (`vsync = true`, set on the first launch); turning it off in F10 sticks.

Chips are matched by CRC32, so the zip has to be a MAME Model 2 set: one made only for the old Model 2 Emulator can be missing a chip, and that chip is named on the game list (and in `/opt/fliperos/logs/sm2-emu.log`).

A gamepad is read by button position through SDL, with the keyboard live beside it (5 and 6 insert coins, 1 and 2 start, arrows and Z X C V are player 1). F9 quits back to the desktop; F10 is the emulator's own settings.

It is CPU-bound on one core. FliperOS builds it with link-time optimization. The speed work below started as FliperOS patches and is part of SM2-Emu itself since 0.9.41, so they left `config/sm2-emu-patches` (installed to `/usr/local/share/fliperos/sm2-emu-patches`); a patch put there is applied before compiling.

The one there now publishes game state as outputs: the recoil, ammunition and life of the gun games for light guns, the round wins of the fighting games and the credits ([DIY hardware](DIY-hardware.md#model-2-game-outputs)).

Most of the time on the 2B and 2C boards went to the geometry coprocessor waiting for its next command: the Model 2C MB86235 re-ran a read of its empty input FIFO every cycle, and the Model 2B SHARC spun in a one-NOP `DO ... UNTIL NOT FLAG0_IN` loop.

Nothing else runs during that slice, so each repeat leaves the machine in the same state. The emulator now skips to the end of the slice instead. The i960 also fetches instructions straight from ROM and work RAM, without a virtual bus call.

The emulated machine is unchanged: a 600-frame run gives the same final state and the same audio, bit for bit, on House of the Dead, Last Bronx, Sonic Championship and Virtua Fighter 2.

On the cabinet's i3-540 (headless, one core), the speed went from 0.93× to 2.34× on House of the Dead (2C), 0.71× to 1.65× on Last Bronx (2B), 0.80× to 2.35× on Sonic Championship (2B), 0.85× to 2.84× on Fighting Vipers (2B) and 2.42× to 3.15× on Virtua Fighter 2 (2A).

The F10 settings menu stays readable on a 640x240 screen (also upstream now): the overlay no longer shrinks its font below the native 13 pixels, and the Settings window fits between the menu bar and the status bar, scrolling what does not fit.

A patch that no longer applies to a newer SM2-Emu is skipped, and the build goes on without it. When a FliperOS update brings a different set of patches, the next **Games > Model 2** offers to update: it pulls SM2-Emu and rebuilds (the network, a few minutes), because a patch that left FliperOS now comes from upstream.

Since 0.9.43 the settings menu is translated, and the build also asks for the HarfBuzz and fontconfig headers. The quick check of a set before it opens uses a throwaway NVRAM, so it does not overwrite the game's saved one. OpenGL 4.3 needs a GPU that can open that context (that cabinet's R7 240 opened a 4.5 core context).

## Steam and GOG

Neither ships in the image (they would take over 500 MB, and are useless without network): **Setup > Games > Extras** installs them. **Steam**: Ubuntu's `steam-installer`; on first launch Valve downloads the client (hundreds of MB, needs network).

**GOG**: there is no official Linux client; the Setup installs **Heroic Games Launcher** (official `.deb`, with a pinned hash) (GOG, Epic and Amazon; the same as on the Steam Deck), which runs Windows games with the Wine/Proton it downloads itself.

Both open **inside the LXDE desktop** (they are X programs), from the **Games** menu. Their UIs were made for larger screens: on a 15 kHz CRT at 640x480 they are cramped — on a 31 kHz monitor or an LCD they are much better.

## Wine and Wine Staging

**Setup > Games > Extras** has two Wines. **Wine** is Ubuntu's (9.0 on noble), the stable one, and what Fightcade installs by itself. **Wine Staging** is the newest Wine from WineHQ (`winehq-staging`, from WineHQ's repository, with its key pinned in `config/winehq-archive.asc`). It has the patches that are not in Wine yet, so more Windows games run, and some run better. It is the development line, a new version every two weeks, so a game can also break with it.

Wine Staging takes the place of Ubuntu's Wine: its package replaces `wine` and provides `/usr/bin/wine`, so Fightcade, Hook Of The Reaper and the custom games use it without any change. With it installed, choosing Wine or Hook Of The Reaper in the Extras doesn't bring Ubuntu's Wine back. A Wine prefix opened by a newer Wine is upgraded once and doesn't go back to the older one (Fightcade's is `~/.local/share/fliperos/wine-fightcade`). Not tested yet on a cabinet: the install itself, and Fightcade's emulators on Wine Staging.

## Namco System 246 and 256 (PCSX2x6)

PCSX2x6 is PS2Homebrew-arcade's fork of PCSX2 for the Namco arcade boards (Tekken 4 and 5, Soul Calibur II and III, Time Crisis 3 and 4...). It is an emulator of its own, next to PCSX2, which keeps `~/roms/ps2`; the image carries v0.2.22, checked by sha256 (`/opt/pcsx2x6`), and update 44 brings it to cabinets already installed. Its settings are in `~/.config/PCSX2x6`, apart from PCSX2's.

Each game is a `NM00000.acgame` file (a text file with the game's name, its `gameid`, the `platform`, the dongle and the image) plus a folder of the same name with the game's `boot.elf` (from the fork's proverb project) and its image (`.chd` or `.iso`), in `~/roms/namco2x6` (one folder for the 246, the 256 and the Super 256; the older `namco246` and `namco256` folders are moved into it at the next login). One folder in each place, like `~/roms`:

| What | Where |
| --- | --- |
| The arcade BIOS: `256.BIN` with its `.nvm` and `.mec`, for the 246, the 256 and the Super 256 (the 246 board's own `COH-H31000.BIN` made Soul Calibur II stop with "Jump to unaligned address", so it is only used when `256.BIN` is missing) | `~/bios/namco2x6` |
| The game's dongle (`NM00000.ps2`, a memory card image the game rewrites: keep a copy) and its save cards | `~/save/namco2x6` |
| The game's memory (`sram.bin`, 32 KB; delete it to start from zero) | `~/nvram/namco2x6` |

Setup > Games > Downloader > Download BIOS fetches the BIOS from RetroBIOS. The games and dongles are not downloaded: bring your own. The panel's buttons follow Setup > Joysticks > Button mapping: the arcade buttons are the `[JVS]` section of the emulator's `PCSX2.ini` (`config/pcsx2x6-jvs-bindings`). Button N of a game goes to the panel position that Setup > Joysticks > Buttons layout gives it (position N without a layout), on the controller of each player. Without a 4-button line in Buttons layout, the 4-button games (Tekken, Soul Calibur, Bloody Roar...) are laid out 2x2, as on Namco's cabinets: buttons 1 and 2 on the top row, 3 and 4 below them (in Tekken, the punches on top and the kicks below). This only applies to PCSX2x6; the other emulators keep button N on position N. The section is written on the first launch and again by every Button mapping save and system update; a change made inside PCSX2x6 stays until then.

### The files of a game

A game ready to run is three things: a `.acgame` file and a folder in `~/roms/namco2x6`, and the dongle in `~/save/namco2x6`. For Tekken 5 from the MAME CHD:

```
~/roms/namco2x6/NM00019.acgame
~/roms/namco2x6/NM00019/boot.elf
~/roms/namco2x6/NM00019/te51-dvd0.chd
~/save/namco2x6/NM00019.ps2
```

```ini
[game]
name=Tekken 5
gameid=NM00019
platform=256

[data]
subdir=NM00019
elf=boot.elf
dongle=NM00019.ps2
mediasrc=te51-dvd0.chd
media=DVD
```

| Line | What it is |
| --- | --- |
| `gameid` | The game's code, `NM` and five digits (NM00019 is Tekken 5). The only line that is required |
| `platform` | `246`, `256` or `super256`. It sets the emulated clock, and a 256 game refuses to boot as `246`. Without it, the fork's game list decides |
| `subdir` | The game's folder, next to the `.acgame`. Without it, the `gameid` |
| `elf` | The boot program inside that folder, `boot.elf` by default. It comes from the fork's proverb project (`bin/NM00019/boot.elf` in its nightly zip); the frontend downloads it when it extracts a packed game |
| `mediasrc` | The image inside that folder, `NM00019.chd` by default |
| `media` | `CD`, `DVD` or `HDD`. Without it, the fork's game list decides |
| `dongle` | The dongle's file in `~/save/namco2x6`, `NM00019.ps2` by default |
| `card` | A second memory card, only for Soul Calibur II's Conquest mode |

The image can be:
- A **`.chd`**. A MAME CHD of the game works as it is (`bldyr3b.chd`, `te51-dvd0.chd`, `ted1dvd0b.chd`), and it is the best choice for the CD games.
- A **`.iso`** of 2048-byte sectors. The DVD images of the archive.org item are fine. Its CD images are not: see Bloody Roar 3 below.
- A hard disk **`.img`** for the HDD games.

The dongle is a memory card image of 8,650,752 bytes, with the extension `.ps2`. The dongle `.bin` files of the archive.org item (once gunzipped) and of the MAME sets (`br3-dongle.bin`) are the same data: rename them to `.ps2`. The game writes to it, so keep a copy as it came.

A packed game is the archive.org folder as it comes, with its `.iso.gz`, `.bin.gz` and `(HDD).img.gz` files dropped in `~/roms/namco2x6`: the frontend writes all of the above when you choose it (see Packed games below). The BIOS is `256.BIN` in `~/bios/namco2x6`.

### Packed games (the archive.org folders)

Drop a folder with the `.gz` files (`NM00019 TE51 DVD0 (DVD-ROM).iso.gz`, `NM00019 TE51, Ver.B4 a026051314505a.bin.gz`...) in `~/roms/namco2x6`, with any name. The frontend lists the game (Tekken 5) with its versions as clones (a version is a disc and a dongle of the same code; the newest is the parent, and a disc or dongle with no pair is left out). Choosing one extracts what it needs with a progress bar in the middle of the screen (B cancels): the disc and the `boot.elf` (from the proverb project, downloaded once and kept) into a folder of the game, the dongle into `~/save/namco2x6` (a copy as it came stays in `originals`), and a `.acgame` ready to run. Then the `.gz` files used are deleted and the game opens; a disc or dongle that other versions use stays extracted for them. It needs free space for the whole disc (about twice the `.gz`). A copy that stopped short is not extracted (FILE INCOMPLETE: COPY IT AGAIN) and loses nothing. A CD image whose sectors carry the 8-byte CD subheader in front, which the fork refuses, is put back in place while extracting; the bytes missing from such an image stay missing, so for a CD game the MAME CHD is the better copy.

The hard disk games (media HDD: Battle Gear 3, Zoids Infinity, Cobra, Time Crisis 4, Taiko 12 to 14...) come in the same folders: the archive.org item has their `(HDD).img.gz` image next to the dongles, so a version is a dongle and that image (a game with a single disc or image pairs every dongle with it; otherwise a dongle takes the disc whose code matches, ignoring hyphens, `DVD0` and `HDD0`). The image is written sparse, so the zeros do not take the disk. A disc or tool disc with no pair, and the games whose names give no hint (Dragon Chronicle Online), are left out. The hard disk games have not been run in PCSX2x6 here.

### What was tested, and what went wrong

Tested on a cabinet on 2026-11-05 and 06: i7 870 (2.93 GHz, turbo off in the firmware), R7 240 (RADV, Vulkan), 6 GB DDR3 in two unmatched sticks (2 GB DDR3-1066 and 4 GB DDR3-1333).

| Game | Board | Image | Result |
| --- | --- | --- | --- |
| Tekken 5 (NM00019) | 256 | `.iso`, then MAME CHD `te51-dvd0.chd` | Plays; FPS dips in fights |
| Tekken 5 Dark Resurrection (NM00026) | 256 | archive.org `.iso`, then MAME CHD `ted1dvd0b.chd` | Plays; the same dips with either image |
| Soul Calibur II (NM00007) | 246 | archive.org `.iso` (DVD0D and DVD0B) | Plays, with `256.BIN` |
| Bloody Roar 3 (NM00002) | 246 | MAME CHD `bldyr3b.chd` | Plays at a steady 60 FPS |
| Capcom Fighting Jam (NM00018) | 246 | archive.org `.iso` | Extracted, not run |
| Hard disk games | | | Not run |

The problems met on the way, in the order they came:

| What was seen | Cause | What was done |
| --- | --- | --- |
| The setup wizard on every launch | Passing `-datapath X` makes the fork use `X/PCSX2x6`, a new empty folder | No `-datapath`: the fork uses `~/.config/PCSX2x6` by itself |
| Black screen, the EE at 100%, "ROM directory not found" in the log | The retail PS2 BIOS (`scph39001.bin`) | The arcade BIOS, `256.BIN` from RetroBIOS |
| No input in the game | The fork ignores `[Pad1]`; arcade inputs come only from the `[JVS]` section | `[JVS]` written from Setup > Joysticks > Button mapping |
| Soul Calibur II stops with "Jump to unaligned address" right after `boot.elf`, on both discs | The 246 board's BIOS `COH-H31000.BIN` (board A-000-010, from 2000) | `256.BIN` for every board, as the fork's guide allows; Download BIOS fetches only `256.BIN` |
| The FPS, CPU and GPU counters come back on screen | The emulator saves to `PCSX2.ini` the counters it had on when it closes | `fliperos-x11-run` turns them off on every launch |
| One Tekken 5 stage comes out blocky | Texture filtering Nearest (`filter = 0`, from the official PCSX2 file); the fork warns it "will break rendering in some games" | The fork's own video defaults with VSync on fixed it, in Vulkan. That change was reverted on request, so `PCSX2.ini` still has Nearest: set Texture Filtering to Bilinear (PS2) inside PCSX2x6 for a game that draws like that |
| An extraction fails at the end | The copy to the cabinet had stopped 59 MB short (`gzip -t`: "unexpected end of file") | The frontend says FILE INCOMPLETE: COPY IT AGAIN, deletes nothing and logs the cause in `~/.cache/fliperos/namco-unpack.log` |
| Bloody Roar 3: "corrupted dump (truncated sectors)" | The archive.org CD image keeps the 8-byte CD subheader at the start of each 2048-byte sector, and has lost the last 8 bytes of each | The extraction moves the data back into place (the fork then opens it), but the game hung at the versus screen. The clean MAME CHD fixed it, and the small glitches went away |

**Why the 256 games dip.** The fork emulates each board's clock from `platform=` in the `.acgame`: the 246 runs the emulated processor at 294.9 MHz, like a PS2; the 256 at 393.2 MHz (33% more, with a faster IOP too); the Super 256 at 442.4 MHz. In a Tekken 5 fight the emulated processor's thread used 99.9% of one core, the vector unit's thread 84-89%, the drawing thread about 39%, and the video card 5-35%, with the processor at its full 2926 MHz. So the cabinet's processor is the limit. Inside the arcade it also reached 94-98 C and throttled to 1.2 GHz, which made it worse; out of the arcade it stays at 62-67 C and FPS went up a little.

These did not change the dips: the sound off, the card's clock, the EE cycle rate (the fork does not allow lowering it), the blending fixes, a CHD instead of the `.iso`, and the fork's video defaults. A 256 game with `platform=246` stops at boot with "System 256 modeset error": the game checks the board.

On a desktop with an i7-7700 and a GTX 1080 Ti (Windows, Direct3D 12 and Vulkan) Tekken 5 Dark Resurrection ran much better, with a few small dips. Those were not measured; the shader cache being filled on the first run is the likely cause.

Still open: a hand-made `.acgame` shows in the frontend under its file name (`NM00019`), because the list does not read its `name=` line.
