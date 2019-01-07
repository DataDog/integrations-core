# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

# stdlib
import socket
import time
import ssl
from datetime import datetime

# project
from datadog_checks.checks import NetworkCheck, Status
from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.ca_cert import get_ca_certs_path


DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600


class BadConfException(Exception):
    pass


class TCPCheck(NetworkCheck):

    SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_CAN_CONNECT = 'tcp.can_connect'
    SERVICE_CHECK_SSL_CERT = 'tcp.ssl_cert'

    def __init__(self, name, init_config, agentConfig, instances=None):
        NetworkCheck.__init__(self, name, init_config, agentConfig, instances)

        self.ca_certs = init_config.get('ca_certs')
        if not self.ca_certs:
            self.ca_certs = get_ca_certs_path()

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
            raise BadConfException("{} is not a correct port.".format(str(port)))
        try:
            url = instance.get('host', None)
            split = url.split(":")
        except Exception:  # Would be raised if url is not a string
            raise BadConfException("A valid url must be specified")

        # IPv6 address format: 2001:db8:85a3:8d3:1319:8a2e:370:7348
        if len(split) == 8:  # It may then be a IP V6 address, we check that
            for block in split:
                if len(block) != 4:
                    raise BadConfException("{} is not a correct IPv6 address.".format(url))

            addr = url
            # It's a correct IP V6 address
            socket_type = socket.AF_INET6

        if socket_type is None:
            try:
                addr = socket.gethostbyname(url)
                socket_type = socket.AF_INET
            except Exception:
                msg = "URL: {} is not a correct IPv4, IPv6 or hostname".format(url)
                raise BadConfException(msg)

        check_certificate_expiration = is_affirmative(instance.get('check_certificate_expiration', False))
        ssl_server_name = instance.get('ssl_server_name') or url
        ca_certs = self.ca_certs or instance.get('ca_certs')
        client_key = instance.get('client_key')
        client_cert = instance.get('client_cert')
        check_hostname = is_affirmative(instance.get('check_hostname', True))
        try:
            days_warning = int(instance.get('days_warning', DEFAULT_EXPIRE_DAYS_WARNING))
        except Exception:
            raise BadConfException("{} should be an integer".format(instance['days_warning']))
        try:
            days_critical = int(instance.get('days_critical', DEFAULT_EXPIRE_DAYS_CRITICAL))
        except Exception:
            raise BadConfException("{} should be an integer".format(instance['days_critical']))
        try:
            seconds_warning = int(instance.get('seconds_warning', 0))
        except Exception:
            raise BadConfException("{} should be an integer".format(instance['seconds_warning']))
        try:
            seconds_critical = int(instance.get('seconds_critical', 0))
        except Exception:
            raise BadConfException("{} should be an integer".format(instance['seconds_critical']))

        return url, addr, port, custom_tags, socket_type, timeout, response_time, \
            check_certificate_expiration, ssl_server_name, ca_certs, \
            client_key, client_cert, check_hostname, \
            days_warning, days_critical, seconds_warning, seconds_critical

    def check_cert_expiration(self, url, addr, port, timeout, ca_certs,
                              check_hostname, ssl_server_name,
                              days_warning, days_critical, seconds_warning, seconds_critical,
                              client_key=None, client_cert=None):
        # thresholds expressed in seconds take precedence over those expressed in days
        seconds_warning = seconds_warning or days_warning * 24 * 3600
        seconds_critical = seconds_critical or days_critical * 24 * 3600
        server_name = ssl_server_name or url

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(float(timeout))
            sock.connect((url, port))
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_REQUIRED
            context.check_hostname = check_hostname
            context.load_verify_locations(ca_certs)

            if client_cert and client_key:
                context.load_cert_chain(client_cert, keyfile=client_key)

            ssl_sock = context.wrap_socket(sock, server_hostname=server_name)
            cert = ssl_sock.getpeercert()

        except ssl.CertificateError as e:
            self.log.debug("The hostname on the SSL certificate does not match the given host: {}".format(e))
            return Status.CRITICAL, 0, 0, str(e)
        except ssl.SSLError as e:
            self.log.debug("error: {}. Cert might be expired.".format(e))
            return Status.DOWN, 0, 0, str(e)
        except Exception as e:
            self.log.debug("Site is down, unable to connect to get cert expiration: {}".format(e))
            return Status.DOWN, 0, 0, str(e)

        exp_date = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
        time_left = exp_date - datetime.utcnow()
        days_left = time_left.days
        seconds_left = time_left.total_seconds()

        self.log.debug("Exp_date: {}".format(exp_date))
        self.log.debug("seconds_left: {}".format(seconds_left))

        if seconds_left < seconds_critical:
            return (Status.CRITICAL, days_left, seconds_left,
                    "This cert TTL is critical: only {} days before it expires".format(days_left))

        elif seconds_left < seconds_warning:
            return (Status.WARNING, days_left, seconds_left,
                    "This cert is almost expired, only {} days left".format(days_left))

        else:
            return Status.UP, days_left, seconds_left, "Days left: {}".format(days_left)

    def _check(self, instance):
        url, addr, port, custom_tags, socket_type, timeout, response_time, \
            check_certificate_expiration, ssl_server_name, ca_certs, \
            client_key, client_cert, check_hostname, \
            days_warning, days_critical, seconds_warning, seconds_critical = self._load_conf(instance)
        status_checks = []

        start = time.time()
        try:
            self.log.debug("Connecting to {} {}".format(addr, port))
            sock = socket.socket(socket_type)
            try:
                sock.settimeout(timeout)
                sock.connect((addr, port))
            finally:
                sock.close()

        except socket.timeout as e:
            # The connection timed out because it took more time than the specified value in the yaml config file
            length = int((time.time() - start) * 1000)
            self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(addr, port, str(e), length))
            status_checks.append((
                self.SERVICE_CHECK_CAN_CONNECT,
                Status.DOWN,
                "{}. Connection failed after {} ms".format(str(e), length)))

        except socket.error as e:
            length = int((time.time() - start) * 1000)
            if "timed out" in str(e):

                # The connection timed out becase it took more time than the system tcp stack allows
                self.log.warning('The connection timed out because it took more time '
                                 'than the system tcp stack allows. You might want to '
                                 'change this setting to allow longer timeouts')
                self.log.info("System tcp timeout. Assuming that the checked system is down")
                status_checks.append((
                    self.SERVICE_CHECK_CAN_CONNECT,
                    Status.DOWN,
                    """Socket error: {}.
                 The connection timed out after {} ms because it took more time than the system tcp stack allows.
                 You might want to change this setting to allow longer timeouts""".format(str(e), length)))
            else:
                self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(addr, port, str(e), length))
                status_checks.append((
                    self.SERVICE_CHECK_CAN_CONNECT,
                    Status.DOWN,
                    "{}. Connection failed after {} ms".format(str(e), length)))

        except Exception as e:
            length = int((time.time() - start) * 1000)
            self.log.info("{}:{} is DOWN ({}). Connection failed after {} ms".format(addr, port, str(e), length))
            status_checks.append((
                self.SERVICE_CHECK_CAN_CONNECT,
                Status.DOWN,
                "{}. Connection failed after {} ms".format(str(e), length)))
        else:
            self.log.debug("{}:{} is UP".format(addr, port))
            status_checks.append((self.SERVICE_CHECK_CAN_CONNECT, Status.UP, ""))

        if response_time:
            self.gauge('network.tcp.response_time', time.time() - start,
                       tags=['url:{}:{}'.format(instance.get('host', None), port),
                             'instance:{}'.format(instance.get('name'))] + custom_tags)

        if check_certificate_expiration:
            ssl_check_status, days_left, seconds_left, message = self.check_cert_expiration(
                url, addr, port, timeout, ca_certs,
                check_hostname, ssl_server_name,
                days_warning, days_critical, seconds_warning, seconds_critical,
                client_key, client_cert)
            tags_list = custom_tags + [
                'target_host:{}'.format(url),
                'port:{}'.format(port),
                'instance:{}'.format(self.normalize(instance['name']))
            ]
            self.gauge('tcp.ssl.days_left', days_left, tags=tags_list)
            self.gauge('tcp.ssl.seconds_left', seconds_left, tags=tags_list)
            status_checks.append((self.SERVICE_CHECK_SSL_CERT, ssl_check_status, message))

        return status_checks

    def report_as_service_check(self, sc_name, status, instance, msg=None):
        instance_name = self.normalize(instance['name'])
        host = instance.get('host', None)
        port = instance.get('port', None)
        custom_tags = instance.get('tags', [])

        if status == Status.UP:
            msg = None

        tags = custom_tags + ['target_host:{}'.format(host),
                              'port:{}'.format(port),
                              'instance:{}'.format(instance_name)]

        self.service_check(sc_name,
                           NetworkCheck.STATUS_TO_SERVICE_CHECK[status],
                           tags=tags,
                           message=msg
                           )
        # Report as a metric as well
        if sc_name == self.SERVICE_CHECK_CAN_CONNECT:
            self.gauge("network.tcp.can_connect", 1 if status == Status.UP else 0, tags=tags)
