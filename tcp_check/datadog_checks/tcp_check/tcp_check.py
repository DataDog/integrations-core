# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time

from datadog_checks.base import AgentCheck, ConfigurationError


class TCPCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_NAME = 'tcp.can_connect'

    def __init__(self, name, init_config, instances):
        super(TCPCheck, self).__init__(name, init_config, instances)

        self.instance_name = self.normalize_tag(self.instance['name'])
        self.collect_response_time = self.instance.get('collect_response_time', False)
        self.custom_tags = self.instance.get('tags', [])
        self.socket_type = None

        raw_port = self.instance.get('port', None)
        try:
            self.port = int(raw_port)
        except Exception:
            raise ConfigurationError("{} is not a correct port.".format(str(raw_port)))

        raw_timeout = self.instance.get('timeout', 10)
        try:
            self.timeout = float(raw_timeout)
        except Exception:
            raise ConfigurationError("{} is not a correct timeout.".format(str(raw_timeout)))

        try:
            self.host = self.instance.get('host', None)
            self.split_url = self.host.split(":")
        except Exception:  # Would be raised if url is not a string
            raise ConfigurationError("A valid url must be specified")

        if len(self.split_url) == 8:  # It may then be a IP V6 address, we check that
            for block in self.split_url:
                if len(block) != 4:
                    raise ConfigurationError("{} is not a correct IPv6 address.".format(self.host))

        self._set_socket_type()

    def _set_socket_type(self):
        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(self.split_url) == 8:  # It may then be a IP V6 address, we check that
            self.addr = self.host
            # It's a correct IP V6 address
            self.socket_type = socket.AF_INET6

        if self.socket_type is None:
            try:
                self.addr = socket.gethostbyname(self.host)
                self.socket_type = socket.AF_INET
            except Exception:
                msg = "URL: {} is not a correct IPv4, IPv6 or hostname".format(self.host)
                raise ConfigurationError(msg)

    def check(self, instance):
        response_time = None
        start = time.time()  # Avoid initialisation warning
        try:
            self.log.debug("Connecting to %s %d", self.addr, self.port)
            sock = socket.socket(self.socket_type)
            try:
                sock.settimeout(self.timeout)
                start = time.time()
                sock.connect((self.addr, self.port))
                response_time = time.time() - start
            finally:
                sock.close()
        except socket.timeout as e:
            # The connection timed out because it took more time than the specified value in the yaml config file
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%d is DOWN (%s). Connection failed after %d ms", self.addr, self.port, str(e), length)
            self.report_as_service_check(
                AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
            )
        except socket.error as e:
            length = int((time.time() - start) * 1000)
            if "timed out" in str(e):

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
        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%d is DOWN (%s). Connection failed after %d ms", self.addr, self.port, str(e), length)
            self.report_as_service_check(
                AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
            )
        else:
            self.log.debug("%s:%d is UP", self.addr, self.port)
            self.report_as_service_check(AgentCheck.OK, 'UP')

        if self.collect_response_time and response_time is not None:
            self.gauge(
                'network.tcp.response_time',
                response_time,
                tags=[
                    'url:{}:{}'.format(self.host, self.port),
                    'instance:{}'.format(instance.get('name')),
                ]
                + self.custom_tags,
            )

    def report_as_service_check(self, status, msg=None):
        if status == AgentCheck.OK:
            msg = None

        tags = self.custom_tags + [
            'target_host:{}'.format(self.host),
            'port:{}'.format(self.port),
            'instance:{}'.format(self.instance_name),
        ]

        self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=msg)
        # Report as a metric as well
        self.gauge("network.tcp.can_connect", 1 if status == AgentCheck.OK else 0, tags=tags)
