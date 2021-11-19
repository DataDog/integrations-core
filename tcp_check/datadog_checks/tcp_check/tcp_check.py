# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
from contextlib import closing

from datadog_checks.base import AgentCheck, ConfigurationError
from datadog_checks.base.errors import CheckException
from datadog_checks.base.utils.time import get_precise_time
from datadog_checks.base.utils.tracing import traced_class


@traced_class()
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
        self.socket_type = None
        self._addr = None
        self.ip_cache_last_ts = 0
        self.ip_cache_duration = self.DEFAULT_IP_CACHE_DURATION

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
        try:
            split_url = self.host.split(":")
        except Exception:  # Would be raised if url is not a string
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

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split_url) == 8:  # It may then be a IP V6 address, we check that
            for block in split_url:
                if len(block) != 4:
                    raise ConfigurationError(
                        self.CONFIGURATION_ERROR_MSG.format(self.host, 'IPv6 address', 'valid address')
                    )
            # It's a correct IP V6 address
            self._addr = self.host
            self.socket_type = socket.AF_INET6
        else:
            self.socket_type = socket.AF_INET
            # IP will be resolved at check time

    @property
    def addr(self):
        if self._addr is None:
            try:
                self.resolve_ip()
            except Exception as e:
                self.log.error(str(e))
                msg = "URL: {} could not be resolved".format(self.host)
                raise CheckException(msg)
        return self._addr

    def resolve_ip(self):
        self._addr = socket.gethostbyname(self.host)
        self.log.debug("%s resolved to %s", self.host, self._addr)

    def should_resolve_ip(self):
        if self.ip_cache_duration is None:
            return False
        return get_precise_time() - self.ip_cache_last_ts > self.ip_cache_duration

    def connect(self):
        with closing(socket.socket(self.socket_type)) as sock:
            sock.settimeout(self.timeout)
            start = get_precise_time()
            sock.connect((self.addr, self.port))
            response_time = get_precise_time() - start
            return response_time

    def check(self, _):
        start = get_precise_time()  # Avoid initialisation warning

        if self.should_resolve_ip():
            self.resolve_ip()
            self.ip_cache_last_ts = start

        self.log.debug("Connecting to %s on port %d", self.host, self.port)
        try:
            response_time = self.connect()
            self.log.debug("%s:%d is UP", self.host, self.port)
            self.report_as_service_check(AgentCheck.OK, 'UP')
            if self.collect_response_time:
                self.gauge(
                    'network.tcp.response_time',
                    response_time,
                    tags=self.tags,
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
                    """Socket error: {}.
                 The connection timed out after {} ms because it took more time than the system tcp stack allows.
                 You might want to change this setting to allow longer timeouts""".format(
                        str(e), length
                    ),
                )
            else:
                self.log.info("%s:%d is DOWN (%s). Connection failed after %d ms", self.host, self.port, str(e), length)
                self.report_as_service_check(
                    AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
                )

            if self.socket_type == socket.AF_INET:
                self.log.debug("Will attempt to re-resolve IP for %s:%d on next run", self.host, self.port)
                self._addr = None

    def report_as_service_check(self, status, msg=None):
        if status is AgentCheck.OK:
            msg = None
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=self.service_check_tags, message=msg)
        # Report as a metric as well
        self.gauge("network.tcp.can_connect", 1 if status == AgentCheck.OK else 0, tags=self.service_check_tags)
