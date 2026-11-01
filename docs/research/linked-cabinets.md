# Linked cabinets: research notes

Lab notebook for the work of 31 October and 1 November 2026. It records what was found, how, what failed, and what is left, so the research can go on later.

The user-facing result is the wiki page *Linked cabinets* (`docs/wiki/Linked-cabinets.md`). The tools are in `tools/link-tests`. The per-set lists of MAME games are in `docs/research/mame-link-sets.md` (generated).

## Question

Which arcade games link several machines (cabinets), and for each one: how it connects, whether it is automatic, what must be configured and where, whether that can go on the command line, how many cabinets it needs, whether one must be master, and whether the number of cabinets is set in the game.

## Setup used

| What | Version or detail |
| --- | --- |
| PC | Windows 10, 2560x1440, Ethernet 192.168.1.158, Docker Desktop, PuTTY (plink, pscp) |
| Cabinet | FliperOS, Ubuntu 24.04, 192.168.1.241 (it changes: find it with `Resolve-DnsName fliperos.local`), Intel i3 540, CRT on VGA-1 |
| MAME on the PC | Official MAME 0.289 for Windows, and a Docker image (`fliperos-linktest`) with the same GroovyMAME release the ISO ships (`gm0289sr222f`) for headless runs |
| MAME on the cabinet | GroovyMAME 0.289 in `/usr/local/libexec/groovymame`, started through `fliperos-x11-run` |
| SM2-Emu | Upstream release 0.9.56 (Windows zip on the PC, Linux tar on the cabinet). The cabinet's own build (`~/.local/src/sm2-emu`) was not used |
| Supermodel | 0.3a git `1481545` (25 October 2026), the cabinet's commit, as the Windows release build |
| MAME source | Cloned at tag `mame0289` (about 1.2 GB), read with grep |

## How to find the games that link in MAME

This is the method that would have found everything without a hint. The first attempt missed the Tournament Battle because the list was cut to parent games and the group of eight clones came out empty.

1. **Devices.** Run `mame -listxml` and count every `device_ref` whose name looks like a link, **clones included** (`tools/link-tests/devscan.py`). Look at each device's own entry for a `configuration` (for example "Communication").
2. **Source.** Search the source for who reads `comm_localhost`, `comm_remotehost` and friends, and for `osd_file::open("socket.`. That gives the devices with real networking. In 0.289: `m1comm`, `m2comm`, `s32comm`, `cps2comm`, `gunbustr_link` (and `mb89374`, the data link controller inside `m1comm`). The rest of the hits are not arcade: a Nascom, TI-99 TIPI, CoCo DriveWire, Colour Genie, the GDB stub and the Lua engine.
3. **Games per device.** Find where each device is instantiated and, for `s32comm`, which `init_` functions call `set_linktype`. `tools/link-tests/mkreport.py` does this and writes `mame-link-sets.md`.
4. **Header comments.** `cps2comm.cpp` and `gunbustr_link.cpp` explain how to start several instances.
5. **Flags.** The XML `feature` of type `lan`, `wan` or `comms` marks games whose link is known but not emulated (309 sets, 107 games in 0.289). No code reads `comm_*` for them.
6. **Check the stubs.** A device in step 1 that is never in step 2 is a stub: `m3comm`, `seganetw`, `konami_gn676a_lan` and `konami_gn676b_lan`, `k056230`, `namco_c139`.

## What the MAME source says

### Common

- Options (global): `comm_localhost`, `comm_localport`, `comm_remotehost`, `comm_remoteport`, `comm_framesync`. They are not per game and not per device. The role and the switch that enables the board are **not** options.
- Ring boards (`m1comm`, `m2comm`, `s32comm`) build file names `socket.<host>:<port>` and open them through MAME's OSD file layer: the receive side is opened with `OPEN_FLAG_CREATE` (it listens), the transmit side with flags 0 (it connects). `m1comm.h`, `m2comm.h` and `s32comm.h` define `*_SIMULATION`, so the ring protocol is compiled in.
- The ring protocol: the master sends a link-id frame (`0xFF`, id 1), each slave adds one and forwards it, the master sends a link-size frame (`0xFE`), then a VSYNC frame (`0xFC`) every frame. The number of machines is discovered, not configured. There is a 4 second timer (`m_linktimer = 0x00e8`, "58 fps * 4s").
- If a read or write fails after the link is up, the ring boards set the link state to dead (`m_linkalive = 0x02`) and do not reconnect.
- `comm_framesync` makes non-master nodes wait for the master's VSYNC frame.

### Per board

| Board | Role and enable | Notes |
| --- | --- | --- |
| `m2comm` (Model 2) | The game writes it. `EPR-16726` uses the `fg` register for master and slave, `EPR-18643` uses shared byte 1 with `fg` as a fallback. Master is `fg == 1` or `shared[1] == 1`, slave is `fg == 0` and `shared[1] == 2`, relay is both zero | Four machine configs in `model2.cpp` instantiate it. One sets a frame offset of `0x180`. Every Model 2 game has the board |
| `m1comm` (Model 1) | Shared byte 1: 1 master, 2 slave, 0 relay | Frame size `0x1c4`. BIOS `epr15112` for Virtua Racing, Wing War and Star Wars, `epr15624` for Virtua Formula. The data link controller `mb89374` has its own copy of the socket code |
| `s32comm` (System 32) | Shared byte, game dependent: types 14084 (Rad Rally) and 15033 (Stadium Cross, OutRunners) use byte 2 (0 slave, 1 master), type 15612 (F1 Super Lap) uses byte 1 | `set_linktype` is called only by `init_f1lap`, `init_f1lapt`, `init_orunners`, `init_radr` and `init_scross`. The Soreike Kokology sets use `init_radr`, so they get type 14084 too |
| `cps2comm` (CPS-2) | No roles. The head is the instance with an empty `comm_remotehost`, the tail has an empty `comm_localhost`. Needs the config port `:comm:CFG` | TCP with `asio`, no delay. A failed outgoing connection times out after 10 seconds and is retried. A dropped incoming one closes and accepts again. No fixed chain length. `ssf2tbd` uses `dead_cps2comm` (no link) |
| `gunbustr_link` (Gunbuster) | IDs 0 and 1 in the test menu (Configuration > Link Play On). Needs the config port `:link:CFG` ("Link Simulation") | One instance listens (empty remote host), the other connects (empty local host). Reset both at about the same time. COMMUNICATION ERROR if the other is missing, COMMUNICATION CUT after sixteen frames without a frame counter change |
| `m3comm` | none | Stub. The socket reads and writes are commented out, status registers return fixed values, IRQ 5 comes from a timer. One game hack mentions `srally2` |
| `seganetw` | none | Only a ROM. Used by the Chihiro family |
| `konami_gn676a_lan`, `konami_gn676b_lan` | none | Only the memory registers. Racing Jam, Racing Jam 2, Thrill Drive |
| `k056230` (LANC) | none | "Nearly everything TODO", a wrapper so the POST passes. GTI Club, Plygonet, ZR107 and others |
| `namco_c139` | none | "TODO: make this actually work" |
| `gaelco_serial` | Master and slave set in service mode | Link through shared memory, only compiled with `SHARED_MEM_DRIVER`, which is commented out |

## Supermodel

- Games with `<netboard>true` in `Games.xml`: `daytona2`, `dayto2pe`, `dirtdvls` (and four clones), `harley` (`harleya`), `lemans24`, `scud` (`scudau`, `scudplus`, `scudplusa`), `skichamp`, `spikeout`, `spikeofe`, `srally2`, `von2` (and clones). 22 sets. `scuddx` and `scuddxo` are explicitly false. `lostwsga` has none.
- Command line: `-net`, `-no-net` (the default), `-simulate-netboard` (the default), `-emulate-netboard` (needs `-no-threads`), `-port-in=<n>` (also `-port=`, default 1970), `-port-out=<n>` (default 1971), `-address-out=<addr>` (default 127.0.0.1). Config keys: `Network`, `SimulateNet`, `PortIn`, `PortOut`, `AddressOut`.
- Keys on the PC: 1 start, 3 coin, 5 service A, 6 test A, A and S for VR1 and VR2.
- The README says almost nothing about the net board. Web reports (a forum thread on a four-player Scud Race, a fork's release notes) say two cabinets work and four have given trouble.
- Windows builds: `https://github.com/trzy/Supermodel/releases`, with the commit in the tag name.

## SM2-Emu

- Link is UDP, a ring: keys `link_enabled`, `link_local_ip` (empty binds every interface), `link_subnet_mask` (informational), `link_port` (15112), `link_next_ip`, `link_next_port` (15112), `link_cabinet_index` (bookkeeping only) in the `[network]` section of `sm2-emu.ini`, or F10 > Network (the page shows "Connected: cabinet N of M"). It takes effect at the next game launch.
- Master and slave are set in the game's test menu. Keys: `5` coin, `1` start, `9` service, `0` test, `B N M ,` the VR buttons, Left Ctrl accelerate, arrows steer, F8 FPS, F9 quit, F10 menu, F12 screenshot.
- `--config <dir>`, `--nvram <dir>` and `--game <set>` were enough to run several instances. A zip with several revisions needs `--game` (the Daytona zip holds "To The MAXX" and picks it otherwise).
- The software renderer on the PC runs at 57.5 Hz with the window in front and about 23 Hz when it is not.

## Test log

### Daytona USA, pair (done)

- **MAME, two instances on the PC (loopback).** Both start as MASTER: both stay on "Network Checking, this is master controller". One must be a slave. The slave's settings were made in the test menu with a Lua sequence and saved in its own NVRAM directory (`backup1` and `ioboard_eeprom`). Slave first, then master: both TCP links establish and both show the attract screen with "up to N players".
- **SM2-Emu, PC (master) and cabinet CRT (slave).** The slave's NVRAM (`daytona.nv`, `daytona.eeprom`) made on the PC was copied to the cabinet. Master first, then slave. A slave started first showed CANCELLED. After the restart both showed "up to 2 players". Two races were played with keys on both: both at 57.5 frames a second, the other car visible on each side, "Gentlemen start your engines", the rolling start and GO within a second or two of each other. The cabinet log has repeated ALSA underruns.
- **Attract screens are not synchronised**, only the race is. The first "PC is ahead" impression was a 40 second later start of the slave.

### Super Street Fighter II: The Tournament Battle (done)

- The board needs Machine Configuration > Communication = Enable. A cfg file with the tag `:comm:CFG` does it; the tag without the colon is ignored.
- The sockets open only after a coin and Start. With the link enabled but in a **ring** of two or three instances, the game stays on a blinking TERMINAL CHECK. That was the wrong topology.
- With the **chain of four** from MAME pull request 9699, the terminal check passes at once, the attract screen shows INSERT COIN, and after a coin and Start on all four each screen shows "The Tournament Battle, Battle 1" with a different match (Cammy v Chun-Li, Blanka v Fei Long, Zangief v T. Hawk, Ryu v Dee Jay).
- Not done: fewer than four in a chain, a fourth joining late, one leaving.

### Model 2 in SM2-Emu, alone, link off and on (done)

Twelve games, started alone for 60 seconds, with `link_enabled` false and true (next machine absent). Only Daytona stops on "Network Checking" (its default Link ID is Master). Sega Rally, Indy 500, Motor Raid, Desert Tank, Over Rev, Touring Car, Super GT 24h, Wave Runner, Sega Water Ski and Virtual-On Twin reach attract either way. Manx TT stops on "DANGER! Active Motion Slider, now checking system" in both.

Link items in the test menus:

| Game | Items | Default |
| --- | --- | --- |
| Daytona USA | Link ID (Master, Single, Slave), Car Number 1 to 8 | Master, car 1 |
| Sega Touring Car | Link Type | Stand alone |
| Indy 500, Motor Raid, Wave Runner | Network Type, Cabinet ID | Stand alone, 1 |
| Virtual-On Twin | Network Link Attribute | No link |
| Super GT 24h | Link Type, Link Max | Not link |
| Sega Water Ski | none | |
| Over Rev | "Game Assignments Menu" with Foundational Setting and Optional Game Setting, not read | |
| Sega Rally, Desert Tank, Manx TT | not read | |

Menu navigation: most menus say "select with service button and press test button", GAME ASSIGNMENTS is the 7th item counted from EXIT (6th in Over Rev, 5th in Sega Rally). Daytona and Desert Tank use the VR buttons (red up, blue down in the Desert Tank legend) and Start.

### Model 3 in Supermodel, alone (done)

Ten games, 60 seconds, without and with `-net`:

- Scud Race and Daytona USA 2: "CANCELLED, network board not present" without `-net`; with it they wait as MASTER ("This is master controller").
- Dirt Devils: attract mode without; a SLAVE diagnostic (mode SLAVE, packet size 0DA0/0E00, synch gap and status 0) with.
- Spikeout: the game window never opened without `-net`; attract with it.
- Sega Rally 2, Le Mans 24, Harley-Davidson, The Lost World: attract with and without.
- Ski Champ: "Drive board trouble, code FF" (a drive board check), the same with and without.
- Virtual-On 2: the warning screen without, a black screen with.

### Scud Race pair in Supermodel (done, on 1 November, all on the PC)

- Two copies of the Supermodel folder (`A` and `B`, each with `Config`, `Assets`, `NVRAM`), the ROMs in a shared folder. The NVRAM file is `scudau.nv` (the `scud` zip loads the `scudau` set).
- **Slave settings.** `-net` alone shows "This is master controller". Test (`6`) once shows a video test menu, a second time the main test menu (cursor on Exit). Service (`5`) moves down, Test selects, and in Game Assignments Test changes the value of the item under the cursor. The first rows (Link ID, Car Number) are above the visible area of the window, so the cursor is invisible when it is on them. From Exit, Service goes to Link ID, then Car Number. One Test on Link ID gave SLAVE, one Test on Car Number gave 2. Game Assignments is the 8th item from Exit in the main menu, and Exit is 4 presses after it. Leaving the menu restarts the game on the "Network Checking" screen, which shows the values.
- **Link.** Master `-port-in=1970 -port-out=1971`, slave `-port-in=1971 -port-out=1970`, both `-address-out=127.0.0.1`, master first and the slave six seconds later: both TCP connections up, "Up to 2 players may race at once" in attract, then course select, transmission, and the race with 1st of 2 and 2nd of 2. Lap times 00'24"88 and 00'24"84.
- **Slave killed in the race:** the master kept racing and its timer kept running; some seconds later it was back on "Network Checking" (not seen exactly when, the race may have ended).
- **Slave started again:** only the slave's connection to the master came back, the master's connection to the slave did not, after more than a minute. The same when only the master was restarted. Both machines have to restart.
- Windows note: the SDL window and the console are separate windows of the same process. Find the game window by its title with `EnumWindows`, because `Process.MainWindowHandle` is the console.

### Daytona USA 2, Dirt Devils and rings of four in Supermodel (done, 1 November, all on the PC)

- **Daytona USA 2 menu.** Test (`6`) four times: the diagnostic screen, the network check screen, then the test menu with the cursor on Exit. Game Assignments is the 8th item from Exit. Link ID goes round Master, Slave, Live, Single with each Test (blind edits left it on Live and Single twice: read the values on the network screen). Once it is a slave the list has five rows: Link ID, Car Number, Cabinet Type, Motor Power, Exit. Car Number goes 1 to 8.
- **Daytona USA 2 pair:** raced, lap times 0.01 s apart. For two machines the master first also worked.
- **Scud Race ring of four.** With the master first the link between the third and fourth machine never came up. With the slaves first (the machine before the master first) and the master last, all four showed "Up to 4 Players may race at once". Car Number goes 1 to 8 and 8 goes back to 1.
- **Daytona USA 2 ring of four:** 8 connections, the games went together to the car selection, started slaves first and master last.
- **Why the order.** Each machine connects to the next only after it receives the connection of the previous one. The master starts the chain, so every other machine must be listening already.
- **Dirt Devils.** Starts as slave (Communication Mode). The values are Slave, Satellite, No Link, Master. Test once opens the menu, Game Assignments is the 7th item from Exit, the Machine ID row is on the visible part of the page. Pair: ID 1 master, ID 2 slave, master first, raced with lap times 0'20"96 and 0'21"03. Ring of four: only two of the four links came up in both start orders (not solved).
- **Saving.** Closing the emulator while still in the test menu does not save the settings. Leave through Exit.

### A link game started from the frontend on the real hardware (done, 1 November)

The cabinet's frontend on the CRT (the web panel's `/api/screenshot` after a login with `X-FliperOS: 1` gave pictures of it), driven with the virtual pads of `tools/video/vpad.py` (the real Xbox pads unbound with `pads.sh unbind`), and the PC as the second cabinet (python.org embeddable Python, `FLIPEROS_LINK_WIRE=Ethernet,192.168.1.158,192.168.1.255`, Windows SM2-Emu). Daytona USA: LINK PLAY on the cabinet, the PC joined from its presence table, A started, the cabinet's emulator opened first and the PC's 6 s later, and both showed the attract screen "up to 2 players" (cars 1 and 2). After the game closed on the cabinet its `daytona.nv` and `daytona.eeprom` were gone (the player's own `daytonam.*` were never touched), `link_enabled` was false again and the party listener was closed. Mistake: the first taps hit Air Walkers (the saved cursor was ignored because the frontend restarts at the first game of the list) and favourited it; one more press of button 4 undid it.

### Flycast Naomi network: Club Kart (done, 1 November)

Club Kart: European Session (`clubk2k3`, in `~/roms/naomi2`), the cabinet's Flycast (built from master in October 2026) as the **server** and Flycast 2.7 for Windows (`flycast-win64-2.7.zip`) on the PC as the **client**, wired. Options, as `-config` strings (two `-config` arguments on one command line both apply, which matters because `fliperos-x11-run` adds its own): `network:Enable=yes`, `network:ActAsServer=yes|no`, `network:server=IP`, `network:EnableUPnP=no`. The log of the server says "Waiting for slave connections" and of the client "Connecting to server". The link is UDP on port 37391: two instances on one machine both bind it and do not link, and on the cabinet the server socket's receive queue filled and emptied while the PC played. With UPnP on, the log also had "Internet Gateway not found" and "Port 37391 redirection failed" (the Internet), which is why it is turned off. The PC client sat on "CHECKING NETWORK NOW / MODE SLAVE / SEQUENCE SYNCING" and 15 seconds later was on the attract screen "FREE PLAY, PRESS START BUTTON". The server's own dialog (seen with the client missing): "Starting network, press Start to start the game now, waiting for players" with Start Now and Cancel. Not done: two people racing, a third machine, Initial D and F355.

**Flycast GGPO, KOF Neo Wave (`kofnw`, Atomiswave), same pair of machines: not working.** Options `network:GGPO=yes`, `network:ActAsServer=yes|no`, `network:server=IP`, `network:GGPODelay=0`, `network:EnableUPnP=no`; the port is UDP 19713 on both sides (the Windows client binds `0.0.0.0:19713` too). The server log said only "GGPO: Using 0 full analog axes" and, as a warning, that `~/.local/share/flycast/kofnw.state.net` (an optional start state) was not there. A Python raw-socket sniffer on the cabinet (no tcpdump there; `/tmp/fc/sniff.py` as root) saw 96 packets `192.168.1.158:19713 -> 192.168.1.241:19713` in 90 seconds and **none the other way**; the client stayed on "Starting network..." with only a Cancel button. Not proven: the version difference (the image builds Flycast from the development branch of October 2026, the PC ran the 2.7 release; no Windows nightly was found), and whether the server read the packets. Two Flycast on one machine cannot be used to isolate it (same port).

Recovering the cabinet's screen after a takeover when the tty1 loop is stopped and the Setup got in the way: `sudo systemctl restart getty@tty1` starts a fresh autologin session and the frontend comes back. A stray `flycast --version` (it opens the emulator instead of printing) kept running from a `strings` experiment: do not run it.

### The NVRAM of each cabinet number (done)

`tools/link-tests/nvram-supermodel.ps1` and `nvram-sm2emu.ps1` made one NVRAM for every cabinet number: Supermodel Scud Race (1 to 8, `scudau.nv`), Daytona USA 2 (1 to 8, `daytona2.nv`) and Dirt Devils (1 to 4, `dirtdvlsau.nv`), and SM2-Emu Daytona USA (1 to 8, `daytona.nv` and `daytona.eeprom`). Cabinet 1 is the master. The others are slaves, and the cabinet number is the car number (the Machine ID for Dirt Devils). Each file was checked by starting the game with it and reading the role on the screen. They are in `config/link-nvram` with a manifest.

### Model 1 and System 32 in MAME (menus only)

`vr`, `f1lap`, `orunners`, `radr`, `scross` and `gunbustr` load in MAME 0.289 from the 0.283 set and their test menus open. Gunbuster's has MONITOR, SWITCH, SOUND, CONFIGURATION, GUN ADJUSTMENT, FACTORY SETTING and COMMUNICATION TEST. Rad Rally's has a Network Test item and the title "Individual". `swa` and `wingwar` fail the checksum of `315-5711.bin` in 0.283 (and Wing War needs `hd44780`). No link was tried.

## Procedures that worked

### Making a slave's settings (any Sega game with a test menu)

1. Start the game with its own `-nvram_directory`.
2. Drive the test menu with `seq.lua`: turn "Service Mode" on at about frame 930, press the VR or service buttons with 400 ms between them, change the item, leave the menu, take a snapshot, quit. The NVRAM is written on exit.
3. Copy the NVRAM files to the machine that will be the slave.

For Daytona in MAME the steps were Service Mode on, Green x9, Start (Game System), Green x8 (Link ID), Blue x2 (Slave), Red x1, Yellow x1 (car 2), Red x7 (Exit), Start, Service Mode off.

### Opening an emulator on the cabinet's CRT from SSH

The frontend and the Setup keep the screen's DRM master. Taking it needs the tty1 loop stopped, and the program run as root on another VT.

1. Find `fliperos-tty1` (the loop) and its children. `kill -STOP` the loop, and `sudo kill -TERM` the `fliperos-gui` and `fliperos-frontend` processes (they run as root or the user).
2. `sudo openvt -c 2 -s -f -- script`, where the script runs `/opt/fliperos/bin/fliperos-x11-run <emulator> <args>` as root with `HOME=/home/fliperos`, and at the end does `kill -CONT <loop pid>; chvt 1`.
3. Do not use `pkill -f` through `sudo -S`: the pattern matches the `sudo` command itself and kills it. Use `pgrep` and a pid.
4. Keys: `tools/link-tests/xkeys.py` as root with `DISPLAY=:0`. Screenshots: the emulator's F12 key.

If the user quits the game on the CRT, the script resumes the loop and the Setup returns.

### Side effects left on the cabinet

- `~/bios/mame/segabill.zip` was added (the Model 2 and 3 sets need it in MAME).
- The Downloader filter was rewritten several times. It now holds the Model 2 filter with Buttons = any (so Daytona and Royal Ascot II are chosen). The previous filter is in `~/downloader-filter-before-daytona.kv` and the state before the first change in `~/downloader-state-backup-20261031`. The Flycast filter has to be saved again in the Setup.
- Model 2 and Model 3 sets from the Downloader are in `~/roms/model2` and `~/roms/model3`.
- `/tmp/dl` (scripts, NVRAM, config) is gone at the next reboot.

## Mistakes to avoid

- **Parents only.** Filtering to parent games hid the whole `cps2comm` group.
- **MAME's warning screen.** The first batch of MAME runs sat on the warning and was thrown away.
- **Ring versus chain.** The Tournament Battle needs a chain. Two and three instances in a ring told nothing.
- **Stale screenshots.** `xgrab.py` showed the same frame for an OpenGL window and nearly led to the wrong conclusion that the cabinet was frozen.
- **Hidden windows.** A background PowerShell cannot take the foreground, so keys went nowhere.

## Open questions and next tests

Roughly in order of value.

1. **Supermodel.** Pairs and rings of four are done on one PC for Scud Race and Daytona USA 2, and a pair for Dirt Devils. Left: the Dirt Devils ring of four (only two links came up) and its highest Machine ID, and a pair with the PC and the cabinet.
2. **Model 2 roles.** Set MASTER in each game that has a link item and see which ones wait for a partner. Then pairs: Touring Car, Indy 500, Motor Raid, Wave Runner, Virtual-On Twin, Super GT 24h (read the range of Link Max). Read Sega Rally, Over Rev and Desert Tank, and find out what the Manx TT motion slider check wants.
3. **Late join and leaving.** A third cabinet in a Daytona ring, one cabinet leaving, in MAME, SM2-Emu (UDP, "best effort") and Supermodel. For the Tournament Battle, a fourth instance joining late and one leaving (the source says it reconnects).
4. **Gunbuster pair** with the procedure in the header comment, then Model 1 (`vr`, `vformula`, and fix `swa` and `wingwar`) and System 32 (`radr`, `f1lap`, `orunners`, `scross`, the Kokology games).
5. **Flycast.** The LAN link (Broadband adapter and Naomi network, server and IP), the F355 battle cable, the claim that 2.6 added a match-code server and 2.7 multiscreen. Needs ROMs the cabinet does not have (F355, Initial D, Club Kart).
6. **More than two cabinets.** SM2-Emu Daytona with 3 or more (its NVRAMs for 1 to 8 exist, the ring was only tried with two), and the maximum of the Model 2 games (Cabinet ID and Link Max ranges).
7. **Numbers.** The real maximum of cabinets per game, from operator manuals. A web search found none.
8. **A Setup screen.** Generate the `.ini`, the options and the NVRAM for each game, with the role, the next machine's address and the order of start, and open the firewall.

## Sources consulted

- MAME pull request 9699 (the Tournament Battle link, with the command lines): `https://github.com/mamedev/mame/pull/9699`
- MAME command line documentation, communication options: `https://docs.mamedev.org/commandline/commandline-all.html`
- MAME source files `m1comm.cpp`, `m2comm.cpp`, `s32comm.cpp`, `m3comm.cpp`, `cps2comm.cpp`, `gunbustr_link.cpp`, `konami_gn676_lan.cpp`, `k056230.cpp`, `namco_c139.cpp`, `gaelco3d_m.cpp` and `src/frontend/mame/ui/ui.cpp` (startup screens), at tag `mame0289`
- SM2-Emu README, "Networking (cabinet link)": `https://github.com/dmanlfc/sm2-emu`
- Supermodel releases and its `-?` help: `https://github.com/trzy/Supermodel`
- A forum thread on Scud Race with four cabinets and Batocera's Model 3 page (the "Network Board Not Present" error and the Link ID fix)
- Wikipedia and arcade-history pages on the Tournament Battle (four cabinets for the eight-player mode)
