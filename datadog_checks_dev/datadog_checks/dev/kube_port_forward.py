# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
from contextlib import contextmanager

from .env import environment_run
from .ssh_tunnel import KillProcess, find_free_port, get_ip, run_background_command
from .structures import LazyFunction, TempDir

PID_FILE = 'kubectl.pid'


@contextmanager
def port_forward(namespace, deployment, remote_port):
    set_up = PortForwardUp(namespace, deployment, remote_port)
    key = 'kube_forward_{}_{}'.format(namespace, deployment)
    tear_down = KillProcess(key, 'kubectl.pid')

    with environment_run(up=set_up, down=tear_down) as result:
        yield result


class PortForwardUp(LazyFunction):
    def __init__(self, namespace, deployment, remote_port):
        self.namespace = namespace
        self.deployment = deployment
        self.remote_port = remote_port

    def __call__(self):
        key = 'kube_forward_{}_{}'.format(self.namespace, self.deployment)
        with TempDir(key) as temp_dir:
            local_port = find_free_port()
            command = [
                'kubectl',
                'port-forward',
                '--namespace',
                self.namespace,
                'deployment/{}'.format(self.deployment),
                '{}:{}'.format(local_port, self.remote_port),
            ]
            run_background_command(command, os.path.join(temp_dir, PID_FILE))
            return get_ip(), local_port
