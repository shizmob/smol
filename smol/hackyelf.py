
# stolen from the contrib folder in https://github.com/blackle/LZMA-Vizualizer
# (i.e. I'm stealing it from myself)

# custom elf parser because a standard one wouldn't be trustable because the
# ELFs we're parsing will be a bit wonky anyway

from struct import unpack
from typing import *

ELFCLASS32 = 1
ELFCLASS64 = 2

EM_386    =  3
EM_X86_64 = 62

PT_NULL    = 0
PT_LOAD    = 1
PT_DYNAMIC = 2
PT_INTERP  = 3

DT_NULL   = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_SYMTAB = 6

class Phdr(NamedTuple):
    ptype: int
    off  : int
    vaddr: int
    paddr: int
    filesz: int
    memsz: int
    flags: int
    align: int

class Dyn(NamedTuple):
    tag: int
    val: int

class ELF(NamedTuple):
    data  : bytes
    ident : bytes
    eclass: int
    mach  : int
    entry : int
    phdrs : Sequence[Phdr]
    dyn   : Sequence[Dyn]
    is32bit: bool

# yeah, there's some code duplication here
# idgaf

def parse_phdr32(data: bytes, phoff:int, phentsz:int, phnum:int) -> Sequence[Phdr]:
    ps = []
    for off in range(phoff, phoff+phentsz*phnum, phentsz):
        ptype, off, vaddr, paddr, filesz, memsz, flags, align = \
            unpack('<IIIIIIII', data[off:off+8*4])
        p = Phdr(ptype, off, vaddr, paddr, filesz, memsz, flags, align)
        ps.append(p)

    return ps

def parse_dyn32(data: bytes, dynp: Phdr) -> Dyn:
    ds = []

    off = dynp.off
    while True:
        tag, val = unpack('<II', data[off:off+2*4])
        ds.append(Dyn(tag, val))

        if tag == DT_NULL: break
        off = off + 2*4

    return ds

def parse_32(data: bytes) -> ELF:
    ident  = data[:16]
    eclass = data[4]
    mach   = unpack('<H', data[18:18+2])[0]
    entry  = unpack('<I', data[24:24+4])[0]

    phoff   = unpack('<I', data[28:28+4])[0]
    phentsz = unpack('<H', data[42:42+2])[0]
    phnum   = unpack('<H', data[44:44+2])[0]

    phdrs = parse_phdr32(data, phoff, phentsz, phnum)
    dyn   = None

    for p in phdrs:
        if p.ptype == PT_DYNAMIC:
            dyn = parse_dyn32(data, p)
            break

    return ELF(data, ident, eclass, mach, entry, phdrs, dyn, True)

def parse_phdr64(data: bytes, phoff:int, phentsz:int, phnum:int) -> Sequence[Phdr]:
    ps = []
    for off in range(phoff, phoff+phentsz*phnum, phentsz):
        # TODO
        ptype, flags, off, vaddr, paddr, filesz, memsz, align = \
            unpack('<IIQQQQQQ', data[off:off+2*4+6*8])
        p = Phdr(ptype, off, vaddr, paddr, filesz, memsz, flags, align)
        ps.append(p)

    return ps

def parse_dyn64(data: bytes, dynp: Phdr) -> Dyn:
    ds = []

    off = dynp.off
    while True:
        tag, val = unpack('<QQ', data[off:off+2*8])
        ds.append(Dyn(tag, val))

        if tag == DT_NULL: break
        off = off + 2*8

    return ds

def parse_64(data: bytes) -> ELF:
    ident  = data[:16]
    eclass = data[4]
    mach   = unpack('<H', data[18:18+2])[0]
    entry  = unpack('<Q', data[24:24+8])[0]

    phoff   = unpack('<Q', data[32:32+8])[0]
    phentsz = unpack('<H', data[54:54+2])[0]
    phnum   = unpack('<H', data[56:56+2])[0]

    phdrs = parse_phdr64(data, phoff, phentsz, phnum)
    dyn   = None

    for p in phdrs:
        if p.ptype == PT_DYNAMIC:
            dyn = parse_dyn64(data, p)
            break

    return ELF(data, ident, eclass, mach, entry, phdrs, dyn, False)

def parse(data: bytes) -> ELF:
    assert data[:4] == b'\x7FELF', "Not a valid ELF file" # good enough

    ecls  = data[4]
    if ecls == ELFCLASS32: return parse_32(data)
    elif ecls == ELFCLASS64: return parse_64(data)
    else:
        emch = unpack('<H', data[18:18+2])[0]
        if emch == EM_386: return parse_32(data)
        elif emch == EM_X86_64: return parse_64(data)

        assert False, "bad E_CLASS %d" % ecls

