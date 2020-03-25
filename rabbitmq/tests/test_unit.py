# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import pytest
import requests
from tests.common import EXCHANGE_MESSAGE_STATS

import datadog_checks.base
from datadog_checks.rabbitmq import RabbitMQ
from datadog_checks.rabbitmq.rabbitmq import EXCHANGE_TYPE, NODE_TYPE, OVERVIEW_TYPE, RabbitMQException

from . import common, metrics

pytestmark = pytest.mark.unit


@pytest.mark.unit
def test__get_data(check):
    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.side_effect = [requests.exceptions.HTTPError, ValueError]
        with pytest.raises(RabbitMQException) as e:
            check._get_data('')
            assert isinstance(e, RabbitMQException)
        with pytest.raises(RabbitMQException) as e:
            check._get_data('')
            assert isinstance(e, RabbitMQException)


@pytest.mark.unit
def test_status_check(check, aggregator):
    check.check({"rabbitmq_api_url": "http://example.com"})
    assert len(aggregator._service_checks) == 1
    scs = aggregator.service_checks('rabbitmq.status')
    assert len(scs) == 1
    sc = scs[0]
    assert sc.status == RabbitMQ.CRITICAL

    # test aliveness service_checks on server down
    aggregator.reset()
    check.cached_vhosts = {"http://example.com/": ["vhost1", "vhost2"]}
    check.check({"rabbitmq_api_url": "http://example.com"})
    assert len(aggregator._service_checks) == 2

    scs = aggregator.service_checks('rabbitmq.status')
    assert len(scs) == 1
    sc = scs[0]
    assert sc.status == RabbitMQ.CRITICAL
    scs = aggregator.service_checks('rabbitmq.aliveness')
    assert len(scs) == 2
    sc = scs[0]
    assert sc.status == RabbitMQ.CRITICAL
    assert sc.tags == [u'vhost:vhost1']
    sc = scs[1]
    assert sc.status == RabbitMQ.CRITICAL
    assert sc.tags == [u'vhost:vhost2']

    aggregator.reset()
    check._get_data = mock.MagicMock()
    check.check({"rabbitmq_api_url": "http://example.com"})
    assert len(aggregator._service_checks) == 1
    scs = aggregator.service_checks('rabbitmq.status')
    assert len(scs) == 1
    sc = scs[0]
    assert sc.status == RabbitMQ.OK


@pytest.mark.unit
def test__check_aliveness(check, aggregator):
    instance = {"rabbitmq_api_url": "http://example.com"}
    check._get_data = mock.MagicMock()

    # only one vhost should be OK
    check._get_data.side_effect = [{"status": "ok"}, {}]
    check._check_aliveness('', vhosts=['foo', 'bar'], custom_tags=[])
    sc = aggregator.service_checks('rabbitmq.aliveness')
    assert len(sc) == 2
    aggregator.assert_service_check('rabbitmq.aliveness', status=RabbitMQ.OK)
    aggregator.assert_service_check('rabbitmq.aliveness', status=RabbitMQ.CRITICAL)

    # in case of connection errors, this check should stay silent
    check._get_data.side_effect = RabbitMQException
    with pytest.raises(RabbitMQException) as e:
        check._get_vhosts(instance, '')
        assert isinstance(e, RabbitMQException)


@pytest.mark.unit
def test__get_metrics(check, aggregator):
    data = {'fd_used': 3.14, 'disk_free': 4242, 'mem_used': 9000}

    assert check._get_metrics(data, NODE_TYPE, []) == 3
    assert check._get_metrics({}, NODE_TYPE, []) == 0


@pytest.mark.unit
def test__get_metrics_3_1(check, aggregator):
    data = {'queue_totals': []}

    metrics = check._get_metrics(data, OVERVIEW_TYPE, [])
    assert metrics == 0


@pytest.mark.unit
@mock.patch.object(datadog_checks.rabbitmq.RabbitMQ, '_get_object_data')
def test_get_stats_empty_exchanges(mock__get_object_data, instance, check, aggregator):
    data = [
        {'name': 'ex1', 'message_stats': EXCHANGE_MESSAGE_STATS},
        {'name': 'ex2', 'message_stats': EXCHANGE_MESSAGE_STATS},
        {'name': 'ex3', 'message_stats': {}},
        {'name': 'ex4', 'message_stats': EXCHANGE_MESSAGE_STATS},
    ]
    mock__get_object_data.return_value = data
    check.get_stats(instance, 'base_url', EXCHANGE_TYPE, 3, {'explicit': [], 'regexes': ['ex.*']}, [], [])
    aggregator.assert_metric('rabbitmq.exchange.messages.ack.count', tags=['rabbitmq_exchange:ex1'])
    aggregator.assert_metric('rabbitmq.exchange.messages.ack.count', tags=['rabbitmq_exchange:ex2'])
    aggregator.assert_metric('rabbitmq.exchange.messages.ack.count', tags=['rabbitmq_exchange:ex4'])


@pytest.mark.parametrize(
    'test_case, extra_config, expected_http_kwargs',
    [
        (
            "legacy auth config",
            {'rabbitmq_user': 'legacy_foo', 'rabbitmq_pass': 'legacy_bar'},
            {'auth': ('legacy_foo', 'legacy_bar')},
        ),
        ("new auth config", {'username': 'new_foo', 'password': 'new_bar'}, {'auth': ('new_foo', 'new_bar')}),
        ("legacy ssl config True", {'ssl_verify': True}, {'verify': True}),
        ("legacy ssl config False", {'ssl_verify': False}, {'verify': False}),
    ],
)
def test_config(check, test_case, extra_config, expected_http_kwargs):
    config = {'rabbitmq_api_url': common.URL, 'queues': ['test1'], 'tags': ["tag1:1", "tag2"], 'exchanges': ['test1']}
    config.update(extra_config)
    check = RabbitMQ('rabbitmq', {}, instances=[config])

    with mock.patch('datadog_checks.base.utils.http.requests') as r:
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(config)

        http_wargs = dict(
            auth=mock.ANY, cert=mock.ANY, headers=mock.ANY, proxies=mock.ANY, timeout=mock.ANY, verify=mock.ANY
        )
        http_wargs.update(expected_http_kwargs)

        r.get.assert_called_with('http://localhost:15672/api/connections', **http_wargs)


@pytest.mark.unit
def test_nodes(aggregator, check):

    # default, node metrics are collected
    check = RabbitMQ('rabbitmq', {}, instances=[common.CONFIG])
    check.check(common.CONFIG)

    for m in metrics.COMMON_METRICS:
        aggregator.assert_metric(m, count=1)

    aggregator.reset()


@pytest.mark.unit
def test_disable_nodes(aggregator, check):

    # node metrics collection disabled in config, node metrics should not appear
    check = RabbitMQ('rabbitmq', {}, instances=[common.CONFIG_NO_NODES])
    check.check(common.CONFIG_NO_NODES)

    for m in metrics.COMMON_METRICS:
        aggregator.assert_metric(m, count=0)

    # check to ensure other metrics are being collected
    for m in metrics.Q_METRICS:
        aggregator.assert_metric(m, count=1)
