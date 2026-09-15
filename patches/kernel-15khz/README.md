# Patches de kernel 15kHz (D0023R)

Vendorizados de <https://github.com/D0023R/linux_kernel_15khz>, commit
`97968a0bdb682f2b6e1469de24449a4536bd8ecb` (2026-09-13), licença GPLv3
(`LICENSE` do repositório de origem).

Usados por `fliperos-mkiso.sh --with-15khz-kernel` como alternativa ao
método EDID-only (`crt15-edid.bin`) que o build usa por padrão. Diferença:
o EDID-only força o modo fixo no boot sem tocar no kernel; esse conjunto de
patches habilita troca dinâmica de modo via KMS sem X (patch 06,
"groovyarcade kms enabler"), que o EDID-only não garante.

## Pasta `6.12/`

Alvo: kernel.org vanilla **6.12.104** (série Longterm, patch set ativamente
mantido). Escolhido em vez do 6.6 porque o FliperOS passou a usar Ubuntu
24.04 (noble) como base — cujo próprio kernel GA já é 6.8 — e o 6.12 cobre
mais gerações de hardware AMD (DCN3, ver tabela) que o 6.6 não cobre. Se
`KERNEL_15KHZ_VERSION` em `fliperos-mkiso.sh` for atualizado para outra
série, vendorizar a pasta correspondente do repositório D0023R junto — os
patches são específicos de versão.

| Arquivo | Escopo |
| --- | --- |
| `01_linux_15khz.patch` | Patch principal — suporte a modo 15kHz (DRM core) |
| `02_linux_15khz_interlaced_mode_fix.patch` | Fix de vertical blank interrupt — necessário para o driver **radeon** |
| `03_linux_15khz_dcn1_dcn2_dcn3_interlaced_mode_fix.patch` | Habilita modo entrelaçado — **amdgpu/DCN1-3** (standalone/APU, inclui placas mais recentes que o patch set do 6.6 não cobria) |
| `04_linux_15khz_dce_interlaced_mode_fix.patch` | Habilita modo entrelaçado — **amdgpu/DCE** (placas mais antigas) |
| `05_linux_15khz_amdgpu_pll_fix.patch` | Fix de cálculo de PLL — **amdgpu** |
| `06_linux_switchres_kms_drm_modesetting.patch` | Manipulação de modesetting via KMS para uso do Switchres sem X (`drmkms`) — o recurso que motivou adotar esse caminho |
| `07_linux_15khz_fix_ddc.patch` | Desde o kernel 6.7 — corrige kernel oops ao sondar DDC sem adaptador conectado (não existe no patch set do 6.6) |

Cobre **radeon** e **amdgpu** (DCE e DCN1-3). Não há patch de **i915/Intel**
nesse conjunto — o hack de iGPU Intel mencionado no escopo de hardware do
projeto é independente disso.

Aplicação: `patch -p1 < arquivo.patch`, a partir da raiz da árvore de
source do kernel extraída, em ordem numérica.
