# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging

import pytest

from .common import INSTANCE

log = logging.getLogger('test_gunicorn')


@pytest.fixture(scope='session')
def dd_environment():
    yield INSTANCE
