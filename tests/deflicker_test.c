/*
 * Teste do config/fliperos-deflicker.c (tools/deflicker-test.sh, no Xvfb
 * com o Mesa por software): desenha listras de uma linha (branca, preta,
 * branca...), troca o quadro e imprime o vermelho de algumas linhas da tela.
 *
 *   deflicker_test link|dlsym [core]
 *
 * link: chama o glXSwapBuffers ligado na libGL. dlsym: abre a libGL por
 * dlopen e pega o glXSwapBuffers por dlsym, como o SDL. core: contexto
 * OpenGL 3.3 core (o RetroArch glcore); sem, o de compatibilidade.
 */
#define GL_GLEXT_PROTOTYPES
#include <EGL/egl.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <GL/gl.h>
#include <GL/glext.h>
#include <GL/glx.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>

#define W 64
#define H 16

typedef GLXContext (*create_attribs_fn)(Display *, GLXFBConfig, GLXContext, Bool, const int *);

/* stripes: listras de uma linha, a y branca se y for par. */
static void stripes(void)
{
    glViewport(0, 0, W, H);
    glClearColor(0, 0, 0, 1);
    glClear(GL_COLOR_BUFFER_BIT);
    glEnable(GL_SCISSOR_TEST);
    glClearColor(1, 1, 1, 1);
    for (int y = 0; y < H; y += 2) {
        glScissor(0, y, W, 1);
        glClear(GL_COLOR_BUFFER_BIT);
    }
}

static int print_rows(Display *dpy, Window win)
{
    XSync(dpy, False);
    XImage *img = XGetImage(dpy, win, 0, 0, W, H, AllPlanes, ZPixmap);
    if (!img)
        return 5;
    printf("rows:");
    for (int y = H - 1; y >= 0; y--)
        printf(" %lu", (XGetPixel(img, W / 2, y) >> 16) & 0xff);
    printf("\nscissor-kept: %d\n", glIsEnabled(GL_SCISSOR_TEST));
    fflush(stdout);
    /* DEFLICKER_TEST_HOLD=SEGUNDOS: a janela fica aberta (outro programa
     * le a tela, como o compositor a pintou). */
    if (getenv("DEFLICKER_TEST_HOLD"))
        sleep((unsigned)atoi(getenv("DEFLICKER_TEST_HOLD")));
    return 0;
}

/* egl: o caminho do RetroArch (EGL, OpenGL desktop), numa janela do X. */
static int egl_test(void)
{
    Display *dpy = XOpenDisplay(NULL);
    EGLDisplay ed = eglGetDisplay((EGLNativeDisplayType)dpy);
    EGLint major, minor, n = 0;
    EGLConfig cfg;
    EGLint attrs[] = {EGL_SURFACE_TYPE, EGL_WINDOW_BIT, EGL_RED_SIZE, 8, EGL_GREEN_SIZE, 8, EGL_BLUE_SIZE, 8,
                      EGL_RENDERABLE_TYPE, EGL_OPENGL_BIT, EGL_NONE};
    if (!dpy || !eglInitialize(ed, &major, &minor) || !eglBindAPI(EGL_OPENGL_API) ||
        !eglChooseConfig(ed, attrs, &cfg, 1, &n) || !n)
        return 6;
    EGLint vid;
    eglGetConfigAttrib(ed, cfg, EGL_NATIVE_VISUAL_ID, &vid);
    XVisualInfo tmpl = {0}, *vi;
    int nv;
    tmpl.visualid = vid;
    vi = XGetVisualInfo(dpy, VisualIDMask, &tmpl, &nv);
    XSetWindowAttributes swa = {0};
    swa.colormap = XCreateColormap(dpy, DefaultRootWindow(dpy), vi->visual, AllocNone);
    Window win = XCreateWindow(dpy, DefaultRootWindow(dpy), 0, 0, W, H, 0, vi->depth, InputOutput, vi->visual,
                               CWColormap, &swa);
    XMapWindow(dpy, win);
    XSync(dpy, False);
    EGLint ca[] = {EGL_CONTEXT_MAJOR_VERSION, 3, EGL_CONTEXT_MINOR_VERSION, 3,
                   EGL_CONTEXT_OPENGL_PROFILE_MASK, EGL_CONTEXT_OPENGL_CORE_PROFILE_BIT, EGL_NONE};
    EGLContext ctx = eglCreateContext(ed, cfg, EGL_NO_CONTEXT, ca);
    EGLSurface surf = eglCreateWindowSurface(ed, cfg, (EGLNativeWindowType)win, NULL);
    if (!ctx || !surf || !eglMakeCurrent(ed, surf, surf, ctx))
        return 7;
    stripes();
    eglSwapBuffers(ed, surf);
    glFinish();
    return print_rows(dpy, win);
}

int main(int argc, char **argv)
{
    if (argc > 1 && !strcmp(argv[1], "egl"))
        return egl_test();
    int use_dlsym = argc > 1 && !strcmp(argv[1], "dlsym");
    int core = argc > 2 && !strcmp(argv[2], "core");
    Display *dpy = XOpenDisplay(NULL);
    if (!dpy)
        return 2;
    int attrs[] = {GLX_X_RENDERABLE, True, GLX_DRAWABLE_TYPE, GLX_WINDOW_BIT, GLX_RENDER_TYPE, GLX_RGBA_BIT,
                   GLX_DOUBLEBUFFER, True, GLX_RED_SIZE, 8, GLX_GREEN_SIZE, 8, GLX_BLUE_SIZE, 8, None};
    int n = 0;
    GLXFBConfig *cfg = glXChooseFBConfig(dpy, DefaultScreen(dpy), attrs, &n);
    if (!cfg || !n)
        return 3;
    XVisualInfo *vi = glXGetVisualFromFBConfig(dpy, cfg[0]);
    XSetWindowAttributes swa = {0};
    swa.colormap = XCreateColormap(dpy, RootWindow(dpy, vi->screen), vi->visual, AllocNone);
    Window win = XCreateWindow(dpy, RootWindow(dpy, vi->screen), 0, 0, W, H, 0, vi->depth, InputOutput,
                               vi->visual, CWColormap, &swa);
    XMapWindow(dpy, win);
    XSync(dpy, False);
    GLXContext ctx;
    if (core) {
        create_attribs_fn create = (create_attribs_fn)glXGetProcAddressARB(
            (const GLubyte *)"glXCreateContextAttribsARB");
        int ca[] = {GLX_CONTEXT_MAJOR_VERSION_ARB, 3, GLX_CONTEXT_MINOR_VERSION_ARB, 3,
                    GLX_CONTEXT_PROFILE_MASK_ARB, GLX_CONTEXT_CORE_PROFILE_BIT_ARB, None};
        ctx = create(dpy, cfg[0], NULL, True, ca);
    } else {
        ctx = glXCreateNewContext(dpy, cfg[0], GLX_RGBA_TYPE, NULL, True);
    }
    if (!ctx || !glXMakeCurrent(dpy, win, ctx))
        return 4;

    /* O scissor fica ligado: o estado que o filtro tem de devolver. */
    stripes();

    void (*swap)(Display *, GLXDrawable) = glXSwapBuffers;
    if (use_dlsym) {
        void *lib = dlopen("libGL.so.1", RTLD_NOW | RTLD_LOCAL);
        swap = (void (*)(Display *, GLXDrawable))dlsym(lib, "glXSwapBuffers");
    }
    swap(dpy, win);
    glFinish();
    /* O que foi para a janela, de baixo para cima (como no OpenGL). */
    return print_rows(dpy, win);
}
