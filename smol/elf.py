import enum


class ELFMachine(enum.IntEnum):
    i386 = 3
    x86_64 = 62


ELF_DEFAULT_BITS = {
    ELFMachine.i386: 32,
    ELFMachine.x86_64: 64
}