/* fliperos-dropmaster: carregada (LD_PRELOAD) no ffmpeg da tela ao vivo
 * (config/fliperos-stream). Quem abre /dev/dri/cardN quando ninguem e o dono
 * da tela (o "DRM master": entre um jogo e o frontend, o desktop abrindo)
 * vira o dono, e o kernel nao devolve: o X e o menu grafico do Setup nao
 * conseguem mais o video ("drmSetMaster failed", visto no gabinete em
 * 2026-10-22). O kmsgrab nao precisa ser dono (como root, le os buffers com o
 * CAP_SYS_ADMIN): logo depois de abrir, a tela e devolvida.
 *
 * Compilada pelo config/fliperos-deflicker-build (libfliperos-dropmaster.so). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <stdarg.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/types.h>

#ifndef DRM_IOCTL_DROP_MASTER
#define DRM_IOCTL_DROP_MASTER _IO('d', 0x1f)
#endif

static int drop(int fd, const char *path)
{
    /* Sem ser o dono, o ioctl so falha (EINVAL): nada a fazer. */
    if (fd >= 0 && path && strncmp(path, "/dev/dri/card", 13) == 0)
        ioctl(fd, DRM_IOCTL_DROP_MASTER, 0);
    return fd;
}

static mode_t mode_of(int flags, va_list ap)
{
    if ((flags & O_CREAT) || (flags & O_TMPFILE) == O_TMPFILE)
        return (mode_t)va_arg(ap, int);
    return 0;
}

#define WRAP_OPEN(name)                                                      \
    int name(const char *path, int flags, ...)                               \
    {                                                                        \
        static int (*real)(const char *, int, ...);                          \
        va_list ap;                                                          \
        mode_t mode;                                                         \
        if (!real)                                                           \
            real = (int (*)(const char *, int, ...))dlsym(RTLD_NEXT, #name); \
        va_start(ap, flags);                                                 \
        mode = mode_of(flags, ap);                                           \
        va_end(ap);                                                          \
        return drop(real(path, flags, mode), path);                          \
    }

#define WRAP_OPENAT(name)                                                         \
    int name(int dir, const char *path, int flags, ...)                           \
    {                                                                             \
        static int (*real)(int, const char *, int, ...);                          \
        va_list ap;                                                               \
        mode_t mode;                                                              \
        if (!real)                                                                \
            real = (int (*)(int, const char *, int, ...))dlsym(RTLD_NEXT, #name); \
        va_start(ap, flags);                                                      \
        mode = mode_of(flags, ap);                                                \
        va_end(ap);                                                               \
        return drop(real(dir, path, flags, mode), path);                          \
    }

WRAP_OPEN(open)
WRAP_OPEN(open64)
WRAP_OPENAT(openat)
WRAP_OPENAT(openat64)
