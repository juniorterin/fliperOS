A **custom game** is a game or program that is not a ROM of one of FliperOS's emulators: a PC game for Windows or Linux, an emulator you brought with one game, a script. FliperOS shows custom games in the frontends like any other system, opens them in a 15 kHz video mode, and gives them the flicker filter and the on-screen menu.

Everything is in **Setup > Games > Custom games**. There are three ways to add a game:

| Way | When |
|---|---|
| **Install a package** (`<game>.fliperos-customgame.zip`) | someone made the package, on their FliperOS or by hand |
| **Create a package** from a game folder | the game is on the cabinet, a USB stick or the network, and you want it complete (picture, video, text, controller map) and easy to copy to another FliperOS |
| **By its command** | quick: a group, a name, a command line and the video mode |

The [web panel](Web-panel-System.md#custom-games) has the same page in **System > Setup > Games > Custom games**, plus a table to add many games at once: rows typed or picked in lists, imported from a folder (one subfolder per game) or pasted from a spreadsheet. There, a Windows or Linux game in a folder is copied to `~/games/GROUP/NAME`, like an installed package.

## Contents

- [Step by step: adding your game from the cabinet](#step-by-step-adding-your-game-from-the-cabinet)
- [The screens](#the-screens)
- [Groups](#groups)
- [Installing a package](#installing-a-package)
- [Creating a package](#creating-a-package)
- [The package format](#the-package-format)
- [Adding a game by its command](#adding-a-game-by-its-command)
- [Windows games: PortProton](#windows-games-portproton)
- [The controller as a keyboard](#the-controller-as-a-keyboard)
- [Video mode, flicker filter and on-screen menu](#video-mode-flicker-filter-and-on-screen-menu)
- [Pictures, video and text](#pictures-video-and-text)
- [Packing a game folder (squashfs)](#packing-a-game-folder-squashfs)
- [Opening a custom game from another frontend](#opening-a-custom-game-from-another-frontend)
- [Where everything is](#where-everything-is)
- [Under the hood](#under-the-hood)
- [Problems](#problems)

## Step by step: adding your game from the cabinet

The game folder has to be somewhere the cabinet can read. Any of these works:

- **Over the network:** from a PC, copy the folder to the share `\\fliperos\FliperOS` (the home folder), for example into `games`. Or use the **web panel** (`http://fliperos.local:8081`) > Files.
- **On a USB stick or disk:** plug it in; it shows up under `/media/fliperos/<disk name>`.
- **Already in the cabinet**, in any folder of the home.

Then, with the controller:

1. **Setup > Games > Custom games.**
2. Open a group, or **Add group** for a new one (for example *PC games*). Each group is a system in the frontends.
3. Inside the group, choose **Package**.
4. **Name**: how the frontend shows the game.
5. **Windows or Linux**: a Windows game is a `.exe`; a Linux one is a program or a command.
6. **The game folder**: open it in the folder picker and choose *Use this folder*. Everything the game needs must be inside it.
7. **What opens the game**:
   - Windows: pick the `.exe` inside the folder. The first time, the Setup offers to download PortProton (about 3 GB, see [below](#windows-games-portproton)). Then choose which Wine runs it; keep the first one unless the game fails with it.
   - Linux: type the command, run inside the game folder (for example `./game.x86_64 -fullscreen`), or press *Browse* to pick the program and the Setup writes `./<program>` for you.
8. **Picture, video and text** (optional): pick each file, or type the text. Without them the game gets samples, which you can replace later.
9. **Video mode**: 240p, 480i or another resolution and refresh rate.
10. **Category, controls, buttons, players**: what the frontend shows and filters by.
11. The Setup writes `~/roms/custom/<group>/<game>.fliperos-customgame.zip` and asks whether to **install it now**. Say yes: the game folder is copied to `~/games/<group>/<game>` and packed.
12. Open the frontend: the game is in the system of its group.
13. **If the game only takes the keyboard**, open the on-screen menu during the game (by default Start + Down held for a second), choose **Controller configuration** and give each key a button (see [below](#the-controller-as-a-keyboard)). Save.

The zip stays in the group folder: copy it to another FliperOS (into its `~/roms/custom`) to install the same game there, complete, with its controller map.

To add a game quickly instead, step 3 is **Add games > By its command** (see [below](#adding-a-game-by-its-command)).

## The screens

**Setup > Games > Custom games** shows tiles:

- one tile per **group**, with its number of games; packages waiting to be installed in that group show in green (*2 NEW*);
- **Add group**: a new group;
- **New games**: every package waiting to be installed (only when there is one);
- **Packed**: the game folders kept in squashfs.

Inside a group:

- **Add games**: the packages of this group and the ones in `~/roms/custom`, and *By its command*;
- **Package**: creates a package from a game folder;
- **All new**: installs every package in `~/roms/custom/<group>` (only when there is one);
- one tile per **game**, with its picture and the kind of game and video mode (*WIN 240P*, *LINUX 480I*, *CMD 240P*).

A game tile opens:

- **Information and video mode**: the video mode, the category, the controls, the buttons and the players;
- **Make a package of it** (an installed package): a new zip with what the game has now;
- **Edit name and command** (a game added by its command);
- **Delete**. For an installed package you choose between keeping the game folder or deleting it too, with what the game saved in it.

A name that doesn't fit its tile runs from side to side when the tile is under the cursor. Without the graphical Setup (`ui=text`) the same screens are menus.

## Groups

A group is a folder, `~/roms/custom/<group>`, and a system in every frontend (the FliperOS frontend, Attract-Mode Plus, ES-DE, Pegasus). Group and game names can't be empty, start with a dot, or have `/` or `|`. A group with no games left is removed.

## Installing a package

Put the zip in one of two places (from the cabinet, the network share `\\fliperos\roms\custom`, or the web panel):

| Where | Group |
|---|---|
| `~/roms/custom/<group>/<game>.fliperos-customgame.zip` | that group, no question |
| `~/roms/custom/<game>.fliperos-customgame.zip` | asked when installing from *New games*; from a group's *Add games*, that group |

Then open **Setup > Games > Custom games**: the group shows *N NEW*. Choose the package in **Add games** or **New games**, or every package of the group with **All new**.

What installing does:

1. Checks the zip. A zip with an absolute path, a `..`, a link, an encrypted file or a file that isn't one of the [package's](#the-package-format) is refused, with the reason, and nothing is written. A bad zip shows in the list as *(cannot install)*.
2. Checks there is room for the game.
3. For a Windows game, offers PortProton if it isn't installed.
4. Copies the game folder to `~/games/<group>/<name>`. A Linux program loses its executable bit in a zip made on Windows: the Setup gives it back to every file that starts like a Linux program (ELF or `#!`).
5. Puts the `.ppdb` next to the `.exe`, the picture, video and text in `~/media`, and writes `<name>.cfg`, `<name>.key` and `<name>.sh` in the group folder.
6. Makes samples for the media the package didn't bring (the logo, for example).
7. Packs the game folder in [squashfs](#packing-a-game-folder-squashfs). If that fails (no room, for example), the folder stays loose and the game opens the same.
8. Updates the frontends.

**The zip stays where it was.** The installed game notes it, with its size and date, so it leaves the list of packages to install. If you replace it with a different zip of the same name, it shows up again (*replaces the one in …*); installing it puts the new game over the old one, and what the old one saved in its folder is lost. Deleting the game brings the zip back to the list.

## Creating a package

**Package** (inside a group) is the step-by-step of the [first section](#step-by-step-adding-your-game-from-the-cabinet). Some details:

- Every file picker of the assistant opens where the previous one stopped (the game folder, then the picture's folder...), and the next package starts there too (`~/.config/fliperos/customgame-last-dir`). The first time it starts at `~/games`, the plugged disks or the home.
- The `.exe` and the Linux program must be inside the game folder: the package stores the path relative to it.
- The text can be a `.txt` or typed on the on-screen keyboard.
- The zip is `~/roms/custom/<group>/<name>.fliperos-customgame.zip`. Pictures, videos and files that are already compressed are stored as they are; the rest is compressed.
- **Make a package of it** on an installed game starts from what it has: its settings, its media (not the samples), its `.key` and its `.ppdb`.

## The package format

`<game>.fliperos-customgame.zip`:

| File | Required | What it is |
|---|---|---|
| `<game>.cfg` | yes | the settings |
| `<game>/` | yes | the game folder, with all its files |
| `<game>.png`, `.jpg`, `.jpeg`, `.webp` or `.gif` | no | the picture (snap) |
| `<game>.mp4`, `.mkv`, `.webm`, `.avi`, `.mov` or `.flv` | no | the video |
| `<game>.txt` | no | the text the frontend shows |
| `<game>.key` | no | the [controller map](#the-controller-as-a-keyboard) |
| `<game>.ppdb` | no | PortProton's settings (Windows) |

`<game>` is the name of the `.cfg`; every other file must have the same name. A zip with everything inside one folder (made by right-clicking the folder on Windows) is accepted too, as are paths with `\`. `__MACOSX`, `.DS_Store`, `Thumbs.db` and `desktop.ini` are ignored.

The `.cfg` has one `key=value` per line; lines starting with `#` are comments:

```
name=Metal Slug X
platform=windows
exe=bin/mslugx.exe
mode=240p
category=Shooter / Walking
controls=joy8
buttons=3
players=2
```

| Key | Value |
|---|---|
| `name` | the name in the frontend (without it, the file name) |
| `platform` | `windows` or `native` |
| `exe` | Windows: the `.exe`, relative to the game folder |
| `command` | Linux: the command line, run inside the game folder |
| `mode` | `240p` (640x240), `480i` (640x480) or `WIDTHxHEIGHT@HZ`, for example `384x224@59.6` (without it, 240p) |
| `category` | a category of MAME's catver.ini, `Genre / Subgenre` |
| `controls` | one or more, separated by commas: `joy8 joy4 joy2 twin trackball spinner paddle positional analog pedal lightgun keyboard mahjong` |
| `buttons` | 0 to 8 |
| `players` | 1 to 8 |

An installed game's `.cfg` also has `folder=` (the game folder), `package=` and `package_stamp=` (the zip it came from, its size and date).

Making a package by hand: put the game folder and a `.cfg` like the one above side by side, add the optional files with the same name, and zip them.

## Adding a game by its command

**Add games > By its command** asks for a name, the command (as you would type it in a terminal, for example `wine ~/games/pang/pang.exe`) and the video mode. The command runs from the home folder. It is the quickest way for a script or an emulator you installed yourself, but it has no package: copying it means copying the folder and the entry by hand.

A `.sh` you put in a group folder by hand also shows up in the frontends.

## Windows games: PortProton

Windows games in a package run in **PortProton**, a launcher of Wine and Proton builds made for games. It is not in the image. You can install it ahead in **Setup > Games > Extras > PortProton** (choosing it again puts back the version of your FliperOS), or let the Setup offer it the first time a Windows package is created or installed. Either way:

1. It asks, and checks the internet.
2. Installs the packages PortProton needs (the 32-bit Vulkan and OpenGL libraries, `yad`, `bubblewrap`, `xvfb`...).
3. Downloads PortProton's scripts at a fixed version (checked by sha256) into `~/PortProton`.
4. Runs PortProton for the first time in a virtual screen, which downloads its runtime, DXVK, VKD3D, the default Wine and the Windows prefix. About 3 GB in all; the progress bar follows the size of `~/PortProton`.

PortProton's own installer only works with windows and a mouse. FliperOS installs it without any, and PortProton never updates itself (the version changes with FliperOS updates). Its downloads go over https: it asks for addresses without `https://`, which would go through port 80, blocked on many networks. On those networks the first download used to stop on an error window waiting for a click.

The **`.ppdb`** is PortProton's settings file for one `.exe`, next to it: `mslugx.exe.ppdb`. It says, for example, which Wine runs the game (`PW_WINE_USE`) and which prefix it uses. When you create a package, the Setup asks which Wine runs the game and PortProton writes the `.ppdb`; installing the package puts it back next to the `.exe`. The choices are Proton LG (PortProton's default), Wine LG, and any other build already downloaded in `~/PortProton/data/dist`.

Without PortProton (you said no, or it failed), a Windows package can still be installed: the game opens with the system's Wine (Setup > Games > Extras), if there is one.

## The controller as a keyboard

Many PC games only take the keyboard. While a custom game runs, `fliperos-buttons gamekeys` reads the controllers and presses keys on a virtual keyboard (*FliperOS game keys*), from the game's `<name>.key`:

```
p1_up=UP
p1_down=DOWN
p1_left=LEFT
p1_right=RIGHT
p1_b1=Z
p1_b2=X
p1_start=ENTER
p1_coin=5
p2_b1=LEFTCTRL
```

Each line is a player and a command of **Joysticks > Button mapping**: `up down left right`, `b1` to `b8` (the panel's buttons, in its order), `start` and `coin`. Because the map talks about *player 1 button 1* and not about a controller's button number, the same package works on any panel, with any controller.

The keys are Linux's names: the letters and digits, `F1` to `F12`, `ESC TAB ENTER SPACE BACKSPACE`, `UP DOWN LEFT RIGHT`, `LEFTCTRL RIGHTCTRL LEFTALT RIGHTALT LEFTSHIFT RIGHTSHIFT CAPSLOCK`, `INSERT DELETE HOME END PAGEUP PAGEDOWN PAUSE`, `MINUS EQUAL LEFTBRACE RIGHTBRACE BACKSLASH SEMICOLON APOSTROPHE GRAVE COMMA DOT SLASH`, and the keypad's `KP0` to `KP9`, `KPENTER KPPLUS KPMINUS KPASTERISK KPSLASH KPDOT`.

### Setting it up on the screen

Open the **on-screen menu** during the game (by default Start + Down held for a second; Frontend controls > OSD MENU changes it). A custom game has **Controller configuration** in place of *Emulator menu*:

- A keyboard on the screen. The keys that already have a button are lit.
- Move to a key and press Enter: it turns yellow and waits 5 seconds for a button. Press the controller button that should send it.
- The same button again on the same key clears it. A button that had another key moves to this one.
- The line under the keyboard says which buttons the key under the cursor has (`Z: P1 B1, P2 B1`).
- **Clear** empties the map, **Save** writes `<name>.key` and takes effect at once, **Back** leaves without saving.

While the menu is open, the buttons send no keys to the game. The keyboard fits every game resolution and the vertical monitor.

Several buttons can send the same key (player 1 and player 2 button 1 on `LEFTCTRL`, for example). The mapper doesn't take the controller from the game: a game that reads the joystick as well gets both.

## Video mode, flicker filter and on-screen menu

Each game opens in its own Xorg, in its video mode (`fliperos-x11-run --mode`): 240p, 480i (interlaced on a 15 kHz monitor) or any `WIDTHxHEIGHT@HZ`. Switchres makes the mode for the monitor chosen in the Setup.

Each game has its own row in **Video Setup > Interlaced hacks** (only the flicker filter: the mode is the game's), and the level chosen in the on-screen menu during the game stays with that game. Its name for the filter, the menu and the log is `custom_` plus the group and the name in lower case, with `_` for everything else: *PC games* / *Metal Slug X* is `custom_pc_games_metal_slug_x`, and its log is `/opt/fliperos/logs/custom_pc_games_metal_slug_x.log`.

Windows games are mostly 32-bit: the 32-bit flicker filter and on-screen menu go with them (built when Wine is installed from the Extras), and with DXVK the 32-bit Vulkan layer.

The frontend's **Emulator menu** shortcut opens the on-screen menu in a custom game (it has no emulator menu of its own). **Exit game** closes it like any other game.

## Pictures, video and text

The frontends look for the media in `~/media/<kind>/custom/<group>/<name>.<ext>` (the share `\\fliperos\media`):

| Kind | Folder | Formats |
|---|---|---|
| picture | `snap` | png, jpg, jpeg, webp, gif |
| video | `preview` | mp4, mkv, webm, avi, mov, flv |
| text | `texto` | txt |
| logo | `logo` | png, jpg, jpeg, webp, gif |
| box, marquee | `box`, `marquee` | png, jpg, jpeg, webp, gif |

A game without a kind gets a **sample** with its name and random colours, so it already shows with art: a picture, a 4-second video, a text that says which file to replace, and a logo. A sample is only made for a kind the game has in no format, so your own `.jpg` is never hidden behind a sample `.png`. The samples are noted with their checksums in `~/media/.custom-samples`: a sample you replaced counts as yours. Renaming a game takes your media along and makes new samples; deleting it removes its samples. A package's media is removed with the game (the zip brings it back).

The FliperOS frontend shows the `.txt` as the game's description, and the category, controls, buttons and players from the `.cfg` (what you change in its *Classify* screen wins). The Scraper skips the custom groups.

## Packing a game folder (squashfs)

A PC game can have thousands of small files. Packing turns its folder into one compressed file (zstd), mounted back in the same place: the game opens as before and can still write in its folder. An installed package is packed by itself; **Packed** packs any other game folder of the home, and lists the packed ones.

How a folder is packed:

1. `mksquashfs` writes `<folder>.squashfs` next to it.
2. The copy is checked (same number of files and bytes) and mounted once with its writable layer, as a trial. If a check fails, the folder stays as it was.
3. The loose files are removed and the `.squashfs` is mounted on the folder, with a writable layer in `.<folder>.squashfs-data` for what the game saves.

At boot, `fliperos-squashgames.service` mounts every packed folder again, before the frontend and the network share. Choosing a packed folder in **Packed** unpacks it back into a normal folder, with what the game saved. To copy a packed game to another computer, unpack it first, or make a package of it.

Close the game before packing, unpacking or deleting it. Packing and unpacking need free space about the size of the folder. Only folders inside the home can be packed, not hidden ones and not a path through a link. The list is `/etc/fliperos/squashgames.list`.

## Opening a custom game from another frontend

The FliperOS frontend, Attract-Mode Plus, ES-DE and Pegasus already list each group as a system: the Setup writes their configuration. For any other frontend, or a launcher of your own, the command that opens an installed custom game is its script:

```
/bin/sh "/home/fliperos/roms/custom/<group>/<name>.sh"
```

For example `/bin/sh "/home/fliperos/roms/custom/PC games/Metal Slug X.sh"`. Use the full path, in quotes when the group or the name has spaces. In a frontend that fills in the game's file, point the system at the folder `~/roms/custom/<group>`, with the extension `.sh` and the command `/bin/sh "%ROM%"` (ES-DE), `"[romfilename]"` with the executable `/bin/sh` (Attract-Mode), or `/bin/sh "{file.path}"` (Pegasus).

Run it from the console (tty), as the player `fliperos`, outside an X session: the script opens its own X server in the game's video mode. Its last line is the command itself:

```
exec /opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 --app custom_pc_games_metal_slug_x --wine \
  /opt/fliperos/bin/fliperos-customgame run "/home/fliperos/roms/custom/PC games/Metal Slug X.cfg"
```

- `--mode`: the video mode from the `.cfg`.
- `--app`: the game's name for the flicker filter, the on-screen menu and the log.
- `--wine`: only for a Windows game (or a command with `wine`), so the 32-bit filter and menu are loaded.
- `fliperos-customgame run <name>.cfg` opens the game: the command in the game folder, or the `.exe` in PortProton (the system's Wine without it), with the controller mapper next to it.

Changing the video mode or the information in the Setup rewrites the script, so call the `.sh` rather than a copy of its line.

## Where everything is

| What | Where |
|---|---|
| groups and entries | `~/roms/custom/<group>/<name>.sh` |
| settings | `~/roms/custom/<group>/<name>.cfg` |
| controller map | `~/roms/custom/<group>/<name>.key` |
| packages | `~/roms/custom/*.fliperos-customgame.zip`, `~/roms/custom/<group>/*.fliperos-customgame.zip` |
| installed game folders | `~/games/<group>/<name>` (packed: `~/games/<group>/<name>.squashfs` and `.<name>.squashfs-data`) |
| PortProton settings of a game | next to its `.exe`: `<exe>.ppdb` |
| media | `~/media/<kind>/custom/<group>/<name>.<ext>` |
| samples made | `~/media/.custom-samples` |
| last folder of the package assistant | `~/.config/fliperos/customgame-last-dir` |
| PortProton | `~/PortProton` |
| logs | `/opt/fliperos/logs/custom_<group>_<name>.log` |
| packed folders | `/etc/fliperos/squashgames.list` |

## Under the hood

| Program | What it does |
|---|---|
| `fliperos-customgame` | `inspect ZIP` (checks a package and prints its `.cfg`), `pending` (the packages waiting), `install ZIP --group G` (installs one), `pack` (makes one), `run CFG` (opens a game) |
| `fliperos-portproton` | `check`, `install` (as root, the Setup), `versions`, `edit-db EXE VAR=VALUE`, `run EXE` |
| `fliperos-portproton-curl` | the curl of PortProton's downloads, over https |
| `fliperos-buttons gamekeys KEY` | the controller as a keyboard; its socket `$XDG_RUNTIME_DIR/fliperos-gamekeys/sock` answers the on-screen menu (`reload`, `mute`, `unmute`, `capture SECONDS`) and exits with the game |
| `fliperos-squashgames` | `pack`, `unpack`, `remove`, `list`, `mount-all`, `umount-all` (as root) |
| `fliperos-x11-run`, `fliperos-x11-client` | the game's own Xorg in its video mode, with the flicker filter and the on-screen menu |

The System Update rewrites every entry's script (`customgames_refresh`), and gives a `.cfg` to the entries made by command before packages existed.

## Problems

- **The game doesn't open from the frontend.** Read its log, `/opt/fliperos/logs/custom_<group>_<name>.log` (also in the web panel > Logs). For a package, check that the game folder exists: a disk or packed folder that is not mounted leaves it empty.
- **"is not a FliperOS game package".** The reason is shown: usually a file with another name next to the `.cfg`, a missing game folder, or a `.cfg` value out of the list above.
- **A Linux game says "permission denied".** Its program must be executable: the Setup fixes the ones that start like a Linux program; for a launcher script without `#!`, run it through `bash ./script.sh` in the command.
- **The keys don't reach the game.** Check that the game window has the focus (most do, alone in their Xorg), that the map was saved (*Save* in Controller configuration), and Joysticks > Button mapping: the map follows it.
- **PortProton's install failed.** The details are in `/var/log/fliperos-setup.log`. It needs the internet and about 3 GB free in the home; choosing a Windows package again, or Setup > Games > Extras > PortProton, retries.
- **Not seen on a cabinet yet** (TODO.md): a real `.exe` through PortProton, the filter and on-screen menu inside PortProton's runtime, and the key capture with a real panel.
