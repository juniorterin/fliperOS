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
