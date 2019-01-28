; vim: set ft=nasm:

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

%define DT_SYMTAB                0x6
%define DT_SYMSIZE_SHIFT         4

