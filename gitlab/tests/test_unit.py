# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
from mock.mock import MagicMock

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.dev.testing import requires_py2, requires_py3
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.gitlab.common import get_gitlab_version

from .common import V1_METRICS, V2_METRICS, assert_check

pytestmark = [pytest.mark.unit]


@pytest.mark.parametrize('use_openmetrics', [True, False], indirect=True)
def test_check(dd_run_check, aggregator, mock_data, gitlab_check, get_config, use_openmetrics):
    check = gitlab_check(get_config(use_openmetrics))
    dd_run_check(check)
    dd_run_check(check)

    assert_check(aggregator, V2_METRICS if use_openmetrics else V1_METRICS, use_openmetrics)
    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


@requires_py2
def test_openmetrics_with_python2(gitlab_check, get_config):
    with pytest.raises(
        ConfigurationError, match="This version of the integration is only available when using Python 3."
    ):
        gitlab_check(get_config(True))


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


@requires_py3
def test_no_gitlab_url(dd_run_check, aggregator, mock_data, gitlab_check, get_config):
    config = get_config(True)
    del config['instances'][0]['gitlab_url']
    check = gitlab_check(config)
    dd_run_check(check)
    aggregator.assert_service_check('gitlab.openmetrics.health', status=AgentCheck.OK)
