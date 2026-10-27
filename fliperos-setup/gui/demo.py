# Telas de demonstracao: os menus do Setup com dados falsos, para ver a
# interface sem um FliperOS instalado (--demo NOME). Os rotulos e as dicas
# sao os de fliperos-setup/screens/.

from widgets import (Capture, Download, FilterBoard, GunResult, GunTarget, Input, LayoutEdit, Menu, Message,
                     Progress, Stepper, ToggleGrid, YesNo, control_art,
                     layout_tile)

CONTEXT = {"version": "0.14", "status": "192.168.1.155 - 42%"}


def main():
    return Menu("FliperOS", [
        ("frontend", "Start frontend", "Open the game list (the frontend chosen in Setup)."),
        ("setup", "Setup", "Video, audio, network, controls, games and system."),
        ("desktop", "Start desktop", "The LXDE desktop, for a mouse and a keyboard."),
        ("shell", "Exit to shell", "The command line. Type fliperos-menu to come back."),
        ("power", "Shutdown / Reboot", "Power off or restart the computer."),
    ], "frontend")


def live():
    return Menu("FliperOS Setup", [
        ("install", "Install to HD/SSD", "Copy FliperOS to a disk of this computer."),
        ("recovery", "Recovery Mode", "Repair a FliperOS that is already installed."),
        ("terminal", "Terminal", "The command line of the install media."),
        ("shutdown", "Shutdown", "Power off or restart the computer."),
    ], "install")


def setup():
    return Menu("Setup", [
        ("video", "Video Setup", "Monitor type, orientation, resolution and geometry."),
        ("audio", "Audio Setup", "Sound card, volume and the menu sounds."),
        ("network", "Network Setup", "Wi-Fi networks and the network status."),
        ("games", "Games", "Frontend, emulators, folders, downloader and scraper."),
        ("joysticks", "Joysticks", "Button mapping, layouts, light guns and wheels."),
        ("system", "System", "Extras, latency, updates and the splash screen."),
        ("return", "Return", "Back to the FliperOS menu."),
    ], "video")


def video():
    return Menu("Video Setup", [
        ("monitor", "Monitor Type", "The kind of CRT: its horizontal frequency range."),
        ("orientation", "Monitor Orientation", "Horizontal or vertical (rotated) screen."),
        ("resolution", "Resolution", "The video mode of the menus and the frontend."),
        ("geometry", "Geometry", "Center and size the picture on the tube."),
        ("reset", "Reset Geometry", "Back to the geometry of the monitor type."),
        ("outputs", "Multiple Monitors", "Which video outputs are on."),
        ("return", "Return"),
    ], "monitor")


def monitor():
    return Menu("Monitor Type", [
        ("generic_15", "Generic 15 kHz"),
        ("arcade_15", "Arcade 15 kHz"),
        ("arcade_15_25", "Arcade 15/25 kHz"),
        ("arcade_15_25_31", "Arcade 15/25/31 kHz"),
        ("ntsc", "NTSC TV"),
        ("pal", "PAL TV"),
        ("pc_31_120", "PC monitor 31 kHz"),
        ("vesa_480", "VESA 640x480"),
        ("vesa_600", "VESA 800x600"),
        ("custom", "Custom ranges"),
    ], "arcade_15", "The monitor connected to this computer:", mode="radio", marked=["arcade_15"])


def emulators():
    return Menu("Emulators & Games", [
        ("retroarch", "RetroArch"),
        ("groovymame", "GroovyMAME"),
        ("flycast", "Flycast"),
        ("pcsx2", "PCSX2"),
        ("sm2emu", "SM2-Emu (Model 2)"),
        ("hypseus", "Hypseus Singe"),
        ("openbor", "OpenBOR"),
        ("fightcade", "Fightcade 2"),
    ], "flycast", "Mark what to install:", mode="check", marked=["retroarch", "groovymame", "flycast"])


def power():
    return Menu("Shutdown / Reboot", [
        ("poweroff", "Power off"),
        ("reboot", "Reboot"),
        ("return", "Return"),
    ], "poweroff")


def poweroff():
    return YesNo("Power off", ["Really power off the computer?"], "no")


def install():
    return Progress("Installing FliperOS", [
        ("Partition the disk", "done"),
        ("Copy the system", "done"),
        ("Install the bootloader", "run"),
        ("Create the user", "todo"),
        ("Finish", "todo"),
    ], 58, "Limine: writing the EFI entry")


def error():
    return Message("Start frontend", [
        "Attract-Mode Plus is not installed.",
        "",
        "Choose another one in Setup > Games > Frontend.",
    ], "error")


def wifi():
    return Input("Wi-Fi password", ["Password of the network FliperNet:"], "arcade1994", password=True)


def joysticks():
    return Menu("Joysticks", [
        ("buttons", "Button mapping", "Teach FliperOS the panel: press each control when asked."),
        ("layout", "Buttons layout", "Where the buttons of 1 to 5-button games go on the panel."),
        ("guncon", "GunCon 2", "Shoot the targets so the gun hits where it points."),
        ("axes", "Wheel / analog", "Set the range and the center of each axis."),
        ("lpt", "LPT joysticks", "Arcade sticks and console pads wired to the parallel port."),
        ("quirks", "Quirks", "Kernel fixes for a USB encoder read wrong, as one player."),
        ("return", "Return", "Back to Setup."),
    ], "buttons")


def players():
    return Menu("Button mapping", [
        ("1", "1 player"), ("2", "2 players"), ("3", "3 players"), ("4", "4 players"),
        ("return", "Return"),
    ], "2", "Map the panel for all emulators, one player at a time. How many players?")


def capture():
    return Capture("Button mapping", 1, "b3", ["up", "down", "left", "right", "b1", "b2"], 7, 12, 5)


# O layout de cada numero de botoes: a posicao (1 a 6) de cada botao do jogo.
LAYOUTS = {"1": [1], "2": [1, 2], "3": [4, 5, 6], "4": [1, 2, 4, 5], "5": [1, 2, 3, 4, 5]}


def layout():
    return Menu("Buttons layout", [
        (count, "%s-button games" % count) for count in LAYOUTS
    ] + [("return", "Return")], "3",
        "Where the buttons of a game go on the panel, by how many buttons the game uses.",
        tiles={count: layout_tile(order) for count, order in LAYOUTS.items()})


def layoutedit():
    return LayoutEdit("Buttons layout", 3, [4])


def guncon():
    return YesNo("GunCon 2", [
        "The screen turns white with a target in each corner. Aim at the + of each "
        "target and pull the trigger 3 times; then one shot in the center checks the result.",
    ], "yes", "START", "CANCEL", icon="guncon")


def guntarget1():
    return GunTarget(1, 3, "top-left", 3, 1, "Shot 1 of 3: x=182 y=47")


def guntarget2():
    return GunTarget(2, 3, "bottom-right", 3, 2, "Shot 2 of 3: x=655 y=221")


def guntarget3():
    return GunTarget(3, 3, "center", 1, 0)


def gunresult():
    return GunResult("GunCon 2", (49, 52))


def downloads():
    return Menu("Downloader", [
        ("torrent", "MAME torrent", "Only the games your filter picks, from a romset torrent."),
        ("freeroms", "Free games", "Open-source homebrew, so the frontends have something to show."),
        ("return", "Return", "Back to Games."),
    ], "torrent", "Games straight to the emulator folders")


def torrent():
    return Menu("MAME torrent", [
        ("filter", "Filter", "Arcade classics, for GroovyMAME 0.289."),
        ("roms", "ROM set link", "Required. Now: MAME 0.289 ROMs (merged)."),
        ("chds", "CHD set link", "Optional. Now: not set."),
        ("dest", "Download folder", "The games go to ~/roms/mame."),
        ("start", "Start", "Download the games the filter picks: 1,284 games, 9.6 GB."),
        ("return", "Return", "Back to the Downloader."),
    ], "start", "STATUS: READY, NOT STARTED")


def magnet(focus=0):
    return Input("ROM set link", ["Paste or type the magnet link of the", "MAME ROM set:"],
                 "magnet:?xt=urn:btih:9f3c0a71e5b84d2c6a17d0e2b45f8a3391c7de60",
                 action=[("browser", "WEB BROWSER",
                          "Find the romset on the web, copy its magnet link and close the browser: "
                          "the link comes back here."),
                         ("file", ".TORRENT FILE",
                          "Choose a .torrent file of the ROM set on a USB disk, the network share or the home folder.")],
                 focus=focus)


def magnetbrowser():
    return magnet(1)


def wifipass():
    return Input("Wi-Fi", ["Password for Casa Terin (leave empty for an open network)"], "fliper",
                 password=True, keyboard=True)


def download():
    return Download("Downloader", [
        ("ROMS", "3.5 GB", "9.6 GB", 18, 0.37),
        ("CHDS", "1.1 GB", "24 GB", 6, 0.05),
    ], 14, "2.4 MB/s", "3 h 12 min")


KEEP, REMOVE = (True, "KEEP"), (False, "REMOVE")


def romfilter(cursor=6):
    return FilterBoard("ROM filter", [
        ("preset", "Preset", "text", "CABINET", "Start from a preset; each parameter can be changed after."),
        ("arcade", "Games", "switch", (True, "ARCADE"), "Which machines of the romset?"),
        ("status", "Emulation", "lamps", 2, "How well MAME must emulate the game."),
        ("genres", "Categories", "text", "31 OF 48", "Mark the categories to take (catver.ini)."),
        ("mature", "Adult", "switch", REMOVE, "Games marked Mature in catver.ini."),
        ("modes", "Play mode", "text", "ALL", "Mark how two or more play (nplayers.ini)."),
        ("players", "Players", "people", (2, 8), "The most players a game may have."),
        ("buttons", "Buttons", "dots", (4, 8), "The most buttons a game may use per player."),
        ("controls", "Controls", "text", "5 OF 13", "Mark what the panel has. Button-only games always pass."),
        ("orientation", "Screen", "screens", (True, False), "Mark the screen orientations to take."),
        ("lines", "Resolution", "blocks", ([1, 0, 0], "15 KHZ"),
         "Mark the resolutions. Only Low is progressive on a 15 kHz CRT."),
        ("decades", "Years", "blocks", ([0, 1, 1, 1, 0, 0], "80S-00S"), "Mark the decades to take."),
        ("clones", "Clones", "text", "BEST ONE", "Which versions of each game?"),
        ("region", "Region", "text", "WORLD", "With one version per game, the region that wins."),
        ("bootlegs", "Bootlegs", "switch", REMOVE, "Bootlegs and hacks."),
        ("prototypes", "Prototypes", "switch", REMOVE, "Prototypes, betas and location tests."),
        ("vector", "Vector", "switch", KEEP, "Vector games (Asteroids, Tempest...)."),
        ("chd", "With CHD", "switch", KEEP, "Games that need a CHD (a disk image)."),
        ("hardware", "Hardware", "text", "ANY", "Only the marked boards. None: any but Naomi and Atomiswave."),
        ("save", "Done", "action", "SAVE", "Save the filter and go back to the Downloader."),
    ], cursor, "1,284", "9.6 GB")


def romfilter2():
    return romfilter(11)


def filterplayers():
    return Stepper("Players", "The most players a game may have.", [
        ("0", "Any"), ("1", "Up to 1"), ("2", "Up to 2"), ("3", "Up to 3"), ("4", "Up to 4"),
        ("6", "Up to 6"), ("8", "Up to 8"),
    ], "2")


def filterbuttons():
    return Stepper("Buttons", "The most buttons a game may use per player.", [
        ("0", "Any"), ("1", "Up to 1"), ("2", "Up to 2"), ("3", "Up to 3"), ("4", "Up to 4"),
        ("5", "Up to 5"), ("6", "Up to 6"), ("8", "Up to 8"),
    ], "4", "dots")


def filtercontrols():
    return ToggleGrid("Controls", "Mark what the panel has. Button-only games always pass.", [
        ("joy8", "8-way joystick", ""), ("joy4", "4-way joystick", ""), ("joy2", "2-way joystick", ""),
        ("twin", "Twin sticks", ""), ("trackball", "Trackball", ""), ("spinner", "Spinner", ""),
        ("paddle", "Paddle", ""), ("positional", "Rotary joystick", ""), ("analog", "Analog stick", ""),
        ("pedal", "Pedals", ""), ("lightgun", "Light gun", ""), ("keyboard", "Keyboard", ""),
        ("mahjong", "Mahjong", ""),
    ], ["joy8", "joy4", "joy2", "trackball", "lightgun"], 5, control_art, 4)


def filteryears():
    return ToggleGrid("Years", "Mark the decades to take.", [
        ("1970", "1970s", "70s"), ("1980", "1980s", "80s"), ("1990", "1990s", "90s"),
        ("2000", "2000s", "00s"), ("2010", "2010s", "10s"), ("2020", "2020s", "20s"),
    ], ["1980", "1990", "2000"], 6, None, 2)


def extras():
    return Menu("Extras", [
        ("wine", "Wine (Fightcade 2 emulators)"),
        ("steam", "Steam (installed)"),
        ("heroic", "Heroic (GOG, Epic, Amazon)"),
        ("pixelcade", "Pixelcade (LED/LCD marquee)"),
        ("zedmd", "ZeDMD (open-source LED DMD, firmware 5.1+)"),
        ("doflinx", "DOFLinx (Pixelcade in-game effects)"),
        ("hotr", "Hook Of The Reaper (game outputs: light guns, boards)"),
        ("qmamehook", "QMamehook (game outputs: serial light guns, native)"),
        ("ledspicer", "LEDSpicer (button LEDs: Ultimarc, LED-Wiz...)"),
        ("return", "Return"),
    ], "steam", "Programs that don't come with FliperOS, to keep the download small. "
       "Installing one needs the network.")


SCREENS = {
    "main": main, "live": live, "setup": setup, "video": video, "monitor": monitor,
    "emulators": emulators, "power": power, "poweroff": poweroff, "install": install,
    "error": error, "wifi": wifi, "joysticks": joysticks, "players": players,
    "capture": capture, "layout": layout, "layoutedit": layoutedit, "guncon": guncon,
    "guntarget1": guntarget1, "guntarget2": guntarget2, "guntarget3": guntarget3,
    "gunresult": gunresult, "downloads": downloads, "torrent": torrent, "magnet": magnet,
    "magnetbrowser": magnetbrowser,
    "wifipass": wifipass,
    "download": download, "extras": extras, "romfilter": romfilter, "romfilter2": romfilter2,
    "filterplayers": filterplayers, "filterbuttons": filterbuttons,
    "filtercontrols": filtercontrols, "filteryears": filteryears,
}
# A escolha de um menu que abre outra tela de demonstracao.
LINKS = {"games": "emulators", "frontend": "error", "network": "wifi", "shutdown": "power",
         "buttons": "players", "2": "capture", "3": "layoutedit", "roms": "magnet",
         "start": "download", "filter": "romfilter", "players": "filterplayers",
         "controls": "filtercontrols", "decades": "filteryears"}
