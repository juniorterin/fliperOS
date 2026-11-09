/* fliperos-sdl-audio: carregada (LD_PRELOAD) no GroovyMAME pelo comando
 * groovymame (config/fliperos-groovymame). O MAME 0.289 liga o alto-falante
 * de cada jogo na saida que o SDL diz ser a padrao (SDL_GetDefaultAudioInfo)
 * e grava a escolha no cfg do jogo. O ALSA do SDL 2.30 nao sabe dizer a
 * padrao (devolve erro) e lista so os hw: das placas: o MAME pegava o
 * primeiro, "HDA Intel MID, ALC662 rev3 Analog", e abria o hw: direto, fora
 * do "default" do ALSA (sem o dmix, sem a placa do Setup, sem o som na tela
 * ao vivo; visto no gabinete em 2026-10-23). Aqui a padrao e o "default":
 * o MAME o abre pelo SDL sem nome, que no ALSA e o default.
 *
 * Com um SDL que sabe a padrao (PulseAudio, PipeWire), vale a dele.
 *
 * E o SIGTERM fecha o jogo (o fim deste arquivo).
 *
 * Compilada pelo config/fliperos-deflicker-build (libfliperos-sdl-audio.so). */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdint.h>
#include <string.h>

/* O SDL_AudioSpec do SDL 2 (SDL_audio.h), sem precisar dos cabecalhos. */
typedef struct {
    int freq;
    uint16_t format;
    uint8_t channels;
    uint8_t silence;
    uint16_t samples;
    uint16_t padding;
    uint32_t size;
    void *callback;
    void *userdata;
} audio_spec;

int SDL_GetDefaultAudioInfo(char **name, audio_spec *spec, int iscapture)
{
    static int (*real)(char **, audio_spec *, int);
    if (!real)
        real = (int (*)(char **, audio_spec *, int))dlsym(RTLD_NEXT, "SDL_GetDefaultAudioInfo");
    if (real && real(name, spec, iscapture) == 0)
        return 0;
    if (iscapture)
        return -1;
    /* O MAME devolve o nome com SDL_free, que e o free da libc. */
    if (name && !(*name = strdup("default")))
        return -1;
    if (spec) {
        memset(spec, 0, sizeof *spec);
        spec->freq = 48000;
        spec->format = 0x8010; /* AUDIO_S16LSB */
        spec->channels = 2;
        spec->samples = 1024;
    }
    return 0;
}

/* O SIGTERM (o botao de desligar, config/fliperos-powerkey; o atalho de
 * sair do frontend): o SDL o transforma num SDL_QUIT, que o MAME 0.289
 * ignora (src/osd/sdl/osdsdl.cpp so sai com o SDL_WINDOWEVENT_CLOSE da
 * janela). No X o Xorg fechava junto; no KMS o jogo seguia aberto ate o
 * SIGKILL, sem gravar a nvram, o hiscore e o cfg. Aqui o SDL_QUIT vira o
 * "fechar" da ultima janela criada, e o MAME sai como pelo Esc. */
#define EV_QUIT 0x100
#define EV_WINDOW 0x200
#define WINDOW_CLOSE 14

/* O SDL_WindowEvent dentro do SDL_Event (56 bytes) do SDL 2. */
typedef struct {
    uint32_t type;
    uint32_t timestamp;
    uint32_t window_id;
    uint8_t event;
    uint8_t padding[3];
    int32_t data1;
    int32_t data2;
} window_event;

uint32_t fliperos_last_window; /* a ultima janela criada (o teste a troca) */

void *SDL_CreateWindow(const char *title, int x, int y, int w, int h, uint32_t flags)
{
    static void *(*real)(const char *, int, int, int, int, uint32_t);
    static uint32_t (*window_id)(void *);
    if (!real)
        real = (void *(*)(const char *, int, int, int, int, uint32_t))dlsym(RTLD_NEXT, "SDL_CreateWindow");
    if (!window_id)
        window_id = (uint32_t (*)(void *))dlsym(RTLD_NEXT, "SDL_GetWindowID");
    void *window = real ? real(title, x, y, w, h, flags) : 0;
    if (window && window_id)
        fliperos_last_window = window_id(window);
    return window;
}

/* fliperos_quit_to_close: o SDL_QUIT em EVENT vira o fechar da janela (sem
 * janela criada, fica como esta). Separada para o teste. */
int fliperos_quit_to_close(void *event)
{
    window_event *e = event;
    if (!e || e->type != EV_QUIT || !fliperos_last_window)
        return 0;
    uint32_t timestamp = e->timestamp;
    memset(e, 0, 56);
    e->type = EV_WINDOW;
    e->timestamp = timestamp;
    e->window_id = fliperos_last_window;
    e->event = WINDOW_CLOSE;
    return 1;
}

int SDL_PollEvent(void *event)
{
    static int (*real)(void *);
    if (!real)
        real = (int (*)(void *))dlsym(RTLD_NEXT, "SDL_PollEvent");
    if (!real)
        return 0;
    int got = real(event);
    if (got)
        fliperos_quit_to_close(event);
    return got;
}
