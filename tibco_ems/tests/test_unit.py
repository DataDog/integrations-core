# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401
from unittest.mock import MagicMock

import pytest

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tibco_ems import TibcoEMSCheck

from .common import METRIC_DATA, SHOW_MAP, mock_output


def test_check(dd_run_check, aggregator, instance):
    """
    Test the main check functionality
    """
    check = TibcoEMSCheck('tibco_ems', {}, [instance])
    check.run_tibco_command = MagicMock(return_value=mock_output('show_all'))
    dd_run_check(check)

    for metric in METRIC_DATA:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'server_version:10.1.0')
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_show_server_metrics(dd_run_check, aggregator, instance):
    """
    Test specific show server metrics
    """
    expected_metrics = SHOW_MAP['show server']['expected_metrics']

    check = TibcoEMSCheck('tibco_ems', {}, [instance])
    check.run_tibco_command = MagicMock(return_value=mock_output('show_server'))
    dd_run_check(check)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_parse_show_server():
    """
    Test the parse_show_server method
    """
    section = SHOW_MAP['show server']['section'].decode('utf-8')
    regex = SHOW_MAP['show server']['regex']

    check = TibcoEMSCheck('tibco_ems', {}, [{}])
    output = check._section_output(section)['show server']
    result = check._parse_show_server(output, regex)

    expected_result = SHOW_MAP['show server']['expected_result']

    assert result == expected_result


@pytest.mark.parametrize(
    "output, expected_metrics",
    [
        pytest.param(
            mock_output('show_queues'),
            SHOW_MAP['show queues']['expected_metrics'],
            id="show queues",
        ),
        pytest.param(
            mock_output('show_topics'),
            SHOW_MAP['show topics']['expected_metrics'],
            id="show topics",
        ),
        pytest.param(
            mock_output('show_stat_consumers'),
            SHOW_MAP['show stat consumers']['expected_metrics'],
            id="show stat consumers",
        ),
        pytest.param(
            mock_output('show_stat_producers'),
            SHOW_MAP['show stat producers']['expected_metrics'],
            id="show stat producers",
        ),
        pytest.param(
            mock_output('show_connections'),
            SHOW_MAP['show connections full']['expected_metrics'],
            id="show connections full",
        ),
        pytest.param(
            mock_output('show_durables'),
            SHOW_MAP['show durables']['expected_metrics'],
            id="show durables",
        ),
    ],
)
def test_show_metrics(dd_run_check, aggregator, instance, output, expected_metrics):
    check = TibcoEMSCheck('tibco_ems', {}, [instance])
    check.run_tibco_command = MagicMock(return_value=output)
    dd_run_check(check)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize(
    "expected_result, data, regex",
    [
        pytest.param(
            SHOW_MAP['show queues']['expected_result'],
            SHOW_MAP['show queues']['section'],
            SHOW_MAP['show queues']['regex'],
            id="show queues",
        ),
        pytest.param(
            SHOW_MAP['show topics']['expected_result'],
            SHOW_MAP['show topics']['section'],
            SHOW_MAP['show topics']['regex'],
            id="show topics",
        ),
        pytest.param(
            SHOW_MAP['show stat consumers']['expected_result'],
            SHOW_MAP['show stat consumers']['section'],
            SHOW_MAP['show stat consumers']['regex'],
            id="show stat consumers",
        ),
        pytest.param(
            SHOW_MAP['show stat producers']['expected_result'],
            SHOW_MAP['show stat producers']['section'],
            SHOW_MAP['show stat producers']['regex'],
            id="show stat producers",
        ),
        pytest.param(
            SHOW_MAP['show connections full']['expected_result'],
            SHOW_MAP['show connections full']['section'],
            SHOW_MAP['show connections full']['regex'],
            id="show connections full",
        ),
        pytest.param(
            SHOW_MAP['show durables']['expected_result'],
            SHOW_MAP['show durables']['section'],
            SHOW_MAP['show durables']['regex'],
            id="show durables",
        ),
    ],
)
def test_parse_factory(data, regex, expected_result):
    check = TibcoEMSCheck('tibco_ems', {}, [{}])
    result = check._parse_factory(data.decode('utf-8'), regex)

    assert result == expected_result
