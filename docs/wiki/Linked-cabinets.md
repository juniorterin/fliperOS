# Linked cabinets

Some arcade games were built to be played on several machines at once: racing cabinets joined by a link cable, or a fighting game that needs four cabinets for its tournament mode.

This page lists those games, how the link works in each emulator FliperOS ships, and what each game needs to start: how many cabinets, how many players and screens, whether one cabinet must be master, and whether you tell the game how many cabinets there are.

**The FliperOS frontend does link play for five games on its own**: Daytona USA, Scud Race, Daytona USA 2, Dirt Devils and the Super Street Fighter II Tournament Battle. A green globe marks them in the list, the game menu offers LINK PLAY or JOIN LINK, and a waiting room starts the machines in the right order with the right NVRAM. It uses the **network cable only** (never Wi-Fi) and needs the cabinets on the same network.

For every other game, and to know what the frontend does underneath, everything on this page is set by hand in the emulator: a command line, an ini file, or the game's own test menu.

## At a glance

Every row says how it was checked. **Tested** means two or more instances were linked and played here. **Solo** means the game was only started alone, with the link on. **Source** means it comes from reading the emulator's code.

| Game | Emulator | Cabinets | Players per cabinet | Screens | Master / slave | Cabinets set in the game | Checked |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Daytona USA | SM2-Emu, GroovyMAME | 2 to 8 | 1 | 1 | Yes (Link ID) | No (found when the link starts) | **Tested** with 2 |
| Super Street Fighter II: The Tournament Battle | GroovyMAME | 4 | 2 | 1 | No (the first one has an empty remote host) | No (the game finds its place in the chain) | **Tested** with 4 |
| Sega Touring Car Championship | SM2-Emu | not checked | 1 | 1 | Link Type | not checked | Solo |
| Indy 500 | SM2-Emu | not checked | 1 | 1 | Network Type + Cabinet ID | not checked | Solo |
| Motor Raid | SM2-Emu | not checked | 1 | 1 | Network Type + Cabinet ID | not checked | Solo |
| Wave Runner | SM2-Emu | not checked | 1 | 1 | Network Type + Cabinet ID | not checked | Solo |
| Cyber Troopers Virtual-On Twin | SM2-Emu | not checked | 1 | 1 | Network Link Attribute | not checked | Solo |
| Super GT 24h | SM2-Emu | set by Link Max | 1 | 1 | Link Type | **Yes** (Link Max) | Solo |
| Scud Race | Supermodel | 2 to 8 (car numbers 1 to 8) | 1 | 1 | Yes (Link ID in the test menu, starts as master) | No (found when the link starts) | **Tested** with 2 and 4 |
| Daytona USA 2 | Supermodel | 2 to 8 (car numbers 1 to 8) | 1 | 1 | Yes (Link ID, starts as master) | No (found when the link starts) | **Tested** with 2 and 4 |
| Dirt Devils | Supermodel | 2 (four did not link) | 1 | 1 | Yes (Communication Mode, starts as slave, and Machine ID) | No | **Tested** with 2 |
| Spikeout | Supermodel | not checked | 2 | 1 | not checked | not checked | Solo |
| Sega Rally 2, Le Mans 24, Harley-Davidson | Supermodel | not checked | 1 | 1 | not checked | not checked | Solo |
| Gunbuster | GroovyMAME | 2 | 2 | 1 | Yes (ID 0 and ID 1) | No | Source |
| Virtua Racing, Virtua Formula | GroovyMAME | not checked | 1 | 1 | Set by the game | No | Source |
| Wing War | GroovyMAME | not checked | 1 | 2 | Set by the game | No | Source |
| F1 Super Lap, Rad Rally | GroovyMAME | not checked | 1 | 1 | Set by the game | No | Source |
| OutRunners, Stadium Cross | GroovyMAME | not checked | 2 | 2 | Set by the game | No | Source |

"Not checked" means the answer was not found, not that the game has no limit. The sections below say what each emulator needs.

## Which emulator

**Model 2 goes to SM2-Emu.** GroovyMAME emulates Model 2 poorly, and SM2-Emu has its own link.

**Model 3 goes to Supermodel.** MAME's Model 3 communication board is an empty stub: the network code in it is commented out, so no data crosses between two MAME instances.

**Model 1, System 32, CPS-2 and Gunbuster go to GroovyMAME.** These are the boards whose link MAME really emulates.

## How a link starts

Most links are a **ring**: each machine listens on its own port and connects to the next one, and the last connects back to the first. For two machines, each points at the other.

A few things apply to all of them:

- **Start the machines close together.** The order matters, and it is not the same everywhere: see each emulator below.
- **The machines must run at the same speed.** One that is fast-forwarded, or much slower, loses the link.
- **Open the ports.** The cabinet has no firewall. On a Windows PC, allow the emulator through the firewall if the link does not form.
- **Do not count on joining late.** In MAME the ring boards do not reconnect after the link drops (the source marks the link dead). In Supermodel a machine that was restarted did not rejoin, and the other had to be restarted too. A game already running was not joined by a third machine in any emulator.

## SM2-Emu: Sega Model 2

The link is a UDP ring. In `sm2-emu.ini` (or in F10 > Network):

```ini
[network]
link_enabled = true
link_local_ip =
link_port = 15112
link_next_ip = 192.168.1.11
link_next_port = 15112
```

`link_next_ip` is the next machine in the ring. For two machines each one points at the other, and the changes take effect on the next game launch. With the link off, the game starts alone as a standalone cabinet.

**Start the master first, then the slave.** A slave that waits too long for the master gives up and shows CANCELLED.

**The role is set in the game's test menu**, not in the ini. The keys are `0` for Test and `9` for Service. In most Model 2 menus, Service moves the cursor and Test selects. Daytona and Desert Tank use the VR buttons to move (`B` and `N`) and Start (`1`) to select. The menus differ from game to game.

| Game | Link settings in the test menu | Default | Alone with the link on |
| --- | --- | --- | --- |
| Daytona USA | Link ID: Master, Single or Slave. Car Number: 1 to 8 | **Master** | Waits on "Network Checking". Choose Single to play alone |
| Sega Touring Car Championship | Link Type | Stand alone | Plays normally |
| Indy 500, Motor Raid, Wave Runner | Network Type and Cabinet ID | Stand alone, ID 1 | Plays normally |
| Cyber Troopers Virtual-On Twin | Network Link Attribute | No link | Plays normally |
| Super GT 24h | Link Type and **Link Max** | Not link | Plays normally |
| Sega Water Ski | none found | | Plays normally |
| Sega Rally Championship, Over Rev, Desert Tank | not read | | Plays normally |
| Manx TT Superbike | not read | | Stops at the motion slider check, which has nothing to do with the link |

Daytona is the only one tested with two machines. The others were started alone, with the link on and the default role, to see which ones wait for a partner. Only Daytona does. Setting each game to master and looking again was not done.

**Daytona with two machines.** On the slave, open the test menu, go to Game System, set Link ID to Slave and Car Number to 2, and leave the menu. Start the master (Link ID Master, car 1) first, then the slave. Both leave the "Network Checking" screen and show "up to 2 players" in attract mode. Insert a coin and press Start on each one to race.

Two races were played this way, one machine on a PC and one on the cabinet's CRT. Both ran at 57.5 frames a second, the other car showed on each screen, and the start was within a second or two on both. Car Number goes up to 8, but only two machines were tried.

**Daytona in GroovyMAME** links the same way, with the `-comm_*` options below. There the order is the other way round: start the slave first, then the master. Two masters never link: both stay on "Network Checking".

## Supermodel: Sega Model 3

Supermodel's games with a net board are Daytona USA 2 (and Power Edition), Dirt Devils, Harley-Davidson, Le Mans 24, Scud Race (and Plus), Ski Champ, Spikeout (and Final Edition), Sega Rally 2 and Virtual-On 2. The Lost World has none.

The link is a TCP ring, set on the command line:

```sh
supermodel scud.zip -net -port-in=1970 -port-out=1971 -address-out=192.168.1.11
```

`-port-in` is this machine's port, `-port-out` and `-address-out` are the next machine's. The defaults are 1970, 1971 and 127.0.0.1.

Alone, with and without `-net`:

| Game | Without `-net` | With `-net`, no partner |
| --- | --- | --- |
| Scud Race, Daytona USA 2 | "CANCELLED, network board not present" | Waits as MASTER ("This is master controller") |
| Dirt Devils | Attract mode | Waits as SLAVE (a diagnostic screen: mode, packet size, synch gap) |
| Spikeout | The game window never opened | Attract mode |
| Sega Rally 2, Le Mans 24, Harley-Davidson | Attract mode | Attract mode |
| Ski Champ | "Drive board trouble FF" | Same |
| Virtual-On 2 | Warning screen | Black screen |

The table only says which games wait for a partner. Ski Champ and Virtual-On 2 could not be judged.

**Scud Race with two machines** was linked and raced, as two Supermodel windows on one PC. Each instance needs its own folder, so the NVRAM does not clash.

- **Set the slave first.** Run the game with `-net`, press Test (`6`) twice to reach the test menu, and use Service (`5`) to move. Game Assignments is the 8th item counted from Exit. Its first two rows, Link ID and Car Number, are above the visible part of the window, so they are changed blind: Service from Exit goes to Link ID, then Car Number, and Test changes the value. One Test on Link ID makes it Slave. One Test on Car Number makes it 2. Leave through Exit twice. The "Network Checking" screen that follows shows the values. Close the emulator normally so the NVRAM is saved.
- **Start the machines:**

```sh
supermodel scud.zip -net -port-in=1970 -port-out=1971 -address-out=127.0.0.1   # master, car 1
supermodel scud.zip -net -port-in=1971 -port-out=1970 -address-out=127.0.0.1   # slave, car 2
```

  The master was started first, six seconds before the slave. Both TCP links come up, both leave "Network Checking" and show "Up to 2 players may race at once". After a coin and Start on each, both pick a course and a transmission and race: the master showed 1st of 2, the slave 2nd of 2, with the lap times 0.04 seconds apart.
- **If the slave leaves during a race,** the master keeps racing. A little later it goes back to "Network Checking".
- **A machine that restarts does not rejoin.** With the slave restarted, only its connection to the master came back. The master did not connect to it again, and the same happened the other way round. Both stayed on "Network Checking". Restart both machines.

**Car numbers.** The Car Number of Scud Race and Daytona USA 2 goes from 1 to 8, and one more press after 8 goes back to 1. The cabinet number you give each machine is the car number.

**Four machines in Scud Race.** Four instances formed a ring and all four showed "Up to 4 players may race at once". Each machine only connects to the next one after it receives the connection of the one before, so **in a ring of three or more, start the slaves first and the master last**, in the reverse order of the ring (the machine just before the master first). With the master first, the link between the last two machines never came up. For two machines the master first also works.

### Daytona USA 2

Same method as Scud Race, with a different test menu. Press Test (`6`) four times to get to it: a diagnostic screen, the network check screen, then the menu with the cursor on Exit. Game Assignments is the 8th item counted from Exit.

- **Link ID** goes round four values, one for each press of Test: Master, Slave, Live and Single. It starts as Master. Use Master and Slave for a link.
- Once the machine is a slave, the list shrinks to five rows: Link ID, Car Number, Cabinet Type, Motor Power and Exit.
- Leave through Exit. Closing the emulator while still inside the menu does **not** save the changes.

A pair raced, with lap times 0.01 seconds apart. Four instances formed a ring (eight connections) and went together up to the car selection, starting the slaves first and the master last.

### Dirt Devils

It starts as a **slave**, so one machine of the pair needs the master role. Press Test (`6`) once to open the test menu. Game Assignments is the 7th item counted from Exit, and its page fits the window, so the values can be read.

- **Communication Mode** goes round Slave, Satellite, No Link and Master.
- **Machine ID** is 1 on the master and 2 and up on the others. Ids 1 to 4 were set and read. The highest value was not looked for.

A pair raced (ID 1 master, ID 2 slave), with lap times 0'20"96 and 0'21"03. **Four instances did not link:** only two of the four links came up, in both start orders. This was not solved, so treat two as the limit.

## One NVRAM for each cabinet number

The role of a cabinet (master or slave, car number or machine ID) is saved in the game's NVRAM, so each cabinet number needs its own file. The repository keeps them in `config/link-nvram`: SM2-Emu Daytona USA, and Supermodel Scud Race, Daytona USA 2 and Dirt Devils. The README there says what each file holds and how to use it.

## GroovyMAME

The link uses four options. They are the same for every board:

| Option | What it is |
| --- | --- |
| `-comm_localhost`, `-comm_localport` | The address and port this machine listens on |
| `-comm_remotehost`, `-comm_remoteport` | The address and port of the machine it connects to |
| `-comm_framesync` | Wait for the vertical sync (on or off) |

The role and the switch that turns the board on are **not** command line options. For most boards they come from the game's test menu. For CPS-2 and Gunbuster they are a Machine Configuration setting, which can be saved in the game's `.cfg` file.

GroovyMAME shows a warning screen for imperfect games, and the game waits on it. A mouse click on the window closes it. `-skip_gameinfo` does not.

### Super Street Fighter II: The Tournament Battle

The sets are `ssf2tb`, `ssf2tba`, `ssf2tbh`, `ssf2tbj`, `ssf2tbj1`, `ssf2tbr1` and `ssf2tbu`. The bootleg `ssf2tbd` has the board but no link.

It needs **four cabinets**, in a **chain, not a ring**. Turn on Machine Configuration > Communication on each one. There is no master or slave: the first machine is the one with an empty remote host, and the last has an empty local host.

```sh
mame ssf2tb -comm_localhost 0.0.0.0 -comm_localport 1234 -comm_remotehost ""
mame ssf2tb -comm_localhost 0.0.0.0 -comm_localport 1235 -comm_remotehost 127.0.0.1 -comm_remoteport 1234
mame ssf2tb -comm_localhost 0.0.0.0 -comm_localport 1236 -comm_remotehost 127.0.0.1 -comm_remoteport 1235
mame ssf2tb -comm_localhost "" -comm_remotehost 127.0.0.1 -comm_remoteport 1236
```

Replace 127.0.0.1 with the previous machine's address when they are on different PCs. Insert a coin and press Start on all four: each screen then shows "The Tournament Battle, Battle 1" with a different match, eight fighters in all.

The game finds its place in the chain by itself, so you do not tell it how many cabinets there are. With fewer than four it stays on a blinking TERMINAL CHECK. That was seen with two and three machines joined in a ring, which is the wrong layout, so fewer than four in a chain was not tested.

### Gunbuster

Two cabinets, two players each. Turn on Machine Configuration > Link Simulation. In the test menu, Configuration, set Link Play to On and the ID Number to 0 on one and 1 on the other.

```sh
mame gunbustr -comm_localhost 0.0.0.0 -comm_localport 1234 -comm_remotehost ""
mame gunbustr -comm_localhost "" -comm_remotehost 127.0.0.1 -comm_remoteport 1234
```

Reset both at about the same time. The game shows COMMUNICATION ERROR if the other cabinet is missing, and COMMUNICATION CUT if the frame counter stops for sixteen frames. This comes from the source, and it was not tested.

### Model 1 and System 32

Both are rings, with the master, slave or relay role written by the game into the board's shared memory. How many machines there are is found when the link starts: the master numbers the others as the setup frame goes round the ring.

- **Model 1:** Virtua Racing, Virtua Formula and Wing War (and its R360 version).
- **System 32:** F1 Super Lap, OutRunners, Rad Rally, Stadium Cross (`scrossa` is the "linkable" set) and the two Soreike Kokology games. The board is in every System 32 game, but only these ones set a link type. The Rad Rally test menu has a Network Test item.

Virtua Racing, Rad Rally, OutRunners and Stadium Cross were started in MAME 0.289 and their test menus opened. The other games here were not tried. No link between two instances was tried for any of them.

## Flycast: NAOMI

**Games that use several boards in one cabinet** are not a link between machines. Ferrari F355 Challenge, Airline Pilots and Sega Strike Fighter run each board as its own Flycast window, one per monitor. See [Multiple monitors](Multiple-Monitors.md).

**Linking two cabinets.** Flycast's own LAN link is turned on in its advanced settings (Broadband adapter and Naomi network): one instance is the server, and the other types its IP. This comes from reports on the web, and it was not tested here. Reports say two machines work and a third can fail with a country error. The F355 "twin" sets are the ones made for a battle cable between two cabinets.

The Derby Owners Club, World Club Champion Football and Mushiking sets are online and card games, and were not tried.

## What cannot be linked

MAME marks 309 sets (107 games) as having a network or serial link that is not emulated: Namco's Ridge Racer, Final Lap, Cyber Cycles and Alpine Racer 2 and others, Konami's GTI Club, Midnight Run, Racing Jam and Thrill Drive, Taito's Battle Gear and Chase Bombers, Midway's Cruis'n Exotica and Atari's Road Riot 4WD. No MAME code reads the link options for them, so there is nothing to turn on.

The Model 3 boards in MAME (and the NAOMI ones that share the same board) and the Chihiro network board are stubs. The Konami network PCBs and the Namco C139 serial chip are stubs too.

Gaelco's Speed Up, Surf Planet, Radikal Bikers and Football Power link through shared memory between two instances, and only if MAME is rebuilt with a source switch. The normal build cannot do it.

## How this was checked

Between 31 October and 1 November 2026. The emulators were GroovyMAME gm0289sr222f (MAME 0.289), SM2-Emu 0.9.56, and Supermodel 0.3a at the same commit as the cabinet's (1481545). The Daytona link ran with one instance in a window on a PC and the other on the cabinet's CRT. The Tournament Battle (four instances) and the Supermodel games (Scud Race and Daytona USA 2 in pairs and in fours, Dirt Devils in a pair) ran all on the PC.

The "Source" rows and the lists of boards come from MAME 0.289's source and its game list (`mame -listxml`).
