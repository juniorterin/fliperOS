# Link tests

Tools used on 2026-10-31 and 2026-11-01 to find out which arcade games link several machines and how. The notes and results are in `docs/research/linked-cabinets.md`. The user-facing summary is the wiki page *Linked cabinets*.

They are research tools, not part of the image. The PowerShell scripts drive emulators on a **Windows PC** with a screen, because the tests need a real window, keys and a mouse. Nothing here runs in the build or in the tests.

## Settings

The scripts read these environment variables, and have defaults you will probably change:

| Variable | What it is | Default |
| --- | --- | --- |
| `LINK_TESTS_OUT` | Where captures and result files go | `%TEMP%\link-tests` |
| `LINK_TESTS_ROMS` | The folder with the ROM zips | `C:\roms` |
| `MAME_HOME` | The folder with `mame.exe` (official MAME for Windows) | `C:\mame0289\mame` |
| `SM2_HOME` | The folder with the SM2-Emu Windows release unpacked in `app` | `C:\sm2-emu-win` |
| `SUPERMODEL_HOME` | The Supermodel Windows release folder | `C:\supermodel-win\app\supermodel-0.3a-20261025-git-1481545` |
| `SUPERMODEL_COPIES` | The folder with the copies `A` to `D` of the Supermodel release (each with `Config`, `Assets`, `NVRAM`) and the shared `roms` folder, for the role scripts | `C:\supermodel-win` |

## Files

| File | What it does |
| --- | --- |
| `seq.lua` | A MAME Lua script that presses ports, takes snapshots and exits, from a list in the file named by `SEQ_FILE`. Steps are `{frame, "press"|"on"|"off"|"shot"|"exit", "Port field name"}`. A missing field is skipped |
| `ports.lua` | Prints every input port field of a game (run headless with `-video none`) |
| `solo-sm2emu.ps1` | Starts each Model 2 game in SM2-Emu alone, with the link off and on (nobody on the other end), and takes a window capture at 20, 40 and 60 seconds |
| `solo-supermodel.ps1` | The same for Supermodel games, without and with `-net` |
| `menu-sm2emu.ps1` | Opens a Model 2 game's test menu and goes to Game Assignments with the keyboard, to read the link settings. The number of key presses per game is in the `$plan` list |
| `mame-menu.ps1` | Opens the test menu of MAME games with `seq.lua` and dismisses the warning screen with a mouse click |
| `mkreport.py` | Builds the list of link games from `mame -listxml` (standard input) and MAME's source. It reads `segas32.cpp` from `/src` and `gunbustr.cpp` from `/src2` |
| `devscan.py` | Counts every device in `mame -listxml` whose name looks like a network or serial link |
| `xkeys.py` | Sends keys to an X server with XTest (`KEYSYM:SECONDS`, `wait:SECONDS`, `down:`, `up:`). Used on the cabinet, as root, with `DISPLAY=:0` |
| `xgrab.py` | Saves the X root window as a PPM. It shows **stale frames** for OpenGL windows, so use the emulator's own screenshot key instead |
| `frontend-mockups.py` | Draws the mock-ups of `docs/research/link-frontend-plan.md` with the frontend's font, palette and Arcadeflow icons. `python3 frontend-mockups.py OUT_DIR REAL_LIST_PNG ART_DIR`: the list screenshot gives the title band, ART_DIR holds the cabinet's snaps (`~/media/snap/<system>/<game>.png`) named `snap_<system>_<game>.png`. The art is not in the repo. Run it in the `fliperos-tests-pil` image |
| `kb.ps1`, `kb2.ps1` | Helpers to dot-source: key presses with scan codes (`Tap`), window focus, window captures, finding the SDL window of a process (`GameWin`) |
| `roles.ps1` | Supermodel role helpers: start one of the copies A to D with `-net` and its ports (`Start-SM`), set the role and car number of Scud Race (`Set-ScudRole`), Daytona USA 2 (`Set-Daytona2Role`) and Dirt Devils (`Set-DirtRole`) through the test menu. Reads `SUPERMODEL_COPIES` |
| `nvram-supermodel.ps1` | Collects the NVRAM of each cabinet number of Scud Race, Daytona USA 2 and Dirt Devils into `$LINK_TESTS_OUT\nvram\supermodel`. Cabinets 1 to 4 are the files the four-copy tests left in the copies, 5 to 8 are made by raising the car number |
| `nvram-sm2emu.ps1` | Makes the SM2-Emu NVRAM of Daytona USA for cabinets 1 to 8 and checks each one on the network screen |
| `ssf2tb-tournament.sh` | Four Super Street Fighter II: The Tournament Battle in a chain, headless, in the `fliperos-linktest` image: a coin and Start on each, and each machine's screen saved as PNG (12 a second) through the tournament intro and the start of the fights. Uses `rec.lua` |
| `daytona-link.sh` | Four Daytona USA in a ring (MAME's `m2comm`), headless, in the `fliperos-linktest` image, for the site animation. It first makes the NVRAM of cars 2 to 4 (slaves) through the test menu, once, into `OUT/nvram`. Then the master starts, the slaves right after it, with `-comm_framesync` so the four advance frame by frame together; coin, Start and the accelerator at the same frame on each, counted from the moment the link is up. `EVERY`, `FROM`, `END`, `COIN`, `STARTS`, `ACC` set what is recorded and pressed. Uses `rec.lua` |
| `rec.lua` | A MAME Lua script that presses ports, sets analog values (a pedal, a wheel) and saves snapshots every N frames, from the plan in the file named by `REC_FILE`. With an `anchor` it counts frames from the moment some bytes of memory hold the given values (the link up), and prints `SHOT frame` for each snapshot |
| `link-story.py` | The real frontend's link screens on every cabinet, for the site animations: `netplay` (Escape Kids, 2 cabinets), `ssf2tb` (4 cabinets) or `daytona` (4 cabinets of one player, Model 2). A fake library with the cabinet's art and a real party on the loopback. Run it in the `fliperos-guitest` image |
| `pixelcab.py` | The drawing shared by the animations: Japanese candy cabinets in pixel art (light body with a rounded top, lit green marquee, black glass around the monitor, red ball-top joysticks with three buttons per player, coin door); the Formula 1 racing cabinets of the home's RACE LINK room (`RaceCab`: red monitor dome, lit marquee with chequered flags and the car number, the car seen from behind with its rear wing, wide tyres and the steering wheel in the cockpit); the network cables lying on the floor with pulses, the CRT screens and the captions |
| `netplay-anim.py`, `ssf2tb-anim.py`, `daytona-anim.py` | The site animations `anim/netplay-{en,pt}.webp`, `anim/ssf2tb-{en,pt}.webp` and `anim/daytona-{en,pt}.webp` (plus GIFs), 1200x900, from the screens of `link-story.py` and the game (the cabinet's preview video of Escape Kids, the PNGs of `ssf2tb-tournament.sh` and `daytona-link.sh`). Run them in the `fliperos-video` image; `PREVIEW=t1,t2` saves only those instants |

## Things that cost time

- **MAME warning screen.** The warning for imperfect games waits for a key. `-skip_gameinfo` does not skip it. It is skipped by `-seconds_to_run` between 1 and 299, by `-video none`, and by a mouse click on the window.
- **Keys.** `keybd_event` needs the scan code (`MapVirtualKey`) and the window in the foreground. A hidden PowerShell has no right to take the foreground: click the window instead. Hold a key for 250 to 450 ms, or the emulator misses it.
- **MAME's `.cfg` tag.** A Machine Configuration setting is saved with a leading colon, for example `:comm:CFG`. Without the colon the setting is ignored.
- **Empty values in PowerShell.** `-comm_remotehost ""` only reaches MAME if the whole argument list is one string.
- **Screenshots of the cabinet.** Use the emulator's key (F12 in SM2-Emu and MAME). `xgrab.py` returns old frames.
- **Stopping the cabinet's frontend.** See the notes in `docs/research/linked-cabinets.md`.
