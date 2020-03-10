# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time
from contextlib import closing

from datadog_checks.base import AgentCheck, ConfigurationError


class TCPCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_NAME = 'tcp.can_connect'

    def __init__(self, name, init_config, instances):
        super(TCPCheck, self).__init__(name, init_config, instances)
        instance = self.instances[0]

        self.instance_name = self.normalize_tag(instance['name'])
        port = instance.get('port', None)
        self.timeout = float(instance.get('timeout', 10))
        self.collect_response_time = instance.get('collect_response_time', False)
        custom_tags = instance.get('tags', [])
        self.socket_type = None

        try:
            self.port = int(port)
        except Exception:
            raise ConfigurationError("{} is not a correct port.".format(str(port)))
        try:
            self.url = instance.get('host', None)
            split_url = self.url.split(":")
        except Exception:  # Would be raised if url is not a string
            raise ConfigurationError("A valid url must be specified")

        self.tags = [
            'url:{}:{}'.format(instance.get('host', None), self.port),
            'instance:{}'.format(instance.get('name')),
        ] + custom_tags

        self.service_check_tags = custom_tags + [
            'target_host:{}'.format(self.url),
            'port:{}'.format(self.port),
            'instance:{}'.format(self.instance_name),
        ]

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split_url) == 8:  # It may then be a IP V6 address, we check that
            for block in split_url:
                if len(block) != 4:
                    raise ConfigurationError("{} is not a correct IPv6 address.".format(self.url))
            # It's a correct IP V6 address
            self.addr = self.url
            self.socket_type = socket.AF_INET6
        else:
            self.socket_type = socket.AF_INET
            try:
                self.resolve_ip()
            except Exception:
                msg = "URL: {} is not a correct IPv4, IPv6 or hostname".format(self.url)
                raise ConfigurationError(msg)

    def resolve_ip(self):
        self.addr = socket.gethostbyname(self.url)

    def connect(self):
        with closing(socket.socket(self.socket_type)) as sock:
            sock.settimeout(self.timeout)
            start = time.time()
            sock.connect((self.addr, self.port))
            response_time = time.time() - start
            return response_time

    def check(self, instance):
        start = time.time()  # Avoid initialisation warning
        self.log.debug("Connecting to %s %d", self.addr, self.port)
        try:
            response_time = self.connect()
            self.log.debug("%s:%d is UP", self.addr, self.port)
            self.report_as_service_check(AgentCheck.OK, 'UP')
            if self.collect_response_time:
                self.gauge(
                    'network.tcp.response_time', response_time, tags=self.tags,
                )
        except Exception as e:
            length = int((time.time() - start) * 1000)
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
                self.log.info("%s:%d is DOWN (%s). Connection failed after %d ms", self.addr, self.port, str(e), length)
                self.report_as_service_check(
                    AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
                )
            if self.socket_type == socket.AF_INET:
                self.log.debug("Attempting to re-resolve IP for %s:%d", self.addr, self.port)
                try:
                    self.resolve_ip()
                except Exception:
                    self.log.debug("Unable to re-resolve IP for %s:%d", self.addr, self.port)

    def report_as_service_check(self, status, msg=None):
        if status == AgentCheck.OK:
            msg = None
        self.service_check(self.SERVICE_CHECK_NAME, status, tags=self.service_check_tags, message=msg)
        # Report as a metric as well
        self.gauge("network.tcp.can_connect", 1 if status == AgentCheck.OK else 0, tags=self.service_check_tags)
