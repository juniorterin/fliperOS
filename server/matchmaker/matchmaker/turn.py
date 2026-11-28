"""The relay's credentials (phase 2): Cloudflare Realtime TURN.

The cabinets only relay when a direct connection is impossible (both behind
CGNAT or a symmetric NAT), and only the inputs of a game go through it (the
ROMs never do). A cabinet in a party asks the server; the server asks
Cloudflare for short-lived credentials with the key that lives only in its
environment (CF_TURN_KEY_ID, CF_TURN_API_TOKEN) and hands them out.

The 1,000 GB a month are free, then Cloudflare charges per GB, so the server
keeps a monthly count and stops handing out credentials before the cap
(TURN_MONTHLY_GB_CAP, 800 by default). Cloudflare does not tell the server
what one credential used, so the count is: a reserve for every credential
handed out, replaced by what the cabinet reports when its relay closes
(never more than a credential could carry). A cabinet also gets at most
PER_DAY credentials a day.
"""
import asyncio
import json
import time
import urllib.error
import urllib.request

API = "https://rtc.live.cloudflare.com/v1/turn/keys/%s/credentials/generate-ice-servers"
TTL = 4 * 3600              # seconds a credential lives (an evening of play)
RESERVE = 50 * 10**6        # bytes counted for a credential until its cabinet reports
CEILING = 2 * 10**6         # bytes a second one credential could carry at most (both ways)
PER_DAY = 12                # credentials per cabinet per day
USER_AGENT = "FliperOS-Matchmaker-Server/1"


class TurnError(Exception):
    """code: "off" (no key on this server), "cap" (the month's cap), "daily", "fail"."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def month_of(t):
    return time.strftime("%Y-%m", time.gmtime(t))


def ice_of(answer):
    """The TURN entry of Cloudflare's answer: {"urls", "username", "credential"}.
    generate-ice-servers gives a list (STUN first); the older endpoint, one object."""
    servers = answer.get("iceServers")
    if isinstance(servers, dict):
        servers = [servers]
    for s in servers or []:
        urls = s.get("urls") or []
        if isinstance(urls, str):
            urls = [urls]
        turn = [u for u in urls if isinstance(u, str) and u.startswith(("turn:", "turns:"))]
        if turn and s.get("username") and s.get("credential"):
            return {"urls": turn, "username": s["username"], "credential": s["credential"]}
    return None


def cloudflare_fetch(key_id, token, ttl):
    req = urllib.request.Request(API % key_id, data=json.dumps({"ttl": ttl}).encode(), method="POST", headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json", "User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())


class Turn:
    def __init__(self, store, key_id="", token="", cap_gb=800, clock=time.time, fetch=None):
        self.store, self.key_id, self.token = store, key_id or "", token or ""
        self.cap = int(float(cap_gb) * 10**9)
        self.clock = clock
        self.fetch = fetch or cloudflare_fetch

    @classmethod
    def from_env(cls, store, env):
        return cls(store, env.get("CF_TURN_KEY_ID"), env.get("CF_TURN_API_TOKEN"),
                   env.get("TURN_MONTHLY_GB_CAP") or 800)

    @property
    def enabled(self):
        return bool(self.key_id and self.token)

    async def credentials(self, cab_id):
        """{"urls", "username", "credential", "ttl"} for one cabinet, or TurnError."""
        if not self.enabled:
            raise TurnError("off")
        now = self.clock()
        month = month_of(now)
        if self.store.turn_bytes(month) + RESERVE > self.cap:
            raise TurnError("cap")
        if self.store.turn_issued_since(cab_id, now - 86400) >= PER_DAY:
            raise TurnError("daily")
        try:
            answer = await asyncio.to_thread(self.fetch, self.key_id, self.token, TTL)
        except (OSError, ValueError, urllib.error.URLError):
            raise TurnError("fail")
        ice = ice_of(answer) if isinstance(answer, dict) else None
        if ice is None:
            raise TurnError("fail")
        self.store.turn_issue(cab_id, ice["username"], month, RESERVE, now)
        return dict(ice, ttl=TTL)

    def used(self, cab_id, username, nbytes):
        """What a cabinet says its relay carried: it takes the reserve's place."""
        if not isinstance(nbytes, int) or isinstance(nbytes, bool) or nbytes < 0 or not isinstance(username, str):
            return False
        return self.store.turn_report(cab_id, username, min(nbytes, TTL * CEILING))
