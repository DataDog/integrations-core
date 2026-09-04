# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from xml.etree.ElementTree import ParseError

import mock
import pytest
import requests
from lxml import etree

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.ibm_was import IbmWasCheck

from . import common

pytestmark = pytest.mark.unit


def mock_data(file):
    filepath = os.path.join(common.FIXTURE_DIR, file)
    with open(filepath, 'rb') as f:
        return f.read()


def test_metric_collection_per_category(aggregator, instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check = check(instance)
        check.check(instance)

    metrics_in_fixture = ['ibm_was.thread_pools.percent_used']
    for metric_name in common.METRICS_ALWAYS_PRESENT + metrics_in_fixture:
        aggregator.assert_metric(metric_name)
        aggregator.assert_metric_has_tag(metric_name, 'key1:value1')


def test_custom_query(aggregator, instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check = check(instance)
        check.check(instance)

    aggregator.assert_metric_has_tag(
        'ibm_was.object_pool.objects_created_count',
        'implementations:ObjectPool_ibm.system.objectpool_com.ibm.ws.webcontainer.srt.SRTConnectionContextImpl',
    )


def test_custom_queries_missing_stat_in_payload(instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check = check(instance)
        check.log = mock.MagicMock()
        check.check(instance)

        check.log.debug.assert_any_call(
            'Error finding %s stats in XML output for server name `%s`.',
            'JVM Runtime Custom',
            'server2',
        )


def test_custom_query_validation(check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        with pytest.raises(ConfigurationError, match='missing required field'):
            IbmWasCheck('ibm_was', {}, [common.MALFORMED_CUSTOM_QUERY_INSTANCE])


def test_custom_query_unit(aggregator, instance, check):
    instance['custom_queries'] = [{"stat": "xdProcessModule", "metric_prefix": "xdpm"}]
    instance['custom_queries_units_gauge'] = ['unit.kbyte']
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check = check(instance)
        check.check(instance)

    aggregator.assert_metric('ibm_was.xdpm.resident_memory', metric_type=aggregator.GAUGE)


def test_custom_query_unit_casing(aggregator, instance, check):
    instance['custom_queries'] = [{"stat": "xdProcessModule", "metric_prefix": "xdpm"}]
    instance['custom_queries_units_gauge'] = ['unit.KByte']
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check = check(instance)
        check.check(instance)

    aggregator.assert_metric('ibm_was.xdpm.total_memory', metric_type=aggregator.GAUGE)


def test_critical_service_check(instance, check, aggregator):
    instance['servlet_url'] = 'http://localhost:5678/wasPerfTool/servlet/perfservlet'
    tags = ['url:{}'.format(instance['servlet_url']), 'key1:value1']

    with pytest.raises(requests.ConnectionError):
        check = check(instance)
        check.check(instance)

    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.CRITICAL, tags=tags, count=1)


def test_right_server_tag(instance, check, aggregator):
    del instance['custom_queries']
    with mock.patch(
        'datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('perfservlet-multiple-nodes.xml')
    ):
        check = check(instance)
        check.check(instance)

    node = 'node:cmhqlvij2a04'
    for metric_name, metrics in aggregator._metrics.items():
        for metric in metrics:
            if 'server:IJ2Server02' in metric.tags:
                assert node in metric.tags, "Expected '{}' tag in '{}' tags, found {}".format(
                    node, metric_name, metric.tags
                )


def test_right_values(instance, check, aggregator):
    del instance['custom_queries']

    with mock.patch(
        'datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('perfservlet-multiple-nodes.xml')
    ):
        check = check(instance)
        check.check(instance)

    aggregator.assert_metric(
        'ibm_was.jdbc.pool_size',
        tags=['server:IJ2Server05', 'key1:value1', 'node:cmhqlvij2a02', 'provider:Oracle JDBC Driver'],
        value=3,
    )
    aggregator.assert_metric(
        'ibm_was.jdbc.pool_size',
        tags=['server:IJ2Server02', 'key1:value1', 'node:cmhqlvij2a04', 'provider:Oracle JDBC Driver'],
        value=4,
    )


def test_validate_config_requires_servlet_url(instance):
    # Kills core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at ibm_was.py:40 (not X -> X / not not X).
    missing_url_instance = dict(instance)
    del missing_url_instance['servlet_url']
    with pytest.raises(ConfigurationError, match='Please specify a servlet_url'):
        IbmWasCheck('ibm_was', {}, [missing_url_instance])._validate_config()

    IbmWasCheck('ibm_was', {}, [instance])._validate_config()


def test_check_reports_critical_on_parse_error(instance, check, aggregator):
    # Kills core/ExceptionReplacer mutant at ibm_was.py:48 (ParseError -> CosmicRayTestingException): the
    # except clause must catch the real parse error and report a CRITICAL service check instead of raising.
    with (
        mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=b'data'),
        mock.patch('datadog_checks.ibm_was.ibm_was.etree.fromstring', side_effect=ParseError('bad xml')),
    ):
        check = check(instance)
        check.log = mock.MagicMock()
        check.check(instance)

    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.CRITICAL)


def test_get_node_from_name_returns_first_match(instance, check):
    # Kills core/NumberReplacer mutant at ibm_was.py:75 (data[0] -> data[-1]) when multiple Stat nodes match.
    xml_data = etree.fromstring(
        '<Node><Stat name="JVM Runtime" id="first"/><Stat name="JVM Runtime" id="second"/></Node>'
    )
    check = check(instance)
    result = check.get_node_from_name(xml_data, 'JVM Runtime')
    assert result.get('id') == 'first'


def test_process_stats_stops_recursion_at_tag_list_bound(instance, check):
    # Kills core/ReplaceComparisonOperator_Gt_NotEq and Gt_IsNot mutants at ibm_was.py:94
    # (len(tag_list) > recursion_level -> != / is not): past the tag_list bound, no tag should be appended
    # and tag_list must not be indexed out of range.
    stat_child = etree.fromstring('<Stat name="inner"/>')
    check = check(instance)
    check.process_stats([stat_child], 'jdbc', ['base'], recursion_level=3)


def test_process_stats_recursion_level_increments_by_one(instance, check, aggregator):
    # Kills the core/ReplaceBinaryOperator_Add_* and core/NumberReplacer family at ibm_was.py:98
    # (recursion_level + 1 -> -, *, //, %, **, >>, <<, |, &, ^, +2, +0): a 3-level nested Stat structure only
    # produces the correct provider/dataSource tag pair if recursion_level increases by exactly one per level.
    leaf = etree.fromstring('<Stat name="deep"><CountStatistic name="metric1" count="7"/></Stat>')
    data_source = etree.fromstring('<Stat name="d1"/>')
    data_source.append(leaf)
    provider = etree.fromstring('<Stat name="p1"/>')
    provider.append(data_source)

    check = check(instance)
    check.process_stats([provider], 'jdbc', ['base'], recursion_level=0)

    aggregator.assert_metric('ibm_was.jdbc.metric1', tags=['base', 'provider:p1', 'dataSource:d1'], count=1)


def test_submit_metrics_requires_gauge_unit_and_tracked_prefix(instance, check, aggregator):
    # Kills core/ReplaceAndWithOr mutant at ibm_was.py:109 (unit-in-gauge and prefix-in-custom-stats -> or):
    # a gauge-unit metric in an untracked prefix must not be coerced from a rate into a gauge.
    check = check(instance)
    check.custom_queries_units_gauge = {'unit.kbyte'}
    child = etree.fromstring('<DoubleStatistic name="metric_a" double="1.5" unit="unit.kbyte"/>')
    check.submit_metrics(child, 'jvm', ['base'])
    aggregator.assert_metric('ibm_was.jvm.metric_a', metric_type=aggregator.RATE)


def test_submit_metrics_requires_count_statistic_tag(instance, check, aggregator):
    # Kills core/ReplaceAndWithOr and core/ReplaceComparisonOperator_Eq_{GtE,IsNot} mutants at ibm_was.py:110
    # (tag == 'CountStatistic' -> or / >= / is not): a DoubleStatistic in a tracked, gauge-unit prefix must
    # stay a rate, not get coerced to a gauge just because the other two conditions hold.
    check = check(instance)
    check.custom_queries_units_gauge = {'unit.kbyte'}
    child = etree.fromstring('<DoubleStatistic name="metric_b" double="1.5" unit="unit.kbyte"/>')
    check.submit_metrics(child, 'jdbc', ['base'])
    aggregator.assert_metric('ibm_was.jdbc.metric_b', metric_type=aggregator.RATE)


def test_submit_metrics_jvm_prefix_adds_gauge_metric(instance, check, aggregator):
    # Kills core/ReplaceComparisonOperator_Eq_{NotEq,Lt,LtE,Gt,GtE} and core/AddNot mutants at ibm_was.py:116
    # (prefix == "jvm"): only the jvm prefix should emit the extra "_gauge" metric.
    check = check(instance)
    child = etree.fromstring('<RangeStatistic name="heap" value="10"/>')

    check.submit_metrics(child, 'jvm', ['base'])
    aggregator.assert_metric('ibm_was.jvm.heap_gauge', value=10, tags=['base'])

    aggregator.reset()
    check.submit_metrics(child, 'jdbc', ['base'])
    aggregator.assert_metric('ibm_was.jdbc.heap_gauge', count=0)

    aggregator.reset()
    check.submit_metrics(child, 'thread_pools', ['base'])
    aggregator.assert_metric('ibm_was.thread_pools.heap_gauge', count=0)


def test_submit_service_checks_value_encoding(instance, check, aggregator):
    # Kills core/ReplaceComparisonOperator_Eq_{NotEq,Lt,LtE,Gt,GtE,IsNot}, core/AddNot, and core/NumberReplacer
    # mutants at ibm_was.py:134: the gauge value must be exactly 1 for OK and exactly 0 for any other status.
    check = check(instance)

    check.submit_service_checks(AgentCheck.OK)
    aggregator.assert_metric('ibm_was.can_connect', value=1, tags=list(check.service_check_tags))

    aggregator.reset()
    check.submit_service_checks(AgentCheck.CRITICAL)
    aggregator.assert_metric('ibm_was.can_connect', value=0, tags=list(check.service_check_tags))

    aggregator.reset()
    check.submit_service_checks(-1)
    aggregator.assert_metric('ibm_was.can_connect', value=0, tags=list(check.service_check_tags))
