# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import CONFIG, METRICS


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(CONFIG)
    import subprocess

    try:
        print(subprocess.check_output(['docker', 'logs', 'dd_nfsstat_py27']))
    except Exception:
        print(subprocess.check_output(['docker', 'logs', 'dd_nfsstat_py38']))
    for metric in METRICS:
        aggregator.assert_metric(metric)

    aggregator.assert_all_metrics_covered()
