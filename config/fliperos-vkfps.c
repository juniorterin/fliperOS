/*
 * fliperos-vkfps: a camada dos programas em Vulkan: o FPS para o painel web
 * (config/fliperos-web) e o filtro de flicker do 480i.
 *
 * A camada OpenGL (config/fliperos-deflicker.c) conta as trocas de quadro do
 * OpenGL e filtra a imagem delas; um emulador em Vulkan (o Flycast, o PCSX2, o
 * Dolphin e o DuckStation no amdgpu) nao passa por ela. Esta e uma camada
 * implicita do Vulkan (config/fliperos-vkfps.json, em
 * /usr/share/vulkan/implicit_layer.d): o carregador do Vulkan a poe em todo
 * programa aberto com FLIPEROS_VK_FPS=1 (o fliperos-kms-run e o
 * fliperos-x11-client ligam), e ela fica no vkQueuePresentKHR.
 *
 * O FPS: a cada segundo grava $XDG_RUNTIME_DIR/fliperos-fps (FLIPEROS_FPS_FILE
 * troca o arquivo) na mesma linha da camada OpenGL, "pid fps programa - filtro";
 * o programa e o FLIPEROS_DEFLICKER_APP (o nome na tabela do fliperos-x11-run)
 * ou o do processo.
 *
 * O filtro: com o modo de video da tela entrelacado (o DRM diz), antes de ir
 * para a tela a imagem e copiada e desenhada de volta pelos mesmos pesos e os
 * mesmos niveis da camada OpenGL (Setup > Video Setup > 480i hacks): do
 * FLIPEROS_DEFLICKER_FILE, do FLIPEROS_DEFLICKER, do deflicker_PROGRAMA= e do
 * deflicker= no fliperos.conf; FLIPEROS_DEFLICKER_FORCE=1 filtra sem modo
 * entrelacado. Sem filtrar nada e alocado e o quadro passa direto. A saturacao
 * e o matiz por software (color_ctm=sw) nao entram: so o radeon, que nao tem
 * Vulkan, precisa deles. Se algo falha ao preparar, o programa segue sem o
 * filtro.
 *
 * Os poucos tipos do Vulkan que ela usa estao aqui: compila so com o gcc, a
 * libc e o libdrm (o libvulkan-dev nao vem na imagem nem no gabinete).
 * tools/deflicker-test.sh confere estes tipos contra os cabecalhos de verdade
 * (FLIPEROS_VK_CHECK).
 */
#define _GNU_SOURCE
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
#include <xf86drm.h>
#include <xf86drmMode.h>

#ifdef FLIPEROS_VK_CHECK
#include <vulkan/vulkan.h>
#include <vulkan/vk_layer.h>
#endif

#ifndef VULKAN_H_
typedef int32_t VkResult;
typedef uint32_t VkStructureType;
typedef void (*PFN_vkVoidFunction)(void);
typedef struct VkInstance_T *VkInstance;
typedef struct VkPhysicalDevice_T *VkPhysicalDevice;
typedef struct VkDevice_T *VkDevice;
typedef struct VkQueue_T *VkQueue;
typedef struct VkCommandBuffer_T *VkCommandBuffer;
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
#define VK_LOADER_DATA_CALLBACK 1
#endif

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

/* ── Os tipos do filtro (vulkan_core.h) ─────────────────────────── */

/* Os objetos nao despachaveis sao 64 bits. */
typedef uint64_t Handle;

/* Os sType. */
enum {
    ST_SUBMIT_INFO = 4, ST_MEMORY_ALLOCATE_INFO = 5, ST_FENCE_CREATE_INFO = 8, ST_SEMAPHORE_CREATE_INFO = 9,
    ST_IMAGE_CREATE_INFO = 14, ST_IMAGE_VIEW_CREATE_INFO = 15, ST_SHADER_MODULE_CREATE_INFO = 16,
    ST_PIPELINE_SHADER_STAGE_CREATE_INFO = 18, ST_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO = 19,
    ST_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO = 20, ST_PIPELINE_VIEWPORT_STATE_CREATE_INFO = 22,
    ST_PIPELINE_RASTERIZATION_STATE_CREATE_INFO = 23, ST_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO = 24,
    ST_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO = 26, ST_PIPELINE_DYNAMIC_STATE_CREATE_INFO = 27,
    ST_GRAPHICS_PIPELINE_CREATE_INFO = 28, ST_PIPELINE_LAYOUT_CREATE_INFO = 30, ST_SAMPLER_CREATE_INFO = 31,
    ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO = 32, ST_DESCRIPTOR_POOL_CREATE_INFO = 33,
    ST_DESCRIPTOR_SET_ALLOCATE_INFO = 34, ST_WRITE_DESCRIPTOR_SET = 35, ST_FRAMEBUFFER_CREATE_INFO = 37,
    ST_RENDER_PASS_CREATE_INFO = 38, ST_COMMAND_POOL_CREATE_INFO = 39, ST_COMMAND_BUFFER_ALLOCATE_INFO = 40,
    ST_COMMAND_BUFFER_BEGIN_INFO = 42, ST_RENDER_PASS_BEGIN_INFO = 43, ST_IMAGE_MEMORY_BARRIER = 45,
    ST_DEVICE_QUEUE_INFO_2 = 1000145003,
};

enum {
    LAYOUT_UNDEFINED = 0, LAYOUT_COLOR_ATTACHMENT = 2, LAYOUT_SHADER_READ = 5, LAYOUT_TRANSFER_SRC = 6,
    LAYOUT_TRANSFER_DST = 7, LAYOUT_PRESENT_SRC = 1000001002,
};

enum {
    USAGE_TRANSFER_SRC = 0x1, USAGE_TRANSFER_DST = 0x2, USAGE_SAMPLED = 0x4, USAGE_COLOR_ATTACHMENT = 0x10,
    ACCESS_SHADER_READ = 0x20, ACCESS_COLOR_WRITE = 0x100, ACCESS_TRANSFER_READ = 0x800,
    ACCESS_TRANSFER_WRITE = 0x1000, ACCESS_MEMORY_WRITE = 0x10000,
    STAGE_TOP = 0x1, STAGE_FRAGMENT = 0x80, STAGE_COLOR_OUTPUT = 0x400, STAGE_TRANSFER = 0x1000,
    STAGE_BOTTOM = 0x2000, STAGE_ALL = 0x10000,
    ASPECT_COLOR = 0x1, QUEUE_GRAPHICS = 0x1, MEMORY_DEVICE_LOCAL = 0x1,
    SHADER_VERTEX = 0x1, SHADER_FRAGMENT = 0x10,
};

typedef struct { uint32_t width, height; } Extent2D;
typedef struct { uint32_t width, height, depth; } Extent3D;
typedef struct { int32_t x, y; } Offset2D;
typedef struct { int32_t x, y, z; } Offset3D;
typedef struct { Offset2D offset; Extent2D extent; } Rect2D;
typedef struct { float x, y, width, height, minDepth, maxDepth; } Viewport;
typedef struct { uint32_t aspectMask, baseMipLevel, levelCount, baseArrayLayer, layerCount; } SubresourceRange;
typedef struct { uint32_t aspectMask, mipLevel, baseArrayLayer, layerCount; } SubresourceLayers;
typedef struct { SubresourceLayers srcSubresource; Offset3D srcOffset; SubresourceLayers dstSubresource; Offset3D dstOffset; Extent3D extent; } ImageCopy;
typedef struct { uint64_t size, alignment; uint32_t memoryTypeBits; } MemoryRequirements;
typedef struct { uint32_t propertyFlags, heapIndex; } MemoryType;
typedef struct { uint64_t size; uint32_t flags; } MemoryHeap;
typedef struct { uint32_t memoryTypeCount; MemoryType memoryTypes[32]; uint32_t memoryHeapCount; MemoryHeap memoryHeaps[16]; } MemoryProperties;
typedef struct { uint32_t queueFlags, queueCount, timestampValidBits; Extent3D minImageTransferGranularity; } QueueFamilyProperties;
typedef struct {
    uint32_t minImageCount, maxImageCount;
    Extent2D currentExtent, minImageExtent, maxImageExtent;
    uint32_t maxImageArrayLayers, supportedTransforms, currentTransform, supportedCompositeAlpha, supportedUsageFlags;
} SurfaceCapabilities;

typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, queueFamilyIndex, queueCount; const float *pQueuePriorities; } DeviceQueueCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, queueCreateInfoCount;
    const DeviceQueueCreateInfo *pQueueCreateInfos;
} DeviceCreateHead;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, queueFamilyIndex, queueIndex; } DeviceQueueInfo2;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags; Handle surface; uint32_t minImageCount, imageFormat,
        imageColorSpace; Extent2D imageExtent; uint32_t imageArrayLayers, imageUsage, imageSharingMode,
        queueFamilyIndexCount; const uint32_t *pQueueFamilyIndices; uint32_t preTransform, compositeAlpha, presentMode,
        clipped; Handle oldSwapchain;
} SwapchainCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t waitSemaphoreCount; const Handle *pWaitSemaphores;
    uint32_t swapchainCount; const Handle *pSwapchains; const uint32_t *pImageIndices; VkResult *pResults;
} PresentInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, imageType, format; Extent3D extent; uint32_t mipLevels,
        arrayLayers, samples, tiling, usage, sharingMode, queueFamilyIndexCount; const uint32_t *pQueueFamilyIndices;
    uint32_t initialLayout;
} ImageCreateInfo;
typedef struct { VkStructureType sType; const void *pNext; uint64_t allocationSize; uint32_t memoryTypeIndex; } MemoryAllocateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags; Handle image; uint32_t viewType, format;
    uint32_t components[4]; SubresourceRange subresourceRange;
} ImageViewCreateInfo;
typedef struct {
    uint32_t flags, format, samples, loadOp, storeOp, stencilLoadOp, stencilStoreOp, initialLayout, finalLayout;
} AttachmentDescription;
typedef struct { uint32_t attachment, layout; } AttachmentReference;
typedef struct {
    uint32_t flags, pipelineBindPoint, inputAttachmentCount; const AttachmentReference *pInputAttachments;
    uint32_t colorAttachmentCount; const AttachmentReference *pColorAttachments, *pResolveAttachments,
        *pDepthStencilAttachment; uint32_t preserveAttachmentCount; const uint32_t *pPreserveAttachments;
} SubpassDescription;
typedef struct { uint32_t srcSubpass, dstSubpass, srcStageMask, dstStageMask, srcAccessMask, dstAccessMask, dependencyFlags; } SubpassDependency;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, attachmentCount; const AttachmentDescription *pAttachments;
    uint32_t subpassCount; const SubpassDescription *pSubpasses; uint32_t dependencyCount;
    const SubpassDependency *pDependencies;
} RenderPassCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags; Handle renderPass; uint32_t attachmentCount;
    const Handle *pAttachments; uint32_t width, height, layers;
} FramebufferCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, magFilter, minFilter, mipmapMode, addressModeU, addressModeV,
        addressModeW; float mipLodBias; uint32_t anisotropyEnable; float maxAnisotropy; uint32_t compareEnable, compareOp;
    float minLod, maxLod; uint32_t borderColor, unnormalizedCoordinates;
} SamplerCreateInfo;
typedef struct { uint32_t binding, descriptorType, descriptorCount, stageFlags; const Handle *pImmutableSamplers; } DescriptorSetLayoutBinding;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, bindingCount; const DescriptorSetLayoutBinding *pBindings; } DescriptorSetLayoutCreateInfo;
typedef struct { uint32_t type, descriptorCount; } DescriptorPoolSize;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, maxSets, poolSizeCount; const DescriptorPoolSize *pPoolSizes; } DescriptorPoolCreateInfo;
typedef struct { VkStructureType sType; const void *pNext; Handle descriptorPool; uint32_t descriptorSetCount; const Handle *pSetLayouts; } DescriptorSetAllocateInfo;
typedef struct { Handle sampler, imageView; uint32_t imageLayout; } DescriptorImageInfo;
typedef struct {
    VkStructureType sType; const void *pNext; Handle dstSet; uint32_t dstBinding, dstArrayElement, descriptorCount,
        descriptorType; const DescriptorImageInfo *pImageInfo; const void *pBufferInfo; const Handle *pTexelBufferView;
} WriteDescriptorSet;
typedef struct { uint32_t stageFlags, offset, size; } PushConstantRange;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, setLayoutCount; const Handle *pSetLayouts;
    uint32_t pushConstantRangeCount; const PushConstantRange *pPushConstantRanges;
} PipelineLayoutCreateInfo;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags; size_t codeSize; const uint32_t *pCode; } ShaderModuleCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, stage; Handle module; const char *pName;
    const void *pSpecializationInfo;
} ShaderStageCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, vertexBindingDescriptionCount;
    const void *pVertexBindingDescriptions; uint32_t vertexAttributeDescriptionCount;
    const void *pVertexAttributeDescriptions;
} VertexInputState;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, topology, primitiveRestartEnable; } InputAssemblyState;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, viewportCount; const Viewport *pViewports;
    uint32_t scissorCount; const Rect2D *pScissors;
} ViewportState;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, depthClampEnable, rasterizerDiscardEnable, polygonMode,
        cullMode, frontFace, depthBiasEnable; float depthBiasConstantFactor, depthBiasClamp, depthBiasSlopeFactor, lineWidth;
} RasterizationState;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, rasterizationSamples, sampleShadingEnable; float minSampleShading;
    const uint32_t *pSampleMask; uint32_t alphaToCoverageEnable, alphaToOneEnable;
} MultisampleState;
typedef struct { uint32_t blendEnable, srcColor, dstColor, colorOp, srcAlpha, dstAlpha, alphaOp, colorWriteMask; } ColorBlendAttachment;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, logicOpEnable, logicOp, attachmentCount;
    const ColorBlendAttachment *pAttachments; float blendConstants[4];
} ColorBlendState;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, dynamicStateCount; const uint32_t *pDynamicStates; } DynamicState;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t flags, stageCount; const ShaderStageCreateInfo *pStages;
    const VertexInputState *pVertexInputState; const InputAssemblyState *pInputAssemblyState; const void *pTessellationState;
    const ViewportState *pViewportState; const RasterizationState *pRasterizationState;
    const MultisampleState *pMultisampleState; const void *pDepthStencilState; const ColorBlendState *pColorBlendState;
    const DynamicState *pDynamicState; Handle layout, renderPass; uint32_t subpass; Handle basePipelineHandle;
    int32_t basePipelineIndex;
} GraphicsPipelineCreateInfo;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags, queueFamilyIndex; } CommandPoolCreateInfo;
typedef struct { VkStructureType sType; const void *pNext; Handle commandPool; uint32_t level, commandBufferCount; } CommandBufferAllocateInfo;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags; const void *pInheritanceInfo; } CommandBufferBeginInfo;
typedef struct { VkStructureType sType; const void *pNext; uint32_t flags; } SimpleCreateInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t srcAccessMask, dstAccessMask, oldLayout, newLayout,
        srcQueueFamilyIndex, dstQueueFamilyIndex; Handle image; SubresourceRange subresourceRange;
} ImageMemoryBarrier;
typedef union { float color[4]; } ClearValue;
typedef struct {
    VkStructureType sType; const void *pNext; Handle renderPass, framebuffer; Rect2D renderArea;
    uint32_t clearValueCount; const ClearValue *pClearValues;
} RenderPassBeginInfo;
typedef struct {
    VkStructureType sType; const void *pNext; uint32_t waitSemaphoreCount; const Handle *pWaitSemaphores;
    const uint32_t *pWaitDstStageMask; uint32_t commandBufferCount; const VkCommandBuffer *pCommandBuffers;
    uint32_t signalSemaphoreCount; const Handle *pSignalSemaphores;
} SubmitInfo;

/* Os shaders, em SPIR-V (glslangValidator -V --vn), para nao levar o compilador
 * ao gabinete. tools/deflicker-test.sh confere que batem com a fonte.
 *
 * #version 450
 * void main() {
 *     vec2 p = vec2(gl_VertexIndex == 1 ? 3.0 : -1.0, gl_VertexIndex == 2 ? 3.0 : -1.0);
 *     gl_Position = vec4(p, 0.0, 1.0);
 * }
 * --
 * #version 450
 * layout(set = 0, binding = 0) uniform sampler2D tex;
 * layout(push_constant) uniform Push { vec4 w; } push;  // w.xyz os pesos, w.w a altura
 * layout(location = 0) out vec4 color;
 * void main() {
 *     ivec2 p = ivec2(gl_FragCoord.xy);
 *     vec4 up = texelFetch(tex, ivec2(p.x, max(p.y - 1, 0)), 0);
 *     vec4 mid = texelFetch(tex, p, 0);
 *     vec4 down = texelFetch(tex, ivec2(p.x, min(p.y + 1, int(push.w.w) - 1)), 0);
 *     color = up * push.w.x + mid * push.w.y + down * push.w.z;
 * }
 */
static const uint32_t vert_spv[] = {
    0x07230203, 0x00010000, 0x0008000b, 0x00000029, 0x00000000, 0x00020011, 0x00000001, 0x0006000b,
    0x00000001, 0x4c534c47, 0x6474732e, 0x3035342e, 0x00000000, 0x0003000e, 0x00000000, 0x00000001,
    0x0007000f, 0x00000000, 0x00000004, 0x6e69616d, 0x00000000, 0x0000000c, 0x0000001f, 0x00030003,
    0x00000002, 0x000001c2, 0x00040005, 0x00000004, 0x6e69616d, 0x00000000, 0x00030005, 0x00000009,
    0x00000070, 0x00060005, 0x0000000c, 0x565f6c67, 0x65747265, 0x646e4978, 0x00007865, 0x00060005,
    0x0000001d, 0x505f6c67, 0x65567265, 0x78657472, 0x00000000, 0x00060006, 0x0000001d, 0x00000000,
    0x505f6c67, 0x7469736f, 0x006e6f69, 0x00070006, 0x0000001d, 0x00000001, 0x505f6c67, 0x746e696f,
    0x657a6953, 0x00000000, 0x00070006, 0x0000001d, 0x00000002, 0x435f6c67, 0x4470696c, 0x61747369,
    0x0065636e, 0x00070006, 0x0000001d, 0x00000003, 0x435f6c67, 0x446c6c75, 0x61747369, 0x0065636e,
    0x00030005, 0x0000001f, 0x00000000, 0x00040047, 0x0000000c, 0x0000000b, 0x0000002a, 0x00030047,
    0x0000001d, 0x00000002, 0x00050048, 0x0000001d, 0x00000000, 0x0000000b, 0x00000000, 0x00050048,
    0x0000001d, 0x00000001, 0x0000000b, 0x00000001, 0x00050048, 0x0000001d, 0x00000002, 0x0000000b,
    0x00000003, 0x00050048, 0x0000001d, 0x00000003, 0x0000000b, 0x00000004, 0x00020013, 0x00000002,
    0x00030021, 0x00000003, 0x00000002, 0x00030016, 0x00000006, 0x00000020, 0x00040017, 0x00000007,
    0x00000006, 0x00000002, 0x00040020, 0x00000008, 0x00000007, 0x00000007, 0x00040015, 0x0000000a,
    0x00000020, 0x00000001, 0x00040020, 0x0000000b, 0x00000001, 0x0000000a, 0x0004003b, 0x0000000b,
    0x0000000c, 0x00000001, 0x0004002b, 0x0000000a, 0x0000000e, 0x00000001, 0x00020014, 0x0000000f,
    0x0004002b, 0x00000006, 0x00000011, 0x40400000, 0x0004002b, 0x00000006, 0x00000012, 0xbf800000,
    0x0004002b, 0x0000000a, 0x00000015, 0x00000002, 0x00040017, 0x00000019, 0x00000006, 0x00000004,
    0x00040015, 0x0000001a, 0x00000020, 0x00000000, 0x0004002b, 0x0000001a, 0x0000001b, 0x00000001,
    0x0004001c, 0x0000001c, 0x00000006, 0x0000001b, 0x0006001e, 0x0000001d, 0x00000019, 0x00000006,
    0x0000001c, 0x0000001c, 0x00040020, 0x0000001e, 0x00000003, 0x0000001d, 0x0004003b, 0x0000001e,
    0x0000001f, 0x00000003, 0x0004002b, 0x0000000a, 0x00000020, 0x00000000, 0x0004002b, 0x00000006,
    0x00000022, 0x00000000, 0x0004002b, 0x00000006, 0x00000023, 0x3f800000, 0x00040020, 0x00000027,
    0x00000003, 0x00000019, 0x00050036, 0x00000002, 0x00000004, 0x00000000, 0x00000003, 0x000200f8,
    0x00000005, 0x0004003b, 0x00000008, 0x00000009, 0x00000007, 0x0004003d, 0x0000000a, 0x0000000d,
    0x0000000c, 0x000500aa, 0x0000000f, 0x00000010, 0x0000000d, 0x0000000e, 0x000600a9, 0x00000006,
    0x00000013, 0x00000010, 0x00000011, 0x00000012, 0x0004003d, 0x0000000a, 0x00000014, 0x0000000c,
    0x000500aa, 0x0000000f, 0x00000016, 0x00000014, 0x00000015, 0x000600a9, 0x00000006, 0x00000017,
    0x00000016, 0x00000011, 0x00000012, 0x00050050, 0x00000007, 0x00000018, 0x00000013, 0x00000017,
    0x0003003e, 0x00000009, 0x00000018, 0x0004003d, 0x00000007, 0x00000021, 0x00000009, 0x00050051,
    0x00000006, 0x00000024, 0x00000021, 0x00000000, 0x00050051, 0x00000006, 0x00000025, 0x00000021,
    0x00000001, 0x00070050, 0x00000019, 0x00000026, 0x00000024, 0x00000025, 0x00000022, 0x00000023,
    0x00050041, 0x00000027, 0x00000028, 0x0000001f, 0x00000020, 0x0003003e, 0x00000028, 0x00000026,
    0x000100fd, 0x00010038,
};
static const uint32_t frag_spv[] = {
    0x07230203, 0x00010000, 0x0008000b, 0x00000052, 0x00000000, 0x00020011, 0x00000001, 0x0006000b,
    0x00000001, 0x4c534c47, 0x6474732e, 0x3035342e, 0x00000000, 0x0003000e, 0x00000000, 0x00000001,
    0x0007000f, 0x00000004, 0x00000004, 0x6e69616d, 0x00000000, 0x0000000d, 0x00000042, 0x00030010,
    0x00000004, 0x00000007, 0x00030003, 0x00000002, 0x000001c2, 0x00040005, 0x00000004, 0x6e69616d,
    0x00000000, 0x00030005, 0x00000009, 0x00000070, 0x00060005, 0x0000000d, 0x465f6c67, 0x43676172,
    0x64726f6f, 0x00000000, 0x00030005, 0x00000013, 0x00007075, 0x00030005, 0x00000017, 0x00786574,
    0x00030005, 0x00000028, 0x0064696d, 0x00040005, 0x0000002d, 0x6e776f64, 0x00000000, 0x00040005,
    0x00000034, 0x68737550, 0x00000000, 0x00040006, 0x00000034, 0x00000000, 0x00000077, 0x00040005,
    0x00000036, 0x68737570, 0x00000000, 0x00040005, 0x00000042, 0x6f6c6f63, 0x00000072, 0x00040047,
    0x0000000d, 0x0000000b, 0x0000000f, 0x00040047, 0x00000017, 0x00000021, 0x00000000, 0x00040047,
    0x00000017, 0x00000022, 0x00000000, 0x00030047, 0x00000034, 0x00000002, 0x00050048, 0x00000034,
    0x00000000, 0x00000023, 0x00000000, 0x00040047, 0x00000042, 0x0000001e, 0x00000000, 0x00020013,
    0x00000002, 0x00030021, 0x00000003, 0x00000002, 0x00040015, 0x00000006, 0x00000020, 0x00000001,
    0x00040017, 0x00000007, 0x00000006, 0x00000002, 0x00040020, 0x00000008, 0x00000007, 0x00000007,
    0x00030016, 0x0000000a, 0x00000020, 0x00040017, 0x0000000b, 0x0000000a, 0x00000004, 0x00040020,
    0x0000000c, 0x00000001, 0x0000000b, 0x0004003b, 0x0000000c, 0x0000000d, 0x00000001, 0x00040017,
    0x0000000e, 0x0000000a, 0x00000002, 0x00040020, 0x00000012, 0x00000007, 0x0000000b, 0x00090019,
    0x00000014, 0x0000000a, 0x00000001, 0x00000000, 0x00000000, 0x00000000, 0x00000001, 0x00000000,
    0x0003001b, 0x00000015, 0x00000014, 0x00040020, 0x00000016, 0x00000000, 0x00000015, 0x0004003b,
    0x00000016, 0x00000017, 0x00000000, 0x00040015, 0x00000019, 0x00000020, 0x00000000, 0x0004002b,
    0x00000019, 0x0000001a, 0x00000000, 0x00040020, 0x0000001b, 0x00000007, 0x00000006, 0x0004002b,
    0x00000019, 0x0000001e, 0x00000001, 0x0004002b, 0x00000006, 0x00000021, 0x00000001, 0x0004002b,
    0x00000006, 0x00000023, 0x00000000, 0x0003001e, 0x00000034, 0x0000000b, 0x00040020, 0x00000035,
    0x00000009, 0x00000034, 0x0004003b, 0x00000035, 0x00000036, 0x00000009, 0x0004002b, 0x00000019,
    0x00000037, 0x00000003, 0x00040020, 0x00000038, 0x00000009, 0x0000000a, 0x00040020, 0x00000041,
    0x00000003, 0x0000000b, 0x0004003b, 0x00000041, 0x00000042, 0x00000003, 0x0004002b, 0x00000019,
    0x0000004d, 0x00000002, 0x00050036, 0x00000002, 0x00000004, 0x00000000, 0x00000003, 0x000200f8,
    0x00000005, 0x0004003b, 0x00000008, 0x00000009, 0x00000007, 0x0004003b, 0x00000012, 0x00000013,
    0x00000007, 0x0004003b, 0x00000012, 0x00000028, 0x00000007, 0x0004003b, 0x00000012, 0x0000002d,
    0x00000007, 0x0004003d, 0x0000000b, 0x0000000f, 0x0000000d, 0x0007004f, 0x0000000e, 0x00000010,
    0x0000000f, 0x0000000f, 0x00000000, 0x00000001, 0x0004006e, 0x00000007, 0x00000011, 0x00000010,
    0x0003003e, 0x00000009, 0x00000011, 0x0004003d, 0x00000015, 0x00000018, 0x00000017, 0x00050041,
    0x0000001b, 0x0000001c, 0x00000009, 0x0000001a, 0x0004003d, 0x00000006, 0x0000001d, 0x0000001c,
    0x00050041, 0x0000001b, 0x0000001f, 0x00000009, 0x0000001e, 0x0004003d, 0x00000006, 0x00000020,
    0x0000001f, 0x00050082, 0x00000006, 0x00000022, 0x00000020, 0x00000021, 0x0007000c, 0x00000006,
    0x00000024, 0x00000001, 0x0000002a, 0x00000022, 0x00000023, 0x00050050, 0x00000007, 0x00000025,
    0x0000001d, 0x00000024, 0x00040064, 0x00000014, 0x00000026, 0x00000018, 0x0007005f, 0x0000000b,
    0x00000027, 0x00000026, 0x00000025, 0x00000002, 0x00000023, 0x0003003e, 0x00000013, 0x00000027,
    0x0004003d, 0x00000015, 0x00000029, 0x00000017, 0x0004003d, 0x00000007, 0x0000002a, 0x00000009,
    0x00040064, 0x00000014, 0x0000002b, 0x00000029, 0x0007005f, 0x0000000b, 0x0000002c, 0x0000002b,
    0x0000002a, 0x00000002, 0x00000023, 0x0003003e, 0x00000028, 0x0000002c, 0x0004003d, 0x00000015,
    0x0000002e, 0x00000017, 0x00050041, 0x0000001b, 0x0000002f, 0x00000009, 0x0000001a, 0x0004003d,
    0x00000006, 0x00000030, 0x0000002f, 0x00050041, 0x0000001b, 0x00000031, 0x00000009, 0x0000001e,
    0x0004003d, 0x00000006, 0x00000032, 0x00000031, 0x00050080, 0x00000006, 0x00000033, 0x00000032,
    0x00000021, 0x00060041, 0x00000038, 0x00000039, 0x00000036, 0x00000023, 0x00000037, 0x0004003d,
    0x0000000a, 0x0000003a, 0x00000039, 0x0004006e, 0x00000006, 0x0000003b, 0x0000003a, 0x00050082,
    0x00000006, 0x0000003c, 0x0000003b, 0x00000021, 0x0007000c, 0x00000006, 0x0000003d, 0x00000001,
    0x00000027, 0x00000033, 0x0000003c, 0x00050050, 0x00000007, 0x0000003e, 0x00000030, 0x0000003d,
    0x00040064, 0x00000014, 0x0000003f, 0x0000002e, 0x0007005f, 0x0000000b, 0x00000040, 0x0000003f,
    0x0000003e, 0x00000002, 0x00000023, 0x0003003e, 0x0000002d, 0x00000040, 0x0004003d, 0x0000000b,
    0x00000043, 0x00000013, 0x00060041, 0x00000038, 0x00000044, 0x00000036, 0x00000023, 0x0000001a,
    0x0004003d, 0x0000000a, 0x00000045, 0x00000044, 0x0005008e, 0x0000000b, 0x00000046, 0x00000043,
    0x00000045, 0x0004003d, 0x0000000b, 0x00000047, 0x00000028, 0x00060041, 0x00000038, 0x00000048,
    0x00000036, 0x00000023, 0x0000001e, 0x0004003d, 0x0000000a, 0x00000049, 0x00000048, 0x0005008e,
    0x0000000b, 0x0000004a, 0x00000047, 0x00000049, 0x00050081, 0x0000000b, 0x0000004b, 0x00000046,
    0x0000004a, 0x0004003d, 0x0000000b, 0x0000004c, 0x0000002d, 0x00060041, 0x00000038, 0x0000004e,
    0x00000036, 0x00000023, 0x0000004d, 0x0004003d, 0x0000000a, 0x0000004f, 0x0000004e, 0x0005008e,
    0x0000000b, 0x00000050, 0x0000004c, 0x0000004f, 0x00050081, 0x0000000b, 0x00000051, 0x0000004b,
    0x00000050, 0x0003003e, 0x00000042, 0x00000051, 0x000100fd, 0x00010038,
};

/* ── O nivel e o modo da tela (os mesmos do fliperos-deflicker.c) ─ */

#define API __attribute__((visibility("default")))
#define SLOTS 32
#define MAX_IMAGES 16

static float weights[3] = {0.5f, 0.5f, 0.0f};
static int level_off, forced;
static char app[64];
static char conf_lines[4096];
static struct timespec conf_mtime;

static const char *conf_path(void)
{
    const char *conf = getenv("FLIPEROS_CONF");
    return conf ? conf : "/etc/fliperos/fliperos.conf";
}

static int conf_changed(void)
{
    struct stat st;
    if (stat(conf_path(), &st))
        return 0;
    return st.st_mtim.tv_sec != conf_mtime.tv_sec || st.st_mtim.tv_nsec != conf_mtime.tv_nsec;
}

static void load_conf(void)
{
    struct stat st;
    FILE *f = fopen(conf_path(), "r");
    if (f && !fstat(fileno(f), &st))
        conf_mtime = st.st_mtim;
    char line[256];
    size_t used = 0;
    while (f && fgets(line, sizeof(line), f)) {
        size_t n = strlen(line);
        if (strncmp(line, "deflicker", 9) || used + n + 1 >= sizeof(conf_lines))
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
        snprintf(key, sizeof(key), "deflicker_%s", app);
        if (!conf_value(key, value, sizeof(value)))
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
        fprintf(stderr, "fliperos-vkfps: level %s (program %s)\n", value, app);
}

#define CARDS 8
static int interlaced(void)
{
    static int fds[CARDS], opened, frames, state;
    if (forced)
        return 1;
    if (frames++ % 30)
        return state;
    if (!opened) {
        const char *card = getenv("FLIPEROS_DRM_CARD");
        char path[32];
        for (int n = 0; n < CARDS; n++) {
            snprintf(path, sizeof(path), "/dev/dri/card%d", n);
            fds[n] = card && n ? -1 : open(card ? card : path, O_RDWR | O_CLOEXEC);
        }
        opened = 1;
    }
    state = 0;
    for (int n = 0; n < CARDS && !state; n++) {
        drmModeResPtr res = fds[n] < 0 ? NULL : drmModeGetResources(fds[n]);
        for (int i = 0; res && i < res->count_crtcs && !state; i++) {
            drmModeCrtcPtr crtc = drmModeGetCrtc(fds[n], res->crtcs[i]);
            if (crtc && crtc->mode_valid && (crtc->mode.flags & DRM_MODE_FLAG_INTERLACE))
                state = 1;
            drmModeFreeCrtc(crtc);
        }
        drmModeFreeResources(res);
    }
    return state;
}

/* filter_wanted: filtrar este quadro? A cada 30 quadros rele o fliperos.conf
 * (quando muda) e o arquivo do preview. */
static int filter_wanted(void)
{
    static int init, frames;
    if (!init) {
        const char *env = getenv("FLIPEROS_DEFLICKER_APP");
        snprintf(app, sizeof(app), "%s", env && *env ? env : program_invocation_short_name);
        load_conf();
        env = getenv("FLIPEROS_DEFLICKER_FORCE");
        forced = env && *env == '1';
        read_level();
        init = 1;
    } else if (!(++frames % 30)) {
        int changed = conf_changed();
        if (changed)
            load_conf();
        if (changed || getenv("FLIPEROS_DEFLICKER_FILE"))
            read_level();
    }
    return !level_off && interlaced();
}

/* ── A cadeia de camadas ────────────────────────────────────────── */

#define DEVICE_FUNCTIONS(X) \
    X(GetDeviceQueue) X(GetDeviceQueue2) X(CreateSwapchainKHR) X(DestroySwapchainKHR) X(GetSwapchainImagesKHR) \
    X(CreateImage) X(DestroyImage) X(GetImageMemoryRequirements) X(AllocateMemory) X(FreeMemory) X(BindImageMemory) \
    X(CreateImageView) X(DestroyImageView) X(CreateFramebuffer) X(DestroyFramebuffer) X(CreateRenderPass) \
    X(DestroyRenderPass) X(CreateSampler) X(DestroySampler) X(CreateShaderModule) X(DestroyShaderModule) \
    X(CreateDescriptorSetLayout) X(DestroyDescriptorSetLayout) X(CreateDescriptorPool) X(DestroyDescriptorPool) \
    X(AllocateDescriptorSets) X(UpdateDescriptorSets) X(CreatePipelineLayout) X(DestroyPipelineLayout) \
    X(CreateGraphicsPipelines) X(DestroyPipeline) X(CreateCommandPool) X(DestroyCommandPool) \
    X(AllocateCommandBuffers) X(BeginCommandBuffer) X(EndCommandBuffer) X(ResetCommandBuffer) X(CmdPipelineBarrier) \
    X(CmdCopyImage) X(CmdBeginRenderPass) X(CmdEndRenderPass) X(CmdBindPipeline) X(CmdBindDescriptorSets) \
    X(CmdPushConstants) X(CmdSetViewport) X(CmdSetScissor) X(CmdDraw) X(CreateFence) X(DestroyFence) X(WaitForFences) \
    X(ResetFences) X(CreateSemaphore) X(DestroySemaphore) X(QueueSubmit)

/* Os ponteiros vem do GetDeviceProcAddr, com o tipo de cada chamada na hora de
 * usar (o macro V). */
typedef struct {
#define X(name) PFN_vkVoidFunction name;
    DEVICE_FUNCTIONS(X)
#undef X
} DeviceTable;

#define V(ret, name, ...) ((ret (*)(__VA_ARGS__))d->vk.name)

/* O que vem depois desta camada, pela chave de despacho do objeto (o
 * primeiro ponteiro dele: a mesma na instancia e nas placas dela, e no
 * device e nas filas dele). */
static struct {
    void *key;
    VkInstance instance;
    PFN_vkGetInstanceProcAddr gipa;
} instances[SLOTS];

typedef VkResult (*SetLoaderData)(VkDevice, void *);

typedef struct Dev {
    void *key;
    VkDevice device;
    VkPhysicalDevice gpu;
    VkInstance instance;
    PFN_vkGetInstanceProcAddr gipa;
    PFN_vkGetDeviceProcAddr gdpa;
    PFN_vkQueuePresentKHR present;
    SetLoaderData set_loader_data;
    DeviceTable vk;
} Dev;
static Dev devices[SLOTS];

/* A familia de cada fila (o comando do filtro roda na fila do present). */
static struct { VkQueue queue; uint32_t family; } queues[64];
static unsigned next_instance, next_device, next_queue;
static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;

static void *key_of(const void *handle)
{
    return handle ? *(void *const *)handle : NULL;
}

static LayerCreateInfo *chain_info(const void *create_info, VkStructureType type, int function)
{
    LayerCreateInfo *info = (LayerCreateInfo *)((const Base *)create_info)->pNext;
    while (info && !(info->sType == type && info->function == function))
        info = (LayerCreateInfo *)info->pNext;
    return info && info->link ? info : NULL;
}

static LayerCreateInfo *link_info(const void *create_info, VkStructureType type)
{
    return chain_info(create_info, type, VK_LAYER_LINK_INFO);
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

static Dev *dev_of(const void *handle)
{
    pthread_mutex_lock(&lock);
    int i = device_slot(key_of(handle));
    pthread_mutex_unlock(&lock);
    return i < 0 ? NULL : &devices[i];
}

static void log_once(const char *msg)
{
    if (!getenv("FLIPEROS_DEFLICKER_QUIET"))
        fprintf(stderr, "fliperos-vkfps: %s\n", msg);
}

/* ── O filtro ───────────────────────────────────────────────────── */

/* Tudo de uma swapchain, feito no primeiro quadro filtrado. */
typedef struct Chain {
    Handle swapchain;
    Dev *dev;
    uint32_t format, width, height, count;
    int usable;     /* a superficie aceita a copia */
    int built, broken;
    uint32_t family;
    Handle images[MAX_IMAGES], views[MAX_IMAGES], framebuffers[MAX_IMAGES], fences[MAX_IMAGES], semaphores[MAX_IMAGES];
    VkCommandBuffer commands[MAX_IMAGES];
    Handle copy, copy_memory, copy_view, sampler, set_layout, descriptor_pool, descriptor_set, pipeline_layout;
    Handle render_pass, pipeline, command_pool;
} Chain;

static Chain *chains[SLOTS];

static Chain *chain_of(Handle swapchain)
{
    Chain *c = NULL;
    pthread_mutex_lock(&lock);
    for (int i = 0; i < SLOTS && !c; i++)
        if (chains[i] && chains[i]->swapchain == swapchain)
            c = chains[i];
    pthread_mutex_unlock(&lock);
    return c;
}

static int memory_type(Dev *d, uint32_t bits)
{
    MemoryProperties props;
    void (*get)(VkPhysicalDevice, MemoryProperties *) =
        (void (*)(VkPhysicalDevice, MemoryProperties *))d->gipa(d->instance, "vkGetPhysicalDeviceMemoryProperties");
    if (!get)
        return -1;
    get(d->gpu, &props);
    for (uint32_t i = 0; i < props.memoryTypeCount; i++)
        if ((bits & (1u << i)) && (props.memoryTypes[i].propertyFlags & MEMORY_DEVICE_LOCAL))
            return (int)i;
    for (uint32_t i = 0; i < props.memoryTypeCount; i++)
        if (bits & (1u << i))
            return (int)i;
    return -1;
}

#define CHECK(call) do { if ((call) != VK_SUCCESS) return 0; } while (0)
#define CREATE(name, info_type, info, out) \
    V(VkResult, Create##name, VkDevice, const info_type *, const void *, Handle *)(d->device, &(info), NULL, (out))

static Handle shader_module(Dev *d, const uint32_t *code, size_t size)
{
    Handle module = 0;
    ShaderModuleCreateInfo info = {ST_SHADER_MODULE_CREATE_INFO, NULL, 0, size, code};
    if (CREATE(ShaderModule, ShaderModuleCreateInfo, info, &module) != VK_SUCCESS)
        return 0;
    return module;
}

/* chain_build: os recursos da swapchain. 0 se algo falhou (chain_free limpa). */
static int chain_build(Chain *c, uint32_t family)
{
    Dev *d = c->dev;
    c->family = family;
    uint32_t count = MAX_IMAGES;
    if (V(VkResult, GetSwapchainImagesKHR, VkDevice, Handle, uint32_t *, Handle *)(d->device, c->swapchain, &count,
                                                                                   c->images) != VK_SUCCESS)
        return 0;
    c->count = count;

    /* A copia da imagem, que o shader le. */
    ImageCreateInfo image = {ST_IMAGE_CREATE_INFO, NULL, 0, 1 /* 2D */, c->format, {c->width, c->height, 1}, 1, 1, 1,
                             0 /* optimal */, USAGE_TRANSFER_DST | USAGE_SAMPLED, 0, 0, NULL, LAYOUT_UNDEFINED};
    CHECK(CREATE(Image, ImageCreateInfo, image, &c->copy));
    MemoryRequirements req;
    V(void, GetImageMemoryRequirements, VkDevice, Handle, MemoryRequirements *)(d->device, c->copy, &req);
    int type = memory_type(d, req.memoryTypeBits);
    if (type < 0)
        return 0;
    MemoryAllocateInfo alloc = {ST_MEMORY_ALLOCATE_INFO, NULL, req.size, (uint32_t)type};
    CHECK(V(VkResult, AllocateMemory, VkDevice, const MemoryAllocateInfo *, const void *, Handle *)(d->device, &alloc, NULL,
                                                                                                    &c->copy_memory));
    CHECK(V(VkResult, BindImageMemory, VkDevice, Handle, Handle, uint64_t)(d->device, c->copy, c->copy_memory, 0));
    ImageViewCreateInfo view = {ST_IMAGE_VIEW_CREATE_INFO, NULL, 0, c->copy, 1 /* 2D */, c->format, {0, 0, 0, 0},
                                {ASPECT_COLOR, 0, 1, 0, 1}};
    CHECK(CREATE(ImageView, ImageViewCreateInfo, view, &c->copy_view));

    /* O desenho: a imagem chega como origem da copia e sai para a tela. */
    AttachmentDescription attachment = {0, c->format, 1, 2 /* load dont care */, 0 /* store */, 2, 1,
                                        LAYOUT_TRANSFER_SRC, LAYOUT_PRESENT_SRC};
    AttachmentReference reference = {0, LAYOUT_COLOR_ATTACHMENT};
    SubpassDescription subpass = {0, 0, 0, NULL, 1, &reference, NULL, NULL, 0, NULL};
    SubpassDependency deps[2] = {
        {~0u, 0, STAGE_TRANSFER, STAGE_COLOR_OUTPUT, ACCESS_TRANSFER_READ, ACCESS_COLOR_WRITE, 0},
        {0, ~0u, STAGE_COLOR_OUTPUT, STAGE_BOTTOM, ACCESS_COLOR_WRITE, 0, 0},
    };
    RenderPassCreateInfo pass = {ST_RENDER_PASS_CREATE_INFO, NULL, 0, 1, &attachment, 1, &subpass, 2, deps};
    CHECK(CREATE(RenderPass, RenderPassCreateInfo, pass, &c->render_pass));

    SamplerCreateInfo sampler = {ST_SAMPLER_CREATE_INFO, NULL, 0, 0, 0, 0, 2, 2, 2, 0, 0, 1, 0, 0, 0, 0, 0, 0};
    CHECK(CREATE(Sampler, SamplerCreateInfo, sampler, &c->sampler));
    DescriptorSetLayoutBinding binding = {0, 1 /* combined */, 1, SHADER_FRAGMENT, NULL};
    DescriptorSetLayoutCreateInfo set_layout = {ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, NULL, 0, 1, &binding};
    CHECK(CREATE(DescriptorSetLayout, DescriptorSetLayoutCreateInfo, set_layout, &c->set_layout));
    DescriptorPoolSize pool_size = {1, 1};
    DescriptorPoolCreateInfo pool = {ST_DESCRIPTOR_POOL_CREATE_INFO, NULL, 0, 1, 1, &pool_size};
    CHECK(CREATE(DescriptorPool, DescriptorPoolCreateInfo, pool, &c->descriptor_pool));
    DescriptorSetAllocateInfo set_alloc = {ST_DESCRIPTOR_SET_ALLOCATE_INFO, NULL, c->descriptor_pool, 1, &c->set_layout};
    CHECK(V(VkResult, AllocateDescriptorSets, VkDevice, const DescriptorSetAllocateInfo *, Handle *)(d->device, &set_alloc,
                                                                                                     &c->descriptor_set));
    DescriptorImageInfo image_info = {c->sampler, c->copy_view, LAYOUT_SHADER_READ};
    WriteDescriptorSet write = {ST_WRITE_DESCRIPTOR_SET, NULL, c->descriptor_set, 0, 0, 1, 1, &image_info, NULL, NULL};
    V(void, UpdateDescriptorSets, VkDevice, uint32_t, const WriteDescriptorSet *, uint32_t, const void *)(d->device, 1, &write,
                                                                                                          0, NULL);
    PushConstantRange push = {SHADER_FRAGMENT, 0, 16};
    PipelineLayoutCreateInfo layout = {ST_PIPELINE_LAYOUT_CREATE_INFO, NULL, 0, 1, &c->set_layout, 1, &push};
    CHECK(CREATE(PipelineLayout, PipelineLayoutCreateInfo, layout, &c->pipeline_layout));

    Handle vs = shader_module(d, vert_spv, sizeof(vert_spv)), fs = shader_module(d, frag_spv, sizeof(frag_spv));
    int ok = 0;
    if (vs && fs) {
        ShaderStageCreateInfo stages[2] = {{ST_PIPELINE_SHADER_STAGE_CREATE_INFO, NULL, 0, SHADER_VERTEX, vs, "main", NULL},
                                           {ST_PIPELINE_SHADER_STAGE_CREATE_INFO, NULL, 0, SHADER_FRAGMENT, fs, "main", NULL}};
        VertexInputState vertex = {ST_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO, NULL, 0, 0, NULL, 0, NULL};
        InputAssemblyState assembly = {ST_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO, NULL, 0, 3 /* triangle list */, 0};
        ViewportState viewport = {ST_PIPELINE_VIEWPORT_STATE_CREATE_INFO, NULL, 0, 1, NULL, 1, NULL};
        RasterizationState raster = {ST_PIPELINE_RASTERIZATION_STATE_CREATE_INFO, NULL, 0, 0, 0, 0 /* fill */, 0 /* no cull */,
                                     0, 0, 0, 0, 0, 1.0f};
        MultisampleState multi = {ST_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO, NULL, 0, 1, 0, 0, NULL, 0, 0};
        ColorBlendAttachment blend = {0, 0, 0, 0, 0, 0, 0, 0xf};
        ColorBlendState blending = {ST_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO, NULL, 0, 0, 0, 1, &blend, {0, 0, 0, 0}};
        uint32_t dynamic_states[2] = {0 /* viewport */, 1 /* scissor */};
        DynamicState dynamic = {ST_PIPELINE_DYNAMIC_STATE_CREATE_INFO, NULL, 0, 2, dynamic_states};
        GraphicsPipelineCreateInfo info = {ST_GRAPHICS_PIPELINE_CREATE_INFO, NULL, 0, 2, stages, &vertex, &assembly, NULL,
                                           &viewport, &raster, &multi, NULL, &blending, &dynamic, c->pipeline_layout,
                                           c->render_pass, 0, 0, -1};
        ok = V(VkResult, CreateGraphicsPipelines, VkDevice, Handle, uint32_t, const GraphicsPipelineCreateInfo *, const void *,
               Handle *)(d->device, 0, 1, &info, NULL, &c->pipeline) == VK_SUCCESS;
    }
    if (vs)
        V(void, DestroyShaderModule, VkDevice, Handle, const void *)(d->device, vs, NULL);
    if (fs)
        V(void, DestroyShaderModule, VkDevice, Handle, const void *)(d->device, fs, NULL);
    if (!ok)
        return 0;

    CommandPoolCreateInfo command_pool = {ST_COMMAND_POOL_CREATE_INFO, NULL, 0x2 /* reset */, family};
    CHECK(CREATE(CommandPool, CommandPoolCreateInfo, command_pool, &c->command_pool));
    CommandBufferAllocateInfo buffers = {ST_COMMAND_BUFFER_ALLOCATE_INFO, NULL, c->command_pool, 0, c->count};
    CHECK(V(VkResult, AllocateCommandBuffers, VkDevice, const CommandBufferAllocateInfo *, VkCommandBuffer *)(d->device, &buffers,
                                                                                                              c->commands));
    for (uint32_t i = 0; i < c->count; i++) {
        /* O comando criado aqui nao passou pelo carregador: o despacho dele. */
        CHECK(d->set_loader_data(d->device, c->commands[i]));
        ImageViewCreateInfo target = {ST_IMAGE_VIEW_CREATE_INFO, NULL, 0, c->images[i], 1, c->format, {0, 0, 0, 0},
                                      {ASPECT_COLOR, 0, 1, 0, 1}};
        CHECK(CREATE(ImageView, ImageViewCreateInfo, target, &c->views[i]));
        FramebufferCreateInfo framebuffer = {ST_FRAMEBUFFER_CREATE_INFO, NULL, 0, c->render_pass, 1, &c->views[i], c->width,
                                             c->height, 1};
        CHECK(CREATE(Framebuffer, FramebufferCreateInfo, framebuffer, &c->framebuffers[i]));
        SimpleCreateInfo fence = {ST_FENCE_CREATE_INFO, NULL, 1 /* signaled */};
        CHECK(CREATE(Fence, SimpleCreateInfo, fence, &c->fences[i]));
        SimpleCreateInfo semaphore = {ST_SEMAPHORE_CREATE_INFO, NULL, 0};
        CHECK(CREATE(Semaphore, SimpleCreateInfo, semaphore, &c->semaphores[i]));
    }
    return 1;
}

/* chain_free: tudo, depois de esperar os comandos que ainda rodam. */
static void chain_free(Chain *c)
{
    Dev *d = c->dev;
#define DESTROY(name, handle) \
    do { \
        if (handle) \
            V(void, Destroy##name, VkDevice, Handle, const void *)(d->device, (handle), NULL); \
        (handle) = 0; \
    } while (0)
    for (uint32_t i = 0; i < c->count; i++) {
        if (c->fences[i])
            V(VkResult, WaitForFences, VkDevice, uint32_t, const Handle *, uint32_t, uint64_t)(d->device, 1, &c->fences[i], 1,
                                                                                               1000000000ull);
    }
    for (uint32_t i = 0; i < c->count; i++) {
        DESTROY(Fence, c->fences[i]);
        DESTROY(Semaphore, c->semaphores[i]);
        DESTROY(Framebuffer, c->framebuffers[i]);
        DESTROY(ImageView, c->views[i]);
    }
    DESTROY(CommandPool, c->command_pool);
    DESTROY(Pipeline, c->pipeline);
    DESTROY(PipelineLayout, c->pipeline_layout);
    DESTROY(DescriptorPool, c->descriptor_pool);
    DESTROY(DescriptorSetLayout, c->set_layout);
    DESTROY(Sampler, c->sampler);
    DESTROY(RenderPass, c->render_pass);
    DESTROY(ImageView, c->copy_view);
    DESTROY(Image, c->copy);
    if (c->copy_memory)
        V(void, FreeMemory, VkDevice, Handle, const void *)(d->device, c->copy_memory, NULL);
    c->copy_memory = 0;
    c->built = 0;
#undef DESTROY
}

/* chain_record: copia a imagem pronta e a desenha de volta pelo filtro. */
static int chain_record(Chain *c, uint32_t index)
{
    Dev *d = c->dev;
    VkCommandBuffer cmd = c->commands[index];
    SubresourceRange range = {ASPECT_COLOR, 0, 1, 0, 1};
    CommandBufferBeginInfo begin = {ST_COMMAND_BUFFER_BEGIN_INFO, NULL, 0x1 /* one time */, NULL};
    CHECK(V(VkResult, ResetCommandBuffer, VkCommandBuffer, uint32_t)(cmd, 0));
    CHECK(V(VkResult, BeginCommandBuffer, VkCommandBuffer, const CommandBufferBeginInfo *)(cmd, &begin));

    ImageMemoryBarrier before[2] = {
        {ST_IMAGE_MEMORY_BARRIER, NULL, ACCESS_MEMORY_WRITE, ACCESS_TRANSFER_READ, LAYOUT_PRESENT_SRC, LAYOUT_TRANSFER_SRC, ~0u, ~0u,
         c->images[index], range},
        {ST_IMAGE_MEMORY_BARRIER, NULL, ACCESS_SHADER_READ, ACCESS_TRANSFER_WRITE, LAYOUT_UNDEFINED, LAYOUT_TRANSFER_DST, ~0u, ~0u,
         c->copy, range},
    };
    V(void, CmdPipelineBarrier, VkCommandBuffer, uint32_t, uint32_t, uint32_t, uint32_t, const void *, uint32_t, const void *,
      uint32_t, const ImageMemoryBarrier *)(cmd, STAGE_ALL, STAGE_TRANSFER, 0, 0, NULL, 0, NULL, 2, before);
    ImageCopy region = {{ASPECT_COLOR, 0, 0, 1}, {0, 0, 0}, {ASPECT_COLOR, 0, 0, 1}, {0, 0, 0}, {c->width, c->height, 1}};
    V(void, CmdCopyImage, VkCommandBuffer, Handle, uint32_t, Handle, uint32_t, uint32_t, const ImageCopy *)(
        cmd, c->images[index], LAYOUT_TRANSFER_SRC, c->copy, LAYOUT_TRANSFER_DST, 1, &region);
    ImageMemoryBarrier after = {ST_IMAGE_MEMORY_BARRIER, NULL, ACCESS_TRANSFER_WRITE, ACCESS_SHADER_READ, LAYOUT_TRANSFER_DST,
                                LAYOUT_SHADER_READ, ~0u, ~0u, c->copy, range};
    V(void, CmdPipelineBarrier, VkCommandBuffer, uint32_t, uint32_t, uint32_t, uint32_t, const void *, uint32_t, const void *,
      uint32_t, const ImageMemoryBarrier *)(cmd, STAGE_TRANSFER, STAGE_FRAGMENT, 0, 0, NULL, 0, NULL, 1, &after);

    Rect2D area = {{0, 0}, {c->width, c->height}};
    RenderPassBeginInfo pass = {ST_RENDER_PASS_BEGIN_INFO, NULL, c->render_pass, c->framebuffers[index], area, 0, NULL};
    V(void, CmdBeginRenderPass, VkCommandBuffer, const RenderPassBeginInfo *, uint32_t)(cmd, &pass, 0);
    V(void, CmdBindPipeline, VkCommandBuffer, uint32_t, Handle)(cmd, 0, c->pipeline);
    V(void, CmdBindDescriptorSets, VkCommandBuffer, uint32_t, Handle, uint32_t, uint32_t, const Handle *, uint32_t,
      const uint32_t *)(cmd, 0, c->pipeline_layout, 0, 1, &c->descriptor_set, 0, NULL);
    Viewport viewport = {0, 0, (float)c->width, (float)c->height, 0, 1};
    V(void, CmdSetViewport, VkCommandBuffer, uint32_t, uint32_t, const Viewport *)(cmd, 0, 1, &viewport);
    V(void, CmdSetScissor, VkCommandBuffer, uint32_t, uint32_t, const Rect2D *)(cmd, 0, 1, &area);
    float push[4] = {weights[0], weights[1], weights[2], (float)c->height};
    V(void, CmdPushConstants, VkCommandBuffer, Handle, uint32_t, uint32_t, uint32_t, const void *)(
        cmd, c->pipeline_layout, SHADER_FRAGMENT, 0, sizeof(push), push);
    V(void, CmdDraw, VkCommandBuffer, uint32_t, uint32_t, uint32_t, uint32_t)(cmd, 3, 1, 0, 0);
    V(void, CmdEndRenderPass, VkCommandBuffer)(cmd);
    return V(VkResult, EndCommandBuffer, VkCommandBuffer)(cmd) == VK_SUCCESS;
}

/* queue_family: a familia da fila, ou -1 se ela nao desenha. */
static int64_t queue_family(Dev *d, VkQueue queue)
{
    int64_t family = -1;
    pthread_mutex_lock(&lock);
    for (unsigned i = 0; i < sizeof(queues) / sizeof(queues[0]); i++)
        if (queues[i].queue == queue)
            family = queues[i].family;
    pthread_mutex_unlock(&lock);
    if (family < 0)
        return -1;
    QueueFamilyProperties props[32];
    uint32_t count = 32;
    void (*get)(VkPhysicalDevice, uint32_t *, QueueFamilyProperties *) =
        (void (*)(VkPhysicalDevice, uint32_t *, QueueFamilyProperties *))d->gipa(d->instance,
                                                                                 "vkGetPhysicalDeviceQueueFamilyProperties");
    if (!get)
        return -1;
    get(d->gpu, &count, props);
    return family < count && (props[family].queueFlags & QUEUE_GRAPHICS) ? family : -1;
}

/* chain_ready: os recursos prontos para esta fila? */
static int chain_ready(Chain *c, Dev *d, VkQueue queue)
{
    if (c->broken || !c->usable)
        return 0;
    int64_t family = queue_family(d, queue);
    if (family < 0)
        return 0;
    if (c->built)
        return c->family == (uint32_t)family;
    if (!chain_build(c, (uint32_t)family)) {
        log_once("could not prepare the filter; filter off for this program");
        chain_free(c);
        c->broken = 1;
        return 0;
    }
    c->built = 1;
    if (getenv("FLIPEROS_DEFLICKER_DEBUG"))
        fprintf(stderr, "fliperos-vkfps: filtering %ux%u, %u images\n", c->width, c->height, c->count);
    return 1;
}

/* filter_present: cada imagem da swapchain passa pelo filtro antes do present,
 * que passa a esperar os semaforos daqui. Devolve quantos semaforos pos em
 * waits; o primeiro comando espera os do programa. Imagem que nao passou (sem
 * recursos, erro) vai direto: se nenhuma passou, o present segue como veio. */
static uint32_t filter_present(Dev *d, VkQueue queue, const PresentInfo *info, Handle *waits, int *filtered)
{
    uint32_t done = 0, wait_count = info->waitSemaphoreCount;
    const Handle *wait = info->pWaitSemaphores;
    for (uint32_t i = 0; i < info->swapchainCount && done < MAX_IMAGES; i++) {
        Chain *c = chain_of(info->pSwapchains[i]);
        uint32_t index = info->pImageIndices[i];
        if (!c || !chain_ready(c, d, queue) || index >= c->count)
            continue;
        V(VkResult, WaitForFences, VkDevice, uint32_t, const Handle *, uint32_t, uint64_t)(d->device, 1, &c->fences[index], 1,
                                                                                           1000000000ull);
        if (!chain_record(c, index))
            continue;
        V(VkResult, ResetFences, VkDevice, uint32_t, const Handle *)(d->device, 1, &c->fences[index]);
        uint32_t stages[16];
        for (uint32_t s = 0; s < wait_count && s < 16; s++)
            stages[s] = STAGE_ALL;
        SubmitInfo submit = {ST_SUBMIT_INFO, NULL, wait_count, wait, stages, 1, &c->commands[index], 1, &c->semaphores[index]};
        if (wait_count > 16 ||
            V(VkResult, QueueSubmit, VkQueue, uint32_t, const SubmitInfo *, Handle)(queue, 1, &submit, c->fences[index]) != VK_SUCCESS) {
            /* A fence ficou sem sinal: que a proxima espera nao trave. */
            log_once("could not submit the filter; filter off for this swapchain");
            c->broken = 1;
            continue;
        }
        wait_count = 0;
        wait = NULL;
        waits[done++] = c->semaphores[index];
        *filtered = 1;
    }
    return done;
}

/* ── As chamadas ────────────────────────────────────────────────── */

/* fps_tick: as trocas de quadro de cada segundo, gravadas a cada segundo. */
static void fps_tick(int filtering)
{
    static double start;
    static int count, disabled;
    static char path[256], name_buf[64];
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
        snprintf(name_buf, sizeof(name_buf), "%s", name && *name ? name : program_invocation_short_name);
        start = now;
    }
    count++;
    if (now - start >= 1.0) {
        char tmp[300];
        snprintf(tmp, sizeof(tmp), "%s.%d", path, (int)getpid());
        FILE *f = fopen(tmp, "w");
        if (f) {
            fprintf(f, "%d %.1f %s - %d\n", (int)getpid(), count / (now - start), name_buf, filtering);
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
    LayerCreateInfo *loader = chain_info(create_info, VK_STRUCTURE_TYPE_LOADER_DEVICE_CREATE_INFO, VK_LOADER_DATA_CALLBACK);
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
        Dev *d = &devices[i];
        memset(d, 0, sizeof(*d));
        d->device = *device;
        d->gpu = gpu;
        d->instance = instance;
        d->gipa = gipa;
        d->gdpa = gdpa;
        d->present = present;
        d->set_loader_data = loader ? (SetLoaderData)loader->link : NULL;
#define X(name) d->vk.name = gdpa(*device, "vk" #name);
        DEVICE_FUNCTIONS(X)
#undef X
        d->key = key_of(*device);
        pthread_mutex_unlock(&lock);
    }
    return result;
}

static void remember_queue(VkQueue queue, uint32_t family)
{
    pthread_mutex_lock(&lock);
    for (unsigned i = 0; i < sizeof(queues) / sizeof(queues[0]); i++)
        if (queues[i].queue == queue) {
            queues[i].family = family;
            pthread_mutex_unlock(&lock);
            return;
        }
    unsigned i = next_queue++ % (sizeof(queues) / sizeof(queues[0]));
    queues[i].queue = queue;
    queues[i].family = family;
    pthread_mutex_unlock(&lock);
}

static void layer_GetDeviceQueue(VkDevice device, uint32_t family, uint32_t index, VkQueue *queue)
{
    Dev *d = dev_of(device);
    if (!d)
        return;
    V(void, GetDeviceQueue, VkDevice, uint32_t, uint32_t, VkQueue *)(device, family, index, queue);
    if (*queue)
        remember_queue(*queue, family);
}

static void layer_GetDeviceQueue2(VkDevice device, const DeviceQueueInfo2 *info, VkQueue *queue)
{
    Dev *d = dev_of(device);
    if (!d)
        return;
    V(void, GetDeviceQueue2, VkDevice, const DeviceQueueInfo2 *, VkQueue *)(device, info, queue);
    if (*queue)
        remember_queue(*queue, info->queueFamilyIndex);
}

/* A swapchain passa a poder ser copiada e desenhada, se a superficie deixa. */
static VkResult layer_CreateSwapchainKHR(VkDevice device, const SwapchainCreateInfo *info, const void *alloc, Handle *swapchain)
{
    Dev *d = dev_of(device);
    if (!d)
        return VK_ERROR_DEVICE_LOST;
    SwapchainCreateInfo mine = *info;
    uint32_t wanted = USAGE_TRANSFER_SRC | USAGE_COLOR_ATTACHMENT;
    SurfaceCapabilities caps;
    VkResult (*get)(VkPhysicalDevice, Handle, SurfaceCapabilities *) =
        (VkResult (*)(VkPhysicalDevice, Handle, SurfaceCapabilities *))d->gipa(d->instance,
                                                                               "vkGetPhysicalDeviceSurfaceCapabilitiesKHR");
    int usable = get && get(d->gpu, info->surface, &caps) == VK_SUCCESS && (caps.supportedUsageFlags & wanted) == wanted &&
                 info->imageArrayLayers == 1;
    if (usable)
        mine.imageUsage |= wanted;
    VkResult result = V(VkResult, CreateSwapchainKHR, VkDevice, const SwapchainCreateInfo *, const void *, Handle *)(
        device, &mine, alloc, swapchain);
    if (result != VK_SUCCESS)
        return result;
    Chain *c = calloc(1, sizeof(*c));
    if (!c)
        return result;
    c->swapchain = *swapchain;
    c->dev = d;
    c->format = info->imageFormat;
    c->width = info->imageExtent.width;
    c->height = info->imageExtent.height;
    c->usable = usable && d->set_loader_data != NULL;
    pthread_mutex_lock(&lock);
    for (int i = 0; i < SLOTS; i++)
        if (!chains[i]) {
            chains[i] = c;
            c = NULL;
            break;
        }
    pthread_mutex_unlock(&lock);
    free(c);    /* sem vaga: esta swapchain fica sem o filtro */
    return result;
}

static void layer_DestroySwapchainKHR(VkDevice device, Handle swapchain, const void *alloc)
{
    Dev *d = dev_of(device);
    if (!d)
        return;
    Chain *c = NULL;
    pthread_mutex_lock(&lock);
    for (int i = 0; i < SLOTS && !c; i++)
        if (chains[i] && chains[i]->swapchain == swapchain) {
            c = chains[i];
            chains[i] = NULL;
        }
    pthread_mutex_unlock(&lock);
    if (c) {
        chain_free(c);
        free(c);
    }
    V(void, DestroySwapchainKHR, VkDevice, Handle, const void *)(device, swapchain, alloc);
}

static VkResult layer_QueuePresentKHR(VkQueue queue, const void *present_info)
{
    PFN_vkQueuePresentKHR present = NULL;
    Dev *d = dev_of(queue);
    if (d)
        present = d->present;
    if (!present)
        return VK_ERROR_DEVICE_LOST;
    const PresentInfo *info = present_info;
    PresentInfo mine = *info;
    Handle waits[MAX_IMAGES];
    int filtering = 0;
    if (filter_wanted() && d->vk.QueueSubmit) {
        uint32_t count = filter_present(d, queue, info, waits, &filtering);
        if (count) {
            mine.waitSemaphoreCount = count;
            mine.pWaitSemaphores = waits;
        }
    }
    fps_tick(filtering);
    return present(queue, (const void *)&mine);
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
    if (!gdpa)
        return NULL;
    PFN_vkVoidFunction next = gdpa(device, name);
    if (!next)
        return NULL;
    if (!strcmp(name, "vkGetDeviceQueue"))
        return (PFN_vkVoidFunction)layer_GetDeviceQueue;
    if (!strcmp(name, "vkGetDeviceQueue2"))
        return (PFN_vkVoidFunction)layer_GetDeviceQueue2;
    if (!strcmp(name, "vkCreateSwapchainKHR"))
        return (PFN_vkVoidFunction)layer_CreateSwapchainKHR;
    if (!strcmp(name, "vkDestroySwapchainKHR"))
        return (PFN_vkVoidFunction)layer_DestroySwapchainKHR;
    return next;
}

#ifdef FLIPEROS_VK_CHECK
/* Os tipos daqui contra os cabecalhos de verdade (tools/deflicker-test.sh). */
#define SAME(mine, real) _Static_assert(sizeof(mine) == sizeof(real), #mine)
#define AT(mine, field, real, rfield) _Static_assert(offsetof(mine, field) == offsetof(real, rfield), #mine "." #field)
#define NUM(mine, real) _Static_assert((long long)(mine) == (long long)(real), #mine)
SAME(SwapchainCreateInfo, VkSwapchainCreateInfoKHR); AT(SwapchainCreateInfo, surface, VkSwapchainCreateInfoKHR, surface);
AT(SwapchainCreateInfo, imageFormat, VkSwapchainCreateInfoKHR, imageFormat);
AT(SwapchainCreateInfo, imageExtent, VkSwapchainCreateInfoKHR, imageExtent);
AT(SwapchainCreateInfo, imageUsage, VkSwapchainCreateInfoKHR, imageUsage);
AT(SwapchainCreateInfo, oldSwapchain, VkSwapchainCreateInfoKHR, oldSwapchain);
SAME(PresentInfo, VkPresentInfoKHR); AT(PresentInfo, pImageIndices, VkPresentInfoKHR, pImageIndices);
SAME(ImageCreateInfo, VkImageCreateInfo); AT(ImageCreateInfo, initialLayout, VkImageCreateInfo, initialLayout);
SAME(MemoryAllocateInfo, VkMemoryAllocateInfo); SAME(ImageViewCreateInfo, VkImageViewCreateInfo);
AT(ImageViewCreateInfo, subresourceRange, VkImageViewCreateInfo, subresourceRange);
SAME(AttachmentDescription, VkAttachmentDescription); SAME(SubpassDescription, VkSubpassDescription);
SAME(SubpassDependency, VkSubpassDependency); SAME(RenderPassCreateInfo, VkRenderPassCreateInfo);
SAME(FramebufferCreateInfo, VkFramebufferCreateInfo); SAME(SamplerCreateInfo, VkSamplerCreateInfo);
AT(SamplerCreateInfo, unnormalizedCoordinates, VkSamplerCreateInfo, unnormalizedCoordinates);
SAME(DescriptorSetLayoutBinding, VkDescriptorSetLayoutBinding);
SAME(DescriptorSetLayoutCreateInfo, VkDescriptorSetLayoutCreateInfo); SAME(DescriptorPoolCreateInfo, VkDescriptorPoolCreateInfo);
SAME(DescriptorSetAllocateInfo, VkDescriptorSetAllocateInfo); SAME(DescriptorImageInfo, VkDescriptorImageInfo);
SAME(WriteDescriptorSet, VkWriteDescriptorSet); AT(WriteDescriptorSet, pImageInfo, VkWriteDescriptorSet, pImageInfo);
SAME(PipelineLayoutCreateInfo, VkPipelineLayoutCreateInfo); SAME(ShaderModuleCreateInfo, VkShaderModuleCreateInfo);
SAME(ShaderStageCreateInfo, VkPipelineShaderStageCreateInfo); SAME(VertexInputState, VkPipelineVertexInputStateCreateInfo);
SAME(InputAssemblyState, VkPipelineInputAssemblyStateCreateInfo); SAME(ViewportState, VkPipelineViewportStateCreateInfo);
SAME(RasterizationState, VkPipelineRasterizationStateCreateInfo); AT(RasterizationState, lineWidth, VkPipelineRasterizationStateCreateInfo, lineWidth);
SAME(MultisampleState, VkPipelineMultisampleStateCreateInfo); SAME(ColorBlendAttachment, VkPipelineColorBlendAttachmentState);
SAME(ColorBlendState, VkPipelineColorBlendStateCreateInfo); SAME(DynamicState, VkPipelineDynamicStateCreateInfo);
SAME(GraphicsPipelineCreateInfo, VkGraphicsPipelineCreateInfo); AT(GraphicsPipelineCreateInfo, layout, VkGraphicsPipelineCreateInfo, layout);
AT(GraphicsPipelineCreateInfo, basePipelineIndex, VkGraphicsPipelineCreateInfo, basePipelineIndex);
SAME(CommandPoolCreateInfo, VkCommandPoolCreateInfo); SAME(CommandBufferAllocateInfo, VkCommandBufferAllocateInfo);
SAME(CommandBufferBeginInfo, VkCommandBufferBeginInfo); SAME(ImageMemoryBarrier, VkImageMemoryBarrier);
AT(ImageMemoryBarrier, image, VkImageMemoryBarrier, image); SAME(RenderPassBeginInfo, VkRenderPassBeginInfo);
AT(RenderPassBeginInfo, renderArea, VkRenderPassBeginInfo, renderArea); SAME(SubmitInfo, VkSubmitInfo);
AT(SubmitInfo, pSignalSemaphores, VkSubmitInfo, pSignalSemaphores); SAME(ImageCopy, VkImageCopy);
SAME(MemoryRequirements, VkMemoryRequirements); SAME(MemoryProperties, VkPhysicalDeviceMemoryProperties);
SAME(QueueFamilyProperties, VkQueueFamilyProperties); SAME(SurfaceCapabilities, VkSurfaceCapabilitiesKHR);
AT(SurfaceCapabilities, supportedUsageFlags, VkSurfaceCapabilitiesKHR, supportedUsageFlags);
SAME(DeviceQueueInfo2, VkDeviceQueueInfo2); SAME(Viewport, VkViewport); SAME(Rect2D, VkRect2D);
NUM(ST_SUBMIT_INFO, VK_STRUCTURE_TYPE_SUBMIT_INFO); NUM(ST_MEMORY_ALLOCATE_INFO, VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO);
NUM(ST_FENCE_CREATE_INFO, VK_STRUCTURE_TYPE_FENCE_CREATE_INFO); NUM(ST_SEMAPHORE_CREATE_INFO, VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO);
NUM(ST_IMAGE_CREATE_INFO, VK_STRUCTURE_TYPE_IMAGE_CREATE_INFO); NUM(ST_IMAGE_VIEW_CREATE_INFO, VK_STRUCTURE_TYPE_IMAGE_VIEW_CREATE_INFO);
NUM(ST_SHADER_MODULE_CREATE_INFO, VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO);
NUM(ST_PIPELINE_SHADER_STAGE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO);
NUM(ST_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_VERTEX_INPUT_STATE_CREATE_INFO);
NUM(ST_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_INPUT_ASSEMBLY_STATE_CREATE_INFO);
NUM(ST_PIPELINE_VIEWPORT_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_VIEWPORT_STATE_CREATE_INFO);
NUM(ST_PIPELINE_RASTERIZATION_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_RASTERIZATION_STATE_CREATE_INFO);
NUM(ST_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_MULTISAMPLE_STATE_CREATE_INFO);
NUM(ST_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_COLOR_BLEND_STATE_CREATE_INFO);
NUM(ST_PIPELINE_DYNAMIC_STATE_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_DYNAMIC_STATE_CREATE_INFO);
NUM(ST_GRAPHICS_PIPELINE_CREATE_INFO, VK_STRUCTURE_TYPE_GRAPHICS_PIPELINE_CREATE_INFO);
NUM(ST_PIPELINE_LAYOUT_CREATE_INFO, VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO); NUM(ST_SAMPLER_CREATE_INFO, VK_STRUCTURE_TYPE_SAMPLER_CREATE_INFO);
NUM(ST_DESCRIPTOR_SET_LAYOUT_CREATE_INFO, VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO);
NUM(ST_DESCRIPTOR_POOL_CREATE_INFO, VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO);
NUM(ST_DESCRIPTOR_SET_ALLOCATE_INFO, VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO);
NUM(ST_WRITE_DESCRIPTOR_SET, VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET); NUM(ST_FRAMEBUFFER_CREATE_INFO, VK_STRUCTURE_TYPE_FRAMEBUFFER_CREATE_INFO);
NUM(ST_RENDER_PASS_CREATE_INFO, VK_STRUCTURE_TYPE_RENDER_PASS_CREATE_INFO); NUM(ST_COMMAND_POOL_CREATE_INFO, VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO);
NUM(ST_COMMAND_BUFFER_ALLOCATE_INFO, VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO);
NUM(ST_COMMAND_BUFFER_BEGIN_INFO, VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO); NUM(ST_RENDER_PASS_BEGIN_INFO, VK_STRUCTURE_TYPE_RENDER_PASS_BEGIN_INFO);
NUM(ST_IMAGE_MEMORY_BARRIER, VK_STRUCTURE_TYPE_IMAGE_MEMORY_BARRIER); NUM(ST_DEVICE_QUEUE_INFO_2, VK_STRUCTURE_TYPE_DEVICE_QUEUE_INFO_2);
NUM(LAYOUT_COLOR_ATTACHMENT, VK_IMAGE_LAYOUT_COLOR_ATTACHMENT_OPTIMAL); NUM(LAYOUT_SHADER_READ, VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL);
NUM(LAYOUT_TRANSFER_SRC, VK_IMAGE_LAYOUT_TRANSFER_SRC_OPTIMAL); NUM(LAYOUT_TRANSFER_DST, VK_IMAGE_LAYOUT_TRANSFER_DST_OPTIMAL);
NUM(LAYOUT_PRESENT_SRC, VK_IMAGE_LAYOUT_PRESENT_SRC_KHR);
NUM(USAGE_TRANSFER_SRC, VK_IMAGE_USAGE_TRANSFER_SRC_BIT); NUM(USAGE_TRANSFER_DST, VK_IMAGE_USAGE_TRANSFER_DST_BIT);
NUM(USAGE_SAMPLED, VK_IMAGE_USAGE_SAMPLED_BIT); NUM(USAGE_COLOR_ATTACHMENT, VK_IMAGE_USAGE_COLOR_ATTACHMENT_BIT);
NUM(ACCESS_SHADER_READ, VK_ACCESS_SHADER_READ_BIT); NUM(ACCESS_COLOR_WRITE, VK_ACCESS_COLOR_ATTACHMENT_WRITE_BIT);
NUM(ACCESS_TRANSFER_READ, VK_ACCESS_TRANSFER_READ_BIT); NUM(ACCESS_TRANSFER_WRITE, VK_ACCESS_TRANSFER_WRITE_BIT);
NUM(ACCESS_MEMORY_WRITE, VK_ACCESS_MEMORY_WRITE_BIT); NUM(STAGE_FRAGMENT, VK_PIPELINE_STAGE_FRAGMENT_SHADER_BIT);
NUM(STAGE_COLOR_OUTPUT, VK_PIPELINE_STAGE_COLOR_ATTACHMENT_OUTPUT_BIT); NUM(STAGE_TRANSFER, VK_PIPELINE_STAGE_TRANSFER_BIT);
NUM(STAGE_BOTTOM, VK_PIPELINE_STAGE_BOTTOM_OF_PIPE_BIT); NUM(STAGE_ALL, VK_PIPELINE_STAGE_ALL_COMMANDS_BIT);
NUM(QUEUE_GRAPHICS, VK_QUEUE_GRAPHICS_BIT); NUM(MEMORY_DEVICE_LOCAL, VK_MEMORY_PROPERTY_DEVICE_LOCAL_BIT);
NUM(VK_LAYER_LINK_INFO, 0); NUM(VK_LOADER_DATA_CALLBACK, 1);
#endif
