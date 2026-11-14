[ZeDMD](https://github.com/PPUC/ZeDMD) is an open-source LED display you can build yourself: an ESP32 board driving HUB75 LED panels, 128x32 (two 64x32 panels) or 256x64. What it shows is on [LED displays](LED-displays.md); this page is about installing it and its firmware.

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/docs/img/zedmd-startup-led.gif" width="640" alt="The FliperOS startup animation drawn as the ZeDMD LEDs show it">

**It needs ZeDMD firmware 5.1.0 or newer.** Older firmware, like the one that works on Batocera 41, doesn't connect. See [Firmware version](#firmware-version) to check yours and [Updating the firmware](#updating-the-firmware).

## Installing it

**Setup > Games > Extras > ZeDMD** installs the display's server, and starts it when the display is plugged in.

The high scores need hi2txt and Java, which come with **Extras > Pixelcade**: install both if you want the high scores on the ZeDMD.

## The startup animation

When the display starts, and whenever the frontend is idle, it plays a looping 3D vector animation in cyan and magenta on black: the screen opens like a CRT, the camera dives through a wireframe tunnel with spinning cubes, and the FliperOS letters appear as extruded line art, each spinning like a coin while it is drawn, over a scrolling floor. It flies back into the distance as the screen closes, and goes on until the next game or system event.

**Idle** means 30 seconds without a button in the FliperOS frontend; the first press brings back the selected system. ES-DE and Attract-Mode Plus start it with their own screensaver timers.

## Firmware version

FliperOS talks to the display through libdmdutil 0.11.0, which brings libzedmd 0.10. That library only understands **firmware 5.1.0 or newer**. The newest release is [5.1.8](https://github.com/PPUC/ZeDMD/releases/latest).

| Firmware | Works with FliperOS |
| --- | --- |
| 3.x and 4.x | **No.** 3.6.0 was tried on a user's cabinet: it never answers |
| 5.0.x | **No.** Its handshake reply is shorter than libzedmd 0.10 expects (read from the code, not tried) |
| 5.1.0 and newer | **Yes.** 5.1.8 was tried on the same cabinet: a 128x32 ESP32 board with a CH340 USB adapter |

**Coming from Batocera.** Batocera 41 has an older libzedmd, which still talks to firmware before 5.1; Batocera 42 and 43 have the new one, like FliperOS. So a ZeDMD that works on Batocera 41 but not on 42 or 43 has old firmware, and FliperOS won't see it either until it is updated. After the update it no longer works on Batocera 41.

**Seeing the version.** The display shows it at the bottom right of its logo when it powers on. Once it connects, `journalctl -u fliperos-zedmd` shows `ZeDMD 5.1.8 found: device=/dev/zedmd, width=128, height=32`.

**What old firmware looks like.** The display stays on its logo. The log shows `ZeDMD handshake response error, result: 0`, then `Unable to connect to ZeDMD on /dev/zedmd` and `No DMD displays found`, three times, and the service stops.

A ZeDMD 5.x gives the same messages while its settings menu is open: it only talks over USB after **Exit** in that menu.

## Updating the firmware

FliperOS doesn't update the display by itself. It is done once, from FliperOS or from a PC.

1. From the [latest ZeDMD release](https://github.com/PPUC/ZeDMD/releases/latest), download the zip for your board: `ZeDMD-128x32.zip` for an ESP32 with two 64x32 panels, `ZeDMD-256x64.zip` for HD, `ZeDMD-128x64.zip` for a single 128x64 panel, the `ZeDMD-S3-N16R8_…` ones for an ESP32-S3 N16R8 ([ZeDMD README](https://github.com/PPUC/ZeDMD#flashing-the-firmware)). The zip has `ZeDMD.bin`, written at address 0.
2. On FliperOS, in a terminal (SSH, or the web panel's Terminal), with the display plugged in:

   ```
   sudo systemctl stop fliperos-zedmd
   sudo apt install esptool
   esptool --chip esp32 --port /dev/zedmd -b 460800 --no-stub write_flash 0x0 ZeDMD.bin
   ```

   It takes about 2 minutes and ends with `Hash of data verified`. For an ESP32-S3 the chip is `esp32s3`. From a Windows PC, [ZeDMD_Updater2](https://github.com/zesinger/ZeDMD_Updater2) does the same.
3. On the first start the display opens its settings menu, and it doesn't talk over USB while the menu is open. Set **RGB Order** until the top left shows red as red, green as green and blue as blue, then pick **Exit**. Without buttons, unplugging the display and plugging it back also leaves the menu. The update doesn't keep the old RGB order and brightness.
4. Start the service again, since it gave up after 3 tries:

   ```
   sudo systemctl reset-failed fliperos-zedmd
   sudo systemctl start fliperos-zedmd
   ```

   The log should show `ZeDMD 5.1.8 found`.

**Two warnings in the log are normal** with 5.1.8 on the original ESP32: `The ZeDMD USB package size of 32 is a very low value` and `The ZeDMD panel minimal refresh rate of 30 is a very low value`. Pictures and scrolling text are fine with them. If animations stutter, the ZeDMD README suggests a USB package size of 512 (`USB packet size` in the display's menu).

**Keeping the old firmware.** To go back to it later, save the flash before updating. Ubuntu's esptool can't: with `--no-stub`, `read_flash` stops at 2 MB with `CRC or checksum was invalid`. Espressif's own esptool, which has the stub (`pipx install esptool`), reads it with `esptool --chip esp32 --port /dev/zedmd read_flash 0 ALL zedmd-backup.bin` (not tried here), and it goes back with `write_flash 0x0 zedmd-backup.bin`.

## How it works

- **What is installed:** `dmdserver` from [libdmdutil](https://github.com/vpinball/libdmdutil) (the Visual Pinball DMD library, pinned version and hash) into `~/zedmd`, and the `python3-pil` package. Neither is in the image.
- **Service:** `fliperos-zedmd.service` runs `dmdserver` as the `fliperos` user, on `127.0.0.1:6789`. The udev rule (`99-fliperos-zedmd.rules`) names the ESP32's USB serial adapter `/dev/zedmd` and starts the service when it is plugged in (CP210x `10c4:ea60`, CH340 `1a86:7523`, CH9102 `1a86:55d4`, ESP32-S3 native USB `303a:1001`). With another adapter, `dmdserver` searches every USB serial port. With no ZeDMD found, it tries 3 times and then waits for one to be plugged in.
- **Pictures:** `fliperos-dmd` sends a 128x32 picture (`dmdserver` scales it up for a 256x64 panel). System logos come straight from `fliperos-dmd slide`. The pictures in `~/media/dmd` and `~/media/marquee` are no longer cycled when idle; `fliperos-dmd attract art` still does it.
- **The animation** is rendered by `tools/zedmd-vector-anim.py` (`config/zedmd-fliperos.gif`, 128x32, 8 seconds). `FLIPEROS_IDLE_SECONDS` changes the idle time (0 turns it off).
- **esptool:** Ubuntu's comes without esptool's helper program (the "stub"), hence `--no-stub`: the ESP32's own ROM writes the flash.

See also: [LED displays](LED-displays.md), [DIY hardware](DIY-hardware.md#led-display-marquee-dmd).
