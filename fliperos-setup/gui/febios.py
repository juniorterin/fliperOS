"""O baixador de BIOS (config/fliperos-bios) visto pelo frontend.

Quem baixa e o Setup, como root (fliperos-setup --bios-check, lib/downloader.sh);
o frontend so le o que ele deixa em /var/lib/fliperos/bios, legivel por todos:

  running   "pid<TAB>porcentagem<TAB>texto" enquanto uma checagem roda (some no fim)
  last.kv   o resumo da ultima checagem (missing=, failed=, error=...)
  failed    existe quando a ultima checagem automatica nao deu certo

O quadro "BIOS DOWNLOAD" do menu do Tab aparece enquanto baixa ou quando algo nao
deu certo (falhou, ou nao esta em nenhuma fonte), e sai quando acaba e esta tudo
certo, como o do scrape automatico.
"""
import os
import subprocess
import time

STATE = os.environ.get("FLIPEROS_BIOS_STATE", "/var/lib/fliperos/bios")
SETUP = os.environ.get("FLIPEROS_SETUP_BIN", "/usr/local/bin/fliperos-setup")
# Uma checagem que nao deu sinal ha tanto tempo morreu sem limpar.
STALE = 30 * 60
EVERY = 3.0


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True      # o Setup roda como root: existe, so nao e nosso
    except OSError:
        return False
    return True


def start_check():
    """A checagem automatica, solta (como o menu do Setup faz ao abrir): so
    olha de novo se as pastas mudaram, entao abrir o frontend de novo e barato.
    Sem o Setup (o emulador do frontend, os testes), nao faz nada."""
    if not os.path.exists(SETUP):
        return False
    try:
        subprocess.Popen(["setsid", "-f", "nice", "-n", "19", "sudo", "-n", SETUP, "--bios-check"],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        return False
    return True


class BiosStatus:
    def __init__(self, state=None):
        self.state = state or STATE
        self.read_at = 0.0
        self.running = None        # (porcentagem, texto) com uma checagem rodando
        self.stats = {}            # o last.kv
        self.failed = False        # a ultima checagem automatica falhou

    def path(self, name):
        return os.path.join(self.state, name)

    def refresh(self, now=None):
        now = time.monotonic() if now is None else now
        if now - self.read_at >= EVERY:
            self.read_at = now
            self.read()

    def read(self):
        self.running = self.read_running()
        self.stats = {}
        try:
            with open(self.path("last.kv"), encoding="utf-8", errors="replace") as f:
                for line in f:
                    key, sep, value = line.rstrip("\n").partition("=")
                    if sep:
                        self.stats[key] = value
        except OSError:
            pass
        self.failed = os.path.exists(self.path("failed"))

    def read_running(self):
        path = self.path("running")
        try:
            if time.time() - os.stat(path).st_mtime > STALE:
                return None
            with open(path, encoding="utf-8", errors="replace") as f:
                pid, pct, text = f.readline().rstrip("\n").split("\t", 2)
            if not alive(int(pid)):
                return None
            return max(0, min(100, int(pct))), text
        except (OSError, ValueError):
            return None

    def count(self, key):
        try:
            return int(self.stats.get(key, 0))
        except ValueError:
            return 0

    def box(self):
        """O que o quadro mostra: (texto da direita, cor, porcentagem ou None,
        linha de baixo), ou None quando nao ha o que mostrar."""
        if self.running:
            pct, text = self.running
            return "%d%%" % pct, "cyan", pct, text
        failed = self.count("failed")
        if failed or self.stats.get("error") or self.failed:
            n = "%d FAILED" % failed if failed else "COULD NOT CHECK"
            return n, "pink", None, "TRYING AGAIN WHEN THE MENU OPENS"
        missing = self.count("missing")
        if missing:
            return "%d MISSING" % missing, "yellow", None, "NOT IN ANY BIOS SOURCE"
        return None
