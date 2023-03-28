# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.testing import requires_py2

from .common import METRICS, assert_check

pytestmark = [pytest.mark.unit]


def test_check(dd_run_check, aggregator, mock_data, gitlab_check, config):
    check = gitlab_check(config)
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, METRICS)
    aggregator.assert_all_metrics_covered()


@requires_py2
def test_openmetrics_with_python2(gitlab_check, config):
    instance = config['instances'][0]
    instance["use_openmetrics"] = True

    with pytest.raises(
        ConfigurationError, match="This version of the integration is only available when using Python 3."
    ):
        gitlab_check(config)
