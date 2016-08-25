#!/usr/bin/env python

# Delimiter between json and file data
magic_delimiter = 0x7

# Send a json with a list of files and their sizes.
# {files: [{file1: 234234, file2: 23492}]}

# Higher values of debug output more information
debug = [0]
verbose = [0]
version = ["1.0"]

def filename(path):
    import os.path
    return os.path.basename(path)

def size(path):
    import os
    return os.stat(path).st_size

def check_file_ok(path):
    import os
    import os.path
    if not os.path.exists(path):
        print "%s does not exist" % path
        return False
    if not os.path.isfile(path):
        print "%s is not a file" % path
        return False
    if not os.access(path, os.R_OK):
        print "Cannot read %s" % path
        return False
    return True

def create_json(options):
    import json
    import os.path

    # Filter paths based on file expansion in the include/exclude options.
    # If it matches an include pattern then include it always
    # If it matches an exclude pattern then exclude it always
    # Otherwise include it
    def path_ok(path):
        import fnmatch
        if options.filter_include:
            for include in options.filter_include:
                if not fnmatch.fnmatch(path, include):
                    return False
        if options.filter_exclude:
            for exclude in options.filter_exclude:
                if fnmatch.fnmatch(path, exclude):
                    return False
        return True

    paths = options.args

    all = []
    for v in paths:
        v = v.rstrip('/')
        if os.path.isdir(v):
            group = {'dir': v}
            files = []
            for root, dirs, filenames in os.walk(v):
                for dir in dirs:
                    path = os.path.join(root, dir)
                    files.append({path: -1})
                for file in filenames:
                    full = os.path.join(root, file)
                    if path_ok(full) and check_file_ok(full):
                        files.append({full: size(full)})
            group['files'] = files
            all.append({'group': group})
        else:
            if path_ok(v) and check_file_ok(v):
                all.append({v: size(v)})

    if len(all) == 0:
        raise Exception("No files sent")

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
            read_json_file(pipe, prefix, -1)
            for subfile in file['group']['files']:
                path = subfile.keys()[0]
                size = subfile[path]
                read_json_file(pipe, os.path.join(prefix, path[len(base) + 1:]), size)
        else:
            path = file.keys()[0]
            size = file[path]
            read_json_file(pipe, filename(path), size)

def twoplaces(size):
    import decimal
    return decimal.Decimal(str(size)).quantize(decimal.Decimal(10) ** -2)

def nicesize(size):
    if size < 1024:
        return "%sB" % twoplaces(size)
    size /= 1024
    if size < 1024:
        return "%sK" % twoplaces(size)
    size /= 1024
    if size < 1024:
        return "%sM" % twoplaces(size)
    size /= 1024
    if size < 1024:
        return "%sG" % twoplaces(size)
    size /= 1024
    if size < 1024:
        return "%sT" % twoplaces(size)
    return "%sT" % twoplaces(size)

def send_file(fifo, file_data):
    path = file_data.keys()[0]
    size = file_data[path]
    print "Sending %s" % path
    if os.path.isfile(path):
        import time
        bytes = bytearray(read_file(path))
        start = time.time()
        send(fifo, bytes)
        end = time.time()
        if verbose[0] > 0:
            print "  sent %s in %fs at %s/s" % (nicesize(size), (end - start), nicesize(size / (end - start)))


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

class Options:
    def __init__(self):
        self.args = []
        self.debug = 0
        self.filter_include = []
        self.filter_exclude = []
        self.verbose = 0

def show_help():
    print "portal %s" % version[0]
    print " Sends files over a fifo on the local system. Another invocation of portal on the same system will read the files."
    print "Usage: portal [options] [files/directories ...]"
    print " -h: show help"
    print " -d --debug: Increase debug level"
    print " -v --verbose: Increase verbose level"
    print " --include <pattern>: Include files that match the given pattern, example *.txt. Multiple --include options can be given"
    print " --exclude <pattern>: Exclude files that match the given pattern. Muliple --exclude options can be given"

def process_args(args):
    options = Options()
    skip = []
    for arg in args:
        if skip:
            last = skip.pop()
            last(arg)
            continue
        if arg == '-d' or arg == '--debug':
            options.debug += 1
        elif arg == "-v" or arg == "--verbose":
            options.verbose += 1
        elif arg == "-h":
            show_help()
            import sys
            sys.exit(0)
        elif arg == '--include':
            def filter_arg(f):
                options.filter_include.append(f)
            skip.append(filter_arg)
        elif arg == '--exclude':
            def filter_arg(f):
                options.filter_exclude.append(f)
            skip.append(filter_arg)
        else:
            options.args.append(arg)
    return options

import sys
options = process_args(sys.argv[1:])
debug[0] = options.debug
verbose[0] = options.verbose
args = options.args
if len(args) >= 1:
    import os.path
    json = create_json(options)
    print "Waiting for a receiver to run portal to receive the data"
    fifo = make_fifo('w')
    send_json(fifo, json)
    
    fifo.close()
else:
    print "Receiving data from a portal sender"
    fifo = make_fifo('r')
    json = read_json(fifo)
    fifo.close()
