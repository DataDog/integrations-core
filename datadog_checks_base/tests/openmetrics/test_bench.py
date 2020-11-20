# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import pytest

from datadog_checks.base import OpenMetricsBaseCheck
from datadog_checks.dev import get_here

from ..utils import requires_py3

pytestmark = [requires_py3, pytest.mark.openmetrics, pytest.mark.openmetrics_config]

HERE = get_here()


@pytest.fixture
def fixture_ksm():
    return os.path.join(os.path.dirname(HERE), 'fixtures', 'prometheus', 'ksm.txt')


def test_ksm_new(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    c = OpenMetricsBaseCheck('test', {}, [{'openmetrics_endpoint': 'foo', 'namespace': 'bar', 'metrics': ['.+']}])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, None)


def test_ksm_old(benchmark, dd_run_check, mock_http_response, fixture_ksm):
    mock_http_response(file_path=fixture_ksm)
    instance = {'prometheus_url': 'foo', 'namespace': 'bar', 'metrics': ['*']}
    c = OpenMetricsBaseCheck('test', {}, [instance])

    # Run once to get initialization steps out of the way.
    dd_run_check(c)

    benchmark(c.check, instance)
