
import sys

archmagic = {
    'i386': 3, 3: 'i386',
    ##'arm': 40, 40: 'arm',
    #'x86_64': 62, 62: 'x86_64',
    ###'aarch64': 183, 183: 'aarch64'
}

def eprintf(*args, **kwargs): print(*args, file=sys.stderr, **kwargs)

