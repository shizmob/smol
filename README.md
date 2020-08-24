# smol

Shoddy minsize-oriented linker

PoC by Shiz, bugfixing, 64-bit version and maintenance by PoroCYon,
enhancements and bugfixes by blackle.

## Dependencies

* GCC (not clang, as the latter doesn't support `nolto-rel` output), GNU ld,
  binutils, GNU make, ...
* nasm 2.13 or newer
* Python 3

## Usage

***NOTE***: Your entrypoint (`_start`) ***must*** be in a section called
`.text.startup._start`! Otherwise, the linker script will fail silently, and
the smol startup/symbol resolving code will jump to an undefined location.

***NOTE***: C++ exceptions, RTTI, global *external* variables, thread-local
storage, global constructors and destructors (the ELF `.ctors`/`.dtors`/
`attribute((con-/destructor))` things, not the C++ language constructs), ...
aren't supported yet, and probably won't be anytime soon.

```sh
# example:
./smold.py -fuse-dnload-loader [--opts...] -lfoo -lbar input.o... output.elf
```

```
usage: smold.py [-h] [-m TARGET] [-l LIB] [-L DIR] [-s | -c] [-n] [-d] [-g] [-fuse-interp] [-falign-stack]
                [-fskip-zero-value] [-fifunc-support] [-fuse-dnload-loader] [-fuse-nx] [-fuse-dt-debug]
                [-fuse-dl-fini] [-fskip-entries] [-fno-start-arg] [-funsafe-dynamic] [-fifunc-strict-cconv]
                [--nasm NASM] [--cc CC] [--readelf READELF] [-Wc CFLAGS] [-Wa ASFLAGS] [-Wl LDFLAGS]
                [--smolrt SMOLRT] [--smolld SMOLLD] [--gen-rt-only] [--verbose] [--keeptmp] [--debugout DEBUGOUT]
                input [input ...] output

positional arguments:
  input                 input object file
  output                output binary

optional arguments:
  -h, --help            show this help message and exit
  -m TARGET, --target TARGET
                        architecture to generate asm code for (default: auto)
  -l LIB, --library LIB
                        libraries to link against
  -L DIR, --libdir DIR  directories to search libraries in
  -s, --hash16          Use 16-bit (BSD2) hashes instead of 32-bit djb2 hashes. Implies -fuse-dnload-loader. Only
                        usable for 32-bit output.
  -c, --crc32c          Use Intel's crc32 intrinsic for hashing. Implies -fuse-dnload-loader. Conflicts with
                        `--hash16'.
  -n, --nx              Use NX (i.e. don't use RWE pages). Costs the size of one phdr, plus some extra bytes on
                        i386.
  -d, --det             Make the order of imports deterministic (default: just use whatever binutils throws at us)
  -g, --debug           Pass `-g' to the C compiler, assembler and linker. Only useful when `--debugout' is
                        specified.
  -fuse-interp          [Default ON] Include a program interpreter header (PT_INTERP). If not enabled, ld.so has to
                        be invoked manually by the end user. Disable with `-fno-use-interp'.
  -falign-stack         [Default ON] Align the stack before running user code (_start). If not enabled, this has to
                        be done manually. Costs 1 byte. Disable with `-fno-align-stack'.
  -fskip-zero-value     [Default: ON if `-fuse-dnload-loader' supplied, OFF otherwise] Skip an ELF symbol with a
                        zero address (a weak symbol) when parsing libraries at runtime. Try enabling this if you're
                        experiencing sudden breakage. However, many libraries don't use weak symbols, so this
                        doesn't often pose a problem. Costs ~5 bytes.Disable with `-fno-skip-zero-value'.
  -fifunc-support       [Default ON] Support linking to IFUNCs. Probably needed on x86_64, but costs ~16 bytes.
                        Ignored on platforms without IFUNC support. Disable with `-fno-fifunc-support'.
  -fuse-dnload-loader   Use a dnload-style loader for resolving symbols, which doesn't depend on
                        nonstandard/undocumented ELF and ld.so features, but is slightly larger. If not enabled, a
                        smaller custom loader is used which assumes glibc. `-fskip-zero-value' defaults to ON if
                        this flag is supplied.
  -fuse-nx              Don't use one big RWE segment, but use separate RW and RE ones. Use this to keep strict
                        kernels (PaX/grsec) happy. Costs at least the size of one program header entry.
  -fuse-dt-debug        Use the DT_DEBUG Dyn header to access the link_map, which doesn't depend on
                        nonstandard/undocumented ELF and ld.so features. If not enabled, the link_map is accessed
                        using data leaked to the entrypoint by ld.so, which assumes glibc. Costs ~10 bytes.
  -fuse-dl-fini         Pass _dl_fini to the user entrypoint, which should be done to properly comply with all
                        standards, but is very often not needed at all. Costs 2 bytes.
  -fskip-entries        Skip the first two entries in the link map (resp. ld.so and the vDSO). Speeds up symbol
                        resolving, but costs ~5 bytes.
  -fno-start-arg        Don't pass a pointer to argc/argv/envp to the entrypoint using the standard calling
                        convention. This means you need to read these yourself in assembly if you want to use them!
                        (envp is a preprequisite for X11, because it needs $DISPLAY.) Frees 3 bytes.
  -funsafe-dynamic      Don't end the ELF Dyn table with a DT_NULL entry. This might cause ld.so to interpret the
                        entire binary as the Dyn table, so only enable this if you're sure this won't break things!
  -fifunc-strict-cconv  On i386, if -fifunc-support is specified, strictly follow the calling convention rules.
                        Probably not needed, but you never know.
  --nasm NASM           which nasm binary to use
  --cc CC               which cc binary to use (MUST BE GCC!)
  --readelf READELF     which readelf binary to use
  -Wc CFLAGS, --cflags CFLAGS
                        Flags to pass to the C compiler for the relinking step
  -Wa ASFLAGS, --asflags ASFLAGS
                        Flags to pass to the assembler when creating the ELF header and runtime startup code
  -Wl LDFLAGS, --ldflags LDFLAGS
                        Flags to pass to the linker for the final linking step
  --smolrt SMOLRT       Directory containing the smol runtime sources
  --smolld SMOLLD       Directory containing the smol linker scripts
  --gen-rt-only         Only generate the headers/runtime assembly source file, instead of doing a full link. (I.e.
                        fall back to pre-release behavior.)
  --verbose             Be verbose about what happens and which subcommands are invoked
  --keeptmp             Keep temp files (only useful for debugging)
  --debugout DEBUGOUT   Write out an additional, unrunnable debug ELF file with symbol information. (Useful for
                        debugging with gdb, cannot be ran due to broken relocations.)
  --hang-on-startup     Hang on startup until a debugger breaks the code out of the loop. Only useful for debugging.
```

A minimal crt (and `_start` funcion) are provided in case you want to use `main`.

## smoldd

`smoldd.py` is a script that tries to resolve all symbols from the hashes when
imported by a `smol`-ified binary. This can thus be used to detect user mistakes
during dynamic linking. (Think of it as an equivalent of `ldd`, except that it
also checks whether the imported functions are present as well.)

```
usage: smoldd.py [-h] [--cc CC] [--readelf READELF] [--map MAP] [-s | -c] input

positional arguments:
  input              input file

optional arguments:
  -h, --help         show this help message and exit
  --cc CC            C compiler binary
  --readelf READELF  readelf binary
  --map MAP          Get the address of the symbol hash table from the linker map
                     output instead of attempting to parse the binary.
  -s, --hash16       Use 16-bit (BSD2) hashes instead of 32-bit djb2 hashes. Only
                     usable for 32-bit output.
  -c, --crc32c       Use Intel's crc32 intrinsic for hashing. Conflicts with `--hash16'.
```

## Debugging your smol-ified executable

So suddenly the output binaries are crashing, while non-smol-ified executables
run just fine. What could've happened?

First of all, it could be PEBCAK: are you compiling with the exact same set of
compiler flags for the optimized and the regular builds? There could always be
a broken codepath in the former.

Secondly, did you enable any of the "evil" flags that can possibly break
compatiblity, such as `-fno-use-interp`, `-fno-align-stack`,
`-fno-skip-zero-value`, `-fno-ifunc-support`, `-fno-start-arg`,
`-funsafe-dynamic`, etc.? Try disabling these first, or try specifying
`-fskip-zero-value`, `-fifunc-strict-cconv`, `-fuse-nx`, `-fuse-dt-debug`,
`-fuse-dl-fini` or `-fuse-dnload-loader` (or remove the last one if you already
were using it). If you had to enable `-fuse-dt-debug` or mess with
`-fuse-dnload-loader`, please file an issue. If you had to specify `-fuse-nx`,
please don't use PaX/grsec for democoding.

But let's assume smol is the cause of the issue here. The first thing you
should do, is to check whether the crash happens in smol's runtime linking
code, or your actual executable code. This can be done by adding an `int3`
(x86) or `bkpt` (ARM) instruction or `__builtin_trap()` intrinsic (GCC/clang)
at the very beginning of your `_start` function. If the binary is now exiting
with a `Trace/breakpoint trap` or `Undefined instruction` error (or something
similar) instead of a `Segmentation fault`, it means the segfault is happening
after smol's runtime linker code has ran.

### The error is happening in the smol runtime linking/startup code

A common source of crashes here is that a symbol actually might not have been
resolved correctly. Try checking the output of `smoldd.py`.

If that isn't the cause, it's time to dig out GDB (see a later section), find
out what roughly is going wrong, and send in an issue ticket.

### The error is happening after the smol runtime linking/startup code

If a segfault is happening here, it's most likely happening when the binary
tries to call an external function. One cause if this can be bad stack
alignment (try messing with `-f[no-]align-stack`, or fix your `_start` code).

Another is that a symbol might have a 'value' (relative address) of zero, which
means the function call turned into a jump to the ELF header of the library,
instead of to the actual function. In this case, try specifying the
`-fskip-zero-value` flag.

Of course, it's still entirely possible it's a yet-unknown calling convention,
reloction, or other issue. If it isn't one of the above known causes, it's yet
again time to dust off your GDB skills and open an issue.

### Attaching GDB to a smol-ified executable

As you might have noticed, GDB cannot run smol-ified executables by itself, as
the ELF headers are too messed up. However, the Linux kernel and glibc dynamic
linker are able to parse it just fine. This means you'll have to attach a live
process, ideally before it segfaults. As racing a below-one-millisecond
timeframe is difficult, there is another solution: specify the `--hang-on-startup`
flag. Then attach your (currently-stuck) process to GDB, increase the program
counter manually to break out of the infinite loop, then continue debugging as
usual.

However, here you don't have any symbols available (let alone DWARF source
info), which makes debugging a bit hard. This can be mitigated by specifying
the `-g` flag, and loading the file specified by the `--debugout` flag into gdb,
which will provide you with symbol and (if `-g` was specified) debugging info.

A quick overview:

```sh
python3 ./smold.py -g --hang-on-startup --debugout=path/to/out.smol.dbg \
    [usual args...] input... path/to/out.smol
path/to/out.smol # run it (it will hang)
^Z # background the hung process

# 1. attach the backgrounded process
# 2. break out of the loop (x86_64 example, s/rip/eip/g for i386)
# 3. load symbol and debugging info
gdb -ex "attach $(jobs sp)" \
    -ex 'set $rip=$rip+2' \
    path/to/out.smol.dbg
```

## Internal workings

`smol.py` inspects the input object files for needed library files and symbols.
It then outputs the list of needed libraries, hashes of the needed symbols and
provides stubs for the external functions. This is then combined with a
custom-made, small ELF header and 'runtime linker' which resolves the symbols
(from the hashes) so that the function stubs are usable.

The runtime linker uses an unorthodox way of resolving the symbols (which only
works for glibc): on both i386 and x86_64, the linker startup code
(`_dl_start_user`) leaks the global `struct link_map` to the user code:
on i386, a pointer to it is passed directly through `eax`:

```asm
# (eax, edx, ecx, esi) = (_dl_loaded, argc, argv, envp)
movl _rtld_local@GOTOFF(%ebx), %eax
## [ boring stuff... ]
pushl %eax
# Call the function to run the initializers.
call _dl_init
## eax still lives thanks to the ABI and calling convention
## [ boring stuff... ]
# Jump to the user's entry point.
jmp *%edi
## eax contains the pointer to the link_map!
```

On x86_64, it's a bit more convoluted: the contents of `_rtld_local` is loaded
into `rsi`, but because of the x86_64 ABI, the caller isn't required to restore
that register. However, due to the `call` instruction, a pointer to the
instruction after the call will be placed on the stack. And thus, at `_start`,
that pointer will be available at `rsp - 8`. Then, the offset to the "load from
`_rtld_local`"-instruction can be calculated, and the part of the instruction
which contains the offset to `_rtld_local`, from the instruction after the load
(of which the address is now also known), can be read, and thus the location
and contents of that global variable are available as well.

When using `DT_DEBUG`, a different mechanism is used to take hold of the
`struct link_map`: on program startup, `ld.so` will place a pointer to its
debug data in the value of the `DT_DEBUG` key-value-pair. In glibc, this is
the `r_debug` datatype. The second field of that type, is a pointer to the
root `struct link_map`.

Now the code continues with walking the "import tables" for the needed
libraries (which already have been automatically parsed by `ld.so`), looks
though their hash tables for the hashes of the imported symbols, gets their
addresses, and replaces the hashes in the table with the function addresses.

However, because the `struct link_map` can change between glibc versions,
especially the size of the `l_info` field (a fixed-size array, the `DT_*NUM`
constants tend to change every few versions). To remediate this, one can note
that the `l_entry` field comes a few bytes after `l_info`, that the root
`struct link_map` is the one of the main executable, and that the contents of
the `l_entry` field is known at compile-time. Thus, the loader scans the struct
for the entry point address, and uses that as an offset for the 'far fields' of
the `struct link_map`. ('Near' fields like `l_name` and `l_addr` are resp. 8
and 0, and will thus pretty much never change.)

## Greets

auld alrj blackle breadbox faemiyah gib3&tix0 las leblane parcelshit unlord

## License

[WTFPL](/LICENSE)

