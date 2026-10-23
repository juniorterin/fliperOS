Open-source projects you can build yourself, with an Arduino, a Raspberry Pi Pico or an ESP32, and use on a FliperOS cabinet. Most of them plug into USB and show up as a standard joystick, mouse or keyboard, so FliperOS needs no driver for them. This page says, for each one, what FliperOS does with it and whether it has been tried.

Only two of these have been used with FliperOS so far: the V-USB MamePanel, which is the control panel of the test cabinet, and the ZeDMD support, which is written but has not been tried on a real display. The others are listed because of how they present themselves to the computer, not because they were tested.

## Control panel (joysticks and buttons)

After plugging the panel in, map each player's buttons once in **Setup > Joysticks > Button mapping**; the mapping goes to every emulator ([Controls](Controls.md)).

| Project | Board | What the computer sees |
| --- | --- | --- |
| [GP2040-CE](https://github.com/OpenStickCommunity/GP2040-CE) ([documentation](https://gp2040-ce.info)) | Raspberry Pi Pico and other RP2040 boards | A gamepad, in the mode you choose (XInput, DInput, keyboard and others); one board per player. MIT license |
| [DaemonBite Arcade Encoder](https://github.com/MickGyver/DaemonBite-Arcade-Encoder) | Arduino Pro Micro (ATmega32U4) | A USB joystick with up to 12 buttons, made for low latency. GPL-3.0 |
| [Arduino Joystick Library](https://github.com/MHeironimus/ArduinoJoystickLibrary) | Arduino Leonardo, Micro and other ATmega32U4 boards | A joystick or gamepad you describe in your own sketch (32 buttons by default). LGPL-3.0 |
| [V-USB MamePanel](http://vusb.wikidot.com/project:mamepanel) | ATmega8 (18 inputs) or ATmega32 (30 inputs, two joysticks), with the [V-USB](https://github.com/obdev/v-usb) software USB driver | Joysticks with up to 8 buttons each. This is the panel of the FliperOS test cabinet |

- **Two players on one board**: an encoder that carries both players may arrive as a single joystick. **Setup > System > Quirks** has the kernel flag that splits it (`0x40`, one device per player); see [Controls](Controls.md).
- **Latency**: **Setup > System > Latency** reads USB at 1000 Hz, which only helps if the board also answers at that rate ([Latency](Latency.md)).

## Spinner and trackball

| Project | Board | What the computer sees |
| --- | --- | --- |
| [Arcade Spinner](https://github.com/jmtw000/Arcade-Spinner) | Arduino Micro or another ATmega32U4 board, with a rotary encoder | A mouse (the spinner is the X axis) and a joystick (the buttons). GPL-3.0 |

GroovyMAME and the MAME cores of RetroArch read a mouse as the spinner or trackball of the game. FliperOS has no screen to set this up: it is done in the emulator's own input menu.

## Light gun

FliperOS ships the driver and the calibration for the **GunCon 2**, which reads the tube itself ([Controls](Controls.md)). The projects below work another way: an infrared camera in the gun looks at LEDs placed around the screen, so they don't depend on the kind of monitor.

| Project | Board | What the computer sees |
| --- | --- | --- |
| [OpenFIRE](https://github.com/TeamOpenFIRE/OpenFIRE-Firmware) | Raspberry Pi Pico and other RP2040 or RP2350 boards | An absolute-position mouse, a keyboard and a gamepad |
| [SAMCO IR Light Gun](https://github.com/samuelballantyne/IR-Light-Gun) | Arduino boards (ATmega32U4, M0, M4) | The project OpenFIRE came from; its page now points to OpenFIRE. GPL-3.0 |

The GunCon 2 calibration of the Setup is for the GunCon 2 only. These guns are calibrated in their own firmware and used as a mouse in the emulator.

## LED display (marquee, DMD)

| Project | Board | With FliperOS |
| --- | --- | --- |
| [ZeDMD](https://github.com/PPUC/ZeDMD) | ESP32 (the ESP32-S3-N16R8 is the recommended one) or Raspberry Pi Pico, driving HUB75 LED panels of 128x32 or 256x64 | **Setup > Games > Extras > ZeDMD** installs the support: the display shows the selected game, the game that is open, its high scores and the achievements ([Frontends](Frontends.md)). GPL-2.0 |
| [libdmdutil](https://github.com/vpinball/libdmdutil) | (runs on the PC) | The library, from the Visual Pinball project, whose `dmdserver` FliperOS uses to talk to the ZeDMD |

The Pixelcade marquee, which FliperOS also supports, is a commercial product with closed software; it is on the [Frontends](Frontends.md) page.

## Game outputs: lamps, recoil, motors and button lights

Arcade games drive things outside the screen: start lamps, gun recoil, motors, digit displays. GroovyMAME, Flycast, Supermodel and SM2-Emu (Model 2) can publish these **outputs** over the network (TCP port 8000, one `name = value` line per change). On Windows the program that reads them is MAMEHooker. FliperOS has three readers, each one an extra in **Setup > Games > Extras**. They can be installed together.

| Project | What it drives | With FliperOS |
| --- | --- | --- |
| [Hook Of The Reaper](https://hotr.6bolt.com/) | Light guns with recoil and lights (OpenFIRE, GUN4IR, Blamcon, Fusion, RS3 Reaper, Alien, AimTrak, Sinden and others), boards on a serial port or USB HID, Ultimarc light boards | **Setup > Games > Extras > Hook Of The Reaper**. A Windows program, run through Wine. Its source isn't public at the moment |
| [QMamehook](https://github.com/SeongGino/QMamehook) | Light guns on a serial port only: OpenFIRE, GUN4IR, Blamcon, RS3 Reaper | **Setup > Games > Extras > QMamehook**. Native, without Wine: its source is built on the cabinet. LGPL-2.1 |
| [LEDSpicer](https://github.com/meduzapat/LEDSpicer) | Ready-made LED boards: Ultimarc (PacLED64, PacDrive, Ultimate I/O, NanoLED), LED-Wiz 32, Howler, Adalight | **Setup > Games > Extras > LEDSpicer**, from its author's Ubuntu repository. It lights the buttons each game uses. GPL-3.0 |

The emulators only open port 8000 when one of them is installed, because the port is reachable from the network and accepts a pause command.

None of them has been tried with a real gun or board on a FliperOS cabinet yet. QMamehook was built and run against a simulated game: it connects to the port, looks for the game's `.ini` and closes with the game. Hook Of The Reaper was run under Wine against a simulated game: it connects to the port, loads the game's file and closes with the game. On the test cabinet it was installed from the Extras and opened with a Model 2 game (The House of the Dead in SM2-Emu, on a virtual screen): it stayed connected to the game's port for the whole run and closed with it. Whether Wine reaches each gun's serial port or USB HID interface still has to be seen on hardware.

### Model 2 game outputs

A Model 2 gun cabinet has no recoil, so the board never says that a shot was fired, and SM2-Emu on its own only publishes the lamps. FliperOS adds a patch to it (`config/sm2-emu-patches`, to be offered to the SM2-Emu project) that reads the game's own memory and publishes it as outputs. The gun games use the names Hook Of The Reaper's game files already listen for:

| Game | Outputs |
| --- | --- |
| Virtua Cop (`vcop`), Virtua Cop 2 (`vcop2`), The House of the Dead (`hotd`) | `P1_CtmRecoil` (a pulse per shot), `P1_Ammo`, `P1_Clip`, `P1_Life`, `P1_Damaged` (a pulse per life lost), `P1_LmpStart`, the same for `P2_`, and `Credits` |
| Gunblade NY (`gunblade`) | `P1_CtmRecoil`, `P1_GunMotor` (the cabinet's own gun motor), `P1_Life`, `P1_Damaged`, `P1_LmpStart`, the same for `P2_`, and `Credits` |
| Behind Enemy Lines (`bel`) | `P1_CtmRecoil`, `P1_Ammo`, `P1_Clip`, `P1_Life`, `P1_Damaged`, the same for `P2_`, and `Credits` |
| Rail Chase 2 (`rchase2`) | `P1_Life`, `P1_Damaged`, `P1_LmpStart`, the same for `P2_` |
| Virtua Fighter 2 (`vf2`), Fighting Vipers (`fvipers`), Sonic the Fighters (`schamp`), Last Bronx (`lastbrnx`), Dead or Alive (`doa`) | `P1_Wins` and `P2_Wins` (the rounds each side has taken in the match being fought, back to zero when it ends), and `Credits` |
| Desert Tank, Dynamite Cop, Indianapolis 500, Over Rev, Pilot Kids, Sega GT 24h, Sega Ski Super G, Sky Target, Top Skater, Virtua Striker, Zero Gunner | `Credits` |

Each was checked with a reader on port 8000 through a game played by a script: a credit, a start, shots until the magazine is empty and lives lost, for player 1; the fighting games with two scripted two-player matches, one won by each side. Player 2 in the gun games and a real gun haven't been tried. The wins feed the [versus score on the LED display](Frontends.md#versus-score-on-the-led-display). The addresses were found in the sets of the MAME 0.289 romset, and belong to the revision that set opens as.

The games on two coins a credit that start by themselves when the credit completes (Daytona USA, Sega Rally, Sega Touring Car, Motor Raid, Manx TT, Wave Runner, Sega Water Ski, Virtual On) have no `Credits`: it is spent the moment it exists. The two baseball games and the credit counter of Rail Chase 2 weren't found.

The patch reaches a cabinet that already built Model 2 the next time **Games > Model 2** opens, which offers to update and rebuild.

### Hook Of The Reaper

[Hook Of The Reaper](https://hotr.6bolt.com/) is the current successor of MAMEHooker. It has no Linux version yet (its author plans one after the program is complete), so FliperOS runs the Windows program through Wine.

- **What is installed**: 64-bit Wine and a virtual screen (`xvfb`) from apt, and the program from its own website (pinned version and hash) into `~/hotr`. It gets its own Wine folder, separate from Fightcade's. Nothing of this is in the image.
- **Setting it up**: on the desktop, **Preferences > Hook Of The Reaper** opens its window. Add your light guns and assign each one to a player, as its [tutorial](https://hotr.6bolt.com/pmwiki.php/Tutorial/Setup) shows. The settings stay in `~/hotr/data`.
- **Game files**: it comes with its own files for over 200 gun games (`~/hotr/defaultLG`), which work with any gun it supports. MAMEHooker `.ini` files go in `~/hotr/ini/MAME`. The folder is also at `~/config/hotr`, shared on the network.
- **When it runs**: it opens with each game of GroovyMAME, Flycast, Supermodel and SM2-Emu and closes with it. It runs on the virtual screen, so none of its windows or warnings appear over the game. Installing it again from the Extras updates the program and keeps your guns, players and `.ini` files.
- **USB HID guns and boards**: the install lets the `fliperos` user open the USB HID devices (`/dev/hidraw*`, group `input`), which is how Wine reaches them. Serial boards already belong to the user's `dialout` group.

### LEDSpicer

- The install adds the packages for every board it supports, but doesn't turn the service on: LEDSpicer needs `/etc/ledspicer.conf` describing your boards and which LED is which button, as its [wiki](https://github.com/meduzapat/LEDSpicer/wiki) explains. Then `sudo systemctl enable --now ledspicerd`.
- With the service running, FliperOS tells it which game opened (`emitter LoadProfileByEmulator <game> arcade`, or the console's folder for the others) and when it closed, from any frontend or emulator.

### QMamehook

[QMamehook](https://github.com/SeongGino/QMamehook) is an open-source (LGPL-2.1) reader that runs natively on Linux, without Wine, and uses MAMEHooker's `.ini` files unchanged. It is small on purpose: it only writes to serial ports and only accepts the USB IDs of a few gun boards (OpenFIRE, GUN4IR, Blamcon; the RS3 Reaper after `sudo modprobe usbserial vendor=0x0483 product=0x5750`). It has no window and nothing to set up.

- **What is installed**: its author publishes only the Windows program, so the install builds version 2.2 from source (pinned by hash) into `~/qmamehook`. The compiler and Qt 6 come from apt; it takes about two minutes. Nothing of this is in the image.
- **Game files**: MAMEHooker `.ini` files go in `~/qmamehook/ini`, one per ROM set (`sf2ce.ini`). The folder is also at `~/config/qmamehook`, shared on the network. For a game without a file, QMamehook writes one there listing the outputs the game sent, for you to fill in.
- **Players**: the guns are numbered in the order of their USB product IDs, so the `.ini` writes to port 1 for the first gun, 2 for the second.
- **When it runs**: it opens with each game of GroovyMAME, Flycast, Supermodel and SM2-Emu and closes with it. What it says (the guns it found, the file it loaded) is in `/opt/fliperos/logs/qmamehook.log`.
- **With Hook Of The Reaper also installed**, only one of the two opens with the game, because a gun's serial port can't be shared: Hook Of The Reaper, unless `/etc/fliperos/fliperos.conf` has the line `outputs_reader=qmamehook`.

## Adding a project to this page

A project fits here if its firmware or software is open source and it works on Linux without a closed driver. If you use one of these on your cabinet, or another one, open an issue in the [repository](https://github.com/juniorterin/fliperOS/issues) saying which board, what the Setup showed in **Setup > System > Quirks > USB devices connected now**, and whether it needed a quirk: that is what turns a line of this page from "should work" into "tested".
