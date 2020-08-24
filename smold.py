#!/usr/bin/env python3

import argparse
import glob
import itertools
import os, os.path
import shutil
import subprocess
import sys
import tempfile

from smol.shared import *
from smol.parse  import *
from smol.emit   import *
from smol.cnl    import *

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--target', default='', \
        help='architecture to generate asm code for (default: auto)')
    parser.add_argument('-l', '--library', default=[], metavar='LIB', action='append', \
        help='libraries to link against')
    parser.add_argument('-L', '--libdir', default=[], metavar='DIR', action='append', \
        help="directories to search libraries in")

    parser.add_argument('-s', '--hash16', default=False, action='store_true', \
        help="Use 16-bit (BSD) hashes instead of 32-bit djb2 hashes. "+\
             "Implies -fuse-dnload-loader")
    parser.add_argument('-n', '--nx', default=False, action='store_true', \
        help="Use NX (i.e. don't use RWE pages). Costs the size of one phdr, "+\
             "plus some extra bytes on i386.")
    parser.add_argument('-d', '--det', default=False, action='store_true', \
        help="Make the order of imports deterministic (default: just use " + \
             "whatever binutils throws at us)")

    parser.add_argument('-fuse-interp', default=False, action='store_true', \
        help="Include a program interpreter header (PT_INTERP). If not " +\
             "enabled, ld.so has to be invoked manually by the end user.")
    parser.add_argument('-falign-stack', default=False, action='store_true', \
        help="Align the stack before running user code (_start). If not " + \
             "enabled, this has to be done manually. Costs 1 byte.")
    parser.add_argument('-fuse-nx', default=False, action='store_true', \
        help="Don't use one big RWE segment, but use separate RW and RE ones."+\
             " Use this to keep strict kernels (PaX/grsec) happy. Costs at "+\
             "least the size of one program header entry.")
    parser.add_argument('-fuse-dnload-loader', default=False, action='store_true', \
        help="Use a dnload-style loader for resolving symbols, which doesn't "+\
             "depend on nonstandard/undocumented ELF and ld.so features, but "+\
             "is slightly larger. If not enabled, a smaller custom loader is "+\
             "used which assumes glibc.")
    parser.add_argument('-fskip-zero-value', default=False, action='store_true', \
        help="Skip an ELF symbol with a zero address (a weak symbol) when "+\
             "parsing libraries at runtime. Try enabling this if you're "+\
             "experiencing sudden breakage. However, many libraries don't use "+\
             "weak symbols, so this doesn't often pose a problem. Costs ~5 bytes.")
    parser.add_argument('-fuse-dt-debug', default=False, action='store_true', \
        help="Use the DT_DEBUG Dyn header to access the link_map, which doesn't"+\
             " depend on nonstandard/undocumented ELF and ld.so features. If "+\
             "not enabled, the link_map is accessed using data leaked to the "+\
             "entrypoint by ld.so, which assumes glibc. Costs ~10 bytes.")
    parser.add_argument('-fuse-dl-fini', default=False, action='store_true', \
        help="Pass _dl_fini to the user entrypoint, which should be done to "+\
             "properly comply with all standards, but is very often not "+\
             "needed at all. Costs 2 bytes.")
    parser.add_argument('-fskip-entries', default=False, action='store_true', \
        help="Skip the first two entries in the link map (resp. ld.so and "+\
             "the vDSO). Speeds up symbol resolving, but costs ~5 bytes.")
    parser.add_argument('-fno-start-arg', default=False, action='store_true', \
        help="Don't pass a pointer to argc/argv/envp to the entrypoint using "+\
             "the standard calling convention. This means you need to read "+\
             "these yourself in assembly if you want to use them! (envp is "+\
             "a preprequisite for X11, because it needs $DISPLAY.) Frees 3 bytes.")
    parser.add_argument('-funsafe-dynamic', default=False, action='store_true', \
        help="Don't end the ELF Dyn table with a DT_NULL entry. This might "+\
             "cause ld.so to interpret the entire binary as the Dyn table, "+\
             "so only enable this if you're sure this won't break things!")
    parser.add_argument('-fifunc-support', default=False, action='store_true', \
        help="Support linking to IFUNCs. Probably needed on x86_64, but costs "+\
             "~16 bytes. Ignored on platforms without IFUNC support.")
    parser.add_argument('-fifunc-strict-cconv', default=False, action='store_true', \
        help="On i386, if -fifunc-support is specified, strictly follow the "+\
             "calling convention rules. Probably not needed, but you never know.")

    parser.add_argument('--nasm', default=os.getenv('NASM') or shutil.which('nasm'), \
        help="which nasm binary to use")
    parser.add_argument('--cc', default=os.getenv('CC') or shutil.which('cc'), \
        help="which cc binary to use (MUST BE GCC!)")
    parser.add_argument('--scanelf', default=os.getenv('SCANELF') or shutil.which('scanelf'), \
        help="which scanelf binary to use")
    parser.add_argument('--readelf', default=os.getenv('READELF') or shutil.which('readelf'), \
        help="which readelf binary to use")

    parser.add_argument('-Wc','--cflags', default=[], metavar='CFLAGS', action='append',
        help="Flags to pass to the C compiler for the relinking step")
    parser.add_argument('-Wa','--asflags', default=[], metavar='ASFLAGS', action='append',
        help="Flags to pass to the assembler when creating the ELF header and runtime startup code")
    parser.add_argument('-Wl','--ldflags', default=[], metavar='LDFLAGS', action='append',
        help="Flags to pass to the linker for the final linking step")
    parser.add_argument('--smolrt', default=os.getcwd()+"/rt",
        help="Directory containing the smol runtime sources")
    parser.add_argument('--smolld', default=os.getcwd()+"/ld",
        help="Directory containing the smol linker scripts")

    parser.add_argument('--gen-rt-only', default=False, action='store_true', \
        help="Only generate the headers/runtime assembly source file, instead"+\
             " of doing a full link. (I.e. fall back to pre-release behavior.)")
    parser.add_argument('--verbose', default=False, action='store_true', \
        help="Be verbose about what happens and which subcommands are invoked")
    parser.add_argument('--keeptmp', default=False, action='store_true', \
        help="Keep temp files (only useful for debugging)")
    parser.add_argument('--debugout', type=str, default=None, \
        help="Write out an additional, unrunnable debug ELF file with symbol "+\
             "information. (Useful for debugging with gdb, cannot be ran due "+\
             "to broken relocations.)")

    parser.add_argument('input', nargs='+', help="input object file")
    parser.add_argument('output', type=str, help="output binary")

    args = parser.parse_args()

    if args.hash16:
        args.fuse_dnload_loader = True

    if args.fskip_zero_value: args.asflags.insert(0, "-DSKIP_ZERO_VALUE")
    if args.fuse_nx: args.asflags.insert(0, "-DUSE_NX")
    if args.fskip_entries: args.asflags.insert(0, "-DSKIP_ENTRIES")
    if args.funsafe_dynamic: args.asflags.insert(0, "-DUNSAFE_DYNAMIC")
    if args.fno_start_arg: args.asflags.insert(0, "-DNO_START_ARG")
    if args.fuse_dl_fini: args.asflags.insert(0, "-DUSE_DL_FINI")
    if args.fuse_dt_debug: args.asflags.insert(0, "-DUSE_DT_DEBUG")
    if args.fuse_dnload_loader: args.asflags.insert(0, "-DUSE_DNLOAD_LOADER")
    if args.fuse_interp: args.asflags.insert(0, "-DUSE_INTERP")
    if args.falign_stack: args.asflags.insert(0, "-DALIGN_STACK")
    if args.fifunc_support: args.asflags.insert(0, "-DIFUNC_SUPPORT")
    if args.fifunc_strict_cconv: args.asflags.insert(0, "-DIFUNC_CORRECT_CCONV")

    for x in ['nasm','cc','scanelf','readelf']:
        val = args.__dict__[x]
        if val is None or not os.path.isfile(val):
            error("'%s' binary%s not found" %
                  (x, ("" if val is None else (" ('%s')" % val))))

    arch = args.target.tolower() if len(args.target) != 0 else decide_arch(args.input)
    if arch not in archmagic:
        error("Unknown/unsupported architecture '%s'" % str(arch))
    if args.verbose: eprintf("arch: %s" % str(arch))

    objinput = None
    objinputistemp = False
    tmp_asm_file = args.output
    if not args.gen_rt_only:
        tmp_asm_file = tempfile.mkstemp(prefix='smoltab',suffix='.asm',text=True)
        tmp_asm_fd = tmp_asm_file[0]
        tmp_asm_file = tmp_asm_file[1]
    tmp_elf_file = tempfile.mkstemp(prefix='smolout',suffix='.o')
    os.close(tmp_elf_file[0])
    tmp_elf_file = tmp_elf_file[1]
    try:
        # if >1 input OR input is LTO object:
        if len(args.input) > 1 or has_lto_object(args.readelf, args.input):
            fd, objinput = tempfile.mkstemp(prefix='smolin',suffix='.o')
            objinputistemp = True
            os.close(fd)
            cc_relink_objs(args.verbose, args.cc, arch, args.input, objinput, args.cflags)
        else: objinput = args.input[0]

        # generate smol hashtab
        cc_paths = get_cc_paths(args.cc)
        syms = get_needed_syms(args.readelf, objinput)
        spaths = args.libdir + cc_paths['libraries']
        libraries = cc_paths['libraries']
        libs = list(find_libs(spaths, args.library))
        if args.verbose: eprintf("libs = %s" % str(libs))
        symbols = {}
        for symbol, reloc in syms:
            library = find_symbol(args.scanelf, libs, args.library, symbol)
            if not library:
                error("could not find symbol: {}".format(symbol))
            symbols.setdefault(library, [])
            symbols[library].append((symbol, reloc))

        with os.fdopen(tmp_asm_fd, mode='w') as taf:
            output(arch, symbols, args.nx, args.hash16, taf, args.det)
            if args.verbose:
                eprintf("wrote symtab to %s" % tmp_asm_file)

        # assemble hash table/ELF header
        nasm_assemble_elfhdr(args.verbose, args.nasm, arch, args.smolrt,
                             tmp_asm_file, tmp_elf_file, args.asflags)

        if not args.gen_rt_only:
            # link with LD into the final executable, w/ special linker script
            ld_link_final(args.verbose, args.cc, arch, args.smolld, [objinput, tmp_elf_file],
                          args.output, args.ldflags, False)
            if args.debugout is not None:
                ld_link_final(args.verbose, args.cc, arch, args.smolld, [objinput, tmp_elf_file],
                              args.debugout, args.ldflags, True)
    finally:
        if not args.keeptmp:
            if objinputistemp: os.remove(objinput)
            if not args.gen_rt_only: os.remove(tmp_asm_file)
            os.remove(tmp_elf_file)

if __name__ == '__main__':
    rv = main()
    if rv is None: pass
    else:
        try: sys.exit(int(rv))
        except: sys.exit(1)

