# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from contextlib import contextmanager

import pytest

from datadog_checks.dev import kube_port_forward
from datadog_checks.dev.kube_port_forward import PortForwardConfig, PortForwardUp, multiple_port_forward


@pytest.mark.parametrize('local_port', [None, 49152], ids=['allocated', 'provided'])
def test_port_forward_up(mocker, local_port):
    ip = '192.0.2.1'
    allocated_port = 49153
    expected_port = allocated_port if local_port is None else local_port
    mocker.patch.object(kube_port_forward, 'get_ip', return_value=ip)
    find_free_port = mocker.patch.object(kube_port_forward, 'find_free_port', return_value=allocated_port)
    run_background_command = mocker.patch.object(kube_port_forward, 'run_background_command')
    wait = mocker.patch.object(kube_port_forward, 'WaitForPortListening')

    result = PortForwardUp('kubeconfig', 'namespace', 8080, 'service', 'api', local_port)()

    assert result == (ip, expected_port)
    if local_port is None:
        find_free_port.assert_called_once_with(ip)
    else:
        find_free_port.assert_not_called()

    command, pid_file = run_background_command.call_args.args
    assert command == [
        'kubectl',
        'port-forward',
        '--address',
        f'localhost,{ip}',
        '--namespace',
        'namespace',
        'service/api',
        f'{expected_port}:8080',
    ]
    assert os.path.basename(pid_file) == kube_port_forward.PID_FILE
    assert run_background_command.call_args.kwargs['env']['KUBECONFIG'] == 'kubeconfig'
    wait.assert_called_once_with(ip, expected_port)
    wait.return_value.assert_called_once_with()


def test_multiple_port_forward(mocker):
    ip = '192.0.2.1'
    local_ports = [49152, 49153]
    configs = [
        PortForwardConfig('namespace', 2112, 'statefulset', 'weaviate'),
        PortForwardConfig('namespace', 8080, 'statefulset', 'weaviate'),
    ]
    stopped = []

    mocker.patch.object(kube_port_forward, 'get_ip', return_value=ip)
    find_free_ports = mocker.patch.object(kube_port_forward, 'find_free_ports', return_value=local_ports)

    @contextmanager
    def port_forward(kubeconfig, namespace, remote_port, resource, resource_name, local_port):
        assert kubeconfig == 'kubeconfig'
        yield ip, local_port
        stopped.append(local_port)

    mocker.patch.object(kube_port_forward, 'port_forward', side_effect=port_forward)

    with multiple_port_forward('kubeconfig', configs) as forwards:
        assert forwards == [(ip, 49152), (ip, 49153)]
        assert stopped == []

    find_free_ports.assert_called_once_with(ip, 2)
    assert kube_port_forward.port_forward.call_args_list == [
        mocker.call('kubeconfig', 'namespace', 2112, 'statefulset', 'weaviate', 49152),
        mocker.call('kubeconfig', 'namespace', 8080, 'statefulset', 'weaviate', 49153),
    ]
    assert stopped == [49153, 49152]
