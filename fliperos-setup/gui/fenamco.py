"""Jogos Namco System 246/256 empacotados (gui/fedata.py, gui/fliperos-frontend).

Uma pasta como a do archive.org "Namco System 2X6" (NM00019 Tekken 5/ com
"NM00019 TE51 DVD0 (DVD-ROM).iso.gz" e "NM00019 TE51, Ver.B4 a026051314505a.bin.gz"),
posta em ~/roms/namco246 ou ~/roms/namco256 com qualquer nome, vira no frontend
um jogo pai (o da versao mais nova) e as outras versoes como clones. Uma versao
e um disco e um dongle do mesmo codigo (TE51 com TE51); ao escolher uma, o
frontend extrai o que ela precisa (ver unpack) e abre o PCSX2x6.

O que sobra depois de extrair fica no registro .fliperos-namco.json da pasta
dos jogos: os discos e os dongles ja extraidos (outra versao do mesmo disco ou
dongle os reaproveita, sem os .gz que foram apagados) e as versoes montadas.
"""
import gzip
import json
import os
import re
import shutil
import threading
import urllib.request
import zipfile

KEYS = ("namco246", "namco256")
GAME_INDEX = os.environ.get("FLIPEROS_PCSX2X6_GAMEINDEX", "/opt/pcsx2x6/usr/bin/resources/GameIndex.yaml")
PROVERB = os.environ.get("FLIPEROS_PROVERB_URL",
                         "https://github.com/PS2Homebrew-arcade/proverb/releases/download/nightly/proverb.zip")
REGISTRY = ".fliperos-namco.json"
CHUNK = 1 << 20
NAME = re.compile(r"^(NM\d{5}) (.+)$")
# "TE51 DVD0B [Ver.5.1] (DVD-ROM).iso.gz", "RRV1-A (CD-ROM).iso.gz", "CBR1-HA (HDD).img.gz"
DISC_TAIL = re.compile(r"^(?P<label>.+?) \((?P<kind>DVD-ROM|CD-ROM|HDD)\)\.(?P<ext>iso|chd|img)(?P<gz>\.gz)?$", re.I)
# "TE51, Ver.B4 a026051314505a.bin.gz", "B3900065A, Ver.2.07J.bin.gz", "IDMT1, Ver.D a0260... [Tower].bin.gz"
DONGLE_TAIL = re.compile(r"^(?P<code>[\w-]+), (?P<ver>Ver\.\S+)(?: (?P<serial>a\d+a))?(?P<tags>(?: \[[^\]]+\])*)"
                         r"\.bin(?P<gz>\.gz)?$", re.I)
# Discos que sao ferramenta, nao jogo.
TOOL_TAGS = ("firmware updater",)


def home():
    return os.environ.get("FLIPEROS_HOME") or os.path.expanduser("~")


def slug(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def disc_code(label):
    """O codigo do disco que casa com o do dongle: a primeira palavra do nome
    (TE51 de "TE51 DVD0B [Ver.5.1]") sem o "-DVD0"/"-HDD0" (o disco
    SC31001-NA-DVD0-A e o dongle SC31001-NA-A)."""
    return re.sub(r"-(?:DVD|CD|HDD)\d*[A-Z]?(?=-|$)", "", label.split()[0].upper())


def norm(code):
    """So letras e numeros: TK8100-1-NA-A (disco) e TK81001-NA-A (dongle) viram o mesmo."""
    return re.sub(r"[^A-Z0-9]", "", code.upper())


def parse_part(file):
    """(gid, "disc"|"dongle", info) de um nome de arquivo do pacote, ou None
    (o que nao e disco nem dongle, e os discos de ferramenta)."""
    m = NAME.match(file)
    if not m:
        return None
    gid, rest = m.group(1).upper(), m.group(2)
    d = DISC_TAIL.match(rest)
    if d:
        label = d.group("label")
        tags = re.findall(r"\[([^\]]+)\]", label)
        if any(t.lower() in TOOL_TAGS for t in tags):
            return None
        code = disc_code(label)
        return gid, "disc", {"file": file, "label": label, "code": code, "norm": norm(code), "kind": d.group("kind").upper(),
                             "gz": bool(d.group("gz")), "ext": d.group("ext").lower()}
    d = DONGLE_TAIL.match(rest)
    if d:
        tags = re.findall(r"\[([^\]]+)\]", d.group("tags") or "")
        code = d.group("code").upper()
        return gid, "dongle", {"file": file, "code": code, "norm": norm(code), "ver": d.group("ver"),
                               "serial": d.group("serial") or "", "tag": ", ".join(tags) or None, "gz": bool(d.group("gz"))}
    return None


def game_index(path=None):
    """{NM00019: {"name", "region", "media"}} do GameIndex.yaml do PCSX2x6."""
    out, cur = {}, None
    try:
        with open(path or GAME_INDEX, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = re.match(r"^(NM\d{5}):\s*$", line)
                if m:
                    cur = out.setdefault(m.group(1), {})
                    continue
                if cur is not None and line.startswith("  ") and not line.startswith("   "):
                    key, _, value = line.strip().partition(":")
                    if key in ("name", "region", "media"):
                        cur[key] = value.strip().strip("\"'")
                elif cur is not None and line.strip() and not line.startswith(" "):
                    cur = None
    except OSError:
        pass
    return out


def board(region):
    """O sistema (pasta de ~/roms) da placa que a regiao do GameIndex diz."""
    return "namco246" if (region or "").strip() == "System246" else "namco256"


def registry_path(folder):
    return os.path.join(folder, REGISTRY)


def read_registry(folder):
    try:
        with open(registry_path(folder), encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("games", {})
            data.setdefault("discs", {})
            data.setdefault("dongles", {})
            return data
    except (OSError, ValueError):
        pass
    return {"games": {}, "discs": {}, "dongles": {}}


def write_registry(folder, data):
    tmp = registry_path(folder) + ".part"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    os.replace(tmp, registry_path(folder))


def roots(system):
    """As duas pastas Namco de ~/roms, pela pasta do sistema."""
    base = os.path.dirname(os.path.normpath(system["folder"]))
    return {k: os.path.join(base, k) for k in KEYS}


def parts_in(folder, depth=2):
    """Os arquivos de disco e de dongle de uma pasta Namco, nela e nas
    subpastas (ate depth): (caminho, gid, "disc"|"dongle", info)."""
    found = []
    base = os.path.normpath(folder)
    for top, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        if top[len(base):].count(os.sep) >= depth:
            dirs[:] = []
        for name in files:
            part = parse_part(name)
            if part:
                found.append((os.path.join(top, name),) + part)
    return found


def collect(system):
    """{gid: {"discs": [...], "dongles": [...]}} do que as pastas Namco tem
    (os .gz e os arquivos soltos) e do que o registro diz que ja foi extraido."""
    games = {}

    def add(gid, kind, info):
        entry = games.setdefault(gid, {"discs": [], "dongles": []})
        entry["discs" if kind == "disc" else "dongles"].append(info)

    for folder in roots(system).values():
        for path, gid, kind, info in parts_in(folder):
            add(gid, kind, dict(info, path=path))
        reg = read_registry(folder)
        for section, want in (("discs", "disc"), ("dongles", "dongle")):
            for file, entry in reg[section].items():
                part = parse_part(file)
                if part and part[1] == want and os.path.exists(entry["path"]):
                    gid, kind, info = part
                    have = games.get(gid, {}).get(section, [])
                    if not any(x["file"] == file for x in have):
                        add(gid, kind, dict(info, path=entry["path"], gz=False))
    return games


def version_name(gid, disc, dongle):
    return "%s_%s_%s" % (gid, slug(disc["label"]), slug(dongle["ver"] + ("_" + dongle["tag"] if dongle["tag"] else "")))


def sort_key(disc, dongle):
    """A versao mais nova primeiro; as de ferramenta ([Live Monitor], [Rebuilt]) por ultimo."""
    return (0 if dongle["tag"] else 1, disc["norm"], disc["label"], dongle["ver"])


def related(a, b):
    """Um codigo e o comeco ou o fim do outro (RRV1 e RRV1-A, IN2 e HM-IN2), ou
    os dois comecam igual por 7 ou mais caracteres (ZNT1001STA e ZNT1001NAA)."""
    return len(a) >= 3 and len(b) >= 3 and (a.startswith(b) or b.startswith(a) or a.endswith(b) or b.endswith(a)
                                            or len(os.path.commonprefix([a, b])) >= 7)


def combos(info):
    """As versoes: cada dongle com o disco (ou a imagem de HD) dele. O de
    mesmo codigo; senao o de codigo parecido; senao, se o jogo so tem um
    disco, esse. Um dongle sem par fica de fora."""
    discs, out = info["discs"], []
    for dongle in info["dongles"]:
        exact = [d for d in discs if d["norm"] == dongle["norm"]]
        near = exact or [d for d in discs if related(d["norm"], dongle["norm"])]
        for disc in near or (discs if len(discs) == 1 else []):
            out.append((disc, dongle))
    return out


def title_of(gid, index):
    return (index.get(gid) or {}).get("name") or gid


def merge(system, rows, index=None):
    """As linhas da pasta (web.games) com os jogos empacotados: a versao mais
    nova e o pai (o jogo), as outras clones dele; as ja extraidas (um .acgame
    do registro) ficam no grupo; as que faltam extrair entram com Packed=1.
    Um disco ou dongle sem par e um jogo sem disco ficam de fora."""
    if system.get("key") not in KEYS:
        return rows
    index = index if index is not None else game_index()
    mine = roots(system)
    mine_folder = os.path.normpath(system["folder"])
    registries = {k: read_registry(f) for k, f in mine.items()}
    installed = {}
    for key, reg in registries.items():
        for name, entry in reg["games"].items():
            installed[name] = dict(entry, board=key)
    by_name = {r["Name"]: r for r in rows}
    cands = {}      # gid -> [(sortkey, Name, packed-info or None)]
    for name, entry in installed.items():
        if entry["board"] == system["key"] and name in by_name:
            cands.setdefault(entry["gid"], []).append((tuple(entry["sort"]), name, None))
    for gid, info in collect(system).items():
        meta = index.get(gid) or {}
        if board(meta.get("region")) != system["key"]:
            continue
        for disc, dongle in combos(info):
            name = version_name(gid, disc, dongle)
            if name in installed and name in by_name:
                continue
            cands.setdefault(gid, []).append((sort_key(disc, dongle), name, (disc, dongle)))
    out = []
    for gid, items in cands.items():
        items.sort(key=lambda c: c[0], reverse=True)
        title = title_of(gid, index)
        parent = items[0][1]
        for n, (key, name, packed) in enumerate(items):
            if packed:
                disc, dongle = packed
                label = "%s, %s%s" % (disc["label"], dongle["ver"], " [%s]" % dongle["tag"] if dongle["tag"] else "")
                row = {"Name": name, "Title": title if n == 0 else "%s (%s)" % (title, label), "Packed": "1",
                       "Manufacturer": "Namco", "Category": "Arcade", "GameId": gid}
                if n:
                    row["CloneOf"] = parent
                out.append(row)
            else:
                row = by_name[name]
                label = installed[name].get("label", "")
                row["Title"] = title if n == 0 else "%s (%s)" % (title, label)
                row.setdefault("Manufacturer", "Namco")
                if n:
                    row["CloneOf"] = parent
                else:
                    row.pop("CloneOf", None)
    for row in out:
        by_name.setdefault(row["Name"], row)
    merged = [r for r in rows if r["Name"] not in {o["Name"] for o in out}] + out
    merged.sort(key=lambda e: (e.get("Title") or e["Name"]).lower())
    return merged


def _gunzip(src, dst, progress, cancel, base, total):
    """src (.gz, ou um arquivo solto: so move) em dst, devolvendo os bytes de
    src ja lidos: o andamento e o do arquivo comprimido."""
    tmp = dst + ".part"
    if not src.lower().endswith(".gz"):
        if cancel.is_set():
            raise InterruptedError
        shutil.move(src, tmp)
        os.replace(tmp, dst)
        return os.path.getsize(dst)
    size = os.path.getsize(src)
    try:
        with open(src, "rb") as raw, gzip.GzipFile(fileobj=raw) as gz, open(tmp, "wb") as out:
            while True:
                if cancel.is_set():
                    raise InterruptedError
                chunk = gz.read(CHUNK)
                if not chunk:
                    break
                # Um pedaco todo de zeros nao e gravado (o arquivo fica esparso): as
                # imagens de HD sao quase todas vazias e nao ocupam o disco inteiro.
                if chunk.count(0) == len(chunk):
                    out.seek(len(chunk), os.SEEK_CUR)
                else:
                    out.write(chunk)
                progress(base + raw.tell(), total, os.path.basename(src))
            out.truncate(out.tell())
        os.replace(tmp, dst)
    except BaseException:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return size


def boot_elf(gid, dest, cache=None):
    """O boot.elf do jogo (e o que mais o proverb traz na pasta dele), do
    proverb.zip em cache; sem ele (ou sem o jogo nele), baixa de novo."""
    cache = cache or os.path.join(home(), ".cache", "fliperos", "proverb.zip")
    prefix = "bin/%s/" % gid

    def members():
        try:
            with zipfile.ZipFile(cache) as z:
                return [n for n in z.namelist() if n.startswith(prefix) and not n.endswith("/")]
        except (OSError, zipfile.BadZipFile):
            return []
    names = members()
    if not names:
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        part = cache + ".part"
        with urllib.request.urlopen(PROVERB, timeout=60) as resp, open(part, "wb") as out:
            shutil.copyfileobj(resp, out)
        os.replace(part, cache)
        names = members()
    if not any(n.endswith("/boot.elf") for n in names):
        raise OSError("no boot.elf for %s" % gid)
    with zipfile.ZipFile(cache) as z:
        for n in names:
            target = os.path.join(dest, n[len(prefix):])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with z.open(n) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)


def find_version(system, name, index=None):
    """(gid, disc, dongle) da versao NAME entre as empacotadas, ou None."""
    index = index if index is not None else game_index()
    for gid, info in collect(system).items():
        for disc, dongle in combos(info):
            if version_name(gid, disc, dongle) == name:
                return gid, disc, dongle
    return None


def unpack(system, name, progress, cancel=None, index=None):
    """Extrai a versao NAME para a pasta da placa dela: o .acgame, a pasta com
    o boot.elf e o disco, e o dongle em ~/save/PLACA. Quando tudo deu certo, os
    .gz usados saem; um disco ou dongle que outra versao ainda usa fica no
    registro. progress(feitos, total, arquivo); levanta OSError/InterruptedError.
    Devolve o caminho do .acgame."""
    cancel = cancel or threading.Event()
    index = index if index is not None else game_index()
    found = find_version(system, name, index)
    if not found:
        raise OSError("the files of this game are gone")
    gid, disc, dongle = found
    meta = index.get(gid) or {}
    plat = board(meta.get("region"))
    folder = roots(system)[plat]
    save = os.path.join(home(), "save", plat)
    reg = read_registry(folder)
    title = title_of(gid, index)
    vdir = os.path.join(folder, name)
    acgame = os.path.join(folder, name + ".acgame")
    os.makedirs(folder, exist_ok=True)
    # O disco inteiro (um .gz rende uns 1,5 a 2 vezes o tamanho dele) e folga.
    need = (os.path.getsize(disc["path"]) * 2 if disc["gz"] else 0) + (32 << 20) + (200 << 20)
    if shutil.disk_usage(folder).free < need:
        raise OSError("not enough space")
    total = (os.path.getsize(disc["path"]) if disc["gz"] else 1) + (os.path.getsize(dongle["path"]) if dongle["gz"] else 1)
    done = 0
    used = []
    shared_disc = reg["discs"].get(disc["file"], {}).get("path") == disc["path"]
    shared_dongle = reg["dongles"].get(dongle["file"], {}).get("path") == dongle["path"]
    try:
        os.makedirs(vdir, exist_ok=True)
        progress(0, total, "boot.elf")
        boot_elf(gid, vdir)
        iso = os.path.join(vdir, name + "." + disc["ext"])
        if disc["gz"]:
            done += _gunzip(disc["path"], iso, progress, cancel, done, total)
            reg["discs"][disc["file"]] = {"path": iso}
            used.append(disc["path"])
        elif shared_disc:
            # Outra versao ja extraiu este disco: a pasta desta aponta para ele.
            if os.path.lexists(iso):
                os.remove(iso)
            os.symlink(disc["path"], iso)
        else:
            _gunzip(disc["path"], iso, progress, cancel, done, total)      # um .iso solto: so muda de lugar
            reg["discs"][disc["file"]] = {"path": iso}
        os.makedirs(save, exist_ok=True)
        ps2 = os.path.join(save, "%s_%s.ps2" % (gid, slug("%s_%s_%s" % (dongle["code"], dongle["ver"], dongle["serial"]))))
        if shared_dongle:
            ps2 = dongle["path"]
        elif dongle["gz"]:
            done += _gunzip(dongle["path"], ps2, progress, cancel, done, total)
            used.append(dongle["path"])
        else:
            _gunzip(dongle["path"], ps2, progress, cancel, done, total)
        if not shared_dongle:
            # O jogo regrava o dongle: uma copia de como veio fica ao lado.
            backup = os.path.join(save, "originals")
            os.makedirs(backup, exist_ok=True)
            shutil.copyfile(ps2, os.path.join(backup, os.path.basename(ps2)))
        reg["dongles"][dongle["file"]] = {"path": ps2}
        label = "%s, %s%s" % (disc["label"], dongle["ver"], " [%s]" % dongle["tag"] if dongle["tag"] else "")
        with open(acgame + ".part", "w", encoding="utf-8", newline="\n") as f:
            f.write("[game]\nname=%s\ngameid=%s\nplatform=%s\n\n[data]\nsubdir=%s\nelf=boot.elf\ndongle=%s\n"
                    "mediasrc=%s\nmedia=%s\n" % (title, gid, "256" if plat == "namco256" else "246", name,
                                                   os.path.basename(ps2), os.path.basename(iso), meta.get("media") or "DVD"))
        os.replace(acgame + ".part", acgame)
        reg["games"][name] = {"gid": gid, "label": label, "sort": list(sort_key(disc, dongle))}
        write_registry(folder, reg)
        progress(total, total, "")
    except BaseException:
        if not os.path.exists(acgame):
            shutil.rmtree(vdir, ignore_errors=True)
        raise
    for path in used:
        try:
            os.remove(path)
            parent = os.path.dirname(path)
            if os.path.normpath(parent) not in [os.path.normpath(r) for r in roots(system).values()] and not os.listdir(parent):
                os.rmdir(parent)
        except OSError:
            pass
    return acgame
