import sys


def read_keys(path):
    # open the file and read every line
    with open(path) as f:
        return [line.strip() for line in f]
