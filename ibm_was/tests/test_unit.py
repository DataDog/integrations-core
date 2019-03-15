# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import os
import pytest
import requests

from datadog_checks.base import AgentCheck, ConfigurationError
from . import common

pytestmark = pytest.mark.unit


def mock_data(file):
    filepath = os.path.join(common.FIXTURE_DIR, file)
    with open(filepath, 'rb') as f:
        return f.read()


def test_metric_collection_per_category(aggregator, instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check.check(instance)

    for metric_name in common.METRICS_ALWAYS_PRESENT:
        aggregator.assert_metric(metric_name)
        aggregator.assert_metric_has_tag(metric_name, 'key1:value1')


def test_custom_query(aggregator, instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check.check(instance)

    aggregator.assert_metric_has_tag(
        'ibm_was.object_pool.objects_created_count',
        'implementations:ObjectPool_ibm.system.objectpool_com.ibm.ws.webcontainer.srt.SRTConnectionContextImpl'
    )


def test_custom_queries_missing_stat_in_payload(instance, check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        check.check(instance)

    assert "Error finding JDBC Connection Custom stats in XML output." in check.warnings


def test_custom_query_validation(check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        with pytest.raises(ConfigurationError) as e:
            check.check(common.MALFORMED_CUSTOM_QUERY_INSTANCE)
            assert "missing required field" in str(e)


def test_config_validation(check):
    with mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request', return_value=mock_data('server.xml')):
        with pytest.raises(ConfigurationError) as e:
            check.check(common.MISSING_REQ_FIELD_INSTANCE)
            assert "Please specify a servlet_url" in str(e)


def test_critical_service_check(instance, check, aggregator):
    instance['servlet_url'] = 'http://localhost:5678/wasPerfTool/servlet/perfservlet'
    tags = ['url:{}'.format(instance['servlet_url']), 'key1:value1']

    with pytest.raises(requests.ConnectionError):
        check.check(instance)

    aggregator.assert_service_check('ibm_was.can_connect', status=AgentCheck.CRITICAL, tags=tags, count=1)
