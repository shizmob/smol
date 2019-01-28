; vim: set ft=nasm:

%define ORIGIN 0x400000
;org ORIGIN
bits 32

extern _smol_total_size
[section .header]

%include "elf.inc"

header:
    ; e_ident
    db 0x7F, "ELF"
    db EI_CLASS, EI_DATA, EI_VERSION, EI_OSABI
    db EI_OSABIVERSION
    times 7 db 0       ; EI_PAD, ld.so is a busta and won't let us use our leet
                       ; group tags for padding bytes :(
    dw ELF_TYPE        ; e_type: 2 = executable
    dw ELF_MACHINE     ; e_machine: 3 = x86
    dd EI_VERSION      ; e_version
    dd _smol_start     ; e_entry
    dd (.segments - header) ; e_phoff
    dd 0               ; e_shoff
    dd 0               ; e_flags
    dw (.segments - header) ; e_ehsize
    dw (.segments.load - .segments.dynamic) ; e_phentsize
.segments:
%ifdef USE_INTERP
.segments.interp:
    dd PT_INTERP          ; {e_phnum: 2, e_shentsize: 0}, p_type
    dd (.interp - header) ; {e_shnum: <junk>, e_shstrnd: <junk>}, p_offset
    dd .interp, .interp   ; p_vaddr, p_paddr
    dd (.interp.end-.interp) ; p_filesz
    dd (.interp.end-.interp) ; p_memsz
    dd 0,0                ; p_flags, p_align
%endif
.segments.dynamic:
    dd PT_DYNAMIC          ; {e_phnum: 2, e_shentsize: 0}, p_type
    dd (.dynamic - header) ; {e_shnum: <junk>, e_shstrnd: <junk>}, p_offset
    dd .dynamic, 0         ; p_vaddr, p_paddr
    dd (.dynamic.end - .dynamic) ; p_filesz
    dd (.dynamic.end - .dynamic) ; p_memsz
    dd 0, 0                ; p_flags, p_align
.segments.load:
    dd PT_LOAD          ; p_type: 1 = PT_LOAD
    dd 0                ; p_offset
    dd ORIGIN, 0        ; p_vaddr, p_paddr
    dd _smol_total_size ; p_filesz
    dd _smol_total_size ; p_memsz
    dd (PHDR_R | PHDR_W | PHDR_X) ; p_flags
    dd 0x1000           ; p_align
.segments.end:
%ifdef USE_INTERP
.interp:
    db "/lib/ld-linux.so.2",0
.interp.end:
%endif
.dynamic:
.dynamic.strtab:
    dd DT_STRTAB ; d_tag
    dd _symbols  ; d_un.d_ptr
.dynamic.symtab:
    ; this is required to be present or ld.so will crash, but it can be bogus
    dd DT_SYMTAB ; d_tag: 6 = DT_SYMTAB
    dd 0         ; d_un.d_ptr

