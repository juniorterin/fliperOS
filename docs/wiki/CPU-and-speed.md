How fast a game runs on FliperOS depends mostly on **one CPU core**: how quick it is, not how many there are. This page shows how the cabinet's processor is used, how to tell when it is the limit, and the firmware switch that most often holds it back: **Turbo Boost** (AMD: Core Performance Boost), which can be left off in the firmware.

## One fast core

An emulator puts the work that sets the speed on one thread: the game's own processor, its coprocessors and the sound chips. The other cores take the drawing, the audio and the video driver, which are lighter. A game that is too heavy shows it as one thread at about 100% of a core and the rest nearly idle.

Measured on a cabinet with a Core i7-870 (2.93 GHz, 4 cores, 8 threads) and a Radeon R7 240:

| Game | Emulator | The busiest thread | What it showed |
| --- | --- | --- | --- |
| Fighting Vipers 2 (Model 3) | Keisho | The main thread: 98-99% of a core in the slow scenes, about 45% in the light ones | 57.5 Hz in light scenes, 48 to 52 Hz in heavy ones |
| Tekken 5 fights (Namco 256) | PCSX2x6 | The emulated processor: 99.9% of a core. The vector unit: 84-89% | FPS dips in fights |

The video card was far from its limit in both. On Fighting Vipers 2 the 3D drawing took 1.8 ms of each frame.

### Where a Model 3 frame goes

The Model 2 and Model 3 boards run at **57.524 Hz**, so a frame has **17.38 ms**. Keisho's own timing (`--profile`, Turbo off, 60 seconds without the speed limiter: about 4000 frames of Fighting Vipers 2 from boot on, with a coin and start pressed at frame 700):

| Part of the frame | Average | Slow frames (95th percentile) |
| --- | --- | --- |
| The game's PowerPC processor | 8.4 ms | 13.2 ms |
| The sound boards (two SCSP chips and the MPEG music board) | 5.3 ms | 5.8 ms |
| The two together (`run_frame`, one thread) | 14.0 ms | 19.2 ms |
| The 3D drawing on the video card | 1.8 ms | 3.9 ms |

Light frames fit in the 17.38 ms. In a heavy scene the processor alone takes 13 ms, the sound adds its 5 or 6 ms and the frame comes out at about 20 ms: 49 frames a second instead of 57.5. The sound costs the same in every frame, so it is the part that does not shrink when the scene is easy.

## Turbo Boost

**Turbo Boost** lets a core run above its rated clock while few cores are busy. It is a firmware setting. With it off, the cabinet runs at the rated clock all the time: an i7-870 stays at 2933 MHz, and it has 3600 MHz to give.

| Cores awake | Clock of the i7-870 |
| --- | --- |
| Turbo off in the firmware | 2933 MHz |
| 3 or 4 | 3200 MHz |
| 2 | 3467 MHz |
| 1 | 3600 MHz |

A game wakes more cores than the one that matters: the audio, the drawing and the video driver run on their own threads and wake now and then. With Turbo on, the clock in a game sat between 3.2 and 3.5 GHz, not at the 3.6 GHz of a single busy core.

On the i7-870, with Turbo on: 3372 MHz measured under one busy thread, and temperatures of 63 to 74 °C while a game ran. In Fighting Vipers 2 the heavy scenes still dipped to 48 to 52 Hz, so on this processor Turbo alone did not hold 57.5 Hz everywhere. It was not a controlled comparison (the scenes were not the same), and the clock gain here is 9 to 19%.

### Turning it on

Open the BIOS (the key at power on: Del, F2 or F10, depending on the board) and look in the CPU or performance pages for **Intel Turbo Boost Technology** (also called Turbo Mode) or, on AMD, **Core Performance Boost**. Set it to Enabled, and keep **Enhanced Intel SpeedStep** (EIST) on. The names change from board to board.

**Linux can't turn it on for you** on a board where the firmware has it off. On the i7-870 board, clearing the processor's "turbo disable" bit and asking for the turbo state from the system left the clock at the rated 2933 MHz. Only the firmware setting changed it.

**Cooling matters.** A processor at a higher clock makes more heat. A PS2 test in a closed arcade cabinet reached 94 to 98 °C and slowed down to 1.2 GHz, and the same machine outside the cabinet stayed at 62 to 67 °C ([PlayStation 2 and Namco 246/256](Namco-246-256.md)). After turning Turbo on, play for a while with the cabinet closed and read the temperatures (below).

### How to tell if Turbo is on

On the i7-870, with the firmware setting off and then on:

| What | Turbo off | Turbo on |
| --- | --- | --- |
| `grep -m1 -o -w ida /proc/cpuinfo` (Intel) | prints nothing | prints `ida` |
| `ls /sys/devices/system/cpu/cpu0/cpufreq` | no such folder | the folder exists (driver `acpi-cpufreq`) |
| `cat /sys/devices/system/cpu/cpufreq/boost` | no such file | `1` |
| `grep MHz /proc/cpuinfo` | 2926 on every core, always | the measured clock of each core, changing |

With Turbo off the system has no frequency control at all: the `performance` governor of the [Latency](Latency.md) modes has nothing to act on, and the clock is fixed.

To read the temperatures: `cat /sys/class/hwmon/hwmon*/temp*_input` (thousandths of a degree). On the i7-870 the processor's own limits are 83 °C (high) and 99 °C (critical).

### What the Setup shows

**Setup > System > Latency** shows the **Max clock** of this computer and checks it against the 3.0 GHz of the Low latency mode. It reads the clock the driver reports as the highest. On the i7-870 that is **2.9 GHz even with Turbo on**: the driver lists the turbo state as the rated clock plus 1 MHz (2934 MHz) and doesn't give the real 3.2 to 3.6 GHz. Read the real clock in a game with `grep MHz /proc/cpuinfo`.

## Reading how much a game uses

- **The rate of Keisho.** The window title carries it (`Fighting Vipers 2 [Vulkan] - 57.5 Hz`), averaged over the last second. **F8** shows it on the screen. A game at full speed reads 57.5 Hz, or up to 57.8 Hz when the audio is pulling it back (the sync can move the speed by 0.5%). Under 57 Hz the machine is behind.
- **Without touching the game, from another computer.** The title can be read from the cabinet's X session: `DISPLAY=:0 xprop -id $(DISPLAY=:0 xwininfo -root -tree | awk '/Keisho/ {print $1; exit}') WM_NAME`.
- **The thread that limits it.** `top -H -p PID` lists the threads. One at about 100% and the others low means the game is bound by one core.
- **The time of each part.** From the console, outside the desktop: `fliperos-x11-run fliperos-model3 fvipers2o --profile 60 --no-throttle --no-vsync --coin-at 700`. The game runs for 60 seconds without the speed limiter, then the log (`/opt/fliperos/logs/fliperos-model3.log`) gets a table with the time of each part of the frame, the average rate (how much room there is) and the 95th and 99th percentile of the frame times (what the slow scenes cost). It needs no input: it inserts a coin and presses start at frame 700.

## What did not help

- **Pinning the emulator to one logical CPU per physical core**, so that none of its threads shares a core with a hyperthread: 66.7 fps against 67.1, with the same slow scenes.
- **Turning on Turbo from Linux** on a board that has it off in the firmware, as above.
- **More cores.** Keisho's author reports that moving a Model 2 coprocessor to its own thread made it slower, and the speed depends on the one fast core.

## What does help

A faster core, which in practice means a newer processor: a recent core does more in each clock cycle than a 2009 design at the same GHz. The [recommended hardware](Latency.md#recommended-hardware) table lists what the heavy emulators (Model 3, PS2, Dreamcast) ask for. Next come Turbo Boost, with the cabinet cooled, and the `performance` governor.

## Problems

| What was seen | Likely cause | What to do |
| --- | --- | --- |
| A game is slow only in busy scenes, and one thread of the game sits at about 100% | The processor is the limit | Turn Turbo on, then a faster processor |
| `/proc/cpuinfo` shows the same MHz on every core, and there is no `cpufreq` folder | The firmware has Turbo and frequency scaling off | Turn them on in the BIOS |
| The clock falls to 1.2 GHz in a long session | The processor is too hot and slows itself down | Clean the cooler, add airflow to the cabinet |
| **Setup > System > Latency** shows 2.9 GHz with Turbo on | The driver doesn't report the turbo clock of this processor | Nothing to fix: read the clock in a game |

## How it works

- **The frame pacer.** Keisho holds the machine to its own 57.5245 Hz against real time, not the display's refresh (`src/osd/frame_pacer.cpp`). A frame that falls more than four periods behind is not made up for: the debt is written off. The rate in the title is the number of frames in the last second.
- **The audio sync.** The speed is nudged by up to 0.5% to keep the audio queue at its target, so a steady 57.8 Hz means the queue is running short, not that the game is fast.
- **The names in `--profile`.** `cpu_i960` is the game's main processor on any board (the PowerPC on Model 3), `cpu_sound` the sound boards, `m3_build` the frame build that Keisho does on a second thread. `run_frame` is the sum of the processor stages on the main thread.
- **The governor.** `fliperos-session` sets `performance` while a session runs (the frontend and the games it opens) and puts the system's own governor back afterwards ([Latency](Latency.md)).
- **The build.** The package `fliperos-keisho` is built for the generic x86-64 baseline (no `SM2_TUNE`), with link-time optimisation, so the compiler doesn't use the newer instructions of a given processor.
- **Where the Setup reads the clock.** `hw_cpu_max_mhz` in `fliperos-setup/lib/hardware.sh` reads `cpufreq/cpuinfo_max_freq`, and the highest `cpu MHz` of `/proc/cpuinfo` when there is no cpufreq.

See also: [Latency](Latency.md), [Sega Model 2 and 3](Sega-Model-2-and-3.md), [PlayStation 2 and Namco 246/256](Namco-246-256.md).
