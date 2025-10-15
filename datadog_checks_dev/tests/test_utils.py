# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import socket
from contextlib import closing

import pytest

from datadog_checks.dev.utils import find_free_port, find_free_ports


def assert_ports_valid(ip, ports):
    assert all(isinstance(p, int) for p in ports)
    assert all(0 < port <= 65535 for port in ports)

    for port in ports:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.bind((ip, port))


@pytest.mark.parametrize('ip', ['127.0.0.1', '0.0.0.0'], ids=['localhost', 'any_interface'])
def test_find_free_port(ip):
    port = find_free_port(ip)

    assert_ports_valid(ip, [port])


@pytest.mark.parametrize(
    'ip,count',
    [
        ('127.0.0.1', 1),
        ('127.0.0.1', 5),
        ('127.0.0.1', 10),
        ('0.0.0.0', 3),
    ],
    ids=['localhost_single', 'localhost_multiple', 'localhost_many', 'any_interface'],
)
def test_find_free_ports(ip, count):
    ports = find_free_ports(ip, count)

    assert len(ports) == count
    assert len(ports) == len(set(ports))
    assert_ports_valid(ip, ports)


def test_find_free_ports_empty():
    ports = find_free_ports('127.0.0.1', 0)
    assert ports == []
