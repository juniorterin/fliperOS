"""O disco novo que o frontend pergunta se vira o armazenamento do FliperOS.

Quem anota o disco e o fliperos-automount, como root, ao montar um disco que serve
(fliperos-setup --storage auto, lib/storage.sh), em /var/lib/fliperos/storage/offer,
legivel por todos: uma linha "MONTAGEM|ROTULO|FS|TOTAL|ID" por disco ainda sem
resposta. O frontend so le a fila (um arquivo, a cada poucos segundos), pergunta
uma vez e manda a resposta ao Setup (--storage answer MONTAGEM yes|no), que liga
o disco (yes) e registra o UUID dele: o mesmo disco nao pergunta de novo.

Um disco que ja tem um Batocera filesystem (lib/batocera.sh) entra na fila com
mais dois campos, "MONTAGEM|ROTULO|FS|TOTAL|ID|batocera|CONSOLES", e a pergunta
e a do Batocera filesystem: o "yes" usa as roms (um sistema por console, com o
core padrao) e as pastas irmas dele (--storage answer MONTAGEM yes batocera).
"""
import os
import re
import subprocess
import time

STATE = os.environ.get("FLIPEROS_STORAGE_STATE", "/var/lib/fliperos/storage")
SETUP = os.environ.get("FLIPEROS_SETUP_BIN", "/usr/local/bin/fliperos-setup")
EVERY = 3.0

# Onde mudar depois, no texto de quem disse que nao (duas linhas de tela).
WHERE = ("SETUP > GAMES > FOLDERS", "> EXTERNAL STORAGE. ALSO IN THE WEB PANEL")
# O caminho inteiro, numa linha so (a fonte pequena tem 4 px por letra).
WHERE_FULL = "SETUP > GAMES > FOLDERS > EXTERNAL STORAGE"


def human(size):
    """O tamanho de um disco como ele vem na caixa: 932 GB, 1.0 TB."""
    try:
        size = int(size)
    except (TypeError, ValueError):
        return "?"
    if size >= 10 ** 12:
        return "%.1f TB" % (size / 10 ** 12)
    return "%d GB" % round(size / 10 ** 9)


class Offers:
    def __init__(self, state=None):
        self.state = state or STATE
        self.read_at = None
        self.items = []
        self.answered = set()      # os discos que ja responderam aqui (o Setup ainda pode estar registrando)

    def path(self):
        return os.path.join(self.state, "offer")

    def refresh(self, now=None):
        now = time.monotonic() if now is None else now
        if self.read_at is None or now - self.read_at >= EVERY:
            self.read_at = now
            self.read()

    def read(self):
        """Os discos esperando a resposta que ainda estao ligados (um disco que
        saiu sem resposta volta a perguntar quando for ligado de novo)."""
        items = []
        try:
            with open(self.path(), encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
        except OSError:
            lines = []
        for line in lines:
            parts = line.split("|")
            if len(parts) < 5 or not os.path.ismount(parts[0]):
                continue
            mount, label, fs, total, ident = parts[:5]
            if ident in self.answered:
                continue
            item = {"mount": mount, "label": label, "fs": fs, "total": total, "id": ident}
            if len(parts) > 5 and parts[5] == "batocera":
                item["kind"] = "batocera"
                item["consoles"] = parts[6] if len(parts) > 6 and parts[6].isdigit() else "0"
            items.append(item)
        self.items = items

    def first(self):
        return self.items[0] if self.items else None

    def done(self, mount):
        """Respondido: o disco sai da lista ja, antes de o Setup o tirar da fila
        (que leva um instante e nao pode perguntar de novo)."""
        self.answered.update(i["id"] for i in self.items if i["mount"] == mount)
        self.items = [i for i in self.items if i["mount"] != mount]


def kind_of(offer):
    """O tipo da pergunta: "fliperos" (a estrutura do FliperOS no disco) ou
    "batocera" (um Batocera filesystem)."""
    return offer.get("kind", "fliperos")


def answer(mount, yes, kind="fliperos", timeout=300):
    """A resposta ao Setup, como root (a regra do sudoers do usuario). Devolve
    (deu certo, linhas de aviso): o motivo, se nao deu."""
    cmd = [SETUP, "--storage", "answer", mount, "yes" if yes else "no"]
    if kind == "batocera":
        cmd.append("batocera")
    if os.geteuid() != 0 and os.path.exists("/usr/bin/sudo"):
        cmd = ["sudo", "-n"] + cmd
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return False, ["COULD NOT RUN THE SETUP"]
    # O que o Setup conta de bom (kept=, linked=, systems=...) nao e aviso.
    lines = [l.strip() for l in r.stdout.splitlines() if l.strip() and not re.match(r"^[a-z]+=", l.strip())]
    return r.returncode == 0, lines
