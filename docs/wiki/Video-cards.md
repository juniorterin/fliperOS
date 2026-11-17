Which video cards FliperOS supports, and what each one gives on a 15 kHz CRT.

The difference between them is the **dotclock**: a 320x240 game at 15 kHz needs about 6.5 MHz, a 640x480i boot about 13 MHz. A card that generates those clocks shows each game at its **native resolution**.

A card that doesn't uses a **super resolution**: the same lines and the same refresh as the game, with the width multiplied (1280 or 2560 instead of 320). On a CRT the picture is almost the same, since the beam has no horizontal pixels. What gives it away: RetroArch draws its notifications at 2560 wide, so they come out squeezed.

**Each game opened is checked against the card.** On a card that only makes super resolutions, a game has to stretch itself across the wide mode. RetroArch, GroovyMAME, Flycast, PCSX2, Dolphin, DuckStation, Supermodel, Model 2 and Hypseus already do. For the others, FliperOS changes the game's own settings when it opens (`fliperos-gpufit`):

| Game | What changes | Result |
| --- | --- | --- |
| OpenBOR (4 and 3.0) | Its *stretch* option, in each `.cfg` of `Saves/` | Fills the screen (seen on a CRT) |
| Ikemen GO (KOF Final Attack, custom games with `save/config.ini`) | `WindowWidth`/`WindowHeight` at the wide mode, `KeepAspect = 0` | Fills the screen (seen on a CRT) |
| MUGEN (custom games with `data/mugen.cfg`) | `Width`/`Height` of `[Video]` at the wide mode | Opens, but narrow: MUGEN 1.0 keeps 4:3, and its OpenGL mode scattered the picture |
| Other custom games, the Fightcade lobby | Nothing | Narrow, or doesn't open |

When the game can't fill the screen, an orange **VIDEO CARD WARNING** bar shows at the bottom of the screen for a few seconds, over the game. The 240p hack of custom games doesn't work on these cards: the X can't enlarge a screen into the wide mode (the tube stays black), so it is turned off there. On a card that makes the game's own mode (another card, another monitor), the next launch puts the old settings back (kept in `~/.local/share/fliperos/gpufit.json`).

| Page | What it covers |
| --- | --- |
| [AMD cards](Video-cards-AMD.md) | Which Radeons, the drivers and Vulkan, GCN 2 and 3 with DVI-I, APUs, the cards GroovyArcade reports |
| [NVIDIA cards](Video-cards-NVIDIA.md) | nouveau and the low resolution test, NVIDIA's own driver, cards without analog output |
| [Intel graphics](Video-cards-Intel.md) | Super resolution, the 240p mode, what was tested, the limits of the Intel HD |
| [Converters](Converters.md) | DisplayPort or HDMI to VGA: which ones, what to expect, what the Setup does |
| [ATOM-15](ATOM-15.md) | 15 kHz from power on, in the card's BIOS: how the Setup flashes it, at your own risk |

## Summary

| Card | Driver | Analog output | 15 kHz |
| --- | --- | --- | --- |
| AMD/ATI Radeon HD 2000 to HD 7000, R7/R9 200 and 300 (GCN 1.0) | `radeon` or `amdgpu` | VGA, DVI-I | **Native** (recommended) |
| AMD GCN 2 and 3 with DVI-I (R7 260X, R9 380) | `radeon` or `amdgpu` (GCN 2), `amdgpu` (GCN 3) | DVI-I | Reported by GroovyArcade. [The R9 380 needs a kernel parameter](Video-cards-AMD.md#gcn-2-and-3-cards-with-dvi-i) |
| AMD Radeon RX and newer, Ryzen APUs | `amdgpu` | None on the card; VGA on some motherboards | Native through a [DisplayPort to VGA converter](Converters.md); super resolution through HDMI |
| NVIDIA GeForce 8 to GTX 900, Quadro up to K series | `nouveau`, or NVIDIA's own driver (GTX 900) | VGA, DVI-I | Super resolution; **native if the card passes the low resolution test** |
| NVIDIA GTX 10 and newer (Pascal, Turing, Ampere...) | `nouveau` | None | Super resolution, through a converter |
| Intel Gen9 (HD/UHD 500 and 600 series: Skylake to Comet Lake) | `i915` | VGA on the motherboard | Super resolution, with interlace (patch 09) |
| Intel HD Graphics Gen5 (Ironlake: Core i3 5xx, i5 6xx) | `i915` | VGA on the motherboard | Super resolution, 480i, **seen on a CRT**. Only OpenGL 2.1: [no ES-DE, no filter, no Vulkan](Video-cards-Intel.md#limits-of-the-intel-hd) |
| Other Intel generations | `i915` | VGA on the motherboard | Super resolution; 480i may not work |

Three cards have been seen on a CRT by the project: an AMD R7 240 (`radeon` and `amdgpu`), an Intel HD Graphics (Ironlake, `i915`) and an NVIDIA GTX 980 Ti (`nouveau`). The other lines come from the kernel patches and from what the GroovyArcade and Batocera communities report ([list below](Video-cards-AMD.md#reported-by-groovyarcade)).

## Changing the video card

The output test stores the card's PCI id (`gpu_id` in `/etc/fliperos/fliperos.conf`). At each boot the installed system checks that the card is still there; a card that comes or goes but is not the main one (a new CPU graphics with the AMD still in) changes nothing.

The check looks at the PCI bus, where the card is from power-on, with or without its driver. It runs early in the boot, and the video driver can come after it (an R9 380's `amdgpu` came 1 s later): until then only `simpledrm`, the firmware's framebuffer with no PCI id, is a video card, and the card seemed changed. Cabinets that got that false question lose it by themselves: when the saved card is there and the boot wrote no safe mode for another one, the flag is dropped without asking.

When the main card changed:

1. **Before any picture** (`fliperos-driver-trial.service`): FliperOS writes a safe mode for the new card on its first analog output, with the monitor that was set (native boot mode on a card that makes low clocks, `1280x480iS` on an Intel), drops what belonged to the old card (extra monitors, the NVIDIA grid step) and **reboots once**. A saved `320x240` mode on an Intel, which can't make that clock, no longer leaves the screen black. Without an analog output, or with an LCD monitor, it only marks the change.
2. **Before the frontend opens** (also when the boot goes straight into a game): a question says which card it was and which it is now, and offers to redo the **output test**. *Yes* runs the same test as the installation, saves the result (kernel line, Switchres, RetroArch, Xorg) and offers a reboot. *No* asks again at the next boot; after three answers it accepts the card.

Installs from before this feature have no `gpu_id`: the first boot compares the saved driver with the cards that are there, and records the id if they match.

**Setup > Video Setup > Test the video outputs** asks for the same test on the next boot (it needs the screen free, without the graphic menu open).

## What the Setup marks as not supported

On a card that gives less than OpenGL 3, the Setup marks the item with a red X (and `(not supported)` in the text menus), shows the reason (`Needs OpenGL 3.3 or Vulkan, and this video card gives OpenGL 2.1 and OpenGL ES 2.0`) and asks before opening it (the default is *No*). The check reads the card with `eglinfo`; without it, nothing is marked.

| Where | Item | Needs |
| --- | --- | --- |
| Games > Frontend | EmulationStation-DE | OpenGL 3.3 or OpenGL ES 3.0 |
| Video Setup | Interlaced hacks (the flicker filter) | OpenGL 3.0 |
| Games > Emulators & Games | PCSX2, Dolphin, DuckStation | OpenGL 3.3 or Vulkan (each project's own minimum) |

Flycast, Keisho and the other emulators are not marked: their minimum was not checked against this card.

## Several cards

A second card for a second or third monitor works best if it is AMD too. See [Multiple monitors](Multiple-Monitors.md).

<a id="amdati"></a><a id="converters"></a><a id="reported-by-groovyarcade"></a><a id="atom-15-15-khz-from-power-on"></a><a id="nvidia"></a><a id="nvidia-driver"></a><a id="intel"></a><a id="limits-of-the-intel-hd"></a>
## Where sections moved

This page used to hold every card. AMD, converters, ATOM-15, NVIDIA and Intel are now on the pages above.

See also: [Monitors](Monitors.md), [Video Setup](Setup-Video.md).
