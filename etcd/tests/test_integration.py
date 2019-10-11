# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.dev import run_command
from datadog_checks.etcd import Etcd

from .common import COMPOSE_FILE, HOST, STORE_METRICS, URL
from .utils import is_leader, legacy, preview

CHECK_NAME = 'etcd'

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


@preview
def test_check(aggregator, instance, openmetrics_metrics):
    check = Etcd('etcd', {}, [instance])
    check.check(instance)

    tags = ['is_leader:{}'.format('true' if is_leader(URL) else 'false')]

    for metric in openmetrics_metrics:
        aggregator.assert_metric('etcd.{}'.format(metric), tags=tags, at_least=0)

    assert aggregator.metrics_asserted_pct > 79, 'Missing metrics {}'.format(aggregator.not_asserted())


@preview
def test_check_no_leader_tag(aggregator, instance, openmetrics_metrics):
    instance = deepcopy(instance)
    instance['leader_tag'] = False

    check = Etcd('etcd', {}, [instance])
    check.check(instance)

    for metric in openmetrics_metrics:
        aggregator.assert_metric('etcd.{}'.format(metric), tags=[], at_least=0)

    assert aggregator.metrics_asserted_pct > 79, 'Missing metrics {}'.format(aggregator.not_asserted())


@preview
def test_service_check(aggregator, instance):
    check = Etcd(CHECK_NAME, {}, [instance])
    check.check(instance)

    tags = ['endpoint:{}'.format(instance['prometheus_url'])]

    aggregator.assert_service_check('etcd.prometheus.health', Etcd.OK, tags=tags, count=1)


@legacy
def test_bad_config(aggregator):
    bad_url = '{}/test'.format(URL)
    instance = {'url': bad_url, 'use_preview': False}
    check = Etcd(CHECK_NAME, {}, [instance])

    with pytest.raises(Exception):
        check.check(instance)

    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, tags=['url:{}'.format(bad_url)], count=1)
    aggregator.assert_service_check(check.HEALTH_SERVICE_CHECK_NAME)


@legacy
def test_legacy_metrics(legacy_instance, aggregator):
    check = Etcd(CHECK_NAME, {}, [legacy_instance])
    check.check(legacy_instance)

    tags = ['url:{}'.format(URL), 'etcd_state:{}'.format('leader' if is_leader(URL) else 'follower')]

    for mname in STORE_METRICS:
        aggregator.assert_metric('etcd.store.{}'.format(mname), tags=tags, count=1)

    aggregator.assert_metric('etcd.self.send.appendrequest.count', tags=tags, count=1)
    aggregator.assert_metric('etcd.self.recv.appendrequest.count', tags=tags, count=1)


@legacy
def test_legacy_service_checks(legacy_instance, aggregator):
    check = Etcd(CHECK_NAME, {}, [legacy_instance])
    check.check(legacy_instance)

    tags = ['url:{}'.format(URL), 'etcd_state:{}'.format('leader' if is_leader(URL) else 'follower')]

    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, tags=tags, count=1)
    aggregator.assert_service_check(check.HEALTH_SERVICE_CHECK_NAME, tags=tags[:1], count=1)


@legacy
def test_followers(aggregator):
    urls = []
    result = run_command('docker-compose -f {} ps -q'.format(COMPOSE_FILE), capture='out', check=True)
    container_ids = result.stdout.splitlines()

    for container_id in container_ids:
        result = run_command('docker port {} 2379/tcp'.format(container_id), capture='out', check=True)
        port = result.stdout.strip().split(':')[-1]
        urls.append('http://{}:{}'.format(HOST, port))

    for url in urls:
        if is_leader(url):
            break
    else:
        raise Exception('No leader found')

    response = requests.get('{}/v2/stats/leader'.format(url))
    followers = list(response.json().get('followers', {}).keys())

    instance = {'url': url, 'use_preview': False}
    check = Etcd(CHECK_NAME, {}, [instance])
    check.check(instance)

    common_leader_tags = ['url:{}'.format(url), 'etcd_state:leader']
    follower_tags = [
        common_leader_tags + ['follower:{}'.format(followers[0])],
        common_leader_tags + ['follower:{}'.format(followers[1])],
    ]

    for fol_tags in follower_tags:
        aggregator.assert_metric('etcd.leader.counts.fail', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.counts.success', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.latency.avg', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.latency.min', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.latency.max', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.latency.stddev', count=1, tags=fol_tags)
        aggregator.assert_metric('etcd.leader.latency.current', count=1, tags=fol_tags)


@legacy
@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_cert_validation': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_cert_validation': False}, {'verify': False}),
        ("legacy ssl config unset", {}, {'verify': False}),
    ],
)
def test_config_legacy(legacy_instance, test_case, extra_config, expected_http_kwargs):
    legacy_instance.update(extra_config)
    check = Etcd(CHECK_NAME, {}, [legacy_instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(legacy_instance)

        http_kwargs = dict(
            auth=mock.ANY, cert=mock.ANY, headers=mock.ANY, proxies=mock.ANY, timeout=mock.ANY, verify=mock.ANY
        )
        http_kwargs.update(expected_http_kwargs)
        r.get.assert_called_with(URL + '/v2/stats/store', **http_kwargs)


@preview
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
def test_config(instance, test_case, extra_config, expected_http_kwargs):
    instance.update(extra_config)
    check = Etcd(CHECK_NAME, {}, [instance])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(instance)

        http_kwargs = dict(
            auth=mock.ANY,
            cert=mock.ANY,
            data=mock.ANY,
            headers=mock.ANY,
            proxies=mock.ANY,
            timeout=mock.ANY,
            verify=mock.ANY,
        )
        http_kwargs.update(expected_http_kwargs)
        r.post.assert_called_with(URL + '/v3alpha/maintenance/status', **http_kwargs)
