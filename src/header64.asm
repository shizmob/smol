; vim: set ft=nasm:

%include "linkscr.inc"

[section .header]

%include "elf.inc"

ehdr:
    ; e_ident
    db 0x7F, "ELF"
    db EI_CLASS, EI_DATA, EI_VERSION, EI_OSABI
    db EI_OSABIVERSION
    times 7 db 0
    dw ELF_TYPE         ; e_type
    dw ELF_MACHINE      ; e_machine
    dd EI_VERSION       ; e_version
    dq _smol_start      ; e_entry
    dq phdr - ehdr      ; e_phoff
    dq 0                ; e_shoff
    dd 0                ; e_flags
    dw ehdr.end - ehdr  ; e_ehsize
    dw phdr.load - phdr.dynamic ; e_phentsize

%ifdef USE_NX
    %ifdef USE_INTERP
    dw 4                ; e_phnum
    %else
    dw 3                ; e_phnum
    %endif
    dw 0, 0, 0          ; e_shentsize, e_shnum, e_shstrndx
ehdr.end:
%endif

phdr:
%ifdef USE_INTERP
phdr.interp:
    dd PT_INTERP        ; p_type    ; e_phnum, e_shentsize
    dd 0                ; p_flags   ; e_shnum, e_shstrndx
    %ifndef USE_NX
ehdr.end:
    %endif
    dq interp - ehdr    ; p_offset
    dq interp, interp   ; p_vaddr, p_paddr
    dq interp.end - interp ; p_filesz
    dq interp.end - interp ; p_memsz
    dq 0                ; p_align
%endif
phdr.dynamic:
    dd PT_DYNAMIC       ; p_type    ; e_phnum, e_shentsize
    dd 0                ; p_flags   ; e_shnum, e_shstrndx
%ifndef USE_INTERP
ehdr.end:
%endif
    dq dynamic - ehdr   ; p_offset
    dq dynamic, 0       ; p_vaddr, p_paddr
    dq dynamic.end - dynamic ; p_filesz
    dq dynamic.end - dynamic ; p_memsz
    dq 0                ; p_align
%ifndef USE_NX
phdr.load:
    dd PT_LOAD          ; p_type
    dd PHDR_R | PHDR_W | PHDR_X ; p_flags
    dq 0                ; p_offset
    dq ehdr, 0          ; p_vaddr, p_paddr
    dq _smol_total_memsize ; p_filesz
    dq _smol_total_memsize ; p_memsz
    dq 0x1000           ; p_align
%else
phdr.load:
    dd PT_LOAD
    dd PHDR_R | PHDR_X
    dq 0
    dq ehdr, 0
    dq _smol_textandheader_size
    dq _smol_textandheader_size
    dq 0x1000 ; let's hope this works
phdr.load2:
    dd PT_LOAD
    dd PHDR_R | PHDR_W
    dq _smol_data_off
    dq _smol_data_start, 0
    dq _smol_dataandbss_size
    dq _smol_dataandbss_size
    dq 0x1000
%endif
phdr.end:

%ifdef USE_INTERP
interp:
    db "/lib64/ld-linux-x86-64.so.2", 0
interp.end:
%endif

dynamic:
dynamic.strtab:
    dq DT_STRTAB        ; d_tag
    dq _symbols         ; d_un.d_ptr
dynamic.symtab:
    dq DT_SYMTAB        ; d_tag
    dq 0                ; d_un.d_ptr

