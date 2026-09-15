# Patches de kernel 15kHz (D0023R)

Vendorizados de <https://github.com/D0023R/linux_kernel_15khz>, commit
`97968a0bdb682f2b6e1469de24449a4536bd8ecb` (2026-09-13), licença GPLv3
(`LICENSE` do repositório de origem).

Usados por `fliperos-mkiso.sh --with-15khz-kernel` como alternativa ao
método EDID-only (`crt15-edid.bin`) que o build usa por padrão. Diferença:
o EDID-only força o modo fixo no boot sem tocar no kernel; esse conjunto de
patches habilita troca dinâmica de modo via KMS sem X (patch 06,
"groovyarcade kms enabler"), que o EDID-only não garante.

## Pasta `6.6/`

Alvo: kernel.org vanilla **6.6.152** (série Longterm). Se
`KERNEL_15KHZ_VERSION` em `fliperos-mkiso.sh` for atualizado para outra
série (ex.: 6.12), vendorizar a pasta correspondente do repositório D0023R
junto — os patches são específicos de versão.

| Arquivo | Escopo |
| --- | --- |
| `01_linux_15khz.patch` | Patch principal — suporte a modo 15kHz (DRM core) |
| `02_linux_15khz_interlaced_mode_fix.patch` | Fix de vertical blank interrupt — necessário para o driver **radeon** |
| `03_linux_15khz_dcn1_dcn2_interlaced_mode_fix.patch` | Habilita modo entrelaçado — **amdgpu/DCN** (placas standalone/APU mais novas) |
| `04_linux_15khz_dce_interlaced_mode_fix.patch` | Habilita modo entrelaçado — **amdgpu/DCE** (placas mais antigas) |
| `05_linux_15khz_amdgpu_pll_fix.patch` | Fix de cálculo de PLL — **amdgpu** |
| `06_linux_switchres_kms_drm_modesetting.patch` | Manipulação de modesetting via KMS para uso do Switchres sem X (`drmkms`) — o recurso que motivou adotar esse caminho |

Cobre **radeon** e **amdgpu** (DCE e DCN). Não há patch de **i915/Intel**
nesse conjunto — o hack de iGPU Intel mencionado no escopo de hardware do
projeto é independente disso.

Aplicação: `patch -p1 < arquivo.patch`, a partir da raiz da árvore de
source do kernel extraída, em ordem numérica.
