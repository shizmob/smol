# smol

Shoddy minsize-oriented linker

PoC by Shiz, bugfixing and 64-bit version by PoroCYon.

## Usage

```sh
./smol.py -lfoo -lbar input.o... smol-output.asm
nasm -I src/ [-Doption ...] -o nasm-output.o smol-output.asm
ld -T ld/link.ld --oformat=binary -o output.elf nasm-output.o input.o...
# or cc -T ld/link.ld -Wl,--oformat=binary -o output.elf nasm-output.o input.o...
```

* `USE_INTERP`: Include an interp segment in the output ELF file. If not, the
  dynamic linker **must** be invoked *explicitely*! (You probably want to
  enable this.) Costs the size of a phdr plus the size of the interp string.
* `ALIGN_STACK`: *64-bit only*: realign the stack so that SSE instructions
  won't segfault. Costs 1 byte.
* `USE_NX`: Don't use `RWE` segments at all. Not very well tested. Costs the
  size of 1 phdr, plus some extra stuff on `i386`. Don't forget to pass `-n`
  to `smol.py` as well.
* `USE_DL_FINI`: keep track of the `_dl_fini` function and pass it to your
  `_start`. Costs 2 bytes, plus maybe a few more depending on how it's passed
  to `__libc_start_main`.
* `USE_DT_DEBUG`: retrieve the `struct link_map` from the `r_debug` linker
  data (which is placed at `DT_DEBUG` at startup) instead of exploiting data
  leakage from `_dt_start_user`. Might be more compatible and compressable, but
  strictly worse size-wise by 10 (i386) or 3 (x86_64) bytes.
* `SKIP_ENTRIES`: skip the first two entries of the `struct link_map`, which
  represent the main binary and the vDSO. Costs around 5 bytes.
* `USE_DNLOAD_LOADER`: use the symbol loading mechanism as used in dnload (i.e.
  traverse the symtab of the imported libraries). Slightly larger, but probably
  better compressable and more compatible with other libcs and future versions
  of glibc.
* `NO_START_ARG`: *don't* pass the stack pointer to `_start` as the first arg.
  Will make it unable to read argc/argv/environ, but gives you 3 bytes.
* `SKIP_ZERO_VALUE`: skip a `Sym` with a `st_value` field of `0`. If this isn't
  enabled, weak symbols etc. might be imported instead of the real ones,
  causing breakage. Many libraries don't have weak symbols at all, though.
  Costs 4 (i386) or 5 (x86_64) bytes.

```
usage: smol.py [-h] [-m TARGET] [-l LIB] [-L DIR] [--nasm NASM] [--cc CC]
               [--scanelf SCANELF] [--readelf READELF]
               input [input ...] output

positional arguments:
  input                 input object file
  output                output nasm file

optional arguments:
  -h, --help            show this help message and exit
  -m TARGET, --target TARGET
                        architecture to generate asm code for (default: auto)
  -l LIB, --library LIB
                        libraries to link against
  -L DIR, --libdir DIR  directories to search libraries in
  --nasm NASM           which nasm binary to use
  --cc CC               which cc binary to use
  --scanelf SCANELF     which scanelf binary to use
  --readelf READELF     which readelf binary to use
  -n, --nx              Use NX (i.e. don't use RWE pages). Costs the size of
                        one phdr, plus some extra bytes on i386. Don't forget
                        to pass -DUSE_NX to the assembly loader as well!

```

A minimal crt (and `_start` funcion) are provided in case you want to use `main`.

## smoldd

`smoldd.py` is a script that tries to resolve all symbols from the hashes when
imported by a `smol`-ified binary. This can thus be used to detect user mistakes
during dynamic linking. (Think of it as an equivalent of `ldd`, except that it
also checks whether the imported functions are present as well.)

***NOTE***: `smoldd.py` currently doesn't support 64-bit binaries anymore, as
there's currently no (good) way of retrieving the symbol hash table anymore.

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

```s
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

