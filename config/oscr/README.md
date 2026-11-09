# OSCR firmware with the FliperOS patch

The firmware Setup > System > Cartridge reader writes to an Open Source Cartridge Reader HW5, so the FliperOS frontend can read cartridges over USB (`fliperos-setup/lib/oscr.sh`).

- `OSCR-HW5-fliperos.hex`: an HW5 with the 3.3V/5V switch.
- `OSCR-HW5-VSELECT-fliperos.hex`: an HW5 with the VSELECT module.

Both are built by `tools/oscr-firmware.sh` from [sanni/cartreader](https://github.com/sanni/cartreader) at commit `060d8ae0bf4be40bfc6a368bf6fbf7b594b3884d`, with `patches/oscr` applied. The firmware is GPL-3.0, like the original: the source is that commit plus the patch in this repository.

Rebuild them after changing the patch: `bash tools/oscr-firmware.sh`, then copy `output/oscr/*.hex` here.
