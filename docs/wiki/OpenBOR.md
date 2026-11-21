[OpenBOR](https://github.com/DCurrent/openbor) runs the beat 'em up games made with it: hundreds of fan games and mods, each one a `.pak` file.

## Where the games go

The games (`.pak`) go in `/opt/fliperos/roms/openbor/Paks` (over the network: `\\fliperos\FliperOS\roms\openbor\Paks`). `~/roms/openbor` is a shortcut to `~/roms/retroarch/anybor`, the folder of the AnyBOR core ([below](#the-anybor-core-in-retroarch)), so the paks, and what the engine keeps next to them (`Saves`, `Logs`, `v3`), live there. A system that still had `~/roms/openbor` as a plain folder gets everything moved into the core's folder at the next login, with nothing overwritten: a file whose name is already in both places stays where it was, and the folder stays a folder until the next login moves the rest. A folder you pointed to another disk ([Folders](Setup-Games.md)) is left alone. The **Games > OpenBOR** menu opens OpenBOR's own engine, which lists the paks.

## The AnyBOR core in RetroArch

 The paks of the frontends open in **AnyBOR**, a libretro core for OpenBOR with 322 engine profiles (OpenBOR 3.0 builds 3020 to 6391, and 4.0 up to 8023-dev) and an automatic choice of the profile for each pak, so old mods and new ones open in the same core. It runs in RetroArch (KMS, each game's mode from the CRT SwitchRes engine), with save states and up to four players.

It is not in the ISO. The first time you open an OpenBOR game, the frontend downloads and installs the `fliperos-anybor` package (about 5 MB, with the bar in the middle of the screen) and the game opens. Without a network, and with no package installed, the game does not open; the engine of **Games > OpenBOR** works without it. The core goes to `/opt/fliperos/retroarch/cores/anybor_libretro.so`. It is built from [retrodiv/AnyBOR-libretro](https://github.com/retrodiv/AnyBOR-libretro) at a pinned commit (`packaging/packages/fliperos-anybor.sh`) and is published like the other optional packages ([Packages](Packages.md)). The core includes OpenBOR 3400 and 3741, whose license forbids selling the code or the binaries: the license texts are in `/usr/share/doc/fliperos-anybor`. To open a pak by hand: `fliperos-kms-run retroarch -L /opt/fliperos/retroarch/cores/anybor_libretro.so "/home/fliperos/roms/openbor/Paks/My Game.pak"`.

## In the frontends

 The paks are also a system of their own, **OpenBOR**, in the FliperOS frontend (and in the web panel, Attract-Mode Plus, ES-DE and Pegasus), one game per `.pak` (any case: `HFFgp32.PAK` counts). Picking one opens that pak straight away, without OpenBOR's menu, in the AnyBOR core. The system shows up once `Paks` has a pak; `Saves`, `Logs` and `v3` next to it are not games and stay out.

## Game information

 A pak has no record of its name, author or year: it is a package of the game's files. `fliperos-openbor-meta` (`config/fliperos-openbor-meta`) reads what is inside each pak (the file table at the end, PAK32 or PAK64) and the frontend shows it:

| From the pak | Where it goes |
|---|---|
| The title screen (`data/bgs/title.*`, then `titleb`, `logo`, `select`) | The game's picture, `~/media/snap/openbor/<pak>.png` or `.gif` |
| Players: the highest `maxplayers` of the modes in `levels.txt` (OpenBOR assumes 2; `single` is 1) | **Players** (the frontend's player filter) |
| The modes (`set` lines of `levels.txt`: Story, Arcade, Boss Rush...) | **Series** |
| The resolution (`data/videopc.txt` or `data/video.txt`: `video 400x300`, or modes 0 to 6, 320x240 to 960x540) | **Extra**, and the video mode the game opens in |

Until ScreenScraper brings one, the description is made from the pak: *An OpenBOR game for 1 player. Mode: Story. Resolution 400x300.* ScreenScraper's description replaces it; a description from anywhere else (written by hand, or by the Scraper's own lists) is left alone. An image with almost no colours (the flat backgrounds many paks leave in place of a title) is skipped. The select screen is only a background with "Player Select", so it is not used as a cover. Art already in `~/media` (from the Scraper, or put there by hand) is never replaced.

The rest (the real title, year, developer, genre, description, cover and logo) comes from **ScreenScraper** through the Scraper: **Setup > Games > Scraper** (or the web panel's Scraper page) lists OpenBOR with the other folders (Skyscraper's `openbor` platform, ScreenScraper system 214). After the Scraper runs for OpenBOR, `fliperos-openbor-meta` takes the title, year, developer, genre, players and description from Skyscraper's cache (`~/.skyscraper/cache/openbor`) and puts them over what came from the pak. Everything goes in the FliperOS list `~/.local/share/fliperos/lists/OpenBOR.txt` (the frontend and the web panel read it; Attract-Mode Plus gets a copy) and the description in `~/media/texto/openbor/<pak>.txt`. The list is rewritten when the frontend opens and when the `Paks` folder changes (`fliperos-setup --romlists`). The FliperOS frontend's automatic scrape (Arcade Database, libretro-thumbnails) has no OpenBOR games; ScreenScraper only comes through the Scraper. To see what a pak has: `fliperos-openbor-meta info "My Game.pak"`.

## Video mode

 This section is about OpenBOR's own engine (**Games > OpenBOR** and the `openbor` command). In the AnyBOR core, RetroArch's CRT engine sets the mode from what the core reports. Each pak opens in its own resolution, adjusted to the monitor (`fliperos-openbor-meta mode`, called by `fliperos-x11-run`):

| Pak | 15 kHz monitor | 25/31 kHz and LCD |
|---|---|---|
| Up to 240 lines (320x240) | as is, 60 Hz | as is, 60 Hz |
| 241 to 288 lines (480x272) | as is, 50 Hz (like PAL) | as is, 60 Hz |
| More, divided exactly by 2 or 3 into 200 to 288 lines (640x480, 720x480, 960x540) | the divided size: 320x240 and 360x240 at 60 Hz, 480x270 at 50 Hz | as is, 60 Hz |
| Any other (400x300, 800x600, 1280x720) | 240 lines, same shape: 320x240, 426x240 (OpenBOR scales the game down) | as is, 60 Hz |

The mode always has the pak's shape: OpenBOR keeps the pak's aspect ratio in full screen (*Preserve Aspect Ratio*, the default in each pak's `.cfg`), so in a mode of another shape it leaves black bars (a 400x300 pak in 400x240 came out 320 pixels wide, seen on the cabinet).

With **Setup > Video Setup > Interlaced hacks** on for OpenBOR, a 15 kHz monitor gets the other column (480 lines, interlaced). Without a pak (the menu, **Games > OpenBOR**), the mode stays the one in `emulator-modes.conf` (320x240).

## Running a pak from the command line

 The `openbor` command takes the pak as its only argument: the full path, or only the file name of a pak that is in `Paks`. In the console (Setup > Exit to shell, on the cabinet), the same line the frontends run:

```sh
/opt/fliperos/bin/fliperos-x11-run openbor "/home/fliperos/roms/openbor/Paks/My Game.pak"
```

`fliperos-x11-run` opens an Xorg in the pak's video mode (above); the short form `fliperos-x11-run openbor "My Game.pak"` finds the pak in `Paks`. Without an argument, `openbor` opens the menu, as before. OpenBOR 4 reads the pak from its first argument (`OpenBOR /path/game.pak`); 3.0 doesn't take arguments, so for a pak listed in `v3/paks.txt` the command links `v3/Paks` to `v3/OnePak`, a folder with only that pak, and 3.0 opens it without the menu (it skips the menu when there is one pak).

## Old paks (OpenBOR 3.0)

 OpenBOR is version 4. Many mods were made for 3.0 (build 6391) and stop as soon as they load in 4 (the log in `Logs/OpenBorLog.txt` says *An Error Occurred*, e.g. *Unable to load image file '...gif'*: 4 no longer takes GIF sprites).

FliperOS also ships 3.0 build 6391: when 4 refuses a pak, the `openbor` command (`config/fliperos-openbor`) opens 3.0 right away and writes the pak in `openbor/v3/paks.txt`; when every pak is on that list, 3.0 opens directly. 3.0 runs in `openbor/v3`, with its own `Saves` and `Logs` (the `.cfg` files of one version don't work in the other) and the same `Paks` and `ScreenShots`; the controls of the Setup go to both.

To try a pak in 4 again, remove its line from `paks.txt`. The 3.0 binary is in the repository (`config/openbor-legacy`, rebuilt by `tools/build-openbor-legacy.sh`), so updates bring it too.

Its log is `Logs/OpenBorLog.txt`, also in the web panel's **System > Processes and logs**. **Build the newest** in **Setup > Games > Emulators & Games** builds OpenBOR's latest code ([Games Setup](Setup-Games.md#the-newest-version-of-a-packaged-emulator)).

See also: [Emulators](Emulators.md), [Scraper](Scraper.md).
