# Multiple monitors

Some arcade games were built for two or three monitors side by side or stacked: Darius and The Ninja Warriors (3 screens in a row), Punch-Out!! and Super Punch-Out!! (2 screens, one above the other), Ferrari F355 Challenge, Airline Pilots and Sega Strike Fighter (3 screens in a row, one NAOMI board per screen). FliperOS drives **two arcade CRTs** from the analog outputs of one video card, and up to **three** with a second video card or an active converter on a digital output (both experimental). When a game has 2 or more screens and the multi-screen mode is on, the emulator sends each screen to its own monitor. Every other game stays on monitor 1.

## What you need

- A video card with one **analog output** (VGA, DVI-I) for each monitor, supported by the [15 kHz kernel](Kernel-15-kHz.md). The tested way is every monitor on the **same card** as monitor 1; a second card is experimental (below). Older Radeons with VGA + DVI-I (HD 5000, 6000 and 7000 series, like the HD 5450 or HD 6450) are the tested way to get 2 CRTs. These cards usually have **two DACs**, so even with VGA + 2 DVI-I outputs only two analog monitors work at the same time.
- Check the DVI connector: only **DVI-I** (the 4 extra pins around the flat blade) carries analog VGA, and works with a passive DVI-to-VGA adapter. **DVI-D** is digital only. For example the Radeon R7 240 has VGA + DVI-D + HDMI: only one analog output.
- Monitors of the **same type** as monitor 1 (Setup > Video Setup > Monitor Type): they get the same video mode.
- Monitor 1 already chosen by the output test (boot menu or Setup > Video Setup).

### Digital outputs with an active converter (experimental)

An HDMI, DVI-D or DisplayPort output can drive a CRT through an **active** converter to VGA (one with a DAC chip inside; passive adapters don't work). The Setup lists these outputs as *digital, active VGA converter, experimental*. This is **not tested yet** on a cabinet:
- A digital link can't go below about 25 MHz of pixel clock, so the extra monitor boots in the **super resolution** of the monitor's preset (`video=HDMI-A-1:1280x480iSe` at 15 kHz: the same lines and frequencies, with thinner pixels), and the Xorg configuration doesn't give it monitor 1's low-dotclock modeline.
- Many cheap converters refuse non-standard modes, interlaced modes or low frequencies. If the monitor stays black, try another converter.
- GroovyMAME's Switchres makes each game's mode for every screen with the card's own limits; on an AMD card these can go below the converter's minimum, and that screen goes black. Flycast's 3-screen games only use analog outputs for now.

### A second video card (experimental)

With two or more PCI/PCIe slots, the extra monitors can be on **another video card**. The Setup lists its outputs as `card1:VGA-1 (AMD Radeon ...)`, and `fliperos.conf` saves them with the card in front (`screens=VGA-1,DVI-I-1,card1:VGA-1`). This is **not tested yet** on a cabinet:
- **Monitor 1's card draws everything.** X opens on it (its `BusID` is in `/etc/X11/xorg.conf.d/10-fliperos.conf`) and adds the other card as a *GPU screen* (`AutoAddGPU`, `AutoBindGPU`): its outputs join the same desktop, and the picture is copied to them (reverse PRIME). In XRandR they get another name: `VGA-1` of the first extra card is `VGA-1-1`, of the second `VGA-1-2`. `fliperos-multiscreen xnames` makes that translation for GroovyMAME and Flycast, and binds the card (`xrandr --setprovideroutputsource`) if X didn't.
- **The kernel's `video=` goes by connector name, on every card.** `video=VGA-1:640x480iSe` sets the VGA-1 of both cards, so an extra monitor on a second card's `VGA-1` gets monitor 1's mode, and an unused output with the same name on the other card is also forced on (with nothing plugged in, it does no harm).
- Use a card the 15 kHz kernel supports with low dotclocks (AMD/ATI, `radeon` or `amdgpu`). On a card without them (Intel, NVIDIA) the monitor boots in the super resolution, and GroovyMAME's per-game modes may not reach it.
- Programs in KMS (RetroArch, the frontends) only see monitor 1: the others are turned off while they run, as on one card.

Reports from anyone testing a converter or a second card are welcome in the [issues](https://github.com/juniorterin/fliperOS/issues).

## Step by step

1. **Plug the monitors in.** Monitor 1 is the one the boot menu and the output test found. Plug the others into free analog outputs (VGA, or DVI-I with a passive adapter), on the same card or on a second card. Turn them all on.
2. **Open the Setup**: Setup > Video Setup > **Multiple Monitors**. The top shows monitor 1, monitors 2 and 3 (off) and the game screen order.
3. **Monitor 2**: choose its output from the list (analog outputs of monitor 1's card first; digital outputs and other cards are marked experimental). The Setup asks if a monitor of the same type as monitor 1 is plugged in there. The first time it also prepares the GroovyMAME games with 2 or 3 screens (about a minute).
4. **Monitor 3**, if you have one: same thing.
5. **Leave Video Setup**: the Setup writes the kernel line (each extra monitor with its forced 15 kHz mode) and the Xorg configuration, and offers to **reboot**. The new monitors only light up after that.
6. **Identify Monitors**: each one turns off for 3 seconds, in the game screen order. If the order is wrong (Darius' left screen on the right), fix it in **Game Screen Order**: left to right for Darius and F355 Challenge, top to bottom for Punch-Out!!.
7. **Play.** Open a game with several screens from any frontend or the Games menu: GroovyMAME and Flycast send each screen to its monitor. Single-screen games, RetroArch and the frontends stay on monitor 1.
8. **Multi-Screen Games: Off** puts every game back on monitor 1 without removing the monitors; **Monitor 2/3: Off** removes them (another reboot).

## Setting it up

Setup > Video Setup > **Multiple Monitors**:

| Item | What it does |
| --- | --- |
| **Monitor 2**, **Monitor 3** | Picks the output of each extra monitor. The list shows the free outputs of monitor 1's card, the analog ones first and the digital ones marked as experimental; *Off* removes the monitor. Before saving, the Setup asks if a monitor of the same type is plugged in there. |
| **Multi-Screen Games** | *On* (default): games with 2 or 3 screens use one monitor per screen. *Off*: every game opens on monitor 1, and the extra monitors stay on but unused. |
| **Game Screen Order** | Which output shows each screen of a game: from **left to right** (Darius, F355 Challenge) or from **top to bottom** (Punch-Out!!). |
| **Identify Monitors** | Turns each monitor off for 3 seconds, in the game screen order, so you know which is which. |

New monitors only turn on **after a reboot**: the Setup offers it when you leave Video Setup. FliperOS never turns on an output that didn't get its 15 kHz mode at boot, since the kernel would send 31 kHz to the tube.

## Which emulators use it

| Emulator | Games | Monitors |
| --- | --- | --- |
| **GroovyMAME** | Every MAME system with 2 or more screens (Darius, Darius II, The Ninja Warriors, Punch-Out!!, Super Punch-Out!!, Vs. Tennis...) | 2 or 3. With 2 monitors, a 3-screen game opens on the first 2 |
| **Flycast** | NAOMI multi-board games: Ferrari F355 Challenge (deluxe, twin, twin 2), Airline Pilots, Sega Strike Fighter | 3 (left, center, right), all analog |

The other emulators (RetroArch, PCSX2, Dolphin, Supermodel, Model 2...) and the frontends stay on monitor 1. It works from any launcher: the frontends, LXDE's **Games** menu, GroovyMAME's own game list and the terminal all go through the same commands.

## How it works

**Boot.** Each extra monitor gets the boot mode of monitor 1, forced on, in the kernel line (`video=DVI-I-1:640x480iSe`; with an EDID boot, the preset's mode; on a digital output, the preset's super resolution). Rotation (Monitor Orientation) applies to all of them. The `fliperos.conf` keeps the outputs in the game screen order (`screens=DVI-I-1,VGA-1,DVI-I-2`) and the multi-screen switch (`multiscreen=off` when off).

**X.** Each output of monitor 1's card has its own `Monitor` section in `/etc/X11/xorg.conf.d/10-fliperos.conf`, side by side in the game screen order, with monitor 1 as the primary screen: single-screen programs open there. Outputs of a second card come in as a GPU screen (see above).

**KMS.** RetroArch, Attract-Mode, EmulationStation and Pegasus open on the first connected output, which could be an extra monitor. So `fliperos-kms-run` turns the extra ones off (`fliperos-setup --outputs main`), and every X server (`fliperos-x11-run`, the desktop) turns them back on (`--outputs all`).

**GroovyMAME.** `fliperos-mame-screens` reads GroovyMAME's own `-listxml` and writes one `.ini` with `numscreens` per system with 2 or more screens in `/etc/fliperos/mame/screens` (limited to the number of monitors). This takes about a minute the first time and only runs again when the GroovyMAME binary or the number of monitors changes. The `groovymame` command adds that folder to the `-inipath` after the main one, so a user `.ini` in the main folder wins, and sends each window to its output (`-screen0 screen1`...). GroovyMAME's Switchres finds `screenN` in XRandR order and SDL counts the primary screen first; for both to agree the command makes the first output primary, and on the desktop restores the previous one when GroovyMAME closes. Switchres sets the mode of each game on every monitor.

**Flycast.** Flycast runs each NAOMI board of these games as its own process, with its own window (`network:MultiboardSlaves=2`): the main board where `window:left` says and the others one window width to each side. For the F355 Challenge, Airline Pilots and Sega Strike Fighter sets (`f355`, `f355twin`, `f355twinp`, `f355twn2`, `alpilot`, `alpilotj`, `sstrkfgt`, `sstrkfgta`), with 3 monitors and the switch on, `fliperos-x11-run` puts `fliperos-multiscreen` in front of Flycast. Inside the X server it gives the three outputs the mode Switchres made for monitor 1, side by side with no gap, and places the main board on the middle one; in full screen SDL puts each window on the monitor it falls on. The other boards are new Flycast processes that only read `~/.config/flycast/emu.cfg`, so full screen and the stretch are saved there. The board BIOS (`f355dlx`, `airlbios`, `naomi`...) must be in a Flycast content folder, next to the game.

## Problems

- **The Setup offers no output for monitor 2**: no other output is free on any card. A DVI-D connector is not analog (see above).
- **An extra monitor stays black**: check that you rebooted after choosing it, and use **Identify Monitors**. On a digital output, try another active converter. On a second card, `xrandr --listproviders` (in a terminal on the desktop) must show both cards, and `xrandr` must list its outputs (`VGA-1-1`...). The kernel line must have its `video=` (Setup > Debug mode shows `/proc/cmdline`).
- **The screens are swapped**: change **Game Screen Order**.
- **A game opens on one monitor only**: check that **Multi-Screen Games** is *On*. For GroovyMAME, `/etc/fliperos/mame/screens/<game>.ini` must exist (the Setup makes them when you add a monitor; `groovymame` remakes them otherwise). For Flycast, it needs 3 monitors.
- **Logs**: `/opt/fliperos/logs/groovymame.log` and `/opt/fliperos/logs/flycast.log` (the `fliperos-multiscreen` lines show the layout used).

See also [Emulators](Emulators.md) and [Installed system](Installed-system.md).
