The sound and the network of the cabinet: **Setup > Audio Setup** and **Setup > Network Setup**.

## Audio Setup

| Item | What it does |
| --- | --- |
| **Default card** | The sound card used by the system and every emulator |
| **Volume** | From 0 to 100. The volume keys of a keyboard or a panel work too ([Power and volume buttons](Power-and-volume-buttons.md#volume-keys)) |
| **AlsaMixer** | Every control of the sound card, one by one |
| **MAME audio latency** | GroovyMAME's sound buffer, 0.0 to 50.0 (0 is MAME's default). Lower responds faster; raise it if the sound crackles |
| **Test sound** | Plays a sound to check the speakers |
| **Menu sounds** | A sound when the cursor moves and another on Enter, with your own WAV files |

There is no sound server: every emulator plays straight into ALSA, in KMS or in X, so this volume and this card count for all of them.

### Menu sounds

Like the select screen of a game: one sound as the cursor moves through the menus, another on Enter. FliperOS ships no game sounds, so they are yours:

1. Put `move.wav` and `select.wav` in `/opt/fliperos/sounds/menu`. Over the network it is the `FliperOS` share, folder `sounds/menu`.
2. With one of them there, the sounds turn on by themselves.
3. **Menu sounds** in Audio Setup turns them off and on.

A new sound cuts the one still playing, and the Enter sound keeps going after the menu closes.

### How it works

- The default card is written to `/etc/asound.conf`. The volume moves `Master`, `Front`, `Speaker` and `Headphone` and leaves `PCM` at its maximum, as on GroovyArcade; a card with only `PCM` uses `PCM`. It is saved at every change, because cabinets are usually switched off at the wall.
- RetroArch uses `audio_driver = alsa`, GroovyMAME `sound sdl` on the ALSA `default` (through `libfliperos-sdl-audio.so`), and the SDL emulators `SDL_AUDIODRIVER=alsa`.
- MAME audio latency is `audio_latency` in `mame.ini` (GroovyArcade's "Audio Latency MAME").
- The HDA codec stays always on (`options snd_hda_intel power_save=0`). With the Ubuntu kernel's 1 s power saving it went silent and popped in the speakers each time it turned back on.
- Menu sounds are FliperOS's Gum patch `patches/gum/0002-sons-do-menu.patch` in the text menu, and the graphical menu itself; `menu_sounds=` in `fliperos.conf`.

## Network Setup

| Item | What it does |
| --- | --- |
| **Connect to a Wi-Fi network** | The networks in range, with their signal. Pick one and type its password |
| **Connect to a hidden network** | For a network that hides its name: type the SSID, then the password |
| **Network status** | The connections and the IP address of the cabinet |

Once connected, the IP shows in the FliperOS menu's title. Connecting to Wi-Fi also checks for a FliperOS update right away, without waiting for the next boot ([Updates and versions](Updates-and-versions.md)).

The network cable needs nothing: it connects by itself.

### Typing with the controller

The Wi-Fi password, a hidden network's name and every other password in the Setup have an **on-screen keyboard**:

- the arrows pick a key and button 1 types it;
- **SHIFT** gives capitals and symbols;
- **SHOW** shows the password as you type it.

### The internet check

Everything in the Setup that downloads checks the internet first: the Downloader, the Scraper, System Update, installing an emulator, a frontend or an extra. Without internet:

- with a Wi-Fi adapter, it offers to connect to a Wi-Fi network, then carries on with what you asked;
- without one, it asks for the network cable.

### How it works

- NetworkManager runs both the cable and the Wi-Fi (`nmcli`). The Wi-Fi radio itself is a service you can turn off in **Setup > System > Services** ([System Setup](Setup-System.md#services)).
- The first boot offers Wi-Fi only when the cable brings no internet ([Installed system](Installed-system.md#first-boot)).

See also: [Remote access](Remote-access.md), [Web panel](Web-panel.md).
