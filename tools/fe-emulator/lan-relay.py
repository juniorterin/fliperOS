#!/usr/bin/env python3
"""A rede dos gabinetes no emulador do frontend: ouve a presenca que cada
gabinete manda por UDP (gui/felink.py, porta 55436; o Docker repassa a porta
publicada para ca) e escreve a tabela que o frontend le no lugar da rede
(FLIPEROS_LINK_FAKE, felink.FakePresence).

O emulador so olha: o IP de cada gabinete vira 192.0.2.1 (TEST-NET, que nao
existe), entao o JOIN nao copia arquivos nem ocupa vaga numa festa de verdade.
Um jogo que o gabinete abre e a biblioteca do emulador nao tem ganha um
arquivo vazio na pasta do sistema, para a linha da festa aparecer na lista.

    lan-relay.py TABELA SISTEMAS
"""
import json
import os
import socket
import sys
import time

PORT, EXPIRE, NOWHERE = 55436, 4.0, "192.0.2.1"
TABLE, SYSTEMS = sys.argv[1], sys.argv[2]


def log(msg):
    print("fe-emulator: " + msg, file=sys.stderr, flush=True)


def write(rows):
    with open(TABLE + ".tmp", "w") as f:
        json.dump({"table": rows}, f)
    os.replace(TABLE + ".tmp", TABLE)


def ensure_game(system, game):
    """O arquivo vazio do jogo na pasta do sistema (se o sistema existe aqui)."""
    try:
        with open(SYSTEMS) as f:
            rows = [line.rstrip("\n").split("|") for line in f]
    except OSError:
        return
    row = next((r for r in rows if len(r) >= 7 and r[0] == system), None)
    if not row or "/" in game or game.startswith("."):
        return
    folder, ext = row[1], (row[6].split(";") or [""])[0]
    os.makedirs(folder, exist_ok=True)
    if not any(os.path.splitext(n)[0] == game for n in os.listdir(folder)):
        open(os.path.join(folder, game + ext), "w").close()
        log("%s/%s%s criado para a festa aparecer na lista" % (system, game, ext))


def describe(rec):
    what = rec.get("game") or "nenhum jogo"
    if rec.get("party"):
        what = "festa %s de %s (%s, vaga %s, %s/%s)" % (
            rec.get("state"), rec.get("game"), rec.get("system"), rec.get("slot"), rec.get("take") or 1,
            rec.get("max"))
    return "%s (%s): %s" % (rec.get("name"), rec.get("ip"), what)


def main():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    rx.bind(("", PORT))
    rx.settimeout(0.5)
    seen, said = {}, {}
    write([])
    log("ouvindo a presenca dos gabinetes na UDP %d" % PORT)
    while True:
        try:
            data, _ = rx.recvfrom(2048)
            rec = json.loads(data.decode())
            if isinstance(rec, dict) and rec.get("v") == 1 and rec.get("id"):
                seen[rec["id"]] = (rec, time.monotonic())
                text = describe(rec)
                if said.get(rec["id"]) != text:
                    said[rec["id"]] = text
                    log(text)
                if rec.get("party") and rec.get("system") and rec.get("game"):
                    ensure_game(rec["system"], rec["game"])
        except socket.timeout:
            pass
        except (ValueError, UnicodeDecodeError):
            continue
        now = time.monotonic()
        for k in [k for k, (_, t) in seen.items() if now - t > EXPIRE]:
            log("%s saiu da rede" % seen[k][0].get("name"))
            del seen[k], said[k]
        write([dict(r, ip=NOWHERE) for r, _ in seen.values()])


if __name__ == "__main__":
    main()
