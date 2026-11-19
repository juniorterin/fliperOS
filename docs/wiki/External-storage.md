**Setup > Games > Folders** has two ways to put your games on another disk: **Folder shortcuts**, for one folder at a time, and **External storage**, for a whole disk. External storage has two kinds: the **FliperOS folders** (the structure FliperOS makes on a second disk) and the **Batocera filesystem** (a disk that already keeps its games in the folders Batocera uses). It can also **format** a disk.

| You have | Use | Details |
| --- | --- | --- |
| A new, empty disk | **External storage > FliperOS folders**, then *Use it* (or *Format this disk* first) | [Below](#fliperos-folders-a-second-disk) |
| A disk with the games in `batocera/roms/snes`, `megadrive`, `psx`... | **External storage > Batocera filesystem** | [Below](#batocera-filesystem) |
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

**The question:** when a disk with a Batocera filesystem is plugged in, or the cabinet turns on with it connected, the frontend asks **once** whether to use it (**YES** / **NO**, **NO** selected), in a card that says how many consoles it found. It does not make the `fliperos` folder on that disk. **YES** is the same as *Use it* above; **NO** says where to do it later. It is asked once per disk, apart from the question of the FliperOS folders.

## How it works

- Folder shortcuts: `lib/folders.sh` (`folders_link`, `folders_unlink`, `folders_shown`, `folders_looks_like_systems`) and `screens/folders.sh`; the state is what is on disk, and the list for the cloud backup is `~/.config/fliperos/folders.list`.
- FliperOS folders: `lib/storage.sh` and `screens/storage.sh`. `fliperos-setup --storage list|prepare MOUNT|use MOUNT|unuse|offer MOUNT|answer MOUNT yes|no [batocera]|auto MOUNT|format-info MOUNT|format MOUNT ext4|exfat` does it from a terminal. `fliperos-automount` runs `--storage auto MOUNT` after mounting a disk; the queue is `/var/lib/fliperos/storage/offer` and the answers are in `/var/lib/fliperos/storage/answered` (`UUID`, and `batocera:UUID` for the other question), read and written by `gui/festorage.py`.
- Format: `storage_format` unmounts, `wipefs -a`, `mkfs.ext4 -F -m 0` or `mkfs.exfat`, and lets `fliperos-automount` mount it again as `FliperOS-HD`. `exfatprogs` comes in the image.
- Batocera filesystem: `lib/batocera.sh`; the table of console names, the cores and what each console opens is `config/batocera-systems.list` (installed as `/usr/local/share/fliperos/batocera-systems.list`). The choices are `~/.config/fliperos/batocera.list` (`console<TAB>folder<TAB>core`), in the cloud backup. A console is a frontend system with the key `batocera/<name>` (`scraper_detect` and `scraper_attract_emulator`, `lib/scraper.sh`), so ES-DE, Pegasus, Attract-Mode Plus, the FliperOS frontend and the web panel all list it. `fliperos-setup --batocera detect|scan|list|cores|set|unset|auto|use|unuse|extras` does it from a terminal.
- Where a folder really is: `folders_shown` (and `fliperos-setup --folders shown <folder>`) is the one text every screen and the web panel use for a folder that can be on another disk.

See also: [ROMs, BIOS and artwork](ROMs.md), [Games Setup](Setup-Games.md), [Custom games](Custom-games.md), [Web panel: System](Web-panel-System.md).
