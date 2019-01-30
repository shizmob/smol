
import sys

archmagic = {
    'i386':    3,  3: 'i386'  ,
    'x86_64': 62, 62: 'x86_64',
}

def eprintf(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

