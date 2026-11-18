**Setup > Joysticks > Haptic events** sets the vibration that modern controllers (Xbox, 8BitDo, DualSense and the like) give in the menu, in the frontends and when a game opens and closes. For each event you pick one of about 40 presets, and it plays at once so you can feel it.

| Event | Where | Default preset |
| --- | --- | --- |
| **Moving through items** | Menu and frontend | `tick`, a short dry click |
| **Entering an item** | Menu and frontend | `select`, a firm tap |
| **Going back** | Menu and frontend | `back`, two clicks |
| **Moving through systems** | Frontend | `step`, a fuller click |
| **Entering the frontend** | FliperOS, ES-DE, AttractPlus, Pegasus | `open`, rises from light to firm |
| **Leaving the frontend** | The same | `close`, falls from firm to light |

**Strength** at the top of the screen is the overall force: low (half), on, high (one and a half times) or off, which silences everything. Any event can also be set to **Off** alone.

Two more events are not yet in the list and keep fixed vibrations: a game **starts** (rises and ends in a thump) and **ends** (a thump with two fading echoes). A game that closes within 6 seconds of opening gives three hard knocks instead, because it most likely did not open.

## The presets

- **Motors:** `left-motor`, `right-motor`, `both-motors`, `alternate`.
- **Extremes:** `thump`, `buzz`, `purr`.
- **Body and machine:** `heartbeat`, `engine-rev`, `engine-idle`.
- **Ramps and wave:** `ramp-up`, `ramp-down`, `wave`.
- **Bursts:** `machine-gun`, `pulse-train`, `knock-knock`.
- **Impacts:** `explosion`, `sword-clash`, `earthquake`.
- **Alerts:** `sonar-ping`, `notification`, `success`, `fail`, `warning`, `sos`, `rain`.
- **The built-in events:** `tick`, `step`, `select`, `back`, `open`, `close`, `start`, `end`, `error`, `coin`.

Only controllers with rumble vibrate. Wheels, light guns, arcade panels and keyboards do not. A pad has two motors, the big left one (deep) and the small right one (sharp); both take a force from 0 to 65535 and nothing else, so a preset is a sequence of forces and times. A pulse shorter than about 40 ms is hardly felt, because the kernel updates rumble every 50 ms.

On the command line, `fliperos-haptic list` shows the presets and the pads it found, `fliperos-haptic demo` plays them all one after the other, and `fliperos-haptic NAME [--pad TEXT]` plays one, on the pads whose name has TEXT.

## How it works

- The choices are `haptic_move`, `haptic_enter`, `haptic_back`, `haptic_system`, `haptic_open` and `haptic_close` in `fliperos.conf` (a preset name or `off`; without the line, the default), and `haptic=low|high|off` for the strength. The web panel has the same rows under **Joysticks**.
- `gui/fehaptic.py` holds the presets and plays them through the kernel's force feedback (`FF_RUMBLE`), or through pygame in the frontend. Each step of a preset is one effect with its own delay, uploaded at once. The menu and the frontend read the choices again when the file changes.
- In the Setup menu, `config/fliperos-padkeys` vibrates the pad that pressed each key; the FliperOS frontend does the same in `gui/feinput.py`, on the pad in use (holding a direction gives one tick per step).
- `config/fliperos-haptic launch` runs beside every game and frontend (the `after_game` of `fliperos-kms-run` and `fliperos-x11-run`) and plays the open, close, start and end events.

See also: [Controls](Controls.md), [Controller light](Controller-light.md).
