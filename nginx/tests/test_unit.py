# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from copy import deepcopy

import mock

from .common import FIXTURES_PATH
from .utils import mocked_perform_request


def test_flatten_json(check):
    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_in.json')) as f:
        parsed = check.parse_json(f.read())
        parsed.sort()

    with open(os.path.join(FIXTURES_PATH, 'nginx_plus_out.python')) as f:
        expected = eval(f.read())

    # Check that the parsed test data is the same as the expected output
    assert parsed == expected


def test_plus_api(check, instance, aggregator):
    instance = deepcopy(instance)
    instance['use_plus_api'] = True
    check._perform_request = mock.MagicMock(side_effect=mocked_perform_request)
    check.check(instance)

    total = 0
    for m in aggregator.metric_names:
        total += len(aggregator.metrics(m))
    assert total == 1180


def test_nest_payload(check):
    keys = ["foo", "bar"]
    payload = {"key1": "val1", "key2": "val2"}

    result = check._nest_payload(keys, payload)
    expected = {"foo": {"bar": payload}}

    assert result == expected
