# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os

import mock
import pytest

from datadog_checks.dev.fs import read_file
from datadog_checks.silk import SilkCheck
from datadog_checks.silk.metrics import Metric

from .common import BLOCKSIZE_METRICS, HERE, HOST, METRICS, READ_WRITE_METRICS


def mock_get_data(data):
    if data == 'test':
        file_contents = read_file(os.path.join(HERE, 'fixtures', 'stats', 'system__bs_breakdown=True'))
        response = json.loads(file_contents)

        return response


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    dd_run_check(check)
    base_tags = ['silk_host:localhost:80', 'system_id:5501', 'system_name:K2-5501', 'test:silk']

    for metric in METRICS:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)

    # blocksize and read/write metrics don't appear in test env since caddy can't mock HTTP query strings
    for metric in BLOCKSIZE_METRICS + READ_WRITE_METRICS:
        aggregator.assert_metric(metric, at_least=0)

    aggregator.assert_service_check('silk.can_connect', SilkCheck.OK)
    aggregator.assert_service_check('silk.system.state', SilkCheck.OK)
    aggregator.assert_service_check('silk.server.state', SilkCheck.OK, count=2)


def test_error_msg_response(dd_run_check, aggregator, instance):
    error_response = {"error_msg": "Statistics data is unavailable while system is OFFLINE"}
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        g.return_value = error_response
        check = SilkCheck('silk', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('silk.can_connect', SilkCheck.WARNING)


def test_incorrect_config(dd_run_check, aggregator):
    invalid_instance = {'host_addres': 'localhost'}  # misspelled required parameter
    check = SilkCheck('silk', {}, [invalid_instance])

    with pytest.raises(Exception):
        dd_run_check(check)


def test_unreachable_endpoint(dd_run_check, aggregator):
    invalid_instance = {
        'host_address': 'http://{}:81'.format(HOST),
    }
    check = SilkCheck('silk', {}, [invalid_instance])

    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_service_check('silk.can_connect', SilkCheck.CRITICAL)
