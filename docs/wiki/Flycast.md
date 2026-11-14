[Flycast](https://github.com/flyinghead/flycast) runs the Dreamcast and the Sega arcade boards built on it: Naomi, Naomi 2 and Atomiswave.

| Games | Folder | BIOS in `~/bios/dc` |
| --- | --- | --- |
| Dreamcast (`.gdi`, `.cdi`, `.chd`) | `~/roms/dreamcast` | `dc_boot.bin`, `dc_flash.bin` |
| Naomi | `~/roms/naomi` | `naomi.zip` |
| Naomi 2 | `~/roms/naomi2` | `naomi2.zip` |
| Atomiswave | `~/roms/atomiswave` | `awbios.zip` |

The arcade games are MAME sets; the [ROM Cleaner](ROM-Cleaner.md) splits a MAME romset into the three folders, and [Download BIOS](BIOS.md) brings every BIOS Flycast knows as soon as there is one game.

## Playing

- It opens in its own Xorg: **640x240** at 15 kHz, stretched to fill the tube, or interlaced with the flicker filter if **Interlaced hacks** says so ([Interlaced, colour and scanlines](Picture-filters.md)); 640x480 on other monitors.
- **Straight to the game:** no box art and "Loading..." window; the screen stays black until the game starts, as on the arcade board. A load error still shows.
- **Leaving:** **coin + Start**; **coin + button 1** opens Flycast's menu ([Frontend controls](Frontend-controls.md#game-shortcuts)).
- **Players:** player 2 (port B) has a controller from the start. A panel whose D-pad is sent as axes gets mapping files of its own.
- **Sharp pixels:** linear interpolation is off, and textures are *Force Nearest-Neighbor*.
- **Unlocked memory** for the Naomi and Atomiswave games Fightcade brings, plus Cannon Spike and Faster than Speed ([ROMs, BIOS and artwork](ROMs.md#nvram)).
- On amdgpu it runs in **Vulkan**; on radeon, OpenGL.

Flycast also has: **multi-screen games** on 3 monitors (F355 Challenge, Airline Pilots, Sega Strike Fighter; [Multiple monitors](Multiple-Monitors.md)), **link play** between cabinets (the NAOMI link games), **party** for up to 4 cabinets, and **GGPO net play** ([Linked cabinets](Linked-cabinets.md)), and [RetroAchievements](RetroAchievements.md) for the Dreamcast.

## Updating it

Flycast is a FliperOS package, updated over the network with FliperOS. **Setup > Games > Emulators & Games > Flycast > Build the newest** compiles the newest Flycast with FliperOS's patches; **Back to the FliperOS package** returns to the tested one ([Games Setup](Setup-Games.md#the-newest-version-of-a-packaged-emulator)).

## How it works

- `fliperos-x11-run flycast` passes `-config` with `rend.ScreenStretching=200` (800 on a card with super resolutions), and the content and BIOS paths (`Dreamcast.ContentPath`, `Dreamcast.BiosPath`, `FLYCAST_BIOS_PATH`).
- The patches are in `config/flycast-patches`: the black loading screen, the lockstep party, and 0006, which writes each achievement unlock to `$FLIPEROS_CHEEVOS_LOG` and adds `Notifications = no`. If a newer Flycast doesn't take a patch, the build warns and leaves it out.
- `emu.cfg` comes with `rend.LinearInterpolation = no` and `rend.TextureFiltering = 1`. Flycast saves its own default when it closes, so on an older `emu.cfg` each is changed once (`/var/lib/fliperos/flycast-texture-nearest`); after that the choice is yours.
- Flycast builds its default mapping from SDL, but doesn't understand a D-pad wired to a half axis; `fliperos-controllers` writes Dreamcast and arcade mapping files for those controllers, only if there isn't one yet ([Controls](Wheels-and-quirks.md#controllers-in-sdl)).
- Its memory lives in `~/nvram/flycast`: each Naomi or Atomiswave game's `.nvmem`/`.eeprom`, and the Dreamcast's `vmu_save_*.bin`.

See also: [Emulators](Emulators.md), [Linked cabinets](Linked-cabinets.md).
