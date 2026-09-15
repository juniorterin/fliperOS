#include <stdio.h>
#include <stddef.h>
#include <xf86drmMode.h>
int main(void) {
    printf("%zu %zu %zu %zu %zu %zu %zu\n",
        sizeof(drmModeModeInfo), sizeof(drmModeRes), sizeof(drmModeConnector),
        sizeof(drmModeEncoder), sizeof(drmModeCrtc),
        offsetof(drmModeConnector, modes), offsetof(drmModeCrtc, mode));
    return 0;
}
