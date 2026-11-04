/* fliperos-sdl-gun: carregada (LD_PRELOAD) no GroovyMAME pelo comando
 * groovymame (config/fliperos-groovymame) quando ha uma pistola de luz
 * ligada. A pistola (GunCon 2) chega ao X como um mouse de posicao absoluta,
 * e o lightgun do MAME (-lightgunprovider sdl, o unico do release) le a mira
 * da posicao do ponteiro na janela. Mas em tela cheia o MAME prende o mouse
 * no modo relativo do SDL, e o SDL 2.30 transforma a posicao absoluta em
 * deltas crus: a mira escorregava e ficava colada na borda de baixo (visto
 * no gabinete com o Area 51 em 2026-11-03). Aqui o modo relativo nunca liga:
 * o ponteiro segue a pistola e o MAME le a posicao dele.
 *
 * Compilada pelo config/fliperos-deflicker-build (libfliperos-sdl-gun.so). */
#define _GNU_SOURCE
#include <dlfcn.h>

int SDL_SetRelativeMouseMode(int enabled)
{
    static int (*real)(int);
    if (!real)
        real = (int (*)(int))dlsym(RTLD_NEXT, "SDL_SetRelativeMouseMode");
    (void)enabled;
    return real ? real(0) : 0;
}
