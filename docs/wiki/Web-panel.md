**The cabinet from your phone or PC.** Open **http://fliperos.local** in a browser on the same network (or the cabinet's IP) and sign in with the `fliperos` user. There is nothing to install on the phone or the computer.

What you can do from the couch:

- **Pick a game and play it** on the tube, with the pictures, the history and the buttons of each arcade game from the Arcade Database, your favourites and the game filters.
- **See what is playing**, with the FPS, and take a screenshot of the tube.
- **Watch the cabinet live** in the browser, and put the live screen and the game's marquee in OBS.
- **Change settings while you play**: colour, 480i hacks, services, latency mode, volume.
- **Copy games, BIOS and artwork** through the browser: upload, download, new folders.
- **Filter a MAME romset** and **download** only the games that suit your cabinet, plus the **BIOS** your games lack.
- **Scrape the art** of your games, typing the site's login on a real keyboard, and download the art packs.
- **Install or update emulators and extras** that don't come in the image.
- **Check the system**: the video mode with its modeline, CPU, GPU, temperatures, network and logs.
- **Open a terminal** on the cabinet, without an SSH program.

## Page by page

The cabinet's state in a browser on the same network (a phone too): **http://fliperos.local**, or the cabinet's IP. Port 80 only forwards to the panel's own port, 8081, so `http://fliperos.local:8081` works too.

You sign in with the same user and password as SSH and the network share (`fliperos`, changed in **Setup > System > Password**). Until 2026-10-22 the panel was on port 8080, which Pixelcade's own settings page also uses; with both installed one of them didn't open.

The panel has ten pages, tabs at the top, each with its own address (`#frontend`, `#live`, `#romfilter`, `#downloads`, `#scraper`, `#install`, `#files`, `#settings`, `#status`, `#terminal`); the browser remembers the last one:
- **Frontend:** now playing with the FPS, games, volume and screen;
- **Live:** the cabinet screen live, the streaming controls (service, encoder, sound) and the addresses for OBS (the live screen and the marquee). Leaving the page stops the stream, so ffmpeg on the cabinet stops too;
- **ROM filter:** the MAME ROM Cleaner filter, for the Downloader or for a romset folder;
- **Downloads:** the Downloader, Download BIOS and the tasks;
- **Scraper:** the art of the games, from the FliperOS scraper or a site, and the art packs by torrent;
- **Install:** the emulators and the extras, installed or updated;
- **Files:** files and tasks;
- **Settings:** colour values are sliders;
- **Status:** now playing and the screen at the top, then video, the marquee preview, CPU, GPU, memory, storage, network, processes and logs;
- **Terminal.**

The status refreshes every second. What each part shows:
- **Now playing:** the game open (emulator, file, RetroArch core) and the frontend, with the **FPS** and a graph of the last minute. The FPS comes from the OpenGL layer of the flicker filter, which counts the frames of whatever game is open, and for games in Vulkan (Flycast, PCSX2, Dolphin, DuckStation on amdgpu) from a small implicit Vulkan layer (`config/fliperos-vkfps.c`, on with `FLIPEROS_VK_FPS=1`) that counts their frames the same way. The minute of history stays in the browser.

The browser never keeps the panel: its pages, code, icons and fonts are sent with `Cache-Control: no-store`, so every visit gets the version on the cabinet, right after an update. The games' pictures and videos are checked each time (`no-cache` with an ETag), so new art from a scrape shows at once.
- **Video:** what Video Setup asks (monitor, frequency, resolution, connector, orientation) next to what is on screen now: the mode, the horizontal kHz and vertical Hz, interlaced or progressive, and the full **modeline** of each active output, read from DRM by `fliperos-video-check`.
- **CPU:** the total, each core and the load, plus the temperatures of the sensors.
- **GPU:** the name and the driver, plus whatever the card reports: use, VRAM, clock, temperature, power.
- **Memory, disks and network:** the speed of each interface, its IPs and the Wi-Fi signal.
- **Volume**, which can also be changed from here (`fliperos-setup --volume up|down|mute|get|set N`).
- **Processes:** the ones using the most CPU.
- **Logs:** those of `/opt/fliperos/logs`, the Setup's and the updates'.
- **Games:** the folders with games, the same ones the frontends show (`fliperos-setup --systems`).
  - The list is Attract-Mode Plus's (`~/.attract/romlists/EMULATOR.txt`), so arcade games show their real names, year and manufacturer from AttractPlus ROM List. Clones without their own file in a merged MAME set are listed too, since MAME opens them by name.

    Files the list doesn't know (copied after it was made, or a folder without a list) show by file name. An arcade list made by AttractPlus ROM List leaves out the BIOS files.
  - At the end of the search box is the **filter**: FliperOS's own game filters (All Games, Most Played, the genres, manufacturers and years), the same set the Setup writes into each Attract-Mode display (`fliperos-setup --filters`), plus *Favourites*.
  - Next to it, the **Clones** button. Off (the default), the list shows only the original games: a clone is hidden when its original game is in the list (a clone left without its original stays, and so do favourites and the most played). On, every version shows. The choice is remembered in the browser.

    They are applied the way Attract-Mode applies them: the rules in order, exceptions, the regular expressions, sorting and the limit. The panel copies these filters; it doesn't read the frontend's displays, so a later frontend of FliperOS's own can use the same ones.
  - Each game opens like an accordion, one at a time. It shows what the list knows (file, year, manufacturer, genre, players, buttons, control, screen, emulation status, parent, how many times and how long it was played) and what the internet knows:
    - arcade games: the [Arcade Database](https://adb.arcadeitalia.net) by the set name.

      That adds the full title, series, rating, the player 1 buttons drawn on the panel where Setup > Joysticks > Buttons layout puts them (colour and function, no joystick directions), the game's description and then each section of the arcade-history.com text (Technical, Trivia...), the in-game, title, marquee, flyer and cabinet pictures, and links to the video and the game's page.

      The browser can't ask the Arcade Database directly (it sends no CORS header), so the panel asks for it.

      The answer is **saved on the cabinet**, next to the other media: `~/media/info/<games folder>/<set>.<language>.json` (`~/media/info/mame/samsho.en.json`). A game fetched once is never fetched again and opens without internet, and FliperOS's own frontend will read the same file. The page says when it was saved. A game the Arcade Database doesn't know is asked again after 30 days;
    - consoles: the box, screen and title pictures of [libretro-thumbnails](https://github.com/libretro-thumbnails), by the file name (No-Intro), the way RetroArch looks for them.
  - The browser keeps each game's answer for 30 days (`localStorage`), so opening it again is instant and works offline. When the storage is full, the older half goes.
  - At the end are **Play** and **Favourite**. Play closes what is on the cabinet screen and opens the game; when the game closes, what was there comes back (the frontend, the desktop or the menu). Favourite keeps FliperOS's own favourites, in `~/.config/fliperos/favourites` (one `folder<TAB>name` line per game).

    The first time the panel lists games, it copies Attract-Mode's favourites into that file (`romlists/EMULATOR.tag`). After that it never writes to the frontend's file, and changes made in the frontend no longer come in.
  - **Close the game**, in *Now playing*, closes the open game (`SIGTERM`, like the power button, so RetroArch still writes its saves).
  - Naomi, Naomi 2 and Atomiswave may all point to one folder with the whole Flycast romset. AttractPlus ROM List then keeps only each system's games in its list, by the BIOS in each set's `romof` chain (`awbios` is Atomiswave, `naomi2` is Naomi 2, `naomi` and the GD-ROM BIOS are Naomi). Lists made before this split are redone the next time the frontend opens.

  How it works: the panel writes the request to `$XDG_RUNTIME_DIR/fliperos-web-launch` (the first line is what comes back afterwards, the rest is the command), then closes the game, the frontend, the desktop or the Setup menu. `fliperos-tty1` opens the request before the menu and after each session.

  A newer request comes first, so switching from one game to another works. `fliperos-session` does not start the desktop's X again while a request is waiting. With only the desktop on screen, it takes the same path as the desktop's Games menu (`fliperos-next`).

  Only commands that start with `fliperos-kms-run` or `fliperos-x11-run` are opened, and only files of that folder.
- **Screen:** a screenshot of what is on the cabinet screen, shown in 4:3 as on the tube or at the frame's own size (a 2560x240 frame of RetroArch's super resolution is very wide), with *Save PNG*. Games, frontends and the Setup's graphical menu go through the OpenGL layer of the flicker filter.

  When the panel asks (`$XDG_RUNTIME_DIR/fliperos-shot-request`), the layer reads the next finished frame, before the filter, into `fliperos-shot.ppm`, and the panel turns it into a PNG. The LXDE desktop draws without OpenGL, so it is read from X (`XGetImage`). The text console and programs without OpenGL have no screenshot.
- **Live screen:** what is on the tube, live, in the browser. It covers the game, the frontend, the menu, the desktop and the text console, with sound when *Live screen sound* is on. Pick 15, 30 or 60 frames per second. The card shows the size, the frame rate and the delay in the browser's buffer, and has *Sound* (it starts muted, as browsers ask) and *Full screen*.
  - It is installed and turned on by the **first boot** of the installed system. When that couldn't download it (no internet), install it in **Setup > Games > Extras > Live screen** (or with *Install* on the card): ffmpeg from apt and [go2rtc](https://github.com/AlexxIT/go2rtc) (MIT, a pinned version checked by sha256). Then it is a service in Setup > System > Services (*Live screen*, after boot by default).
  - How it works: go2rtc (`fliperos-stream.service`) opens ffmpeg only while someone watches. ffmpeg reads the screen from DRM (`kmsgrab`) and encodes H.264.
    - **Video:** On AMD cards (radeon and amdgpu) the driver does not let the screen's buffer be mapped into memory, so the frame goes through VA-API's video processing, which copies and scales it on the card; the R7 240 has that part even without an encoder.

      Cards that allow the mapping read it directly (`hwdownload`). ffmpeg runs with `libfliperos-dropmaster.so` (`LD_PRELOAD`, `config/fliperos-dropmaster.c`): opening `/dev/dri/cardN` at a moment when nobody owns the screen made it the DRM master.

      Then X and the Setup's graphical menu could no longer open the video: the cabinet stayed on the text menu and the desktop failed with "exit code 1" (seen on 2026-10-22). The library gives the screen back right after the open. kmsgrab doesn't need it: as root it reads the buffers with `CAP_SYS_ADMIN`.

      Without the library the capture doesn't start. Encoding runs on the graphics card (VA-API) when it has an encoder; otherwise in software with x264, ultrafast, no B-frames, a keyframe every second. The R7 240 has no encoder: its Oland chip has no VCE. On the cabinet (an i7 870) x264 keeps 60 frames per second.
    - **Mode changes:** kmsgrab stops when the framebuffer changes size ("framebuffer dimensions changed"), which happens every time a game opens or closes on a 15 kHz screen. go2rtc doesn't restart the capture for someone already watching, so the viewer kept the frontend's last frame (seen on 2026-10-23).

      So the capture is two processes. The grabber (`fliperos-stream grab`) runs kmsgrab in a loop, reopening it at the new size, and always outputs raw 640x480 RGB. The encoder reads that pipe with wall-clock timestamps and never stops, so a mode change costs about a second of frozen picture with the sound still in sync.
    - **Size:** never larger than 640x480. The frame is copied in RGB and scaled with nearest-neighbour to 640x480 (4:3) before it is encoded: 640x240 doubles each line, 480i stays as it is, and RetroArch's 2560x240 drops to a quarter across.

      The panel and the OBS page draw each frame on a 640x480 canvas, which the browser enlarges without smoothing (`image-rendering: pixelated`). Chrome and OBS always smooth a `<video>` when they enlarge it, and ignore that property on it.
    - **Bitrate and network:** 1.5 Mbit/s at 15 fps, 2 at 30 and 3 at 60, with half a second of buffer, so a keyframe is as sharp as the other frames. WebRTC goes over TCP only (`listen: ":8555/tcp"`).

      Over UDP, the cabinet's USB Wi-Fi lost packets, and go2rtc cannot ask ffmpeg for a new keyframe, so each loss froze the picture until the next keyframe. Measured on 2026-10-23: at 8 Mbit/s over UDP, 321 lost packets and 8.6 s frozen in 20 s.

      Over TCP at 640x480, Chrome on a wired PC got 60 fps for 60 s with no loss and no freeze, with the cabinet on Wi-Fi. A two-frame buffer also hid the loss, but made each keyframe blurry.

      The Live page shows the cabinet's network (the interface of the default route) and recommends a network cable instead of Wi-Fi, highlighted when the cabinet is on Wi-Fi.
  - The browser sends its WebRTC offer to the panel (`/api/stream/offer`), so the panel login applies. The panel passes it to go2rtc, whose API and RTSP only listen on the cabinet itself (`127.0.0.1`). The video then goes straight to the browser on the local network, on port 8555 (TCP and UDP), with no STUN server outside.
  - **In OBS:** the card also has an address for a Browser Source (`/overlay/live?key=…&fps=…`, the same key as the marquee page). It shows the screen in 4:3, as on the tube, plays the sound (tick *Control audio via OBS*) and reconnects by itself. `&fit=fill` stretches it to any size; `&muted=1` drops the sound.
  - **Delay for OBS:** while the stream plays on the page, a tip balloon under the OBS steps shows how many milliseconds to delay the camera (its source: Filters > Render Delay) and the microphone (Advanced Audio Properties > Sync Offset) so that they line up with the game.

    The figure is measured from the browser's last second of WebRTC stats: buffer and decode time, half the round trip, and the cabinet side (about two frames of capture and encoding; for the sound, the loopback period and the Opus frame).

    Chrome delays the picture to match the sound, so both settle on about the same value, roughly 300 ms on the cabinet over Wi-Fi. The stream starts with sound on; if the browser refuses, it starts muted and the button shows it.
  - **Live screen sound** (Settings and the Setup, off by default) is **experimental, and on the cabinet it doesn't work yet**: the live screen goes without sound. The idea is a copy of everything that plays on an ALSA loopback.
    - `snd-aloop` loads as the card `FliperOSLoop`, on the kernel's default timer.
    - `asound.conf` gets `fliperos_tee`, a route over a multi that feeds a `dmix` on the card and one on the loopback, both with the same format and timing. The volume leveler goes in front when it is on.
    - ffmpeg records the loopback's capture side in Opus.
    - Turning it on tests the `default` with a tenth of a second of silence. If it doesn't play, the setting goes back off by itself, and the game sound stays as it was. On the cabinet's HDA card it doesn't play while another program holds the card through the system's `dmix`.
    - The copy only goes into `asound.conf` with the loopback really there. Each session start also checks this: without the loopback the `default` would not open and everything would be silent.
- <a id="marquee-for-obs"></a>**Marquee for OBS:** with *Turn on the marquee page* (or *Marquee overlay for OBS* in Settings), the marquee of the game on screen becomes a page for an OBS Browser Source, `/overlay/marquee?key=…`. It needs no Pixelcade or ZeDMD.
  - The card links to [Scoreboard games](Scoreboard-games.md) in this documentation: the games with the versus scoreboard and which emulator has each (GroovyMAME, RetroArch with FBNeo, SM2-Emu for Model 2).
  - The page has a transparent background. It shows the game's art, the same as the ZeDMD uses: `~/media/dmd`, `marquee` or `logo` (Pixelcade's art may only be used on its own hardware). Without art it shows the name.

    The opening text (the high scores, or "Now Playing") scrolls once, achievements pop up and the versus score shows each side's name and wins. `&led=1` draws it as LED dots and `&text=0` leaves out the texts. In OBS: width 1280, height 320.
  - **Marquee preview mode:** in **System > Status**, the *Marquee preview* card has a switch and a list with **Pixelcade** or **ZeDMD**. With it on, the panel draws an LED marquee (128 columns of dots for the Pixelcade, 256 for the ZeDMD) with what that device would show for the game that is open, with no hardware: in the card, under the screen in **Live**, in place of the preview of the page in **Live > OBS > Marquee**, and in the marquee of the cabinet drawing in **Frontend**. The ZeDMD looks for `~/media/dmd`, then `marquee`, then `logo`; the Pixelcade for `marquee`, then `logo`; without art, the game's name. The preview also shows the scoreboard, like the OBS page: the versus score in place of the art, the opening text (the high scores) scrolling once and the achievements. That needs the marquee state, which `fliperos-pixelcade` only writes with *Marquee overlay for OBS* on, so turning the preview on turns it on too. Turning it on also downloads the Fightcade score detectors in the background (they used to come only with the Pixelcade or ZeDMD install, so without that hardware no game had a score). The score only works for a game opened after that: GroovyMAME turns the score plugin on when the game starts. *When both exist, the marquee shows* (**Art** or **Scoreboard**, in the Status card and, with the preview on, in the **Frontend** page next to the cabinet) picks what the preview draws when a game has both: with Art the score, the scrolling text and the achievements stay out. Only games with a score detector have one (see [Scoreboard games](Scoreboard-games.md)); the others just show the art. The choice of device and of art or score stays in the browser.
  - How it works: `fliperos-pixelcade`, which already gets every event (kms-run, x11-run, GroovyMAME, the Attract-Mode Plus plugin and the ES-DE scripts, installed when the page is turned on), writes the current marquee to `$XDG_RUNTIME_DIR/fliperos-marquee`. The page asks the panel for it every second; the art comes from `fliperos-dmd art`.
  - The OBS pages can't sign in, so their address carries a key, created on first use in `/etc/fliperos/overlay.key` (root only). *New address* makes another key and the old address stops working, the live screen's and the controller's included. The key only opens the marquee state, the current game's picture, the live screen and the controller.
- <a id="controller-for-obs"></a>**Controller for OBS:** the player's controller on the stream, `/overlay/input?key=…`. Its own page, with the OBS steps and CSS examples: [Controller on the stream](Controller-overlay.md). The stick and the six buttons (1 2 3 on top, 4 5 6 below), Start and Coin light up while they are pressed on the cabinet.
  - It reads the controls of Setup > Joysticks > Button mapping (`/etc/fliperos/buttons.map`): the joysticks through SDL and a keyboard encoder's keys straight from the input devices, without taking them from the game. With no mapping, it uses MAME's default keys for players 1 and 2.
  - `&players=2` or `&players=1,2` picks the players. In OBS: width 800, height 400 for one player, 1600 × 400 for two. The background is transparent.
  - The card has a CSS editor with syntax colours. The preview follows each key you type, and *Demo in the preview* presses the buttons by itself, so the look can be tried with nobody at the cabinet. *Format* lays the CSS out with one property per line (Ctrl+Z undoes it). *Save* writes it to `/etc/fliperos/input-overlay.css`, and the pages open in OBS take it at once, with no need to refresh the source; *Factory CSS* goes back to `input.css`.
  - The classes: `.pad` (`.p1`, `.p2`, `.active` while something is pressed), `.label`, `.stick` (`.up` `.down` `.left` `.right`, and `data-dir` such as `up-left`) with `.gate` and `.ball`, and `.button` (`.b1` to `.b6`, `.start`, `.coin`; `.on` while pressed). The sizes use `--u`: one panel is 200 × 100 `--u`.
  - How it works: while at least one controller page is open, the panel runs one `fliperos-buttons watch` at low priority. It sends the panel a line each time the pressed controls change, and the panel passes it to the pages as Server-Sent Events. It stops when the last page closes.
- **Settings:** the Setup settings that are safe to change over the network, grouped as System, Services, 480i hacks and Colour.
  - System: the default launcher, latency mode, debug mode, the volume leveler and menu sounds.
  - Services: the whole services table.
  - 480i hacks: a card per program, with an explanation of each method at the top. The method is a row of buttons (640x240, 480i with filter, 480i pure), and the filter strength (light, medium, strong) shows only when the filter is on.
  - Colour: every colour calibration value and **Back to the defaults**. A slider saves while it moves, so the game on screen changes with it; the **−** and **+** on its sides move it one step per tap (a run of taps saves once, just after the last).
  - Each change is saved and applied at once, through the same functions as the Setup screens (`fliperos-setup --settings` and `--setting KEY VALUE`, `lib/system.sh`). Debug and latency rewrite the kernel line the way their screens do; their kernel part counts after a restart.
  - Monitor, resolution and video driver are not here, since a wrong choice can leave the cabinet without a picture. They stay in the Setup, on the cabinet screen.
- <a id="lab-mode"></a>**Lab mode** (on the Settings page, and in **Setup > System > Lab mode**): a temporary internet address to this panel, so someone far away can help you (a FliperOS developer looking at a problem).
  - *Turn on lab mode* gives an address like `https://some-random-words.trycloudflare.com/lab?key=…`. *Copy* puts it on the clipboard, to send by chat or email. In the Setup it shows on the screen.
  - Whoever opens it gets into the panel without your password: status, logs, files, screenshots, and a **root** terminal (`su - fliperos` there gives the normal user). Send it only to someone you trust.
  - It ends by itself after 4 hours, when the cabinet powers off, or with *Turn off*. Then the address and every session opened with it stop working. A new start gives a new address.
  - Nothing changes on your router. The cabinet opens the connection to Cloudflare, through a [Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) of `cloudflared` (no account). It is downloaded the first time, about 40 MB, with a fixed version and checksum, to `/opt/fliperos/cloudflared`.
  - If the web panel is off in Services, lab mode starts it until the next boot.
  - The live screen doesn't work through the address. Its video goes straight to the browser on the local network.
  - How it works: `fliperos-lab start` writes a random key to `/run/fliperos-lab` and starts `fliperos-lab.service`, which runs `cloudflared` as a temporary user with `RuntimeMaxSec=4h`. The address comes from cloudflared's `/quicktunnel` metrics. The panel's `/lab?key=` compares the key; wrong keys have their own limit of 5 a minute.
- **Downloads:** the Setup's Downloader (Setup > Games > Downloader), which takes from the MAME ROM and CHD torrents only what the MAME ROM Cleaner filter picks.
  - The panel shows the progress and the filter that is chosen.
  - It adds a torrent's link (the one that comes with FliperOS, or one you paste), applies the filter and starts, and removes a torrent (optionally with what it already downloaded).
  - The filter itself is chosen on the ROM filter page or in the Setup. Starting from the panel deletes nothing; deleting what a changed filter leaves out stays a Setup step.
  - It goes through the Setup's own functions (`fliperos-setup --downloader status|add|start|remove`, `lib/downloader.sh`).
- **Download BIOS** (on the Downloads page): the same as **Setup > Games > Downloader > Download BIOS**.
  - It shows the last check (downloaded, already there, not in the pack, failed) and the list by state. The BIOS that failed or are not in the pack open first, since they ask for something from you.
  - *Check now* runs the check as a task. *Check, reading the pack again* reads the BIOS pack's list again first. The box turns the automatic check off or on; that check runs each time the cabinet menu opens.
  - It goes through `fliperos-setup --bios status|list|check [--refresh]|auto on|off` (`lib/downloader.sh`).
- **Scraper:** the same as **Setup > Games > Scraper**.
  - The page says what each kind of folder gets, since arcade has much more art. The folders come in two groups, **Arcade** (MAME sets) and **Consoles**.
  - Pick the folders (none picked means all). *Scrape the games* is the FliperOS scraper: what each game lacks, like the frontend does by itself, with no account. An arcade folder gets the description, screenshot, flyer, marquee and logo from the Arcade Database. A console folder gets only the screenshot and the box art from libretro-thumbnails; logos, videos and descriptions of console games come from a site (ScreenScraper covers every system).
  - *Scrape with a site* is Skyscraper. Each provider shows what it covers: every system (ScreenScraper, MobyGames), arcade only (ArcadeDB; progetto-SNAPS, only screenshots) or consoles and computers (TheGamesDB, IGDB, OpenRetro). Pick the provider, type its account (user and password, the API key, or the client ID and secret), mark what to fetch and, with a MAME folder, the clones. The account is easier to type here than with the joystick.

    The account goes to the Setup through standard input, never on a command line or in a log, and the saved password never comes back to the page. A scrape that stopped before the end (a power off) can be resumed here or in the Setup.
  - *Art packs by torrent* puts every pack with ROMs to download, as in the Setup, and shows its progress. The packs are arcade only: logos and videos of MAME, RetroArch's arcade cores, Naomi, Atomiswave, Model 2 and Model 3.
  - It goes through `fliperos-setup --scraper status|sources|systems|source|account|media|scrape|site|resume` (`lib/scraper.sh`) and `--mediapacks auto|status`.
- **Install:** **Setup > Games > Emulators & Games** and **Extras**.
  - Each emulator shows whether it is installed and its version. *Check for an update* asks GitHub for the newest one. Those that come in the image update with FliperOS, so they have no button.
  - *Install* or *Update* runs as a task. Only one installation runs at a time, the live screen's included.
  - KOF Final Attack is downloaded from itch.io; installing it from a copy of the original game stays a Setup step. An installed Pixelcade also takes the code of the paid art pack.
  - It runs `fliperos-emulators`, `fliperos-extras` and `fliperos-pixelcade`, the same programs as the Setup.
- **ROM filter:** the filter of the MAME ROM Cleaner (Setup > Games > Cleaner), with the same parameters, options and presets as the Setup's screen, which come from the Setup itself (`fliperos-setup --romfilter`, `lib/romclean.sh`).
  - It has two uses. *Downloader filter*: what the Downloader takes from the ROM and CHD torrents; it opens with the saved filter, and *Save* records it as Setup > Games > Downloader > Filter does. *Clean a romset folder*: a folder with a romset (a disk, a USB drive, the network folder mounted by the Setup), chosen in a folder list.
  - Pick the emulator (the MAME version of the romset: GroovyMAME, Flycast, SM2-Emu, Supermodel, MAME 2010) and a preset. The emulator of a romset folder is guessed from its name, as in the Setup.
  - The parameters are a board of tiles in groups (which games, players and controls, screen, categories and years, hardware), like the Setup's graphical filter board. Each tile shows its value with a small drawing: players and buttons lit up to the limit, the emulation lamps, a switch, the marked blocks.

    A pink dot marks a value changed from the preset or the saved filter. A yes/no tile switches with a click; the others open their options in a dialog, one choice or chips for several, with a search box on long lists such as the categories.
  - The scoreboard (GAMES and SIZE) stays in view while scrolling and counts what passes after every change: on the ROM torrent's list for the Downloader, on the folder for a romset. Only the latest count is kept; a new one stops the one before it.
  - For a folder, *Preview* shows what goes where (sets, size, parents, BIOS and devices, free space) and the list. *Copy them*, or *Move them* from a folder that can be written to, runs as a task with its progress. Deleting what is left over after a move stays a Setup step.
- **Tasks:** what takes minutes (reading a torrent's link, applying the filter, scraping, checking the BIOS, installing) runs in the background. The card is on the Downloads, Scraper, Install and Files pages, and when a task ends, its card refreshes by itself.
  - Each task shows the step and the percentage from the Setup's progress events, and has a log and *Cancel*.
  - Only one task of each kind runs at a time, and the last 20 stay listed.
- **Trackball** (off for now: the card is hidden and `/api/trackball` answers 404 unless the service has `FLIPEROS_WEB_TRACKBALL=1`): the phone as the cabinet's mouse, for trackball and spinner games (MAME reads the mouse for them), frontends and the desktop.
  - Roll with a finger on the pad. After a quick flick the ball keeps rolling and slows down by itself, like an arcade trackball, and a touch stops it.
  - There are three big buttons and a sensitivity slider; a mouse wheel on the pad also scrolls.
  - The panel creates a virtual USB mouse in `/dev/uinput` ("FliperOS web trackball": X, Y, wheel and three buttons) the first time it is used. It stays while the panel runs. The page sends the movement over a WebSocket (`/api/trackball`) once per screen frame.
  - A button that is held when the connection drops is released.
- **Terminal:** the cabinet's shell in the browser, as the `fliperos` user, with its own zsh and the window's size: the same as SSH, without a program on the computer.
  - It is a login shell in a pseudo-terminal (`setsid -c`, so Ctrl+C and job control work). `~/.zprofile` only starts the tty1 flow on `/dev/tty1`, so the shell opens normally. The shell runs at normal priority, not the service's `Nice=15`.
  - The page talks to it over a WebSocket (`/api/terminal`). Only the panel's own page can open it (the `Origin` must be the panel's address), and only after the login.
  - The screen is drawn by [xterm.js](https://xtermjs.org) 5.5.0 with its fit addon (MIT, `config/web/xterm-LICENSE.txt`). It ships inside the panel and loads only when the terminal opens.
- **Files:** the folders `~/roms`, `~/bios`, `~/media`, `~/nvram`, `~/save` and `~/splashscreen`. You can open folders (inside one, the `..` folder at the top of the list goes back up), download a file, and upload several files with their progress (also by dropping them on the list). You can also create a folder and delete a file or an empty folder.
  - An upload is written to a hidden `.part` file in the same folder and renamed at the end, so a cut upload doesn't leave a broken game under the right name.
  - A file that already exists is only replaced after you confirm.
  - What you send belongs to the `fliperos` user.
  - Nothing outside those folders is reachable (no `..`, no absolute paths), but links inside them work (a games folder on an external disk). The folder at the top is never deleted.

It is a service in **Setup > System > Services** (*Web panel*). By default it is **After boot**, so it starts about 15 s after the menu, frontend or game opens at boot.

`config/fliperos-web` (installed as `/opt/fliperos/bin/fliperos-web`, the `fliperos-web.service` unit) uses only Python's standard library, on port 8081 (`--port` changes it; 8080 is Pixelcade's own settings page).

It runs as root to read DRM and to check the password in `/etc/shadow` through libcrypt, the same way the login does. Only the `fliperos` user signs in. The session is an `HttpOnly`, `SameSite=Strict` cookie that lasts 12 hours.

Every `POST` asks for the `X-FliperOS: 1` header, which a form on another site cannot send, and five wrong passwords in a minute lock that address for a minute. The page is plain HTTP, so the password crosses the network unencrypted: use it on a network you trust.

The page is in English, or in Portuguese with a Portuguese browser; the button at the top switches.

The JSON API is the same one the page uses, so it also serves scripts: `POST /api/login {"user","password"}`, then `GET /api/status` (all of it), `/api/logs`, `/api/log?name=NAME&lines=N` and `POST /api/volume {"action":"up"|"down"|"mute"}` or `{"set":0..100}`, `GET /api/systems`, `GET /api/games?system=KEY` (the romlist fields, `Favourite`, `PlayedCount`, `PlayedTime`, and the `filters`), `GET /api/gameinfo?system=&game=`, `POST /api/favourite {"system","game","on":true|false}`, `POST /api/launch {"system","game"}` (the set name or the file), `POST /api/close`, `GET /api/files?root=roms&path=FOLDER`, `GET /api/download?root=&path=`, `POST /api/upload?root=&path=&name=` (the body is the file; `&overwrite=1` replaces), `POST /api/mkdir {"root","path","name"}`, `POST /api/delete {"root","path"}`, `GET /api/settings`, `POST /api/settings {"key","value"}`, `GET /api/downloader`, `POST /api/downloader` (`{"action":"add","kind":"roms"|"chds","magnet"}`, `{"action":"start"}` or `{"action":"remove","kind","delete"}`), `GET /api/romfilter?target=&folder=` (the parameters, presets and saved Downloader filter), `POST /api/romfilter/count`, `/save`, `/scan` and `/run` (`{"target","folder","values":{KEY:VALUE},"preset"|"transfer"}`), `GET /api/dirs?path=`, `GET /api/stream`, `POST /api/stream/offer {"fps":15|30|60,"sdp"}` (the SDP answer), `POST /api/stream/install`, `GET /api/overlay` and `POST /api/overlay {"action":"newkey"}`, and without login, by the key: `GET /overlay/marquee?key=`, `/overlay/live?key=`, `/api/overlay/state?key=`, `/api/overlay/art?key=&id=` and `POST /api/overlay/offer?key=`, `GET /api/tasks`, `GET /api/task?id=N` (with the log), `POST /api/task/cancel {"id":N}`, `GET /api/screenshot` (a PNG) and `GET /api/terminal` (a WebSocket: binary frames are the keys and the screen, a text frame `{"resize":[columns,rows]}` sets the size) and `GET /api/trackball` (a WebSocket of text frames `{"m":[dx,dy],"w":wheel}` and `{"b":["left"|"right"|"middle",1|0]}`).
