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
import re

logger = logging.getLogger(__name__)


class GrpcCheck(AgentCheck):

    # This will be the prefix of every metric and service check the integration sends
    __NAMESPACE__ = 'grpc'

    def __init__(self, name, init_config, instances):
        super(GrpcCheck, self).__init__(name, init_config, instances)
        host = self.instance.get("host")
        port = self.instance.get("port")
        self.addr = '{}:{}'.format(host, port)
        logger.debug("addr: %s", self.addr)

    def _get_server_metrics(self, channelz_stub, server):
        num_sockets = 0
        end = False
        last_socket_id=0

        while not end:
            logger.debug('Queryring sockets, server_id: %d, start_socket_id: %d', server.ref.server_id, last_socket_id)
            sockets_stub = channelz_stub.GetServerSockets(channelz_pb2.GetServerSocketsRequest(server_id=server.ref.server_id,
                max_results=100,
                start_socket_id=last_socket_id))
            # [{socket_id: 17, name: "127.0.0.1:40438 -> 127.0.0.1:8888"}]
            sockets = sockets_stub.socket_ref
            num_sockets += len(sockets)
            last_socket_id = sockets[-1].socket_id
            end = sockets_stub.end

        logger.debug('Processing server %r, %d connected sockets', server, num_sockets)
        server_data = server.data

        tags = []
        # Very likely to be empty
        # https://github.com/grpc/grpc-go/blob/aee9f0ed1722db9c45e66eab9e530e72fa2b067c/server.go#L620
        if hasattr(server.ref, 'server_name'):
            tags = [{'name': server.ref.server_name}]

        for listening_socket in server.listen_socket:
            tags += [f'listening_socket:{listening_socket.name}']

        self.monotonic_count("server.calls_started", server_data.calls_started, tags=tags)
        self.monotonic_count("server.calls_succeeded", server_data.calls_succeeded, tags=tags)
        self.monotonic_count("server.calls_failed", server_data.calls_failed, tags=tags)
        self.count("server.connected_clients", num_sockets, tags=tags)

    def _get_servers_metrics(self, channelz_stub):
        get_servers_res = channelz_stub.GetServers(channelz_pb2.GetServersRequest())
        servers = get_servers_res.server
        logger.debug("Found %d servers", len(servers))
        self.count("server.number_servers", len(servers), tags=[])
        for server in servers:
            self._get_server_metrics(channelz_stub, server)

    def _extract_lb_policy(self, description):
        regex = re.compile('.*LB policy "(.*)"', re.IGNORECASE)
        m = regex.match(description)
        if m is None:
            return None
        return m.group(1)

    def _get_lb_policy(self, events):
        logger.debug('Processing %d events', len(events))
        for event in events:
            # logger.debug('Checking event %s', event)
            if 'LB policy' in event.description:
                # Checking event description: "Channel switches to new LB policy "round_robin"
                regex = re.compile('.*LB policy "(.*)"', re.IGNORECASE)
                m = regex.match(event.description)
                if m is None:
                    break
                return self._extract_lb_policy(event.description)

    # Generate metrics from a channelz_pb2.ChannelData
    # This include both channels and subchannels
    def _channel_data_metrics(self, channel_type, channel_data, additional_tags):
        state_value = channel_data.state.state
        state_str = channel_data.state.State.Name(state_value)

        state_tags = [f'state:{state_str}'] + additional_tags
        if channel_data.target:
            state_tags += [f'target:{channel_data.target}']
        if channel_type == 'channel':
            lb_policy = self._get_lb_policy(channel_data.trace.events)
            logger.debug("lb_policy: %s", lb_policy)
            if lb_policy:
                state_tags += [f'lb_policy:{lb_policy}']

        self.count(f"{channel_type}.state", 1, tags=state_tags)

        creation_time = channel_data.trace.creation_timestamp.ToDatetime()
        uptime = datetime.now() - creation_time
        self.gauge(f"{channel_type}.uptime", uptime.seconds, tags=state_tags)

        self.monotonic_count(f"{channel_type}.calls_started", channel_data.calls_started, tags=state_tags)
        self.monotonic_count(f"{channel_type}.calls_succeeded", channel_data.calls_succeeded, tags=state_tags)
        self.monotonic_count(f"{channel_type}.calls_failed", channel_data.calls_failed, tags=state_tags)

    def _get_subchannel_metrics(self, channelz_stub, subchannel_id, additional_tags):
        subchannel_response = channelz_stub.GetSubchannel(channelz_pb2.GetSubchannelRequest(subchannel_id=subchannel_id))
        subchannel = subchannel_response.subchannel
        self._channel_data_metrics('subchannel', subchannel.data, additional_tags)

    def _get_channels_metrics(self, channelz_stub):
        top_channels = channelz_stub.GetTopChannels(channelz_pb2.GetTopChannelsRequest())
        channels = top_channels.channel
        logger.debug("Found %d channels", len(channels))
        for channel in channels:
            self._channel_data_metrics('channel', channel.data, [])
            channel_target = channel.data.target
            additional_tags = [f'channel_target:{channel_target}']
            logger.debug("Processing %d subchannel", len(channel.subchannel_ref))
            for subchannel_ref in channel.subchannel_ref:
                self._get_subchannel_metrics(channelz_stub, subchannel_ref.subchannel_id, additional_tags)

    def check(self, _):
        # type: (Any) -> None
        logger.info("Connecting to %s", self.addr)
        with grpc.insecure_channel(self.addr) as channel:
            channelz_stub = channelz_pb2_grpc.ChannelzStub(channel)
            self._get_servers_metrics(channelz_stub)
            self._get_channels_metrics(channelz_stub)
