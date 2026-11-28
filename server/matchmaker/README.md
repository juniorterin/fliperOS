# FliperOS Matchmaker server

The online lobby of the FliperOS Matchmaker ([plan](../../docs/research/matchmaker-plan.md)). Phase 1: who a cabinet is (`NICK#tag`), who is online and what they play, the counts per game and the room of a game. Python 3.12, one WebSocket, SQLite on a volume.

The server opens no UDP port. The cabinets find their public address with Cloudflare's STUN (`stun.cloudflare.com`) and, when a direct connection is impossible, relay through Cloudflare Realtime TURN (phase 2: the server asks Cloudflare for short-lived TURN credentials per match). That is why it can run behind CGNAT, reached only through a Cloudflare Tunnel.

## Protocol

`GET /health` answers `ok`; `GET /ws` is the WebSocket, one JSON object per message. The messages are documented at the top of [`matchmaker/app.py`](matchmaker/app.py).

- **Identity:** the cabinet sends a 64-hex secret it made once; the server keeps only its sha256. The tag (4 characters, digits and lower case) comes from that hash; two cabinets with the same nickname get different tags. At most 5 new identities per address per hour.
- **Presence:** state (idle, looking, playing, party, download), game (`system:set`), emulator, connection (cable or wifi), the ping to the server, and who plays together (a group id with its kind, match or party, and its score or places). Anything else is dropped.
- **Counts and rooms** go out at most every half second.
- **The signed profile (the "ficha"):** right after `welcome` (and on `{"t": "profile"}`) the server sends the player's profile: id, `NICK#tag`, the key's hash, wins and losses per game and in all, a version that only grows, and the ledger's head, as canonical JSON signed with **Ed25519** (`matchmaker/profile.py`). The private key is only in the server's environment (`MATCHMAKER_SIGNING_KEY`, made on the server itself and never printed); `GET /pubkey` gives the public key (`kid`, `public`), which FliperOS carries to check the profiles. The cabinet keeps the profile in its cloud backup encrypted (AES-256-GCM, a key from its secret), next to its secret sealed with its PIN (Argon2id). No GitHub secret is involved.

## Tests

```
docker run --rm -v "$PWD/server/matchmaker:/m" -w /m python:3.12-slim \
    sh -c "pip install -q -r requirements.txt && python -m unittest discover -s tests -v"
```

## Deploying on Coolify

Live since 2026-11-27 at **`wss://fliperos-matchmaker.juniorter.in/ws`** (`https://fliperos-matchmaker.juniorter.in/health`).

- **Resource:** the application `fliperos-matchmaker` in the Coolify project **FliperOS** (environment `production`), a Docker Compose app built from this repository through the same GitHub App as the site, branch `main`, base directory `/server/matchmaker` (`docker-compose.yml`). No port is published.
- **Updates:** automatic. A push that touches `server/matchmaker/**` (the app's watch paths) deploys it again; other pushes don't.
- **Domain:** `http://fliperos-matchmaker.juniorter.in:8080` in Coolify's domain for the `matchmaker` service: plain HTTP on purpose, Cloudflare puts the HTTPS in front. The server's Cloudflare Tunnel already sends `*.juniorter.in` to Coolify's proxy and the DNS has a wildcard, so a new subdomain needs no change in the tunnel. The proxy only routes to the container once its health check passes (a few seconds after each deploy, `/health` answers 404).
- **Environment:** `MATCHMAKER_SIGNING_KEY` (the Ed25519 seed of the profiles, 32 bytes base64url; without it the server signs with a throwaway key and says so in its log); phase 2: `CF_TURN_KEY_ID` and `CF_TURN_API_TOKEN` (the Cloudflare Realtime TURN key, kept only here), `TURN_MONTHLY_GB_CAP` (default 800: past it the server stops handing out relay credentials for the month, below the 1,000 GB free tier).
- **Data:** the `matchmaker-data` volume (`/data/matchmaker.db`).
