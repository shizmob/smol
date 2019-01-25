; vim: set ft=nasm:
%define ORIGIN 0x400000

extern _size
[section .header]

header:
        ; e_ident
        db 0x7F, "ELF"     ; EI_MAG0-EI_MAG3
        db 1               ; EI_CLASS: 1 = 32-bit
        db 1               ; EI_DATA:  1 = LSB
        db 1               ; EI_VERSION
        db 3               ; EI_OSABI: 3 = Linux
        db 1               ; EI_OSABIVERSION
        times 7 db 0       ; EI_PAD, ld.so is a busta and won't let us use our leet group tags for padding bytes :(
        ; e_type: 2 = executable
        dw 2
        ; e_machine: 3 = x86
        dw 3
        ; e_version
        dd 1
        ; e_entry
        dd _start
        ; e_phoff
        dd (.segments - header)
        ; e_shoff
        dd 0
        ; e_flags
        dd 0
        ; e_ehsize
        dw (.segments - header)
        ; e_phentsize
        dw (.segments.load - .segments.dynamic)
.segments:
; TODO: .segments.interp
.segments.dynamic:
        ; {e_phnum: 2, e_shentsize: 0}, p_type: 2 = PT_DYNAMIC
        dd 2
        ; {e_shnum: <junk>, e_shstrnd: <junk>}, p_offset
        dd (.dynamic - header)
        ; p_vaddr
        dd .dynamic
        ; p_paddr
        dd 0
        ; p_filesz
        dd (.dynamic.end - .dynamic)
        ; p_memsz
        dd (.dynamic.end - .dynamic)
        ; p_flags, p_align
        dq 0
.segments.load:
        ; p_type: 1 = PT_LOAD
        dd 1
        ; p_offset
        dd 0
        ; p_vaddr
        dd ORIGIN
        ; p_paddr
        dd 0
        ; p_filesz
        dd _size
        ; p_memsz
        dd _size
        ; p_flags: 1 = execute, 4 = read
        dd (1 | 2 | 4)
        ; p_align
        dd 0x1000
.segments.end:
.dynamic:
.dynamic.strtab:
        ; d_tag: 5 = DT_STRTAB
        dd 5
        ; d_un.d_ptr
        dd _symbols
.dynamic.symtab:
        ; this is required to be present or ld.so will crash, but it can be bogus
        ; d_tag: 6 = DT_SYMTAB
        dd 6
        ; d_un.d_ptr
        dd 0
