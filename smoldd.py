#!/usr/bin/env python3

import argparse
import glob
import os.path
import shutil
import subprocess
import struct
import sys

from smolshared import *

def readbyte(blob, off):
    return struct.unpack('<B', blob[off:off+1])[0], (off+1)

def readint(blob, off):
    return struct.unpack('<I', blob[off:off+4])[0], (off+4)

def readlong(blob, off):
    return struct.unpack('<Q', blob[off:off+8])[0], (off+8)

def readstr(blob, off):
    text = bytearray()
    while True:
        char, off = readbyte(blob, off)
        if char == 0:
            break

        text.append(char)

    return text.decode('utf-8'), off

def find_libs(bits, libname):
    dirs = os.environ['LD_LIBRARY_PATH'].split(':')
    dirs += ['/usr/lib','/lib']

    for d in dirs:
        for f in glob.glob(glob.escape(d+str(bits)+'/'+libname)+'*'):
            yield f

def build_hashtab(scanelf_bin, lib):
    out = subprocess.check_output([scanelf_bin, '-B', '-F', '%s', '-s', '%pd%*', lib],
                                     stderr=subprocess.DEVNULL)

    blah = set(out.decode('utf-8').split('\n'))
    ret = dict({})

    for x in blah:
        y = x.split()
        if len(y) != 7:
            continue
        ret[hash_djb2(y[6])] = y[6]

    return ret

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=argparse.FileType('rb'),
                        default=sys.stdin.buffer, help="input file")
    parser.add_argument('--scanelf',
                        default=shutil.which('scanelf'), help="scanelf binary")

    args = parser.parse_args()

    blob = args.input.read()

    machnum = struct.unpack('<H', blob[18:18+2])[0]

    is32bit = machnum == archmagic['i386']

    phoff, phsz, phnum = 0, 0, 0
    if is32bit:
        phoff = struct.unpack('<I', blob[28:28+4])[0]
        phsz  = struct.unpack('<H', blob[42:42+2])[0]
        phnum = struct.unpack('<H', blob[44:52+2])[0]
    elif machnum == archmagic['x86_64']:
        phoff = struct.unpack('<Q', blob[32:32+8])[0]
        phsz  = struct.unpack('<H', blob[54:54+2])[0]
        phnum = struct.unpack('<H', blob[56:56+2])[0]
    else:
        eprintf("Unknown architecture " + str(machnum))
        sys.exit(1)

    for i in range(phnum):
        off = phoff + i * phsz
        #print(hex(off))

        ptyp, poff, pva, ppa, pfsz, pmsz, pfl, pal = 0,0,0,0,0,0,0,0
        if is32bit:
            ptyp, poff, pva, ppa, pfsz, pmsz, pfl, pal = \
                struct.unpack('<ILLLIIII', blob[off:off+phsz])
        else:
            ptyp, pfl, poff, pva, ppa, pfsz, pmsz, pal = \
                struct.unpack('<IIQQQQQQ', blob[off:off+phsz])

        if ptyp != 2: # PT_DYNAMIC
            continue

        #print(hex(poff))

        # right after the dynamic section, the smol 'symtab'/'hashtab' is found
        #
        # note that on i386, every lib name is followed by an E9 byte
        # if the next libname/first byte of the hash is null, the table has
        # come to an end.

        j = poff
        strtaboff = 0
        while j < poff + pfsz:
            tag, j = (readint(blob, j) if is32bit else readlong(blob, j))
            ptr, j = (readint(blob, j) if is32bit else readlong(blob, j))

            if tag == 5: # DT_STRTAB
                strtaboff = ptr
            elif tag == 1: # DT_NEEDED
                bakoff = j

                smoltaboff = strtaboff + ptr - (pva - poff)
                j = smoltaboff

                libname, j = readstr(blob, j)
                if len(libname) == 0:
                    break

                sys.stdout.write("* " + libname)

                libs = list(find_libs(32 if is32bit else 64, libname))
                print(" -> NOT FOUND" if len(libs) == 0 else (" -> " + libs[0]))
                ht = dict({}) if len(libs) == 0 else build_hashtab(args.scanelf, libs[0])

                while True:
                    hashv, j = (readint(blob, j) if is32bit else readlong(blob, j))

                    if (hashv & 0xFF) == 0:
                        break

                    sys.stdout.write("  * " + hex(hashv))
                    print(" -> NOT FOUND" if hashv not in ht else (" -> " + ht[hashv]))

                j = bakoff

        break

if __name__ == '__main__':
    main()

