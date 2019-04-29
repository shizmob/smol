; vim: set ft=nasm et:

%include "rtld.inc"

; TODO
%define R10_BIAS (0)

%ifdef ELF_TYPE
[section .text.startup.smol]
%else
; not defined -> debugging!
[section .text]
%endif

%ifndef USE_DNLOAD_LOADER
_smol_linkmap:
    dd 0
_smol_linkoff:
    dd 0
%endif

_smol_start:
%ifdef USE_DL_FINI
   push edx ; _dl_fini
%endif
        ; try to get the 'version-agnostic' pffset of the stuff we're
        ; interested in

%ifdef USE_DT_DEBUG
    mov eax, [rel _DEBUG]
    mov eax, [eax + 4]
%endif

%ifdef SKIP_ENTRIES
    mov eax, [eax + LM_NEXT_OFFSET] ; skip this binary
;   mov eax, [eax + LM_NEXT_OFFSET] ; skip the vdso
%endif

%ifdef USE_JMP_BYTES
   push _symbols+1
%else
   push _symbols
%endif

%ifdef USE_DNLOAD_LOADER
    ; TODO: borked!
    pop ebp
    pop edi

    .next_hash:
        mov ecx, [edi]
            ; assume it's nonzero
       push ebp
        pop edx
            ; edx: hash
            ; ebx: link_map* chain

        .next_link:
;           pop edx
            mov edx, [edx + L_NEXT_OFF]
                ; ElfW(Dyn)* dyn(esi) = ebx->l_ld
            mov esi, [edx + L_LD_OFF]

           push edx
                ; get strtab off
            .next_dyn:
              lodsd
                cmp al, DT_STRTAB
              lodsd
                jne short .next_dyn

                ; void* addr(edx) = ebx->l_addr
                ; const char* strtab(ebx)=lookup(esi,DT_STRTAB);
            mov edx, [edx + L_ADDR_OFF]
            cmp eax, edx
            jae short .noreldynaddr
            add eax, edx
        .noreldynaddr:
           push eax
            pop ebx

                ; const ElfW(Sym)* symtab(edx) = lookup(esi, DT_SYMTAB);
          lodsd ; SYMTAB d_tag
          lodsd ; SYMTAB d_un
            cmp eax, edx
            jae short .norelsymaddr
            add eax, edx
        .norelsymaddr:
           push eax
            pop edx

        .next_sym:
            mov esi, [edx + ST_NAME_OFF]
            add esi, ebx

           push ecx
%ifndef USE_HASH16
           push ebx
           push 33
           push 5381
            pop eax
            pop ebx
%else
            xor eax, eax
%endif
            xor ecx, ecx
        .nexthashiter:
                    ;
               xchg eax, ecx
              lodsb
                 or al, al
               xchg eax, ecx
                 jz short .breakhash

%ifndef USE_HASH16
               push edx
                mul ebx
                pop edx
;               add eax, ecx
%else
                ror ax, 2
;               add ax, cx
%endif
                add eax, ecx
                jmp short .nexthashiter

        .breakhash:
%ifndef USE_HASH16
            pop ebx
%endif
            pop ecx
;%ifndef USE_HASH16
;           cmp ecx, eax
;%else
;           cmp  cx,  ax
;%endif
            cmp ecx, eax
             je short .hasheq

            add edx, SYMTAB_SIZE
            cmp edx, ebx
             jb short .next_sym
            pop edx
            jmp short .next_link

        .hasheq:
            mov eax, [edx + ST_VALUE_OFF]
            pop edx
%ifdef SKIP_ZERO_VALUE
             or eax, eax
             jz short .next_link
%endif
            mov esi, [edx + L_ADDR_OFF]
           ;cmp eax, esi
           ; jb short .hasheqnorel
            add eax, esi
        .hasheqnorel:
           ;add eax, [edx + L_ADDR_OFF] ; TODO: CONDITIONAL!
          stosd
%ifdef USE_JMP_BYTES
            inc edi ; skip 0xE9 (jmp) offset
%endif
            cmp word [edi], 0
            jne short .next_hash

; if USE_DNLOAD_LOADER
%else
;.loopme: jmp short .loopme

        mov [_smol_linkmap], eax

        mov ebx, eax
        mov edi, eax
       push -1
        pop ecx
        mov eax, _smol_start
repne scasd
        sub edi, ebx
        sub edi, LM_ENTRY_OFFSET_BASE+4
        mov [_smol_linkoff], edi

        pop edi ; _symbols

            ; edi: _symbols
            ; ebp: link_map* root
           push ecx
    .next_hash:
            pop ecx
            mov ecx, [edi]

            mov ebp, [_smol_linkmap]
                ; ecx: hash (assumed nonzero)
                ; ebp: link_map* chain

               push ecx
        .next_link:
                pop ecx
                mov ebp, [ebp + L_NEXT_OFF]
                mov esi, ebp
                add esi, [_smol_linkoff]

                    ; edx: btk_ind
               push ecx
               push ecx
               push ecx
                pop eax
                mov ecx, [esi + LF_NBUCKETS_OFF]
                xor edx, edx
                div ecx
                pop ecx
                shr ecx, 1

                    ; ebx: bucket
                mov ebx, [esi + LF_GNU_BUCKETS_OFF]
                mov ebx, [ebx + edx * 4]

                .next_chain:
                        ; edx: luhash
                    mov edx, [esi + LF_GNU_CHAIN_ZERO_OFF]
                    mov edx, [edx + ebx * 4]

                        ; ecx: hash
                    mov al, dl

                    shr edx, 1
                    cmp edx, ecx
                     je short .chain_break

                    and al, 1
                    jnz short .next_link

                    inc ebx
                    jmp short .next_chain

            .chain_break:
                mov eax, [ebp + L_INFO_DT_SYMTAB_OFF]
                mov eax, [eax + D_UN_PTR_OFF]
                lea eax, [eax + ebx * 8]
                mov eax, [eax + ebx * 8 + ST_VALUE_OFF]
%ifdef SKIP_ZERO_VALUE
                 or eax, eax
                 jz short .next_link
%endif

                add eax, [ebp + L_ADDR_OFF]
              stosd
%ifdef USE_JMP_BYTES
                inc edi
%endif
                cmp word [edi], 0
                jne short .next_hash

; if USE_DNLOAD_LOADER ... else ...
%endif

      ;xor ebp, ebp ; let's put that burden on the user code, so they can leave
                    ; it out if they want to

%ifdef USE_DL_FINI
       pop edx      ; _dl_fini
%endif
           ; move esp into eax, *then* increase the stack by 4, as main()
           ; expects a return address to be inserted by a call instruction
           ; (which we don't have, so we're doing a 1-byte fixup instead of a
           ; 5-byte call)
      push esp
       pop eax
      push eax
      push eax

      ;jmp short _start
           ; by abusing the linker script, _start ends up right here :)

