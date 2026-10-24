"""Grava o frontend do FliperOS em tempo real (com os videos dos jogos), a
30 quadros por segundo, em 320x240 sem perda (FFV1), seguindo um roteiro:
[(segundo, acao)], a acao e uma tecla do frontend ("down", "b1", "start"...),
("play", segundos) - o video do jogo escolhido em tela cheia, como se o jogo
tivesse aberto - ou ("set", atributo, valor).

    python3 fe_rec.py SAIDA.mkv ROTEIRO.py
"""
import importlib.util
import os
import subprocess
import sys
import time
from importlib.machinery import SourceFileLoader

os.environ["SDL_VIDEODRIVER"] = "dummy"
FPS = 30
OUT, SCRIPT = sys.argv[1], sys.argv[2]
scene = {}
exec(open(SCRIPT).read(), scene)
TIMELINE = sorted(scene["TIMELINE"], key=lambda x: x[0])
DURATION = scene["DURATION"]

sys.argv = ["fliperos-frontend"]
loader = SourceFileLoader("fe", "/g/fliperos-frontend")
spec = importlib.util.spec_from_loader("fe", loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


class Args:
    shot = None
    keys = ""


fe = m.Frontend(Args())
for k, v in scene.get("START", {}).items():
    setattr(fe, k, v)
if "MODE" in scene:
    fe.mode = scene["MODE"]
    fe.rebuild()
if "GAME" in scene:
    for i, row in enumerate(fe.rows):
        if row[0]["Name"] == scene["GAME"]:
            fe.cursor = i
            break
fe.overlay = scene.get("OVERLAY", fe.overlay)
pg = fe.pg
import fevideo  # noqa: E402

enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "320x240",
                        "-r", str(FPS), "-i", "-", "-c:v", "ffv1", OUT], stdin=subprocess.PIPE)
start = time.monotonic()
written = 0
playing = None        # (Video, ate quando)


def frame_bytes():
    if playing:
        data = playing[0].frame
        if data:
            return data
        # Ate o primeiro quadro do jogo chegar, a ultima tela do frontend.
    return pg.image.tostring(fe.back, "RGB")


while True:
    now = time.monotonic()
    t = now - start
    if t >= DURATION:
        break
    while TIMELINE and TIMELINE[0][0] <= t:
        _, action = TIMELINE.pop(0)
        if not isinstance(action, tuple) and fe.act(action) == "launch":
            # Jogar, no cartao do jogo: o video do jogo em tela cheia.
            action = ("play", scene.get("PLAY_SECONDS", 6.0))
        elif not isinstance(action, tuple):
            continue
        if action[0] == "play":
            g = fe.game()
            path = fe.lib.video(g) if g else None
            if path:
                fe.player.stop()
                fe.grid.stop()
                playing = (fevideo.Video(path, 320, 240, sound=False), now + action[1])
        elif action[0] == "set":
            setattr(fe, action[1], action[2])
    if playing and now >= playing[1]:
        playing[0].stop()
        playing = None
        fe.media.clear()
    if not playing:
        fe.tick(now)
        if fe.lib.generation != fe.generation:
            fe.generation = fe.lib.generation
            fe.cats = fe.lib.categories()
            fe.rebuild()
        while fe.dirty:
            fe.dirty.pop()
        fe.prefetch()
        fe.draw(now)
    data = frame_bytes()
    due = int(t * FPS) + 1
    while written < due:
        enc.stdin.write(data)
        written += 1
    nxt = start + written / FPS
    time.sleep(max(0.0, nxt - time.monotonic()))
enc.stdin.close()
enc.wait()
fe.player.stop()
fe.grid.stop()
print("frames", written)
os._exit(0)
