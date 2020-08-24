# smol

Shoddy minsize-oriented linker

PoC by Shiz, bugfixing and 64-bit version by PoroCYon.

## Dependencies

* GCC (not clang, as the latter doesn't support `nolto-rel` output), GNU ld,
  binutils, GNU make, ...
* nasm 2.13 or newer
* Python 3

## Usage

***NOTE***: Your entrypoint (`_start`) ***must*** be in a section called
`.text.startup._start`! Otherwise, the linker script will fail silently, and
the smol startup/symbol resolving code will jump to an undefined location.

```sh
./smold.py --use_interp --align_stack [--opts...] -lfoo -lbar input.o... output.elf
```

```
usage: smold.py [-h] [-m TARGET] [-l LIB] [-L DIR] [-s] [-n] [-d] [-fuse-interp] [-falign-stack] [-fuse-nx]
                [-fuse-dnload-loader] [-fskip-zero-value] [-fuse-dt-debug] [-fuse-dl-fini] [-fskip-entries]
                [-fno-start-arg] [-funsafe-dynamic] [--nasm NASM] [--cc CC] [--readelf READELF]
                [--cflags CFLAGS] [--asflags ASFLAGS] [--ldflags LDFLAGS] [--smolrt SMOLRT] [--smolld SMOLLD]
                [--verbose] [--keeptmp]
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
  -s, --hash16          Use 16-bit (BSD) hashes instead of 32-bit djb2 hashes. Implies -fuse-dnload-loader
  -n, --nx              Use NX (i.e. don't use RWE pages). Costs the size of one phdr, plus some extra bytes on
                        i386.
  -d, --det             Make the order of imports deterministic (default: just use whatever binutils throws at us)
  -fuse-interp          Include a program interpreter header (PT_INTERP). If not enabled, ld.so has to be invoked
                        manually by the end user.
  -falign-stack         Align the stack before running user code (_start). If not enabled, this has to be done
                        manually. Costs 1 byte.
  -fuse-nx              Don't use one big RWE segment, but use separate RW and RE ones. Use this to keep strict
                        kernels (PaX/grsec) happy. Costs at least the size of one program header entry.
  -fuse-dnload-loader   Use a dnload-style loader for resolving symbols, which doesn't depend on
                        nonstandard/undocumented ELF and ld.so features, but is slightly larger. If not enabled, a
                        smaller custom loader is used which assumes glibc.
  -fskip-zero-value     Skip an ELF symbol with a zero address (a weak symbol) when parsing libraries at runtime.
                        Try enabling this if you're experiencing sudden breakage. However, many libraries don't use
                        weak symbols, so this doesn't often pose a problem. Costs ~5 bytes.
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
  --nasm NASM           which nasm binary to use
  --cc CC               which cc binary to use (MUST BE GCC!)
  --readelf READELF     which readelf binary to use
  --cflags CFLAGS       Flags to pass to the C compiler for the relinking step
  --asflags ASFLAGS     Flags to pass to the assembler when creating the ELF header and runtime startup code
  --ldflags LDFLAGS     Flags to pass to the linker for the final linking step
  --smolrt SMOLRT       Directory containing the smol runtime sources
  --smolld SMOLLD       Directory containing the smol linker scripts
  --verbose             Be verbose about what happens and which subcommands are invoked
  --keeptmp             Keep temp files (only useful for debugging)
```

A minimal crt (and `_start` funcion) are provided in case you want to use `main`.

## smoldd

`smoldd.py` is a script that tries to resolve all symbols from the hashes when
imported by a `smol`-ified binary. This can thus be used to detect user mistakes
during dynamic linking. (Think of it as an equivalent of `ldd`, except that it
also checks whether the imported functions are present as well.)

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

