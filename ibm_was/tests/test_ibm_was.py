# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import os

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.ibm_was import IbmWasCheck

from . import common


def mock_data(file):
    filepath = os.path.join(common.FIXTURE_DIR, file)
    with open(filepath, "rb") as f:
        data = f.read()
    return data


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_metric_collection_per_category(mock_server, aggregator, instance):
    check = IbmWasCheck('ibm_was', {}, {})
    check.check(instance)
    aggregator.assert_metric('ibmwas.jdbc.CreateCount')
    aggregator.assert_metric('ibmwas.jvm.FreeMemory')
    aggregator.assert_metric('ibmwas.servlet_session.LifeTime')
    aggregator.assert_metric('ibmwas.thread_pools.CreateCount')


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_custom_queries_missing_stat_in_payload(mock_server, aggregator, instance):
    check = IbmWasCheck('ibm_was', {}, {})
    check.check(instance)
    assert b"Error finding JDBC Connection Custom stats in XML output." in check.warnings


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_custom_query_validation(mock_server, aggregator):
    check = IbmWasCheck('ibm_was', {}, {})
    with pytest.raises(ConfigurationError) as e:
        check.check(common.MALFORMED_CUSTOM_QUERY_INSTANCE)
    assert "missing required field" in str(e.value)


@mock.patch('datadog_checks.ibm_was.IbmWasCheck.make_request',
            return_value=mock_data("server.xml"))
def test_config_validation(mock_server, aggregator):
    check = IbmWasCheck('ibm_was', {}, {})
    with pytest.raises(ConfigurationError) as e:
        check.check(common.MISSING_REQ_FIELD_INSTANCE)
    assert "Please specify a servlet_url" in str(e.value)
