/*
 * O filtro de flicker da camada do Vulkan (config/fliperos-vkfps.c): uma
 * janela em Vulkan, com listras de uma linha, e o que chega ao X. Num Xvfb com
 * o lavapipe, por tools/deflicker-test.sh.
 *
 *   vkfps_test VALOR_ESPERADO_DA_LINHA_CLARA VALOR_ESPERADO_DA_LINHA_ESCURA
 *
 * Linhas pares brancas, impares pretas. Sem filtro: 255 e 0. Com o medium (a
 * media com a linha de cima): 127 ou 128 nas duas. O programa nao sabe da
 * camada, como um emulador. Sai 0 se bate (com folga de 2 valores).
 */
#define VK_USE_PLATFORM_XLIB_KHR
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <vulkan/vulkan.h>
#include <X11/Xlib.h>
#include <X11/Xutil.h>

#define W 320
#define H 240
#define CHECK(x) do { VkResult r_ = (x); if (r_ != VK_SUCCESS) { fprintf(stderr, "%s: %d\n", #x, r_); exit(2); } } while (0)

int main(int argc, char **argv)
{
    int want_light = argc > 1 ? atoi(argv[1]) : 255, want_dark = argc > 2 ? atoi(argv[2]) : 0;
    Display *dpy = XOpenDisplay(NULL);
    if (!dpy)
        return 3;
    Window win = XCreateSimpleWindow(dpy, DefaultRootWindow(dpy), 0, 0, W, H, 0, 0, 0);
    XMapWindow(dpy, win);
    XSync(dpy, False);

    const char *instance_ext[] = {VK_KHR_SURFACE_EXTENSION_NAME, VK_KHR_XLIB_SURFACE_EXTENSION_NAME};
    VkApplicationInfo app = {VK_STRUCTURE_TYPE_APPLICATION_INFO, .apiVersion = VK_API_VERSION_1_1};
    VkInstanceCreateInfo ici = {VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo = &app,
                                .enabledExtensionCount = 2, .ppEnabledExtensionNames = instance_ext};
    VkInstance instance;
    CHECK(vkCreateInstance(&ici, NULL, &instance));
    VkXlibSurfaceCreateInfoKHR sci = {VK_STRUCTURE_TYPE_XLIB_SURFACE_CREATE_INFO_KHR, .dpy = dpy, .window = win};
    VkSurfaceKHR surface;
    CHECK(vkCreateXlibSurfaceKHR(instance, &sci, NULL, &surface));
    uint32_t n = 1;
    VkPhysicalDevice gpu;
    vkEnumeratePhysicalDevices(instance, &n, &gpu);
    float priority = 1;
    VkDeviceQueueCreateInfo qci = {VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO, .queueFamilyIndex = 0, .queueCount = 1,
                                   .pQueuePriorities = &priority};
    const char *device_ext[] = {VK_KHR_SWAPCHAIN_EXTENSION_NAME};
    VkDeviceCreateInfo dci = {VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO, .queueCreateInfoCount = 1, .pQueueCreateInfos = &qci,
                              .enabledExtensionCount = 1, .ppEnabledExtensionNames = device_ext};
    VkDevice device;
    CHECK(vkCreateDevice(gpu, &dci, NULL, &device));
    VkQueue queue;
    vkGetDeviceQueue(device, 0, 0, &queue);

    VkSurfaceFormatKHR formats[32];
    n = 32;
    vkGetPhysicalDeviceSurfaceFormatsKHR(gpu, surface, &n, formats);
    VkFormat format = VK_FORMAT_UNDEFINED;
    for (uint32_t i = 0; i < n; i++)
        if (formats[i].format == VK_FORMAT_B8G8R8A8_UNORM)
            format = formats[i].format;
    if (format == VK_FORMAT_UNDEFINED)
        return 4;
    VkSwapchainCreateInfoKHR swci = {VK_STRUCTURE_TYPE_SWAPCHAIN_CREATE_INFO_KHR, .surface = surface, .minImageCount = 3,
                                     .imageFormat = format, .imageColorSpace = VK_COLOR_SPACE_SRGB_NONLINEAR_KHR,
                                     .imageExtent = {W, H}, .imageArrayLayers = 1,
                                     /* Como um emulador: so o que ele usa. A camada pede o resto. */
                                     .imageUsage = VK_IMAGE_USAGE_TRANSFER_DST_BIT,
                                     .preTransform = VK_SURFACE_TRANSFORM_IDENTITY_BIT_KHR,
                                     .compositeAlpha = VK_COMPOSITE_ALPHA_OPAQUE_BIT_KHR,
                                     .presentMode = VK_PRESENT_MODE_FIFO_KHR, .clipped = VK_TRUE};
    VkSwapchainKHR swapchain;
    CHECK(vkCreateSwapchainKHR(device, &swci, NULL, &swapchain));
    VkImage images[16];
    n = 16;
    CHECK(vkGetSwapchainImagesKHR(device, swapchain, &n, images));

    /* As listras num buffer. */
    VkBufferCreateInfo bci = {VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO, .size = W * H * 4, .usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT};
    VkBuffer buffer;
    CHECK(vkCreateBuffer(device, &bci, NULL, &buffer));
    VkMemoryRequirements req;
    vkGetBufferMemoryRequirements(device, buffer, &req);
    VkPhysicalDeviceMemoryProperties props;
    vkGetPhysicalDeviceMemoryProperties(gpu, &props);
    uint32_t type = 0;
    for (uint32_t i = 0; i < props.memoryTypeCount; i++)
        if ((req.memoryTypeBits & (1u << i)) && (props.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT) &&
            (props.memoryTypes[i].propertyFlags & VK_MEMORY_PROPERTY_HOST_COHERENT_BIT)) {
            type = i;
            break;
        }
    VkMemoryAllocateInfo mai = {VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO, .allocationSize = req.size, .memoryTypeIndex = type};
    VkDeviceMemory memory;
    CHECK(vkAllocateMemory(device, &mai, NULL, &memory));
    CHECK(vkBindBufferMemory(device, buffer, memory, 0));
    unsigned char *pixels;
    CHECK(vkMapMemory(device, memory, 0, VK_WHOLE_SIZE, 0, (void **)&pixels));
    for (int y = 0; y < H; y++)
        memset(pixels + y * W * 4, y % 2 ? 0 : 255, W * 4);

    VkCommandPoolCreateInfo cpi = {VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO, .flags = VK_COMMAND_POOL_CREATE_RESET_COMMAND_BUFFER_BIT};
    VkCommandPool pool;
    CHECK(vkCreateCommandPool(device, &cpi, NULL, &pool));
    VkCommandBufferAllocateInfo cbi = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO, .commandPool = pool,
                                       .level = VK_COMMAND_BUFFER_LEVEL_PRIMARY, .commandBufferCount = 1};
    VkCommandBuffer cmd;
    CHECK(vkAllocateCommandBuffers(device, &cbi, &cmd));
    VkSemaphoreCreateInfo semi = {VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO};
    VkSemaphore acquired, rendered;
    CHECK(vkCreateSemaphore(device, &semi, NULL, &acquired));
    CHECK(vkCreateSemaphore(device, &semi, NULL, &rendered));
    VkFenceCreateInfo fci = {VK_STRUCTURE_TYPE_FENCE_CREATE_INFO};
    VkFence fence;
    CHECK(vkCreateFence(device, &fci, NULL, &fence));

    /* Mais quadros que imagens, para reusar cada uma, e mais de 1 s, para o FPS. */
    for (int frame = 0; frame < 45; frame++) {
        uint32_t index;
        CHECK(vkAcquireNextImageKHR(device, swapchain, UINT64_MAX, acquired, VK_NULL_HANDLE, &index));
        VkCommandBufferBeginInfo begin = {VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO, .flags = VK_COMMAND_BUFFER_USAGE_ONE_TIME_SUBMIT_BIT};
        CHECK(vkResetCommandBuffer(cmd, 0));
        CHECK(vkBeginCommandBuffer(cmd, &begin));
        VkImageSubresourceRange range = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 1, 0, 1};
        VkImageMemoryBarrier to_dst = {VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER, .dstAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT,
                                       .oldLayout = VK_IMAGE_LAYOUT_UNDEFINED, .newLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL,
                                       .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED, .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                                       .image = images[index], .subresourceRange = range};
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TOP_OF_PIPE_BIT, VK_PIPELINE_STAGE_TRANSFER_BIT, 0, 0, NULL, 0, NULL, 1, &to_dst);
        VkBufferImageCopy copy = {.imageSubresource = {VK_IMAGE_ASPECT_COLOR_BIT, 0, 0, 1}, .imageExtent = {W, H, 1}};
        vkCmdCopyBufferToImage(cmd, buffer, images[index], VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL, 1, &copy);
        VkImageMemoryBarrier to_present = to_dst;
        to_present.srcAccessMask = VK_ACCESS_TRANSFER_WRITE_BIT;
        to_present.dstAccessMask = 0;
        to_present.oldLayout = VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL;
        to_present.newLayout = VK_IMAGE_LAYOUT_PRESENT_SRC_KHR;
        vkCmdPipelineBarrier(cmd, VK_PIPELINE_STAGE_TRANSFER_BIT, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT, 0, 0, NULL, 0, NULL, 1, &to_present);
        CHECK(vkEndCommandBuffer(cmd));
        VkPipelineStageFlags stage = VK_PIPELINE_STAGE_TRANSFER_BIT;
        VkSubmitInfo submit = {VK_STRUCTURE_TYPE_SUBMIT_INFO, .waitSemaphoreCount = 1, .pWaitSemaphores = &acquired,
                               .pWaitDstStageMask = &stage, .commandBufferCount = 1, .pCommandBuffers = &cmd,
                               .signalSemaphoreCount = 1, .pSignalSemaphores = &rendered};
        CHECK(vkQueueSubmit(queue, 1, &submit, fence));
        VkPresentInfoKHR present = {VK_STRUCTURE_TYPE_PRESENT_INFO_KHR, .waitSemaphoreCount = 1, .pWaitSemaphores = &rendered,
                                    .swapchainCount = 1, .pSwapchains = &swapchain, .pImageIndices = &index};
        CHECK(vkQueuePresentKHR(queue, &present));
        CHECK(vkWaitForFences(device, 1, &fence, VK_TRUE, UINT64_MAX));
        CHECK(vkResetFences(device, 1, &fence));
        usleep(30000);
    }
    usleep(200000);
    XSync(dpy, False);

    XImage *shot = XGetImage(dpy, win, 0, 0, W, H, AllPlanes, ZPixmap);
    if (!shot)
        return 5;
    int bad = 0;
    /* A linha 0 nao tem de cima: a primeira que vale e a 2. */
    for (int y = 2; y < H - 2; y++) {
        int value = (int)(XGetPixel(shot, W / 2, y) & 0xff), want = y % 2 ? want_dark : want_light;
        if (abs(value - want) > 2) {
            if (bad++ < 4)
                fprintf(stderr, "line %d: %d, wanted %d\n", y, value, want);
        }
    }
    printf("lines 2,3: %lu %lu; wrong lines: %d\n", XGetPixel(shot, W / 2, 2) & 0xff, XGetPixel(shot, W / 2, 3) & 0xff, bad);

    /* A troca de swapchain e o fim: a camada libera o que fez. */
    vkDeviceWaitIdle(device);
    vkDestroySwapchainKHR(device, swapchain, NULL);
    vkDestroyFence(device, fence, NULL);
    vkDestroySemaphore(device, rendered, NULL);
    vkDestroySemaphore(device, acquired, NULL);
    vkDestroyCommandPool(device, pool, NULL);
    vkDestroyBuffer(device, buffer, NULL);
    vkFreeMemory(device, memory, NULL);
    vkDestroyDevice(device, NULL);
    vkDestroySurfaceKHR(instance, surface, NULL);
    vkDestroyInstance(instance, NULL);
    return bad ? 1 : 0;
}
