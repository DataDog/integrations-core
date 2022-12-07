# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest

from datadog_checks.apache import Apache
from datadog_checks.dev.utils import get_metadata_metrics

from .common import (
    APACHE_GAUGES,
    APACHE_RATES,
    APACHE_VERSION,
    AUTO_CONFIG,
    BAD_CONFIG,
    HOST,
    NO_METRIC_CONFIG,
    PORT,
    STATUS_CONFIG,
)


@pytest.mark.usefixtures("dd_environment")
def test_connection_failure(aggregator, check):
    check = check(BAD_CONFIG)
    with pytest.raises(Exception):
        check.check(BAD_CONFIG)

    sc_tags = ['apache_host:localhost', 'port:1234']
    aggregator.assert_service_check('apache.can_connect', Apache.CRITICAL, tags=sc_tags)
    assert len(aggregator._metrics) == 0


@pytest.mark.usefixtures("dd_environment")
def test_no_metrics_failure(aggregator, check):
    check = check(NO_METRIC_CONFIG)
    with pytest.raises(Exception) as excinfo:
        check.check(NO_METRIC_CONFIG)

    assert str(excinfo.value) == (
        "No metrics were fetched for this instance. Make sure that http://localhost:18180 " "is the proper url."
    )

    sc_tags = ['apache_host:localhost', 'port:18180']
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)
    assert len(aggregator._metrics) == 0


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    """
    This test will try and fail with `/server-status` url first then fallback on `/server-status??auto`
    """
    check = check(STATUS_CONFIG)
    check._submit_metadata = mock.MagicMock()
    check.check(STATUS_CONFIG)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['apache_host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()

    check._submit_metadata.assert_called_once()


@pytest.mark.usefixtures("dd_environment")
def test_check_auto(aggregator, check):
    check = check(AUTO_CONFIG)
    check.check(AUTO_CONFIG)

    tags = AUTO_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['apache_host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(STATUS_CONFIG, rate=True)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags)

    sc_tags = ['apache_host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.usefixtures("dd_environment")
def test_metadata_in_content(check, datadog_agent):
    check = check(AUTO_CONFIG)
    check.check_id = 'test:123'
    major, minor, patch = APACHE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': APACHE_VERSION,
    }

    check.check(AUTO_CONFIG)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.usefixtures("dd_environment")
def test_metadata_in_header(check, datadog_agent, mock_hide_server_version):
    """For older Apache versions, the version is not in the output. This test asserts that
    the check can fallback to the headers."""
    check = check(AUTO_CONFIG)
    check.check_id = 'test:123'
    major, minor, patch = APACHE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': APACHE_VERSION,
    }

    check.check(AUTO_CONFIG)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


def test_invalid_version(check):
    check = check({})
    check.log = mock.MagicMock()

    check._submit_metadata("invalid_version")

    check.log.info.assert_called_once_with("Cannot parse the complete Apache version from %s.", "invalid_version")


@pytest.mark.parametrize(
    'version, expected_parts',
    [
        pytest.param(
            'Apache/2.4.2 (Unix) PHP/4.2.2 MyMod/1.2',
            {'major': '2', 'minor': '4', 'patch': '2'},
            id='unix_full_version',
        ),
        pytest.param(
            'Apache/2.4.6 (Red Hat Enterprise Linux) OpenSSL/1.0.2k-fips',
            {'major': '2', 'minor': '4', 'patch': '6'},
            id='redhat_version',
        ),
        pytest.param('Apache/2.14.27', {'major': '2', 'minor': '14', 'patch': '27'}, id='min_version'),
        pytest.param('Apache/2.4', {'major': '2', 'minor': '4'}, id='only_minor'),
        pytest.param('Apache/2', {'major': '2'}, id='only_major'),
        pytest.param('Apache', {}, id='only_apache'),
    ],
)
def test_full_version_regex(check, version, expected_parts, datadog_agent):
    """The default server token is Full. Full results in server info that can include
    multiple non-Apache version specific information.
    """
    check = check({})
    check.check_id = 'test:123'

    check._submit_metadata(version)

    version_metadata = {'version.{}'.format(k): v for k, v in list(expected_parts.items())}
    if expected_parts:
        version_metadata['version.scheme'] = 'semver'

    datadog_agent.assert_metadata('test:123', version_metadata)


@pytest.mark.usefixtures("dd_environment")
def test_scoreboard(aggregator, check):
    check = check(AUTO_CONFIG)
    check.check(AUTO_CONFIG)

    tags = AUTO_CONFIG['tags']
    aggregator.assert_metric('apache.performance.max_workers', tags=tags, value=400)
    # 'MaxClients 400' is set in httpd.conf


@pytest.mark.parametrize(
    'scoreboard, expected_metrics',
    [
        pytest.param(
            '..._W',
            {
                'apache.performance.max_workers': 5,
                'apache.scoreboard.open_slot': 3,
                'apache.scoreboard.waiting_for_connection': 1,
                'apache.scoreboard.sending_reply': 1,
            },
            id='simple_scoreboard',
        ),
        pytest.param(
            '_SRWKDCLGI. ',
            {
                'apache.performance.max_workers': 12,
                'apache.scoreboard.waiting_for_connection': 1,
                'apache.scoreboard.starting_up': 1,
                'apache.scoreboard.reading_request': 1,
                'apache.scoreboard.sending_reply': 1,
                'apache.scoreboard.keepalive': 1,
                'apache.scoreboard.dns_lookup': 1,
                'apache.scoreboard.closing_connection': 1,
                'apache.scoreboard.logging': 1,
                'apache.scoreboard.gracefully_finishing': 1,
                'apache.scoreboard.idle_cleanup': 1,
                'apache.scoreboard.open_slot': 1,
                'apache.scoreboard.disabled': 1,
            },
            id='every_option',
        ),
        pytest.param(
            '',
            {
                'apache.performance.max_workers': 0,
                'apache.scoreboard.waiting_for_connection': 0,
                'apache.scoreboard.starting_up': 0,
                'apache.scoreboard.reading_request': 0,
                'apache.scoreboard.sending_reply': 0,
                'apache.scoreboard.keepalive': 0,
                'apache.scoreboard.dns_lookup': 0,
                'apache.scoreboard.closing_connection': 0,
                'apache.scoreboard.logging': 0,
                'apache.scoreboard.gracefully_finishing': 0,
                'apache.scoreboard.idle_cleanup': 0,
                'apache.scoreboard.open_slot': 0,
                'apache.scoreboard.disabled': 0,
            },
            id='empty_scoreboard',
        ),
        pytest.param(
            'WWWWWWWWWW__WWWWWWWWWW_WW_WWWWWWW.WWWWW_WW_W_.WW.W........G'
            '.....................................................................',
            {
                'apache.performance.max_workers': 128,
                'apache.scoreboard.waiting_for_connection': 7,
                'apache.scoreboard.starting_up': 0,
                'apache.scoreboard.reading_request': 0,
                'apache.scoreboard.sending_reply': 40,
                'apache.scoreboard.keepalive': 0,
                'apache.scoreboard.dns_lookup': 0,
                'apache.scoreboard.closing_connection': 0,
                'apache.scoreboard.logging': 0,
                'apache.scoreboard.gracefully_finishing': 1,
                'apache.scoreboard.idle_cleanup': 0,
                'apache.scoreboard.open_slot': 80,
                'apache.scoreboard.disabled': 0,
            },
            id='real_scoreboard',
        ),
    ],
)
def test_scoreboard_values(aggregator, check, scoreboard, expected_metrics, datadog_agent):
    """The default server token is Full. Full results in server info that can include
    multiple non-Apache version specific information.
    """
    check = check({})
    tags = []

    check._submit_scoreboard(scoreboard, tags)

    for metric, expected_value in expected_metrics.items():
        aggregator.assert_metric(metric, tags=tags, value=expected_value)

    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_no_duplicate_metrics()
