# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import absolute_import

import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Iterator

from .conditions import WaitForPortListening
from .env import environment_run
from .fs import chdir
from .ssh_tunnel import KillProcess, run_background_command
from .structures import LazyFunction, TempDir
from .utils import find_free_port, find_free_ports, get_ip

PID_FILE = 'kubectl.pid'


@dataclass(frozen=True)
class PortForwardConfig:
    namespace: str
    remote_port: int
    resource: str
    resource_name: str


def _build_temp_key(namespace, deployment, remote_port):
    return 'kube_forward_{}_{}_{}'.format(namespace.replace('-', '_'), deployment.replace('-', '_'), remote_port)


@contextmanager
def port_forward(
    kubeconfig: str,
    namespace: str,
    remote_port: int,
    resource: str,
    resource_name: str,
    local_port: int | None = None,
) -> Iterator[tuple[str, int]]:
    """Use `kubectl` to forward a remote port locally."""
    set_up = PortForwardUp(kubeconfig, namespace, remote_port, resource, resource_name, local_port)
    key = _build_temp_key(namespace, resource_name, remote_port)
    tear_down = KillProcess(key, PID_FILE)

    with environment_run(up=set_up, down=tear_down) as result:
        yield result


@contextmanager
def multiple_port_forward(kubeconfig: str, configs: list[PortForwardConfig]) -> Iterator[list[tuple[str, int]]]:
    """Forward multiple remote ports to distinct local ports."""
    ip = get_ip()
    local_ports = find_free_ports(ip, len(configs))

    with ExitStack() as stack:
        forwards = [
            stack.enter_context(
                port_forward(
                    kubeconfig,
                    config.namespace,
                    config.remote_port,
                    config.resource,
                    config.resource_name,
                    local_port,
                )
            )
            for config, local_port in zip(configs, local_ports, strict=True)
        ]
        yield forwards


class PortForwardUp(LazyFunction):
    """Setup `kubectl port-forward`."""

    def __init__(
        self,
        kubeconfig: str,
        namespace: str,
        remote_port: int,
        resource: str,
        resource_name: str,
        local_port: int | None = None,
    ) -> None:
        self.kubeconfig = kubeconfig
        self.namespace = namespace
        self.remote_port = remote_port
        self.resource = resource
        self.resource_name = resource_name
        self.local_port = local_port

    def __call__(self):
        key = _build_temp_key(self.namespace, self.resource_name, self.remote_port)
        with TempDir(key) as temp_dir:
            # Run in the temp dir to put kube cache files there
            with chdir(temp_dir):
                ip = get_ip()
                local_port = self.local_port if self.local_port is not None else find_free_port(ip)
                command = [
                    'kubectl',
                    'port-forward',
                    '--address',
                    # Explicitly add localhost to avoid getting a popup each time we use this
                    'localhost,{}'.format(ip),
                    '--namespace',
                    self.namespace,
                    "{}/{}".format(self.resource, self.resource_name),
                    '{}:{}'.format(local_port, self.remote_port),
                ]
                env = os.environ.copy()
                env['KUBECONFIG'] = self.kubeconfig
                run_background_command(command, os.path.join(temp_dir, PID_FILE), env=env)
                WaitForPortListening(ip, local_port)()
                return ip, local_port
