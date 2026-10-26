# Screenshots

Real FliperOS captures only. `src/lib/site.ts` says where each one shows:
`HERO_SHOTS` (the carousel of the home), `HOME_GALLERY` (the gallery of the
home, one group per page), `PAGE_SHOTS` ("All screens" at the end of each
detail page) and the `rows` of each page in `src/i18n`. Each id looks for one
of these files (`.avif`, `.webp`, `.gif`, `.png` or `.jpg`, first match wins)
and is left out until it exists. Titles and captions live in `shots` in
`src/i18n`. Rebuild the site after adding images.

`anim/` holds animated WebPs cut from the scenes recorded for the presentation
video (`tools/video`, `.shots/video/clips`): native 320x240, 12–15 fps, lossy
quality 55–70, a few seconds each; the page scales them up without smoothing.
An animated GIF with the same name works too. Example:

```sh
ffmpeg -ss 87 -t 11 -i .shots/video/clips/s5_frontend.mkv -an -vf fps=12 \
  -c:v libwebp_anim -lossless 0 -quality 55 -loop 0 anim/frontend-grid.webp
```

`frontend/` holds the FliperOS frontend in its three views, each with what
opens in it: 320x240 captures of `fliperos-frontend` (the `--shot` rig),
scaled 3x nearest-neighbour to 960x720 and saved as lossless WebP.

`gui/` holds every screen of the graphical interface: the `-crt` 960x720 PNGs
that `sh tools/gui-shots.sh` writes to `.shots/gui` (how the 640x240 frame shows
on a 4:3 tube), named without the number and converted to lossless WebP. When
the interface changes, run it again and convert them all.

`desktop.webp` is the LXDE desktop with the Dracula theme.

`web/` holds the web panel, one capture per language (`-en`, `-pt`).

`multi/` holds the multi-monitor examples: MAME snaps of Darius and Punch-Out!!
cut into one image per screen (4x nearest-neighbour, lossless WebP).

Captures must be 4:3: the frame shows the whole image without cropping it.
