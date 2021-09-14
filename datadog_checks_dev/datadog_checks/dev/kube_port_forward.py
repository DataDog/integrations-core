# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
from contextlib import contextmanager

from .env import environment_run
from .fs import chdir
from .ssh_tunnel import KillProcess, run_background_command
from .structures import LazyFunction, TempDir
from .utils import find_free_port, get_ip

PID_FILE = 'kubectl.pid'


def _build_temp_key(namespace, deployment, remote_port):
    return 'kube_forward_{}_{}_{}'.format(namespace.replace('-', '_'), deployment.replace('-', '_'), remote_port)


@contextmanager
def port_forward(kubeconfig, namespace, remote_port, resource, resource_name):
    """Use `kubectl` to forward a remote port locally."""
    set_up = PortForwardUp(kubeconfig, namespace, remote_port, resource, resource_name)
    key = _build_temp_key(namespace, resource_name, remote_port)
    tear_down = KillProcess(key, PID_FILE)

    with environment_run(up=set_up, down=tear_down) as result:
        yield result


class PortForwardUp(LazyFunction):
    """Setup `kubectl port-forward`."""

    def __init__(self, kubeconfig, namespace, remote_port, resource, resource_name):
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.remote_port = remote_port
        self.resource = resource
        self.resource_name = resource_name

    def __call__(self):
        key = _build_temp_key(self.namespace, self.resource_name, self.remote_port)
        with TempDir(key) as temp_dir:
            # Run in the temp dir to put kube cache files there
            with chdir(temp_dir):
                ip = get_ip()
                local_port = find_free_port(ip)
                command = [
                    'kubectl',
                    'port-forward',
                    '--address',
                    ip,
                    '--namespace',
                    self.namespace,
                    "{}/{}".format(self.resource, self.resource_name),
                    '{}:{}'.format(local_port, self.remote_port),
                ]
                env = os.environ.copy()
                env['KUBECONFIG'] = self.kubeconfig
                run_background_command(command, os.path.join(temp_dir, PID_FILE), env=env)
                return ip, local_port
