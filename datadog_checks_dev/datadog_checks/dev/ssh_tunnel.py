# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
import socket
from contextlib import closing, contextmanager

from six import PY3

from .env import environment_run
from .structures import LazyFunction, TempDir
from .subprocess import run_command

if PY3:
    import subprocess
else:
    import subprocess32 as subprocess


def find_free_port():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def get_ip():
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]


@contextmanager
def socks_proxy(host, user, private_key):
    """Open a SSH connection with a SOCKS proxy."""
    set_up = SocksProxyUp(host, user, private_key)
    tear_down = SocksProxyDown()
    conditions = []

    with environment_run(up=set_up, down=tear_down, conditions=conditions) as result:
        yield result


class SocksProxyUp(LazyFunction):
    def __init__(self, host, user, private_key):
        self.host = host
        self.user = user
        self.private_key = private_key

    def __call__(self):
        with TempDir('socks_proxy') as temp_dir:
            local_port = find_free_port()
            key_file = os.path.join(temp_dir, 'ssh_key')
            with open(key_file, 'w') as f:
                f.write(self.private_key)
            os.chmod(key_file, 0o600)
            ip = get_ip()
            command = [
                'ssh',
                '-N',
                '-D',
                '{}:{}'.format(ip, local_port),
                '-i',
                key_file,
                '-o',
                'BatchMode=yes',
                '-o',
                'UserKnownHostsFile=/dev/null',
                '-o',
                'StrictHostKeyChecking=no',
                '{}@{}'.format(self.user, self.host),
            ]
            process = subprocess.Popen(command, start_new_session=True)
            with open(os.path.join(temp_dir, 'ssh.pid'), 'w') as ssh_pid:
                ssh_pid.write(str(process.pid))
            return ip, local_port


class SocksProxyDown(LazyFunction):
    def __call__(self):
        with TempDir('socks_proxy') as temp_dir:
            with open(os.path.join(temp_dir, 'ssh.pid')) as ssh_pid:
                pid = int(ssh_pid.read())
                run_command('kill {}'.format(pid))
                return 0
