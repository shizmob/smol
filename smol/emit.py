
import sys

from .util import error, hash_djb2
from .elf import ELFMachine


def output_x86(libraries, outf):
    outf.write('bits 32\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header-x86.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('dd 1;DT_NEEDED\n')
        outf.write('dd (_symbols.{} - _strtab)\n'.format(shorts[library]))
    outf.write('dynamic.end:\n')

    outf.write('_strtab:\n')
    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

        for sym, reloc in symrels:
            # meh
            if reloc != 'R_386_PC32':
                error('Relocation type ' + reloc + ' of symbol ' + sym + ' unsupported!')
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

    outf.write('%include "loader-x86.asm"\n')


def output_x86_64(libraries, outf):
    outf.write('bits 64\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header-x86_64.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('    dq 1;DT_NEEDED\n')
        outf.write('    dq (_symbols.{} - _strtab)\n'.format(shorts[library]))
    outf.write("""\
dynamic.symtab:
    dq DT_SYMTAB        ; d_tag
    dq 0                ; d_un.d_ptr
dynamic.end:
%ifndef UNSAFE_DYNAMIC
    dq DT_NULL
%endif
""")

    outf.write('[section .rodata.neededlibs]\n')

    outf.write('_strtab:\n')
    for library, symrels in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

    outf.write('[section .data.smolgot]\n')

    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
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
    outf.write('%include "loader-x86_64.asm"\n')


def output_table(arch, libraries, outf):
    if arch == ELFMachine.i386:
        return output_x86(libraries, outf)
    elif arch == ELFMachine.x86_64:
        return output_x86_64(libraries, outf)
    else:
        error('')
        eprintf("E: cannot emit for arch '" + str(arch) + "'")
        sys.exit(1)

