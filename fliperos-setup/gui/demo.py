# Telas de demonstracao: os menus do Setup com dados falsos, para ver a
# interface sem um FliperOS instalado (--demo NOME). Os rotulos e as dicas
# sao os de fliperos-setup/screens/.

from widgets import Capture, Input, LayoutEdit, Menu, Message, Progress, YesNo, layout_tile

CONTEXT = {"version": "0.9.1", "status": "192.168.1.155 - 42%"}


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
        ("joysticks", "Joysticks", "Button mapping, layouts, light guns and wheels."),
        ("games", "Games", "Frontend, emulators, folders, downloader and scraper."),
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


SCREENS = {
    "main": main, "live": live, "setup": setup, "video": video, "monitor": monitor,
    "emulators": emulators, "power": power, "poweroff": poweroff, "install": install,
    "error": error, "wifi": wifi, "joysticks": joysticks, "players": players,
    "capture": capture, "layout": layout, "layoutedit": layoutedit,
}
# A escolha de um menu que abre outra tela de demonstracao.
LINKS = {"games": "emulators", "frontend": "error", "network": "wifi", "shutdown": "power",
         "buttons": "players", "2": "capture", "3": "layoutedit"}
