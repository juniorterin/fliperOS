"""The lab's "internet" side: the real Matchmaker server (relay credentials
pointing at the lab's coturn instead of Cloudflare) and a STUN responder.

    python3 natlab_server.py REPO PUBLIC_IP
"""
import asyncio
import os
import socket
import sys
import threading

REPO, PUBLIC = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(REPO, "server", "matchmaker"))
sys.path.insert(0, os.path.join(REPO, "fliperos-setup", "gui"))

import fenat  # noqa: E402
from matchmaker import app, turn  # noqa: E402


def stun_responder(port=3479):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))
    while True:
        data, src = s.recvfrom(2048)
        msg = fenat.parse(data)
        if not msg or msg[0] != fenat.BINDING | fenat.REQUEST:
            continue
        s.sendto(fenat.message(fenat.BINDING | fenat.SUCCESS, msg[1], [(fenat.A_XOR_MAPPED, fenat.xor_addr(*src))]), src)


def lab_turn(key_id, token, ttl):
    return {"iceServers": [{"urls": ["turn:%s:3478?transport=udp" % PUBLIC], "username": "lab", "credential": "lab"}]}


async def main():
    ready = asyncio.get_running_loop().create_future()
    task = asyncio.create_task(app.run("0.0.0.0", 8080, ":memory:", ready))
    server, _ = await ready
    server.turn = turn.Turn(server.store, "lab", "lab", fetch=lab_turn)
    print("server ready", flush=True)
    await task


threading.Thread(target=stun_responder, daemon=True).start()
asyncio.run(main())
