**Setup > Games > Folders** has two ways to put your games on another disk: **Folder shortcuts**, for one folder at a time, and **External storage**, for a whole disk. External storage has two kinds: the **FliperOS folders** (the structure FliperOS makes on a second disk) and the **Batocera filesystem** (a disk that already keeps its games in the folders Batocera uses). It can also **format** a disk, and open a **network folder** (a NAS, RetroNAS, a Windows PC) as one more disk.

| You have | Use | Details |
| --- | --- | --- |
| A new, empty disk | **External storage > FliperOS folders**, then *Use it* (or *Format this disk* first) | [Below](#fliperos-folders-a-second-disk) |
| A disk with the games in `batocera/roms/snes`, `megadrive`, `psx`... | **External storage > Batocera filesystem** | [Below](#batocera-filesystem) |
| The games on another computer of the house (a NAS, RetroNAS, Windows, a Batocera's share) | **External storage > Network folder** | [Below](#network-folder) |
| The games of one system on a disk, in a folder of their own | **Folder shortcuts** | [Below](#folder-shortcuts) |

## Folder shortcuts

A shortcut sends one FliperOS folder to another disk. It was called **Link** before (*Link this to another folder*, *Unlink the custom folder*): the same thing, now with clearer names. Example: `~/roms/mame` is on the disk of the cabinet, and your external hard disk has the MAME games in `HD/mame`. In **Folder shortcuts** pick `roms`, then `mame`, then **Point it to a folder on another disk** and open `HD/mame`. From then on the games show up as if they were in `~/roms/mame`: the frontends, the Downloader, the Scraper and the network share all use them.

- Nothing is copied or deleted. The folder used until then stays beside it, renamed with `old-` in front (`~/roms/old-mame`).
- **Change where it points** swaps the target. **Remove the shortcut** brings the `old-` folder back to its name; nothing is deleted from the other disk.
- The list says what each root keeps (`roms` games, `bios` BIOS files, `media` art and videos...) and, for a shortcut, where it points. A disk that is not connected shows as *not found* and that folder is left alone. **How shortcuts work** on top of the list tells the same with an example.
- Linking a folder of one system to a folder that holds many consoles (`snes`, `megadrive`, `psx`...) asks first: the games would not show up. Use the Batocera filesystem for that.

The same shortcuts are in the [web panel](Web-panel-System.md) (**System > Setup > Games > Folders**). Everything that looks in a folder goes through the shortcut, and the screens that tell you where to put something (the custom game packages, for one) say where the folder really is: `~/roms/custom-packages (on HD: batocera/roms/custom-packages)`, or *the disk HD is off*.

## FliperOS folders: a second disk

A data disk that is plugged in (a USB hard disk, an SSD, another internal disk of 8 GB or more) is mounted by itself in `/media/fliperos/<label>`, and gets a **`fliperos` folder with the whole structure** of the cabinet inside it: `roms` (one folder per emulator and per RetroArch core), `bios`, `media` (one folder per type of art), `nvram` and `save`. Only the folders are made: nothing on the main disk changes, and a small stick, a read-only disk or a CD is left alone. `storage_auto=off` in `fliperos.conf` turns this off. A disk that already has a Batocera filesystem gets nothing written: see below.

**External storage > FliperOS folders** lists the disks (label, type, size, free space, and *in use* when the cabinet already uses it). Pick one:

- **Use it:** the five folders in the home of the cabinet become shortcuts to the disk's `fliperos` folders (the same as **Folder shortcuts**, for the five at once). From then on everything the Downloader, the Scraper and the art packs download, and the saves and the nvram, go to the second disk, next to the main one. What was in the home before stays beside, as `~/old-roms`, `~/old-bios`…, nothing is lost or copied. Put your ROMs, saves and art straight in the disk's folders (on a PC, or by the network share) and the frontends see them.
- **Only prepare the folders:** makes the structure and changes nothing else.
- **Format this disk:** erases the disk and makes it new (below).
- **Back to the main disk** (on the list): the folders of the home are the main disk's again (the `old-` ones come back); nothing is deleted from the second disk.

### Format this disk

For a disk that has nothing you want, or that Linux can't use as it is. It works on the partition you picked, in three steps, and the first answer is **No**:

1. It says what goes: the model, the size, the partition, the type and how much is in use. A disk with a Batocera filesystem says so.
2. **ext4** or **exFAT**. ext4 is the best for FliperOS: the fastest, and it keeps links and owners; Windows can't open it. exFAT opens on Windows and Mac too, but is slower and has no links, so the art is kept apart (`~/.local/share/fliperos/media-links`).
3. A last menu, with **Cancel** first and *Yes, erase everything* second.

It refuses a disk the FliperOS folders or a Batocera filesystem are using (stop using it first), a disk with a packed game folder on it, one with RAID, LVM or encryption, a read-only one, and any disk that also holds the system or the installation media. When it is done the disk is called `FliperOS-HD`, empty, and the cabinet offers to use it right away.

### The question when a disk is plugged in

The first time a disk like that is plugged in (identified by the UUID of its file system), the FliperOS frontend asks, **once**, whether to use it for the ROMs, BIOS, art, saves and downloads (**YES** / **NO**; **NO** is the one selected and back on the panel is a NO). A button pressed in the first second is ignored, so someone already pressing a button in the list does not turn the disk on by mistake. **YES** is the same as *Use it* above. **NO** shows where to change it later (**Setup > Games > Folders > External storage**, also in the web panel) and the disk never asks again. A disk already in use is not offered, and neither is one that does not serve (a small stick). While a game is open, or any frontend menu, the question waits for the frontend to be free; it does not appear in the commercial mode.

## Batocera filesystem

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/fliperos-setup/gui/icons/batocera.png" width="64" alt="Batocera">

A disk that was set up for Batocera keeps the games by **console**, not by emulator: `batocera/roms/snes`, `megadrive`, `psx`, `atomiswave`... (the folder can also be `userdata` or the disk itself). FliperOS has one folder per emulator and per RetroArch core, so the two don't line up by themselves. The Batocera filesystem fixes that by reading the disk where it is and letting you **choose what opens each console**.

**External storage > Batocera filesystem** lists the disks that have such folders. Pick one:

- **Use it (everything it has):**
  - each console folder FliperOS knows (about a hundred names, from `nes` and `snes` to `dreamcast`, `psx`, `gamecube`, `mame`, `neogeo`...) becomes a **system of the frontends**, with the core FliperOS prefers for it, working at once. The games are not copied or moved;
  - each folder beside `roms` that has a FliperOS counterpart becomes a shortcut of it: `bios`, `saves` (as `save`), `nvram`, `media` and `snap` (as `media/snap`). What was in your home stays beside, as `old-bios`...;
  - the **FliperOS folders that Batocera doesn't have** are made beside the consoles and linked: `namco2x6`, `fightcade`, `hypseus` and `custom-packages`, so the packages of the [custom games](Custom-games.md) and the Namco games live on the disk too. `custom` stays on the cabinet: it only holds the launchers the Setup makes.
  - A disk that is read only only gets its consoles. A shortcut you made yourself to another place is left as it was.
- **Cores of the consoles:** the list of consoles, each with its core. Pick one to choose another core: the RetroArch cores that handle that system, and the standalone emulator when there is one (PCSX2, DuckStation, Flycast, Dolphin, the Sega Model emulator...). The best one is marked, and a core that is not installed says *downloads on first use*. **Not used** takes the console out of the frontends.
- **Best core for all:** gives every console the core FliperOS prefers.
- **Stop using it:** the consoles leave the frontends and the shortcuts of the home go back. Nothing is deleted from the disk, and the folders made beside the consoles stay there.

Nothing is written inside a console folder. A folder name that FliperOS has no emulator for is left out, and the list says how many.

**The art and the game details Batocera keeps.** The frontends show what Batocera saved beside the games: the pictures and videos its scraper (or Skraper) put in `images/`, `videos/` or another folder named in `gamelist.xml`, and from `gamelist.xml` the title, the description, the year, the developer, the genre, the number of players, the language and the region. A game with no line in `gamelist.xml` still gets the files named the way Batocera's scraper names them (`images/Game-image.png`, `-thumb`, `-marquee`, `videos/Game-video.mp4`). The art FliperOS has for a game (its own [Scraper](Scraper.md), a media pack) wins, and Batocera's fills what is missing. A title or a field the Scraper wrote, or that you edited, is kept. This works in the FliperOS frontend, the web panel, Attract-Mode Plus and ES-DE (which also gets Batocera's `gamelist.xml` when it has no list of its own for that console). A [ROM package](Custom-games.md) of a Batocera console carries all of it: the art, the descriptions, the game details and, for a RetroArch core, the saves Batocera made (`saves/<console>`), placed where the FliperOS that installs it reads them. The manuals (`manuals/`) have no place in FliperOS yet and stay out.

**Which folder.** A disk can keep Batocera's folders in more than one place: `batocera/roms`, `userdata/roms` and `roms` in the root of the disk (the `/userdata` of a disk that Batocera itself set up). FliperOS compares them and uses the one with the **most games** (the `gamelist.xml`, `images` and `videos` beside the games don't count), so an old `batocera` folder with only the sample game of each console doesn't win over the real library. A `roms` folder that FliperOS wrote its own folders into (the `retroarch` folder and the like, after you pointed `~/roms` at it) is still Batocera when it has the consoles. A disk that was set up on the other folder is set up again on the right one when the cabinet starts or the disk is plugged in (and by update 108): the consoles keep the core you chose, `~/bios`, `~/save` and the other shortcuts follow, and nothing is moved or deleted on the disk. A shortcut you made yourself to another place is left as it was.

**The question:** when a disk with a Batocera filesystem is plugged in, or the cabinet turns on with it connected, the frontend asks **once** whether to use it (**YES** / **NO**, **NO** selected), in a card that says how many consoles it found. It does not make the `fliperos` folder on that disk. **YES** is the same as *Use it* above; **NO** says where to do it later. It is asked once per disk, apart from the question of the FliperOS folders.

## Network folder

A folder shared by another computer of the house (SMB: a NAS, [RetroNAS](https://github.com/retronas/retronas), Windows, a Linux with Samba, the share of a Batocera) opens on the cabinet as **one more disk**, in `/media/fliperos/<name>`, at every boot. The games are played from there: nothing is copied to the cabinet. It is what an `fstab` line with `cifs` did on Batocera or RGBuntu, without editing `fstab` by hand (it belongs to the system, so the desktop's text editor can't save it).

**External storage > Network folder > Add a network folder** asks:

1. The computer: its IP (`192.168.1.10`) or name.
2. Your user on it (empty: as a guest) and the password. The password stays on the cabinet in a file only the system reads (`/etc/fliperos/netshares/<name>.cred`), never on a command line.
3. The shared folder, from the list the computer gives (or typed, when it does not list them).

It opens the folder once to check it, saves it, and then says what to do with it, by what it has inside:

- **Batocera folders** (`batocera/roms/<console>`, the copy RetroNAS keeps for Batocera, or a Batocera's own share): it offers the [Batocera filesystem](#batocera-filesystem) right away. Each console becomes a system of the frontends, read from the network.
- **A `fliperos` folder:** it offers the [FliperOS folders](#fliperos-folders-a-second-disk), as for a second disk.
- **Anything else:** use a [Folder shortcut](#folder-shortcuts) to a folder in it (`~/roms/mame` to `retronas/roms/arcade/mame`, say), or make a `fliperos` folder there with **FliperOS folders**.

The list in **Network folder** shows each saved folder (`//computer/folder`), *in use* when the games use it and *not answering* when the computer is off. Pick one to **Use it** (the same choice as above) or **Forget this folder**: FliperOS stops opening it and nothing is deleted on the computer. A folder the games still use asks you to stop using it first.

- **The computer turns on later:** the folder opens the first time something looks into it, so a NAS that starts after the cabinet works without a restart. While it is off, the lists skip it after one 2-second check (instead of waiting for each folder), and its consoles are left out of the frontends until it is back.
- **Old servers** that only speak SMB1 (an old NAS, Windows XP) are opened with `vers=1.0` by themselves.
- The folder is writable when the computer lets your user write: the Batocera filesystem makes its own system folders beside the consoles, and the saves can live there.
- The [ROM Cleaner](ROM-Cleaner.md) lists the saved network folders too, without asking the password again.
- The same is in the [web panel](Web-panel-System.md) (**System > Setup > Games > Network folder**), where the IP and the password are easier to type: add a folder, list the folders of a computer, **Use its consoles** for Batocera folders, and **Forget**.

## How it works

- Network folder: `lib/netshare.sh` and `screens/storage.sh` (`screen_netshares`). Each saved folder is a pair of systemd units in `/etc/systemd/system`, `media-fliperos-<name>.mount` (`Type=cifs`, the options that worked when it was checked, `TimeoutSec=15`) and `.automount` (in `remote-fs.target`), marked with a `# fliperos-netshare` line; nothing goes into `/etc/fstab`. `fliperos-setup --netshare list|shares HOST [USER]|add HOST SHARE [USER]|remove NAME|layout MOUNT` does it from a terminal (the password on standard input). `netshare_offline` is the check the disk lists and the Batocera consoles make before touching a folder of a computer that is off.
- Folder shortcuts: `lib/folders.sh` (`folders_link`, `folders_unlink`, `folders_shown`, `folders_looks_like_systems`) and `screens/folders.sh`; the state is what is on disk, and the list for the cloud backup is `~/.config/fliperos/folders.list`.
- FliperOS folders: `lib/storage.sh` and `screens/storage.sh`. `fliperos-setup --storage list|prepare MOUNT|use MOUNT|unuse|offer MOUNT|answer MOUNT yes|no [batocera]|auto MOUNT|format-info MOUNT|format MOUNT ext4|exfat` does it from a terminal. `fliperos-automount` runs `--storage auto MOUNT` after mounting a disk; the queue is `/var/lib/fliperos/storage/offer` and the answers are in `/var/lib/fliperos/storage/answered` (`UUID`, and `batocera:UUID` for the other question), read and written by `gui/festorage.py`.
- Format: `storage_format` unmounts, `wipefs -a`, `mkfs.ext4 -F -m 0` or `mkfs.exfat`, and lets `fliperos-automount` mount it again as `FliperOS-HD`. `exfatprogs` comes in the image.
- Batocera filesystem: `lib/batocera.sh`; the table of console names, the cores and what each console opens is `config/batocera-systems.list` (installed as `/usr/local/share/fliperos/batocera-systems.list`). The choices are `~/.config/fliperos/batocera.list` (`console<TAB>folder<TAB>core`), in the cloud backup. A console is a frontend system with the key `batocera/<name>` (`scraper_detect` and `scraper_attract_emulator`, `lib/scraper.sh`), so ES-DE, Pegasus, Attract-Mode Plus, the FliperOS frontend and the web panel all list it. `fliperos-setup --batocera detect|scan|list|cores|set|unset|auto|use|unuse|repair|extras` does it from a terminal (`repair` sets a disk up again on the folder `detect` chooses today, when it was set up on another).
- Batocera's art and game details: `config/fliperos-batocera-media` (`/opt/fliperos/bin`), run by `frontends_lists` (`frontends_batocera`, every time the lists are rebuilt, as the player) and by `fliperos-rompack` before it lists or packs a console. It reads `gamelist.xml` (and the names of Batocera's scraper) and makes, on the system disk (an NTFS or exFAT disk and a network folder don't keep links), `~/.local/share/fliperos/batocera-media/<type>/batocera/<console>/<game>.<ext>`: one link per game and type (`snap`, `box`, `logo`, `preview`) to FliperOS's own file in `~/media` or, when there is none, to Batocera's. The web panel and the FliperOS frontend (`media_dirs` in `fliperos-web`) and Attract-Mode (a second path in each `artwork` line) look in `~/media` first and then there; ES-DE's art folders of a Batocera console point there. The descriptions go to `~/media/texto/batocera/<console>/<game>.txt` only where there is none (one written by it follows `gamelist.xml`; the Scraper's stays), and the details fill the empty fields of the console's list in `~/.local/share/fliperos/lists` before the edits of the **+** are applied over them. A console is read again only when `gamelist.xml` or one of the folders changes (`.state/batocera-<console>.json`). Nothing is written inside the Batocera folders. `fliperos-batocera-media refresh KEY FOLDER LIST EXTENSIONS` and `meta KEY FOLDER [GAME...]` (JSON) run it from a terminal.
- Where a folder really is: `folders_shown` (and `fliperos-setup --folders shown <folder>`) is the one text every screen and the web panel use for a folder that can be on another disk.

See also: [ROMs, BIOS and artwork](ROMs.md), [Games Setup](Setup-Games.md), [Custom games](Custom-games.md), [Web panel: System](Web-panel-System.md).
