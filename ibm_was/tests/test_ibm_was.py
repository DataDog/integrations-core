# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import os

import pytest

from datadog_checks.base import ConfigurationError

from . import common


def mock_data(file):
    filepath = os.path.join(common.FIXTURE_DIR, file)
    with open(filepath, "rb") as f:
        data = f.read()
    return data


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_metric_collection_per_category(mock_server, aggregator, instance, check):
    check.check(instance)
    for metric_name in common.METRICS_ALWAYS_PRESENT:
        aggregator.assert_metric(metric_name)


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_custom_query(mock_server, aggregator, instance, check):
    check.check(instance)
    aggregator.assert_metric_has_tag(
        'ibmwas.object_pool.ObjectsCreatedCount',
        'implementations:ObjectPool_ibm.system.objectpool_com.ibm.ws.webcontainer.srt.SRTConnectionContextImpl'
    )


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_custom_queries_missing_stat_in_payload(mock_server, aggregator, instance, check):
    check.check(instance)
    assert b"Error finding JDBC Connection Custom stats in XML output." in check.warnings


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_custom_query_validation(mock_server, aggregator, check):
    with pytest.raises(ConfigurationError) as e:
        check.check(common.MALFORMED_CUSTOM_QUERY_INSTANCE)
    assert "missing required field" in str(e.value)


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_config_validation(mock_server, aggregator, check):
    with pytest.raises(ConfigurationError) as e:
        check.check(common.MISSING_REQ_FIELD_INSTANCE)
    assert "Please specify a servlet_url" in str(e.value)
