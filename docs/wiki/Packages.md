The compiled programs of FliperOS (RetroArch, Flycast, Dolphin, GroovyMAME, Keisho, PCSX2, OpenBOR, Gum, SDL2 for KMS, Attract-Mode Plus, RAHasher) are `.deb` packages built from recipes in `packaging/packages/`. The ISO installs them from a local repository, and the network updates download the very same files, so someone who installed the ISO and someone who only applied updates end up with the same binary.

## A recipe

`packaging/packages/NAME.sh` is a Bash file that sets the package's fields and defines `pkg_build()`. The fields are listed in [Variables](Variables.md#recipe-fields); the shape is:

```bash
PKG_NAME="fliperos-example"
PKG_VERSION="1.2.3"
PKG_REVISION="1fliperos1"
PKG_SUMMARY="One line"
PKG_DESCRIPTION="Longer text"
PKG_BUILD_DEPS="build-essential pkg-config git ca-certificates libfoo-dev"
PKG_SHLIB_TARGETS="usr/local/bin/example"   # where dpkg-shlibdeps looks for the Depends
COMMIT="0123456789abcdef0123456789abcdef01234567"

pkg_build() {
  git init -q "$SRC/example" \
    && git -C "$SRC/example" fetch -q --depth 1 https://github.com/owner/example "$COMMIT" \
    && git -C "$SRC/example" checkout -q FETCH_HEAD || return 1
  make -C "$SRC/example" -j"$(nproc)" &&
    make -C "$SRC/example" install DESTDIR="$STAGING" || return 1
}
```

- `pkg_build` compiles into `$SRC` and installs into `$STAGING`, which becomes the package's contents. Chain the steps with `&&` and `return 1` on failure: the shell ignores `set -e` inside a function called with `||`.
- Pin the source to a commit or a release tag. The patches in `packaging/patches/NAME/` are checked against that exact version, and a new commit is a new version of the package.
- The `Depends` line is computed from the binaries listed in `PKG_SHLIB_TARGETS`, not written by hand. A library opened with `dlopen` does not show there: add it to `PKG_RUNTIME_EXTRA`.
- A recipe is for the Ubuntu 24.04 the ISO uses: building on another base produces wrong dependencies.

## Building

```bash
bash packaging/build-deb.sh --list         # every recipe
bash packaging/build-deb.sh --list-iso     # the ones that go in the ISO
```

It runs as root inside the `Dockerfile.packages` image (Ubuntu 24.04), which is how the Release workflow builds too. `tools/publish-changed-packages.sh` does it for you (below); by hand:

```bash
docker build -f Dockerfile.packages -t fliperos-packages .
docker run --rm -v "$PWD/output/packages:/pkg/output/packages" fliperos-packages bash packaging/build-deb.sh fliperos-example
```

The result is `output/packages/NAME_VERSION-REVISION_amd64.deb`. `--skip-existing` leaves a package whose file is already there alone, and `--output DIR` changes the folder. `bash packaging/make-repo.sh` turns the folder into the flat APT repository the ISO build carries (`output/repo`).

A rebuilt `.deb` is never byte-identical to the one built before. What counts is the published file's sha256.

## Versions

- **A changed recipe, patch or asset needs a new `PKG_REVISION`** (`1fliperos1` → `1fliperos2`). A `.deb` that is already published is never replaced: the same version with other contents would leave the cabinets that already have it on the old build.
- **A new upstream version** changes `PKG_VERSION` (and usually restarts the revision).
- The version has no `+` or `:`: GitHub renames them in asset names and the download then fails.
- A package that follows the project's HEAD (RetroArch, Flycast) puts the date in `PKG_VERSION`, so each new commit sorts higher.

## Publishing

Packages are published to the `packages` release of the GitHub repository, and `updates/packages.list` says which version, with which sha256, each cabinet should have:

```
NAME<TAB>VERSION<TAB>SHA256<TAB>WHEN
```

`WHEN` is `always` (every cabinet gets it, as the ISO does) or `installed` (only a cabinet that already has the package is raised). A new package enters as `installed`; after it is tested on a cabinet, change it to `always` by hand and publish an update.

Run it in WSL, from the repository (`gh` is logged in only there), after [checking Docker's health](Development-environment.md):

```bash
tools/publish-changed-packages.sh                       # shows the state of each package
tools/publish-changed-packages.sh --run                 # builds what changed, publishes, commits and pushes the list
tools/publish-changed-packages.sh --run --bump          # first raises the revision of the ones that changed without one
tools/publish-changed-packages.sh --run --bump NAME…    # rebuilds the named ones with a new revision
```

| State | Meaning |
| --- | --- |
| em dia | The recipe, its patches and its version match the list |
| versão nova | `PKG_VERSION`/`PKG_REVISION` differ from the list: it is built |
| pacote novo | Not in the list yet: it is built and enters as `installed` |
| sem revisão | The recipe or its patches changed since the list's row was written, with the same revision: needs `--bump` |

Comments and the `PKG_UPSTREAM`, `PKG_COMMIT_VAR` and `PKG_EDGE_*` fields do not count as a change (they do not alter the `.deb`). `--force` builds even if another container is running, `--no-commit` leaves the commit of the list for later.

The routine checks `tools/docker-health.ps1` and `docker ps` before building, builds only what is needed, and runs `tools/publish-packages.sh`, which:

- uploads each `.deb` that is not on the release yet and rewrites `updates/packages.list` (a package already published keeps its published sha256);
- keeps a copy of the on-demand packages (below) and of the 15 kHz kernel's `.deb`s on the release, outside the list;
- accepts a package that is not built here if that exact version is already published.

After the push, an update has to carry the new list to the machines: see [Publishing updates](Publishing-updates.md) and [Making a release](Making-a-release.md).

## Programs built on demand

A recipe with `PKG_ON_DEMAND=1` is not in the ISO and not in the list: the Setup builds the program on the cabinet when someone chooses it (`config/fliperos-frontend-build`). EmulationStation (ES-DE) and Pegasus are like that. Their `.deb` is still kept on the release as a copy.

## The newest version of a program

**Setup > Games > Emulators & Games** can build the newest version of a packaged emulator on the cabinet with the same recipe (`fliperos-emulators edge NAME`). A recipe supports it with:

- `PKG_UPSTREAM`: the project's address;
- `PKG_COMMIT_VAR`: the variable of the recipe that holds the commit or tag to build;
- `PKG_EDGE_TAGS` (a regex of the stable tags, for Dolphin) or `PKG_EDGE_RELEASE` (the latest GitHub release, for PCSX2); without either, the project's HEAD.

The package's files are kept aside with `dpkg-divert`, so updates keep replacing the package without erasing the newer build, and `fliperos-emulators edge-off NAME` goes back to it. A patch that does not fit the newer code stops the build and the package stays.

## If an upstream disappears

The published `.deb` stays installable: a cabinet downloads it from the release, not from the project. What is lost is the ability to rebuild with another version. For that, the recipe's pinned source has to be reachable, so keep an eye on the projects the recipes pull from.

## Problems

- **`publish-packages: … is missing: build it first`.** The package is in the recipes but its `.deb` is not in `output/packages` and not published at that version. Build it.
- **`the local build differs; the published one stays`.** Normal: only the published file counts. Raise the revision if the code changed.
- **A cabinet does not get a package.** Look at its row: `installed` skips a cabinet that does not have the package yet. `packages-sync.sh` also skips a file whose sha256 does not match the list.
- **The test on the list fails.** `updates/packages.list` has to have one row for each recipe of `--list-iso`, with the recipe's version and no other rows.

## How it works

- `updates/packages-sync.sh` runs during an update, on the cabinet: for each row, if the package is missing (and the row is `always`) or older, it downloads `NAME_VERSION_amd64.deb` from the release (`FLIPEROS_PACKAGES_URL`), checks the sha256, caches it in `/var/cache/fliperos/packages` and prints the path for `tools/cabinet-update.sh` to install.
- The Release workflow gets the packages the same way: it downloads from the release each file the list names, checks the sha256, and compiles only the recipes that have no file yet. The ISO and the updates therefore carry the same binaries. The build's cache key is the hash of `packaging/` and `Dockerfile.packages`.
- Packaged emulators write their version to `/usr/local/share/fliperos/emulator-versions.d/NAME`, which `config/fliperos-emulators` reads first.

See also: [Making a release](Making-a-release.md), [Publishing updates](Publishing-updates.md), [Adding an emulator](Adding-an-emulator.md), [Development](Development.md).
