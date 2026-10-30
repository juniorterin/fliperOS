What to try when the tube shows nothing, or when only some games go black. Most of this comes from the [GroovyArcade wiki](https://gitlab.com/groovyarcade/support/-/wikis/home), adapted to where FliperOS keeps each thing, so it hasn't all been tried here.

**If the picture rolls or tears at a frequency the monitor can't take, turn the monitor off first.** A 31 kHz signal can damage a 15 kHz tube.

## Getting in without a picture

The system usually booted even with a black tube. From another computer on the same network:

- **SSH**, on from the first boot: `ssh fliperos@fliperos.local`.
- **The web panel**, at `http://fliperos.local`, has a terminal page ([Web panel](Web-panel.md)).
- **Recovery Mode** on the media, when the disk doesn't boot ([Install](Install.md)).

**Debug mode** in the Setup shows the boot messages instead of the splash ([Installed system](Installed-system.md)).

## What the system sees

This lists each video output, whether something is connected, its EDID and its modes, then the card, the driver and what FliperOS saved:

```bash
for c in /sys/class/drm/card?-*; do
  echo "${c##*/}: $(cat "$c/status"), EDID $(wc -c < "$c/edid") bytes"
  cat "$c/modes"
done
cat /proc/cmdline
lspci -nnk | grep -A3 -E 'VGA|Display'
grep -E '^(driver|connector|detection|monitor|kernel_video)=' /etc/fliperos/fliperos.conf
```

The name in `connector=` must be the output your monitor is plugged into. If you moved the cable, **Setup > Video Setup > Test the video outputs** finds it again.

## Changing the kernel line by hand

The Setup writes this line, so use it whenever you can see its menu. Without a picture, change `FLIPEROS_CMDLINE` in `/etc/default/fliperos-boot`. FliperOS has no text editor for the terminal, so these commands use `sed`.

To replace a part of the line, here the mode:

```bash
grep FLIPEROS_CMDLINE /etc/default/fliperos-boot
sudo sed -i 's/video=VGA-1:640x480iS/video=VGA-1:640x240S/' /etc/default/fliperos-boot
```

To add a parameter:

```bash
sudo sed -i 's/^FLIPEROS_CMDLINE="/&amdgpu.dc=0 /' /etc/default/fliperos-boot
```

Then write it to the bootloader and restart:

```bash
sudo fliperos-limine-update
sudo reboot
```

The next save in Video Setup rewrites the `video=` part.

## Black from the boot

| Situation | Try |
| --- | --- |
| At the installation | Another entry of the boot menu: *EDID progressive*, then *EDID interlaced*, which force every output on. To choose on a 15 kHz-only tube, see [Install](Install.md#boot-menu) |
| Interlaced modes may be the problem (black at `640x480iS`) | Change `video=VGA-1:640x480iS` to `video=VGA-1:640x240S`. In the Setup it is **Video Setup > Resolution** |
| Black after moving the cable or booting without it | Force the output on, with an `e` at the end of the mode: `video=VGA-1:640x480iSe` |
| Through a converter | Interlaced modes often fail: see [Converters](Video-cards.md#converters) |
| AMD with DVI-I that has no `radeon` driver (R9 380, 380X) | Add `amdgpu.dc=0` to the line: on kernel 6.18 amdgpu's new display code has no analog output. See [Video cards](Video-cards.md#amdati) |
| Ryzen 2200GE with random black screens | Disable legacy boot (CSM) in the BIOS. Reported by GroovyArcade on this APU |
| Motherboard VGA on an APU or Intel | It may be a DisplayPort bridge chip, which limits low clocks and interlace. See [Video cards](Video-cards.md#amdati) |
| You changed the video card | FliperOS notices at boot and offers the output test: see [Changing the video card](Video-cards.md#changing-the-video-card) |

## Splash shows, then black or a crash

With two video cards, the frontend may be opening on the wrong one. Set up FliperOS with only the card you will use, and disable the other in the BIOS or pull it out. To try it without opening the case, until the next boot:

```bash
lspci | grep VGA
echo 1 | sudo tee /sys/bus/pci/devices/0000:XX:00.0/remove    # XX from the line above
```

For monitors on two cards, see [Multiple monitors](Multiple-Monitors.md).

## The menus work, some games go black

Some modes are below what the card or the converter generates. `dotclock_min` tells Switchres the lowest clock to use. Modes under it get a wider picture with the same lines, which looks the same on a CRT.

**On AMD cards** the GroovyArcade wiki says 8 MHz is often needed, and lists 12 and 25 as other common values. The NVIDIA low resolution test finds this value by itself; on other cards it is by hand.

Set the same value in both files: `/etc/switchres.ini` for Switchres and the programs that use it, `/etc/fliperos/mame/mame.ini` for GroovyMAME. For 8 MHz:

```bash
sudo sed -i -E 's/^([[:space:]]*dotclock_min[[:space:]]+).*/\18.0/' /etc/switchres.ini
sed -i -E 's/^([[:space:]]*dotclock_min[[:space:]]+).*/\18.0/' /etc/fliperos/mame/mame.ini
```

The Setup keeps a value of yours. It only replaces its own (0, 25, or a step of the NVIDIA test). To see the mode a game gets:

```bash
switchres 320 240 60 -c
```

To test a resolution with a real game, the GroovyArcade wiki has [tables of games by resolution and frequency](https://gitlab.com/groovyarcade/support/-/wikis/4-Issues-and-Troubleshooting/4.4-Video-Mode-Troubleshooting). Each program's own log is `/opt/fliperos/logs/<program>.log`.

## The picture is there but wrong

Off-centre, too large or too small: [Monitors](Monitors.md#centring-the-picture). Flickering menus: the 480i hacks in [Emulators](Emulators.md#480i-hacks-640x240-filter-or-pure-480i).

## Asking for help

Open an [issue](https://github.com/juniorterin/fliperOS/issues) with the output of the commands in *What the system sees*, your monitor, and how it is connected, converter included.
