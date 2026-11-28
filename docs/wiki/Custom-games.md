A **custom game** is a game or program that is not a ROM of one of FliperOS's emulators: a PC game for Windows or Linux, an emulator you brought with one game, a script. FliperOS shows custom games in the frontends like any other system, opens them in a 15 kHz video mode, and gives them the flicker filter and the on-screen menu.

Everything is in **Setup > Games > Custom games**. Packages have two areas of their own, **Install games** and **Create package**, and every package lives in one folder, `~/roms/custom-packages` (the network share `\\fliperos\roms\custom-packages`). There are three ways to add a game:

| Way | When |
|---|---|
| **Install games**: a package (always named `<game>.fliperos-customgame.zip`, [structure below](#the-package-format)) | someone made the package, on their FliperOS or by hand |
| **Create package** from a game folder | the game is on the cabinet, a USB stick or the network, and you want it complete (picture, video, text, controller map) and easy to copy to another FliperOS |
| **By its command** (inside a group) | quick: a group, a name, a command line and the video mode |

The [web panel](Web-panel-System.md#custom-games) has the same page in **System > Setup > Games > Custom games**, in three tabs: **Games** (with a table to add many games at once: rows typed or picked in lists, imported from a folder or pasted from a spreadsheet), **Install packages** and **Create package**. There, a Windows or Linux game in a folder is copied to `~/games/GROUP/NAME`, like an installed package. A folder laid out like a package (see [A folder with the package's structure](#a-folder-with-the-packages-structure)) brings its picture, video, text, controller map and PortProton settings by itself, there and in **Create package** on the cabinet.

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
2. Choose **Create package**, then **From a game folder**. The group comes later, when the package is installed.
3. **Name**: how the frontend shows the game.
4. **Windows or Linux**: a Windows game is a `.exe`; a Linux one is a program or a command.
5. **The game folder**: open it in the folder picker and choose *Use this folder*. Everything the game needs must be inside it. If the folder has the [package's structure](#a-folder-with-the-packages-structure) (`<game>.jpg`, `<game>.logo.png`, `<game>.icon.png`, `<game>.mp4`, `<game>.txt`, `<game>.key`, `<game>.ppdb` or `<game>.cfg` next to the folder `<game>`), those files are picked by themselves: steps 6 and 7 come already filled.
6. **What opens the game**:
   - Windows: pick the `.exe` inside the folder, then **what runs it**: PortProton (the default), Wine or Wine Staging. If the game doesn't open or runs badly with one, make the package again with another (see [Windows games: PortProton, Wine or Wine Staging](#windows-games-portproton)). With PortProton, the first time the Setup offers to download it (about 3 GB); then choose which of its Wine builds runs the game; keep the first one unless the game fails with it.
   - Linux: type the command, run inside the game folder (for example `./game.x86_64 -fullscreen`), or press *Browse* to pick the program and the Setup writes `./<program>` for you.
7. **Picture, logo, icon, video and text** (optional): pick each file (the logo is a `.png`, `.jpg` or `.webp`; it travels in the package as `<game>.logo.png` or `.logo.jpg`), or type the text. The **icon** is the game's icon in the desktop menu (a `.png`, `.jpg`, `.webp` or `.ico`; it travels as `<game>.icon.png`); without one, the picture is the icon. Without the others the game gets samples, which you can replace later.
8. **Video mode**: 240p, 240p hack (Mugen), 480i or another resolution and refresh rate. Then **16:9 crop**, for a game that only runs in a widescreen picture (see [16:9 crop](#169-crop)).
9. **Category, controls, buttons, players, year, developer**: what the frontend shows and filters by. The year (four digits) and the developer show next to the game's name in the frontend list; leave them empty and the icons move up into that line. Then **Does the game already work with the joystick?** (asked when the game has no `.key` yet): say yes and the package carries an empty `<game>.key`, so the on-screen menu does not ask for a controller map (the same as the *Joystick* box in the web panel).
10. The Setup writes `~/roms/custom-packages/<game>.fliperos-customgame.zip` and asks whether to **install it now**. Say yes and pick the group (or a new one, for example *PC games*; each group is a system in the frontends): the game folder is copied to `~/games/<group>/<game>` and packed. At the end it asks whether to delete the package; keep it to install the game again or copy it to another FliperOS.
11. Open the frontend: the game is in the system of its group.
12. **The first time the game opens**, without a `<game>.key`, the on-screen menu opens by itself on **Controller configuration**: give each key the game uses a button (see [below](#the-controller-as-a-keyboard)) and Save. A game that takes the joystick by itself: Save with no key marked, and it doesn't ask again.

A kept zip stays in `~/roms/custom-packages`: copy it to another FliperOS (into its `~/roms/custom-packages`) to install the same game there, complete, with its controller map.

To add a game quickly instead, open a group and choose **Add by its command** (see [below](#adding-a-game-by-its-command)).

## The screens

**Setup > Games > Custom games** shows tiles:

- one tile per **group**, with its number of games;
- **Add group**: a new group;
- **Install games**: the packages in `~/roms/custom-packages` (*2 NEW* when some are waiting), see [Installing a package](#installing-a-package);
- **Create package**: a package from a game folder or from an installed game, see [Creating a package](#creating-a-package);
- **Packed**: the game folders kept in squashfs.

Inside a group:

- **Add by its command**: a game or program opened by a command line;
- one tile per **game**, with its picture and the kind of game and video mode (*WIN 240P*, *LINUX 480I*, *CMD 240P*);
- **Group icon**: the drawing of the group (see [Groups](#groups));
- **Group logo**: a one-colour logo for the marquee and the frontend's ribbon (see [Groups](#groups));
- **Rename group**: another name for the group, with everything that goes with it (see [Groups](#groups));
- **Delete group**: the whole group (see [Groups](#groups)).

A game tile opens:

- **Information and video mode**: the video mode, the category, the year, the developer, the controls, the buttons and the players;
- **Make a package of it** (an installed package): a new zip with what the game has now;
- **Edit name and command** (a game added by its command);
- **Delete**. For an installed package you choose between keeping the game folder or deleting it too, with what the game saved in it.

A name that doesn't fit its tile runs from side to side when the tile is under the cursor. Without the graphical Setup (`ui=text`) the same screens are menus.

## Groups

A group is a folder, `~/roms/custom/<group>`, and a system in every frontend (the FliperOS frontend, Attract-Mode Plus, ES-DE, Pegasus). Group and game names can't be empty, start with a dot, or have `/` or `|`. Deleting the last game of a group removes the group when nothing else is left in its folder.

**Group icon** (inside the group, in the Setup; the web panel has no button for it) picks one of 19 drawings (gamepad, game box, arcade cabinet, joypad, joystick, light gun, wheel, keyboard, emulator, monitor, sound, disk, chip, desktop PC, network, cloud, lab flask, disc, trophy). The group's tile in the Setup and its tile in the frontend's ribbon (when the group has no logo of its own) show it. The choice is the line in `~/roms/custom/<group>/.icon`; without it the group keeps the default drawing.

**Group logo** (inside the group; in the web panel, **Edit the group**, the pencil next to its name, with the name and the logo in one window) gives the group a logo like the ones the systems have: **one colour**, shown on the marquee (Pixelcade and ZeDMD slide it in and blink it twice when you move to the group in the frontend), in the frontend's ribbon and at the top of the group's list. The frontend paints it in its own white and the marquee in its cyan, so only the **drawing** of the image counts, not its colours:

- **Upload an image** (web panel) or give its path (Setup): PNG, JPG or WebP. With a transparent background, the opaque part is the drawing; with no transparency, whatever differs from the background is, so a dark logo on white and a light one on black both work. An image with nothing to draw (one flat colour) is refused and the group keeps what it had;
- **Pick one of the logos we already have** (a list with a preview, in the Setup and in the web panel): the same ones the systems use, for when you don't want to upload yours. A logo of a system that has the same name as the group never wins over the one you chose for the group.

The result is the file `~/roms/custom/<group>/.logo.png`, white on a transparent background, at most 400 pixels high. With a logo, the frontend's ribbon shows it instead of the icon; **Remove the logo** brings the icon back. Changing it shows in the frontend within a few seconds, without restarting it.

**Rename group** (inside the group; in the web panel, the pencil next to the group's name) changes the name of the group and takes along everything that carries it: the folder `~/roms/custom/<group>` (with the icon and the logo), the group's game folders in `~/games` (the packed ones, in squashfs, are unmounted, moved and mounted again), the pictures, videos and texts in `~/media/<kind>/custom/<group>` (the sample ones are made again with the new name), each game's script and settings, the flicker filter, the OSD profile of each game, and the frontend's favourites and play counts of the group. It refuses a name that another group already has, or a `~/games/<name>` folder that has something else in it, and it stops with nothing changed when a game of the group is open. The frontends are updated at the end.

**Delete group** (inside the group; in the web panel, the bin next to the group's name) removes the whole group, even an empty one or one whose folder holds other files:

1. It says first what goes: its games, and the other files in its folder by name (a misnamed zip, a manual...).
2. When some game has a game folder in `~/games`, or the group's folder holds packages, it asks whether those go too:
   - **Keep**: the game folders stay in `~/games/<group>`, and the packages go to `~/roms/custom-packages`, where they show in **Install games** (a zip of the same name already there: the same file is dropped, a different one gets `(<group>)` in its name). The packages already in `~/roms/custom-packages` always stay.
   - **Delete them too**: the game folders (with what the games saved), the packages and the media you put in `~/media/<kind>/custom/<group>` go as well.
3. Each game goes as with its own **Delete**, then the folder `~/roms/custom/<group>` with whatever was left in it, and the empty media folders. The frontends are updated.

A game folder in use (the game open) stops it before anything of that game is deleted: close the game and choose *Retry*.

## Installing a package

Every package lives in one folder, `~/roms/custom-packages`. Put the zip there from a PC (the network share `\\fliperos\roms\custom-packages`), from a USB stick, or with the web panel (**Games**: drop the zip on the dashed area and it installs by itself in the group you choose). **Create package** writes there too, and in the web panel it asks whether to install what it made.

Then open **Setup > Games > Custom games > Install games**. The list shows every package of the folder:

| In the list | What choosing it does |
|---|---|
| `Name (Windows game)` | asks the group (the last one used comes marked, or a new group), installs it, then asks whether to delete the package |
| `Name (Windows, newer than the one in <group>)` | the zip changed since it was installed: installs it over the game in its group |
| `Name (installed in <group>)` | install it again, or delete the package (the game stays installed) |
| `file.zip (cannot install)` | says why, and offers to delete the file |

**Install all new** puts every new package in one group (asked once), installs the newer ones over their games, and at the end asks whether to delete the installed packages.

**From the desktop**: double-click a `<game>.fliperos-customgame.zip` in the file manager (in `~/roms/custom-packages`, in Downloads, on a USB stick, anywhere) and the install window opens: the same steps as choosing it in **Install games**. The group comes marked as the one the game is already in (or the last one used); a game that is already installed asks whether to install over it. Select several packages and press Enter, and one window installs them all in one group. A package from the packages folder asks at the end whether to delete the zip; one from anywhere else is left where it is. Right-click > **Open with** still lets you open the zip with the archive manager (the type is a zip: `application/x-fliperos-customgame`).

**A package in parts** (`GAME.fliperos-customgame.zip.001`, `.002`...: the [web panel](Web-panel-System.md#custom-games) cuts a package into parts of the size you choose, 2000 MB by default, the file limit of Telegram's free plan, and the bot of the group reads them as one package). Double-clicking **any** of the parts (not only the `.001`) opens the same install window: it finds the other parts in the same folder, checks them (a missing number, parts of different sizes, or a last part that is not there are said before anything is copied), joins them into `~/roms/custom-packages/GAME.fliperos-customgame.zip` with a progress bar and goes on as for a zip. Joining needs the free space of the whole package, once more. Parts chosen together (all five, for example) join once; if the zip is already in the packages folder it asks before replacing it. The parts that were in `~/roms/custom-packages` go away after joining; parts on a USB stick or in Downloads stay where they are (the type is `application/x-fliperos-customgame-part`, not a zip). From the command line: `fliperos-customgame parts PART` shows the set and what is missing, `fliperos-customgame join PART` joins it.

Zips from before this folder existed (loose in `~/roms/custom` or in the group folders) move to `~/roms/custom-packages` by themselves, when the System Update runs or Custom games opens; a game installed from one stays installed.

What installing does:

1. Checks the zip. A zip with an absolute path, a `..`, a link, an encrypted file or a file that isn't one of the [package's](#the-package-format) is refused, with the reason, and nothing is written. A bad zip shows in the list as *(cannot install)*. So does a real package with another name (`Pang.zip`): the reason says the name it must have (`Pang.fliperos-customgame.zip`). Any other zip in those folders is left alone.
2. Checks there is room for the game.
3. For a Windows game, offers PortProton if it isn't installed.
4. Copies the game folder to `~/games/<group>/<name>`. A Linux program loses its executable bit in a zip made on Windows: the Setup gives it back to every file that starts like a Linux program (ELF or `#!`).
5. Puts the `.ppdb` next to the `.exe`, the picture, video and text in `~/media`, and writes `<name>.cfg`, `<name>.key` and `<name>.sh` in the group folder.
6. Makes samples for the media the package didn't bring (the logo, for example).
7. Packs the game folder in [squashfs](#packing-a-game-folder-squashfs). If that fails (no room, for example), the folder stays loose and the game opens the same.
8. Updates the frontends.

**After installing, you choose whether the zip stays.** A kept zip shows as *installed in …*: the installed game notes it, with its size and date. If you replace it with a different zip of the same name, it shows as newer; installing it puts the new game over the old one, and what the old one saved in its folder is lost. Deleting the game makes the zip new again. A deleted zip doesn't touch the game.

## Creating a package

**Create package** has two ways: **From a game folder** is the step-by-step of the [first section](#step-by-step-adding-your-game-from-the-cabinet), and **From an installed game** packs a Windows or Linux game already in a group, with what it has now (the same as **Make a package of it** on the game: it brings the settings and the `.key` you changed after installing). The web panel's **Create package** tab is the same form, without the group, and can also make **many packages at once** from a table. Some details:

- Every file picker of the assistant opens where the previous one stopped (the game folder, then the picture's folder...), and the next package starts there too (`~/.config/fliperos/customgame-last-dir`). The first time it starts at `~/games`, the plugged disks or the home.
- A game folder with the [package's structure](#a-folder-with-the-packages-structure) fills the picture, the logo, the video, the text, the `.key` and the `.ppdb` by itself, and the `.exe` when its `<game>.cfg` names one (the `.exe` and Wine questions are skipped then). Picking the opened zip uses the game folder inside it.
- The `.exe` and the Linux program must be inside the game folder: the package stores the path relative to it.
- The text can be a `.txt` or typed on the on-screen keyboard.
- The zip is `~/roms/custom-packages/<name>.fliperos-customgame.zip`, and shows in **Install games**; one with that name already there is replaced only if you say so. Pictures, videos and files that are already compressed are stored as they are; the rest is compressed.
- **Make a package of it** on an installed game starts from what it has: its settings, its media (not the samples), its `.key` and its `.ppdb`.

## The package format

A package is always named `<game>.fliperos-customgame.zip`, and always has this structure:

```
<game>.fliperos-customgame.zip
├─ <game>.cfg    the settings (required)
├─ <game>.jpg    the picture (.png, .webp... too)
├─ <game>.logo.png   the logo over the picture (a .png with a transparent background; <game>.logo.jpg or .webp too)
├─ <game>.icon.png   the game's icon in the desktop menu (optional; .jpg, .webp or .ico too)
├─ <game>.mp4    the video
├─ <game>.txt    the text the frontend shows
├─ <game>.key    controller → keyboard (optional: the on-screen menu makes it the first time)
├─ <game>.ppdb   PortProton's settings (Windows games)
└─ <game>/       the game's files (packed in squashfs when installed)
```

| File | Required | What it is |
|---|---|---|
| `<game>.cfg` | yes | the settings |
| `<game>/` | yes | the game folder, with all its files |
| `<game>.png`, `.jpg`, `.jpeg`, `.webp` or `.gif` | no | the picture (snap) |
| `<game>.logo.png` (or `.jpg`, `.jpeg`, `.webp`) | no | the logo (wheel): the frontends show it over the picture; installed, it is `~/media/logo/custom/<group>/<game>.png` |
| `<game>.icon.png` (or `.jpg`, `.jpeg`, `.webp`, `.ico`) | no | the icon of the game in the desktop menu (Games); installed, it is `~/media/icon/custom/<group>/<game>.png`. Without it, the picture is the icon |
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
year=1999
developer=Nazca Corporation
```

| Key | Value |
|---|---|
| `name` | the name in the frontend (required) |
| `platform` | `windows` or `native` (required) |
| `exe` | Windows: the `.exe`, relative to the game folder |
| `runner` | Windows: what runs it, `portproton` (the default, without the line), `wine` or `wine-staging` |
| `command` | Linux: the command line, run inside the game folder |
| `mode` | `240p` (640x240), `240p-hack` (640x240 on the tube, the game sees 640x480), `480i` (640x480) or `WIDTHxHEIGHT@HZ`, for example `384x224@59.6` (without it, 480i) |
| `category` | a category of MAME's catver.ini, `Genre / Subgenre` |
| `controls` | one or more, separated by commas: `joy8 joy4 joy2 twin trackball spinner paddle positional analog pedal lightgun keyboard mahjong` |
| `buttons` | 0 to 8 |
| `players` | 1 to 8 |
| `year` | four digits (1900 to 2099); the frontend shows it next to the name |
| `developer` | who made the game, up to 80 characters; the frontend shows it after the year |

An installed game's `.cfg` also has `folder=` (the game folder), `package=` and `package_stamp=` (the zip it came from, its size and date).

**The minimum** is the folder `<game>/` with the game's files and `<game>.cfg` with `name=`, `platform=` and `exe=` (Windows) or `command=` (Linux). Everything else is optional; without `mode=` the game opens in 640x480i.

Making a package by hand: put the game folder and a `.cfg` like the one above side by side, add the optional files with the same name, and zip them.

**Checking a package.** The list of packages shows every problem a package has at once, each on its own line: a missing `<game>.cfg` or game folder, a `.cfg` without `name=`, `platform=`, `exe=` or `command=`, an `.exe` that is not in the folder, files outside the structure, a wrong video mode, controls, buttons or players, a wrong name. An absolute path, a `..`, a link, a special file or a password stops the check at once: such a zip is never opened further.

### A folder with the package's structure

The same files loose in a folder (the zip opened, or kept that way on a disk) are recognized when you choose the folder, in **Package** on the cabinet and in the web panel (one game, or **Import from a folder**). The folder you choose can be:

| You choose | The game folder | The other files |
|---|---|---|
| the opened zip: a folder with `<game>/` and `<game>.cfg` (or only `<game>.*` files around `<game>/`) | `<game>/` inside it | next to `<game>/` |
| the game folder itself | that folder | next to it, with its name (`Metal Slug X/` and `Metal Slug X.jpg`) |
| the game folder, without files next to it | that folder | a picture or video inside it with the game's name, or named `snap`, `screenshot`, `cover`, `title`, `preview`, `video`, `trailer`, `gameplay`... |

Names are compared without case, spaces or `_` (`Metal_Slug_X.jpg` goes with `Metal Slug X/`). The logo is `Metal Slug X.logo.png` next to the folder, or inside it a file called `logo`, `wheel`, `marquee` or `gamelogo` (`Metal Slug X.png` inside the folder is the picture, never the logo). The `<game>.cfg` counts only when it is a FliperOS one (`platform=windows` or `native`); a game's own `.cfg` is left alone. What it says fills the `.exe` or the command, the video mode, the category, the players, the buttons and the controls.

## Adding a game by its command

**Add by its command** (inside a group) asks for a name, the command (as you would type it in a terminal, for example `wine ~/games/pang/pang.exe`) and the video mode. The command runs from the home folder. It is the quickest way for a script or an emulator you installed yourself, but it has no package: copying it means copying the folder and the entry by hand.

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

**PortProton, Wine or Wine Staging.** Each Windows game says what runs it (`runner=` in its `.cfg`), chosen when the package is created, in the Setup or in the web panel's **Create package** (one package or the table):

| Runner | What it is | Installed from |
|---|---|---|
| PortProton (default) | Wine and Proton builds made for games, with DXVK, in a container of their own | Setup > Games > Extras > PortProton, or offered with the first Windows game |
| Wine | the system's Wine | Setup > Games > Extras > Wine |
| Wine Staging | the newest Wine from WineHQ, with fixes not in Wine yet (it takes the place of Wine) | Setup > Games > Extras > Wine Staging |

**OpenGL or Vulkan.** Whatever runs the game, it draws with **Vulkan** (DXVK for Direct3D 9 to 11, VKD3D-Proton for 12) or with **OpenGL** (Wine's own WineD3D) according to the driver of the video card that has the CRT, the one you chose in Video Setup:

| Driver of the CRT's card | Renders with |
|---|---|
| **amdgpu** | Vulkan (when Mesa's Vulkan is installed) |
| **radeon** | OpenGL: the radeon driver has no Vulkan |
| **NVIDIA** (proprietary) | Vulkan; with nouveau, OpenGL |
| **Intel** | Vulkan from Broadwell on (device id 0x1600 and later); Ironlake, Sandy Bridge, Ivy Bridge and Haswell use OpenGL |

PortProton gets it as `PW_VULKAN_USE` in the game's `.ppdb` (0 = OpenGL, 2 = DXVK and VKD3D-Proton): a card without Vulkan always goes to 0, and with Vulkan a game that has no Vulkan choice goes to 2 (a 1 or a 6 that a package brings stays). It is written only when the value changes. Wine and Wine Staging (and the Fightcade room) get it from the DLL overrides FliperOS sets when the game opens: with Vulkan, the DXVK and VKD3D-Proton DLLs of the prefix are used when it has them; with OpenGL, Wine's own are, even if the prefix has DXVK. `wine_renderer=vulkan` or `wine_renderer=opengl` in `fliperos.conf` forces one of them (`auto`, the default, follows the driver).

Some games only open, or run better, with one of them. The `.ppdb` only goes with PortProton. When the game's runner isn't installed on a cabinet, the game opens with the first of the others that is (PortProton, then Wine, then Wine Staging), and the game's log says so.

**Mods (BepInEx, MelonLoader, ASI Loader).** These mod loaders get into the game through a DLL next to the `.exe` that takes the place of a Windows one (`winhttp.dll`, `version.dll`, `winmm.dll`, `dinput8.dll` or `dsound.dll`). Wine loads its own copy of that DLL first, so the mod never loaded. When the game's folder has a loader (a `doorstop_config.ini` or `.doorstop_version`, a `MelonLoader` folder, or `.asi` files in the folder, `scripts/` or `plugins/`), FliperOS sets that DLL to native first (`n,b`) when the game opens. In PortProton this goes into the `WINEDLLOVERRIDES` of the `.ppdb`, because PortProton ignores the one from outside. In Wine and Wine Staging it goes into the environment. An override already there for that DLL is kept.

**A light gun in a PC game.** The GunCon 2 reaches the game as an absolute mouse:

| Gun | In the PC game |
| --- | --- |
| Trigger | left click |
| A and C | right click |
| B | middle click |
| Start | key `1` |
| Select | key `5` |

Games that keep the pointer free (menus, most arcade ports) aim where the gun points. Many 3D shooters lock the pointer and turn mouse *movement* into aim, so the sight moves slowly and drifts from where the gun points. Those need the game's own light gun or arcade mod. For example, *The House of the Dead Remake* needs Argonlefou's ArcadeMod (BepInEx) with **Input type: single player** in `ArcadeMod_Config.ini` (`InputType=0`). Its multiplayer mode (`InputType=1`) reads the guns from DemulShooter, a Windows program that doesn't run here. The mod's Start and coin keys are `1` and `5`, the same as the gun's Start and Select.

The [screen flash](Light-guns.md#screen-flash) works in PC games too, including PortProton's, with the same settings. Without it the gun lost its aim over the dark parts of a game.

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

The `.key` rarely comes ready: you make it here. A custom game with no `.key` opens the on-screen menu by itself, straight on Controller configuration, two seconds after the game shows (once each time the game opens; *NO KEYS YET* in the corner). **Save** writes the `.key`, even with no key marked, and then the game stops asking; **Back** closes the menu without saving, and it asks again next time. A package made with **Joystick** ticked (web panel) or *yes* to "Does the game already work with the joystick?" (Setup) carries that empty `.key` from the start, so a game that takes the joystick by itself never asks.

Any other time, open the **on-screen menu** during the game (by default Start + Down held for a second; Frontend controls > OSD MENU changes it), go to **Controller configuration** and choose **Joystick to keyboard**:

- A keyboard on the screen. The keys that already have a button are lit.
- Move to a key and press Enter: it turns yellow and waits 5 seconds for a button. Press the controller button that should send it.
- The same button again on the same key clears it. A button that had another key moves to this one.
- The line under the keyboard says which buttons the key under the cursor has (`Z: P1 B1, P2 B1`).
- **Clear** empties the map, **Save** writes `<name>.key` and takes effect at once, **Back** leaves without saving.

While the menu is open, the buttons send no keys to the game. The keyboard fits every game resolution and the vertical monitor.

Several buttons can send the same key (player 1 and player 2 button 1 on `LEFTCTRL`, for example). The mapper doesn't take the controller from the game: a game that reads the joystick as well gets both.

## Video mode, flicker filter and on-screen menu

Each game opens in its own Xorg, in its video mode (`fliperos-x11-run --mode`): 240p, 240p hack, 480i (interlaced on a 15 kHz monitor) or any `WIDTHxHEIGHT@HZ`. Switchres makes the mode for the monitor chosen in the Setup.

**240p hack (Mugen)** is for a Windows game that only opens full screen at 640x480, like M.U.G.E.N with `GameWidth = 640` and `GameHeight = 480`: in plain 240p it shows a white screen with "Error detected" (`mugen.log`: `trying 640x480x16 mode ... failed`), because the Wine of PortProton only offers modes up to the size of the screen. With the hack the tube stays at 640x240 (true 240p, no flicker), the X screen is 640x480 scaled down to it (`xrandr --scale 1x2`, mode `640x240@60/640x480` in the `.cfg`), and picom with vsync stops the tearing of games that draw through X without OpenGL (M.U.G.E.N with `RenderMode = System`). A game that opens at 320x240 or 640x240 by itself stays in plain 240p or `320x240@60`.

### 16:9 crop

For a game that only runs in a widescreen (16:9) picture. Without it, such a game on a 4:3 tube comes out squeezed or with black bars. With **16:9 crop** on, the game opens in a 16:9 X screen (1280x720, `FLIPEROS_CROP_SCREEN` changes it) and the tube shows only the middle of it, in 4:3: the full height, nothing squeezed, the sides of the picture cut off (`xrandr --transform`, the same mechanism as the 240p hack's scale; the crop wins over the 240p hack when both are set).

- **Where to set it:** the *16:9 crop* box in **Create package** (web panel, one package or the table) with its explanation, *Yes/No* in the Setup's Create package, the game's information in the Setup, the edit window of an installed game, and **Video configuration > 16:9 crop** in the on-screen menu. It is `crop169=1` in the game's `.cfg` and travels in the package.
- **When it counts:** the X screen is made when the game opens, so a change in the on-screen menu or in the edit window counts the next time the game opens.
- **On-screen menu:** while the game runs with the crop, the menu and the volume and achievement bars are drawn only in the middle three quarters of the picture, the part the tube shows (so the letters come out a third wider than usual).
- **What the game sees:** the whole 1280x720 screen. The X server would report the tube's part (960x720) as the monitor, and a widescreen game would open in that 4:3 window with black bars, so the crop also sets a 1280x720 monitor (`xrandr --setmonitor`), which the window manager and SDL games use as it is. A Windows game (Wine, PortProton) asks the RandR extension instead, so while it runs with the crop its Wine prefix gets `UseXRandR=N` (under `[Software\\Wine\\X11 Driver]` in `user.reg`, with a `FliperosCrop169` mark) and the line is removed when it opens without the crop. The first time a game opens in a prefix that Wine hasn't made yet, there is no `user.reg` to change: open the game once more.
- A card that can't make the bigger screen opens the game without the crop.

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
| icon (desktop menu only; optional, never gets a sample) | `icon` | png, jpg, jpeg, webp, ico |
| box, marquee | `box`, `marquee` | png, jpg, jpeg, webp, gif |

A game without a kind gets a **sample** with its name and random colours, so it already shows with art: a picture, a 4-second video, a text that says which file to replace, and a logo. A sample is only made for a kind the game has in no format, so your own `.jpg` is never hidden behind a sample `.png`. The samples are noted with their checksums in `~/media/.custom-samples`: a sample you replaced counts as yours. Renaming a game takes your media along and makes new samples; deleting it removes its samples. A package's media is removed with the game (the zip brings it back).

The FliperOS frontend shows the `.txt` as the game's description, and the category, year, developer, controls, buttons and players from the `.cfg` (what you change in its *Classify* screen wins). The Scraper skips the custom groups.

## Packing a game folder (squashfs)

A PC game can have thousands of small files. Packing turns its folder into one compressed file (zstd), mounted back in the same place: the game opens as before and can still write in its folder. An installed package is packed by itself; **Packed** packs any other game folder of the home, and lists the packed ones.

How a folder is packed:

1. `mksquashfs` writes `<folder>.squashfs` next to it.
2. The copy is checked (same number of files and bytes) and mounted once with its writable layer, as a trial. If a check fails, the folder stays as it was.
3. The loose files are removed and the `.squashfs` is mounted on the folder, with a writable layer in `.<folder>.squashfs-data` for what the game saves.

At boot, `fliperos-squashgames.service` mounts every packed folder again, before the frontend and the network share. Choosing a packed folder in **Packed** unpacks it back into a normal folder, with what the game saved. To copy a packed game to another computer, unpack it first, or make a package of it.

Close the game before packing, unpacking or deleting it. Packing and unpacking need free space about the size of the folder. Only folders inside the home can be packed, not hidden ones and not a path through a link. The list is `/etc/fliperos/squashgames.list`.

## Opening a custom game from another frontend

**On the desktop** (LXDE), the menu's **Games** lists every custom game, once, with its **icon** (the optional *Icon* field of Create package, and of the game's art in the web panel; without one, its picture). Choosing one closes the desktop, opens the game on the CRT in its video mode (`fliperos-launch custom <name>.sh`) and brings the desktop back when it closes. The Setup, the web panel and the System Update keep the entries up to date (`~/.local/share/applications/fliperos-custom_*.desktop`). There is no *Custom games* submenu any more: it showed each game twice, in Games and inside it, and the update that removes the duplicates deletes it (`~/.config/menus/applications-merged/fliperos-custom-games.menu`).

**Double click on a package** (on the desktop, in a folder or on a USB stick) installs it: the desktop closes and the Setup opens on the CRT in 240p and full screen, straight to the install screen, as **Install games** does ([The Setup from the desktop](Desktop.md#the-setup-from-the-desktop)).

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
| packages | `~/roms/custom-packages/*.fliperos-customgame.zip` (the share `\\fliperos\roms\custom-packages`) |
| last group a package went to | `~/.config/fliperos/customgame-last-group` |
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
| `fliperos-customgame` | `inspect ZIP` (checks a package and prints its `.cfg`), `pending` (the packages waiting), `install ZIP --group G` (installs one), `pack` (makes one), `synced` (is the package of an installed game up to date with its settings, key map and art?), `stamp` (a zip's size and date), `add` (copies a game folder, the web panel), `scan` and `found` (the games of a folder and what came with them in the package's structure), `run CFG` (opens a game; when it ends, closes whatever the game left running: SIGTERM, then SIGKILL 3 s later) |
| `fliperos-portproton` | `check`, `install` (as root, the Setup), `versions`, `edit-db EXE VAR=VALUE`, `run EXE` |
| `fliperos-portproton-curl` | the curl of PortProton's downloads, over https |
| `fliperos-buttons gamekeys KEY` | the controller as a keyboard; its socket `$XDG_RUNTIME_DIR/fliperos-gamekeys/sock` answers the on-screen menu (`reload`, `mute`, `unmute`, `capture SECONDS`) and exits with the game |
| `fliperos-squashgames` | `pack`, `unpack`, `remove`, `list`, `mount-all`, `umount-all` (as root) |
| `fliperos-x11-run`, `fliperos-x11-client` | the game's own Xorg in its video mode, with the flicker filter and the on-screen menu |

The System Update rewrites every entry's script (`customgames_refresh`), and gives a `.cfg` to the entries made by command before packages existed.

**Nothing stays running after the game.** `run` becomes a *subreaper* (`PR_SET_CHILD_SUBREAPER`): a process of the game whose parent dies is handed to it instead of to `init`, so it stays inside the tree the frontend closes. When the game ends, `run` sends SIGTERM to whatever is left and SIGKILL 3 s later. Before, each PortProton game closed with the exit shortcut left a `pv-adverb` and a `winedevice.exe` behind: the frontend's SIGTERM killed PortProton's container (`srt-bwrap`), its `pv-adverb` went to `init` and missed the SIGKILL 4 s later, still waiting for a `winedevice.exe` that never quits.

## Problems

- **The game doesn't open from the frontend.** Read its log, `/opt/fliperos/logs/custom_<group>_<name>.log` (also in the web panel > Logs). For a package, check that the game folder exists: a disk or packed folder that is not mounted leaves it empty.
- **"is not a FliperOS game package".** The reason is shown: usually a file with another name next to the `.cfg`, a missing game folder, or a `.cfg` value out of the list above.
- **A Linux game says "permission denied".** Its program must be executable: the Setup fixes the ones that start like a Linux program; for a launcher script without `#!`, run it through `bash ./script.sh` in the command.
- **The keys don't reach the game.** Check that the game window has the focus (most do, alone in their Xorg), that the map was saved (*Save* in Controller configuration), and Joysticks > Button mapping: the map follows it.
- **PortProton's install failed.** The details are in `/var/log/fliperos-setup.log`. It needs the internet and about 3 GB free in the home; choosing a Windows package again, or Setup > Games > Extras > PortProton, retries.
- **Not seen on a cabinet yet** (TODO.md): a real `.exe` through PortProton, the filter and on-screen menu inside PortProton's runtime, and the key capture with a real panel.
