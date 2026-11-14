[Attract-Mode Plus](https://github.com/oomek/attractplus) is an optional frontend, with the [Arcadeflow](https://github.com/zpaolo11x/Arcadeflow) theme. Pick it in **Setup > Games > Frontend**: it comes from the FliperOS repository inside the image, and the Setup sets up every games folder in it.

## Setting it up

Picking it in **Setup > Games > Frontend** makes, for each folder with games:

- an **emulator** (`~/.attract/emulators/<name>.cfg`): the command that opens the game, and where its art is;
- a **display** in `~/.attract/config/displays.cfg`;
- a **game list** (romlist, `~/.attract/romlists/<name>.txt`) from the files in the folder.

A folder that gets its first games later gets its emulator and display by itself, the next time Attract-Mode Plus opens.

Every display also gets the **default filters**: All Games, Most Played (the 25 most played), by genre (Driving, Fighting, Shooting…), by manufacturer (© Capcom, © SNK, © Sega…) and by release year. A display with filters of its own is left as it is.

## Arcadeflow

Arcadeflow is the default theme. Its license doesn't allow shipping it, so **Setup > Games > Frontend** downloads version 17.7 from its GitHub (55 MB) when you pick Attract-Mode Plus.

- **Every display uses it by default.** A display you put on another layout (Attract-Mode's menu, **Tab > Displays**) stays there.
- **On a 15 kHz tube** (320x240) turn on **Small screen** and **Low Spec mode** in its options, or go back to Basic if the text is too small: Arcadeflow is drawn for high-resolution screens and uses shaders on every frame.
- **In 640x240** FliperOS makes the theme draw in 4:3 at 320x240 and stretch to the width of the mode, like the emulators do, so nothing comes out twice as wide.
- **The select button** keeps the theme's default: the first press opens the context menu over the game (information, favourite, tags), the second opens the game. To open the game at the first press, set **Context menu button: None** in the theme's options.
- **Clones are grouped** (Attract-Mode Plus's **Group Clones**, in **Tab > General**): one tile per family; opening a game with clones shows the list of its clones. Turn Group Clones off to have every clone as a tile of its own.

Without Arcadeflow (no network when you picked the frontend; pick it again to retry), the displays use FliperOS's **Basic** layout: the same look as Attract-Mode Plus's own, drawn at the screen's real resolution with slightly larger letters.

## Game lists and real names

A list made only from the files shows the file name: `mvsc2u` instead of *Marvel Vs. Capcom 2 New Age of Heroes*. Two ways to get the real names:

- **Setup > Games > AttractPlus ROM List**, for the arcade folders (`mame`, `naomi`, `naomi2`, `atomiswave`, `model2`, `model3` and the RetroArch arcade cores). No internet needed: the name, year, manufacturer, players, controls and emulation status come from GroovyMAME's game list (the MAME 0.139 list for `mame2010`), with the clones and bootlegs under their parent. It also creates an **Arcade** display with all those folders together.
- **Setup > Games > Scraper**, for every folder, with names and descriptions from a site, plus the art ([Scraper](Scraper.md)).

Each one rewrites the lists it works on, so whichever ran last wins; the art is kept either way.

**New games in a folder.** Each time Attract-Mode Plus opens (and in **Setup > Games > Frontend**, **Folders** and **AttractPlus ROM List**), FliperOS brings the romlists up to date: a new file goes in under its file name, and a game whose file is gone leaves. A file still being copied (`.part`) enters when the copy ends. An arcade list with real names is only redone by **AttractPlus ROM List**.

To rebuild a list yourself:

- **Setup > Games > AttractPlus ROM List** or **Scraper**;
- in Attract-Mode itself: **Tab > Emulators > (the emulator) > Generate Collection/Rom List**;
- or delete `~/.attract/romlists/<name>.txt` and pick the frontend again.

**AttractPlus ROM List also cleans up:** it gives every folder with games the emulator, display and list it is missing, and deletes the empty lists and their displays, like the ones Attract-Mode Plus makes by itself on its first run for each program it finds. Arcadeflow's collections (`AF ...`) are left alone, and nothing is removed while Attract-Mode Plus is open.

## Artwork

The art is in `~/media`, one folder per type, as for every frontend ([ROMs, BIOS and artwork](ROMs.md#the-folders-in-)). In the emulator's `.cfg`, the `artwork` lines say where:

| `~/media` folder | `artwork` line |
| --- | --- |
| `snap` (screenshots) and `preview` (videos) | `snap` |
| `logo` | `wheel` |
| `box` | `flyer` |
| `marquee` | `marquee` |
| `texto` (descriptions) | the overview (`~/.attract/scraper/<emulator>/overview` is a link to it) |

**Shared arcade artwork.** The other arcade folders (Model 2, Model 3, Naomi, Atomiswave, the MAME and FBNeo cores) look in their own folder first, then in the `mame` one, so the art of a set you have for MAME also shows in the other emulators:

```text
artwork    snap            /home/fliperos/media/snap/naomi;/home/fliperos/media/preview/naomi;/home/fliperos/media/snap/mame;/home/fliperos/media/preview/mame
artwork    wheel           /home/fliperos/media/logo/naomi;/home/fliperos/media/logo/mame
```

## Adding an emulator by hand

Each emulator is a file in `~/.attract/emulators/<name>.cfg` (`~/config/attractmode` on the share). The lines that matter:

```text
executable           /opt/fliperos/bin/fliperos-x11-run
args                 supermodel "[romfilename]"
workdir              $HOME
rompath              /home/fliperos/roms/model3/
romext               .zip
system               arcade
```

`[romfilename]` is the full path of the game file (keep the quotes: file names have spaces), and `[name]` the name without the extension, for emulators that open a game by name (GroovyMAME, Model 2). For a KMS program, `executable` is `/opt/fliperos/bin/fliperos-kms-run` and `args` starts with the program (`retroarch -L <core> "[romfilename]"`).

Copy a `.cfg` with a new name, change those lines, give it a romlist (**Generate Collection/Rom List**) and a display (**Displays > Add new display**). Which command, KMS or X11: [Adding an emulator](Adding-games.md#adding-a-new-emulator).

**The Setup rewrites the `.cfg` files it created** (the first line is `# Criado pelo FliperOS Setup`), to keep the art paths up to date. To keep your change in one of them, delete that first line.

## The Pixelcade and the ZeDMD

FliperOS's *Pixelcade* plugin tells a [Pixelcade](Pixelcade.md) or [ZeDMD](ZeDMD.md) marquee the game you pick, and the screensaver starts their idle animation.

## How it works

- **The package:** Attract-Mode Plus comes from FliperOS's APT repository of prebuilt `.deb`s, like GroovyArcade's `groovy-ux-repo` (`packaging/build-deb.sh`, `packaging/make-repo.sh`, recipes in `packaging/packages/`). The repository ships inside the image (`/opt/fliperos/repo`, `deb [trusted=yes] file:/opt/fliperos/repo ./`), so it installs without internet.
- **Arcadeflow** goes to `~/.attract/layouts/Arcadeflow`. FliperOS turns off its check for new versions (it waits for an answer on the keyboard) and its *Game not available indicator* (it refused a clone that lives inside its parent's zip, which GroovyMAME opens by name), and adds one line so the clone list shows at once. The 640x240 stretch is the theme's **Resolution W x H** option, set each time the launcher opens from the console's mode, and undone in a 4:3 mode.
- The **Basic** layout is `config/attractplus-layouts/Basic`, installed in `~/.attract/layouts`, where it wins over the packaged one (which draws at a fixed 640x480 and blurs at 320x240).
- **Arcadeflow's own copy of the list:** the theme reads each game once into `~/.attract/romlists/<name>.db1`, then only adds what is missing. When a romlist is rebuilt, FliperOS empties the older `.db1` before Attract-Mode Plus opens; favourites and play counts (`.db2`) stay. A game scraped inside Arcadeflow whose fields came back empty gets the romlist's values back.
- **The logo of each display:** Arcadeflow shows a system's logo and picture when the display's name is one it knows (`data_systems.txt`). Before Attract-Mode Plus opens, FliperOS adds each of its displays to the right system (`fliperos-arcadeflow systems`): Sega Model 3 for Supermodel, GameCube for Dolphin, FBNeo for its core, the platform for the other cores. A RetroArch MAME core is a system of its own (**MAME 2010**), with a logo FliperOS adds to the theme's font and picture (`fliperos-arcadeflow-art`, with fontTools and Pillow); the theme's font is kept as `.fliperos-orig`, and what was added is listed in `fliperos_systems.txt`.
- **Real names:** `fliperos-romclean romlist`, from `groovymame -listxml` (about a minute the first time), with the category from the `catver.ini` in `/usr/local/share/fliperos/romclean` (or yours in `~/roms/mame`). In the MAME folder the list also has the clones that live inside the parent's zip; other emulators open a file, so only clones with their own file are listed.
- Naomi, Naomi 2 and Atomiswave may share one folder with the whole Flycast romset: the ROM List keeps each system's games in its list, by the BIOS in each set's `romof` chain.

See also: [Frontends](Frontends.md), [Adding games](Adding-games.md), [Scraper](Scraper.md).
