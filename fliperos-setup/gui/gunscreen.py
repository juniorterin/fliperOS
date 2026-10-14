# A tela da calibracao do GunCon 2 na interface grafica: o
# config/fliperos-calibrate a usa no lugar do desenho no terminal quando o
# Setup esta na interface grafica (FLIPEROS_CALIBRATE_GUI=1). Tem a mesma
# conversa da classe Screen de la (white, draw_target, at, key, restore), e
# rows/cols sao os pixels da tela logica: os alvos ficam onde o calibrador
# os pede, em fracoes da tela.
#
# A tela e branca: a pistola so enxerga onde ha luz. Nao gira com o monitor
# em pe, porque o calibrador mede a posicao no tubo como ele e.

import os

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402
import widgets as W  # noqa: E402

WHITE = (255, 255, 255)


class GunScreen:
    rows, cols = T.HEIGHT, T.WIDTH

    def __init__(self):
        pygame.display.init()
        pygame.font.init()
        size, flags = T.MODE, 0
        if os.environ.get("SDL_VIDEODRIVER", "kmsdrm") == "kmsdrm":
            flags = pygame.FULLSCREEN
            modes = pygame.display.list_modes()
            if not isinstance(modes, list) or size not in modes:
                info = pygame.display.Info()
                size = (info.current_w, info.current_h)
        self.window = pygame.display.set_mode(size, flags)
        pygame.mouse.set_visible(False)
        self.surf = pygame.Surface((T.WIDTH, T.HEIGHT))
        self.lines = []
        self.target = None
        self.status = ""
        self.shots = 0
        self.result = None

    # A conversa da Screen do calibrador ---------------------------------

    def white(self, *lines):
        self.lines = list(lines)
        self.target = None
        self.status = ""
        self.shots = 0
        self.result = None
        self.draw()

    def draw_target(self, row, col):
        self.target = (col, row)
        self.draw()

    def at(self, row, col, text):
        # A ultima linha e a do tiro ("Shot 2 of 3: x=..."): o cartucho gasto.
        if row == self.rows:
            self.status = text.strip()
            if self.status.startswith("Shot "):
                self.shots = int(self.status.split()[1])
            self.draw()

    def show_result(self, hit, want):
        """O fim: o tiro de conferencia numa miniatura da tela."""
        self.result = (hit, want)
        self.draw()

    def write(self, text):
        pass

    def key(self):
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "\033"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return "\n"
        return ""

    def restore(self):
        pygame.display.quit()

    # O desenho ----------------------------------------------------------

    def draw(self):
        surf = self.surf
        surf.fill(WHITE)
        if self.result:
            hit, want = self.result
            x, y, w, h = 104, 30, 112, 84
            pygame.draw.rect(surf, T.SPACE, (x, y, w, h), 2)
            cx, cy = x + round(w * want[0] / 100), y + round(h * want[1] / 100)
            for r, color in ((14, T.RED), (10, WHITE), (6, T.RED), (2, WHITE)):
                pygame.draw.circle(surf, color, (cx, cy), r)
            hx, hy = x + round(w * hit[0] / 100), y + round(h * hit[1] / 100)
            pygame.draw.circle(surf, T.SPACE, (hx, hy), 4)
            pygame.draw.circle(surf, T.GREEN, (hx, hy), 3)
            off = max(abs(hit[0] - want[0]), abs(hit[1] - want[1]))
            label = "ON TARGET!" if off <= 3 else "A BIT OFF"
            name = W.big(label, 2, [T.SPACE, T.SPACE, (0x40, 0x20, 0x70)])
            surf.blit(name, ((T.WIDTH - name.get_width()) // 2, 124))
            y = 148
        else:
            if self.target:
                W.bullseye(surf, *self.target)
            # O texto longe do alvo: em cima quando ele esta no meio.
            mid = self.target and abs(self.target[1] - T.HEIGHT // 2) < 40
            y = 30 if mid else 84
            W.centered(surf, "GUNCON 2 CALIBRATION", T.COMMENT, y)
            y += 14
        for line in self.lines:
            for part in W.wrap(line, T.SAFE_W):
                W.centered(surf, part, T.SPACE, y)
                y += 11
        if self.target and not self.result:
            need = 3 if "3 times" in " ".join(self.lines) else 1
            x = T.WIDTH // 2 - need * 8
            for i in range(need):
                rect = (x + i * 16 + 3, y + 8, 9, 16)
                if i < self.shots:
                    pygame.draw.rect(surf, T.LINE, rect, 1)
                else:
                    pygame.draw.rect(surf, T.ORANGE, rect)
                    pygame.draw.rect(surf, T.RED, (rect[0], rect[1], 9, 5))
                    pygame.draw.rect(surf, T.SPACE, rect, 1)
            y += 30
        if self.status:
            W.centered(surf, self.status[:36], T.COMMENT, max(y, 200))
        pygame.transform.scale(surf, self.window.get_size(), self.window)
        pygame.display.flip()
