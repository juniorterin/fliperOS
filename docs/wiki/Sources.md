Current GroovyArcade code, on the `groovyarcade` group's GitLab:

- `gasetup` `2dbaa5297c716b4f32b0b55d5439c1f08f8cedda` — `core/procedures/interactive` (isomainmenu, mainmenu, setup; audio: `worker_audio_menu`, `worker_set_volume`, `worker_audio_latency`), `core/libs/lib-video.sh`, `lib-install.sh`, `lib-network.sh`, `lib-troubleshoot.sh`; latency: `core/libs/lib-bootloaders.sh` (default kernel line), `core/configs/groovymame/groovymame.sh` and `core/configs/retroarch/retroarch.sh`
- `tools/gatools` `28cef9faeec9d85d001ea5259af2d7e2fa343430` — `video/video.sh` (output test, Testing results), `video/monitor.sh`, `video/inform.sh`
- `tools/galauncher` `7e4950e3a4b92faf5eeebcae7c3a29a9e73689be` — `startfe.sh`, `videodata.conf`, `modules/cpu_governor.sh`
- `os` `59670f3d476331e7c18bc3a03fea6e7860fa1b7a` — boot menu, `.bash_profile`, LXDE, AntiMicroX, QJoyPad
- `packages` `608bd30c3799c6a14c0b21823c53919c40ab8e9a` — `linux-15khz` kernel, `switchres` (`rebuild_edids`, `geometry`), `skyscraper`

Latency option names checked against current code: [GroovyMAME](https://github.com/antonioginer/GroovyMAME) `953db38` (`src/emu/emuopts.h`: `lowlatency`, `autoframedelay`, `framedelay`) and [RetroArch](https://github.com/libretro/RetroArch) `6fe0b87` (`settings/settings_def_frame_delay.h`, `settings_def_video_sync.h`, `configuration.c`).

Also: [Switchres](https://github.com/antonioginer/switchres) (`geometry.py`, `edid.cpp`, `switchres.ini`), [D0023R/linux_kernel_15khz](https://github.com/D0023R/linux_kernel_15khz) `ece6ef15eca9480eaf75870a44764f47118e9cfe`, [Gum](https://github.com/charmbracelet/gum) v2.0.2 and [Dracula](https://draculatheme.com) ([dracula/gtk](https://github.com/dracula/gtk) `71640b9456110f3bac2130d0b387a3154a9fb4d2`, [dracula/zsh](https://github.com/dracula/zsh) `a3e27d47ea2ed1e3b435f44aa71caf71d3219af6`, [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh) `4d4cfc287e9d887b81242c0e431b5f49f9cec5c1`; the RGUI theme is `RGUI_THEME_DRACULA` in RetroArch's `menu/menu_defines.h`; GroovyMAME's UI color options are in `src/frontend/mame/ui/moptions.cpp`).
