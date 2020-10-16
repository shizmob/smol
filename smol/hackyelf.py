
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

SHT_NULL     =  0
SHT_PROGBITS =  1
SHT_SYMTAB   =  2
SHT_STRTAB   =  3
SHT_DYNSYM   = 11

STB_LOCAL  = 0
STB_GLOBAL = 1
STB_WEAK   = 2

STT_NOTYPE = 0
STT_OBJECT = 1
STT_FUNC   = 2
STT_SECTION= 3
STT_FILE   = 4
STT_COMMON = 5
STT_TLS    = 6
STT_GNU_IFUNC = 10

STV_DEFAULT   = 0
STV_INTERNAL  = 1
STV_HIDDEN    = 2
STV_PROTECTED = 3

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

class Shdr(NamedTuple):
    name: Union[int, str]
    type: int
    flags: int
    addr: int
    offset: int
    size: int
    link: int
    info: int
    addralign: int
    entsize: int

class Sym(NamedTuple):
    name: str
    value: int
    size: int
    type: int
    binding: int
    visibility: int
    shndx: int

class ELF(NamedTuple):
    data  : bytes
    ident : bytes
    eclass: int
    mach  : int
    entry : int
    phdrs : Sequence[Phdr]
    dyn   : Sequence[Dyn]
    shdrs : Sequence[Shdr]
    symtab: Sequence[Sym]
    dynsym: Sequence[Sym]
    is32bit: bool

def readstr(data: bytes, off: int) -> str:
    strb = bytearray()
    while data[off] != 0 and off < len(data):
        strb.append(data[off])
        off = off + 1
    return strb.decode('utf-8')

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

def parse_shdr32(data: bytes, shoff: int, shentsz: int, shnum: int,
                 shstrndx: int) -> Sequence[Shdr]:
    if shnum*shentsz+shoff > len(data) or shentsz==0 or shnum==0 or shoff==0:
        print("snum*shentsz+shoff",shnum*shentsz+shoff)
        print("len(data)",len(data))
        print("shentsz",shentsz)
        print("shnum",shnum)
        print("shoff",shoff)
        return []

    ss = []
    for off in range(shoff, shoff+shentsz*shnum, shentsz):
        noff, typ, flags, addr, off, size, link, info, align, entsz = \
            unpack('<IIIIIIIIII', data[off:off+10*4])
        s = Shdr(noff, typ, flags, addr, off, size, link, info, align, entsz)
        ss.append(s)

    if shstrndx < shnum:
        shstr = ss[shstrndx]
        for i in range(len(ss)):
            sname = readstr(data, shstr.offset + ss[i].name) \
                if ss[i].name < shstr.size else None
            ss[i] = Shdr(sname, ss[i].type, ss[i].flags, ss[i].addr,
                         ss[i].offset, ss[i].size, ss[i].link, ss[i].info,
                         ss[i].addralign, ss[i].entsize)

    return ss

def parse_sym32(data: bytes, sym: Shdr, strt: Shdr) -> Sequence[Sym]:
    ss = []
    for off in range(sym.offset, sym.offset+sym.size, sym.entsize):
        noff, val, sz, info, other, shndx = \
            unpack('<IIIBBH', data[off:off+3*4+2+2])

        sn = readstr(data, strt.offset + noff) \
            if noff < strt.size else None
        s = Sym(sn, val, sz, (info & 15), (info >> 4), other, shndx)
        ss.append(s)
    return sorted(ss, key=lambda x:x.value)

def parse_32(data: bytes) -> ELF:
    ident  = data[:16]
    eclass = data[4]
    mach   = unpack('<H', data[18:18+2])[0]
    entry  = unpack('<I', data[24:24+4])[0]

    phoff   = unpack('<I', data[28:28+4])[0]
    shoff   = unpack('<I', data[32:32+4])[0]
    phentsz = unpack('<H', data[42:42+2])[0]
    phnum   = unpack('<H', data[44:44+2])[0]
    shentsz = unpack('<H', data[46:46+2])[0]
    shnum   = unpack('<H', data[48:48+2])[0]
    shstrndx= unpack('<H', data[50:50+2])[0]

    phdrs = parse_phdr32(data, phoff, phentsz, phnum)
    dyn   = None

    for p in phdrs:
        if p.ptype == PT_DYNAMIC:
            dyn = parse_dyn32(data, p)
            break

    shdrs = parse_shdr32(data, shoff, shentsz, shnum, shstrndx)
    #print("shdrs",shdrs)

    symtabsh = [s for s in shdrs if s.type == SHT_SYMTAB and s.name == ".symtab"]
    strtabsh = [s for s in shdrs if s.type == SHT_STRTAB and s.name == ".strtab"]
    dynsymsh = [s for s in shdrs if s.type == SHT_SYMTAB and s.name == ".dynsym"]
    dynstrsh = [s for s in shdrs if s.type == SHT_STRTAB and s.name == ".dynstr"]

    #print("symtab",symtabsh)
    #print("strtab",strtabsh)

    assert len(symtabsh) < 2
    assert len(strtabsh) < 2
    assert len(dynsymsh) < 2
    assert len(dynstrsh) < 2

    symtab, dynsym = None, None
    if len(symtabsh) and len(strtabsh):
        symtab = parse_sym32(data, symtabsh[0], strtabsh[0]) \
            if len(shdrs) > 0 else []
    if len(dynsymsh) and len(dynstrsh):
        dynsym = parse_sym32(data, symtabsh[0], strtabsh[0]) \
            if len(shdrs) > 0 else []

    return ELF(data, ident, eclass, mach, entry, phdrs, dyn, shdrs,
               symtab, dynsym, True)

def parse_phdr64(data: bytes, phoff:int, phentsz:int, phnum:int) -> Sequence[Phdr]:
    ps = []
    for off in range(phoff, phoff+phentsz*phnum, phentsz):
        # TODO # what is TODO exactly??
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

def parse_shdr64(data: bytes, shoff: int, shentsz: int, shnum: int,
                 shstrndx: int) -> Sequence[Shdr]:
    if shnum*shentsz+shoff >= len(data) or shentsz==0 or shnum==0 or shoff==0:
        return []

    ss = []
    for off in range(shoff, shoff+shentsz*shnum, shentsz):
        noff, typ, flags, addr, off, size, link, info, align, entsz = \
            unpack('<IIQQQQIIQQ', data[off:off+4*4+6*8])
        s = Shdr(noff, typ, flags, addr, off, size, link, info, align, entsz)
        ss.append(s)

    if shstrndx < shnum:
        shstr = ss[shstrndx]
        for i in range(len(ss)):
            sname = readstr(data, shstr.offset + ss[i].name) \
                if ss[i].name < shstr.size else None
            ss[i] = Shdr(sname, ss[i].type, ss[i].flags, ss[i].addr,
                         ss[i].offset, ss[i].size, ss[i].link, ss[i].info,
                         ss[i].addralign, ss[i].entsize)

    return ss

def parse_sym64(data: bytes, sym: Shdr, strt: Shdr) -> Sequence[Sym]:
    ss = []
    for off in range(sym.offset, sym.offset+sym.size, sym.entsize):
        noff, info, other, shndx, value, sz = \
            unpack('<IBBHQQ', data[off:off+4+2+2+8*2])

        sn = readstr(data, strt.offset + noff) \
            if noff < strt.size else None
        s = Sym(sn, val, sz, (info & 15), (info >> 4), other, shndx)
        ss.append(s)
    return sorted(ss, key=lambda x:x.value)

def parse_64(data: bytes) -> ELF:
    ident  = data[:16]
    eclass = data[4]
    mach   = unpack('<H', data[18:18+2])[0]
    entry  = unpack('<Q', data[24:24+8])[0]

    phoff   = unpack('<Q', data[32:32+8])[0]
    shoff   = unpack('<Q', data[40:40+8])[0]
    phentsz = unpack('<H', data[54:54+2])[0]
    phnum   = unpack('<H', data[56:56+2])[0]
    shentsz = unpack('<H', data[58:58+2])[0]
    shnum   = unpack('<H', data[60:60+2])[0]
    shstrndx= unpack('<H', data[62:62+2])[0]

    phdrs = parse_phdr64(data, phoff, phentsz, phnum)
    dyn   = None

    for p in phdrs:
        if p.ptype == PT_DYNAMIC:
            dyn = parse_dyn64(data, p)
            break

    shdrs = parse_shdr64(data, shoff, shentsz, shnum, shstrndx)

    symtabsh = [s for s in shdrs if s.type == SHT_SYMTAB and s.name == ".symtab"]
    strtabsh = [s for s in shdrs if s.type == SHT_STRTAB and s.name == ".strtab"]
    dynsymsh = [s for s in shdrs if s.type == SHT_SYMTAB and s.name == ".dynsym"]
    dynstrsh = [s for s in shdrs if s.type == SHT_STRTAB and s.name == ".dynstr"]

    assert len(symtabsh) < 2
    assert len(strtabsh) < 2
    assert len(dynsymsh) < 2
    assert len(dynstrsh) < 2

    symtab, dynsym = None, None
    if len(symtabsh) and len(strtabsh):
        symtab = parse_sym64(data, symtabsh[0], strtabsh[0]) \
            if len(shdrs) > 0 else []
    if len(dynsymsh) and len(dynstrsh):
        dynsym = parse_sym64(data, symtabsh[0], strtabsh[0]) \
            if len(shdrs) > 0 else []

    return ELF(data, ident, eclass, mach, entry, phdrs, dyn, shdrs,
               symtab, dynsym, False)

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

