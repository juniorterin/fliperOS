#!/usr/bin/env python3
"""Gera as imagens em pe do splash do FliperOS (config/splashscreen/fliperos).

    python3 tools/splash-vertical.py [PASTA_DO_TEMA]

O Plymouth nao gira a tela num CRT (o panel_orientation do kernel so vale
para paineis internos), entao o tema traz as imagens ja giradas: com o
monitor em pe, o logo de 640x480 cabe na largura do tubo em pe (480x360, no
meio de uma tela de 480x640) e o todo gira para o lado do monitor
(logo-cw.png, logo-ccw.png, de 640x480 como o logo deitado). A barra
(throbber-0N.png) encolhe na mesma proporcao e gira junto
(throbber-cw-0N.png, throbber-ccw-0N.png). O fliperos.script escolhe pelo
orientation do comeco dele (lib/splash.sh splash_orientation).
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = 33
SCALE = 480 / 640                      # o logo deitado na largura do tubo em pe
ANGLES = {"cw": -90, "ccw": 90}        # como o ror/rol do MAME e o fbcon


def main():
    theme = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "config/splashscreen/fliperos")
    pygame.display.init()
    logo = pygame.image.load(os.path.join(theme, "logo.png"))
    portrait = pygame.Surface((480, 640))
    portrait.fill((0, 0, 0))
    small = pygame.transform.smoothscale(logo, (480, 360))
    portrait.blit(small, (0, (640 - 360) // 2))
    for side, angle in ANGLES.items():
        pygame.image.save(pygame.transform.rotate(portrait, angle), os.path.join(theme, "logo-%s.png" % side))
        for frame in range(FRAMES):
            bar = pygame.image.load(os.path.join(theme, "throbber-0%d.png" % frame))
            w, h = bar.get_size()
            bar = pygame.transform.smoothscale(bar, (round(w * SCALE), round(h * SCALE)))
            pygame.image.save(pygame.transform.rotate(bar, angle),
                              os.path.join(theme, "throbber-%s-0%d.png" % (side, frame)))
    print("ok")


if __name__ == "__main__":
    main()
