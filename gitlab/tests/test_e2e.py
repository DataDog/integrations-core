# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest
from flaky import flaky

from datadog_checks.dev.utils import get_metadata_metrics

from .common import assert_check

pytestmark = pytest.mark.e2e


def test_e2e_legacy(dd_agent_check, legacy_config):
    aggregator = dd_agent_check(legacy_config, rate=True)
    assert_check(aggregator)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
@flaky(max_runs=5)
# GitLab can start returning 502s even if all the conditions were met in the e2e env.
# Example:
# tests/test_e2e.py::test_e2e[True] PASSED                                 [ 66%]
# tests/test_e2e.py::test_e2e[False] FAILED                                [100%]
#
# =================================== FAILURES ===================================
# _______________________________ test_e2e[False] ________________________________
# tests/test_e2e.py:22: in test_e2e
#     aggregator = dd_agent_check(get_config(use_openmetrics), rate=True)
# ...
# E     File "/home/datadog_checks_base/datadog_checks/base/checks/openmetrics/mixins.py", line 854, in poll
# E       response.raise_for_status()
# E     File "/opt/datadog-agent/embedded/lib/python3.11/site-packages/requests/models.py", line 1021,
# in raise_for_status
# E       raise HTTPError(http_error_msg, response=self)
# E   requests.exceptions.HTTPError: 502 Server Error: Bad Gateway for url: http://localhost:8086/-/metrics
def test_e2e(dd_agent_check, get_config, use_openmetrics):
    aggregator = dd_agent_check(get_config(use_openmetrics), rate=True)
    assert_check(aggregator, use_openmetrics=use_openmetrics)
    # Excluding gitlab.rack.http_requests_total because it is a distribution metric
    # (its sum and count metrics are in the metadata)
    aggregator.assert_metrics_using_metadata(get_metadata_metrics(), exclude=["gitlab.rack.http_requests_total"])
