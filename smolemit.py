
import sys

from smolshared import *

def hash_djb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + ord(c)) & 0xFFFFFFFF
    return h

def output_x86(libraries, outf):
    outf.write('; vim: set ft=nasm:\n') # be friendly
    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header.asm"\n')
    outf.write('.dynamic.needed:\n')
    for library in libraries:
        outf.write('dd 1\n')
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

        outf.write('\tdb 0\n')
    outf.write('db 0\n')
    outf.write('%include "loader.asm"\n')

def output(arch, libraries, outf):
    if arch == 'i386': output_x86(libraries, outf)
    ##elif arch == 'arm':
    #elif arch == 'x86_64':
    ###elif arch == 'aarch64':
    else:
        eprintf("E: cannot emit for arch '" + str(arch) + "'")
        sys.exit(1)

