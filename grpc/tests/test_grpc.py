# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from typing import Any, Callable, Dict

from datadog_checks.base import AgentCheck
from datadog_checks.base.stubs.aggregator import AggregatorStub
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.grpc import GrpcCheck

import argparse
from concurrent import futures
import logging

import grpc
# TODO: Suppress until the macOS segfault fix rolled out
from grpc_channelz.v1 import channelz  # pylint: disable=wrong-import-position

from grpc_channelz.v1 import channelz_pb2
from grpc_channelz.v1 import channelz_pb2_grpc

log = logging.getLogger('test_grpc')


def create_server(addr):
    server = grpc.server(futures.ThreadPoolExecutor())
    channelz.add_channelz_servicer(server)
    server.add_insecure_port(addr)
    return server


def _start_test_server(addr):
    server = grpc.server(futures.ThreadPoolExecutor())
    channelz.add_channelz_servicer(server)
    server.add_insecure_port(addr)
    server.start()
    return server


def _query_stats(addr):
    log.debug(f'Query channelz endpoint on {addr}')
    with grpc.insecure_channel(addr) as channel:
        channelz_stub = channelz_pb2_grpc.ChannelzStub(channel)
        _ = channelz_stub.GetServers(channelz_pb2.GetServersRequest())


def test_simple_grpc(dd_run_check, aggregator, instance):
    # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
    server_addr = "127.0.0.1:12345"
    server = _start_test_server(server_addr)
    _query_stats(server_addr)

    instance= {'addr': server_addr}
    check = GrpcCheck('grpc', {}, [instance])
    dd_run_check(check)

    aggregator.assert_metric('grpc.server.number_servers', value=1, tags=[])
    aggregator.assert_metric('grpc.server.calls_started', value=2, tags=[])
    aggregator.assert_metric('grpc.server.calls_succeeded', value=1, tags=[])
    aggregator.assert_metric('grpc.server.calls_failed', value=0, tags=[])

    channel_state_tags = ['state:READY', f'target:{server_addr}']
    aggregator.assert_metric('grpc.channel.state', value=1, tags=channel_state_tags)
    channel_tags = [f'target:{server_addr}']
    aggregator.assert_metric('grpc.channel.calls_started', value=2, tags=channel_tags)
    aggregator.assert_metric('grpc.channel.calls_succeeded', value=1, tags=channel_tags)


    subchannel_state_tags = ['state:READY', f'target:ipv4:{server_addr}', f'channel_target:{server_addr}']
    aggregator.assert_metric('grpc.subchannel.state', value=1, tags=subchannel_state_tags)
    subchannel_tags = [f'target:ipv4:{server_addr}', f'channel_target:{server_addr}']
    aggregator.assert_metric('grpc.subchannel.calls_started', value=3, tags=subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_succeeded', value=2, tags=subchannel_tags)
    aggregator.assert_metric('grpc.subchannel.calls_failed', value=0, tags=subchannel_tags)

    server.stop(0)


# def test_transient_failure(dd_run_check, aggregator, instance):
#     # type: (Callable[[AgentCheck, bool], None], AggregatorStub, Dict[str, Any]) -> None
#     server_addr = "127.0.0.1:12345"
#     server = _start_test_server(server_addr)
#     broken_channel = grpc.insecure_channel('127.0.0.1:12346')
#
#     instance= {'addr': server_addr}
#     check = GrpcCheck('grpc', {}, [instance])
#     dd_run_check(check)
#
#     aggregator.assert_metric('grpc.server.number_servers', value=1, tags=[])
#
#     server.stop(0)
