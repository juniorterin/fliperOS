# FliperOS 0.8.2

**English** | [Português](README.pt-BR.md)

Ubuntu 24.04 (amd64) for arcade cabinets with a CRT monitor, in the style of GroovyArcade: a **15 kHz kernel**, Switchres, emulators and frontends ready to play, and a setup menu (`fliperos-setup`) made for the tube's screen.

In development: 0.8.2 is tested in QEMU and on a 15 kHz CRT cabinet. Full documentation in the **[wiki](https://github.com/juniorterin/fliperOS/wiki)**. Website: **[fliperos.juniorter.in](https://fliperos.juniorter.in)** (source in [`website/`](website)).

## What's included

- **Video**: 6.18 LTS kernel with the 15 kHz patches, boot at 15, 25 or 31 kHz or LCD, Switchres.
- **Emulators**: GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Model 2, Hypseus Singe and OpenBOR; Wine, Steam and Heroic through Setup > Extras.
- **Frontends**: Attract-Mode Plus, EmulationStation (ES-DE), Pegasus and Fightcade 2, whose online matches play in each game's native resolution on the tube.
- **Light gun**: GunCon 2 out of the box (driver via DKMS), calibrated for the tube in Setup > Joysticks. Wheels too.
- **Setup**: video, geometry, audio, network, scraper, ROM lists, MAME romset cleaning, controls and latency.
- **Folders** `roms`, `bios`, `media` and `config` in `~` and over the network (Samba); LXDE desktop with an app store.
- **SSH** on from the first boot (`ssh fliperos@fliperos.local`, password `fliperos`). Under the menus it's a regular Ubuntu, so an AI assistant can configure it over SSH.

## From zero to playing: step by step

This guide goes from an empty cabinet to a game on screen. Each step says what you will see and what to press. The details behind each screen are in the wiki pages linked along the way.

### 1. What you need

- **A PC (amd64)** for the cabinet. For arcade games up to the 90s and consoles up to the PlayStation, a 2-core CPU, 4 GB of RAM and a 16 GB disk are enough. For PS2, Model 3 and Dreamcast, a 4-core CPU with AVX2 (Core i7-7700, Ryzen 5 3600 or newer), 16 GB and an SSD. The disk you install to is **erased completely**.
- **A graphics card with analog output.** The best fit is an **AMD Radeon with VGA or DVI-I** from the HD 2000 series to the R7/R9 (GCN 1.0), which generates 15 kHz natively. Intel and NVIDIA work at 15 kHz with "super resolution" modes. Cards without an analog output need a DisplayPort/HDMI to VGA converter.
- **The monitor**: an arcade CRT (15 kHz), a TV through a VGA to SCART/component adapter, or a 25/31 kHz monitor. An LCD also works.
- **A USB stick of 4 GB or more** (it will be erased).
- **A USB keyboard** for the installation. After that, the panel or a gamepad moves through all the menus.
- **A network connection** (cable or Wi-Fi), to copy games from another computer and to receive updates. Optional, but it makes everything easier.
- **Another computer** (Windows, Linux or macOS) to write the USB stick and, later, to copy the games over the network.

### 2. Download the ISO

1. Open [Releases](https://github.com/juniorterin/fliperOS/releases) and download `fliperos-0.8.2.iso` from the latest version (what changed is in [CHANGELOG.md](CHANGELOG.md)).
2. If the release lists a SHA-256, compare it: `sha256sum fliperos-0.8.2.iso` on Linux, `Get-FileHash fliperos-0.8.2.iso` in Windows PowerShell.

### 3. Write the USB stick

The ISO must be written **byte for byte**. Programs that rebuild the stick's boot structure break it: **Rufus in its default mode ("ISO image"), Ventoy and UNetbootin don't work.**

- **Windows, macOS or Linux, the easiest**: [balenaEtcher](https://etcher.balena.io). *Flash from file* > choose the ISO > *Select target* > the USB stick > *Flash!*.
- **Windows with Rufus**: choose the stick and the ISO, click *START* and, when it asks, choose **"Write in DD Image mode"**.
- **Linux**: find the stick with `lsblk` (here `/dev/sdX`; the wrong device erases the wrong disk) and run:

  ```bash
  sudo dd if=fliperos-0.8.2.iso of=/dev/sdX bs=4M status=progress conv=fsync
  ```

### 4. Prepare the cabinet's BIOS

Enter the BIOS/UEFI setup (usually **Del**, **F2** or **F10** right after power-on) and:

1. **Disable Secure Boot**: the 15 kHz kernel is custom and unsigned, and with Secure Boot on it doesn't start.
2. **SATA mode on AHCI** (not RAID or Intel RST); otherwise the installer doesn't see the disk.
3. **Boot from the USB stick**: put it first in the boot order, or use the one-time boot menu (often **F8**, **F11** or **F12**). BIOS (legacy) and UEFI both work.

Save and exit with the stick plugged in.

### 5. Boot from the USB stick

1. **Wait about 30 seconds without pressing anything.** The boot menu (15 kHz, 25 kHz, 31 kHz, LCD...) is drawn at 31 kHz, so **it doesn't show on a 15 kHz tube**. With no key pressed, the **15 kHz** entry boots by itself, which is the safe one for a cabinet. On a PC monitor or an LCD, you can pick *SVGA / LCD monitor* in the menu instead.
2. The FliperOS splash appears, already at 15 kHz.
3. **Output test.** FliperOS turns on one video output at a time and a voice says *"Testing output VGA 1. If you can see this screen, press Enter."* When the text *"If you can see this screen clearly, press ENTER"* is readable on **your** monitor, press **Enter**. Without Enter it moves on to the next output and repeats the round up to three times.
4. **Testing Results** shows the card, the output, the mode and the frequency. Choose **Validate settings** (or **Repeat test**).
5. **Monitor type**: choose your monitor from the list (for example *generic_15* for a common arcade monitor or TV, *arcade_15*, *ntsc*, *pal*, or a specific model). The list opens on the suggestion for the boot entry. The full table of boot entries is in [Install](https://github.com/juniorterin/fliperOS/wiki/Install).

### 6. Install to the disk

The **FliperOS Setup** menu opens (Install to HD/SSD, Recovery Mode, Terminal, Shutdown). The arrows move, **Enter** confirms and **Esc** goes back.

1. Choose **Install to HD/SSD**.
2. **Do you want to configure video?** Choose *Yes* to adjust it now (you can also do it later in Setup > Video Setup):
   - **Monitor Type**: the same monitor as in the test;
   - **Monitor Orientation**: horizontal, or vertical for a rotated monitor (vertical games);
   - **Resolution**: the modes your monitor and card accept (the suggestion is fine);
   - **Geometry**: a grid to center the picture and fit its size on the tube. Use the arrows to adjust and Enter to save.
3. **Automatically Partition**: choose the disk by model, size and type (USB/NVMe/SATA). If yours isn't listed, **My drive is not listed (details)** explains why (usually the SATA mode, step 4).
4. **WARNING**: it shows the disk that will be **completely erased**. Check it and confirm (*No* goes back to the list).
5. **Installing FliperOS**: a progress bar with the current step. It takes a few minutes.
6. **Installation completed successfully**: remove the USB stick and choose **Reboot now**.

### 7. First boot of the installed system

1. The cabinet boots straight to the splash, without text.
2. **Choose default launcher**: what opens every time the cabinet is turned on. For a cabinet, choose **Attract-Mode Plus** (a game list with artwork, made for arcade). The others are EmulationStation (ES-DE), Pegasus, RetroArch, the LXDE desktop or the FliperOS Setup itself. You can change it later in Setup > Frontend.
3. When you leave the launcher (Esc), the **FliperOS menu** appears: *Start frontend*, *Setup (video, audio, network...)*, *Start desktop*, *Exit to shell*, *Shutdown / Reboot*. The title shows the cabinet's IP address.
4. **Network**: a network cable works by itself. For Wi-Fi: *Setup > Network Setup*, choose the network and type the password. Once connected, the IP appears in the menu title.
5. **Updates**: at each boot with internet, if there is a FliperOS update, a screen describes it and asks **Apply now** or **Not now**.

### 8. Set up the controls

In the menus, the panel or a gamepad already acts as the keyboard: directions = arrows, button 1 = Enter, button 2 = Esc.

1. *Setup > Joysticks > Button mapping*.
2. For each player, press what it asks for, in order: up, down, left, right, **buttons 1 to 6** in panel order (1 2 3 in the top row, 4 5 6 in the bottom row), **Start** and **Coin**. The first input pressed tells which controller belongs to that player. With nothing pressed for 8 seconds, that input is skipped.
3. The mapping goes to every emulator at once (GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Hypseus and OpenBOR).
4. Light gun (GunCon 2), wheel and pedals have their own calibrators in the same menu, and *Setup > Quirks* fixes USB encoders that arrive wrong (for example a dual encoder showing up as a single player). See [Controls](https://github.com/juniorterin/fliperOS/wiki/Controls).

### 9. Copy your games

Use only games you have the right to use (your own dumps, or the free homebrew from *Setup > Downloader > Free games*).

**Over the network (the easiest)**, from another computer on the same network:

- **Windows**: in File Explorer's address bar type `\\fliperos\roms` (or `\\IP-of-the-cabinet\roms`) and press Enter. If it asks for a login, use `fliperos` / `fliperos`.
- **macOS**: Finder > Go > Connect to Server > `smb://fliperos.local/roms`.
- **Linux**: `smb://fliperos.local/roms` in the file manager.
- Also available: `\\fliperos\bios` (BIOS files), `\\fliperos\media` (artwork) and `\\fliperos\config` (emulator settings).

**Without a network**: copy the files to a USB stick, open *Start desktop* (LXDE) and drag them into the `roms` folder in the file manager. Or use SFTP (`fliperos@fliperos.local`, password `fliperos`).

**Each emulator has its folder** in `roms`. Copy the files as they come: MAME sets stay zipped and are **never renamed** (`sf2ce.zip`, not `Street Fighter II.zip`).

| Folder | Games | Emulator |
| --- | --- | --- |
| `mame` | Arcade: MAME sets (`.zip`, `.7z`) and their CHD folders | GroovyMAME |
| `naomi`, `naomi2`, `atomiswave` | Sega Naomi and Sammy Atomiswave sets | Flycast |
| `model3` | Sega Model 3 sets | Supermodel |
| `model2` | Sega Model 2 sets | Model 2 Emulator (needs Setup > Extras > Wine) |
| `dreamcast` | `.gdi`, `.cdi`, `.chd` | Flycast |
| `ps2` | `.iso`, `.chd`, `.cso` | PCSX2 |
| `dolphin` | GameCube and Wii (`.iso`, `.rvz`, `.wbfs`) | Dolphin |
| `retroarch/<core>` | Consoles and computers; the `_info.txt` in each folder lists the extensions | RetroArch |
| `openbor/Paks` | OpenBOR games (`.pak`) | OpenBOR |

**BIOS** go in `bios`, never in a games folder: `bios/mame` for MAME (`neogeo.zip`, `qsound.zip`...), `bios/dc` for Flycast (`naomi.zip`, `awbios.zip`, `dc_boot.bin`), `bios/ps2` for PCSX2, and the `bios` folder itself for the RetroArch cores.

Has a full MAME romset? *Setup > Cleaner > MAME ROM Cleaner* keeps only the games that work and suit your cabinet (horizontal or vertical, the controls you have) and puts them in the right emulator's folder. More in [ROMs, BIOS and artwork](https://github.com/juniorterin/fliperOS/wiki/ROMs).

### 10. Make the frontend show the games

1. *Setup > Frontend* > choose **Attract-Mode Plus** again (even if it already is the default). The Setup creates a system for each folder that has games. Do this again every time a folder gets its first games.
2. **Real game names** (*Street Fighter II* instead of `sf2`): *Setup > AttractPlus ROM List*, for the arcade folders. It works offline and also brings year, manufacturer and the clones.
3. **Artwork** (screenshots, logos, videos, descriptions): *Setup > Scraper*, which needs internet. See [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper).
4. New games added later to a folder that already shows in Attract-Mode: run *Setup > AttractPlus ROM List* or *Setup > Scraper* again. Details in [Adding games](https://github.com/juniorterin/fliperOS/wiki/Adding-games).

### 11. Play

1. In the FliperOS menu choose **Start frontend** (or just turn the cabinet on: the default launcher opens by itself).
2. In **Attract-Mode Plus**: **left/right** change the system (MAME, Naomi, PCSX2...) and **up/down** move through the games. Each system comes with filters (All Games, Most Played, genres, manufacturers, years); **Tab** opens Attract-Mode's configuration, where *Controls* binds buttons to change filters and anything else.
3. Press **button 1** (or Enter) on a game. The screen goes black for a moment while Switchres sets the video mode for that game, and the game starts.
4. Insert a credit with **Coin** and start with **Start**.
5. **Leaving the game**: in GroovyMAME, **Esc** on the keyboard. In RetroArch, **Start + Coin** together open its menu, then *Quick Menu > Close Content*. The other emulators use their own exit key or menu ([Emulators](https://github.com/juniorterin/fliperOS/wiki/Emulators)). You go back to the game list.
6. **Esc** in Attract-Mode (and confirming) leaves the frontend and returns to the FliperOS menu, where *Shutdown / Reboot* turns the cabinet off safely.

### 12. If something goes wrong

- **No picture at boot**: wait the 30 seconds (the menu doesn't show at 15 kHz). On a 15 kHz-only tube, connect an LCD temporarily to choose another boot entry.
- **The installer doesn't list the disk**: SATA mode on AHCI in the BIOS. *My drive is not listed (details)* shows what Linux sees.
- **The picture is off-center or too big**: *Setup > Video Setup > Geometry*.
- **A system doesn't appear in the frontend**: the folder needs at least one game file (the `_info.txt` doesn't count); then choose the frontend again in *Setup > Frontend*.
- **A game doesn't open**: turn on *Setup > Debug mode* to see the emulator's messages on screen; without it they are saved in `/opt/fliperos/logs`. Check the BIOS in `bios`.
- **No sound**: *Setup > Audio Setup* chooses the card and the volume and plays a test.
- **Something the menus don't cover**: over SSH (`ssh fliperos@fliperos.local`, password `fliperos`) it's a regular Ubuntu 24.04, and an AI assistant with terminal access can configure it for you. On a network you don't control, change the password with `passwd`.

More in [Installed system](https://github.com/juniorterin/fliperOS/wiki/Installed-system), [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) and [Latency](https://github.com/juniorterin/fliperOS/wiki/Latency).

## Build and tests

Always in Docker ([`CLAUDE.md`](CLAUDE.md) explains why).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.8.2.iso

docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

## Documentation

**Using it:** [Install](https://github.com/juniorterin/fliperOS/wiki/Install) · [Installed system](https://github.com/juniorterin/fliperOS/wiki/Installed-system) · [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) · [Emulators](https://github.com/juniorterin/fliperOS/wiki/Emulators) · [Fightcade 2](https://github.com/juniorterin/fliperOS/wiki/Fightcade-2) · [ROMs, BIOS and artwork](https://github.com/juniorterin/fliperOS/wiki/ROMs) · [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper) · [Adding games](https://github.com/juniorterin/fliperOS/wiki/Adding-games) · [Controls](https://github.com/juniorterin/fliperOS/wiki/Controls) · [Desktop and theme](https://github.com/juniorterin/fliperOS/wiki/Desktop) · [Latency](https://github.com/juniorterin/fliperOS/wiki/Latency)

**Hacking on it:** [15 kHz kernel](https://github.com/juniorterin/fliperOS/wiki/Kernel-15-kHz) · [Build and tests](https://github.com/juniorterin/fliperOS/wiki/Build-and-tests) · [Architecture](https://github.com/juniorterin/fliperOS/wiki/Architecture) · [Sources](https://github.com/juniorterin/fliperOS/wiki/Sources)

The pages live in [`docs/wiki`](docs/wiki) and go to the wiki with `bash tools/wiki-publish.sh`. [`fliperos-doc.html`](fliperos-doc.html) is all of it in one file (`tools/render-docs.py`).
