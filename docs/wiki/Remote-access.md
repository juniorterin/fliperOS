The cabinet from another computer: SSH and SFTP, the network share, an AI assistant that configures it for you, and lab mode for someone helping you from far away.

## SSH and SFTP

SSH is on from the first boot, and SFTP too. From another computer on the same network:

| Field | Value |
| --- | --- |
| **Address** (host) | `fliperos.local`, or the cabinet's IP (shown in the FliperOS menu's title) |
| **User** (login, username) | `fliperos` |
| **Password** | `fliperos`, until you change it in **Setup > System > Password** |
| **Port** | `22` |

The user and the password are the same word by default, but they are two different things.

In `ssh fliperos@fliperos.local`, the `fliperos` before the `@` is the **user**, and `fliperos.local` after it is the **address**. The **password** is not in the command: you type it when SSH asks, and nothing shows while you type.

In an SFTP program (FileZilla, WinSCP) the same four fields are *Host*, *Username*, *Password* and *Port*. `sudo` asks for the same password. After a password change only the password is different: the user is still `fliperos`.

Over SSH, `sudo fliperos-setup` (or `fliperos-menu`) opens the Setup as a text menu in the SSH session. Frontends, games and the desktop only open on the cabinet itself.

The web panel's **System > Terminal** is the same shell in a browser, without an SSH program ([Web panel](Web-panel.md)).

## The network share

From Windows, open `\\fliperos` in Explorer (or `\\` and the cabinet's IP). The shares are:

| Share | Folder |
| --- | --- |
| `roms`, `bios`, `media`, `nvram`, `save`, `splashscreen`, `config` | The folders in `~` ([ROMs, BIOS and artwork](ROMs.md)) |
| `FliperOS` | `/opt/fliperos`: logs, menu sounds and the rest of FliperOS |

They take the same user and password as SSH. The share is a service in **Setup > System > Services**, after boot by default ([System Setup](Setup-System.md#services)).

## AI assistants

Under the menus it is a regular Ubuntu 24.04, so whatever the Setup doesn't cover can be done from a terminal. An AI assistant with shell access (Claude Code, Cursor, Codex and the like) can do it for you: give it the cabinet's address and say what you want (a button mapping, an emulator's settings, a frontend theme, a service), and it configures the system over SSH.

The configuration is in plain text files, easy for a person or an assistant to read and change:

- `/etc/fliperos/fliperos.conf`: the Setup's choices;
- `~/config`: links to the emulators' and frontends' settings;
- `/opt/fliperos`: FliperOS's programs and logs.

The cabinet has no terminal text editor (no `nano` or `vi`): change files with `sed`, from the desktop's text editor, or over SFTP.

## Lab mode

A temporary internet address to the cabinet's web panel, so someone far away can help you, like a FliperOS developer looking at a problem.

Turn it on in **Setup > System > Lab mode**, or on the web panel's **System > Lab mode** tab.

1. It gives an address like `https://some-random-words.trycloudflare.com/lab?key=…`. In the Setup it shows on the screen; in the panel, **Copy** puts it on the clipboard, to send by chat or email.
2. Whoever opens it gets into the panel without your password: status, logs, files, screenshots, and a **root** terminal. Send it only to someone you trust.
3. It ends by itself after 4 hours, when the cabinet powers off, or with **Turn off**. Then the address and every session opened with it stop working. Turning it on again gives a new address.

Nothing changes on your router: the cabinet opens the connection itself. The first time, it downloads `cloudflared` (about 40 MB). If the web panel is off in Services, lab mode starts it until the next boot. The live screen doesn't work through the address.

## Security

On a network you don't control:

- change the default password in **Setup > System > Password** (it changes the network share's too);
- turn off what you don't use in **Setup > System > Services**: SSH, the network share, the web panel.

The web panel is plain HTTP, so its password crosses the network unencrypted: use it on a network you trust.

## How it works

- SSH is Ubuntu's `ssh` service; the share is Samba (`config/smb.conf`), with its own password changed together with the system's.
- Lab mode: `fliperos-lab start` writes a random key to `/run/fliperos-lab` and starts `fliperos-lab.service`, which runs a [Cloudflare Quick Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/do-more-with-tunnels/trycloudflare/) (`cloudflared`, no account) as a temporary user with `RuntimeMaxSec=4h`. The address comes from cloudflared's `/quicktunnel` metrics. `cloudflared` has a fixed version and checksum and lives in `/opt/fliperos/cloudflared`. The panel's `/lab?key=` compares the key; wrong keys are limited to 5 a minute. In the lab terminal, `su - fliperos` gives the normal user.
- Commands of `fliperos-lab`: `fetch`, `installed`, `start`, `stop`, `status`, `cleanup`.

See also: [Web panel](Web-panel.md), [System Setup](Setup-System.md).
