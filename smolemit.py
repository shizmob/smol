
import sys

from smolshared import *

def hash_djb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + ord(c)) & 0xFFFFFFFF
    return h

def output_x86(libraries, outf):
    outf.write('; vim: set ft=nasm:\n') # be friendly
    outf.write('bits 32\n')
    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header32.asm"\n')
    outf.write('.dynamic.needed:\n')
    for library in libraries:
        outf.write('dd 1;DT_NEEDED\n')
        outf.write('dd (_symbols.{} - _symbols)\n'.format(shorts[library]))
    outf.write('.dynamic.end:\n')

    outf.write('_symbols:\n')
    for library, symbols in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

        for sym in symbols:
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

def output_amd64(libraries, outf):
    outf.write('; vim: set ft=nasm:\n')
    outf.write('bits 64\n')
    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header64.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('dq 1;DT_NEEDED\n')
        outf.write('dq (_symbols.{} - _symbols)\n'.format(shorts[library]))
    outf.write('dynamic.end:\n')

    outf.write('[section .data.smolgot]\n')
    outf.write('_symbols:\n')
    for library, symbols in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

        for sym in symbols:
            hash = hash_djb2(sym)
            outf.write('\t\t_symbols.{lib}.{name}: dq 0x{hash:x}\n'\
                       .format(lib=shorts[library],name=sym,hash=hash))

        outf.write('\tdq 0\n')
    outf.write('db 0\n')
    outf.write('_symbols.end:\n')

    outf.write('_smolplt:\n')
    for library, symbols in libraries.items():
        for sym in symbols:
            outf.write("""
[section .text.smolplt.{name}]
global {name}
{name}:
    jmp [rel _symbols.{lib}.{name}]
""".format(lib=shorts[library],name=sym).lstrip('\n'))

    outf.write('_smolplt.end:\n')
    outf.write('%include "loader64.asm"\n')
def output(arch, libraries, outf):
    if arch == 'i386': output_x86(libraries, outf)
    elif arch == 'x86_64': output_amd64(libraries, outf)
    else:
        eprintf("E: cannot emit for arch '" + str(arch) + "'")
        sys.exit(1)

