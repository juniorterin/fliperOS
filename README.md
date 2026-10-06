# FliperOS 0.7

Ubuntu 24.04 (amd64) for arcade cabinets with a CRT monitor, in the style of GroovyArcade: a **15 kHz kernel**, Switchres, emulators and frontends ready to play, and a setup menu (`fliperos-setup`) made for the tube's screen.

In development: 0.7 is tested in a VM (QEMU) and on a cabinet with a 15 kHz CRT. The full documentation is in the **[wiki](https://github.com/juniorterin/fliperOS/wiki)**. Website: [`website/`](website).

## What's included

- **Video**: 6.18 LTS kernel with the 15 kHz patches, boot at 15, 25 or 31 kHz or LCD, Switchres.
- **Emulators**: GroovyMAME, RetroArch, Flycast, PCSX2, Dolphin, Supermodel, Model 2, Hypseus Singe and OpenBOR; Wine, Steam and Heroic through Setup > Extras.
- **Frontends**: Attract-Mode Plus, EmulationStation (ES-DE), Pegasus and Fightcade 2.
- **Setup**: video and geometry, audio, network, scraper, MAME romset cleaning, controls (buttons, light gun, wheel) and latency.
- **Folders** `roms`, `bios`, `media` and `config` in `~` and over the network (Samba); LXDE desktop with an app store.

## Install

Each version's ISO is published in [Releases](https://github.com/juniorterin/fliperOS/releases), along with what changed ([CHANGELOG.md](CHANGELOG.md)).

1. Write the ISO **byte for byte** (balenaEtcher, Rufus in "DD Image mode" or `dd`; Rufus in its default mode and Ventoy don't work) and disable Secure Boot.

   ```bash
   sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
   ```

2. Boot the cabinet from the media and wait 30 seconds: it comes up at **15 kHz** (the boot menu doesn't show on a 15 kHz tube).
3. Press **Enter** when you see the screen, choose the monitor and **Install to HD/SSD**, which erases the chosen disk.
4. Reboot, choose the default launcher and put your ROMs in `~/roms` (over the network, `\\fliperos\roms`).

## Build and tests

Always in Docker ([`CLAUDE.md`](CLAUDE.md) explains why).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.7.iso

docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

## Documentation

**Using it:** [Install](https://github.com/juniorterin/fliperOS/wiki/Install) · [Installed system](https://github.com/juniorterin/fliperOS/wiki/Installed-system) · [Frontends](https://github.com/juniorterin/fliperOS/wiki/Frontends) · [Emulators](https://github.com/juniorterin/fliperOS/wiki/Emulators) · [Fightcade 2](https://github.com/juniorterin/fliperOS/wiki/Fightcade-2) · [ROMs, BIOS and artwork](https://github.com/juniorterin/fliperOS/wiki/ROMs) · [Scraper](https://github.com/juniorterin/fliperOS/wiki/Scraper) · [Controls](https://github.com/juniorterin/fliperOS/wiki/Controls) · [Desktop and theme](https://github.com/juniorterin/fliperOS/wiki/Desktop) · [Latency](https://github.com/juniorterin/fliperOS/wiki/Latency)

**Hacking on it:** [15 kHz kernel](https://github.com/juniorterin/fliperOS/wiki/Kernel-15-kHz) · [Build and tests](https://github.com/juniorterin/fliperOS/wiki/Build-and-tests) · [Architecture](https://github.com/juniorterin/fliperOS/wiki/Architecture) · [Sources](https://github.com/juniorterin/fliperOS/wiki/Sources)

The pages live in [`docs/wiki`](docs/wiki) and go to the wiki with `bash tools/wiki-publish.sh`. [`fliperos-doc.html`](fliperos-doc.html) is everything in a single file, for offline reading (`tools/render-docs.py`), and [`docs/wikipedia`](docs/wikipedia) holds a draft Wikipedia article.
