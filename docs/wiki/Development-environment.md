How the work is set up on a Windows machine: what runs where, the rules that keep the build from breaking the machine, and what to do when Docker or WSL misbehave. Anything heavy runs in Docker; the Windows side only drives it.

## What runs where

| Job | Where |
| --- | --- |
| Building the ISO, the kernel and the packages | Docker (`Dockerfile.fliperos`, `Dockerfile.packages`), never directly in WSL |
| The tests (`test_setup.py`, `test_build.py`) | Docker, image `fliperos-tests` (Ubuntu 24.04 with `python3` and `jq`) |
| The `gh` command (releases, Actions logs, uploads) | WSL Ubuntu 22.04: it is logged in only there |
| `tools/make-update.sh`, `tools/publish-*.sh` | WSL, where there is a Linux `python3`, `gh` and `docker` |
| Editing, `git` | Windows (Git Bash or PowerShell) |

The Windows side has no usable Python. Run Python through Docker or WSL.

In Git Bash, a Docker mount needs `MSYS_NO_PATHCONV=1` and `$(pwd -W)` instead of `$PWD`, or the path is rewritten. In PowerShell, `${PWD}` works as it is. A long job (the kernel build, a whole ISO) runs as a detached container (`docker run -d --name …`), not as a background task of the terminal: those die with the session.

## The rules

These come from builds that broke the machine.

1. **No `debootstrap` or `chroot` with a bind mount of `/dev` on WSL2.** It exposes the host's real `/dev` inside the chroot, corrupts the host's `/dev/null` (it becomes a regular file) and leaves mounts stuck. A container has no such problem, so the build is Docker.
2. **`/dev/null` as a regular file means something leaked.** Check with `stat /dev/null`: it has to be a character device. If it is not, stop the build; do not just run `mknod` and try again.
3. **The same kind of error twice** (stuck mount, corrupted `/dev`, failing `umount`): stop and find the cause before a third try.
4. **Check Docker's health before anything heavy** (an ISO, the kernel, packages, the test suites) and before restarting Docker:

   ```powershell
   powershell -NoProfile -File tools\docker-health.ps1
   ```

5. **One heavy Docker job at a time**, across everyone using the machine: look at `docker ps` first. Two builds in parallel have taken Docker down.
6. **Never kill `com.docker.backend` and never run `wsl --shutdown`** to unstick Docker: that leaves another VM holding memory.

## docker-health.ps1

| Exit | Meaning | What to do |
| --- | --- | --- |
| 0 | Fine | Go ahead |
| 1 | Windows' committed memory is above 85% | Do not start anything heavy or restart Docker; close programs or restart Windows |
| 2 | Docker does not answer, WSL does | Quit Docker Desktop from the tray and open it again, once |
| 3 | WSL itself is hung | Reopening Docker does not help: restart the WSL service as administrator, or Windows |

## Working with other people

Several people (or several Claude sessions) can work in the same checkout. The git index is shared, so a `git add` by one shows up in another's commit. Look at `git diff --cached --stat` first, and add and commit in one go. If someone else has staged files, commit with `git commit -- PATH…` or a private `GIT_INDEX_FILE`.

Commit only your own files, even when `git status` shows many changed files: they belong to someone's work in progress. Push to `main` after each change.

## Problems

- **Docker Desktop is stopped.** Start it and wait for `docker info` to answer. A stopped daemon kills any running build.
- **A mount stays stuck after a failed build.** Do not retry; read rule 3.
- **`gh` says you are not logged in.** You are in the wrong shell: use WSL (`wsl -d Ubuntu-22.04 -- gh …`).

## How it works

- Windows' committed memory (commit) runs out when something leaks handles, and Docker then fails with error 1455 ("paging file too small") and "engine stopped unexpectedly". `tools/docker-health.ps1` prints the commit, the free memory, the processes that look like they are leaking and the state of Docker and WSL.
- The rules are in the repository's `CLAUDE.md`, which every Claude session reads first.

See also: [Build and tests](Build-and-tests.md), [Making a change](Making-a-change.md), [Development](Development.md).
