# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest
from datadog_test_libs.mock_dns import mock_e2e_agent, mock_socket
from mock import patch

from datadog_checks.dev import docker_run
from datadog_checks.dev.utils import ON_WINDOWS
from datadog_checks.http_check import HTTPCheck

from .common import CONFIG_E2E, HERE

MOCKED_HOSTS = ['valid.mock', 'expired.mock', 'wronghost.mock', 'selfsigned.mock']


@pytest.fixture(scope='session')
def dd_environment(mock_local_http_dns):
    cacert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    e2e_metadata = {'docker_volumes': ['{}:/opt/cacert.pem'.format(cacert_path)]}
    with docker_run(
        os.path.join(HERE, 'compose', 'docker-compose.yml'), build=True, log_patterns=["starting server on port"]
    ):
        yield CONFIG_E2E, e2e_metadata


@pytest.fixture(scope='session')
def mock_http_e2e_hosts():
    """Only for e2e testing"""
    with mock_e2e_agent('http_check', MOCKED_HOSTS):
        yield


@pytest.fixture(scope='session')
def mock_local_http_dns():
    mapping = {x: ('127.0.0.1', 443) for x in MOCKED_HOSTS}
    with mock_socket(mapping):
        yield


@pytest.fixture(scope='session')
def http_check():
    # Patch the function to return the certs located in the `tests/` folder
    with patch('datadog_checks.http_check.http_check.get_ca_certs_path', new=mock_get_ca_certs_path):
        yield HTTPCheck('http_check', {}, [{}])


@pytest.fixture(scope='session')
def embedded_dir():
    if ON_WINDOWS:
        return 'embedded{}'.format(sys.version_info[0])
    else:
        return 'embedded'


def mock_get_ca_certs_path():
    """
    Mimic get_ca_certs_path() by using the certificates located in the `tests/` folder
    """
    embedded_certs = os.path.join(HERE, 'fixtures', 'cacert.pem')

    if os.path.exists(embedded_certs):
        return embedded_certs

    raise Exception("Embedded certs not found: {}".format(embedded_certs))
