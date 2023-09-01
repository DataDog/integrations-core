# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest

from datadog_checks.etcd import Etcd

from .common import ETCD_VERSION, REMAPED_DEBUGGING_METRICS, URL
from .utils import is_leader

CHECK_NAME = 'etcd'

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@pytest.mark.integration
def test_check(aggregator, instance, openmetrics_metrics, dd_run_check):
    check = Etcd('etcd', {}, [instance])
    dd_run_check(check)

    tags = ['is_leader:{}'.format('true' if is_leader(URL) else 'false')]

    # Make sure we assert at least one metric to make sure the expected tags are being added
    aggregator.assert_metric('etcd.process.cpu.seconds.total', tags=tags)
    for metric in openmetrics_metrics:
        aggregator.assert_metric('etcd.{}'.format(metric), tags=tags, at_least=0)

    for metric in REMAPED_DEBUGGING_METRICS:
        aggregator.assert_metric('etcd.{}'.format(metric), at_least=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_check_no_leader_tag(aggregator, instance, openmetrics_metrics, dd_run_check):
    instance = deepcopy(instance)
    instance['leader_tag'] = False

    check = Etcd('etcd', {}, [instance])
    dd_run_check(check)

    # Make sure we assert at least one metric to make sure the leader tag is indeed not there
    aggregator.assert_metric('etcd.process.cpu.seconds.total', tags=[])
    for metric in openmetrics_metrics:
        aggregator.assert_metric('etcd.{}'.format(metric), tags=[], at_least=0)

    for metric in REMAPED_DEBUGGING_METRICS:
        aggregator.assert_metric('etcd.{}'.format(metric), at_least=1)

    aggregator.assert_all_metrics_covered()


@pytest.mark.integration
def test_service_check(aggregator, instance, dd_run_check):
    check = Etcd(CHECK_NAME, {}, [instance])
    dd_run_check(check)

    tags = ['endpoint:{}'.format(instance['prometheus_url'])]

    aggregator.assert_service_check('etcd.prometheus.health', Etcd.OK, tags=tags, count=1)


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_verify': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_verify': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': False}),
        ("timeout", {'prometheus_timeout': 100}, {'timeout': (100.0, 100.0)}),
    ],
)
@pytest.mark.integration
def test_config(instance, test_case, extra_config, expected_http_kwargs, dd_run_check):
    instance.update(extra_config)
    check = Etcd(CHECK_NAME, {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        dd_run_check(check)

        http_kwargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'data': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_kwargs.update(expected_http_kwargs)
        r.post.assert_called_with(URL + '/v3/maintenance/status', **http_kwargs)


@pytest.mark.integration
def test_version_metadata(aggregator, instance, dd_environment, datadog_agent, dd_run_check):
    check_instance = Etcd(CHECK_NAME, {}, [instance])
    check_instance.check_id = 'test:123'
    dd_run_check(check_instance)

    raw_version = ETCD_VERSION.lstrip('v')  # version contain `v` prefix
    major, minor, patch = raw_version.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': raw_version,
    }

    datadog_agent.assert_metadata('test:123', version_metadata)
