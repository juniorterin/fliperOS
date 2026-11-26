One folder for the cheats, `~/cheats`, with a subfolder for each emulator and RetroArch core that can read them. Put a game's cheat file in its emulator's folder and the emulator finds it when the game starts: no menu to open, no path to set.

| Folder | What goes in it | How it is switched on |
| --- | --- | --- |
| `mame` | GroovyMAME: `cheat.7z` (the MAME cheat pack, every game in one file) and/or `<set>.xml`, one game (`sf2.xml`) | Tab menu > Cheat, in the game |
| `hbmame` | hbgroovymame (HBMAME): the same files | Tab menu > Cheat, in the game |
| `retroarch/<core>` | `<game>.cht`, named like the game file without its extension (`Sonic.md` takes `Sonic.cht`). One folder for each core that has cheats, named like the core (`Snes9x`, `FinalBurn Neo`, `PCSX-ReARMed`…) | The cheats the file marks as enabled are applied when the game opens |
| `ps2` | PCSX2: `<SERIAL>_<CRC>.pnach` or `<CRC>.pnach`, one per game (`SLUS-20946_AD2A0A4A.pnach`) | Cheats are on; the game's file is applied when it starts |
| `namco2x6` | PCSX2x6 (Namco System 246/256): `<CRC>.pnach` | The same |
| `ps1` | DuckStation: `<SERIAL>.cht` or `<SERIAL>_<HASH>.cht` (`SLUS-00594.cht`) | Esc > Cheats, in the game, where each cheat is turned on |
| `flycast` | Flycast, Dreamcast, Naomi, Naomi 2 and Atomiswave: one `.cht` per game, named like the game file with `.cht` added (`crzytaxi.zip.cht`, `Sonic Adventure.gdi.cht`); a `.txt` works too | The cheats the file marks `enable` are applied when the game starts |
| `dolphin` | Dolphin, GameCube and Wii: `<GAMEID>.ini`, one per game (`GALE01.ini`), with the codes in `[ActionReplay]` and `[Gecko]` | Cheats are on; the codes listed in `[ActionReplay_Enabled]` and `[Gecko_Enabled]` are applied when the game starts |

Each folder has an `_info.txt` with the same lines.

## Who reads cheats and who doesn't

Only the emulators that can read cheats have a folder. The other ones are left out on purpose, because there is nothing to read:

- **Keisho** (Sega Model 2 and 3), **Odin** (Hikaru, Gaelco 3D), **xemu** (Chihiro), **Hypseus** (laserdiscs) and **OpenBOR** have no cheat system.
- In RetroArch, a core only gets a folder if its information file says `cheats = "true"`. MAME 2010, the Flycast core and the other cores that say `false` (or say nothing) have none. A core you add later from the Online Updater gets its folder at the next login, if it has cheats.

RetroArch also keeps its own cheat database here: **Online Updater > Update Cheats** downloads the libretro database into `~/cheats/retroarch` (as folders named after each system), and **Quick Menu > Cheats** loads from there. A cheat file you save from that menu for the game goes to `~/cheats/retroarch/<core>/<game>.cht`, the same place this page describes.

With RetroAchievements in hardcore mode, Flycast and DuckStation refuse to apply cheats on purpose ([RetroAchievements](RetroAchievements.md)).

## Where the old folders went

The paths each emulator used before still work: `~/.mame/cheat`, `~/.hbmame/cheat` and Dolphin's `GameSettings` (in `~/.local/share/dolphin-emu`) are now links to `~/cheats/mame`, `~/cheats/hbmame` and `~/cheats/dolphin`, with what they had inside. The folder can also be on another disk (**Setup > Games > Folders**, [External storage](External-storage.md)) and is a network share, `\\fliperos\cheats`, like the others.

Dolphin keeps the cheats of a game in the same file as the settings you change for it in its *Properties*, so `~/cheats/dolphin` shows both.

## How it works

- `config/fliperos-roms` makes the folders at every login: the fixed ones, one per emulator, and one per RetroArch core whose `.info` in `/opt/fliperos/retroarch/info` has `cheats = "true"` (the folder takes the core's `corename`, which is the name RetroArch looks for).
- RetroArch: `config/retroarch.cfg` has `cheat_database_path` pointing at `~/cheats/retroarch` and `apply_cheats_after_load`.
- MAME and HBMAME: `cheatpath` in `config/mame.ini` and in the hbgroovymame `paths.ini`, and `cheat 1` in `mame.ini`; an older `mame.ini` with `cheat 0` is changed by the update.
- Flycast, PCSX2, PCSX2x6, DuckStation and Dolphin are set by `config/fliperos-x11-run` each time they open: Flycast's `Dreamcast.CheatPath` in `emu.cfg` (only if you have not chosen one), `Folders Cheats` and `EmuCore EnableCheats` in the `PCSX2.ini` of PCSX2 and PCSX2x6, `Folders Cheats` in DuckStation's `settings.ini` and `Core EnableCheats` in Dolphin's `Dolphin.ini`.
- DuckStation keeps which cheats are on in the settings of each game, so they are turned on from its menu, not from the folder.

See also: [ROMs, BIOS and artwork](ROMs.md), [RetroArch](RetroArch.md), [GroovyMAME](GroovyMAME.md), [Flycast](Flycast.md), [PlayStation 2 and Namco 246/256](Namco-246-256.md).
