# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

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

@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(check, instance, datadog_agent):
    check.check_id = 'test:123'

    check.check(instance)

    version = common.SQUID_SERVER_VERSION

    major, minor, patch = version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
