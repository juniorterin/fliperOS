From the written media to the system on disk: writing the ISO, the boot menu, the video output test and the installation through **FliperOS Setup**.

## Writing the media

Write the ISO **byte for byte** to a USB stick and disable Secure Boot (the 15 kHz kernel is custom and unsigned).

The ISO uses the **Limine** bootloader and is **hybrid** (`xorriso` + `limine bios-install`): the same image boots as a CD and as a USB stick, on BIOS and on UEFI. Writers that rebuild the boot structure break it — **Rufus in its default mode ("ISO image"), Ventoy and UNetbootin don't work**. Use **balenaEtcher**, or Rufus in "DD Image mode", or `dd`:

```bash
sudo dd if=fliperos-0.7.iso of=/dev/sdX bs=4M status=progress conv=fsync
```

Check `/dev/sdX` with `lsblk` first: the wrong device erases the wrong disk.

## Boot menu

The same options as GroovyArcade (`os/groovyarcade/syslinux/syslinux.cfg`). Here you only choose the range Linux boots in; the output and the monitor are decided later, by the output test.

| Entry | Parameters | For |
| --- | --- | --- |
| **15 kHz** (default) | `video=640x480iS` | Arcade monitor or TV, 640x480 interlaced |
| 25 kHz | `video=512x384S` | Medium resolution monitor |
| 31 kHz | `video=640x480S` | High resolution monitor |
| SVGA / LCD monitor | — | PC monitor or LCD (its EDID applies) |
| Intel 15 kHz | `video=1280x480iS i915.no_ytiled_scanout=1` | Intel: super resolution; the parameter comes from patch 09 and enables interlacing on Gen9 |
| NVIDIA 15 kHz | `video=1280x480iS` | NVIDIA: super resolution |
| NTSC | `video=720x480iS` | NTSC TV |
| PAL | `video=768x576iS` | PAL TV |
| EDID progressive | `drm.edid_firmware=edid/generic_15_super_resp.bin video=e` | Switchres EDID, all outputs forced |
| EDID interlaced | `drm.edid_firmware=edid/generic_15_super_resi.bin video=e` | Same, interlaced |

The `S` at the end of the mode comes from the 15 kHz patch: it uses the kernel's fixed table of low-dotclock modes (`drm_modes_low_dotclock.c`), and `i` means interlaced. Every entry carries `quiet splash consoleblank=0` and `radeon` on SI/CIK cards.

**30-second timer.** With no key pressed, the **15 kHz** entry boots, which is the safe one for a cabinet: an LCD receiving 15 kHz only shows "out of range", but 31 kHz on a 15 kHz-only tube can damage it.

The menu itself **doesn't show on a 15 kHz CRT** — it is drawn in the firmware's text mode (~31 kHz), before the kernel. GroovyArcade is the same. To choose another entry on a 15 kHz-only cabinet, connect an LCD temporarily; with the CRT, wait the 30 s. The first readable thing on the tube is the splash, already in the boot mode.

## Output test and *Testing Results*

Ported from `gatools` (`video/video.sh`): as soon as the media boots, `fliperos-setup`:

1. forces the analog outputs on ("Lights on") and explains the test, speaking through `espeak-ng`;
2. turns all outputs off and enables **one at a time**, writing `on`/`off`/`detect` to `/sys/class/drm/cardN-CONNECTOR/status` (an analog output with no monitor detected is forced; a digital one with nothing connected is skipped);
3. on each one, says "Testing output V G A 1. If you can see this screen, press Enter." and shows *"If you can see this screen clearly, press ENTER."* for 10 s;
4. **stops at the first ENTER** and goes to the *Testing Results* screen (gatools tests all of them and picks the best; here, whoever is looking at the screen has already decided). Without ENTER, it repeats the round up to three times.

With two cards, the console is moved to the framebuffer of the card being tested (`con2fbmap`), as in gatools.

The **Testing Results** screen shows the GPU, driver, connector, current mode and horizontal frequency (read from the active CRTC by `fliperos-video-check`), whether the card generates low dotclocks, whether there is an interlaced mode, the EDID, whether the monitor was identified and whether the output will be forced at boot — with the same sentences as gatools' `inform_user` — and offers **Validate settings** or **Repeat test**.

Once validated, gatools' `configure_from_connector` applies:

- Switchres EDID (dongle) → the monitor comes from the EDID itself;
- otherwise, the monitor type is **mandatory** (the list opens on the suggestion of the boot entry);
- the kernel line comes from the monitor: `video=VGA-1:640x480iSe` (the `e` when the output had to be forced); a card without low dotclock (Intel, NVIDIA) → super resolution `1280x480iS` and `dotclock_min 25.0` in Switchres; APU → `interlace_force_even 1`; EDID boot → `drm.edid_firmware=CONNECTOR:edid/<monitor>.bin`; LCD → nothing (its EDID applies).

Everything is saved in **`/etc/fliperos/fliperos.conf`** (GPU, driver, connector, detection, monitor, range, boot mode, kernel parameters, orientation, launcher), the equivalent of `ga.conf`, and in `switchres.ini`/`mame.ini`.

## FliperOS Setup

The media's menu (gasetup's `isomainmenu`): **Install to HD/SSD**, **Recovery Mode**, **Terminal** and **Shutdown**. The title shows the host and the IP.

### Install to HD/SSD

1. **Do you want to configure video?** — *Yes* opens **Video Setup**:
   - **Monitor Type**: the 29 Switchres presets, in the gatools list;
   - **Monitor Orientation**: horizontal, vertical clockwise, vertical counter-clockwise (console rotated with `fbcon=rotate`, `panel_orientation` in `video=`, MAME's `ror`/`rol` and the desktop through `xrandr`);
   - **Resolution**: only the modes of the kernel table that the monitor's range and the card accept (without low dotclock, only the super resolutions), plus a **custom resolution**: tested on the Switchres `grid` and turned into an EDID (`switchres -e`), like `worker_custom_video_mode`;
   - **Geometry**: the same **`geometry`** as GroovyArcade — Switchres' `geometry.py`, which draws the grid and returns the `crt_range`, saved as `monitor custom` in `/etc/switchres.ini`. The grid is drawn at the resolution chosen above, with its refresh rate (50 Hz in PAL modes; with no choice, 640x480). Downwards the image only moves while there are blank lines below it (Switchres doesn't go past the *front porch*); when it stops, the adjustment is the monitor's **V-POS**.
2. **Automatically Partition** — lists the disks by **model, size, path and bus** (USB/NVMe/SATA). Not listed: the installation media itself, disks under 16 GiB, mounted or in swap, with RAID/LVM/encryption or active dependents — each one with the reason, above the list. **My drive is not listed (details)** shows everything Linux sees (`lsblk`, the controllers and the kernel messages): an HD/SSD that doesn't even show there is hidden before Linux, almost always by the BIOS SATA mode set to RAID/Intel RST (switch to AHCI) or by Intel VMD.
3. **WARNING** — model, path and size of the disk that will be erased; *No* goes back to the disk choice. If the disk already has FliperOS, the warning suggests Recovery Mode.
4. **Installing FliperOS** — a single screen, with the target disk, a **real** progress bar (the system copy comes from the `unsquashfs` percentage, like gasetup's `dialog --gauge`), the step and short messages. Command output goes to `/var/log/fliperos-setup.log`. On error: step, error, **View log / Retry / Return**.
5. **Installation completed successfully. Remove the installation CD/DVD/USB.** — and **Reboot now?**

Partitioning: GPT, a 1 MiB BIOS boot partition, a 1 GiB FAT32 ESP, the rest in ext4. The new partitions have their old signatures wiped and the BIOS boot one is zeroed (a leftover file system from the previous disk there made `limine bios-install` refuse; it also runs with `--force`). Limine is installed for BIOS (stage 2 in the BIOS boot partition) and for UEFI (`EFI/BOOT/BOOTX64.EFI`, the removable path), without touching the NVRAM. Limine only reads FAT, so the kernel and initrd live **on the ESP** (`/boot/efi/fliperos/`), maintained by `fliperos-limine-update` — the equivalent of `update-grub`, called by the kernel and initramfs hooks. The kernel parameters are in `/etc/default/fliperos-boot`.

The new disk carries what was decided on the media: `fliperos.conf`, Switchres, MAME, Xorg, the kernel line, the configured Wi-Fi networks and the sound card.

### Recovery Mode

Looks for disks with FliperOS (a `FliperOS` partition with the `/etc/fliperos/installed` marker) and offers: a terminal inside the installed system (`chroot`, gasetup's `rescue_mode`), **reinstall the bootloader** (the "Fix UEFI boot", for BIOS and UEFI), **apply this session's video settings** (graphics card replaced) and **restore the system files** from the media, keeping ROMs, saves, home, network, audio and video.
