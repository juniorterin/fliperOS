FliperOS sets up the emulators it ships by itself. For any other emulator (an AppImage, a package, something you built), there are four steps. Follow them, and the same command works in the FliperOS frontend's custom games, Attract-Mode Plus, ES-DE, Pegasus or the console.

For a single PC game or a program, [Custom games](Custom-games.md) is simpler: it makes the frontend system for you.

## Step 1: install it and test it by hand

Put the program where the system finds it: a package (`sudo apt install ...`), or the binary or AppImage in `/usr/local/bin` (`chmod +x`). Then, in the console (**Exit to shell** in the FliperOS menu), open a game through the wrapper:

```bash
/opt/fliperos/bin/fliperos-x11-run myemu "/home/fliperos/roms/myemu/game.bin"
```

If it opens full screen, plays and returns to the console when you quit, it will work from any frontend. Use `fliperos-kms-run` instead only if the program runs without X (most don't; see [What KMS and X11 are](KMS-and-X11.md#what-kms-and-x11-are)).

## Step 2: make the command frontend-proof

A frontend only knows how to run **one command with the game's path** and wait for it to finish. So the command must follow a few rules:

- **Absolute paths:** start with `/opt/fliperos/bin/fliperos-x11-run` (or `fliperos-kms-run`), never just the program's name. The frontends don't run a shell with your `PATH`.
- **The program right after the wrapper:** `fliperos-x11-run [--mode WxH@HZ] program [options] game`. The wrapper takes a name in the `PATH` or the full path of an executable.
- **Full screen and no questions:** pass the emulator's own options for full screen, for skipping its welcome or update dialogs and for loading the game directly. Nobody should need a mouse.
- **It has to quit, and stay in the foreground:** the emulator needs a way to exit with the panel or the keyboard (a hotkey or a menu), or you are stuck in it. It must not hand off to another process and exit: when the program the wrapper started ends, the wrapper closes its X and the frontend comes back.
- **The game's path in quotes:** file names have spaces. Each frontend writes the path with its own placeholder (table below).

If the emulator needs more (environment variables, a config file per game, a `cd` to its folder, Wine), **write a small launcher script** and point the frontends to it. The frontend then only passes the game, and every detail stays in one place:

```bash
#!/bin/bash
# /usr/local/bin/myemu-run GAME
export MYEMU_BIOS="$HOME/bios/myemu"
cd /opt/myemu || exit 1
exec /opt/myemu/myemu --fullscreen --no-gui "$1"
```

```bash
sudo chmod +x /usr/local/bin/myemu-run
/opt/fliperos/bin/fliperos-x11-run myemu-run "/home/fliperos/roms/myemu/game.bin"
```

The `exec` keeps the emulator as the program the wrapper waits for. This is how FliperOS opens Keisho for a frontend (`fliperos-model2`).

The cabinet has no terminal text editor: write the script over SFTP, from the desktop's text editor, or with `cat > file` in the terminal.

## Step 3: the video mode (X11 only)

`fliperos-x11-run` takes the mode from `/etc/fliperos/emulator-modes.conf` by the **program's name** (the first word after the wrapper, without its path). Add a line:

```text
# program           15 kHz          25/31 kHz and LCD
myemu-run           320x240@60      640x480@60
```

Without a line, the program gets 320x240@60. Use 640x240 at 15 kHz for systems that draw 448 or 480 lines, and the system's own refresh rate when it isn't 60 Hz (Model 2 and 3: 57.524).

## Step 4: one folder and the command in each frontend

Create the game folder, for example `~/roms/myemu`. **Setup > Games > Frontend** only creates the systems FliperOS knows, so a new emulator is added by hand in each frontend you use. The command is the same everywhere; only the placeholders change:

| Frontend | Where | Game path | Name without extension |
| --- | --- | --- | --- |
| Attract-Mode Plus | `args` in `~/.attract/emulators/<name>.cfg` | `"[romfilename]"` | `[name]` |
| ES-DE | `<command>` in `~/ES-DE/custom_systems/es_systems.xml` | `%ROM%` (ES-DE adds the quotes) | `%BASENAME%` |
| Pegasus | `launch:` in `metadata.pegasus.txt` in the game folder | `"{file.path}"` | `{file.basename}` |

The same emulator in the three:

```text
# Attract-Mode Plus: ~/.attract/emulators/My Emulator.cfg
executable           /opt/fliperos/bin/fliperos-x11-run
args                 myemu-run "[romfilename]"
rompath              /home/fliperos/roms/myemu/
romext               .bin;.zip
```

```xml
<!-- ES-DE: inside <systemList> in ~/ES-DE/custom_systems/es_systems.xml -->
<system>
  <name>myemu</name>
  <fullname>My Emulator</fullname>
  <path>/home/fliperos/roms/myemu</path>
  <extension>.bin .zip</extension>
  <command label="My Emulator">/opt/fliperos/bin/fliperos-x11-run myemu-run %ROM%</command>
  <platform>arcade</platform>
  <theme>arcade</theme>
</system>
```

```text
# Pegasus: ~/roms/myemu/metadata.pegasus.txt
collection: My Emulator
extensions: bin, zip
launch: /opt/fliperos/bin/fliperos-x11-run myemu-run "{file.path}"
```

Then:

- **Attract-Mode Plus:** generate the romlist and add a display ([Attract-Mode Plus](Attract-Mode-Plus.md#adding-an-emulator-by-hand)). For the art, point the emulator's `artwork` lines to `~/media/<type>/myemu`.
- **ES-DE:** use the `<platform>` the scraper should search as ([ES-DE and Pegasus](ES-DE-and-Pegasus.md#a-system-by-hand)).
- **Pegasus:** add the folder to `~/.config/pegasus-frontend/game_dirs.txt`.

**What the Setup keeps and what it rewrites.** A `.cfg` you created yourself, without the `# Criado pelo FliperOS Setup` line, is never touched, and neither is a `metadata.pegasus.txt` that already exists. **Setup > Games > Frontend** does rewrite ES-DE's `es_systems.xml` and Pegasus's `game_dirs.txt` with only the folders it knows, so add your system again after using it.

## How it works

- The wrappers are `fliperos-x11-run` (its own Xorg, with the Switchres mode, for that program alone) and `fliperos-kms-run` (straight on the console). They also bring the flicker filter and on-screen menu, the controls, the marquee, the achievements and the cloud backup, so a game opened through them gets everything the shipped emulators get ([Emulators](Emulators.md)).
- The modes table is `config/fliperos-emulator-modes.conf`, installed as `/etc/fliperos/emulator-modes.conf`. An update that changes it replaces your edited copy, after saving it in the update's backup folder ([Updates and versions](Updates-and-versions.md#what-an-update-keeps)), so keep a copy of your lines.

See also: [Adding games](Adding-games.md), [Custom games](Custom-games.md).
