#!/usr/bin/env python

# Delimiter between json and file data
magic_delimiter = 0x7

# Send a json with a list of files and their sizes.
# {files: [{file1: 234234, file2: 23492}]}

def filename(path):
    import os.path
    return os.path.basename(path)

def size(path):
    import os
    return os.stat(path).st_size

def create_json(paths):
    import json
    import os.path

    files = []

    for v in paths:
        if os.path.isdir(v):
            for root, dirs, filenames in os.walk(v):
                for dir in dirs:
                    files.append({os.path.join(root, dir): -1})
                for file in filenames:
                    full = os.path.join(root, file)
                    files.append({full: size(full)})
        else:
            files.append({filename(v): size(v)})

    # data = {'files': [{filename(v): size(v)} for v in paths]}
    data = {'files': files}
    out = json.JSONEncoder().encode(data)
    # print out

    return out;

def send(pipe, data):
    pipe.write(data)

def make_fifo(mode):
    fifo_path = '/tmp/portal.fifo'
    import os.path
    if os.path.exists(fifo_path):
        return open(fifo_path, mode)
    os.mkfifo(fifo_path, 0600)
    return open(fifo_path, mode)

def read_file(path):
    f = open(path, 'r')
    bytes = f.read()
    f.close()
    return bytes

def read_json_data(pipe):
    out = []
    while True:
        byte = pipe.read(1)
        if ord(byte) == magic_delimiter:
            return ''.join(out)
        out.append(byte)

def read_json(pipe):
    print "Reading files from portal"
    text = read_json_data(pipe)
    # print text
    import json
    import os
    decoder = json.JSONDecoder()
    out, ignore = decoder.raw_decode(text)
    # print "Read json " + str(out)
    for file in out['files']:
        path = file.keys()[0]
        size = file[path]
        print "Reading file %s size %d" % (path, size)
        if size == -1:
            os.makedirs(path)
        else:
            f = open(path, 'w')
            bytes = pipe.read(size)
            f.write(bytes)
            f.close()

import sys
if len(sys.argv) > 1:
    import os.path
    fifo = make_fifo('w')
    json = create_json(sys.argv[1:])
    send(fifo, json)
    fifo.write(bytearray([magic_delimiter]))
    for path in sys.argv[1:]:
        print "Sending %s" % path
        if os.path.isfile(path):
            bytes = bytearray(read_file(path))
            send(fifo, bytes)
    fifo.close()
else:
    fifo = make_fifo('r')
    json = read_json(fifo)
    fifo.close()
