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
def port_forward(kubeconfig, namespace, remote_port, deployment=None, service=None):
    """Use `kubectl` to forward a remote port locally."""
    if not deployment and not service:
        raise Exception("You must specify a deployment or service")
    if deployment:
        set_up = PortForwardUp(kubeconfig, namespace, remote_port, deployment=deployment)
        key = _build_temp_key(namespace, deployment, remote_port)
        tear_down = KillProcess(key, PID_FILE)
    else:
        set_up = PortForwardUp(kubeconfig, namespace, remote_port, service=service)
        key = _build_temp_key(namespace, service, remote_port)
        tear_down = KillProcess(key, PID_FILE)

    with environment_run(up=set_up, down=tear_down) as result:
        yield result


class PortForwardUp(LazyFunction):
    """Setup `kubectl port-forward`."""

    def __init__(self, kubeconfig, namespace, remote_port, deployment=None, service=None):
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.remote_port = remote_port
        self.deployment = deployment
        self.service = service

    def __call__(self):
        if self.deployment:
            key = _build_temp_key(self.namespace, self.deployment, self.remote_port)
            subject = 'deployment/{}'.format(self.deployment)
        else:
            key = _build_temp_key(self.namespace, self.service, self.remote_port)
            subject = 'service/{}'.format(self.service)

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
                    subject,
                    '{}:{}'.format(local_port, self.remote_port),
                ]
                env = os.environ.copy()
                env['KUBECONFIG'] = self.kubeconfig
                run_background_command(command, os.path.join(temp_dir, PID_FILE), env=env)
                return ip, local_port
