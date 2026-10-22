# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock
import pytest
import requests

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


@pytest.mark.parametrize(
    'exception',
    [
        pytest.param(requests.ReadTimeout, id='read timeout'),
        pytest.param(requests.ConnectTimeout, id='connect timeout'),
        pytest.param(requests.TooManyRedirects, id='too many redirects'),
    ],
)
def test_request_failure_reports_critical(instance, check, aggregator, exception):
    # Any failure to retrieve the response has to report can_connect. Narrower except clauses let
    # some of these escape, and the run then submits no service check at all, so a monitor sees a
    # gap instead of a CRITICAL exactly when the servlet is unhealthy.
    tags = ['url:{}'.format(instance['servlet_url']), 'key1:value1']

    with mock.patch('datadog_checks.base.utils.http.requests.Session.get', side_effect=exception):
        check = check(instance)
        with pytest.raises(exception):
            check.check(instance)

    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.CRITICAL, tags=tags, count=1)
    aggregator.assert_metric('ibm_was.can_connect', value=0, tags=tags, count=1)


def test_malformed_xml_reports_critical(instance, check, aggregator, caplog):
    # lxml raises XMLSyntaxError, which is a sibling of ElementTree's ParseError rather than a
    # subclass, so a narrower clause leaves malformed responses unhandled and silent. The request
    # itself has to succeed here, so that a run which fetches a 2xx body it cannot parse reports
    # CRITICAL alone rather than contradicting itself with an OK from the successful fetch.
    response = mock.MagicMock(content=b'<Nodes><Node')
    response.raise_for_status.return_value = None

    with mock.patch('datadog_checks.base.utils.http.requests.Session.get', return_value=response):
        check = check(instance)
        check.check(instance)

    tags = ['url:{}'.format(instance['servlet_url']), 'key1:value1']
    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.CRITICAL, tags=tags, count=1)
    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.OK, count=0)
    aggregator.assert_metric('ibm_was.can_connect', value=0, tags=tags, count=1)
    assert 'Unable to parse the XML response' in caplog.text


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
