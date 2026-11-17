Everything a programmer needs to work on FliperOS: setting up the machine, making and testing a change, building the ISO, packaging a program, publishing an update and cutting a release. The user's side of the project starts at [Home](Home.md).

FliperOS is built on Windows with Docker, from one repository: the ISO build scripts, `fliperos-setup` (the Bash and Gum setup, and the pygame GUI), the `config/` files that land in the installed system, the `.deb` recipes in `packaging/`, the tests in `tests/`, and the network updates in `updates/`. [Architecture](Architecture.md) says what each file is.

## I want to…

| I want to… | Read |
| --- | --- |
| Set up a machine to work on it, and know what not to do | [Development environment](Development-environment.md) |
| Change or add a feature, test it and get it into the repository | [Making a change](Making-a-change.md) |
| Add an emulator to the Setup and the frontends | [Adding an emulator](Adding-an-emulator.md) |
| Build the ISO, or check one | [Build and tests](Build-and-tests.md#build) |
| Change a compiled program, or add one | [Packages](Packages.md) |
| Put a new `.deb` on GitHub | [Packages](Packages.md#publishing) |
| Send a change to machines that are already installed | [Publishing updates](Publishing-updates.md) |
| Release a new version | [Making a release](Making-a-release.md) |
| Find what a variable or an option does | [Variables](Variables.md) |
| Change the 15 kHz kernel | [15 kHz kernel](Kernel-15-kHz.md) |

## Pages

| Page | What it covers |
| --- | --- |
| [Development environment](Development-environment.md) | What runs where on Windows, the rules that keep the build from breaking the machine, working in the same repository as other people |
| [Making a change](Making-a-change.md) | Where the code lives, running the tests, trying a change on a cabinet without a new ISO, writing the docs, committing |
| [Packages](Packages.md) | The `.deb` recipes: anatomy, building, versions, publishing to the `packages` release, programs built on demand, the newest-version mode |
| [Making a release](Making-a-release.md) | The whole release in order: packages, update, changelog, version, tag, the build and the posts |
| [Build and tests](Build-and-tests.md) | Building the ISO in Docker, the options, the audit, the release workflow, the tests, the frontend emulator |
| [Publishing updates](Publishing-updates.md) | Making a network update and lining it up with a new ISO |
| [Variables](Variables.md) | The options, environment variables, recipe fields, secrets and state files |

## How it works

- The same code builds the ISO and the updates: `fliperos-rootfs.sh` installs `fliperos-setup` and `config/` into the image, and `tools/cabinet-update.sh` applies them again on an installed machine.
- Compiled programs are `.deb` packages from `packaging/packages/`. The ISO carries them in a local repository; the updates download the same files from the `packages` release on GitHub.
- A release is a tag: pushing it starts the **Release** workflow, which builds the ISO and publishes it. Updates are lines in `updates/index`, published by `tools/make-update.sh`.
- The repository's `CLAUDE.md` holds the rules that came from real failures (the build, Docker, releases). [Development environment](Development-environment.md) and [Making a release](Making-a-release.md) explain them.

See also: [Architecture](Architecture.md), [Commands](Commands.md), [Sources](Sources.md).
