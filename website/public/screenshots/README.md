# Screenshots

Real FliperOS captures only. They turn one at a time in the CRT frame of the
hero, in this order; each one looks for one of these files
(`.avif`, `.webp`, `.png` or `.jpg`, first match wins) and is left out until it
exists. Captions live in `hero.slides` in `src/i18n`. Rebuild the site after
adding images.

| File | Where it shows |
| --- | --- |
| `hero.webp` | Main menu (the first screen of the carousel) |
| `install.webp` | Installer (the ISO boots straight into it, in text): choosing the HD/SSD |
| `setup.webp` | FliperOS Setup carousel |
| `video.webp` | Video Setup carousel |
| `buttons.webp` | Button mapping |
| `guncon.webp` | GunCon 2 calibration target |
| `filter.webp` | ROM filter board |
| `downloader.webp` | MAME torrent screen of the Downloader |
| `desktop.webp` | LXDE desktop with the Dracula theme |

The graphical interface ones come from `sh tools/gui-shots.sh` (the `-crt`
960x720 PNGs in `.shots/gui`), converted to lossless WebP:

| File | Shot |
| --- | --- |
| `hero.webp` | `01-main` |
| `setup.webp` | `05-setup-games` |
| `video.webp` | `06-video` |
| `buttons.webp` | `09-buttons-capture` |
| `guncon.webp` | `13-guncon-target1` |
| `filter.webp` | `20-filter` |
| `downloader.webp` | `18-downloader-torrent` |

`multi/` holds the multi-monitor examples: MAME snaps of Darius and Punch-Out!!
cut into one image per screen (4x nearest-neighbour, lossless WebP).

4:3 captures work best (the frame crops to fill). Prefer WebP or AVIF around
1280 px wide; the site serves resized AVIF/WebP versions on its own.
