portal.py sends files across the filesystem using a global fifo. The utility is that copying files between disparate directories is very simple. The global fifo name is currently /tmp/portal.fifo

# Sender
    /a/b/c $ portal.py file1 file2
    Sending file1
    Sending file2

# Receiver
	/x/y/z $ portal.py
	Reading file file1 size 2342
	Reading file file2 size 943
	/x/y/z $ ls
	file1 file2

An alternative method is to copy the source file to /, then move it to the destination.

# Sender
	$ cp file1 /
# Receiver
	$ mv /file1 .

Its easier to use portal.py because the receiver doesnt have to retype the filenames again.
