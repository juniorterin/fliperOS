How a FliperOS update is made and published, and how it has to line up with a new ISO. What a cabinet does with it is on [Updates and versions](Updates-and-versions.md).

## What an update is

Each update is a repository commit, listed in `updates/index` with a number, its commit, the hash of its files, whether it needs a restart, and a title:

```
N<TAB>commit<TAB>treehash<TAB>reboot<TAB>title
```

| File | What it is |
| --- | --- |
| `updates/notes/NNNN.md` | The changelog the cabinet shows before asking (required), in English |
| `updates/notes/pt-BR/NNNN.md` | The same in Portuguese, for the Telegram post |
| `updates/NNNN.sh` | Optional: steps that aren't a file copy (rebuilding something, moving a file) |
| `docs/telegram/update-NNNN.md` | Optional: the Telegram post with pictures |
| `updates/packages.list` | The FliperOS packages of the newest ISO, which updates also install |

The cabinet downloads the files of that commit from GitHub over HTTPS and checks each one against the treehash before writing anything. Updates are always applied in order.

## Publishing one

1. Commit everything the update brings, and push it: the commit has to be on `origin/main`, where the cabinets download it.
2. Write `updates/notes/NNNN.md` (and the pt-BR copy) with what changes, in words a player understands.
3. Run, where there is a Linux `python3` (on Windows, through WSL):

   ```bash
   tools/make-update.sh "Title shown on the cabinet" [--reboot]
   ```

   It appends the line to `updates/index`, commits and pushes it, and posts the update to the [Telegram group](https://t.me/fliperos15khz) in Portuguese and English.

`--reboot` marks an update that needs a restart to finish (a new kernel line, a new initramfs).

## A change that needs a generated file

A change that only works after generating a file on the cabinet (an EDID, the initramfs, a `modprobe.d`) needs a step in the update that generates it on the machines that already have that setting, like the `boot_apply` of `tools/cabinet-update.sh`. Installing the new scripts isn't enough: they run only when the setting changes.

## Updates and a new ISO end at the same point

Someone who installs a new ISO and someone who only applies the updates must end up with the same system. In 2026-11, version 0.20 came out 3 commits after update 39, and the cabinets at level 39 lacked those changes until update 40.

So, before tagging a version:

1. Publish the update that covers everything that changed in the system since the last one, and tag the version on that same commit, or on the next one with nothing that touches `fliperos-setup`, `config`, `packaging`, `patches` or the build scripts.
2. Check that this comes out empty (`LAST_UPDATE` is the commit of the last line of `updates/index`):

   ```bash
   git log --oneline LAST_UPDATE..HEAD -- fliperos-setup config packaging patches fliperos-rootfs.sh fliperos-mkiso.sh
   ```

   If it doesn't, publish an update first.

The release itself (the tag, the Actions build, the GitHub release) is on [Build and tests](Build-and-tests.md#release).

## An old installation

A cabinet installed before the update system, or stuck on an update, gets going with `updates/bootstrap.sh`:

```bash
curl -fsSL https://raw.githubusercontent.com/juniorterin/fliperOS/main/updates/bootstrap.sh | sudo bash
```

## How it works on the cabinet

- `config/fliperos-update`: `level`, `check [--save]`, `pending`, `notes`, `plan`/`apply`, `shutdown`, `versions`, `goto N|latest`, `restore N`, `apt-heal`, `record`. The level is `/etc/fliperos/patch-level`; the log `/var/log/fliperos-update.log`.
- Before asking, the update is rehearsed in an overlay over `/`, and each file it would write is compared with the manifest of what FliperOS installed (`/var/lib/fliperos/update/manifest`); a file changed on the machine is copied to `/var/lib/fliperos/update/backup/NNNN-date/` first.
- `tools/cabinet-push.sh` copies the working tree to a cabinet over SSH, for testing before an update exists.

See also: [Updates and versions](Updates-and-versions.md), [Build and tests](Build-and-tests.md), [Packages](Packages.md), [Making a release](Making-a-release.md).
