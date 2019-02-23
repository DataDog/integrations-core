# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from ast import literal_eval
from socket import error as SocketError

from . import common

pytestmark = pytest.mark.unit


def test_parser(mocked_check):
    input_json = common.read_fixture('riakcs_in.json')
    output_python = common.read_fixture('riakcs_out.python')
    assert mocked_check.load_json(input_json) == literal_eval(output_python)


def test_metrics(mocked_check, aggregator, instance):
    with mock.patch("datadog_checks.riakcs.riakcs.S3Connection"):
        mocked_check.check(instance)
    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)


def test_service_checks(check, aggregator, instance):
    with pytest.raises(SocketError):
        check.check(instance)

    aggregator.assert_service_check(
        common.SERVICE_CHECK_NAME,
        status=check.CRITICAL,
        tags=common.EXPECTED_TAGS,
        count=1,
    )


def test_21_parser(mocked_check21):
    input_json = common.read_fixture('riakcs21_in.json')
    output_python = common.read_fixture('riakcs21_out.python')
    assert mocked_check21.load_json(input_json) == literal_eval(output_python)


def test_21_metrics(mocked_check21, aggregator, instance21):
    with mock.patch("datadog_checks.riakcs.riakcs.S3Connection"):
        mocked_check21.check(instance21)
    for metric in common.EXPECTED_METRICS_21:
        aggregator.assert_metric(metric, tags=common.EXPECTED_TAGS)

    assert len(aggregator.metrics("riakcs.bucket_policy_get_in_one")) == 0
