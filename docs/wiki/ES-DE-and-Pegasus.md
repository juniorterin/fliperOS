**EmulationStation (ES-DE)** and **Pegasus** are optional frontends. They aren't in the image: the first time you pick one in **Setup > Games > Frontend**, the cabinet builds it, with FliperOS's patches and a theme made for 240 lines.

## Installing

1. Pick ES-DE (EmulationStation) or Pegasus in **Setup > Games > Frontend**.
2. The Setup says it will be built on this machine and asks. It needs the internet and about 4 GB free.
3. It installs the build tools, downloads the official source at the pinned version, applies FliperOS's patches, compiles, installs the package and removes the build tools it added.

Choosing the frontend again rebuilds it. The log is `/var/log/<package>-build.log`.

**ES-DE needs OpenGL 3.3** (or OpenGL ES 3.0). A card with less, like a first-generation Intel HD (OpenGL 2.1), can't open it: the Frontend screen marks it with a red X and the reason, and asks before choosing it. See [Video cards](Video-cards-Intel.md#limits-of-the-intel-hd).

## The 240p themes

On a 15 kHz monitor the frontends run at 320x240, and each one's default theme is drawn for 720 lines or more: the text ends up 4 to 8 pixels tall. So both get a **FliperOS 240p** theme, in Dracula colours: the system at the top, the game list in a 12-pixel font, the game's picture with year, publisher and description.

| Frontend | Theme |
| --- | --- |
| **ES-DE** | The systems as a list of names, the game's video (if any) in place of the picture, and only the buttons that fit in 320 pixels in the footer. No menu background blur, no new-version notice |
| **Pegasus** | Left and right switch systems, L2 and R2 skip ten games |

The Setup writes these settings once: what you change later in the frontend itself stays.

In a wide-pixel mode (640x240 on a 4:3 tube), ES-DE draws at 320x240 and stretches it twice across, so text and pictures keep their shape on the tube, as the emulators do.

## ES-DE

- **Systems:** the Setup writes every games folder to `~/ES-DE/custom_systems/es_systems.xml` (folder, extensions, command, theme). Pick ES-DE again in **Setup > Games > Frontend** whenever a folder gets its first games.
- **New games** in a folder that is already a system show the next time ES-DE opens, or at once with **Main menu > Utilities > Rescan ROM directory**.
- **Names:** in the arcade systems (`mame`, `model2`, `model3`, the RetroArch MAME cores) ES-DE shows each MAME set's full name from its own list. Everything else shows the file name until it is scraped: **Setup > Games > Scraper** writes names, descriptions and art to `~/ES-DE/gamelists/<system>/gamelist.xml`. ES-DE's own scraper (**Main menu > Scraper**) works too, and saves to the same places.
- **Art:** ES-DE reads it from `~/media/.es-de/<system>/<type>`, where each type is a link to the right folder in `~/media`.

| `~/media` folder | ES-DE |
| --- | --- |
| `snap` | screenshot |
| `preview` | video |
| `logo` | marquee |
| `box` | cover |

### A system by hand

Each system is a `<system>` block:

```xml
<system>
  <name>model3</name>
  <fullname>Model 3</fullname>
  <path>/home/fliperos/roms/model3</path>
  <extension>.zip .ZIP</extension>
  <command label="Model 3">/opt/fliperos/bin/fliperos-x11-run fliperos-model3 %ROM%</command>
  <platform>arcade</platform>
  <theme>model3</theme>
</system>
```

- `%ROM%` is the game's path (ES-DE adds the quotes); `%BASENAME%` is the name without the extension (`fliperos-x11-run groovymame %BASENAME%`).
- `<platform>` is what the scraper searches as (Model 2, Model 3 and the MAME cores are MAME sets, so `arcade`).
- `<theme>` is the system's folder in the themes, which gives its logo and background.
- A system can have more than one `<command>`, with different labels: ES-DE lets you pick one per game (**Edit this game's metadata > Alternative emulator**).

**Setup > Games > Frontend rewrites the whole `es_systems.xml`** every time ES-DE is picked, so a system added by hand disappears. Keep a copy of your blocks and paste them back afterwards.

## Pegasus

- **Folders:** the list is `~/.config/pegasus-frontend/game_dirs.txt`, which the Setup rewrites with the folders it knows; add your own folders again after using it.
- **A folder by hand:** a `metadata.pegasus.txt` in the game folder. One that already exists is never touched.

```text
collection: My Emulator
extensions: bin, zip
launch: /opt/fliperos/bin/fliperos-x11-run myemu-run "{file.path}"
```

Pegasus has no event hooks, so a Pixelcade or ZeDMD marquee only shows the game you open.

## How it works

- `config/fliperos-frontend-build`, installed as `/opt/fliperos/bin/fliperos-emulationstation` and `fliperos-pegasus` (the name picks the recipe), builds with the recipe in `packaging/packages/<package>.sh`, the same the CI uses, kept in `/usr/local/share/fliperos/packaging`. `build-deb.sh` applies ES-DE's 2x horizontal stretch (`packaging/patches/emulationstation`) and Pegasus's KMS patch. A recipe with `PKG_ON_DEMAND=1` is left out of the image's package list. The build uses `/var/tmp`.
- `fliperos-emulationstation unsupported` prints why a card can't run ES-DE.
- The themes: ES-DE's is `config/esde-theme-fliperos`, installed in `/usr/share/es-de/themes/fliperos-240p-es-de` (`Theme` in `es_settings.xml`); Pegasus's is `config/pegasus-theme-fliperos`, in `/usr/share/pegasus-frontend/themes`. The stretch is `ESDE_STRETCH_X`, set by `fliperos-kms-run` from the mode.
- The `<theme>` the Setup gives: `model2`, `model3`, `mame` for the RetroArch MAME cores, `fbneo`, and `arcade` for the GroovyMAME folder.
- The Pixelcade and ZeDMD events of ES-DE are its custom event scripts in `~/ES-DE/scripts` ([Pixelcade](Pixelcade.md)).

See also: [Frontends](Frontends.md), [Adding games](Adding-games.md).
