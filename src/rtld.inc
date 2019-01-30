; vim: set ft=nasm:

%if __BITS__ == 32
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

%define DT_SYMTAB                0x6

%else
%define L_ADDR_OFF           (  0)
%define L_NAME_OFF           (  8)
%define L_NEXT_OFF           ( 24)
%define L_INFO_OFF           ( 64)
%define L_INFO_DT_SYMTAB_OFF (112)

%define LF_ENTRY_OFF          (688)
%define LF_NBUCKETS_OFF       (756)
%define LF_GNU_BUCKETS_OFF    (776)
%define LF_GNU_CHAIN_ZERO_OFF (784)

%define L_GNU_BUCKETS_SZ     (  4)
%define L_GNU_CHAIN_ZERO_SZ  (  4)

%define D_UN_PTR_OFF         (  8)
%define ST_VALUE_OFF         (  8)

%define ELF_SYM_SZ           ( 24)
%define ELF_DYN_SZ           ( 16)
%endif

