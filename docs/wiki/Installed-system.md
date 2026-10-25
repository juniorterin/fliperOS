What happens from boot onwards on an installed FliperOS: the default launcher, the Setup menu and what each of its items does. The desktop is covered in [Desktop and theme](Desktop.md).

**Boot without text:** from Limine straight to Plymouth, and **the splash stays on screen until the menu or the frontend opens**: `fliperos-tty1` takes it down right before the launcher, the menu, the first boot or the update notice, so the login and the wait for the network (for the update check) don't leave the screen black.

Ubuntu's `plymouth-quit` only takes it down after 90 seconds, as a safety net, and `plymouth-quit-wait` doesn't hold the tty1 login.

The Limine menu is hidden (`quiet: yes`; a key during its 3 seconds shows it, with the diagnostics entry), the kernel and udev stay quiet (`quiet loglevel=3 rd.udev.log_level=3 udev.log_level=3`), the console cursor disappears (`vt.global_cursor_default=0`, and comes back in the shell), the automatic login writes nothing (`agetty --skip-login --noissue`, `~/.hushlogin`) and the console stays quiet after boot (`kernel.printk = 3 4 1 3` in `/etc/sysctl.d/99-fliperos-console.conf`: Ubuntu's `10-console-messages.conf` set the level back to 4, and a kernel error after Plymouth, such as the one from the unused Intel HDMI codec, showed up on screen).

tty1 logs in by itself and follows the flow of GroovyArcade's `.bash_profile` (`config/fliperos-tty1`, called by `~/.zprofile`): it opens the **default launcher** and, when it closes, the **FliperOS menu**.

The menu is a loop: **Start frontend** and **Start desktop** make the setup exit and `fliperos-tty1` opens the launcher on tty1 itself, as at boot, and returns to the menu when it closes.

The setup runs as root inside `sudo`'s pseudo-terminal; opened from there, X doesn't have tty1 as its terminal and can't switch VT (`xf86OpenConsole: VT_ACTIVATE failed`) — that was the cabinet's "desktop doesn't start".

If X crashes on startup, the errors from its log stay on screen until Enter (a copy goes to `/opt/fliperos/logs/Xorg-failed.log`). The user's shell is **zsh with Oh My Zsh** and the Dracula theme ([Desktop and theme](Desktop.md)); `~/.bash_profile` calls the same flow, for whoever goes back to bash.

**Controller in the menus:** with the setup menu on screen, the controller acts as the keyboard — D-pad, hat or analog stick = arrows (repeat while held), button 1 / A / Start = Enter, button 2 / B / Select = Esc, button 3 / X / Y = Space (toggles in checklists), L / R = Page Up / Page Down.

It works with arcade encoders (digital axis 0–255), gamepads and USB joysticks; light guns are left out (aiming would move through the menu).

The `fliperos-padkeys` service (pure Python, the kernel's `uinput`) only translates while `/run/fliperos/padkeys` exists, which the setup creates when it opens and deletes when it exits: frontends, emulators and the desktop read the controller by themselves, without a button counting twice.

**First boot:** *Choose default launcher*, with the generated list of the launchers actually installed (Attract-Mode Plus, RetroArch, EmulationStation..., LXDE) and *FliperOS Setup* itself. Change it later in Setup > Games > Frontend.

Right after it, the first boot installs the web panel's **Live screen** and turns it on (go2rtc from its GitHub, a pinned version checked by sha256; ffmpeg is already in the image). Without internet it offers the Wi-Fi first; if it still can't download, it says so and the Live screen stays in Setup > Games > Extras > Live screen.

**FliperOS updates (without a new ISO):** at every boot with internet, before the launcher, tty1 asks the repository whether there are FliperOS updates (`fliperos-update check`, waiting for NetworkManager and, with a cable plugged in or a saved Wi-Fi network, up to 30 s for the connection, since Wi-Fi connects after NetworkManager starts; offline or with GitHub out of reach, the boot goes on as always).

Connecting to a Wi-Fi network in *Setup > Network Setup* runs the same check right after the connection, without waiting for the next boot. With one pending, a screen says what it brings and asks: **Apply now** or **Not now** (asked again at the next boot).

Before asking it lists the **files changed on this machine that the update replaces** (up to six on screen, the rest in *View the files*): it rehearses the update in an overlay over `/` and compares each file it would write with what FliperOS itself installed (`/var/lib/fliperos/update/manifest`, the sha256 of each file, recorded by the ISO and by each update).

Each of those files is copied to `/var/lib/fliperos/update/backup/NNNN-date/` before being replaced (`fliperos-update restore N` puts them back), and the Setup choices (video, latency, buttons) are applied again afterwards. Personal files (`fliperos.conf`, button maps, ROMs, saves, frontend lists) aren't touched.

Updates are numbered and **always applied in order**: update N only goes in on a machine at N−1 (`/etc/fliperos/patch-level`), a list with a gap is refused, and if one fails nothing after it is applied (it is offered again at the next boot; log in `/var/log/fliperos-update.log`).

Each one is a repository commit listed in `updates/index` with the sha256 of its files (downloaded over HTTPS from GitHub and checked before anything is written), plus an optional `updates/NNNN.sh` for what isn't a file copy and its changelog in `updates/notes/NNNN.md` (required). They are published with `tools/make-update.sh "title" [--reboot]`.

When an update is available, the boot screen first shows **what it changes** (the changelog of each pending part, with scrolling: `fliperos-update notes`), then the files of this machine it replaces, and asks; *Read what changes* in that menu shows the changelog again. After it is applied, the [What's new](#whats-new) screen lists it with its changelog.

An install older than this system gets it with `curl -fsSL https://raw.githubusercontent.com/juniorterin/fliperOS/main/updates/bootstrap.sh | sudo bash`.

<a id="whats-new"></a>**What's new:** after a new version or a new update, the FliperOS menu opens once on a *What's new in FliperOS* screen, with scrolling (up/down a line, left/right a page): the updates installed since the last time, each with its changelog (`/usr/local/share/fliperos/update-notes`), and the [CHANGELOG](https://github.com/juniorterin/fliperOS/blob/main/CHANGELOG.md) sections of the versions since then (an update alone does not repeat the version sections; the first time, only this version's section). *Setup > System > What's new* shows it again, with every update and every version. The changelog is `/usr/local/share/fliperos/CHANGELOG.md` (put there by the ISO, by each update and by `cabinet-push`); the titles come from `/var/log/fliperos-update.log`, and what was already seen is `whatsnew_version` and `whatsnew_level` in `fliperos.conf`. A new install starts with its own version and update marked as seen. The installation media does not show it.

**Colour calibration** (Setup > Video Setup) sets the picture's colour: everything the card can do, plus saturation and hue by software when it can't. The fifteen settings are saved in `fliperos.conf` as `color_NAME=`:

| Setting | Range | How it is done |
| --- | --- | --- |
| Brightness | −50 to +50 | the card's gamma table (LUT) |
| Contrast | 50 to 150 % | LUT |
| Gamma | 0.50 to 2.00 | LUT |
| Colour temperature | 4000 to 10000 K (6500 neutral, 9300 the bluish white of many arcade monitors) | LUT: red, green and blue gains from the black-body white |
| Red / green / blue gain (drive) | 0 to 150 % | LUT |
| Red / green / blue black level (cutoff) | −50 to +50 | LUT |
| Red / green / blue gamma | 0.50 to 2.00 | LUT |
| Saturation | 0 to 200 % | the card's colour matrix (CTM); on cards without one, by software |
| Hue | −180 to +180° | CTM, or by software |
| RGB range | card default, full, limited | the connector's `output_csc` (radeon) or `Broadcast RGB` (Intel), only on cards that have it |

**Calibrate on the screen** opens test patterns in the Video Setup mode, through the same path as the emulators:
- colour bars (75 % SMPTE with near-black bars);
- 16 grey steps over a continuous ramp;
- black level: 1, 2, 4 and 8 % bars, for brightness;
- white level: 90, 95 and 98 % boxes on white, for contrast;
- red, green, blue and grey ramps;
- the 24 ColorChecker patches.

Up and down pick a setting and left and right change it while you look at the tube. Space hides the bar, Enter keeps the settings and Esc goes back to the previous ones. **Settings in numbers** changes each setting by its number (it also works over SSH), and **Back to the defaults** clears them all, the RGB range included (it goes back to the card's own default).

A change made with a game open (from the web panel or over SSH) shows in that game at once:
- the gamma table goes through the screen owner's own descriptor: `fliperos-color`, as root, takes a copy of it with `pidfd_getfd` (a card refuses the table from anyone but the program that owns the screen);
- software saturation and hue come from the OpenGL layer, which reads `fliperos.conf` again when it changes.

`config/fliperos-color.c` (built with the image and by each update as `/usr/local/bin/fliperos-color`) applies the settings. Its commands:
- `fliperos-color caps` tells what the card has: the size of the gamma table, whether there is a CTM, which range property;
- `apply` writes the LUT, the CTM and the range through DRM;
- `x11` writes the LUT to every CRTC in X;
- `lut N` prints the table and the matrix.

Where FliperOS applies them:
- at boot, as soon as the splash leaves the screen (`fliperos-tty1`);
- before each program in `fliperos-kms-run` and `fliperos-x11-run` (an X server that closes puts back the table it found);
- in X, in `fliperos-x11-client` and `fliperos-lxde`, because Xorg starts with a linear table;
- when the settings are saved.

Without a CTM (the cabinet's Radeon R7 240 on the `radeon` driver has only the 256-point LUT and `output_csc`), the Setup writes `color_ctm=sw`. Then saturation and hue go through the same OpenGL layer as the flicker filter (`libfliperos-deflicker.so`, in every emulator and frontend, and in the Setup's menu), and through picom on the desktop. Only the text console stays without them.

**Main menu** (gasetup's `mainmenu`; the title shows `host (IP) - N% used on /`):

- **Start frontend**
- **Setup** — the items come in the order of setting up a cabinet, and a balloon under the list says what the item under the cursor is for (FliperOS's gum, `patches/gum/0004-choose-balao.patch`: framed at 80 columns, two lines of text in place of the key help at 40):
  - **Video Setup** — the same as in the installation, including [Multiple monitors](Multiple-Monitors.md); saves the kernel line and offers to reboot.

    Also **480i hacks**: a table of every program (emulators, RetroArch cores, Fightcade, the desktop) where each one gets 640x240, 480i with the flicker filter at its own level (with a preview on the tube), or pure 480i ([Emulators](Emulators.md#480i-hacks-640x240-filter-or-pure-480i)).

    Changes in that table are saved as they are made; there is no Save step. Also **Colour calibration** (below). Also **Video driver**, only with an AMD card that works with both drivers (GCN 1.0 and 1.1: HD 7000, R7/R9 200 and 300, like the R7 240).

    The card name comes from `lspci`, and whether both drivers take it comes from the modules' own PCI ID tables (`modprobe -R` on the card's modalias). **radeon** is the recommended choice and the default, as on GroovyArcade: 15 kHz was validated on it; OpenGL only.

    **amdgpu** adds Vulkan (PCSX2, Dolphin, Flycast, DuckStation); it was seen working at 15 kHz on the cabinet's R7 240 (2026-10-16), not yet on other cards. RetroArch is built with Vulkan as well, but stays on `glcore`: without X its Vulkan context is `khr_display`, which does not switch the CRT's mode.

    It goes in with `amdgpu.dc=0`, because the 6.18 kernel has no analog output (VGA, DVI-I) in amdgpu's new display code for these cards (that came in 6.19). Only the kernel line chooses (`amd_driver=` in `fliperos.conf`, `AMD_DRIVER_KEYS` in `lib/bootloader.sh`).

    With amdgpu set, the boot menu (a key while the system boots) gets a **FliperOS - radeon driver** entry, the way back if there is no picture.

    **Every switch is on trial**, like a resolution change on Windows: the next boot, before the frontend or the menu, asks to confirm the picture with Enter (or button 1) within 15 s, and with no answer it goes back to the driver the card was running and restarts (`screen_amd_driver_confirm`; state in `amd_driver_trial=`, `amd_driver_previous=`).

    The `fliperos-driver-trial` service covers a confirmation screen that never opens (it goes back after 2 minutes) and a trial boot that hung and was powered off (the next boot goes back at once). An installation with a driver other than the one the media is running makes its first boot a trial too.

    In the installation the item only saves the choice, and when the card has the choice and it was not made in Video Setup, the installation asks it before the disk.

    Once, the first time the main menu opens, the Setup checks the card: if it runs on the driver that is not the recommended one (and nobody chose it in the Setup or the installation), a popup offers the switch (`screen_amd_driver_check`, `amd_driver_checked=` in `fliperos.conf`);
  - **Audio Setup** — default card (`/etc/asound.conf`), volume, AlsaMixer, **MAME audio latency** (`audio_latency` in `mame.ini`, 0.0 to 50.0, 0 = default; GA's "Audio Latency MAME") and a sound test, and the **Volume leveler**, off by default: on, every system goes through a compressor (SC4 from `swh-plugins`, a LADSPA plugin in the ALSA `default`, `/etc/asound.conf`) that brings loud and quiet systems closer to the same volume, with no lookahead and so no added delay; on an image without `swh-plugins` the Setup offers to install it.

    As in GA, the volume moves `Master`/`Front`/`Speaker`/`Headphone` and leaves `PCM` at maximum (a card with only `PCM` uses `PCM`).

    The HDA codec stays always on (`options snd_hda_intel power_save=0 power_save_controller=N`): with the Ubuntu kernel's 1 s `power_save` it went silent and turned back on at the next sound, and each on-off popped in the speakers ("puffs" with the menu idle).

    There is no sound server: RetroArch (`audio_driver = alsa`), GroovyMAME (`sound sdl`, on the ALSA `default` through `libfliperos-sdl-audio.so`; see [Emulators](Emulators.md)) and the SDL emulators (`SDL_AUDIODRIVER=alsa`) play straight into ALSA, so this volume applies to all of them, in KMS or X. **Menu sounds**: FliperOS's gum (`patches/gum/0002-sons-do-menu.patch`) plays a WAV when the cursor moves and another on Enter, like a game's select screen (Street Fighter Alpha 2, for example), in the menus and in the Setup's yes/no questions (`aplay`; a new sound cuts the one still playing, and the Enter one keeps going after the menu closes).

    The sounds are your own — FliperOS ships no game sounds: `move.wav` and `select.wav` in `/opt/fliperos/sounds/menu` (over the network, the FliperOS share, folder `sounds/menu`). With one of them there, it turns on by itself; the Audio Setup item turns it off and on (`menu_sounds` in `fliperos.conf`);
  - **Network Setup** — Wi-Fi from the list of networks (with signal) or a **hidden network by typing the SSID**; once connected, the IP shows in the title, next to the disk usage;
  - **Joysticks** — each player's buttons and where the buttons of 1 to 5-button games go on the panel, light gun and wheel calibration, joysticks on the parallel port. For a keyboard encoder (I-PAC and the like), Button mapping writes MAME's default keys instead. See [Controls](Controls.md);
  - **Games** — what puts games in the cabinet, in the order of use:
    - **Frontend** — the default boot launcher; what isn't in the image is installed (or downloaded) from here. See [Frontends](Frontends.md).

      **A game, straight from the boot** opens a single game instead of a game list: pick the system among the folders with games, then the file; the command is the one the frontends use for that folder, saved in `/etc/fliperos/bootgame` and run by `fliperos-bootgame`.

      Leaving the game (Esc) opens the FliperOS menu, whose first item becomes *Start* and the game's name. Choosing a game moves every service that starts at boot to *After boot* (below) and turns *Wait for network* off, so the game reaches the screen sooner.

      Before the game the boot also skips what only serves the frontends or needs the network: the FliperOS update check (it runs when the game closes, on the way to the menu, without waiting for a network that isn't up), the creation of missing `~/roms` folders and the frontends' preparation (game lists, art, 240p settings);
    - **Emulators & Games** — the emulators of the desktop menu, each marked installed or not, and the installation of the ones that don't come in the image: Model 2 (built on the machine), Fightcade 2, DuckStation and KOF Final Attack on Ikemen GO (downloaded from itch.io and patched by itself, or from a folder you bring).

      An installed one has **Update**, which downloads the newest version over it (Model 2: the newest source, built again; KOF Final Attack: the newest patch and Ikemen GO, converting the original game again); the ones that come in the image are updated with FliperOS. See [Emulators](Emulators.md#emulators--games);
    - **Extras** — installs over the network Wine (the Fightcade 2 emulators), Steam and Heroic (GOG), which are left out of the ISO so it fits in a single GitHub file. See [Emulators](Emulators.md).

      Also the **Pixelcade** LED/LCD marquee software, which is closed source, the **ZeDMD** open-source LED display and **DOFLinx**, the effects on the Pixelcade marquee during a game ([Frontends](Frontends.md)).

      And the two programs that take the games' outputs (lamps, recoil, button lights) to hardware: **Hook Of The Reaper**, for light guns and controller boards (a Windows program, run through Wine), **QMamehook**, for serial light guns (native, built on the cabinet), and **LEDSpicer**, for LED boards ([DIY hardware](DIY-hardware.md)).

      **Live screen** brings ffmpeg and go2rtc for the cabinet screen live in the web panel and in OBS (see [Web panel](Web-panel.md)). Choosing an extra that is already installed offers to download it again, which updates it;
    - **Custom games** — games and programs that are not a ROM (a PC game, your own emulator, a script), in groups the frontends show as systems: a group, a name, the command and the video mode (240p, 480i or WIDTHxHEIGHT@HZ). See [Adding games](Adding-games.md#custom-games);
    - **Folders** — a **custom folder** for `~/roms`, `~/bios`, `~/media`, `~/splashscreen` or any folder inside them (an emulator, a RetroArch core, a type of art): another folder (an external disk) used in its place. See [ROMs, BIOS and artwork](ROMs.md#custom-folders);
    - **Downloader** — **ROM/CHD MAME torrent** (from a romset magnet link and a CHD one, only what the ROM Cleaner filter chooses, through Transmission), **Free games** (open-source homebrew) and **Download BIOS** (the BIOS the games in your folders lack, checked each time the menu opens). See [ROMs, BIOS and artwork](ROMs.md);
    - **Cleaner** — **MAME ROM Cleaner** and **MAME CHD Cleaner**: filter a MAME romset (for GroovyMAME, Flycast, SM2-Emu, Supermodel or MAME 2010 — the MAME 3D, for the PlayStation-based arcade games) into the emulator's folder and bring the CHDs of the games that stayed. See [ROMs, BIOS and artwork](ROMs.md);
    - **Scraper** — covers, screenshots, logos, videos and information for each ROM. See [Scraper](Scraper.md);
    - **AttractPlus ROM List** — Attract-Mode Plus game lists of the arcade folders with each game's real name, from GroovyMAME's list, clones and bootlegs included. See [Adding games](Adding-games.md);
  - **System** — the rest:
    - **Latency** — **Standard** mode (any machine) or **Low latency** (modern CPUs), with a check of this machine against the recommendation and the list of ideal hardware ([Latency](Latency.md));
    - **Services** — a table with one mark per service: **Boot** (starts with the computer), **After boot** (about 15 s after the first screen of the boot opens, the menu, the frontend or the game, so it has loaded first: `fliperos-tty1` starts `fliperos-services-screen.timer`; if nothing opens on the screen, `fliperos-services-late.timer` starts them 3 min after the boot) or **Off**.

      The services are SSH, the network share (Samba, After boot by default: `nmbd` alone took about 13 s at boot), `fliperos.local` (Avahi), the Wi-Fi radio (only the radio: NetworkManager stays, it runs the network cable), *Wait for network* (`NetworkManager-wait-online`: off, the boot goes on without waiting for the network) and the [web panel](#web-panel) (After boot by default).

      The Downloader's Transmission is not in the table: it starts only when a download is asked for (see [Downloader](ROMs.md#downloader)). What Ubuntu starts at boot and a cabinet doesn't use is masked in the image: Samba as a domain controller, `gpu-manager`, Ubuntu Pro and the MOTD news.

      The choice is kept in `/etc/fliperos/services.conf`; the Pixelcade and the ZeDMD are not in it, udev starts them when the device shows up;
    - **Quirks** — kernel fixes for USB devices that arrive wrong: controllers, guns, keyboards and disks. See [Controls](Controls.md#setup--system--quirks);
    - **Password** — the password of the `fliperos` user: the login, `sudo`, SSH and the network share (Samba keeps a password of its own, and both change together);
    - **System Update** — `apt-get update` and `upgrade`, with apt's real progress;
    - **What's new** — the updates installed on this machine (newest first) and the changelog of every FliperOS version, with scrolling (see [What's new](#whats-new));
    - **Debug mode** — off (the default), the boot goes straight to Plymouth and the output of frontends and emulators (X, Switchres, the program itself) goes to `/opt/fliperos/logs/<program>.log`, rewritten on each launch: only the picture is on screen.

      On, everything shows: the Limine menu (`FLIPEROS_QUIET="no"` in `/etc/default/fliperos-boot`), the kernel and systemd messages at boot (without `quiet splash` or the silencing parameters) and the programs' output on the console. Programs follow immediately; the boot, after a reboot;
    - **Splash screen** — the boot screen (Plymouth).

      The themes are the folders in `~/splashscreen` (`\\fliperos\splashscreen` over the network); picking one shows a **preview** on screen for 10 seconds (from the FliperOS menu, not from the desktop) or sets it for the boot: it is copied to `/usr/share/plymouth/themes`, becomes the default and the initramfs is rebuilt (about a minute).

      The default is `fliperos-text`, animated like a modern terminal (the name typing itself in, a gradient progress bar and the services starting); `fliperos` is in the style of the 2000s boot screens; **Cogwheel**, **Into It** and **Windoze 95** also come installed.

      **More themes:** [Plymouth Themes on Gnome-look](https://www.gnome-look.org/browse?cat=108&ord=latest) — unpack each one into its own folder in `~/splashscreen`;
- **Start desktop** — LXDE. **Logout** (the menu item, the panel button and the end of the lxsession session) opens a full-screen terminal with the gum menu, in the Setup's look: back to the FliperOS menu, reboot, power off or cancel (`config/fliperos-logout`; the icon window of `lxsession-logout` was unreadable on a low-resolution screen);
- **Exit to shell** — `fliperos-menu` returns to the menu. Typed in an SSH session, `fliperos-menu` opens the text menu (gum) there, never the graphical one on the cabinet's monitor; frontends, games and the desktop are only started from the cabinet;
- **Shutdown / Reboot**.

**The power button.** A short press of the cabinet's power button (the motherboard's, or a panel key programmed to send `KEY_POWER`) depends on what is on screen:

| On screen | The button |
| --- | --- |
| A game opened from a frontend (Attract-Mode Plus, ES-DE, Pegasus, your own frontends) | closes the game; the frontend comes back |
| A Fightcade match | closes the match's emulator; the lobby comes back |
| An emulator opened from the desktop's Games menu | closes the emulator; the desktop comes back |
| A frontend's game list, the Fightcade lobby, the desktop, the FliperOS menu, the shell, the install media | powers the machine off |
| RetroArch or GroovyMAME as the default launcher | powers the machine off (they are the launcher, there is no frontend to go back to) |

From inside a game it therefore takes two presses to power off. For 3 seconds after a press the next ones don't count, so a second press given too early (or a board that reports one press through two devices) can't close the game and power off at once.

The game gets a `SIGTERM`, the same as closing it normally, so RetroArch still writes its saves; a game that stays open is killed (`SIGKILL`) by the next press. Holding the button for 4 seconds still cuts the power: that is the motherboard, not FliperOS.

How it works: `systemd-logind` ignores the button (`HandlePowerKey=ignore` in `/etc/systemd/logind.conf.d/fliperos.conf`; by default it would power off at every press), and triggerhappy, which already reads the volume keys, runs `config/fliperos-powerkey` on `KEY_POWER` (`config/fliperos-power.triggers`).

The script finds the open game through the `FLIPEROS_POWERKEY` variable that `fliperos-session` gives what it opens: `frontend` (the game is whatever runs below it), `game` (an emulator opened from the desktop) or `games:FILE` (Fightcade, whose emulators are not its children, lists their PIDs in `FILE`).

**Volume keys:** the keyboard's volume keys (or those of a panel encoder programmed to send them) work on any screen — emulator in KMS, desktop, console.

`triggerhappy` reads `/dev/input` and calls `fliperos-setup --volume up|down|mute` (5% steps on the Audio Setup card, saved on every press because cabinets are usually switched off at the wall); `config/fliperos-volume.triggers` says which keys. The LXDE panel only handles the mouse, so the volume doesn't change twice. No volume bar appears during a game (nothing draws on top of an emulator in KMS).

## Web panel

The cabinet in a browser on the same network, a phone too: **http://fliperos.local**. Games to play, the screen live and in OBS, settings while you play, files, the ROM filter, downloads, the system status and a terminal. It has its own page: **[Web panel](Web-panel.md)**.

**SSH and AI assistants:** SSH is on from the first boot, and SFTP too. From another computer on the same network:

| Field | Value |
|---|---|
| **Address** (host) | `fliperos.local`, or the cabinet's IP (shown in the FliperOS menu title) |
| **User** (login, username) | `fliperos` |
| **Password** | `fliperos` until you change it in **Setup > System > Password** |
| **Port** | `22` |

The user and the password are the same word by default, but they are two separate things.

In the command `ssh fliperos@fliperos.local`, the `fliperos` before the `@` is the **user** and `fliperos.local` after it is the **address**; the **password** is not in the command, you type it when SSH asks (`fliperos@fliperos.local's password:`), and nothing appears on screen while you type.

In an SFTP program (FileZilla, WinSCP) the same four fields are *Host*, *Username*, *Password* and *Port*. `sudo` asks for the same password, and the network share (`\\fliperos\roms`) takes the same user and password. After a password change only the password is different: the user is still `fliperos`.

Under the menus it's a regular Ubuntu 24.04, so whatever the Setup doesn't cover can be done from a terminal, and an AI assistant with shell access (Claude Code, Cursor, Codex and the like) can do it for you: give it the cabinet's address and say what you want (button mapping, an emulator's settings, a frontend theme, a service) and it configures the system over SSH.

The configuration is in plain text files (`/etc/fliperos/fliperos.conf`, `~/config`, `/opt/fliperos`), easy for a person or an assistant to read and change.

On a network you don't control, change the default password in **Setup > System > Password** (it changes the network share's too), and turn off what you don't use in **Setup > System > Services**.
