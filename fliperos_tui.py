"""Wrappers de whiptail usados pelo setup e pelo instalador do FliperOS.

Modulo compartilhado de proposito: as primitivas de interface duplicadas em
dois scripts divergiriam com o tempo.

Mecanica do whiptail que os wrappers escondem: a selecao sai no *stderr*, nao
no stdout, e o codigo de saida distingue OK (0), Cancelar (1) e ESC (255).
"""
import os
import shutil
import subprocess
from pathlib import Path

BACKTITLE = "FliperOS"

# Paleta do newt. O formato e "elemento=frente,fundo" por linha, e as cores
# sao as 16 do console — NAO existe RGB aqui, entao "azul ceu" e brightcyan
# ou brightblue, nao um tom arbitrario. Nomes validos:
#   black red green brown blue magenta cyan lightgray
#   gray brightred brightgreen yellow brightblue brightmagenta brightcyan white
# ("brown" e o amarelo escuro, "lightgray" o branco normal e "white" o
# branco brilhante.)
PALETTE_FILE = Path("/etc/fliperos/newt-palette")
DEFAULT_PALETTE = """
root=white,brightblue
border=black,lightgray
window=black,lightgray
shadow=black,gray
title=blue,lightgray
button=lightgray,blue
actbutton=white,brightblue
checkbox=black,lightgray
actcheckbox=white,blue
entry=black,lightgray
label=blue,lightgray
listbox=black,lightgray
actlistbox=white,blue
sellistbox=white,brightblue
actsellistbox=white,brightblue
textbox=black,lightgray
acttextbox=white,blue
helpline=white,brightblue
roottext=white,brightblue
emptyscale=,gray
fullscale=,brightblue
disentry=gray,lightgray
compactbutton=black,lightgray
"""


def palette():
    """A paleta pode ser trocada na maquina sem rebuildar a imagem."""
    if PALETTE_FILE.is_file():
        try:
            return PALETTE_FILE.read_text()
        except OSError:
            pass
    return DEFAULT_PALETTE

# O console do CRT em 640x240 com fonte 8x16 tem 80x15 caracteres. O
# auto-size do whiptail (passar 0 0) estoura essa tela, entao as dimensoes
# sao calculadas e limitadas.
MAX_WIDTH = 72
MAX_HEIGHT = 20


# ── Voz ──────────────────────────────────────────────────────
# Narracao falada dos passos criticos. A razao e concreta: ao trazer um CRT a
# vida a tela pode nao mostrar NADA, e uma pergunta que so existe na tela fica
# sem resposta. O GroovyArcade mantem o livecd-talk do archiso habilitado (o
# gasetup em si nao narra nada); aqui a voz e usada onde ela resolve o
# problema, em vez de anunciar o boot.
VOICE_FLAG = Path("/etc/fliperos/voice")


def voice_enabled():
    """Ligada por padrao na midia de instalacao, que e quando a tela pode
    estar ilegivel; no sistema instalado ela incomoda mais do que ajuda."""
    if VOICE_FLAG.is_file():
        return VOICE_FLAG.read_text().strip().lower() not in ("0", "off", "nao", "no")
    return not Path("/etc/fliperos/installed").is_file()


def set_voice(on):
    VOICE_FLAG.parent.mkdir(parents=True, exist_ok=True)
    VOICE_FLAG.write_text("on\n" if on else "off\n")


def speak(text, wait=False):
    """Fala em pt-br, sempre best-effort: sem placa, com mixer mudo ou com o
    dispositivo ocupado, isso falha em silencio e nao pode travar a interface."""
    if not voice_enabled() or not shutil.which("espeak-ng"):
        return
    args = ["espeak-ng", "-v", "pt-br", "-s", "150", text]
    try:
        if wait:
            subprocess.run(args, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=30)
        else:
            subprocess.Popen(args, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        pass


def available():
    return shutil.which("whiptail") is not None


def require():
    if not available():
        raise SystemExit("whiptail nao encontrado; instale o pacote whiptail.")


def _box(extra_lines=0):
    size = shutil.get_terminal_size(fallback=(80, 15))
    width = max(40, min(size.columns - 4, MAX_WIDTH))
    height = max(8, min(size.lines - 1, MAX_HEIGHT))
    # Sobra pra moldura, texto e botoes; o whiptail rola a lista se faltar.
    list_height = max(3, min(extra_lines, height - 8))
    return height, width, list_height


def _call(args, capture=True):
    """Roda o whiptail. A resposta vem no stderr; devolve (ok, texto)."""
    base = ["whiptail", "--backtitle", BACKTITLE]
    env = dict(os.environ, NEWT_COLORS=palette())
    result = subprocess.run(base + args, stderr=subprocess.PIPE, text=True, env=env)
    return result.returncode == 0, (result.stderr or "").strip()


def message(text, title="FliperOS"):
    height, width, _ = _box()
    _call(["--title", title, "--msgbox", text, str(height), str(width)])


def yesno(text, title="Confirmar", default_no=True):
    height, width, _ = _box()
    args = ["--title", title]
    if default_no:
        args.append("--defaultno")
    args += ["--yesno", text, str(height), str(width)]
    ok, _ = _call(args)
    return ok


def inputbox(text, default="", title="FliperOS"):
    """None quando o usuario cancela — diferente de string vazia, que e uma
    resposta valida."""
    height, width, _ = _box()
    ok, value = _call(["--title", title, "--inputbox", text,
                       str(height), str(width), default])
    return value if ok else None


def password(text, title="FliperOS"):
    height, width, _ = _box()
    ok, value = _call(["--title", title, "--passwordbox", text,
                       str(height), str(width)])
    return value if ok else None


def menu(text, options, title="FliperOS", cancel="Voltar", default=None):
    """options: lista de (tag, rotulo). Devolve a tag ou None se cancelar."""
    height, width, list_height = _box(len(options))
    args = ["--title", title, "--cancel-button", cancel]
    if default is not None:
        args += ["--default-item", str(default)]
    args += ["--menu", text, str(height), str(width), str(list_height)]
    for tag, label in options:
        args += [str(tag), label]
    ok, value = _call(args)
    return value if ok else None


def checklist(text, options, title="FliperOS"):
    """options: lista de (tag, rotulo, marcado). Devolve lista de tags."""
    height, width, list_height = _box(len(options))
    args = ["--title", title, "--separate-output",
            "--checklist", text, str(height), str(width), str(list_height)]
    for tag, label, checked in options:
        args += [str(tag), label, "on" if checked else "off"]
    ok, value = _call(args)
    return value.split() if ok and value else []


def run_visible(argv, text="", pause_after=True):
    """Roda um comando com a saida visivel, fora do dialogo.

    Serve pra apt, compilacao e diagnostico: whiptail nao mostra saida
    contínua, e esconder o progresso de algo demorado parece travamento."""
    subprocess.run(["clear"], check=False)
    if text:
        print("== " + text + " ==\n")
    code = subprocess.run(argv).returncode
    if pause_after:
        try:
            input("\nENTER para voltar ao menu. ")
        except (KeyboardInterrupt, EOFError):
            pass
    return code
