
import glob
import os.path
import subprocess
import struct
import sys
import re

from .shared import *

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
        error("Input files have multiple architectures, can't link this...")

    archn = list(archs)[0]

    if archn not in archmagic:
        eprintf("Unknown architecture number " + str(archn) + \
            ". Consult elf.h and rebuild your object files.")

    return archmagic[archn]

def build_reloc_typ_table(reo):
    relocs = dict({})

    for s in reo.decode('utf-8').splitlines():
        stuff = s.split()

        # prolly a 'header' line
        if len(stuff) < 5:
            continue

        # yes, we're assuming every reference to the same symbol will use the
        # same relocation type. if this isn't the case, your compiler flags are
        # stupid
        relocs[stuff[4]] = stuff[2]

    return relocs

def has_lto_object(readelf_bin, files):
    for x in files:
        with open(x,'rb') as f:
            if f.read(2) == b'BC': # LLVM bitcode! --> clang -flto
                return True

    output = subprocess.check_output([readelf_bin, '-s', '-W'] + files,
                                     stderr=subprocess.DEVNULL)

    curfile = files[0]
    for entry in output.decode('utf-8').splitlines():
        stuff = entry.split()
        if len(stuff)<2: continue
        if stuff[0] == "File:": curfile = stuff[1]
        if "__gnu_lto_" in entry or ".gnu.lto" in entry: # assuming nobody uses a symbol called "__gnu_lto_" ...
            return True
    return False

def get_needed_syms(readelf_bin, inpfile):
    output = subprocess.check_output([readelf_bin, '-s', '-W',inpfile],
                                     stderr=subprocess.DEVNULL)
    outrel = subprocess.check_output([readelf_bin, '-r', '-W',inpfile],
                                     stderr=subprocess.DEVNULL)

    relocs = build_reloc_typ_table(outrel)

    curfile = inpfile
    syms=set({})
    for entry in output.decode('utf-8').splitlines():
        stuff = entry.split()
        if len(stuff)<2: continue
        if stuff[0] == "File:": curfile = stuff[1]
        if len(stuff)<8: continue
        #if stuff[7].startswith("__gnu_lto_"): # yikes, an LTO object
        #    error("{} is an LTO object file, can't use this!".format(curfile))
        if stuff[4] == "GLOBAL" and stuff[6] == "UND" and len(stuff[7])>0 \
                and stuff[7] in relocs:
            syms.add((stuff[7], relocs[stuff[7]]))

    #needgot = False
    #if "_GLOBAL_OFFSET_TABLE_" in syms:
    #    needgot = True
    #    syms.remove("_GLOBAL_OFFSET_TABLE_")

    return syms#, needgot

def format_cc_path_line(entry):
    category, path = entry.split(': ', 1)
    path = path.lstrip('=')
    return (category, list(set(os.path.realpath(p) \
        for p in path.split(':') if os.path.isdir(p))))

def get_cc_paths(cc_bin):
    bak = os.environ.copy()
    os.environ['LANG'] = "C" # DON'T output localized search dirs!
    output = subprocess.check_output([cc_bin, '-print-search-dirs'],
                                     stderr=subprocess.DEVNULL)
    os.environ = bak

    outputpairs = list(map(format_cc_path_line,
                           output.decode('utf-8').splitlines()))
    paths = {}

    for category, path in outputpairs: paths[category] = path

    if 'libraries' not in paths: # probably localized... sigh
        # monkeypatch, assuming order...
        paths = {}
        paths['install'  ] = outputpairs[0][1]
        paths['programs' ] = outputpairs[1][1]
        paths['libraries'] = outputpairs[2][1]

    return paths

def get_cc_version(cc_bin):
    bak = os.environ.copy()
    os.environ['LANG'] = "C" # DON'T output localized search dirs!
    output = subprocess.check_output([cc_bin, '--version'],
                                     stderr=subprocess.DEVNULL)
    os.environ = bak

    lines = output.decode('utf-8').splitlines()
    if "Free Software Foundation" in lines[1]: # GCC
        verstr = lines[0].split()[-1]
        return ("gcc", tuple(map(int, verstr.split('.'))))
    else: # assume clang
        verstr = lines[0].split()[-1]
        return ("clang", tuple(map(int, verstr.split('.'))))

def is_valid_elf(f): # Good Enough(tm)
    with open(f, 'rb') as ff: return ff.read(4) == b'\x7FELF'

def find_lib(spaths, wanted):
    for p in spaths:
        for f in glob.glob(glob.escape(p + '/lib' + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f): return f
        for f in glob.glob(glob.escape(p + '/'    + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f): return f
        #for f in glob.glob(glob.escape(p) + '/lib' + wanted + '.a' ): return f
        #for f in glob.glob(glob.escape(p) + '/'    + wanted + '.a' ): return f

    error("E: couldn't find library '" + wanted + "'.")

def find_libs(spaths, wanted):
    return [find_lib(spaths, l) for l in wanted]

def list_symbols(readelf_bin, lib):
    out = subprocess.check_output([readelf_bin, '-sW', lib], stderr=subprocess.DEVNULL)

    lines = set(out.decode('utf-8').split('\n'))
    symbols = []

    for line in lines:
        fields = re.split(r"\s+", line)
        if len(fields) != 9:
            continue

        vis, ndx, symbol = fields[6:9]
        if vis != "DEFAULT" or ndx == "UND":
            continue

        # strip away GLIBC versions
        symbol = re.sub(r"@@.*$", "", symbol)
        symbols.append(symbol)

    return symbols

def build_symbol_map(readelf_bin, libraries):
    # create dictionary that maps symbols to libraries that provide them
    symbol_map = {}
    for lib in libraries:
        symbols = list_symbols(readelf_bin, lib)
        for symbol in symbols:
            if symbol not in symbol_map:
                symbol_map[symbol] = set()
            soname = lib.split("/")[-1]
            symbol_map[symbol].add(soname)
    return symbol_map
