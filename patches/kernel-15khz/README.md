# Patches de kernel 15kHz (D0023R)

Vendorizados de <https://github.com/D0023R/linux_kernel_15khz>, commit
`ece6ef15eca9480eaf75870a44764f47118e9cfe` (2026-09-29), licença GPLv3
(`LICENSE` do repositório de origem). É o mesmo conjunto que o GroovyArcade
aplica no pacote `linux-15khz`.

O `fliperos-mkiso.sh` sempre compila o kernel com eles: é o que dá o modo de
boot `video=640x480iS` (e os demais da tabela) usado pelo menu do Limine e
pelo `fliperos-setup`, igual ao GroovyArcade.

## Pasta `6.18/`

Alvo: kernel.org vanilla **6.18.54** (série Longterm). Escolhida por ser a
série LTS mais nova com o conjunto completo, incluindo o patch 09 (entrelaçado
em Intel Gen9). Se `KERNEL_15KHZ_VERSION` em `fliperos-mkiso.sh` mudar de
série, vendorizar a pasta correspondente do D0023R junto — os patches são
específicos de versão.

| Arquivo | Escopo |
| --- | --- |
| `01_linux_15khz.patch` | Patch principal: flag `S` no `video=` e a tabela fixa de modos de baixo dotclock (15/25/31 kHz) |
| `02_linux_15khz_interlaced_mode_fix.patch` | Interrupção de vertical blank em modo entrelaçado — driver **radeon** |
| `03_linux_15khz_dcn1_dcn2_dcn3_interlaced_mode_fix.patch` | Entrelaçado em **amdgpu/DCN1-3** (placas e APUs) |
| `04_linux_15khz_dce_interlaced_mode_fix.patch` | Entrelaçado em **amdgpu/DCE** (placas mais antigas) |
| `05_linux_15khz_amdgpu_pll_fix.patch` | Cálculo de PLL — **amdgpu** |
| `06_linux_switchres_kms_drm_modesetting.patch` | Troca de modo via KMS para o Switchres sem X (`drmkms`) |
| `07_linux_15khz_fix_ddc.patch` | Oops ao sondar DDC sem adaptador conectado |
| `08_linux_15khz_interlace_force_even.patch` | Campos pares no entrelaçado em **amdgpu/DCN1** |
| `09_linux_15khz_i915_gen9_interlace.patch` | Entrelaçado em **Intel Gen9** com `i915.no_ytiled_scanout=1` (a entrada "Intel 15 kHz" do boot passa esse parâmetro) |

Cobre **radeon**, **amdgpu** (DCE e DCN1-3) e, pelo 09, **i915 Gen9**.
NVIDIA (nouveau) e as demais Intel usam a super resolução `1280x480iS`.

Aplicação: `patch -p1 < arquivo.patch`, a partir da raiz da árvore do kernel,
em ordem numérica.
