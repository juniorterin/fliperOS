Which video cards FliperOS supports, and what each one gives on a 15 kHz CRT.

The difference between them is the **dotclock**: a 320x240 game at 15 kHz needs about 6.5 MHz, a 640x480i boot about 13 MHz. A card that generates those clocks shows each game at its **native resolution**.

A card that doesn't uses a **super resolution**: the same lines and the same refresh as the game, with the width multiplied (1280 or 2560 instead of 320). On a CRT the picture is almost the same, since the beam has no horizontal pixels. What gives it away: RetroArch draws its notifications at 2560 wide, so they come out squeezed.

## Summary

| Card | Driver | Analog output | 15 kHz |
| --- | --- | --- | --- |
| AMD/ATI Radeon HD 2000 to HD 7000, R7/R9 200 and 300 (GCN 1.0) | `radeon` or `amdgpu` | VGA, DVI-I | **Native** (recommended) |
| AMD GCN 2 and 3 with DVI-I (R7 260X, R9 380) | `radeon` or `amdgpu` (GCN 2), `amdgpu` (GCN 3) | DVI-I | Reported by GroovyArcade. [The R9 380 needs a kernel parameter](#amdati) |
| AMD Radeon RX and newer, Ryzen APUs | `amdgpu` | None on the card; VGA on some motherboards | Native through a [DisplayPort to VGA converter](#converters); super resolution through HDMI |
| NVIDIA GeForce 8 to GTX 900, Quadro up to K series | `nouveau`, or NVIDIA's own driver (GTX 900) | VGA, DVI-I | Super resolution; **native if the card passes the low resolution test** |
| NVIDIA GTX 10 and newer (Pascal, Turing, Ampere...) | `nouveau` | None | Super resolution, through a converter |
| Intel Gen9 (HD/UHD 500 and 600 series: Skylake to Comet Lake) | `i915` | VGA on the motherboard | Super resolution, with interlace (patch 09) |
| Intel HD Graphics Gen5 (Ironlake: Core i3 5xx, i5 6xx) | `i915` | VGA on the motherboard | Super resolution, 480i, **seen on a CRT**. Only OpenGL 2.1: [no ES-DE, no filter, no Vulkan](#limits-of-the-intel-hd) |
| Other Intel generations | `i915` | VGA on the motherboard | Super resolution; 480i may not work |

Three cards have been seen on a CRT by the project: an AMD R7 240 (`radeon` and `amdgpu`), an Intel HD Graphics (Ironlake, `i915`) and an NVIDIA GTX 980 Ti (`nouveau`). The other lines come from the kernel patches and from what the GroovyArcade and Batocera communities report ([list below](#reported-by-groovyarcade)).

## AMD/ATI

The cards CRT_EmuDriver covers on Windows, with VGA or DVI-I: the HD 2000 series to the R7/R9 200 and 300 with GCN 1.0. The 15 kHz kernel patches cover `radeon` and `amdgpu` (DCE and DCN 1 to 3): native boot at `640x480iS` and every game at its own resolution, in GroovyMAME, RetroArch and the frontends.

Good, cheap choices: **HD 5450, HD 6450, HD 7750, R7 240, R7 250**.

SI and CIK cards (HD 7000, R7/R9) work on both drivers; the Setup picks `radeon` by default and offers `amdgpu` (with Vulkan) in *Video Setup > Video driver*.

The emulators follow the driver the card runs on, checked at every session start: on `amdgpu`, Flycast goes to the Vulkan renderer that matches its OpenGL one (per-pixel or per-triangle) and Dolphin to Vulkan; PCSX2 and DuckStation stay on Automatic, which already picks Vulkan there. Back on `radeon` (no Vulkan), each goes back to its factory renderer: Flycast to OpenGL with per-pixel transparency, Dolphin to OpenGL. RetroArch stays on `glcore` on both: its Vulkan output can't switch the CRT's modes. A choice made in an emulator is kept until the driver changes again.

Cards with no analog output (RX 400 and newer) and the Ryzen APUs need an **active converter**: see [Converters](#converters).

**GCN 2 and 3 cards with DVI-I.** Not every card after GCN 1.0 lost its analog output: GroovyArcade reports the R7 260X on DVI-I and the R9 380 on DVI-I. None of them has been tried on FliperOS.

- **R9 380 and 380X (GCN 3)** only run on `amdgpu`, and on kernel 6.18 its new display code has no analog output (that came in 6.19). They need `amdgpu.dc=0` on the kernel line, which the Setup doesn't add for them: see [Black screen](Black-screen.md#changing-the-kernel-line-by-hand).
- **GCN 2, also called 1.1, on `amdgpu`:** GroovyArcade's table says these cards (HD 7790, R7 260, R7 360) don't do interlaced modes on that driver. It wasn't checked with the `amdgpu.dc=0` FliperOS uses. If the picture is lost after switching to `amdgpu`, the [trial](Installed-system.md) goes back to `radeon` by itself.

**APUs.** GroovyArcade reports Wrestler, Kabini, Kaveri and Mullins working out of the box, and Wani with `amdgpu.dc=0` or an EDID. On any APU the Setup sets `interlace_force_even` in Switchres, which AMD APUs need.

**A VGA connector isn't always analog.** On some APUs and motherboards the VGA port is a DisplayPort to VGA bridge chip. It may not switch modes quickly, make low clocks or do interlaced modes, so results vary by motherboard. GroovyArcade found the ASRock DeskMini A300's to be the best so far.

**ArcadeVGA cards.** GroovyArcade's wiki says they "are not supported and won't work", without saying why, and other reports disagree. One forum thread has an ArcadeVGA 5000 running GroovyArcade at half speed; the documentation of another 15 kHz package says they seem to be supported.

On Windows, forum posts say CRT_EmuDriver doesn't support the 3000 and the 5000, even though the 5000 is an HD 5450 with Ultimarc's own BIOS. The cause on Linux isn't documented, and none has been tried on FliperOS. If you are buying a card, a plain HD 5450 is the safer choice.

**ATOM-15 isn't needed.** Flashing a supported Radeon with [ATOM-15](#atom-15-15-khz-from-power-on) makes it start at 15 kHz from the BIOS, which [GroovyArcade's FAQ](https://gitlab.com/groovyarcade/support/-/wikis/1-About-GroovyArcade/1.3-General-FAQ) describes as protection against out-of-range signals at boot. Once the kernel has loaded, 15 kHz is there either way.

## Converters

A card with only digital outputs can drive a CRT through an **active converter** with a DAC chip inside. A passive adapter doesn't work on a digital output.

**DisplayPort is the one to use.** GroovyArcade reports no lower limit for its pixel clock, so a card that makes low clocks can often show games at their native resolution. An HDMI or DVI-D link doesn't go under about 25 MHz, so it only gives super resolutions.

**Recommended by the GroovyArcade community:**

| Converter | Notes |
| --- | --- |
| **CableDeconn** DisplayPort to VGA ([one sold on AliExpress](https://a.aliexpress.com/_mPCmfYb), with HDMI and DVI outputs too) | Very fragile VGA connector. 5 V on VGA pin 9 |
| **Cable Matters** DisplayPort to VGA (product 102026) | Only 3.2 V on VGA pin 9, which matters if the device after it expects 5 V |

Both use a Realtek RTD2168 chip. The community found no processing of the signal and no measurable lag, apart from the mode switch.

The CableDeconn has also been reported working on a FliperOS cabinet, without a record yet of the card, the driver or the modes.

**What to expect, even with these:**

- **Mode switches are slower** than on a native VGA or DVI-I output.
- **Interlaced modes are hit-or-miss**, mostly misses. So FliperOS' default 15 kHz boot (`640x480iS`) may stay black: use the **EDID progressive** entry of the boot menu, which GroovyArcade calls the most compatible for these outputs, or a progressive mode ([Black screen](Black-screen.md#black-from-the-boot)).
- **Some modes may be refused.** If only some games go black, raise [`dotclock_min`](Black-screen.md#the-menus-work-some-games-go-black).

**Protecting the CableDeconn's connector.** Users fix a VGA gender changer to it with 4-40 hex screws, so the changer takes the wear of plugging and unplugging. Use screws of 10 or 12 mm: **never longer than 12 mm**.

**In the Setup:** the output test skips a digital output that reports nothing connected.

On HDMI or DVI-D with a CRT preset, the Setup uses super resolutions by itself, even on an AMD card: `1280x480iS` at boot and `dotclock_min 25.0`. An LCD on those outputs isn't affected. On DisplayPort an AMD card stays native.

**A converter with its own EDID.** Most converters report an EDID of their own, with 31 kHz modes, so the output test takes them for an LCD ("Found a monitor that could be a LCD panel"). When you then choose a CRT monitor, the Setup replaces the converter's EDID with a 15 kHz one (`generic_15_super_resp.bin`, as in the *EDID progressive* boot entry). Without it the menu came up at 1024x768 and 48 kHz and the tube stayed black, and so did the screen after leaving a game, although the games, which set their own modes, were fine. A `video=1280x480iS` line alone didn't fix it: the console used it, but the frontend opens the first mode of the list, the converter's. Games stay native on a card with low dotclocks.

**Seen with one CableDeconn-type converter** (Ryzen 5 5600GT, `amdgpu`, DisplayPort), with a numbered test card for each mode and the person reading the numbers on the tube: native modes from 224 to 640 pixels wide (4.5 to 13.0 MHz) and from 712 to 2560 wide (14.5 to 52 MHz) showed, `1280x480i` too. Modes between about 13.1 and 14.4 MHz (672 to 704 wide) and below 4 MHz (192 wide and less) gave no signal, though the kernel had set them. So a game of those widths can go black on this converter: raise [`dotclock_min`](Black-screen.md#the-menus-work-some-games-go-black). Other converters and monitors may differ.

For a third monitor on a converter, see [Multiple monitors](Multiple-Monitors.md).

## Reported by GroovyArcade

Cards in the [GroovyArcade wiki's list of tested GPUs](https://gitlab.com/groovyarcade/support/-/wikis/2-Pre-Requisites-and-Installation/2.1-Hardware-Suggestions-General#tested-gpus). They ran on its kernel, not on FliperOS, but it is the same family of 15 kHz patches. Older cards than these should work but aren't recommended.

| Card | Driver | Output | Notes |
| --- | --- | --- | --- |
| HD 5450, HD 5570, HD 5750, HD 6450, R7 250 | `radeon` | VGA, DVI-I | Out of the box |
| HD 6320 (Wrestler) | `radeon` | VGA, DVI-I | Out of the box |
| HD 8400E (Kabini) | `radeon` | VGA, DVI-I | Out of the box; `dotclock_min 6` for perfect sync in every game |
| HD 7520G (Trinity) | `radeon` | VGA, DisplayPort | `video=VGA-1:640x240S`, no interlaced modes, `dotclock_min 12` |
| A8 APU | `radeon` | DisplayPort | With a converter and an EDID; its VGA is a bridge that works badly |
| R5 (Mullins, GX-242CC) | `radeon` | VGA, DVI-I | With an EDID |
| R7 260X | `radeon` | DVI-I | With an EDID |
| R7 350X | `radeon` | DisplayPort | With an EDID |
| Ryzen 2200G, 2400G | `amdgpu` | VGA, DisplayPort | The bridged VGA may lack low clocks or interlace, depending on the motherboard |
| Ryzen 2200GE | `amdgpu` | VGA, DisplayPort | Same; disable legacy BIOS boot if the screen goes black at random |
| Ryzen 3400G | `amdgpu` | VGA | A 1280x240 EDID and `video=DP-1:e` |
| R7 (Wani, A10-8800E) | `amdgpu` | DisplayPort | EDID `generic_15_super_resp.bin` and `dotclock_min 25` |
| RX 5700 XT (Navi 10) | `amdgpu` | DisplayPort | With an EDID |
| R9 380, 380X | `amdgpu` | DVI-I | Needs `amdgpu.dc=0`; to be confirmed since Linux 6.19 |

"With an EDID" means booting the EDID entries of the boot menu, or a monitor's file from `edid/` ([Install](Install.md#boot-menu)).

If yours works on FliperOS, open an [issue](https://github.com/juniorterin/fliperOS/issues) with the card, the driver, the output and what you saw: that is what turns a line here into "seen on FliperOS".

## ATOM-15: 15 kHz from power on

**This rewrites your video card's BIOS chip, at your own risk.** A bad result can leave the card dead, with no picture even at power on. FliperOS cannot repair that: it takes a second video card (usually not the one on the motherboard) or a chip programmer. It is an experimental community tool, not made by AMD or the card's maker.

[ATOM-15](https://github.com/antonioginer/ATOM-15), by Antonio Giner "Calamity", changes the video modes in the BIOS of an ATI/AMD card, so the computer's own startup screens already come out at 15 kHz, instead of signals out of the monitor's range until the system starts. It changes nothing after that: games and menus already run at 15 kHz without it.

*Video Setup > Card firmware* appears with an AMD card on the installed system, at the cabinet (not over SSH, since you have to watch the next boot).

**Opening it reads the card first.** The menu says what the BIOS on the card has (*ATOM-15* or *No ATOM-15*), even if the card came that way, and saves a copy in `~/vbios`. With the flash tool it reads the chip. Without it, it uses the copy the system has from this boot, in `~/vbios/card-<card>-<sum>.rom`, which is only for checking: only a read of the chip, with no ATOM-15 in it, can be flashed back as the original. A card that already has ATOM-15 has nothing to apply, and *Restore* only appears if the original BIOS was saved on this computer.

**To flash, you need the flash tool.** `amdvbflash` is AMD's, closed, and AMD does not publish it, so FliperOS does not ship or download it. Get the 64-bit Linux version yourself (the TechPowerUp forums have it) and put the file at `~/vbios/amdvbflash`. It runs as root, so use a copy you trust. It does not work with Secure Boot on.

**What the Setup does, in order:**

1. The warnings, with *No* as the default. In UEFI mode one more: ATOM-15 is not guaranteed there, the computer's setup screen can stay black, and a patched BIOS loses the signature of its EFI part (a bricked R9 380 has been reported that way).
2. Reads the card's BIOS twice with `amdvbflash -s` and compares. If it is good and belongs to this card, the **backup** goes to `~/vbios/original-<card>-<sum>.rom`, and the Setup shows where. **Copy it off the computer:** if the card dies, this machine may show no picture to reach it.
3. Makes the patched BIOS for the monitor's frequencies: `~/vbios/atom15-<card>-<range>khz.rom`, with a log of each mode next to it. A BIOS that already has the hook, a card outside ATOM-15's list, or a BIOS with no room for the hook outside its EFI part is refused here, with the card untouched.
4. Flashes it after one more question, reads it back and compares. If that fails, the original goes back right away.
5. **Reboot and test.** Watch the screen from the first second. Before the frontend, a question asks if the startup screens were stable. Enter (button 1) within 90 seconds keeps it.

**With no answer, or with Esc, the original BIOS is flashed back and the computer restarts.** A guard service (`fliperos-atom15-guard.service`) does the same if the question never opens within 5 minutes, or if the test boot hung and the computer was turned off. *Card firmware > Restore the original BIOS* puts it back later.

A card that does not pass the power-on test never reaches the system, so **none of this can undo it**; that is the risk the warning is about. To flash the backup by hand from another card: `amdvbflash -p <adapter> original-<card>-<sum>.rom`.

**How far this was tested:** the patch is a translation of ATOM-15 v1.6 to Python (`config/fliperos-atom15`), made with the author's permission, because the original is Windows-only, with no command line. Against a BIOS written by the real `atom-15.exe` (R7 240, 15 kHz) all 65536 bytes came out the same (`tools/atom15-check.py`). Other card families, other ranges and the move of the EFI part use the same code but were not compared. **The flash, the test at the next boot and the way back have only run with a fake flash tool**, never on a real card.

## NVIDIA

NVIDIA cards run on the open driver, **nouveau**, out of the box. On the installed system, *Setup > Video Setup > Video driver* can switch to **NVIDIA's own driver** (see below).

**With VGA or DVI-I (GeForce 8 to GTX 900, Quadro up to the K series).** Out of the box nouveau refuses every mode under 25 MHz. FliperOS's own kernel patch (`10_fliperos_nouveau_analog_low_dotclock.patch`) lifts that floor on the analog outputs, but whether each card's PLL actually reaches 6.5 MHz varies.

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

<a id="nvidia-driver"></a>**NVIDIA's own driver.** In *Setup > Video Setup > Video driver* on a card with an NVIDIA chip. *Compare the two* there lists what each driver gives and takes:

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

**Without analog output (GTX 10 and newer).** Super resolution only, through an active converter. RTX 20 and 30 cards need their GSP firmware, which stays in the system (`/usr/lib/firmware/nvidia`).

## Intel

Intel integrated graphics use the **Intel 15 kHz** boot entry, always in super resolution (`1280x480iS`): `i915` doesn't generate the low clocks.

**You need a monitor at a standard frequency first.** The boot menu and the installation are drawn at 31 kHz, so on an Intel HD connect a regular VGA monitor (an LCD or a PC monitor), boot the media, install FliperOS and set the video with it. Only then power off, move the cable to the CRT and turn the cabinet on.

In Setup > Video Setup > Resolution an Intel card also lists **1280x240 60 Hz progressive** (240p, no interlace flicker in the menus). It is not in the kernel's mode table, so the Setup writes an EDID with that mode (`fliperos-1280x240.bin`, 26.058 MHz, 15.66 kHz), puts it in the initramfs and points `drm.edid_firmware` at it. Pick the 480i entry again to go back. **Seen on the tube** (Core i3-540, VGA).

The same mode is in the media's boot menu as **Intel 15 kHz 240p** (next to *Intel 15 kHz*): the installer, the Setup and the frontend already come up in progressive 240p, and the installed system keeps it. The image builds the EDID (`fliperos-rebuild-edids`); on the installed disk it goes into the initramfs.

On **Gen9** (Skylake, Kaby Lake, Coffee Lake, Comet Lake) patch 09 enables interlace, with `i915.no_ytiled_scanout=1` on the kernel line. Other generations have no interlace patch: 240p works, 480i may not.

The VGA port of many motherboards is a DisplayPort to VGA bridge chip on the board, so results vary by motherboard.

### What was tested

Seen working on a CRT, through the VGA output, installed from the **Intel 15 kHz** boot entry:

- **Card:** Intel HD Graphics of a Core i3-540 (Clarkdale, Ironlake, Gen5), driver `i915`, kernel 6.18, Mesa 25.2.
- **Works:** the boot menu and the Setup (1280x480i), the **FliperOS frontend**, **RetroArch** (each game in its own super resolution, such as 2560x224), **GroovyMAME** and **Attract-Mode Plus**.
- **Starts, games not tried:** Pegasus.
- **Also seen:** the 1280x240 progressive mode above.
- **Not seen on the tube:** any other Intel generation, and the 3D emulators.

### Limits of the Intel HD

What a user of this card has to know:

- **No native low resolutions.** The card can't generate a pixel clock under about 25 MHz, so a 320x240 game is shown as 2560x240 (same lines, same refresh, wider). On a CRT the picture is almost the same. The boot, the Setup and the frontend are in 1280x480i by default: interlaced, so thin horizontal lines flicker. The 1280x240 option above is the way out, once it is checked on a tube.
- **OpenGL 2.1 and OpenGL ES 2.0 only** (Ironlake; the Mesa driver is `crocus`). Everything that asks for OpenGL 3 does not run:
  - **EmulationStation-DE does not open** (it needs OpenGL 3.3 or OpenGL ES 3.0). Setup > Games > Frontend marks it with a red X and a warning, asks before choosing it, and the installer refuses to build it. Pegasus (Qt, OpenGL ES 2.0) is not affected.
  - **RetroArch uses its `gl` driver instead of `glcore`**: `fliperos-kms-run` checks the card and switches by itself. A core or a shader that needs OpenGL 3 will not work.
  - **The 480i flicker filter and the software colour adjustments are off** (the log says `OpenGL 3.0 or newer is needed; filter off for this program`). Setup > Video Setup > 480i hacks has no effect on this card.
- **No Vulkan on Ironlake.** Emulators that need it (the Vulkan renderers of Flycast, Dolphin, PCSX2, DuckStation) are not usable, and the Vulkan-by-driver switch of the Setup only acts on `amdgpu`. Not tested; it follows from the hardware. The same goes for the 3D emulators on a card from 2010: not tried.
- **The processor must have graphics.** The VGA port of a board only works with a CPU that has them: Clarkdale (Core i3 5xx, i5 6xx) does; Lynnfield (Core i7 8xx, i5 7xx) does not, and the board shows no video device at all (seen on an i7 870).
- **Changing the video card (or the CPU that has the graphics) is noticed at boot.** See [Changing the video card](#changing-the-video-card) below. **Recovery Mode** of the media (see [Install](Install.md)) stays as the last resort.

### Changing the video card

The output test stores the card's PCI id (`gpu_id` in `/etc/fliperos/fliperos.conf`). At each boot the installed system checks that the card is still there; a card that comes or goes but is not the main one (a new CPU graphics with the AMD still in) changes nothing.

When the main card changed:

1. **Before any picture** (`fliperos-driver-trial.service`): FliperOS writes a safe mode for the new card on its first analog output, with the monitor that was set (native boot mode on a card that makes low clocks, `1280x480iS` on an Intel), drops what belonged to the old card (extra monitors, the NVIDIA grid step) and **reboots once**. A saved `320x240` mode on an Intel, which can't make that clock, no longer leaves the screen black. Without an analog output, or with an LCD monitor, it only marks the change.
2. **Before the frontend opens** (also when the boot goes straight into a game): a question says which card it was and which it is now, and offers to redo the **output test**. *Yes* runs the same test as the installation, saves the result (kernel line, Switchres, RetroArch, Xorg) and offers a reboot. *No* asks again at the next boot; after three answers it accepts the card.

Installs from before this feature have no `gpu_id`: the first boot compares the saved driver with the cards that are there, and records the id if they match.

**Setup > Video Setup > Test the video outputs** asks for the same test on the next boot (it needs the screen free, without the graphic menu open).

### What the Setup marks as not supported

On a card that gives less than OpenGL 3, the Setup marks the item with a red X (and `(not supported)` in the text menus), shows the reason (`Needs OpenGL 3.3 or Vulkan, and this video card gives OpenGL 2.1 and OpenGL ES 2.0`) and asks before opening it (the default is *No*). The check reads the card with `eglinfo`; without it, nothing is marked.

| Where | Item | Needs |
| --- | --- | --- |
| Games > Frontend | EmulationStation-DE | OpenGL 3.3 or OpenGL ES 3.0 |
| Video Setup | 480i hacks (the flicker filter) | OpenGL 3.0 |
| Games > Emulators & Games | PCSX2, Dolphin, DuckStation | OpenGL 3.3 or Vulkan (each project's own minimum) |

Flycast, Supermodel and the other emulators are not marked: their minimum was not checked against this card.

### Intel-specific workarounds in FliperOS

Three things only the Intel showed, fixed in the code:

- **The screen was not released after a program closed it.** On Ironlake the Mesa leaves descriptors of `/dev/dri/card0` open after `pygame.display.quit()`, so the process stayed the owner (DRM master) of the screen: RetroArch failed with `Error when switching mode` and the frontend could not reopen (`kmsdrm not available`). `gui/drmmaster.py` drops the master after the display is closed (frontend and Setup).
- **Attract-Mode Plus showed a black screen** because SFML makes its buffer in ARGB8888, which Ironlake refuses to scan out (`Failed to create fb`). The package `fliperos-attractplus` carries two SFML patches: a fallback to XRGB8888 (`0002`) and the same drop of the master when its context is cleaned up (`0003`).
- **The frontend chooser** marks what the card can't run (see above).

## Several cards

A second card for a second or third monitor works best if it is AMD too. See [Multiple monitors](Multiple-Monitors.md).
