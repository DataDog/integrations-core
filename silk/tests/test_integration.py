# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.silk import SilkCheck

from .common import BASE_TAGS, BLOCKSIZE_METRICS, METRICS, READ_WRITE_METRICS, SYSTEM_TAGS

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures("dd_environment")]


@pytest.mark.parametrize(
    'enable_rw, enable_bs, expected_metrics',
    [
        pytest.param(False, False, METRICS[0:], id="rw bs disabled"),
        pytest.param(True, True, METRICS[0:] + BLOCKSIZE_METRICS[0:] + READ_WRITE_METRICS[0:], id="rw bs enabled"),
        pytest.param(False, True, METRICS[0:] + BLOCKSIZE_METRICS[0:], id="bs enabled"),
        pytest.param(True, False, METRICS[0:] + READ_WRITE_METRICS[0:], id="rw enabled"),
    ],
)
def test_check(dd_run_check, aggregator, instance, enable_rw, enable_bs, expected_metrics):
    instance['enable_read_write_statistics'] = enable_rw
    instance['enable_blocksize_statistics'] = enable_bs

    check = SilkCheck('silk', {}, [instance])
    dd_run_check(check)
    for metric in expected_metrics:
        aggregator.assert_metric(metric)
        for tag in BASE_TAGS[0:] + SYSTEM_TAGS[0:]:
            # There are metric-specific tags so we just assert the common tags here
            aggregator.assert_metric_has_tag(metric, tag)


def test_error_msg_response(dd_run_check, aggregator, instance):
    error_response = {"error_msg": "Statistics data is unavailable while system is OFFLINE"}
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        g.return_value = error_response
        check = SilkCheck('silk', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check(
            'silk.can_connect', SilkCheck.WARNING, message="Received error message: " + error_response["error_msg"]
        )


def test_submit_system_state(instance, datadog_agent):
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:123'
    system_tags = check.submit_system_state()

    version_metadata = {
        'version.scheme': 'silk',  # silk does not use semver
        'version.major': '6',
        'version.minor': '0',
        'version.patch': '102',
        'version.release': '25',
        'version.raw': '6.0.102.25',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    assert all(expected_system_tag in system_tags for expected_system_tag in SYSTEM_TAGS)
