"""Who a cabinet is online: NICK#tag.

The nickname is the cabinet's name (upper case, the same rules as Setup >
System > Cabinet name: A-Z, 0-9, space and dash, up to 12). The tag is four
characters of base36 (digits and lower case), tied to the cabinet's secret:
the server keeps only the sha256 of that secret, and the tag comes from it.
Two cabinets with the same nickname get different tags.
"""
import hashlib
import re

ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"
TAG_LEN = 4
NICK_MAX = 12
_NICK = re.compile(r"^[A-Z0-9](?:[A-Z0-9 -]{0,%d})$" % (NICK_MAX - 1))
_SECRET = re.compile(r"^[0-9a-f]{64}$")

# Words a nickname may not contain (checked without spaces and dashes). A
# short list on purpose: the admin bans the rest by key.
BLOCKED = ("FUCK", "SHIT", "NAZI", "PORRA", "CARALHO", "BUCETA", "VIADO", "PUTA")


def key_hash(secret):
    """The server's handle of a cabinet: sha256 of its 32-byte secret (64 hex)."""
    secret = (secret or "").strip().lower()
    if not _SECRET.match(secret):
        raise ValueError("secret")
    return hashlib.sha256(bytes.fromhex(secret)).hexdigest()


def base36(n, width=TAG_LEN):
    out = []
    for _ in range(width):
        n, r = divmod(n, 36)
        out.append(ALPHABET[r])
    return "".join(reversed(out))


def tags_for(khash):
    """The tags this key may take, best first: the first is its own, the next
    ones are for when a cabinet with the same nickname already has it."""
    n = 0
    while True:
        digest = hashlib.sha256(("%s:%d" % (khash, n)).encode()).digest()
        yield base36(int.from_bytes(digest[:8], "big"))
        n += 1


def clean_nick(nick):
    """The nickname as the server keeps it, or ValueError("nick")."""
    nick = re.sub(r"\s+", " ", (nick or "").strip().upper())
    if not _NICK.match(nick):
        raise ValueError("nick")
    flat = re.sub(r"[ -]", "", nick)
    if any(word in flat for word in BLOCKED):
        raise ValueError("nick")
    return nick


def full(nick, tag):
    return "%s#%s" % (nick, tag)
