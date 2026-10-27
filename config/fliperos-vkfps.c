/*
 * fliperos-vkfps: o FPS dos programas em Vulkan para o painel web
 * (config/fliperos-web).
 *
 * A camada OpenGL (config/fliperos-deflicker.c) conta as trocas de quadro do
 * OpenGL; um emulador em Vulkan (o Flycast, o PCSX2, o Dolphin e o
 * DuckStation no amdgpu) nao passa por ela, e o painel ficava sem o FPS.
 * Esta e uma camada implicita do Vulkan (config/fliperos-vkfps.json, em
 * /usr/share/vulkan/implicit_layer.d): o carregador do Vulkan a poe em todo
 * programa aberto com FLIPEROS_VK_FPS=1 (o fliperos-kms-run e o
 * fliperos-x11-client ligam), e ela conta os vkQueuePresentKHR.
 *
 * A cada segundo grava $XDG_RUNTIME_DIR/fliperos-fps (FLIPEROS_FPS_FILE
 * troca o arquivo) na mesma linha da camada OpenGL, "pid fps programa - 0";
 * o programa e o FLIPEROS_DEFLICKER_APP (o nome na tabela do
 * fliperos-x11-run) ou o do processo.
 *
 * Os poucos tipos do Vulkan que ela usa estao aqui: compila so com o gcc e a
 * libc (o libvulkan-dev nao vem na imagem nem no gabinete).
 */
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

typedef int32_t VkResult;
typedef uint32_t VkStructureType;
typedef void (*PFN_vkVoidFunction)(void);
typedef struct VkInstance_T *VkInstance;
typedef struct VkPhysicalDevice_T *VkPhysicalDevice;
typedef struct VkDevice_T *VkDevice;
typedef struct VkQueue_T *VkQueue;
typedef PFN_vkVoidFunction (*PFN_vkGetInstanceProcAddr)(VkInstance, const char *);
typedef PFN_vkVoidFunction (*PFN_vkGetDeviceProcAddr)(VkDevice, const char *);
typedef VkResult (*PFN_vkCreateInstance)(const void *, const void *, VkInstance *);
typedef VkResult (*PFN_vkCreateDevice)(VkPhysicalDevice, const void *, const void *, VkDevice *);
typedef VkResult (*PFN_vkQueuePresentKHR)(VkQueue, const void *);

#define VK_SUCCESS 0
#define VK_ERROR_INITIALIZATION_FAILED (-3)
#define VK_ERROR_DEVICE_LOST (-4)
/* O elo da cadeia de camadas que o carregador poe no pNext do
 * VkInstanceCreateInfo e do VkDeviceCreateInfo (vk_layer.h). */
#define VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO 47
#define VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO 48
#define VK_LAYER_LINK_INFO 0

typedef struct {
    VkStructureType sType;
    const void *pNext;
} Base;

typedef struct InstanceLink {
    struct InstanceLink *pNext;
    PFN_vkGetInstanceProcAddr pfnNextGetInstanceProcAddr;
    PFN_vkVoidFunction pfnNextGetPhysicalDeviceProcAddr;
} InstanceLink;

typedef struct DeviceLink {
    struct DeviceLink *pNext;
    PFN_vkGetInstanceProcAddr pfnNextGetInstanceProcAddr;
    PFN_vkGetDeviceProcAddr pfnNextGetDeviceProcAddr;
} DeviceLink;

/* VkLayerInstanceCreateInfo e VkLayerDeviceCreateInfo: o union comeca com o
 * ponteiro do elo. */
typedef struct {
    VkStructureType sType;
    const void *pNext;
    int function;
    void *link;
} LayerCreateInfo;

#define API __attribute__((visibility("default")))
#define SLOTS 32

/* O que vem depois desta camada, pela chave de despacho do objeto (o
 * primeiro ponteiro dele: a mesma na instancia e nas placas dela, e no
 * device e nas filas dele). */
static struct {
    void *key;
    VkInstance instance;
    PFN_vkGetInstanceProcAddr gipa;
} instances[SLOTS];
static struct {
    void *key;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkQueuePresentKHR present;
} devices[SLOTS];
static unsigned next_instance, next_device;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

static void *key_of(const void *handle)
{
    return handle ? *(void *const *)handle : NULL;
}

static LayerCreateInfo *link_info(const void *create_info, VkStructureType type)
{
    LayerCreateInfo *info = (LayerCreateInfo *)((const Base *)create_info)->pNext;
    while (info && !(info->sType == type && info->function == VK_LAYER_LINK_INFO))
        info = (LayerCreateInfo *)info->pNext;
    return info && info->link ? info : NULL;
}

static int instance_slot(void *key)
{
    for (int i = 0; i < SLOTS; i++)
        if (instances[i].key == key)
            return i;
    return -1;
}

static int device_slot(void *key)
{
    for (int i = 0; i < SLOTS; i++)
        if (devices[i].key == key)
            return i;
    return -1;
}

/* fps_tick: as trocas de quadro de cada segundo, gravadas a cada segundo. */
static void fps_tick(void)
{
    static double start;
    static int count, disabled;
    static char path[256], app[64];
    struct timespec ts;
    pthread_mutex_lock(&lock);
    if (disabled) {
        pthread_mutex_unlock(&lock);
        return;
    }
    clock_gettime(CLOCK_MONOTONIC, &ts);
    double now = (double)ts.tv_sec + ts.tv_nsec / 1e9;
    if (!path[0]) {
        const char *file = getenv("FLIPEROS_FPS_FILE"), *dir = getenv("XDG_RUNTIME_DIR");
        const char *name = getenv("FLIPEROS_DEFLICKER_APP");
        if (file && *file)
            snprintf(path, sizeof(path), "%s", file);
        else if (dir && *dir)
            snprintf(path, sizeof(path), "%s/fliperos-fps", dir);
        else {
            disabled = 1;
            pthread_mutex_unlock(&lock);
            return;
        }
        snprintf(app, sizeof(app), "%s", name && *name ? name : program_invocation_short_name);
        start = now;
    }
    count++;
    if (now - start >= 1.0) {
        char tmp[300];
        snprintf(tmp, sizeof(tmp), "%s.%d", path, (int)getpid());
        FILE *f = fopen(tmp, "w");
        if (f) {
            fprintf(f, "%d %.1f %s - 0\n", (int)getpid(), count / (now - start), app);
            fclose(f);
            if (rename(tmp, path))
                unlink(tmp);
        }
        count = 0;
        start = now;
    }
    pthread_mutex_unlock(&lock);
}

static VkResult layer_CreateInstance(const void *create_info, const void *alloc, VkInstance *instance)
{
    LayerCreateInfo *info = link_info(create_info, VK_STRUCTURE_TYPE_LOADER_INSTANCE_CREATE_INFO);
    if (!info)
        return VK_ERROR_INITIALIZATION_FAILED;
    InstanceLink *link = info->link;
    PFN_vkGetInstanceProcAddr gipa = link->pfnNextGetInstanceProcAddr;
    /* A proxima camada acha o elo dela. */
    info->link = link->pNext;
    PFN_vkCreateInstance create = (PFN_vkCreateInstance)gipa(NULL, "vkCreateInstance");
    if (!create)
        return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = create(create_info, alloc, instance);
    if (result == VK_SUCCESS) {
        pthread_mutex_lock(&lock);
        int i = instance_slot(key_of(*instance));
        if (i < 0)
            i = next_instance++ % SLOTS;
        instances[i].key = key_of(*instance);
        instances[i].instance = *instance;
        instances[i].gipa = gipa;
        pthread_mutex_unlock(&lock);
    }
    return result;
}

static VkResult layer_CreateDevice(VkPhysicalDevice gpu, const void *create_info, const void *alloc, VkDevice *device)
{
    LayerCreateInfo *info = link_info(create_info, VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO);
    if (!info)
        return VK_ERROR_INITIALIZATION_FAILED;
    DeviceLink *link = info->link;
    PFN_vkGetInstanceProcAddr gipa = link->pfnNextGetInstanceProcAddr;
    PFN_vkGetDeviceProcAddr gdpa = link->pfnNextGetDeviceProcAddr;
    info->link = link->pNext;
    /* A instancia da placa (a mesma chave): o vkCreateDevice de baixo. */
    VkInstance instance = NULL;
    pthread_mutex_lock(&lock);
    int k = instance_slot(key_of(gpu));
    if (k >= 0)
        instance = instances[k].instance;
    pthread_mutex_unlock(&lock);
    PFN_vkCreateDevice create = (PFN_vkCreateDevice)gipa(instance, "vkCreateDevice");
    if (!create)
        return VK_ERROR_INITIALIZATION_FAILED;
    VkResult result = create(gpu, create_info, alloc, device);
    if (result == VK_SUCCESS) {
        PFN_vkQueuePresentKHR present = (PFN_vkQueuePresentKHR)gdpa(*device, "vkQueuePresentKHR");
        pthread_mutex_lock(&lock);
        int i = device_slot(key_of(*device));
        if (i < 0)
            i = next_device++ % SLOTS;
        devices[i].key = key_of(*device);
        devices[i].gdpa = gdpa;
        devices[i].present = present;
        pthread_mutex_unlock(&lock);
    }
    return result;
}

static VkResult layer_QueuePresentKHR(VkQueue queue, const void *present_info)
{
    PFN_vkQueuePresentKHR present = NULL;
    pthread_mutex_lock(&lock);
    int i = device_slot(key_of(queue));
    if (i >= 0)
        present = devices[i].present;
    pthread_mutex_unlock(&lock);
    if (!present)
        return VK_ERROR_DEVICE_LOST;
    fps_tick();
    return present(queue, present_info);
}

API PFN_vkVoidFunction fliperos_vkfps_GetDeviceProcAddr(VkDevice device, const char *name);

API PFN_vkVoidFunction fliperos_vkfps_GetInstanceProcAddr(VkInstance instance, const char *name)
{
    if (!strcmp(name, "vkGetInstanceProcAddr"))
        return (PFN_vkVoidFunction)fliperos_vkfps_GetInstanceProcAddr;
    if (!strcmp(name, "vkGetDeviceProcAddr"))
        return (PFN_vkVoidFunction)fliperos_vkfps_GetDeviceProcAddr;
    if (!strcmp(name, "vkCreateInstance"))
        return (PFN_vkVoidFunction)layer_CreateInstance;
    if (!strcmp(name, "vkCreateDevice"))
        return (PFN_vkVoidFunction)layer_CreateDevice;
    if (!instance)
        return NULL;
    PFN_vkGetInstanceProcAddr gipa = NULL;
    pthread_mutex_lock(&lock);
    int i = instance_slot(key_of(instance));
    if (i >= 0)
        gipa = instances[i].gipa;
    pthread_mutex_unlock(&lock);
    return gipa ? gipa(instance, name) : NULL;
}

API PFN_vkVoidFunction fliperos_vkfps_GetDeviceProcAddr(VkDevice device, const char *name)
{
    PFN_vkGetDeviceProcAddr gdpa = NULL;
    PFN_vkQueuePresentKHR present = NULL;
    if (!strcmp(name, "vkGetDeviceProcAddr"))
        return (PFN_vkVoidFunction)fliperos_vkfps_GetDeviceProcAddr;
    pthread_mutex_lock(&lock);
    int i = device_slot(key_of(device));
    if (i >= 0) {
        gdpa = devices[i].gdpa;
        present = devices[i].present;
    }
    pthread_mutex_unlock(&lock);
    /* So com o swapchain ligado nesse device: sem ele a funcao nao existe. */
    if (!strcmp(name, "vkQueuePresentKHR"))
        return present ? (PFN_vkVoidFunction)layer_QueuePresentKHR : NULL;
    return gdpa ? gdpa(device, name) : NULL;
}
