A [Pixelcade](https://pixelcade.org) LED or LCD marquee shows the game you have selected in the frontend and the game you open, with its high scores, achievements and the versus score. What it shows is on [LED displays](LED-displays.md); this page is about installing and running it.

## Installing it

**Setup > Games > Extras > Pixelcade.** Pixelcade's software (`pixelweb`) is closed source, so it isn't in the image: the Setup downloads it from Pixelcade's GitHub ([alinke/pixelcade-linux-builds](https://github.com/alinke/pixelcade-linux-builds)), with the artwork (a few hundred MB), into `~/pixelcade`.

It also downloads **hi2txt**, which reads the high scores, and installs Java, which hi2txt needs.

Choosing **Extras > Pixelcade** again, once it is installed:

- **Update** the program and the artwork;
- **Paid art pack**: type the license code you got from Pixelcade and the Setup downloads the pack. It is also in the web panel's **Library > Install**.

`~/pixelcade` is the folder Pixelcade's own guides use, so the same can be done by hand: `cd ~/pixelcade && ./pixelweb -install-artpack <code>`.

Pixelcade's own settings page is at `http://<cabinet IP>:8080`.

## In each frontend

| Frontend | What the marquee follows |
| --- | --- |
| FliperOS frontend | The game and the system you pick, the idle animation |
| ES-DE | The game and the system you pick, its screensaver |
| Attract-Mode Plus | The game you pick, its screensaver |
| Pegasus | Only the game you open (Pegasus has no event hooks) |

When a game closes, the marquee shows its marquee again, the way the frontend selection does.

**Arcade folders** (`mame`, `naomi`, `naomi2`, `atomiswave`, `model2`, `model3`, the MAME and FBNeo cores) use Pixelcade's `mame` artwork. RetroArch cores go by their system (`snes`, `genesis`, `psx`…), other folders by their name.

## Pixelcade LCD over USB

The LCD marquee (firmware 6.3 or newer) appears as a network card over USB. FliperOS sets it up as Pixelcade's installer does: it gives the card its address and tells `pixelweb` the LCD is there. Not yet tested with an LCD marquee.

## DOFLinx (effects during the game)

[DOFLinx](https://doflinx.github.io/docs/) shows the score and effects on the Pixelcade marquee while a game runs, for the **FBNeo** arcade games in RetroArch. It is closed source and large (about 230 MB), so it is a separate extra: **Setup > Games > Extras > DOFLinx**, after Pixelcade. Not yet tested with a marquee.

If you change `DOFLinx.ini`, a later install keeps your file and saves the new one as `DOFLinx.ini.latest`.

## Visual Pinball

A program whose name starts with `vpinball` draws the display itself, over the same serial port: when it opens, `pixelweb` and `dmdserver` let go of the port, and when it ends they take it back. FliperOS doesn't ship Visual Pinball.

## How it works

- **Service:** `fliperos-pixelcade.service` keeps `pixelweb` running as the `fliperos` user and starts it when the marquee is plugged in (`99-fliperos-pixelcade.rules`, USB IDs `1b4f:0008` for V1 and `2e8a:1050` for V2). The serial port belongs to the `dialout` group. With no marquee, `pixelweb` searches for about 30 seconds and exits; the service tries 3 times and then waits for the marquee to be plugged in. At start the marquee shows the FliperOS logo; at shutdown, "Bye".
- **Events** are the ones of Pixelcade's own EmulationStation scripts ([alinke/pixelcade-linux](https://github.com/alinke/pixelcade-linux/tree/main/batocera/scripts)), with the same calls to `pixelweb`. The game is the last argument of `fliperos-kms-run`/`fliperos-x11-run`: a file in `~/roms`, or the set name for GroovyMAME and Model 2. With no game (a frontend, an emulator's menu) nothing happens.
- **High scores:** the top three (`#1 19,130 DAA #2 ...`) come from the game's `.hi` file, the newest among `~/.mame/hiscore` (GroovyMAME's `hiscore` plugin) and the RetroArch saves folder (`/opt/fliperos/saves/retroarch`, where the MAME and FBNeo cores write theirs), read by hi2txt (pinned by hash, in `~/pixelcade/hi2txt`, with `default-jre-headless`). A game hi2txt doesn't know shows its name.
- **ES-DE** events are its custom event scripts (`~/ES-DE/scripts/game-select`, `system-select`, `screensaver-start`, `screensaver-end`, with *Custom event scripts* and *Browsing custom events* on); **Attract-Mode Plus** uses FliperOS's *Pixelcade* plugin, copied to `~/.attract/plugins` and turned on in `plugins.cfg`. The service writes these settings at every boot; with the frontend open, they wait for the next boot.
- **Idle animation:** the same as the ZeDMD's, copied to `~/pixelcade/console/fliperos-idle.gif`. Without it the marquee goes into Pixelcade's attract mode, a playlist set on its settings page.
- **System logos:** the Pixelcade only shows files, so each logo goes in a GIF in `~/pixelcade/console` (`fliperos-logo-*`, replaced at each switch).
- **LCD over USB:** USB ID `1d6b:3232`. The udev rule keeps it out of NetworkManager and starts `fliperos-pixelcade-lcd@<interface>.service`, which gives the card `169.254.100.2` (the LCD is `169.254.100.1`), sets `lcdMarquee` and `lcdUsbConnected` in `~/pixelcade/pixelcade.ini`, writes the LCD's name there and restarts the service.
- **DOFLinx:** the Linux program from [DOFLinx/CurrentExecutable](https://github.com/DOFLinx/CurrentExecutable) into `~/doflinx`, with the `DOFLinx.ini` and `colours.ini` Pixelcade publishes (FliperOS's folders) in `~/doflinx/config`, and the per-game files downloaded by `pixelweb -update-doflinx` into `~/pixelcade/DOFLinx`. It reads the running game's memory through RetroArch's Network Command Interface: the install writes `/etc/fliperos/retroarch/doflinx.cfg` (`network_cmd_enable`, port 55355), which `fliperos-kms-run` adds to RetroArch. `fliperos-doflinx.service` runs it after `pixelweb` answers.

See also: [LED displays](LED-displays.md), [ZeDMD](ZeDMD.md).
