# Telas de demonstracao: os menus do Setup com dados falsos, para ver a
# interface sem um FliperOS instalado (--demo NOME). Os rotulos e as dicas
# sao os de fliperos-setup/screens/.

from widgets import (Capture, ConfirmCapture, Download, FilterBoard, GunResult, GunTarget, Input, LayoutEdit,
                     Menu, Message, PadCapture, Progress, Stepper, ToggleGrid, YesNo, control_art,
                     layout_tile, panel_tile)


def confirm():
    return ConfirmCapture("Button mapping", 3, "accept", 10)


def confirm2():
    return ConfirmCapture("Button mapping", 3, "cancel", 10)

CONTEXT = {"version": "0.24", "status": "192.168.1.155 - 42%"}


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
        ("retest", "Test the video outputs", "Run the output test again after a card change."),
        ("firmware", "Card firmware", "15 kHz from power on. Rewrites the card's BIOS: at your own risk."),
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
        ("bluetooth", "Bluetooth", "Pair, connect and forget Bluetooth controllers."),
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


def capture8():
    return Capture("Button mapping", 2, "b7", ["up", "down", "left", "right", "b1", "b2", "b3", "b4", "b5", "b6"],
                   11, 14, 6, 8, 8)


def controllers():
    return Menu("Button mapping", [
        ("0", "P1 Xbox 360 Controller"),
        ("1", "P2 Xbox 360 Controller"),
        ("2", "P3 8BitDo Ultimate 2 Wireless"),
        ("3", "-- Pro Controller"),
        ("keyboard", "Keyboard encoder (MAME default keys)"),
        ("return", "Return"),
    ], "3", "Choose a controller to map: 4 connected (P = player, -- = not mapped). Wired ones come first; "
            "Bluetooth (BT) ones take the players left, by the order they connect.", vertical=True,
        row_icons={"0": "wired", "1": "wired", "2": "wireless", "3": "wireless"})


def player():
    return Menu("Button mapping", [
        ("1", "Player 1"), ("2", "Player 2"), ("3", "Player 3"), ("4", "Player 4"), ("return", "Return"),
    ], "2", "Which player is vusb.wikidot.com V-USB Mame Panel?")


def kind():
    return Menu("Button mapping", [
        ("arcade", "Arcade stick or JAMMA panel", "A stick and 1 to 8 buttons, on an encoder or a JAMMA board."),
        ("pad", "Joypad (console controller)", "Xbox, PlayStation, Nintendo, 8BitDo...: USB or Bluetooth."),
        ("return", "Return", "Back to the controllers."),
    ], "arcade", "vusb.wikidot.com V-USB Mame Panel: what kind of controller is it?")


def panelbuttons():
    return Menu("Button mapping", [
        (str(n), "%d button%s" % (n, "s" if n > 1 else "")) for n in range(1, 9)
    ] + [("return", "Return")], "6", "How many buttons does each player have? Start and Coin do not count.",
        tiles={str(n): panel_tile(n) for n in range(1, 9)})


def padcapture():
    return PadCapture("Button mapping", 1, "b3", 11, "xbox", "Xbox Wireless Controller", {
        "b4": "b0", "b5": "b1", "b2": "b3", "b1": "b2", "start": "b7", "coin": "b6",
        "up": "h0.1", "down": "h0.4", "left": "h0.8", "right": "-"})


def padcapture2():
    return PadCapture("Button mapping", 2, "b4", 1, "generic", "", {})


def bluetooth():
    return Menu("Bluetooth", [
        ("pair", "Pair a controller", "Put it in pairing mode, then choose it in the list."),
        ("auto", "Pair controllers automatically", "For 30 s every controller in pairing mode is paired."),
        ("devices", "Paired devices (2)", "Connect, disconnect or forget a paired device."),
        ("power", "Bluetooth: on", "Turn the Bluetooth adapter off or on."),
        ("return", "Return", "Back to Joysticks."),
    ], "pair", "Adapter: hci0 (on). Paired: 2, connected: 1.")


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




def system():
    return Menu("System", [
        ("latency", "Latency", "Standard or low latency mode, and a check of this computer."),
        ("services", "Services", "SSH, network share, Wi-Fi: at boot, after boot or off."),
        ("quirks", "Quirks (USB device fixes)", "Kernel fixes for a USB device read wrong: encoders, guns, disks."),
        ("password", "Password", "The password of the fliperos user: login, SSH and network share."),
        ("update", "System Update", "Download and install the updates of all packages."),
        ("version", "FliperOS version", "Choose the update to use: an earlier one or the newest."),
        ("whatsnew", "What's new", "The changelog of each FliperOS version and the updates installed."),
        ("debug", "Debug mode (off)", "Show boot and emulator messages on screen to find a problem."),
        ("lab", "Lab mode (off)", "Remote help: a temporary internet address to this cabinet."),
        ("splash", "Splash screen", "The boot screen theme, with a preview."),
        ("return", "Return", "Back to Setup."),
    ], "debug")


def versions():
    return Menu("FliperOS version", [
        ("69", "Update 69: OSD shortcut and live line, controller hotplug", "Newer: installs the ones up to it. The newest."),
        ("68", "Update 68: Achievements on screen and in the frontend", "Newer: installs the ones up to it."),
        ("67", "Update 67: The graphical Setup menu is back", "Installed now."),
        ("66", "Update 66: The 0.24 image's level", "Earlier: undoes the ones after it."),
        ("return", "Return", "Back to System."),
    ], "67", "This cabinet is at update 67. Choose the update to use.", vertical=True)


def quirks():
    return Menu("Quirks", [
        ("0x0079:0x0006:0x0040", "Generic USB Joystick: two players (0x0079:0x0006:0x0040)"),
        ("add", "Add a quirk"),
        ("usb", "USB devices connected now"),
        ("return", "Return"),
    ], "add", "Kernel fixes for USB devices read wrong (controllers, guns, keyboards, disks). "
              "Choose a quirk to delete it. Changes apply after a restart.", vertical=True)


def axes():
    return Menu("Calibration", [
        ("/dev/input/event7", "Logitech G29 Driving Force Racing Wheel (event7)"),
        ("/dev/input/event9", "Thrustmaster T-Pedals (event9)"),
    ], "/dev/input/event7", "Which one?", vertical=True)


def padcolor():
    return Menu("Controller light", [
        ("roulette", "FliperOS (roulette, game colours)", "8BitDo: purple roulette, purple/pink rings in games."),
        ("purple", "Purple", "#7a00ff on the controller light."),
        ("pink", "Pink", "#ff0080 on the controller light."),
        ("red", "Red", "#ff0000 on the controller light."),
        ("cyan", "Cyan", "#00e0ff on the controller light."),
        ("custom", "Other colour", "Type the colour as RRGGBB (like 7a00ff)."),
        ("off", "Off", "FliperOS leaves the light as the controller sets it."),
        ("return", "Return", "Back to Joysticks."),
    ], "roulette", "Changes now: DualSense Wireless Controller, 8BitDo Ultimate 2 Wireless.")


def latency():
    return Menu("Latency", [
        ("standard", "Standard (any hardware)"),
        ("low", "Low latency (modern CPUs) - current"),
        ("check", "Check this computer"),
        ("ideal", "Recommended hardware"),
        ("return", "Return"),
    ], "low", "Mode: Low latency\nCPU: Intel Core i5-3470\nCores: 4 cores, 4 threads, 3.6 GHz\n"
              "Memory: 8 GB\nGPU: AMD Radeon R7 240 (Oland)", vertical=True)


def recovery():
    return Menu("Recovery Mode", [
        ("shell", "Open a terminal in the installed system"),
        ("bootloader", "Reinstall the bootloader"),
        ("video", "Apply this session's video settings (new video card)"),
        ("restore", "Restore system files (keeps ROMs and settings)"),
        ("return", "Return"),
    ], "bootloader", "FliperOS on sda2 (Kingston SA400S37240G): what to do?", vertical=True)


def frontend():
    reason = "Needs OpenGL 3.3 or OpenGL ES 3.0, and this video card gives OpenGL ES 2.0"
    return Menu("Frontend", [
        ("fliperos", "FliperOS frontend", "", True),
        ("attractplus", "Attract-Mode Plus", "", True),
        ("emulationstation", "EmulationStation", "Not installed. " + reason + ". Not supported", False, True),
        ("pegasus", "Pegasus", "Not installed", False),
        ("retroarch", "RetroArch", "", True),
    ], "fliperos", "Choose what starts when the computer turns on. Now: FliperOS frontend.")


SCREENS = {
    "main": main, "live": live, "setup": setup, "video": video, "monitor": monitor,
    "emulators": emulators, "power": power, "poweroff": poweroff, "install": install,
    "error": error, "wifi": wifi, "joysticks": joysticks, "players": players,
    "capture": capture, "capture8": capture8, "confirm": confirm, "confirm2": confirm2, "controllers": controllers, "player": player, "kind": kind, "panelbuttons": panelbuttons,
    "padcapture": padcapture, "padcapture2": padcapture2, "bluetooth": bluetooth, "layout": layout, "layoutedit": layoutedit, "guncon": guncon,
    "guntarget1": guntarget1, "guntarget2": guntarget2, "guntarget3": guntarget3,
    "gunresult": gunresult, "downloads": downloads, "torrent": torrent, "magnet": magnet,
    "magnetbrowser": magnetbrowser, "frontend": frontend, "system": system, "versions": versions,
    "quirks": quirks, "axes": axes, "padcolor": padcolor, "latency": latency, "recovery": recovery,
    "wifipass": wifipass,
    "download": download, "extras": extras, "romfilter": romfilter, "romfilter2": romfilter2,
    "filterplayers": filterplayers, "filterbuttons": filterbuttons,
    "filtercontrols": filtercontrols, "filteryears": filteryears,
}
# A escolha de um menu que abre outra tela de demonstracao.
LINKS = {"games": "emulators", "network": "wifi", "shutdown": "power",
         "buttons": "controllers", "0": "player", "1": "kind", "arcade": "panelbuttons", "pad": "padcapture2", "6": "capture8", "3": "layoutedit", "roms": "magnet",
         "start": "download", "filter": "romfilter", "players": "filterplayers",
         "controls": "filtercontrols", "decades": "filteryears"}
