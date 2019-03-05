; vim: set ft=nasm:

; TODO: r13 -> something else
; TODO: smaller!!

%define R10_BIAS (0x2B8)

%include "rtld.inc"

%ifdef ELF_TYPE
[section .text.startup.smol]
%else
; not defined -> debugging!
[section .text]
%endif

; r9 : ptrdiff_t glibc_vercompat_extra_hi_field_off
; r10: struct link_map* entry + far correction factor
; r12: struct link_map* entry
; r14: struct link_map* root
; r13: _dl_fini address (reqd by the ABI)

%ifndef ELF_TYPE
extern _symbols
global _start
_start:
%endif
_smol_start:
%ifdef USE_DL_FINI
   xchg r13, rdx ; _dl_fini
%endif

%ifdef USE_DT_DEBUG
    mov r12, [rel _DEBUG]
    mov r12, [r12 + 8]
%else
    mov r12, [rsp -  8]        ; return address of _dl_init
    mov ebx, dword [r12 - 20] ; decode part of 'mov rdi, [rel _rtld_global]'
    mov r12, [r12 + rbx - 16]  ; ???
%endif
        ; struct link_map* root = r12
%ifdef SKIP_ENTRIES
    mov r12, [r12 + L_NEXT_OFF] ; skip this binary
;   mov r12, [r12 + L_NEXT_OFF] ; skip the vdso
        ; the second one isn't needed anymore, see code below (.next_link)
%endif

        mov rdi, r12
       push -1
        pop rcx
       ;mov rax, _smol_start
        lea rax, [rel _smol_start] ; TODO: make offset positive!
repne scasq
        sub rdi, r12
        sub rdi, LF_ENTRY_OFF+8
       xchg r9 , rdi

   ;mov edi, _symbols
    lea edi, [rel _symbols]

%ifdef LIBSEP
            ; for (rdi = (uint8_t*)_symbols; *rdi; ++rdi) {
     .next_needed:
        cmp byte [rdi], 0
         je .needed_end

            ; do { // iter over the link_map
         .next_link:
                ; entry = entry->l_next;
            mov r12, [r12 + L_NEXT_OFF] ; skip the first one (this is our main
                                        ; binary, it has no symbols)
            lea r10, [r12 + r9  + R10_BIAS]

                ; keep the current symbol in a backup reg
           push rdi
            pop rdx

                ; r11 = basename(rsi = entry->l_name)
            mov rsi, [r12 + L_NAME_OFF]
         .basename:
           push rsi
            pop r11
         .basename.next:
          lodsb
            cmp al, '/'
          cmove r11, rsi
             or al, al
            jnz short .basename.next
         .basename.done:

                ; and place it back
           push rdx
           push rdx
            pop rdi ; rdi == _symbol
            pop rsi

                ; strcmp(rsi, r11) -> flags; rsi == first hash if matches
         .strcmp:
          lodsb
             or al, al
             jz short .strcmp.done
            sub al, byte [r11]
         cmovnz rsi, rdx
            jnz short .next_link;.strcmp.done
            inc r11
            jmp short .strcmp
         .strcmp.done:
           xchg rsi, rdi

                ; if (strcmp(...)) goto next_link;
        ;cmovnz r12, [r12 + L_NEXT_OFF] ; this is guaranteed to be nonzero
           ;jnz short .next_link ; because otherwise ld.so would have complained

                ; now we have the right link_map of the library, so all we have
                ; to do now is to find the right symbol addresses corresponding
                ; to the hashes.

                ; do {
         .next_hash:
                ; if (!*phash) break;
         ;lodsq
            mov eax, dword [rdi]
             or eax, eax
             jz short .next_needed ; done the last hash, so move to the next lib

;link_symbol(struct link_map* entry = r12, size_t* phash = rsi, uint32_t hash = eax)

           push rax
            pop r11
                ; uint32_t bkt_ind(edx) = hash % entry->l_nbuckets
            xor edx, edx
            mov ecx, dword [r10 + LF_NBUCKETS_OFF - R10_BIAS]
            div ecx

                ; shift left because we don't want to compare the lowest bit
            shr r11, 1

                ; uint32_t bucket(edx) = entry->l_gnu_buckets[bkt_ind]
            mov r8, [r10 + LF_GNU_BUCKETS_OFF - R10_BIAS]
            mov edx, dword [r8 + rdx * 4]

                ; do {
            .next_chain:
                    ; uint32_t luhash(ecx) = entry->l_gnu_chain_zero[bucket] >> 1
                mov rcx, [r10 + LF_GNU_CHAIN_ZERO_OFF - R10_BIAS]
                mov ecx, dword [rcx + rdx * 4]
                shr ecx, 1

                    ; if (luhash == hash) break;
                cmp ecx, r11d
                 je short .chain_break
                    ; ++bucket; } while (LIBSEP || (luhash & 1))
                inc edx
                jne short .next_chain
%else
; !LIBSEP
   push r12
    pop r11 ; back up link_map root
    .next_hash:
     ;lodsq
        mov eax, dword [rdi]
         or al, al
         jz short .needed_end
       push r11
       push rax
       push rax
        pop rbx
        pop r14
        pop r12
            ; shift left because we don't want to compare the lowest bit
        shr ebx, 1

        .next_link:
            mov r12, [r12 + L_NEXT_OFF]

            lea r10, [r12 + r9  + R10_BIAS]
                ; uint32_t bkt_ind(edx) = hash % entry->l_nbuckets
            xor edx, edx
           push r14
            pop rax
            mov ecx, dword [r10 + LF_NBUCKETS_OFF - R10_BIAS]
            div ecx

                ; uint32_t bucket(edx) = entry->l_gnu_buckets[bkt_ind]
            mov r8 , [r10 + LF_GNU_BUCKETS_OFF - R10_BIAS]
            mov edx, dword [r8 + rdx * 4]

             or edx, edx
             jz short .next_link

            .next_chain:
                    ; uint32_t luhash(ecx) = entry->l_gnu_chain_zero[bucket] >> 1
                mov rcx, [r10 + LF_GNU_CHAIN_ZERO_OFF - R10_BIAS]
                mov ecx, dword [rcx + rdx * 4]

                    ; if (!(luhash & 1)) goto next_link; // nothing to be found in this lib.
                mov al, cl

                shr ecx, 1

                    ; if (luhash == hash) break;
                cmp ecx, ebx
                 je short .chain_break

                    ; ++bucket; } while (luhash & 1);
                and al, 1
                jnz short .next_link
                inc edx
                jmp short .next_chain
%endif

        .chain_break:
                ; ElfW(Sym)* symtab = entry->l_info[DT_SYMTAB]->d_un.d_ptr
                ; ElfW(Sym)* sym = &symtab[bucket]
                ; *phash = sym->st_value + entry->l_addr

                ; ElfW(Dyn)* dyn(rax) = entry->l_info[DT_SYMTAB]
            mov rax, [r12 + L_INFO_DT_SYMTAB_OFF]
                ; ElfW(Sym)* symtab(rax) = dyn->d_un.d_ptr
            mov rax, [rax + D_UN_PTR_OFF]
                ; ElfW(Addr) symoff(rax) = symtab[bucket].st_value
            lea rdx, [rdx + rdx * 2]
            mov rax, [rax + rdx * 8 + ST_VALUE_OFF]
                ; void* finaladdr(rax) = symoff + entry->l_addr
            mov rcx, [r12 + L_ADDR_OFF]
            add rax, rcx

                ; *phash = finaladdr
           ;mov [rsi-8], rax
;           mov [rsi], rax
;         lodsq
          stosq

            ; } while (1)
        jmp short .next_hash

.needed_end:
   ;xor rbp, rbp ; still 0 from _dl_start_user
    mov rdi, rsp
%ifdef ALIGN_STACK
   push rax
%endif
%ifdef USE_DL_FINI
   xchg rsi, r13 ; _dl_fini
%endif
        ; fallthru to _start

