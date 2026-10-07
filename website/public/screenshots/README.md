# Screenshots

Real FliperOS captures only. Each slot on the site looks for one of these files
(`.avif`, `.webp`, `.png` or `.jpg`, first match wins); until it exists, the site
shows a placeholder with the expected path. Rebuild the site after adding images.

| File | Where it shows |
| --- | --- |
| `hero.webp` | Hero, inside the CRT frame (4:3) |
| `setup.webp` | FliperOS Setup menu |
| `install.webp` | Installer (the ISO boots straight into it): choosing the HD/SSD |
| `video.webp` | Video Setup: monitor, output test, geometry |
| `desktop.webp` | LXDE desktop with the Dracula theme |

4:3 captures work best (the tiles crop to fill). Prefer WebP or AVIF around
1280 px wide; the site serves resized AVIF/WebP versions on its own.
