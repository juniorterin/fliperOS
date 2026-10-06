What weighs most in the delay between pressing the button and the picture changing is the same on FliperOS and on GroovyArcade: the same kernel patches (the same video output on radeon/amdgpu), the same Switchres and GroovyMAME, and the CRT, which doesn't process the image. FliperOS applies the tweaks GA already makes and adds others, in two modes chosen in **Setup > Latency** (`fliperos-setup/lib/latency.sh`).

| Tweak | GroovyArcade | FliperOS Standard | FliperOS Low latency |
| --- | --- | --- | --- |
| `mitigations=off audit=0` in the kernel | yes | yes | yes |
| USB polled at 1000 Hz (`usbhid.jspoll=1 kbpoll=1 mousepoll=1`) | no | yes | yes |
| CPU on the `performance` governor | while the frontend runs | while the frontend runs | always, from boot |
| Kernel preemption | `linux-15khz` (there is also a `linux-rt`) | 6.18 `PREEMPT_DYNAMIC`, voluntary mode | `preempt=full` |
| GroovyMAME `lowlatency 1`, `autoframedelay 1`, `framedelay 0` | `lowlatency` (the rest is default) | yes | yes |
| RetroArch `video_max_swapchain_images = 2` | yes | yes | yes |
| RetroArch `video_threaded` off, `input_poll_type_behavior = 2` | default | yes | yes |
| RetroArch automatic frame delay | no | no | yes |
| RetroArch preemptive frames (1 frame) | no | no | yes |
| apt and man-db running by themselves | don't exist (Arch) | masked | masked |

**What each tweak does:**

- **`mitigations=off audit=0`** — GA's default line. Turns off the kernel's Spectre/Meltdown protections, which cost the most on the older CPUs (without hardware fixes) typical of cabinets. It trades security for performance, acceptable on a machine that only runs games.
- **USB at 1000 Hz** — a full-speed controller is polled every 8 ms (125 Hz); the average wait drops from ~4 ms to ~0.5 ms. It applies to whatever uses the `usbhid` driver (Zero Delay/Xin-Mo style encoders, I-PAC as a keyboard, trackball); Xbox controllers use `xpad` and don't change. If a controller misbehaves, `usb_poll=default` in `/etc/fliperos/fliperos.conf` and applying the mode again restores the original polling.
- **`performance` governor** — frame delay counts on a fixed emulation time per frame; with the CPU raising its clock only after the load appears, that time varies. In the standard mode it only applies during the session (`fliperos-session` calls `fliperos-setup --session-start/--session-end`, like galauncher's `cpu_governor.sh`); in the low latency one, from boot (`fliperos-latency.service`).
- **`preempt=full`** — FliperOS's 6.18 kernel is `PREEMPT_DYNAMIC`; with this parameter it interrupts any kernel work to run the emulator, which Ubuntu's old `lowlatency` kernel did. It reduces the variation (jitter) more than the average.
- **Frame delay** (GroovyMAME's `autoframedelay`, RetroArch's `video_frame_delay_auto`) — the emulator waits part of the frame before emulating, and reads the controls closer to when the picture goes out: up to almost a frame (16.7 ms) less. The automatic one backs off by itself when the CPU can't keep up.
- **Preemptive frames** — removes the game's own internal delay (1 frame), redoing the last frame only when the input changes (lighter than run-ahead, which redoes every frame). It needs a core with savestates; those without turn the feature off with a warning.
- **apt and man-db** — Ubuntu's timers would run `apt update` and the `man` reindexing in the middle of a game. Updating lives in Setup > System Update, as in GA.

**What was left out, and why:** a `PREEMPT_RT` kernel (GA has a `linux-rt`), because `preempt=full` covers cabinet use and RT trades throughput for predictability, which is only worth it with measurements showing a gain; limiting the CPU C-states, because the gain would be microseconds when the CPU wakes up, against more power draw and heat; and RetroArch's `video_hard_sync`, because in KMS the 2-image swapchain already waits for each flip.

**Compared with GA:** on the same hardware, expect a tie in Standard mode (with an advantage of a few ms from USB at 1000 Hz) and up to 1 to 2 frames less in RetroArch games in Low latency mode. A hand-tuned GA gets to the same place; the difference is that FliperOS ships this way out of the box.

## Recommended hardware

| Use | CPU | Memory and disk | GPU |
| --- | --- | --- | --- |
| **Standard** (up to PS1 and most of arcade) | x86-64 with 2 cores | 4 GB, 16 GB of disk | AMD with VGA or DVI-I output, within CRT_EmuDriver's range (HD 2000 to R7/R9 GCN 1.0) |
| **Low latency** | AVX2 (x86-64-v3: 4th-generation Intel Core, AMD Ryzen or newer), 4 threads, 3.0 GHz or more | 4 GB (8 GB better) | same |
| **Everything** (PS2, Model 3, Dreamcast) | 4 physical cores with AVX2 and single-thread PassMark ≥ 2000 (Core i7-7700, Ryzen 5 3600 or newer) | 16 GB, SSD | same: at CRT resolutions even the R7 240 exceeds PCSX2's minimum (G3D ≥ 600) |

The "Everything" tier follows the *Moderate* level of the [PCSX2 requirements](https://pcsx2.net/docs/setup/requirements), the heaviest emulator in the ISO; the stronger GPU PCSX2 asks for at that level is for upscaled resolution, which doesn't exist on a CRT. Cards without analog output (AMD after GCN 1.0, recent NVIDIA) need a DisplayPort/HDMI to VGA converter.

**Checking the machine:** Setup > Latency shows the CPU, cores, clock, instruction level, memory, GPU and analog outputs, and **Check this computer** compares them with the Low latency mode minimum (`lib/hardware.sh`: x86-64-v3, 4 threads, 3.0 GHz, 4 GB). Choosing Low latency on a machine below that asks for confirmation.

## Measuring

The only reliable comparison is measuring, on the same cabinet, the same game and the same emulator version. Film the button and the screen together with a phone in 240 fps slow motion (~4 ms per video frame), 20 to 30 presses per configuration, and count the video frames between the button going down and the picture reacting.
