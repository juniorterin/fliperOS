A release is a new ISO with a version number. This page is the whole procedure in order, with what can go wrong at each step; the details of the build and the publishing script are in [Build and tests](Build-and-tests.md#release).

The one rule that shapes the order: **someone who installs the new ISO and someone who only applies the updates must end up with the same system.** So the packages and the update come first, and the tag is placed on the commit that carries them.

## Before you start

- Check that nobody else is about to tag: another session or person may have unfinished work in the same repository.
- Work from WSL for the `gh` steps ([Development environment](Development-environment.md)).
- Tag only when the tests pass: `test_setup.py` and `test_build.py` ([Making a change](Making-a-change.md#testing-it)).

## The steps

1. **Publish the packages that changed.** `tools/publish-changed-packages.sh` shows which; `--run` builds and publishes them ([Packages](Packages.md#publishing)). The ISO build downloads the published `.deb`s, so a package that is not published is compiled again by the build, and the cabinets would not have it.
2. **Publish the update.** Write `updates/notes/NNNN.md` (English, shown on the cabinet) and `updates/notes/pt-BR/NNNN.md` (Portuguese, for the Telegram group), then run `tools/make-update.sh "Title"`, with `--reboot` if the machine has to restart ([Publishing updates](Publishing-updates.md)). The update has to cover everything that changed in the system since the last one.
3. **Check that nothing is left out.** This has to print nothing (`LAST_UPDATE` is the commit of the last line of `updates/index`):

   ```bash
   git log --oneline LAST_UPDATE..HEAD -- fliperos-setup config packaging patches fliperos-rootfs.sh fliperos-mkiso.sh
   ```

   If it prints commits, go back to step 2. A change that only works after a generated file (an EDID, the initramfs, a `modprobe.d` file) needs a step in the update that generates it, as `boot_apply` in `tools/cabinet-update.sh` does.
4. **Raise the version.** Change `FLIPEROS_VERSION` in `fliperos-mkiso.sh`, then change the other places that name it: `git grep -n "fliperos-0\.25"` (use the old version) lists the READMEs, the wiki and the tests. The tag has to be exactly this number, with no `v`.
5. **Write the changelog.** Add `## VERSION` at the top of `CHANGELOG.md`, above the previous version, with what changed since it (`git log PREVIOUS..HEAD` lists the commits). The section has an intro and the four headings `**System changes:**`, `**Package changes:**`, `**fliperos-setup changes:**` and `**Tool changes:**`, each with a list of items. `ReleaseTests` fails if the first section is not the version of `FLIPEROS_VERSION` or if a heading is missing.
6. **Optional: the Telegram text.** `docs/telegram/VERSION.md` is a list of messages (a picture and a caption each, in Portuguese and English) separated by `---`. Without it, the group gets the changelog section. Check it with `python3 tools/telegram-post.py --dry-run VERSION` ([Telegram group](Build-and-tests.md#telegram-group)).
7. **Commit and push to `main`.**
8. **Tag and push the tag:**

   ```bash
   git tag 0.26
   git push origin 0.26
   ```

9. **Follow the build.** It takes about 3 hours without caches (the limit is 6):

   ```bash
   wsl -d Ubuntu-22.04 -- gh run list -R juniorterin/fliperOS -w Release
   wsl -d Ubuntu-22.04 -- gh run watch RUN_ID --exit-status
   wsl -d Ubuntu-22.04 -- gh run view RUN_ID --log-failed
   ```

10. **Check the result.** The release has the ISO (or its parts), `fliperos-VERSION.sha256`, `fliperos-VERSION-pkglist.txt` and the changelog text; the Telegram group got the post. `tools/verify-iso.sh` ran on the ISO before it was published.

## Doing it again

- **Redo a version that was just tagged:** `git tag -f 0.26` on the new commit, then `git push -f origin 0.26`. The build of the old tag still running is cancelled, and a release that was already published is replaced. Do it only for a version nobody has downloaded yet.
- **Build without publishing:** *Actions > Release > Run workflow*. It builds the current version's ISO and keeps it as an artifact for 3 days.
- **Post to Telegram again:** *Actions > Telegram > Run workflow*, with the version (*dry run* only checks the file). With `all` it posts every version of the changelog, oldest first.
- **Publish an ISO built on your machine:** `tools/release-publish.sh`, in the audit container ([Build and tests](Build-and-tests.md#release)). It refuses an ISO that is not from the current repository, one with a Wi-Fi network saved in it, and a version without a changelog section.

## Problems

- **The workflow stops at the first step.** The tag is not `FLIPEROS_VERSION`, the changelog has no section for it, or the Telegram text does not pass the dry run. The message names which.
- **The build fails.** `fliperos-mkiso.log` is kept as a workflow artifact for 7 days. A recipe that compiled badly shows there.
- **Cabinets on the previous level miss something that is in the ISO.** Step 3 was skipped: publish the update that covers the difference.

## How it works

- `.github/workflows/release.yml` runs on a tag that starts with a digit. It checks the tag, the changelog and the Telegram text, then builds the packages repository (the published `.deb`s come first, only the missing ones are compiled), then the ISO with `Dockerfile.fliperos`, then publishes with `tools/release-publish.sh --replace`, then calls the Telegram workflow.
- The kernel and the packages are cached by key: the kernel by `fliperos-kernel.sh key` (the version, the patches and the script), the packages by the hash of `packaging/` and `Dockerfile.packages`.
- The Google sign-in of the cloud backup gets its client from repository secrets while the ISO builds ([Variables](Variables.md#github-secrets-and-variables)).

See also: [Publishing updates](Publishing-updates.md), [Packages](Packages.md), [Build and tests](Build-and-tests.md), [Development](Development.md).
