# Os dados do Matchmaker, sem pygame: as paginas (uma por emulador ou core
# que joga online), o id de cada jogo para o servidor, e as linhas de uma
# pagina e do lobby de um jogo. O fliperos-matchmaker so desenha o que sai daqui.
#
# Paginas por emulador ou core, nunca por console ou "arcade": GroovyMAME
# (pasta mame), hbgroovymame (hbmame), Flycast (Naomi, Naomi 2 e Atomiswave
# juntos) e cada core do RetroArch que faz net play ("deterministic", o
# rollback do proprio RetroArch).

import re

GAME_ID = re.compile(r"^[a-z0-9_.-]{1,24}:[a-z0-9_.-]{1,40}$")
PRETTY = {"fbneo": "FBNEO", "snes9x": "SNES9X", "genesis_plus_gx": "GENESIS PLUS GX", "fceumm": "FCEUMM",
          "mgba": "MGBA", "pcsx_rearmed": "PCSX REARMED"}
FLYCAST_SYSTEMS = ("naomi", "naomi2", "atomiswave")


def page_of(system, netplay_core=None, dojo=False):
    """(chave, nome) da pagina de um sistema do fedata, ou None se ele nao joga online."""
    key = system.get("key", "")
    if key == "mame":
        return "mame", "GROOVYMAME"
    if key == "hbmame":
        return "hbmame", "HBGROOVYMAME"
    if key in FLYCAST_SYSTEMS:
        return "flycast", "FLYCAST DOJO" if dojo else "FLYCAST"
    if key.startswith("retroarch/") and netplay_core is not None and netplay_core(key):
        core = key.split("/", 1)[1]
        return core.replace("-", "_").lower(), PRETTY.get(core, core.upper().replace("_", " "))
    return None


def pages(systems, netplay_core=None, dojo=False):
    """As paginas, na ordem fixa: GroovyMAME, hbgroovymame, Flycast, e os
    cores do RetroArch em ordem alfabetica. Cada uma com os sistemas dela e o
    exe do primeiro (o icone do emulador na faixa, feview.system_icon)."""
    found = {}
    for s in systems:
        p = page_of(s, netplay_core, dojo)
        if p is None:
            continue
        page = found.setdefault(p[0], {"key": p[0], "name": p[1], "systems": [], "exe": s.get("exe", ""),
                                       "args": s.get("args", "")})
        page["systems"].append(s)
    head = [k for k in ("mame", "hbmame", "flycast") if k in found]
    rest = sorted(k for k in found if k not in head)
    return [found[k] for k in head + rest]


def game_id(page_key, game):
    """O id que o servidor conhece ("mame:sf2ce"), ou None se o nome nao serve."""
    gid = "%s:%s" % (page_key, (game.get("Name") or "").lower())
    return gid if GAME_ID.match(gid) else None


def home_rows(page, games, counts, opened=True):
    """As linhas de uma pagina: o grupo ONLINE NOW (os jogos da pagina com
    alguem online, os que este gabinete nao tem tambem, os mais cheios antes)
    e depois os outros jogos da pagina (os do ONLINE NOW nao se repetem).
    counts: {id: {"players", "looking"}}."""
    by_id = {}
    for g in games:
        gid = game_id(page["key"], g)
        if gid:
            by_id[gid] = g
    prefix = page["key"] + ":"
    live = sorted(((gid, c) for gid, c in counts.items() if gid.startswith(prefix) and c.get("players")),
                  key=lambda x: (-x[1].get("players", 0), x[0]))
    rows = [{"kind": "group", "name": "ONLINE NOW", "count": len(live), "open": opened}]
    if opened:
        for n, (gid, c) in enumerate(live):
            g = by_id.get(gid)
            have = g is not None
            if not have:
                name = gid.split(":", 1)[1]
                g = {"Name": name, "Title": name.upper(), "_missing": True}
            rows.append({"kind": "online", "id": gid, "game": g, "have": have, "players": c.get("players", 0),
                         "looking": c.get("looking", 0), "last": n == len(live) - 1})
    shown = {gid for gid, _ in live}
    for g in games:
        gid = game_id(page["key"], g)
        if gid not in shown:
            rows.append({"kind": "game", "id": gid, "game": g, "have": True, "players": 0, "looking": 0})
    return rows


GROUPS = ("LOOKING", "PLAYING", "IN PARTY", "IDLE")


def lobby_rows(players, opened=None, open_subs=None):
    """As linhas do lobby de um jogo: LOOKING, PLAYING (cada partida uma linha
    com o placar e os dois jogadores dentro), IN PARTY (cada party uma linha
    com os membros dentro, quem baixa a ROM tambem) e IDLE. opened: {grupo:
    aberto}; open_subs: {id do grupo: aberto} (o padrao: aberto)."""
    opened = dict({"LOOKING": True, "PLAYING": True, "IN PARTY": True, "IDLE": False}, **(opened or {}))
    open_subs = open_subs or {}
    looking = [p for p in players if p.get("state") == "looking"]
    idle = [p for p in players if p.get("state") in (None, "idle")]
    playing, parties = {}, {}
    for p in players:
        st = p.get("state")
        if st == "playing":
            playing.setdefault(p.get("group") or "solo-%s" % p.get("id"), []).append(p)
        elif st in ("party", "download"):
            parties.setdefault(p.get("group") or "solo-%s" % p.get("id"), []).append(p)
    rows = []

    def players_of(group, members):
        rows.append({"kind": "group", "name": group, "count": len(members), "open": opened[group]})
        if opened[group]:
            for n, p in enumerate(members):
                rows.append({"kind": "player", "player": p, "level": 1, "last": n == len(members) - 1})

    def subs_of(group, subs, label):
        count = sum(len(m) for m in subs.values())
        rows.append({"kind": "group", "name": group, "count": count, "open": opened[group]})
        if not opened[group]:
            return
        items = sorted(subs.items(), key=lambda kv: kv[0])
        for k, (gid, members) in enumerate(items):
            last_sub = k == len(items) - 1
            is_open = open_subs.get(gid, True)
            text, right = label(members)
            rows.append({"kind": "sub", "id": gid, "text": text, "right": right, "open": is_open, "last": last_sub,
                         "members": members})
            if is_open:
                for n, p in enumerate(members):
                    rows.append({"kind": "player", "player": p, "level": 2, "last": n == len(members) - 1,
                                 "outer": not last_sub})

    def match_label(members):
        names = " VS ".join(p.get("nick", "?") for p in members[:2])
        return names, next((p.get("score") for p in members if p.get("score")), "")

    def party_label(members):
        host = members[0].get("nick", "?")
        return "PARTY " + host, next((p.get("score") for p in members if p.get("score")), "%d" % len(members))

    players_of("LOOKING", looking)
    subs_of("PLAYING", playing, match_label)
    subs_of("IN PARTY", parties, party_label)
    players_of("IDLE", idle)
    return rows


def tag_of(p):
    return "%s#%s" % (p.get("nick", "?"), p.get("tag", ""))
