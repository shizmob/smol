
import sys
import struct


def log(msg, file=sys.stdout):
    file.write(msg)
    file.write('\n')

def warn(msg):
    log(msg, file=sys.stderr)

def error(msg):
    log(msg, file=sys.stderr)
    sys.exit(1)


def hash_djb2(s):
    h = 5381
    for c in s:
        h = (h * 33 + ord(c)) & 0xFFFFFFFF
    return h

def readbyte(blob, off):
    return struct.unpack('<B', blob[off:off+1])[0], (off+1)

def readint(blob, off):
    return struct.unpack('<I', blob[off:off+4])[0], (off+4)

def readlong(blob, off):
    return struct.unpack('<Q', blob[off:off+8])[0], (off+8)

def readstr(blob, off):
    text = bytearray()
    while True:
        char, off = readbyte(blob, off)
        if char == 0:
            break

        text.append(char)

    return text.decode('utf-8'), off