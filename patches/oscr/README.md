# OSCR: dumps over USB

A patch for the [Open Source Cartridge Reader](https://github.com/sanni/cartreader) firmware, applied on top of commit `060d8ae`. With it, the FliperOS frontend reads a cartridge through the USB cable without taking out the SD card (`fliperos-setup/gui/femedia.py`, wiki [Frontends](../../docs/wiki/Frontends.md)).

The commands come in on the line the firmware updater already listens on (`checkUpdater`, 9600 baud), one per line:

| Command | Answer |
|---|---|
| `FLIPEROS` | `FLIPEROS 1 SNES MD N64 GB GBA` (the systems built in) |
| `SCAN` | `CART system\|name\|rom bytes\|save bytes` for each cart found, then `END` |
| `INFO system` | `CART ...` or `NONE` |
| `DUMP system` | `FILE path` for each file written to the SD card, then `END` (`ERROR` if the firmware stopped) |
| `BAUD rate` | `OK`, then the line switches (FliperOS uses 1000000) |
| `GET path` | `SIZE bytes`, the bytes, then `CRC crc32-in-hex`; `NONE` if missing |

All of it lives in `Cart_Reader/FLIPEROS.ino`; the rest of the firmware gets small hooks:
- `wait()` and `question_box()` don't wait for the button while a command runs (a menu takes its default answer);
- `createFolder()` notes each file it writes;
- a fatal error tells the host with `ERROR`;
- `setVoltage()` never goes to 5V during `SCAN`, so a 3.3V cart is never powered at 5V while probing.

Build both HW5 variants (without and with VSELECT) with `bash tools/oscr-firmware.sh`; it prints the flash and RAM use (about 73% and 67%).

Not tested on a real OSCR yet.
