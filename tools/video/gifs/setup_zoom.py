# Cena do Setup grafico para o Telegram e o site: o zoom ao entrar e ao voltar nos itens
# (fliperos-setup/gui/navfx.py, 0,3 s, so a camada da interface; o fundo segue vivo por baixo).
# Gravada em tempo virtual por gui_rec.py com R.zoom = True, que toca o mesmo zoom de
# App.swap (fliperos-gui). Use GUI_REC_FPS=50: o gabinete toca a 60 quadros por segundo, e
# em 30 o zoom teria so 9 quadros.

STATUS = "192.168.1.155 - 9%"


def audio():
    return W.Menu("Audio Setup", [
        ("card", "Default card", "The sound card used by the system and the emulators."),
        ("volume", "Volume", "From 0 to 100. The keyboard volume keys work too."),
        ("mixer", "AlsaMixer", "Every control of the sound card, one by one."),
        ("latency", "MAME audio latency", "Lower responds faster; raise it if the sound crackles."),
        ("test", "Test sound", "Play a sound to check the speakers."),
        ("sounds", "Menu sounds (on)", "The sound and volume of each menu event."),
        ("return", "Return", "Back to Setup."),
    ], "card", "Default card:  Realtek ALC887\nVolume:        80%")


def sounds():
    return W.Menu("Menu sounds", [
        ("master", "Sounds (on)", "Turns all the menu sounds on or off."),
        ("snd-move", "Browse: default, 60%", "Plays when the cursor moves through a list."),
        ("snd-enter", "Enter: default, 80%", "Plays when you go into something."),
        ("snd-back", "Back: default, 80%", "Plays when you go back."),
        ("snd-open", "Open game: default, 90%", "Plays when a game is opened."),
        ("snd-close", "Close game: default, 90%", "Plays when a game closes."),
        ("snd-alert", "Alert dialog: default, 90%", "Plays when an alert or a question opens."),
        ("folder", "Sounds folder", "Where the sound files are, and how to add yours."),
        ("return", "Return", "Back to Audio Setup."),
    ], "master", "Pick an event, then its sound and volume. The frontend uses the same ones.")


def script(R):
    R.ctx["status"] = STATUS
    R.bg("stars")
    R.push(demo.setup(), 1.0)
    R.zoom = True
    R.key("right", 0.6)                       # Audio Setup
    R.key("enter", 0)
    R.push(audio(), 1.3)                      # entrar: o zoom aproxima
    R.keys("right right right right right", 0.4)    # Menu sounds
    R.wait(0.5)
    R.key("enter", 0)
    R.push(sounds(), 1.5)                     # entrar mais um nivel
    R.key("esc", 0)
    R.pop(1.3)                                # voltar: o zoom afasta
    R.key("esc", 0)
    R.pop(1.5)                                # e voltar ao Setup
