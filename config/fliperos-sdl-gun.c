/* fliperos-sdl-gun: carregada (LD_PRELOAD) no GroovyMAME pelo comando
 * groovymame (config/fliperos-groovymame) quando ha uma pistola de luz
 * ligada. A pistola (GunCon 2) chega como um mouse de posicao absoluta, e o
 * lightgun do MAME (-lightgunprovider sdl, o unico do release) le a mira da
 * posicao do ponteiro na janela. Mas em tela cheia o MAME prende o mouse no
 * modo relativo do SDL, e o SDL 2.30 transforma a posicao absoluta em deltas
 * crus: a mira escorregava e ficava colada na borda de baixo (visto no
 * gabinete com o Area 51 em 2026-11-03). Aqui o modo relativo nunca liga: o
 * ponteiro segue a pistola e o MAME le a posicao dele.
 *
 * No KMS (sem X) o SDL le a pistola pelo evdev. Mirando fora da tela ela
 * passa do comeco da faixa, o SDL calcula uma posicao negativa, tira o mouse
 * da janela (SDL_WINDOWEVENT_LEAVE) e nao o devolve mais: no X quem o
 * devolve e o servidor. Dai em diante os eventos chegam sem janela
 * (windowID 0), e o MAME (sdl_lightgun_device) deixa a mira em 0 (visto no
 * gabinete com o Area 51 em 2026-11-05). Aqui o evento sem janela ganha a
 * janela do jogo e o LEAVE dessa janela some. A posicao fica como o SDL a
 * calculou, fora da janela quando a pistola mira fora da tela: o MAME a le
 * assim e o jogo recarrega. Presa na borda (como o ponteiro do X), o Area 51
 * as vezes lia o tiro como dentro da tela e nao recarregava.
 *
 * Compilada pelo config/fliperos-deflicker-build (libfliperos-sdl-gun.so). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>

int SDL_SetRelativeMouseMode(int enabled)
{
    static int (*real)(int);
    if (!real)
        real = (int (*)(int))dlsym(RTLD_NEXT, "SDL_SetRelativeMouseMode");
    (void)enabled;
    return real ? real(0) : 0;
}

/* O SDL_Event do SDL2 (ABI estavel), so os campos usados aqui. */
enum { WINDOWEVENT = 0x200, MOUSEMOTION = 0x400, MOUSEBUTTONDOWN = 0x401, MOUSEBUTTONUP = 0x402 };
enum { WINDOWEVENT_LEAVE = 11, GETEVENT = 2 };
typedef union {
    uint32_t type;
    struct { uint32_t type, timestamp, window, which, state; int32_t x, y, xrel, yrel; } motion;
    struct { uint32_t type, timestamp, window, which; uint8_t button, state, clicks, pad; int32_t x, y; } button;
    struct { uint32_t type, timestamp, window; uint8_t event, pad1, pad2, pad3; int32_t data1, data2; } window;
    uint8_t padding[56];
} event_t;

/* fix: 0 para tirar o evento da fila (o LEAVE), 1 para entregar. */
static int fix(event_t *e)
{
    static void *(*keyboard_focus)(void);
    static uint32_t (*window_id)(void *);
    uint32_t *window;
    void *win;

    if (!keyboard_focus) {
        keyboard_focus = (void *(*)(void))dlsym(RTLD_DEFAULT, "SDL_GetKeyboardFocus");
        window_id = (uint32_t (*)(void *))dlsym(RTLD_DEFAULT, "SDL_GetWindowID");
        if (!keyboard_focus || !window_id)
            return 1;
    }
    if (e->type == MOUSEMOTION) {
        window = &e->motion.window;
    } else if (e->type == MOUSEBUTTONDOWN || e->type == MOUSEBUTTONUP) {
        window = &e->button.window;
    } else if (e->type == WINDOWEVENT && e->window.event == WINDOWEVENT_LEAVE) {
        win = keyboard_focus();
        return !(win && window_id(win) == e->window.window);
    } else {
        return 1;
    }
    if (*window == 0 && (win = keyboard_focus()))
        *window = window_id(win);
    return 1;
}

int SDL_PollEvent(event_t *e)
{
    static int (*real)(event_t *);
    if (!real)
        real = (int (*)(event_t *))dlsym(RTLD_NEXT, "SDL_PollEvent");
    if (!real)
        return 0;
    for (;;) {
        int r = real(e);
        if (!r || !e || fix(e))
            return r;
    }
}

int SDL_PeepEvents(event_t *events, int n, int action, uint32_t min, uint32_t max)
{
    static int (*real)(event_t *, int, int, uint32_t, uint32_t);
    int r, i, kept = 0;
    if (!real)
        real = (int (*)(event_t *, int, int, uint32_t, uint32_t))dlsym(RTLD_NEXT, "SDL_PeepEvents");
    if (!real)
        return -1;
    r = real(events, n, action, min, max);
    if (action != GETEVENT || r <= 0 || !events)
        return r;
    for (i = 0; i < r; i++)
        if (fix(&events[i]))
            events[kept++] = events[i];
    return kept;
}
