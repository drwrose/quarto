#! /usr/bin/env python

import getopt
import socket
import sys
import os

# Change to the starting directory.
try:
    __file__
except:
    this_dir = None
    pass
else:
    this_dir = os.path.split(__file__)[0]
    if this_dir:
        os.chdir(this_dir)

from BoardGameArena import BoardGameArena

help = """
This script starts up the BoardGameArena client that drives Quarto AI.

Options:

    -l logfile
        Send output to the indicated log file.

    -d pid_file
        Run in daemon mode, and write the pid number to the indicated
        file.  Unix/Mac only.

"""

def usage(code, msg = ''):
    print >> sys.stderr, help
    print >> sys.stderr, msg
    sys.exit(code)

try:
    opts, args = getopt.getopt(sys.argv[1:], 'l:d:h')
except getopt.error:
    import pdb; pdb.set_trace()
    usage(1, msg)

logfile_name = None
daemon = False

for opt, arg in opts:
    if opt == '-l':
        logfile_name = arg
    elif opt == '-d':
        daemon = True
        pidfile = arg
    elif opt == '-h':
        usage(0)

if logfile_name:
    # We use os.dup2() here to map the underlying, C-level stdout and
    # stderr to the logfile, so our C++-based Quarto library will also
    # send its output to the log.
    logfile = open(logfile_name, 'w', buffering = 1, encoding = 'utf-8')
    print("logfile.fileno = %s" % (logfile.fileno()))
    os.dup2(logfile.fileno(), 1)
    os.dup2(logfile.fileno(), 2)

    # Then we remap the Python-level objects too.
    sys.stdout = logfile
    sys.stderr = logfile

if daemon:
    if not hasattr(os, 'fork'):
        print >> sys.stderr, "Daemon mode is not supported on this platform."
        sys.exit(1)
    else:
        child_pid = os.fork()
        if child_pid == 0:
            # In the first child.  Fork again.
            grandchild_pid = os.fork()
            if grandchild_pid == 0:
                # In the grandchild.  Here's where we'll run.
                if hasattr(os, 'setpgid'):
                    os.setpgid(0, 0)

            else:
                # In the first child.  Write the grandchild pid number
                # to the pidfile, then gracefully exit.
                f = open(pidfile, 'w')
                f.write('%s\n' % (grandchild_pid))
                f.close()
                os._exit(0)
        else:
            # In the parent.  Wait for the first child to exit.
            pid, status = os.wait()
            if status == 0:
                os._exit(0)
            else:
                os._exit(1)

bga = BoardGameArena()
bga.serve()
