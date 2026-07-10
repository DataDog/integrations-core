# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.dev.docker import assert_all_discovery_candidates_stable
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.twemproxy import Twemproxy

from . import common, metrics

SC_TAGS = ['host:{}'.format(common.HOST), 'port:{}'.format(common.PORT), 'optional:tag1']


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_integration(check, dd_environment, setup_request, aggregator):
    check.check(common.INSTANCE)

    for stat in metrics.POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)
    for stat in metrics.SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.SERVER_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.POOL_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)

    for stat in metrics.GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat))

    aggregator.assert_all_metrics_covered()

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK, tags=SC_TAGS, count=1)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_metadata_integration(aggregator, datadog_agent, check):
    check.check_id = 'test:123'
    check.check(common.INSTANCE)

    major, minor, patch = common.TWEMPROXY_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': common.TWEMPROXY_VERSION,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.e2e
def test_e2e(dd_agent_check, setup_request, instance):
    aggregator = dd_agent_check(instance, rate=True)

    for stat in metrics.POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=4)

    for stat in metrics.SERVER_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.POOL_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)

    for stat in metrics.GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat))

    aggregator.assert_all_metrics_covered()

    # Test service check
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK, tags=SC_TAGS, count=2)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_discovery(dd_agent_check_discovery, setup_request):
    aggregator = dd_agent_check_discovery(rate=True)

    for stat in metrics.POOL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.SERVER_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=4)

    for stat in metrics.SERVER_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=2)
    for stat in metrics.POOL_STATS_2:
        aggregator.assert_metric("twemproxy.{}".format(stat), count=1)

    for stat in metrics.GLOBAL_STATS:
        aggregator.assert_metric("twemproxy.{}".format(stat))

    aggregator.assert_all_metrics_covered()

    # Discovery resolves host/port from the container itself and has no way to set the
    # `optional:tag1` tag that comes from the static instance config, so tags aren't
    # asserted exactly here as they are in test_e2e above.
    aggregator.assert_service_check('twemproxy.can_connect', status=Twemproxy.OK, count=2)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.e2e
def test_e2e_discovery_all_candidates(dd_agent_check):
    assert_all_discovery_candidates_stable(dd_agent_check, Twemproxy)
