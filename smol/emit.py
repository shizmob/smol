
import sys
from collections import OrderedDict

from .shared import *

fetch_width_from_bits = { 8: 'byte', 16: 'word', 32: 'dword', 64: 'qword' }

def get_min_check_width(libraries, hashfn):
    minv = 8 # can't go lower
    for k, v in libraries.items():
        for sym in v:
            hv = hashfn(sym[0]) # sym == (name, reloc)
            if (hv & 0xffffffff) == 0:
                # this should (hopefully) NEVER happen
                error("Aiee, all-zero hash for sym '%s'!" % sym)
            elif (hv & 0xFFFF) == 0:
                minv = max(minv, 32) # need at least 32 bits
            elif (hv & 0xFF) == 0:
                minv = max(minv, 16) # need at least 16 bits

    return minv

def sort_imports(libraries, hashfn):
    #eprintf("in: " + str(libraries))

    # sort libs by name length, then by name
    ll = sorted(libraries.items(), key=lambda ls: (len(ls[0]), ls[0]))

    for i in range(len(ll)):
        # sort symbols by hash value
        ll[i] = (ll[i][0], sorted(ll[i][1], key=lambda sr: hashfn(sr[0])))

    #eprintf("out:" + str(dict(ll)))

    # insertion order only works with python >=3.6!
    if sys.version_info < (3, 6): return OrderedDict(ll)
    else: return dict(ll)

def output_x86(libraries, nx, h16, outf, det):
    outf.write('; vim: set ft=nasm:\n') # be friendly

    if nx:  outf.write('%define USE_NX 1\n')
    if h16: outf.write('%define USE_HASH16 1\n')

    hashfn = hash_bsd2 if h16 else hash_djb2
    if det: libraries = sort_imports(libraries, hashfn)

    outf.write('%%define HASH_END_TYP %s\n' %
               fetch_width_from_bits[get_min_check_width(libraries, hashfn)])

    usedrelocs = set({})
    for library, symrels in libraries.items():
        for sym, reloc in symrels: usedrelocs.add(reloc)

    if not(nx) and 'R_386_PC32' in usedrelocs and 'R_386_GOT32X' in usedrelocs:
        error("Using a mix of R_386_PC32 and R_386_GOT32X relocations! "+\
                "Please change a few C compiler flags and recompile your code.")


    use_jmp_bytes = not nx and 'R_386_PC32' in usedrelocs
    if use_jmp_bytes:
        outf.write('%define USE_JMP_BYTES 1\n')

    outf.write('bits 32\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header32.asm"\n')
    outf.write('dynamic.needed:\n')
    for library in libraries:
        outf.write('dd 1;DT_NEEDED\n')
        outf.write('dd (_symbols.{} - _strtab)\n'.format(shorts[library]))
    outf.write("""\
dynamic.end:
%ifndef UNSAFE_DYNAMIC
    dd DT_NULL
%endif
""")

    outf.write('[section .rodata.neededlibs]\n')
    outf.write('global _strtab\n')
    outf.write('_strtab:\n')
    for library, symrels in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

    outf.write('[section .data.smolgot]\n')
    if not nx:
        outf.write('[section .text.smolplt]\n')

    outf.write('global _symbols\n')
    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
        for sym, reloc in symrels:
            # meh
            if reloc != 'R_386_PC32' and reloc != 'R_386_GOT32X':
                eprintf('Relocation type %s of symbol %s unsupported!' % (reloc, sym))
                sys.exit(1)

            if nx:
                outf.write("\t\t_symbols.{lib}.{name}: dd 0x{hash:x}"\
                    .format(lib=shorts[library],name=sym,hash=hashfn(sym)).lstrip('\n'))
            else:
                outf.write(("""\
\t\tglobal {name}
\t\t{name}:""" + ("\n\t\t\tdb 0xE9" if use_jmp_bytes else '') + """
\t\t\tdd 0x{hash:x}
""").format(name=sym, hash=hashfn(sym)).lstrip('\n'))

    outf.write('db 0\n')
    outf.write('_symbols.end:\n')

    if nx:
        outf.write('global _smolplt\n')
        outf.write('_smolplt:\n')
        for library, symrels in libraries.items():
            for sym, reloc in symrels:
                outf.write("""\
[section .text.smolplt.{name}]
global {name}
{name}:
\tjmp [dword _symbols.{lib}.{name}]
""".format(lib=shorts[library],name=sym).lstrip('\n'))

        outf.write('_smolplt.end:\n')

    outf.write('%include "loader32.asm"\n')
# end output_x86


def output_amd64(libraries, nx, h16, outf, det):
    if h16:
        error("--hash16 not supported yet for x86_64 outputs.")

    if nx:  outf.write('%define USE_NX 1\n')
#   if h16: outf.write('%define USE_HASH16 1\n')

    hashfn = hash_djb2 #hash_bsd2 if h16 else hash_djb2
    if det: libraries = sort_imports(libraries, hashfn)

    outf.write('%%define HASH_END_TYP %s\n' %
               fetch_width_from_bits[get_min_check_width(libraries, hashfn)])

    outf.write('; vim: set ft=nasm:\n')
    outf.write('bits 64\n')

    shorts = { l: l.split('.', 1)[0].lower().replace('-', '_') for l in libraries }

    outf.write('%include "header64.asm"\n')
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

    outf.write('global _strtab\n')
    outf.write('_strtab:\n')
    for library, symrels in libraries.items():
        outf.write('\t_symbols.{}: db "{}",0\n'.format(shorts[library], library))

    outf.write('[section .data.smolgot]\n')

    outf.write('global _symbols\n')
    outf.write('_symbols:\n')
    for library, symrels in libraries.items():
        for sym, reloc in symrels:
            if reloc not in ['R_X86_64_PLT32', 'R_X86_64_GOTPCRELX', \
                             'R_X86_64_REX_GOTPCRELX', 'R_X86_64_GOTPCREL']:
                error('Relocation type %s of symbol %s unsupported!' % (reloc, sym))

            if reloc in ['R_X86_64_GOTPCRELX', 'R_X86_64_REX_GOTPCRELX', \
                         'R_X86_64_GOTPCREL']:
                outf.write("""
global {name}
{name}:
""".format(name=sym).lstrip('\n'))

            outf.write('\t\t_symbols.{lib}.{name}: dq 0x{hash:x}\n'\
                       .format(lib=shorts[library],name=sym,hash=hashfn(sym)))

    outf.write('db 0\n')
    outf.write('_symbols.end:\n')

    outf.write('global _smolplt\n')
    outf.write('_smolplt:\n')
    for library, symrels in libraries.items():
        for sym, reloc in symrels:
            if reloc == 'R_X86_64_PLT32':
                outf.write("""\
[section .text.smolplt.{name}]
global {name}
{name}:
\tjmp [rel _symbols.{lib}.{name}]
""".format(lib=shorts[library],name=sym).lstrip('\n'))

    outf.write('_smolplt.end:\n')
    outf.write('%include "loader64.asm"\n')
# end output_amd64


def output(arch, libraries, nx, h16, outf, det):
    if arch == 'i386': output_x86(libraries, nx, h16, outf, det)
    elif arch == 'x86_64': output_amd64(libraries, nx, h16, outf, det)
    else:
        error("E: cannot emit for arch '%s'" % str(arch))

