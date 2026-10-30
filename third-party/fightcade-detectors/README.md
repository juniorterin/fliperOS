# Fightcade detectors

One `<game>.inf` per ROM set, saying where in the game's memory a match starts,
where each side wins and which character each side chose. FliperOS reads them to
show the wins and the characters of a versus match on the LED display and in the
marquee preview of the web panel (`config/fliperos-versus` and the MAME plugin
in `config/mame-plugins/fliperos-versus`).

- **Source:** <https://github.com/fightcadeorg/fightcade-detectors>, commit
  `de9e7a99c494af488ed64155678e9d22d78f7ae6` (319 files, unchanged).
- **License:** the upstream repository has none. These files are kept here as a
  reference copy of the version FliperOS uses, so you can read and diff them. They
  are **not installed in the image** (nothing in `config/` points here): the
  cabinet downloads them itself with `fliperos-versus fetch`, into
  `~/.local/share/fliperos/versus-detectors`.
- **Format:** one line per target, `target=name,area,operation,0xADDRESS,value,bits`
  (`start`, `player1`, `player2`, `char1`, `char2`), plus `char=N,Name` lines for
  the character names. `config/fliperos-versus` (`read_detector`) is the parser.

## Updating the copy

The commit is pinned in `config/fliperos-versus` (`DETECTORS_COMMIT`). After
changing it, refresh this folder with the same download the cabinet uses:

    VERSUS_DETECTORS=third-party/fightcade-detectors python3 config/fliperos-versus fetch

It writes the new files and removes the ones the new commit no longer has. Then
update the commit above and regenerate the games list of the wiki
(`tools/scoreboard-games.py`, which reads this folder by default).
