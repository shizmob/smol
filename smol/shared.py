
import sys
import traceback


archmagic = {
    'i386':    3,  3: 'i386'  ,
   # arm: 40
    'x86_64': 62, 62: 'x86_64',
}

HASH_DJB2 = 0
HASH_BSD2 = 1
HASH_CRC32C=2

define_for_hash = {
    HASH_DJB2: None
    HASH_BSD2: 'USE_HASH16',
    HASH_CRC32C: 'USE_CRC32C_HASH'
}


def hash_bsd2(s):
    h = 0
    for c in s:
        h = ((h >> 2) + ((h & 3) << 14) + ord(c)) & 0xFFFF
    return h


def hash_djb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + ord(c)) & 0xFFFFFFFF
    return h


def hash_crc32c(s):
    # crc32 implementation is basically:
    # sum = -1; for (; *s; ++s) crc32_instr(&sum, *s); return sum
    assert False, "not implemented!" # TODO


def eprintf(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def get_hash_id(h16, c32):
    if not h16 and not c32:
        return HASH_DJB2
    elif h16 and not c32:
        return HASH_BSD2
    elif not h16 and c32:
        return HASH_CRC32C
    else:
        return False, "??????? (shouldn't happen)"


def get_hash_fn(hid):
    return (hash_djb2, hash_bsd2, hash_crc32c)[hid]


def error(*args, **kwargs):
    traceback.print_stack()
    eprintf(*args, **kwargs)
    sys.exit(1)

