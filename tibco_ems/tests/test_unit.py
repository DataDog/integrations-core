# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Callable, Dict  # noqa: F401

import pytest
from mock import patch

from datadog_checks.base import AgentCheck  # noqa: F401
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.tibco_ems import TibcoEMSCheck

from .common import METRIC_DATA, SECTION_OUTPUT_SHOW_ALL, SECTION_RESULT, SHOW_MAP, mock_output


def test_check(dd_run_check, aggregator, instance):

    check = TibcoEMSCheck('tibco_ems', {}, [instance])
    with patch('datadog_checks.tibco_ems.tibco_ems.get_subprocess_output', return_value=mock_output('show_all')):
        dd_run_check(check)

    for metric in METRIC_DATA:
        aggregator.assert_metric(metric)
        aggregator.assert_metric_has_tag(metric, 'server_version:10.1.0')
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
    aggregator.assert_all_metrics_covered()


def test_parse_show_server():
    # Use the 0th index to get string output from the mock_output function
    output = SHOW_MAP['show server']['output']
    regex = SHOW_MAP['show server']['regex']
    check = TibcoEMSCheck('tibco_ems', {}, [{}])
    result = check.parse_show_server(output, regex)

    expected_result = SHOW_MAP['show server']['expected_result']

    assert result == expected_result


@pytest.mark.parametrize(
    "expected_result, data, regex",
    [
        [
            SHOW_MAP['show queues']['expected_result'],
            SHOW_MAP['show queues']['output'],
            SHOW_MAP['show queues']['regex'],
        ],
        [
            SHOW_MAP['show topics']['expected_result'],
            SHOW_MAP['show topics']['output'],
            SHOW_MAP['show topics']['regex'],
        ],
        [
            SHOW_MAP['show stat consumers']['expected_result'],
            SHOW_MAP['show stat consumers']['output'],
            SHOW_MAP['show stat consumers']['regex'],
        ],
        [
            SHOW_MAP['show stat producers']['expected_result'],
            SHOW_MAP['show stat producers']['output'],
            SHOW_MAP['show stat producers']['regex'],
        ],
        [
            SHOW_MAP['show connections full']['expected_result'],
            SHOW_MAP['show connections full']['output'],
            SHOW_MAP['show connections full']['regex'],
        ],
    ],
)
def test_parse_factory(data, regex, expected_result):

    check = TibcoEMSCheck('tibco_ems', {}, [{}])
    result = check.parse_factory(data, regex)

    assert result == expected_result


def test_section_output():
    check = TibcoEMSCheck('tibco_ems', {}, [{}])
    output = check.section_output(SECTION_OUTPUT_SHOW_ALL)

    assert output == SECTION_RESULT
