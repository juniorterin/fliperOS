"""Grava a troca de romlist do frontend em cada uma das animacoes de cada
modo (feview.TRANSITION_CHOICES), a 60 quadros por segundo, em tempo virtual:
o relogio do processo anda exatamente 1/60 s por quadro (as animacoes saem
lisas mesmo quando um quadro demora), no ritmo do relogio de verdade (os
videos dos jogos tocam na velocidade certa).

    python3 fe_transitions.py PASTA

Em PASTA: um MP4 por animacao (list-2-cascade.mp4...) e o all.mp4, todas em
seguida, com um cartao com o nome antes de cada uma. 960x720 (a tela de
320x240 ampliada 3x, pixel a pixel). Roda no rig.sh (a amostra do gabinete).
"""
import importlib.util
import os
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader

os.environ["SDL_VIDEODRIVER"] = "dummy"
FPS = 60
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)
REAL = time.monotonic
T0 = REAL()
VT = [T0]
time.monotonic = lambda: VT[0]

sys.argv = ["fliperos-frontend"]
loader = SourceFileLoader("fe", "/g/fliperos-frontend")
spec = importlib.util.spec_from_loader("fe", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class Args:
    shot = None
    keys = ""


fe = m.Frontend(Args())
pg = fe.pg
import feview  # noqa: E402
import theme as T  # noqa: E402
import tiny  # noqa: E402
import widgets as W  # noqa: E402

MODE_NAMES = {"list": "LIST", "full": "FULL SCREEN", "flow": "GRID"}
frames = [0]


def encoder(path):
    return subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                             "-s", "320x240", "-r", str(FPS), "-i", "-", "-vf", "scale=960:720:flags=neighbor",
                             "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p",
                             "-r", str(FPS), path], stdin=subprocess.PIPE)


def advance(outs, data):
    for enc in outs:
        enc.stdin.write(data)
    frames[0] += 1
    VT[0] = T0 + frames[0] / FPS
    # No ritmo do relogio de verdade (os videos dos jogos e o carregamento).
    late = T0 + frames[0] / FPS - REAL()
    if late > 0:
        time.sleep(late)


def run(seconds, outs):
    for _ in range(round(seconds * FPS)):
        now = VT[0]
        fe.tick(now)
        if fe.lib.generation != fe.generation:
            fe.generation = fe.lib.generation
            fe.cats = fe.lib.categories()
            fe.rebuild()
        while fe.dirty:
            fe.dirty.pop()
        fe.prefetch()
        fe.draw(now)
        advance(outs, pg.image.tostring(fe.back, "RGB"))


def card(title, sub, seconds, outs):
    """O cartao antes de cada animacao: o modo e o numero, e o nome dela."""
    back = pg.Surface((320, 240))
    back.fill(T.SPACE)
    big = W.big(title, 2, W.LABEL)
    back.blit(big, ((320 - big.get_width()) // 2, 96))
    tiny.centered(back, sub, T.CYAN, 160, 132)
    data = pg.image.tostring(back, "RGB")
    for _ in range(round(seconds * FPS)):
        advance(outs, data)


# A biblioteca carregando, sem gravar.
fe.overlay = None
run(4.0, [])
everything = encoder(os.path.join(OUT, "all.mp4"))
for mode, styles in feview.TRANSITION_CHOICES.items():
    for n, style in enumerate(styles, 1):
        name = feview.TRANSITION_NAMES[style]
        card(name, "%s - OPTION %d OF %d" % (MODE_NAMES[mode], n, len(styles)), 1.2, [everything])
        fe.transitions[mode] = style
        fe.overlay = None
        if fe.mode != mode:
            fe.mode = mode
            fe.rebuild()
        if mode == "flow":
            # Na grade, o cursor na coluna da direita: mais um toque troca a romlist.
            fe.cursor = min(len(fe.rows) - 1, m.COLS - 1)
        one = encoder(os.path.join(OUT, "%s-%d-%s.mp4" % (mode, n, style)))
        outs = [everything, one]
        run(1.0, outs)
        fe.act("right")
        # A tira parada PICK_WAIT segundos escolhe o sistema; depois a troca.
        run(m.PICK_WAIT + feview.INTRO + 1.2, outs)
        one.stdin.close()
        one.wait()
        print(mode, n, style, flush=True)
everything.stdin.close()
everything.wait()
fe.player.stop()
fe.grid.stop()
print("frames", frames[0])
os._exit(0)
