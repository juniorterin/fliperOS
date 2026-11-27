# FliperOS Matchmaker server

The online lobby of the FliperOS Matchmaker ([plan](../../docs/research/matchmaker-plan.md)). Phase 1: who a cabinet is (`NICK#tag`), who is online and what they play, the counts per game and the room of a game. Python 3.12, one WebSocket, SQLite on a volume.

The server opens no UDP port. The cabinets find their public address with Cloudflare's STUN (`stun.cloudflare.com`) and, when a direct connection is impossible, relay through Cloudflare Realtime TURN (phase 2: the server asks Cloudflare for short-lived TURN credentials per match). That is why it can run behind CGNAT, reached only through a Cloudflare Tunnel.

## Protocol

`GET /health` answers `ok`; `GET /ws` is the WebSocket, one JSON object per message. The messages are documented at the top of [`matchmaker/app.py`](matchmaker/app.py).

- **Identity:** the cabinet sends a 64-hex secret it made once; the server keeps only its sha256. The tag (4 characters, digits and lower case) comes from that hash; two cabinets with the same nickname get different tags. At most 5 new identities per address per hour.
- **Presence:** state (idle, looking, playing, party, download), game (`system:set`), emulator, connection (cable or wifi), the ping to the server, and who plays together (a group id with its kind, match or party, and its score or places). Anything else is dropped.
- **Counts and rooms** go out at most every half second.

## Tests

```
docker run --rm -v "$PWD/server/matchmaker:/m" -w /m python:3.12-slim \
    sh -c "pip install -q -r requirements.txt && python -m unittest discover -s tests -v"
```

## Deploying on Coolify

- **Resource:** Docker Compose, from this repository, base directory `/server/matchmaker` (`docker-compose.yml`). No port is published.
- **Domain:** a public hostname in the server's Cloudflare Tunnel (for example `online.fliperos.juniorter.in`) to `http://<the container>:8080`. The tunnel passes WebSockets.
- **Environment (phase 2):** `CF_TURN_KEY_ID` and `CF_TURN_API_TOKEN` (the Cloudflare Realtime TURN key, kept only here), `TURN_MONTHLY_GB_CAP` (default 800: past it the server stops handing out relay credentials for the month, below the 1,000 GB free tier).
- **Data:** the `matchmaker-data` volume (`/data/matchmaker.db`).
