; vim: set ft=nasm:

;%define R10_BIAS (0x2B4)
%define R10_BIAS (0x2B4+0x40)

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

       push _smol_start
       push r12
       push -1
        pop rcx
        pop rdi
        pop rax
repne scasd ; technically, scasq should be used, but ehhhh
        sub rdi, r12
        sub rdi, LF_ENTRY_OFF+4
       xchg r9, rdi

   push _symbols
        ; back up link_map root
   push r12
    pop r11
    pop rdi

;.loopme: jmp short .loopme ; debugging
    .next_hash:
        mov r14d, dword [rdi]
            ; assume we need at least one function
;        or al, al
;        jz short .needed_end
        mov r12, r11
;      push r11
       push r14
        pop rbx
;       pop r12
            ; shift left because we don't want to compare the lowest bit
        shr ebx, 1

        .next_link:
            mov r12, [r12 + L_NEXT_OFF]

            lea r10, [r12 + r9 + R10_BIAS]
                ; uint32_t bkt_ind(edx) = hash % entry->l_nbuckets
            xor edx, edx
           push r14
            pop rax
            mov ecx, dword [r10 + LF_NBUCKETS_OFF - R10_BIAS]
            div ecx

                ; uint32_t bucket(edx) = entry->l_gnu_buckets[bkt_ind]
            mov r8 , [r10 + LF_GNU_BUCKETS_OFF - R10_BIAS]
            mov ecx, dword [r8 + rdx * 4]

                ; can be ignored apparently?
;         jecxz .next_link

            .next_chain:
                    ; uint32_t luhash(ecx) = entry->l_gnu_chain_zero[bucket] >> 1
                mov rdx, [r10 + LF_GNU_CHAIN_ZERO_OFF - R10_BIAS]
                mov edx, dword [rdx + rcx * 4]

                    ; TODO: make this not suck. (maybe using bt*?)
                mov al, dl

                shr edx, 1
                    ; if (luhash == hash) break;
                cmp edx, ebx
                 je short .chain_break

                    ; ++bucket; } while (luhash & 1);
                and al, 1
                jnz short .next_link

                inc ecx
                jmp short .next_chain

        .chain_break:
                ; ElfW(Sym)* symtab = entry->l_info[DT_SYMTAB]->d_un.d_ptr
                ; ElfW(Sym)* sym = &symtab[bucket]
                ; *phash = sym->st_value + entry->l_addr

                ; ElfW(Dyn)* dyn(rax) = entry->l_info[DT_SYMTAB]
            mov rax, [r12 + L_INFO_DT_SYMTAB_OFF]
                ; ElfW(Sym)* symtab(rax) = dyn->d_un.d_ptr
            mov rax, [rax + D_UN_PTR_OFF]
                ; ElfW(Addr) symoff(rax) = symtab[bucket].st_value
            lea rdx, [rcx + rcx * 2]
            mov rax, [rax + rdx * 8 + ST_VALUE_OFF]
                ; void* finaladdr(rax) = symoff + entry->l_addr
            add rax, [r12 + L_ADDR_OFF]

                ; *phash = finaladdr
          stosq
            cmp word [rdi], 0
            jne short .next_hash
            ; } while (1)
;       jmp short .next_hash

.needed_end:
;  int3 ; debugging
;   xor rbp, rbp ; still 0 from _dl_start_user
%ifndef NO_START_ARG
        ; arg for _start
    mov rdi, rsp
%endif
%ifdef ALIGN_STACK
       ; apparently not needed?
; push rax
%endif
%ifdef USE_DL_FINI
   xchg rsi, r13 ; _dl_fini
%endif
        ; fallthru to _start

