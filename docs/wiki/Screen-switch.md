# Screen switch

A 15 kHz arcade tube and a 31 kHz monitor (a PC CRT, an EDTV plasma) on the **same cable**, one at a time. FliperOS reads which one is on the cable when it starts and uses that screen's video: the tube gets its 15 kHz modes, and the 31 kHz monitor gets 640x480 and the 31 kHz modes of the games (Dreamcast, PS2 and NAOMI at 480p). Swapping with the cabinet off needs no extra restart in either direction.

It replaces the dual boot some people used to keep one system per monitor: the games, saves and settings are the same on both screens.

**Not tested on a 31 kHz monitor yet.** On a 15 kHz cabinet, the kernel took a new EDID with the system on and read the tube's empty DDC as expected. Reports are welcome in the [issues](https://github.com/juniorterin/fliperOS/issues).

## What you need

- The monitors on an **analog output** (VGA, or DVI-I with a passive adapter) of the card. Not on HDMI, DVI-D or DisplayPort: a converter to VGA answers with its own 31 kHz EDID even with the tube behind it.
- One monitor on the cable at a time. The same cable moved from one monitor to the other, or a VGA switch box (see the warning below).
- The 31 kHz monitor has an **EDID** (almost every PC monitor and plasma does). The tube has none (an arcade monitor, a TV on SCART), or a Switchres EDID dongle with a 15 kHz preset.
- The output test done with the tube, and the tube chosen in Setup > Video Setup > **Monitor Type**.
- Not with [Multiple monitors](Multiple-Monitors.md) or a vertical monitor.

## Step by step

1. With the **tube** on the cable, open Setup > Video Setup > **Screen Switch** and turn it on. The Setup prepares the boot (about a minute) and asks to reboot.
2. Turn the cabinet **off**, move the cable to the 31 kHz monitor and turn it on. The start is black on it for a few seconds (the boot always starts in the tube's mode), then the frontend opens at 640x480.
3. Adjust the 31 kHz monitor in Video Setup if you want (Monitor Type, Resolution, Geometry): the changes stay with that monitor.
4. Back to the tube: cabinet off, cable on the tube, cabinet on. Everything is as it was on the tube, geometry included.

The web panel has the same switch: System > Setup > Video > **Screen switch by the cable**.

## Swapping with the cabinet on

**Swap the cable with the cabinet off.** A 15 kHz tube that gets a 31 kHz signal can be damaged, so FliperOS watches the cable:

- **Tube to the 31 kHz monitor**: safe, and no restart. The monitor gets 15 kHz for a moment (no picture), then what was on screen closes and opens again at 31 kHz.
- **31 kHz monitor to the tube**: the cable is read 5 times a second. When the monitor's EDID disappears, the output is turned off and whatever is on screen is closed at once (a game open loses what it didn't save). Unplugging one cable and plugging the other takes longer than that, so the tube finds no signal. Then the cabinet **restarts** in the tube's mode: AMD cards keep the 31 kHz monitor's modes until a monitor answers on the cable, and a tube doesn't.
- **A VGA switch box swaps instantly**: the tube can get 31 kHz for a fraction of a second. With a switch box, turn the cabinet off first.
- **Never** put the tube behind a splitter, a KVM or any box that answers with another monitor's EDID: FliperOS would take the tube for that monitor.

## Setting it up

Setup > Video Setup > **Screen Switch**:

| Item | What it does |
| --- | --- |
| The screens | Each screen FliperOS has seen, with its monitor type; *now* marks the one on the cable. A screen that is not on the cable can be forgotten: next time it comes back as new, at 640x480. |
| **Turn Off** | Only the tube's video stays. Only with the tube on the cable. |

A new 31 kHz monitor gets the **VESA 640x480** type (31.5 kHz, 60 Hz), which every VGA display accepts. Monitor Type, Resolution and Geometry change the screen that is on the cable.

## How it works

- Each screen is a profile in `/etc/fliperos/screens/`: the video keys of `fliperos.conf` (monitor, frequency, boot resolution, geometry) and the EDID that identifies it (manufacturer, product and serial). The tube is `home.conf`.
- **The kernel line is always the tube's.** With the switch on, the tube's boot mode goes into an EDID (`video=VGA-1:e drm.edid_firmware=VGA-1:edid/fliperos-screen.bin`) instead of the `video=` mode. A change that needs the kernel line, made while the 31 kHz monitor is on the cable, is written when the tube comes back.
- `config/fliperos-ddc` reads the EDID straight from the cable (the output's DDC i2c bus, address 0x50): with an EDID file in the kernel line, the kernel itself doesn't read the cable.
- Before the first screen (`fliperos-tty1`) and in `fliperos-screen-watch.service`, `fliperos-setup` compares the cable with the active screen. To switch to a 31 kHz screen, it turns the output off, puts the screen's video in `fliperos.conf`, Switchres, MAME and Xorg, writes the screen's EDID into `/sys/module/drm/parameters/edid_firmware`, and sets the output to `detect` and then `on`: the driver drops the EDID it kept (the monitor answers on the DDC) and reads the new one, and the frontend (SDL), X, Qt and RetroArch open in its mode.
- `amdgpu` (without DC) and `radeon` keep a connector's EDID until a monitor answers on the DDC (seen on a cabinet: the list stayed after a `detect` with the tube). So once a 31 kHz screen was used in a boot (`/run/fliperos/screen-edid-dirty`), going back to the tube never turns the output on again: the tube's video goes back to `fliperos.conf` and the cabinet restarts.
- The code is in `fliperos-setup/lib/screens.sh`; the log lines start with `screens:` in `/var/log/fliperos-setup.log`.
