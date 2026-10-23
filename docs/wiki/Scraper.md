**Setup > Games > Scraper** has three items: **Scrape the games**, **Scraper provider** and **Art packs by torrent**.

**Scraper provider** picks where the art and the information come from, and keeps the account of the providers that ask for one, the way ES-DE and Arcadeflow keep the ScreenScraper login in their options:

| Provider | Has | Account |
|---|---|---|
| ScreenScraper | every system | user and password, optional (a free account raises the daily limits) |
| TheGamesDB | consoles and computers | none |
| ArcadeDB | arcade games | none |
| progetto-SNAPS | arcade screenshots only | none |
| MobyGames | every system | your API key, required |
| IGDB | consoles and computers | a Twitch client ID and secret, required |
| OpenRetro | Amiga and old computers | none |

The choice is saved in `fliperos.conf` (`scraper_source`) and the account in `/etc/fliperos/scraper-accounts`, a file only root reads; it is what Skyscraper gets in `-u`. A provider that only works with an account doesn't scrape until it has one.

**Art packs by torrent** brings logos and videos from torrents, without an account and without the per-day limits of the providers. The screen comes filled with packs from the Internet Archive: logos and videos for MAME (also used by the RetroArch arcade cores), Naomi and Naomi 2, Atomiswave, Model 2 and Model 3.

Each pack belongs to some folders of `~/roms`, and it **only downloads when those folders have ROMs**, and only the files of the games that are in them: the torrent's file list is compared with the names of the ROMs, and the rest of the torrent is never downloaded. A game that already has that art in `~/media` is skipped.

Where a pack keeps the files inside `.zip` archives by letter (the MAME videos), only the archives of the letters your games start with are downloaded, and only your games' files come out of them.

The download is done by the same Transmission service as the [Downloader](ROMs.md), in the background, even with a game open; when a torrent ends, each file goes to `~/media/logo/<games folder>` or `~/media/preview/<games folder>` with the name of the ROM, and the torrent is removed.

**Add a torrent** takes a pack of your own (a magnet link or the address of a `.torrent`, the kind of art and the folder it is for), and the link of a pack that comes filled in can be changed. The packs are in `config/fliperos-media-torrents` and the program is `/opt/fliperos/bin/fliperos-mediapacks`.

**Scrape the games** — covers, screenshots, logos, videos and information for each ROM, with **Skyscraper** (the same one GroovyArcade packages), from the one chosen in Scraper provider.

**What to fetch** is a checklist: screenshots (`snap`), logos, covers (`box`), marquees, descriptions (`texto`) and videos (`preview`, unchecked at first: they take much more space).

Skyscraper only downloads the checked types (`--flags noscreenshots,nocovers,nowheels,nomarquees` and `videos`) and only exports those; the choice is remembered. An artwork type the folder didn't have yet makes it fetch again the games already in the cache (`--refresh`): without that Skyscraper doesn't go back to them.

The folders with games (each one's `_info.txt` doesn't count) that FliperOS knows how to open are included: `~/roms/mame`, `dreamcast`, `ps2`, `dolphin` and the RetroArch core folders (`~/roms/retroarch/<core>`, by the platform of the `systemid` in the core's `.info`).

Artwork and text go to **`~/media/<type>/<system>`** ([ROMs, BIOS and artwork](ROMs.md)): Skyscraper writes each type into a subfolder with a fixed name (`screenshots`, `covers`, `wheels`, `marquees`, `videos`), and for it `~/media/.skyscraper/<system>` has links with those names to `snap`, `box`, `logo`, `marquee` and `preview`; the descriptions come out of the generated list into `~/media/texto`.

The list goes to the frontend. With **GroovyMAME** as the default launcher, the MAME folder only gets the artwork: `mame.ini` and `ui.ini` already look in `~/media/<type>/arcade` (the first `snapshot_directory` is still F12's).

In **ES-DE** (FliperOS's EmulationStation) the list goes to `~/ES-DE/gamelists/<system>` (Skyscraper's `esde` format, relative paths) and `MediaDirectory` is `~/media/.es-de`, with one link per ES-DE type (`screenshots`, `covers`, `marquees` = logo, `videos`) into `~/media`.

Earlier artwork (`~/.mame/scraped/mame`, `~/.attract/scraped/<folder>`, `<ROM folder>/media`) moves to `~/media` in `tools/cabinet-update.sh` and when the folder is scraped.

The images come out each one as it came (screenshot, cover, logo, marquee; the Setup's `artwork.xml`), and not composited on top of each other as in Skyscraper's default.

**Clones**: in the MAME folder the Setup asks whether to also fetch the clones of the existing games (`groovymame -listclones`: mvscu, mvscj...), which in a merged romset are inside the parent's zip and have no file — the scraped folder becomes one of references in `~/.cache/fliperos-scraper` (links to the ROMs and a small file per clone).

**Resuming**: Skyscraper only writes its cache at the end of each run, so the games go in batches of 20 (`--includefrom`) and the work is recorded in `/var/lib/fliperos/scraper` (the folders still to do, the files of each one already saved, the source and the account, readable by root only); if the machine was switched off or the Setup closed midway, Setup > Games > Scraper offers to resume from the batch where it stopped.

In **Attract-Mode Plus** (the default launcher's, or with no frontend chosen, if it is installed) the Setup creates, like GroovyArcade's `efc.sh`, any missing emulator in `~/.attract/emulators` — with the command that opens the game (`fliperos-x11-run groovymame [name]`, `fliperos-kms-run retroarch -L <core>`, `fliperos-x11-run flycast/pcsx2/dolphin-emu`) and the artwork in `~/media/<type>/<system>` — and its display in `attract.cfg` (AdvanceMenu theme); Skyscraper writes the romlist to `~/.attract/romlists` and the descriptions to `~/.attract/scraper/<emulator>/overview`, a link to `~/media/texto/<system>`.

In Pegasus, `metadata.pegasus.txt` lives in the ROM folder itself, pointing to the artwork in `~/media`. What already exists (a display, an emulator changed in Attract-Mode) isn't rewritten — the emulator created by the Setup is redone, so the artwork moves to `~/media` —, and a system that fails doesn't stop the others.

**progetto-SNAPS** (no account) is one of the providers, for the arcade folders only (MAME, Naomi, Atomiswave...): the in-game screenshots of [progetto-SNAPS](https://www.progettosnaps.net/snapshots/) by AntoPISA, the same set GroovyArcade users know.

`/opt/fliperos/bin/fliperos-snaps` follows the site's guidelines: the pack names come from its Snapshots page and each pack goes through its download link, one at a time; the monthly update (`pS_snap_upd_N.zip`) wins over the full set (`pS_snap_fullset_N.zip`, about 520 MB, with the images in a 7z).

The packs stay in `/var/cache/fliperos/snaps` (about 1 GB with the 7z unpacked), so scraping another folder later downloads nothing again, and a newer version replaces the older one.

Only the screenshots of the games in the folder are copied, to `~/media/snap/<games folder>` (`~/media/snap/mame`); one that is already there stays.

The site doesn't host logos, covers or descriptions, so those still come from the other sources; the Attract-Mode Plus romlist and the ES-DE/Pegasus lists are refreshed the same way.
