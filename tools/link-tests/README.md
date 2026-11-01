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

## Things that cost time

- **MAME warning screen.** The warning for imperfect games waits for a key. `-skip_gameinfo` does not skip it. It is skipped by `-seconds_to_run` between 1 and 299, by `-video none`, and by a mouse click on the window.
- **Keys.** `keybd_event` needs the scan code (`MapVirtualKey`) and the window in the foreground. A hidden PowerShell has no right to take the foreground: click the window instead. Hold a key for 250 to 450 ms, or the emulator misses it.
- **MAME's `.cfg` tag.** A Machine Configuration setting is saved with a leading colon, for example `:comm:CFG`. Without the colon the setting is ignored.
- **Empty values in PowerShell.** `-comm_remotehost ""` only reaches MAME if the whole argument list is one string.
- **Screenshots of the cabinet.** Use the emulator's key (F12 in SM2-Emu and MAME). `xgrab.py` returns old frames.
- **Stopping the cabinet's frontend.** See the notes in `docs/research/linked-cabinets.md`.
