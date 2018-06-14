# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import socket
import time

# project
from checks.network_checks import NetworkCheck, Status


class BadConfException(Exception):
    pass


class TCPCheck(NetworkCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_NAME = 'tcp.can_connect'

    def _load_conf(self, instance):
        # Fetches the conf

        port = instance.get('port', None)
        timeout = float(instance.get('timeout', 10))
        response_time = instance.get('collect_response_time', False)
        custom_tags = instance.get('tags', [])
        socket_type = None
        try:
            port = int(port)
        except Exception:
            raise BadConfException("%s is not a correct port." % str(port))

        try:
            url = instance.get('host', None)
            split = url.split(":")
        except Exception:  # Would be raised if url is not a string
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8:  # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("%s is not a correct IPv6 address." % url)

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6

        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                msg = "URL: %s is not a correct IPv4, IPv6 or hostname" % url
                raise BadConfException(msg)

        return addr, port, custom_tags, socket_type, timeout, response_time

    def _check(self, instance):
        addr, port, custom_tags, socket_type, timeout, response_time = self._load_conf(instance)
        start = time.time()
        try:
            self.log.debug("Connecting to %s %s" % (addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except socket.timeout as e:
            # The connection timed out because it took more time than the specified value in the yaml config file
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" % (addr, port, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            if "timed out" in str(e):

                # The connection timed out becase it took more time than the system tcp stack allows
                self.log.warning("The connection timed out because it took more time than the system tcp stack allows. You might want to change this setting to allow longer timeouts")
                self.log.info("System tcp timeout. Assuming that the checked system is down")
                return Status.DOWN, """Socket error: %s.
                 The connection timed out after %s ms because it took more time than the system tcp stack allows.
                 You might want to change this setting to allow longer timeouts""" % (str(e), length)
            else:
                self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" % (addr, port, str(e), length))
                return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s:%s is DOWN (%s). Connection failed after %s ms" % (addr, port, str(e), length))
            return Status.DOWN, "%s. Connection failed after %s ms" % (str(e), length)

        if response_time:
            self.gauge('network.tcp.response_time', time.time() - start, tags=['url:%s:%s' % (instance.get('host', None), port), 'instance:%s' % instance.get('name')] + custom_tags)

        self.log.debug("%s:%s is UP" % (addr, port))
        return Status.UP, "UP"

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        instance_name = self.normalize(instance['name'])
        host = instance.get('host', None)
        port = instance.get('port', None)
        custom_tags = instance.get('tags', [])

        if status == Status.UP:
            msg = None

        tags = custom_tags + ['target_host:{0}'.format(host),
                              'port:{0}'.format(port),
                              'instance:{0}'.format(instance_name)]

        self.service_check(self.SERVICE_CHECK_NAME,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )
