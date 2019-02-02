# smol

Shoddy minsize-oriented linker

PoC by Shiz, bugfixing and 64-bit version by PoroCYon.

## Usage

```sh
./smol.py -lfoo -lbar input.o... smol-output.asm
nasm -I src/ [-DUSE_NX] [-DUSE_DL_FINI] -o nasm-output.o smol-output.asm
ld -T ld/link.ld -o binary nasm-output.o input.o...
```

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
```

A minimal crt (and `_start` funcion) are provided in case you want to use `main`.

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
instruction after the call will be placed on the stack, at `_start`, it's at
`rsp - 8`. Then, the offset to the "load from `_rtld_local`"-instruction can be
calculated, and the part of the instruction which contains the offset to
`_rtld_local`, from the instruction after the load (of which the address is now
also known), can be read, and thus the contents of that global variable are
available as well.

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

