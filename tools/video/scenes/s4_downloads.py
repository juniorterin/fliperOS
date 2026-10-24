# Cena 4: baixar jogos (o filtro do romset, o link, o download) e as BIOS.

GAMES = [
    ("emulators", "Emulators & Games", "What is installed, and install what is not in the image."),
    ("frontend", "Frontend", "The game list that starts when the computer turns on."),
    ("extras", "Extras", "Wine, Steam, Heroic, Pixelcade, ZeDMD and game output tools."),
    ("custom", "Custom games", "PC games, scripts and your own emulators, as frontend systems."),
    ("folders", "Folders", "Where ROMs, BIOS and art are; use an external disk instead."),
    ("downloader", "Downloader", "MAME ROM/CHD sets by torrent and free homebrew games."),
    ("cleaner", "Cleaner", "Filter a MAME romset: only the games you want, per emulator."),
    ("scraper", "Scraper", "Download covers, screenshots, logos and videos of the games."),
    ("return", "Return", "Back to Setup."),
]
DOWNLOADER = [
    ("torrent", "ROM/CHD MAME torrent", "Only the games your filter picks, from a romset torrent."),
    ("freeroms", "Free games (open-source homebrew)", "So the frontends have something to show."),
    ("biospack", "Download BIOS", "The BIOS your games lack, also checked when the menu opens."),
    ("return", "Return", "Back to Games."),
]


def script(R):
    R.ctx["status"] = "192.168.1.155 - 9%"
    R.bg("smoke")
    R.push(W.Menu("Games", GAMES, "emulators"), 1.6)
    R.keys("right right right right right", 0.45)
    R.key("enter", 0.3)
    R.push(W.Menu("Downloader", DOWNLOADER, "torrent", "Games downloaded straight to the emulator folders."), 1.6)
    R.key("enter", 0.3)
    torrent = demo.torrent()
    R.push(torrent, 1.2)
    R.keys("left left left left", 0.4)
    R.key("enter", 0.3)
    # O filtro: a tabua de quadros, o placar de jogos e tamanho.
    board = demo.romfilter(0)
    R.push(board, 1.6)
    R.keys("right right right right right right", 0.4)
    R.key("enter", 0.3)
    R.push(demo.filterplayers(), 0.8)
    R.keys("left right", 0.5)
    R.key("enter", 0.3)
    R.pop(0.5)
    R.keys("right right", 0.45)
    R.key("enter", 0.3)
    R.push(demo.filtercontrols(), 0.8)
    R.keys("right enter right right enter", 0.45)
    R.key("esc", 0.3)
    R.pop(0.4)
    R.keys("down down", 0.5)
    R.wait(0.8)
    R.pop(0.4)
    # O link do romset
    R.key("right", 0.4)
    R.key("enter", 0.3)
    link = W.Input("ROM set link", ["Paste or type the magnet link of the", "MAME ROM set:"], "",
                   action=("browser", "OPEN THE BROWSER",
                           "Find the romset on the web, copy its magnet link and close the browser: "
                           "the link comes back here."))
    R.push(link, 0.6)
    R.type("value", "magnet:?xt=urn:btih:9f3c0a71e5b84d2c6a17d0e2b45f8a3391c7de60", 0.035, 0.7)
    R.pop(0.4)
    R.keys("right right right", 0.45)
    R.key("enter", 0.3)
    # O download, em segundo plano
    dl = W.Download("Downloader", [("ROMS", "0 MB", "9.6 GB", 3, 0.0), ("CHDS", "NOT STARTED", "", 0, 0.0)],
                    0, "--", "--")
    R.push(dl, 0.4)
    total = 9.6 * 1024
    for f in range(int(9 * 30)):
        frac = min(1.0, f / (9 * 30) * 0.42)
        mb = total * frac
        speed = 2.1 + 0.6 * ((f // 15) % 3) / 2
        dl.parts = [("ROMS", "%.1f GB" % (mb / 1024) if mb > 1024 else "%d MB" % mb, "9.6 GB", 9 + (f // 30) % 7, frac),
                    ("CHDS", "NOT STARTED", "", 0, 0.0)]
        dl.pct = int(frac * 100)
        dl.speed = "%.1f MB/s" % speed
        left = (total - mb) / speed / 60
        dl.left = "%d h %02d min" % (left // 60, left % 60)
        R.wait(1 / 30)
    R.wait(0.6)
    R.pop()
    R.pop(0.3)
    # Download BIOS
    R.replace(W.Menu("Downloader", DOWNLOADER, "biospack", "Games downloaded straight to the emulator folders."),
              0.9)
    R.key("enter", 0.3)
    live = W.Live("Download BIOS", "The BIOS the games in ~/roms need, from the BIOS pack", 0, "Checking the folders",
                  "Each file is checked by its hash.", [])
    R.push(live, 0.5)
    files = ["neogeo.zip (MAME, Neo Geo)", "naomi.zip (Naomi)", "awbios.zip (Atomiswave)", "naomi2.zip (Naomi 2)",
             "scph5501.bin (PlayStation)", "dc_boot.bin (Dreamcast)", "ps2-0230a-20080220.bin (PS2)"]
    msgs = []
    for i, name in enumerate(files):
        live.step = "Downloading %d of %d" % (i + 1, len(files))
        msgs.append(name + " - OK")
        for f in range(16):
            live.pct = int((i + f / 16) * 100 / len(files))
            live.msgs = msgs[-3:]
            R.wait(1 / 30)
    live.pct, live.step = 100, "7 BIOS downloaded, every game has its BIOS"
    R.wait(2.0)
    R.pop(0.3)
