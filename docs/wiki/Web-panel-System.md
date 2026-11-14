The **System** area of the [web panel](Web-panel.md): the cabinet's status and logs, every Setup setting while you play, accounts, a terminal and lab mode.

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/website/public/screenshots/web/status-en.webp" width="640" alt="The status page of the web panel">

| Tab | What it has |
| --- | --- |
| **Status** | The video mode, CPU, GPU, temperatures, memory, disks, network |
| **Processes and logs** | What uses the CPU, and every FliperOS log |
| **Settings** | The Setup's settings, in the Setup's order |
| **RetroAchievements** | The account, achievements on/off, hardcore, the Web API Key |
| **Cloud backup** | The cloud account and syncing |
| **Terminal** | The cabinet's shell in the browser |
| **Lab mode** | A temporary internet address for remote help |

## Status

Refreshed every second:

- **Video:** what Video Setup asks (monitor, frequency, resolution, connector, orientation) next to what is on screen now: the mode, the horizontal kHz and vertical Hz, interlaced or progressive, and the full **modeline** of each active output.
- **CPU:** the total, each core and the load, plus the temperatures of the sensors.
- **GPU:** the name and the driver, plus what the card reports: use, VRAM, clock, temperature, power.
- **Memory, disks and network:** the speed of each interface, its IPs and the Wi-Fi signal.

## Processes and logs

The processes using the most CPU, and the logs: those of `/opt/fliperos/logs` (each emulator and frontend, the cloud backup, OpenBOR, DuckStation…), the Setup's and the updates'. The first place to look when a game doesn't open.

## Settings

The Setup's settings, in the same order as on the cabinet. Each change is saved and applied at once.

| Group | What it has |
| --- | --- |
| **Video** | Monitor type, boot resolution, **Back to the previous monitor**, orientation, multi-screen games, the on-screen menu on or off |
| **Geometry** | The saved geometry, and resetting it to the monitor preset |
| **Colour** | Every colour calibration value and **Back to the defaults** |
| **Scanlines** | The scanlines of a 31 kHz monitor |
| **Interlaced hacks** | A card per program: 640x240, Interlaced with filter or Interlaced pure, and the filter's strength |
| **Audio** | The sound card, MAME audio latency, menu sounds, a test sound |
| **GunCon 2** | The light gun's settings |
| **Network** | Wi-Fi |
| **Live screen** | Sound, quality, the marquee overlay for OBS |
| **System** | The cabinet name, what starts at power on, the boot splash, latency mode, debug mode |
| **Password** | The `fliperos` user's password |
| **Services** | The whole services table |
| **Version** | Choose the FliperOS update, or follow the updates ([Updates and versions](Updates-and-versions.md#choosing-the-version)) |
| **What's new** | The changelog |
| **Power** | Restart, turn off |

A colour slider saves while it moves, so the game on screen changes with it; the **−** and **+** at its sides move it one step per tap.

A new monitor or resolution counts after a restart, and the page offers to restart when it is saved. The video driver is not here: changing it asks for a confirmation on the cabinet's screen, so it stays in the Setup.

### No picture after a monitor change?

The panel doesn't need the tube. From a phone, open **Settings > Video** and pick the right monitor or resolution, or press **Back to the previous monitor**: it brings back the monitor and resolution from before the last change, made here or in **Setup > Video Setup**. Pressed again, it goes back to the new one.

A custom resolution and the Geometry grid stay on the cabinet's screen, since they need you to see the picture.

## RetroAchievements

Sign in to your retroachievements.org account (or open the sign-up page in a new tab), turn the achievements and hardcore mode on or off, and paste the **Web API Key** for the badge in the game list; the tab links to the page where you copy it. See [RetroAchievements](RetroAchievements.md).

## Cloud backup

Install rclone, sign in (Google Drive with a code, Dropbox at its site, WebDAV, SFTP or MEGA with a user and password), **Sync now**, **Send** or **Get**, sync by itself after each game, and choose what to sync. See [Cloud backup](Cloud-backup.md).

## Terminal

The cabinet's shell in the browser, as the `fliperos` user, with its own zsh and the window's size: the same as SSH, without a program on the computer. In a lab session it is root.

## Lab mode

Starts and stops a temporary internet address to the panel, for someone helping you from far away: **Copy** puts it on the clipboard, and the tab shows when it expires (after 4 hours). Read what it gives the other person before you send it: [Remote access](Remote-access.md#lab-mode).

## How it works

- The video status comes from DRM, through `fliperos-video-check`. The volume goes through `fliperos-setup --volume up|down|mute|get|set N`.
- Settings go through the same functions as the Setup's screens: `fliperos-setup --settings` lists the groups, and `--setting KEY VALUE` changes one (`settings_list` in `lib/system.sh`). Debug and latency rewrite the kernel line the way their screens do; their kernel part counts after a restart. A run of taps on **−** or **+** saves once, just after the last.
- The terminal is a login shell in a pseudo-terminal (`setsid -c`, so Ctrl+C and job control work), at normal priority. The page talks to it over a WebSocket (`/api/terminal`) that only the panel's own page can open, after the login. The screen is drawn by [xterm.js](https://xtermjs.org) 5.5.0 with its fit addon (MIT), shipped inside the panel.
- RetroAchievements and Cloud backup call the same programs as the Setup: `lib/cheevos.sh` and `config/fliperos-cloud`.

See also: [Web panel](Web-panel.md), [System Setup](Setup-System.md).
