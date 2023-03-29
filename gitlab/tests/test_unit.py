# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock.mock import MagicMock

from datadog_checks.base import ConfigurationError
from datadog_checks.dev.testing import requires_py2
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab.common import get_gitlab_version

from .common import METRICS, assert_check

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_check(dd_run_check, aggregator, mock_data, gitlab_check, config, use_openmetrics):
    if use_openmetrics:
        instance = config['instances'][0]
        instance["openmetrics_endpoint"] = instance["prometheus_url"]

    check = gitlab_check(config)
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, METRICS, use_openmetrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_py2
def test_openmetrics_with_python2(gitlab_check, config):
    instance = config['instances'][0]
    instance["openmetrics_endpoint"] = instance["prometheus_url"]

    with pytest.raises(
        ConfigurationError, match="This version of the integration is only available when using Python 3."
    ):
        gitlab_check(config)


@pytest.mark.parametrize(
    "raw_version",
    [
        "1.2.3",
        "5.6.7",
    ],
)
def test_get_gitlab_version(raw_version):
    http = MagicMock()
    http.get.return_value.json.return_value = {"version": raw_version}

    version = get_gitlab_version(http, MagicMock(), "http://localhost", "my-token")

    http.get.assert_called_with("http://localhost/api/v4/version", params={'access_token': "my-token"})
    assert version == raw_version


def test_get_gitlab_version_without_token():
    http = MagicMock()
    version = get_gitlab_version(http, MagicMock(), "http://localhost", None)
    http.get.assert_not_called()
    assert version is None
