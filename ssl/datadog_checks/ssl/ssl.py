# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# to prevent conflicts with built-in SSL libraries:
from __future__ import absolute_import
from datadog_checks.base import AgentCheck
from datadog_checks.errors import CheckException
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
    DEFAULT_EXPIRE_DAYS_WARNING = 14
    DEFAULT_EXPIRE_DAYS_CRITICAL = 7
    DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
    DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600

    def check(self, instance):

        print("this is roman logging stuff")

        url = instance.get('url')
        ssl_version = "unknown"
        tags = ['url:%s' % url]

        if not url:
            raise CheckException("Configuration error, url field missing, please fix ssl.yaml")

        try:
            context = ssl.create_default_context()
            with socket.create_connection((url, 443)) as sock:
                with context.wrap_socket(sock, server_hostname=url) as ssl_sock:
                    print(ssl_sock.getpeercert())
                    ssl_version = ssl_sock.version()
                    print(ssl_version)
                    tags.append('ssl_version:%s' % ssl_version)
        except Exception as e:
            # Something went horribly wrong. Ideally we'd be more specific...
            print("Exception: " + str(e))
            self.service_check('ssl_cert.can_connect', self.CRITICAL, tags=tags)
