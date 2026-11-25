A marquee display on top of the cabinet that follows what you do: the game you pick in the frontend, the game you open, its high scores, the versus score of a fight, the achievements you unlock. FliperOS works with two:

| Page | What it covers |
| --- | --- |
| [Pixelcade](Pixelcade.md) | The Pixelcade LED or LCD marquee: installing it, the paid art pack, the events it shows, DOFLinx effects during a game |
| [ZeDMD](ZeDMD.md) | The open-source LED display you build with an ESP32: installing it, what it shows, the startup animation, the firmware version and how to update it |
| [Versus score](Versus-score.md) | The match score of fighting games on the display, in GroovyMAME, RetroArch with FBNeo and Model 2 |
| [Scoreboard games](Scoreboard-games.md) | The list of games with the versus score and the high scores, and which emulator has each |

<img src="https://raw.githubusercontent.com/juniorterin/fliperOS/main/docs/img/zedmd-startup-led.gif" width="640" alt="The FliperOS startup animation drawn as the ZeDMD LEDs show it">

## What both show

Pixelcade and ZeDMD get the same events, and can be installed together:

| When | The display shows |
| --- | --- |
| A game is picked in the frontend | Its marquee or logo |
| The system changes in the FliperOS frontend | The system's written logo slides in and blinks twice |
| A game opens, from any frontend or emulator | Its high scores (or "Now Playing") scroll once, then its marquee stays |
| A fight is on | The versus score ([Versus score](Versus-score.md)) |
| An achievement is unlocked | The achievement, then the marquee again |
| The frontend is idle | The FliperOS logo animation |
| The FliperOS menu is open | The animation of the item under the cursor |
| The cabinet powers off | "Bye" |

No display at all? The web panel draws the same marquee in the browser, and makes a page of it for OBS ([Web panel: Frontend](Web-panel-Frontend.md#marquee-preview), [Web panel: Live](Web-panel-Live.md#marquee-for-obs)).

## Art for the display

The ZeDMD, the web panel's preview and the OBS page look in `~/media`, in this order:

1. `dmd/<games folder>/<rom>.png` or `.gif`: art made for a 128x32 display (`dmd/mame/sf2.gif`); a GIF plays animated;
2. the scraped `marquee`, then `logo` images ([Scraper](Scraper.md)).

Without any picture, the game's name scrolls in big letters, like an LED sign. A system's picture goes in `~/media/dmd/<system>.png`.

The Pixelcade uses its own artwork, which is licensed only for Pixelcade hardware, so FliperOS doesn't use it anywhere else.

## The FliperOS menu animations

In the FliperOS menu, the marquee follows the cursor. Each item has its own animation in the style of the logo: a synthwave sun with an animated icon and the item's name in neon chrome, with glitches.

| Item | Icon |
| --- | --- |
| FRONTEND | A joystick |
| SETUP | Two gears |
| DESKTOP | A monitor with windows and a mouse |
| SHELL | A terminal typing |
| POWER | The power symbol pulsing |

Entering an item keeps its animation through the submenus.

## How it works

- Every game goes through `fliperos-kms-run` or `fliperos-x11-run`, which call `fliperos-pixelcade launch` in the background, so a game never waits for the marquee; the same helper sends the events to the ZeDMD through `fliperos-dmd`. The frontends' own events come from the Attract-Mode Plus plugin and the ES-DE scripts that FliperOS installs.
- The system logos are characters of Arcadeflow's logo font, drawn by `fliperos-syslogo` from the font and `data_systems.txt`, which ship in the image (`config/syslogo`, installed in `/usr/local/share/fliperos/syslogo`) with the permission of Arcadeflow's author. `fliperos-syslogo export DIR` writes every logo as a PNG. Systems the font does not have (the Sega Chihiro) use a PNG from `config/syslogo/extra` instead, which the marquee and the frontend find the same way (`fliperos-syslogo find` answers `extra`).
- The menu animations are made by `tools/marquee-logo-anim.py`; the graphical Setup sends each cursor move (`fliperos-pixelcade menu ITEM`), the text Setup the item you enter.
- Achievements: `fliperos-cheevos watch` reads each unlock from the emulator's log and calls `fliperos-pixelcade achievement` ([RetroAchievements](RetroAchievements.md)).

See also: [DIY hardware](DIY-hardware.md#led-display-marquee-dmd), [Scoreboard games](Scoreboard-games.md).
