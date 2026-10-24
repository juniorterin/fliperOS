## `fliperos-setup`

```
fliperos-setup/
├── fliperos-setup        entry point (media or installed system)
├── lib/                  logic — no file here calls gum, except ui.sh
│   ├── common.sh config.sh progress.sh speech.sh
│   ├── drm.sh video.sh monitor.sh xorg.sh bootloader.sh
│   ├── disk.sh install.sh recovery.sh
│   ├── launcher.sh audio.sh network.sh status.sh scraper.sh update.sh
│   ├── romclean.sh netshare.sh  MAME ROM Cleaner; network shared folder (SMB)
│   ├── downloader.sh     romset and CHDs by magnet link (Transmission)
│   ├── folders.sh        custom folder (external disk) for ~/roms, ~/bios, ~/media
│   ├── hardware.sh latency.sh   CPU/memory/GPU and the latency modes
│   ├── quirks.sh padkeys.sh     usbhid quirks; controller in the menus
│   ├── lpt.sh            parallel port joysticks (db9, gamecon, turbografx)
│   └── ui.sh             Gum, theme, screen frame
└── screens/              screens — they only combine ui.sh with the logic
    ├── output-test.sh (test + Testing Results)  main-menu.sh  setup-menu.sh
    ├── video-setup.sh  disk-selection.sh  install-progress.sh  progress.sh
    └── recovery.sh  first-boot.sh  latency.sh  lpt.sh  rom-cleaner.sh  downloader.sh
```

Long operations (install, repair, update, scraper) don't know about the screen: they write events (`@step`, `@pct`, `@msg`, `@fail`) that `screens/progress.sh` draws. Everything goes to `/var/log/fliperos-setup.log`.

## Launch commands and wrappers

Nothing on FliperOS opens a frontend or an emulator by calling its binary directly. Between the boot and the game there is a short chain of scripts, each one with a single job. All of them are in `/opt/fliperos/bin`, except `fliperos-menu` and `groovymame`, which are in `/usr/local/bin` so they can be typed in the shell.

| Command | Called by | What it does |
| --- | --- | --- |
| `fliperos-tty1` | `~/.zprofile`, at the tty1 login | The boot flow: first boot or update notice, then the default launcher, then the menu loop |
| `fliperos-menu` | You, in the shell | Back to the menu: runs `fliperos-tty1 --menu` and, on leaving, shows the MOTD again |
| `fliperos-session [name]` | `fliperos-tty1` | Opens one launcher from the sessions table and returns when it closes |
| `fliperos-kms-run program [arguments]` | `fliperos-session`, frontends, you | Runs a program straight on KMS/DRM, without Xorg |
| `fliperos-x11-run [--mode WxH@HZ] program [arguments]` | Frontends, `fliperos-launch`, you | Runs a program in an Xorg of its own, in a video mode made by Switchres |
| `fliperos-x11-client` | `fliperos-x11-run`, through `xinit` | Inside that Xorg: window manager, then Switchres switches the mode and launches the program |
| `fliperos-launch name` | The **Games** menu of the desktop | Closes the desktop, opens the emulator, brings the desktop back |
| `fliperos-escquit PID` | `fliperos-session`, `fliperos-fightcade` | Esc closes the frontend when no game is open |
| `fliperos-powerkey` | triggerhappy, on the power button | Closes the open game; with no game open, powers off |

### From the boot to the launcher

`fliperos-tty1` is the only entry point. At boot it runs `fliperos-session` with no argument, which opens the launcher chosen in **Setup > Games > Frontend** (`/etc/fliperos/session`); when that closes, it enters the menu loop.

In the loop the Setup never opens anything itself: **Start frontend** and **Start desktop** write the launcher's name to `/run/fliperos/launch` and exit with code 20, and `fliperos-tty1` then calls `fliperos-session <name>` from the login shell, where tty1 is the controlling terminal ([Installed system](Installed-system.md) explains why). `fliperos-menu` is the same loop without the boot part.

`fliperos-session` looks the name up in `/etc/fliperos/sessions.conf` (and in `sessions.custom.conf`, the frontends you registered), one launcher per line as `name|backend|binary|package|description`. The backend decides how it opens:

- `kms`: `fliperos-kms-run <binary>`. For the frontends (Attract-Mode Plus, ES-DE, Pegasus and your own) it also starts `fliperos-escquit` and marks the process with `FLIPEROS_POWERKEY=frontend`.
- `x`: `xinit <binary>` on the same VT. Only the LXDE desktop uses it.
- `none`: opens nothing; the boot goes straight to the menu.

Around the launcher it sets the CPU governor to performance and restores it afterwards (`fliperos-setup --session-start` and `--session-end`).

### The two wrappers: KMS and X11

Every emulator is opened through one of them, and both refuse to run inside an X session (`DISPLAY` set): they need the console. Which one to use for each emulator is in [Adding games](Adding-games.md#emulator-command-lines-kms-or-x11).

**`fliperos-kms-run`** is for what draws on KMS by itself: RetroArch and the KMS frontends. The video mode is the one from the boot, and RetroArch switches it per game on its own. Before the program starts, the wrapper:

- tells the Pixelcade marquee and the game outputs (`fliperos-pixelcade launch`, `fliperos-outputs launch`) which game is opening;
- for RetroArch, stacks the system configuration on top of the user's with `--appendconfig` (the FliperOS `retroarch.cfg`, the `gl` fallback for cards without OpenGL 3.2, the Button mapping, DOFLinx and the versus score);
- turns off the extra monitors, leaving only the main one;
- exports the console drivers: `SDL_VIDEODRIVER=kmsdrm`, `SDL_AUDIODRIVER=alsa` and Qt's `eglfs`;
- gives the program the session's terminal as its input when a frontend handed it `/dev/null`;
- sends the program's output to `/opt/fliperos/logs/<program>.log` (to the screen in Debug mode).

**`fliperos-x11-run`** is for what needs X: Flycast, PCSX2, Dolphin, Supermodel, Model 2, OpenBOR, Hypseus. It starts an Xorg just for that program and closes it when the program exits.

The mode comes from `--mode`, or from the program's line in `/etc/fliperos/emulator-modes.conf` (one column for a 15 kHz monitor, another for 25/31 kHz and LCD), or is 320x240@60.

It also adds each emulator's own full-screen and stretch options, turns the extra monitors back on, exports `SDL_VIDEODRIVER=x11`, and writes the same log.

The Xorg's client is `fliperos-x11-client`: it starts Openbox (which fits the window to the screen at every mode switch) and hands over to `switchres WIDTH HEIGHT HZ --switch --launch "<program>"`, which creates the modeline for the monitor in `/etc/switchres.ini`, switches to it and runs the program. More in [Emulators](Emulators.md#running-a-program-at-640x240).

### Commands that wrap themselves

Two launchers are `kms` in the sessions table but need X. Their own command notices it is on the console and opens itself again through `fliperos-x11-run`:

- **`groovymame`** (`config/fliperos-groovymame`): the real binary is `/usr/local/libexec/groovymame`. Commands with no screen (`-listxml`, `-verifyroms`...) run directly.
- **`/opt/fliperos/fightcade/fightcade`** (a link to `fliperos-fightcade`, see [Fightcade 2](Fightcade-2.md)).

So choosing Fightcade in the menu runs this chain, each line starting the next:

```
fliperos-tty1                                    the menu loop
└─ fliperos-session fightcade                    the row in sessions.conf, CPU governor
   └─ fliperos-kms-run /opt/fliperos/fightcade/fightcade      log, Pixelcade, outputs
      └─ fliperos-fightcade                      no DISPLAY: opens itself in X
         └─ fliperos-x11-run /opt/fliperos/fightcade/fightcade    mode from the table, xinit
            └─ fliperos-x11-client               Openbox, Switchres switches the mode
               └─ fliperos-fightcade             DISPLAY set: Wine prefix, emulator settings
                  └─ Fightcade2.sh               the Fightcade client
```

### From the desktop

The desktop is itself an X session, and the wrappers don't run inside one. `fliperos-launch <name>` (the items in **Games**, see [Desktop and theme](Desktop.md)) writes the full command, already with its wrapper, to `$XDG_RUNTIME_DIR/fliperos-next` and closes LXDE.

`fliperos-session`, which was waiting for the desktop's X to end, runs that command with `FLIPEROS_POWERKEY=game` and then opens the desktop again. It only accepts a request that starts with `fliperos-kms-run` or `fliperos-x11-run`. `fliperos-launch --mode 640x240@60 program` does the same for any program.

### Which one to type

On a console (tty1 after leaving the menu to the shell, or another VT), not over SSH: an SSH session has no VT for the screen.

| To | Type |
| --- | --- |
| Return to the FliperOS menu | `fliperos-menu` |
| Open a launcher exactly as the menu does | `/opt/fliperos/bin/fliperos-session fightcade` (or `retroarch`, `attractplus`, `lxde`...) |
| Open the default launcher | `/opt/fliperos/bin/fliperos-session` |
| Run RetroArch with a core | `/opt/fliperos/bin/fliperos-kms-run retroarch -L <core>.so <game>` |
| Run an X emulator in its table mode | `/opt/fliperos/bin/fliperos-x11-run flycast <game>` |
| Run any program in a chosen mode | `/opt/fliperos/bin/fliperos-x11-run --mode 640x240@60 <program>` |
| Open GroovyMAME or Fightcade | `groovymame [game]`, `/opt/fliperos/fightcade/fightcade` |

## Other components

**Splash.** Plymouth.

The default `fliperos-text` theme is text only, in the style of a modern terminal: the name scrambles into place and then waves through a gradient, a prompt types the subtitle, a gradient progress bar with a moving shine, the last systemd units with a spinner (`SetUpdateStatusFunction`) and faint falling characters.

It draws everything with JetBrains Mono (OFL, `config/fonts`), which goes to `/usr/share/fonts/truetype/fliperos` and, through the `fliperos-fonts` initramfs hook, into the initramfs: the Ubuntu plymouth hook only copies the Ubuntu font.

`fliperos` is a full 640x480 image scaled to the boot mode (640x480, 640x240, 320x240...) with an animated bar.

Three themes from Gnome-look come too: `cogwheel` (by DUKE93, GPL 3), `into-it` and `windoze95`, adapted to scale to the window, with the pixel twice as tall in the double-width modes (640x240), and Windoze 95's art reduced to 640x480.

All of them live in `config/splashscreen` and go to `/usr/share/plymouth/themes` and to `~/splashscreen`, where Setup > System > Splash screen also lists the user's themes (more on [Gnome-look](https://www.gnome-look.org/browse?cat=108&ord=latest)).

Setting one (`lib/splash.sh`) copies its folder with `ImageDir` and `ScriptFile` rewritten, points the `default.plymouth` alternative at it and runs `update-initramfs` (the initramfs hook takes the new initrd to the ESP); the preview runs `plymouthd` with `plymouth.splash=NAME`.

`tools/cabinet-update.sh` rebuilds the initramfs when the boot theme's files change. The build can also use `evangelion` (202 frames, with a **seizure risk** declared by the author and no license in the package) or none.

**Network.** Samba (`\\<ip>\FliperOS` → `/opt/fliperos`, and `\\<ip>\roms`, `bios`, `media` and `config` → the folders of the same name in `~`, writable only with the `fliperos` user; `config/smb.conf`), SSH/SFTP and Avahi (`fliperos.local`).

Default user `fliperos` with password `fliperos`, like GroovyArcade's user `arcade` with password `arcade` (see [Installed system](Installed-system.md)).

NetworkManager handles Wi-Fi **and wired** (the empty `10-globally-managed-devices.conf` overrides Ubuntu's, which only managed Wi-Fi) and writes `/etc/resolv.conf` itself with the DNS from DHCP (`90-fliperos-dns.conf`: Ubuntu would hand DNS to `systemd-resolved`, which isn't in the image).

The clock comes from the network (`systemd-timesyncd`). On the first test on the cabinet all three were missing: `resolv.conf` was the build container's, the BIOS clock was two months behind, and apt didn't work (neither System Update nor frontends).

**Diagnostics.** `sudo fliperos-video-check --json` reads the active mode of each output (current CRTC through libdrm, read-only): connector, resolution, kHz, Hz, interlaced.

## Files

| File | Purpose |
| --- | --- |
| `fliperos-setup/` | The setup (media and installed system) |
| `fliperos-mkiso.sh` | ISO build |
| `fliperos-kernel.sh` | 15 kHz kernel as `.deb`, with a cache |
| `fliperos-rootfs.sh` | Installs into the image the setup, the session, LXDE, the palette and the initial configuration |
| `fliperos-limine.sh` | Pinned Limine: downloads it, installs it in the rootfs, builds the hybrid ISO |
| `fliperos-limine-update.py` | Limine's `update-grub` on the installed disk |
| `fliperos-video-check.py` | Active mode of the outputs (DRM, read-only) |
| `fliperos-detect.sh` | System and video report |
| `config/limine.conf` | The media's boot menu |
| `config/fliperos-rebuild-edids`, `config/fliperos-edid-hook` | Switchres EDIDs and the initramfs hook |
| `config/fliperos-session`, `config/fliperos-sessions.conf` | Opens the default launcher; table of launchers |
| `config/fliperos-lxde`, `config/lxde/` | LXDE session and configuration |
| `config/vtrgb-dracula` | Dracula console palette |
| `config/fliperos-latency.service` | Applies the latency mode at boot |
| `config/fliperos-volume.triggers` | Volume keys (triggerhappy) |
| `config/fliperos-powerkey`, `config/fliperos-power.triggers` | The power button: closes the open game, or powers off from the frontend (triggerhappy) |
| `fliperos-dracula.sh`, `config/openbox-3/themerc` | Dracula theme for LXDE (GTK pinned by commit + Openbox) and the terminal (Oh My Zsh + dracula/zsh) |
| `config/zshrc`, `config/fliperos-tty1`, `config/fliperos-menu` | The user's zsh; tty1 flow (first boot, launcher, the menu loop); from the shell back to the menu |
| `config/fliperos-padkeys`, `config/fliperos-padkeys.service` | Controller as keyboard in the setup menus |
| `config/fliperos-calibrate` | GunCon 2 and wheel/pedals/analog calibration (Setup > Joysticks) and its reapplication by udev |
| `config/fliperos-roms`, `config/smb.conf`, `config/flycast-emu.cfg` | Folders in `~` (`roms`, `bios`, `media`, `config`); Samba (FliperOS, roms, bios, media, config); initial Flycast settings |
| `config/fliperos-controllers`, `config/fliperos-controllers.service` | Completes SDL2's (and Flycast's) automatic mapping of connected controllers |
| `config/lxde/alacritty/alacritty.toml`, `config/fliperos-software.gschema.override`, `config/applications/org.gnome.Software.desktop` | The desktop's terminal (Alacritty) and App Store |
| `fliperos-setup/lib/debug.sh` | Debug mode: boot and programs with or without text |
| `config/fliperos-resolution`, `config/applications/fliperos-resolution.desktop` | Screen Resolution: the desktop resolution on the fly |
| `config/mame-ui.ini` | Dracula colors for GroovyMAME's UI |
| `config/applications/`, `config/icons/`, `config/fliperos-launch` | Emulators in the LXDE menu and leaving the desktop to open them |
| `config/fliperos-x11-run`, `config/fliperos-emulator-modes.conf` | Opens a program in an Xorg of its own in the requested mode (`--mode 640x240@60`) or in the per-emulator table's mode |
| `fliperos-setup/lib/multimonitor.sh`, `config/fliperos-mame-screens`, `config/fliperos-multiscreen` | [Multiple monitors](Multiple-Monitors.md): the extra monitors in the Setup, the `numscreens` of GroovyMAME's multi-screen games, and Flycast's NAOMI multi-board games across 3 monitors |
| `config/fliperos-model2`, `config/fliperos-sm2emu`, `config/sm2-emu-patches`, `config/fliperos-ini-set` | Model 2 is SM2-Emu (clone, apply the FliperOS patches if there are any, build with LTO, game list; the binary is not in the image); per-section ini tweaks (PCSX2) |
| `config/fliperos-fightcade`, `config/openbox-fightcade.xml` | Fightcade 2: downloads it from its website (`fetch`) and opens it in an Xorg of its own; its window shortcuts |
| `config/fliperos-groovymame` | The `groovymame` command: the release in `/usr/local/libexec` with the system `mame.ini` |
| `config/retroarch.cfg`, `config/mame.ini` | System configuration for RetroArch and GroovyMAME (Standard mode values) |
| `patches/kernel-15khz/6.18/` | D0023R patches |
| `packaging/` | Frontend `.deb`s and the APT repository |
| `tests/`, `tools/` | Tests and verification tools |
| `README.md`, `docs/wiki/` | The summary and the full documentation: the pages of this wiki, kept next to the code |
| `tools/wiki-publish.sh`, `tools/render-docs.py` | Publishes `docs/wiki` to the GitHub wiki; builds `fliperos-doc.html` (everything in a single file, for offline reading) |
| `CHANGELOG.md`, `tools/release-publish.sh` | What changed in each version, in the format of GroovyArcade's releases; publishes the audited ISO to GitHub Releases with the version's section |
| `docs/wikipedia/FliperOS.wiki` | Draft of a Wikipedia article, in wikitext; its references point to the pages in `docs/wiki` |
| `website/` | The project website (Next.js), served as a Docker container |
