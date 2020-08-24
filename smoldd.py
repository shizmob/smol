#!/usr/bin/env python3

import os.path, struct, sys
import argparse, glob, shutil, subprocess

import smol.hackyelf as hackyelf
import smol.linkmap  as linkmap
from smol.shared import *
from smol.parse  import *

# TODO: support for hashes that aren't djb2


def readbyte(blob, off): return struct.unpack('<B', blob[off:off+1])[0], (off+1)
def readint(blob, off):  return struct.unpack('<I', blob[off:off+4])[0], (off+4)
def readlong(blob, off): return struct.unpack('<Q', blob[off:off+8])[0], (off+8)
def readstr(blob, off):
    text = bytearray()
    while True:
        char, off = readbyte(blob, off)
        if char == 0: break

        text.append(char)

    return text.decode('utf-8'), off

def get_def_libpaths(cc_bin, is32bit):
    # FIXME: HACK
    if is32bit: return ['/usr/lib32/','/lib32/']

    return get_cc_paths(cc_bin)['libraries']

def find_libs(deflibs, libname):
    dirs = os.environ.get('LD_LIBRARY_PATH','').split(':') + deflibs

    for d in dirs:
        for f in glob.glob(glob.escape(d + '/' + libname) + '*'): yield f

def build_hashtab(readelf_bin, lib, hashid):
    symbols = list_symbols(readelf_bin, lib)

    hashfn = get_hash_fn(hashid)
    return { hashfn(symbol):symbol for symbol in symbols }

def addr2off(elf, addr):
    for x in elf.phdrs:
        if x.ptype != hackyelf.PT_LOAD: continue

        if addr >= x.vaddr and addr < x.vaddr + x.memsz:
            aoff = addr - x.vaddr
            assert aoff < x.filesz, ".bss address!"
            return aoff + x.off

    error("E: Address %08x not in the static address range!" % addr)

def get_needed_libs(elf, blob):
    assert elf.dyn is not None, "No DYNAMIC table present in the ELF file!"

    strtabs = [x.val for x in elf.dyn if x.tag == hackyelf.DT_STRTAB]
    assert len(strtabs) == 1, "Only one DT_STRTAB may be present in an ELF file."
    strtab = strtabs[0]

    return [readstr(blob,addr2off(elf, strtab+x.val))[0]
            for x in elf.dyn if x.tag == hackyelf.DT_NEEDED]

def get_hashtbl(elf, blob, args):
    htaddr = None
    if args.map is not None:
        lmap = linkmap.parse(args.map.read())
        tabs = [x for x in lmap.mmap if x.sym == '_symbols']
        assert len(tabs) == 1, "One '_symbols' symbol must be present."
        htaddr = tabs[0].org
    elif elf.is32bit:
        txtoff = addr2off(elf, elf.entry)
        # scan for 'push IMM32'
        while blob[txtoff] != 0x68:
            txtoff = txtoff + 1
            assert txtoff < len(blob), "wtf??? (can't find a push IMM32 instruction which pushes the hashtable address)"
        txtoff = txtoff + 1

        #eprintf("Hash table offset: 0x%08x?" % txtoff)
        htaddr = struct.unpack('<I', blob[txtoff:txtoff+4])[0]
    else: # 64-bit
        txtoff = addr2off(elf, elf.entry)
        # scan for 'push IMM32'
        # but the first one we'll encounter pushes the entrypoint addr!
        while blob[txtoff] != 0x68:
            txtoff = txtoff + 1
            assert txtoff < len(blob), "wtf??? (can't find a push IMM32 instruction which pushes the hashtable or entrypoint address)"
        txtoff = txtoff + 1

        # except, this is actually the value we're looking for when the binary
        # had been linked with -fuse-dnload-loader! so let's just check the
        # value
        htaddr = struct.unpack('<I', blob[txtoff:txtoff+4])[0]

        #eprintf("ELF entry == 0x%08x" % elf.entry)
        if htaddr == elf.entry:
            # now we can look for the interesting address
            while blob[txtoff] != 0x68:
                txtoff = txtoff + 1
                assert txtoff < len(blob), "wtf??? (can't find a push IMM32 instruction which pushes the hashtable address)"
            txtoff = txtoff + 1

            #eprintf("Hash table offset: 0x%08x?" % txtoff)
            htaddr = struct.unpack('<I', blob[txtoff:txtoff+4])[0]
        else:
            pass#eprintf("Hash table offset: 0x%08x?" % txtoff)

    assert htaddr is not None, "wtf? (no hashtable address)"
    #eprintf("Hash table address: 0x%08x" % htaddr)
    htoff = addr2off(elf, htaddr)
    #eprintf("Hash table offset: 0x%08x" % htoff)

    tbl = []
    while True:
        hashsz = 2 if elf.is32bit and args.hash16 else 4

        #eprintf("sym from 0x%08x" % htoff)
        #eprintf("sym end at 0x%08x, blob end at 0x%08x" % (htoff+hashsz, len(blob)))
        if htoff+hashsz > len(blob):
            #eprintf("htoff = 0x%08x, len=%08x" % (htoff, len(blob)))
            if len(blob) <= htoff and len(tbl) > 0:
                break
            #if elf.is32bit:
            if struct.unpack('<B', blob[htoff:htoff+1])[0] == 0:
                break
            else:
                assert False, "AAAAA rest is %s" % repr(blob[htoff:])
            #else:
            #    if struct.unpack('<H', blob[htoff:htoff+2])[0] == 0:
            #        break
            #    else:
            #        assert False, "AAAAA rest is %s" % repr(blob[htoff:])
        val = struct.unpack(('<I' if hashsz == 4 else '<H'),
                            blob[htoff:htoff+hashsz])[0]
        if (val & 0xFFFF) == 0: break
        tbl.append(val)
        #eprintf("sym %08x" % val)
        htoff = htoff + (4 if elf.is32bit else 8)

    return tbl

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=argparse.FileType('rb'),
                        default=sys.stdin.buffer, help="input file")
    parser.add_argument('--cc',
                        default=shutil.which('cc'), help="C compiler binary")
    parser.add_argument('--readelf',
                        default=shutil.which('readelf'), help="readelf binary")
    parser.add_argument('--map', type=argparse.FileType('r'), help=\
                        "Get the address of the symbol hash table from the "+\
                        "linker map output instead of attempting to parse the"+\
                        " binary.")

    hashgrp = parser.add_mutually_exclusive_group()
    hashgrp.add_argument('-s', '--hash16', default=False, action='store_true', \
        help="Use 16-bit (BSD2) hashes instead of 32-bit djb2 hashes. "+\
             "Only usable for 32-bit output.")
    hashgrp.add_argument('-c', '--crc32c', default=False, action='store_true', \
        help="Use Intel's crc32 intrinsic for hashing. Conflicts with `--hash16'.")
    args = parser.parse_args()

    blob = args.input.read()
    elf  = hackyelf.parse(blob)

    deflibs = get_def_libpaths(args.cc, elf.is32bit)
    needed = get_needed_libs(elf, blob)
    neededpaths = dict((l,list(find_libs(deflibs, l))[0]) for l in needed)

    htbl = get_hashtbl(elf, blob, args)

    hashid = get_hash_id(args.hash16, args.crc32c)
    libhashes = dict((l, build_hashtab(args.readelf, neededpaths[l], hashid)) for l in needed)

    hashresolves = dict({})
    noresolves   = []
    # TODO: group by libs
    for x in htbl:
        done = False
        for l in libhashes.keys():
            v = libhashes[l]
            if x in v:
                if l not in hashresolves: hashresolves[l] = dict({})
                hashresolves[l][x] = v[x]
                done = True
                break
        if not done: noresolves.append(x)

    for l in hashresolves.keys():
        print("%s:" % l)
        v = hashresolves[l]
        for x in v.keys():
            print("\t%08x -> %s" % (x, v[x]))

    if len(noresolves) > 0:
        print("UNRESOLVED:")
        for x in noresolves: print("\t%08x" % x)

    return 0

if __name__ == '__main__':
    rv = main()
    if rv is None: pass
    else:
        try: sys.exit(int(rv))
        except: sys.exit(1)

