# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.grpc import GrpcCheck

from .common import GRPC_METRICS


@pytest.mark.integration
@pytest.mark.usefixtures('dd_environment')
def test_grpc_check(dd_run_check, aggregator, instance):
    check = GrpcCheck('grpc', {}, [instance])
    dd_run_check(check)

    ok_channel_tags = ['lb_policy:round_robin', 'state:READY', 'target::8080']
    aggregator.assert_metric('grpc.channel.calls_failed', value=0, tags=ok_channel_tags)
    aggregator.assert_metric('grpc.channel.calls_started', value=0, tags=ok_channel_tags)
    aggregator.assert_metric('grpc.channel.calls_succeeded', value=0, tags=ok_channel_tags)
    aggregator.assert_metric('grpc.channel.state', value=2, tags=ok_channel_tags)

    bad_address_channel_tags = ['lb_policy:round_robin', 'state:TRANSIENT_FAILURE', 'target:wrong_address:8083']
    aggregator.assert_metric('grpc.channel.calls_failed', value=0, tags=bad_address_channel_tags)
    aggregator.assert_metric('grpc.channel.calls_started', value=0, tags=bad_address_channel_tags)
    aggregator.assert_metric('grpc.channel.calls_succeeded', value=0, tags=bad_address_channel_tags)
    aggregator.assert_metric('grpc.channel.state', value=4, tags=bad_address_channel_tags)

    aggregator.assert_metric('grpc.channel.uptime', tags=ok_channel_tags)
    aggregator.assert_metric('grpc.channel.uptime', tags=bad_address_channel_tags)

    ok_subchannel_tags = ['channel_target::8080', 'state:READY', 'target::8080']
    aggregator.assert_metric('grpc.subchannel.calls_failed', value=0, tags=ok_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_started', value=0, tags=ok_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_succeeded', value=0, tags=ok_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.state', value=2, tags=ok_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.uptime', tags=ok_subchannel_tags)

    bad_address_subchannel_tags = ['channel_target:wrong_address:8083', 'state:TRANSIENT_FAILURE']
    aggregator.assert_metric('grpc.subchannel.calls_failed', value=0, tags=bad_address_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_started', value=0, tags=bad_address_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_succeeded', value=0, tags=bad_address_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.state', value=4, tags=bad_address_subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.uptime', tags=bad_address_subchannel_tags)

    server_tags = ['listening_socket:[::]:8080']
    aggregator.assert_metric('grpc.server.calls_failed', value=0, tags=server_tags)
    aggregator.assert_metric('grpc.server.calls_started', value=1, tags=server_tags)
    aggregator.assert_metric('grpc.server.calls_succeeded', value=0, tags=server_tags)
    aggregator.assert_metric('grpc.server.connected_clients', value=3, tags=server_tags)

    aggregator.assert_metric('grpc.server.number_servers', value=1, tags=[])

    for metric in GRPC_METRICS:
        formatted_metric = "grpc.{}".format(metric)
        aggregator.assert_metric(formatted_metric)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())
