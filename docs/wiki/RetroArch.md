[RetroArch](https://www.retroarch.com) runs the consoles, and some arcade boards, through its cores. On FliperOS each game opens in its own mode on the tube (CRT SwitchRes), with your panel's buttons already mapped.

## Cores

Seven come compiled, to work without network:

| Core | System |
| --- | --- |
| FCEUmm | NES |
| Snes9x | Super Nintendo |
| Genesis Plus GX | Mega Drive, Master System, Sega CD |
| mGBA | Game Boy Advance |
| PCSX ReARMed | PlayStation |
| MAME 2010 | Arcade, MAME 0.139: the **MAME 3D**, for the PlayStation-based arcade games (Tekken 3, Soul Calibur, Street Fighter EX, Rival Schools) |
| FinalBurn Neo | Arcade, in FBNeo's own ROM sets; it has the [versus score](Versus-score.md) |

Any other comes from RetroArch's own **Online Updater > Core Downloader**. Each core has its folder, `~/roms/retroarch/<core>`, with an `_info.txt` listing its extensions; a new core gets its folder at the next login.

A game whose core isn't installed yet (from a disc or a cartridge, for example) downloads it first, with a progress bar.

## Playing

- **Leaving a game:** **coin + Start** held for a second ([Frontend controls](Frontend-controls.md#game-shortcuts)).
- **RetroArch's menu (Quick Menu):** **coin + button 1** held for a second. A single Esc on a keyboard closes the game.
- **Controls:** the buttons of **Setup > Joysticks > Button mapping**, also the D-pad of a gamepad RetroArch has no profile for (an 8BitDo Ultimate and many others whose D-pad is a hat) ([Button mapping](Button-mapping.md)).
- **Light gun:** in every core that has one (FBNeo, PlayStation, SNES, Mega Drive, Master System, NES with Nestopia and Mesen's Zapper), the gun is set up by itself for the games that use it, and the other players stay on their pads ([Controls](Light-guns.md)).
- **Achievements:** [RetroAchievements](RetroAchievements.md).
- **Party and net play** across cabinets: [Linked cabinets](Net-play.md).

## Video

- At each game's **native width** when the card makes low dotclocks (radeon, amdgpu, an NVIDIA that passed the low resolution test), like GroovyArcade. Other cards get the 2560-wide super resolution ([KMS and X11](KMS-and-X11.md#cards-without-low-dotclocks)).
- Games taller than 240 lines follow **Setup > Video Setup > Interlaced hacks**, per core: PS1, SNES, Mega Drive and FBNeo interlaced with the filter by default, MAME 2010 at 640x240 ([Interlaced, colour and scanlines](Picture-filters.md)).
- The video driver is `glcore` (OpenGL 3.2); on a card with only OpenGL 2.x (Radeon X300 to X1950, first-generation Intel, GeForce FX/6/7) it is `gl`. On amdgpu, RetroArch also runs in **Vulkan**, still switching the CRT's mode for each game.
- No on-screen notifications: the [on-screen menu](On-screen-menu.md) shows the volume and the achievements instead.

## Updating it

FliperOS updates bring new RetroArch packages. **Setup > Games > Emulators & Games > RetroArch > Build the newest** compiles the newest RetroArch on the cabinet, with FliperOS's patches; **Back to the FliperOS package** returns to the tested one ([Games Setup](Setup-Games.md#the-newest-version-of-a-packaged-emulator)).

## How it works

- **Settings:** the system `retroarch.cfg` (`/etc/fliperos/retroarch`) is applied on top of the user's on each launch by `fliperos-kms-run` (`--appendconfig`), with the other files of that folder (achievements, the versus score's network commands, DOFLinx). It sets `crt_switch_resolution 4` (the Setup's `/etc/switchres.ini`), `video_driver glcore`, `audio_driver sdl2` straight into ALSA, input and joypad in `linuxraw` (`/dev/input/js*`), no notifications and `confirm_quit` off. `video_retroarch_super` (saved by the output test) is the super resolution width.
- **Controller profiles:** `fliperos-controllers` writes RetroArch's autoconfig for each controller from the Button mapping, D-pad included.
- **Light gun:** `config/lightgun-games.tsv` lists the gun games of each core, and the core's port devices are set for them; the gun's own joystick is remapped so it doesn't take player 1's pad.
- **Interlacing per core:** a `switchres.ini` of the core only, `~/.config/retroarch/config/<Core>/<Core>.switchres.ini`, read on top of `/etc/switchres.ini` (`config/retroarch-switchres`). MAME 2010's ships with `interlace 0`.
- **Vulkan without X** is the `khr_display` context, which FliperOS patches so it switches the CRT's mode for each game (`config/retroarch-patches`).
- **Cores and files:** cores, `.info` files and controller profiles live in `/opt/fliperos/retroarch`, owned by the `fliperos` user, so the menu saves without root; the factory `.info` files and profiles are pinned by commit (`libretro-core-info`, `retroarch-joypad-autoconfig`).
- **MAME 2010** is compiled without the `_FORTIFY_SOURCE` that Ubuntu's gcc turns on by itself (`ARCHOPTS=-U_FORTIFY_SOURCE`): MAME 0.139 writes 9 bytes into a `char[8]` when starting the H8/3002 CPU, and glibc closed RetroArch on every Namco System 12 game.

See also: [Emulators](Emulators.md), [KMS and X11](KMS-and-X11.md).
