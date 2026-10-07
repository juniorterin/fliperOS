A step-by-step guide to putting games, names and artwork into **Attract-Mode Plus** and **EmulationStation (ES-DE)**, to the emulator command lines (KMS or X11) and to adding a new emulator that opens from any frontend. The folders themselves are described in [ROMs, BIOS and artwork](ROMs.md); the automatic artwork download is in [Scraper](Scraper.md).

## Copy the games

Each emulator has its folder in `~/roms` (`/home/fliperos/roms`; over the network, `\\fliperos\roms`). Copy the files as they come: MAME sets stay zipped and are never renamed (the frontends and MAME find a game by its set name, `sf2ce.zip`).

| Folder | What goes in it | Opens in |
| --- | --- | --- |
| `mame` | MAME sets (`.zip`, `.7z`) and their CHD folders | GroovyMAME |
| `naomi`, `naomi2`, `atomiswave` | MAME sets of these systems | Flycast |
| `model3` | MAME sets of Model 3 | Supermodel |
| `model2` | Model 2 Emulator sets (a link to its folder in Wine) | Model 2 Emulator |
| `dreamcast` | `.gdi`, `.cdi`, `.chd` | Flycast |
| `ps2` | `.iso`, `.chd`, `.cso` | PCSX2 |
| `dolphin` | GameCube and Wii (`.iso`, `.rvz`, `.wbfs`) | Dolphin |
| `retroarch/<core>` | Whatever that core opens (the `_info.txt` in each folder lists the extensions) | RetroArch |

BIOS files go in `~/bios` (`\\fliperos\bios`): `~/bios/mame` for MAME (`neogeo.zip`, `qsound.zip`), `~/bios/dc` for Flycast (`naomi.zip`, `awbios.zip`, `dc_boot.bin`), `~/bios/ps2` for PCSX2 and the folder itself for the RetroArch cores. A BIOS left in a games folder shows up as a game in the frontend.

## Make the frontend see the folder

A folder with games becomes a **system** in the frontend when you pick the frontend in **Setup > Frontend**. Pick it again (even if it already is the default) every time a folder gets its first games: the Setup only creates what is missing, so nothing you changed is lost.

- **Attract-Mode Plus**: for each folder the Setup creates an emulator (`~/.attract/emulators/<name>.cfg`, with the command that opens the game and where the artwork is), a display in `~/.attract/config/displays.cfg` (`~/.attract/attract.cfg` before Attract-Mode Plus first runs), and a game list (romlist, `~/.attract/romlists/<name>.txt`) built from the files in the folder.
- **ES-DE**: the Setup writes every system to `~/ES-DE/custom_systems/es_systems.xml` (folder, extensions, command and theme). ES-DE reads the folders itself each time it starts.

**New games in a folder that is already a system.** ES-DE finds them the next time it opens (or right away with *Main menu > Utilities > Rescan ROM directory*). Attract-Mode Plus doesn't look at the folder: its list is the romlist. Rebuild it with one of these:

- **Setup > AttractPlus ROM List** (arcade folders, below);
- **Setup > Scraper** (any folder; it also fetches the artwork);
- in Attract-Mode itself: Tab opens the configuration, *Emulators > (the emulator) > Generate Collection/Rom List*;
- or delete `~/.attract/romlists/<name>.txt` and pick the frontend again in Setup > Frontend.

## Real game names

A game list made only from the files shows the file name: `mvsc2u` instead of *Marvel Vs. Capcom 2 New Age of Heroes*.

**Attract-Mode Plus.** The name is the second field of each line in the romlist (`Name;Title;Emulator;CloneOf;Year;Manufacturer;...`). Two ways to fill it in:

- **Setup > AttractPlus ROM List** ? for the arcade folders (`mame`, `naomi`, `naomi2`, `atomiswave`, `model2`, `model3` and the RetroArch arcade cores: `mame2010`, `mame2003_plus`, `fbneo`, `hbmame`...). No internet needed: the name, year, manufacturer, players, controls and emulation status of each game come from GroovyMAME's game list (`groovymame -listxml`), and from the MAME 0.139 list for the `mame2010` folder. **Clones and bootlegs** come in with their own names and with their parent in the `CloneOf` field. In the MAME folder the list also gets the clones that only exist inside the parent's zip (a merged romset), because GroovyMAME opens a game by its name and finds the clone there. The other emulators open a file, so in their folders only the clones that have their own file are listed. A set that isn't in MAME's list keeps its file name, and BIOS sets are left out. With `catver.ini` in `~/roms/mame` (or in `/usr/local/share/fliperos/romclean`), the category comes in too. The Setup also creates an **Arcade** display with all those folders together. The first run reads GroovyMAME's list (about a minute); the next ones take a second.
- **Setup > Scraper** ? for every folder, with names and descriptions from ScreenScraper, ArcadeDB or TheGamesDB, plus the artwork.

Each of the two rewrites the list of the folders it works on, so whichever ran last wins. The artwork is found by the set name, so it is kept either way.

**ES-DE.** In systems with the arcade platform (`mame`, `model2`, `model3` and the RetroArch MAME cores), ES-DE already shows the full name of each MAME set from its own list. Everything else shows the file name until it is scraped: **Setup > Scraper** writes the names, descriptions and artwork to `~/ES-DE/gamelists/<system>/gamelist.xml`. ES-DE's own scraper (*Main menu > Scraper*) also works and saves to the same places.

## Artwork

All artwork lives in `~/media` (`\\fliperos\media`), one folder per type and, inside it, one per platform. The file name is the ROM name without the extension: the screenshot of `~/roms/mame/sf2.zip` is `~/media/snap/arcade/sf2.png`. Setup > Scraper fills these folders, but you can also copy images and videos there yourself (from a MAME artwork pack, for example).

| `~/media` folder | What it holds | Attract-Mode Plus (`artwork` line) | ES-DE |
| --- | --- | --- | --- |
| `snap` | Screenshots (`.png`) | `snap` | screenshot |
| `preview` | Videos (`.mp4`) | `snap` (videos sit in the same line) | video |
| `logo` | Logos, wheel art (`.png`) | `wheel` | marquee |
| `box` | Covers and flyers (`.png`) | `flyer` | cover |
| `marquee` | Cabinet marquees (`.png`) | `marquee` | ? |
| `texto` | Descriptions (`.txt`) | overview (`~/.attract/scraper/<emulator>/overview` is a link here) | ? (descriptions come from `gamelist.xml`) |

The platform folder of each games folder: `arcade` for `mame`, `model2`, `model3` and the RetroArch MAME cores; `naomi`, `naomi2` and `atomiswave` for Flycast's arcades; `fba` for the FBNeo and FB Alpha cores; `dreamcast`, `ps2`, `gc` (Dolphin) and the console name for the other RetroArch cores (`snes`, `megadrive`, `psx`...).

**Shared arcade artwork.** In Attract-Mode Plus, the arcade emulators that have a platform of their own (Naomi, Naomi 2, Atomiswave, FBNeo...) look in their own folder first and then in the `arcade` folder: the artwork of a set scraped for MAME also shows for the same set in Flycast or FBNeo. You can see it in the emulator's `.cfg`:

```text
artwork    snap            /home/fliperos/media/snap/naomi;/home/fliperos/media/preview/naomi;/home/fliperos/media/snap/arcade;/home/fliperos/media/preview/arcade
artwork    wheel           /home/fliperos/media/logo/naomi;/home/fliperos/media/logo/arcade
```

ES-DE reads the artwork from `~/media/.es-de/<system>/<type>`, where each type is a link to the right folder in `~/media`. It only looks in the system's own folder.

## Emulator command lines: KMS or X11

### What KMS and X11 are

Linux has two ways to put a program on the screen, and FliperOS uses both.

- **KMS** (Kernel Mode Setting, through the kernel's DRM driver) means the program draws **directly on the video card**, without any window system. It is the lightest and fastest path, with the least input lag, and the program changes the video mode itself. RetroArch (with its CRT SwitchRes, one mode per game) and the frontends (Attract-Mode Plus, ES-DE, Pegasus) run like this. The FliperOS wrapper is **`fliperos-kms-run`**: it starts the program on the console and, for RetroArch, adds the FliperOS settings (video driver, button mapping) on top of the user's.
- **X11** (Xorg, the classic Linux window system) is for programs that only know how to open a window: Flycast, PCSX2, Dolphin, Supermodel, Model 2 Emulator (in Wine), Hypseus, GroovyMAME. The FliperOS wrapper is **`fliperos-x11-run`**: it starts an Xorg just for that program, has **Switchres** create a video mode for the monitor chosen in Video Setup (640x240 at 15 kHz for the 480-line systems, so nothing flickers), opens the program full screen and closes Xorg when the program exits. Nothing else runs in that X: no desktop, no panel.

Rule of thumb: **RetroArch, in KMS; any other emulator, in X11.** If a program says *"Cannot open display"* or doesn't start in KMS, it needs X11. Both wrappers must be started from the console, as the frontends do: inside the LXDE desktop (which already is an X session), run the emulator directly.

The commands, as a frontend calls them:

```bash
# KMS: RetroArch with a core
/opt/fliperos/bin/fliperos-kms-run retroarch -L /opt/fliperos/retroarch/cores/fbneo_libretro.so "/home/fliperos/roms/retroarch/fbneo/sf2.zip"

# X11: the mode comes from /etc/fliperos/emulator-modes.conf
/opt/fliperos/bin/fliperos-x11-run flycast "/home/fliperos/roms/naomi/mvsc2.zip"

# X11 with a mode chosen on the spot (width x height @ Hz)
/opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 pcsx2 "/home/fliperos/roms/ps2/game.iso"

# GroovyMAME opens a game by its set name
/opt/fliperos/bin/fliperos-x11-run groovymame sf2
```

The X11 video mode of each program is in `/etc/fliperos/emulator-modes.conf` (one column for 15 kHz, another for 25/31 kHz and LCD; a program not in the table gets 320x240@60). Add a line there for a new program instead of repeating `--mode` everywhere. More on the modes in [Emulators](Emulators.md).

### Attract-Mode Plus

Each emulator is a file in `~/.attract/emulators/<name>.cfg` (in the cabinet's `~/config/attractmode`). The lines that matter:

```text
executable           /opt/fliperos/bin/fliperos-x11-run
args                 supermodel "[romfilename]"
workdir              $HOME
rompath              /home/fliperos/roms/model3/
romext               .zip
system               arcade
```

`[romfilename]` is the full path of the game file (keep it in quotes: file names have spaces), and `[name]` is the name without the extension, for emulators that open a game by name (GroovyMAME, Model 2). For a KMS program, `executable` is `/opt/fliperos/bin/fliperos-kms-run` and `args` starts with the program (`retroarch -L <core> "[romfilename]"`).

To add an emulator of your own: copy a `.cfg` from the folder with a new name, change those lines, give it a romlist (*Emulators > (the emulator) > Generate Collection/Rom List* in Attract-Mode's configuration, or Setup > AttractPlus ROM List for an arcade folder) and a display (*Displays > Add new display*, with that romlist). **The Setup rewrites the `.cfg` files it created itself** (the ones whose first line is `# Criado pelo FliperOS Setup`), to keep the artwork paths up to date: to change the command of one of them and keep your change, delete that first line.

### ES-DE

Each system is a `<system>` block in `~/ES-DE/custom_systems/es_systems.xml`:

```xml
<system>
  <name>model3</name>
  <fullname>Supermodel</fullname>
  <path>/home/fliperos/roms/model3</path>
  <extension>.zip .ZIP</extension>
  <command label="Supermodel">/opt/fliperos/bin/fliperos-x11-run supermodel %ROM%</command>
  <platform>arcade</platform>
  <theme>arcade</theme>
</system>
```

`%ROM%` is the game's path (ES-DE adds the quotes) and `%BASENAME%` the name without the extension (`/opt/fliperos/bin/fliperos-x11-run groovymame %BASENAME%`). A system can have more than one `<command>` with different labels: ES-DE lets you pick one per game (*Edit this game's metadata > Alternative emulator*). `<platform>` decides the scraper's platform and `<theme>` the system's look.

**Setup > Frontend rewrites the whole `es_systems.xml`** every time ES-DE is picked, so a system added by hand disappears. Keep a copy of your blocks and paste them back after using Setup > Frontend.

## Adding a new emulator

FliperOS sets up the emulators it ships by itself. For any other emulator (an AppImage, a package, something you built), there are four steps. If you follow them, the same command works in Attract-Mode Plus, ES-DE, Pegasus or the console.

### Step 1: install it and test it by hand

Put the program where the system finds it: a package (`sudo apt install ...`), or the binary or AppImage in `/usr/local/bin` (`chmod +x`). Then, in the console (*Exit to shell* in the FliperOS menu), open a game through the wrapper:

```bash
/opt/fliperos/bin/fliperos-x11-run myemu "/home/fliperos/roms/myemu/game.bin"
```

If it opens full screen, plays and returns to the console when you quit it, it will work from any frontend. Use `fliperos-kms-run` instead only if the program runs without X (most don't; see [What KMS and X11 are](#what-kms-and-x11-are)).

### Step 2: make the command frontend-proof

A frontend only knows how to run **one command with the game's path** and then wait for it to finish. The command must therefore follow a few rules:

- **Absolute paths**: start with `/opt/fliperos/bin/fliperos-x11-run` (or `fliperos-kms-run`), never just the program name. The frontends don't run a shell with your `PATH`.
- **The program right after the wrapper**: `fliperos-x11-run [--mode WxH@HZ] program [options] game`. The wrapper accepts a name in the `PATH` or the full path of an executable.
- **Full screen and no questions**: pass the emulator's own options for full screen, for skipping its welcome or update dialogs and for loading the game directly. Nobody should need a mouse.
- **It has to quit and stay in the foreground**: the emulator needs a way to exit with the panel or the keyboard (a hotkey or a menu), otherwise you are stuck in it. It also must not hand off to another process and exit: when the program the wrapper started ends, the wrapper closes its X and the frontend comes back.
- **The game path in quotes**: file names have spaces. Each frontend writes the path with its own placeholder (table below).

If the emulator needs more than that (environment variables, a config file chosen per game, a `cd` to its folder, Wine), **write a small launcher script** and point the frontends to it. The frontend then only passes the game, and every detail stays in one place:

```bash
#!/bin/bash
# /usr/local/bin/myemu-run GAME
export MYEMU_BIOS="$HOME/bios/myemu"
cd /opt/myemu || exit 1
exec /opt/myemu/myemu --fullscreen --no-gui "$1"
```

```bash
sudo chmod +x /usr/local/bin/myemu-run
/opt/fliperos/bin/fliperos-x11-run myemu-run "/home/fliperos/roms/myemu/game.bin"
```

The `exec` keeps the emulator as the program the wrapper waits for. This is how FliperOS opens Model 2 Emulator through Wine (`fliperos-model2`).

### Step 3: the video mode (X11 only)

`fliperos-x11-run` takes the mode from `/etc/fliperos/emulator-modes.conf` by the **program name** (the first word after the wrapper, without its path). Add a line:

```text
# program           15 kHz          25/31 kHz and LCD
myemu-run           320x240@60      640x480@60
```

Without a line, the program gets 320x240@60. Use 640x240 at 15 kHz for systems that draw 448 or 480 lines, and the system's own refresh rate when it isn't 60 Hz (Model 2 and 3: 57.524).

### Step 4: one folder and the command in each frontend

Create the game folder, for example `~/roms/myemu`. Setup > Frontend only creates the systems FliperOS knows about, so a new emulator has to be added by hand in each frontend you use. The command is the same everywhere; only the placeholders change:

| Frontend | Where | Game path | Name without extension |
| --- | --- | --- | --- |
| Attract-Mode Plus | `args` in `~/.attract/emulators/<name>.cfg` | `"[romfilename]"` | `[name]` |
| ES-DE | `<command>` in `~/ES-DE/custom_systems/es_systems.xml` | `%ROM%` (ES-DE adds the quotes) | `%BASENAME%` |
| Pegasus | `launch:` in `metadata.pegasus.txt` in the game folder | `"{file.path}"` | `{file.basename}` |

The same emulator in the three of them:

```text
# Attract-Mode Plus: ~/.attract/emulators/My Emulator.cfg
executable           /opt/fliperos/bin/fliperos-x11-run
args                 myemu-run "[romfilename]"
rompath              /home/fliperos/roms/myemu/
romext               .bin;.zip
```

```xml
<!-- ES-DE: inside <systemList> in ~/ES-DE/custom_systems/es_systems.xml -->
<system>
  <name>myemu</name>
  <fullname>My Emulator</fullname>
  <path>/home/fliperos/roms/myemu</path>
  <extension>.bin .zip</extension>
  <command label="My Emulator">/opt/fliperos/bin/fliperos-x11-run myemu-run %ROM%</command>
  <platform>arcade</platform>
  <theme>arcade</theme>
</system>
```

```text
# Pegasus: ~/roms/myemu/metadata.pegasus.txt
collection: My Emulator
extensions: bin, zip
launch: /opt/fliperos/bin/fliperos-x11-run myemu-run "{file.path}"
```

Then, in Attract-Mode Plus, generate the romlist and add a display (as in [Attract-Mode Plus](#attract-mode-plus) above). In Pegasus, add the folder to the list in `~/.config/pegasus-frontend/game_dirs.txt`. For the artwork, use a `~/media/<type>/<platform>` folder ([Artwork](#artwork)) in the emulator's `artwork` lines; for ES-DE, use the `<platform>` that the scraper should use.

**What the Setup keeps and what it rewrites.** A `.cfg` you created yourself, without the `# Criado pelo FliperOS Setup` line, is never touched, and neither is a `metadata.pegasus.txt` that already exists. Setup > Frontend does rewrite ES-DE's `es_systems.xml` and Pegasus's `game_dirs.txt` with only the folders it knows, so add your system again after using it.

## Quick checks

- **The system doesn't show up**: the folder must have at least one game file (the `_info.txt` doesn't count) and the frontend must be picked again in Setup > Frontend.
- **The game doesn't open**: with debug mode on (Setup > Debug mode) the emulator's output shows on the screen; otherwise it is saved in `/opt/fliperos/logs`. Try the same command in the console (*Exit to shell* in the FliperOS menu).
- **No artwork**: check the name (exactly the ROM name, without the extension, case included) and the platform folder, and in Attract-Mode the emulator's `artwork` lines.
