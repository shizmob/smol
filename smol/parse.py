
import glob
import os.path
import subprocess
import struct
import sys

from .elf import ELFMachine
from .util import warn, error


def decide_arch(files):
    machine = None

    for fn in files:
        with open(fn, 'rb') as f:
            ident = f.read(16) # ei_ident
            clas = ident[4] * 32 # EI_CLASS
            _ = f.read(2) # ei_type
            mach = f.read(2) # ei_machine
            machid = struct.unpack('<H', mach)[0]
            if machine is not None and machine != machid:
                warn('Input files have multiple architectures, can\'t link this...')
                return None, None
            machine = machid

    if machine not in set(item.value for item in ELFMachine):
        warn('Unsupported machine ID: {}'.format(machine))
        warn('If you are sure this is correct, contact us to add support!')
        return None, None

    return ELFMachine(machine), clas

def build_reloc_typ_table(reo):
    relocs = {}

    for s in reo.decode('utf-8').splitlines():
        cols = s.split()

        # prolly a 'header' line
        if len(cols) < 5:
            continue

        # yes, we're assuming every reference to the same symbol will use the
        # same relocation type. if this isn't the case, your compiler flags are
        # stupid
        relocs[cols[4]] = cols[2]

    return relocs

def get_needed_syms(readelf_bin, inpfiles):
    output = subprocess.check_output([readelf_bin, '-s', '-W'] + inpfiles,
        stderr=subprocess.DEVNULL)
    outrel = subprocess.check_output([readelf_bin, '-r', '-W'] + inpfiles,
        stderr=subprocess.DEVNULL)
    relocs = build_reloc_typ_table(outrel)

    syms = set()
    for entry in output.decode('utf-8').splitlines():
        cols = entry.split()
        if len(cols) < 8:
            continue
        if cols[4] == "GLOBAL" and cols[6] == "UND" and cols[7] and cols[7] in relocs:
            syms.add((cols[7], relocs[cols[7]]))

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

def is_valid_elf(fn):
    with open(fn, 'rb') as f:
        return f.read(4) == b'\x7FELF'

def find_lib(spaths, wanted):
    for p in spaths:
        for f in glob.glob(glob.escape(p + '/lib' + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f):
                return f
        for f in glob.glob(glob.escape(p + '/' + wanted) + '.so*'):
            if os.path.isfile(f) and is_valid_elf(f):
                return f

    return None

def find_symbol(scanelf_bin, libraries, libnames, symbol):
    output = subprocess.check_output([scanelf_bin, '-B', '-F' '%s %S', '-s', \
                '+{}'.format(symbol)] + libraries, stderr=subprocess.DEVNULL)
    for entry in output.decode('utf-8').splitlines():
        sym, soname, path = entry.split(' ', 2)
        if symbol in sym.split(',') and \
                any(soname.startswith('lib'+l) for l in libnames):
            return soname

    return None