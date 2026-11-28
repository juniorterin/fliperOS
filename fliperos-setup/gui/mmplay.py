# O jogo da party online, aberto pelo Matchmaker: o mesmo caminho do play()
# do frontend padrao (fliperos-frontend), sem o modo comercial e sem importar
# o frontend (sao programas separados):
# - o atalho que fecha o jogo e o do menu do emulador sao os de Tab > Frontend
#   options (exit_key/exit_combo e menu_key/menu_combo do frontend.json; sem
#   nada gravado, coin+start e coin+1), lidos pelo fliperos-buttons hotkey;
# - o ambiente do jogo sem o SDL do KMS que a sessao deu ao Matchmaker;
# - o jogo fecha com o que esta abaixo dele (o X, o emulador), SIGKILL em 4 s.
#
# Nada aqui desenha: o Matchmaker fecha a tela, chama run() e abre de novo.

import os
import signal
import subprocess
import threading
import time

BUTTONS_TOOL = os.environ.get("FLIPEROS_BUTTONS_TOOL", "/opt/fliperos/bin/fliperos-buttons")
EXIT_HOLD = 1.0
DEFAULT_EXIT_COMBO, DEFAULT_MENU_COMBO = ["coin", "start"], ["coin", "b1"]


def shortcut(cfg, name, default, combo_ok):
    """(tecla, botoes) de um atalho do frontend.json, como o frontend le."""
    key = cfg.get(name + "_key")
    combo = cfg.get(name + "_combo")
    combo = [c for c in combo if combo_ok(c)] if isinstance(combo, list) else []
    if cfg.get("shortcuts") is None and not combo:
        combo = list(default)
    return (key if isinstance(key, list) and len(key) == 2 else None), combo


def game_program(argv):
    """O programa do comando do jogo (o de depois do fliperos-kms-run/x11-run)."""
    if len(argv) < 2 or os.path.basename(argv[0]) not in ("fliperos-x11-run", "fliperos-kms-run"):
        return None
    words = argv[1:]
    while words and words[0] in ("--mode", "--app", "--wine"):
        words = words[1:] if words[0] == "--wine" else words[2:]
    return os.path.basename(words[0]) if words else None


def game_env():
    """O ambiente do jogo: sem o SDL do KMS e o vsync pedido pelo Matchmaker."""
    env = dict(os.environ)
    env.pop("SDL_RENDER_VSYNC", None)
    sdl = env.pop("FLIPEROS_FRONTEND_SDL", "")
    if sdl:
        rest = [p for p in env.get("LD_LIBRARY_PATH", "").split(":") if p and p != sdl]
        if rest:
            env["LD_LIBRARY_PATH"] = ":".join(rest)
        else:
            env.pop("LD_LIBRARY_PATH", None)
    return env


def tree(pid):
    """O processo e os que estao abaixo dele."""
    import glob
    found = [pid]
    for path in glob.glob("/proc/%d/task/*/children" % pid):
        try:
            with open(path) as f:
                for child in f.read().split():
                    found += tree(int(child))
        except (OSError, ValueError):
            pass
    return found


def hotkey_args(cfg, argv, combo_ok):
    exit_key, exit_combo = shortcut(cfg, "exit", DEFAULT_EXIT_COMBO, combo_ok)
    menu_key, menu_combo = shortcut(cfg, "menu", DEFAULT_MENU_COMBO, combo_ok)
    args = []
    if exit_key:
        args += ["--key", str(exit_key[1])]
    if exit_combo:
        args += ["--combo", "+".join(exit_combo), "--hold", str(EXIT_HOLD)]
    if menu_key:
        args += ["--menu-key", str(menu_key[1])]
    if menu_combo:
        args += ["--menu-combo", "+".join(menu_combo), "--menu-hold", str(EXIT_HOLD)]
    if (menu_key or menu_combo) and game_program(argv):
        args += ["--program", game_program(argv)]
    return args


def stop(proc, state, sig=signal.SIGTERM):
    for pid in tree(proc.pid):
        try:
            os.kill(pid, sig)
        except OSError:
            pass
    state["kill"] = time.monotonic() + 4 if sig == signal.SIGTERM else None


def run(argv, cfg, combo_ok, should_stop=None, popen=subprocess.Popen, tool=None):
    """Abre o jogo e espera ele fechar; o atalho de sair o fecha. should_stop():
    o Matchmaker pede o fim (a party acabou do outro lado). True se abriu."""
    tool = tool or BUTTONS_TOOL
    state, watch = {}, None
    args = hotkey_args(cfg, argv, combo_ok)
    if args and os.access(tool, os.X_OK):
        try:
            watch = popen([tool, "hotkey"] + args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, text=True)
        except OSError:
            watch = None
    if watch is not None:
        ready = threading.Event()

        def read():
            for line in watch.stdout:
                if line.strip() == "exit":
                    state["exit"] = True
                elif line.strip() == "ready":
                    ready.set()
            ready.set()
        threading.Thread(target=read, daemon=True).start()
        ready.wait(2)
    try:
        proc = popen(argv, env=game_env())
    except OSError:
        if watch is not None:
            watch.terminate()
        return False
    try:
        while proc.poll() is None:
            if state.pop("exit", False) or (should_stop and should_stop() and "asked" not in state):
                state["asked"] = True
                stop(proc, state)
            elif state.get("kill") and time.monotonic() > state["kill"]:
                stop(proc, state, signal.SIGKILL)
            time.sleep(0.1)
    finally:
        if proc.poll() is None:
            stop(proc, state)
        if watch is not None:
            watch.terminate()
            try:
                watch.wait(2)
            except subprocess.TimeoutExpired:
                watch.kill()
    return True
