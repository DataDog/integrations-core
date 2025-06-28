# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import mock
import pytest

from . import common


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_fail(aggregator, check, instance):
    instance["host"] = "bad_host"
    with pytest.raises(Exception):
        check.check(instance)


@pytest.mark.usefixtures('dd_environment')
@pytest.mark.integration
def test_check_ok(aggregator, check, instance):
    check.check(instance)

    expected_tags = ["name:ok_instance", "custom_tag"]
    aggregator.assert_service_check(common.SERVICE_CHECK, tags=expected_tags, status=check.OK)

    for metric in common.EXPECTED_METRICS:
        aggregator.assert_metric("squid.cachemgr." + metric, tags=expected_tags)
    aggregator.assert_all_metrics_covered()


@pytest.mark.parametrize(
    'raw_version, version_metadata, count',
    [
        (
            'squid/3.0.3',
            {
                'version.scheme': 'semver',
                'version.major': '3',
                'version.minor': '0',
                'version.patch': '3',
                'version.raw': '3.0.3',
            },
            5,
        ),
        (
            'squid/1.4.5',
            {
                'version.scheme': 'semver',
                'version.major': '1',
                'version.minor': '4',
                'version.patch': '5',
                'version.raw': '1.4.5',
            },
            5,
        ),
        # these versions aren't valid squid versions, so the version metadata should not be submitted
        (
            'squid/1.3',
            {
                'version.scheme': 'semver',
                'version.major': '1',
                'version.minor': '3',
                'version.raw': '1.3',
            },
            4,
        ),
        (
            'squid/1',
            {},
            0,
        ),
        (
            '1.4.5',
            {},
            0,
        ),
    ],
)
@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(check, instance, datadog_agent, raw_version, version_metadata, count):
    with mock.patch('datadog_checks.base.utils.http.requests.Session.get') as g:
        g.return_value.headers = {'Server': raw_version}

        check.check_id = 'test:123'
        check.check(instance)

        datadog_agent.assert_metadata('test:123', version_metadata)
        datadog_agent.assert_metadata_count(count)
