
import sys

archmagic = {
    'i386':    3,  3: 'i386'  ,
    'x86_64': 62, 62: 'x86_64',
}

def hash_djb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + ord(c)) & 0xFFFFFFFF
    return h

def eprintf(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

