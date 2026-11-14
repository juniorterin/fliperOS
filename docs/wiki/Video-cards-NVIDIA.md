NVIDIA cards run on the open driver, **nouveau**, out of the box. On the installed system, *Setup > Video Setup > Video driver* can switch to **NVIDIA's own driver** (see below).

## With VGA or DVI-I (GeForce 8 to GTX 900, Quadro up to the K series)

 Out of the box nouveau refuses every mode under 25 MHz. FliperOS's own kernel patch (`10_fliperos_nouveau_analog_low_dotclock.patch`) lifts that floor on the analog outputs, but whether each card's PLL actually reaches 6.5 MHz varies.

Each card's PLL has its own lowest clock, so the card is tested on the tube:

1. boot the **NVIDIA 15 kHz** entry (super resolution, `1280x480iS`);
2. after you confirm the output in the video output test, the Setup shows a **Switchres grid at 320x240** (6.5 MHz) for 20 seconds;
3. black screen → a wider grid, easier for the PLL: 384x240 (7.8 MHz), 512x240 (10.4 MHz), then 640x240 (13 MHz);
4. the first grid you see sets `dotclock_min` for Switchres, MAME and RetroArch (0 at 320, then 7.7, 10.3 or 12.9);
5. none seen, or no answer → super resolutions, as before. Nothing is lost by trying.

Below the card's minimum, Switchres, MAME, RetroArch and the standalone emulators double the width: a 320x240 game comes out at 640x240. On a CRT the picture is the same. Boot modes under the minimum are not offered.

The test can be repeated on the installed system in *Setup > Video Setup > Low resolutions*. It only runs on an analog output with a 15 kHz monitor.

**Seen on a CRT: GTX 980 Ti** (GM200, DVI-I, VGA-SCART) on nouveau, with the patch. Black at 6.5 and 6.8 MHz, picture at 7.15 MHz and above: every width from 352x240 to 2560x240, plus 640x480i and 1280x480i. Community reports with lower clocks on nouveau: **GeForce 8400 GS** and **Quadro K600** (Batocera).

Mind the speed: nouveau runs most GTX 600, 700 and 900 cards at their boot clock (it can't raise the clock of Maxwell 2, and on Kepler only by hand). For arcade and 2D consoles that is enough; for PS2, GameCube and Model 3, an AMD card is better, or NVIDIA's own driver.

## NVIDIA's own driver

 In *Setup > Video Setup > Video driver* on a card with an NVIDIA chip. *Compare the two* there lists what each driver gives and takes:

| | nouveau | NVIDIA's own driver |
|---|---|---|
| Programs that change resolution | All: menus, frontends, RetroArch, MAME, standalone emulators | Only those in Xorg (MAME, the standalone emulators) |
| Lowest pixel clock | The card's PLL (7.15 MHz on the GTX 980 Ti) | Any (320x240 at 6.5 MHz), in Xorg |
| 480i | Yes | In Xorg only |
| 3D speed | Boot clock: slow for PS2, GameCube | Full |
| Cards | GeForce 8 to GTX 900 with VGA/DVI-I | GTX 750 to 900 (Maxwell) |

Measured on the same GTX 980 Ti with driver 580: its KMS (`nvidia-drm`) only takes **progressive modes from the EDID**. It drops interlaced ones (an EDID with only 1280x480i leaves no mode at all, and the boot is black) and every mode Switchres adds ("Kernel doesn't supports user modes"). That check is inside NVIDIA's binary module, so no kernel patch reaches it. In Xorg, with `ModeValidation`, `UseEDID false` and its own modelines, every 15 kHz mode worked, as Batocera does on these cards.

Details of the switch:

- **NVIDIA driver** downloads it from Ubuntu's own repository (a few hundred MB), and DKMS compiles its kernel module for the 15 kHz kernel (a few minutes). The package is **`nvidia-driver-580`**, from the GTX 900 (Maxwell, the last with DVI-I) to the current cards; it is the one checked to build on the 15 kHz kernel. The 470 of the GTX 600/700 (Kepler) does not build on kernel 6.18, so those cards and the older ones stay on nouveau.
- Both drivers stay installed; the kernel line chooses (`modprobe.blacklist=nouveau nvidia-drm.modeset=1 nvidia-drm.fbdev=1`, or the NVIDIA modules blacklisted for nouveau). The package's own nouveau blacklist in `/lib/modprobe.d` is overridden by a file of the same name in `/etc/modprobe.d`.
- The switch is on trial, like radeon/amdgpu: after the restart, press Enter to confirm the picture. With no answer in 15 s FliperOS goes back to nouveau and restarts. The boot menu (a key during the countdown) also has **FliperOS - nouveau driver**.
- The low resolution result belongs to a driver, so a switch starts in super resolution. Back on nouveau, once the picture is confirmed, the Setup offers the grid again. The NVIDIA driver has no grid: its KMS doesn't take Switchres modes.
- X uses the `nvidia` driver with mode validation relaxed (`ModeValidation`: modes without EDID, low pixel clocks, any sync range), which a 15 kHz tube needs. RetroArch, Switchres and the console use its KMS (`nvidia-drm`).
- If a kernel update leaves no NVIDIA module for the new kernel, the boot tries DKMS again; with no module, it goes back to nouveau and restarts, so the screen is never left black.

## Without analog output (GTX 10 and newer)

 Super resolution only, through an active converter. RTX 20 and 30 cards need their GSP firmware, which stays in the system (`/usr/lib/firmware/nvidia`).

See also: [Video cards](Video-cards.md), [Video Setup](Setup-Video.md#low-resolutions).
