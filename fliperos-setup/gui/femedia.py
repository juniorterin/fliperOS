#!/usr/bin/env python3
# A midia fisica do frontend do FliperOS (gui/fliperos-frontend): os drives
# de CD/DVD, o console de cada disco (lido do proprio disco), o comando que
# abre o jogo direto do drive (o emulador standalone ou um core do RetroArch
# que le o drive) e o rip para a pasta do sistema.
#
#   femedia.py list                     os drives e o estado de cada um
#   femedia.py identify /dev/sr0        o console, o serial e o titulo do disco
#   femedia.py rip /dev/sr0 PASTA NOME  rippa, com as linhas @step/@done/@fail
#   femedia.py oscr-hello /dev/ttyUSB0  o firmware do FliperOS responde?
#   femedia.py oscr-scan /dev/ttyUSB0   os cartuchos no OSCR (JSON)
#   femedia.py oscr-info /dev/ttyUSB0 SNES          o cartucho de um sistema
#   femedia.py oscr-rip /dev/ttyUSB0 SNES PASTA NOME  o dump, como o rip
#
# O RetroArch le o drive pelo "cdrom://driveN.cue", e N e o /dev/sgN do drive
# (libretro-common, vfs_implementation_cdrom.c); so os cores compilados com o
# HAVE_CDROM sabem abrir esse caminho. O DuckStation abre o /dev/srN e o
# PCSX2 o "-disc /dev/srN". Dreamcast (GD-ROM) e GameCube nao entram: um
# drive de PC nao le esses discos.

import fcntl
import json
import os
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import time
import zlib

SYS_BLOCK = os.environ.get("FLIPEROS_SYS_BLOCK", "/sys/block")
DEV_DIR = os.environ.get("FLIPEROS_DEV_DIR", "/dev")
BIN = os.environ.get("FLIPEROS_BIN", "/opt/fliperos/bin")
RA_CORES = os.environ.get("FLIPEROS_RA_CORES", "/opt/fliperos/retroarch/cores")

# linux/cdrom.h
CDROMREADTOCHDR, CDROMREADTOCENTRY, CDROM_DRIVE_STATUS = 0x5305, 0x5306, 0x5326
CDSL_CURRENT = 0x7FFFFFFF
CDROM_LBA, CDROM_LEADOUT, CDROM_DATA_TRACK = 0x01, 0xAA, 0x04
TOCENTRY = "BBBxiB3x"      # struct cdrom_tocentry (o lba alinhado em 4)
STATES = {1: "empty", 2: "open", 3: "busy", 4: "disc"}
# O que a fileira PHYSICAL MEDIA escreve embaixo de cada drive.
LABELS = {"disc": "DISC", "empty": "EMPTY", "open": "OPEN", "busy": "WAIT", "noaccess": "NO ACCESS",
          "unknown": "?"}
SECTOR, RAW = 2048, 2352
DVD_BYTES = 900 * 1024 * 1024   # acima disso e um DVD: o rip e a imagem .iso

# Os consoles que o FliperOS abre do drive: o nome, os standalones (id, nome,
# programa, argumentos, pasta em ~/roms) e os cores do RetroArch que leem o
# drive (HAVE_CDROM no Makefile de cada um), o preferido primeiro.
CONSOLES = {
    "psx": {"name": "Sony PlayStation",
            "standalone": [("duckstation", "DUCKSTATION", "duckstation", ["{dev}"], "ps1")],
            "cores": ("mednafen_psx_hw", "mednafen_psx", "pcsx_rearmed")},
    "ps2": {"name": "Sony PlayStation 2",
            "standalone": [("pcsx2", "PCSX2", "pcsx2", ["-disc", "{dev}"], "ps2")], "cores": ()},
    "saturn": {"name": "Sega Saturn", "standalone": [], "cores": ("mednafen_saturn",)},
    "segacd": {"name": "Sega CD", "standalone": [], "cores": ("genesis_plus_gx",)},
    "pce": {"name": "PC Engine CD", "standalone": [], "cores": ("mednafen_pce_fast", "mednafen_pce")},
    "pcfx": {"name": "PC-FX", "standalone": [], "cores": ("mednafen_pcfx",)},
    "3do": {"name": "3DO", "standalone": [], "cores": ("opera",)},
    "neocd": {"name": "Neo Geo CD", "standalone": [], "cores": ("neocd",)},
    # Os cartuchos do OSCR: o jogo abre do arquivo do dump (CARTS).
    "snes": {"name": "Super Nintendo", "standalone": [], "cores": ("snes9x", "bsnes", "mesen-s")},
    "md": {"name": "Mega Drive", "standalone": [], "cores": ("genesis_plus_gx", "picodrive")},
    "n64": {"name": "Nintendo 64", "standalone": [], "cores": ("mupen64plus_next", "parallel_n64")},
    "gb": {"name": "Game Boy", "standalone": [], "cores": ("gambatte", "sameboy", "mgba")},
    "gba": {"name": "Game Boy Advance", "standalone": [], "cores": ("mgba", "vba_next")},
}
CORE_LABELS = {"mednafen_psx_hw": "BEETLE PSX HW", "mednafen_psx": "BEETLE PSX", "pcsx_rearmed": "PCSX REARMED",
               "mednafen_saturn": "BEETLE SATURN", "genesis_plus_gx": "GENESIS PLUS GX",
               "mednafen_pce_fast": "BEETLE PCE FAST", "mednafen_pce": "BEETLE PCE", "mednafen_pcfx": "BEETLE PC-FX",
               "opera": "OPERA", "neocd": "NEOCD", "snes9x": "SNES9X", "bsnes": "BSNES", "mesen-s": "MESEN-S",
               "picodrive": "PICODRIVE", "mupen64plus_next": "MUPEN64PLUS-NEXT", "parallel_n64": "PARALLEL N64",
               "gambatte": "GAMBATTE", "sameboy": "SAMEBOY", "mgba": "MGBA", "vba_next": "VBA NEXT"}


def read_text(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    except OSError:
        return ""


# ── Os drives ──────────────────────────────────────────────────────
def drives():
    """Os drives de CD/DVD na ordem do kernel (sr0, sr1...): a chave, o nome
    da tela (DRIVE 1, DRIVE 2...), o modelo, o /dev e o /dev/sgN do RetroArch."""
    try:
        names = [n for n in os.listdir(SYS_BLOCK) if re.fullmatch(r"sr\d+", n)]
    except OSError:
        names = []
    out = []
    for i, name in enumerate(sorted(names, key=lambda n: int(n[2:])), 1):
        device = os.path.join(SYS_BLOCK, name, "device")
        model = " ".join(w for w in (read_text(os.path.join(device, "vendor")),
                                     read_text(os.path.join(device, "model"))) if w)
        try:
            sg = next((s for s in os.listdir(os.path.join(device, "scsi_generic")) if re.fullmatch(r"sg\d+", s)), None)
        except OSError:
            sg = None
        out.append({"key": name, "kind": "cd", "name": "DRIVE %d" % i, "model": model or "CD/DVD",
                    "dev": os.path.join(DEV_DIR, name), "sg": sg})
    return out


def drive_state(dev):
    """disc, empty, open (a gaveta aberta), busy (o disco ainda girando),
    noaccess (sem permissao: o usuario fora do grupo cdrom) ou unknown."""
    try:
        fd = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
    except PermissionError:
        return "noaccess"
    except OSError:
        return "unknown"
    try:
        return STATES.get(fcntl.ioctl(fd, CDROM_DRIVE_STATUS, CDSL_CURRENT), "unknown")
    except OSError:
        return "unknown"
    finally:
        os.close(fd)


def scan():
    """Os drives com o estado de cada um e, depois deles, os OSCR ligados (o
    que a fileira mostra). O OSCR nao e aberto aqui: abrir a porta o reinicia."""
    out = drives()
    for d in out:
        d["state"] = drive_state(d["dev"])
        d["label"] = LABELS[d["state"]]
    return out + oscr_ports()


# ── O que tem no disco ─────────────────────────────────────────────
class Disc:
    """O disco (ou uma imagem, nos testes): as trilhas do TOC e os setores de
    2048 bytes."""

    def __init__(self, path):
        self.fd = os.open(path, os.O_RDONLY)
        self.cache = {}
        try:
            self.tracks, self.leadout = self.read_toc()
        except OSError:
            # Uma imagem (ou um drive sem TOC): uma trilha de dados so.
            size = os.fstat(self.fd).st_size or os.lseek(self.fd, 0, os.SEEK_END)
            self.tracks, self.leadout = [{"num": 1, "lba": 0, "data": True}], size // SECTOR
        self.bytes = self.size(path)

    def size(self, path):
        name = os.path.basename(path)
        blocks = read_text(os.path.join(SYS_BLOCK, name, "size"))
        if blocks.isdigit() and int(blocks):
            return int(blocks) * 512
        return self.leadout * SECTOR

    def read_toc(self):
        first, last = fcntl.ioctl(self.fd, CDROMREADTOCHDR, bytes(2))[:2]
        tracks = []
        for num in list(range(first, last + 1)) + [CDROM_LEADOUT]:
            raw = fcntl.ioctl(self.fd, CDROMREADTOCENTRY, struct.pack(TOCENTRY, num, 0, CDROM_LBA, 0, 0))
            _, adr_ctrl, _, lba, _ = struct.unpack(TOCENTRY, raw)
            if num == CDROM_LEADOUT:
                return tracks, lba
            tracks.append({"num": num, "lba": lba, "data": bool((adr_ctrl >> 4) & CDROM_DATA_TRACK)})
        return tracks, 0

    def sector(self, lba):
        if lba not in self.cache:
            try:
                data = os.pread(self.fd, SECTOR, lba * SECTOR)
            except OSError:
                data = b""
            self.cache[lba] = data.ljust(SECTOR, b"\0")
        return self.cache[lba]

    def read(self, lba, size):
        return b"".join(self.sector(lba + i) for i in range((size + SECTOR - 1) // SECTOR))[:size]

    def close(self):
        os.close(self.fd)


def clean(raw):
    """O texto de um cabecalho: sem os nulos, os espacos repetidos e o lixo."""
    text = raw.decode("latin-1", "replace").replace("\0", " ")
    text = re.sub(r"[^\x20-\x7e]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def iso_root(disc, base):
    """Os arquivos da raiz do ISO9660 que comeca em base: NOME -> (lba, tamanho)."""
    pvd = disc.sector(base + 16)
    if pvd[1:6] != b"CD001":
        return None, pvd
    extent, size = struct.unpack_from("<I", pvd, 158)[0], struct.unpack_from("<I", pvd, 166)[0]
    files = {}
    for i in range(min(8, (size + SECTOR - 1) // SECTOR)):
        sec = disc.sector(extent + i)
        p = 0
        while p < SECTOR and sec[p]:
            length = sec[p]
            lba, fsize = struct.unpack_from("<I", sec, p + 2)[0], struct.unpack_from("<I", sec, p + 10)[0]
            name = sec[p + 33:p + 33 + sec[p + 32]].decode("latin-1", "replace").split(";")[0].upper()
            if name not in ("\0", "\1"):
                files[name] = (lba, fsize)
            p += length
    return files, pvd


def ps_serial(text):
    """O serial do jogo da linha BOOT do SYSTEM.CNF (SLUS_000.67 -> SLUS-00067)."""
    m = re.search(r"([A-Z]{4})[_-]?(\d{3})\.?(\d{2})", text.upper())
    return "%s-%s%s" % m.groups() if m else ""


def identify(path):
    """O console do disco: {"console", "name", "title", "serial", "dvd",
    "bytes"}; "unsupported" (o nome do console) num disco que o FliperOS nao
    abre; console None num disco que ninguem reconhece (ou sem disco)."""
    try:
        disc = Disc(path)
    except OSError as e:
        return {"console": None, "error": str(e)}
    try:
        info = detect(disc)
        info.setdefault("title", "")
        info.setdefault("serial", "")
        info["dvd"] = disc.bytes > DVD_BYTES
        info["bytes"] = disc.bytes
        info["sectors"] = disc.leadout
        info["audio"] = sum(1 for t in disc.tracks if not t["data"])
        if info.get("console"):
            info["name"] = CONSOLES[info["console"]]["name"]
        return info
    finally:
        disc.close()


def detect(disc):
    data = [t["lba"] for t in disc.tracks if t["data"]]
    if not data:
        return {"console": None, "audio_only": True}
    base = data[0]
    s0 = disc.sector(base)
    if s0[0x1C:0x20] == b"\xc2\x33\x9f\x3d":
        return {"console": None, "unsupported": "GAMECUBE"}
    if s0[0x18:0x1C] == b"\x5d\x1c\x9e\xa3":
        return {"console": None, "unsupported": "WII"}
    if s0.startswith(b"SEGA SEGASATURN "):
        return {"console": "saturn", "serial": clean(s0[0x20:0x2A]), "title": clean(s0[0x60:0xD0])}
    # O Dreamcast gravado em CD-R tem o IP.BIN no comeco da trilha da segunda sessao.
    if any(disc.sector(lba).startswith(b"SEGA SEGAKATANA ") for lba in data):
        return {"console": None, "unsupported": "DREAMCAST"}
    if s0[:14] in (b"SEGADISCSYSTEM", b"SEGABOOTDISC  ") or s0[:12] == b"SEGABOOTDISC":
        title = clean(s0[0x150:0x180]) or clean(s0[0x120:0x150])
        serial = re.sub(r"^(GM|AI|OS)\s+", "", clean(s0[0x180:0x18E]))
        return {"console": "segacd", "title": title, "serial": re.sub(r"\s*-\d\d$", "", serial)}
    if s0.startswith(b"PC-FX:Hu_CD-ROM"):
        return {"console": "pcfx"}
    if s0[0] == 1 and s0[1:6] == b"\x5a" * 5:
        return {"console": "3do", "title": clean(s0[0x28:0x48])}
    if b"PC Engine CD-ROM SYSTEM" in disc.sector(base + 1)[:0x80]:
        return {"console": "pce"}
    files, pvd = iso_root(disc, base)
    if files is None:
        return {"console": None}
    system, volume = clean(pvd[8:40]), clean(pvd[40:72])
    if "SYSTEM.CNF" in files:
        lba, size = files["SYSTEM.CNF"]
        cnf = disc.read(lba, min(size, 4096)).decode("latin-1", "replace")
        boot2 = re.search(r"^\s*BOOT2\s*=\s*(.+)$", cnf, re.M | re.I)
        boot = boot2 or re.search(r"^\s*BOOT\s*=\s*(.+)$", cnf, re.M | re.I)
        serial = ps_serial(boot.group(1)) if boot else ""
        title = volume if volume and ps_serial(volume) != serial else ""
        return {"console": "ps2" if boot2 else "psx", "serial": serial, "title": title.replace("_", " ")}
    if system.startswith("PLAYSTATION"):
        return {"console": "psx", "title": volume.replace("_", " ")}
    if "IPL.TXT" in files:
        return {"console": "neocd", "title": volume.replace("_", " ")}
    return {"console": None, "label": volume}


# ── Os emuladores ──────────────────────────────────────────────────
def which(exe):
    return shutil.which(exe, path=os.environ.get("PATH", "") + ":/usr/local/bin")


def emulators(console):
    """O que abre o disco: os standalones instalados e, com o RetroArch, os
    cores que leem o drive (os que faltam sao baixados ao abrir). Cada um:
    {"id", "label", "icon", "folder", "core"}."""
    spec = CONSOLES.get(console)
    if not spec:
        return []
    out = []
    for ident, label, exe, _, folder in spec["standalone"]:
        if which(exe):
            out.append({"id": ident, "label": label, "icon": ident, "folder": folder, "core": None})
    if which("retroarch"):
        for core in spec["cores"]:
            out.append({"id": "retroarch:" + core, "label": CORE_LABELS.get(core, core.upper()), "icon": "retroarch",
                        "folder": "retroarch/" + core, "core": core,
                        "missing": not os.path.exists(core_path(core))})
    return out


def core_path(core):
    return os.path.join(RA_CORES, core + "_libretro.so")


def pick(console, saved=None):
    """O emulador do console: o escolhido da ultima vez (se ainda existe) ou
    o primeiro (o standalone, se instalado)."""
    options = emulators(console)
    ids = [o["id"] for o in options]
    if saved in ids:
        return options[ids.index(saved)]
    return options[0] if options else None


def command(console, option, drive, path=None):
    """A linha de comando que abre o disco do drive com option; None quando o
    drive nao serve (o RetroArch so le de /dev/sg0 a /dev/sg9). path: o
    arquivo do dump de um cartucho, que o core abre no lugar do drive."""
    if option["core"] and path:
        return [os.path.join(BIN, "fliperos-kms-run"), "retroarch", "-L", core_path(option["core"]), path]
    if option["core"]:
        sg = drive.get("sg") or ""
        if not re.fullmatch(r"sg\d", sg):
            return None
        return [os.path.join(BIN, "fliperos-kms-run"), "retroarch", "-L", core_path(option["core"]),
                "cdrom://drive%s.cue" % sg[2:]]
    for ident, _, exe, args, _ in CONSOLES[console]["standalone"]:
        if ident == option["id"]:
            return [os.path.join(BIN, "fliperos-x11-run"), exe] + [a.format(dev=drive["dev"]) for a in args]
    return None


def file_name(info):
    """O nome do arquivo do rip: o titulo e o serial, sem o que o sistema de
    arquivos e os frontends nao aceitam."""
    title, serial = info.get("title") or "", info.get("serial") or ""
    name = title or info.get("name") or "Disc"
    if serial and serial not in name:
        name = "%s (%s)" % (name, serial)
    return re.sub(r"\s+", " ", re.sub(r'[\\/:*?"<>|\x00-\x1f]', " ", name)).strip()[:120] or "Disc"


# ── O rip ──────────────────────────────────────────────────────────
# Roda num processo so dele (o frontend le as linhas e cancela com SIGTERM).
# CD: o cdrdao le o disco inteiro em bruto (as trilhas de audio tambem) e o
# toc2cue faz o .cue; com o chdman (mame-tools), vira um .chd so, que o
# DuckStation e os cores abrem, e o .bin/.cue sai. DVD: a imagem .iso.

PARTIAL = []               # os arquivos que um cancelamento apaga


def say(line):
    print(line, flush=True)


def unique(folder, name, exts):
    """Um nome que ainda nao existe na pasta com nenhuma das extensoes."""
    base, n = name, 2
    while any(os.path.exists(os.path.join(folder, base + e)) for e in exts):
        base, n = "%s (%d)" % (name, n), n + 1
    return base


def run_watched(argv, cwd, log, progress):
    """Roda argv com a saida no log, chamando progress() a cada meio segundo."""
    proc = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
    PARTIAL.append(proc)
    while proc.poll() is None:
        progress()
        time.sleep(0.5)
    PARTIAL.remove(proc)
    return proc.returncode


def rip_cd(dev, folder, name, info, log):
    total = max(1, info.get("sectors", 0)) * RAW
    base = unique(folder, name, (".chd", ".cue", ".bin"))
    toc, data, cue = base + ".toc", base + ".bin", base + ".cue"
    PARTIAL.extend(os.path.join(folder, f) for f in (toc, data, cue))
    chdman = which("chdman")
    share = 85 if chdman else 100

    def reading():
        try:
            done = os.path.getsize(os.path.join(folder, data))
        except OSError:
            done = 0
        say("@step %d READING %d OF %d MB" % (min(share - 1, done * share // total), done >> 20, total >> 20))

    rc = run_watched(["cdrdao", "read-cd", "--read-raw", "--driver", "generic-mmc-raw", "--device", dev,
                      "--datafile", data, toc], folder, log, reading)
    if rc != 0 or not os.path.isfile(os.path.join(folder, data)):
        raise RuntimeError("could not read the disc")
    if run_watched(["toc2cue", toc, cue], folder, log, lambda: None) != 0:
        raise RuntimeError("could not write the cue")
    os.unlink(os.path.join(folder, toc))
    if not chdman:
        return os.path.join(folder, cue)
    chd = base + ".chd"
    PARTIAL.append(os.path.join(folder, chd))
    say("@step %d COMPRESSING (CHD)" % share)
    if run_watched([chdman, "createcd", "-i", cue, "-o", chd], folder, log, lambda: None) != 0:
        # Sem o .chd, fica o .bin/.cue (que as listas tambem abrem).
        PARTIAL[:] = []
        return os.path.join(folder, cue)
    for f in (data, cue):
        os.unlink(os.path.join(folder, f))
    return os.path.join(folder, chd)


def rip_dvd(dev, folder, name, info):
    total = max(1, info.get("bytes", 0))
    path = os.path.join(folder, unique(folder, name, (".iso",)) + ".iso")
    PARTIAL.append(path)
    done, last = 0, 0.0
    with open(dev, "rb", buffering=0) as src, open(path, "wb") as out:
        while True:
            chunk = src.read(64 * SECTOR)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if time.monotonic() - last > 0.5:
                last = time.monotonic()
                say("@step %d READING %d OF %d MB" % (min(99, done * 100 // total), done >> 20, total >> 20))
    return path


def cancel(*_):
    for item in PARTIAL:
        if isinstance(item, subprocess.Popen):
            item.terminate()
    for item in PARTIAL:
        if isinstance(item, str):
            try:
                os.unlink(item)
            except OSError:
                pass
    say("@fail cancelled")
    os._exit(1)


def rip(dev, folder, name):
    signal.signal(signal.SIGTERM, cancel)
    PARTIAL[:] = []
    info = identify(dev)
    if info.get("error"):
        say("@fail " + info["error"])
        return 1
    try:
        os.makedirs(folder, exist_ok=True)
        need = info["bytes"] if info["dvd"] else info.get("sectors", 0) * RAW
        if shutil.disk_usage(folder).free < need * 1.1:
            say("@fail not enough space")
            return 1
        log_path = os.path.join(os.path.expanduser("~"), ".cache", "fliperos", "rip.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a") as log:
            log.write("%s %s -> %s/%s\n" % (time.strftime("%Y-%m-%d %H:%M:%S"), dev, folder, name))
            log.flush()
            if info["dvd"]:
                path = rip_dvd(dev, folder, name, info)
            else:
                if not which("cdrdao"):
                    say("@fail cdrdao is not installed")
                    return 1
                path = rip_cd(dev, folder, name, info, log)
    except (OSError, RuntimeError) as e:
        PARTIAL[:] = [p for p in PARTIAL if isinstance(p, str)]
        for p in PARTIAL:
            try:
                os.unlink(p)
            except OSError:
                pass
        say("@fail %s" % e)
        return 1
    say("@step 100 DONE")
    say("@done " + path)
    return 0


# ── O leitor de cartuchos (OSCR) ───────────────────────────────────
# O Open Source Cartridge Reader com o firmware do FliperOS (patches/oscr,
# tools/oscr-firmware.sh) responde pela serial da USB: FLIPEROS, SCAN, INFO,
# DUMP, GET e BAUD, uma linha cada (FLIPEROS.ino). O dump vai primeiro para o
# cartao SD do OSCR (como no menu dele) e de la vem pela USB, a 1 Mbaud, com
# o CRC32 conferido. Abrir a porta reinicia o Mega (o DTR): a conversa espera
# o OSCR ligar. O SCAN so le a 3,3 V: um cartucho de 5 V que nao responde
# assim fica de fora, e o frontend pergunta o sistema dele.

SYS_TTY = os.environ.get("FLIPEROS_SYS_TTY", "/sys/class/tty")
# O conversor USB-serial do HW5 (CH340) e os do Arduino Mega.
OSCR_USB = {("1a86", "7523"), ("2341", "0042"), ("2341", "0010"), ("2a03", "0042")}
# Os sistemas do firmware: o console (CONSOLES) e o nome da tela.
CARTS = {"SNES": "snes", "MD": "md", "N64": "n64", "GB": "gb", "GBA": "gba"}
OSCR_FAST = 1000000


class OscrError(Exception):
    """firmware (o OSCR sem o firmware do FliperOS), noanswer, error (o
    firmware parou num erro), crc (o arquivo chegou estragado)."""


def oscr_ports():
    """Os OSCR ligados: as portas ttyUSB/ttyACM de um conversor que o OSCR usa."""
    try:
        names = sorted(n for n in os.listdir(SYS_TTY) if re.fullmatch(r"tty(USB|ACM)\d+", n))
    except OSError:
        return []
    out = []
    for name in names:
        node = os.path.realpath(os.path.join(SYS_TTY, name, "device"))
        ids = None
        for _ in range(5):
            vid, pid = read_text(os.path.join(node, "idVendor")), read_text(os.path.join(node, "idProduct"))
            if vid:
                ids = (vid.lower(), pid.lower())
                break
            node = os.path.dirname(node)
        if ids in OSCR_USB:
            n = len(out)
            out.append({"key": "oscr%d" % n if n else "oscr", "kind": "oscr", "name": "OSCR" if not n else "OSCR %d" % (n + 1),
                        "model": "CART READER", "dev": os.path.join(DEV_DIR, name), "state": "ready",
                        "label": "READY"})
    return out


class Oscr:
    """A conversa com o OSCR pela porta serial."""

    def __init__(self, dev, wait=10.0):
        self.fd = os.open(dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        self.buf = b""
        self.speed(9600)
        self.systems = self.hello(wait)

    def speed(self, baud):
        attrs = termios.tcgetattr(self.fd)
        attrs[0] = attrs[1] = attrs[3] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[4] = attrs[5] = getattr(termios, "B%d" % baud)
        attrs[6][termios.VMIN], attrs[6][termios.VTIME] = 0, 0
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)

    def send(self, text):
        os.write(self.fd, (text + "\n").encode())

    def fill(self, deadline):
        left = deadline - time.monotonic()
        if left <= 0:
            return False
        if select.select([self.fd], [], [], left)[0]:
            try:
                chunk = os.read(self.fd, 65536)
            except BlockingIOError:
                chunk = b""
            self.buf += chunk
            return True
        return False

    def line(self, timeout):
        """A proxima linha, ou None passado timeout."""
        deadline = time.monotonic() + timeout
        while b"\n" not in self.buf:
            if not self.fill(deadline):
                return None
        raw, _, self.buf = self.buf.partition(b"\n")
        return raw.decode("latin-1").strip()

    def read(self, size, timeout, progress=None):
        """size bytes crus (o GET), chamando progress(feito)."""
        deadline = time.monotonic() + timeout
        while len(self.buf) < size:
            if not self.fill(deadline):
                raise OscrError("noanswer")
            if progress:
                progress(min(size, len(self.buf)))
            deadline = time.monotonic() + timeout
        data, self.buf = self.buf[:size], self.buf[size:]
        return data

    def hello(self, wait):
        """Espera o OSCR ligar e confere o firmware: devolve os sistemas dele."""
        deadline = time.monotonic() + wait
        asked = 0.0
        while time.monotonic() < deadline:
            if time.monotonic() - asked > 1.0:
                self.send("FLIPEROS")
                asked = time.monotonic()
            got = self.line(0.3)
            if got and got.startswith("FLIPEROS 1"):
                return got.split()[2:]
            if got and "Unknown Command" in got:
                raise OscrError("firmware")
        raise OscrError("noanswer")

    def answer(self, timeout):
        """As linhas de um comando, ate o END, o NONE ou o ERROR."""
        lines = []
        while True:
            got = self.line(timeout)
            if got is None:
                raise OscrError("noanswer")
            if got == "ERROR":
                raise OscrError("error")
            if got in ("END", "NONE"):
                return lines, got
            if got.split(" ", 1)[0] in ("CART", "FILE"):
                lines.append(got)

    @staticmethod
    def cart(line):
        system, title, rom, save = (line[5:].split("|") + ["", "", "0", "0"])[:4]
        return {"system": system, "console": CARTS.get(system), "title": title.strip(),
                "rom": int(rom) if rom.isdigit() else 0, "save": int(save) if save.isdigit() else 0}

    def scan(self):
        self.send("SCAN")
        lines, _ = self.answer(120)
        return [self.cart(line) for line in lines]

    def info(self, system):
        self.send("INFO " + system)
        lines, _ = self.answer(60)
        return self.cart(lines[0]) if lines else None

    def dump(self, system):
        """O dump no cartao SD do OSCR; devolve os arquivos que ele gravou."""
        self.send("DUMP " + system)
        lines, end = self.answer(1800)
        if end == "NONE":
            raise OscrError("nocart")
        return [line[5:] for line in lines]

    def get(self, path, progress=None):
        """O arquivo do cartao SD do OSCR, pela USB a OSCR_FAST, conferido."""
        if not getattr(self, "fast", False):
            self.send("BAUD %d" % OSCR_FAST)
            if self.line(5) != "OK":
                raise OscrError("noanswer")
            time.sleep(0.05)
            self.speed(OSCR_FAST)
            self.buf = b""
            self.fast = True
        self.send("GET " + path)
        head = self.line(10)
        if not head or not head.startswith("SIZE "):
            raise OscrError("noanswer")
        size = int(head[5:])
        data = self.read(size, 10, progress and (lambda done: progress(done, size)))
        crc = self.line(10) or ""
        if not crc.startswith("CRC ") or int(crc[4:], 16) != zlib.crc32(data):
            raise OscrError("crc")
        return data

    def close(self):
        os.close(self.fd)


def oscr_rip(dev, system, folder, name):
    """O dump do cartucho para a pasta: a ROM com o nome NOME e o save ao lado,
    com as linhas @step/@done/@fail do rip."""
    signal.signal(signal.SIGTERM, cancel)
    PARTIAL[:] = []
    try:
        os.makedirs(folder, exist_ok=True)
        say("@step 2 STARTING THE OSCR")
        oscr = Oscr(dev)
        say("@step 5 READING THE CARTRIDGE")
        files = oscr.dump(system)
        rom = next((f for f in files if "/ROM/" in f.upper()), files[0] if files else None)
        if not rom:
            raise OscrError("nocart")
        base = unique(folder, name, (os.path.splitext(rom)[1].lower(),))
        out = None
        for i, remote in enumerate([rom] + [f for f in files if f != rom]):
            ext = os.path.splitext(remote)[1].lower()
            # A ROM com o nome do jogo; o save com o mesmo nome (o .srm do RetroArch).
            path = os.path.join(folder, base + (ext if i == 0 else (".srm" if ext in (".srm", ".sav") else ext)))
            PARTIAL.append(path)

            def step(done, total, first=(i == 0)):
                # A ROM de 10 a 98%; o save, pequeno, no fim.
                pct = 10 + done * 88 // max(1, total) if first else 99
                say("@step %d COPYING %d OF %d KB" % (pct, done >> 10, total >> 10))
            data = oscr.get(remote, step)
            with open(path, "wb") as f:
                f.write(data)
            out = out or path
        oscr.close()
    except (OSError, OscrError) as e:
        for p in PARTIAL:
            if isinstance(p, str):
                try:
                    os.unlink(p)
                except OSError:
                    pass
        say("@fail %s" % (e.args[0] if isinstance(e, OscrError) else e))
        return 1
    say("@step 100 DONE")
    say("@done " + out)
    return 0


def oscr_call(dev, what, system=None):
    """SCAN ou INFO, para o frontend (numa thread): {"carts", "systems"} ou
    {"error"}."""
    try:
        oscr = Oscr(dev)
        try:
            if what == "scan":
                return {"carts": oscr.scan(), "systems": oscr.systems}
            cart = oscr.info(system)
            return {"carts": [cart] if cart else [], "systems": oscr.systems}
        finally:
            oscr.close()
    except OscrError as e:
        return {"error": e.args[0]}
    except OSError as e:
        return {"error": "noaccess" if isinstance(e, PermissionError) else str(e)}


def main(argv):
    if argv[:1] == ["list"]:
        print(json.dumps(scan(), indent=1))
        return 0
    if len(argv) == 2 and argv[0] == "identify":
        print(json.dumps(identify(argv[1]), indent=1))
        return 0
    if len(argv) == 4 and argv[0] == "rip":
        return rip(*argv[1:])
    if len(argv) == 2 and argv[0] == "oscr-hello":
        # O firmware do FliperOS responde? (Setup > System > Cartridge reader)
        try:
            oscr = Oscr(argv[1])
        except (OSError, OscrError) as e:
            print("the OSCR did not answer as FliperOS firmware: %s" % (e.args[0] if e.args else e))
            return 1
        print("FLIPEROS 1 " + " ".join(oscr.systems))
        oscr.close()
        return 0
    if len(argv) == 2 and argv[0] == "oscr-scan":
        print(json.dumps(oscr_call(argv[1], "scan"), indent=1))
        return 0
    if len(argv) == 3 and argv[0] == "oscr-info":
        print(json.dumps(oscr_call(argv[1], "info", argv[2]), indent=1))
        return 0
    if len(argv) == 5 and argv[0] == "oscr-rip":
        return oscr_rip(*argv[1:])
    print("usage: femedia.py list | identify DEV | rip DEV FOLDER NAME | oscr-scan DEV | oscr-info DEV SYSTEM"
          " | oscr-rip DEV SYSTEM FOLDER NAME", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
