# Arcade memory that comes with FliperOS

What each emulator's games remember without power, with content the game
normally unlocks over time or with codes already unlocked. The image installs
this folder to `/usr/share/fliperos/nvram`, and `config/fliperos-roms` copies
each game to `~/nvram/<emulator>` once, only when that game has no memory of
its own yet.

- `mame/<set>/` — GroovyMAME. From the archive.org item
  [nvram](https://archive.org/details/nvram) ("NVRam for MAME", tested by its
  author on MAME 0.284), without its CPS3 and simpbowl zips (flash images, not
  unlocks). `mk2/nvram` is `mk2.nv` from
  [mk2_20230702](https://archive.org/details/mk2_20230702). The author was not
  sure that `sfa3` and `soulclbr` unlock anything.
- `flycast/` — Flycast, Naomi and Atomiswave. The memory the Fightcade 2 Linux
  package brings in `emulator/flycast/data` (version 2.1.45), without the
  `.net` files of online matches. `cspike.zip.eeprom` and `ftspeed.zip.nvmem`
  are from the
  [Flycast wiki](https://github.com/TheArcadeStriker/flycast-wiki/wiki/Savedata-and-Extras-for-NAOMI-Atomiswave-games),
  which Fightcade does not cover.
