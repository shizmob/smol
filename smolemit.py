
import sys

from smolshared import *

def output_x86(libraries, libsep, outf):
    outf.write('; vim: set ft=nasm:\n') # be friendly
    outf.write('bits 32\n')
    if libsep:
        outf.write('%define LIBSEP\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header32.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('dd 1;DT_NEEDED\n')
        outf.write('dd (_symbols.{} - _strtab)\n'.format(shorts[library]))
    outf.write('dynamic.end:\n')

#    if needgot:
#        outf.write('global _GLOBAL_OFFSET_TABLE_\n')
#        outf.write('_GLOBAL_OFFSET_TABLE_:\n')
#        outf.write('dd dynamic\n')
    outf.write('_strtab:\n')
    if not libsep:
        for library, symrels in libraries.items():
            outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
        if libsep:
            outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

        for sym, reloc in symrels:
            # meh
            if reloc != 'R_386_PC32':
                eprintf('Relocation type ' + reloc + ' of symbol ' + sym + ' unsupported!')
                sys.exit(1)

            hash = hash_djb2(sym)
            outf.write("""
\t\tglobal {name}
\t\t{name}: db 0xE9
\t\t  dd 0x{hash:x}
""".format(name=sym, hash=hash).lstrip('\n'))

        outf.write('\tdb 0\n') # TODO: not a dd?
    outf.write('db 0\n')
    outf.write('_symbols.end:\n')

    outf.write('%include "loader32.asm"\n')
# end output_x86


def output_amd64(libraries, libsep, outf):
    outf.write('; vim: set ft=nasm:\n')
    outf.write('bits 64\n')
    if libsep:
        outf.write('%define LIBSEP\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header64.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('dq 1;DT_NEEDED\n')
        outf.write('dq (_symbols.{} - _strtab)\n'.format(shorts[library]))
    outf.write('dynamic.end:\n')

    if libsep:
        outf.write('[section .data.smolgot]\n')
    else:
        outf.write('[section .rodata.neededlibs]\n')
#    if needgot:
#        outf.write('global _GLOBAL_OFFSET_TABLE_\n')
#        outf.write('_GLOBAL_OFFSET_TABLE_:\n')
#        outf.write('dq dynamic\n')

    outf.write('_strtab:\n')
    if not libsep:
        for library, symrels in libraries.items():
            outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

    if not libsep:
        outf.write('[section .data.smolgot]\n')

    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
        if libsep:
            outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

        for sym, reloc in symrels:
            if reloc != 'R_X86_64_PLT32' and reloc != 'R_X86_64_GOTPCRELX':
                eprintf('Relocation type ' + reloc + ' of symbol ' + sym + ' unsupported!')
                sys.exit(1)

            if reloc == 'R_X86_64_GOTPCRELX':
                outf.write("""
global {name}
{name}:
""".format(name=sym).lstrip('\n'))

            hash = hash_djb2(sym)
            outf.write('\t\t_symbols.{lib}.{name}: dq 0x{hash:x}\n'\
                       .format(lib=shorts[library],name=sym,hash=hash))

        if libsep:
            outf.write('\tdq 0\n')

    outf.write('db 0\n')
    outf.write('_symbols.end:\n')

    outf.write('_smolplt:\n')
    for library, symrels in libraries.items():
        for sym, reloc in symrels:
            if reloc == 'R_X86_64_PLT32':
                outf.write("""
[section .text.smolplt.{name}]
global {name}
{name}:
    jmp [rel _symbols.{lib}.{name}]
""".format(lib=shorts[library],name=sym).lstrip('\n'))

    outf.write('_smolplt.end:\n')
    outf.write('%include "loader64.asm"\n')
# end output_amd64


def output(arch, libraries, libsep, outf):
    if arch == 'i386': output_x86(libraries, libsep, outf)
    elif arch == 'x86_64': output_amd64(libraries, libsep, outf)
    else:
        eprintf("E: cannot emit for arch '" + str(arch) + "'")
        sys.exit(1)

