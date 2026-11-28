"""The matchmaker's database (SQLite in WAL mode, on the Coolify volume).

Phase 1 keeps the cabinets (by the hash of their secret, never the secret),
their NICK#tag, the bans, and when new identities were made from an address
(a limit against making accounts in a loop). Phase 2 adds the relay
credentials handed out (turn.py: the month's count against the cap).
"""
import sqlite3
import threading
import time

from . import identity

SCHEMA = """
CREATE TABLE IF NOT EXISTS cabinets (
    id INTEGER PRIMARY KEY,
    key_hash TEXT NOT NULL UNIQUE,
    nick TEXT NOT NULL,
    tag TEXT NOT NULL,
    created REAL NOT NULL,
    last_seen REAL NOT NULL,
    UNIQUE (nick, tag)
);
CREATE TABLE IF NOT EXISTS bans (
    key_hash TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS signups (
    ip TEXT NOT NULL,
    at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS signups_ip ON signups (ip, at);
CREATE TABLE IF NOT EXISTS profiles (
    cabinet_id INTEGER PRIMARY KEY REFERENCES cabinets (id),
    version INTEGER NOT NULL,
    record TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS turn (
    username TEXT PRIMARY KEY,
    cabinet_id INTEGER NOT NULL,
    month TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    reported INTEGER NOT NULL DEFAULT 0,
    at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS turn_month ON turn (month);
CREATE INDEX IF NOT EXISTS turn_cabinet ON turn (cabinet_id, at);
"""


class Store:
    def __init__(self, path, clock=time.time):
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        if path != ":memory:":
            self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        self.lock = threading.Lock()
        self.clock = clock

    def find(self, khash):
        return self.db.execute("SELECT * FROM cabinets WHERE key_hash = ?", (khash,)).fetchone()

    def banned(self, khash):
        return self.db.execute("SELECT 1 FROM bans WHERE key_hash = ?", (khash,)).fetchone() is not None

    def ban(self, khash, reason):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO bans VALUES (?, ?, ?)", (khash, reason, self.clock()))

    def signups_since(self, ip, seconds):
        row = self.db.execute("SELECT COUNT(*) FROM signups WHERE ip = ? AND at > ?",
                              (ip, self.clock() - seconds)).fetchone()
        return row[0]

    def _free_tag(self, khash, nick, own_id=None):
        for tag in identity.tags_for(khash):
            row = self.db.execute("SELECT id FROM cabinets WHERE nick = ? AND tag = ?", (nick, tag)).fetchone()
            if row is None or row["id"] == own_id:
                return tag

    def register(self, khash, nick, ip=""):
        """A new cabinet: its tag is the first free one for this nickname."""
        with self.lock:
            now = self.clock()
            self.db.execute("BEGIN IMMEDIATE")
            try:
                tag = self._free_tag(khash, nick)
                cur = self.db.execute(
                    "INSERT INTO cabinets (key_hash, nick, tag, created, last_seen) VALUES (?, ?, ?, ?, ?)",
                    (khash, nick, tag, now, now))
                self.db.execute("INSERT INTO signups VALUES (?, ?)", (ip, now))
                self.db.execute("COMMIT")
            except Exception:
                self.db.execute("ROLLBACK")
                raise
            return cur.lastrowid, nick, tag

    def record(self, cab_id):
        """(version, {game: {"w": n, "l": n}}) of a cabinet; (1, {}) before any match."""
        import json
        row = self.db.execute("SELECT version, record FROM profiles WHERE cabinet_id = ?", (cab_id,)).fetchone()
        return (row["version"], json.loads(row["record"])) if row else (1, {})

    def add_result(self, cab_id, game, won):
        """One more win or loss in a game: the version goes up (phase 3 calls it
        once both cabinets agree on the result)."""
        import json
        with self.lock:
            version, rec = self.record(cab_id)
            r = rec.setdefault(game, {"w": 0, "l": 0})
            r["w" if won else "l"] += 1
            self.db.execute("INSERT OR REPLACE INTO profiles VALUES (?, ?, ?)",
                            (cab_id, version + 1, json.dumps(rec, sort_keys=True)))
            return version + 1, rec

    def row(self, cab_id):
        return self.db.execute("SELECT * FROM cabinets WHERE id = ?", (cab_id,)).fetchone()

    def seen(self, cab_id, nick):
        """A cabinet that came back: last_seen, and the new nickname if it
        changed (the tag stays unless another cabinet has it with that name)."""
        with self.lock:
            row = self.db.execute("SELECT * FROM cabinets WHERE id = ?", (cab_id,)).fetchone()
            tag = row["tag"]
            if nick != row["nick"]:
                taken = self.db.execute("SELECT id FROM cabinets WHERE nick = ? AND tag = ? AND id != ?",
                                        (nick, tag, cab_id)).fetchone()
                if taken:
                    tag = self._free_tag(row["key_hash"], nick, cab_id)
            self.db.execute("UPDATE cabinets SET nick = ?, tag = ?, last_seen = ? WHERE id = ?",
                            (nick, tag, self.clock(), cab_id))
            return nick, tag

    # -- The relay's credentials (turn.py) --
    def turn_bytes(self, month):
        row = self.db.execute("SELECT COALESCE(SUM(bytes), 0) FROM turn WHERE month = ?", (month,)).fetchone()
        return row[0]

    def turn_issued_since(self, cab_id, since):
        row = self.db.execute("SELECT COUNT(*) FROM turn WHERE cabinet_id = ? AND at > ?", (cab_id, since)).fetchone()
        return row[0]

    def turn_issue(self, cab_id, username, month, reserve, now):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO turn VALUES (?, ?, ?, ?, 0, ?)",
                            (username, cab_id, month, reserve, now))

    def turn_report(self, cab_id, username, nbytes):
        """The bytes a credential carried, once, by the cabinet it was given to."""
        with self.lock:
            cur = self.db.execute("UPDATE turn SET bytes = ?, reported = 1 WHERE username = ? AND cabinet_id = ? "
                                  "AND reported = 0", (nbytes, username, cab_id))
            return cur.rowcount == 1
