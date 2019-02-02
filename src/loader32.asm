; vim: set ft=nasm ts=8:

%include "rtld.inc"

%ifdef ELF_TYPE
[section .text.startup.smol]
%else
; not defined -> debugging!
[section .text]
%endif


_smol_start:

%ifdef USE_DL_FINI
       push edx ; _dl_fini
%endif
            ; try to get the 'version-agnostic' pffset of the stuff we're
            ; interested in
        mov ebx, eax
        mov esi, eax
.looper:
      lodsd
        cmp dword eax, _smol_start
        jne short .looper
        sub esi, ebx
        sub esi, LM_ENTRY_OFFSET_BASE+4 ; +4: take inc-after from lodsd into acct

       xchg ebp, ebx
       xchg ebx, esi
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

      ;xor ebp, ebp ; let's put that burden on the user code, so they can leave
                    ; it out if they want to

%ifdef USE_DL_FINI
       pop edx      ; _dl_fini
%endif
       sub esp, 20  ; put the stack where _start (C code) expects it to be
                    ; this can't be left out, because X needs the envvars

;.loopme: jmp short .loopme
      ;jmp short _start
           ; by abusing the linker script, _start ends up right here :)

