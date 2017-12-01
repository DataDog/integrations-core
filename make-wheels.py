#!/usr/bin/env python


# (C) Datadog, Inc. 2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


from __future__ import print_function


import glob
import os
import shlex
import subprocess


def main():
    # Get only directories for which there is a "setup.py."
    dirs = sorted(os.path.dirname(d) for d in glob.glob('./**/setup.py'))
    # Get the current working directory.
    pwd = os.getcwd()

    # For each directory:
    for name in dirs:
        # Get the next working directory.
        nwd = os.path.join(pwd, name)
        # Change to the next working directory.
        os.chdir(nwd)
        print('Trying to build {}...'.format(name))
        # https://packaging.python.org/tutorials/distributing-packages/#wheels
        cmd = shlex.split('python setup.py bdist_wheel')

        # Try building.
        try:
            stdout = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                             universal_newlines=True)
        # If something went wrong, reraise the exception.
        except:
            raise
        # In any case, print stdout+stderr.
        else:
            print(stdout)
            print()


if __name__ == '__main__':
    main()
