; vim: set ft=nasm et:

%include "rtld.inc"

%ifdef ELF_TYPE
[section .text.startup.smol]
%else
; not defined -> debugging!
[section .text]
%endif


_smol_start:
;.loopme: jmp short .loopme
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

   push _symbols
   push eax
%ifdef USE_DNLOAD_LOADER
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
        mov ebx, eax
        mov edi, eax
       push -1
        pop ecx
        mov eax, _smol_start
repne scasd
        sub edi, ebx
        sub edi, LM_ENTRY_OFFSET_BASE+4

       xchg ebp, ebx
       xchg ebx, edi;esi
        mov esi, _symbols

link: ; (struct link_map *root, char *symtable)
.do_library:          ; null library name means end of symbol table, we're done
              cmp byte [esi], 0
               jz .done
.find_map_entry:            ; compare basename(entry->l_name) to lib name, if so we got a match
                   push esi
                    mov esi, [ebp + LM_NAME_OFFSET]

.basename: ; (const char *s (esi))
                            mov edi, esi
                    .basename.cmp:
                          lodsb
                            cmp al, '/'
                          cmove edi, esi
                             or al, al
                            jnz short .basename.cmp
                    .basename.done:
                            pop esi
.basename.end:

.strcmp: ; (const char *s1 (esi), const char *s2 (edi))
                           push esi
                           push edi
                    .strcmp.cmp:
                          lodsb
                             or al, al
                             jz short .strcmp.done
                            sub al, [edi]
                            jnz short .strcmp.done
                            inc edi
                            jmp short .strcmp.cmp
                    .strcmp.done:
                            pop edi
                            pop esi
.strcmp.end:


                         jz short .process_map_entry
                            ; no match, next entry it is!
                        mov ebp, [ebp + LM_NEXT_OFFSET]
                        jmp short .find_map_entry
.process_map_entry:         ; skip past the name in the symbol table now to get to the symbols
                      lodsb
                         or al, al
                        jnz short .process_map_entry

.do_symbols:                ; null byte means end of symbols for this library!
                      lodsb
                       test al, al
                         jz short .do_library
                       push ebx
                       xchg ebx, edi

                    link_symbol: ; (struct link_map *entry, uint32_t *h)
                            mov ecx, esi

                                ; eax = *h % entry->l_nbuckets
                            mov eax, [ecx]
                            xor edx, edx
                            mov ebx, [ebp + edi + LM_NBUCKETS_OFFSET]
                            div ebx
                                ; eax = entry->l_gnu_buckets[edx]
                            mov eax, [ebp + edi + LM_GNU_BUCKETS_OFFSET]
                            mov eax, [eax + edx * 4]
                                ; *h |= 1
                             or word [ecx], 1
                    .check_bucket:      ; edx = entry->l_gnu_chain_zero[eax] | 1
                                    mov edx, [ebp + edi + LM_GNU_CHAIN_ZERO_OFFSET]
                                    mov edx, [edx + eax * 4]
                                     or edx, 1
                                        ; check if this is our symbol
                                    cmp edx, [ecx]
                                     je short .found
                                    inc eax
                                    jmp short .check_bucket
                    .found:     ; it is! edx = entry->l_info[DT_SYMTAB]->d_un.d_ptr
                            mov edx, [ebp + LM_INFO_OFFSET + DT_SYMTAB * 4]
                            mov edx, [edx + DYN_PTR_OFFSET]
                                ; edx = edx[eax].dt_value + entry->l_addr
                            shl eax, DT_SYMSIZE_SHIFT
                            mov edx, [edx + eax + DT_VALUE_OFFSET]
                            add edx, [ebp + LM_ADDR_OFFSET]
                            sub edx, ecx
                            sub edx, 4
                                ; finally, write it back!
                            mov [ecx], edx

                        pop ebx
                        add esi, 4
                        jmp short link.do_symbols
                inc esi
link.done:
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

