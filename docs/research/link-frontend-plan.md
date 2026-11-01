# Link play in the FliperOS frontend: plan

A plan, not an implementation. It turns the link research (`docs/research/linked-cabinets.md`, wiki page *Linked cabinets*) into screens and a protocol for the frontend (`gui/fliperos-frontend`). The mock-ups are in `docs/research/link-frontend-mockups/`, drawn with the frontend's own font and palette (`tools/link-tests/frontend-mockups.py`).

## What was asked

1. A game that links machines, or that has more players than this cabinet has controls, shows a mark. In the list it is a dim green globe to the left of the title. In the other modes (grid, full screen) it is another mark.
2. Selecting such a game adds a second way to play: link play, shown as a globe made of green lines. If nobody is playing the game, this cabinet is the first one. The next one to come is the second, and so on.
3. A cabinet that looks at a game someone is already playing sees the globe lit, with the cabinets already in it, lit, and the free ones dim.
4. The game also offers "join the existing link": this cabinet becomes the next one if there is a free place.
5. All of this updates in real time with the other machines on the network. Cable only.
6. A game with fewer controls here than players it allows gets the same idea with a different icon: net play. The user joins another cabinet's party and picks the player slot (player 2 if the host has one control, player 3 if the game has three or more players), among the free ones.
7. The Super Street Fighter II Tournament Battle and its sets need all four machines before they start. The frontend must keep everyone in a waiting room until all are connected, and then enter together. Do the same for any other game that works like that.
8. A cabinet that has just joined the network shows, first in its lists, the games being played on other machines.
9. If the one who wants to join does not have the game, the master sends the files it needs.
10. One NVRAM per cabinet number, for each game with two or more cabinets.

## What the tests say about how link games behave

These facts decide the design. They come from the tests of 31 October to 1 November 2026.

| Fact | Where it was seen | What it means for the frontend |
| --- | --- | --- |
| Every link game waits for the other machines at start: "Network Checking" (Daytona, Scud Race, Daytona USA 2), "Checking Network" (Dirt Devils), "Terminal Check" (Tournament Battle). It does not start alone | all of them | **Every link game needs a waiting room.** The Tournament Battle is not special |
| The link is fixed when the games start. A machine that restarts does not rejoin, and the other has to restart too. A third machine joining a running game was not seen to work in any emulator | Supermodel, MAME | **No joining after the start.** The lobby closes at the start, and the game shows as "in progress, closed" to the others |
| The role is in the game's NVRAM (master, slave, car number, machine ID), and the cabinet number is part of it | all the Sega games | The launcher puts the NVRAM of the right cabinet in place before it starts the game |
| The order of start matters and differs by emulator | see the table below | The lobby, not the user, starts the machines in the right order |
| The number of cabinets is not set in the game. It is discovered when the link starts. Only the Tournament Battle (4) and Gunbuster (2) have a fixed size | MAME source, tests | A game with a flexible size needs a minimum and a maximum in its profile, and the host decides when to start |
| The machines must run at about the same speed | MAME's notes, tests | The lobby can warn when a cabinet is much slower |
| A link game still plays alone with the right NVRAM (Link ID Single, or the link off) | SM2-Emu, Supermodel | "Play" (solo) keeps working and uses a standalone NVRAM |

### Start order and sizes tested

| Game | Emulator | Order that worked | Sizes tested | Menu allows |
| --- | --- | --- | --- | --- |
| Daytona USA | SM2-Emu | master first, then the slave | 2 | cars 1 to 8 |
| Daytona USA | GroovyMAME | slave first, then the master | 2 | cars 1 to 8 |
| Scud Race | Supermodel | for 2, master first. For 4, the slaves first (last of the ring first), the master last | 2, 4 | cars 1 to 8 |
| Daytona USA 2 | Supermodel | slaves first, master last (for 2: master first also worked) | 2, 4 | cars 1 to 8 |
| Dirt Devils | Supermodel | master first | 2 (4 only formed two of four links) | machine IDs to be checked |
| Tournament Battle | GroovyMAME | the head first (empty remote host), the others in chain order | 4 | 4 |

The reason for the Supermodel order: each machine connects to the next one only after it receives the connection from the previous one. The master starts the chain, so every other machine must already be listening.

## Screens

All drawn at 320x240 and shown here at 3x.

### List: marks and the games being played elsewhere

![List](link-frontend-mockups/01-list-link-badges.png)

- The globe is to the left of the title. **Dim** when nobody is playing the game on another cabinet, **lit** (with white nodes) when someone is. The two-controller icon marks a game with more players than this cabinet has controls.
- A group at the top, "playing now elsewhere", lists what the other cabinets are playing. For each: the lit globe, the title, and the cabinets in the link as small lit and dim icons with the count. It is empty when nothing is being played, and then it takes no space.
- The right panel says "nobody is playing it" or who is.

### Grid and full screen: the mark has no title to sit next to

![Grid](link-frontend-mockups/02-grid-link-badges.png)

- In the grid the mark is a small badge in the top-left corner of the tile. A tile of a game being played also shows the cabinet icons along its bottom edge.
- In full screen the mark goes in the information line under the title, next to the players and buttons icons, with the same lit and dim states.

### Choosing how to play

New link, nobody playing it:

![New link](link-frontend-mockups/03-options-new-link.png)

Joining a link that already exists:

![Join link](link-frontend-mockups/04-options-join-link.png)

- **This window appears only when the user presses play on one of these games** (a link game, or a game with more players than this cabinet has controls). Every other game starts straight away, as it does today.
- "Play" (solo) is always first, with the play triangle. The second entry is the globe: "link play" when nobody is playing (this cabinet becomes #1, the master), "join link" when a party is waiting (this cabinet becomes the next free number).
- The cabinet icons show who is in and which place this cabinet would take. If a party is closed or full, "join" is replaced by the state and a new party can still be started.
- A game with more than one open party lists them, one line each, with the host's name.

A game with more players than this cabinet has controls gets the same window with the two-controller icon instead of the globe. Net play shows the party's slots, free or taken:

![Net play options](link-frontend-mockups/03b-options-netplay.png)

### The waiting room

![Waiting room](link-frontend-mockups/05-lobby-waiting.png)

![All here](link-frontend-mockups/06-lobby-all-here.png)

- One screen for every link game. The cabinet icons light as machines come in. Each shows its number, and "you" marks this one.
- **Fixed size** (Tournament Battle, 4; Gunbuster, 2): the party starts by itself when the last one arrives, after a short countdown.
- **Flexible size** (Daytona, Scud Race and the others, 2 to 8): the host chooses when to start. It starts by itself when the maximum is reached. Until the minimum is there, the start is not offered.
- Everyone enters together: at the start the lobby runs each machine's emulator in the right order and with the right NVRAM, and shows "starting". After that no one can join.
- B leaves the room. If the host leaves, the party closes for everyone and the others go back to the list.

### Net play

![Net play](link-frontend-mockups/07-netplay-party.png)

- For a game with more players than this cabinet's controls. The user joins another cabinet's party and takes a free slot (P2, P3 and so on). The host sees the slots fill.
- Net play uses RetroArch's netplay with an FBNeo core, and it is the only way for fighting games of two players or more to be played across cabinets. It does not link the boards: the Tournament Battle's eight-player bracket still needs its four-cabinet link.

### Missing game files

![ROM transfer](link-frontend-mockups/08-rom-transfer.png)

- If this cabinet does not have the game, the host sends the files: the zip, its parent, the BIOS, the device ROMs and the CHDs, only the ones the game needs. The cabinet checks them and then goes on to the lobby.
- The transfer is between the user's own cabinets on the cable. Nothing leaves the local network.

## How it would work

### Presence on the cable

- Each cabinet announces itself on the wired interface only, by UDP multicast, once a second: an id, the cabinet's name, the game and emulator it has open, the party id, its slot, how many places the party has and how many are used, and the state (waiting room, playing, closed). A cabinet that is silent for four seconds disappears from the others' lists.
- The frontend listens and keeps a table. The lists, the marks and the "playing elsewhere" group are drawn from it, so they change as machines come and go.
- The wireless interface is ignored. It is wired only, as asked.

### The party

- A small TCP exchange between the host and the ones who join: create, join (with the slot offered), leave, ready, start, and the files request.
- The party fixes, at the start, the number of cabinets and each one's number. From the number the launcher derives everything: the role, the car number or machine ID, the ports, and the next machine's address in the ring or chain.

### The launcher

A table of link profiles in a data file, one per game family, with: the emulator, the topology (pair, ring or chain), the minimum and maximum cabinets, the order of start, how to build the command line and the config from a cabinet number, which NVRAM file belongs to which number, and which files the game needs. This is the data the research produced.

Games that are not in the table have no link mark. Adding a game means adding a profile and its NVRAMs.

### NVRAMs

One NVRAM per cabinet number and game (`config/link-nvram`, with a README and a manifest). The launcher copies the right one into the emulator's own NVRAM folder before it starts, and puts the standalone one back for solo play. The NVRAM is named by ROM set, so each region set needs its own.

### Net play and the files

- **Net play:** the host starts RetroArch in host mode, the guest connects and asks for a player slot.
- **Files:** the host serves them over the cable (the web panel's port or a small transfer service), with a check of each file against MAME's game list, a free space check on the guest, and a resume after a drop.

## Phases

1. **Data.** The link profiles and the NVRAMs for every game with two or more cabinets. Done for part of the games.
2. **Presence and marks.** The announcements, the table, the marks in the list, the grid and the full-screen mode, and the "playing elsewhere" group.
3. **Waiting room and launcher** for the games already tested: Daytona, Scud Race, Daytona USA 2 and the Tournament Battle.
4. **Files transfer.**
5. **Net play.**
6. **More games**, after each one is tested in pairs.

Each phase is tested on the real cabinets with two machines, and on four for the games that need them.

## Open questions

- A game with a flexible size: should the host be able to start with fewer than the maximum, or always wait for the maximum? The plan lets the host start from the minimum.
- Two parties for the same game: show both, or only the first? The plan shows both.
- ROM sharing between cabinets: is it fine for the host to send files without asking the owner of the guest cabinet? The plan has the guest ask for them.
- The first cabinet is the master. If the master cabinet is the slowest, should the lobby move the role? Not planned.
- Region sets: the NVRAM depends on the set. Should the lobby refuse to link two different region sets of the same game? It needs the same ROM version on all machines, so it should.
- Dirt Devils in groups of four did not link in the tests. Until that is solved its profile says two.
