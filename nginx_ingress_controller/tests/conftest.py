# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest


@pytest.fixture(scope='session')
def dd_environment(instance):
    yield instance


@pytest.fixture(scope='session')
def instance():
    return {'prometheus_url': 'http://localhost:10249/metrics'}
