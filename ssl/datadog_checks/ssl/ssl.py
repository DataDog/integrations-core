# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
# to prevent conflicts with built-in SSL libraries:
from __future__ import absolute_import
# import pdb
from datadog_checks.base import AgentCheck
from datadog_checks.errors import CheckException
from config import SslConfig
import ssl
import socket

DEFAULT_EXPIRE_DAYS_WARNING = 14
DEFAULT_EXPIRE_DAYS_CRITICAL = 7
DEFAULT_EXPIRE_WARNING = DEFAULT_EXPIRE_DAYS_WARNING * 24 * 3600
DEFAULT_EXPIRE_CRITICAL = DEFAULT_EXPIRE_DAYS_CRITICAL * 24 * 3600


class SslCheck(AgentCheck):
    # tcp SOURCE_TYPE_NAME = 'system'
    SERVICE_CHECK_CAN_CONNECT = 'ssl_cert.can_connect'
    SERVICE_CHECK_EXPIRATION = 'ssl_cert.expiration'
    SERVICE_CHECK_IS_VALID = 'ssl_cert.is_valid'

    def check(self, instance):
        config = SslConfig(instance)
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
