; vim: set ft=nasm:

%if __BITS__ == 32
%define L_ADDR_OFF           (   0)
%define L_NAME_OFF           (   4)
%define L_LD_OFF             (   8)
%define L_NEXT_OFF           (0x0C)
%define L_INFO_OFF           (0x20)
;%define L_INFO_DT_SYMTAB_OFF ()

%define LF_ENTRY_OFF          (  340)
%define LF_NBUCKETS_OFF       (0x178)
%define LF_GNU_BUCKETS_OFF    (0x188)
%define LF_GNU_CHAIN_ZERO_OFF (0x18C)

%define L_GNU_BUCKETS_SZ      (4)
%define L_GNU_CHAIN_ZERO_SZ   (4)

; old defs:

%define LM_NAME_OFFSET           0x4
%define LM_NEXT_OFFSET           0xC
%define LM_ADDR_OFFSET           0
%define LM_INFO_OFFSET           0x20

; by default, use the offset 'correction' from glibc 2.28
%define LM_ENTRY_OFFSET_BASE     340

%define LM_NBUCKETS_OFFSET       0x178
%define LM_GNU_BUCKETS_OFFSET    0x188
%define LM_GNU_CHAIN_ZERO_OFFSET 0x18C

%define DT_VALUE_OFFSET          0x4
%define DYN_PTR_OFFSET           0x4

%define DT_SYMSIZE_SHIFT         4

%else ;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
%define L_ADDR_OFF           (  0)
%define L_NAME_OFF           (  8)
%define L_LD_OFF             ( 16)
%define L_NEXT_OFF           ( 24)
%define L_INFO_OFF           ( 64)
%define L_INFO_DT_SYMTAB_OFF (112)

%define LF_ENTRY_OFF          (688)
%define LF_NBUCKETS_OFF       (756)
%define LF_GNU_BUCKETS_OFF    (776)
%define LF_GNU_CHAIN_ZERO_OFF (784)

%define L_GNU_BUCKETS_SZ     (  4)
%define L_GNU_CHAIN_ZERO_SZ  (  4)

%endif

%define ELF_SYM_SZ           (SYMTAB_SIZE)

