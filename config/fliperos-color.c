/*
 * fliperos-color: a calibracao de cor do monitor (Setup > Video Setup >
 * Colour calibration). Os parametros ficam no fliperos.conf (color_*=) e
 * viram o que a placa tem:
 *
 *   a tabela de gama (LUT) de cada CRTC    brilho, contraste, gama, ganho,
 *                                          offset e gama de cada cor,
 *                                          temperatura de cor
 *   a matriz de cor (CTM) do CRTC          saturacao e matiz (sem ela, a
 *                                          camada config/fliperos-deflicker.c
 *                                          faz a mesma conta nos programas
 *                                          OpenGL: color_ctm=sw)
 *   a faixa RGB do conector                output_csc (radeon) ou
 *                                          Broadcast RGB (Intel)
 *
 *   fliperos-color caps        o que a placa tem: "lut N", "ctm yes|no",
 *                              "range NOME|none"
 *   fliperos-color apply       aplica no KMS (o dono do video, ou ninguem:
 *                              quem abre a placa primeiro vira o dono)
 *   fliperos-color x11         aplica a tabela de gama no X ($DISPLAY)
 *   fliperos-color lut [N]     imprime a tabela de N pontos e a matriz (testes)
 *
 * --conf ARQUIVO (ou FLIPEROS_CONF) troca o fliperos.conf. FLIPEROS_DRM_CARD
 * troca o /dev/dri/card0.
 */
#define _GNU_SOURCE
#include <fcntl.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <X11/Xlib.h>
#include <X11/extensions/Xrandr.h>
#include <drm_mode.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

/* ── Os parametros ──────────────────────────────────────────────── */

struct params {
    int brightness;     /* -50..50, 0 */
    int contrast;       /* 50..150 %, 100 */
    int gamma;          /* 50..200 (0,50 a 2,00), 100 */
    int gain[3];        /* 0..150 %, 100 */
    int offset[3];      /* -50..50, 0 */
    int cgamma[3];      /* 50..200, 100 */
    int temperature;    /* 4000..10000 K, 6500 */
    int saturation;     /* 0..200 %, 100 */
    int hue;            /* -180..180 graus, 0 */
    char range[16];     /* full, limited ou nada (nao mexe) */
};

static const char *channel[3] = {"red", "green", "blue"};

static int clampi(int v, int lo, int hi)
{
    return v < lo ? lo : v > hi ? hi : v;
}

static void defaults(struct params *p)
{
    memset(p, 0, sizeof(*p));
    p->contrast = 100;
    p->gamma = 100;
    for (int c = 0; c < 3; c++)
        p->gain[c] = 100, p->cgamma[c] = 100;
    p->temperature = 6500;
    p->saturation = 100;
}

static void read_conf(const char *path, struct params *p)
{
    char line[256], key[64], value[64];
    FILE *f = fopen(path, "r");
    defaults(p);
    while (f && fgets(line, sizeof(line), f)) {
        if (strncmp(line, "color_", 6) || sscanf(line, "color_%63[^=]=%63s", key, value) != 2)
            continue;
        int v = atoi(value);
        if (!strcmp(key, "brightness"))
            p->brightness = clampi(v, -50, 50);
        else if (!strcmp(key, "contrast"))
            p->contrast = clampi(v, 50, 150);
        else if (!strcmp(key, "gamma"))
            p->gamma = clampi(v, 50, 200);
        else if (!strcmp(key, "temperature"))
            p->temperature = clampi(v, 4000, 10000);
        else if (!strcmp(key, "saturation"))
            p->saturation = clampi(v, 0, 200);
        else if (!strcmp(key, "hue"))
            p->hue = clampi(v, -180, 180);
        else if (!strcmp(key, "range"))
            snprintf(p->range, sizeof(p->range), "%.15s", value);
        for (int c = 0; c < 3; c++) {
            char k[32];
            snprintf(k, sizeof(k), "%s_gain", channel[c]);
            if (!strcmp(key, k))
                p->gain[c] = clampi(v, 0, 150);
            snprintf(k, sizeof(k), "%s_offset", channel[c]);
            if (!strcmp(key, k))
                p->offset[c] = clampi(v, -50, 50);
            snprintf(k, sizeof(k), "%s_gamma", channel[c]);
            if (!strcmp(key, k))
                p->cgamma[c] = clampi(v, 50, 200);
        }
    }
    if (f)
        fclose(f);
}

/* temperature_rgb: o branco de uma temperatura de cor (a aproximacao de
 * Tanner Helland do corpo negro), dividido pelo de 6500 K: 6500 K nao
 * muda nada, 9300 K (o branco azulado de muito monitor de fliperama) tira
 * vermelho, 5000 K tira azul. */
static void blackbody(double kelvin, double rgb[3])
{
    double t = kelvin / 100.0;
    rgb[0] = t <= 66 ? 255 : 329.698727446 * pow(t - 60, -0.1332047592);
    rgb[1] = t <= 66 ? 99.4708025861 * log(t) - 161.1195681661 : 288.1221695283 * pow(t - 60, -0.0755148492);
    rgb[2] = t >= 66 ? 255 : t <= 19 ? 0 : 138.5177312231 * log(t - 10) - 305.0447927307;
    for (int c = 0; c < 3; c++)
        rgb[c] = rgb[c] < 0 ? 0 : rgb[c] > 255 ? 1.0 : rgb[c] / 255.0;
}

static void temperature_rgb(int kelvin, double out[3])
{
    double ref[3], want[3];
    blackbody(6500, ref);
    blackbody(kelvin, want);
    double top = 0;
    for (int c = 0; c < 3; c++) {
        out[c] = ref[c] > 0 ? want[c] / ref[c] : 1.0;
        if (out[c] > top)
            top = out[c];
    }
    /* O canal mais forte fica em 100%: so os outros caem (nada estoura). */
    for (int c = 0; c < 3; c++)
        out[c] /= top;
}

/* curve: a saida (0..1) da entrada x (0..1) num canal. */
static double curve(const struct params *p, const double temp[3], int c, double x)
{
    double v = pow(x, 1.0 / ((p->gamma / 100.0) * (p->cgamma[c] / 100.0)));
    v = (v - 0.5) * (p->contrast / 100.0) + 0.5 + p->brightness / 100.0;
    v = v * (p->gain[c] / 100.0) * temp[c] + p->offset[c] / 100.0;
    return v < 0 ? 0 : v > 1 ? 1 : v;
}

static void build_lut(const struct params *p, int n, uint16_t *r, uint16_t *g, uint16_t *b)
{
    double temp[3];
    uint16_t *out[3] = {r, g, b};
    temperature_rgb(p->temperature, temp);
    for (int c = 0; c < 3; c++)
        for (int i = 0; i < n; i++)
            out[c][i] = (uint16_t)lround(curve(p, temp, c, n > 1 ? (double)i / (n - 1) : 0) * 65535.0);
}

/* matrix: saturacao e matiz, as do filtro do CSS (saturate, hue-rotate),
 * que mantem a luminancia. Linha por linha: saida = m * (r, g, b). */
static void build_matrix(const struct params *p, double m[9])
{
    const double lr = 0.213, lg = 0.715, lb = 0.072;
    double s = p->saturation / 100.0, a = p->hue * M_PI / 180.0, cs = cos(a), sn = sin(a);
    double sat[9] = {lr + (1 - lr) * s, lg - lg * s, lb - lb * s,
                     lr - lr * s, lg + (1 - lg) * s, lb - lb * s,
                     lr - lr * s, lg - lg * s, lb + (1 - lb) * s};
    double hue[9] = {lr + cs * (1 - lr) - sn * lr, lg - cs * lg - sn * lg, lb - cs * lb + sn * (1 - lb),
                     lr - cs * lr + sn * 0.143, lg + cs * (1 - lg) + sn * 0.140, lb - cs * lb - sn * 0.283,
                     lr - cs * lr - sn * (1 - lr), lg - cs * lg + sn * lg, lb + cs * (1 - lb) + sn * lb};
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) {
            m[i * 3 + j] = 0;
            for (int k = 0; k < 3; k++)
                m[i * 3 + j] += hue[i * 3 + k] * sat[k * 3 + j];
        }
}

static int matrix_identity(const struct params *p)
{
    return p->saturation == 100 && p->hue == 0;
}

/* ── KMS ────────────────────────────────────────────────────────── */

static int open_card(void)
{
    const char *card = getenv("FLIPEROS_DRM_CARD");
    return open(card ? card : "/dev/dri/card0", O_RDWR | O_CLOEXEC);
}

/* find_prop: o id da propriedade NOME do objeto (0 se nao tem); em
 * enum_value, o valor do item VALOR de um enum. */
static uint32_t find_prop(int fd, uint32_t obj, uint32_t type, const char *name, const char *value,
                          uint64_t *enum_value)
{
    drmModeObjectPropertiesPtr props = drmModeObjectGetProperties(fd, obj, type);
    uint32_t id = 0;
    for (uint32_t i = 0; props && i < props->count_props && !id; i++) {
        drmModePropertyPtr prop = drmModeGetProperty(fd, props->props[i]);
        if (prop && !strcmp(prop->name, name)) {
            id = prop->prop_id;
            if (value && enum_value) {
                id = 0;
                for (int e = 0; e < prop->count_enums; e++)
                    if (!strcmp(prop->enums[e].name, value)) {
                        *enum_value = prop->enums[e].value;
                        id = prop->prop_id;
                    }
            }
        }
        drmModeFreeProperty(prop);
    }
    drmModeFreeObjectProperties(props);
    return id;
}

/* O nome do enum da faixa RGB: output_csc (radeon) ou Broadcast RGB. */
static const char *range_value(const char *prop, const char *range)
{
    if (!strcmp(prop, "output_csc"))
        return !strcmp(range, "limited") ? "tvrgb" : "bypass";
    return !strcmp(range, "limited") ? "Limited 16:235" : "Full";
}

static const char *range_props[] = {"output_csc", "Broadcast RGB", NULL};

static int caps(void)
{
    int fd = open_card(), lut = 0, ctm = 0;
    const char *range = "none";
    if (fd < 0) {
        printf("lut 0\nctm no\nrange none\n");
        return 1;
    }
    drmModeResPtr res = drmModeGetResources(fd);
    for (int i = 0; res && i < res->count_crtcs; i++) {
        drmModeCrtcPtr crtc = drmModeGetCrtc(fd, res->crtcs[i]);
        if (crtc && crtc->gamma_size > lut)
            lut = crtc->gamma_size;
        drmModeFreeCrtc(crtc);
        if (find_prop(fd, res->crtcs[i], DRM_MODE_OBJECT_CRTC, "CTM", NULL, NULL))
            ctm = 1;
    }
    for (int i = 0; res && i < res->count_connectors && !strcmp(range, "none"); i++)
        for (int k = 0; range_props[k]; k++)
            if (find_prop(fd, res->connectors[i], DRM_MODE_OBJECT_CONNECTOR, range_props[k], NULL, NULL))
                range = range_props[k];
    drmModeFreeResources(res);
    close(fd);
    printf("lut %d\nctm %s\nrange %s\n", lut, ctm ? "yes" : "no", range);
    return 0;
}

/* O formato do CTM: S31.32 com sinal e magnitude. */
static uint64_t s3132(double v)
{
    uint64_t mag = (uint64_t)llround(fabs(v) * 4294967296.0);
    return v < 0 ? (mag | (1ULL << 63)) : mag;
}

static int apply_kms(const struct params *p)
{
    int fd = open_card(), fails = 0;
    if (fd < 0) {
        perror("fliperos-color: /dev/dri/card0");
        return 1;
    }
    drmModeResPtr res = drmModeGetResources(fd);
    double m[9];
    build_matrix(p, m);
    for (int i = 0; res && i < res->count_crtcs; i++) {
        drmModeCrtcPtr crtc = drmModeGetCrtc(fd, res->crtcs[i]);
        if (crtc && crtc->gamma_size > 0) {
            int n = crtc->gamma_size;
            uint16_t *lut = calloc((size_t)n * 3, sizeof(uint16_t));
            build_lut(p, n, lut, lut + n, lut + 2 * n);
            if (drmModeCrtcSetGamma(fd, crtc->crtc_id, (uint32_t)n, lut, lut + n, lut + 2 * n)) {
                fprintf(stderr, "fliperos-color: CRTC %u: the gamma table was refused (another program owns the screen?)\n",
                        crtc->crtc_id);
                fails++;
            }
            free(lut);
        }
        uint32_t ctm = find_prop(fd, res->crtcs[i], DRM_MODE_OBJECT_CRTC, "CTM", NULL, NULL);
        if (ctm) {
            uint32_t blob = 0;
            if (!matrix_identity(p)) {
                struct drm_color_ctm c;
                for (int k = 0; k < 9; k++)
                    c.matrix[k] = s3132(m[k]);
                drmModeCreatePropertyBlob(fd, &c, sizeof(c), &blob);
            }
            if (drmModeObjectSetProperty(fd, res->crtcs[i], DRM_MODE_OBJECT_CRTC, ctm, blob))
                fails++;
            if (blob)
                drmModeDestroyPropertyBlob(fd, blob);
        }
        drmModeFreeCrtc(crtc);
    }
    for (int i = 0; res && p->range[0] && i < res->count_connectors; i++)
        for (int k = 0; range_props[k]; k++) {
            uint64_t value = 0;
            uint32_t prop = find_prop(fd, res->connectors[i], DRM_MODE_OBJECT_CONNECTOR, range_props[k],
                                      range_value(range_props[k], p->range), &value);
            if (prop && drmModeObjectSetProperty(fd, res->connectors[i], DRM_MODE_OBJECT_CONNECTOR, prop, value))
                fails++;
        }
    drmModeFreeResources(res);
    close(fd);
    return fails ? 1 : 0;
}

/* ── X ──────────────────────────────────────────────────────────── */

static int apply_x11(const struct params *p)
{
    Display *dpy = XOpenDisplay(NULL);
    int done = 0;
    if (!dpy) {
        fprintf(stderr, "fliperos-color: no X display\n");
        return 1;
    }
    XRRScreenResources *res = XRRGetScreenResourcesCurrent(dpy, DefaultRootWindow(dpy));
    for (int i = 0; res && i < res->ncrtc; i++) {
        int n = XRRGetCrtcGammaSize(dpy, res->crtcs[i]);
        if (n <= 0)
            continue;
        XRRCrtcGamma *g = XRRAllocGamma(n);
        build_lut(p, n, g->red, g->green, g->blue);
        XRRSetCrtcGamma(dpy, res->crtcs[i], g);
        XRRFreeGamma(g);
        done++;
    }
    if (res)
        XRRFreeScreenResources(res);
    XSync(dpy, False);
    XCloseDisplay(dpy);
    return done ? 0 : 1;
}

int main(int argc, char **argv)
{
    const char *conf = getenv("FLIPEROS_CONF");
    const char *cmd = argc > 1 ? argv[1] : "";
    int n = 16;
    struct params p;
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--conf") && i + 1 < argc)
            conf = argv[++i];
        else
            n = clampi(atoi(argv[i]), 2, 4096);
    }
    read_conf(conf ? conf : "/etc/fliperos/fliperos.conf", &p);
    if (!strcmp(cmd, "caps"))
        return caps();
    if (!strcmp(cmd, "apply"))
        return apply_kms(&p);
    if (!strcmp(cmd, "x11"))
        return apply_x11(&p);
    if (!strcmp(cmd, "lut")) {
        uint16_t *lut = calloc((size_t)n * 3, sizeof(uint16_t));
        double m[9];
        build_lut(&p, n, lut, lut + n, lut + 2 * n);
        for (int c = 0; c < 3; c++) {
            printf("%s", channel[c]);
            for (int i = 0; i < n; i++)
                printf(" %u", lut[c * n + i]);
            printf("\n");
        }
        build_matrix(&p, m);
        printf("matrix");
        for (int k = 0; k < 9; k++)
            printf(" %.4f", m[k]);
        printf("\n");
        free(lut);
        return 0;
    }
    fprintf(stderr, "Usage: fliperos-color caps|apply|x11|lut [N] [--conf FILE]\n");
    return 2;
}
