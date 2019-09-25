# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys

import pytest
from mock import patch

from datadog_checks.dev.utils import ON_WINDOWS
from datadog_checks.http_check import HTTPCheck

from .common import CONFIG_E2E, HERE


@pytest.fixture(scope='session')
def dd_environment():
    cacert_path = os.path.join(HERE, 'fixtures', 'cacert.pem')
    e2e_metadata = {'docker_volumes': ['{}:/opt/cacert.pem'.format(cacert_path)]}
    yield CONFIG_E2E, e2e_metadata


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
