Sega's 3D arcade boards of the 1990s: **Model 2** (Daytona USA, Virtua Fighter 2, The House of the Dead, Sega Rally) and **Model 3** (Scud Race, Virtua Fighter 3, Daytona USA 2), both in [Keisho](https://github.com/Keisho-Emu/Keisho). It was called SM2-Emu until November 2026, and Model 3 used to be [Supermodel](https://github.com/trzy/Supermodel).

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/docs/img/wiki/game-model2.webp" width="480" alt="Fighting Vipers in Keisho">

| Board | Emulator | Folder | Sets | Memory and save states |
| --- | --- | --- | --- | --- |
| Model 2 (2, 2A, 2B, 2C) | Keisho | `~/roms/model2` | MAME sets | `~/nvram/model2` |
| Model 3 | Keisho | `~/roms/model3` | MAME sets | `~/nvram/model3` |

Both open in their own Xorg at **640x240 at 57.524 Hz** on a 15 kHz tube (the boards' refresh), stretched to fill it, or 496x384 interlaced with **Interlaced hacks** ([Interlaced, colour and scanlines](Picture-filters.md)). Both have link play between cabinets: Daytona USA, Scud Race and more ([Linked cabinets](Linked-cabinets.md)).

## Opening a game

Keisho **comes in the image**, as a FliperOS package that the updates keep current. **Build the newest** in **Setup > Games > Emulators & Games > Keisho** builds the project's latest code on the cabinet, with FliperOS's patch.

- From a frontend: the **Model 2** and **Model 3** screens open the game straight away.
- From the desktop's **Games > Model 2** or **Games > Model 3**: a terminal lists the `.zip` files of that folder by their names; Enter opens one, Esc exits. A set that can't be loaded stays on that screen, with the missing chip named.

**Sets:** chips are matched by CRC32, so a zip has to be a MAME set; one made only for the old Model 2 Emulator can miss a chip. Daytona USA, Desert Tank and Virtua Cop also need MAME's I/O boards (`model1io.zip`, `model1io2.zip`) next to them, which the [ROM Cleaner](ROM-Cleaner.md) brings. A clone finds its parent's chips in the same folder.

**Controls:** a gamepad is read by button position, with the keyboard live beside it (5 and 6 insert coins, 1 and 2 start, the arrows and Z X C V are player 1). The panel's [button mapping](Button-mapping.md) is the same for Model 2 and Model 3. **F9** quits; **F10** is the emulator's own settings menu, readable at 640x240. **coin + button 1** opens it too.

**Video: Vulkan or OpenGL.** Like Flycast and Dolphin, Keisho follows the video card's driver: **Vulkan** on `amdgpu`, **OpenGL** on the others (`radeon` has no Vulkan). The first launch writes `graphics_backend` to `keisho.ini`, and switching the driver in **Setup > Video Setup** switches it again. A choice made in F10 stays. If the card has no Vulkan, Keisho falls back to OpenGL by itself. It needs OpenGL 4.3 or Vulkan 1.3.

**Game outputs:** it publishes the lamps, the recoil, ammunition and life of the gun games (Model 2 and Model 3), the round wins of the Model 2 fighting games (for the [versus score](Versus-score.md)) and the credits, on TCP port 8000 ([DIY hardware](DIY-hardware.md#model-2-game-outputs)).

**Speed:** Model 1 and 2 run on one CPU core; FliperOS's speed work on the geometry coprocessors is part of the emulator since 0.9.41 (on the cabinet's i3-540: 0.93× to 2.34× on The House of the Dead, 0.71× to 1.65× on Last Bronx, 0.85× to 2.84× on Fighting Vipers). Model 3's PowerPC runs through a JIT, and each frame is drawn on a second thread. Model 3 in Keisho has not been timed on the cabinet's i3-540 yet (Supermodel needed its PowerPC slowed to 75 MHz there).

## Coming from Supermodel

The update to Keisho removes the Supermodel package once Keisho is installed. The `<set>.nv` files in `~/nvram/model3` stay: Keisho reads Supermodel's NVRAM format, so high scores, settings and link roles carry over. The frontend screen **Supermodel** is now **Model 3**: its play counts move with it, and favourites stay. A frontend that still has the old `supermodel` command opens the game in Keisho.

## How it works

- The package `fliperos-keisho` (`packaging/packages/fliperos-keisho.sh`) builds a fixed commit with Vulkan and OpenGL and the patches in `packaging/patches/keisho`: the light gun keeps the last position that saw the screen over a missed beam. It installs `/usr/local/bin/keisho` and `/usr/local/share/keisho/games.xml`.
- `fliperos-model2` and `fliperos-model3` (the same script, the name picks the system) open a game for the frontends with `exec`, so the wrapper waits for it. They pass both ROM folders; Model 3 gets `--nvram ~/nvram/model3`, Model 2 uses Keisho's own `nvram_dir`, which `fliperos-roms` links to `~/nvram/model2`.
- `fliperos-x11-run` writes to `~/.config/keisho/keisho.ini` on each launch: `aspect_mode = stretch` when the mode is wider than 4:3, `vsync = true` and `graphics_backend` the first time, the outputs, the light gun and the GunCon 2 buttons. `lib/emulators.sh` switches `graphics_backend` when the card's driver changes.
- `fliperos-sm2emu` is the desktop's game list (the quick check of a set uses a throwaway NVRAM) and moves the SM2-Emu folders (`~/.config/sm2-emu`, `~/.local/share/sm2-emu`) to Keisho's. The log is `/opt/fliperos/logs/fliperos-model2.log` or `fliperos-model3.log`.

See also: [Emulators](Emulators.md), [Linked cabinets](Linked-cabinets.md).
