# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.testing import requires_py3

from ..utils import get_check

pytestmark = [
    requires_py3,
]


def test_basic(aggregator, datadog_agent, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP kubernetes_build_info A metric with a constant '1' value labeled by major, minor, git version, git commit, git tree state, build date, Go version, and compiler from which Kubernetes was built, and platform on which it is running.
        # TYPE kubernetes_build_info gauge
        kubernetes_build_info{buildDate="2016-11-18T23:57:26Z",compiler="gc",gitCommit="3872cb93abf9482d770e651b5fe14667a6fca7e0",gitTreeState="dirty",gitVersion="v1.6.0-alpha.0.680+3872cb93abf948-dirty",goVersion="go1.7.3",major="1",minor="6+",platform="linux/amd64"} 1
        """  # noqa: E501
    )
    check = get_check(
        {'metrics': [{'kubernetes_build_info': {'name': 'version', 'type': 'metadata', 'label': 'gitVersion'}}]}
    )
    check.check_id = 'test:instance'
    dd_run_check(check)

    version_metadata = {
        'version.major': '1',
        'version.minor': '6',
        'version.patch': '0',
        'version.release': 'alpha.0.680',
        'version.build': '3872cb93abf948-dirty',
        'version.raw': 'v1.6.0-alpha.0.680+3872cb93abf948-dirty',
        'version.scheme': 'semver',
    }

    datadog_agent.assert_metadata('test:instance', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
    aggregator.assert_all_metrics_covered()


def test_options(aggregator, datadog_agent, dd_run_check, mock_http_response):
    mock_http_response(
        """
        # HELP kubernetes_build_info A metric with a constant '1' value labeled by major, minor, git version, git commit, git tree state, build date, Go version, and compiler from which Kubernetes was built, and platform on which it is running.
        # TYPE kubernetes_build_info gauge
        kubernetes_build_info{buildDate="2016-11-18T23:57:26Z",compiler="gc",gitCommit="3872cb93abf9482d770e651b5fe14667a6fca7e0",gitTreeState="dirty",gitVersion="v1.6.0-alpha.0.680+3872cb93abf948-dirty",goVersion="go1.7.3",major="1",minor="6+",platform="linux/amd64"} 1
        """  # noqa: E501
    )
    check = get_check(
        {
            'metrics': [
                {
                    'kubernetes_build_info': {
                        'name': 'version',
                        'type': 'metadata',
                        'label': 'gitVersion',
                        'scheme': 'regex',
                        'final_scheme': 'semver',
                        'pattern': 'v(?P<major>\\d+)\\.(?P<minor>\\d+)\\.(?P<fix>\\d+)',
                    }
                }
            ],
        }
    )
    check.check_id = 'test:instance'
    dd_run_check(check)

    version_metadata = {
        'version.major': '1',
        'version.minor': '6',
        'version.fix': '0',
        'version.raw': 'v1.6.0-alpha.0.680+3872cb93abf948-dirty',
        'version.scheme': 'semver',
    }

    datadog_agent.assert_metadata('test:instance', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))
    aggregator.assert_all_metrics_covered()
