# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import io
import logging
import re

import mock
import pytest
from six import PY2, PY3

from datadog_checks.zk import ZookeeperCheck

from . import common, conftest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def extract_nan_metrics(text):
    log_pattern = r'Metric value \"(\S+)\" is not supported for metric (\S+)'
    metrics = []
    for line in text.splitlines():
        m = re.search(log_pattern, line)
        if m:
            key = m.groups()[1]
            metrics.append(ZookeeperCheck.normalize_metric_label(key))
    return metrics


def test_check(aggregator, dd_environment, get_test_instance, caplog):
    """
    Collect ZooKeeper metrics.
    """
    caplog.set_level(logging.DEBUG)
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_test_instance])
    zk_check.check(get_test_instance)

    # adding to skip for now
    skipped_metrics = extract_nan_metrics(caplog.text)

    # Test metrics
    common.assert_stat_metrics(aggregator)
    common.assert_latency_metrics(aggregator)
    common.assert_mntr_metrics_by_version(aggregator, skipped_metrics)

    common.assert_service_checks_ok(aggregator)

    expected_mode = get_test_instance['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1, tags=["mytag"])
    aggregator.assert_all_metrics_covered()


def test_wrong_expected_mode(aggregator, dd_environment, get_invalid_mode_instance):
    """
    Raise a 'critical' service check when ZooKeeper is not in the expected mode.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_invalid_mode_instance])
    zk_check.check(get_invalid_mode_instance)

    # Test service checks
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.CRITICAL)


def test_multiple_expected_modes(aggregator, dd_environment, get_multiple_expected_modes_config):
    """
    Accept multiple expected modes.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_multiple_expected_modes_config])
    zk_check.check(get_multiple_expected_modes_config)
    aggregator.assert_service_check("zookeeper.mode", status=zk_check.OK)


def test_error_state(aggregator, dd_environment, get_conn_failure_config):
    """
    Raise a 'critical' service check when ZooKeeper is in an error state.
    Report status as down.
    """
    zk_check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_conn_failure_config])
    with pytest.raises(Exception):
        zk_check.check(get_conn_failure_config)

    aggregator.assert_service_check("zookeeper.ruok", status=zk_check.CRITICAL)

    aggregator.assert_metric("zookeeper.instances", tags=["mode:down", "mytag"], count=1)

    expected_mode = get_conn_failure_config['expected_mode']
    mname = "zookeeper.instances.{}".format(expected_mode)
    aggregator.assert_metric(mname, value=1, count=1, tags=["mytag"])


def test_parse_replica_mntr(aggregator, mock_mntr_output, get_test_instance):
    unparsed_line = "zk_peer_state	following - broadcast\n"
    expected_message = "Unexpected 'mntr' output `%s`: %s"

    # Value Error is more verbose in PY 3
    error_message = 'too many values to unpack'
    if PY3:
        error_message = "too many values to unpack (expected 2)"

    check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_test_instance])
    check.log = mock.MagicMock()
    metrics, mode = check.parse_mntr(mock_mntr_output)

    assert mode == 'follower'
    assert len(metrics) == 499
    check.log.debug.assert_called_once_with(expected_message, unparsed_line, error_message)


def test_metadata(datadog_agent, get_test_instance):
    check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_test_instance])

    check.check_id = 'test:123'

    check.check(get_test_instance)

    raw_version = common.ZK_VERSION
    major, minor = raw_version.split('.')[:2]
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': mock.ANY,
        'version.raw': mock.ANY,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def test_metadata_regex(datadog_agent, get_test_instance):
    check = ZookeeperCheck(conftest.CHECK_NAME, {}, [get_test_instance])
    check.check_id = 'test:123'
    check.check(get_test_instance)
    if PY2:
        import StringIO

        buf = StringIO.StringIO(common.ZK_CLICKHOUSE_PAYLOAD)
    else:
        buf = io.StringIO(common.ZK_CLICKHOUSE_PAYLOAD)
    check.parse_stat(buf)
    expected_version = {
        'version.scheme': 'semver',
        'version.major': '22',
        'version.minor': '9',
        'version.patch': '1',
        'version.raw': mock.ANY,
    }

    datadog_agent.assert_metadata('test:123', expected_version)
