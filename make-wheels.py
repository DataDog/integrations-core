#!/usr/bin/env python3


'''
Author: Trishank Karthik Kuppusamy <trishank.kuppusamy@datadoghq.com>
Date: Nov 27 2017
Description: A simple Python script to build and test wheels.
'''


import os
import subprocess


def main():
    # Get non-hidden directories.
    dirs = sorted(name for name in os.listdir('.') \
                  if os.path.isdir(name) \
                  and not name.startswith('.'))
    # Get the current working directory.
    pwd = os.getcwd()
    # For each directory:
    for name in dirs:
        # Get the next working directory.
        nwd = os.path.join(pwd, name)
        # Change to the next working directory.
        os.chdir(nwd)
        # If the next working directory has 'setup.py', then we can build.
        if os.path.isfile('setup.py'):
            print('Trying to build {}...'.format(name), end='')
            # https://packaging.python.org/tutorials/distributing-packages/#wheels
            cmd = 'python setup.py bdist_wheel'.split()
            proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE)
            print('done.'.format(name))


if __name__ == '__main__':
    main()


