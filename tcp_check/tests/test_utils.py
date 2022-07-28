# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
from copy import deepcopy

import mock
import pytest

from datadog_checks.tcp_check.tcp_check import TCPCheck

from . import common

# from datadog_checks.base.utils.subprocess_output import get_subprocess_output


@pytest.mark.parametrize(
    'ping_output, hostname, getaddrinfo, gethostbyname_ex, expected_result',
    [
        pytest.param(
            ('output1', '', 0),
            'somehost',
            [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))],
            ('somehost', [], ['127.0.0.1']),
            True,
            id="Has public IPv6 connectivity",
        ),
        pytest.param(
            ('output2', 'err', 1),
            'another-host',
            [],
            ('another-host', [], ['127.0.0.1']),
            False,
            id="Does not have public IPv6",
        ),
        pytest.param(
            ('output3', 'err', 2),
            'hostname',
            [(socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('::ffff:127.0.0.1', 0, 0, 0))],
            ('hostname', [], ['127.0.0.1']),
            True,
            id="Does not have public IPv6, but has internal IPv6",
        ),
    ],
)
def test_has_ipv6_connectivity(monkeypatch, ping_output, hostname, getaddrinfo, gethostbyname_ex, expected_result):
    instance = deepcopy(common.INSTANCE_IPV6)
    instance['host'] = hostname
    check = TCPCheck(common.CHECK_NAME, {}, [instance])
    monkeypatch.setattr(
        'datadog_checks.base.utils.subprocess_output.get_subprocess_output', mock.Mock(return_value=ping_output)
    )
    monkeypatch.setattr('socket.gethostname', mock.Mock(return_value=hostname))
    monkeypatch.setattr('socket.gethostbyname_ex', mock.Mock(return_value=gethostbyname_ex))
    monkeypatch.setattr('socket.getaddrinfo', mock.Mock(return_value=getaddrinfo))

    check.check(instance)
    has_ipv6 = check.has_ipv6_connectivity()

    assert has_ipv6 == expected_result
