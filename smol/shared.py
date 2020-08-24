
import sys
import traceback


archmagic = {
    'i386':    3,  3: 'i386'  ,
   # arm: 40
    'x86_64': 62, 62: 'x86_64',
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


def eprintf(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def error(*args, **kwargs):
    traceback.print_stack()
    eprintf(*args, **kwargs)
    sys.exit(1)

