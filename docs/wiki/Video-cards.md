Which video cards FliperOS supports, and what each one gives on a 15 kHz CRT.

The difference between them is the **dotclock**: a 320x240 game at 15 kHz needs about 6.5 MHz, a 640x480i boot about 13 MHz. A card that generates those clocks shows each game at its **native resolution**.

A card that doesn't uses a **super resolution**: the same lines and the same refresh as the game, with the width multiplied (1280 or 2560 instead of 320). On a CRT the picture is almost the same, since the beam has no horizontal pixels. What gives it away: RetroArch draws its notifications at 2560 wide, so they come out squeezed.

## Summary

| Card | Driver | Analog output | 15 kHz |
| --- | --- | --- | --- |
| AMD/ATI Radeon HD 2000 to HD 7000, R7/R9 200 and 300 (GCN 1.0) | `radeon` or `amdgpu` | VGA, DVI-I | **Native** (recommended) |
| AMD Radeon RX and newer, Ryzen APUs | `amdgpu` | None on the card; VGA on some motherboards | Native, through an active DisplayPort/HDMI to VGA converter that accepts low clocks |
| NVIDIA GeForce 8 to GTX 900, Quadro up to K series | `nouveau` | VGA, DVI-I | Super resolution; **native if the card passes the low resolution test** |
| NVIDIA GTX 10 and newer (Pascal, Turing, Ampere...) | `nouveau` | None | Super resolution, through a converter |
| Intel Gen9 (HD/UHD 500 and 600 series: Skylake to Comet Lake) | `i915` | VGA on the motherboard | Super resolution, with interlace (patch 09) |
| Other Intel generations | `i915` | VGA on the motherboard | Super resolution; 480i may not work |

Only one card has been seen on a CRT by the project: an AMD R7 240 (`radeon`). The other lines come from the kernel patches and from what the GroovyArcade and Batocera communities report.

## AMD/ATI

The cards CRT_EmuDriver covers on Windows, with VGA or DVI-I: the HD 2000 series to the R7/R9 200 and 300 with GCN 1.0. The 15 kHz kernel patches cover `radeon` and `amdgpu` (DCE and DCN 1 to 3): native boot at `640x480iS` and every game at its own resolution, in GroovyMAME, RetroArch and the frontends.

Good, cheap choices: **HD 5450, HD 6450, HD 7750, R7 240, R7 250**.

SI and CIK cards (HD 7000, R7/R9) work on both drivers; the Setup picks `radeon` by default and offers `amdgpu` (with Vulkan) in *Video Setup > Video driver*.

Cards with no analog output (RX 400 and newer) and the Ryzen APUs need an **active DisplayPort or HDMI to VGA converter**. The card generates the low clocks; whether they reach the tube depends on the converter's chip, so pick one that the GroovyMAME community reports for 15 kHz.

## NVIDIA

NVIDIA cards run on the open driver, **nouveau**. The proprietary driver is not in FliperOS.

**With VGA or DVI-I (GeForce 8 to GTX 900, Quadro up to the K series).** Out of the box nouveau refuses every mode under 25 MHz. FliperOS's own kernel patch (`10_fliperos_nouveau_analog_low_dotclock.patch`) lifts that floor on the analog outputs, but whether each card's PLL actually reaches 6.5 MHz varies.

So the card is tested on the tube:

1. boot the **NVIDIA 15 kHz** entry (super resolution, `1280x480iS`);
2. after you confirm the output in the video output test, the Setup shows a **Switchres grid at 320x240** for 20 seconds;
3. saw the grid → native resolutions (boot at `640x480iS`, `dotclock_min 0`, RetroArch at native width);
4. black screen or no answer → super resolutions, as before. Nothing is lost by trying.

The test can be repeated on the installed system in *Setup > Video Setup > Low resolutions*. It only runs on an analog output with a 15 kHz monitor.

Community reports with low clocks on nouveau: **GeForce 8400 GS** and **Quadro K600** (Batocera). No NVIDIA card has been seen on a CRT by the project yet.

Mind the speed: nouveau runs most GTX 600, 700 and 900 cards at their boot clock (it can't raise the clock of Maxwell 2, and on Kepler only by hand). For arcade and 2D consoles that is enough; for PS2, GameCube and Model 3, an AMD card is better.

**Without analog output (GTX 10 and newer).** Super resolution only, through an active converter. RTX 20 and 30 cards need their GSP firmware, which stays in the system (`/usr/lib/firmware/nvidia`).

## Intel

Intel integrated graphics use the **Intel 15 kHz** boot entry, always in super resolution (`1280x480iS`): `i915` doesn't generate the low clocks.

On **Gen9** (Skylake, Kaby Lake, Coffee Lake, Comet Lake) patch 09 enables interlace, with `i915.no_ytiled_scanout=1` on the kernel line. Other generations have no interlace patch: 240p works, 480i may not.

The VGA port of many motherboards is a DisplayPort to VGA bridge chip on the board, so results vary by motherboard.

## Several cards

A second card for a second or third monitor works best if it is AMD too. See [Multiple monitors](Multiple-Monitors.md).
