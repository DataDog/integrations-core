# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import logging
import pytest

from ast import literal_eval
from socket import error as SocketError

from datadog_checks.riakcs import RiakCs

from . import common

log = logging.getLogger(__file__)


def test_parser(mocked_check):
    input_json = common.read_fixture('riakcs_in.json')
    output_python = common.read_fixture('riakcs_out.python')
    assert mocked_check.load_json(input_json) == literal_eval(output_python)


def test_metrics(mocked_check, aggregator):
    mocked_check.check(common.CONFIG)
    expected = literal_eval(common.read_fixture('riakcs_metrics.python'))
    for m in expected:
        aggregator.assert_metric(m[0], m[2], m[3].get('tags', []))


def test_service_checks(check, aggregator):
    with pytest.raises(SocketError):
        check.check(common.CONFIG)

    scs = aggregator.service_checks(common.SERVICE_CHECK_NAME)
    assert len(scs) == 1

    aggregator.assert_service_check(common.SERVICE_CHECK_NAME,
                                    status=RiakCs.CRITICAL,
                                    tags=['aggregation_key:localhost:8080', 'optional:tag1'])


def test_21_parser(mocked_check21):
    input_json = common.read_fixture('riakcs21_in.json')
    output_python = common.read_fixture('riakcs21_out.python')
    assert mocked_check21.load_json(input_json) == literal_eval(output_python)


def test_21_metrics(mocked_check21, aggregator):
    mocked_check21.check(common.CONFIG_21)
    expected = literal_eval(common.read_fixture('riakcs21_metrics.python'))
    for m in expected:
        aggregator.assert_metric(m[0], m[2], m[3].get('tags', []))

    assert len(aggregator.metrics("riakcs.bucket_policy_get_in_one")) == 0
