
import glob
import os.path
import subprocess
import struct
import sys

from smolshared import *

def decide_arch(inpfiles):
    archs=set({})

    for fp in inpfiles:
        with open(fp, 'rb') as ff:
            _ = ff.read(16) # ei_ident
            _ = ff.read( 2) # ei_type
            machine = ff.read(2) # ei_machine

            machnum = struct.unpack('<H', machine)[0]
            archs.add(machnum)

    if len(archs) != 1:
        eprintf("Input files have multiple architectures, can't link this...")
        sys.exit(1)

    archn = list(archs)[0]

    if archn not in archmagic:
        eprintf("Unknown architecture number " + str(archn) + \
            ". Consult elf.h and rebuild your object files.")

    return archmagic[archn]

def get_needed_syms(readelf_bin, inpfiles):
    output = subprocess.check_output([readelf_bin, '-s', '-W']+inpfiles,
                                     stderr=subprocess.DEVNULL)

    syms=set({})
    for entry in output.decode('utf-8').splitlines():
        stuff = entry.split()
        if len(stuff)<8: continue
        if stuff[4] == "GLOBAL" and stuff[6] == "UND" and len(stuff[7])>0:
            syms.add(stuff[7])

    return syms

def get_cc_paths(cc_bin):
    output = subprocess.check_output([cc_bin, '-print-search-dirs'],
                                     stderr=subprocess.DEVNULL)
    paths = {}
    for entry in output.decode('utf-8').splitlines():
        category, path = entry.split(': ', 1)
        path = path.lstrip('=')
        paths[category] = list(set(os.path.realpath(p) \
                for p in path.split(':') if os.path.isdir(p)))
    return paths

def is_valid_elf(f):
    with open(f, 'rb') as ff: return ff.read(4) == b'\x7FELF'

def find_lib(spaths, wanted):
    for p in spaths:
        for f in glob.glob(glob.escape(p + '/lib' + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f): return f
        for f in glob.glob(glob.escape(p + '/'    + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f): return f
        #for f in glob.glob(glob.escape(p) + '/lib' + wanted + '.a' ): return f
        #for f in glob.glob(glob.escape(p) + '/'    + wanted + '.a' ): return f

    eprintf("E: couldn't find library '" + wanted + "'.")
    sys.exit(1)

def find_libs(spaths, wanted): return map(lambda l: find_lib(spaths, l), wanted)

def find_symbol(scanelf_bin, libraries, libnames, symbol):
    output = subprocess.check_output([scanelf_bin, '-B', '-F' '%s %S', '-s', \
                '+{}'.format(symbol)] + libraries, stderr=subprocess.DEVNULL)
    for entry in output.decode('utf-8').splitlines():
        sym, soname, path = entry.split(' ', 2)
        if symbol in sym.split(',') and \
                any(soname.startswith('lib'+l) for l in libnames):
            return soname

