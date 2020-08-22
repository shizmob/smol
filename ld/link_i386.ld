OUTPUT_FORMAT("elf32-i386")
OUTPUT_ARCH(i386)
SEARCH_DIR("/usr/i386-pc-linux-gnu/lib32"); SEARCH_DIR("/usr/x86_64-pc-linux-gnu/lib32"); SEARCH_DIR("/usr/lib"); SEARCH_DIR("/usr/local/lib"); SEARCH_DIR("/usr/i386-pc-linux-gnu/lib");

INCLUDE "link_common.ld"

