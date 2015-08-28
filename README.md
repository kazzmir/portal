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

Files passed to portal.py directory will be sent using the basename of the file. That is, any preceeding pathname that is part of the file will be removed and only the filename itself will be sent.

    $ portal.py /var/log/auth.log
	# The receiver will get a filename called 'auth.log'
	# /var/log will be removed from the path

Directories can be sent with portal. The directory structure and all files will also be sent in-tact.

# Sender
    /a/b/c/dir1
	|------ dir2/
	|------ dir2/x
	|------ y

    /a/b/c $ portal.py dir1
	Sending dir1
    /a/b/c $

# Receiver
    /x/y/z $ portal.py
	Reading file dir2/x size 23
	Reading file y size 9

	/x/y/z/dir1
	|------ dir2/
	|------ dir2/x
	|------ y

An alternative method is to copy the source file to /, then move it to the destination.

# Sender
	$ cp file1 /
# Receiver
	$ mv /file1 .

Its easier to use portal.py because the receiver doesnt have to retype the filenames again.
