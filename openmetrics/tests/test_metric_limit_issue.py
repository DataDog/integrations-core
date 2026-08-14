# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

import pytest

from datadog_checks.base.checks.openmetrics.metric_limit_issue import ISSUE_NAME, ISSUE_TYPE
from datadog_checks.openmetrics import OpenMetricsCheck

ISSUE_ID = 'openmetrics-dropped-config:40c8930ce3bf6455'
ENDPOINT = 'http://localhost:10249/metrics'


@pytest.mark.parametrize(
    ('instance', 'filter_option'),
    [
        pytest.param(
            {
                'openmetrics_endpoint': ENDPOINT,
                'namespace': 'openmetrics',
                'metrics': ['.*'],
                'max_returned_metrics': 5,
            },
            'metrics / exclude_metrics',
            id='v2',
        ),
        pytest.param(
            {
                'prometheus_url': ENDPOINT,
                'namespace': 'openmetrics',
                'metrics': ['*'],
                'max_returned_metrics': 5,
            },
            'metrics / ignore_metrics',
            id='v1',
        ),
    ],
)
def test_openmetrics_base_classes_report_metric_limit_issue(
    datadog_agent: Any, instance: dict[str, Any], filter_option: str
) -> None:
    check = OpenMetricsCheck('openmetrics', {}, [instance])

    check._on_metric_limit_state(True, 20, 5)

    [issue] = datadog_agent._sent_reported_issues['openmetrics']
    assert issue['id'] == ISSUE_ID
    assert issue['issue_name'] == ISSUE_NAME
    assert issue['issue_type'] == ISSUE_TYPE
    assert issue['extra']['observed_contexts'] == 20
    assert issue['extra']['dropped_contexts'] == 15
    assert filter_option in issue['remediation']['steps'][0]['text']
