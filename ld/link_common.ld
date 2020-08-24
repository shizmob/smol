/*OUTPUT_FORMAT(binary)*/
ENTRY(_smol_start)

PHDRS {
	dyn     PT_DYNAMIC FLAGS(0); /* --- */
	interp  PT_INTERP  FLAGS(0); /* --- */
	rodttxt PT_LOAD    FLAGS(5); /* r-x */
	rwdt    PT_LOAD    FLAGS(6); /* rw- */
}

SECTIONS {
  . = 0x10000;
  _smol_origin = .;

  .header : { KEEP(*(.header)) } :rodttxt
  .dynamic : { *(.dynamic .rodata.dynamic) } :dyn :rodttxt
  .interp : { *(.interp .rodata.interp) } :interp /*:rodttxt*/

  _smol_text_start = .;
  _smol_text_off = _smol_text_start - _smol_origin;
  .text : {
     KEEP(*(.rodata.dynamic))
     KEEP(*(.rodata.interp .rodata.neededlibs))
     *(.rdata .rdata.* .rodata .rodata.*)
     KEEP(*(.text.startup.smol))
     KEEP(*(.text.startup._start))
     *(.text .text.*)
  } :rodttxt
  _smol_text_end = .;
  _smol_text_size = _smol_text_end - _smol_text_start;

  _smol_textandheader_size = _smol_text_end - _smol_origin;

  _smol_data_start = .;
  _smol_data_off = _smol_data_start - _smol_origin;
  .data : {
     KEEP(*(.data.smolgot))
     *(.data .data.* .tdata .tdata.*)
  } :rwdt

  .dynstuff : { *(.symtab .strtab .shstrtab .rel.text .got.plt .gnu.linkonce.* .plt .plt.got) } /*:dyn*/ :rodttxt
  _smol_data_end = .;
  _smol_data_size = _smol_data_end - _smol_data_start;

  _smol_total_filesize = . - _smol_origin;

  _smol_bss_start = .;
  _smol_bss_off = _smol_bss_start - _smol_origin;
  .bss : {
      *(.bss .bss.* .tbss .tbss.* .sbss .sbss.*)
  } :rwdt
  _smol_bss_end = .;
  _smol_bss_size = _smol_bss_end - _smol_bss_start;

  _smol_dataandbss_size = _smol_bss_end - _smol_data_start;

  _smol_total_memsize = . - _smol_origin;

  /* Stabs debugging sections.  */
  .stab          0 : { *(.stab) }
  .stabstr       0 : { *(.stabstr) }
  .stab.excl     0 : { *(.stab.excl) }
  .stab.exclstr  0 : { *(.stab.exclstr) }
  .stab.index    0 : { *(.stab.index) }
  .stab.indexstr 0 : { *(.stab.indexstr) }
  /*.comment       0 : { *(.comment) }*/
  /*.gnu.build.attributes : { *(.gnu.build.attributes .gnu.build.attributes.*) }*/
  /* DWARF debug sections.
     Symbols in the DWARF debugging sections are relative to the beginning
     of the section so we begin them at 0.  */
  /* DWARF 1 */
  .debug          0 : { *(.debug) }
  .line           0 : { *(.line) }
  /* GNU DWARF 1 extensions */
  .debug_srcinfo  0 : { *(.debug_srcinfo) }
  .debug_sfnames  0 : { *(.debug_sfnames) }
  /* DWARF 1.1 and DWARF 2 */
  .debug_aranges  0 : { *(.debug_aranges) }
  .debug_pubnames 0 : { *(.debug_pubnames) }
  /* DWARF 2 */
  .debug_info     0 : { *(.debug_info .gnu.linkonce.wi.*) }
  .debug_abbrev   0 : { *(.debug_abbrev) }
  .debug_line     0 : { *(.debug_line .debug_line.* .debug_line_end) }
  .debug_frame    0 : { *(.debug_frame) }
  .debug_str      0 : { *(.debug_str) }
  .debug_loc      0 : { *(.debug_loc) }
  .debug_macinfo  0 : { *(.debug_macinfo) }
  /* SGI/MIPS DWARF 2 extensions */
  .debug_weaknames 0 : { *(.debug_weaknames) }
  .debug_funcnames 0 : { *(.debug_funcnames) }
  .debug_typenames 0 : { *(.debug_typenames) }
  .debug_varnames  0 : { *(.debug_varnames) }
  /* DWARF 3 */
  .debug_pubtypes 0 : { *(.debug_pubtypes) }
  .debug_ranges   0 : { *(.debug_ranges) }
  /* DWARF Extension.  */
  .debug_macro    0 : { *(.debug_macro) }
  .debug_addr     0 : { *(.debug_addr) }
  /*.gnu.attributes 0 : { KEEP (*(.gnu.attributes)) }*/

  /DISCARD/ : {
     *(.*)
  }
}

