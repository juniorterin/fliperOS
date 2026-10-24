"""No gabinete: exporta para /tmp/demo.tar a biblioteca de amostra do video
(listas filtradas, midia, videos, informacoes, favoritos, nomes das ROMs).
Le a escolha de /tmp/pick.txt (saida do pick.py)."""
import os
import tarfile

HOME = os.path.expanduser("~")
LISTS = os.path.join(HOME, ".local/share/fliperos/lists")
TAKE = {"mame": 40, "naomi": 10, "naomi2": 3, "atomiswave": 6, "model2": 6, "model3": 6, "retroarch/mame2010": 6}
CLONES_PER_PARENT = 3

chosen = {}
for line in open("/tmp/pick.txt"):
    key, title, _, names = line.rstrip("\n").split("|")
    if key in TAKE:
        chosen[key] = (title, names.split()[:TAKE[key]])

systems = {}
for line in open(os.path.join(HOME, ".cache/fliperos/frontend-systems")):
    p = line.strip().split("|")
    if len(p) >= 7:
        systems[p[0]] = p

out = tarfile.open("/tmp/demo.tar", "w")


def add(path):
    if os.path.lexists(path):
        real = os.path.realpath(path)
        arc = os.path.relpath(path, HOME)
        out.add(real, arcname=arc, recursive=False)
        return True
    return False


manifest = []
for key, (title, names) in chosen.items():
    folder = systems[key][1]
    rows = []
    keep = set(names)
    lines = open(os.path.join(LISTS, title + ".txt"), encoding="utf-8", errors="replace").read().splitlines()
    header = [l for l in lines if l.startswith("#")][:1]
    clones = {}
    for l in lines:
        if l.startswith("#"):
            continue
        f = l.split(";")
        if f[0] in keep:
            rows.append(l)
        elif len(f) > 3 and f[3] in keep and len(clones.setdefault(f[3], [])) < CLONES_PER_PARENT:
            clones[f[3]].append(f[0])
            rows.append(l)
    path = "/tmp/demo-lists/%s.txt" % title
    os.makedirs("/tmp/demo-lists", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(header + rows) + "\n")
    out.add(path, arcname=".local/share/fliperos/lists/%s.txt" % title)
    every = [r.split(";")[0] for r in rows]
    for name in every:
        for kind in ("snap", "box", "logo", "marquee"):
            for ext in (".png", ".jpg"):
                add(os.path.join(HOME, "media", kind, key, name + ext))
        for ext in (".mp4", ".mkv", ".avi"):
            add(os.path.join(HOME, "media", "preview", key, name + ext))
        for lang in ("en", "pt"):
            add(os.path.join(HOME, "media", "info", key, "%s.%s.json" % (name, lang)))
        files = [f for f in (os.listdir(folder) if os.path.isdir(folder) else []) if os.path.splitext(f)[0] == name]
        for f in files:
            manifest.append("%s\t%s" % (key, f))
with open("/tmp/demo-roms.txt", "w") as fh:
    fh.write("\n".join(manifest) + "\n")
out.add("/tmp/demo-roms.txt", arcname="demo-roms.txt")
for p in (".cache/fliperos/frontend-systems", ".cache/fliperos/frontend-filters", ".config/fliperos/favourites"):
    add(os.path.join(HOME, p))
out.close()
print(len(manifest), "rom files;", os.path.getsize("/tmp/demo.tar") // 1048576, "MB")
