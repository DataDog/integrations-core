# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError

from datadog_checks.hdfs_datanode import HDFSDataNode

from .common import (
    CUSTOM_TAGS,
    HDFS_DATANODE_CONFIG,
    HDFS_DATANODE_METRIC_TAGS,
    HDFS_DATANODE_METRICS_VALUES,
    HDFS_RAW_VERSION,
    INSTANCE_INTEGRATION,
)

pytestmark = pytest.mark.unit


def _make_check():
    return HDFSDataNode('hdfs_datanode', {}, [dict(INSTANCE_INTEGRATION)])


def test_disable_ssl_validation_absent_defaults_tls_verify_to_true():
    # Kills the core/ReplaceTrueWithFalse and ReplaceFalseWithTrue mutants at hdfs_datanode.py:13
    # (HTTP_CONFIG_REMAPPER invert True->False and default False->True).
    check = _make_check()
    assert check.http.options['verify'] is True


def test_disable_ssl_validation_true_inverts_tls_verify_to_false():
    # Kills the core/ReplaceTrueWithFalse mutant at hdfs_datanode.py:13 (invert True->False).
    instance = dict(INSTANCE_INTEGRATION, disable_ssl_validation=True)
    check = HDFSDataNode('hdfs_datanode', {}, [instance])
    assert check.http.options['verify'] is False


def test_set_metric_type_alphabetically_below_gauge_is_not_submitted(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE mutant at hdfs_datanode.py:99
    # ('count' <= 'gauge' is True, but 'count' == 'gauge' is False).
    check = _make_check()
    check._set_metric('hdfs.datanode.test', 'count', 5, tags=[])
    aggregator.assert_metric('hdfs.datanode.test', count=0)


def test_set_metric_type_alphabetically_above_gauge_is_not_submitted(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at hdfs_datanode.py:99
    # ('histogram' >= 'gauge' is True, but 'histogram' == 'gauge' is False).
    check = _make_check()
    check._set_metric('hdfs.datanode.test', 'histogram', 5, tags=[])
    aggregator.assert_metric('hdfs.datanode.test', count=0)


def test_set_metric_type_equal_but_not_identical_to_gauge_is_submitted(aggregator):
    # Kills the core/ReplaceComparisonOperator_Eq_Is mutant at hdfs_datanode.py:99: a value that is
    # == self.GAUGE but not the same object (`is`) must still be treated as a gauge metric type.
    check = _make_check()
    metric_type = ''.join(['g', 'a', 'u', 'g', 'e'])
    check._set_metric('hdfs.datanode.test', metric_type, 5, tags=[])
    aggregator.assert_metric('hdfs.datanode.test', value=5, count=1)


def test_rest_request_joins_object_path_into_url():
    # Kills the core/AddNot mutant at hdfs_datanode.py:108 (`if object_path` -> `if not object_path`).
    check = _make_check()
    captured = {}

    def fake_get(*args, **kwargs):
        captured['url'] = args[1]
        return mock.Mock(json=lambda: {'beans': []}, raise_for_status=lambda: None)

    with mock.patch('requests.Session.get', new=fake_get):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])

    assert 'jmx' in captured['url']


def test_rest_request_appends_query_params_into_url():
    # Kills the core/AddNot mutant at hdfs_datanode.py:112 (`if query_params` -> `if not query_params`).
    check = _make_check()
    captured = {}

    def fake_get(*args, **kwargs):
        captured['url'] = args[1]
        return mock.Mock(json=lambda: {'beans': []}, raise_for_status=lambda: None)

    with mock.patch('requests.Session.get', new=fake_get):
        check._rest_request_to_json('http://host:9870', '', {'qry': 'FooBean'}, tags=[])

    assert 'qry=FooBean' in captured['url']


def test_rest_request_timeout_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:123 (Timeout -> CosmicRayTestingException).
    check = _make_check()
    with mock.patch('requests.Session.get', side_effect=Timeout('timed out')), pytest.raises(Timeout):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_rest_request_http_error_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:129 (HTTPError -> CosmicRayTestingException).
    check = _make_check()
    with mock.patch('requests.Session.get', side_effect=HTTPError('bad status')), pytest.raises(HTTPError):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_rest_request_invalid_url_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:129 (InvalidURL -> CosmicRayTestingException).
    check = _make_check()
    with mock.patch('requests.Session.get', side_effect=InvalidURL('bad url')), pytest.raises(InvalidURL):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_rest_request_connection_error_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:129 (ConnectionError -> CosmicRayTestingException).
    check = _make_check()
    with mock.patch('requests.Session.get', side_effect=ConnectionError('no route')), pytest.raises(ConnectionError):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_rest_request_json_decode_error_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:135 (JSONDecodeError -> CosmicRayTestingException).
    check = _make_check()
    error = JSONDecodeError('bad json', 'doc', 0)
    with mock.patch('requests.Session.get', side_effect=error), pytest.raises(JSONDecodeError):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_rest_request_value_error_reports_critical_and_reraises(aggregator):
    # Kills the core/ExceptionReplacer mutant at hdfs_datanode.py:144 (ValueError -> CosmicRayTestingException).
    check = _make_check()
    with mock.patch('requests.Session.get', side_effect=ValueError('bad value')), pytest.raises(ValueError):
        check._rest_request_to_json('http://host:9870', 'jmx', {}, tags=[])
    aggregator.assert_service_check(HDFSDataNode.JMX_SERVICE_CHECK, status=HDFSDataNode.CRITICAL, count=1)


def test_check_raises_when_jmx_uri_missing():
    # Kills the core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at hdfs_datanode.py:46
    # (`if jmx_address is None` inverted), which would skip the required-config error entirely.
    check = HDFSDataNode('hdfs_datanode', {}, [{}])
    with pytest.raises(Exception, match='The JMX URL must be specified'):
        check.check({})


def test_check_emits_metrics_from_jmx_response(aggregator, mocked_request):
    # Kills the core/AddNot mutant at hdfs_datanode.py:63 (`if hdfs_datanode_beans`) and the
    # core/ZeroIterationForLoop mutant at hdfs_datanode.py:90 (`for metric, ... in self.HDFS_METRICS.items()`
    # -> `in []`), and the core/ReplaceComparisonOperator_IsNot_Is / AddNot mutants at hdfs_datanode.py:92
    # (`if metric_value is not None`) — any of these would leave the metrics below unsubmitted.
    instance = HDFS_DATANODE_CONFIG['instances'][0]
    check = HDFSDataNode('hdfs_datanode', {}, [instance])
    check.check(instance)

    for metric, value in HDFS_DATANODE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=HDFS_DATANODE_METRIC_TAGS + CUSTOM_TAGS, count=1)


def test_check_collects_version_metadata_when_present(aggregator, mocked_metadata_request, datadog_agent):
    # Kills the core/AddNot mutant at hdfs_datanode.py:56 (`if datanode_info`) and the
    # core/ReplaceComparisonOperator_IsNot_Is / AddNot mutants at hdfs_datanode.py:169
    # (`if version is not None`) — any of these would leave version metadata uncollected.
    instance = HDFS_DATANODE_CONFIG['instances'][0]
    check = HDFSDataNode('hdfs_datanode', {}, [instance])
    check.check_id = 'test:456'
    check.check(instance)

    major, minor, patch = HDFS_RAW_VERSION.split('.')
    datadog_agent.assert_metadata(
        'test:456',
        {
            'version.raw': mock.ANY,
            'version.scheme': 'semver',
            'version.major': major,
            'version.minor': minor,
            'version.patch': patch,
            'version.build': mock.ANY,
        },
    )


def test_join_url_dir_is_a_classmethod_that_joins_every_arg():
    # Kills the core/RemoveDecorator mutant at hdfs_datanode.py:151 (removing @classmethod breaks the
    # unbound class-level call below) and the core/ZeroIterationForLoop mutant at hdfs_datanode.py:157
    # (`for path in args` -> `for path in []`, which would leave the url unjoined).
    assert HDFSDataNode._join_url_dir('http://host:9870', 'jmx', 'sub') == 'http://host:9870/jmx/sub'
