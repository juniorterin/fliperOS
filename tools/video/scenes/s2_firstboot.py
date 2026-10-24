# Cena 2: o primeiro boot do sistema instalado.


def script(R):
    R.ctx["status"] = "192.168.1.155 - 9%"
    R.black(0.5)
    R.boot(3.0)
    R.bg("water")
    R.push(W.Menu("Choose default launcher", [
        ("fliperos", "FliperOS frontend", "The game list of FliperOS: list, full screen and grid, with videos."),
        ("attractplus", "Attract-Mode Plus", "With the Arcadeflow theme, downloaded by the Setup."),
        ("emulationstation", "ES-DE", "EmulationStation, with the FliperOS 240p theme."),
        ("menu", "FliperOS menu", "This menu: frontend, Setup, desktop and shell."),
        ("desktop", "Desktop", "The LXDE desktop."),
    ], "fliperos", "Welcome to FliperOS. Choose what starts when the computer turns on."), 2.4)
    R.keys("right right", 0.7)
    R.keys("left left", 0.7)
    R.key("enter", 0.4)
    R.pop()
    R.push(demo.main(), 2.6)
    R.key("right", 1.6)
