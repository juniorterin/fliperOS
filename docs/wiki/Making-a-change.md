How a change goes from an idea to the repository, and from there to a cabinet: where the code lives, which tests to run, how to try it on a real machine without building an ISO, and what else to touch.

## Where the code lives

| Change | Where |
| --- | --- |
| A Setup screen or option | `fliperos-setup/screens/*.sh` (the screens) and `fliperos-setup/lib/*.sh` (what they call) |
| The graphical Setup and the frontend | `fliperos-setup/gui/` (pygame): `fliperos-frontend`, `feview.py`, `theme.py` |
| A command, a service or a file in the installed system | `config/` (installed by `fliperos-rootfs.sh`) |
| What goes into the image and how | `fliperos-mkiso.sh`, `fliperos-rootfs.sh`, `fliperos-kernel.sh` |
| A compiled program | `packaging/packages/NAME.sh` and `packaging/patches/NAME/` ([Packages](Packages.md)) |
| What a network update does | `updates/` and `tools/cabinet-update.sh` ([Publishing updates](Publishing-updates.md)) |
| The web panel | `config/fliperos-web` and `config/web/` |
| The docs | `docs/wiki/`, `README.md`, `README.pt-BR.md`; the site is in `website/` |

A new Setup menu item also needs an icon in `fliperos-setup/gui/theme.py` (a test fails without it). Text that does not fit a row runs on the selected row (`feview.ticker`); it is not cut.

## Testing it

Run the tests in Docker, after [checking Docker's health](Development-environment.md):

```powershell
docker build -t fliperos-tests -f tests/Dockerfile tests
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_setup.py
docker run --rm -v "${PWD}:/w" -w /w fliperos-tests python3 tests/test_build.py
```

- `tests/test_setup.py` runs the logic of `fliperos-setup` against a fake system.
- `tests/test_build.py` checks the boot menu, kernel pins, image files, the recipes, the release text and the docs (`DocsTests`).
- Run both whenever a screen or a file in `config/` changes. A hint balloon in a screen has to fit two lines of 34 columns, and `test_setup.py` checks it.
- A screen can be seen as text with `tools/ui-snapshot.sh SCREEN`, and the frontend runs on a PC with `sh tools/fe-emulator/run.sh`. Both are in [Build and tests](Build-and-tests.md#tests).

## Trying it on a cabinet

An ISO takes hours, so a change is tried on an installed machine. From the repository, in the `fliperos-ssh` container:

```powershell
docker build -t fliperos-ssh -f tools/Dockerfile.ssh tools
docker run --rm -v "${PWD}:/w:ro" -w /w fliperos-ssh sh tools/cabinet-push.sh 192.168.1.111
```

`tools/cabinet-push.sh` sends `fliperos-setup`, `config/`, `packaging/`, `fliperos-rootfs.sh` and `updates/`, and runs `tools/cabinet-update.sh` there. The cabinet's address can change: check it (`fliperos.local`) before assuming the old one. A file you put on a cabinet by hand is overwritten by the next update.

## A change that needs a generated file

A change that only works after a file is generated (an EDID, the initramfs, a `modprobe.d` file) needs a step that generates it on the machines that already have that setting, like `boot_apply` in `tools/cabinet-update.sh`. Installing the new scripts is not enough. See [Publishing updates](Publishing-updates.md#a-change-that-needs-a-generated-file).

## Style guide

`docs/styleguide/index.html` is a page only for the people who work on FliperOS: open it in a browser (it uses the web panel's own stylesheets, by relative path). It shows the colour tokens of the web panel and of the Setup's theme side by side, the type and radius scales, every icon of the sprite, the components (buttons, tags, chips, setting rows, meter, cards, toast, fields) rendered by the real CSS, the rules (two languages, an icon for every menu item, text that doesn't fit runs) and an **audit**: loose colours, font sizes and radii that are not on the scale, tokens with the same value, and a panel colour that is not the Setup's colour.

Run `python3 tools/styleguide.py` (in the tests image, `docker run --rm -v "$(pwd -W):/w" -w /w fliperos-tests-pil python3 tools/styleguide.py`) after changing `config/web/*.css`, `config/web/icons.svg` or `fliperos-setup/gui/theme.py`, and commit the new page. `StyleguideTests` checks that the page lists every token and icon.

## Finishing

1. Document it on the page of its subject, not on an index page ([Build and tests](Build-and-tests.md#writing-the-wiki) has the rules).
2. Commit and push to `main`. Commit only your own files.
3. If cabinets that are already installed need it, publish an update ([Publishing updates](Publishing-updates.md)). If it is a compiled program, publish the package first ([Packages](Packages.md#publishing)).
4. If it belongs in the next version, add it to the `CHANGELOG.md` section when you make the release ([Making a release](Making-a-release.md)).

## Problems

- **The tests fail on a file you did not touch.** Another person's unfinished work is in the same checkout; run the tests on a clean `git worktree` of `HEAD`.
- **A change works through `cabinet-push.sh` but not after an update.** An update carries only `fliperos-setup`, `config`, `updates`, `fliperos-rootfs.sh`, `fliperos-video-check.py`, `fliperos-limine-update.py` and `tools/cabinet-update.sh`. A file anywhere else (`tools/`, `packaging/`) never reaches a cabinet that way. Put new files under `config/` or `updates/`.

## How it works

- `tools/cabinet-update.sh` runs the same `fliperos-rootfs.sh` as the build, then applies what the build does outside it: the bootloader, automatic login, DNS, the clock, packages and the kernel line. It keeps a copy of what it changes in `/root/fliperos-backup-DATE.tgz`.
- A network update downloads the files of one commit from GitHub and checks them against a hash of those paths (`TREE` in `config/fliperos-update`). Adding a path to `TREE` makes older cabinets compute another hash and refuse the update, so new files go under the paths already there.

See also: [Development](Development.md), [Architecture](Architecture.md), [Adding an emulator](Adding-an-emulator.md).
