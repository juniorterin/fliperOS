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

## Other components

**Splash.** Plymouth. The default `fliperos-text` theme is text only, in the style of a modern terminal: the name scrambles into place and then waves through a gradient, a prompt types the subtitle, a gradient progress bar with a moving shine, the last systemd units with a spinner (`SetUpdateStatusFunction`) and faint falling characters. It draws everything with JetBrains Mono (OFL, `config/fonts`), which goes to `/usr/share/fonts/truetype/fliperos` and, through the `fliperos-fonts` initramfs hook, into the initramfs: the Ubuntu plymouth hook only copies the Ubuntu font. `fliperos` is a full 640x480 image scaled to the boot mode (640x480, 640x240, 320x240...) with an animated bar. Three themes from Gnome-look come too: `cogwheel` (by DUKE93, GPL 3), `into-it` and `windoze95`, adapted to scale to the window, with the pixel twice as tall in the double-width modes (640x240), and Windoze 95's art reduced to 640x480. All of them live in `config/splashscreen` and go to `/usr/share/plymouth/themes` and to `~/splashscreen`, where Setup > Splash screen also lists the user's themes (more on [Gnome-look](https://www.gnome-look.org/browse?cat=108&ord=latest)). Setting one (`lib/splash.sh`) copies its folder with `ImageDir` and `ScriptFile` rewritten, points the `default.plymouth` alternative at it and runs `update-initramfs` (the initramfs hook takes the new initrd to the ESP); the preview runs `plymouthd` with `plymouth.splash=NAME`. `tools/cabinet-update.sh` rebuilds the initramfs when the boot theme's files change. The build can also use `evangelion` (202 frames, with a **seizure risk** declared by the author and no license in the package) or none.

**Network.** Samba (`\\<ip>\FliperOS` → `/opt/fliperos`, and `\\<ip>\roms`, `bios`, `media` and `config` → the folders of the same name in `~`, writable only with the `fliperos` user; `config/smb.conf`), SSH/SFTP and Avahi (`fliperos.local`). Default login `fliperos`/`fliperos`, like GroovyArcade's `arcade`/`arcade`. NetworkManager handles Wi-Fi **and wired** (the empty `10-globally-managed-devices.conf` overrides Ubuntu's, which only managed Wi-Fi) and writes `/etc/resolv.conf` itself with the DNS from DHCP (`90-fliperos-dns.conf`: Ubuntu would hand DNS to `systemd-resolved`, which isn't in the image). The clock comes from the network (`systemd-timesyncd`). On the first test on the cabinet all three were missing: `resolv.conf` was the build container's, the BIOS clock was two months behind, and apt didn't work (neither System Update nor frontends).

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
| `config/fliperos-model2`, `config/fliperos-sm2emu`, `config/sm2-emu-patches`, `config/fliperos-ini-set` | Model 2 is SM2-Emu (clone, apply the FliperOS patches, build with LTO, game list; the binary is not in the image); per-section ini tweaks (PCSX2) |
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
