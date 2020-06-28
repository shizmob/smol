
# stolen from the contrib folder in https://github.com/blackle/LZMA-Vizualizer
# (i.e. I'm stealing it from myself)

import re
from typing import *

class CommonSym(NamedTuple):
    name: str
    size: int
    file: str
class Discard(NamedTuple):
    name: str
    size: int
    file: str
class MemCfg(NamedTuple):
    name: str
    org : int
    size: int
class MMap(NamedTuple):
    sect: str
    org : int
    #size: int
    sym : str
    file: str
class XRef(NamedTuple):
    name: str
    deff: str
    reff: Sequence[str]

class LinkMap(NamedTuple):
    common : Sequence[CommonSym]
    discard: Sequence[Discard]
    memcfg : Sequence[MemCfg]
    mmap   : Sequence[MMap]
    xref   : Sequence[XRef]

def parse_common( ls: Sequence[str]) -> Sequence[CommonSym]: return [] # TODO
def parse_discard(ls: Sequence[str]) -> Sequence[Discard  ]: return [] # TODO
def parse_memcfg( ls: Sequence[str]) -> Sequence[MemCfg   ]: return [] # TODO
def parse_xref(   ls: Sequence[str]) -> Sequence[XRef     ]: return [] # TODO

def parse_mmap(ls: Sequence[str]) -> Sequence[MMap]:
    rrr = []

    bigsect = None
    section = None
    curfile = None
    #size = -1

    for l in ls:
        def matcher(mobj):
            return mobj.group(0).replace(' ', '_')
        l = re.sub(r"\*\(.*\)", matcher, l)
        #print(repr(l))
        s = l.strip(); w = s.split()

        if s.startswith('LOAD ') or s.startswith('OUTPUT('): continue#break

        if l[0] != ' ':
            bigsect = w[0]
            del w[0]
        elif l[1] != ' ':
            section = w[0]
            del w[0]

        if len(w) == 0 or w[0] == "[!provide]":
            continue # addr placed on next line for prettyprinting reasons

        #print(repr(l), w[0])
        assert w[0].startswith("0x"), "welp, bad symbol addr"

        addr = int(w[0], 16)

        size = -1
        symn = ""
        if w[1].startswith("0x"): # filename will prolly follow
            size = int(w[1], 16)
            curfile = w[2] if len(w) > 2 else ""
        else: symn = w[1]

        if len(symn) > 0:
            rrr.append(MMap(section, addr, symn, curfile))

    return rrr

def parse(s: str) -> LinkMap:
    COMMON  = 0
    DISCARD = 1
    MEMCFG  = 2
    MMAP    = 3
    XREF    = 4

    curpt = -1

    commonl, discardl, memcfgl, mmapl, xrefl = [], [], [], [], []

    for l in s.split('\n'):
        if len(l.strip()) == 0: continue

        ls = l.strip()
        if ls == "Allocating common symbols": curpt = COMMON
        elif ls == "Discarded input sections": curpt = DISCARD
        elif ls == "Memory Configuration": curpt = MEMCFG
        elif ls == "Linker script and memory map": curpt = MMAP
        elif ls == 'Cross Reference Table': curpt = XREF
        elif curpt == COMMON :  commonl.append(l)
        elif curpt == DISCARD: discardl.append(l)
        elif curpt == MEMCFG :  memcfgl.append(l)
        elif curpt == MMAP   :    mmapl.append(l)
        elif curpt == XREF   :    xrefl.append(l)
        else:
            assert False, "bad line %s" % ls

    return LinkMap(parse_common(commonl), parse_discard(discardl), \
                   parse_memcfg(memcfgl), parse_mmap(mmapl), parse_xref(xrefl))

