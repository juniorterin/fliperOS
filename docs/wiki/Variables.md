The options, environment variables, recipe fields, secrets and state files a developer meets, with where each is defined and what it does. Defaults are the ones in the code.

## ISO build options

`fliperos-mkiso.sh` takes these on the command line (run it as root, in the build container). The table with what each one removes is in [Build and tests](Build-and-tests.md#build).

| Option | Default | Effect |
| --- | --- | --- |
| `--output FILE` (or a `*.iso` argument) | `/tmp/fliperos-VERSION.iso` | Where the ISO is written |
| `--skip-switchres`, `--skip-groovymame`, `--skip-retroarch`, `--skip-flycast`, `--skip-pcsx2`, `--skip-keisho`, `--skip-dolphin`, `--skip-hypseus`, `--skip-openbor`, `--skip-skyscraper` | all included | Leaves that part out of the image |
| `--skip-input-drivers` | included | Without the GunCon 2 and wheel drivers |
| `--skip-wheel-drivers` | included | Without only the wheel drivers |
| `--kernel-cache DIR` | `/output/kernel-cache` when `/output` exists | Where the kernel `.deb`s are kept and reused |
| `--repo DIR` | `/output/repo` when it exists | The APT repository of packages carried into the image |
| `--splash NAME` | `fliperos-text` | `fliperos-text`, `fliperos`, `evangelion` or `none` |
| `--wifi-ssid`, `--wifi-psk` | none | Saves a Wi-Fi network in the image; the password is stored as plain text |

`--skip-wine`, `--skip-steam`, `--skip-heroic` and `--with-wheel-drivers` are accepted and ignored.

## Build variables

| Variable | Where | What it is |
| --- | --- | --- |
| `FLIPEROS_VERSION` | `fliperos-mkiso.sh` | The ISO's version. The release tag has to equal it, and `CHANGELOG.md` has to start with its section |
| `FLIPEROS_REPO` | `fliperos-mkiso.sh` | The package repository folder (set by `--repo`) |
| `KERNEL_CACHE` | `fliperos-mkiso.sh` | The kernel cache folder (set by `--kernel-cache`) |
| `UBUNTU_CODENAME`, `UBUNTU_MIRROR` | `fliperos-mkiso.sh` | `noble` and `http://archive.ubuntu.com/ubuntu`: the base the image is made from |
| `FLIPEROS_ROOTFS_CHROOT` | `fliperos-rootfs.sh` | Set to `1` by `fliperos-mkiso.sh` when `fliperos-rootfs.sh` runs in the build chroot, where `/proc/1` does not exist, so it still compiles the schemas and the alternatives |

## Kernel

In `fliperos-kernel.sh` (`bash fliperos-kernel.sh key` prints the cache key, `build OUTPUT` compiles):

| Variable | What it is |
| --- | --- |
| `KERNEL_VERSION` | The kernel.org version (`6.18.54`) |
| `KERNEL_SERIES` | The series, taken from `KERNEL_VERSION` |
| `KERNEL_BUILD` | Rises with every new or changed patch. The kernel becomes `6.18.54-15khz.N`, a new package installed beside the previous one, which Limine keeps as the previous kernel |
| `KERNEL_PATCHES_SHA256` | The hash of the patches of this build. `test_build.py` fails if the patches change without `KERNEL_BUILD` rising |

The cache key changes with the version, a patch or the script, and a build with the same key reuses the `.deb`s. See [15 kHz kernel](Kernel-15-kHz.md).

## Recipe fields

Set in `packaging/packages/NAME.sh`; `packaging/build-deb.sh` reads them. See [Packages](Packages.md).

| Field | What it is |
| --- | --- |
| `PKG_NAME` | The package name (required) |
| `PKG_VERSION` | The upstream version (required). No `+` or `:` |
| `PKG_REVISION` | The package revision, default `1`. Raise it on every change |
| `PKG_SUMMARY`, `PKG_DESCRIPTION` | The one-line and the long description |
| `PKG_SECTION` | The Debian section, default `games` |
| `PKG_HOMEPAGE` | The project's address |
| `PKG_BUILD_DEPS` | The packages `apt-get` installs before building |
| `PKG_SHLIB_TARGETS` | The binaries (paths inside the package) that `dpkg-shlibdeps` reads to compute `Depends` |
| `PKG_RUNTIME_EXTRA` | Dependencies added by hand, such as a library opened with `dlopen` |
| `PKG_ON_DEMAND` | `1`: not in the ISO, built on the cabinet when chosen |
| `PKG_UPSTREAM` | The project's address, for the newest-version mode |
| `PKG_COMMIT_VAR` | The recipe variable that holds the commit or tag to build in that mode |
| `PKG_EDGE_TAGS` | A regex of the stable tags to choose from (Dolphin) |
| `PKG_EDGE_RELEASE` | Use the latest GitHub release (PCSX2) |
| `PKG_EDGE_WAIT` | How long the newest-version build takes, when it is not minutes |

Inside `pkg_build()`: `SRC` is where to compile, `STAGING` is the package's root, and `FLIPEROS_EDGE=1` marks a newest-version build, where the pinned commit is not the one being built.

## Publishing

| Name | Where | What it is |
| --- | --- | --- |
| `FLIPEROS_GH_REPO` | `tools/publish-packages.sh` | The GitHub repository of the release, default `juniorterin/fliperOS` |
| `FLIPEROS_KERNEL_DIR` | `tools/publish-packages.sh` | Where the kernel `.deb`s are, default `output/kernel` |
| `FLIPEROS_PACKAGES_URL` | `updates/packages-sync.sh` | Where a cabinet downloads packages from, default the `packages` release of the repository |
| `FLIPEROS_PACKAGES_CACHE` | `updates/packages-sync.sh` | The cabinet's download cache, default `/var/cache/fliperos/packages` |
| `FLIPEROS_PACKAGES_ARCH` | `updates/packages-sync.sh` | The architecture of the file names, default `amd64` |
| `FLIPEROS_VERIFY_DIR` | `tools/verify-iso.sh` | A folder to extract the ISO into, for whoever uses the result afterwards |
| `FLIPEROS_USER`, `FLIPEROS_PASSWORD` | `tools/cabinet-push.sh` | The cabinet's login to send files over SSH, default `fliperos` and `fliperos` |

## GitHub secrets and variables

| Name | Where | What it is |
| --- | --- | --- |
| `GITHUB_TOKEN` | Release workflow | The workflow's own token, used to publish the release |
| `TELEGRAM_BOT_TOKEN` | Secret, Telegram workflow | The token of the bot (from @BotFather) that is an administrator of the group. Without it nothing is posted and the workflow only warns |
| `TELEGRAM_CHAT_ID` | Repository variable | The group to post in; `@fliperos15khz` when it is not set |
| `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET` | Secrets, Release workflow | The Google sign-in of the cloud backup. They go into `/etc/fliperos/google-oauth.conf` through `tools/google-oauth-conf.sh`; without them the file is empty and the cabinet downloads it from the `packages` release |

## On the cabinet

| Variable | Where | What it is |
| --- | --- | --- |
| `FLIPEROS_CONF` | many `config/` commands | The settings file, default `/etc/fliperos/fliperos.conf` |
| `FLIPEROS_ETC` | `config/fliperos-roms`, `-tty1`, `-automount` | The settings folder, default `/etc/fliperos` |
| `FLIPEROS_USER` | `config/fliperos-emulators`, `-arcadeflow` and others | The arcade user whose home they work on, default `fliperos` |
| `FLIPEROS_UI` | `fliperos-setup/lib/ui.sh` | `text` or `gui`: forces the Setup's interface (`ui=` in `fliperos.conf` does the same) |
| `FLIPEROS_LOG` | `fliperos-setup/lib/common.sh` | The Setup's log, default `/var/log/fliperos-setup.log` |
| `FLIPEROS_NO_SPEECH` | `fliperos-setup/lib/speech.sh` | `1` turns the spoken prompts off |
| `FLIPEROS_UPDATE` | `config/fliperos-update` | `1` while an update runs: `tools/cabinet-update.sh` then does not take the update lock a second time |
| `FLIPEROS_RECIPES`, `FLIPEROS_EDGE_STATE`, `FLIPEROS_EDGE_WORK` | `config/fliperos-emulators` | Where the newest-version mode finds the recipes, keeps its state and builds. Defaults `/usr/local/share/fliperos/packaging/packages`, `/var/lib/fliperos/edge`, `/var/cache/fliperos/edge` |

## Picture filters and the on-screen menu

These are read by the preloaded libraries and the commands that draw over a game ([Interlaced, colour and scanlines](Picture-filters.md), [On-screen menu](On-screen-menu.md)).

| Variable | What it is |
| --- | --- |
| `FLIPEROS_DEFLICKER` | `off`, `light`, `medium` or `strong`: overrides the interlaced filter level |
| `FLIPEROS_DEFLICKER_FORCE` | `1` filters in any video mode, not only interlaced |
| `FLIPEROS_DEFLICKER_DEBUG`, `FLIPEROS_DEFLICKER_QUIET` | Print what the filter does, or keep it silent |
| `FLIPEROS_DEFLICKER_APP` | The program's name (the one in the `fliperos-x11-run` table), so each program has its own setting |
| `FLIPEROS_DEFLICKER_FILE` | A file with the filter level, read again every 30 frames (the Setup's preview changes the level on the spot) |
| `FLIPEROS_SCANLINES_FILE` | A file with the scanline settings, read again every 30 frames and active on any monitor (the preview) |
| `FLIPEROS_COLOR_FILE` | A file with the colour settings (saturation and hue), read again every 30 frames (the calibrator) |
| `FLIPEROS_OSD_FILE` | The on-screen menu's picture, `/run/fliperos-osd/screen`, which exists only while the menu is open |
| `FLIPEROS_GUN_DEVICES` | The light-gun input events to read, separated by `:` (for the tests) |
| `FLIPEROS_VK_FPS` | `1` loads the Vulkan layer that counts frames for the web panel (set by `fliperos-kms-run` and `fliperos-x11-client`) |
| `FLIPEROS_FPS_FILE` | The file the frame counter writes each second, instead of `$XDG_RUNTIME_DIR/fliperos-fps` |

## Tests and tools

| Variable | Where | What it is |
| --- | --- | --- |
| `FLIPEROS_GUI_HEADLESS` | `fliperos-setup/gui/serve.py` | `1` runs the graphical Setup without video, for the tests |
| `FLIPEROS_GUI_KEYS` | `fliperos-setup/gui/serve.py` | The keys the GUI presses, in order |
| `FLIPEROS_GUI_SHOTS` | `fliperos-setup/gui/serve.py` | A folder where each screen is saved as a PNG |
| `FLIPEROS_GUI_BG` | `fliperos-setup/gui/background.py` | Fixes the GUI's background instead of picking one |
| `FE_EMU_PORT`, `FE_EMU_SIZE` | `tools/fe-emulator/run.sh` | The frontend emulator's browser port (`6080`) and screen size (`960x720`) |
| `MSYS_NO_PATHCONV` | Git Bash | `1` stops Git Bash rewriting the paths of a Docker mount |

## State files

| File | What it is |
| --- | --- |
| `updates/index` | One line per update: number, commit, tree hash, reboot, title |
| `updates/packages.list` | Name, version, sha256 and `always`/`installed` of each package of the ISO |
| `updates/notes/NNNN.md`, `updates/notes/pt-BR/NNNN.md` | The notes of an update, in English and Portuguese |
| `docs/telegram/VERSION.md`, `docs/telegram/update-NNNN.md` | The Telegram posts, with pictures |
| `CHANGELOG.md` | The text of each release |
| `/etc/fliperos/patch-level` | The cabinet's update level |
| `/var/log/fliperos-update.log` | The cabinet's update log |
| `/var/lib/fliperos/update/manifest` | What FliperOS installed, to tell the user's own changes apart |
| `/etc/fliperos/fliperos.conf` | The cabinet's settings |

## How it works

- Command-line options are parsed at the top of each script (`fliperos-mkiso.sh` takes them in a `case`), and `--help` prints the usage.
- Environment variables with a default use `${NAME:-default}`, so a test or a developer overrides one without editing the file.

See also: [Build and tests](Build-and-tests.md), [Packages](Packages.md), [Commands](Commands.md), [Development](Development.md).
