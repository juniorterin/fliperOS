"""Solta o DRM master depois de fechar a tela.

O pygame fecha o video com pygame.display.quit(), mas na Intel (visto numa
HD Graphics Ironlake, Mesa 25) o Mesa deixa descritores de /dev/dri/card0
abertos depois disso. Enquanto eles existem o processo segue dono da tela:
o programa que abre em seguida (um jogo, o RetroArch) falha em "Error when
switching mode", e o proprio pygame nao consegue reabrir ("kmsdrm not
available"). O drop() tira o master de cada um deles, sem fecha-los (o Mesa
ainda os conhece). Onde nao ha descritor sobrando (a AMD) nao faz nada.
"""

import fcntl
import os

DRM_IOCTL_DROP_MASTER = 0x641F  # _IO('d', 0x1f), do drm.h


def drop():
    """Devolve em quantos descritores o master foi solto."""
    dropped = 0
    try:
        names = os.listdir("/proc/self/fd")
    except OSError:
        return 0
    for name in names:
        try:
            target = os.readlink("/proc/self/fd/" + name)
        except OSError:
            continue
        if not target.startswith("/dev/dri/card"):
            continue
        try:
            fcntl.ioctl(int(name), DRM_IOCTL_DROP_MASTER)
            dropped += 1
        except OSError:
            pass  # nao era dono (EACCES) ou o kernel nao tem o ioctl
    return dropped
