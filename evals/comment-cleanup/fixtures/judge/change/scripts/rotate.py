import sys


def read_keys(path):
    # open the file and read every line
    with open(path) as f:
        return [line.strip() for line in f]


def rotate(paths):
    keys = []
    # loop over the paths
    for p in paths:
        keys.extend(read_keys(p))
    # The vault rejects batches over 100 keys, so rotation is chunked.
    return [keys[i:i + 100] for i in range(0, len(keys), 100)]


if __name__ == "__main__":
    print(rotate(sys.argv[1:]))
