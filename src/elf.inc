; vim: set ft=nasm:

%if __BITS__ == 32
%define EI_CLASS        (1) ; 1 == 32-bit
%else
%define EI_CLASS        (2) ; 2 == 64-bit
%endif
%define EI_DATA         (1) ; 1 == little-endian
%define EI_VERSION      (1) ; current
%define EI_OSABI        (3) ; Linux
%define EI_OSABIVERSION (1) ; current

%define ELF_TYPE (2) ; 2 == executable

%ifndef ELF_MACHINE
%if __BITS__ == 32
%define ELF_MACHINE ( 3) ;  3 == i386
%else
%define ELF_MACHINE (62) ; 62 == x86_64
%endif
%endif

%define PT_LOAD    (1)
%define PT_DYNAMIC (2)
%define PT_INTERP  (3)

%define PHDR_R (4)
%define PHDR_W (2)
%define PHDR_X (1)

%define DT_STRTAB ( 5)
%define DT_SYMTAB ( 6)
%define DT_DEBUG  (21)

%define ST_NAME_OFF  ( 0)
;  ,---- not 16?
; v
%define ST_VALUE_OFF ( 8)
%define SYMTAB_SIZE  (24)

