"""One cabinet of the NAT lab: online, a party (host or guest), the tunnel,
then a TCP echo over it and the path it took.

    python3 natlab_cab.py REPO SERVER_IP host|guest NAME STATEDIR

The host writes its party id to STATEDIR/party; the guest waits for it.
Prints "PATH direct" or "PATH relay" and "ECHO ok" (or fails).
"""
import json
import os
import socket
import sys
import threading
import time

REPO, SERVER, ROLE, NAME, STATE = sys.argv[1:6]
sys.path.insert(0, os.path.join(REPO, "fliperos-setup", "gui"))

import fenat  # noqa: E402
import feonline  # noqa: E402
import fetunnel  # noqa: E402

ECHO_PORT = 55499


T0 = time.time()


def log(*a):
    print("[%s %5.1f]" % (NAME, time.time() - T0), *a, flush=True)


online = feonline.Online(NAME, url="ws://%s:8080/ws" % SERVER, secret=os.urandom(32).hex())
online.start()
end = time.time() + 15
while online.snapshot()["status"] != "online":
    if time.time() > end:
        sys.exit("never online: %s" % online.snapshot())
    time.sleep(0.1)


def wait_msg(op, timeout=15):
    end = time.time() + timeout
    while time.time() < end:
        batch = online.take()
        for i, m in enumerate(batch):
            if m.get("t") == "party" and m.get("op") == op:
                pending.extend(batch[i + 1:])
                return m
            pending.append(m)
        time.sleep(0.05)
    sys.exit("no %s" % op)


pending = []
if ROLE == "host":
    online.send({"t": "party", "op": "open", "game": "mame:sf2ce", "emu": "groovymame", "max": 2})
    opened = wait_msg("opened")
    with open(os.path.join(STATE, "party"), "w") as f:
        f.write(opened["party"])
    me, members = opened["addr"], []
else:
    path = os.path.join(STATE, "party")
    while not os.path.exists(path):
        time.sleep(0.1)
    online.send({"t": "party", "op": "join", "party": open(path).read().strip()})
    joined = wait_msg("joined")
    me, members = joined["addr"], joined["members"]
log("party addr", me)

helper = fetunnel.Helper(["python3", os.path.join(REPO, "config", "fliperos-online-tunnel")])
tunnel = fetunnel.Tunnel(me, online.send, helper=helper, log=log,
                         stun=lambda port: fenat.public_port(port, server=(SERVER, 3479)))
tunnel.start(members)
for m in pending:
    tunnel.handle(m)


def pump():
    while True:
        for m in online.take():
            tunnel.handle(m)
        time.sleep(0.05)


threading.Thread(target=pump, daemon=True).start()

end = time.time() + 60
next_dump = time.time() + 5
while not (tunnel.ready() and tunnel.snapshot()["peers"]):
    if time.time() > end:
        sys.exit("tunnel never ready: %s" % json.dumps(tunnel.snapshot()))
    if time.time() > next_dump:
        next_dump += 5
        relay = tunnel.relay
        log("wg", helper.show(), "relay", relay and relay.counts)
    time.sleep(0.2)
snap = tunnel.snapshot()
peer = snap["peers"][0]
log("PATH", peer["path"], peer["endpoint"], "after %.1f s" % (time.time() - end + 60))

if ROLE == "host":
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((me, ECHO_PORT))
    srv.listen(1)
    srv.settimeout(30)
    conn, src = srv.accept()
    data = conn.recv(100)
    conn.sendall(b"echo " + data)
    conn.close()
    log("ECHO ok from", src[0])
    time.sleep(1)
else:
    for _ in range(50):
        try:
            c = socket.create_connection((peer["addr"], ECHO_PORT), timeout=2)
            break
        except OSError:
            time.sleep(0.3)
    else:
        sys.exit("no TCP over the tunnel")
    c.sendall(b"hello")
    got = c.recv(100)
    log("ECHO", "ok" if got == b"echo hello" else "BAD %r" % got)
tunnel.stop()
online.stop()
