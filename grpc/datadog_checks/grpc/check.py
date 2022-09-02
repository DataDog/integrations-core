# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

import grpc
import logging
from datetime import datetime
from grpc_channelz.v1 import channelz_pb2
from grpc_channelz.v1 import channelz_pb2_grpc

logger = logging.getLogger(__name__)


class GrpcCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'grpc'

    def __init__(self, name, init_config, instances):
        super(GrpcCheck, self).__init__(name, init_config, instances)
        self.addr = self.instance.get("addr")
        logger.debug("addr: %s", self.addr)

    def _get_servers_metrics(self, channelz_stub):
        get_server = channelz_stub.GetServers(channelz_pb2.GetServersRequest())
        servers = get_server.server
        self.gauge("server.number_servers", len(servers), tags=[])
        for server in servers:
            server_data = server.data
            tags = []
            # TODO Need tag
            self.gauge("server.calls_started", server_data.calls_started, tags=tags)
            self.gauge("server.calls_succeeded", server_data.calls_succeeded, tags=tags)
            self.gauge("server.calls_failed", server_data.calls_failed, tags=tags)

    def _get_lb_policy(self, events):
        for event in events:
            lb_prefix = 'Created new LB policy "'
            if event.description.startswith(lb_prefix):
                lb_policy = event.description[len(lb_prefix):]
                return lb_policy.strip('"')

    # Generate metrics from a channelz_pb2.ChannelData
    # This include both channels and subchannels
    def _channel_data_metrics(self, channel_type, channel_data, additional_tags):
        state_value = channel_data.state.state
        state_str = channel_data.state.State.Name(state_value)
        target = channel_data.target

        state_tags = [f'state:{state_str}', f'target:{target}'] + additional_tags
        lb_policy = self._get_lb_policy(channel_data.trace.events)
        if lb_policy:
            state_tags += [f'lb_policy:{lb_policy}']

        self.gauge(f"{channel_type}.state", 1, tags=state_tags)

        creation_time = channel_data.trace.creation_timestamp.ToDatetime()
        uptime = datetime.now() - creation_time
        self.gauge(f"{channel_type}.uptime", uptime.seconds, tags=state_tags)

        tags = [f'target:{target}'] + additional_tags
        self.gauge(f"{channel_type}.calls_started", channel_data.calls_started, tags=tags)
        self.gauge(f"{channel_type}.calls_succeeded", channel_data.calls_succeeded, tags=tags)
        self.gauge(f"{channel_type}.calls_failed", channel_data.calls_failed, tags=tags)

    def _get_subchannel_metrics(self, channelz_stub, subchannel_id, additional_tags):
        subchannel_response = channelz_stub.GetSubchannel(channelz_pb2.GetSubchannelRequest(subchannel_id=subchannel_id))
        subchannel = subchannel_response.subchannel
        self._channel_data_metrics('subchannel', subchannel.data, additional_tags)

    def _get_channels_metrics(self, channelz_stub):
        top_channels = channelz_stub.GetTopChannels(channelz_pb2.GetTopChannelsRequest())
        channels = top_channels.channel
        for channel in channels:
            self._channel_data_metrics('channel', channel.data, [])
            channel_target = channel.data.target
            additional_tags = [f'channel_target:{channel_target}']
            for subchannel_ref in channel.subchannel_ref:
                self._get_subchannel_metrics(channelz_stub, subchannel_ref.subchannel_id, additional_tags)

    def check(self, _):
        # type: (Any) -> None
        logger.error("Connecting to %s", self.addr)
        with grpc.insecure_channel(self.addr) as channel:
            channelz_stub = channelz_pb2_grpc.ChannelzStub(channel)
            self._get_servers_metrics(channelz_stub)
            self._get_channels_metrics(channelz_stub)
