/*OUTPUT_FORMAT(binary)*/
ENTRY(_smol_start)

PHDRS {
	rodttxt PT_LOAD FLAGS(5); /* r-x */
	rwdt    PT_LOAD FLAGS(6); /* rw- */
}

SECTIONS {
  . = 0x10000;
  _smol_origin = .;

  .header : { KEEP(*(.header)) } :rodttxt

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

  .dynamic : { *(.dynamic) } :rodttxt :dyn
  .dynstuff : { *(.symtab .strtab .shstrtab .rel.text .got.plt .gnu.linkonce.* .plt .plt.got .interp) } :rodttxt
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

  /DISCARD/ : {
     *(.*)
  }

  _smol_total_memsize = . - _smol_origin;
}

