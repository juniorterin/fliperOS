# Cena do Setup grafico para o Telegram e o site: Setup > Audio Setup > Menu sounds (o icone novo),
# os seis eventos, o volume de cada um e o seletor de arquivos. Gravada em tempo virtual por
# gui_rec.py (as telas sao as de verdade, fliperos-setup/gui, com os rotulos que o
# screens/sounds.sh monta), em 30 quadros por segundo.

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


def sounds(close="default, 90%"):
    return W.Menu("Menu sounds", [
        ("master", "Sounds (on)", "Turns all the menu sounds on or off."),
        ("snd-move", "Browse: default, 60%", "Plays when the cursor moves through a list."),
        ("snd-enter", "Enter: default, 80%", "Plays when you go into something."),
        ("snd-back", "Back: default, 80%", "Plays when you go back."),
        ("snd-open", "Open game: default, 90%", "Plays when a game is opened."),
        ("snd-close", "Close game: " + close, "Plays when a game closes."),
        ("snd-alert", "Alert dialog: default, 90%", "Plays when an alert or a question opens."),
        ("folder", "Sounds folder", "Where the sound files are, and how to add yours."),
        ("return", "Return", "Back to Audio Setup."),
    ], "master", "Pick an event, then its sound file and volume.")


def event(file="default", volume=90):
    return W.Menu("Close game", [
        ("file", "Sound file", "Choose a WAV, OGG, MP3 or FLAC from the sounds folder."),
        ("volume", "Volume", "From 0 to 100."),
        ("test", "Play", "Hear it now, with this volume."),
        ("default", "Use the default", "The sound FliperOS comes with."),
        ("off", "No sound", "Keep this event quiet."),
        ("return", "Return", "Back to the menu sounds."),
    ], "file", "Sound:   %s\nVolume:  %d%%" % (file, volume))


def picker():
    files = ["alert.wav", "back.wav", "browse.wav", "close-game.wav", "coin.wav", "enter.wav", "laser.wav",
             "open-game.wav", "power-up.wav"]
    entries = [("0", "music/")] + [(str(i + 1), name) for i, name in enumerate(files)]
    return W.Menu("Close game", entries, "0",
                  "Choose the sound for Close game (WAV, OGG, MP3 or FLAC).\n/home/fliperos/media/fliperos-sounds",
                  "menu", (), None, vertical=True, fixed=True)


def script(R):
    R.ctx["status"] = STATUS
    R.bg("stars")
    R.push(demo.setup(), 1.0)
    R.key("right", 0.5)                      # Audio Setup
    R.key("enter", 0.3)
    R.push(audio(), 1.2)
    R.keys("right right right right right", 0.5)    # Menu sounds: o icone novo
    R.wait(1.0)
    R.key("enter", 0.3)
    R.push(sounds(), 1.2)
    R.keys("right right right right right", 0.5)    # Close game
    R.key("enter", 0.3)
    R.push(event(), 1.2)
    R.key("enter", 0.3)                       # Sound file: o seletor
    R.push(picker(), 1.0)
    R.keys("down down down down down down down", 0.28)     # laser.wav
    R.wait(0.6)
    R.key("enter", 0.3)
    R.pop()
    R.replace(event("laser.wav", 90), 1.0)
    R.key("right", 0.5)                       # Volume
    R.wait(0.8)
    R.key("esc", 0.2)
    R.pop()
    R.replace(sounds("laser.wav, 90%"), 1.4)
