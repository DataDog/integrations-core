# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError

from datadog_checks.hdfs_namenode import HDFSNameNode

from .common import HDFS_NAMENODE_CONFIG, INSTANCE_INTEGRATION

pytestmark = pytest.mark.unit


def test_check_raises_without_jmx_uri(check):
    # Kills core/ReplaceComparisonOperator_Is_IsNot and core/AddNot mutants at hdfs_namenode.py:68.
    hdfs_namenode = check({})

    with pytest.raises(Exception, match="The JMX URL must be specified"):
        hdfs_namenode.check({})


def test_check_processes_all_three_bean_groups(aggregator, dd_run_check, mocked_request, datadog_agent):
    # Kills the three core/AddNot mutants at hdfs_namenode.py:81,84,87: each `if <beans>:` gate
    # must run for its bean group, or that group's metrics/metadata never get emitted.
    instance = HDFS_NAMENODE_CONFIG['instances'][0]
    hdfs_namenode = HDFSNameNode('hdfs_namenode', {}, [instance])
    hdfs_namenode.check_id = 'test:unit'

    dd_run_check(hdfs_namenode)

    aggregator.assert_metric('hdfs.namenode.capacity_total', count=1)
    aggregator.assert_metric('hdfs.namenode.missing_blocks', count=1)
    datadog_agent.assert_metadata_count(6)


def test_http_config_remapper():
    # Kills core/ReplaceTrueWithFalse and core/ReplaceFalseWithTrue mutants at hdfs_namenode.py:16.
    # Checked as a sub-dict rather than full equality since RequestsWrapper.__init__ mutates this
    # very dict in place with unrelated default keys as a side effect of check instantiation.
    assert HDFSNameNode.HTTP_CONFIG_REMAPPER['disable_ssl_validation'] == {
        'name': 'tls_verify',
        'default': False,
        'invert': True,
    }


def test_hdfs_namenode_metrics_raises_on_unequal_bean_name(check):
    # Kills core/ReplaceComparisonOperator_NotEq_Lt|Gt|IsNot mutants at hdfs_namenode.py:113: an
    # object whose __ne__ always returns True forces the tautological `!=` to raise, while `<`,
    # `>` blow up with TypeError and `is not` never fires.
    class AlwaysUnequal:
        def __eq__(self, other):
            return False

        def __ne__(self, other):
            return True

    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {'name': AlwaysUnequal()}

    with pytest.raises(Exception, match="Unexpected bean name"):
        hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])


def test_hdfs_namenode_metrics_requires_both_capacity_keys(aggregator, check):
    # Kills core/ReplaceAndWithOr mutant at hdfs_namenode.py:122: only one of
    # CapacityUsed/CapacityTotal being present must not produce capacity_in_use.
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {'name': 'foo', 'CapacityUsed': 100}

    hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])

    aggregator.assert_metric('hdfs.namenode.capacity_in_use', count=0)


def test_hdfs_namenode_metrics_capacity_total_default_is_zero(aggregator, check):
    # Kills the two core/NumberReplacer mutants at hdfs_namenode.py:123 (bean.get('CapacityTotal',
    # 0) -> default 1/-1): 'CapacityTotal' is reported present but never actually stored, so the
    # real value used comes entirely from the default argument.
    class BeanWithFakeCapacityTotal(dict):
        def __contains__(self, key):
            if key == 'CapacityTotal':
                return True
            return super().__contains__(key)

    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = BeanWithFakeCapacityTotal({'name': 'foo', 'CapacityUsed': 100})

    hdfs_namenode._hdfs_namenode_metrics([bean], {}, [])

    aggregator.assert_metric('hdfs.namenode.capacity_in_use', value=0, tags=[], count=1)


def test_hdfs_namenode_metrics_emits_from_metrics_mapping(aggregator, check):
    # Kills core/ZeroIterationForLoop at hdfs_namenode.py:116 (metrics.items() -> []) and the
    # core/ReplaceComparisonOperator_IsNot_Is / core/AddNot mutants at hdfs_namenode.py:119
    # (metric_value is not None): a mapped, present raw metric must produce exactly one gauge.
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    bean = {'name': 'foo', 'SomeRawMetric': 42}
    metrics = {'SomeRawMetric': ('hdfs.namenode.some_metric', HDFSNameNode.GAUGE)}

    hdfs_namenode._hdfs_namenode_metrics([bean], metrics, [])

    aggregator.assert_metric('hdfs.namenode.some_metric', value=42, count=1)


def test_rest_request_to_json_builds_query_string_only_when_present(check):
    # Kills core/AddNot at hdfs_namenode.py:148 (`if query_params:` -> `if not query_params:`) and
    # the core/ReplaceBinaryOperator_Add_* family at hdfs_namenode.py:150 ('?' + query): the built
    # URL must carry exactly the given query params, in order, joined with '&'.
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    captured_urls = []

    def fake_get(session, url, **kwargs):
        captured_urls.append(url)
        response = mock.Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}
        return response

    with mock.patch('requests.Session.get', fake_get):
        hdfs_namenode._rest_request_to_json('http://example.com/', None, {'qry': 'Foo', 'a': 'b'})

    assert captured_urls == ['http://example.com/?qry=Foo&a=b']


def test_collect_metadata_sets_version_when_present(check, datadog_agent):
    # Kills core/ReplaceComparisonOperator_IsNot_Is and core/AddNot mutants at hdfs_namenode.py:205
    # (version is not None): a present Version key must produce parsed version metadata.
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    hdfs_namenode.check_id = 'test:unit'

    hdfs_namenode._collect_metadata([{'Version': '3.1.3, rba631c436b806728f8ec2f54ab1e289526c90579'}])

    datadog_agent.assert_metadata(
        'test:unit',
        {'version.scheme': 'semver', 'version.major': '3', 'version.minor': '1', 'version.patch': '3'},
    )


def test_set_metric_rejects_lexically_smaller_type(aggregator, check):
    # Kills core/ReplaceComparisonOperator_Eq_LtE mutant at hdfs_namenode.py:135 (== -> <=): a
    # type sorting before 'gauge' must not be treated as the gauge type.
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    hdfs_namenode._set_metric('hdfs.namenode.test_metric', 'aauge', 1, tags=[])

    aggregator.assert_metric('hdfs.namenode.test_metric', count=0)


def test_set_metric_rejects_lexically_larger_type(aggregator, check):
    # Kills core/ReplaceComparisonOperator_Eq_GtE mutant at hdfs_namenode.py:135 (== -> >=): a
    # type sorting after 'gauge' must not be treated as the gauge type.
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    hdfs_namenode._set_metric('hdfs.namenode.test_metric', 'zauge', 1, tags=[])

    aggregator.assert_metric('hdfs.namenode.test_metric', count=0)


def test_set_metric_accepts_equal_but_distinct_gauge_string(aggregator, check):
    # Kills core/ReplaceComparisonOperator_Eq_Is mutant at hdfs_namenode.py:135 (== -> is): a
    # value-equal 'gauge' string built at runtime (distinct identity from the class constant)
    # must still be treated as the gauge type.
    hdfs_namenode = check(INSTANCE_INTEGRATION)
    metric_type = ''.join(['g', 'a', 'u', 'g', 'e'])

    hdfs_namenode._set_metric('hdfs.namenode.test_metric', metric_type, 1, tags=[])

    aggregator.assert_metric('hdfs.namenode.test_metric', value=1, count=1)


def test_rest_request_to_json_reports_critical_on_timeout(aggregator, check):
    # Kills core/ExceptionReplacer mutant at hdfs_namenode.py:159 (except Timeout -> except
    # CosmicRayTestingException).
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch('requests.Session.get', side_effect=Timeout('boom')):
        with pytest.raises(Timeout):
            hdfs_namenode._rest_request_to_json('http://example.com/', None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="Request timeout", count=1
    )


@pytest.mark.parametrize('raised_exception', [HTTPError, InvalidURL, ConnectionError])
def test_rest_request_to_json_reports_critical_on_request_errors(aggregator, check, raised_exception):
    # Kills the three core/ExceptionReplacer mutants at hdfs_namenode.py:165, one per exception
    # type swapped out of the (HTTPError, InvalidURL, ConnectionError) tuple.
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch('requests.Session.get', side_effect=raised_exception('boom')):
        with pytest.raises(raised_exception):
            hdfs_namenode._rest_request_to_json('http://example.com/', None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="Request failed", count=1
    )


def test_rest_request_to_json_reports_critical_on_json_decode_error(aggregator, check):
    # Kills core/ExceptionReplacer mutant at hdfs_namenode.py:171 (except JSONDecodeError ->
    # except CosmicRayTestingException): JSONDecodeError is also a ValueError, so without this
    # clause it would still get caught downstream with a different message.
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch('requests.Session.get', side_effect=JSONDecodeError('bad json', 'doc', 0)):
        with pytest.raises(JSONDecodeError):
            hdfs_namenode._rest_request_to_json('http://example.com/', None, {})

    aggregator.assert_service_check(
        HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="JSON Parse failed", count=1
    )


def test_rest_request_to_json_reports_critical_on_value_error(aggregator, check):
    # Kills core/ExceptionReplacer mutant at hdfs_namenode.py:180 (except ValueError -> except
    # CosmicRayTestingException).
    hdfs_namenode = check(INSTANCE_INTEGRATION)

    with mock.patch('requests.Session.get', side_effect=ValueError('boom')):
        with pytest.raises(ValueError):
            hdfs_namenode._rest_request_to_json('http://example.com/', None, {})

    aggregator.assert_service_check(HDFSNameNode.JMX_SERVICE_CHECK, HDFSNameNode.CRITICAL, message="boom", count=1)


def test_join_url_dir_is_classmethod():
    # Kills core/RemoveDecorator mutant at hdfs_namenode.py:187: without @classmethod, calling
    # _join_url_dir on the class (no instance) misaligns every positional argument by one.
    result = HDFSNameNode._join_url_dir('http://example.com/', 'jmx', 'path')

    assert result == 'http://example.com/jmx/path'
