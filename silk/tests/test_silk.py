# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import logging
import os

import mock
import pytest

from datadog_checks.dev.fs import read_file
from datadog_checks.silk import SilkCheck
from datadog_checks.silk.metrics import Metric

from .common import BLOCKSIZE_METRICS, HERE, HOST, METRICS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_check(aggregator, instance, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    dd_run_check(check)
    base_tags = ['silk_host:localhost:80', 'system_id:5501', 'system_name:K2-5501', 'test:silk']

    for metric in METRICS + BLOCKSIZE_METRICS:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)

    aggregator.assert_service_check('silk.can_connect', SilkCheck.OK)
    aggregator.assert_service_check('silk.system.state', SilkCheck.OK)
    aggregator.assert_service_check('silk.server.state', SilkCheck.OK, count=2)


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_log_line(aggregator, instance, dd_run_check, caplog):
    caplog.set_level(logging.DEBUG)
    check = SilkCheck('silk', {}, [instance])
    dd_run_check(check)

    assert "Could not find metric part: ['rw'], reverting metric name to: `system.latency.outer`" in caplog.text


@pytest.mark.integration
@pytest.mark.usefixtures("dd_environment")
def test_version_metadata(aggregator, instance, datadog_agent, dd_run_check):
    check = SilkCheck('silk', {}, [instance])
    check.check_id = 'test:123'
    dd_run_check(check)

    version_metadata = {
        'version.scheme': 'silk',  # silk does not use semver
        'version.major': '6',
        'version.minor': '0',
        'version.patch': '102',
        'version.release': '25',
        'version.raw': '6.0.102.25',
    }

    datadog_agent.assert_metadata('test:123', version_metadata)


def test_error_msg_response(dd_run_check, aggregator, instance):
    error_response = {"error_msg": "Statistics data is unavailable while system is OFFLINE"}
    with mock.patch('datadog_checks.base.utils.http.requests.Response.json') as g:
        g.return_value = error_response
        check = SilkCheck('silk', {}, [instance])
        dd_run_check(check)
        aggregator.assert_service_check('silk.can_connect', SilkCheck.WARNING)


def test_incorrect_config(dd_run_check, aggregator):
    invalid_instance = {'host_addres': 'localhost'}  # misspelled required parameter
    with pytest.raises(Exception):
        check = SilkCheck('silk', {}, [invalid_instance])
        dd_run_check(check)


def test_unreachable_endpoint(dd_run_check, aggregator):
    invalid_instance = {
        'host_address': 'http://{}:81'.format(HOST),
    }
    check = SilkCheck('silk', {}, [invalid_instance])

    with pytest.raises(Exception):
        dd_run_check(check)
    aggregator.assert_service_check('silk.can_connect', SilkCheck.CRITICAL)


def mock_get_data(url):
    file_contents = read_file(os.path.join(HERE, 'fixtures', 'stats', url))
    response = json.loads(file_contents)
    return [(response, 200)]


@pytest.mark.parametrize(
    'get_data_url, expected_metrics, metrics_to_collect',
    [
        (
            'system__bs_breakdown=True.json',  # `?` had to be removed to pass windows CI
            [
                'silk.system.block_size.io_ops.avg',
                'silk.system.block_size.latency.inner',
                'silk.system.block_size.latency.outer',
                'silk.system.block_size.throughput.avg',
            ],
            {
                'stats/system?__bs_breakdown=True': Metric(
                    **{
                        'prefix': 'system.block_size',
                        'metrics': {
                            'iops_avg': 'io_ops.avg',
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'resolution': 'resolution',
                            'bs': 'block_size',
                        },
                    }
                )
            },
        ),
        (
            'volumes__bs_breakdown=True.json',
            [
                'silk.volume.block_size.io_ops.avg',
                'silk.volume.block_size.latency.inner',
                'silk.volume.block_size.latency.outer',
                'silk.volume.block_size.throughput.avg',
            ],
            {
                'stats/volumes?__bs_breakdown=True': Metric(
                    **{
                        'prefix': 'volume.block_size',
                        'metrics': {
                            'iops_avg': ('io_ops.avg', 'gauge'),
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'peer_k2_name': 'peer_name',
                            'volume_name': 'volume_name',
                            'resolution': 'resolution',
                            'bs': 'block_size',
                        },
                    }
                )
            },
        ),
        (
            'volumes__rw_breakdown=True.json',
            [
                'silk.volume.read.io_ops.avg',
                'silk.volume.read.latency.inner',
                'silk.volume.read.latency.outer',
                'silk.volume.read.throughput.avg',
                'silk.volume.write.io_ops.avg',
                'silk.volume.write.latency.inner',
                'silk.volume.write.latency.outer',
                'silk.volume.write.throughput.avg',
            ],
            {
                'stats/volumes?__rw_breakdown=True': Metric(
                    **{
                        'prefix': 'volume',
                        'metrics': {
                            'iops_avg': ('io_ops.avg', 'gauge'),
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'peer_k2_name': 'peer_name',
                            'volume_name': 'volume_name',
                            'resolution': 'resolution',
                        },
                        'field_to_name': {
                            'rw': {
                                'r': 'read',
                                'w': 'write',
                            }
                        },
                    }
                )
            },
        ),
        (
            'system__rw_breakdown=True.json',
            [
                'silk.system.read.io_ops.avg',
                'silk.system.read.latency.inner',
                'silk.system.read.latency.outer',
                'silk.system.read.throughput.avg',
                'silk.system.write.io_ops.avg',
                'silk.system.write.latency.inner',
                'silk.system.write.latency.outer',
                'silk.system.write.throughput.avg',
            ],
            {
                'stats/system?__rw_breakdown=True': Metric(
                    **{
                        'prefix': 'system',
                        'metrics': {
                            'iops_avg': 'io_ops.avg',
                            'latency_inner': 'latency.inner',
                            'latency_outer': 'latency.outer',
                            'throughput_avg': 'throughput.avg',
                        },
                        'tags': {
                            'resolution': 'resolution',
                        },
                        'field_to_name': {
                            'rw': {
                                'r': 'read',
                                'w': 'write',
                            }
                        },
                    }
                )
            },
        ),
    ],
)
def test_bs_rw_metrics(dd_run_check, aggregator, instance, get_data_url, expected_metrics, metrics_to_collect):
    check = SilkCheck('silk', {}, [instance])
    check._get_data = mock.MagicMock(side_effect=mock_get_data(get_data_url))
    check.metrics_to_collect = metrics_to_collect
    base_tags = ['silk_host:localhost:80', 'system_id:5501', 'system_name:K2-5501', 'test:silk']
    check.collect_metrics(base_tags)

    for metric in expected_metrics:
        aggregator.assert_metric(metric)
        for tag in base_tags:
            aggregator.assert_metric_has_tag(metric, tag)
