The FliperOS commands you can type in a terminal (SSH, the web panel's Terminal, or **Exit to shell**). They live in `/opt/fliperos/bin` and `/usr/local/bin`; most need `sudo` when they change the system. The Setup and the web panel call the same commands.

## Menus and launching

| Command | What it does |
| --- | --- |
| `fliperos-menu` | Back to the FliperOS menu from the shell. Over SSH, the text menu in the session |
| `sudo fliperos-setup` | The Setup, as a text menu |
| `fliperos-launch NAME` | Opens an emulator as the desktop's Games menu does: `retroarch`, `groovymame`, `flycast`, `pcsx2`, `pcsx2x6`, `duckstation`, `dolphin`, `openbor`, `model2`, `model3`, `fightcade`, `kof`; or `--mode WxH@HZ PROGRAM` |
| `fliperos-kms-run PROGRAM [ARGS]` | Runs a program on the console, without X ([KMS and X11](KMS-and-X11.md)) |
| `fliperos-x11-run [--mode WxH@HZ] [--app NAME] [--wine] PROGRAM [ARGS]` | Runs a program in its own Xorg, in its video mode |
| `fliperos-resolution [--apply-saved]` | The desktop's resolution; reverts after 15 s without confirmation |

## Updates

| Command | What it does |
| --- | --- |
| `fliperos-update level` | The update the cabinet is at |
| `fliperos-update check` | Asks GitHub for a new update |
| `fliperos-update notes` | The changelog of the pending updates |
| `fliperos-update versions` | Every update from the image's to the newest |
| `sudo fliperos-update goto N\|latest` | Goes to update N, back or forward; `latest` follows the updates again |
| `sudo fliperos-update restore N` | Puts back the files update N replaced |
| `sudo fliperos-update apt-heal` | Fixes apt sources with two keys for the same repository |

See [Updates and versions](Updates-and-versions.md).

## Games

| Command | What it does |
| --- | --- |
| `fliperos-customgame inspect\|pending\|install\|pack\|run` | Custom game packages ([Custom games](Custom-games.md)) |
| `fliperos-squashgames pack\|unpack\|remove DIR`, `list`, `mount-all`, `umount-all` | Packed game folders (squashfs) |
| `fliperos-portproton check\|install\|versions\|run EXE` | PortProton, for Windows games |
| `fliperos-downloader status\|start\|pause\|resume\|add\|remove` | The ROM/CHD torrent downloader ([Downloader](Downloader.md)) |
| `fliperos-bios check --wants FILE`, `index` | Download BIOS ([BIOS](BIOS.md)) |
| `fliperos-romclean scan\|chds\|apply\|options\|romlist\|uses\|buttons` | The MAME ROM Cleaner and its tables ([ROM Cleaner](ROM-Cleaner.md)) |
| `fliperos-openbor-meta info PAK` | What an OpenBOR pak has ([OpenBOR](OpenBOR.md)) |
| `groovymame -verifyroms GAME` | The files a MAME game is missing |

## Controls and hardware

| Command | What it does |
| --- | --- |
| `fliperos-buttons players` | How many players are mapped and connected |
| `fliperos-bluetooth status\|power on\|off\|devices\|pair MAC\|connect MAC\|disconnect MAC\|remove MAC` | Bluetooth controllers ([Bluetooth](Bluetooth.md)) |
| `fliperos-padcolor list\|all` | Controller lights ([Controller light](Controller-light.md)) |
| `fliperos-versus watch mame\|retroarch\|model2 GAME` | Prints a fight's wins and characters as they change ([Versus score](Versus-score.md)) |
| `fliperos-versus fetch` | Downloads Fightcade's score detectors again |
| `fliperos-outputs installed\|hotr\|fetch-hotr\|fetch-qmamehook` | Game output tools ([DIY hardware](DIY-hardware.md)) |
| `fliperos-syslogo export DIR` | Every system logo as a PNG |

## Online and remote

| Command | What it does |
| --- | --- |
| `fliperos-cloud status\|sync [push\|pull\|both]\|auto on\|off\|what LIST\|forget` | The cloud backup ([Cloud backup](Cloud-backup.md)) |
| `fliperos-lab start\|stop\|status` | Lab mode ([Remote access](Remote-access.md#lab-mode)) |
| `fliperos-video-check` | The video mode on each output, with its modeline |

## Logs

Every program's output is in `/opt/fliperos/logs/<program>.log`; the Setup's in `/var/log/fliperos-setup.log`; the updates' in `/var/log/fliperos-update.log`. The web panel shows them in **System > Processes and logs**.

See also: [Architecture](Architecture.md), [Remote access](Remote-access.md).
