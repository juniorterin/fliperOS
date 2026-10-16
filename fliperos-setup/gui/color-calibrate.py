# A calibracao de cor na tela (Setup > Video Setup > Colour calibration):
# padroes de teste e, embaixo, o parametro escolhido, que as setas mudam na
# hora. Aberto pelo fliperos-x11-run no modo do Video Setup: a tabela de
# gama vai para o X a cada mudanca (fliperos-color x11), e a saturacao e o
# matiz pela camada config/fliperos-deflicker.c, que rele o arquivo de
# FLIPEROS_COLOR_FILE (o mesmo --conf) a cada 30 quadros.
#
#   color-calibrate.py --table TABELA --conf ARQUIVO --out ARQUIVO
#                      [--range NOME|none] [--bin fliperos-color]
#
# TABELA: o color_table do lib/video.sh (chave|rotulo|min|max|padrao|passo|
# ajuda). ARQUIVO: linhas color_CHAVE=valor (e color_range=). Enter grava
# os valores em --out e sai com 0; Esc sai com 1.

import argparse
import os
import subprocess

# O quadro da janela pelo OpenGL: a camada so ve o que passa por ele.
os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "opengl")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

import theme as T  # noqa: E402

BLACK = (0, 0, 0)
PATTERNS = ["Colour bars", "Grey steps", "Black level", "White level", "RGB ramps", "Colour patches"]
# As cores do ColorChecker classico (sRGB), em quatro fileiras.
CHECKER = [
    (115, 82, 68), (194, 150, 130), (98, 122, 157), (87, 108, 67), (133, 128, 177), (103, 189, 170),
    (214, 126, 44), (80, 91, 166), (193, 90, 99), (94, 60, 108), (157, 188, 64), (224, 163, 46),
    (56, 61, 150), (70, 148, 73), (175, 54, 60), (231, 199, 31), (187, 86, 149), (8, 133, 161),
    (243, 243, 242), (200, 200, 200), (160, 160, 160), (122, 122, 121), (85, 85, 85), (52, 52, 52),
]
RANGES = ["", "full", "limited"]
RANGE_NAMES = {"": "Card default", "full": "Full (0-255)", "limited": "Limited (16-235)"}


def read_values(path):
    values = {}
    try:
        with open(path) as f:
            for line in f:
                if line.startswith("color_") and "=" in line:
                    key, value = line.strip()[6:].split("=", 1)
                    values[key] = value
    except OSError:
        pass
    return values


class Calibrator:
    def __init__(self, table, values, conf, range_prop, binary):
        self.params = table
        self.values = {k: int(values.get(k, d)) if str(values.get(k, d)).lstrip("-").isdigit() else d
                       for k, _, _, _, d, _, _ in table}
        self.range = values.get("range", "") if values.get("range", "") in RANGES else ""
        self.range_prop = range_prop
        self.conf = conf
        self.binary = binary
        # As linhas: o padrao, os parametros, a faixa RGB (se a placa tem) e
        # o "voltar ao padrao".
        self.rows = ["pattern"] + [p[0] for p in table] + (["range"] if range_prop != "none" else []) + ["reset"]
        self.row = 0
        self.pattern = 0
        self.hidden = False
        self.dirty = True
        pygame.display.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        pygame.mouse.set_visible(False)
        pygame.key.set_repeat(300, 40)
        self.w, self.h = self.screen.get_size()
        self.font = T.font()

    def param(self, key):
        for p in self.params:
            if p[0] == key:
                return p
        return None

    # Os valores --------------------------------------------------------

    def save_conf(self, path):
        with open(path + ".tmp", "w") as f:
            for key, value in self.values.items():
                f.write("color_%s=%d\n" % (key, value))
            if self.range:
                f.write("color_range=%s\n" % self.range)
        os.replace(path + ".tmp", path)

    def apply(self):
        """A tabela de gama no X na hora; a matriz a camada rele do arquivo."""
        self.save_conf(self.conf)
        try:
            subprocess.run([self.binary, "x11", "--conf", self.conf], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=5)
        except (OSError, subprocess.SubprocessError):
            pass
        self.dirty = False

    def change(self, step):
        key = self.rows[self.row]
        if key == "pattern":
            self.pattern = (self.pattern + step) % len(PATTERNS)
            return
        if key == "range":
            self.range = RANGES[(RANGES.index(self.range) + step) % len(RANGES)]
            return
        if key == "reset":
            for k, _, _, _, d, _, _ in self.params:
                self.values[k] = d
            self.range = ""
            self.dirty = True
            return
        _, _, lo, hi, _, inc, _ = self.param(key)
        self.values[key] = max(lo, min(hi, self.values[key] + step * inc))
        self.dirty = True

    def pretty(self, key):
        if key == "pattern":
            return PATTERNS[self.pattern]
        if key == "range":
            return RANGE_NAMES[self.range] + " (on save)"
        if key == "reset":
            return "< > back to the defaults"
        v = self.values[key]
        if key.endswith("gamma"):
            return "%d.%02d" % (v // 100, v % 100)
        if key == "temperature":
            return "%d K" % v
        if key in ("contrast", "saturation") or key.endswith("_gain"):
            return "%d%%" % v
        if key == "hue":
            return "%d deg" % v
        return "%+d" % v if v else "0"

    def label(self, key):
        if key == "pattern":
            return "Test pattern"
        if key == "range":
            return "RGB range"
        if key == "reset":
            return "Reset"
        return self.param(key)[1]

    def help(self, key):
        if key == "pattern":
            return "Left and right change the test pattern. Space hides this bar."
        if key == "range":
            return "Full for a PC monitor or CRT; limited only for a TV that expects 16-235."
        if key == "reset":
            return "Every setting back to the picture the card sends."
        return self.param(key)[6]

    # Os padroes --------------------------------------------------------

    def rect(self, color, x, y, w, h):
        """Em fracoes da tela (0..1)."""
        W, H = self.w, self.h
        pygame.draw.rect(self.screen, color, (round(x * W), round(y * H), round((x + w) * W) - round(x * W),
                                              round((y + h) * H) - round(y * H)))

    def text(self, s, color, x, y):
        self.screen.blit(self.font.render(s, False, color), (round(x * self.w), round(y * self.h)))

    def draw_pattern(self):
        s = self.screen
        s.fill(BLACK)
        name = PATTERNS[self.pattern]
        if name == "Colour bars":
            # As barras de 75% (SMPTE): branco, amarelo, ciano, verde, magenta,
            # vermelho e azul; embaixo, as invertidas e o branco cheio com os
            # pretos quase pretos (PLUGE).
            bars = [(191, 191, 191), (191, 191, 0), (0, 191, 191), (0, 191, 0), (191, 0, 191), (191, 0, 0), (0, 0, 191)]
            for i, c in enumerate(bars):
                self.rect(c, i / 7, 0, 1 / 7, 0.67)
            rev = [(0, 0, 191), BLACK, (191, 0, 191), BLACK, (0, 191, 191), BLACK, (191, 191, 191)]
            for i, c in enumerate(rev):
                self.rect(c, i / 7, 0.67, 1 / 7, 0.08)
            self.rect((0, 33, 76), 0, 0.75, 5 / 28, 0.25)
            self.rect((255, 255, 255), 5 / 28, 0.75, 5 / 28, 0.25)
            self.rect((50, 0, 106), 10 / 28, 0.75, 5 / 28, 0.25)
            for i, v in enumerate((0, 5, 10)):
                self.rect((v, v, v), 15 / 28 + i * 3 / 28, 0.75, 3 / 28, 0.25)
        elif name == "Grey steps":
            for i in range(16):
                v = i * 17
                self.rect((v, v, v), i / 16, 0, 1 / 16, 0.5)
            for x in range(self.w):
                v = round(255 * x / max(1, self.w - 1))
                pygame.draw.line(s, (v, v, v), (x, self.h // 2), (x, self.h - 1))
        elif name == "Black level":
            # Barras de 1, 2, 4 e 8% no preto: com o brilho certo a de 1% some
            # e a de 2% mal aparece.
            for i, v in enumerate((3, 5, 10, 20)):
                self.rect((v, v, v), 0.15 + i * 0.18, 0.2, 0.12, 0.5)
                self.text("%d%%" % (1 << i), (90, 90, 90), 0.15 + i * 0.18, 0.75)
        elif name == "White level":
            # O branco cheio com quadros de 90, 95 e 98%: com o contraste certo
            # os tres aparecem sem o branco espalhar.
            s.fill((255, 255, 255))
            for i, (v, pct) in enumerate(((230, 90), (242, 95), (250, 98))):
                self.rect((v, v, v), 0.15 + i * 0.25, 0.25, 0.18, 0.4)
                self.text("%d%%" % pct, (150, 150, 150), 0.15 + i * 0.25, 0.68)
            self.rect(BLACK, 0.45, 0.8, 0.1, 0.1)
        elif name == "RGB ramps":
            rows = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)]
            band = self.h // 4
            for r, (fr, fg, fb) in enumerate(rows):
                for x in range(self.w):
                    v = round(255 * x / max(1, self.w - 1))
                    pygame.draw.line(s, (v * fr, v * fg, v * fb), (x, r * band), (x, (r + 1) * band - 1))
        else:
            for i, c in enumerate(CHECKER):
                self.rect(c, 0.04 + (i % 6) * 0.155, 0.04 + (i // 6) * 0.235, 0.145, 0.215)

    def draw_bar(self):
        if self.hidden:
            return
        key = self.rows[self.row]
        h = 36
        y = self.h - h
        pygame.draw.rect(self.screen, T.BG_DEEP, (0, y, self.w, h))
        pygame.draw.line(self.screen, T.PURPLE, (0, y), (self.w, y))
        line = "%d/%d %s: %s" % (self.row + 1, len(self.rows), self.label(key).upper(), self.pretty(key))
        self.screen.blit(self.font.render(line, False, T.PINK), (8, y + 4))
        about = self.help(key)
        cols = max(10, (self.w - 16) // 8)
        self.screen.blit(self.font.render(about[:cols], False, T.FG), (8, y + 15))
        hint = "^v ITEM  <> CHANGE  SPACE HIDE  ENTER SAVE  ESC CANCEL"
        self.screen.blit(self.font.render(hint[:cols], False, T.CYAN), (8, y + 26))

    # O laco ------------------------------------------------------------

    def run(self):
        clock = pygame.time.Clock()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type != pygame.KEYDOWN:
                    continue
                if event.key == pygame.K_UP:
                    self.row = (self.row - 1) % len(self.rows)
                elif event.key == pygame.K_DOWN:
                    self.row = (self.row + 1) % len(self.rows)
                elif event.key == pygame.K_LEFT:
                    self.change(-1)
                elif event.key == pygame.K_RIGHT:
                    self.change(1)
                elif event.key == pygame.K_SPACE:
                    self.hidden = not self.hidden
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return True
                elif event.key == pygame.K_ESCAPE:
                    return False
            if self.dirty:
                self.apply()
            self.draw_pattern()
            self.draw_bar()
            pygame.display.flip()
            clock.tick(30)


def read_table(path):
    table = []
    with open(path) as f:
        for line in f:
            parts = line.rstrip("\n").split("|")
            if len(parts) >= 7:
                key, label, lo, hi, default, step, about = parts[:7]
                table.append((key, label, int(lo), int(hi), int(default), int(step), about))
    return table


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", required=True)
    parser.add_argument("--conf", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--range", default="none")
    parser.add_argument("--bin", default="/usr/local/bin/fliperos-color")
    args = parser.parse_args()
    cal = Calibrator(read_table(args.table), read_values(args.conf), args.conf, args.range, args.bin)
    try:
        keep = cal.run()
    finally:
        pygame.display.quit()
    if not keep:
        raise SystemExit(1)
    cal.save_conf(args.out)


if __name__ == "__main__":
    main()
