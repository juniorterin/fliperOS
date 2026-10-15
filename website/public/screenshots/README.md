# Screenshots

Real FliperOS captures only. They turn one at a time in the CRT frame of the
hero, in this order; each one looks for one of these files
(`.avif`, `.webp`, `.png` or `.jpg`, first match wins) and is left out until it
exists. Captions live in `hero.slides` in `src/i18n`. Rebuild the site after
adding images.

| File | Where it shows |
| --- | --- |
| `hero.webp` | Main menu (the first screen of the carousel) |
| `setup.webp` | FliperOS Setup menu |
| `install.webp` | Installer (the ISO boots straight into it): choosing the HD/SSD |
| `video.webp` | Video Setup: monitor, output test, geometry |
| `desktop.webp` | LXDE desktop with the Dracula theme |

`multi/` holds the multi-monitor examples: MAME snaps of Darius and Punch-Out!!
cut into one image per screen (4x nearest-neighbour, lossless WebP).

4:3 captures work best (the frame crops to fill). Prefer WebP or AVIF around
1280 px wide; the site serves resized AVIF/WebP versions on its own.
