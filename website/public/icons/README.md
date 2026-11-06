# Icons

The official icon of each program, taken from its own repository or website.
The PNGs are scaled down to 128 px. Programs with no icon of their own
(Supermodel, Hypseus Singe) keep a FliperOS monogram on the site.

| File | Source |
| --- | --- |
| `groovymame.png` | GroovyMAME / MAME, `scripts/resources/windows/mame/mame.ico` (256 px frame) |
| `retroarch.svg` | RetroArch, `media/ico_src/icon.svg` |
| `flycast.png` | Flycast, `shell/linux/flycast.png` |
| `pcsx2.png` | PCSX2, `bin/resources/icons/AppIconLarge.png` |
| `pcsx2x6.png` | PCSX2x6, `PCSX2x6.png` (512 px) inside its AppImage (icon by Berion, credited in its README) |
| `dolphin.svg` | Dolphin, `Data/dolphin-emu.svg` |
| `model2.png` | SM2-Emu, `data/icons/sm2-emu-256.png` |
| `openbor.png` | OpenBOR, `engine/resources/OpenBOR_Icon_128x128.png` |
| `attract-mode.png` | Attract-Mode Plus, `util/linux/attract-mode-plus.png` |
| `es-de.svg` | ES-DE, `es-app/assets/org.es_de.frontend.svg` |
| `pegasus.png` | Pegasus Frontend, `assets/icon.png` |
| `fightcade.png` | Fightcade, `fightcade.com/favicon.ico` (128 px frame) |
| `duckstation.png` | DuckStation, `data/resources/images/duck.png` |
| `limine.png` | Limine, `logo.png` of its repository |
| `kof-final-attack.png` | The King of Fighters: Final Attack (United By Games, Bigruss91), the header image of its [itch.io page](https://united-by-games.itch.io/the-king-of-fighters-final-attack), cropped to the logo and scaled to 480 px |
| `hotr.png`, `pixelcade.png` | The Setup's copies (`fliperos-setup/gui/icons`, sources in its README) |
| `ubuntu.svg`, `linux.svg`, `obs.svg`, `nvidia.svg` | [Simple Icons](https://simpleicons.org) (`ubuntu`, `linux`, `obsstudio`, `nvidia`), filled with the brand colour (white for Tux and OBS, on the dark site) |
| `amd.svg` | Simple Icons `amd`, cut down to the arrow, in white |
| `intel.svg` | Simple Icons `intel` (the wordmark is the whole logo), cropped, in Intel's energy blue |

`pixel.svg` is not a logo: it is the sprite of FliperOS's own 16x16 pixel
icons used by the technical highlights bar (`src/sections/BadgeBar.tsx`),
the Setup's icons plus the ones drawn for the bar. `tools/web-icons.py`
writes it; draw new ones there (`SITE_ICONS`), never in this file.
