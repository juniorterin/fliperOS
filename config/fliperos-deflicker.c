/*
 * fliperos-deflicker: o filtro de flicker do 480i do FliperOS (Setup >
 * Video Setup > Interlace flicker filter), para qualquer emulador OpenGL.
 *
 * Carregada por LD_PRELOAD (config/fliperos-kms-run e fliperos-x11-run), ela
 * fica na troca de quadro (eglSwapBuffers no KMS, glXSwapBuffers no X): com o
 * modo de video da tela entrelacado (o DRM diz), a imagem pronta passa por um
 * filtro vertical antes de ir para a tela. Num modo entrelacado cada campo
 * mostra so as linhas pares ou as impares; uma linha fina, que so existe num
 * campo, pisca a 30 Hz. Misturar cada linha com a vizinha poe um pouco dela
 * nos dois campos: o tremor some, com um pouco menos de nitidez vertical. E
 * o "Interlaced Flicker Reduction" do RePlayOS (a textura do jogo filtrada
 * linearmente entre duas linhas), aqui na saida de qualquer programa.
 *
 * Os pesos (linha de cima, a propria, a de baixo):
 *   light   0.15 0.70 0.15
 *   medium  0.50 0.50 0.00   a media de duas linhas, como o RePlayOS
 *   strong  0.33 0.34 0.33
 *   off     nada
 * O nivel de cada programa (Setup > Video Setup > 480i games), do primeiro
 * que existir:
 *   FLIPEROS_DEFLICKER_FILE  um arquivo com o nivel, relido a cada 30
 *                            quadros (o preview, que troca o nivel na hora)
 *   FLIPEROS_DEFLICKER       o nivel
 *   deflicker_CORE=          no fliperos.conf (FLIPEROS_CONF), o core do
 *                            RetroArch aberto (pcsx_rearmed_libretro.so: pcsx_rearmed)
 *   deflicker_PROGRAMA=      o programa: FLIPEROS_DEFLICKER_APP (o nome na
 *                            tabela do fliperos-x11-run) ou o do processo
 *   deflicker=               o de todos os outros
 * Sem nenhum, medium. FLIPEROS_DEFLICKER_FORCE=1 filtra mesmo sem modo
 * entrelacado (os testes, sem DRM). O 240p nao muda: sem modo entrelacado,
 * a troca de quadro passa direto.
 *
 * A saturacao e o matiz da calibracao de cor (Setup > Video Setup > Colour
 * calibration, config/fliperos-color.c) tambem passam por aqui quando a
 * placa nao tem a matriz de cor (CTM) no hardware: color_ctm=sw no
 * fliperos.conf, com color_saturation= e color_hue=. A mesma conta do
 * fliperos-color, em qualquer modo de video. FLIPEROS_COLOR_FILE: um
 * arquivo com essas linhas, relido a cada 30 quadros (o calibrador).
 *
 * O SDL e outros abrem a libGL por dlopen e pegam o glXSwapBuffers por
 * dlsym: o dlsym tambem passa por aqui. O estado do OpenGL do programa e
 * guardado e devolvido em volta do filtro.
 */
#define _GNU_SOURCE
#define GL_GLEXT_PROTOTYPES
#include <ctype.h>
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <link.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <EGL/egl.h>
#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

/* ── O dlsym de verdade ─────────────────────────────────────────── */

typedef void *(*dlsym_fn)(void *, const char *);

static dlsym_fn real_dlsym(void)
{
    static dlsym_fn fn;
    if (!fn) {
        fn = (dlsym_fn)dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.34");
        if (!fn)
            fn = (dlsym_fn)dlvsym(RTLD_NEXT, "dlsym", "GLIBC_2.2.5");
    }
    return fn;
}

/* sym NOME: a funcao da biblioteca de verdade (a proxima depois desta, ou
 * a libGL/libEGL ja carregada pelo programa). */
static void *sym(const char *name)
{
    static const char *libs[] = {"libGLX.so.0", "libGL.so.1", "libEGL.so.1", "libOpenGL.so.0", NULL};
    void *p = real_dlsym()(RTLD_NEXT, name);
    for (int i = 0; !p && libs[i]; i++) {
        void *h = dlopen(libs[i], RTLD_LAZY | RTLD_NOLOAD);
        if (h)
            p = real_dlsym()(h, name);
    }
    return p;
}

/* ── O nivel e o modo da tela ───────────────────────────────────── */

static float weights[3] = {0.5f, 0.5f, 0.0f};
static int level_off;
static int forced;

static void log_once(const char *msg)
{
    if (getenv("FLIPEROS_DEFLICKER_QUIET"))
        return;
    fprintf(stderr, "fliperos-deflicker: %s\n", msg);
}

/* As linhas "deflicker...=" do fliperos.conf, lidas uma vez. */
static char conf_lines[4096];

static void load_conf(void)
{
    const char *conf = getenv("FLIPEROS_CONF");
    FILE *f = fopen(conf ? conf : "/etc/fliperos/fliperos.conf", "r");
    char line[256];
    size_t used = 0;
    while (f && fgets(line, sizeof(line), f)) {
        size_t n = strlen(line);
        if ((strncmp(line, "deflicker", 9) && strncmp(line, "color_", 6)) || used + n + 1 >= sizeof(conf_lines))
            continue;
        memcpy(conf_lines + used, line, n);
        used += n;
        if (line[n - 1] != '\n')
            conf_lines[used++] = '\n';
    }
    conf_lines[used] = 0;
    if (f)
        fclose(f);
}

/* conf_value CHAVE: o valor da ultima linha "CHAVE=valor" em out; 0 se nao
 * houver a chave. */
static int conf_value(const char *key, char *out, size_t size)
{
    size_t k = strlen(key);
    int found = 0;
    for (const char *p = conf_lines; *p;) {
        const char *end = strchr(p, '\n');
        if (!strncmp(p, key, k) && p[k] == '=') {
            sscanf(p + k + 1, "%31s", out);
            out[size - 1] = 0;
            found = 1;
        }
        p = end ? end + 1 : p + strlen(p);
    }
    return found;
}

static char app[64], core[64];

/* O core do RetroArch carregado agora (o ultimo *_libretro.so). */
static int find_core(struct dl_phdr_info *info, size_t size, void *data)
{
    (void)size;
    const char *name = info->dlpi_name, *base, *end;
    if (!name || !(end = strstr(name, "_libretro.so")))
        return 0;
    base = strrchr(name, '/');
    base = base ? base + 1 : name;
    if (end > base && (size_t)(end - base) < sizeof(core)) {
        memcpy(data, base, (size_t)(end - base));
        ((char *)data)[end - base] = 0;
    }
    return 0;
}

static void read_level(void)
{
    char value[32] = "medium", key[96];
    const char *file = getenv("FLIPEROS_DEFLICKER_FILE");
    const char *env = getenv("FLIPEROS_DEFLICKER");
    FILE *f = file ? fopen(file, "r") : NULL;
    if (f && fscanf(f, "%31s", value) == 1) {
        /* o preview */
    } else if (env) {
        snprintf(value, sizeof(value), "%s", env);
    } else {
        int found = 0;
        if (core[0]) {
            snprintf(key, sizeof(key), "deflicker_%s", core);
            found = conf_value(key, value, sizeof(value));
        }
        if (!found && app[0]) {
            snprintf(key, sizeof(key), "deflicker_%s", app);
            found = conf_value(key, value, sizeof(value));
        }
        if (!found)
            conf_value("deflicker", value, sizeof(value));
    }
    if (f)
        fclose(f);
    for (char *c = value; *c; c++)
        *c = (char)tolower((unsigned char)*c);
    level_off = 0;
    weights[0] = 0.5f, weights[1] = 0.5f, weights[2] = 0.0f;
    if (!strcmp(value, "off") || !strcmp(value, "0")) {
        level_off = 1;
    } else if (!strcmp(value, "light")) {
        weights[0] = 0.15f, weights[1] = 0.70f, weights[2] = 0.15f;
    } else if (!strcmp(value, "strong")) {
        weights[0] = 0.33f, weights[1] = 0.34f, weights[2] = 0.33f;
    }
    if (getenv("FLIPEROS_DEFLICKER_DEBUG"))
        fprintf(stderr, "fliperos-deflicker: level %s (program %s, core %s)\n", value, app[0] ? app : "-",
                core[0] ? core : "-");
}

/* A matriz da saturacao e do matiz (por coluna, como o glUniformMatrix3fv
 * quer), a mesma do config/fliperos-color.c: as do filtro do CSS
 * (saturate, hue-rotate), que mantem a luminancia. */
static float matrix[9] = {1, 0, 0, 0, 1, 0, 0, 0, 1};
static int matrix_on;

static void read_matrix(void)
{
    char value[32];
    int sat = 100, hue = 0, sw = 0;
    const char *file = getenv("FLIPEROS_COLOR_FILE");
    if (file) {
        FILE *f = fopen(file, "r");
        char line[128];
        while (f && fgets(line, sizeof(line), f)) {
            sscanf(line, "color_saturation=%d", &sat);
            sscanf(line, "color_hue=%d", &hue);
        }
        if (f)
            fclose(f);
        sw = 1;
    } else {
        if (conf_value("color_ctm", value, sizeof(value)))
            sw = !strcmp(value, "sw");
        if (conf_value("color_saturation", value, sizeof(value)))
            sat = atoi(value);
        if (conf_value("color_hue", value, sizeof(value)))
            hue = atoi(value);
    }
    sat = sat < 0 ? 0 : sat > 200 ? 200 : sat;
    hue = hue < -180 ? -180 : hue > 180 ? 180 : hue;
    matrix_on = sw && (sat != 100 || hue != 0);
    const double lr = 0.213, lg = 0.715, lb = 0.072;
    double s = sat / 100.0, a = hue * M_PI / 180.0, cs = cos(a), sn = sin(a);
    double st[9] = {lr + (1 - lr) * s, lg - lg * s, lb - lb * s,
                    lr - lr * s, lg + (1 - lg) * s, lb - lb * s,
                    lr - lr * s, lg - lg * s, lb + (1 - lb) * s};
    double hu[9] = {lr + cs * (1 - lr) - sn * lr, lg - cs * lg - sn * lg, lb - cs * lb + sn * (1 - lb),
                    lr - cs * lr + sn * 0.143, lg + cs * (1 - lg) + sn * 0.140, lb - cs * lb - sn * 0.283,
                    lr - cs * lr - sn * (1 - lr), lg - cs * lg + sn * lg, lb + cs * (1 - lb) + sn * lb};
    for (int i = 0; i < 3; i++)
        for (int j = 0; j < 3; j++) {
            double v = 0;
            for (int k = 0; k < 3; k++)
                v += hu[i * 3 + k] * st[k * 3 + j];
            matrix[j * 3 + i] = (float)v;
        }
}

/* interlaced: o modo ativo de alguma saida e entrelacado? Pergunta ao DRM
 * a cada 30 quadros (o RetroArch troca de modo no meio do jogo). Ler os
 * modos nao precisa ser o dono da tela. */
static int interlaced(void)
{
    static int fd = -2, frames, state;
    if (forced)
        return 1;
    if (frames++ % 30)
        return state;
    if (fd == -2) {
        const char *card = getenv("FLIPEROS_DRM_CARD");
        fd = open(card ? card : "/dev/dri/card0", O_RDWR | O_CLOEXEC);
    }
    state = 0;
    if (fd < 0)
        return 0;
    drmModeResPtr res = drmModeGetResources(fd);
    for (int i = 0; res && i < res->count_crtcs && !state; i++) {
        drmModeCrtcPtr crtc = drmModeGetCrtc(fd, res->crtcs[i]);
        if (crtc && crtc->mode_valid && (crtc->mode.flags & DRM_MODE_FLAG_INTERLACE))
            state = 1;
        drmModeFreeCrtc(crtc);
    }
    drmModeFreeResources(res);
    return state;
}

/* ── O filtro (OpenGL) ──────────────────────────────────────────── */

typedef void *(*getproc_fn)(const char *);

/* Os ponteiros com o tipo do proprio prototipo (GL_GLEXT_PROTOTYPES): o
 * glext.h nao tem os tipos PFN das funcoes do OpenGL 1.x. Nada e ligado na
 * libGL: cada funcao vem do GetProcAddress do contexto do programa. */
#define F(name) __typeof__(&gl##name) name;
static struct {
    F(GetIntegerv) F(GetString) F(IsEnabled) F(Enable) F(Disable) F(Viewport) F(ColorMask) F(GetBooleanv)
    F(ActiveTexture) F(BindTexture) F(GenTextures) F(TexImage2D) F(TexParameteri) F(CopyTexSubImage2D)
    F(BindFramebuffer) F(ReadBuffer) F(DrawBuffer) F(UseProgram) F(CreateShader) F(ShaderSource)
    F(CompileShader) F(GetShaderiv) F(CreateProgram) F(AttachShader) F(LinkProgram) F(GetProgramiv)
    F(GetUniformLocation) F(Uniform1i) F(Uniform3f) F(GenVertexArrays) F(BindVertexArray) F(BindSampler)
    F(DrawArrays) F(UniformMatrix3fv)
} gl;
#undef F

/* Os recursos de cada contexto do programa (quase sempre um). */
#define CONTEXTS 8
static struct ctx {
    void *id;
    int broken;
    GLuint prog, tex, vao;
    GLint u_tex, u_w, u_m;
    int tw, th;
    int gles, core;
    int tw_logged;
} ctxs[CONTEXTS];

static int load_gl(getproc_fn get)
{
#define L(name) (gl.name = (void *)get("gl" #name))
    L(GetIntegerv); L(GetString); L(IsEnabled); L(Enable); L(Disable); L(Viewport); L(ColorMask);
    L(GetBooleanv); L(ActiveTexture); L(BindTexture); L(GenTextures); L(TexImage2D); L(TexParameteri);
    L(CopyTexSubImage2D); L(BindFramebuffer); L(ReadBuffer); L(DrawBuffer); L(UseProgram);
    L(CreateShader); L(ShaderSource); L(CompileShader); L(GetShaderiv); L(CreateProgram);
    L(AttachShader); L(LinkProgram); L(GetProgramiv); L(GetUniformLocation); L(Uniform1i);
    L(Uniform3f); L(GenVertexArrays); L(BindVertexArray); L(BindSampler); L(DrawArrays); L(UniformMatrix3fv);
#undef L
    return gl.GetIntegerv && gl.GetString && gl.CopyTexSubImage2D && gl.CreateShader && gl.DrawArrays &&
           gl.BindFramebuffer && gl.UseProgram && gl.Uniform3f && gl.UniformMatrix3fv;
}

/* As tres linhas: a de cima (y+1 no OpenGL, que conta de baixo), a propria
 * e a de baixo, pelos pesos. */
static const char *frag_body =
    "void main() {\n"
    "    ivec2 p = ivec2(gl_FragCoord.xy);\n"
    "    int top = textureSize(tex, 0).y - 1;\n"
    "    vec4 up = texelFetch(tex, ivec2(p.x, min(p.y + 1, top)), 0);\n"
    "    vec4 mid = texelFetch(tex, p, 0);\n"
    "    vec4 down = texelFetch(tex, ivec2(p.x, max(p.y - 1, 0)), 0);\n"
    "    vec4 c = up * w.x + mid * w.y + down * w.z;\n"
    "    OUT = vec4(clamp(m * c.rgb, 0.0, 1.0), c.a);\n"
    "}\n";

static GLuint shader(GLenum type, const char *head, const char *body)
{
    const char *src[2] = {head, body};
    GLuint s = gl.CreateShader(type);
    GLint ok = 0;
    gl.ShaderSource(s, 2, src, NULL);
    gl.CompileShader(s);
    gl.GetShaderiv(s, GL_COMPILE_STATUS, &ok);
    return ok ? s : 0;
}

static int setup(struct ctx *c)
{
    const char *version = (const char *)gl.GetString(GL_VERSION);
    const char *vhead, *fhead;
    GLint profile = 0, major = 0;
    c->gles = version && strstr(version, "OpenGL ES") != NULL;
    gl.GetIntegerv(GL_MAJOR_VERSION, &major);
    if (!c->gles && major >= 3) {
        gl.GetIntegerv(GL_CONTEXT_PROFILE_MASK, &profile);
        c->core = (profile & GL_CONTEXT_CORE_PROFILE_BIT) != 0;
    }
    if (major < 3) {
        log_once("OpenGL 3.0 or newer is needed; filter off for this program");
        return 0;
    }
    if (c->gles) {
        vhead = "#version 300 es\n";
        fhead = "#version 300 es\nprecision highp float;\nuniform highp sampler2D tex;\nuniform vec3 w;\n"
                "uniform mat3 m;\nout vec4 color;\n#define OUT color\n";
    } else if (c->core) {
        vhead = "#version 150\n";
        fhead = "#version 150\nuniform sampler2D tex;\nuniform vec3 w;\nuniform mat3 m;\nout vec4 color;\n"
                "#define OUT color\n";
    } else {
        vhead = "#version 130\n";
        fhead = "#version 130\nuniform sampler2D tex;\nuniform vec3 w;\nuniform mat3 m;\n#define OUT gl_FragColor\n";
    }
    GLuint vs = shader(GL_VERTEX_SHADER, vhead,
                       "void main() {\n"
                       "    vec2 p = vec2(gl_VertexID == 1 ? 3.0 : -1.0, gl_VertexID == 2 ? 3.0 : -1.0);\n"
                       "    gl_Position = vec4(p, 0.0, 1.0);\n"
                       "}\n");
    GLuint fs = shader(GL_FRAGMENT_SHADER, fhead, frag_body);
    GLint ok = 0;
    if (!vs || !fs) {
        log_once("the filter shader did not compile; filter off for this program");
        return 0;
    }
    c->prog = gl.CreateProgram();
    gl.AttachShader(c->prog, vs);
    gl.AttachShader(c->prog, fs);
    gl.LinkProgram(c->prog);
    gl.GetProgramiv(c->prog, GL_LINK_STATUS, &ok);
    if (!ok) {
        log_once("the filter shader did not link; filter off for this program");
        return 0;
    }
    c->u_tex = gl.GetUniformLocation(c->prog, "tex");
    c->u_w = gl.GetUniformLocation(c->prog, "w");
    c->u_m = gl.GetUniformLocation(c->prog, "m");
    gl.GenTextures(1, &c->tex);
    if (gl.GenVertexArrays)
        gl.GenVertexArrays(1, &c->vao);
    return 1;
}

static struct ctx *context(void *id)
{
    struct ctx *free_slot = NULL;
    for (int i = 0; i < CONTEXTS; i++) {
        if (ctxs[i].id == id)
            return &ctxs[i];
        if (!ctxs[i].id && !free_slot)
            free_slot = &ctxs[i];
    }
    if (!free_slot)
        free_slot = &ctxs[0];
    memset(free_slot, 0, sizeof(*free_slot));
    free_slot->id = id;
    return free_slot;
}

/* filter: a imagem do quadro (o back buffer, LARGURA x ALTURA) passa pelo
 * filtro, no proprio back buffer: as tres linhas com o modo entrelacado
 * (deflick), so a propria linha sem ele (a matriz de cor sozinha). */
static void filter(void *ctx_id, getproc_fn get, int w, int h, int deflick)
{
    static int loaded = -1;
    struct ctx *c;
    if (loaded < 0)
        loaded = load_gl(get);
    if (!loaded || !ctx_id || w <= 0 || h <= 0)
        return;
    c = context(ctx_id);
    if (c->broken)
        return;
    if (!c->prog && !setup(c)) {
        c->broken = 1;
        return;
    }

    /* O estado do programa, para devolver. */
    GLint prog, vao = 0, draw_fb, read_fb, active, tex, sampler = 0, viewport[4], read_buf = 0, draw_buf = 0;
    GLboolean mask[4];
    GLenum caps[] = {GL_BLEND, GL_DEPTH_TEST, GL_STENCIL_TEST, GL_SCISSOR_TEST, GL_CULL_FACE,
                     GL_FRAMEBUFFER_SRGB, GL_RASTERIZER_DISCARD};
    GLboolean on[sizeof(caps) / sizeof(caps[0])];
    int ncaps = c->gles ? 5 : (int)(sizeof(caps) / sizeof(caps[0]));
    gl.GetIntegerv(GL_CURRENT_PROGRAM, &prog);
    if (gl.BindVertexArray)
        gl.GetIntegerv(GL_VERTEX_ARRAY_BINDING, &vao);
    gl.GetIntegerv(GL_DRAW_FRAMEBUFFER_BINDING, &draw_fb);
    gl.GetIntegerv(GL_READ_FRAMEBUFFER_BINDING, &read_fb);
    gl.GetIntegerv(GL_ACTIVE_TEXTURE, &active);
    gl.ActiveTexture(GL_TEXTURE0);
    gl.GetIntegerv(GL_TEXTURE_BINDING_2D, &tex);
    if (gl.BindSampler)
        gl.GetIntegerv(GL_SAMPLER_BINDING, &sampler);
    gl.GetIntegerv(GL_VIEWPORT, viewport);
    gl.GetBooleanv(GL_COLOR_WRITEMASK, mask);
    for (int i = 0; i < ncaps; i++)
        on[i] = gl.IsEnabled(caps[i]);

    gl.BindFramebuffer(GL_READ_FRAMEBUFFER, 0);
    gl.BindFramebuffer(GL_DRAW_FRAMEBUFFER, 0);
    if (!c->gles) {
        gl.GetIntegerv(GL_READ_BUFFER, &read_buf);
        gl.GetIntegerv(GL_DRAW_BUFFER, &draw_buf);
        gl.ReadBuffer(GL_BACK);
        gl.DrawBuffer(GL_BACK);
    }

    /* A imagem numa textura do tamanho do quadro. */
    gl.BindTexture(GL_TEXTURE_2D, c->tex);
    if (c->tw != w || c->th != h) {
        /* RGB: no OpenGL ES, um framebuffer sem alfa nao copia numa
         * textura com alfa. */
        gl.TexImage2D(GL_TEXTURE_2D, 0, GL_RGB8, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, NULL);
        gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST);
        gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST);
        gl.TexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAX_LEVEL, 0);
        c->tw = w, c->th = h;
    }
    gl.CopyTexSubImage2D(GL_TEXTURE_2D, 0, 0, 0, 0, 0, w, h);
    if (gl.BindSampler)
        gl.BindSampler(0, 0);

    for (int i = 0; i < ncaps; i++)
        gl.Disable(caps[i]);
    gl.ColorMask(GL_TRUE, GL_TRUE, GL_TRUE, GL_TRUE);
    gl.Viewport(0, 0, w, h);
    gl.UseProgram(c->prog);
    gl.Uniform1i(c->u_tex, 0);
    if (deflick)
        gl.Uniform3f(c->u_w, weights[0], weights[1], weights[2]);
    else
        gl.Uniform3f(c->u_w, 0.0f, 1.0f, 0.0f);
    gl.UniformMatrix3fv(c->u_m, 1, GL_FALSE, matrix);
    if (c->vao)
        gl.BindVertexArray(c->vao);
    gl.DrawArrays(GL_TRIANGLES, 0, 3);
    if (!c->tw_logged && getenv("FLIPEROS_DEFLICKER_DEBUG")) {
        fprintf(stderr, "fliperos-deflicker: filtering %dx%d (%s)\n", w, h,
                c->gles ? "GLES" : c->core ? "core" : "compat");
        c->tw_logged = 1;
    }

    /* De volta como estava. */
    if (gl.BindVertexArray)
        gl.BindVertexArray((GLuint)vao);
    gl.UseProgram((GLuint)prog);
    gl.BindTexture(GL_TEXTURE_2D, (GLuint)tex);
    if (gl.BindSampler)
        gl.BindSampler(0, (GLuint)sampler);
    gl.ActiveTexture((GLenum)active);
    gl.Viewport(viewport[0], viewport[1], viewport[2], viewport[3]);
    gl.ColorMask(mask[0], mask[1], mask[2], mask[3]);
    for (int i = 0; i < ncaps; i++)
        if (on[i])
            gl.Enable(caps[i]);
    if (!c->gles) {
        gl.ReadBuffer((GLenum)read_buf);
        gl.DrawBuffer((GLenum)draw_buf);
    }
    gl.BindFramebuffer(GL_READ_FRAMEBUFFER, (GLuint)read_fb);
    gl.BindFramebuffer(GL_DRAW_FRAMEBUFFER, (GLuint)draw_fb);
}

/* active: o que fazer neste quadro: 1 = o filtro de flicker, 2 = a matriz
 * de cor (0 = nada). A cada 30 quadros confere se o core do RetroArch mudou
 * (o nivel pode ser outro) e rele os arquivos do preview e do calibrador. */
static int active(void)
{
    static int init, frames;
    if (!init) {
        const char *env = getenv("FLIPEROS_DEFLICKER_APP");
        snprintf(app, sizeof(app), "%s", env && *env ? env : program_invocation_short_name);
        load_conf();
        env = getenv("FLIPEROS_DEFLICKER_FORCE");
        forced = env && *env == '1';
        dl_iterate_phdr(find_core, core);
        read_level();
        read_matrix();
        init = 1;
    } else if (!(++frames % 30)) {
        char now[sizeof(core)] = "";
        dl_iterate_phdr(find_core, now);
        if (strcmp(now, core) || getenv("FLIPEROS_DEFLICKER_FILE")) {
            memcpy(core, now, sizeof(core));
            read_level();
        }
        if (getenv("FLIPEROS_COLOR_FILE"))
            read_matrix();
    }
    return (!level_off && interlaced() ? 1 : 0) | (matrix_on ? 2 : 0);
}

/* ── As trocas de quadro ────────────────────────────────────────── */

static void *glx_getproc(const char *name)
{
    static void *(*get)(const GLubyte *);
    if (!get)
        get = sym("glXGetProcAddressARB");
    return get ? get((const GLubyte *)name) : NULL;
}

static void *egl_getproc(const char *name)
{
    static void *(*get)(const char *);
    if (!get)
        get = sym("eglGetProcAddress");
    void *p = get ? get(name) : NULL;
    return p ? p : sym(name);
}

void glXSwapBuffers(Display *dpy, GLXDrawable drawable)
{
    static void (*real)(Display *, GLXDrawable);
    if (!real)
        real = sym("glXSwapBuffers");
    int what = active();
    if (what) {
        static GLXContext (*current)(void);
        static void (*query)(Display *, GLXDrawable, int, unsigned int *);
        unsigned int w = 0, h = 0;
        if (!current)
            current = sym("glXGetCurrentContext");
        if (!query)
            query = sym("glXQueryDrawable");
        if (current && query) {
            query(dpy, drawable, GLX_WIDTH, &w);
            query(dpy, drawable, GLX_HEIGHT, &h);
            filter((void *)current(), glx_getproc, (int)w, (int)h, what & 1);
        }
    }
    if (real)
        real(dpy, drawable);
}

EGLBoolean eglSwapBuffers(EGLDisplay dpy, EGLSurface surface)
{
    static EGLBoolean (*real)(EGLDisplay, EGLSurface);
    if (!real)
        real = sym("eglSwapBuffers");
    int what = active();
    if (what) {
        static EGLContext (*current)(void);
        static EGLBoolean (*query)(EGLDisplay, EGLSurface, EGLint, EGLint *);
        EGLint w = 0, h = 0;
        if (!current)
            current = sym("eglGetCurrentContext");
        if (!query)
            query = sym("eglQuerySurface");
        if (current && query && query(dpy, surface, EGL_WIDTH, &w) && query(dpy, surface, EGL_HEIGHT, &h))
            filter((void *)current(), egl_getproc, (int)w, (int)h, what & 1);
    }
    return real ? real(dpy, surface) : EGL_FALSE;
}

/* Quem pede a troca de quadro pelo nome ganha a desta biblioteca. */
static void *hook(const char *name)
{
    if (!name)
        return NULL;
    if (!strcmp(name, "glXSwapBuffers"))
        return (void *)glXSwapBuffers;
    if (!strcmp(name, "eglSwapBuffers"))
        return (void *)eglSwapBuffers;
    return NULL;
}

__GLXextFuncPtr glXGetProcAddressARB(const GLubyte *name)
{
    static __GLXextFuncPtr (*real)(const GLubyte *);
    void *h = hook((const char *)name);
    if (h)
        return (__GLXextFuncPtr)h;
    if (!real)
        real = sym("glXGetProcAddressARB");
    return real ? real(name) : NULL;
}

__GLXextFuncPtr glXGetProcAddress(const GLubyte *name)
{
    return glXGetProcAddressARB(name);
}

__eglMustCastToProperFunctionPointerType eglGetProcAddress(const char *name)
{
    static __eglMustCastToProperFunctionPointerType (*real)(const char *);
    void *h = hook(name);
    if (h)
        return (__eglMustCastToProperFunctionPointerType)h;
    if (!real)
        real = sym("eglGetProcAddress");
    return real ? real(name) : NULL;
}

void *dlsym(void *handle, const char *name)
{
    void *h = hook(name);
    if (h)
        return h;
    if (!strcmp(name, "glXGetProcAddressARB"))
        return (void *)glXGetProcAddressARB;
    if (!strcmp(name, "glXGetProcAddress"))
        return (void *)glXGetProcAddress;
    if (!strcmp(name, "eglGetProcAddress"))
        return (void *)eglGetProcAddress;
    return real_dlsym()(handle, name);
}
