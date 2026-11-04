# O ajuste das scanlines na tela (Setup > Video Setup > Scanlines, monitor de
# 31 kHz): uma imagem de jogo de 320x240 dobrada para o modo do monitor e,
# embaixo, os ajustes, que as setas mudam na hora. Aberto pelo fliperos-x11-run
# com a camada config/fliperos-deflicker.c, que rele o arquivo de
# FLIPEROS_SCANLINES_FILE (o mesmo --conf) a cada 30 quadros.
#
#   scanline-preview.py --table TABELA --conf ARQUIVO --out ARQUIVO
#
# TABELA: o scanline_table do lib/video.sh (chave|rotulo|min|max|padrao|passo|
# ajuda). ARQUIVO: linhas scanlines_CHAVE=valor. Espaco desliga e liga as
# scanlines para comparar. Enter grava os valores em --out e sai com 0; Esc
# sai com 1.

import argparse
import os

# O quadro da janela pelo OpenGL: a camada so ve o que passa por ele.
os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "opengl")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
W, H = 320, 240
BARS = [(255, 255, 255), (255, 255, 0), (0, 255, 255), (0, 255, 0), (255, 0, 255), (255, 0, 0), (0, 0, 255),
        (0, 0, 0)]
# Um robozinho de 16x16 em pixels grandes, como os de um jogo de 240 linhas.
SPRITE = """
.......Y........
.......K........
....CCCCCCCC....
...CFFFFFFFFC...
...CFKKFFKKFC...
...CFKKFFKKFC...
...CFFFFFFFFC...
...CFFKKKKFFC...
....CCCCCCCC....
..O..PPPPPP..O..
..OPPPCYYCPPPO..
.....PCYYCP.....
.....PPPPPP.....
.....PP..PP.....
....CCC..CCC....
...CCCC..CCCC...
"""
SPRITE_COLORS = {"Y": T.YELLOW, "K": T.PINK, "C": T.CYAN, "F": (220, 230, 255), "O": T.ORANGE, "P": T.PURPLE}


def read_values(path):
    values = {}
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("scanlines_") and "=" in line:
                    key, value = line.strip()[10:].split("=", 1)
                    values[key] = value
    except OSError:
        pass
    return values


class Preview:
    def __init__(self, table, values, conf):
        self.params = table
        self.values = {k: int(values[k]) if values.get(k, "").isdigit() else d for k, _, _, _, d, _, _ in table}
        self.conf = conf
        self.on = True
        self.pick = 0
        self.frame = 0
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.canvas = pygame.Surface((W, H))
        self.font = T.font()
        self.scene = self.make_scene()

    def write(self):
        if not self.conf:
            return
        tmp = self.conf + ".tmp"
        with open(tmp, "w") as f:
            if not self.on:
                f.write("scanlines=off\n")
            for key, *_ in self.params:
                f.write("scanlines_%s=%d\n" % (key, self.values[key]))
        os.replace(tmp, self.conf)

    def make_scene(self):
        # Ceu em faixas, montanhas, o chao em xadrez: o que mostra bem as
        # scanlines (cores chapadas e degraus).
        s = pygame.Surface((W, 112))
        for y in range(0, 72, 8):
            s.fill((20 + y, 40 + y, 120 + y), (0, y, W, 8))
        for x0, peak, color in ((-20, 30, (60, 50, 110)), (90, 18, (80, 60, 130)), (200, 26, (60, 50, 110))):
            pygame.draw.polygon(s, color, [(x0, 80), (x0 + 70, peak), (x0 + 140, 80)])
        for y in range(80, 112, 8):
            for x in range(0, W, 16):
                s.fill((40, 160, 60) if (x // 16 + y // 8) % 2 else (30, 120, 50), (x, y, 16, 8))
        for row, line in enumerate(SPRITE.split()):
            for col, c in enumerate(line):
                if c in SPRITE_COLORS:
                    s.fill(SPRITE_COLORS[c], (48 + col * 2, 48 + row * 2, 2, 2))
        return s

    def text(self, s, color, x, y):
        self.canvas.blit(self.font.render(s, False, color), (x, y))

    def pretty(self, key, value):
        if key == "height":
            return "AUTO" if value == 0 else "%d LINES" % value
        return "%d%%" % value

    def draw(self):
        c = self.canvas
        c.fill(BLACK)
        self.text("SCANLINES", T.PINK, 8, 4)
        self.text("ON" if self.on else "OFF", T.GREEN if self.on else T.RED, 96, 4)
        c.blit(self.scene, (0, 16))
        # Uma moeda que gira e um letreiro que corre, como num jogo.
        x = 200 + (self.frame // 2) % 80
        pygame.draw.ellipse(c, T.YELLOW, (x, 60, 4 + abs(8 - (self.frame // 4) % 16), 12))
        width = W // len(BARS)
        for i, color in enumerate(BARS):
            c.fill(color, (i * width, 128, width, 12))
        for i in range(16):
            c.fill((i * 17,) * 3, (i * W // 16, 140, W // 16 + 1, 8))
        self.text("INSERT COIN", WHITE if (self.frame // 30) % 2 else T.YELLOW, 116, 152)
        y = 166
        for i, (key, label, _, _, _, _, _) in enumerate(self.params):
            mark = i == self.pick
            if mark:
                c.fill(T.LINE, (4, y - 2, W - 8, 11))
            self.text(label.upper()[:20], T.CYAN if mark else T.COMMENT, 8, y)
            self.text(self.pretty(key, self.values[key]), T.FG if mark else T.COMMENT, 200, y)
            y += 11
        # A ajuda em ate duas linhas de 39 letras.
        lines, line = [], ""
        for word in self.params[self.pick][6].split():
            if len(line) + len(word) + 1 > 39:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        for i, s in enumerate((lines + [line])[:2]):
            self.text(s, T.FG, 4, y + 1 + i * 9)
        self.text("< > CHANGE SPACE ON/OFF ENTER ESC", T.CYAN, 4, H - 10)
        pygame.transform.scale(c, self.screen.get_size(), self.screen)
        pygame.display.flip()

    def step(self, direction):
        key, _, lo, hi, _, step, _ = self.params[self.pick]
        value = self.values[key] + direction * step
        # A altura pula o 1 (uma linha da tela por linha do jogo, sem espaco).
        if key == "height" and value == 1:
            value += direction
        self.values[key] = max(lo, min(hi, value))
        self.write()

    def run(self):
        clock = pygame.time.Clock()
        self.write()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_UP:
                    self.pick = (self.pick - 1) % len(self.params)
                elif event.key == pygame.K_DOWN:
                    self.pick = (self.pick + 1) % len(self.params)
                elif event.key == pygame.K_LEFT:
                    self.step(-1)
                elif event.key == pygame.K_RIGHT:
                    self.step(1)
                elif event.key == pygame.K_SPACE:
                    self.on = not self.on
                    self.write()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True
                elif event.key == pygame.K_ESCAPE:
                    return False
            self.draw()
            self.frame += 1
            clock.tick(60)


def read_table(path):
    table = []
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("|")
            if len(parts) == 7:
                key, label, lo, hi, default, step, help_text = parts
                table.append((key, label, int(lo), int(hi), int(default), int(step), help_text))
    return table


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--conf", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    preview = Preview(read_table(args.table), read_values(args.conf), args.conf)
    try:
        keep = preview.run()
    finally:
        pygame.display.quit()
    if not keep:
        raise SystemExit(1)
    with open(args.out, "w") as f:
        for key, *_ in preview.params:
            f.write("scanlines_%s=%d\n" % (key, preview.values[key]))


if __name__ == "__main__":
    main()
