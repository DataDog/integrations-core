# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest
import requests

from datadog_checks.dev import run_command
from datadog_checks.etcd import Etcd
from .common import HOST
from .utils import is_leader


CHECK_NAME = 'etcd'

STORE_METRICS = [
    'compareanddelete.fail',
    'compareanddelete.success',
    'compareandswap.fail',
    'compareandswap.success',
    'create.fail',
    'create.success',
    'delete.fail',
    'delete.success',
    'expire.count',
    'gets.fail',
    'gets.success',
    'sets.fail',
    'sets.success',
    'update.fail',
    'update.success',
    'watchers',
]


def test_bad_config(main_instance, aggregator):
    instance = {'url': '{}/test'.format(main_instance['url'])}
    check = Etcd(CHECK_NAME, None, {}, [instance])

    with pytest.raises(Exception):
        check.check(instance)

    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME, tags=['url:{}/test'.format(main_instance['url'])], count=1
    )
    aggregator.assert_service_check(check.HEALTH_SERVICE_CHECK_NAME)


def test_metrics(main_instance, aggregator):
    check = Etcd(CHECK_NAME, None, {}, [main_instance])
    check.check(main_instance)

    url = main_instance['url']
    tags = ['url:{}'.format(url), 'etcd_state:{}'.format('leader' if is_leader(url) else 'follower')]

    for mname in STORE_METRICS:
        aggregator.assert_metric('etcd.store.{}'.format(mname), tags=tags, count=1)

    aggregator.assert_metric('etcd.self.send.appendrequest.count', tags=tags, count=1)
    aggregator.assert_metric('etcd.self.recv.appendrequest.count', tags=tags, count=1)


def test_service_checks(main_instance, aggregator):
    check = Etcd(CHECK_NAME, None, {}, [main_instance])
    check.check(main_instance)

    url = main_instance['url']
    tags = ['url:{}'.format(url), 'etcd_state:{}'.format('leader' if is_leader(url) else 'follower')]

    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, tags=tags, count=1)
    aggregator.assert_service_check(check.HEALTH_SERVICE_CHECK_NAME, tags=tags[:1], count=1)


def test_followers(aggregator, spin_up_etcd):
    compose_file = spin_up_etcd

    urls = []
    result = run_command('docker-compose -f {} ps -q'.format(compose_file), capture='out', check=True)
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

    instance = {'url': url}
    check = Etcd(CHECK_NAME, None, {}, [instance])
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
