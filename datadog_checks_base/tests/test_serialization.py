# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest
from six import PY2

serialization = None


@pytest.fixture(autouse=True)
def load_serialization_module(caplog):
    global serialization

    if serialization is None:
        with caplog.at_level(logging.DEBUG):
            from datadog_checks.base.utils import serialization


@pytest.mark.skipif(PY2, reason='Dependency orjson does not support Python 2')
def test_fast_json(caplog):
    assert serialization.json.__name__ == 'orjson'

    expected_message = 'Using JSON implementation from orjson'
    for record in caplog.get_records('setup'):
        if record.levelno == logging.DEBUG and record.message == expected_message:
            break
    else:
        raise AssertionError('Expected DEBUG log with message `{}`'.format(expected_message))
