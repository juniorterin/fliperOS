; O hook do ATOM-15 v1.6 (Antonio Giner "Calamity", atom-15.bas, bios_hook), a
; fonte dos bytes de HOOK em config/fliperos-atom15. Depois de cada troca de modo
; da BIOS (INT 10h, padrao e VESA) ele liga o entrelacado nos registradores da
; placa, se a tabela do fim diz que o modo e entrelacado.
;
; E montado em 32 bits de proposito, como no original: roda em modo real, onde o
; prefixo 66h inverte o tamanho (o "add ax, bx" daqui e um add eax, ebx la). Os
; zeros sao preenchidos pelo patcher (config/fliperos-atom15, bios_hook).
;
;   nasm -f bin -o hook.bin -l hook.lst tools/atom15-hook.asm
;
; Da 532 bytes, o que o Readme do ATOM-15 v1.6 pede de espaco. Os db sem rotulo
; sao as codificacoes do montador do PowerBASIC, lidas de uma BIOS feita pelo
; atom-15.exe (tools/atom15-check.py), onde o nasm escolheria outras.
bits 32
hook_start:

standard_bios_hook:
        cmp ah, 0
        pushfd
standard_bios_service:
        db 0xe8, 0, 0                   ; call do servico normal de video
        popfd
        jz short standard_bios_service_mod
        retn
standard_bios_service_mod:
        pushfd
        pushad
        and al, 0x7f
        movzx ebx, al
get_standard_modes_offset:
        db 0x81, 0xc3, 0xff, 0xff       ; add bx, tabela dos modos padrao
        jmp short set_interlace
vesa_bios_hook:
        cmp al, 2
        pushfd
vesa_bios_service:
        db 0xe8, 0, 0                   ; call do servico VESA
        popfd
        jz short vesa_bios_service_mod
        retn
vesa_bios_service_mod:
        pushfd
        pushad
        db 0x81, 0xE3, 0xFF, 0x3F       ; and bx, 0x3fff
        db 0x81, 0xEB, 0x00, 0x01       ; sub bx, 0x100
get_vesa_modes_offset:
        db 0x81, 0xc3, 0xff, 0xff       ; add bx, tabela dos modos VESA
set_interlace:
        db 0x66, 0x33, 0xC9            ; xor cx, cx
        db 0x2e, 0x8a, 0x0F             ; mov cl, cs:[bx]
        and cl, 1

get_pci_bus:
        db 0x2E, 0x8B, 0x1E, 0, 0       ; mov bx, cs:[barramento PCI]
        mov dl, 0x20                    ; BAR4
call_get_BAR4:
        db 0xe8, 0, 0                   ; call get_BAR
        test al, 1
        jnz short found_BAR
        mov dl, 0x14                    ; BAR1
call_get_BAR1:
        db 0xe8, 0, 0                   ; call get_BAR
found_BAR:
        db 0x8A, 0xF4                  ; mov dh, ah
        db 0x32, 0xD2                  ; xor dl, dl
        db 0x66, 0x33, 0xDB            ; xor bx, bx
crtc0_enable_interlace:
        db 0x68, 0, 0                   ; push deslocamento da CRTC 0
call_crtc0:
        db 0xe8, 0, 0                   ; call crtc_program_registers
crtc1_enable_interlace:
        db 0x68, 0, 0
call_crtc1:
        db 0xe8, 0, 0
crtc2_enable_interlace:
        db 0x68, 0, 0
call_crtc2:
        db 0xe8, 0, 0
crtc3_enable_interlace:
        db 0x68, 0, 0
call_crtc3:
        db 0xe8, 0, 0
crtc4_enable_interlace:
        db 0x68, 0, 0
call_crtc4:
        db 0xe8, 0, 0
crtc5_enable_interlace:
        db 0x68, 0, 0
call_crtc5:
        db 0xe8, 0, 0
set_interlace_end:
        popad
        popfd
        retn
get_BAR:
        mov ah, 0x80
        db 0x8A, 0xC7                  ; mov al, bh
        shl ax, 0x10
        db 0x8A, 0xE3                  ; mov ah, bl
        db 0x8A, 0xC2                  ; mov al, dl
        and al, 0xFC
        db 0xBA, 0xF8, 0x0C             ; mov dx, 0xcf8
        out dx, ax
        db 0xBA, 0xFC, 0x0C             ; mov dx, 0xcfc
        in ax, dx
        retn
crtc_program_registers:
        db 0x8B, 0xEC                  ; mov ebp, esp
        db 0x66, 0x33, 0xDB            ; xor bx, bx
        db 0x8B, 0x5E, 0x02             ; mov bx, [bp+2]
        push ecx
crtc_enable_interlace:
        test cl, 1
        jz short crtc_enable_composite_sync
crtc_interlace_control_reg:
        db 0x66, 0xB8, 0, 0, 0, 0       ; mov eax, registrador do entrelacado
        db 0x66, 0x03, 0xC3            ; add ax, bx
        db 0x66, 0xB9, 1, 0, 0, 0       ; mov ecx, 1
call_set_value1:
        db 0xe8, 0, 0                   ; call set_value
data_format_reg:
        db 0x66, 0xB8, 0, 0, 0, 0       ; mov eax, registrador do formato
        db 0x66, 0x03, 0xC3            ; add ax, bx
interleave_enable_set:
        db 0x66, 0xB9, 0, 0, 0, 0       ; mov ecx, bit do interleave
call_set_value2:
        db 0xe8, 0, 0                   ; call set_value
crtc_enable_composite_sync:
        jmp short crtc_program_registers_exit
crtc_h_sync_a_cntl_reg:
        db 0x66, 0xB8, 0, 0, 0, 0       ; mov eax, registrador do hsync
        db 0x66, 0x03, 0xC3            ; add ax, bx
crtc_composite_enable_set:
        db 0x66, 0xB9, 0, 0, 0, 0       ; mov ecx, bit do sync composto
call_set_value3:
        db 0xe8, 0, 0                   ; call set_value
crtc_program_registers_exit:
        pop ecx
        retn 2
set_value:
        push bx
        push ax
        mov dl, 0
        out dx, ax
        mov dl, 4
        in ax, dx
        db 0x66, 0x0B, 0xC1            ; or ax, cx
        db 0x66, 0x87, 0xC3            ; xchg ax, bx
        pop ax
        mov dl, 0
        out dx, ax
        db 0x66, 0x87, 0xC3            ; xchg ax, bx
        mov dl, 4
        out dx, ax
        pop bx
        retn
checksum_fix:
        db 0
standard_modes:
        times 20 db 0
vesa_modes:
        times 256 db 0
hook_end:
