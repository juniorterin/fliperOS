# Linked cabinets

Some arcade games were built to be played on several machines at once: racing cabinets joined by a link cable, or a fighting game that needs four cabinets for its tournament mode.

This page lists those games, how the link works in each emulator FliperOS ships, and what each game needs to start: how many cabinets, how many players and screens, whether one cabinet must be master, and whether you tell the game how many cabinets there are.

**The FliperOS frontend does link play for six games on its own**: Daytona USA, Scud Race, Daytona USA 2, Dirt Devils, Club Kart: European Session and the Super Street Fighter II Tournament Battle. A green globe marks them in the list, the game menu offers LINK PLAY or JOIN LINK, and a waiting room starts the machines in the right order with the right NVRAM. It uses the **network cable only** (never Wi-Fi) and needs the cabinets on the same network.

Games of a RetroArch core that does net play, with more players than a cabinet has controls, and the NAOMI and Atomiswave games of Flycast (GGPO, up to four players on two to four cabinets) get **party play** in the same menu: see Party play below. The frontend calls it a party, not net play, because it only runs on your local network, never over the internet.

**Each cabinet has a name** that the others see: in the waiting room, on the JOIN tile ("HOST APPLE") and in a notice with a bell at the bottom of the screen, "APPLE IS PLAYING", when it opens a party or a link game. Set it in **Setup > System > Cabinet name** or during the installation (up to 12 letters, numbers, spaces and hyphens). With no name, each cabinet gets a fruit or an animal out of a list of 100, always the same for that machine (picked from its `/etc/machine-id`). It is kept as `cabinet_name=` in `/etc/fliperos/fliperos.conf`, and the frontend reads it when it opens.

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
| Club Kart: European Session | Flycast | 2 | 1 | 1 | Yes (the first is the server) | No | **Tested** with 2 |
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

### Latency of a link

**Your own controls are as fast as playing alone.** Each cabinet runs its own copy of the game, and only that copy reads its controls. The link adds nothing to them.

**The other cars or players are seen with the delay of the original boards.** The games exchange their state at the pace of the frames (the ring boards of MAME send one VSYNC packet a frame). So you see the other cabinet a frame or two late, as in the arcade. On the network cable a packet takes well under a millisecond (a frame is 16.7 ms at 60 Hz), so the cable adds almost nothing to it. In a ring of more machines, a packet goes through each machine on its way, as it did on the real boards.

**There is no rollback and no input delay to tune.** The games wait for each other by themselves. When the network stops, the game says so (COMMUNICATION ERROR, or the link drops) and does not catch up later. That is why the link is on the cable only.

This comes from the emulators' source and from how the games behaved in the tests. The delay was not measured with a camera.

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

**Linking two cabinets** works for Club Kart: European Session (`clubk2k3`). It was tested on 1 November 2026 with the cabinet's Flycast as the server and Flycast 2.7 on a Windows PC as the client, on the wired network. The link is UDP on port 37391. The options go on the command line (`-config`) or in `emu.cfg`, section `[network]`: `network:Enable=yes` on all of them, `network:ActAsServer=yes` on the first one, and on the others `network:ActAsServer=no` and `network:server=IP-of-the-first`. Start the server first. Also set `network:EnableUPnP=no`: without it Flycast asks the router, and so the Internet, to open the port. The server shows a dialog, "Waiting for players" with a Start Now button. The client showed "CHECKING NETWORK NOW, MODE: SLAVE, SEQUENCE: SYNCING", and a few seconds later the attract mode. Two Flycast on one machine do not work, because both want port 37391. Initial D Arcade Stage Ver. 3 (`initdv3e`) and Ferrari F355 Challenge (`f355`) were started the same way, with two Flycast on the cabinet (the second in a network namespace): the server logged "Waiting for slave connections" and then "Master starting: 1 slaves", and each side sent 3 UDP packets. What the games showed was not seen, so they are not in the frontend. Not tested: a race with two players, and a third machine (reports say Club Kart takes two). The F355 "twin" sets are the ones made for a battle cable between two cabinets.

**Net play (rollback)** is another thing: the Flycast of FliperOS has GGPO options (`network:GGPO`, `network:GGPODelay`, `network:ActAsServer`, `network:server`) for NAOMI and Atomiswave games, on UDP port 19713. **Both machines need `network:server`, the server too.** In Flycast's source (`core/network/ggpo.cpp`) each side sends to the address in `network:server` (empty means 127.0.0.1) and takes packets only from it, and `network:ActAsServer` only chooses the local port (19713) and the player (1). The first try, with KOF Neo Wave (Atomiswave) between the cabinet's Flycast and Flycast 2.7 on a Windows PC, left `network:server` empty on the cabinet, so the cabinet sent to itself and ignored the PC: the PC sent 96 packets in 90 seconds, got no answer and stayed on "Starting network". With the right options, two Flycast of the cabinet's own build did link (KOF Neo Wave, the second one in a network namespace of the cabinet): about 35 UDP packets a second each way for a minute, where the failed try had 2 a second in one direction. The try with Flycast 2.7 on the PC was not repeated, and the screen of the game was not captured, so what the game showed is not seen. The frontend now starts GGPO for NAOMI and Atomiswave games: see Flycast GGPO under Net play.

**Which sets have a network board.** The romset of MAME 0.289 marks these NAOMI sets, among others: `f355`, `f355twin`, `f355twn2` (Ferrari F355 Challenge), `initd`, `initdexp`, `initdv2j`, `initdv3e`, `initdv3j`, `inidv3cy` (Initial D), `clubk2k3`, `clubkcyc`, `clubkprz`, `clubkpzb`, `clubkrt` (Club Kart), `18wheelr`, `crzytaxi` and `vstrik3`. All of them were downloaded to the cabinet on 1 November 2026 with the Downloader's Flycast filter (the "Everything that works" preset, all control types), but only Club Kart, Initial D Ver. 3 and F355 were started as a pair so far.

The Derby Owners Club, World Club Champion Football and Mushiking sets are online and card games, and were not tried.

## Party play: more players than controls

Some games have more players than a cabinet has controls: X-Men has four players, and FBNeo runs it. For these, a party lets cabinets on the local network share one game, through RetroArch's net play. There is no emulator link and no NVRAM per cabinet: every machine runs the same game, and the inputs travel over the network.

**Which games get it:**

- **Every RetroArch core that does net play**, in its own folder (`~/roms/retroarch/<core>`), for a game with more players than this cabinet has controls. A core does net play when its `.info` file says `savestate_features = "deterministic"`, which is what RetroArch itself asks for: in the image that is FBNeo, Snes9x, Genesis Plus GX, FCEUmm, mGBA and PCSX ReARMed. A core installed later counts too. The game needs its number of players in the list (the MAME ones come with it; a console game gets it from the scraper, or from Classify in the frontend).
- **FBNeo uses its own folder only**: `~/roms/retroarch/fbneo`, with FBNeo's own romset, and only the sets FBNeo knows. The MAME romset in `~/roms/mame` is not used for it, even for a game that has the same name in both: FBNeo checks each file by its CRC, and some sets of MAME 0.289 have dumps that FBNeo does not take.
- **NAOMI, NAOMI 2 and Atomiswave games in Flycast**, through Flycast's GGPO, for any game of two or more players: up to four players (the four controller ports) on two to four cabinets, each cabinet with as many players as it has controls. Guilty Gear Isuka's four players can be 2+2, 2+1+1 or 1+1+1+1. See Flycast GGPO below.
- **GameCube and Wii games in Dolphin** (`~/roms/dolphin`), for any game of two or more players: two to four cabinets, one player each. See Dolphin net play below.

Every cabinet of the party needs the same game file.

In the frontend such a game has a **PARTY PLAY** tile in its menu, with a row of player icons. The lit ones are the players this cabinet takes. The other cabinets see **JOIN PARTY**, with the name of the cabinet that opened it.

**Each cabinet takes as many players as it has controls configured** (see [Controls](Controls.md)), so two cabinets with two controls fill the four players of X-Men. To give fewer (two controls, but only one person playing), press down on the PARTY PLAY or JOIN PARTY tile: blinking arrows appear beside the player icons, and left or right picks how many this cabinet gives. Up goes back to the tiles.

**In a RetroArch party nobody waits.** The cabinet that opens it goes into the game after the three-second count, alone, and the others join the game while it runs: JOIN PARTY copies the game if it is missing and opens it at once, connected to the first cabinet, on the first free players. A cabinet that closes its game frees its players for the next one. The party ends when the first cabinet closes the game. Flycast's GGPO and Dolphin need every cabinet at the start, so their parties still wait in the room: GGPO starts when the second cabinet joins, Dolphin when every player has an owner or the first cabinet presses START.

Only the network cable is used. The public lobby, the relay and the NAT traversal of RetroArch are off, and so are the UPnP of Flycast and Dolphin and Dolphin's traversal server. The party's own ports are UDP 55436 (who plays what), TCP 55437 (the party) and TCP 55438 (the game's files). RetroArch's net play is on TCP 55435, Flycast's GGPO on UDP 19713, Dolphin's net play on TCP 2626.

**Run the same release on every cabinet.** RetroArch warns when two machines run different versions. When the builds of the core differ, it turns the desync check off, so a real desync would not be reported.

Tested on 1 November 2026: the frontend of the cabinet hosted X-Men with players 1 and 2, and a Windows PC joined with two RetroArch windows, one player each (players 3 and 4), with a ping of 13 to 18 ms. The coin, start and character selection of each player showed on that player, the same on the cabinet and on both windows. RetroArch 1.22.2 for Windows (the stable build) crashed when it connected; the nightly build worked. Not tested: two people playing a whole credit, and any core other than FBNeo.

### Flycast GGPO

The frontend opens Flycast with `network:GGPO=yes`, `network:GGPODelay=0` and `network:EnableUPnP=no`. The cabinet that opened the party has `network:ActAsServer=yes` and is player 1. **Both have `network:server` set to the other cabinet's IP**: Flycast sends only to that address and takes packets only from it, so an empty one (the loopback) never links. Two Flycast of the cabinet's own build linked this way (see the Flycast section). A party started from the frontend has not been tried yet.

**More than two players.** Flycast's own GGPO has two players, one on each machine, and reads only the first controller of each. The GGPO library under it takes up to four players but only one local player per machine. So FliperOS patches Flycast (`packaging/patches/flycast/0002-ggpo-party-of-up-to-four.patch`) to make **each cabinet one GGPO player that sends all its controllers in one input**. The frontend adds three options:

- `network:GGPOPeers`: the IPs of the cabinets of the party, in order, separated by `;`;
- `network:GGPOPlayerNum`: this cabinet's place in that list;
- `network:GGPOSlots`: how many controllers each cabinet plays, in the same order.

The controller ports go to the cabinets in that order: with `2;1;1`, ports 1 and 2 are the first cabinet's two controllers, port 3 the second cabinet's and port 4 the third's. Each cabinet's own controllers stay its controllers 1, 2... A party says it is protocol 3 in GGPO's check, so a Flycast without the patch refuses it instead of losing the sync. Without `GGPOPeers` Flycast runs its own two-player session, unchanged. The frontend offers the bigger party only when the installed Flycast has the patch (it looks for `GGPOPeers` in the binary); an older one gets the party of two, one player each.

**The network every millisecond.** Flycast gave GGPO the network only once a frame, and sent each frame's input a frame late. On the cable, where a round trip takes under 1 ms, GGPO measured 20 to 110 ms of ping (median 22 ms in a 16-minute session between the cabinet and a PC). That ping decides how far ahead each side may run, so the cabinet ran about 3 frames ahead of the PC, predicted 4 to 7 frames of the PC's input (GGPO stalls at 8), paused 161 times to wait for it, and had a frame of 34 ms or more in 83% of the seconds. The third patch (`0003-ggpo-network-every-millisecond.patch`) adds a thread that reads and sends GGPO's packets every millisecond, apart from the frames; rollbacks stay in the frame. With it, two Flycast on one PC measured 1 to 3 ms of ping.

**Within a frame of each other.** With the right ping the cabinet still ran 4 to 5 frames ahead of the PC: its clock (the CRT mode Switchres makes, a little over 60 Hz) runs faster than the PC monitor's, and GGPO only corrected a gap of 3 frames or more, checking every 4 seconds, with Flycast waiting one frame per correction. So the cabinet saw the PC player's moves about 80 ms late. The fourth patch (`0004-ggpo-keep-machines-within-a-frame.patch`) corrects from one frame and checks every second: the machines stay 0 to 1 frame apart. Each correction is still a one-frame wait on the machine ahead, and there are as many as before (that is the real difference of the two clocks); between two cabinets in the same CRT mode they are rare.

There is no faster network protocol to switch to: GGPO already sends each input in one UDP packet, and on the cable a round trip takes under 1 ms. What made the party slow was inside the emulator (the network read once a frame, the drift corrected late), not the cable. For a party with no prediction at all, `network:GGPODelay=1` delays every player's input by one frame (about 17 ms) and leaves nothing to roll back on a cable; FliperOS keeps 0, so your own controls answer at once.

Like the rest of the party, it is for a wired local network: no relay, no UPnP. The patch makes the GGPO input bigger (32 bytes per player instead of 9) and the input packets bigger (up to 1 KB, under the network cable's MTU).

Tested on 7 November 2026 with three patched Flycast on one PC, each one a cabinet on its own port of the loopback, playing Guilty Gear Isuka (Atomiswave) in a 2+1+1 party: all three ran the game in one GGPO session. A Lua script coined on each one's own controllers (the first cabinet on its second controller, the second once, the third twice), and all three screens showed the credits 0, 1, 1 and 2: each controller reached its port on every machine.

Then, on 6 November 2026, between the owner's cabinet and a PC: the cabinet's frontend hosted the party and the PC joined it with the frontend's own protocol, running the patched Flycast in Docker (software video, through a UDP bridge on Windows so the cabinet always saw the PC's port 19713). The session ran for minutes on both, with about 60 packets a second each way and no disconnection. In one party the cabinet gave 2 players and in the other 1, and the PC's scripted coins, starts and moves landed on ports 3-4 and then 2-3, as each plan said; the person at the cabinet played player 1 against them. The cabinet showed short, light stutters. The likely cause is the PC side, not the patch: a Flycast drawing on the CPU in Docker, behind a bridge in PowerShell, with a ping of 19 to 41 ms, makes GGPO roll back several frames and slow the faster machine down to wait for it. Not tried yet between two cabinets on the cable.

### Dolphin net play

Dolphin opens net play only from its windows, so FliperOS builds it with a patch (`config/dolphin-patches`) that adds two command-line options: `--netplay host` or `--netplay join`, and `--netplay_players N`. The cabinet that opened the party hosts and starts the game by itself when the N cabinets of the party have it. The others connect to it, and retry for 20 seconds while it opens.

The address, port and nickname go in with `-C Dolphin.NetPlay.*`: direct connection (no traversal server), no UPnP, TCP port 2626, buffer 2. Dolphin is opened with `-b`, so it closes when the game ends or the connection drops, and the frontend comes back.

Each cabinet plays with its controller 1, in the order the cabinets joined: the host is player 1. The frontend offers it only when the installed Dolphin has the patch (the ISO build applies it); an older Dolphin gets no PARTY PLAY tile.

### Latency of net play

**Your own controls are as fast as playing alone**, except in Dolphin (below). RetroArch's net play and Flycast's GGPO are both rollback: each cabinet runs the game at once with its own controls and guesses the others' (it repeats their last input). When the real input arrives and differs, it loads the state of a few frames back and runs those frames again, in one frame.

FliperOS sets no input delay (`netplay_input_latency_frames_min` and `_range` are 0 in RetroArch, `GGPODelay` is 0 in Flycast). On the cable the other cabinet's input arrives in a fraction of a frame, so a rollback is rare and is one frame long at most. You see the other players' moves within a frame. The ping that RetroArch shows (13 to 18 ms in the test) counts its own handling, not just the cable, where the round trip is under 1 ms.

**Dolphin has no rollback.** Every cabinet waits for everyone's input of the same frame, with a buffer that holds a few inputs ahead. FliperOS sets the buffer to 2 (Dolphin's default is 5): about one frame of delay on your own controls too, the same for everyone. If the game stutters, the buffer is too small for that network.

**Run-ahead is off during net play.** RetroArch does not run run-ahead or preemptive frames while net play is on. A latency mode that uses them loses that gain in a party.

**Every cabinet runs at the speed of the slowest.** Use the same video mode on all of them: a CRT whose refresh is a little slower holds the others back.

### Cores and emulators with net play

**The frontend offers net play with every RetroArch core marked "deterministic", with Flycast's GGPO and with Dolphin.** A RetroArch core needs a state that it saves and loads quickly and always the same way. A core that cannot do that refuses net play, or loses the sync. Only FBNeo has been played between two machines so far: the others are in the frontend but not yet tested on FliperOS.

| Core or emulator | Systems | Net play | Checked |
| --- | --- | --- | --- |
| FBNeo (RetroArch) | Arcade: CPS1, CPS2, CPS3, Neo Geo, Konami, Toaplan and the rest of its list | **Yes, in the frontend** | **Tested**: X-Men, cabinet and PC |
| Snes9x (RetroArch) | Super Nintendo | **Yes, in the frontend** | Its .info; not tested |
| Genesis Plus GX (RetroArch) | Mega Drive, Master System, Game Gear, Sega CD | **Yes, in the frontend** | Its .info; not tested |
| FCEUmm (RetroArch) | NES, Famicom Disk System | **Yes, in the frontend** | Its .info; not tested |
| mGBA (RetroArch) | Game Boy Advance | **Yes, in the frontend** (one screen shared, not the link cable) | Its .info; not tested |
| PCSX ReARMed (RetroArch) | PlayStation | **Yes, in the frontend**, but heavier and loses the sync more easily | Its .info; not tested |
| MAME 2010 (RetroArch) | Arcade (MAME 0.139) | **No**: "Core does not support netplay" | **Tested** |
| MAME, current core (RetroArch) | Arcade (MAME 0.289) | Yes, but many drivers do not save their state well. Not in the image (415 MB) | Connected once (X-Men) |
| Flycast | NAOMI, NAOMI 2, Atomiswave | **Yes, in the frontend**: GGPO rollback, up to four players on two to four cabinets (FliperOS patch) | Two Flycast linked on the cabinet by hand, game screen not seen |
| Dolphin | GameCube, Wii | **Yes, in the frontend** (FliperOS patch): two to four cabinets, one player each; input delay, no rollback | Patched build compiled; not played between two machines |
| GroovyMAME, Supermodel, SM2-Emu | Arcade, Model 3, Model 2 | **No net play.** Their network is the board link of the link games above | Source |
| PCSX2, DuckStation, Hypseus Singe, OpenBOR | PS2, PS1, Laserdisc, beat 'em ups | **No** | Source |

Fightcade 2 has its own rollback (FBNeo, Flycast and others), but over the Internet with its own matchmaking: it is not part of the cabinets' link or net play.

## What cannot be linked

MAME marks 309 sets (107 games) as having a network or serial link that is not emulated: Namco's Ridge Racer, Final Lap, Cyber Cycles and Alpine Racer 2 and others, Konami's GTI Club, Midnight Run, Racing Jam and Thrill Drive, Taito's Battle Gear and Chase Bombers, Midway's Cruis'n Exotica and Atari's Road Riot 4WD. No MAME code reads the link options for them, so there is nothing to turn on.

The Model 3 boards in MAME (and the NAOMI ones that share the same board) and the Chihiro network board are stubs. The Konami network PCBs and the Namco C139 serial chip are stubs too.

Gaelco's Speed Up, Surf Planet, Radikal Bikers and Football Power link through shared memory between two instances, and only if MAME is rebuilt with a source switch. The normal build cannot do it.

## How this was checked

Between 31 October and 1 November 2026. The emulators were GroovyMAME gm0289sr222f (MAME 0.289), SM2-Emu 0.9.56, and Supermodel 0.3a at the same commit as the cabinet's (1481545). The Daytona link ran with one instance in a window on a PC and the other on the cabinet's CRT. The Tournament Battle (four instances) and the Supermodel games (Scud Race and Daytona USA 2 in pairs and in fours, Dirt Devils in a pair) ran all on the PC. The net play ran with the cabinet and the PC.

The "Source" rows and the lists of boards come from MAME 0.289's source and its game list (`mame -listxml`).
