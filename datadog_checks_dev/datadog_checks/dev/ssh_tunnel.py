# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
import socket
import time
from contextlib import closing, contextmanager
from tempfile import TemporaryFile

from six import PY3

from .structures import TempDir

if PY3:
    import subprocess
else:
    import subprocess32 as subprocess


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('localhost', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_port_listening(host, port, retries=10, wait=1):
    for _ in range(retries):
        try:
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.connect((host, port))
        except socket.error:
            pass
        else:
            return
        time.sleep(wait)
    raise RuntimeError("Couldn't connect to {}:{}".format(host, port))


@contextmanager
def socks_proxy(local_port, host, user, private_key):
    """Open a SSH connection with a SOCKS proxy."""
    with TempDir('socks_proxy') as temp_dir:
        key_file = os.path.join(temp_dir, 'ssh_key')
        with open(key_file, 'w') as f:
            f.write(private_key)
        os.chmod(key_file, 0o600)
        command = [
            'ssh',
            '-N',
            '-D',
            'localhost:{}'.format(local_port),
            '-i',
            key_file,
            '-o',
            'BatchMode=yes',
            '-o',
            'UserKnownHostsFile=/dev/null',
            '-o',
            'StrictHostKeyChecking=no',
            '{}@{}'.format(user, host),
        ]
        stdin = TemporaryFile()
        stdout = TemporaryFile()
        process = subprocess.Popen(command, stdout=stdout, stdin=stdin, stderr=stdout)
        with process as p:
            wait_for_port_listening('localhost', local_port)
            yield p
            p.terminate()
