# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any

from datadog_checks.base import AgentCheck

import grpc
import logging
from grpc_channelz.v1 import channelz_pb2
from grpc_channelz.v1 import channelz_pb2_grpc

# from datadog_checks.base.utils.db import QueryManager
# from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
# from json import JSONDecodeError

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
            self.gauge("server.calls_started", server_data.calls_started, tags=tags)
            self.gauge("server.calls_succeeded", server_data.calls_succeeded, tags=tags)


    def _get_channels_metrics(self, channelz_stub):
        top_channels = channelz_stub.GetTopChannels(channelz_pb2.GetTopChannelsRequest())
        print(top_channels)
        # servers = get_server.server
        # self.gauge("server.number_servers", len(servers), tags=[])
        # for server in servers:
            # server_data = server.data
            # tags = []
            # # LB Used?
            # self.gauge("server.calls_started", server_data.calls_started, tags=tags)
            # self.gauge("server.calls_succeeded", server_data.calls_succeeded, tags=tags)


    def check(self, _):
        # type: (Any) -> None
        logger.error("Connecting to %s", self.addr)
        with grpc.insecure_channel(self.addr) as channel:
            channelz_stub = channelz_pb2_grpc.ChannelzStub(channel)
            self._get_servers_metrics(channelz_stub)
            self._get_channels_metrics(channelz_stub)
