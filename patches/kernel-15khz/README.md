# 15kHz kernel patches (D0023R)

Vendored from <https://github.com/D0023R/linux_kernel_15khz>, commit
`ece6ef15eca9480eaf75870a44764f47118e9cfe` (2026-09-29), GPLv3 license
(`LICENSE` of the source repository). It is the same set GroovyArcade
applies in its `linux-15khz` package.

`fliperos-mkiso.sh` always compiles the kernel with them: they provide the
`video=640x480iS` boot mode (and the others in the table) used by the Limine
menu and by `fliperos-setup`, as in GroovyArcade.

## Folder `6.18/`

Target: vanilla kernel.org **6.18.54** (Longterm series). Chosen because it is
the newest LTS series with the complete set, including patch 09 (interlacing
on Intel Gen9). If `KERNEL_15KHZ_VERSION` in `fliperos-mkiso.sh` changes
series, vendor D0023R's matching folder along with it — the patches are
version-specific.

| File | Scope |
| --- | --- |
| `01_linux_15khz.patch` | Main patch: the `S` flag in `video=` and the fixed table of low-dotclock modes (15/25/31 kHz) |
| `02_linux_15khz_interlaced_mode_fix.patch` | Vertical blank interrupt in interlaced mode — **radeon** driver |
| `03_linux_15khz_dcn1_dcn2_dcn3_interlaced_mode_fix.patch` | Interlacing on **amdgpu/DCN1-3** (cards and APUs) |
| `04_linux_15khz_dce_interlaced_mode_fix.patch` | Interlacing on **amdgpu/DCE** (older cards) |
| `05_linux_15khz_amdgpu_pll_fix.patch` | PLL calculation — **amdgpu** |
| `06_linux_switchres_kms_drm_modesetting.patch` | Mode switching through KMS for Switchres without X (`drmkms`) |
| `07_linux_15khz_fix_ddc.patch` | Oops when probing DDC with no adapter connected |
| `08_linux_15khz_interlace_force_even.patch` | Even fields in interlaced mode on **amdgpu/DCN1** |
| `09_linux_15khz_i915_gen9_interlace.patch` | Interlacing on **Intel Gen9** with `i915.no_ytiled_scanout=1` (the "Intel 15 kHz" boot entry passes this parameter) |

Covers **radeon**, **amdgpu** (DCE and DCN1-3) and, through 09, **i915 Gen9**.
NVIDIA (nouveau) and the other Intel generations use the `1280x480iS` super
resolution.

Applying: `patch -p1 < file.patch`, from the root of the kernel tree, in
numeric order.
