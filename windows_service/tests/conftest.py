# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.windows_service import WindowsService


@pytest.fixture
def check():
    return WindowsService('windows_service', {}, {}, None)


@pytest.fixture
def instance_bad_config():
    return {}


@pytest.fixture
def instance_basic():
    return {
        'services': ['EventLog', 'Dnscache', 'NonExistentService'],
        'tags': ['optional:tag1'],
    }


@pytest.fixture
def instance_wildcard():
    return {
        'host': '.',
        'services': ['Event.*', 'Dns%'],
    }


@pytest.fixture
def instance_all():
    return {
        'services': ['ALL'],
    }
