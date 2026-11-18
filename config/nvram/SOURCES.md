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
- `retroarch/mame2010/<set>.nv` — the RetroArch core MAME 2010 (MAME 0.139),
  which keeps everything a game remembers in one `<set>.nv` file instead of
  the folder of the current MAME. Each file here is the one in `mame/<set>/`,
  byte for byte, and only for the games where that is true in the 0.139
  source (libretro/mame2010-libretro): a game with one AT28C16 chip
  (`mame/<set>/at28c16`, 2080 bytes: tekken3, tektagt, soulclbr, souledge,
  stargld2, sfex, sfex2, rvschool, rvschoola, kikaioh, doapp), the CPS2 93C46
  EEPROM (`sfa3`, 128 bytes) and the Wolf-unit CMOS (`umk3`, 49152 bytes). Left
  out: `mk2` (16384 bytes here, a 32768-byte file in 0.139 with its own CMOS
  pages: the layout is not proven the same), the Naomi games (several files
  here, one in 0.139) and `sfex2u`/`mvsc2u` (not sets in 0.139). The
  clones of a set (`sfa3u`, `tekken3a`…) have no file, as in the current MAME.
  Not run in the core: the bytes were compared against its source, not loaded
  in a game.
