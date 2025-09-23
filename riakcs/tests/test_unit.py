# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from ast import literal_eval
from socket import error as SocketError

import pytest

from . import common

pytestmark = pytest.mark.unit


def test_parser(mocked_check):
    input_json = common.read_fixture('riakcs_in.json')
    output_python = common.read_fixture('riakcs_out.python')
    assert mocked_check.load_json(input_json) == literal_eval(output_python)


def test_metrics(mocked_check, aggregator, instance):
    mocked_check.check(instance)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)


def test_service_checks(check, aggregator):
    instance = {"access_id": "foo", "access_secret": "bar", 'host': 'foo.proxy.com', "tags": ["optional:tag1"]}
    tags = ['aggregation_key:foo.proxy.com:8080', 'optional:tag1']
    with pytest.raises(SocketError):
        check.check(instance)

    aggregator.assert_service_check(common.SERVICE_CHECK_NAME, status=check.CRITICAL, tags=tags, count=1)


def test_21_parser(mocked_check21):
    input_json = common.read_fixture('riakcs21_in.json')
    output_python = common.read_fixture('riakcs21_out.python')
    assert mocked_check21.load_json(input_json) == literal_eval(output_python)


def test_21_metrics(mocked_check21, aggregator, instance21):
    mocked_check21.check(instance21)
    for metric in common.EXPECTED_METRICS_21:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    assert len(aggregator.metrics("riakcs.bucket_policy_get_in_one")) == 0
