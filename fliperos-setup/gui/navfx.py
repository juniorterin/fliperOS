# A animacao de entrar e de voltar nos itens do Setup: o zoom.
#
# Entrar num item: a tela de onde se sai vem para perto (cresce e some) e a
# nova cresce de longe ate o tamanho dela, como quem mergulha no item.
# Voltar e o contrario: a tela que sai recua e some, e a anterior vem de
# perto ate o lugar dela.
#
# So a camada da interface anima (a que tem alfa por pixel, a ui de
# fliperos-gui): o fundo animado fica vivo por baixo, sem congelar. A conta e
# uma funcao do andamento p (0 a 1); quem toca o tempo e App.swap, pelo
# relogio e nao por quadros, para durar o mesmo se um quadro atrasar. A 60
# quadros por segundo, DURATION sao 18 quadros.

import pygame

DURATION = 0.30
IN, OUT = 1, -1

# Os tamanhos, em vezes o da tela: (de, ate) da tela que sai e da que chega.
# Entrar aproxima (1 -> 1,45 e 0,72 -> 1); voltar afasta (1 -> 0,70 e 1,38 -> 1).
SCALES = {
    IN: ((1.0, 1.45), (0.72, 1.0)),
    OUT: ((1.0, 0.70), (1.38, 1.0)),
}


def ease(p):
    """Rapido no comeco e freando no fim (a reacao ao Enter e imediata)."""
    return 1 - (1 - p) ** 3


def clamp(x):
    return max(0.0, min(1.0, x))


def smooth(edge0, edge1, x):
    """Degrau suave de 0 a 1 entre edge0 e edge1."""
    t = clamp((x - edge0) / (edge1 - edge0))
    return t * t * (3 - 2 * t)


def alphas(p):
    """A opacidade (0 a 255) da tela que sai e da que chega. A que chega
    aparece cedo (de 5% a 50% do caminho) e a que sai some por cima dela (de
    15% a 70%): no meio o desenho segue solido, sem uma queda de brilho."""
    return round(255 * (1 - smooth(0.15, 0.70, p))), round(255 * smooth(0.05, 0.50, p))


def scales(p, direction):
    """O tamanho (vezes a tela) da que sai e da que chega."""
    (old_from, old_to), (new_from, new_to) = SCALES[direction]
    e = ease(p)
    return old_from + (old_to - old_from) * e, new_from + (new_to - new_from) * e


def layer(surf, k, alpha):
    """A camada no tamanho k, centrada na tela, com a opacidade alpha. None
    se nao aparece. O tamanho 1 e a propria camada (sem refazer o quadro)."""
    if alpha <= 0:
        return None
    w, h = surf.get_size()
    if abs(k - 1) < 0.004:
        img = surf.copy() if alpha < 255 else surf
        pos = (0, 0)
    else:
        img = pygame.transform.smoothscale(surf, (max(1, round(w * k)), max(1, round(h * k))))
        pos = ((w - img.get_width()) // 2, (h - img.get_height()) // 2)
    if alpha < 255:
        img.set_alpha(alpha)
    return img, pos


def blend(out, old, new, p, direction):
    """Desenha em out (a camada da interface, com alfa) o quadro p (0 a 1) da
    passagem da camada old para a new. direction: IN ao entrar, OUT ao voltar.
    Em p=0 sai exatamente old; em p=1, exatamente new."""
    out.fill((0, 0, 0, 0))
    k_old, k_new = scales(p, direction)
    a_old, a_new = alphas(p)
    if p >= 1:
        a_old, a_new, k_new = 0, 255, 1.0
    elif p <= 0:
        a_old, a_new, k_old = 255, 0, 1.0
    # A que chega por baixo, a que sai por cima: a que sai tapa a nova ate sumir.
    for surf, k, alpha in ((new, k_new, a_new), (old, k_old, a_old)):
        drawn = layer(surf, k, alpha)
        if drawn:
            out.blit(drawn[0], drawn[1])
    return out
