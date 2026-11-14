**This rewrites your video card's BIOS chip, at your own risk.** A bad result can leave the card dead, with no picture even at power on. FliperOS cannot repair that: it takes a second video card (usually not the one on the motherboard) or a chip programmer. It is an experimental community tool, not made by AMD or the card's maker.

[ATOM-15](https://github.com/antonioginer/ATOM-15), by Antonio Giner "Calamity", changes the video modes in the BIOS of an ATI/AMD card, so the computer's own startup screens already come out at 15 kHz, instead of signals out of the monitor's range until the system starts. It changes nothing after that: games and menus already run at 15 kHz without it.

*Video Setup > Card firmware* appears with an AMD card on the installed system, at the cabinet (not over SSH, since you have to watch the next boot).

## Opening it reads the card first

 The menu says what the BIOS on the card has (*ATOM-15* or *No ATOM-15*), even if the card came that way, and saves a copy in `~/vbios`. With the flash tool it reads the chip. Without it, it uses the copy the system has from this boot, in `~/vbios/card-<card>-<sum>.rom`, which is only for checking: only a read of the chip, with no ATOM-15 in it, can be flashed back as the original. A card that already has ATOM-15 has nothing to apply, and *Restore* only appears if the original BIOS was saved on this computer.

## The flash tool

 `amdvbflash` is AMD's, closed, and AMD does not publish it, so FliperOS does not ship or download it. Get the 64-bit Linux version yourself (the TechPowerUp forums have it) and put the file at `~/vbios/amdvbflash`. It runs as root, so use a copy you trust. It does not work with Secure Boot on.

## What the Setup does, in order


1. The warnings, with *No* as the default. In UEFI mode one more: ATOM-15 is not guaranteed there, the computer's setup screen can stay black, and a patched BIOS loses the signature of its EFI part (a bricked R9 380 has been reported that way).
2. Reads the card's BIOS twice with `amdvbflash -s` and compares. If it is good and belongs to this card, the **backup** goes to `~/vbios/original-<card>-<sum>.rom`, and the Setup shows where. **Copy it off the computer:** if the card dies, this machine may show no picture to reach it.
3. Makes the patched BIOS for the monitor's frequencies: `~/vbios/atom15-<card>-<range>khz.rom`, with a log of each mode next to it. A BIOS that already has the hook, a card outside ATOM-15's list, or a BIOS with no room for the hook outside its EFI part is refused here, with the card untouched.
4. Flashes it after one more question, reads it back and compares. If that fails, the original goes back right away.
5. **Reboot and test.** Watch the screen from the first second. Before the frontend, a question asks if the startup screens were stable. Enter (button 1) within 90 seconds keeps it.

**With no answer, or with Esc, the original BIOS is flashed back and the computer restarts.** A guard service (`fliperos-atom15-guard.service`) does the same if the question never opens within 5 minutes, or if the test boot hung and the computer was turned off. *Card firmware > Restore the original BIOS* puts it back later.

A card that does not pass the power-on test never reaches the system, so **none of this can undo it**; that is the risk the warning is about. To flash the backup by hand from another card: `amdvbflash -p <adapter> original-<card>-<sum>.rom`.

## How far this was tested

 the patch is a translation of ATOM-15 v1.6 to Python (`config/fliperos-atom15`), made with the author's permission, because the original is Windows-only, with no command line. Against a BIOS written by the real `atom-15.exe` (R7 240, 15 kHz) all 65536 bytes came out the same (`tools/atom15-check.py`). Other card families, other ranges and the move of the EFI part use the same code but were not compared. **The flash, the test at the next boot and the way back have only run with a fake flash tool**, never on a real card.

See also: [Video cards: AMD](Video-cards-AMD.md), [Video Setup](Setup-Video.md#card-firmware).
