# O preview do filtro de flicker do 480i (Setup > Video Setup > 480i hacks):
# uma tela feita para tremer num modo entrelacado (linhas de um pixel, letra
# pequena, xadrez, bordas finas, uma linha que anda), aberta pelo
# fliperos-x11-run em 640x480 com a camada do config/fliperos-deflicker.c.
# As setas trocam o nivel na hora: ele vai para o arquivo de
# FLIPEROS_DEFLICKER_FILE, que a camada rele a cada 30 quadros.
#
#   flicker-preview.py --level medium --out ARQUIVO [--title NOME]
#
# Enter grava o nivel em ARQUIVO e sai com 0; Esc sai com 1 sem gravar.

import argparse
import os

# O quadro da janela pelo OpenGL (o SDL desenha a superficie numa textura):
# sem isso o SDL manda a imagem ao X sem OpenGL, e a camada nao a ve.
os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "opengl")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402

LEVELS = ["off", "light", "medium", "strong"]
NAMES = {"off": "OFF", "light": "LIGHT", "medium": "MEDIUM", "strong": "STRONG"}
ABOUT = {
    "off": "No filter: sharpest, thin lines flicker.",
    "light": "A little of each neighbour: sharp, less flicker.",
    "medium": "Two lines averaged, like RePlayOS.",
    "strong": "A third of each of three lines: no flicker.",
}
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

TEXT = [
    "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG 0123456789",
    "INSERT COIN   PLAYER 1   HI-SCORE 0012345   CREDIT 03",
    "Thin lines live in one field only and blink at 30 Hz.",
    "The filter puts a little of each line in both fields.",
]


def write_level(path, level):
    if not path:
        return
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(level + "\n")
    os.replace(tmp, path)


class Preview:
    def __init__(self, level, title):
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        self.w, self.h = self.screen.get_size()
        self.small = T.font()
        self.big = pygame.font.Font(T.FONT_FILE, 16)
        self.level = level if level in LEVELS else "medium"
        self.title = title
        self.frame = 0
        self.board = None

    def label(self, font, s, color, x, y):
        self.screen.blit(font.render(s, False, color), (x, y))

    def draw(self):
        s, w, h = self.screen, self.w, self.h
        s.fill(BLACK)
        self.label(self.big, "FLICKER FILTER", T.PINK, 24, 16)
        if self.title:
            self.label(self.small, self.title.upper(), T.CYAN, 24, 38)
        top, half = 56, (w - 72) // 2
        # Listras de uma linha e o xadrez de um pixel: o pior caso.
        for y in range(top, top + 80, 2):
            pygame.draw.line(s, WHITE, (24, y), (24 + half - 1, y))
        if self.board is None:
            self.board = pygame.Surface((half, 80))
            self.board.fill(BLACK)
            for y in range(0, 80):
                for x in range(y % 2, half, 2):
                    self.board.set_at((x, y), WHITE)
        s.blit(self.board, (48 + half, top))
        # Letra pequena (traços de um pixel) em cores do tema.
        y = top + 96
        for i, line in enumerate(TEXT):
            self.label(self.small, line[: (w - 48) // 8], (WHITE, T.YELLOW, T.CYAN, T.GREEN)[i], 24, y)
            y += 12
        # Bordas finas e uma grade de um pixel.
        y += 8
        for i in range(6):
            pygame.draw.rect(s, (WHITE, T.PINK, T.PURPLE, T.CYAN, T.GREEN, T.ORANGE)[i],
                             (24 + i * 8, y + i * 6, half - i * 16, 96 - i * 12), 1)
        gx = 48 + half
        for gy in range(y, y + 96, 8):
            pygame.draw.line(s, WHITE, (gx, gy), (gx + half - 1, gy))
        for x in range(gx, gx + half, 8):
            pygame.draw.line(s, WHITE, (x, y), (x, y + 95))
        # Uma linha que desce e um letreiro que corre.
        sweep = y + (self.frame % 96)
        pygame.draw.line(s, T.YELLOW, (gx, sweep), (gx + half - 1, sweep))
        y += 108
        marquee = "  GAME OVER  " * 8
        offset = self.frame % (13 * 8)
        self.label(self.small, marquee, T.FG, 24 - offset, y)
        pygame.draw.rect(s, BLACK, (0, y, 24, 10))
        pygame.draw.rect(s, BLACK, (w - 24, y, 24, 10))
        # Os niveis e as teclas.
        y = h - 44
        x = 24
        for lv in LEVELS:
            name = NAMES[lv]
            width = len(name) * 8 + 12
            if lv == self.level:
                pygame.draw.rect(s, T.PINK, (x, y - 4, width, 16))
                self.label(self.small, name, BLACK, x + 6, y)
            else:
                pygame.draw.rect(s, T.LINE, (x, y - 4, width, 16), 1)
                self.label(self.small, name, T.COMMENT, x + 6, y)
            x += width + 8
        self.label(self.small, ABOUT[self.level], T.FG, 24, y - 24)
        self.label(self.small, "< > LEVEL   ENTER KEEP   ESC CANCEL", T.CYAN, 24, h - 18)
        pygame.display.flip()

    def run(self, path):
        clock = pygame.time.Clock()
        write_level(path, self.level)
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type != pygame.KEYDOWN:
                    continue
                i = LEVELS.index(self.level)
                if event.key in (pygame.K_LEFT, pygame.K_UP):
                    self.level = LEVELS[max(0, i - 1)]
                    write_level(path, self.level)
                elif event.key in (pygame.K_RIGHT, pygame.K_DOWN, pygame.K_SPACE):
                    self.level = LEVELS[min(len(LEVELS) - 1, i + 1)]
                    write_level(path, self.level)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return self.level
                elif event.key == pygame.K_ESCAPE:
                    return None
            self.draw()
            self.frame += 1
            clock.tick(60)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="medium")
    parser.add_argument("--out", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()
    preview = Preview(args.level, args.title)
    try:
        level = preview.run(os.environ.get("FLIPEROS_DEFLICKER_FILE", ""))
    finally:
        pygame.display.quit()
    if level is None:
        raise SystemExit(1)
    with open(args.out, "w") as f:
        f.write(level + "\n")


if __name__ == "__main__":
    main()
