# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
MOCKED_INSTANCE = {
    'url': 'mocked',
    'username': 'datadog',
    'password': 'password',
    'tags': ['foo:bar'],
}

SESSION_MASTER = {
    'Status': 'Success',
    'Value': 'OpaqueRef:c908ccc4-4355-4328-b07d-c85dc7242b03',
}
SESSION_SLAVE = {
    'Status': 'Failure',
    'ErrorDescription': ['HOST_IS_SLAVE', '192.168.101.102'],
}
SESSION_ERROR = {
    'Status': 'Failure',
    'ErrorDescription': ['SESSION_AUTHENTICATION_FAILED'],
}

SERVER_TYPE_SESSION_MAP = {
    'master': SESSION_MASTER,
    'slave': SESSION_SLAVE,
    'error': SESSION_ERROR,
}


def mocked_xenserver(server_type):
    xenserver = mock.MagicMock()
    xenserver.session.login_with_password.return_value = SERVER_TYPE_SESSION_MAP.get(server_type, {})
    return xenserver
