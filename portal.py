#!/usr/bin/env python

# Delimiter between json and file data
magic_delimiter = 0x7

# Send a json with a list of files and their sizes.
# {files: [{file1: 234234, file2: 23492}]}

# Higher values of debug output more information
debug = [0]

def filename(path):
    import os.path
    return os.path.basename(path)

def size(path):
    import os
    return os.stat(path).st_size

def create_json(paths):
    import json
    import os.path

    all = []
    for v in paths:
        if os.path.isdir(v):
            group = {'dir': v}
            files = []
            for root, dirs, filenames in os.walk(v):
                for dir in dirs:
                    path = os.path.join(root, dir)
                    files.append({path: -1})
                for file in filenames:
                    full = os.path.join(root, file)
                    files.append({full: size(full)})
            group['files'] = files
            all.append({'group': group})
        else:
            all.append({v: size(v)})

    # data = {'files': [{filename(v): size(v)} for v in paths]}
    data = {'files': all}
    out = json.JSONEncoder().encode(data)
    if debug[0] > 0:
        print out

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

# Read either a file or a directory name. If the size is -1 then its a directory, otherwise
# its a file whose length is size
def read_json_file(pipe, path, size):
    import os
    import os.path
    if size == -1:
        if not os.path.isdir(path):
            print "Creating directory %s" % path
            os.makedirs(path)
    else:
        print "Reading file %s size %d" % (path, size)
        f = open(path, 'w')
        bytes = pipe.read(size)
        f.write(bytes)
        f.close()

def read_json(pipe):
    print "Reading files from portal"
    text = read_json_data(pipe)
    # print text
    import json
    import os.path
    decoder = json.JSONDecoder()
    out, ignore = decoder.raw_decode(text)
    # print "Read json " + str(out)
    if debug[0] > 0:
        print str(out)
    for file in out['files']:
        if 'group' in file:
            base = file['group']['dir']
            prefix = filename(base)
            for subfile in file['group']['files']:
                path = subfile.keys()[0]
                size = subfile[path]
                read_json_file(pipe, os.path.join(prefix, path[len(base) + 1:]), size)
        else:
            path = file.keys()[0]
            size = file[path]
            read_json_file(pipe, filename(path), size)

def send_file(fifo, file_data):
    path = file_data.keys()[0]
    size = file_data[path]
    print "Sending %s" % path
    if os.path.isfile(path):
        bytes = bytearray(read_file(path))
        send(fifo, bytes)


def send_json(fifo, json_data):
    import json
    send(fifo, json_data)
    fifo.write(bytearray([magic_delimiter]))

    data = json.JSONDecoder().decode(json_data)

    for file in data['files']:
        if 'group' in file:
            for subfile in file['group']['files']:
                send_file(fifo, subfile)
        else:
            send_file(fifo, file)

def process_args(args):
    out = []
    for arg in args:
        if arg == '-d' or arg == '--debug':
            debug[0] += 1
        else:
            out.append(arg)
    return out

import sys
args = process_args(sys.argv[1:])
if len(args) >= 1:
    import os.path
    json = create_json(args)
    print "Waiting for a receiver to run portal to receive the data"
    fifo = make_fifo('w')
    send_json(fifo, json)
    
    fifo.close()
else:
    print "Receiving data from a portal sender"
    fifo = make_fifo('r')
    json = read_json(fifo)
    fifo.close()
