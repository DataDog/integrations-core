# (C) Datadog, Inc. 2010-2019
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import socket
import time

from datadog_checks.base import AgentCheck


class BadConfException(Exception):
    pass


class TCPCheck(AgentCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_NAME = 'tcp.can_connect'

    def __init__(self, name, init_config, instances):
        super(TCPCheck, self).__init__(name, init_config, instances)
        instance = self.instances[0]

        self.instance_name = self.normalize(instance['name'])
        port = instance.get('port', None)
        self.timeout = float(instance.get('timeout', 10))
        self.response_time = instance.get('collect_response_time', False)
        self.custom_tags = instance.get('tags', [])
        self.socket_type = None

        try:
            self.port = int(port)
        except Exception:
            raise BadConfException("{} is not a correct port.".format(str(port)))

        try:
            self.url = instance.get('host', None)
            split = self.url.split(":")
        except Exception:  # Would be raised if url is not a string
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8:  # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("{} is not a correct IPv6 address.".format(url))

            self.addr = self.url
            # It's a correct IP V6 address
            self.socket_type = socket.AF_INET6

        if self.socket_type is None:
            try:
                self.addr = socket.gethostbyname(self.url)
                self.socket_type = socket.AF_INET
            except Exception:
                msg = "URL: {} is not a correct IPv4, IPv6 or hostname".format(url)
                raise BadConfException(msg)

    def check(self, instance):
        start = time.time()
        try:
            self.log.debug("Connecting to {} {}".format(self.addr, self.port))
            sock = socket.socket(self.socket_type)
            try:
                sock.settimeout(self.timeout)
                sock.connect((self.addr, self.port))
            finally:
                sock.close()

        except socket.timeout as e:
            # The connection timed out because it took more time than the specified value in the yaml config file
            length = int((time.time() - start) * 1000)
            self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(self.addr, self.port, str(e), length))
            self.report_as_service_check(
                AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
            )

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            if "timed out" in str(e):

                # The connection timed out becase it took more time than the system tcp stack allows
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
                self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(self.addr, self.port, str(e), length))
                self.report_as_service_check(
                    AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
                )

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(self.addr, self.port, str(e), length))
            self.report_as_service_check(
                AgentCheck.CRITICAL, "{}. Connection failed after {} ms".format(str(e), length)
            )

        if self.response_time:
            self.gauge(
                'network.tcp.response_time',
                time.time() - start,
                tags=['url:{}:{}'.format(instance.get('host', None), self.port), 'instance:{}'.format(instance.get('name'))]
                     + self.custom_tags,
            )

        self.log.debug("{}:{} is UP".format(self.addr, self.port))
        self.report_as_service_check(AgentCheck.OK, 'UP')

    def report_as_service_check(self, status, msg=None):
        if status == AgentCheck.OK:
            msg = None

        tags = self.custom_tags + [
            'target_host:{}'.format(self.url),
            'port:{}'.format(self.port),
            'instance:{}'.format(self.instance_name),
        ]

        self.service_check(self.SERVICE_CHECK_NAME, status, tags=tags, message=msg)
        # Report as a metric as well
        self.gauge("network.tcp.can_connect", 1 if status == AgentCheck.OK else 0, tags=tags)
