"""Grava telas do Setup grafico (fliperos-setup/gui) seguindo um roteiro, em
tempo virtual: 30 quadros por segundo, 320x240, sem perda (FFV1). O relogio
de todo o processo (time.monotonic) e o do video, entao as animacoes (o
fundo, o carrossel, as contagens) andam como no gabinete.

    python3 gui_rec.py SAIDA.mkv CENA.py

A cena define script(R); R tem push, replace, pop, key, keys, wait, type,
bg, boot, black e ctx.
"""
import os
import subprocess
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
FPS = 30
VT = [1000.0]
time.monotonic = lambda: VT[0]
sys.path.insert(0, "/g")
import pygame  # noqa: E402

pygame.init()
import theme  # noqa: E402
import background  # noqa: E402
import widgets as W  # noqa: E402
import demo  # noqa: E402

OUT, SCENE = sys.argv[1], sys.argv[2]
SPLASH = "/repo/config/splashscreen/fliperos"


class Recorder:
    def __init__(self):
        theme.set_orientation("horizontal")
        background.set_size(theme.WIDTH, theme.HEIGHT)
        self.back = pygame.Surface((theme.WIDTH, theme.HEIGHT))
        self.ui = pygame.Surface((theme.WIDTH, theme.HEIGHT), pygame.SRCALPHA)
        self.bgobj = background.pick("stars")
        self.stack = []
        self.ctx = dict(demo.CONTEXT)
        self.mode = "screen"          # screen, boot, black
        self.t0 = VT[0]
        self.frames = 0
        self.enc = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                     "-s", "%dx%d" % (theme.WIDTH, theme.HEIGHT), "-r", str(FPS), "-i", "-",
                                     "-c:v", "ffv1", OUT], stdin=subprocess.PIPE)
        self.logo = pygame.image.load(os.path.join(SPLASH, "logo.png"))
        self.throbber = [pygame.image.load(os.path.join(SPLASH, "throbber-%02d.png" % i if i < 10 else
                                                        "throbber-0%d.png" % i)) for i in range(33)]

    # ── O roteiro ──
    def push(self, screen, wait=0.0):
        self.stack.append(screen)
        self.mode = "screen"
        self.wait(wait)

    def replace(self, screen, wait=0.0):
        self.stack[-1] = screen
        self.mode = "screen"
        self.wait(wait)

    def pop(self, wait=0.0):
        self.stack.pop()
        self.wait(wait)

    def key(self, k, wait=0.35):
        if self.stack:
            self.stack[-1].key(k)
        self.wait(wait)

    def keys(self, ks, each=0.35):
        for k in ks.split():
            self.key(k, each)

    def type(self, attr, text, each=0.09, wait=0.4):
        """Digita text no campo attr da tela de cima, uma letra por vez."""
        screen = self.stack[-1]
        for i in range(1, len(text) + 1):
            setattr(screen, attr, text[:i])
            self.wait(each)
        self.wait(wait)

    def bg(self, name):
        self.bgobj = background.pick(name)

    def boot(self, seconds):
        self.mode = "boot"
        self.wait(seconds)

    def black(self, seconds):
        self.mode = "black"
        self.wait(seconds)

    def wait(self, seconds):
        for _ in range(int(round(seconds * FPS))):
            self.frame()

    # ── Um quadro ──
    def frame(self):
        now = VT[0] - self.t0
        if self.mode == "black":
            self.back.fill((0, 0, 0))
        elif self.mode == "boot":
            self.back.fill((0, 0, 0))
            # O tema do Plymouth (fliperos.script): o logo e a tela inteira
            # de 640x480 e a barra 117 pixels abaixo do centro; aqui, a tela
            # 4:3 de 320x240, tudo pela metade.
            self.back.blit(pygame.transform.smoothscale(self.logo, (theme.WIDTH, theme.HEIGHT)), (0, 0))
            th = self.throbber[int(now * 20) % len(self.throbber)]
            th = pygame.transform.smoothscale(th, (th.get_width() // 2, max(1, th.get_height() // 2)))
            self.back.blit(th, (theme.WIDTH // 2 - th.get_width() // 2 - 1,
                                theme.HEIGHT // 2 - th.get_height() // 2 + 58))
        else:
            self.ui.fill((0, 0, 0, 0))
            self.ctx["now"] = now
            if self.stack:
                self.stack[-1].draw(self.ui, self.ctx)
                tick = getattr(self.stack[-1], "tick", None)
                if tick:
                    tick()
            self.bgobj.draw(self.back, now)
            self.back.blit(self.ui, (0, 0))
        self.enc.stdin.write(pygame.image.tostring(self.back, "RGB"))
        self.frames += 1
        VT[0] += 1.0 / FPS

    def close(self):
        self.enc.stdin.close()
        self.enc.wait()
        print("frames", self.frames, "seconds %.1f" % (self.frames / FPS))


R = Recorder()
scene = {"W": W, "demo": demo, "R": R}
exec(open(SCENE).read(), scene)
scene["script"](R)
R.close()
