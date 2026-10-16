# Screenshots

Real FliperOS captures only. They turn one at a time in the CRT frame of the
hero, in the order of `SCREENSHOT_IDS` in `src/lib/site.ts`; each one looks for
one of these files (`.avif`, `.webp`, `.png` or `.jpg`, first match wins) and is
left out until it exists. Captions live in `hero.slides` in `src/i18n`.
Rebuild the site after adding images.

`gui/` holds every screen of the graphical interface: the `-crt` 960x720 PNGs
that `sh tools/gui-shots.sh` writes to `.shots/gui` (how the 640x240 frame shows
on a 4:3 tube), named without the number and converted to lossless WebP. When
the interface changes, run it again and convert them all.

`desktop.webp` is the LXDE desktop with the Dracula theme.

`multi/` holds the multi-monitor examples: MAME snaps of Darius and Punch-Out!!
cut into one image per screen (4x nearest-neighbour, lossless WebP).

Captures must be 4:3: the frame shows the whole image without cropping it.
