# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
from collections import namedtuple
from contextlib import closing
from typing import Any, List, Optional  # noqa: F401

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.time import get_precise_time

AddrTuple = namedtuple('AddrTuple', ['address', 'socket_type'])


class TCPCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_NAME = 'tcp.can_connect'
    CONFIGURATION_ERROR_MSG = "`{}` is an invalid `{}`; a {} must be specified."
    DEFAULT_IP_CACHE_DURATION = None

    def __init__(self, name, init_config, instances):
        super(TCPCheck, self).__init__(name, init_config, instances)
        instance = self.instances[0]

        self.instance_name = self.normalize_tag(instance['name'])
        self.timeout = float(instance.get('timeout', 10))
        self.collect_response_time = instance.get('collect_response_time', False)
        self.host = instance.get('host', None)
        self._addrs = None
        self.ip_cache_last_ts = 0
        self.ip_cache_duration = self.DEFAULT_IP_CACHE_DURATION
        self.multiple_ips = instance.get('multiple_ips', False)
        self.ipv4_only = instance.get('ipv4_only', False)

        ip_cache_duration = instance.get('ip_cache_duration', None)
        if ip_cache_duration is not None:
            try:
                self.ip_cache_duration = int(ip_cache_duration)
            except Exception:
                raise ConfigurationError(
                    self.CONFIGURATION_ERROR_MSG.format(ip_cache_duration, 'ip_cache_duration', 'number')
                )

        port = instance.get('port', None)
        try:
            self.port = int(port)
        except Exception:
            raise ConfigurationError(self.CONFIGURATION_ERROR_MSG.format(port, 'port', 'number'))
        if not isinstance(self.host, str):  # Would be raised if url is not a string
            raise ConfigurationError(self.CONFIGURATION_ERROR_MSG.format(self.host, 'url', 'string'))

        custom_tags = instance.get('tags', [])
        self.tags = [
            'url:{}:{}'.format(self.host, self.port),
            'instance:{}'.format(instance.get('name')),
        ] + custom_tags

        self.service_check_tags = custom_tags + [
            'target_host:{}'.format(self.host),
            'port:{}'.format(self.port),
            'instance:{}'.format(self.instance_name),
        ]

    @property
    def addrs(self):
        # type: () -> List[AddrTuple]
        if self._addrs is None or self._addrs == []:
            try:
                self.resolve_ips()
            except Exception as e:
                self.log.error(str(e))
                msg = "URL: {} could not be resolved".format(self.host)
                raise CheckException(msg)
        return self._addrs

    def resolve_ips(self):
        # type: () -> None
        if self.ipv4_only:
            _, _, ipv4_list = socket.gethostbyname_ex(self.host)
            self._addrs = [AddrTuple(ipv4_addr, socket.AF_INET) for ipv4_addr in ipv4_list]
        else:
            self._addrs = [
                AddrTuple(sockaddr[0], socket_type)
                for (socket_type, _, _, _, sockaddr) in socket.getaddrinfo(
                    self.host, self.port, 0, 0, socket.IPPROTO_TCP
                )
            ]
        if not self.multiple_ips:
            self._addrs = self._addrs[:1]

        if self._addrs == []:
            raise Exception("No IPs attached to host")
        self.log.debug(
            "%s resolved to %s. Socket type: %s", self.host, self._addrs[0].address, self._addrs[0].socket_type
        )

    def should_resolve_ips(self):
        # type: () -> bool
        if self.ip_cache_duration is None:
            return False
        return get_precise_time() - self.ip_cache_last_ts > self.ip_cache_duration

    def connect(self, addr, socket_type):
        # type: (str, socket.AddressFamily) -> float
        with closing(socket.socket(socket_type)) as sock:
            sock.settimeout(self.timeout)
            start = get_precise_time()
            sock.connect((addr, self.port))
            response_time = get_precise_time() - start
            return response_time

    def check(self, _):
        # type: (Any) -> None
        start = get_precise_time()  # Avoid initialisation warning

        if self.should_resolve_ips():
            self.resolve_ips()
            self.ip_cache_last_ts = start

        self.log.debug("Connecting to %s on port %d", self.host, self.port)

        for addr, socket_type in self.addrs:
            try:
                response_time = self.connect(addr, socket_type)
                self.log.debug("%s:%d is UP (%s)", self.host, self.port, addr)
                self.report_as_service_check(AgentCheck.OK, addr, 'UP')
                if self.collect_response_time:
                    self.gauge(
                        'network.tcp.response_time',
                        response_time,
                        tags=self.tags + ['address:{}'.format(addr)],
                    )
            except Exception as e:
                length = int((get_precise_time() - start) * 1000)
                if isinstance(e, socket.error) and "timed out" in str(e):
                    # The connection timed out because it took more time than the system tcp stack allows
                    self.log.warning(
                        'The connection timed out because it took more time '
                        'than the system tcp stack allows. You might want to '
                        'change this setting to allow longer timeouts'
                    )
                    self.log.info("System tcp timeout. Assuming that the checked system is down")
                    self.report_as_service_check(
                        AgentCheck.CRITICAL,
                        addr,
                        """Socket error: {}.
                    The connection timed out after {} ms because it took more time than the system tcp stack allows.
                    You might want to change this setting to allow longer timeouts""".format(
                            str(e), length
                        ),
                    )
                else:
                    self.log.info(
                        "%s:%d is DOWN (%s) (%s). Connection failed after %d ms",
                        self.host,
                        self.port,
                        addr,
                        str(e),
                        length,
                    )
                    self.report_as_service_check(
                        AgentCheck.CRITICAL, addr, "{}. Connection failed after {} ms".format(str(e), length)
                    )

                if socket_type == socket.AF_INET:
                    self.log.debug("Will attempt to re-resolve IP for %s:%d on next run", self.host, self.port)
                    self._addrs = None

    def report_as_service_check(self, status, addr, msg=None):
        # type: (AgentCheck.service_check, str, Optional[str]) -> None
        if status is AgentCheck.OK:
            msg = None
        extra_tags = ['address:{}'.format(addr)]
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=self.service_check_tags + extra_tags, message=msg)
        # Report as a metric as well
        self.gauge(
            "network.tcp.can_connect", 1 if status == AgentCheck.OK else 0, tags=self.service_check_tags + extra_tags
        )
