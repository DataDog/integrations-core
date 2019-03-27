# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# to prevent conflicts with built-in SSL libraries:
from __future__ import absolute_import
# import pdb
from datadog_checks.base import AgentCheck
from datadog_checks.errors import CheckException
from .config import SslConfig
from cryptography import x509
from cryptography.hazmat.backends import default_backend

from datetime import datetime
import ssl
import socket

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600


class SslCheck(AgentCheck):
    SERVICE_CHECK_CAN_CONNECT = 'ssl_cert.can_connect'
    SERVICE_CHECK_EXPIRATION = 'ssl_cert.expiration'
    SERVICE_CHECK_IS_VALID = 'ssl_cert.is_valid'

    def check(self, instance):
        config = SslConfig(instance)
        config.check_properly_configured()

        if config.cert_remote:
            self.check_remote_cert(config.host, config.port)
        else:
            self.check_local_cert(config.local_cert_path)

        url = config.host_and_port
        ssl_version = "unknown"
        tags = ['url:%s' % url]
        # pdb.set_trace()

        if not url:
            raise CheckException("Configuration error, url field missing, please fix ssl.yaml")

        try:
            context = ssl.create_default_context()
            sock = socket.create_connection((url, 443))
            ssl_sock = context.wrap_socket(sock, server_hostname=url)
            print(ssl_sock.getpeercert())
            ssl_version = ssl_sock.version()
            print(ssl_version)
            tags.append('ssl_version:%s' % ssl_version)
        except Exception as e:
            # Something went horribly wrong. Ideally we'd be more specific...
            print("Exception: " + str(e))
            self.service_check('ssl_cert.can_connect', self.CRITICAL, tags=tags)

    def check_expiration(self, exp_date):
        # add variables for custom configured thresholds
        seconds_warning = \
            DEFAULT_EXPIRE_WARNING
        seconds_critical = \
            DEFAULT_EXPIRE_CRITICAL
        time_left = exp_date - datetime.utcnow()
        days_left = time_left.days
        seconds_left = time_left.total_seconds()
        print("Exp_date: {}".format(exp_date))
        if seconds_left < seconds_critical:
            print('critical', days_left, seconds_left,
                  "This cert TTL is critical: only {} days before it expires".format(days_left))
        elif seconds_left < seconds_warning:
            print('warning', days_left, seconds_left,
                  "This cert is almost expired, only {} days left".format(days_left))
        else:
            print('up', days_left, seconds_left, "Days left: {}".format(days_left))

    def can_connect(self, status, message=''):
        print("can_connect: {}, {}".format(status, message))

    def is_valid(self, status, message=''):
        print("is_valid: {}, {}".format(status, message))

    def is_expiring(self, status, message=''):
        print("is_expiring: {}, {}".format(status, message))

    def check_protocol_version(self, hostname, port):
        context = ssl.create_default_context()
        sock = socket.create_connection((hostname, port))
        ssock = context.wrap_socket(sock, server_hostname=hostname)
        print(ssock.version())

    def check_remote_cert(self, host, port):
        try:
            context = ssl.create_default_context()
            sock = socket.create_connection((host, port))
            ssock = context.wrap_socket(sock, server_hostname=host)
            return x509.load_der_x509_certificate(ssock.getpeercert(binary_form=True), default_backend())
        except Exception as e:
            self.can_connect('critical', e)

    def check_local_cert(self, local_cert_path):
        try:
            local_cert_file = open(local_cert_path, 'rb')
            local_cert_data = x509.load_pem_x509_certificate(local_cert_file.read(), default_backend())
            self.can_connect('up')
            return local_cert_data
        except Exception as e:
            self.can_connect('critical', e)
            # self.service_check('my_check.all_good', self.CRITICAL, e)
