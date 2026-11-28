"""One cabinet of the NAT lab's party test: the felink party inside the tunnel
(mmparty.OnlineParty). The host has the game (a file in its home) and serves
it; the guest has not: on a direct path the files come over the tunnel, then
both join the room and the party starts with the input delay of the ping.
Through the relay the guest must stop with NEEDS THE ROM.

    python3 natlab_party.py REPO SERVER_IP host|guest NAME STATEDIR

Prints "STAGE ..." lines, "LAUNCH delay=N rtt=M" or "FAILED message".
"""
import os
import sys
import tempfile
import time

REPO, SERVER, ROLE, NAME, STATE = sys.argv[1:6]
sys.path.insert(0, os.path.join(REPO, "fliperos-setup", "gui"))

import fenat  # noqa: E402
import feonline  # noqa: E402
import fetunnel  # noqa: E402
import mmparty  # noqa: E402

T0 = time.time()
GAME_FILE = "roms/mame/labgame.zip"
BIOS_FILE = "roms/mame/neogeo.zip"       # the guest has its own: it must stay as it is
PROFILE = {"id": "netplay", "title": "labgame", "emulator": "groovymame", "systems": ["mame"], "sets": ["labgame"],
           "min": 2, "max": 2, "players": 2, "fixed": True, "order": "master-first", "step": 0, "port": 55440,
           "netplay": True, "lockstep": True}


def log(*a):
    print("[%s %5.1f]" % (NAME, time.time() - T0), *a, flush=True)


home = tempfile.mkdtemp(prefix="home-")
os.makedirs(os.path.join(home, "roms", "mame"))
if ROLE == "host":
    with open(os.path.join(home, GAME_FILE), "wb") as f:
        f.write(os.urandom(3 * 1024 * 1024))
    with open(os.path.join(home, BIOS_FILE), "wb") as f:
        f.write(b"the host's bios")
else:
    with open(os.path.join(home, BIOS_FILE), "wb") as f:
        f.write(b"the guest's own bios")

online = feonline.Online(NAME, url="ws://%s:8080/ws" % SERVER, secret=os.urandom(32).hex())
online.start()
end = time.time() + 15
while online.snapshot()["status"] != "online":
    if time.time() > end:
        sys.exit("never online")
    time.sleep(0.1)

held = []


def wait_msg(op, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        batch = online.take()
        for i, m in enumerate(batch):
            if m.get("t") == "party" and m.get("op") == op:
                held.extend(batch[i + 1:])
                return m
            held.append(m)
        time.sleep(0.05)
    sys.exit("no %s" % op)


if ROLE == "host":
    online.send({"t": "party", "op": "open", "game": "mame:labgame", "emu": "groovymame", "max": 2})
    msg = wait_msg("opened")
    with open(os.path.join(STATE, "party"), "w") as f:
        f.write(msg["party"])
    game = {"system": "mame", "name": "labgame", "profile": dict(PROFILE), "files": [GAME_FILE, BIOS_FILE], "rom": None}
else:
    path = os.path.join(STATE, "party")
    while not os.path.exists(path):
        time.sleep(0.1)
    online.send({"t": "party", "op": "join", "party": open(path).read().strip()})
    msg = wait_msg("joined")
    game = {"system": "mame", "name": "labgame", "profile": dict(PROFILE), "have": False, "rom": None}


def tunnel_factory(addr):
    helper = fetunnel.Helper(["python3", os.path.join(REPO, "config", "fliperos-online-tunnel")])
    return fetunnel.Tunnel(addr, online.send, helper=helper,
                           stun=lambda port: fenat.public_port(port, server=(SERVER, 3479)))


party = mmparty.OnlineParty(online, msg, game, home, NAME, tunnel_factory=tunnel_factory)
party.link_factory = lambda: mmparty.OnlineLink(home, party.tunnel, NAME, local_players=1)
party.start()
for m in held:
    party.handle(m)
stage = None
end = time.time() + 90
while time.time() < end:
    for m in online.take():
        party.handle(m)
    got = party.tick()
    st = party.state()
    if st["stage"] != stage:
        stage = st["stage"]
        log("STAGE", stage, st["message"] or "")
    if got == "launch":
        plan = st["lobby"]["plan"]
        log("LAUNCH delay=%s rtt=%s" % (plan.get("input_delay"), st["rtt"]))
        if ROLE == "guest":
            ok = os.path.isfile(os.path.join(home, GAME_FILE))
            log("FILE", "copied" if ok else "missing")
            with open(os.path.join(home, BIOS_FILE), "rb") as f:
                log("BIOS", "kept" if f.read() == b"the guest's own bios" else "OVERWRITTEN")
        time.sleep(1)
        break
    if stage == "failed":
        log("FAILED", st["message"])
        break
    time.sleep(0.05)
else:
    log("TIMEOUT", party.state()["stage"])
party.leave()
online.stop()
