OUTPUT_FORMAT(binary)

SECTIONS {
  . = 0x400000;

  .header : { *(.header) }

  .text : {
     *(.text.startup.smol)
     *(.text.startup._start)
     *(.text .text.* .rdata .rdata.* .rodata .rodata.*)
  }

  .data : {
     *(.data .data.* .tdata .tdata.* .bss .bss.* .tbss .tbss.*)
  }

  .dynamic : { *(.dynamic) } :all :dyn
  .dynstuff : { *(.symtab .strtab .shstrtab .rel.text .got.plt .gnu.linkonce.* .plt .plt.got .interp) } :all

  /DISCARD/ : {
     *(.*)
  }

  _smol_total_size = . - 0x400000;
}
