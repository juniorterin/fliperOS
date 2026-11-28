"""The player's record, signed by the server: the "ficha".

The server is the authority on wins and losses. After every accepted match it
issues the player's profile: who (id, NICK#tag, the hash of the key), the
record per game and in all, a version that only grows, and the head of the
server's ledger when it was made. It is canonical JSON (sorted keys, no
spaces) signed with Ed25519; the private key lives only in the server's
environment (MATCHMAKER_SIGNING_KEY, 32 bytes base64), FliperOS carries the
public key. Changing a single number breaks the signature, and an older
profile loses to one with a higher version.

The cabinet keeps it in its cloud backup, encrypted (AES-256-GCM, a key from
its own secret), next to that secret sealed with its PIN (Argon2id).
"""
import base64
import hashlib
import json
import os
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

DOMAIN = b"fliperos-profile-v1\n"      # what is signed is DOMAIN + the canonical payload


def b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64(text):
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class Signer:
    def __init__(self, seed_b64=None):
        if seed_b64:
            self.key = Ed25519PrivateKey.from_private_bytes(unb64(seed_b64.strip()))
            self.ephemeral = False
        else:
            self.key = Ed25519PrivateKey.generate()      # tests and local runs only
            self.ephemeral = True
        raw = self.key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        self.public = raw
        self.kid = hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def from_env(cls):
        return cls(os.environ.get("MATCHMAKER_SIGNING_KEY") or None)

    def sign(self, payload):
        text = canonical(payload)
        sig = self.key.sign(DOMAIN + text.encode())
        return {"kid": self.kid, "payload": text, "sig": b64(sig)}

    def public_info(self):
        return {"kid": self.kid, "alg": "Ed25519", "public": b64(self.public)}


def verify(profile, public_b64):
    """The payload (a dict) if the signature is good, else None."""
    try:
        pub = Ed25519PublicKey.from_public_bytes(unb64(public_b64))
        pub.verify(unb64(profile["sig"]), DOMAIN + profile["payload"].encode())
        return json.loads(profile["payload"])
    except Exception:
        return None


def payload(row, record, version, ledger_head, now=None):
    """The profile of a cabinet (a store row) with its record:
    {game: {"w": wins, "l": losses}}."""
    wins = sum(r.get("w", 0) for r in record.values())
    losses = sum(r.get("l", 0) for r in record.values())
    return {
        "v": 1,
        "id": row["id"],
        "nick": row["nick"],
        "tag": row["tag"],
        "key_hash": row["key_hash"],
        "version": version,
        "record": record,
        "total": {"w": wins, "l": losses, "matches": wins + losses},
        "ledger": ledger_head,
        "issued": int(now if now is not None else time.time()),
    }
