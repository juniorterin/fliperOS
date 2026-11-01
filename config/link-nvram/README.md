# One NVRAM for each cabinet number

A linked game keeps its role in its NVRAM: master or slave, and the car number (or machine ID). So each cabinet number needs its own file. This folder holds one file per cabinet number for the games that were tested.

Cabinet 1 is the **master**. Every other number is a **slave**, and the cabinet number is the car number (the Machine ID in Dirt Devils). The files hold the game's default settings for everything else, with no scores and no coin credits.

| Emulator | Game | Cabinets | Files | Install as |
| --- | --- | --- | --- | --- |
| SM2-Emu | Daytona USA | 1 to 8 | `sm2emu/daytona/cabinetN.nv` and `cabinetN.eeprom` | `daytona.nv` and `daytona.eeprom`, in the folder given to `--nvram` |
| Supermodel | Scud Race | 1 to 8 | `supermodel/scud/cabinetN.nv` | `scudau.nv`, in Supermodel's `NVRAM` folder |
| Supermodel | Daytona USA 2 | 1 to 8 | `supermodel/daytona2/cabinetN.nv` | `daytona2.nv` |
| Supermodel | Dirt Devils | 1 to 4 | `supermodel/dirtdvls/cabinetN.nv` | `dirtdvlsau.nv` |

`MANIFEST.tsv` lists every file with its role, number, SHA-256 and how it was checked.

## How to use them

Copy the file of the cabinet's number over the name in the last column before the game starts. Give each emulator instance its own NVRAM folder: two instances in one folder overwrite each other's file. For solo play use no file (delete it): the emulator makes the default one, which is a stand-alone cabinet.

The frontend's link launcher does this (see `docs/research/link-frontend-plan.md`).

## Limits

- **The file belongs to a ROM set.** Supermodel names it after the set it loads: `scud.zip` loads the `scudau` set, `dirtdvls.zip` the `dirtdvlsau` set. Another region set of the same game has another name, and its file has to be made again with `tools/link-tests/nvram-supermodel.ps1`.
- **Same game version everywhere.** All the cabinets of one link need the same ROM set.
- **Dirt Devils works in pairs only.** Four instances formed only two of the four links, so the files for 3 and 4 exist but a link of four is not known to work. Its highest Machine ID was not looked for.
- **The Supermodel files are 128 KB each.** They hold the whole battery-backed RAM of the board.

## How they were made

With `tools/link-tests/nvram-supermodel.ps1` and `nvram-sm2emu.ps1`: each file comes from the game's test menu (Link ID or Communication Mode, Car Number or Machine ID), saved by leaving through Exit. Each was then checked by starting the game with it and reading the role and the number on the screen. Scud Race and Daytona USA 2 cabinets 2 to 4 also took part in a ring of four.
