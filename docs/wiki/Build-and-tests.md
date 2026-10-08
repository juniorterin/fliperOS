## Build

Always in Docker (`CLAUDE.md` forbids chroot with the host's `/dev` on WSL).

```powershell
docker build -f Dockerfile.fliperos -t fliperos-builder .
docker run --rm --privileged --mount "type=bind,source=$PWD/output,target=/output" fliperos-builder bash /build/fliperos-mkiso.sh --output /output/fliperos-0.8.3.iso
```

| Option | Effect |
| --- | --- |
| `--skip-groovymame`, `--skip-retroarch`, `--skip-flycast`, `--skip-pcsx2`, `--skip-supermodel` | Leaves the emulator out of the image (the compiled ones take minutes to hours; GroovyMAME and PCSX2 are the official releases) |
| `--skip-skyscraper` | Without the Setup's Scraper |
| `--skip-switchres` | Without Switchres: no per-monitor EDIDs, geometry or EDID boot entries |
| `--skip-input-drivers`, `--skip-wheel-drivers` | Without the input drivers (GunCon 2 and wheels), or only without the wheel ones. By default `guncon2`, `hid-tmff2` (Thrustmaster T150/T300/TX/T248...) and `new-lg4ff` (Logitech with full force feedback, replacing `hid-logitech`) ship, through DKMS — validated on the cabinet's 6.18 |
| `--kernel-cache DIR` | Where to store/reuse the kernel `.deb`s (default `/output/kernel-cache`) |
| `--splash fliperos-text\|fliperos\|evangelion\|none` | Plymouth theme (default `fliperos-text`) |
| `--wifi-ssid NAME --wifi-psk PASSWORD` | Saves a Wi-Fi network in the image (**the password is stored as plain text in the ISO**; don't distribute it) |
| `--repo DIR` | APT repository of the frontends carried into the image (default `/output/repo`, if it exists) |

What doesn't exist in Ubuntu 24.04 is downloaded with a pinned version and hash: Limine 11.4.1, Gum 2.0.2 (the `.deb` stays for the man pages; the binary is built from the same version's source with `patches/gum`, compiled with Go 1.26.7: ▲/▼ arrows instead of dots in the menus' pagination, the menu sounds and Space toggling in checklists — gum 2.0.2 only knows the key as `" "`, and its library calls it `space` —, put in place of `/usr/bin/gum` with `dpkg-divert`), AntiMicroX 3.6.1 (official `.deb` for 24.04), Skyscraper 3.21.0 (Gemba fork, compiled with Qt6).

Audit of the generated ISO (read-only): checks the boot menu, kernel, setup files, libraries of the compiled programs, EDIDs and BIOS/UEFI boot.

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-vmtest bash tools/verify-iso.sh /w/output/fliperos-0.8.3.iso
```

## Release

Every new ISO goes to GitHub [Releases](https://github.com/juniorterin/fliperOS/releases), with the version's changelog, like GroovyArcade's releases ([substring/os](https://github.com/substring/os/releases)): the text by area (system, packages, `fliperos-setup`, tools) and, next to the ISO, the package list.

1. Write in `CHANGELOG.md` the `## VERSION` section with what changed since the previous release (`git log PREVIOUS_VERSION..HEAD` lists the commits). A new ISO after a release needs a new version (`FLIPEROS_VERSION` in `fliperos-mkiso.sh`).
2. Commit and push.
3. Tag the version and push the tag (the name is the version, without "v"):

   ```powershell
   git tag 0.8.3
   git push origin 0.8.3
   ```

Pushing the tag triggers the GitHub Actions **Release** workflow (`.github/workflows/release.yml`). It checks that the tag is `FLIPEROS_VERSION` and that `CHANGELOG.md` has its section, builds the frontends repository (`Dockerfile.packages`) and generates the ISO with the same `Dockerfile.fliperos` as the local build. Then it publishes through `tools/release-publish.sh`, with the workflow's own token. The kernel and frontend `.deb`s stay in the Actions cache, so they only recompile when the version, a patch or a recipe changes. Without the cache, the build takes about 3 hours on a 4-core runner (the limit is 6 h). If it fails, `fliperos-mkiso.log` is kept as a workflow artifact. Run by hand (*Actions > Release > Run workflow*), it generates the ISO of the current version and keeps it as an artifact for 3 days, without publishing.

To publish an ISO generated here, in the audit container:

```powershell
docker build -t fliperos-vmtest -f tools/Dockerfile.vmtest tools
docker run -it --rm -v fliperos-gh:/root/.config/gh fliperos-vmtest gh auth login
docker run --rm -v "${PWD}:/w:ro" -v fliperos-gh:/root/.config/gh -w /w fliperos-vmtest bash tools/release-publish.sh /w/output/fliperos-0.8.3.iso
```

`gh auth login` is a one-time step: the login stays in the `fliperos-gh` volume.

`tools/release-publish.sh` only publishes what can go public:

- the ISO goes through the audit (`tools/verify-iso.sh`), so it is the one from the current repository — an old ISO, generated before the latest commits, is rejected;
- an ISO with a saved network (`--wifi-ssid`, `--wifi-psk`) is rejected: the password would go with it;
- without the version's section in `CHANGELOG.md`, nothing is published;
- an existing release isn't replaced without `--replace` (deletes and publishes again).

GitHub accepts up to 2 GiB per file, and the ISO stays below that. The build's `slim_rootfs_chroot` removes the `-dev` packages and the build tools, but keeps `build-essential`, `dkms` and the kernel headers, which the DKMS drivers use. No `autoremove`, because the Qt plugins and Vulkan come in through `dlopen` and don't show in `ldd`; the libraries `ldd` shows are marked as manually installed, and an `ldd` before and after fails the build if any is missing. The apt cache and lists also go, as does the out-of-scope firmware (NVIDIA, Mellanox, Marvell Prestera, Qualcomm, QLogic), through a dpkg `path-exclude` so an update doesn't bring it back. The squashfs is xz. Wine, Steam and Heroic aren't in the image: Setup > Extras installs them (`config/fliperos-extras`). If the ISO goes over 2 GiB, it is split into 1900 MiB parts (`fliperos-0.8.3.iso.001`, `.002`...), and the release text gets the instructions to join them (`copy /b` on Windows, `cat` on Linux). Also published: `fliperos-0.8.3.sha256` (the whole ISO and each part) and `fliperos-0.8.3-pkglist.txt` (package, version and architecture of what's in the image). `--prerelease` marks it as a pre-release; `--to FOLDER` only prepares the files and the text (`notes.md`), without touching GitHub; `--notes VERSION` shows the version's text.

## Tests

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

- `tests/test_setup.py` — the logic of `fliperos-setup` with fake DRM sysfs, EDIDs, `lsblk`, `nmcli` and `aplay`, on the same Ubuntu (and the same `mawk`/`jq`) as the ISO.
- `tests/test_build.py` — boot menu, kernel and patches, pins, image files, the installed disk's Limine, `fliperos-video-check`.
- `tools/ui-snapshot.sh SCREEN [WIDTH HEIGHT]` — captures a screen as text in an 80x30 tmux (or 64x24, 25 kHz's 512x384), with a fake system (`tools/ui-demo.sh`).
- `tools/vm-test.py install ISO` — in QEMU: installs through the setup's lib onto a disposable disk and boots the disk on BIOS and UEFI. `tools/vm-test.py screens ISO` and `tools/vm-monitor.py` capture the real tty1 (Gum on the Linux console) screen by screen. `tools/vm-test.py desktop ISO` opens LXDE on the installed disk (from boot and from the menu, with the 15 kHz `xorg.conf`). `tools/vm-test.py dev ISO` takes the current repository's files to the installed disk, without a new ISO, and drives the menu with a fake gamepad (`tools/vm-fakepad.py`, uinput) up to the desktop, the resolution change and the quirks.
- **Updating the cabinet without a new ISO** (over the network, with the default login):

  ```powershell
  docker build -t fliperos-ssh -f tools/Dockerfile.ssh tools
  docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-ssh sh tools/cabinet-push.sh 192.168.1.111
  ```

  `tools/cabinet-push.sh` sends the setup, `config/`, `fliperos-rootfs.sh` and the frontends repository; there, `tools/cabinet-update.sh` keeps a copy of what changes in `/root/fliperos-backup-DATE.tgz`, runs the same `fliperos-rootfs.sh` as the build and applies what comes from outside it: `fliperos-limine-update`, automatic login, DNS, clock, new packages (through apt), kernel line and services. At the end it restarts tty1.

## Website

The project website lives in [`website/`](https://github.com/juniorterin/fliperOS/tree/main/website) (Next.js, server-rendered, English and Portuguese). `npm run dev` inside the folder serves it locally; the `Dockerfile` there builds the standalone server that Coolify (or any Docker host) runs on port 3000. Its README has the details.
