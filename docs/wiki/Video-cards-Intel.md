Intel integrated graphics work on a CRT in super resolution, through the motherboard's VGA output.

Intel integrated graphics use the **Intel 15 kHz** boot entry, always in super resolution (`1280x480iS`): `i915` doesn't generate the low clocks.

**You need a monitor at a standard frequency first.** The boot menu and the installation are drawn at 31 kHz, so on an Intel HD connect a regular VGA monitor (an LCD or a PC monitor), boot the media, install FliperOS and set the video with it. Only then power off, move the cable to the CRT and turn the cabinet on.

In Setup > Video Setup > Resolution an Intel card also lists **1280x240 60 Hz progressive** (240p, no interlace flicker in the menus). It is not in the kernel's mode table, so the Setup writes an EDID with that mode (`fliperos-1280x240.bin`, 26.058 MHz, 15.66 kHz), puts it in the initramfs and points `drm.edid_firmware` at it. Pick the 480i entry again to go back. **Seen on the tube** (Core i3-540, VGA).

The same mode is in the media's boot menu as **Intel 15 kHz 240p** (next to *Intel 15 kHz*): the installer, the Setup and the frontend already come up in progressive 240p, and the installed system keeps it. The image builds the EDID (`fliperos-rebuild-edids`); on the installed disk it goes into the initramfs.

On **Gen9** (Skylake, Kaby Lake, Coffee Lake, Comet Lake) patch 09 enables interlace, with `i915.no_ytiled_scanout=1` on the kernel line. Other generations have no interlace patch: 240p works, 480i may not.

The VGA port of many motherboards is a DisplayPort to VGA bridge chip on the board, so results vary by motherboard.

## What was tested

Seen working on a CRT, through the VGA output, installed from the **Intel 15 kHz** boot entry:

- **Card:** Intel HD Graphics of a Core i3-540 (Clarkdale, Ironlake, Gen5), driver `i915`, kernel 6.18, Mesa 25.2.
- **Works:** the boot menu and the Setup (1280x480i), the **FliperOS frontend**, **RetroArch** (each game in its own super resolution, such as 2560x224), **GroovyMAME** and **Attract-Mode Plus**.
- **Starts, games not tried:** Pegasus.
- **Also seen:** the 1280x240 progressive mode above.
- **Not seen on the tube:** any other Intel generation, and the 3D emulators.

## Limits of the Intel HD

What a user of this card has to know:

- **No native low resolutions.** The card can't generate a pixel clock under about 25 MHz, so a 320x240 game is shown as 2560x240 (same lines, same refresh, wider). On a CRT the picture is almost the same. The boot, the Setup and the frontend are in 1280x480i by default: interlaced, so thin horizontal lines flicker. The 1280x240 option above is the way out, once it is checked on a tube.
- **OpenGL 2.1 and OpenGL ES 2.0 only** (Ironlake; the Mesa driver is `crocus`). Everything that asks for OpenGL 3 does not run:
  - **EmulationStation-DE does not open** (it needs OpenGL 3.3 or OpenGL ES 3.0). Setup > Games > Frontend marks it with a red X and a warning, asks before choosing it, and the installer refuses to build it. Pegasus (Qt, OpenGL ES 2.0) is not affected.
  - **RetroArch uses its `gl` driver instead of `glcore`**: `fliperos-kms-run` checks the card and switches by itself. A core or a shader that needs OpenGL 3 will not work.
  - **The interlaced flicker filter and the software colour adjustments are off** (the log says `OpenGL 3.0 or newer is needed; filter off for this program`). Setup > Video Setup > Interlaced hacks has no effect on this card.
- **No Vulkan on Ironlake.** Emulators that need it (the Vulkan renderers of Flycast, Dolphin, PCSX2, DuckStation) are not usable, and the Vulkan-by-driver switch of the Setup only acts on `amdgpu`. Not tested; it follows from the hardware. The same goes for the 3D emulators on a card from 2010: not tried.
- **The processor must have graphics.** The VGA port of a board only works with a CPU that has them: Clarkdale (Core i3 5xx, i5 6xx) does; Lynnfield (Core i7 8xx, i5 7xx) does not, and the board shows no video device at all (seen on an i7 870).
- **Changing the video card (or the CPU that has the graphics) is noticed at boot.** See [Changing the video card](Video-cards.md#changing-the-video-card) below. **Recovery Mode** of the media (see [Install](Install.md)) stays as the last resort.

## Intel-specific workarounds in FliperOS

Three things only the Intel showed, fixed in the code:

- **The screen was not released after a program closed it.** On Ironlake the Mesa leaves descriptors of `/dev/dri/card0` open after `pygame.display.quit()`, so the process stayed the owner (DRM master) of the screen: RetroArch failed with `Error when switching mode` and the frontend could not reopen (`kmsdrm not available`). `gui/drmmaster.py` drops the master after the display is closed (frontend and Setup).
- **Attract-Mode Plus showed a black screen** because SFML makes its buffer in ARGB8888, which Ironlake refuses to scan out (`Failed to create fb`). The package `fliperos-attractplus` carries two SFML patches: a fallback to XRGB8888 (`0002`) and the same drop of the master when its context is cleaned up (`0003`).
- **The frontend chooser** marks what the card can't run (see above).

See also: [Video cards](Video-cards.md), [Black screen](Black-screen.md).
