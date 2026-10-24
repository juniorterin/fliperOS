# Cena 3b: o menu System (latencia, o que ha de novo, extras, desligar).

SYSTEM = [
    ("latency", "Latency", "Standard or low latency mode, and a check of this computer."),
    ("services", "Services", "SSH, network share, Wi-Fi: at boot, after boot or off."),
    ("quirks", "Quirks (USB device fixes)", "Kernel fixes for a USB device read wrong: encoders, guns, disks."),
    ("password", "Password", "The password of the fliperos user: login, SSH and network share."),
    ("update", "System Update", "Download and install the updates of all packages."),
    ("whatsnew", "What's new", "The changelog of each FliperOS version and the updates installed."),
    ("debug", "Debug mode (off)", "Show boot and emulator messages on screen to find a problem."),
    ("splash", "Splash screen", "The boot screen theme, with a preview."),
    ("return", "Return", "Back to Setup."),
]
WHATSNEW = """FliperOS 0.11

FliperOS has a frontend of its own, and it is the default: game lists made by FliperOS itself, a grid and a full-screen view with each game's video, and a scraper that fetches the missing art, logos, videos and info of every game by itself.

The cabinet also has a web panel at http://fliperos.local: open and close games, see the screen live with sound, change settings mid-game, manage files, the ROM filter and the downloads from a phone.

On a vertical monitor the frontend, the Setup menu, the boot screen and the terminal now stand upright.

Updates show what they change before asking to apply, and after a new version or update the menu shows what's new once.

- FliperOS frontend: list, grid and full screen, with the video of every game
- Automatic scrape: art, logo, video, description, players and buttons
- Game lists of FliperOS's own, with the real names from MAME
- GroovyMAME opens the game straight away
- Web panel: Status, Games, Files, ROM filter, Downloads, Settings, Terminal and Live
"""


def script(R):
    R.ctx["status"] = "192.168.1.155 - 9%"
    R.bg("snow")
    R.push(demo.setup(), 1.2)
    R.keys("left left", 0.5)
    R.key("enter", 0.3)
    R.push(W.Menu("System", SYSTEM, "latency"), 1.6)
    R.key("enter", 0.3)
    R.push(W.Menu("Latency", [
        ("standard", "Standard (any hardware) - current", "Polls USB at 1000 Hz, tunes GroovyMAME and RetroArch."),
        ("low", "Low latency (modern CPUs)", "Adds full kernel preemption, frame delay and preemptive frames."),
        ("check", "Check this computer", "Compares this PC with the low latency minimum."),
        ("ideal", "Recommended hardware", "What each mode asks of the PC."),
        ("return", "Return", "Back."),
    ], "standard"), 1.8)
    R.keys("right right", 0.6)
    R.key("enter", 0.3)
    R.push(W.Message("Check this computer", [
        "CPU            Intel Core i7 870",
        "Cores          4 cores, 8 threads, 2.93 GHz",
        "Instructions   x86-64-v2 (need x86-64-v3, AVX2)",
        "Memory         6 GB",
        "GPU            Radeon R7 240 (amdgpu)",
        "Analog out     VGA-1",
        "",
        "Use Standard mode, or expect stutter in low latency mode.",
    ], "info"), 4.2)
    R.pop()
    R.pop(0.4)
    R.keys("right right right right right", 0.4)
    R.key("enter", 0.3)
    pager = W.Pager("What's new", WHATSNEW, True)
    R.push(pager, 2.4)
    for _ in range(6):
        R.key("down", 0.55)
    R.wait(1.0)
    R.pop()
    R.pop(0.4)
    # Extras, pela rede
    R.keys("right right right right", 0.4)
    R.key("enter", 0.3)
    R.push(W.Menu("Games", [
        ("emulators", "Emulators & Games", "What is installed, and install what is not in the image."),
        ("frontend", "Frontend", "The game list that starts when the computer turns on."),
        ("extras", "Extras", "Wine, Steam, Heroic, Pixelcade, ZeDMD and game output tools."),
        ("return", "Return", "Back to Setup."),
    ], "emulators"), 0.9)
    R.keys("right right", 0.5)
    R.key("enter", 0.3)
    R.push(demo.extras(), 1.4)
    R.keys("down down down down", 0.55)
    R.wait(0.8)
    R.pop()
    R.pop()
    R.pop(0.3)
    # Desligar
    R.push(demo.main(), 1.0)
    R.keys("left left", 0.5)
    R.key("enter", 0.3)
    R.push(demo.power(), 1.2)
    R.key("enter", 0.3)
    R.push(demo.poweroff(), 1.6)
    R.pop()
    R.pop(0.5)
