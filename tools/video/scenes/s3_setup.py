# Cena 3: o Setup no gabinete (video, cor, rede, controles, pistola,
# emuladores).

COLOUR = [
    ("brightness", "Brightness: 0", "Moves the whole picture up or down (-50 to 50)"),
    ("contrast", "Contrast: 100%", "Spreads or squeezes the picture around the middle grey (50 to 150)"),
    ("gamma", "Gamma: %s", "The middle greys: above 1.00 they get brighter, below darker (50 to 200)"),
    ("temperature", "Colour temperature: 9300 K", "The colour of white: 6500 K neutral, 9300 K bluish (4000 to 10000)"),
    ("red_gain", "Red gain: 100%", "How strong red is in bright colours (0 to 150)"),
    ("saturation", "Saturation: 110%", "How strong the colours are: 0 is black and white (0 to 200)"),
    ("return", "Return", "Back."),
]


def colour_menu(gamma):
    return W.Menu("Colour settings", [(k, l % gamma if "%s" in l else l, h) for k, l, h in COLOUR], "gamma",
                  "Changes count right away.")


def gamma_step(v):
    f = lambda x: "%d.%02d" % (x // 100, x % 100)  # noqa: E731
    return W.Menu("Gamma: " + f(v), [
        ("minus", "[ - ]  " + f(v - 5), "One step down (from 50)."),
        ("plus", "[ + ]  " + f(v + 5), "One step up (to 200)."),
        ("type", "Type a value", "From 50 to 200."),
        ("default", "Default: 1.00", "Back to the default."),
        ("return", "Return", "Back."),
    ], "plus", "The middle greys: above 1.00 they get brighter, below darker.")


def script(R):
    R.ctx["status"] = "192.168.1.155 - 9%"
    R.bg("fire")
    R.push(demo.setup(), 2.2)
    # Video Setup > Colour calibration
    R.key("enter", 0.3)
    R.push(W.Menu("Video Setup", [
        ("monitor", "Monitor Type", "The kind of CRT: its horizontal frequency range."),
        ("orientation", "Monitor Orientation", "Horizontal or vertical (rotated) screen."),
        ("resolution", "Resolution", "The video mode of the menus and the frontend."),
        ("geometry", "Geometry", "Center and size the picture on the tube."),
        ("mode480", "480i games", "640x240 or 480i (with the flicker filter) for each program."),
        ("colour", "Colour calibration", "Brightness, contrast, gamma, each gun, colour and hue."),
        ("outputs", "Multiple Monitors", "Two or three CRTs for the multi-screen games."),
        ("return", "Return"),
    ], "monitor"), 1.4)
    R.keys("right right right right right", 0.55)
    R.key("enter", 0.3)
    R.push(colour_menu("1.00"), 1.6)
    R.key("enter", 0.3)
    v = 100
    R.push(gamma_step(v), 1.2)
    for _ in range(3):
        v += 5
        R.replace(gamma_step(v), 0.75)
    R.pop()
    R.replace(colour_menu("%d.%02d" % (v // 100, v % 100)), 1.2)
    R.pop()
    R.pop(0.6)
    # Network Setup > Wi-Fi
    R.keys("right right", 0.5)
    R.key("enter", 0.3)
    R.push(W.Menu("Wi-Fi networks", [
        ("flipernet", "FliperNet", "Signal: strong. WPA2, channel 6"),
        ("casa", "Casa_5G", "Signal: good. WPA2, channel 44"),
        ("vizinho", "Vizinho", "Signal: weak. WPA2, channel 11"),
        ("hidden", "Hidden network", "Type its name and password."),
        ("return", "Return"),
    ], "flipernet", "Pick the network:", mode="radio"), 1.6)
    R.key("enter", 0.3)
    pw = W.Input("Wi-Fi password", ["Password of the network FliperNet:"], "", password=True)
    R.push(pw, 0.5)
    R.type("value", "arcade1994", 0.1, 0.8)
    R.pop()
    R.pop(0.6)
    # Joysticks: Button mapping, Buttons layout, GunCon 2
    R.keys("right right", 0.5)
    R.key("enter", 0.3)
    R.push(demo.joysticks(), 1.4)
    R.key("enter", 0.3)
    R.push(demo.players(), 1.0)
    R.key("enter", 0.3)
    order = ["up", "down", "left", "right", "b1", "b2", "b3", "b4", "b5", "b6", "start", "coin"]
    for i, c in enumerate(order[:9]):
        R.push(W.Capture("Button mapping", 1, c, order[:i], i + 1, 12, 8), 0.0) if i == 0 else \
            R.replace(W.Capture("Button mapping", 1, c, order[:i], i + 1, 12, 8), 0.0)
        R.wait(0.55)
    R.pop()
    R.pop(0.4)
    R.key("right", 0.5)
    R.key("enter", 0.3)
    R.push(demo.layout(), 1.4)
    R.key("enter", 0.3)
    edit = demo.layoutedit()
    R.push(edit, 0.8)
    R.keys("left up enter right enter", 0.55)
    R.wait(0.5)
    R.pop()
    R.pop(0.4)
    R.key("right", 0.5)
    R.key("enter", 0.3)
    R.push(demo.guncon(), 1.6)
    R.key("enter", 0.3)
    for step, where, need in ((1, "top-left", 3), (2, "bottom-right", 3), (3, "center", 1)):
        for shots in range(need + 1):
            last = "Shot %d of %d: x=%d y=%d" % (shots, need, 182 + 3 * shots, 47 - shots) if shots and step < 3 else ""
            screen = W.GunTarget(step, 3, where, need, shots, last)
            if step == 1 and shots == 0:
                R.push(screen, 0.5)
            else:
                R.replace(screen, 0.42)
    R.replace(demo.gunresult(), 2.0)
    R.pop()
    R.pop()
    R.pop(0.4)
    # Games > Emulators & Games, com as versoes
    R.keys("left", 0.6)
    R.key("enter", 0.3)
    R.push(W.Menu("Emulators & Games", [
        ("retroarch", "RetroArch (consoles and arcade cores) 2026-10-12 55c2026 (installed)"),
        ("groovymame", "GroovyMAME (arcade) 0.289 (installed)"),
        ("flycast", "Flycast (Dreamcast, Naomi, Atomiswave) (installed)"),
        ("pcsx2", "PCSX2 (PlayStation 2) 2.8.2 (installed)"),
        ("dolphin", "Dolphin (GameCube, Wii, Triforce) 2609 (installed)"),
        ("supermodel", "Supermodel (Sega Model 3) (installed)"),
        ("model2", "Model 2 (SM2-Emu, Sega Model 2) 2026-10-20 4a8c9e6 (installed)"),
        ("fightcade", "Fightcade 2 (online arcade) 2.1.45 (installed)"),
        ("duckstation", "DuckStation (PlayStation) 0.1-12083-g00e299795 (installed)"),
        ("kof", "KOF Final Attack (Ikemen GO, 4:3) (not installed)"),
        ("return", "Return"),
    ], "groovymame", "Choose one to install it, or to update it when it is installed."), 1.6)
    R.keys("down down down down down", 0.45)
    R.key("enter", 0.3)
    R.push(W.Menu("Model 2 (SM2-Emu, Sega Model 2)", [
        ("update", "Update", "The newest source, built again: several minutes."),
        ("return", "Return", "Back to Emulators & Games."),
    ], "update", "Installed: 2026-10-20 4a8c9e6. Update: 4480789."), 2.6)
    R.pop()
    R.pop(0.6)
