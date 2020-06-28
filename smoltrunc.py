#!/usr/bin/env python3

import argparse
import sys

def main(argv):
    parser = argparse.ArgumentParser()
    # TODO: output null -> in-place!
    parser.add_argument('input', type=argparse.FileType('rb'), \
                        help="input file to truncate")
    parser.add_argument('output', type=argparse.FileType('wb'), \
                        help="output file")

    args = parser.parse_args()

    data = args.input.read()

    i = 0
    while data[-i - 1] == 0:
        i = i + 1

    args.output.write(data[0:len(data)-i])

if __name__ == '__main__':
    rv = main(sys.argv)
    exit(0 if rv is None else rv)

